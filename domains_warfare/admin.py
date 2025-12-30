from django.contrib import admin
from .models import Domain


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

