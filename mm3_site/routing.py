import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from mm3_site.ws_auth_middleware import HybridAuthMiddleware

# Inicializa Django antes de importar rotas que referenciam models
django_asgi_app = get_asgi_application()

import combate.routing  # noqa: E402
import salas.routing    # noqa: E402
import domains_warfare.routing  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # HybridAuthMiddleware substitui AuthMiddlewareStack + token auth
    "websocket": HybridAuthMiddleware(
        URLRouter(
            combate.routing.websocket_urlpatterns
            + salas.routing.websocket_urlpatterns
            + domains_warfare.routing.websocket_urlpatterns
        )
    ),
})
