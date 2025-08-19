from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.storage import default_storage
from combate.models import Mapa
from personagens.models import Personagem

class Command(BaseCommand):
    help = "Mostra informações do storage atual e exemplo de URLs de mídia."

    def handle(self, *args, **kwargs):
        dfs = getattr(settings, 'DEFAULT_FILE_STORAGE', '(padrão de arquivo local)')
        self.stdout.write(f"DEFAULT_FILE_STORAGE: {dfs}")
        self.stdout.write(f"default_storage class: {default_storage.__class__.__module__}.{default_storage.__class__.__name__}")
        self.stdout.write(f"MEDIA_URL: {getattr(settings, 'MEDIA_URL', '')}")
        self.stdout.write(f"MEDIA_ROOT: {getattr(settings, 'MEDIA_ROOT', '')}")
        # Mostra até 5 exemplos mais recentes de mapas e fotos
        for mapa in Mapa.objects.order_by('-id')[:5]:
            try:
                storage_cls = getattr(mapa.imagem.storage, '__class__', type(mapa.imagem.storage))
                self.stdout.write(
                    f"Mapa #{mapa.id} storage: {storage_cls.__module__}.{storage_cls.__name__} | name: {mapa.imagem.name} | url: {mapa.imagem.url}"
                )
            except Exception as e:
                self.stdout.write(f"Mapa #{mapa.id} url ERROR: {e}")
        for p in Personagem.objects.exclude(foto='').order_by('-id')[:5]:
            try:
                storage_cls = getattr(p.foto.storage, '__class__', type(p.foto.storage))
                self.stdout.write(
                    f"Personagem #{p.id} foto storage: {storage_cls.__module__}.{storage_cls.__name__} | name: {p.foto.name} | url: {p.foto.url}"
                )
            except Exception as e:
                self.stdout.write(f"Personagem #{p.id} foto url ERROR: {e}")
