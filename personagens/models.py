from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

CASTING_ABILITY_CHOICES = [
    ('forca', 'Força'),
    ('vigor', 'Vigor'),
    ('destreza', 'Destreza'),
    ('agilidade', 'Agilidade'),
    ('luta', 'Luta'),
    ('inteligencia', 'Inteligência'),
    ('prontidao', 'Prontidão'),
    ('presenca', 'Presença'),
]
class Personagem(models.Model):

    especialidade_casting_ability = models.CharField(
        max_length=20,
        choices=CASTING_ABILITY_CHOICES,
        verbose_name="Habilidade de Conjuração da Especialidade",
        default='inteligencia'
    )

    nome = models.CharField(max_length=100)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nivel_poder = models.IntegerField(default=10)

    # Características
    forca = models.IntegerField(default=0)
    vigor = models.IntegerField(default=0)
    destreza = models.IntegerField(default=0)
    agilidade = models.IntegerField(default=0)
    luta = models.IntegerField(default=0)
    inteligencia = models.IntegerField(default=0)
    prontidao = models.IntegerField(default=0)
    presenca = models.IntegerField(default=0)

    # Defesas
    aparar = models.IntegerField(default=0)
    esquivar = models.IntegerField(default=0)
    fortitude = models.IntegerField(default=0)
    vontade = models.IntegerField(default=0)
    resistencia = models.IntegerField(default=0)
    penalidade_resistencia = models.IntegerField(default=0, blank=True)
    condicao = models.CharField(max_length=30, blank=True, default="")  

    # Perícias
    acrobacias = models.IntegerField(default=0)
    atletismo = models.IntegerField(default=0)
    combate_distancia = models.IntegerField(default=0)
    combate_corpo = models.IntegerField(default=0)
    enganacao = models.IntegerField(default=0)
    especialidade = models.IntegerField(default=0)
    furtividade = models.IntegerField(default=0)
    intimidacao = models.IntegerField(default=0)
    intuicao = models.IntegerField(default=0)
    investigacao = models.IntegerField(default=0)
    percepcao = models.IntegerField(default=0)
    persuasao = models.IntegerField(default=0)
    prestidigitacao = models.IntegerField(default=0)
    tecnologia = models.IntegerField(default=0)
    tratamento = models.IntegerField(default=0)
    veiculos = models.IntegerField(default=0)
    historia = models.IntegerField(default=0)
    sobrevivencia = models.IntegerField(default=0)


    def clean(self):
        np = self.nivel_poder
        atributos = [
            self.forca, self.vigor, self.destreza, self.agilidade,
            self.luta, self.inteligencia, self.prontidao, self.presenca
        ]
        if any(valor > np + 5 for valor in atributos):
            raise ValidationError("Nenhuma característica pode exceder o nível de poder + 5.")

        # Validar defesas combinadas
        if self.aparar + self.resistencia> np * 2:
            raise ValidationError("Aparar + Esquiva não pode exceder o dobro do Nível de Poder.")

        if self.esquivar + self.resistencia > np * 2:
            raise ValidationError("Esquivar + Resistencia não pode exceder o dobro do Nível de Poder.")

        if self.fortitude + self.resistencia > np * 2:
            raise ValidationError("Fortitude + Resistencia não pode exceder o dobro do Nível de Poder.")

        if self.vontade + self.resistencia > np * 2:
            raise ValidationError("Vontade + Resistencia não pode exceder o dobro do Nível de Poder.")

        if self.vontade + self.fortitude > np * 2:
            raise ValidationError("Vontade + Fortitude não pode exceder o dobro do Nível de Poder.")
        
        if self.aparar + self.fortitude > np * 2:
            raise ValidationError("Aparar + Fortitude não pode exceder o dobro do Nível de Poder.")
        
        if self.esquivar + self.fortitude > np * 2:
            raise ValidationError("Esquivar + Fortitude não pode exceder o dobro do Nível de Poder.")

        if self.esquivar + self.vontade > np * 2:
            raise ValidationError("Esquivar + Vontade não pode exceder o dobro do Nível de Poder.")
        
        if self.aparar + self.vontade > np * 2:
            raise ValidationError("Aparar + Vontade não pode exceder o dobro do Nível de Poder.")

        if self.aparar + self.esquivar > np * 2:
            raise ValidationError("Aparar + Esquivar não pode exceder o dobro do Nível de Poder.")

        # Validar perícias
        pericias = [
            ('Acrobacias', self.acrobacias),
            ('Atletismo', self.atletismo),
            ('Combate À Distância', self.combate_distancia),
            ('Combate Corpo-a-corpo', self.combate_corpo),
            ('Enganação', self.enganacao),
            ('Especialidade', self.especialidade),
            ('Furtividade', self.furtividade),
            ('Intimidação', self.intimidacao),
            ('Intuição', self.intuicao),
            ('Investigação', self.investigacao),
            ('Percepção', self.percepcao),
            ('Persuasão', self.persuasao),
            ('Prestidigitação', self.prestidigitacao),
            ('Tecnologia', self.tecnologia),
            ('Tratamento', self.tratamento),
            ('Veículos', self.veiculos),
            ('História', self.historia),
            ('Sobrevivência', self.sobrevivencia),
        ]

        for nome, valor in pericias:
            if valor > np + 5:
                raise ValidationError(f"A perícia {nome} não pode exceder o nível de poder + 5.")

    def __str__(self):
        return self.nome
    
class Poder(models.Model):
    TIPO_CHOICES = [
        ('aflicao', 'Aflição'),
        ('dano', 'Dano'),
        ('cura', 'Cura'),
        ('buff', 'Buff'),
        ('debuff', 'Debuff'),
    ]
    MODO_CHOICES = [
        ('area', 'Área'),
        ('percepcao', 'Percepção'),
        ('ranged', 'À Distância'),
        ('melee', 'Corpo a Corpo'),
    ]

    DEFESA_ATIVA_CHOICES = [
        ('esquiva', 'Esquiva'),
        ('aparar', 'Aparar'),
    ]
    DEFESA_PASSIVA_CHOICES = [
        ('fortitude', 'Fortitude'),
        ('resistencia', 'Resistência'),
        ('vontade', 'Vontade'),
    
    ]
    casting_ability = models.CharField(
        max_length=20,
        choices=CASTING_ABILITY_CHOICES,
        verbose_name="Habilidade de Conjuração",
        default='inteligencia'
    )
    personagem = models.ForeignKey(Personagem, on_delete=models.CASCADE, related_name='poderes')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='dano')
    modo = models.CharField(max_length=20, choices=MODO_CHOICES, default='melee')
    nivel_efeito = models.IntegerField(default=0)
    bonus_ataque = models.IntegerField(default=0)
    defesa_ativa = models.CharField(max_length=20, choices=DEFESA_ATIVA_CHOICES, default='aparar')
    defesa_passiva = models.CharField(max_length=20, choices=DEFESA_PASSIVA_CHOICES, default='resistencia')

    def __str__(self):
        return f"{self.nome} ({self.tipo}, {self.modo})"