---
work_package_id: WP04
title: Import Service Updates
lane: "doing"
dependencies: [WP02]
base_branch: 080-recipe-slug-support-WP02
base_commit: 61d5b75fb0427629d1d27c3bebc919877fdb2e39
created_at: '2026-01-28T17:03:11.601916+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 1 - Export/Import
assignee: ''
agent: ''
shell_pid: "51946"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T07:45:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Import Service Updates

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP02 (can run parallel with WP03)
spec-kitty implement WP04 --base WP02
```

---

## Objectives & Success Criteria

**Objective**: Update all recipe FK imports to resolve via slug first, with fallback to `previous_slug`, then `name`. Log fallback events for migration tracking.

**Success Criteria**:
- [ ] Recipe import uses slug if provided, generates if missing
- [ ] `_resolve_recipe()` helper implements slug → previous_slug → name fallback
- [ ] FinishedUnit import resolves recipe by slug
- [ ] EventProductionTarget import resolves recipe by slug
- [ ] ProductionRun import resolves recipe by slug
- [ ] RecipeComponent import resolves by slug
- [ ] Fallback resolution events are logged
- [ ] Legacy imports (no slug) still work via name fallback

---

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/080-recipe-slug-support/plan.md`
- Research: `kitty-specs/080-recipe-slug-support/research.md`
- Data Model: `kitty-specs/080-recipe-slug-support/data-model.md`

**Key Files**:
- `src/services/catalog_import_service.py` (recipe import)
- `src/services/coordinated_export_service.py` (FK entity imports)

**Resolution Order** (per spec):
1. Try `recipe_slug` against `Recipe.slug`
2. Try `recipe_slug` against `Recipe.previous_slug` (log fallback)
3. Try `recipe_name` against `Recipe.name` (log legacy fallback)
4. If none match, log error and skip record

**Pattern Reference**: See how `_import_products()` resolves `ingredient_slug` in coordinated_export_service.py

---

## Subtasks & Detailed Guidance

### Subtask T019 – Update `_import_recipes()` for Slug Support

**Purpose**: Import recipes with slug resolution and generation.

**Steps**:
1. Open `src/services/catalog_import_service.py`
2. Find `_import_recipes()` function (around line 1031-1206)
3. Update the import logic to handle slugs:

   ```python
   def _import_recipes(
       data: list,
       session: Session,
       result: ImportResult,
       import_mode: str = "ADD_ONLY"
   ) -> dict:
       """Import recipes with slug support.

       Args:
           data: List of recipe dictionaries
           session: Database session
           result: ImportResult for tracking
           import_mode: "ADD_ONLY" or "AUGMENT"

       Returns:
           Mapping of recipe slug/name to recipe ID
       """
       from src.models.recipe import Recipe
       from src.services.recipe_service import RecipeService

       # Build lookup dictionaries
       existing_by_slug = {
           r.slug: r for r in session.query(Recipe).filter(Recipe.slug.isnot(None)).all()
       }
       existing_by_previous_slug = {
           r.previous_slug: r for r in session.query(Recipe).filter(Recipe.previous_slug.isnot(None)).all()
       }
       existing_by_name = {
           r.name: r for r in session.query(Recipe).all()
       }

       recipe_id_map = {}  # slug or name -> id

       for item in data:
           recipe_slug = item.get("slug")
           recipe_name = item.get("name", "")
           identifier = recipe_slug or recipe_name or "unknown"

           try:
               # Check for existing recipe
               existing = None

               if recipe_slug:
                   if recipe_slug in existing_by_slug:
                       existing = existing_by_slug[recipe_slug]
                   elif recipe_slug in existing_by_previous_slug:
                       existing = existing_by_previous_slug[recipe_slug]
                       logger.info(f"Recipe '{identifier}' matched via previous_slug")

               if not existing and recipe_name in existing_by_name:
                   existing = existing_by_name[recipe_name]
                   if recipe_slug:  # Had slug but didn't match
                       logger.info(f"Recipe '{identifier}' matched via name fallback")

               if existing:
                   if import_mode == "AUGMENT":
                       # Update existing recipe
                       # ... update fields as needed
                       pass
                   # Map both slug and name to ID
                   recipe_id_map[existing.slug] = existing.id
                   recipe_id_map[existing.name] = existing.id
                   continue

               # Create new recipe
               # Generate slug if not provided
               if not recipe_slug:
                   recipe_slug = RecipeService._generate_unique_slug(recipe_name, session)

               recipe = Recipe(
                   name=recipe_name,
                   slug=recipe_slug,
                   previous_slug=item.get("previous_slug"),
                   category=item.get("category"),
                   source=item.get("source"),
                   estimated_time_minutes=item.get("estimated_time_minutes"),
                   notes=item.get("notes"),
                   is_archived=item.get("is_archived", False),
                   is_production_ready=item.get("is_production_ready", False),
               )
               session.add(recipe)
               session.flush()

               # Update lookups and map
               existing_by_slug[recipe_slug] = recipe
               recipe_id_map[recipe_slug] = recipe.id
               recipe_id_map[recipe_name] = recipe.id

               result.add_success(f"Recipe: {recipe_name}")

           except Exception as e:
               result.add_error(f"Recipe '{identifier}': {str(e)}")

       return recipe_id_map
   ```

