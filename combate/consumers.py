import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CombateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.combate_id = self.scope['url_route']['kwargs']['combate_id']
        self.combate_group_name = f'combate_{self.combate_id}'
        print('Cliente conectou ao combate', self.combate_id)
        await self.channel_layer.group_add(
            self.combate_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.combate_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Recebe ação do usuário e repassa para todos
        await self.channel_layer.group_send(
            self.combate_group_name,
            {
                'type': 'combate_message',
                'message': text_data,
            }
        )

    async def combate_message(self, event):
        print('Enviando mensagem para o cliente:', event['message'])
        await self.send(text_data=event['message'])
