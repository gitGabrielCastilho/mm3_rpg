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
        logger.info(f"TokenAuthMiddleware: user inicial={user}, autenticado={getattr(user, 'is_authenticated', False)}")
        
        # Se não estiver autenticado, tenta via token
        if not user or isinstance(user, AnonymousUser) or not getattr(user, 'is_authenticated', False):
            token = self._extract_token(scope)
            logger.info(f"TokenAuthMiddleware: token extraído={'sim' if token else 'não'}")
            if token:
                logger.info(f"TokenAuthMiddleware: tentando validar token")
                user = await self._user_from_token(token)
                if user:
                    scope['user'] = user
                    logger.info(f"TokenAuthMiddleware: autenticado via token, user={user.id}")
                else:
                    logger.warning(f"TokenAuthMiddleware: token inválido ou expirado")
            else:
                logger.warning(f"TokenAuthMiddleware: nenhum token encontrado na query string")
        else:
            logger.info(f"TokenAuthMiddleware: usuário já autenticado via sessão: {user.id}")
        
        return await super().__call__(scope, receive, send)
    
    def _extract_token(self, scope):
        """Extrai o ws_token da query string"""
        try:
            qs = scope.get('query_string', b'').decode()
            logger.info(f"TokenAuthMiddleware: query_string={qs}")
            params = urllib.parse.parse_qs(qs)
            logger.info(f"TokenAuthMiddleware: parsed params={params}")
            tok = params.get('ws_token') or params.get('token')
            if tok:
                logger.info(f"TokenAuthMiddleware: token encontrado")
                return tok[0]
            else:
                logger.warning(f"TokenAuthMiddleware: ws_token ou token não encontrado nos params")
        except Exception as e:
            logger.error(f"TokenAuthMiddleware: erro ao extrair token: {e}", exc_info=True)
        return None
    
    @database_sync_to_async
    def _user_from_token(self, token):
        """Valida o token e retorna o usuário"""
        try:
            logger.info(f"TokenAuthMiddleware: validando token com salt='ws-combate'")
            data = signing.loads(token, salt='ws-combate', max_age=60*60*24*30)
            logger.info(f"TokenAuthMiddleware: token payload={data}")
            uid = data.get('uid')
            if not uid:
                logger.warning(f"TokenAuthMiddleware: token não contém uid")
                return None
            user = get_user_model().objects.filter(id=uid).first()
            if user:
                logger.info(f"TokenAuthMiddleware: user encontrado: {user.id} ({user.username})")
            else:
                logger.warning(f"TokenAuthMiddleware: user {uid} não encontrado no BD")
            return user
        except signing.BadSignature:
            logger.warning(f"TokenAuthMiddleware: token com assinatura inválida")
        except signing.SignatureExpired:
            logger.warning(f"TokenAuthMiddleware: token expirado")
        except Exception as e:
            logger.error(f"TokenAuthMiddleware: erro ao validar token: {e}", exc_info=True)
        return None
