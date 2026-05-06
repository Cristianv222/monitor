import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ServerMetricsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "server_metrics_group"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def metrics_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))

class SubscriptionMetricsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sub_id = self.scope['url_route']['kwargs']['sub_id']
        self.group_name = f"sub_metrics_{self.sub_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def metrics_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))

import threading
from channels.generic.websocket import WebsocketConsumer
import docker

class ContainerLogsConsumer(WebsocketConsumer):
    def connect(self):
        self.container_id = self.scope['url_route']['kwargs']['container_id']
        self.accept()
        self.keep_running = True
        self.thread = threading.Thread(target=self.stream_logs)
        self.thread.start()

    def disconnect(self, close_code):
        self.keep_running = False

    def stream_logs(self):
        try:
            client = docker.from_env()
            container = client.containers.get(self.container_id)
            for line in container.logs(stream=True, tail=200, follow=True):
                if not self.keep_running:
                    break
                self.send(text_data=json.dumps({
                    'message': line.decode('utf-8', errors='replace')
                }))
        except Exception as e:
            if self.keep_running:
                self.send(text_data=json.dumps({'error': str(e)}))
