import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Inicializa Django antes de importar rotas que referenciam models
django_asgi_app = get_asgi_application()

import combate.routing  # noqa: E402
import salas.routing    # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            combate.routing.websocket_urlpatterns + salas.routing.websocket_urlpatterns
        )
    ),
})
