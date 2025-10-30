import json
from channels.generic.websocket import AsyncWebsocketConsumer

class UploadProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("upload_progress", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("upload_progress", self.channel_name)

    async def upload_progress(self, event):
        await self.send(json.dumps({"progress": event["progress"]}))

    async def upload_status(self, event):
        await self.send(json.dumps({
            "status": event["status"],
            "file": event.get("file", ""),
            "summary": event.get("summary", "")
        }))
