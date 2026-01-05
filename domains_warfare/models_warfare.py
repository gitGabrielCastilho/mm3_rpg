"""
Modelos para o sistema de Warfare Combat - combate estratégico entre Domains e suas Units.
Similar ao sistema de combate de personagens, mas com mecânicas específicas para unidades militares.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Domain, Unit


class CombateWarfare(models.Model):
    """
    Representa uma sala de combate entre Domains (guerra estratégica).
    Similar ao Combate de personagens, mas para unidades militares.
    """
    sala = models.ForeignKey(
        'salas.Sala',
        on_delete=models.CASCADE,
        related_name='combates_warfare',
        verbose_name="Sala"
    )
    
    nome = models.CharField(
        max_length=200,
        verbose_name="Nome do Combate",
        help_text="Ex: Batalha de Lurching Tower, Cerco de Winterhold"
    )
    
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo"
    )
    
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    
    criador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='combates_warfare_criados',
        verbose_name="Criador"
    )
    
    # Domains participantes (ManyToMany através de ParticipanteWarfare)
    domains = models.ManyToManyField(
        Domain,
        through='ParticipanteWarfare',
        related_name='combates_warfare'
    )
    
    # Fortificação (opcional - apenas um lado pode usar)
    fortificacao = models.ForeignKey(
        'Fortificacao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='combates_warfare',
        verbose_name="Fortificação",
        help_text="Fortificação presente neste combate (bônus para defensores)"
    )
    
    # Domain defensor (qual side está defendendo a fortificação)
    domain_defensor = models.ForeignKey(
        Domain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='combates_defensores',
        verbose_name="Domain Defensor",
        help_text="Domain que está defendendo a fortificação"
    )
    
    # Rastreamento do HP da fortificação durante o combate
    hp_fortificacao_atual = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="HP Atual da Fortificação",
        help_text="HP restante da fortificação durante o combate"
    )
    
    class Meta:
        verbose_name = "Combate Warfare"
        verbose_name_plural = "Combates Warfare"
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.nome} ({self.sala.nome})"
    
    def get_turno_ativo(self):
        """Retorna o turno ativo ou None."""
        return self.turnos_warfare.filter(ativo=True).first()
    
    def inicializar_fortificacao(self):
        """Inicializa o HP da fortificação quando um combate é criado."""
        if self.fortificacao and not self.hp_fortificacao_atual:
            self.hp_fortificacao_atual = self.fortificacao.hp_fortificacao
            self.save(update_fields=['hp_fortificacao_atual'])
    
    def get_modificadores_defesa(self, unit_alvo):
        """
        Retorna o modificador de defesa baseado na fortificação.
        Apenas o alvo (defendendo) recebe bônus, e apenas se for do domain defensor.
        """
        if not self.fortificacao or not self.domain_defensor or not self.hp_fortificacao_atual or self.hp_fortificacao_atual <= 0:
            return 0
        # Verifica se o alvo é do domain defensor
        if unit_alvo.domain_id != self.domain_defensor_id:
            return 0
        return self.fortificacao.defesa
    
    def get_modificadores_poder(self, unit_alvo):
        """
        Retorna o modificador de poder baseado na fortificação.
        Apenas para Archers defendendo na fortificação do seu domain.
        """
        if not self.fortificacao or not self.domain_defensor or not self.hp_fortificacao_atual or self.hp_fortificacao_atual <= 0:
            return 0
        
        # Verifica se o alvo é do domain defensor
        if unit_alvo.domain_id != self.domain_defensor_id:
            return 0
        
        # Verifica se é Archer - verifica no unit_type
        if hasattr(unit_alvo, 'unit_type') and unit_alvo.unit_type:
            unit_type_nome = getattr(unit_alvo.unit_type, 'nome', '')
            if 'archer' in unit_type_nome.lower():
                return self.fortificacao.poder
        
        return 0
    
    def get_modificadores_moral(self, unit_alvo):
        """
        Retorna o modificador de moral baseado na fortificação.
        Apenas o alvo (defendendo) recebe bônus, e apenas se for do domain defensor.
        """
        if not self.fortificacao or not self.domain_defensor or not self.hp_fortificacao_atual or self.hp_fortificacao_atual <= 0:
            return 0
        # Verifica se o alvo é do domain defensor
        if unit_alvo.domain_id != self.domain_defensor_id:
            return 0
        return self.fortificacao.moral
    
    def aplicar_dano_fortificacao(self, quantidade=1):
        """
        Aplica dano à fortificação. Retorna True se a fortificação foi destruída.
        """
        if not self.fortificacao or not self.hp_fortificacao_atual:
            return False
        
        self.hp_fortificacao_atual = max(0, self.hp_fortificacao_atual - quantidade)
        self.save(update_fields=['hp_fortificacao_atual'])
        
        # Retorna True se foi destruída
        return self.hp_fortificacao_atual <= 0


class ParticipanteWarfare(models.Model):
    """
    Representa um Domain participante em um combate warfare.
    """
    combate = models.ForeignKey(
        CombateWarfare,
        on_delete=models.CASCADE,
        related_name='participantes',
        verbose_name="Combate"
    )
    
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='participacoes_warfare',
        verbose_name="Domain"
    )
    
    ordem_iniciativa = models.IntegerField(
        default=0,
        verbose_name="Ordem de Iniciativa",
        help_text="Ordem no combate (menor = primeiro)"
    )
    
    adicionado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Adicionado em"
    )
    
    class Meta:
        verbose_name = "Participante Warfare"
        verbose_name_plural = "Participantes Warfare"
        ordering = ['ordem_iniciativa', 'adicionado_em']
        unique_together = ['combate', 'domain']
    
    def __str__(self):
        return f"{self.domain.nome} em {self.combate.nome}"


class StatusUnitWarfare(models.Model):
    """
    Rastreia o status atual de uma Unit em combate (HP, conditions, etc).
    """
    combate = models.ForeignKey(
        CombateWarfare,
        on_delete=models.CASCADE,
        related_name='status_units',
        verbose_name="Combate"
    )
    
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='status_warfare',
        verbose_name="Unidade"
    )
    
    # HP atual (baseado no Size da unidade)
    hp_atual = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="HP Atual"
    )
    
    hp_maximo = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="HP Máximo"
    )
    
    # Estados
    diminished = models.BooleanField(
        default=False,
        verbose_name="Diminished",
        help_text="Unit com ≤50% HP"
    )
    
    incapacitado = models.BooleanField(
        default=False,
        verbose_name="Incapacitado",
        help_text="Unit com 0 HP"
    )
    
    # Efeitos ativos
    efeitos_ativos = models.TextField(
        blank=True,
        verbose_name="Efeitos Ativos",
        help_text="JSON com efeitos temporários"
    )
    
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )
    
    class Meta:
        verbose_name = "Status de Unidade Warfare"
        verbose_name_plural = "Status de Unidades Warfare"
        unique_together = ['combate', 'unit']
    
    def __str__(self):
        return f"{self.unit.nome}: {self.hp_atual}/{self.hp_maximo} HP"
    
    def aplicar_dano(self, quantidade):
        """Aplica dano à unidade e atualiza estados."""
        self.hp_atual = max(0, self.hp_atual - quantidade)
        
        # Atualiza estado diminished
        if self.hp_atual <= (self.hp_maximo / 2):
            self.diminished = True
        
        # Atualiza estado incapacitado
        if self.hp_atual == 0:
            self.incapacitado = True
        
        self.save()
        return self.hp_atual
    
    def curar(self, quantidade):
        """Cura a unidade."""
        self.hp_atual = min(self.hp_maximo, self.hp_atual + quantidade)
        
        # Remove diminished se HP > 50%
        if self.hp_atual > (self.hp_maximo / 2):
            self.diminished = False
        
        # Remove incapacitado se HP > 0
        if self.hp_atual > 0:
            self.incapacitado = False
        
        self.save()
        return self.hp_atual


class TurnoWarfare(models.Model):
    """
    Representa um turno/ação em um combate warfare.
    Similar aos turnos de combate regular, mas para ações de unidades.
    """
    combate = models.ForeignKey(
        CombateWarfare,
        on_delete=models.CASCADE,
        related_name='turnos_warfare',
        verbose_name="Combate"
    )
    
    unit_atacante = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='turnos_atacante_warfare',
        verbose_name="Unidade Atacante"
    )
    
    unit_alvo = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='turnos_alvo_warfare',
        null=True,
        blank=True,
        verbose_name="Unidade Alvo"
    )
    
    ordem = models.IntegerField(
        default=0,
        verbose_name="Ordem"
    )
    
    ativo = models.BooleanField(
        default=False,
        verbose_name="Turno Ativo"
    )
    
    # Detalhes da ação
    tipo_acao = models.CharField(
        max_length=50,
        choices=[
            ('ataque', 'Ataque'),
            ('movimento', 'Movimento'),
            ('esperar', 'Esperar'),
            ('outro', 'Outro'),
        ],
        default='ataque',
        verbose_name="Tipo de Ação"
    )
    
    # Rolls e resultados
    roll_ataque = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Roll de Ataque (d20)"
    )
    
    roll_poder = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Roll de Poder (d20)"
    )
    
    roll_moral = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Roll de Moral (d20)"
    )
    
    sucesso_ataque = models.BooleanField(
        default=False,
        verbose_name="Ataque Bem-Sucedido"
    )
    
    sucesso_poder = models.BooleanField(
        default=False,
        verbose_name="Poder Bem-Sucedido"
    )
    
    falha_moral = models.BooleanField(
        default=False,
        verbose_name="Falha no Teste de Moral"
    )
    
    dano_causado = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Dano Causado"
    )
    
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição",
        help_text="Narrativa da ação"
    )
    
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    
    class Meta:
        verbose_name = "Turno Warfare"
        verbose_name_plural = "Turnos Warfare"
        ordering = ['ordem', 'criado_em']
    
    def __str__(self):
        return f"Turno {self.ordem}: {self.unit_atacante.nome}"


class MapaWarfare(models.Model):
    """
    Mapa tático para o combate warfare.
    """
    combate = models.ForeignKey(
        CombateWarfare,
        on_delete=models.CASCADE,
        related_name='mapas_warfare',
        verbose_name="Combate"
    )
    
    nome = models.CharField(
        max_length=200,
        verbose_name="Nome do Mapa"
    )
    
    imagem = models.ImageField(
        upload_to='warfare/mapas/',
        verbose_name="Imagem do Mapa"
    )
    
    ativo = models.BooleanField(
        default=True,
        verbose_name="Mapa Ativo"
    )
    
    adicionado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Adicionado em"
    )
    
    class Meta:
        verbose_name = "Mapa Warfare"
        verbose_name_plural = "Mapas Warfare"
        ordering = ['-adicionado_em']
    
    def __str__(self):
        return f"{self.nome} ({self.combate.nome})"


class PosicaoUnitWarfare(models.Model):
    """
    Posição de uma Unit no mapa de combate warfare.
    """
    mapa = models.ForeignKey(
        MapaWarfare,
        on_delete=models.CASCADE,
        related_name='posicoes_units',
        verbose_name="Mapa"
    )
    
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='posicoes_warfare',
        verbose_name="Unidade"
    )
    
    x = models.FloatField(
        default=0,
        verbose_name="Posição X"
    )
    
    y = models.FloatField(
        default=0,
        verbose_name="Posição Y"
    )
    
    visivel = models.BooleanField(
        default=True,
        verbose_name="Visível"
    )
    
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )
    
    class Meta:
        verbose_name = "Posição de Unidade Warfare"
        verbose_name_plural = "Posições de Unidades Warfare"
        unique_together = ['mapa', 'unit']
    
    def __str__(self):
        return f"{self.unit.nome} em ({self.x}, {self.y})"


class Fortificacao(models.Model):
    """
    Representa uma fortificação que pode ser usada em combates warfare.
    Fornece bônus a morais, defesa e poder (para archers) das unidades defensoras.
    """
    TIPOS_FORTIFICACAO = [
        ('cerca_pedra', 'Cerca de Pedra'),
        ('torre_guarda', 'Torre de Guarda'),
        ('muros_cidade', 'Muros da Cidade'),
        ('portoes_cidade', 'Portões da Cidade'),
        ('torreao_keep', 'Torreão (Keep)'),
        ('castelo', 'Castelo'),
    ]
    
    nome = models.CharField(
        max_length=100,
        verbose_name="Nome",
        choices=TIPOS_FORTIFICACAO
    )
    
    moral = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        verbose_name="Bônus de Moral",
        help_text="Bônus adicionado ao roll de Moral (0-4)"
    )
    
    defesa = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        verbose_name="Bônus de Defesa",
        help_text="Bônus adicionado à Defesa (0-4)"
    )
    
    poder = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        verbose_name="Bônus de Poder",
        help_text="Bônus de Poder para Archers apenas (0-2)"
    )
    
    hp_fortificacao = models.IntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Pontos de Vida da Fortificação",
        help_text="HP da própria fortificação (4-12)"
    )
    
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição",
        help_text="Descrição detalhada da fortificação"
    )
    
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    
    class Meta:
        verbose_name = "Fortificação"
        verbose_name_plural = "Fortificações"
        unique_together = ['nome']
    
    def __str__(self):
        return f"{self.get_nome_display()} (Moral +{self.moral}, Def +{self.defesa}, Poder +{self.poder})"
    
    def get_nome_display(self):
        """Retorna o nome formatado da fortificação."""
        return dict(self.TIPOS_FORTIFICACAO).get(self.nome, self.nome)
