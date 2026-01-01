from django.urls import path
from . import views
from . import views_warfare

urlpatterns = [
    # Domain URLs
    path('', views.domain_list, name='domain_list'),
    path('domain/<int:pk>/', views.domain_detail, name='domain_detail'),
    path('domain/create/', views.domain_create, name='domain_create'),
    path('domain/<int:pk>/edit/', views.domain_edit, name='domain_edit'),
    path('domain/<int:pk>/delete/', views.domain_delete, name='domain_delete'),
    
    # Unit URLs
    path('units/', views.unit_list_all, name='unit_list_all'),
    path('domain/<int:domain_pk>/units/', views.unit_list, name='unit_list'),
    path('domain/<int:domain_pk>/units/<int:pk>/', views.unit_detail, name='unit_detail'),
    path('domain/<int:domain_pk>/units/create/', views.unit_create, name='unit_create'),
    path('domain/<int:domain_pk>/units/<int:pk>/edit/', views.unit_edit, name='unit_edit'),
    path('domain/<int:domain_pk>/units/<int:pk>/delete/', views.unit_delete, name='unit_delete'),
    
    # Warfare Combat URLs
    path('warfare/', views_warfare.warfare_listar, name='warfare_listar'),
    path('warfare/criar/', views_warfare.warfare_criar, name='warfare_criar'),
    path('warfare/<int:pk>/', views_warfare.warfare_detalhes, name='warfare_detalhes'),
    path('warfare/<int:pk>/finalizar/', views_warfare.warfare_finalizar, name='warfare_finalizar'),
    path('warfare/<int:pk>/deletar/', views_warfare.warfare_deletar, name='warfare_deletar'),
    path('warfare/<int:pk>/mapa/', views_warfare.warfare_adicionar_mapa, name='warfare_adicionar_mapa'),
    path('warfare/<int:pk>/mapa/<int:mapa_id>/remover/', views_warfare.warfare_remover_mapa, name='warfare_remover_mapa'),
    path('warfare/<int:pk>/posicao/<int:posicao_id>/', views_warfare.warfare_atualizar_posicao_token, name='warfare_atualizar_posicao_token'),
    path('warfare/<int:pk>/ataque/', views_warfare.warfare_resolver_ataque, name='warfare_resolver_ataque'),
    
    # AJAX endpoints
    path('ajax/calculate-unit-cost/', views.calculate_unit_cost, name='calculate_unit_cost'),
]
