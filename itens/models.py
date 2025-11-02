from django.db import models

# Valores base sugeridos por raridade (pode ser ajustado conforme balanceamento)
PRECO_POR_RARIDADE = {
    'common': 50,
    'uncommon': 500,
    'rare': 7500,
    'very rare': 48000,
    'legendary': 165000,
    'artifact': 3300000,
    'unknown': 0,
    'unknown (magic)': 0,
    'none': 0,
    'varies': 0,
}

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
# Create your models here.
class Item(models.Model):
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, blank=True)
    raridade = models.CharField(max_length=20, choices=RARIDADE_CHOICES, blank=True)
    descricao = models.TextField()
    preco = models.PositiveIntegerField(default=0)
    # Modificadores opcionais aplicados quando o item é equipado
    # Ex.: {"caracteristicas": {"forca": 2}, "defesas": {"resistencia": 1}, "pericias": {"atletismo": 3}}
    mods = models.JSONField(default=dict, blank=True)
    sala = models.ForeignKey('salas.Sala', null=True, blank=True, on_delete=models.CASCADE, related_name='itens')
    # Nomes de itens devem ser únicos globalmente
    class Meta:
        constraints = []
    def __str__(self):
        return f"{self.nome} [{self.tipo} | {self.raridade}]"

    def save(self, *args, **kwargs):
        # Se o preço não foi definido manualmente, calcula automaticamente pela raridade
        try:
            rar = (self.raridade or '').lower()
            if not self.preco or int(self.preco) == 0:
                self.preco = PRECO_POR_RARIDADE.get(rar, 0)
        except Exception:
            # fallback silencioso
            pass
        super().save(*args, **kwargs)


# Poderes que pertencem a um Item (template), usados para gerar poderes de item no personagem quando equipado
class ItemPoder(models.Model):
    TIPO_CHOICES = [
        ('descritivo', 'Descritivo'),
        ('aflicao', 'Aflição'),
        ('dano', 'Dano'),
        ('cura', 'Cura'),
        ('buff', 'Buff/Debuff'),
        ('aprimorar', 'Aprimorar/Reduzir'),
    ]
    DURACAO_CHOICES = [
        ('instantaneo', 'Instantâneo'),
        ('concentracao', 'Concentração'),
        ('sustentado', 'Sustentado'),
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
    CASTING_ABILITY_CHOICES = [
        ('forca', 'Força'),
        ('vigor', 'Vigor'),
        ('destreza', 'Destreza'),
        ('agilidade', 'Agilidade'),
        ('luta', 'Luta'),
        ('inteligencia', 'Inteligência'),
        ('prontidao', 'Prontidão'),
        ('presenca', 'Presença'),
        ('aparar', 'Aparar'),
        ('esquivar', 'Esquiva'),
        ('fortitude', 'Fortitude'),
        ('vontade', 'Vontade'),
        ('resistencia', 'Resistência'),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='poderes')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='dano')
    modo = models.CharField(max_length=20, choices=MODO_CHOICES, default='melee')
    duracao = models.CharField(max_length=20, choices=DURACAO_CHOICES, default='instantaneo')
    nivel_efeito = models.IntegerField(default=0)
    bonus_ataque = models.IntegerField(default=0)
    somar_forca_no_nivel = models.BooleanField(default=False)
    defesa_ativa = models.CharField(max_length=20, choices=DEFESA_ATIVA_CHOICES, default='aparar')
    defesa_passiva = models.CharField(max_length=20, choices=DEFESA_PASSIVA_CHOICES, default='resistencia')
    casting_ability = models.CharField(max_length=20, choices=CASTING_ABILITY_CHOICES, default='inteligencia')
    charges = models.PositiveIntegerField(null=True, blank=True, default=None)
    array = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return f"{self.nome} [{self.item_id}]"