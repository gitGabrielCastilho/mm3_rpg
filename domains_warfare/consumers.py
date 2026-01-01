import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models_warfare import CombateWarfare

logger = logging.getLogger(__name__)


class WarfareConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.combate_id = self.scope['url_route']['kwargs']['combate_id']
            self.group_name = f'warfare_{self.combate_id}'

            user = self.scope.get('user')
            if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
                await self.close(code=4001)
                return

            allowed = await self._user_allowed(int(self.combate_id), user.id)
            if not allowed:
                await self.close(code=4003)
                return

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        except Exception:
            try:
                await self.close(code=4000)
            except Exception:
                pass

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data)
            if isinstance(payload, dict) and payload.get('tipo') == 'ping':
                await self.send(text_data=json.dumps({'tipo': 'pong', 't': payload.get('t')}))
        except Exception:
            return

    async def combate_message(self, event):
        msg = event.get('message')
        try:
            if isinstance(msg, str):
                json.loads(msg)
                await self.send(text_data=msg)
            else:
                await self.send(text_data=json.dumps(msg))
        except Exception:
            await self.send(text_data=json.dumps({'evento': 'erro', 'detalhe': 'mensagem inválida'}))

    @database_sync_to_async
    def _user_allowed(self, combate_id: int, user_id: int) -> bool:
        try:
            combate = CombateWarfare.objects.select_related('sala', 'sala__game_master').get(pk=combate_id)
        except CombateWarfare.DoesNotExist:
            return False
        if combate.sala.game_master_id == user_id:
            return True
        # Jogador ligado a algum domain participante
        return combate.domains.filter(criador_id=user_id).exists() or combate.domains.filter(jogadores_acesso__id=user_id).exists()
