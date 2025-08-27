import json
import asyncio
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache

from personagens.models import PerfilUsuario

logger = logging.getLogger(__name__)


class SalaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sala_id = self.scope["url_route"]["kwargs"]["sala_id"]
        self.sala_group_name = f"sala_{self.sala_id}"
        self._hb_task = None

        try:
            await self.channel_layer.group_add(self.sala_group_name, self.channel_name)
        except Exception:
            logger.warning("Falha ao group_add no Channels (ignorado)", exc_info=True)

        await self.accept()

        # Marca presença e notifica
        await self._mark_presence(connected=True)
        await self._broadcast_presence()

        # Inicia heartbeat periódico para manter TTL e disparar atualizações
        self._hb_task = asyncio.create_task(self._heartbeat_loop())

    async def disconnect(self, close_code):
        # Para o heartbeat
        try:
            if getattr(self, "_hb_task", None):
                self._hb_task.cancel()
        except Exception:
            pass

        try:
            await self.channel_layer.group_discard(self.sala_group_name, self.channel_name)
        except Exception:
            logger.warning("Falha ao group_discard no Channels (ignorado)", exc_info=True)

        # Marca ausência e notifica
        await self._mark_presence(connected=False)
        await self._broadcast_presence()

    async def sala_message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps(message))

    async def receive(self, text_data=None, bytes_data=None):
        """Handle optional keepalive pings or ignore client messages.
        Prevents unexpected disconnects when clients send JSON pings.
        """
        try:
            if text_data:
                payload = json.loads(text_data)
                if isinstance(payload, dict) and payload.get("tipo") == "ping":
                    # Optional pong to keep intermediaries happy
                    await self.send(text_data=json.dumps({"tipo": "pong", "t": payload.get("t")}))
        except Exception:
            # Never crash on malformed input; just ignore
            logger.debug("Ignoring malformed WS message", exc_info=True)

    # ======== Helpers ========
    def _presence_key(self):
        user = self.scope.get("user")
        user_id = getattr(user, "id", None)
        # Diferencie por canal para suportar múltiplas conexões simultâneas do mesmo usuário
        channel = getattr(self, "channel_name", "")
        return f"presence:sala:{self.sala_id}:user:{user_id}:chan:{channel}"

    def _presence_user_key(self):
        user = self.scope.get("user")
        user_id = getattr(user, "id", None)
        return f"presence:sala:{self.sala_id}:user:{user_id}"

    async def _broadcast_presence(self):
        try:
            await self.channel_layer.group_send(
                self.sala_group_name,
                {
                    "type": "sala_message",
                    "message": {"tipo": "presence", "sala_id": int(self.sala_id)},
                },
            )
        except Exception:
            logger.warning("Falha ao group_send no Channels (ignorado)", exc_info=True)

    async def _mark_presence(self, connected: bool):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            return
        key_chan = self._presence_key()
        key_user = self._presence_user_key()
        TTL = 30  # segundos
        if connected:
            # Atualiza chave por canal
            cache.set(key_chan, 1, timeout=TTL)
            # Atualiza contador agregado por usuário
            count = cache.get(key_user, 0)
            try:
                count = int(count)
            except Exception:
                count = 0
            count += 1
            cache.set(key_user, count, timeout=TTL)
            # Assegure que o perfil aponte para a sala atual
            await self._set_user_sala_atual(user.id, int(self.sala_id))
        else:
            # Desconexão: não marque offline imediatamente para evitar flicker
            # em reconexões rápidas. Mantém a presença até o TTL expirar.
            # Se houver múltiplas conexões, podemos diminuir o contador, mas
            # nunca deletar imediatamente; a limpeza final ocorre por TTL.
            # Canal: mantém até expirar naturalmente
            cache.set(key_chan, 1, timeout=TTL)
            # Usuário: decrementa, mas mantém pelo menos 1 até TTL
            count = cache.get(key_user, 0)
            try:
                count = int(count)
            except Exception:
                count = 0
            if count > 1:
                cache.set(key_user, count - 1, timeout=TTL)
            else:
                cache.set(key_user, 1, timeout=TTL)

    async def _presence_heartbeat(self):
        """Renova o TTL da presença sem alterar o contador."""
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            return
        key_chan = self._presence_key()
        key_user = self._presence_user_key()
        TTL = 30  # segundos
        if cache.get(key_chan, 0):
            cache.set(key_chan, 1, timeout=TTL)
        # Renova também a chave agregada do usuário sem alterar o valor
        val = cache.get(key_user, 0)
        if val:
            cache.set(key_user, val, timeout=TTL)

    async def _heartbeat_loop(self):
        try:
            while True:
                await asyncio.sleep(10)
                await self._presence_heartbeat()
                await self._broadcast_presence()
        except asyncio.CancelledError:
            return

    @database_sync_to_async
    def _set_user_sala_atual(self, user_id: int, sala_id: int):
        try:
            perfil = PerfilUsuario.objects.get(user_id=user_id)
            if perfil.sala_atual_id != sala_id:
                perfil.sala_atual_id = sala_id
                perfil.save(update_fields=["sala_atual"])
        except PerfilUsuario.DoesNotExist:
            pass

    @database_sync_to_async
    def _clear_user_sala_if_matches(self, user_id: int, sala_id: int):
        try:
            perfil = PerfilUsuario.objects.get(user_id=user_id)
            if perfil.sala_atual_id == sala_id:
                perfil.sala_atual = None
                perfil.save(update_fields=["sala_atual"])
        except PerfilUsuario.DoesNotExist:
            pass