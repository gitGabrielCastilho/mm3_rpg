from django.urls import path
from . import views

urlpatterns = [
    path('usar_poder/', views.usar_poder, name='usar_poder'),
]
