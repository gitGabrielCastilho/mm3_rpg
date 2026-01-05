from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.


class Domain(models.Model):
    """
    Representa um domínio/reino gerenciado por jogadores.
    """
    nome = models.CharField(max_length=200, unique=True, verbose_name="Nome do Domínio")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    brasao = models.ImageField(
        upload_to='domains/brasoes/',
        blank=True,
        null=True,
        verbose_name="Brasão"
    )
    
    # Proprietários e controle
    criador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dominios_criados',
        verbose_name="Criador",
        help_text="Usuário que criou este domínio",
        null=True,
        blank=True
    )
    governante = models.ForeignKey(
        'personagens.Personagem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dominios_governados',
        verbose_name="Governante"
    )
    sala = models.ForeignKey(
        'salas.Sala',
        on_delete=models.CASCADE,
        related_name='dominios',
        verbose_name="Sala"
    )
    jogadores_acesso = models.ManyToManyField(
        User,
        related_name='dominios_acesso',
        blank=True,
        verbose_name="Jogadores com Acesso"
    )
    criado_por_gm = models.BooleanField(
        default=False,
        verbose_name="Criado pelo GM",
        help_text="Se True, apenas o GM pode editar"
    )
    
    # Nível do domínio (1-5)
    nivel = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Nível",
        help_text="Nível do domínio (1 a 5)"
    )
    
    # Características (-3 a 3)
    diplomacy = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-3), MaxValueValidator(3)],
        verbose_name="Diplomacy"
    )
    espionage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-3), MaxValueValidator(3)],
        verbose_name="Espionage"
    )
    lore = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-3), MaxValueValidator(3)],
        verbose_name="Lore"
    )
    operations = models.IntegerField(
        default=0,
        validators=[MinValueValidator(-3), MaxValueValidator(3)],
        verbose_name="Operations"
    )
    
    # Recursos
    ouro = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Ouro"
    )
    dragonshards = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Dragonshards"
    )
    
    # Strongholds (níveis de 1 a 5)
    keep = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Keep",
        help_text="Nível do Keep (0 a 5, 0 = não possui)"
    )
    tower = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Tower",
        help_text="Nível da Tower (0 a 5, 0 = não possui)"
    )
    temple = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Temple",
        help_text="Nível do Temple (0 a 5, 0 = não possui)"
    )
    establishment = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Establishment",
        help_text="Nível do Establishment (0 a 5, 0 = não possui)"
    )
    
    # Metadados
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Domínio"
        verbose_name_plural = "Domínios"
        ordering = ['nome']
    
    def __str__(self):
        return self.nome
    
    def eh_gm(self, user):
        """Verifica se o usuário é GM da sala."""
        return user.is_staff or user.is_superuser or self.sala.game_master == user
    
    def pode_editar(self, user):
        """Verifica se um usuário pode editar este domínio."""
        if not user.is_authenticated:
            return False
        
        # GM pode editar qualquer domain
        if self.eh_gm(user):
            return True
        
        # Se foi criado pelo GM, apenas GM pode editar
        if self.criado_por_gm:
            return False
        
        # Criador pode editar seu próprio domain
        if self.criador == user:
            return True
        
        # Outros jogadores só podem editar se estão em jogadores_acesso
        return self.jogadores_acesso.filter(id=user.id).exists()
    
    def pode_deletar(self, user):
        """Verifica se um usuário pode deletar este domínio."""
        if not user.is_authenticated:
            return False
        
        # GM pode deletar qualquer domain
        if self.eh_gm(user):
            return True
        
        # Criador pode deletar seu próprio domain
        if self.criador == user:
            return True
        
        return False