**Files**:
- `src/services/catalog_import_service.py` (modify)

**Notes**:
- Return recipe_id_map for use by component resolution
- Handle both slug and name in lookups for legacy support

---

### Subtask T020 – Create `_resolve_recipe()` Helper Function

**Purpose**: Centralize recipe resolution logic with fallback chain.

**Steps**:
1. In `src/services/coordinated_export_service.py`, add helper function:

   ```python
   import logging

   logger = logging.getLogger(__name__)


   def _resolve_recipe(
       recipe_slug: Optional[str],
       recipe_name: Optional[str],
       session: Session,
       context: str = ""
   ) -> Optional[int]:
       """Resolve recipe to ID using slug -> previous_slug -> name fallback.

       Args:
           recipe_slug: Recipe slug from import data
           recipe_name: Recipe name from import data (fallback)
           session: Database session
           context: Context string for logging (e.g., "FinishedUnit 'Cookies'")

       Returns:
           Recipe ID if found, None otherwise
       """
       from src.models.recipe import Recipe

       if not recipe_slug and not recipe_name:
           logger.warning(f"{context}: No recipe_slug or recipe_name provided")
           return None

       # Try slug first
       if recipe_slug:
           recipe = session.query(Recipe).filter(Recipe.slug == recipe_slug).first()
           if recipe:
               return recipe.id

           # Try previous_slug
           recipe = session.query(Recipe).filter(Recipe.previous_slug == recipe_slug).first()
           if recipe:
               logger.info(f"{context}: Resolved recipe '{recipe_slug}' via previous_slug fallback")
               return recipe.id

       # Try name (legacy fallback)
       if recipe_name:
           recipe = session.query(Recipe).filter(Recipe.name == recipe_name).first()
           if recipe:
               if recipe_slug:
                   logger.info(f"{context}: Resolved recipe via name fallback (slug '{recipe_slug}' not found)")
               return recipe.id

       # Not found
       logger.error(f"{context}: Recipe not found - slug='{recipe_slug}', name='{recipe_name}'")
       return None
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify)

**Notes**:
- Returns None on failure (caller decides whether to skip or error)
- Logs at INFO for successful fallbacks, ERROR for not found
- Context parameter enables clear log messages

---

### Subtask T021 – Update FinishedUnit Import for Slug Resolution

**Purpose**: Use slug-based recipe resolution for finished unit imports.

**Steps**:
1. Find finished_units import in `coordinated_export_service.py` (around line 1349-1383)
2. Replace name-based resolution with `_resolve_recipe()`:

   ```python
   elif entity_type == "finished_units":
       from src.models.finished_unit import FinishedUnit, YieldMode

       # Resolve recipe FK by slug (with fallback)
       recipe_slug = record.get("recipe_slug")
       recipe_name = record.get("recipe_name")

       recipe_id = _resolve_recipe(
           recipe_slug,
           recipe_name,
           session,
           context=f"FinishedUnit '{record.get('display_name', 'unknown')}'"
       )

       if not recipe_id:
           skipped += 1
           continue

       # ... rest of import logic unchanged, but use recipe_id variable
       obj = FinishedUnit(
           recipe_id=recipe_id,  # Use resolved ID
           slug=record.get("slug"),
           display_name=record.get("display_name"),
           # ... rest unchanged
       )
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify)

