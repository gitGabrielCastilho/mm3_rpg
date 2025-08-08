from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from salas.models import Sala

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

RARIDADE_CHOICES = [
    ('artifact', 'Artifact'),
    ('common', 'Common'),
    ('legendary', 'Legendary'),
    ('none', 'Unknown'),
    ('rare', 'Rare'),
    ('uncommon', 'Uncommon'),
    ('unknown', 'Unknown'),
    ('unknown (magic)', 'Unknown (Magic)'),
    ('varies', 'Varies'),
    ('very rare', 'Very Rare'),
]

TIPO_CHOICES = [
    ('Adventuring Gear', 'Adventuring Gear'),
    ('Air Vehicle', 'Air Vehicle'),
    ('Ammunition', 'Ammunition'),
    ("Artisan's Tools", "Artisan's Tools"),
    ('Explosive', 'Explosive'),
    ('Food/Drink', 'Food/Drink'),
    ('Gaming Set', 'Gaming Set'),
    ('Generic Variant', 'Generic Variant'),
    ('Heavy Armor', 'Heavy Armor'),
    ('Idol/Relic', 'Idol/Relic'),
    ('Instrument', 'Instrument'),
    ('Light Armor', 'Light Armor'),
    ('Medium Armor', 'Medium Armor'),
    ('Melee Weapon', 'Melee Weapon'),
    ('Mount', 'Mount'),
    ('Other', 'Other'),
    ('Poison', 'Poison'),
    ('Ranged Weapon', 'Ranged Weapon'),
    ('Ring', 'Ring'),
    ('Rod', 'Rod'),
    ('Scroll', 'Scroll'),
    ('Shield', 'Shield'),
    ('Ship', 'Ship'),
    ('Space Vehicle', 'Space Vehicle'),
    ('Spellcasting Focus', 'Spellcasting Focus'),
    ('Tack and Harness', 'Tack and Harness'),
    ("Tinker’s Tool (Bundle)", "Tinker’s Tool (Bundle)"),
    ('Tool', 'Tool'),
    ('Trade Good', 'Trade Good'),
    ('Vehicle', 'Vehicle'),
    ('Wondrous Item', 'Wondrous Item'),
    ('martial Weapon, Melee Weapon', 'Martial Weapon, Melee Weapon'),
    ('martial Weapon, Ranged Weapon', 'Martial Weapon, Ranged Weapon'),
    ('simple Weapon, Melee Weapon', 'Simple Weapon, Melee Weapon'),
    ('simple Weapon, Ranged Weapon', 'Simple Weapon, Ranged Weapon'),
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
    foto = models.ImageField(upload_to='personagens_fotos/', blank=True, null=True)

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
    de_item = models.BooleanField("Poder de Item?", default=False)
    item_origem = models.ForeignKey(
        'Item', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Se for poder de item, selecione o item de origem."
    )
    def __str__(self):
        return f"{self.nome} ({self.tipo}, {self.modo})"
 
    
class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=[('jogador', 'Jogador'), ('game_master', 'Game Master')])
    sala_atual = models.ForeignKey(Sala, on_delete=models.SET_NULL, null=True, blank=True)


class Item(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, blank=True)
    raridade = models.CharField(max_length=20, choices=RARIDADE_CHOICES, blank=True)
    descricao = models.TextField()
    preco = models.PositiveIntegerField(default=0)
    def __str__(self):
        return f"{self.nome} [{self.tipo} | {self.raridade}]"

class Inventario(models.Model):
    personagem = models.OneToOneField('Personagem', on_delete=models.CASCADE, related_name='inventario')
    itens = models.ManyToManyField(Item, blank=True)
    ouro = models.PositiveIntegerField(default=0)
    dragon_shard = models.PositiveIntegerField(default=0)