"""
Middleware customizado para autenticação de WebSocket.
Permite autenticação via token de sessão ou via ws_token na query string.
"""
import logging
import urllib.parse
from functools import wraps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core import signing
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


def get_user_from_token(token):
    """Valida o token de forma síncrona e retorna o usuário (ou None)"""
    try:
        logger.info(f"TokenAuth: validando token com salt='ws-combate'")
        data = signing.loads(token, salt='ws-combate', max_age=60*60*24*30)
        logger.info(f"TokenAuth: token payload={data}")
        uid = data.get('uid')
        if not uid:
            logger.warning(f"TokenAuth: token não contém uid")
            return None
        user = get_user_model().objects.filter(id=uid).first()
        if user:
            logger.info(f"TokenAuth: user encontrado: {user.id} ({user.username})")
        else:
            logger.warning(f"TokenAuth: user {uid} não encontrado no BD")
        return user
    except signing.BadSignature:
        logger.warning(f"TokenAuth: token com assinatura inválida")
    except signing.SignatureExpired:
        logger.warning(f"TokenAuth: token expirado")
    except Exception as e:
        logger.error(f"TokenAuth: erro ao validar token: {e}", exc_info=True)
    return None


class TokenAuthMiddleware:
    """
    Middleware que tenta autenticar via ws_token se o usuário não estiver autenticado via sessão.
    Deve ser COLOCADO DEPOIS de AuthMiddlewareStack na pilha de middlewares.
    """
    
    def __init__(self, inner):
        self.inner = inner
        logger.info("TokenAuthMiddleware: inicializado")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket":
            # Não é WebSocket, passa adiante
            return await self.inner(scope, receive, send)
        
        # Obtém o usuário da sessão (já autenticado pelo AuthMiddlewareStack se disponível)
        user = scope.get('user')
        logger.info(f"TokenAuth: user inicial={user}, autenticado={getattr(user, 'is_authenticated', False)}")
        
        # Se não estiver autenticado, tenta via token
        if not user or isinstance(user, AnonymousUser) or not getattr(user, 'is_authenticated', False):
            token = self._extract_token(scope)
            logger.info(f"TokenAuth: token extraído={'sim' if token else 'não'}")
            
            if token:
                logger.info(f"TokenAuth: tentando validar token (async)")
                # Executa a validação de forma assíncrona
                user = await sync_to_async(get_user_from_token)(token)
                if user:
                    scope['user'] = user
                    logger.info(f"TokenAuth: SUCESSO! User autenticado: {user.id} ({user.username})")
                else:
                    logger.warning(f"TokenAuth: validação do token falhou (retornou None)")
            else:
                logger.warning(f"TokenAuth: nenhum token encontrado na query string")
        else:
            logger.info(f"TokenAuth: usuário já autenticado via sessão: {user.id}")
        
        logger.info(f"TokenAuth: passando para inner, user={scope.get('user')}")
        return await self.inner(scope, receive, send)
    
    def _extract_token(self, scope):
        """Extrai o ws_token da query string"""
        try:
            qs = scope.get('query_string', b'').decode()
            logger.info(f"TokenAuth: query_string={qs}")
            params = urllib.parse.parse_qs(qs)
            logger.info(f"TokenAuth: parsed params keys={list(params.keys())}")
            tok = params.get('ws_token') or params.get('token')
            if tok:
                logger.info(f"TokenAuth: token encontrado, comprimento={len(tok[0])}")
                return tok[0]
            else:
                logger.warning(f"TokenAuth: ws_token ou token não encontrado nos params")
        except Exception as e:
            logger.error(f"TokenAuth: erro ao extrair token: {e}", exc_info=True)
        return None
