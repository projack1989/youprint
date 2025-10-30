from django.db import models
import uuid

class Products(models.Model):
    idProduct = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unique_key = models.CharField(unique=True, max_length=100)
    product_title = models.TextField(null=True, blank=True)
    product_description = models.TextField()
    style = models.TextField()
    sanmar_mainframe_color = models.TextField(null=True, blank=True)
    size = models.CharField(max_length=200)
    color_name = models.CharField(max_length=255)
    piece_price = models.DecimalField(max_digits=10, decimal_places=0)

    class Meta:
        db_table = "tmProducts"
        verbose_name = "Table Products"
        verbose_name_plural = "Tabel Products"

    def __str__(self):
        return self.product_description

class UploadLog(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Failed', 'Failed'),
        ('Success', 'Success'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    total_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    skipped_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)

    class Meta:
        db_table = "tmUploadLog"
        verbose_name = "Upload Log"
        verbose_name_plural = "Upload Logs"

    def __str__(self):
        return f"{self.file_name} ({self.status})"
