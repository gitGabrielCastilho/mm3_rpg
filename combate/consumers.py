import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from combate.models import Combate

logger = logging.getLogger(__name__)

class CombateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.combate_id = self.scope['url_route']['kwargs']['combate_id']
            self.combate_group_name = f'combate_{self.combate_id}'
            logger.info(f"WS combate {self.combate_id}: tentando conectar")
            
            # Autorização: requer usuário autenticado e membro da sala do combate
            # O middleware TokenAuthMiddleware já cuidou da autenticação via token ou sessão
            user = self.scope.get('user')
            logger.info(f"WS combate {self.combate_id}: user={user}, autenticado={getattr(user, 'is_authenticated', False)}")
            
            if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
                logger.warning(f"WS combate {self.combate_id}: auth failed (user={user})")
                await self.close(code=4001)
                return
            
            try:
                allowed = await self._user_allowed(int(self.combate_id), user.id)
                logger.info(f"WS combate {self.combate_id}: user {user.id} allowed={allowed}")
            except Exception as e:
                logger.warning(f"WS combate {self.combate_id}: falha ao checar permissão: {e}", exc_info=True)
                await self.close(code=4003)
                return
            
            if not allowed:
                logger.warning(f"WS combate {self.combate_id}: user {user.id} not allowed")
                await self.close(code=4003)
                return
            
            await self.channel_layer.group_add(
                self.combate_group_name,
                self.channel_name
            )
            await self.accept()
            logger.info(f"WS combate {self.combate_id}: user {user.id} connected")
        except Exception as e:
            logger.error(f"WS combate connection error: {e}", exc_info=True)
            try:
                await self.close(code=4000)
            except Exception:
                pass

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