class UnitAncestry(models.Model):
    """
    Define as ancestries disponíveis para unidades e seus modificadores de atributos.
    """
    ANCESTRIES = [
        ('bugbear', 'Bugbear'),
        ('dragonborn', 'Dragonborn'),
        ('dwarf', 'Dwarf'),
        ('elf', 'Elf'),
        ('elf_winged', 'Elf (Winged)'),
        ('ghoul', 'Ghoul'),
        ('gnoll', 'Gnoll'),
        ('gnome', 'Gnome'),
        ('goblin', 'Goblin'),
        ('hobgoblin', 'Hobgoblin'),
        ('human', 'Human'),
        ('kobold', 'Kobold'),
        ('lizardfolk', 'Lizardfolk'),
        ('ogre', 'Ogre'),
        ('orc', 'Orc'),
        ('skeleton', 'Skeleton'),
        ('treant', 'Treant'),
        ('troll', 'Troll'),
        ('zombie', 'Zombie'),
    ]
    
    nome = models.CharField(
        max_length=50,
        choices=ANCESTRIES,
        unique=True,
        verbose_name="Ancestria"
    )
    
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )
    
    # Modificadores de Atributos (podem ser negativos)
    modificador_ataque = models.IntegerField(
        default=0,
        verbose_name="Modificador de Ataque"
    )
    modificador_poder = models.IntegerField(
        default=0,
        verbose_name="Modificador de Poder"
    )
    modificador_defesa = models.IntegerField(
        default=0,
        verbose_name="Modificador de Defesa"
    )
    modificador_resistencia = models.IntegerField(
        default=0,
        verbose_name="Modificador de Resistência"
    )
    modificador_moral = models.IntegerField(
        default=0,
        verbose_name="Modificador de Moral"
    )
    
    # Traits associados (será detalhado depois)
    traits = models.TextField(
        blank=True,
        verbose_name="Traits Associados",
        help_text="Traits que esta ancestry automaticamente fornece (separados por vírgula)"
    )
    
    class Meta:
        verbose_name = "Ancestria de Unidade"
        verbose_name_plural = "Ancestrias de Unidades"
        ordering = ['nome']
    
    def __str__(self):
        return self.get_nome_display()
    
    def get_modificadores(self):
        """Retorna um dicionário com todos os modificadores."""
        return {
            'ataque': self.modificador_ataque,
            'poder': self.modificador_poder,
            'defesa': self.modificador_defesa,
            'resistencia': self.modificador_resistencia,
            'moral': self.modificador_moral,
        }


class UnitTrait(models.Model):
    """
    Define os traits disponíveis que podem ser adquiridos pelas unidades.
    Alguns traits são inatos (vêm da ancestry), outros precisam ser adquiridos com custo.
    """
    TRAITS = [
        ('amphibious', 'Amphibious'),
        ('bred_for_war', 'Bred for War'),
        ('brutal', 'Brutal'),
        ('courageous', 'Courageous'),
        ('eternal', 'Eternal'),
        ('feast', 'Feast'),
        ('horrify', 'Horrify'),
        ('martial', 'Martial'),
        ('mindless', 'Mindless'),
        ('regenerate', 'Regenerate'),
        ('ravenous', 'Ravenous'),
        ('rock_hurler', 'Rock-Hurler'),
        ('savage', 'Savage'),
        ('stalwart', 'Stalwart'),
        ('twisting_roots', 'Twisting Roots'),
        ('undead', 'Undead'),
    ]
    
    nome = models.CharField(
        max_length=50,
        choices=TRAITS,
        unique=True,
        verbose_name="Trait"
    )
    
    descricao = models.TextField(
        verbose_name="Descrição",
        help_text="Explicação do que o trait faz"
    )
    
    custo = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Custo",
        help_text="Custo em pontos para adquirir este trait"
    )
    
    class Meta:
        verbose_name = "Trait de Unidade"
        verbose_name_plural = "Traits de Unidades"
        ordering = ['nome']
    
    def __str__(self):
        return self.get_nome_display()


class UnitExperience(models.Model):
    """
    Define os níveis de experiência disponíveis para unidades.
    Cada nível fornece modificadores específicos aos atributos.
    """
    LEVELS = [
        ('green', 'Green'),
        ('regular', 'Regular'),
        ('seasoned', 'Seasoned'),
        ('veteran', 'Veteran'),
        ('elite', 'Elite'),
        ('super_elite', 'Super-Elite'),
    ]
    
    nome = models.CharField(
        max_length=50,
        choices=LEVELS,
        unique=True,
        verbose_name="Nível de Experiência"
    )
    
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )
    
    # Modificadores de Atributos (podem ser 0)
    modificador_ataque = models.IntegerField(
        default=0,
        verbose_name="Modificador de Ataque"
    )
    modificador_poder = models.IntegerField(
        default=0,
        verbose_name="Modificador de Poder"
    )
    modificador_defesa = models.IntegerField(
        default=0,
        verbose_name="Modificador de Defesa"
    )
    modificador_resistencia = models.IntegerField(
        default=0,
        verbose_name="Modificador de Resistência"
    )
    modificador_moral = models.IntegerField(
        default=0,
        verbose_name="Modificador de Moral"
    )
    
    class Meta:
        verbose_name = "Nível de Experiência de Unidade"
        verbose_name_plural = "Níveis de Experiência de Unidades"
        ordering = ['nome']
    
    def __str__(self):
        return self.get_nome_display()
    
    def get_modificadores(self):
        """Retorna um dicionário com todos os modificadores."""
        return {
            'ataque': self.modificador_ataque,
            'poder': self.modificador_poder,
            'defesa': self.modificador_defesa,
            'resistencia': self.modificador_resistencia,
            'moral': self.modificador_moral,
        }
    
    def __str__(self):
        return self.get_nome_display()


