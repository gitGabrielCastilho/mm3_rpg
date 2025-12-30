# Unit Ancestry & Traits System - Implementation Summary

## Overview
The complete Unit system with Ancestries and Traits has been successfully implemented in the Domains & Warfare module. It provides a comprehensive framework for unit management with ancestry-based attribute modifications and acquired traits with costs.

## Database Models

### UnitAncestry Model
- **Purpose**: Defines all available unit ancestries and their attribute modifiers
- **Fields**:
  - `nome` (CharField): Unique identifier for the ancestry
  - `descricao` (TextField): Optional description
  - `modificador_ataque` (IntegerField): Attack modifier (-∞ to +∞)
  - `modificador_poder` (IntegerField): Power modifier
  - `modificador_defesa` (IntegerField): Defense modifier
  - `modificador_resistencia` (IntegerField): Toughness/Resistance modifier
  - `modificador_moral` (IntegerField): Morale modifier
  - `traits` (TextField): Comma-separated list of innate traits (e.g., "Martial, Courageous")

### UnitTrait Model
- **Purpose**: Defines all available traits that units can acquire
- **Fields**:
  - `nome` (CharField): Unique identifier (16 traits available)
  - `descricao` (TextField): Detailed trait description
  - `custo` (IntegerField): Cost in points to acquire (50, 100, 200, or 250)
- **16 Available Traits**:
  1. **Amphibious** (50) - No terrain penalties for water/land combat
  2. **Bred for War** (100) - Cannot be diminished, always succeeds morale checks
  3. **Brutal** (200) - Inflicts 2 casualties on successful Power test
  4. **Courageous** (50) - Can succeed at failed Morale check once per battle
  5. **Eternal** (50) - Cannot be horrified, always succeeds vs undead/fiends
  6. **Feast** (50) - Immediate free attack when enemy unit diminishes
  7. **Horrify** (200) - Forces DC 15 Morale check on casualties
  8. **Martial** (100) - 2 casualties on Power check if size > target
  9. **Mindless** (100) - Cannot fail Morale checks
  10. **Regenerate** (200) - Increment casualty die on refresh
  11. **Ravenous** (50) - Increment casualty die feeding on corpses
  12. **Rock-Hurler** (250) - 2 casualties on Attack vs fortifications
  13. **Savage** (50) - Advantage on first Attack check per battle
  14. **Stalwart** (50) - Enemy magic has disadvantage on Power tests
  15. **Twisting Roots** (200) - Sap fortifications, advantage on Power checks
  16. **Undead** (50) - Green/Regular troops must pass Morale to attack

### Unit Model
- **Purpose**: Represents a military unit within a domain
- **Fields**:
  - `nome` (CharField): Unit name
  - `descricao` (TextField): Optional description
  - `domain` (ForeignKey to Domain): Parent domain
  - `ancestry` (ForeignKey to UnitAncestry): Selected ancestry with modifiers
  - `traits` (ManyToManyField to UnitTrait): Acquired traits (0 or more)
  - `criador` (ForeignKey to User): Unit creator
  - `ataque` (IntegerField ≥ 1): Base attack value
  - `poder` (IntegerField ≥ 1): Base power value
  - `defesa` (IntegerField ≥ 1): Base defense value
  - `resistencia` (IntegerField ≥ 1): Base resistance value
  - `moral` (IntegerField 0-10): Base morale value
  - `custo_ouro` (IntegerField ≥ 0): Gold recruitment cost
  - `custo_dragonshards` (IntegerField ≥ 0): Dragonshard recruitment cost
  - `quantidade` (IntegerField ≥ 1): Number of soldiers in unit
- **Methods**:
  - `get_atributos_finais()`: Returns attributes with ancestry modifiers applied
  - `pode_editar(user)`: Checks if user can edit this unit
  - `pode_deletar(user)`: Checks if user can delete this unit
  - `pode_acessar_domain(user)`: Checks if user can access parent domain

