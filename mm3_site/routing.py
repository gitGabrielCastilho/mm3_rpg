import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import combate.routing
import salas.routing
from django.core.asgi import get_asgi_application

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            combate.routing.websocket_urlpatterns + salas.routing.websocket_urlpatterns
        )
    ),
})
