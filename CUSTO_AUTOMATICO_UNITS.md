# Cálculo Automático de Custos de Units - Implementação Completa

## Visão Geral
Implementado sistema de cálculo automático de custos em tempo real para Units no formulário de criação/edição, permitindo que usuários vejam imediatamente quanto de ouro a unidade custará.

## Funcionalidades Implementadas

### 1. **Endpoint AJAX para Cálculo de Custos**
- **Rota**: `/domains/ajax/calculate-unit-cost/`
- **Método**: GET
- **Função**: `calculate_unit_cost()` em `views.py`

#### Parâmetros aceitos:
- `ancestry` - ID da ancestria
- `unit_type` - ID do tipo de unidade
- `size` - ID do tamanho
- `experience` - ID da experiência
- `equipment` - ID do equipamento
- `traits` - Lista de IDs de traits selecionados
- `ataque`, `poder`, `defesa`, `resistencia`, `moral` - Atributos base

#### Retorno JSON:
```json
{
  "success": true,
  "custo_ouro": 430,
  "upkeep": 43,
  "final_attributes": {
    "ataque": 7,
    "poder": 7,
    "defesa": 7,
    "resistencia": 5,
    "moral": 10
  },
  "modifiers": {
    "ataque": 4,
    "poder": 4,
    "defesa": 4,
    "resistencia": 2,
    "moral": 5
  }
}
```

### 2. **Interface de Exibição de Custos**
Substituiu os campos manuais de custo por uma exibição automática e elegante que mostra:

- **Custo Total**: Valor em ouro calculado automaticamente
- **Manutenção (Upkeep)**: 10% do custo total por turno
- **Atributos Finais**: Exibe os 5 atributos com todos os modificadores aplicados
- **Status da Calculação**: Feedback visual sobre o estado do cálculo

#### Design Visual:
- Painel destacado com borda dourada
- Grid de 2 colunas para custo e upkeep
- Grid de 5 colunas para atributos finais
- Ícones e cores temáticas do sistema

### 3. **JavaScript em Tempo Real**
Implementado sistema de cálculo dinâmico que:

- **Monitora mudanças** em todos os campos relevantes:
  - Selects: Ancestry, Unit Type, Size, Experience, Equipment
  - Inputs numéricos: Ataque, Poder, Defesa, Resistência, Moral
  - Checkboxes: Traits selecionados

- **Debouncing**: Aguarda 300ms após a última mudança antes de fazer requisição
- **Feedback visual**: Mostra status "Calculando..." durante requisição
- **Atualização automática**: Atualiza custos e atributos instantaneamente
- **Cálculo inicial**: Executa automaticamente ao carregar página (útil para edição)

### 4. **Fórmula de Cálculo**
A view AJAX implementa a mesma fórmula do modelo `Unit.get_custos_finais()`:

1. Calcula atributos finais com todos os modificadores
2. Determina bônus (diferença do valor base 1)
3. Soma bônus (Morale conta dobrado)
4. Multiplica por Type Cost Modifier
5. Multiplica por Size Cost Modifier
6. Multiplica por 10
7. Adiciona custo dos traits
8. Adiciona 30 pontos fixos
9. Calcula upkeep (10%)

## Arquivos Modificados

### 1. `domains_warfare/views.py`
- Adicionados imports: `JsonResponse`, modelos relacionados
- Nova função: `calculate_unit_cost(request)` - endpoint AJAX completo

### 2. `domains_warfare/urls.py`
- Nova rota: `path('ajax/calculate-unit-cost/', views.calculate_unit_cost, name='calculate_unit_cost')`

### 3. `domains_warfare/templates/domains_warfare/unit_form.html`
- Adicionados campos `unit_type` e `size` ao formulário
- Removida seção manual de custos
- Adicionada seção de exibição automática de custos
- Implementado JavaScript para cálculo em tempo real
- Estilização visual para painel de custos

## Exemplo de Uso

### Cenário: Criando uma Unit
1. Usuário preenche nome e descrição
2. Seleciona Ancestry: **Bugbear**
3. Seleciona Type: **Infantry** (se aplicável)
4. Seleciona Size: **1d6**
5. Seleciona Experience: **Elite**
6. Seleciona Equipment: **Heavy**
7. Define atributos base: Attack=3, Power=3, Defense=3, Toughness=3, Morale=5

**Resultado Instantâneo:**
- Custo Total: **430 ⚜ Ouro**
- Manutenção: **43 ⚜/turno**
- Atributos Finais: Attack=7, Power=7, Defense=7, Toughness=5, Morale=10

### Comparação de Tamanhos (mesmo exemplo)
- **1d4**: 294 Ouro
- **1d6**: 430 Ouro
- **1d8**: 562 Ouro
- **1d10**: 693 Ouro
- **1d12**: 830 Ouro

## Testes Realizados

### Teste do Endpoint AJAX
```python
# Parâmetros: Bugbear, 1d6, Elite, Heavy
# Atributos: 3/3/3/3/5
Response: 200 OK
Cost: 430 Gold
Upkeep: 43 Gold/turn
Final Attributes: {7, 7, 7, 5, 10}
```

### Validações
- ✅ Endpoint responde corretamente
- ✅ Cálculo coincide com `Unit.get_custos_finais()`
- ✅ JavaScript sem erros de sintaxe
- ✅ Template renderiza corretamente
- ✅ Imports e rotas configurados
- ✅ Debouncing funciona (300ms delay)
- ✅ Feedback visual implementado

## Benefícios

1. **UX Melhorado**: Usuários veem custos instantaneamente sem submeter formulário
2. **Transparência**: Exibe como cada escolha afeta o custo final
3. **Menos Erros**: Remove entrada manual de custos (fonte de inconsistências)
4. **Decisões Informadas**: Jogadores podem comparar opções antes de criar
5. **Consistência**: Usa mesma lógica de cálculo do modelo Django
6. **Performance**: Debouncing evita requisições excessivas
7. **Feedback**: Status visual indica quando cálculo está em progresso

## Próximos Passos Possíveis

- [ ] Adicionar tooltip explicando a fórmula de cálculo
- [ ] Exibir custo individual de cada trait selecionado
- [ ] Mostrar breakdown detalhado do cálculo (bonus por fonte)
- [ ] Adicionar comparação lado-a-lado de diferentes configurações
- [ ] Implementar preview de "can afford" (verificar se domain tem ouro suficiente)
- [ ] Cache de resultados para configurações idênticas
