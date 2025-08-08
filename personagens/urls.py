from django.urls import path
from .views import criar_personagem, listar_personagens, editar_personagem, excluir_personagem, ficha_personagem

urlpatterns = [
    path('criar/', criar_personagem, name='criar_personagem'),
    path('meus/', listar_personagens, name='listar_personagens'),
    path('editar/<int:personagem_id>/', editar_personagem, name='editar_personagem'),
    path('excluir/<int:personagem_id>/', excluir_personagem, name='excluir_personagem'),
    path('ficha/<int:personagem_id>/', ficha_personagem, name='ficha_personagem'),
]