**Parallel**: Yes - can be done alongside T022, T023

---

### Subtask T022 – Update EventProductionTarget Import for Slug Resolution

**Purpose**: Use slug-based recipe resolution for event production target imports.

**Steps**:
1. Find event/production target import section (events are imported with nested targets)
2. Look for where `recipe_name` is resolved
3. Update to use `_resolve_recipe()`:

   ```python
   # In event import section, when processing production_targets
   for target_data in record.get("production_targets", []):
       recipe_slug = target_data.get("recipe_slug")
       recipe_name = target_data.get("recipe_name")

       recipe_id = _resolve_recipe(
           recipe_slug,
           recipe_name,
           session,
           context=f"EventProductionTarget for event '{record.get('name', 'unknown')}'"
       )

       if not recipe_id:
           logger.warning(f"Skipping production target - recipe not found")
           continue

       target = EventProductionTarget(
           event_id=event.id,
           recipe_id=recipe_id,
           target_batches=target_data.get("target_batches"),
           notes=target_data.get("notes"),
       )
       session.add(target)
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify)

**Parallel**: Yes - can be done alongside T021, T023

---

### Subtask T023 – Update ProductionRun Import for Slug Resolution

**Purpose**: Use slug-based recipe resolution for production run imports.

**Steps**:
1. Find production_runs import (around line 1645-1680)
2. Update to use `_resolve_recipe()`:

   ```python
   elif entity_type == "production_runs":
       from src.models.production_run import ProductionRun

       recipe_slug = record.get("recipe_slug")
       recipe_name = record.get("recipe_name")

       recipe_id = _resolve_recipe(
           recipe_slug,
           recipe_name,
           session,
           context=f"ProductionRun"
       )

       if not recipe_id:
           skipped += 1
           continue

       # Resolve event if present
       event_id = None
       event_name = record.get("event_name")
       if event_name:
           event = session.query(Event).filter(Event.name == event_name).first()
           event_id = event.id if event else None

       run = ProductionRun(
           recipe_id=recipe_id,
           event_id=event_id,
           quantity_planned=record.get("quantity_planned"),
           quantity_actual=record.get("quantity_actual"),
           # ... rest unchanged
       )
       session.add(run)
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify)

**Parallel**: Yes - can be done alongside T021, T022

---

### Subtask T024 – Update RecipeComponent Import for Slug Resolution

**Purpose**: Use slug-based resolution for nested recipe components.

**Steps**:
1. In `catalog_import_service.py`, find where recipe components are processed
2. Look for `component_recipe_name` resolution (around line 1134-1148)
3. Update to use slug-based resolution:

   ```python
   # When processing recipe components after main recipe import
   for item in data:
       components = item.get("components", [])
       recipe_slug = item.get("slug")
       recipe_name = item.get("name")

       # Find parent recipe
       parent_recipe = None
       if recipe_slug and recipe_slug in existing_by_slug:
           parent_recipe = existing_by_slug[recipe_slug]
       elif recipe_name and recipe_name in existing_by_name:
           parent_recipe = existing_by_name[recipe_name]

       if not parent_recipe:
           continue

       for comp in components:
           comp_slug = comp.get("component_recipe_slug")
           comp_name = comp.get("component_recipe_name")

           # Resolve component recipe
           component_recipe = None
           if comp_slug:
               if comp_slug in existing_by_slug:
                   component_recipe = existing_by_slug[comp_slug]
               elif comp_slug in existing_by_previous_slug:
                   component_recipe = existing_by_previous_slug[comp_slug]
                   logger.info(f"Component '{comp_slug}' resolved via previous_slug")

           if not component_recipe and comp_name:
               if comp_name in existing_by_name:
                   component_recipe = existing_by_name[comp_name]
                   if comp_slug:
                       logger.info(f"Component resolved via name fallback")

           if not component_recipe:
               logger.error(f"Component recipe not found: slug='{comp_slug}', name='{comp_name}'")
               continue

           # Create component link
           rc = RecipeComponent(
               recipe_id=parent_recipe.id,
               component_recipe_id=component_recipe.id,
               quantity=comp.get("quantity"),
               unit=comp.get("unit"),
           )
           session.add(rc)
   ```

