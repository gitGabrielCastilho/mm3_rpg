import os
from django.core.asgi import get_asgi_application
import mm3_site.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm3_site.settings')

application = mm3_site.routing.application