## Management Commands

### populate_ancestries.py
Populates the UnitAncestry table with all 19 ancestries and their modifier values.
**Usage**: `python manage.py populate_ancestries`

### populate_traits.py
Populates the UnitTrait table with all 16 traits and their costs/descriptions.
**Usage**: `python manage.py populate_traits`

## Forms

### UnitForm
- **Location**: `domains_warfare/forms.py`
- **Fields**: nome, descricao, ancestry, traits, ataque, poder, defesa, resistencia, moral, custo_ouro, custo_dragonshards, quantidade
- **Widgets**:
  - `traits`: CheckboxSelectMultiple for multi-select of traits
  - All numeric fields with appropriate min/max constraints
- **Auto-defaults**: 
  - ataque = 1, poder = 1, defesa = 1, resistencia = 1
  - moral = 5, quantidade = 1

## Views

### Unit Views (5 total)

1. **unit_list** `GET /domains/domain/<domain_pk>/units/`
   - Lists all units in a domain with their traits displayed
   - Shows permission buttons based on user access

2. **unit_detail** `GET /domains/domain/<domain_pk>/units/<pk>/`
   - Shows complete unit information
   - Displays base attributes and ancestry modifiers
   - Lists innate ancestry traits and acquired traits
   - Shows individual trait costs and total trait count
   - Calculates final attributes with modifiers applied

3. **unit_create** `GET/POST /domains/domain/<domain_pk>/units/create/`
   - Creates new unit in domain
   - Includes trait selection with checkboxes

4. **unit_edit** `GET/POST /domains/domain/<domain_pk>/units/<pk>/edit/`
   - Edits existing unit including trait selection
   - Requires unit edit permission

5. **unit_delete** `GET/POST /domains/domain/<domain_pk>/units/<pk>/delete/`
   - Deletes unit with confirmation
   - Requires unit delete permission

## Templates

### unit_list.html
- Grid layout showing all units in a domain
- Displays key attributes (Attack, Power, Defense, Resistance, Morale, Quantity)
- Shows both innate ancestry traits and acquired traits as pills
- Shows creator information
- Action buttons (View, Edit, Delete) with permission checks
- Empty state message when no units exist

### unit_detail.html
- Complete unit information display
- Sections for:
  - Base attributes with final values (including ancestry modifiers)
  - Ancestry information with all modifiers and innate traits
  - **Acquired Traits** with full descriptions and individual costs
  - Composition details (quantity, gold cost, dragonshard cost)
  - Trait cost breakdown showing cost per trait and total
  - Metadata (creator, creation date, update date)
- Edit and Delete action buttons based on permissions

### unit_form.html
- Form for creating/editing units
- Sections for:
  - Basic information (name, description, ancestry selection)
  - Base attributes with inline explanations
  - **Traits Adquired** section with checkboxes for trait selection
  - Recruitment costs (gold, dragonshards)
  - Composition (quantity)
- Error handling with highlighted fields
- Cancel and Submit buttons

### unit_confirm_delete.html
- Confirmation page for unit deletion
- Displays warning message
- Shows unit information being deleted
- Cancel and Delete action buttons

## Admin Interface

**Location**: `domains_warfare/admin.py`

### UnitAdmin
- List display: nome, domain, ancestry, ataque, poder, defesa, resistencia, moral, quantidade
- Filters: domain, ancestry, criado_em
- Search: nome, descricao, domain__nome
- ManyToMany field `traits` with filter_horizontal for easy selection
- Auto-sets creator to current user on creation
- Optimized queries with select_related and prefetch_related

### UnitTraitAdmin
- List display: nome (display name), custo, descricao_preview
- Filters: custo (for grouping by cost tier)
- Search: nome, descricao
- Clean fieldsets for trait management

### UnitAncestryAdmin
- List display: nome (display name), all modifiers, traits
- Search: nome, descricao, traits
- Read-only list formatting

