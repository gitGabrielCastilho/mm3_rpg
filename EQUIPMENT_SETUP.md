# Como Aplicar o Sistema de Unit Equipment

## Pré-requisitos
- Certificar que não há DATABASE_URL setada (para usar SQLite local)
- Django deve estar rodando ou disponível para migrations

## Passos

### 1. Aplicar Migrations

```bash
cd /d/TI/mm3_rpg
python manage.py migrate domains_warfare
```

Saída esperada:
```
Applying domains_warfare.0007_unitequipment_unit_equipment... OK
```

### 2. Popular Equipamentos

```bash
python manage.py populate_equipment
```

Saída esperada:
```
✓ Criado: Light
✓ Criado: Medium
✓ Criado: Heavy
✓ Criado: Super-Heavy

✓ Concluído: 4 criados, 0 atualizados
```

### 3. Verificar via Django Shell

```bash
python manage.py shell
```

```python
from domains_warfare.models import UnitEquipment

# Verificar que existem 4 tipos
print(UnitEquipment.objects.count())  # Output: 4

# Listar todos com modificadores
for eq in UnitEquipment.objects.all():
    mods = eq.get_modificadores()
    print(f"{eq.get_nome_display()}: POD+{mods['poder']}, DEF+{mods['defesa']}")

# Output:
# Heavy: POD+4, DEF+4
# Light: POD+1, DEF+1
# Medium: POD+2, DEF+2
# Super-Heavy: POD+6, DEF+6
```

### 4. Acessar Admin Interface

1. Ir para http://localhost:8000/admin
2. Login com admin credentials
3. Acessar "Tipos de Equipamento de Unidades" para ver/editar equipment
4. Editar qualquer "Unit" para ver o novo campo equipment

### 5. Testar Cálculos de Atributos

```bash
python manage.py shell
```

```python
from domains_warfare.models import Unit, UnitEquipment, UnitAncestry, Domain
from django.contrib.auth.models import User

# Pegar/criar dados necessários
domain = Domain.objects.first()
user = User.objects.first()
ancestry = UnitAncestry.objects.first()
equipment = UnitEquipment.objects.get(nome='heavy')

# Criar unit de teste
unit, created = Unit.objects.get_or_create(
    nome='TestEquipment',
    domain=domain,
    defaults={
        'ancestry': ancestry,
        'equipment': equipment,
        'criador': user,
        'ataque': 1,
        'poder': 1,
        'defesa': 1,
        'resistencia': 1,
        'moral': 5,
    }
)

# Ver atributos finais
final = unit.get_atributos_finais()
print(f"Base Poder: {unit.poder}")
print(f"Equipment Poder: +{equipment.modificador_poder}")
if unit.ancestry:
    print(f"Ancestry Poder: +{unit.ancestry.modificador_poder}")
print(f"Final Poder: {final['poder']}")

print(f"\nBase Defesa: {unit.defesa}")
print(f"Equipment Defesa: +{equipment.modificador_defesa}")
if unit.ancestry:
    print(f"Ancestry Defesa: +{unit.ancestry.modificador_defesa}")
print(f"Final Defesa: {final['defesa']}")
```

## Troubleshooting

### Erro: "no such table: domains_warfare_unitequipment"
- Significa que a migration não foi aplicada
- Execute: `python manage.py migrate domains_warfare`

### Erro: PostgreSQL connection error
- Certificar que DATABASE_URL não está setada
- Usar SQLite local: `unset DATABASE_URL`

### Migration não foi criada
- Já foi criada automaticamente (0007_unitequipment_unit_equipment.py)
- Está localizada em: `domains_warfare/migrations/0007_unitequipment_unit_equipment.py`

## Verificação Final

Após completar todos os passos:

```bash
python manage.py check
```

Saída esperada:
```
System check identified no issues (0 silenced).
```

---

Se todos os passos forem completados com sucesso, o sistema de Unit Equipment está 100% operacional! 🎉
