from django.db import models
from personagens.models import Personagem

class Combate(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"Combate #{self.id} - {'Ativo' if self.ativo else 'Finalizado'}"

class Participante(models.Model):
    personagem = models.ForeignKey(Personagem, on_delete=models.CASCADE)
    combate = models.ForeignKey(Combate, on_delete=models.CASCADE)
    iniciativa = models.IntegerField()

    def __str__(self):
        return f"{self.personagem.nome} (Iniciativa {self.iniciativa})"


class Turno(models.Model):
    combate = models.ForeignKey(Combate, on_delete=models.CASCADE)
    personagem = models.ForeignKey(Personagem, on_delete=models.CASCADE)
    ordem = models.PositiveIntegerField()
    ativo = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    descricao = models.TextField(blank=True, null=True)  # <-- Adicione esta linha!

    def __str__(self):
        return f"Turno {self.ordem} - {self.personagem.nome}"
