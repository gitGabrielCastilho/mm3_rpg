import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')
from django.core.asgi import get_asgi_application

# Inicializa o app Django para HTTP
django_asgi_app = get_asgi_application()

# Importa a configuração de routing Channels após inicializar Django
from .routing import application as channels_application

# Exponha o application de Channels (que já inclui HTTP via django_asgi_app)
application = channels_application
