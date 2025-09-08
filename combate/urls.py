from django.urls import path
from . import views
from .views import atualizar_posicao_token, remover_mapa_global, adicionar_mapa_global, listar_mapas, adicionar_mapa, remover_mapa, remover_participante, realizar_ataque, criar_combate, detalhes_combate, passar_turno, listar_combates, iniciar_turno, avancar_turno, deletar_combate, finalizar_combate, adicionar_npc_participante, limpar_historico, encerrar_efeito, encerrar_meus_efeitos, participantes_json
from . import views_ajax

urlpatterns = [
    path('poderes-personagem-ajax/', views.poderes_personagem_ajax, name='poderes_personagem_ajax'),
    path('combate/<int:combate_id>/atacar/', realizar_ataque, name='realizar_ataque'),
    path('novo/<int:sala_id>/', criar_combate, name='criar_combate'),
    path('<int:combate_id>/', detalhes_combate, name='detalhes_combate'),
    path('passar_turno/<int:combate_id>/', passar_turno, name='passar_turno'),
    path('listar/<int:sala_id>/', listar_combates, name='listar_combates'),
    path('<int:combate_id>/iniciar-turno/', iniciar_turno, name='iniciar_turno'),
    path('<int:combate_id>/avancar-turno/', avancar_turno, name='avancar_turno'),
    path('<int:combate_id>/finalizar/', finalizar_combate, name='finalizar_combate'),
    path('<int:combate_id>/limpar-historico/', limpar_historico, name='limpar_historico'),
    path('<int:combate_id>/encerrar-efeito/<int:efeito_id>/', encerrar_efeito, name='encerrar_efeito'),
    path('<int:combate_id>/encerrar-meus-efeitos/', encerrar_meus_efeitos, name='encerrar_meus_efeitos'),
    path('<int:combate_id>/deletar/', deletar_combate, name='deletar_combate'),
    path('<int:combate_id>/adicionar-npc/', adicionar_npc_participante, name='adicionar_npc_participante'),
    path('<int:combate_id>/remover-participante/<int:participante_id>/', remover_participante, name='remover_participante'),
    path('<int:combate_id>/adicionar-mapa/', adicionar_mapa, name='adicionar_mapa'),
    path('<int:combate_id>/remover-mapa/<int:mapa_id>/', remover_mapa, name='remover_mapa'),
    path('mapas/adicionar/', adicionar_mapa_global, name='adicionar_mapa_global'),
    path('mapas/', listar_mapas, name='listar_mapas'),
    path('mapas/remover/<int:mapa_id>/', remover_mapa_global, name='remover_mapa_global'),
    path('atualizar-posicao-token/<int:token_id>/', atualizar_posicao_token, name='atualizar_posicao_token'),
    path('<int:combate_id>/participantes-json/', participantes_json, name='participantes_json'),
    path('<int:combate_id>/tabela_participantes/', views_ajax.tabela_participantes, name='tabela_participantes'),
]
