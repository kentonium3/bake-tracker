---
work_package_id: "WP03"
subtasks: ["T020", "T021", "T022", "T023", "T024", "T025", "T026", "T027", "T028", "T029", "T030", "T031", "T032", "T033", "T034", "T035", "T036", "T037"]
title: "VariantService Implementation"
phase: "Phase 2 - Service Implementation"
lane: "done"
assignee: "Claude Code"
agent: "Claude Code"
shell_pid: ""
history:
  - timestamp: "2025-11-09T03:08:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-11-09T07:58:47Z"
    lane: "done"
    agent: "Claude Code"
    shell_pid: ""
    action: "Work package completed - all tasks implemented and integration tests passing"
---

# Work Package Prompt: WP03 – VariantService Implementation

## Objectives & Success Criteria

Implement complete VariantService with 9 functions including critical preferred variant toggle logic using TDD.

**Success Criteria**:
- All 9 service functions pass unit tests
- Preferred variant toggle works atomically (only one variant preferred per ingredient)
- Display name auto-calculated correctly
- Dependency checking prevents orphaned variants
- UPC search works for barcode lookups

## Context & Constraints

**Contract**: `kitty-specs/002-service-layer-for/contracts/variant_service.md`
**Data Model**: `kitty-specs/002-service-layer-for/data-model.md` - Variant entity
**Dependencies**: WP01 (infrastructure), WP02 (IngredientService for FK validation)

**Key Implementation Notes**:
- Display name: `@property` returning `f"{brand} - {package_size}"` or just `brand`
- Preferred toggle: UPDATE all variants for ingredient to False, then SET one to True (atomic)
- Dependency checking: COUNT pantry_items, purchases

## Subtasks (TDD Pattern)

### T020-T021: create_variant()

**Tests**:
- Successful creation with all fields
- Auto-calculation of display_name
- Preferred=True clears other variants
- ValidationError for missing required fields
- IngredientNotFoundBySlug for invalid ingredient_slug

**Implementation**:
```python
from decimal import Decimal
from typing import Dict, Any
from src.models import Variant
from src.services import session_scope, ValidationError, IngredientNotFoundBySlug
from src.services.ingredient_service import get_ingredient

def create_variant(ingredient_slug: str, variant_data: Dict[str, Any]) -> Variant:
    """Create a new variant for an ingredient."""
    # Validate ingredient exists
    ingredient = get_ingredient(ingredient_slug)

    # Validate variant data
    from src.utils.validators import validate_variant_data
    validate_variant_data(variant_data, ingredient_slug)

    with session_scope() as session:
        # If preferred=True, clear all other variants
        if variant_data.get('preferred', False):
            session.query(Variant).filter_by(ingredient_slug=ingredient_slug).update({'preferred': False})

        variant = Variant(
            ingredient_slug=ingredient_slug,
            brand=variant_data['brand'],
            package_size=variant_data.get('package_size'),
            purchase_unit=variant_data['purchase_unit'],
            purchase_quantity=variant_data['purchase_quantity'],
            upc=variant_data.get('upc'),
            gtin=variant_data.get('gtin'),
            supplier=variant_data.get('supplier'),
            preferred=variant_data.get('preferred', False),
            net_content_value=variant_data.get('net_content_value'),
            net_content_uom=variant_data.get('net_content_uom')
        )
        session.add(variant)
        session.flush()
        return variant
```

### T022-T023: get_variant()

**Tests**: Basic retrieval, VariantNotFound exception, eager-loaded ingredient relationship

**Implementation**:
```python
from sqlalchemy.orm import joinedload

def get_variant(variant_id: int) -> Variant:
    """Retrieve variant by ID."""
    with session_scope() as session:
        variant = session.query(Variant).options(
            joinedload(Variant.ingredient)
        ).filter_by(id=variant_id).first()

        if not variant:
            raise VariantNotFound(variant_id)
        return variant
```

### T024-T025: get_variants_for_ingredient()

**Tests**: Sorting (preferred first, then by brand), empty list for no variants