## URL Routing

**Location**: `domains_warfare/urls.py`

```
/domains/domain/<domain_pk>/units/                    → unit_list
/domains/domain/<domain_pk>/units/<pk>/               → unit_detail
/domains/domain/<domain_pk>/units/create/             → unit_create
/domains/domain/<domain_pk>/units/<pk>/edit/          → unit_edit
/domains/domain/<domain_pk>/units/<pk>/delete/        → unit_delete
```

## Permissions System

### Unit Permissions
- **pode_editar(user)**: 
  - Allowed if: user is domain GM, unit creator, or in domain access list
- **pode_deletar(user)**:
  - Allowed if: user is domain GM or unit creator
- **pode_acessar_domain(user)**:
  - Allowed if: user is in domain's sala and has access

## Trait System Features

### Innate Traits (from Ancestry)
- 8 ancestries have innate traits that are automatically applied:
  - Bugbear: Martial
  - Dragonborn: Courageous
  - Ghoul: Eternal
  - Gnoll: Brutal
  - Hobgoblin: Martial
  - Orc: Frenzy (displayed as-is)
  - Skeleton: Mindless
  - Troll: Regenerate
  - Zombie: Mindless

### Acquired Traits
- Units can purchase additional traits at costs ranging from 50 to 250 points
- Each trait has a full description explaining its mechanics
- Traits are displayed separately from innate traits on unit detail page
- Individual and total trait costs are shown
- Multiple traits can be selected for a single unit

## Completed Features

✅ 19 Ancestries with complete attribute modifiers
✅ 16 Traits with descriptions and costs
✅ Unit CRUD operations (Create, Read, Update, Delete)
✅ Ancestry-based attribute modifications
✅ Innate traits display from ancestry
✅ Acquired traits system with multi-select
✅ Individual and total trait cost calculation
✅ Trait cost filtering in admin interface
✅ Permission-based editing/deletion
✅ Unit listing within domains with trait display
✅ Admin interface for units, traits, and ancestries
✅ Dark theme UI matching site style
✅ Comprehensive error handling
✅ Management commands for data population

## Database Migrations

- `0005_unittrait_unit_traits.py`: Creates UnitTrait model and adds traits M2M field to Unit model
- All ancestries and traits populated via management commands
- Data includes full descriptions and cost values

## Next Steps (Awaiting User Specifications)

⏳ **Unit Experience Characteristic** - Awaiting definition
⏳ **Unit Type Characteristic** - Awaiting definition (Infantry, Cavalry, Ranged, etc.)
⏳ **Unit Size Characteristic** - Awaiting definition
⏳ **Additional Features** - Awaiting further specifications

## Summary

The Unit Ancestry & Traits System is now **production-ready** with:
- Complete ancestry system with 19 types and attribute modifiers
- Comprehensive traits system with 16 available traits and point costs
- Full CRUD operations for unit management
- Intuitive UI for selecting and displaying traits
- Proper cost tracking for trait acquisition
- Integration with user permissions and domain access control

## Database Models

### UnitAncestry Model
- **Purpose**: Defines all available unit ancestries and their attribute modifiers
- **Fields**:
  - `nome` (CharField): Unique identifier for the ancestry
  - `descricao` (TextField): Optional description
  - `modificador_ataque` (IntegerField): Attack modifier (-∞ to +∞)
  - `modificador_poder` (IntegerField): Power modifier
  - `modificador_defesa` (IntegerField): Defense modifier
  - `modificador_resistencia` (IntegerField): Toughness/Resistance modifier
  - `modificador_moral` (IntegerField): Morale modifier
  - `traits` (TextField): Comma-separated list of innate traits

