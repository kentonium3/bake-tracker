# Research: Recipe Slug Support

**Feature**: 080-recipe-slug-support
**Date**: 2026-01-28

## Research Questions

1. What slug patterns exist in the codebase?
2. How are slugs generated and collision handled?
3. How do exports include slugs?
4. How do imports resolve via slug?
5. What FK entities reference Recipe?

---

## 1. Existing Slug Column Patterns

### Model Column Definitions

| Model | Column Definition | Length | Nullable | Unique | Index |
|-------|------------------|--------|----------|--------|-------|
| Supplier | `slug = Column(String(100), nullable=False, unique=True, index=True)` | 100 | No | Yes | Yes |
| Ingredient | `slug = Column(String(200), nullable=True, unique=True, index=True)` | 200 | Yes* | Yes | Yes |
| Product | `slug = Column(String(200), nullable=True, unique=True, index=True)` | 200 | Yes* | Yes | Yes |
| FinishedUnit | `slug = Column(String(200), nullable=False, unique=True, index=True)` | 200 | No | Yes | Yes |
| FinishedGood | `slug = Column(String(200), nullable=False, unique=True, index=True)` | 200 | No | Yes | Yes |

*Note: Ingredient/Product have nullable=True due to migration from older schema

### Decision for Recipe

**Copy**: FinishedUnit pattern
```python
slug = Column(String(200), nullable=False, unique=True, index=True)
previous_slug = Column(String(200), nullable=True, index=True)  # NEW: for rename grace period
```

**Rationale**: 200 chars provides flexibility; non-nullable enforces data integrity; unique constraint prevents collision.

---

## 2. Slug Generation Patterns

### Pattern A: Event Listener (Supplier)

Location: `src/models/supplier.py:183-189`

```python
@event.listens_for(Supplier, "before_insert")
def generate_supplier_slug(mapper, connection, target):
    """Auto-generate slug before insert if not provided."""
    if not target.slug:
        target.slug = _generate_slug_from_name(
            target.name, target.supplier_type, target.city, target.state
        )
```

### Pattern B: Service Method (FinishedUnit)

Location: `src/services/finished_unit_service.py:629-679`

```python
@staticmethod
def _generate_slug(display_name: str) -> str:
    """Generate URL-safe slug from display name."""
    if not display_name:
        return "unknown-item"

    # Normalize unicode characters
    slug = unicodedata.normalize("NFKD", display_name)

    # Convert to lowercase and replace spaces/punctuation with hyphens
    slug = re.sub(r"[^\w\s-]", "", slug).strip().lower()
    slug = re.sub(r"[\s_-]+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Ensure not empty
    if not slug:
        return "unknown-item"

    # Limit length
    if len(slug) > 90:
        slug = slug[:90].rstrip("-")

    return slug

@staticmethod
def _generate_unique_slug(
    display_name: str, session: Session, exclude_id: Optional[int] = None
) -> str:
    """Generate unique slug, adding suffix if needed."""
    base_slug = FinishedUnitService._generate_slug(display_name)

    max_attempts = 1000
    for attempt in range(max_attempts):
        if attempt == 0:
            candidate_slug = base_slug
        else:
            candidate_slug = f"{base_slug}-{attempt + 1}"

        query = session.query(FinishedUnit).filter(FinishedUnit.slug == candidate_slug)
        if exclude_id:
            query = query.filter(FinishedUnit.id != exclude_id)

        existing = query.first()
        if not existing:
            return candidate_slug

    raise ValidationError(f"Unable to generate unique slug after {max_attempts} attempts")
```

### Decision for Recipe

**Use hybrid approach:**
1. Event listener for auto-generation on insert (like Supplier)
2. Service methods for collision handling and rename operations (like FinishedUnit)

**Slug format**: Hyphens (not underscores) - more readable, matches FinishedUnit/FinishedGood pattern

---

## 3. Export Patterns

### Current Recipe Export

Location: `src/services/coordinated_export_service.py:343-360`

```python
records.append({
    "uuid": str(r.uuid) if r.uuid else None,
    "name": r.name,  # Human-readable
    "category": r.category,
    # ... other fields
    "ingredients": ingredients,  # Uses ingredient_slug
    "components": components,    # Uses component_recipe_name (TO BE UPDATED)
})
```

### FK Entity Exports (Current)

| Entity | Current Export | Line |
|--------|---------------|------|
| FinishedUnit | `"recipe_name": fu.recipe.name` | 677 |
| EventProductionTarget | `"recipe_name": pt.recipe.name` | 711 |
| ProductionRun | `"recipe_name": r.recipe.name` | 765 |
| RecipeComponent | `"component_recipe_name": rc.component_recipe.name` | 332 |

### Decision: Dual-Field Export

All exports will include BOTH name and slug:

```python
# Recipe export
"slug": r.slug,
"previous_slug": r.previous_slug,
"name": r.name,  # Keep for backward compatibility

# FK entity exports
"recipe_slug": entity.recipe.slug if entity.recipe else None,
"recipe_name": entity.recipe.name if entity.recipe else None,  # Keep for backward compatibility

# Component export
"component_recipe_slug": rc.component_recipe.slug if rc.component_recipe else None,
"component_recipe_name": rc.component_recipe.name if rc.component_recipe else None,
```

---

## 4. Import Patterns

### Current Recipe Import

Location: `src/services/catalog_import_service.py:1079-1160`

