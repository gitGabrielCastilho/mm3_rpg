from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/combate/(?P<combate_id>\w+)/$', consumers.CombateConsumer.as_asgi()),
]