### Unit Model
- **Purpose**: Represents a military unit within a domain
- **Fields**:
  - `nome` (CharField): Unit name
  - `descricao` (TextField): Optional description
  - `domain` (ForeignKey to Domain): Parent domain
  - `ancestry` (ForeignKey to UnitAncestry): Selected ancestry with modifiers
  - `criador` (ForeignKey to User): Unit creator
  - `ataque` (IntegerField ≥ 1): Base attack value
  - `poder` (IntegerField ≥ 1): Base power value
  - `defesa` (IntegerField ≥ 1): Base defense value
  - `resistencia` (IntegerField ≥ 1): Base resistance value
  - `moral` (IntegerField 0-10): Base morale value
  - `custo_ouro` (IntegerField ≥ 0): Gold recruitment cost
  - `custo_dragonshards` (IntegerField ≥ 0): Dragonshard recruitment cost
  - `quantidade` (IntegerField ≥ 1): Number of soldiers in unit
- **Methods**:
  - `get_atributos_finais()`: Returns attributes with ancestry modifiers applied
  - `pode_editar(user)`: Checks if user can edit this unit
  - `pode_deletar(user)`: Checks if user can delete this unit
  - `pode_acessar_domain(user)`: Checks if user can access parent domain

## Ancestry Data (19 Total)

All 19 ancestries have been populated with their specific attribute modifiers:

| Ancestry | Attack | Power | Defense | Resistance | Morale | Traits |
|----------|--------|-------|---------|------------|--------|--------|
| Bugbear | +2 | 0 | 0 | 0 | +1 | Martial |
| Dragonborn | +2 | +2 | +1 | +1 | +1 | Courageous |
| Dwarf | +3 | +1 | +1 | +1 | +2 | — |
| Elf | +2 | 0 | +1 | +1 | 0 | — |
| Elf (Winged) | +1 | +1 | 0 | 0 | +1 | — |
| Ghoul | -1 | 0 | 0 | +1 | 0 | Eternal |
| Gnoll | +2 | 0 | 0 | 0 | 0 | Brutal |
| Gnome | +1 | -1 | +1 | 0 | 0 | — |
| Goblin | -1 | -1 | 0 | 0 | 0 | Savage |
| Hobgoblin | +2 | 0 | +1 | 0 | +1 | Martial |
| Human | +2 | 0 | 0 | 0 | 0 | — |
| Kobold | -1 | -1 | 0 | 0 | 0 | — |
| Lizardfolk | +2 | +1 | 0 | +1 | 0 | — |
| Ogre | 0 | +2 | 0 | 0 | 0 | Brutal |
| Orc | +2 | +1 | 0 | 0 | 0 | Frenzy |
| Skeleton | -2 | -1 | 0 | +2 | 0 | Mindless |
| Treant | 0 | +2 | +1 | +1 | 0 | — |
| Troll | 0 | +2 | 0 | +1 | 0 | Regenerate |
| Zombie | -2 | 0 | 0 | 0 | 0 | Mindless |

## Management Command

**Location**: `domains_warfare/management/commands/populate_ancestries.py`

Provides automated population of the UnitAncestry table with all 19 ancestries and their modifier values.

**Usage**: `python manage.py populate_ancestries`

## Forms

### UnitForm
- **Location**: `domains_warfare/forms.py`
- **Fields**: nome, descricao, ancestry, ataque, poder, defesa, resistencia, moral, custo_ouro, custo_dragonshards, quantidade
- **Auto-defaults**: 
  - ataque = 1
  - poder = 1
  - defesa = 1
  - resistencia = 1
  - moral = 5
  - quantidade = 1

## Views

### Unit Views (5 total)

1. **unit_list** `GET /domains/domain/<domain_pk>/units/`
   - Lists all units in a domain
   - Shows permission buttons (edit/delete) based on user access

2. **unit_detail** `GET /domains/domain/<domain_pk>/units/<pk>/`
   - Shows complete unit information
   - Displays base attributes and ancestry modifiers
   - Calculates final attributes with modifiers applied
   - Shows innate traits from ancestry

