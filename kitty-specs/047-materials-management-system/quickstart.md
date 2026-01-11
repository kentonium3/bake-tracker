# Quickstart: Materials Management System

**Feature**: 047-materials-management-system
**Date**: 2026-01-10

## Overview

This guide helps developers get started with implementing the Materials Management System. The system parallels the existing Ingredients system, so familiarity with that codebase is helpful.

## Prerequisites

- Python 3.10+ with virtual environment activated
- All existing tests passing: `pytest src/tests -v`
- Understanding of SQLAlchemy 2.x patterns used in this codebase

## Key Patterns to Follow

### 1. BaseModel Inheritance

All new models inherit from `BaseModel`:

```python
from .base import BaseModel

class MaterialCategory(BaseModel):
    __tablename__ = "material_categories"
    # ... fields
```

### 2. Session Parameter Pattern

All service functions accept optional `session` parameter:

```python
def create_category(
    name: str,
    session: Session | None = None
) -> MaterialCategory:
    if session is not None:
        return _create_category_impl(name, session)
    with session_scope() as session:
        return _create_category_impl(name, session)
```

### 3. Slug Generation

Use `slugify` from existing utils:

```python
from src.utils.string_utils import slugify

slug = slug or slugify(name)
```

### 4. Unit Conversion

Use existing `unit_converter` service:

```python
from src.services.unit_converter import convert_to_base_units

base_units = convert_to_base_units(
    quantity=100,
    from_unit="feet",
    target_base="linear_inches"
)  # Returns 1200
```

## Implementation Order

### Phase 1: Models (Parallelizable)

Create in this order (or parallel):

1. `src/models/material_category.py`
2. `src/models/material_subcategory.py`
3. `src/models/material.py`
4. `src/models/material_product.py`
5. `src/models/material_unit.py`
6. `src/models/material_purchase.py`
7. `src/models/material_consumption.py`

Update `src/models/__init__.py` to export all new models.

### Phase 2: Services (After Models)

1. `src/services/material_catalog_service.py` - CRUD for hierarchy
2. `src/services/material_purchase_service.py` - Purchases and inventory
3. `src/services/material_unit_service.py` - Unit calculations
4. `src/services/material_consumption_service.py` - Assembly consumption

### Phase 3: Composition Integration

Extend `src/models/composition.py`:
- Add `material_unit_id` and `material_id` columns
- Update XOR constraint to 5-way
- Add new relationships

### Phase 4: Tests

Write tests in parallel with services:

```
src/tests/
├── test_material_catalog_service.py
├── test_material_purchase_service.py
├── test_material_unit_service.py
└── test_material_consumption_service.py
```

### Phase 5: UI (After Services)

Create `src/ui/materials_tab.py` following the Ingredients tab pattern.

## Quick Reference

### Unit Types

| base_unit_type | Example Materials | Conversion |
|----------------|-------------------|------------|
| each | Boxes, bags, tags | No conversion |
| linear_inches | Ribbon, tape | feet→inches, yards→inches |
| square_inches | Tissue paper, labels | sq_feet→sq_inches |

### Key Relationships

```
MaterialCategory (1) ──< MaterialSubcategory (1) ──< Material
                                                        │
                                        ┌───────────────┴───────────────┐
                                        ▼                               ▼
                                  MaterialProduct                 MaterialUnit
                                        │
                                        ▼
                                  MaterialPurchase
```

### Testing Commands

```bash
# Run all tests
pytest src/tests -v

# Run with coverage
pytest src/tests -v --cov=src

# Run specific test file
pytest src/tests/test_material_catalog_service.py -v

# Run single test
pytest src/tests -v -k "test_create_category"
```

## Common Gotchas

### 1. Weighted Average Cost

Remember: weighted average is recalculated on each purchase, not on consumption.

```python
new_avg = (old_qty * old_avg + new_qty * new_cost) / (old_qty + new_qty)
```

### 2. Composition XOR Constraint

The composition must have exactly ONE of:
- finished_unit_id
- finished_good_id
- packaging_product_id
- material_unit_id (NEW)
- material_id (NEW)

### 3. Immutable Records

These records have no `updated_at` and should never be modified:
- MaterialPurchase
- MaterialConsumption

### 4. Denormalized Snapshots

MaterialConsumption stores names at time of consumption:
- Don't rely on FKs for historical display
- Always use snapshot fields for UI

## Files to Reference

| Purpose | File |
|---------|------|
| Base model pattern | `src/models/base.py` |
| Hierarchy pattern | `src/models/ingredient.py` |
| Purchase pattern | `src/models/purchase.py` |
| Consumption pattern | `src/models/production_consumption.py` |
| Composition pattern | `src/models/composition.py` |
| Session management | `CLAUDE.md` (Session Management section) |

## Getting Help

- Check `docs/design/` for architectural decisions
- Review existing tests in `src/tests/` for patterns
- Consult `CLAUDE.md` for session management rules
