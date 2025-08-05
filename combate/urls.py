from django.urls import path
from .views import atualizar_posicao_token, remover_mapa_global, adicionar_mapa_global, listar_mapas, adicionar_mapa, remover_mapa, remover_participante, adicionar_participante, realizar_ataque ,criar_combate, detalhes_combate, passar_turno, listar_combates, iniciar_turno, avancar_turno, deletar_combate,finalizar_combate

urlpatterns = [
    path('combate/<int:combate_id>/atacar/', realizar_ataque, name='realizar_ataque'),
    path('novo/<int:sala_id>/', criar_combate, name='criar_combate'),
    path('<int:combate_id>/', detalhes_combate, name='detalhes_combate'),
    path('passar_turno/<int:combate_id>/', passar_turno, name='passar_turno'),
    path('listar/<int:sala_id>/', listar_combates, name='listar_combates'),
    path('<int:combate_id>/iniciar-turno/', iniciar_turno, name='iniciar_turno'),
    path('<int:combate_id>/avancar-turno/', avancar_turno, name='avancar_turno'),
    path('<int:combate_id>/finalizar/', finalizar_combate, name='finalizar_combate'),
    path('<int:combate_id>/deletar/', deletar_combate, name='deletar_combate'),
    path('<int:combate_id>/adicionar-participante/', adicionar_participante, name='adicionar_participante'),
    path('<int:combate_id>/remover-participante/<int:participante_id>/', remover_participante, name='remover_participante'),
    path('<int:combate_id>/adicionar-mapa/', adicionar_mapa, name='adicionar_mapa'),
    path('<int:combate_id>/remover-mapa/<int:mapa_id>/', remover_mapa, name='remover_mapa'),
    path('mapas/adicionar/', adicionar_mapa_global, name='adicionar_mapa_global'),
    path('mapas/', listar_mapas, name='listar_mapas'),
    path('mapas/remover/<int:mapa_id>/', remover_mapa_global, name='remover_mapa_global'),
    path('atualizar-posicao-token/<int:token_id>/', atualizar_posicao_token, name='atualizar_posicao_token'),
]
