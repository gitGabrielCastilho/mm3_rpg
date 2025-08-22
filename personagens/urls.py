from django.urls import path
from .views import (
    criar_personagem,
    listar_personagens,
    editar_personagem,
    excluir_personagem,
    ficha_personagem,
    criar_npc,
    listar_npcs,
    editar_npc,
    excluir_npc,
)

urlpatterns = [
    path('criar/', criar_personagem, name='criar_personagem'),
    path('npc/criar/<int:sala_id>/', criar_npc, name='criar_npc'),
    path('npc/meus/', listar_npcs, name='listar_npcs'),
    path('npc/editar/<int:personagem_id>/', editar_npc, name='editar_npc'),
    path('npc/excluir/<int:personagem_id>/', excluir_npc, name='excluir_npc'),
    path('meus/', listar_personagens, name='listar_personagens'),
    path('editar/<int:personagem_id>/', editar_personagem, name='editar_personagem'),
    path('excluir/<int:personagem_id>/', excluir_personagem, name='excluir_personagem'),
    path('ficha/<int:personagem_id>/', ficha_personagem, name='ficha_personagem'),
]
