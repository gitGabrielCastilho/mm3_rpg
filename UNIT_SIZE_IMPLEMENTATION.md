# Unit Size Implementation - Complete

## Overview
Successfully implemented the Unit Size system with cost calculation formula for the domains_warfare app.

## Changes Made

### 1. **New Model: UnitSize** (models.py)
- Created a new `UnitSize` model with the following fields:
  - `tamanho` (CharField): Stores unit size values (1d4, 1d6, 1d8, 1d10, 1d12)
  - `multiplicador_custo` (DecimalField): Cost multiplier for each size
  
- Default unit sizes created with correct cost modifiers:
  - 1d4: 0.66x
  - 1d6: 1.00x
  - 1d8: 1.33x
  - 1d10: 1.66x
  - 1d12: 2.00x

### 2. **Updated Model: Unit** (models.py)
- Added new field `size` (ForeignKey to UnitSize):
  - Allows units to specify their size category
  - Links to the cost modifier system

### 3. **Cost Calculation Formula** (models.py)
Implemented the complete `get_custos_finais()` method following the provided formula:

```
1. Sum bonuses to Attack, Power, Defense, and Toughness
2. Add double the Morale bonus
3. Multiply by the unit's Type Cost Modifier
4. Multiply by the unit's Size Cost Modifier
5. Multiply by 10
6. Add the cost of all the unit's Traits
7. Add a flat 30 points
8. Calculate Upkeep as 10% of total cost
```

**Example Calculation:**
- Unit with Attack=7, Power=7, Defense=7, Toughness=5, Morale=10 (all after modifiers)
- Bonuses: Attack=6, Power=6, Defense=6, Toughness=4, Morale=9(x2)=18
- Total Bonus Sum: 40
- Type Multiplier: 1.0, Size Multiplier (1d6): 1.0
- Cost: (40 × 1.0 × 1.0 × 10) + 0 traits + 30 = **430 Gold**
- Upkeep: 43 Gold (10%)

### 4. **Updated Form: UnitForm** (forms.py)
- Added `size` field to the form fields list
- Added widget configuration for `size` field (Select dropdown)
- Removed `custo_ouro` and `custo_dragonshards` from manual input (now calculated automatically)
- Imported `UnitSize` model

### 5. **Admin Interface** (admin.py)
- Imported `UnitSize` model
- Registered `UnitSizeAdmin` class with:
  - List display: Size and Cost Multiplier
  - Read-only: Size field (prevents editing after creation)
  - Fieldsets: Basic Info and Cost sections

### 6. **Database Migration** (0008_unitsize_unittype_unit_size_unit_unit_type.py)
- Auto-generated migration creating:
  - `UnitSize` table
  - `UnitType` table (was missing before)
  - Foreign key field `size` on `Unit` table
  - Foreign key field `unit_type` on `Unit` table

## Formula Explanation

The cost calculation takes into account:

1. **Attribute Bonuses**: Measures how much each attribute exceeds the base value of 1
2. **Morale Premium**: Morale counts double (represents cultural value)
3. **Type Multiplier**: Different unit types (Infantry, Cavalry, etc.) have different costs
4. **Size Multiplier**: Larger units (1d12) cost significantly more than smaller units (1d4)
5. **Trait Costs**: Each special ability adds to the base cost
6. **Base Cost**: Always 30 gold minimum, even for base units

## Testing

The implementation was tested with a sample unit:
- Base attributes: 3 across the board
- With Bugbear ancestry and Elite experience modifiers
- Final attributes: Attack=7, Power=7, Defense=7, Toughness=5, Morale=10
- **Calculated Cost**: 430 Gold
- **Calculated Upkeep**: 43 Gold/turn

## Files Modified

1. `domains_warfare/models.py` - Added UnitSize model, updated Unit model, implemented cost formula
2. `domains_warfare/forms.py` - Added size field to form, removed manual cost fields
3. `domains_warfare/admin.py` - Added UnitSize admin class
4. `domains_warfare/migrations/0008_*.py` - Created new migrations

## Database State

- 5 UnitSize records created with correct multipliers
- All existing units compatible (size field nullable for legacy data)
- Cost calculations ready for production use
