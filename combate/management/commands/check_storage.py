from django.core.management.base import BaseCommand
from django.conf import settings
from combate.models import Mapa
from personagens.models import Personagem

class Command(BaseCommand):
    help = "Mostra informações do storage atual e exemplo de URLs de mídia."

    def handle(self, *args, **kwargs):
        dfs = getattr(settings, 'DEFAULT_FILE_STORAGE', '(padrão de arquivo local)')
        self.stdout.write(f"DEFAULT_FILE_STORAGE: {dfs}")
        self.stdout.write(f"MEDIA_URL: {getattr(settings, 'MEDIA_URL', '')}")
        self.stdout.write(f"MEDIA_ROOT: {getattr(settings, 'MEDIA_ROOT', '')}")
        # Mostra 3 exemplos de mapas e fotos
        for mapa in Mapa.objects.all()[:3]:
            try:
                self.stdout.write(f"Mapa #{mapa.id} url: {mapa.imagem.url}")
            except Exception as e:
                self.stdout.write(f"Mapa #{mapa.id} url ERROR: {e}")
        for p in Personagem.objects.exclude(foto='')[:3]:
            try:
                self.stdout.write(f"Personagem #{p.id} foto url: {p.foto.url}")
            except Exception as e:
                self.stdout.write(f"Personagem #{p.id} foto url ERROR: {e}")
