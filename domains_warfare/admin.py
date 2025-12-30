from django.contrib import admin
from .models import Domain, Unit, UnitAncestry, UnitTrait, UnitExperience, UnitEquipment, UnitType, UnitSize


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    """Interface administrativa para gerenciar domínios."""
    
    list_display = ['nome', 'nivel', 'governante', 'sala', 'criador', 'criado_por_gm', 'ouro', 'dragonshards']
    list_filter = ['sala', 'nivel', 'criado_por_gm', 'criado_em']
    search_fields = ['nome', 'descricao', 'governante__nome', 'sala__nome', 'criador__username']
    filter_horizontal = ['jogadores_acesso']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao', 'brasao', 'nivel', 'governante', 'sala')
        }),
        ('Criação e Controle', {
            'fields': ('criador', 'criado_por_gm', 'jogadores_acesso')
        }),
        ('Características', {
            'fields': ('diplomacy', 'espionage', 'lore', 'operations')
        }),
        ('Recursos', {
            'fields': ('ouro', 'dragonshards')
        }),
        ('Strongholds', {
            'fields': ('keep', 'tower', 'temple', 'establishment')
        }),
        ('Metadados', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['criado_em', 'atualizado_em']
    
    def get_queryset(self, request):
        """Otimiza queries com select_related e prefetch_related."""
        qs = super().get_queryset(request)
        return qs.select_related('governante', 'sala', 'criador').prefetch_related('jogadores_acesso')


@admin.register(UnitAncestry)
class UnitAncestryAdmin(admin.ModelAdmin):
    """Interface administrativa para gerenciar ancestries de unidades."""
    
    list_display = ['get_nome', 'modificador_ataque', 'modificador_poder', 'modificador_defesa', 
                    'modificador_resistencia', 'modificador_moral', 'traits']
    search_fields = ['nome', 'descricao', 'traits']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao')
        }),
        ('Modificadores de Atributos', {
            'fields': ('modificador_ataque', 'modificador_poder', 'modificador_defesa', 
                      'modificador_resistencia', 'modificador_moral')
        }),
        ('Características', {
            'fields': ('traits',),
            'description': 'Traits que esta ancestry fornece automaticamente (separados por vírgula)'
        }),
    )
    
    def get_nome(self, obj):
        """Exibe o nome legível da ancestry."""
        return obj.get_nome_display()
    get_nome.short_description = 'Ancestry'


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    """Interface administrativa para gerenciar unidades."""
    
    list_display = ['nome', 'domain', 'ancestry', 'unit_type', 'experience', 'equipment', 'ataque', 'poder', 'defesa', 'resistencia', 'moral', 'quantidade']
    list_filter = ['domain', 'ancestry', 'unit_type', 'experience', 'equipment', 'criado_em']
    search_fields = ['nome', 'descricao', 'domain__nome']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao', 'domain', 'ancestry', 'unit_type', 'experience', 'equipment', 'criador')
        }),
        ('Atributos Base', {
            'fields': ('ataque', 'poder', 'defesa', 'resistencia', 'moral')
        }),
        ('Traits Adquiridos', {
            'fields': ('traits',),
            'description': 'Selecione os traits especiais que esta unidade adquiriu'
        }),
        ('Custos', {
            'fields': ('custo_ouro', 'custo_dragonshards')
        }),
        ('Composição', {
            'fields': ('quantidade',)
        }),
        ('Metadados', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['criador', 'criado_em', 'atualizado_em']
    filter_horizontal = ['traits']
    
    def get_queryset(self, request):
        """Otimiza queries."""
        qs = super().get_queryset(request)
        return qs.select_related('domain', 'ancestry', 'unit_type', 'experience', 'equipment', 'criador').prefetch_related('traits')
    
    def save_model(self, request, obj, form, change):
        """Define o criador automaticamente."""
        if not change:
            obj.criador = request.user
        super().save_model(request, obj, form, change)


@admin.register(UnitTrait)
class UnitTraitAdmin(admin.ModelAdmin):
    """Interface administrativa para gerenciar traits de unidades."""
    
    list_display = ['get_nome', 'custo', 'descricao_preview']
    search_fields = ['nome', 'descricao']
    list_filter = ['custo']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'custo')
        }),
        ('Descrição', {
            'fields': ('descricao',)
        }),
    )
    
    def get_nome(self, obj):
        """Exibe o nome legível do trait."""
        return obj.get_nome_display()
    get_nome.short_description = 'Trait'
    
    def descricao_preview(self, obj):
        """Mostra preview da descrição."""
        return obj.descricao[:60] + '...' if len(obj.descricao) > 60 else obj.descricao
    descricao_preview.short_description = 'Descrição'