class UnitEquipment(models.Model):
    """
    Define os tipos de equipamento disponíveis para unidades.
    Cada tipo fornece modificadores específicos aos atributos.
    """
    EQUIPMENT_TYPES = [
        ('light', 'Light'),
        ('medium', 'Medium'),
        ('heavy', 'Heavy'),
        ('super_heavy', 'Super-Heavy'),
    ]
    
    nome = models.CharField(
        max_length=50,
        choices=EQUIPMENT_TYPES,
        unique=True,
        verbose_name="Tipo de Equipamento"
    )
    
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )
    
    # Modificadores de Atributos (Attack e Morale sempre 0, Toughness não aplicável)
    modificador_poder = models.IntegerField(
        default=0,
        verbose_name="Modificador de Poder"
    )
    modificador_defesa = models.IntegerField(
        default=0,
        verbose_name="Modificador de Defesa"
    )
    
    class Meta:
        verbose_name = "Tipo de Equipamento de Unidade"
        verbose_name_plural = "Tipos de Equipamento de Unidades"
        ordering = ['nome']
    
    def __str__(self):
        return self.get_nome_display()
    
    def get_modificadores(self):
        """Retorna um dicionário com todos os modificadores."""
        return {
            'ataque': 0,  # Attack nunca muda com equipamento
            'poder': self.modificador_poder,
            'defesa': self.modificador_defesa,
            'resistencia': 0,  # Toughness não se aplica ao resistencia
            'moral': 0,  # Morale nunca muda com equipamento
        }


class UnitType(models.Model):
    """
    Define os tipos de unidades disponíveis (Infantry, Cavalry, etc).
    Cada tipo fornece modificadores específicos aos atributos e um multiplicador de custo.
    """
    UNIT_TYPES = [
        ('airborne', 'Airborne'),
        ('archers', 'Archers'),
        ('cavalry', 'Cavalry'),
        ('levies', 'Levies'),
        ('infantry', 'Infantry'),
        ('siege_engine', 'Siege Engine'),
    ]
    
    nome = models.CharField(
        max_length=50,
        choices=UNIT_TYPES,
        unique=True,
        verbose_name="Tipo de Unidade"
    )
    
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )
    
    # Modificadores de Atributos
    modificador_ataque = models.IntegerField(
        default=0,
        verbose_name="Modificador de Ataque"
    )
    modificador_poder = models.IntegerField(
        default=0,
        verbose_name="Modificador de Poder"
    )
    modificador_defesa = models.IntegerField(
        default=0,
        verbose_name="Modificador de Defesa"
    )
    modificador_resistencia = models.IntegerField(
        default=0,
        verbose_name="Modificador de Resistência (Toughness)"
    )
    modificador_moral = models.IntegerField(
        default=0,
        verbose_name="Modificador de Moral"
    )
    
    # Multiplicador de Custo
    multiplicador_custo = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        verbose_name="Multiplicador de Custo",
        help_text="Multiplica o custo final da unidade (ex: 1.5x, 0.75x)"
    )
    
    class Meta:
        verbose_name = "Tipo de Unidade"
        verbose_name_plural = "Tipos de Unidades"
        ordering = ['nome']
    
    def __str__(self):
        return self.get_nome_display()
    
    def get_modificadores(self):
        """Retorna um dicionário com todos os modificadores."""
        return {
            'ataque': self.modificador_ataque,
            'poder': self.modificador_poder,
            'defesa': self.modificador_defesa,
            'resistencia': self.modificador_resistencia,
            'moral': self.modificador_moral,
        }


