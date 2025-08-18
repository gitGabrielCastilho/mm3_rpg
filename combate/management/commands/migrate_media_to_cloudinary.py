from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from combate.models import Mapa
from personagens.models import Personagem
from pathlib import Path
import os


class Command(BaseCommand):
    help = (
        "Reenvia arquivos de mídia locais (mapas e fotos de personagens) para o storage ativo "
        "(ex.: Cloudinary) re-salvando os ImageFields. Útil após ativar Cloudinary."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Apenas lista o que seria migrado")
        parser.add_argument("--only", choices=["mapas", "fotos", "all"], default="all", help="Filtrar tipo de mídia")
        parser.add_argument("--limit", type=int, default=0, help="Limitar quantidade de registros processados por tipo")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        only = opts["only"]
        limit = opts["limit"]

        using_cloudinary = getattr(settings, "DEFAULT_FILE_STORAGE", "").endswith("MediaCloudinaryStorage")
        if not using_cloudinary:
            self.stdout.write(self.style.WARNING(
                "DEFAULT_FILE_STORAGE não é Cloudinary. A migração só fará re-save no storage atual."
            ))

        total_mapas = 0
        total_fotos = 0

        if only in ("all", "mapas"):
            qs = Mapa.objects.exclude(imagem="")
            if limit:
                qs = qs[:limit]
            for mapa in qs:
                if not mapa.imagem:
                    continue
                path = getattr(mapa.imagem, "path", None)
                url = getattr(mapa.imagem, "url", "")
                self.stdout.write(f"Mapa #{mapa.id} '{mapa.nome}' -> {url or path}")
                total_mapas += 1
                if dry:
                    continue
                try:
                    if path and os.path.exists(path):
                        with open(path, "rb") as f:
                            content = ContentFile(f.read())
                            fname = Path(path).name
                            mapa.imagem.save(fname, content, save=True)
                    else:
                        mapa.imagem.save(mapa.imagem.name, mapa.imagem.file, save=True)
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Falha ao migrar mapa #{mapa.id}: {e}"))

        if only in ("all", "fotos"):
            qs = Personagem.objects.exclude(foto="")
            if limit:
                qs = qs[:limit]
            for p in qs:
                if not p.foto:
                    continue
                path = getattr(p.foto, "path", None)
                url = getattr(p.foto, "url", "")
                self.stdout.write(f"Personagem #{p.id} '{p.nome}' -> {url or path}")
                total_fotos += 1
                if dry:
                    continue
                try:
                    if path and os.path.exists(path):
                        with open(path, "rb") as f:
                            content = ContentFile(f.read())
                            fname = Path(path).name
                            p.foto.save(fname, content, save=True)
                    else:
                        p.foto.save(p.foto.name, p.foto.file, save=True)
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Falha ao migrar foto do personagem #{p.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"Concluído. Mapas processados: {total_mapas}; Fotos processadas: {total_fotos}."
        ))
