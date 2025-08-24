import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging
from channels.db import database_sync_to_async
from django.core.cache import cache

from personagens.models import PerfilUsuario


logger = logging.getLogger(__name__)

class SalaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sala_id = self.scope['url_route']['kwargs']['sala_id']
        self.sala_group_name = f'sala_{self.sala_id}'
        try:
            await self.channel_layer.group_add(self.sala_group_name, self.channel_name)
        except Exception:
            logger.warning("Falha ao group_add no Channels (ignorado)", exc_info=True)
        await self.accept()
        # Marca presença ao conectar
        await self._mark_presence(connected=True)
        # Notifica clientes para atualizarem a sidebar
        await self._broadcast_presence()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.sala_group_name, self.channel_name)
        except Exception:
            logger.warning("Falha ao group_discard no Channels (ignorado)", exc_info=True)
        # Marca ausência ao desconectar
        await self._mark_presence(connected=False)
        # Notifica clientes para atualizarem a sidebar
        await self._broadcast_presence()

    async def sala_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))

    # ======== Helpers ========
    def _presence_key(self):
        user = self.scope.get('user')
        user_id = getattr(user, 'id', None)
        return f"presence:sala:{self.sala_id}:user:{user_id}"

    async def _broadcast_presence(self):
        try:
            await self.channel_layer.group_send(
                self.sala_group_name,
                {
                    'type': 'sala_message',
                    'message': {'tipo': 'presence', 'sala_id': int(self.sala_id)}
                }
            )
        except Exception:
            logger.warning("Falha ao group_send no Channels (ignorado)", exc_info=True)

    async def _mark_presence(self, connected: bool):
        user = self.scope.get('user')
        if not user or not getattr(user, 'is_authenticated', False):
            return
        key = self._presence_key()
        # Atualiza contador de conexões por usuário/sala para lidar com múltiplas abas
        count = cache.get(key, 0)
        if connected:
            count += 1
            cache.set(key, count, timeout=24 * 60 * 60)
            if count == 1:
                await self._set_user_sala_atual(user.id, int(self.sala_id))
        else:
            if count > 1:
                cache.set(key, count - 1, timeout=24 * 60 * 60)
            else:
                cache.delete(key)
                # Só limpa se ainda estiver apontando para esta sala
                await self._clear_user_sala_if_matches(user.id, int(self.sala_id))

    @database_sync_to_async
    def _set_user_sala_atual(self, user_id: int, sala_id: int):
        try:
            perfil = PerfilUsuario.objects.get(user_id=user_id)
            if perfil.sala_atual_id != sala_id:
                perfil.sala_atual_id = sala_id
                perfil.save(update_fields=['sala_atual'])
        except PerfilUsuario.DoesNotExist:
            pass

    @database_sync_to_async
    def _clear_user_sala_if_matches(self, user_id: int, sala_id: int):
        try:
            perfil = PerfilUsuario.objects.get(user_id=user_id)
            if perfil.sala_atual_id == sala_id:
                perfil.sala_atual = None
                perfil.save(update_fields=['sala_atual'])
        except PerfilUsuario.DoesNotExist:
            pass
