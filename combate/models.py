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
    dano = models.IntegerField(default=0)
    aflicao = models.IntegerField(default=0)
    bonus_temporario = models.IntegerField(default=0)      # Para Buff
    penalidade_temporaria = models.IntegerField(default=0) # Para Debuff

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

class Mapa(models.Model):
    nome = models.CharField(max_length=100)
    imagem = models.ImageField(upload_to='mapas/')
    combate = models.ForeignKey('Combate', on_delete=models.CASCADE, related_name='mapas', blank=True, null=True)  # <-- Torne opcional
    criado_por = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)
    
class PosicaoPersonagem(models.Model):
    mapa = models.ForeignKey(Mapa, on_delete=models.CASCADE)
    participante = models.ForeignKey('Participante', on_delete=models.CASCADE)
    x = models.IntegerField(default=0)
    y = models.IntegerField(default=0)