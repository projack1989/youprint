import csv
import time
import re
import unicodedata
import html

import logging
logger = logging.getLogger(__name__)

from decimal import Decimal, InvalidOperation
from django.shortcuts import render
from django.http import JsonResponse
from django.db import IntegrityError, transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Products, UploadLog

# ---------------- helpers ----------------
def normalize_key(v):
    """Normalisasi unique_key: ubah ke string, normalisasi unicode, hilangkan spasi tak terlihat."""
    if v is None:
        return ''
    s = str(v)
    # decode html entities, remove non-utf8 junk if any
    s = html.unescape(s)
    # normalisasi unicode ke NFKC (gabungkan bentuk berbeda)
    s = unicodedata.normalize('NFKC', s)
    # replace non-breaking spaces and zero-width spaces and control chars
    s = re.sub(r'[\u00A0\u200B\u200C\u200D\uFEFF]', '', s)
    # trim and collapse internal whitespace to single space (or remove if you prefer)
    s = s.strip()
    return s

def clean_text(value):
    """Hapus karakter non-UTF8, decode HTML entity, hapus simbol merek dagang, strip."""
    if isinstance(value, str):
        value = value.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
        value = html.unescape(value)
        value = re.sub(r'[®™©]', '', value)
        value = unicodedata.normalize('NFKC', value)
        return value.strip()
    return value

def safe_decimal(value, default=Decimal('0')):
    try:
        return Decimal(str(value).replace(',', '').strip())
    except (InvalidOperation, TypeError, ValueError):
        return default

