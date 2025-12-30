from django.urls import path
from . import views

urlpatterns = [
    # Domain URLs
    path('', views.domain_list, name='domain_list'),
    path('domain/<int:pk>/', views.domain_detail, name='domain_detail'),
    path('domain/create/', views.domain_create, name='domain_create'),
    path('domain/<int:pk>/edit/', views.domain_edit, name='domain_edit'),
    path('domain/<int:pk>/delete/', views.domain_delete, name='domain_delete'),
    
    # Unit URLs
    path('domain/<int:domain_pk>/units/', views.unit_list, name='unit_list'),
    path('domain/<int:domain_pk>/units/<int:pk>/', views.unit_detail, name='unit_detail'),
    path('domain/<int:domain_pk>/units/create/', views.unit_create, name='unit_create'),
    path('domain/<int:domain_pk>/units/<int:pk>/edit/', views.unit_edit, name='unit_edit'),
    path('domain/<int:domain_pk>/units/<int:pk>/delete/', views.unit_delete, name='unit_delete'),
    
    # AJAX endpoints
    path('ajax/calculate-unit-cost/', views.calculate_unit_cost, name='calculate_unit_cost'),
]
