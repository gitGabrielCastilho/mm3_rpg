"""
Middleware customizado para autenticação de WebSocket.
Permite autenticação via token de sessão ou via ws_token na query string.
"""
import logging
import urllib.parse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core import signing
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

logger = logging.getLogger(__name__)


class TokenAuthMiddleware(BaseMiddleware):
    """
    Middleware que tenta autenticar via ws_token se o usuário não estiver autenticado via sessão.
    """
    
    async def __call__(self, scope, receive, send):
        # Primeiro, tenta obter o usuário da sessão (via AuthMiddlewareStack)
        user = scope.get('user')
        
        # Se não estiver autenticado, tenta via token
        if not user or isinstance(user, AnonymousUser) or not getattr(user, 'is_authenticated', False):
            token = self._extract_token(scope)
            if token:
                user = await self._user_from_token(token)
                if user:
                    scope['user'] = user
                    logger.info(f"WS: autenticado via token, user={user.id}")
        
        return await super().__call__(scope, receive, send)
    
    def _extract_token(self, scope):
        """Extrai o ws_token da query string"""
        try:
            qs = scope.get('query_string', b'').decode()
            params = urllib.parse.parse_qs(qs)
            tok = params.get('ws_token') or params.get('token')
            if tok:
                return tok[0]
        except Exception as e:
            logger.warning(f"Erro ao extrair token: {e}")
        return None
    
    @database_sync_to_async
    def _user_from_token(self, token):
        """Valida o token e retorna o usuário"""
        try:
            data = signing.loads(token, salt='ws-combate', max_age=60*60*24*30)
            uid = data.get('uid')
            if not uid:
                logger.warning("Token não contém uid")
                return None
            user = get_user_model().objects.filter(id=uid).first()
            if user:
                logger.info(f"Token válido para user {uid}")
            else:
                logger.warning(f"Token válido mas user {uid} não encontrado")
            return user
        except signing.BadSignature:
            logger.warning("Token com assinatura inválida")
        except signing.SignatureExpired:
            logger.warning("Token expirado")
        except Exception as e:
            logger.warning(f"Erro ao validar token: {e}", exc_info=True)
        return None
