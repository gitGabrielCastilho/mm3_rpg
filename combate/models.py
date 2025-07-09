from django.db import models
from personagens.models import Personagem

class Ataque(models.Model):
    atacante = models.ForeignKey(Personagem, related_name="ataques_feitos", on_delete=models.CASCADE)
    alvo = models.ForeignKey(Personagem, related_name="ataques_recebidos", on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=[("dano", "Dano"), ("aflicao", "Aflição")])
    alcance = models.CharField(max_length=20, choices=[("comum", "Comum"), ("area", "Área"), ("percepcao", "Percepção")])
    nivel = models.IntegerField()
    defesa_usada = models.CharField(max_length=20)
    acertou = models.BooleanField()
    data = models.DateTimeField(auto_now_add=True)
