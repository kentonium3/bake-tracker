# Data Model: Recipe Slug Support

**Feature**: 080-recipe-slug-support
**Date**: 2026-01-28

## Schema Changes

### Recipe Model Additions

```python
# File: src/models/recipe.py

class Recipe(BaseModel):
    __tablename__ = "recipes"

    # Existing fields...

    # NEW: Portable identifier for data import/export
    slug = Column(
        String(200),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique human-readable identifier for export/import portability"
    )

    # NEW: Previous slug for one-rename grace period
    previous_slug = Column(
        String(200),
        nullable=True,
        index=True,
        comment="Previous slug retained after rename for import compatibility"
    )
```

### Index Additions

```python
# In Recipe model __table_args__
Index("idx_recipe_slug", "slug", unique=True),
Index("idx_recipe_previous_slug", "previous_slug"),
```

### Event Listener

```python
# File: src/models/recipe.py (at module level)

from sqlalchemy import event

@event.listens_for(Recipe, "before_insert")
def generate_recipe_slug(mapper, connection, target):
    """Auto-generate slug before insert if not provided."""
    if not target.slug:
        # Import here to avoid circular dependency
        from src.services.recipe_service import RecipeService
        target.slug = RecipeService._generate_slug(target.name)
```

---

## Entity Relationships (Unchanged)

Recipe slug does not affect existing FK relationships. The following entities reference Recipe via `recipe_id`:

| Entity | FK Field | Relationship |
|--------|----------|--------------|
| FinishedUnit | `recipe_id` | Many-to-One |
| ProductionRun | `recipe_id` | Many-to-One |
| EventProductionTarget | `recipe_id` | Many-to-One |
| RecipeComponent | `component_recipe_id` | Many-to-One (self-referential) |
| RecipeSnapshot | `recipe_id` | Many-to-One |

---

## Export Schema Changes

### recipes.json

```json
{
  "uuid": "...",
  "slug": "chocolate-chip-cookies",
  "previous_slug": null,
  "name": "Chocolate Chip Cookies",
  "category": "Cookies",
  "source": "Family Recipe",
  "estimated_time_minutes": 45,
  "notes": null,
  "is_archived": false,
  "is_production_ready": true,
  "ingredients": [...],
  "components": [
    {
      "component_recipe_slug": "cookie-dough-base",
      "component_recipe_name": "Cookie Dough Base",
      "quantity": 1.0,
      "unit": "batch"
    }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

### finished_units.json

```json
{
  "uuid": "...",
  "slug": "chocolate-chip-cookies-dozen",
  "display_name": "Chocolate Chip Cookies (Dozen)",
  "recipe_slug": "chocolate-chip-cookies",
  "recipe_name": "Chocolate Chip Cookies",
  "yield_type_slug": "cookies",
  "yield_type_name": "Cookies",
  "default_yield_quantity": 12,
  "is_archived": false,
  "created_at": "...",
  "updated_at": "..."
}
```

### event_production_targets.json

```json
{
  "uuid": "...",
  "recipe_slug": "chocolate-chip-cookies",
  "recipe_name": "Chocolate Chip Cookies",
  "event_name": "Christmas 2025",
  "target_quantity": 48,
  "target_batches": 4,
  "notes": null,
  "created_at": "...",
  "updated_at": "..."
}
```

### production_runs.json

```json
{
  "uuid": "...",
  "recipe_slug": "chocolate-chip-cookies",
  "recipe_name": "Chocolate Chip Cookies",
  "event_name": "Christmas 2025",
  "quantity_planned": 12,
  "quantity_actual": 11,
  "batch_multiplier": 1.0,
  "status": "completed",
  "notes": "One cookie broken",
  "produced_at": "...",
  "created_at": "...",
  "updated_at": "..."
}
```

---

## Import Resolution Logic

### Recipe Import

```
Input: { "slug": "...", "name": "..." }

Resolution:
1. If slug provided and exists in DB → UPDATE existing recipe
2. If slug provided but not exists → CREATE with provided slug
3. If no slug provided → GENERATE slug from name, check collision, CREATE
```

### FK Import (FinishedUnit, ProductionRun, EventProductionTarget)

```
Input: { "recipe_slug": "...", "recipe_name": "..." }

Resolution Order:
1. recipe_slug matches Recipe.slug → Use that recipe_id
2. recipe_slug matches Recipe.previous_slug → Use that recipe_id (log fallback)
3. recipe_name matches Recipe.name → Use that recipe_id (log legacy fallback)
4. No match → Log error, skip record
```

### RecipeComponent Import

```
Input: { "component_recipe_slug": "...", "component_recipe_name": "..." }

Resolution Order:
1. component_recipe_slug matches Recipe.slug → Use that recipe_id
2. component_recipe_slug matches Recipe.previous_slug → Use that recipe_id
3. component_recipe_name matches Recipe.name → Use that recipe_id
4. No match → Log error, skip component
```

---

## Slug Generation Rules

### Format

- Lowercase
- Spaces replaced with hyphens
- Non-alphanumeric characters removed (except hyphens)
- Max 200 characters
- No leading/trailing hyphens

### Examples

| Recipe Name | Generated Slug |
|-------------|----------------|
| Chocolate Chip Cookies | `chocolate-chip-cookies` |
| Grandma's Apple Pie | `grandmas-apple-pie` |
| Cookies & Cream | `cookies-cream` |
| Test Recipe 2025! | `test-recipe-2025` |
| Crme Brle | `creme-brulee` |

### Collision Handling

If base slug exists, append numeric suffix:

| Existing Slugs | New Recipe Name | Generated Slug |
|----------------|-----------------|----------------|
| `chocolate-chip-cookies` | Chocolate Chip Cookies | `chocolate-chip-cookies-2` |
| `chocolate-chip-cookies`, `chocolate-chip-cookies-2` | Chocolate Chip Cookies | `chocolate-chip-cookies-3` |

---

## Rename Behavior

When recipe name changes:

1. Store current `slug` in `previous_slug`
2. Generate new `slug` from new name
3. Check for collision with new slug
4. If collision, append suffix to new slug
5. Previous `previous_slug` value is discarded (one-rename grace period)

### Example

```
Initial state:
  name: "Chocolate Cookies"
  slug: "chocolate-cookies"
  previous_slug: null

After rename to "Chocolate Chip Cookies":
  name: "Chocolate Chip Cookies"
  slug: "chocolate-chip-cookies"
  previous_slug: "chocolate-cookies"

After second rename to "Best Chocolate Chip Cookies":
  name: "Best Chocolate Chip Cookies"
  slug: "best-chocolate-chip-cookies"
  previous_slug: "chocolate-chip-cookies"  # Previous "chocolate-cookies" discarded
```

---

## Validation Rules

| Field | Rule |
|-------|------|
| `slug` | Required, unique, max 200 chars, alphanumeric + hyphens only |
| `previous_slug` | Optional, max 200 chars, indexed for lookup performance |
| `name` | Required (existing), used for slug generation |

---

## Migration Notes

**Per Constitution Principle VI (Schema Change Strategy):**

This feature does NOT use migration scripts. Instead:

1. Export all data using current export service
2. Update Recipe model with new columns
3. Delete database and recreate with new schema
4. Import data - import service will generate slugs for recipes without them

The import service handles slug generation automatically for legacy exports that don't include slug fields.
