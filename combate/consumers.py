import json
import logging
import urllib.parse
from django.core import signing
from django.contrib.auth import get_user_model
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
            token = self._extract_token()
            if token:
                user = await self._user_from_token(token)
                if user:
                    self.scope['user'] = user
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            logger.warning(f"WS combate {self.combate_id}: auth failed (user={user})")
            return await self.close()
        try:
            allowed = await self._user_allowed(int(self.combate_id), user.id)
        except Exception:
            logger.warning("Falha ao checar permissão no WS de combate", exc_info=True)
            return await self.close()
        if not allowed:
            logger.warning(f"WS combate {self.combate_id}: user {user.id} not allowed")
            return await self.close()
        await self.channel_layer.group_add(
            self.combate_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"WS combate {self.combate_id}: user {user.id} connected")

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
                return
            # Broadcast de desenhos leves (não persistidos)
            if isinstance(payload, dict) and payload.get('tipo') == 'draw':
                data = payload.get('data') or {}
                mapa_id = data.get('mapa_id')
                if mapa_id:
                    await self.channel_layer.group_send(
                        self.combate_group_name,
                        {
                            'type': 'combate_message',
                            'message': {
                                'evento': 'draw',
                                **data,
                            }
                        }
                    )
                return
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

    def _extract_token(self):
        try:
            qs = self.scope.get('query_string', b'').decode()
            params = urllib.parse.parse_qs(qs)
            tok = params.get('ws_token') or params.get('token')
            if tok:
                return tok[0]
        except Exception:
            return None
        return None

    @database_sync_to_async
    def _user_from_token(self, token):
        try:
            data = signing.loads(token, salt='ws-combate', max_age=60*60*24*30)
            uid = data.get('uid')
            if not uid:
                return None
            return get_user_model().objects.filter(id=uid).first()
        except Exception:
            return None
