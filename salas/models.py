from django.db import models
from django.contrib.auth.models import User
import random
import string


class Sala(models.Model):
    nome = models.CharField(max_length=100)
    criador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='salas_criadas')
    participantes = models.ManyToManyField(User, related_name='salas_participando', blank=True)
    codigo = models.CharField(max_length=6, unique=True)
    game_master = models.ForeignKey(User, on_delete=models.CASCADE, related_name='salas_gm')
    jogadores = models.ManyToManyField(User, related_name='salas_jogador', blank=True)
    senha = models.CharField("Senha (opcional)", max_length=128, blank=True, default='')
    criada_em = models.DateTimeField(auto_now_add=True)
    ativa = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.gerar_codigo_unico()
        super().save(*args, **kwargs)

    def gerar_codigo_unico(self):
        while True:
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not Sala.objects.filter(codigo=codigo).exists():
                return codigo

    def __str__(self):
        return f"{self.nome} ({self.codigo})"


class NotaSessao(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='notas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notas_sessao')
    nome_usuario = models.CharField(max_length=150)
    conteudo = models.TextField()
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criada_em']

    def __str__(self):
        return f"{self.sala} - {self.nome_usuario}: {self.conteudo[:30]}"
