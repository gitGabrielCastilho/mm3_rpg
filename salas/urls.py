from django.urls import path
from .views import (
    criar_sala,
    listar_salas,
    excluir_sala,
    entrar_sala,
    sair_sala,
    detalhes_sala,
    editar_senha_sala,
    notas_sala,
    criar_nota_sala,
)
from . import views_ajax

urlpatterns = [
    path('criar/', criar_sala, name='criar_sala'),
    path('listar/', listar_salas, name='listar_salas'),
    path('excluir/<int:sala_id>/', excluir_sala, name='excluir_sala'),
    path('entrar/<int:sala_id>/', entrar_sala, name='entrar_sala'),
    path('sair/', sair_sala, name='sair_sala'),
    path('detalhes/<int:sala_id>/', detalhes_sala, name='detalhes_sala'),
    path('editar-senha/<int:sala_id>/', editar_senha_sala, name='editar_senha_sala'),
    path('<int:sala_id>/notas/', notas_sala, name='notas_sala'),
    path('<int:sala_id>/notas/criar/', criar_nota_sala, name='criar_nota_sala'),
    path('sidebar_participantes/<int:sala_id>/', views_ajax.participantes_sidebar, name='sidebar_participantes'),
]