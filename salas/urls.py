from django.urls import path
from .views import criar_sala, listar_salas, excluir_sala, entrar_sala, sair_sala

urlpatterns = [
    path('criar/', criar_sala, name='criar_sala'),
    path('listar/', listar_salas, name='listar_salas'),
    path('excluir/<int:sala_id>/', excluir_sala, name='excluir_sala'),
    path('entrar/<int:sala_id>/', entrar_sala, name='entrar_sala'),
    path('sair/', sair_sala, name='sair_sala'),
]