@admin.register(UnitExperience)
class UnitExperienceAdmin(admin.ModelAdmin):
    """Interface administrativa para gerenciar níveis de experiência de unidades."""
    
    list_display = ['get_nome', 'modificador_ataque', 'modificador_resistencia', 'modificador_moral', 'descricao_preview']
    search_fields = ['nome', 'descricao']
    list_filter = []
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao')
        }),
        ('Modificadores de Atributos', {
            'fields': ('modificador_ataque', 'modificador_poder', 'modificador_defesa', 
                      'modificador_resistencia', 'modificador_moral')
        }),
    )
    
    readonly_fields = ['nome']
    
    def get_nome(self, obj):
        """Exibe o nome legível do nível de experiência."""
        return obj.get_nome_display()
    get_nome.short_description = 'Nível de Experiência'
    
    def descricao_preview(self, obj):
        """Mostra preview da descrição."""
        preview = obj.descricao[:50] + '...' if len(obj.descricao) > 50 else obj.descricao
        return preview if obj.descricao else '(sem descrição)'
    descricao_preview.short_description = 'Descrição'

@admin.register(UnitEquipment)
class UnitEquipmentAdmin(admin.ModelAdmin):
    """Interface administrativa para gerenciar tipos de equipamento de unidades."""
    
    list_display = ['get_nome', 'modificador_poder', 'modificador_defesa', 'descricao_preview']
    search_fields = ['nome', 'descricao']
    list_filter = []
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao')
        }),
        ('Modificadores de Atributos', {
            'fields': ('modificador_poder', 'modificador_defesa')
        }),
    )
    
    readonly_fields = ['nome']
    
    def get_nome(self, obj):
        """Exibe o nome legível do tipo de equipamento."""
        return obj.get_nome_display()
    get_nome.short_description = 'Tipo de Equipamento'
    
    def descricao_preview(self, obj):
        """Mostra preview da descrição."""
        preview = obj.descricao[:50] + '...' if len(obj.descricao) > 50 else obj.descricao
        return preview if obj.descricao else '(sem descrição)'
    descricao_preview.short_description = 'Descrição'


@admin.register(UnitType)
class UnitTypeAdmin(admin.ModelAdmin):
    """Interface administrativa para gerenciar tipos de unidades."""
    
    list_display = ['get_nome', 'modificador_ataque', 'modificador_poder', 'modificador_defesa', 
                    'modificador_resistencia', 'modificador_moral', 'multiplicador_custo_display']
    search_fields = ['nome', 'descricao']
    list_filter = []
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao')
        }),
        ('Modificadores de Atributos', {
            'fields': ('modificador_ataque', 'modificador_poder', 'modificador_defesa', 
                      'modificador_resistencia', 'modificador_moral')
        }),
        ('Custo', {
            'fields': ('multiplicador_custo',),
            'description': 'Multiplicador que será aplicado aos custos de ouro e dragonshards'
        }),
    )
    
    readonly_fields = ['nome']
    
    def get_nome(self, obj):
        """Exibe o nome legível do tipo de unidade."""
        return obj.get_nome_display()
    get_nome.short_description = 'Tipo'
    
    def multiplicador_custo_display(self, obj):
        """Exibe o multiplicador de custo formatado."""
        return f"{obj.multiplicador_custo}x"
    multiplicador_custo_display.short_description = 'Multiplicador de Custo'


@admin.register(UnitSize)
class UnitSizeAdmin(admin.ModelAdmin):
    """Interface administrativa para gerenciar tamanhos de unidades."""
    
    list_display = ['tamanho', 'multiplicador_custo_display']
    search_fields = ['tamanho']
    list_filter = []
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('tamanho',)
        }),
        ('Custo', {
            'fields': ('multiplicador_custo',),
            'description': 'Multiplicador que será aplicado aos custos de ouro'
        }),
    )
    
    readonly_fields = ['tamanho']
    
    def multiplicador_custo_display(self, obj):
        """Exibe o multiplicador de custo formatado."""
        return f"{obj.multiplicador_custo}x"
    multiplicador_custo_display.short_description = 'Multiplicador de Custo'
