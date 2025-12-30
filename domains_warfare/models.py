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
        return user.is_staff or user.is_superuser or self.sala.mestre == user
    
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