class UnitSize(models.Model):
    """
    Define os tamanhos de unidades disponíveis com seus modificadores de custo.
    Os tamanhos variam de 1d4 até 1d12 com modificadores específicos.
    """
    SIZES = [
        ('1d4', '1d4'),
        ('1d6', '1d6'),
        ('1d8', '1d8'),
        ('1d10', '1d10'),
        ('1d12', '1d12'),
    ]
    
    tamanho = models.CharField(
        max_length=10,
        choices=SIZES,
        unique=True,
        verbose_name="Tamanho",
        help_text="Tamanho da unidade em dados (1d4, 1d6, etc)"
    )
    
    # Multiplicador de Custo
    multiplicador_custo = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        verbose_name="Multiplicador de Custo",
        help_text="Multiplica o custo final da unidade (ex: 1.33x, 0.66x)"
    )
    
    class Meta:
        verbose_name = "Tamanho de Unidade"
        verbose_name_plural = "Tamanhos de Unidades"
        ordering = ['tamanho']
    
    def __str__(self):
        return self.tamanho


class Unit(models.Model):
    """
    Representa uma unidade (tropa/soldado) que compõe um exército de um Domain.
    """
    # Relação com Domain
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='units',
        verbose_name="Domínio"
    )
    
    # Propriedade
    criador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='units_criados',
        verbose_name="Criador",
        help_text="Usuário que criou esta unidade"
    )
    
    # Identificação
    nome = models.CharField(
        max_length=200,
        verbose_name="Nome da Unidade",
        help_text="Ex: Infantaria Pesada, Arqueiros da Floresta, etc"
    )
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )
    
    # Imagem da unidade
    imagem = models.ImageField(
        upload_to='units/',
        blank=True,
        null=True,
        verbose_name="Imagem",
        help_text="Imagem representativa da unidade"
    )
    
    # Características da Unidade
    ancestry = models.ForeignKey(
        UnitAncestry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='units',
        verbose_name="Ancestria"
    )
    
    # Traits adquiridos (além dos inatos da ancestry)
    traits = models.ManyToManyField(
        UnitTrait,
        blank=True,
        related_name='units',
        verbose_name="Traits Adquiridos",
        help_text="Traits que esta unidade adquiriu (além dos inatos da ancestry)"
    )
    
    # Experiência da unidade
    experience = models.ForeignKey(
        UnitExperience,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='units',
        verbose_name="Nível de Experiência",
        help_text="Nível de experiência da unidade"
    )
    
    # Equipamento da unidade
    equipment = models.ForeignKey(
        UnitEquipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='units',
        verbose_name="Equipamento",
        help_text="Tipo de equipamento da unidade"
    )
    
    # Tipo de unidade
    unit_type = models.ForeignKey(
        'UnitType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='units',
        verbose_name="Tipo de Unidade",
        help_text="Tipo estratégico da unidade (Infantry, Cavalry, etc)"
    )
    
    # Tamanho da unidade
    size = models.ForeignKey(
        UnitSize,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='units',
        verbose_name="Tamanho da Unidade",
        help_text="Tamanho da unidade (1d4, 1d6, etc)"
    )
    
    # Atributos da Unidade (valores base, antes de modificadores)
    ataque = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Ataque",
        help_text="Capacidade de ataque da unidade"
    )
    poder = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Poder",
        help_text="Poder/Força da unidade"
    )
    defesa = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Defesa",
        help_text="Capacidade defensiva da unidade"
    )
    resistencia = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Resistência",
        help_text="Resistência da unidade"
    )
    moral = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name="Moral",
        help_text="Moral da unidade (0-10)"
    )

    is_mythic = models.BooleanField(
        default=False,
        verbose_name="Unidade Mítica",
        help_text="Se marcado, os atributos base podem ser definidos manualmente"
    )
    
    # Custos associados
    custo_ouro = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Custo em Ouro"
    )
    custo_dragonshards = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Custo em Dragonshards"
    )
    
    # Quantidade
    quantidade = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Quantidade de Soldados",
        help_text="Número de soldados nesta unidade"
    )
    
    # Metadados
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Unidade"
        verbose_name_plural = "Unidades"
        ordering = ['domain', 'nome']
        unique_together = [['domain', 'nome']]
    
    def __str__(self):
        return f"{self.nome} ({self.domain.nome})"
    
    def pode_editar(self, user):
        """Verifica se um usuário pode editar esta unidade."""
        if not user.is_authenticated:
            return False
        
        # GM da sala pode editar qualquer unidade
        if self.domain.eh_gm(user):
            return True
        
        # Jogadores do domain podem editar unidades
        # (criador + jogadores com acesso ao domain)
        return self.pode_acessar_domain(user)
    
    def pode_deletar(self, user):
        """Verifica se um usuário pode deletar esta unidade."""
        if not user.is_authenticated:
            return False
        
        # GM da sala pode deletar qualquer unidade
        if self.domain.eh_gm(user):
            return True
        
        # Apenas o criador pode deletar
        if self.criador == user:
            return True
        
        return False
    
    def pode_acessar_domain(self, user):
        """Verifica se um usuário pode acessar este domain."""
        # Criador do domain
        if self.domain.criador == user:
            return True
        
        # Jogadores com acesso explícito
        return self.domain.jogadores_acesso.filter(id=user.id).exists()
    
    def get_atributos_finais(self):
        """Retorna os atributos da unidade com modificadores aplicados."""
        mods = {}
        
        # Modificadores de ancestry
        if self.ancestry:
            mods_ancestry = self.ancestry.get_modificadores()
            for key, value in mods_ancestry.items():
                mods[key] = mods.get(key, 0) + value
        
        # Modificadores de experience
        if self.experience:
            mods_experience = self.experience.get_modificadores()
            for key, value in mods_experience.items():
                mods[key] = mods.get(key, 0) + value
        
        # Modificadores de equipment
        if self.equipment:
            mods_equipment = self.equipment.get_modificadores()
            for key, value in mods_equipment.items():
                mods[key] = mods.get(key, 0) + value
        
        # Modificadores de unit type
        if self.unit_type:
            mods_type = self.unit_type.get_modificadores()
            for key, value in mods_type.items():
                mods[key] = mods.get(key, 0) + value
        
        return {
            'ataque': max(1, self.ataque + mods.get('ataque', 0)),
            'poder': max(1, self.poder + mods.get('poder', 0)),
            'defesa': max(1, self.defesa + mods.get('defesa', 0)),
            'resistencia': max(1, self.resistencia + mods.get('resistencia', 0)),
            'moral': self.moral + mods.get('moral', 0),
        }
    
    def get_custos_finais(self):
        """
        Calcula os custos finais da unidade de acordo com a fórmula:
        
        1. Soma os bônus de Ataque, Poder, Defesa e Resistência
        2. Adiciona o dobro do bônus de Moral
        3. Multiplica pelo Cost Modifier do Type
        4. Multiplica pelo Cost Modifier do Size
        5. Multiplica por 10
        6. Adiciona o custo de todos os traits
        7. Adiciona 30 pontos fixos
        8. Upkeep = 10% do custo total
        """
        # Passo 1: Calcular bônus de atributos
        # Bônus = diferença entre valor final e valor base (1)
        atributos_finais = self.get_atributos_finais()
        
        bonus_ataque = max(0, atributos_finais['ataque'] - 1)
        bonus_poder = max(0, atributos_finais['poder'] - 1)
        bonus_defesa = max(0, atributos_finais['defesa'] - 1)
        bonus_resistencia = max(0, atributos_finais['resistencia'] - 1)
        bonus_moral = max(0, atributos_finais['moral'] - 1)
        
        # Passo 1-2: Soma dos bônus (com Moral contando dobro)
        total_bonus = (bonus_ataque + bonus_poder + bonus_defesa + 
                      bonus_resistencia + (2 * bonus_moral))
        
        # Passo 3: Multiplicar pelo Cost Modifier do Type
        custo_base = total_bonus
        if self.unit_type:
            custo_base *= float(self.unit_type.multiplicador_custo)
        
        # Passo 4: Multiplicar pelo Cost Modifier do Size
        if self.size:
            custo_base *= float(self.size.multiplicador_custo)
        
        # Passo 5: Multiplicar por 10
        custo_base *= 10
        
        # Passo 6: Adicionar custo dos traits
        custo_traits = 0
        for trait in self.traits.all():
            custo_traits += trait.custo
        
        # Passo 7: Adicionar 30 pontos fixos
        custo_total = int(custo_base) + custo_traits + 30
        
        # Passo 8: Calcular upkeep (10% do custo total)
        upkeep = int(custo_total * 0.1)
        
        return {
            'custo_ouro': custo_total,
            'custo_dragonshards': 0,
            'upkeep': upkeep,
        }


# Importar modelos de warfare
from .models_warfare import (
    CombateWarfare,
    ParticipanteWarfare,
    StatusUnitWarfare,
    TurnoWarfare,
    MapaWarfare,
    PosicaoUnitWarfare,
)
