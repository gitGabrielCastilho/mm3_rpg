from django.contrib import admin
from django.urls import path, include
from personagens.views import cadastrar_usuario, home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('combate/', include('combate.urls')),
    path('personagens/', include('personagens.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/cadastro/', cadastrar_usuario, name='cadastrar_usuario'),
]
