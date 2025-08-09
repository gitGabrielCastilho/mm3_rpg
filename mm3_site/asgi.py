import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import combate.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            combate.routing.websocket_urlpatterns
        )
    ),
})
application = get_asgi_application()
