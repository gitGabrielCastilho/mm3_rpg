from django.urls import path
from . import views

urlpatterns = [
    path('', views.domain_list, name='domain_list'),
    path('domain/<int:pk>/', views.domain_detail, name='domain_detail'),
    path('domain/create/', views.domain_create, name='domain_create'),
    path('domain/<int:pk>/edit/', views.domain_edit, name='domain_edit'),
    path('domain/<int:pk>/delete/', views.domain_delete, name='domain_delete'),
]