3. **unit_create** `GET/POST /domains/domain/<domain_pk>/units/create/`
   - Creates new unit in domain
   - Requires domain edit permission

4. **unit_edit** `GET/POST /domains/domain/<domain_pk>/units/<pk>/edit/`
   - Edits existing unit
   - Requires unit edit permission

5. **unit_delete** `GET/POST /domains/domain/<domain_pk>/units/<pk>/delete/`
   - Deletes unit with confirmation
   - Requires unit delete permission

## Templates

### unit_list.html
- Grid layout showing all units in a domain
- Displays key attributes (Attack, Power, Defense, Resistance, Morale, Quantity)
- Shows creator information
- Action buttons (View, Edit, Delete) with permission checks
- Empty state message when no units exist

### unit_detail.html
- Complete unit information display
- Sections for:
  - Base attributes with final values (including ancestry modifiers)
  - Ancestry information with all modifiers and innate traits
  - Composition details (quantity, gold cost, dragonshard cost)
  - Metadata (creator, creation date, update date)
- Edit and Delete action buttons based on permissions

### unit_form.html
- Form for creating/editing units
- Sections for:
  - Basic information (name, description, ancestry selection)
  - Base attributes with inline explanations
  - Recruitment costs
  - Composition (quantity)
- Error handling with highlighted fields
- Cancel and Submit buttons

### unit_confirm_delete.html
- Confirmation page for unit deletion
- Displays warning message
- Shows unit information being deleted
- Cancel and Delete action buttons

## Admin Interface

**Location**: `domains_warfare/admin.py`

### UnitAdmin
- List display: nome, domain, ancestry, ataque, poder, defesa, resistencia, moral, quantidade
- Filters: domain, ancestry, criado_em
- Search: nome, descricao, domain__nome
- Auto-sets creator to current user on creation
- Optimized queries with select_related and prefetch_related

### UnitAncestryAdmin
- List display: nome (display name), all modifiers, traits
- Search: nome, descricao, traits
- Read-only list formatting

## URL Routing

**Location**: `domains_warfare/urls.py`

```
/domains/domain/<domain_pk>/units/                    → unit_list
/domains/domain/<domain_pk>/units/<pk>/               → unit_detail
/domains/domain/<domain_pk>/units/create/             → unit_create
/domains/domain/<domain_pk>/units/<pk>/edit/          → unit_edit
/domains/domain/<domain_pk>/units/<pk>/delete/        → unit_delete
```

## Permissions System

### Unit Permissions
- **pode_editar(user)**: 
  - Allowed if: user is domain GM, unit creator, or in domain access list
- **pode_deletar(user)**:
  - Allowed if: user is domain GM or unit creator
- **pode_acessar_domain(user)**:
  - Allowed if: user is in domain's sala and has access

## Completed Features

✅ 19 Ancestries with complete attribute modifiers
✅ Unit CRUD operations (Create, Read, Update, Delete)
✅ Ancestry-based attribute modifications
✅ Innate traits display from ancestry
✅ Permission-based editing/deletion
✅ Unit listing within domains
✅ Admin interface for units and ancestries
✅ Dark theme UI matching site style
✅ Comprehensive error handling
✅ Management command for data population

## Pending Implementation

⏳ **Unit Experience Characteristic** - Awaiting definition
⏳ **Unit Traits System** - Full trait implementation system
⏳ **Unit Type Characteristic** - Awaiting definition (Infantry, Cavalry, Ranged, etc.)
⏳ **Unit Size Characteristic** - Awaiting definition
⏳ **Unit Templates** - Pre-built unit configurations

## Database Migrations

- `0004_unitancestry_unit_ancestry.py`: Creates UnitAncestry model and adds ancestry FK to Unit model
- Data populated via management command

## Next Steps

User should provide specifications for:
1. Unit Experience characteristic system
2. Traits system design (how traits affect units)
3. Unit Type definitions and their effects
4. Unit Size definitions and their effects
