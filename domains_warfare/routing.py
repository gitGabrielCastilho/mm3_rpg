from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/warfare/(?P<combate_id>\d+)/?$', consumers.WarfareConsumer.as_asgi()),
]