```python
# Build name lookup
existing_recipes = {
    row.name: {"id": row.id} for row in session.query(Recipe.name, Recipe.id).all()
}

for item in data:
    recipe_name = item.get("name", "")
    if recipe_name in existing_recipes:
        # Handle collision
        continue

    recipe = Recipe(
        name=recipe_name,
        # ... other fields
    )
```

### Current FK Resolution (FinishedUnit)

Location: `src/services/coordinated_export_service.py:1354-1361`

```python
recipe_name = record.get("recipe_name")
recipe = session.query(Recipe).filter(Recipe.name == recipe_name).first()
if not recipe:
    logger.warning(f"Recipe '{recipe_name}' not found, skipping")
    skipped += 1
    continue
```

### Decision: Slug-First Resolution with Fallback

```python
# Build lookups
existing_by_slug = {row.slug: row.id for row in session.query(Recipe.slug, Recipe.id).filter(Recipe.slug.isnot(None)).all()}
existing_by_previous_slug = {row.previous_slug: row.id for row in session.query(Recipe.previous_slug, Recipe.id).filter(Recipe.previous_slug.isnot(None)).all()}
existing_by_name = {row.name: row.id for row in session.query(Recipe.name, Recipe.id).all()}

# Resolution order
recipe_slug = record.get("recipe_slug")
recipe_name = record.get("recipe_name")

recipe_id = None
resolution_method = None

if recipe_slug and recipe_slug in existing_by_slug:
    recipe_id = existing_by_slug[recipe_slug]
    resolution_method = "slug"
elif recipe_slug and recipe_slug in existing_by_previous_slug:
    recipe_id = existing_by_previous_slug[recipe_slug]
    resolution_method = "previous_slug"
    logger.info(f"Resolved recipe '{recipe_slug}' via previous_slug fallback")
elif recipe_name and recipe_name in existing_by_name:
    recipe_id = existing_by_name[recipe_name]
    resolution_method = "name"
    logger.info(f"Resolved recipe '{recipe_name}' via name fallback (legacy import)")
else:
    logger.error(f"Recipe not found: slug='{recipe_slug}', name='{recipe_name}'")
    # Skip or error
```

---

## 5. FK Entities Referencing Recipe

| Entity | FK Field | Export File | Import Service |
|--------|----------|-------------|----------------|
| FinishedUnit | `recipe_id` | `finished_units.json` | `coordinated_export_service._import_finished_units()` |
| EventProductionTarget | `recipe_id` | `event_production_targets.json` | `coordinated_export_service._import_event_production_targets()` |
| ProductionRun | `recipe_id` | `production_runs.json` | `coordinated_export_service._import_production_runs()` |
| RecipeComponent | `component_recipe_id` | Embedded in `recipes.json` | `catalog_import_service._import_recipes()` |

---

## Summary of Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Column length | 200 chars | Matches Product/Ingredient; allows long names |
| Nullable | No (slug), Yes (previous_slug) | slug required; previous_slug optional |
| Separator | Hyphens | Matches FinishedUnit; more readable than underscores |
| Collision suffix | `-2`, `-3`, etc. | Matches existing pattern |
| Auto-generation | Event listener | Ensures slug always populated |
| Export format | Dual-field (slug + name) | Backward compatibility |
| Import resolution | slug -> previous_slug -> name | Graceful degradation |
| Rename handling | Store old slug in previous_slug | One-rename grace period |

---

## Alternatives Considered

### Alternative 1: Immutable Slugs (Rejected)

**Approach**: Never change slug after creation
**Rejected Because**: User expectation is that slug reflects current name; previous_slug provides migration support

### Alternative 2: UUID as Portable Identifier (Rejected)

**Approach**: Use existing UUID field for import/export resolution
**Rejected Because**: UUID is auto-generated and not human-readable; slug provides better debugging experience

### Alternative 3: Underscore Separator (Rejected)

**Approach**: Use underscores like Supplier model
**Rejected Because**: Hyphen pattern is more common in modern slugs; consistent with FinishedUnit/FinishedGood

---

## Implementation Checklist

- [ ] Add `slug` column to Recipe model (String(200), unique, indexed, non-nullable)
- [ ] Add `previous_slug` column to Recipe model (String(200), nullable, indexed)
- [ ] Add event listener for auto-generation on insert
- [ ] Add `generate_slug()` to RecipeService
- [ ] Add `_generate_unique_slug()` to RecipeService
- [ ] Update `create_recipe()` to use slug generation
- [ ] Update `update_recipe()` to handle rename (slug regeneration, previous_slug preservation)
- [ ] Add `slug`, `previous_slug` to recipe export
- [ ] Add `recipe_slug` to FinishedUnit export
- [ ] Add `recipe_slug` to EventProductionTarget export
- [ ] Add `recipe_slug` to ProductionRun export
- [ ] Add `component_recipe_slug` to RecipeComponent export
- [ ] Update recipe import with slug resolution
- [ ] Update FinishedUnit import with slug resolution
- [ ] Update EventProductionTarget import with slug resolution
- [ ] Update ProductionRun import with slug resolution
- [ ] Update RecipeComponent import with slug resolution
- [ ] Add unit tests for slug generation
- [ ] Add unit tests for collision handling
- [ ] Add integration tests for export/import round-trip
- [ ] Add tests for legacy (name-only) import fallback
