from django.contrib import admin
from django.urls import path, include
from personagens.views import cadastrar_usuario, home
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('combate/', include('combate.urls')),
    path('personagens/', include('personagens.urls')),
    path('salas/', include('salas.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/cadastro/', cadastrar_usuario, name='cadastrar_usuario'),
    path('itens/', include('itens.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)