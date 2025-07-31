from django.urls import path
from .views import remover_participante, adicionar_participante, realizar_ataque ,criar_combate, detalhes_combate, passar_turno, listar_combates, iniciar_turno, avancar_turno, deletar_combate,finalizar_combate

urlpatterns = [
    path('combate/<int:combate_id>/atacar/', realizar_ataque, name='realizar_ataque'),
    path('novo/', criar_combate, name='criar_combate'),
    path('<int:combate_id>/', detalhes_combate, name='detalhes_combate'),
    path('passar_turno/<int:combate_id>/', passar_turno, name='passar_turno'),
    path('', listar_combates, name='listar_combates'),
    path('<int:combate_id>/iniciar-turno/', iniciar_turno, name='iniciar_turno'),
    path('<int:combate_id>/avancar-turno/', avancar_turno, name='avancar_turno'),
    path('<int:combate_id>/finalizar/', finalizar_combate, name='finalizar_combate'),
    path('<int:combate_id>/deletar/', deletar_combate, name='deletar_combate'),
    path('<int:combate_id>/adicionar-participante/', adicionar_participante, name='adicionar_participante'),
    path('<int:combate_id>/remover-participante/<int:participante_id>/', remover_participante, name='remover_participante'),
]
