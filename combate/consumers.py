import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404
from combate.models import Combate

logger = logging.getLogger(__name__)

class CombateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.combate_id = self.scope['url_route']['kwargs']['combate_id']
        self.combate_group_name = f'combate_{self.combate_id}'
        # Autorização: requer usuário autenticado e membro da sala do combate
        user = self.scope.get('user')
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            return await self.close()
        try:
            allowed = await self._user_allowed(int(self.combate_id), user.id)
        except Exception:
            logger.warning("Falha ao checar permissão no WS de combate", exc_info=True)
            return await self.close()
        if not allowed:
            return await self.close()
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
        """Opcional: responder pings; não ecoa mensagens arbitrárias do cliente."""
        try:
            payload = json.loads(text_data)
            if isinstance(payload, dict) and payload.get('tipo') == 'ping':
                await self.send(text_data=json.dumps({'tipo': 'pong', 't': payload.get('t')}))
        except Exception:
            # Silencie entradas inválidas
            pass

    async def combate_message(self, event):
        # Assegura JSON estruturado
        msg = event.get('message')
        try:
            if isinstance(msg, str):
                # Aceita strings JSON (legado)
                json.loads(msg)
                await self.send(text_data=msg)
            else:
                await self.send(text_data=json.dumps(msg))
        except Exception:
            await self.send(text_data=json.dumps({'evento': 'erro', 'detalhe': 'mensagem inválida'}))

    @database_sync_to_async
    def _user_allowed(self, combate_id: int, user_id: int) -> bool:
        try:
            combate = Combate.objects.select_related('sala', 'sala__game_master').get(id=combate_id)
        except Combate.DoesNotExist:
            return False
        # GM da sala ou jogador membro da sala pode conectar
        if combate.sala.game_master_id == user_id:
            return True
        return combate.sala.jogadores.filter(id=user_id).exists()
