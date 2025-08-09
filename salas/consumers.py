import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SalaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sala_id = self.scope['url_route']['kwargs']['sala_id']
        self.sala_group_name = f'sala_{self.sala_id}'
        await self.channel_layer.group_add(
            self.sala_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.sala_group_name,
            self.channel_name
        )

    async def sala_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))
