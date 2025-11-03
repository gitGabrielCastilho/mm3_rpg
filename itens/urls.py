from django.urls import path
from .views import itens, ficha_item

urlpatterns = [
    path('itens/', itens, name='itens'),
    path('<int:item_id>/', ficha_item, name='ficha_item'),
]
