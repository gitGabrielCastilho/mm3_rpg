from django.db import models
from personagens.models import Personagem
from personagens.models import Poder

class Combate(models.Model):
    sala = models.ForeignKey('salas.Sala', on_delete=models.CASCADE, related_name='combates', null=True, blank=True)
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
    # Próximo bônus específico por atributo (para Aprimorar instantâneo): {"forca": 2, "vigor": 1, ...}
    proximo_bonus_por_atributo = models.JSONField(default=dict, blank=True)
    # Ferimentos: penalidade cumulativa única em salvamentos contra Dano e Aflição
    ferimentos = models.IntegerField(default=0)
    # CD fixo usado para reduzir Aflição (mesmo CD que a causou)
    cd_aflicao_origem = models.IntegerField(default=0)

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
    token_size = models.PositiveIntegerField(default=40)

class EfeitoConcentracao(models.Model):
    """Efeito de concentração ativo sobre um alvo específico.
    - criado_em: quando foi aplicado
    - ativo: se ainda está valendo
    - aplicador: personagem que usou o poder
    - alvo_participante: participante alvo do efeito
    - poder: referência ao poder usado
    - combate: combate onde está ativo (facilita consultas)
    - rodada_inicio: ordem do turno em que foi criado
    """
    combate = models.ForeignKey(Combate, on_delete=models.CASCADE, related_name='efeitos_concentracao')
    aplicador = models.ForeignKey(Personagem, on_delete=models.CASCADE, related_name='concentracoes_aplicadas')
    alvo_participante = models.ForeignKey('Participante', on_delete=models.CASCADE, related_name='concentracoes_recebidas')
    poder = models.ForeignKey(Poder, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)
    rodada_inicio = models.IntegerField(default=0)

    def __str__(self):
        return f"Concentração: {self.poder.nome} por {self.aplicador.nome} em {self.alvo_participante.personagem.nome} ({'Ativo' if self.ativo else 'Encerrado'})"