"""
Middleware customizado para autenticação de WebSocket.
Combina autenticação via sessão + token na query string.
"""
import logging
import urllib.parse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.core import signing
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


def _is_connection_closed_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return 'connection is closed' in msg or 'server closed the connection' in msg


def get_user_from_session(session_key):
    """Obtém user a partir da session key (síncrono)"""
    from django.db import close_old_connections, connection
    if not session_key:
        return None

    for attempt in range(2):
        try:
            # Fecha conexões antigas/stale e garante conexão ativa nesta thread
            close_old_connections()
            connection.ensure_connection()

            session = Session.objects.get(session_key=session_key)
            session_data = session.get_decoded()
            user_id = session_data.get('_auth_user_id')
            if user_id:
                user = get_user_model().objects.get(id=user_id)
                logger.info(f"Session auth OK: user {user.id}")
                return user
            return None
        except Exception as e:
            # Erro transitório comum em PaaS (conexão reciclada/fechada)
            if attempt == 0 and _is_connection_closed_error(e):
                logger.warning("Session auth: conexão fechada, tentando reconectar 1x")
                try:
                    connection.close()
                except Exception:
                    pass
                continue
            logger.info(f"Session auth failed: {e}")
            return None
    return None


def get_user_from_token(token):
    """Valida o token de forma síncrona e retorna o usuário (ou None)"""
    from django.db import close_old_connections, connection
    try:
        logger.info(f"Token auth: validando token com salt='ws-combate'")
        data = signing.loads(token, salt='ws-combate', max_age=60*60*24*30)
        logger.info(f"Token auth: payload={data}")
        uid = data.get('uid')
        if not uid:
            logger.warning(f"Token auth: sem uid no payload")
            return None

        for attempt in range(2):
            try:
                # Fecha conexões antigas/stale e garante conexão ativa nesta thread
                close_old_connections()
                connection.ensure_connection()

                user = get_user_model().objects.filter(id=uid).first()
                if user:
                    logger.info(f"Token auth OK: user {user.id} ({user.username})")
                else:
                    logger.warning(f"Token auth: user {uid} não existe")
                return user
            except Exception as e:
                # Erro transitório comum em PaaS (conexão reciclada/fechada)
                if attempt == 0 and _is_connection_closed_error(e):
                    logger.warning("Token auth: conexão fechada, tentando reconectar 1x")
                    try:
                        connection.close()
                    except Exception:
                        pass
                    continue
                raise
    except signing.BadSignature:
        logger.warning(f"Token auth: assinatura inválida")
    except signing.SignatureExpired:
        logger.warning(f"Token auth: expirado")
    except Exception as e:
        logger.error(f"Token auth: erro: {e}", exc_info=True)
    return None


class HybridAuthMiddleware:
    """
    Middleware que tenta autenticar via:
    1. Sessão (cookies)
    2. Token ws_token na query string
    
    Deve ser colocado ANTES de qualquer outro middleware de autenticação.
    """
    
    def __init__(self, inner):
        self.inner = inner
        logger.info("HybridAuthMiddleware: inicializado")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket":
            # Não é WebSocket, passa direto
            return await self.inner(scope, receive, send)
        
        logger.info(f"HybridAuth: === INICIANDO AUTENTICAÇÃO ===")
        
        # 1. Tenta autenticação via sessão (cookie)
        user = await self._auth_via_session(scope)
        
        # 2. Se não conseguiu, tenta token
        if not user:
            user = await self._auth_via_token(scope)
        
        # 3. Se conseguiu autenticar, injeta no scope
        if user:
            scope['user'] = user
            logger.info(f"HybridAuth: ✅ USER INJETADO: {user.id} ({user.username})")
        else:
            scope['user'] = AnonymousUser()
            logger.warning(f"HybridAuth: ❌ NENHUM MÉTODO DE AUTH FUNCIONOU")
        
        return await self.inner(scope, receive, send)
    
    async def _auth_via_session(self, scope):
        """Tenta autenticação via sessão/cookie"""
        try:
            # Cookie da sessão Django
            cookies = {}
            for cookie_header in scope.get('headers', []):
                if cookie_header[0] == b'cookie':
                    cookie_str = cookie_header[1].decode()
                    for item in cookie_str.split(';'):
                        if '=' in item:
                            key, val = item.split('=', 1)
                            cookies[key.strip()] = val.strip()
            
            session_key = cookies.get('sessionid')
            logger.info(f"HybridAuth: session_key={session_key}")
            
            if session_key:
                user = await sync_to_async(get_user_from_session)(session_key)
                if user:
                    return user
        except Exception as e:
            logger.info(f"HybridAuth: session auth erro: {e}")
        
        return None
    
    async def _auth_via_token(self, scope):
        """Tenta autenticação via ws_token na query string"""
        try:
            qs = scope.get('query_string', b'').decode()
            logger.info(f"HybridAuth: query_string={qs}")
            
            params = urllib.parse.parse_qs(qs)
            logger.info(f"HybridAuth: params keys={list(params.keys())}")
            
            token = None
            if 'ws_token' in params:
                token = params['ws_token'][0]
            elif 'token' in params:
                token = params['token'][0]
            
            if token:
                logger.info(f"HybridAuth: token encontrado, comprimento={len(token)}")
                user = await sync_to_async(get_user_from_token)(token)
                if user:
                    return user
        except Exception as e:
            logger.error(f"HybridAuth: token auth erro: {e}", exc_info=True)
        
        return None
