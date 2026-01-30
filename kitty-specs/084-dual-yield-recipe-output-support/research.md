# Research: Dual-Yield Recipe Output Support

**Feature**: 084-dual-yield-recipe-output-support
**Date**: 2026-01-29
**Status**: Complete

## Research Questions

### Q1: Current FinishedUnit Schema Structure

**Decision**: Add `yield_type` field to existing schema without restructuring

**Findings**:

The current FinishedUnit model (`src/models/finished_unit.py:49-153`) has:

```python
class FinishedUnit(BaseModel):
    slug = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)  # User-facing name
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)

    # Yield configuration
    yield_mode = Column(Enum(YieldMode), nullable=False, default=YieldMode.DISCRETE_COUNT)

    # For DISCRETE_COUNT mode
    items_per_batch = Column(Integer, nullable=True)
    item_unit = Column(String(50), nullable=True)  # "cookie", "cake", "slice"

    # For BATCH_PORTION mode
    batch_percentage = Column(Numeric(5,2), nullable=True)
    portion_description = Column(String(200), nullable=True)

    inventory_count = Column(Integer, nullable=False, default=0)
    category = Column(String(100), nullable=True)
```

**Key insight**: The `item_unit` field already serves the purpose that the functional spec called `unit_description`. No renaming needed.

**Rationale**: Adding a single `yield_type` field is the minimal change needed. The existing `yield_mode` (DISCRETE_COUNT vs BATCH_PORTION) is orthogonal to `yield_type` (EA vs SERVING).

---

### Q2: Constraint Patterns in Codebase

**Decision**: Follow existing CHECK and UNIQUE constraint patterns

**Findings** (`src/models/finished_unit.py:131-152`, `src/models/recipe.py:500-516`):

```python
# CHECK constraint pattern (finished_unit.py)
CheckConstraint("inventory_count >= 0", name="ck_finished_unit_inventory_non_negative")
CheckConstraint(
    "items_per_batch IS NULL OR items_per_batch > 0",
    name="ck_finished_unit_items_per_batch_positive",
)

# UNIQUE constraint pattern (recipe.py)
UniqueConstraint(
    "recipe_id",
    "component_recipe_id",
    name="uq_recipe_component_recipe_component",
)
```

**Naming convention**:
- CHECK: `ck_<table>_<description>`
- UNIQUE: `uq_<table>_<columns>`
- Index: `idx_<table>_<columns>`

**For F084**:
```python
CheckConstraint(
    "yield_type IN ('EA', 'SERVING')",
    name="ck_finished_unit_yield_type_valid"
)
UniqueConstraint(
    "recipe_id", "item_unit", "yield_type",
    name="uq_finished_unit_recipe_item_unit_yield_type"
)
```

---

### Q3: Export/Import Patterns

**Decision**: Add yield_type to existing finished_units export structure

**Findings** (`src/services/coordinated_export_service.py:738-769`):

Current export structure:
```json
{
  "slug": "cookies-24-pack",
  "display_name": "Cookies",
  "recipe_slug": "sugar-cookies",
  "yield_mode": "discrete_count",
  "items_per_batch": 24,
  "item_unit": "cookie",
  "inventory_count": 42
}
```

**Import validation pattern** (`coordinated_export_service.py:1613-1657`):
- Validates required fields (slug, display_name, recipe_slug)
- Converts enum strings to Python enums with try/except
- Provides sensible defaults for invalid values

**For F084**:
```json
{
  "slug": "cookies-24-pack",
  "display_name": "Cookies",
  "recipe_slug": "sugar-cookies",
  "yield_mode": "discrete_count",
  "yield_type": "SERVING",  // NEW FIELD
  "items_per_batch": 24,
  "item_unit": "cookie",
  "inventory_count": 42
}
```

Import should:
- Accept `yield_type` field
- Validate value is 'EA' or 'SERVING'
- Default to 'SERVING' if missing (backward compatibility)

---

### Q4: Recipe Service Validation Patterns

**Decision**: Add yield_type validation following existing patterns

**Findings** (`src/services/recipe_service.py:1311-1381`):

```python
def validate_recipe_has_finished_unit(recipe_id: int, session=None) -> List[str]:
    """Returns List[str] of error messages (empty if valid)."""
    # Pattern: Query, validate, return error list
```

**Validation approach**:
- Service functions accept optional `session=None` parameter
- Return `List[str]` of error messages
- Use `ImportResult` class for import error tracking

---

### Q5: UI Component Patterns

**Decision**: Add yield_type dropdown to existing YieldTypeRow component

**Findings** (`src/ui/forms/recipe_form.py:392-501`):

Current YieldTypeRow has 4 columns:
```
| Name (display_name) | Unit (item_unit) | Qty (items_per_batch) | Remove |
```

Grid configuration:
```python
self.grid_columnconfigure(0, weight=3)  # Name (wider)
self.grid_columnconfigure(1, weight=1)  # Unit
self.grid_columnconfigure(2, weight=1)  # Quantity
self.grid_columnconfigure(3, weight=0)  # Remove button
```

**For F084**: Add yield_type dropdown between Unit and Qty:
```
| Name | Unit | Type (EA/SERVING) | Qty | Remove |
```

Widget pattern for dropdowns (`CTkOptionMenu`):
```python
self.yield_type_dropdown = ctk.CTkOptionMenu(
    self,
    values=["SERVING", "EA"],
    width=100,
)
```

---

### Q6: Migration Strategy

**Decision**: Use constitutional export → schema change → import workflow

**Findings** (Constitution Principle VI):
- Schema changes handled via export → reset → import cycle
- No migration scripts required
- Transform JSON to match new schema if needed

**Migration steps**:
1. Export all data with current schema
2. Transform finished_units JSON: add `yield_type: "SERVING"` to each record
3. Update model with new field and constraints
4. Reset database
5. Import transformed data

---

## Alternatives Considered

### Alternative A: Create YieldType Enum in Python

**Rejected because**: String values with CHECK constraint are simpler and match existing `yield_mode` pattern (which does use Enum but for different purposes). Adding another Enum increases complexity without benefit.

### Alternative B: Rename item_unit to unit_description

**Rejected because**: The field already serves the correct purpose. Renaming would require updating all references throughout the codebase for no functional benefit.

### Alternative C: Store yield_type on Recipe instead of FinishedUnit

**Rejected because**: A single recipe can have multiple FinishedUnits with different yield types (e.g., "small cake" with both EA=1 and SERVING=4). The yield_type must be per-FinishedUnit.

---

## Key Files Reference

| Purpose | File | Key Lines |
|---------|------|-----------|
| FinishedUnit Model | `src/models/finished_unit.py` | 49-153 |
| Recipe Relationship | `src/models/recipe.py` | 154-162 |
| Recipe Service Validation | `src/services/recipe_service.py` | 1311-1381 |
| Export Service | `src/services/coordinated_export_service.py` | 738-769 |
| Import Service | `src/services/coordinated_export_service.py` | 1613-1657 |
| Recipe Form UI | `src/ui/forms/recipe_form.py` | 392-501 |
| Recipes Tab | `src/ui/recipes_tab.py` | 343-414, 504-556 |