# ---------------- main view ----------------
def upload_csv(request):

    #logger.debug("Fungsi upload_csv dipanggil.")
    channel_layer = get_channel_layer()

    if request.method == 'POST' and request.FILES.get('file'):
        #logger.debug("Method Post berjalan pada upload_csv.")
        csv_file = request.FILES['file']

        # create upload log
        upload_log = UploadLog.objects.create(file_name=csv_file.name, status='Pending')
        async_to_sync(channel_layer.group_send)(
            "upload_progress", {"type": "upload.status", "status": "Pending", "file": csv_file.name}
        )

        if not csv_file.name.lower().endswith('.csv'):
            upload_log.status = 'Failed'; upload_log.save()
            return JsonResponse({'error': 'File type must CSV'}, status=400)

        try:
            data = csv_file.read().decode('utf-8', errors='ignore').splitlines()
            reader = csv.DictReader(data)
            rows = list(reader)
            total = len(rows)

            upload_log.status = 'Processing'
            upload_log.total_rows = total
            upload_log.save()
            async_to_sync(channel_layer.group_send)(
                "upload_progress", {"type": "upload.status", "status": "Processing", "file": csv_file.name}
            )

            created_count = 0
            updated_count = 0
            failed_count = 0
            notfound_examples = []  # simpan beberapa contoh untuk debugging

            start_time = time.time()

            for i, row in enumerate(rows, start=1):
                try:
                    raw_key = row.get('UNIQUE_KEY', '') or row.get('Unique_Key', '') or row.get('unique_key', '')
                    norm_key = normalize_key(raw_key)
                    if not norm_key:
                        failed_count += 1
                        if len(notfound_examples) < 20:
                            notfound_examples.append({'row': i, 'reason': 'empty_unique_key', 'raw': raw_key})
                        continue

                    # Siapkan data yang akan di-update/dibuat
                    defaults = {
                        'product_title': clean_text(row.get('PRODUCT_TITLE', '')),
                        'product_description': clean_text(row.get('PRODUCT_DESCRIPTION', '')),
                        'style': clean_text(row.get('STYLE#', '')),
                        'sanmar_mainframe_color': clean_text(row.get('SANMAR_MAINFRAME_COLOR', '')),
                        'size': clean_text(row.get('SIZE', '')),
                        'color_name': clean_text(row.get('COLOR_NAME', '')),
                        'piece_price': safe_decimal(row.get('PIECE_PRICE', 0)),
                    }

                    # 1) Coba exact lookup
                    qs = Products.objects.filter(unique_key=norm_key)
                    if qs.exists():
                        #logger.info(f"Cek QS 1: QuerySet ditemukan: {qs}")
                        #print(f'cek QS 1 {qs}')
                        # update existing object(s) — biasanya satu karena unique=True
                        obj = qs.first()
                        for k, v in defaults.items():
                            setattr(obj, k, v)
                        obj.save()
                        updated_count += 1
                    else:
                        #logger.info(f"Cek QS 2: QuerySet ditemukan: {qs}")
                        #print(f'cek QS 2 {qs}')
                        # 2) Coba lookup dengan strip/alternative (case-insensitive)
                        qs2 = Products.objects.filter(unique_key__iexact=norm_key)
                        if qs2.exists():
                            #logger.info(f"Cek QS 3: QuerySet ditemukan: {qs}")
                            #print(f'cek QS 3 {qs}')
                            obj = qs2.first()
                            for k, v in defaults.items():
                                setattr(obj, k, v)
                            obj.save()
                            updated_count += 1
                        else:
                            #logger.info(f"Cek QS 4: QuerySet ditemukan: {qs}")
                            #print(f'cek QS 4 {qs}')
                            # 3) Jika masih tidak ada, buat baru
                            # gunakan unique_key = norm_key
                            Products.objects.create(unique_key=norm_key, **defaults)
                            created_count += 1

                except IntegrityError as ie:
                    # kemungkinan unique constraint race atau tipe data salah
                    failed_count += 1
                    if len(notfound_examples) < 20:
                        notfound_examples.append({'row': i, 'reason': 'integrity_error', 'error': str(ie), 'raw': raw_key})
                except Exception as e:
                    failed_count += 1
                    if len(notfound_examples) < 20:
                        notfound_examples.append({'row': i, 'reason': 'other_error', 'error': str(e), 'raw': raw_key})

                # kirim progress
                progress = int((i / total) * 100) if total else 100
                async_to_sync(channel_layer.group_send)(
                    "upload_progress", {"type": "upload.progress", "progress": progress}
                )

                # 🆕 Tambahan realtime — kirim jumlah created/updated/failed setiap iterasi
                async_to_sync(channel_layer.group_send)(
                    "upload_progress",
                    {
                        "type": "upload.status",              # gunakan event status biar satu handler JS cukup
                        "status": "Processing",
                        "file": upload_log.file_name,
                        "progress": progress,
                        "created_count": created_count,      # 🆕
                        "updated_count": updated_count,      # 🆕
                        "failed_count": failed_count,        # 🆕
                    }
                )

            duration = round(time.time() - start_time, 2)
            upload_log.status = 'Success'
            upload_log.total_rows = total
            upload_log.success_rows = created_count
            upload_log.skipped_rows = updated_count
            upload_log.failed_rows = failed_count
            upload_log.save()

            # kirim final status (summary + contoh masalah)
            async_to_sync(channel_layer.group_send)(
                "upload_progress",
                {
                    "type": "upload.status",
                    "status": "Success",
                    "file": upload_log.file_name,
                    "summary": f"{created_count} created, {updated_count} updated, {failed_count} failed",
                    "examples": notfound_examples[:10],
                }
            )

            return JsonResponse({
                "status": "success",
                "created": created_count,
                "updated": updated_count,
                "failed": failed_count,
                "examples": notfound_examples[:10],
            })

        except Exception as e:
            upload_log.status = 'Failed'
            upload_log.save()
            async_to_sync(channel_layer.group_send)(
                "upload_progress", {"type": "upload.status", "status": "Failed", "file": csv_file.name}
            )
            return JsonResponse({'error': f'Gagal memproses file: {e}'}, status=500)

    # GET: tampilkan halaman + logs
    logs = UploadLog.objects.all().order_by('-uploaded_at')[:20]
    return render(request, 'upload.html', {'logs': logs})
