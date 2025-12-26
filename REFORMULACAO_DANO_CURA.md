# Reformulação do Sistema de Dano e Cura

## Data: 26 de dezembro de 2025

## Visão Geral

O sistema de dano e cura foi completamente reformulado para substituir o modelo anterior de incremento cumulativo por um sistema baseado em **graus de falha** que gera **condições progressivas**.

---

## Sistema de Dano

### Regra Geral

Sempre que um alvo **falha em um teste de Resistência contra dano**, ele sofre consequências de acordo com o **grau de falha** obtido no teste.

### Graus de Falha e Efeitos

Cada ataque pode gerar **apenas um resultado de dano**, variando conforme o grau de falha:

| Grau de Falha | Efeito | Campo `dano` |
|---------------|--------|-------------|
| **1 grau** (falha simples) | 1 Ferimento | `dano = 1` |
| **2 graus** | 1 Ferimento + **Tonto** | `dano = 2` |
| **3 graus** | 1 Ferimento + **Abatido** | `dano = 3` |
| **4+ graus** | **Incapacitado** | `dano = 4` |

### Características Importantes

1. **Campo `dano` como ESTADO**: O campo `dano` no modelo `Participante` agora representa o **estado da condição atual** (valores 1-4), não é mais cumulativo.

2. **Ferimentos Acumulados**: O campo `ferimentos` continua acumulando +1 por cada falha em salvamento contra dano, gerando penalidade cumulativa em futuros salvamentos.

3. **Atualização por Grau Maior**: O estado de dano só é atualizado quando o novo grau é **maior** que o estado atual:
   - Se o participante está Tonto (dano=2) e sofre uma falha de 1 grau, mantém Tonto
   - Se o participante está Tonto (dano=2) e sofre uma falha de 3 graus, passa para Abatido

4. **Imunidade e Resistência**:
   - **Imunidade** ao tipo de dano bloqueia totalmente os efeitos
   - **Resistência** já foi aplicada na defesa passiva (+5), registrada apenas para log

### Registro no Combate

Na coluna "Dano" da tabela de participantes, agora exibe-se o texto da condição:
- `1` → **Ferimento**
- `2` → **Tonto**
- `3` → **Abatido**
- `4` → **Incapacitado**

---

## Sistema de Cura

### Nova Regra de Cura

A cura foi reformulada para:
1. **NÃO remover mais aflições** (atua exclusivamente sobre dano)
2. Remover efeitos de dano **progressivamente**, do mais grave ao menos grave

### Ordem de Remoção dos Efeitos

Sempre que um alvo recebe cura **bem-sucedida**, os efeitos são removidos na seguinte ordem:

1. **Incapacitado** (dano 4) → **Abatido** (dano 3)
2. **Abatido** (dano 3) → **Tonto** (dano 2)
3. **Tonto** (dano 2) → **Ferimento** (dano 1)
4. **Ferimento** (dano 1) + ferimentos acumulados > 0 → Remove 1 ferimento
5. **Ferimento** (dano 1) + ferimentos acumulados = 0 → Completamente curado (dano 0)

### Características da Cura

- **CD baseado em Ferimentos**: CD = 10 + ferimentos acumulados
- **Um passo por vez**: Cada cura bem-sucedida remove apenas um passo na hierarquia
- **Não afeta Aflições**: Cura nunca remove ou altera níveis de aflição

---

## Implementação Técnica

### Arquivos Modificados

1. **`combate/views.py`**:
   - Nova função `_dano_condicao(nivel)`: converte estado numérico em texto
   - Nova função `_aplicar_cura(alvo_part)`: implementa remoção progressiva
   - Função `_aplicar_falha_salvamento()`: reformulada para o novo sistema de dano baseado em graus
   - Atualizadas todas as mensagens de log em ataques, tiques de concentração e avanço de turno

2. **`combate/templates/combate/_tabela_participantes.html`**:
   - Adicionado filtro `dano_condicao` para exibir texto ao invés de número

3. **`combate/templatetags/combate_extras.py`** (novo):
   - Criado filtro de template `dano_condicao` para conversão de número em texto

4. **`combate/migrations/0019_ajustar_dano_novo_sistema.py`** (nova):
   - Migration de dados para truncar valores de dano > 4 para 4 (Incapacitado)

### Funções Principais

#### `_aplicar_falha_salvamento()`
```python
# Sistema NOVO de dano:
# - Sempre acumula Ferimentos +1
# - O campo dano representa o ESTADO (1-4), não é cumulativo
# - Atualiza apenas se o novo grau for maior que o estado atual
```

#### `_aplicar_cura()`
```python
# Remove efeitos progressivamente:
# Incapacitado → Abatido → Tonto → Ferimentos (um a um)
# Retorna: (curou_algo: bool, mensagem: str)
```

---

## Migração de Dados Existentes

A migration `0019_ajustar_dano_novo_sistema.py`:
- Trunca valores de `dano > 4` para `dano = 4`
- Preserva valores de 1-4 como estão
- Não altera campos de `ferimentos` ou `aflicao`

---

## Testagem Recomendada

1. ✅ Verificar exibição correta das condições na tabela de participantes
2. ✅ Testar ataques com diferentes graus de falha (1-4)
3. ✅ Verificar acúmulo correto de Ferimentos
4. ✅ Testar cura progressiva em todas as condições
5. ✅ Verificar que cura não remove aflições
6. ✅ Testar imunidade e resistência a tipos de dano
7. ✅ Verificar mensagens de log em combate

---

## Notas de Compatibilidade

- **Combates em andamento**: Valores de dano existentes são interpretados como estados
- **Ferimentos acumulados**: Mantidos intactos, continuam gerando penalidade em salvamentos
- **Aflições**: Sistema de aflição permanece inalterado
- **Efeitos de concentração/sustentado**: Funcionam normalmente com o novo sistema

---

## Próximos Passos (Opcional)

1. Adicionar indicadores visuais (ícones ou cores) para cada condição na UI
2. Criar relatório de combate com histórico de condições
3. Implementar efeitos especiais baseados em condições (ex: Tonto = penalidades adicionais)
