# 📜 Novo Formato do Histórico de Ataques

## ✅ Implementação Concluída (Parcial)

### O que foi feito:

1. **Função de Formatação** (`_format_attack_log`)
   - Localização: `combate/views.py` (após função `_verificar_resistencia_imunidade`)
   - Retorna HTML estruturado semanticamente
   - Suporta todos os modos e tipos de poder

2. **CSS Completo**
   - Localização: `combate/templates/combate/detalhes_combate.html`
   - Classes CSS para cada modo de ataque com cores distintas
   - Estilos para efeitos (sucesso, dano, resistência, imune, crítico)
   - Layout responsivo e moderno

3. **Exemplo Implementado**
   - Ataque em Área (falha na esquiva) - COMPLETO
   - Mostra rolls de esquiva e defesa separadamente
   - Lista efeitos em badges coloridos

## 🎨 Cores por Modo

- **CORPO A CORPO** (Melee): Vermelho `#ff6b6b`
- **À DISTÂNCIA** (Ranged): Ciano `#4ecdc4`
- **ÁREA** (Area): Amarelo `#ffe66d`
- **PERCEPÇÃO** (Perception): Azul claro `#a8dadc`
- **DIRETO** (Direct): Verde água `#95e1d3`

## 🏷️ Cores dos Efeitos

- **Sucesso** (sem efeito): Verde `#51cf66`
- **Dano/Ferimentos**: Vermelho claro `#ff8787`
- **Resistência**: Amarelo `#ffd43b`
- **Imunidade**: Azul `#748ffc`
- **Crítico** (incapacitado): Vermelho forte `#ff6b6b`
- **Neutro**: Cinza `#868e96`

## 📋 Exemplo Visual

```html
┌─────────────────────────────────────────────────────┐
│ [ÁREA] GM usou Bola de Fogo (Fogo)                 │
│ → teste                                             │
│                                                     │
│ Esquiva:  12 + 3 = 15 vs CD 20 → FALHA             │
│ Defesa (Resistencia): 7 + 2 = 9 vs CD 20          │
│                                                     │
│ Resultado:                                          │
│ [RESISTÊNCIA +5] [Ferimentos +1] [+1 de dano]      │
└─────────────────────────────────────────────────────┘
```

## 🔧 Próximos Passos

Para completar a implementação, você precisará atualizar os seguintes casos:

### 1. Área - Sucesso Parcial na Esquiva
**Linha ~2475-2520**
```python
resultado = _format_attack_log(
    atacante_nome=atacante.nome,
    poder_nome=poder_atual.nome,
    poder_tipo=tipo,
    poder_modo='area',
    duracao=duracao_label,
    tipo_dano=tipo_dano_poder,
    alvo_nome=alvo.nome,
    esquiva_roll={'d20': rolagem_esq_base, 'bonus': esquiva+esq_next, 
                  'total': rolagem_esq, 'cd': cd, 'resultado': 'sucesso parcial'},
    defesa_roll={'defesa': defesa_attr, 'd20': d_base, 'bonus': defesa_bonus,
                 'total': d_total, 'cd': cd_sucesso, 'resultado': ...},
    efeitos=[...]
)
```

### 2. Percepção
**Linha ~2550-2600**
Similar ao área, mas sem esquiva_roll

### 3. Melee/Ranged
**Linha ~2650-2750**
Adiciona ataque_roll com aparar/esquivar

### 4. Cura
**Linha ~1875-1905**
Formato mais simples, apenas defesa_roll como "teste"

### 5. Buff/Debuff
**Linha ~1908-1912**
Formato mais simples, sem rolls

### 6. Descritivo
**Linha ~1858-1865**
Roll único simples

## 🧪 Como Testar

1. Recarregue o servidor Django
2. Entre em um combate
3. Use um poder em área contra um alvo com resistência
4. Verifique o histórico - deve aparecer formatado com:
   - Badge colorido do modo
   - Nome do atacante e poder
   - Rolls organizados em linhas separadas
   - Efeitos em badges coloridos

## 📝 Notas

- O formato antigo ainda aparecerá para casos não atualizados
- Você pode atualizar progressivamente ou de uma vez
- A função `_format_attack_log` é reutilizável para todos os casos
- CSS já está completo e pronto para todos os modos

## 🎯 Vantagens do Novo Formato

✅ **Legibilidade**: Informações organizadas em hierarquia visual clara
✅ **Escaneabilidade**: Cores facilitam identificar tipo de ataque/resultado
✅ **Acessibilidade**: HTML semântico (`<article>`, `<dl>`) para screen readers  
✅ **Manutenibilidade**: Lógica centralizada, fácil adicionar novos modos
✅ **Performance**: CSS renderizado uma vez, não strings Python
✅ **Responsivo**: Adapta-se a qualquer tamanho de tela
