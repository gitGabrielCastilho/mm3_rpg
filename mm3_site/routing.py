import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from mm3_site.ws_auth_middleware import TokenAuthMiddleware

# Inicializa Django antes de importar rotas que referenciam models
django_asgi_app = get_asgi_application()

import combate.routing  # noqa: E402
import salas.routing    # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # Ordem importa: primeiro tenta sessão (AuthMiddlewareStack); se ficar Anonymous,
    # TokenAuthMiddleware injeta user via ws_token na query.
    "websocket": AuthMiddlewareStack(
        TokenAuthMiddleware(
            URLRouter(
                combate.routing.websocket_urlpatterns + salas.routing.websocket_urlpatterns
            )
        )
    ),
})