**Implementation**:
```python
from typing import List

def get_variants_for_ingredient(ingredient_slug: str) -> List[Variant]:
    """Retrieve all variants for ingredient, preferred first."""
    # Validate ingredient exists
    get_ingredient(ingredient_slug)

    with session_scope() as session:
        return session.query(Variant).filter_by(
            ingredient_slug=ingredient_slug
        ).order_by(
            Variant.preferred.desc(),
            Variant.brand
        ).all()
```

### T026-T027: set_preferred_variant() ⚠️ CRITICAL

**Tests**:
- Atomic toggle (preferred=True, all others False)
- Multiple calls to set_preferred_variant
- VariantNotFound for invalid ID

**Implementation**:
```python
def set_preferred_variant(variant_id: int) -> Variant:
    """Mark variant as preferred, clearing all others for same ingredient."""
    variant = get_variant(variant_id)

    with session_scope() as session:
        # Atomic: UPDATE all to False, then SET one to True
        session.query(Variant).filter_by(
            ingredient_slug=variant.ingredient_slug
        ).update({'preferred': False})

        variant_to_update = session.query(Variant).get(variant_id)
        variant_to_update.preferred = True

        return variant_to_update
```

### T028-T029: update_variant()

**Tests**: Partial update, validation, immutable ingredient_slug

**Implementation**: Similar to update_ingredient, prevent ingredient_slug change

### T030-T031: delete_variant()

**Tests**: Success (no deps), VariantInUse (with deps), dependency details in exception

**Implementation**: Use check_variant_dependencies(), raise VariantInUse if any count > 0

### T032-T033: check_variant_dependencies()

**Tests**: Count pantry_items, purchases

**Implementation**:
```python
def check_variant_dependencies(variant_id: int) -> Dict[str, int]:
    """Check if variant is referenced by other entities."""
    from src.models import PantryItem, Purchase

    variant = get_variant(variant_id)

    with session_scope() as session:
        pantry_count = session.query(PantryItem).filter_by(variant_id=variant_id).count()
        purchase_count = session.query(Purchase).filter_by(variant_id=variant_id).count()

        return {
            "pantry_items": pantry_count,
            "purchases": purchase_count
        }
```

### T034-T035: search_variants_by_upc()

**Tests**: Exact match, multiple variants with same UPC, empty list for no match

**Implementation**:
```python
def search_variants_by_upc(upc: str) -> List[Variant]:
    """Search variants by UPC code (exact match)."""
    with session_scope() as session:
        return session.query(Variant).filter_by(upc=upc).all()
```

### T036-T037: get_preferred_variant()

**Tests**: Returns preferred variant, None if no preferred set

**Implementation**:
```python
from typing import Optional

def get_preferred_variant(ingredient_slug: str) -> Optional[Variant]:
    """Get the preferred variant for an ingredient."""
    get_ingredient(ingredient_slug)  # Validate exists

    with session_scope() as session:
        return session.query(Variant).filter_by(
            ingredient_slug=ingredient_slug,
            preferred=True
        ).first()
```

## Test Strategy

**Test file**: `src/tests/test_variant_service.py`

**Critical test**: Preferred variant toggle atomicity:
```python
def test_set_preferred_variant_clears_others():
    """Test only one variant is preferred per ingredient."""
    # Create ingredient
    # Create 3 variants
    # Set variant 1 preferred
    # Assert variant 1.preferred=True, variant 2&3.preferred=False
    # Set variant 2 preferred
    # Assert variant 2.preferred=True, variant 1&3.preferred=False
```

**Run tests**: `pytest src/tests/test_variant_service.py -v --cov=src/services/variant_service`

## Definition of Done Checklist

- [x] All 18 subtasks completed (9 test + 9 implementation)
- [x] `src/services/variant_service.py` created with 9 functions
- [x] Preferred variant toggle works atomically (tested)
- [x] Display name property works correctly
- [x] All tests pass with >70% coverage
- [x] No circular imports
- [x] All functions use session_scope()

## Activity Log

- 2025-11-09T03:08:51Z – system – lane=planned – Prompt created.
- 2025-11-09T08:02:39Z – Claude Code – lane=done – Work package completed. All tasks implemented and integration tests passing.

