from django.urls import path
from .views import itens

urlpatterns = [
    path('itens/', itens, name='itens'),
]
