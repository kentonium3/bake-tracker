# Research: Supplier Slug Support

**Feature**: 050-supplier-slug-support
**Date**: 2026-01-12
**Goal**: Identify existing slug generation patterns to replicate for Supplier model

## Executive Summary

Bake-tracker has a mature slug generation system in `src/utils/slug_utils.py` used by the Ingredient model. The Material model uses a simpler inline function. For consistency and robustness, Supplier slugs should use the full `create_slug()` utility with minor adaptation for supplier-specific input (name + optional city/state).

## Key Findings

### 1. Existing Slug Utility: `src/utils/slug_utils.py`

**Primary Function**: `create_slug(name: str, session: Optional[Session] = None) -> str`

**Algorithm**:
1. Unicode normalize (NFD decomposition)
2. ASCII encode (removes accents gracefully)
3. Lowercase conversion
4. Replace whitespace/hyphens with underscores
5. Remove non-alphanumeric chars (except underscores)
6. Collapse consecutive underscores
7. Strip leading/trailing underscores
8. Check uniqueness via session (if provided), append `_1`, `_2`, etc.

**Examples**:
```python
create_slug("All-Purpose Flour")      # "all_purpose_flour"
create_slug("Confectioner's Sugar")   # "confectioners_sugar"
create_slug("100% Whole Wheat")       # "100_whole_wheat"
```

**Supporting Functions**:
- `validate_slug_format(slug: str) -> bool` - Validates format rules
- `slug_to_display_name(slug: str) -> str` - Reverses slug to display name (lossy)

### 2. Model Implementations

#### Ingredient Model (`src/models/ingredient.py`)
```python
slug = Column(String(200), nullable=True, unique=True, index=True)
```
- Uses full `create_slug()` utility
- Called during creation in `ingredient_service.create_ingredient()`
- Nullable currently (legacy data migration)

#### Material Model (`src/models/material.py`)
```python
slug = Column(String(200), nullable=False, unique=True, index=True)
```
- Uses simpler inline `slugify()` in `material_catalog_service.py`
- DOES NOT use Unicode normalization (less robust)

### 3. Import/Export Service Integration Points

#### Enhanced Import Service (`src/services/enhanced_import_service.py`)
- `_find_existing_by_slug()` - Looks up records by slug
- `_resolve_fk_by_slug()` - Resolves foreign keys by slug
- **Current Supplier handling** (line 600): Uses `name` matching, NOT slug

#### FK Resolver Service (`src/services/fk_resolver_service.py`)
- Collects existing slugs for validation
- **Current Supplier handling** (line 578): Uses `name` set, NOT slug

### 4. Conflict Resolution Pattern

Both Ingredient and Material use numeric suffix pattern:
```python
# First occurrence: "wegmans_burlington_ma"
# First conflict:   "wegmans_burlington_ma_1"  # Note: starts at _1, not _2!
# Second conflict:  "wegmans_burlington_ma_2"
```

**Important**: Current `create_slug()` in slug_utils.py starts suffixes at `_1`. The spec says `_2`, `_3`. Need to verify which is correct or if spec needs updating.

## Supplier-Specific Considerations

### Input String Construction

**Physical Suppliers** (has city/state):
```python
input_string = f"{name} {city} {state}"
# "Wegmans Burlington MA" -> "wegmans_burlington_ma"
```

**Online Suppliers** (no city/state):
```python
input_string = name
# "King Arthur Baking" -> "king_arthur_baking"
```

### Recommended Implementation

1. **Create `generate_supplier_slug()` in supplier_service.py**:
   ```python
   def generate_supplier_slug(supplier_data: dict, session: Session) -> str:
       """Generate slug for supplier based on type."""
       name = supplier_data["name"]
       supplier_type = supplier_data.get("supplier_type", "physical")

       if supplier_type == "online":
           input_string = name
       else:
           city = supplier_data.get("city", "")
           state = supplier_data.get("state", "")
           parts = [name, city, state]
           input_string = " ".join(p for p in parts if p)

       return create_slug_for_model(input_string, Supplier, session)
   ```

2. **Generalize `create_slug()` or create model-agnostic version**:
   - Current `create_slug()` hardcodes `Ingredient` import
   - Need version that accepts model class parameter
   - Or create `create_slug_for_supplier()` variant

### Files Requiring Modification

| File | Change |
|------|--------|
| `src/models/supplier.py` | Add `slug` field |
| `src/services/supplier_service.py` | Add slug generation |
| `src/services/enhanced_import_service.py` | Update supplier matching to use slug |
| `src/services/fk_resolver_service.py` | Update supplier lookup to use slug |
| `src/utils/slug_utils.py` | Add model-agnostic variant (optional) |
| `test_data/suppliers.json` | Add slug field to all records |

## Decisions Needed

1. **Suffix numbering**: Start at `_1` (current code) or `_2` (spec says)?
   - Recommendation: Follow existing code pattern (`_1`) and update spec

2. **Utility reuse**: Generalize `create_slug()` or create supplier-specific copy?
   - Recommendation: Add optional `model_class` parameter to existing utility

3. **Nullable vs Required**: Should supplier slug be nullable initially?
   - Recommendation: Non-nullable - all existing suppliers get slugs in migration

## References

- `src/utils/slug_utils.py:30-143` - Main slug generation logic
- `src/services/ingredient_service.py:194` - Example slug usage in create
- `src/services/enhanced_import_service.py:600` - Current supplier FK resolution
- `docs/design/F050_supplier_slug_support.md` - Original feature design doc
