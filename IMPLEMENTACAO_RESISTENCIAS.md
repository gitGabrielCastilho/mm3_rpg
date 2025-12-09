# Implementação de Resistências, Imunidades e Tipo de Dano

## ✅ Smoke Tests Realizados

**Status:** TODOS OS TESTES PASSARAM ✅

### Testes Executados:
1. ✅ Django check (0 issues)
2. ✅ Compilação Python (combate/views.py)
3. ✅ Função `_verificar_resistencia_imunidade()` (6 testes)
4. ✅ Função `_aplicar_falha_salvamento()` (7 testes)
5. ✅ Servidor Django inicia sem erros

---

## 📋 Checklist de Implementação

### Backend (combate/views.py)
- [x] Função `_verificar_resistencia_imunidade()` criada
- [x] Função `_aplicar_falha_salvamento()` atualizada com tipo_dano
- [x] Retorno expandido para (aplicou, incap, msg_resistencia)
- [x] 6 chamadas de `_aplicar_falha_salvamento()` atualizadas
- [x] Mensagens de resistência/imunidade adicionadas ao histórico

### Frontend (criar/editar_personagem.html)
- [x] Seção de Resistências/Imunidades adicionada
- [x] Badge de custo (Resist 5pp / Imun 10pp)
- [x] Cálculo de custos implementado
- [x] Listeners para recalcular custos em tempo real

### Modelos
- [x] `Personagem.resistencias_dano` (JSONField)
- [x] `Personagem.imunidades_dano` (JSONField)
- [x] `Poder.tipo_dano` (CharField com choices)
- [x] Validação de conflito resistência/imunidade

---

## 🎮 Mecânicas Implementadas

### Resistência (5 pp por tipo)
- Reduz grau de falha em **-1**
- Pode anular completamente falhas de grau 1
- Mensagem exibida: `"RESISTÊNCIA (-1 grau)"`

### Imunidade (10 pp por tipo)
- Bloqueia **totalmente** o dano
- Zero ferimentos, zero dano
- Mensagem exibida: `"IMUNE"`

### Tipo de Dano
- Campo `tipo_dano` em poderes de Dano
- Visível apenas quando `tipo = 'dano'`
- Usado para verificar resistência/imunidade no combate
- Não adiciona custo extra (informativo)

---

## 🧪 Resultados dos Testes

```
============================================================
🔥 SMOKE TEST: Resistências e Imunidades
============================================================

🧪 Testando _verificar_resistencia_imunidade()...
  ✅ Teste 1: Resistência a Fogo detectada corretamente
  ✅ Teste 2: Imunidade a Elétrico detectada corretamente
  ✅ Teste 3: Sem proteção a Ácido (correto)
  ✅ Teste 4: Case-insensitive funcionando (FOGO = fogo)
  ✅ Teste 5: Tipo vazio retorna sem proteção
  ✅ Teste 6: Tipo None retorna sem proteção

🧪 Testando _aplicar_falha_salvamento()...
  ✅ Teste 1: Imunidade bloqueia completamente (msg='IMUNE')
  ✅ Teste 2: Resistência reduz grau 2->1 (ferimentos=1, dano=1)
  ✅ Teste 3: Sem proteção aplica dano normal (ferimentos=1, dano=1)
  ✅ Teste 4: Resistência anula grau 1 completamente (sem dano)
  ✅ Teste 5: Resistência reduz grau 3->2 (ferimentos=1, dano=1)
  ✅ Teste 6: Sem tipo_dano não verifica resistência (dano normal)
  ✅ Teste 7: Aflição não é afetada por resistência (aflicao=2)

============================================================
✅ TODOS OS TESTES PASSARAM!
============================================================
```

---

## 📝 Guia de Testes Manuais

### 1. Testar Custos
1. Acesse criar/editar personagem
2. Marque resistências (ex: Fogo, Gelo)
3. Verifique badge: deve mostrar "Resist 5 / Imun 10 — 10" (2×5pp)
4. Marque imunidade (ex: Elétrico)
5. Badge deve atualizar: "Resist 5 / Imun 10 — 20" (10+10pp)
6. Custo total deve incluir resist+imun

### 2. Testar Tipo de Dano em Poderes
1. Crie/edite um poder
2. Selecione Tipo = "Dano"
3. Campo "Tipo de Dano" deve aparecer
4. Selecione outro Tipo (ex: "Cura")
5. Campo "Tipo de Dano" deve sumir

### 3. Testar em Combate
1. Crie personagem A com Resistência: Fogo
2. Crie personagem B com Imunidade: Gelo
3. Crie poder de Dano com tipo_dano="fogo"
4. Ataque A com esse poder
5. Mensagem deve mostrar: "RESISTÊNCIA (-1 grau)"
6. Ataque B com poder de tipo_dano="gelo"
7. Mensagem deve mostrar: "IMUNE"
8. Verifique que B não sofreu dano nem ferimentos

### 4. Validação
1. Tente marcar Fogo em Resistência E Imunidade
2. Ao salvar deve dar erro de validação
3. Conflitos não são permitidos

---

## 🐛 Edge Cases Testados

- ✅ Tipo de dano vazio/None (não verifica resistência)
- ✅ Case-insensitive (FOGO = fogo)
- ✅ Resistência anula grau 1 completamente
- ✅ Aflição ignora resistência/imunidade
- ✅ Poderes sem tipo_dano aplicam dano normal

---

## 📊 Arquivos Modificados

1. `combate/views.py` - Lógica de resistência/imunidade
2. `personagens/templates/personagens/criar_personagem.html` - UI e custos
3. `personagens/templates/personagens/editar_personagem.html` - UI e custos
4. `personagens/templates/personagens/criar_npc.html` - UI (já tinha)
5. `personagens/templates/personagens/editar_npc.html` - UI e JS
6. `itens/templates/itens/itens.html` - Campo tipo_dano em poderes de item

## 🔧 Ferramentas de Teste

- Script de smoke test: `tools/smoke_resistencias.py`
- Comando: `python tools/smoke_resistencias.py`
- 13 testes automatizados

---

**Data:** 2025-12-09  
**Status:** ✅ Implementação completa e testada