**Files**:
- `src/services/catalog_import_service.py` (modify)

**Notes**:
- Components are processed after main recipes to ensure targets exist
- Same fallback logic: slug -> previous_slug -> name

---

### Subtask T025 – Add Logging for Fallback Resolution

**Purpose**: Track when fallback resolution is used for migration monitoring.

**Steps**:
1. Ensure logging is imported in both services:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```

2. Verify `_resolve_recipe()` logs at appropriate levels:
   - `logger.info()` for successful fallback (previous_slug or name)
   - `logger.error()` for resolution failure

3. Add summary logging at end of import:
   ```python
   # At end of import function
   if fallback_count > 0:
       logger.info(f"Import used fallback resolution {fallback_count} times - consider re-exporting data")
   ```

4. Consider adding a counter for fallback usage:
   ```python
   fallback_stats = {"previous_slug": 0, "name": 0, "not_found": 0}

   # In _resolve_recipe or calling code, increment counters
   # At end, log summary
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify)
- `src/services/catalog_import_service.py` (modify)

**Notes**:
- Logging helps users understand when to re-export
- INFO level for expected fallbacks, WARNING/ERROR for issues

---

## Test Strategy

**Unit tests** (add to test file):
```python
class TestRecipeImportSlugResolution:
    """Tests for recipe import with slug resolution."""

    def test_import_resolves_by_slug(self, session):
        """Test import finds recipe by slug."""
        # Create recipe with known slug
        recipe = Recipe(name="Test", slug="test-slug")
        session.add(recipe)
        session.flush()

        # Import data referencing by slug
        recipe_id = _resolve_recipe("test-slug", None, session, "test")
        assert recipe_id == recipe.id

    def test_import_falls_back_to_previous_slug(self, session):
        """Test import falls back to previous_slug."""
        recipe = Recipe(name="Renamed", slug="new-slug", previous_slug="old-slug")
        session.add(recipe)
        session.flush()

        # Import using old slug
        recipe_id = _resolve_recipe("old-slug", None, session, "test")
        assert recipe_id == recipe.id

    def test_import_falls_back_to_name(self, session):
        """Test legacy import uses name fallback."""
        recipe = Recipe(name="Legacy Recipe", slug="legacy-recipe")
        session.add(recipe)
        session.flush()

        # Import without slug (legacy)
        recipe_id = _resolve_recipe(None, "Legacy Recipe", session, "test")
        assert recipe_id == recipe.id

    def test_import_returns_none_when_not_found(self, session):
        """Test returns None when recipe not found."""
        recipe_id = _resolve_recipe("nonexistent", "Also Not Found", session, "test")
        assert recipe_id is None
```

**Run tests**:
```bash
./run-tests.sh src/tests/test_import*.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking legacy imports | Name fallback preserves compatibility |
| Performance with many recipes | Build lookup dicts once, not per-record |
| Logging too verbose | Use INFO for fallbacks, not DEBUG |
| Circular import | Import Recipe model inside function |

---

## Definition of Done Checklist

- [ ] T019: Recipe import handles slug resolution and generation
- [ ] T020: `_resolve_recipe()` helper implemented with fallback chain
- [ ] T021: FinishedUnit import uses slug resolution
- [ ] T022: EventProductionTarget import uses slug resolution
- [ ] T023: ProductionRun import uses slug resolution
- [ ] T024: RecipeComponent import uses slug resolution
- [ ] T025: Fallback events are logged at INFO level
- [ ] Legacy imports (no slugs) still work
- [ ] All import tests pass

---

## Review Guidance

**Reviewers should verify**:
1. Resolution order is slug → previous_slug → name
2. All FK imports use `_resolve_recipe()` or equivalent logic
3. Logging is at appropriate levels
4. Legacy imports work (test with export from before this feature)
5. No performance regression (lookup dicts vs repeated queries)

---

## Activity Log

- 2026-01-28T07:45:00Z – system – lane=planned – Prompt created.
