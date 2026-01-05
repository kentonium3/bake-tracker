# Cursor Code Review Prompt - Feature 037: Recipe Template & Snapshot System

## Role

You are a senior software engineer performing an independent code review of Feature 037 (recipe-template-snapshot). This feature implements an immutable snapshot system for recipes at production time, enabling historical cost accuracy, batch scaling with scale_factor, recipe variants, and production readiness filtering.

## Feature Summary

**Core Changes:**
1. RecipeSnapshot Model: New model with JSON denormalization of recipe/ingredient data, is_backfilled flag (WP01)
2. Snapshot Service: create_recipe_snapshot(), get_recipe_snapshots(), get_snapshot_by_production_run(), create_recipe_from_snapshot() (WP02)
3. Production Integration: batch_production_service modified to create snapshot FIRST, use snapshot data for cost calculation, support scale_factor (WP03)
4. Migration Script: Backfill snapshots for existing ProductionRuns with is_backfilled=True flag (WP04)
5. Scale Factor UI: RecordProductionDialog modified with scale_factor entry and ingredient requirements display (WP05)
6. Variant Service & UI: base_recipe_id, variant_name support, create_variant_from_recipe() (WP06)
7. Production Readiness: is_production_ready flag with UI toggle and filtering (WP07)
8. Recipe History View: Modal dialog showing snapshot history with "Create Recipe from Snapshot" option (WP08)

**Problem Being Solved:**
- Recipe changes retroactively corrupted historical production costs
- No way to track recipe variants (different flavors/configurations)
- No batch scaling support (repetition + size multiplier)
- No way to filter experimental vs production-ready recipes

**Solution:**
- Template/Snapshot Architecture: Recipes are mutable templates; RecipeSnapshot captures immutable state at production time
- Snapshot created FIRST before any FIFO consumption
- Costs calculated from snapshot data, not live recipe
- scale_factor flows through: expected_yield = base_yield x scale_factor x num_batches
- Backfilled snapshots marked with is_backfilled=True for historical runs

## Files to Review

### Model Layer (WP01)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/models/recipe_snapshot.py`
  - **WP01**: New RecipeSnapshot model with recipe_id, production_run_id, scale_factor, snapshot_date
  - **WP01**: recipe_data (Text/JSON), ingredients_data (Text/JSON), is_backfilled (Boolean)
  - **WP01**: get_recipe_data(), get_ingredients_data() helper methods for JSON parsing
  - **WP01**: Relationships to Recipe and ProductionRun

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/models/recipe.py`
  - **WP06**: base_recipe_id (nullable, self-referential FK with SET NULL)
  - **WP06**: variant_name (String, nullable)
  - **WP07**: is_production_ready (Boolean, default False)
  - **WP06**: CHECK constraint preventing self-reference

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/models/production_run.py`
  - **WP01**: recipe_snapshot_id (FK to recipe_snapshots.id, nullable for migration)
  - **WP01**: Relationship to RecipeSnapshot

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/models/__init__.py`
  - **WP01**: RecipeSnapshot exported

### Snapshot Service (WP02)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/services/recipe_snapshot_service.py`
  - **WP02**: create_recipe_snapshot(recipe_id, scale_factor, production_run_id, session=None)
  - **WP02**: get_recipe_snapshots(recipe_id, session=None) - ordered by date DESC
  - **WP02**: get_snapshot_by_production_run(production_run_id, session=None)
  - **WP02**: get_snapshot_by_id(snapshot_id, session=None)
  - **WP08**: create_recipe_from_snapshot(snapshot_id, session=None) - restores recipe from snapshot
  - **WP02**: NO update methods (immutability enforced)
  - **WP02**: Session management pattern (session=None with session_scope fallback)

### Production Integration (WP03)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/services/batch_production_service.py`
  - **WP03**: record_batch_production() modified to accept scale_factor parameter
  - **WP03**: Snapshot created FIRST before any FIFO consumption
  - **WP03**: Costs calculated from snapshot ingredients_data
  - **WP03**: expected_yield = base_yield x scale_factor x num_batches
  - **WP03**: ProductionRun.recipe_snapshot_id populated

### Migration Script (WP04)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/scripts/migrate_production_snapshots.py`
  - **WP04**: migrate_production_snapshots(dry_run=True) - main migration function
  - **WP04**: _create_backfill_snapshot() - creates snapshot with is_backfilled=True
  - **WP04**: verify_migration() - reports migration status
  - **WP04**: --dry-run mode for validation
  - **WP04**: --verify mode to check status
  - **WP04**: Idempotent (safe to run multiple times)
  - **WP04**: Handles deleted recipes gracefully (skips with warning)

### Scale Factor UI (WP05)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/ui/forms/record_production_dialog.py`
  - **WP05**: scale_factor entry field added
  - **WP05**: Validation for scale_factor > 0
  - **WP05**: Ingredient requirements display
  - **WP05**: Expected yield calculation with scale_factor

### Variant Service & UI (WP06)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/services/recipe_service.py`
  - **WP06**: create_variant_from_recipe(recipe_id, variant_name, session=None)
  - **WP06**: get_recipe_variants(recipe_id, session=None)
  - **WP06**: Variant creation copies recipe data with base_recipe_id link

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/ui/recipes_tab.py`
  - **WP06**: Variant creation UI
  - **WP06**: Variant display grouping under base recipes

### Production Readiness (WP07)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/ui/forms/recipe_form_dialog.py`
  - **WP07**: is_production_ready checkbox/toggle
  - **WP07**: Default to False for new recipes

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/ui/recipes_tab.py`
  - **WP07**: Production readiness filter dropdown
  - **WP07**: Filter recipes by is_production_ready state

### Recipe History View (WP08)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/ui/views/recipe_history_view.py`
  - **WP08**: RecipeHistoryView modal dialog
  - **WP08**: Displays snapshot history for recipe
  - **WP08**: "View Details" for each snapshot
  - **WP08**: "Create Recipe from Snapshot" button
  - **WP08**: "(approximated)" badge for backfilled snapshots

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/ui/views/__init__.py`
  - **WP08**: Package init with RecipeHistoryView export

### Tests

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/tests/services/test_recipe_snapshot_service.py`
  - **WP02**: Tests for create, get, immutability enforcement
  - **WP08**: Tests for create_recipe_from_snapshot

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/src/tests/scripts/test_migrate_production_snapshots.py`
  - **WP04**: Tests for migration script functionality

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/tasks.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/research.md`

### Work Package Prompts (for context)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/tasks/for_review/WP01-models-layer.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/tasks/for_review/WP02-snapshot-service.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/tasks/for_review/WP03-production-integration.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/tasks/for_review/WP04-migration-script.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/tasks/for_review/WP05-scale-factor-ui.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/tasks/for_review/WP06-variant-service-ui.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/tasks/for_review/WP07-production-readiness.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot/kitty-specs/037-recipe-template-snapshot/tasks/for_review/WP08-recipe-history-view.md`

## Review Checklist

### 1. Model Layer (WP01)

- [ ] RecipeSnapshot model exists in src/models/recipe_snapshot.py
- [ ] RecipeSnapshot has recipe_id FK to recipes.id
- [ ] RecipeSnapshot has production_run_id FK (nullable)
- [ ] RecipeSnapshot has scale_factor (Float, default 1.0)
- [ ] RecipeSnapshot has snapshot_date (DateTime with timezone)
- [ ] RecipeSnapshot has recipe_data (Text for JSON)
- [ ] RecipeSnapshot has ingredients_data (Text for JSON)
- [ ] RecipeSnapshot has is_backfilled (Boolean, default False)
- [ ] RecipeSnapshot has get_recipe_data() and get_ingredients_data() helper methods
- [ ] ProductionRun has recipe_snapshot_id FK (nullable for migration)
- [ ] Recipe has base_recipe_id (nullable, self-referential, SET NULL on delete)
- [ ] Recipe has variant_name (String, nullable)
- [ ] Recipe has is_production_ready (Boolean, default False)
- [ ] Recipe has CHECK constraint preventing self-reference (base_recipe_id != id)
- [ ] RecipeSnapshot exported from src/models/__init__.py

### 2. Snapshot Service (WP02)

- [ ] create_recipe_snapshot() exists with session=None pattern
- [ ] create_recipe_snapshot() denormalizes recipe data to JSON (name, category, source, yield_quantity, yield_unit, yield_description, estimated_time_minutes, notes, variant_name, is_production_ready)
- [ ] create_recipe_snapshot() denormalizes ingredients to JSON array (ingredient_id, ingredient_name, ingredient_slug, quantity, unit, notes)
- [ ] get_recipe_snapshots() returns snapshots ordered by date DESC
- [ ] get_snapshot_by_production_run() returns snapshot for given production run
- [ ] get_snapshot_by_id() returns snapshot by ID
- [ ] NO update or delete methods exist (immutability)
- [ ] All functions follow session management pattern

### 3. Production Integration (WP03)

- [ ] record_batch_production() accepts scale_factor parameter (default 1.0)
- [ ] Snapshot created FIRST before any FIFO consumption
- [ ] Cost calculation uses snapshot ingredients_data, not live recipe
- [ ] Ingredient quantities multiplied by scale_factor and num_batches
- [ ] expected_yield = base_yield x scale_factor x num_batches
- [ ] ProductionRun.recipe_snapshot_id populated after snapshot creation
- [ ] Session passed through all nested calls

### 4. Migration Script (WP04)

- [ ] Script exists at scripts/migrate_production_snapshots.py
- [ ] migrate_production_snapshots() accepts dry_run parameter
- [ ] Dry run validates without modifying data
- [ ] Creates backfilled snapshots with is_backfilled=True
- [ ] Uses production_run.produced_at for snapshot_date
- [ ] Handles deleted recipes gracefully (skips with warning)
- [ ] Idempotent - skips already migrated runs
- [ ] verify_migration() reports status
- [ ] --dry-run and --verify CLI arguments work

### 5. Scale Factor UI (WP05)

- [ ] RecordProductionDialog has scale_factor entry field
- [ ] Scale factor validated as > 0
- [ ] UI shows expected yield with scale_factor applied
- [ ] UI shows ingredient requirements with scale_factor applied
- [ ] scale_factor passed to record_batch_production()

### 6. Variant Service & UI (WP06)

- [ ] create_variant_from_recipe() exists
- [ ] Variant copies recipe data with base_recipe_id link
- [ ] get_recipe_variants() returns variants for base recipe
- [ ] UI allows creating variants
- [ ] Variants displayed grouped under base recipes

### 7. Production Readiness (WP07)

- [ ] is_production_ready toggle in recipe form
- [ ] New recipes default to False
- [ ] Filter dropdown in recipes tab
- [ ] Filter correctly shows only ready/experimental/all recipes

### 8. Recipe History View (WP08)

- [ ] RecipeHistoryView modal dialog exists
- [ ] Shows list of snapshots for recipe
- [ ] View Details shows full snapshot data
- [ ] "Create Recipe from Snapshot" button works
- [ ] create_recipe_from_snapshot() creates new recipe from snapshot data
- [ ] "(approximated)" badge shown for backfilled snapshots

### 9. Code Quality

- [ ] Feature comments reference "F037" or "Feature 037"
- [ ] Docstrings present for new functions
- [ ] No unused imports added
- [ ] No debug print statements left in code
- [ ] Session management pattern followed everywhere
- [ ] No business logic in UI layer
- [ ] JSON serialization handles edge cases (None values, empty lists)

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/037-recipe-template-snapshot

# Activate virtual environment
source venv/bin/activate

# Verify all modified modules import correctly
PYTHONPATH=. python3 -c "
from src.models.recipe_snapshot import RecipeSnapshot
from src.models import RecipeSnapshot
from src.services.recipe_snapshot_service import (
    create_recipe_snapshot,
    get_recipe_snapshots,
    get_snapshot_by_production_run,
    get_snapshot_by_id,
    create_recipe_from_snapshot
)
from src.services.batch_production_service import record_batch_production
from src.ui.views.recipe_history_view import RecipeHistoryView
print('All imports successful')
"

# Verify RecipeSnapshot model structure
grep -n "class RecipeSnapshot" src/models/recipe_snapshot.py
grep -n "recipe_data\|ingredients_data\|is_backfilled\|scale_factor" src/models/recipe_snapshot.py
grep -n "get_recipe_data\|get_ingredients_data" src/models/recipe_snapshot.py

# Verify Recipe model additions
grep -n "base_recipe_id\|variant_name\|is_production_ready" src/models/recipe.py

# Verify ProductionRun has recipe_snapshot_id
grep -n "recipe_snapshot_id" src/models/production_run.py

# Verify snapshot service functions exist
grep -n "def create_recipe_snapshot\|def get_recipe_snapshots\|def get_snapshot_by_production_run\|def get_snapshot_by_id\|def create_recipe_from_snapshot" src/services/recipe_snapshot_service.py

# Verify NO update/delete methods in snapshot service
grep -n "def update_\|def delete_" src/services/recipe_snapshot_service.py || echo "Good: No update/delete methods found"

# Verify scale_factor in batch_production_service
grep -n "scale_factor" src/services/batch_production_service.py | head -10

# Verify migration script exists and has key functions
grep -n "def migrate_production_snapshots\|def _create_backfill_snapshot\|def verify_migration" scripts/migrate_production_snapshots.py

# Verify is_backfilled flag usage in migration
grep -n "is_backfilled" scripts/migrate_production_snapshots.py

# Verify RecipeHistoryView exists
grep -n "class RecipeHistoryView" src/ui/views/recipe_history_view.py

# Run snapshot service tests
PYTHONPATH=. python3 -m pytest src/tests/services/test_recipe_snapshot_service.py -v --tb=short

# Run migration script tests
PYTHONPATH=. python3 -m pytest src/tests/scripts/test_migrate_production_snapshots.py -v --tb=short

# Run full test suite to verify no regressions
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -100

# Check git log for F037 commits
git log --oneline -20
```

## Key Implementation Patterns

### Snapshot Creation Pattern (WP02/WP03)
```python
def create_recipe_snapshot(
    recipe_id: int,
    scale_factor: float,
    production_run_id: int,
    session: Session = None
) -> dict:
    """Create an immutable snapshot of recipe state at production time."""
    if session is not None:
        return _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session)

    with session_scope() as session:
        return _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session)

def _create_recipe_snapshot_impl(..., session):
    # Load recipe with relationships
    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        raise SnapshotCreationError(f"Recipe {recipe_id} not found")

    # Eagerly load ingredients
    _ = recipe.recipe_ingredients
    for ri in recipe.recipe_ingredients:
        _ = ri.ingredient

    # Build recipe_data JSON
    recipe_data = {
        "name": recipe.name,
        "category": recipe.category,
        # ... all recipe fields
    }

    # Build ingredients_data JSON
    ingredients_data = []
    for ri in recipe.recipe_ingredients:
        ing_data = {
            "ingredient_id": ri.ingredient_id,
            "ingredient_name": ri.ingredient.display_name,
            "ingredient_slug": ri.ingredient.slug,
            "quantity": float(ri.quantity),
            "unit": ri.unit,
            "notes": ri.notes,
        }
        ingredients_data.append(ing_data)

    # Create snapshot
    snapshot = RecipeSnapshot(
        recipe_id=recipe_id,
        production_run_id=production_run_id,
        scale_factor=scale_factor,
        snapshot_date=utc_now(),
        recipe_data=json.dumps(recipe_data),
        ingredients_data=json.dumps(ingredients_data),
        is_backfilled=False
    )

    session.add(snapshot)
    session.flush()
    return {...}
```

### Production Integration Pattern (WP03)
```python
def record_batch_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    notes: str = None,
    event_id: int = None,
    scale_factor: float = 1.0,  # NEW
    session=None
) -> dict:
    # ... validation ...

    # Create snapshot FIRST - captures recipe state before production
    snapshot = recipe_snapshot_service.create_recipe_snapshot(
        recipe_id=recipe_id,
        scale_factor=scale_factor,
        production_run_id=None,  # Will update after ProductionRun created
        session=session
    )
    snapshot_id = snapshot["id"]

    # Use snapshot ingredients for FIFO consumption
    ingredients_data = snapshot["ingredients_data"]
    for item in ingredients_data:
        base_quantity = Decimal(str(item["quantity"]))
        quantity_needed = base_quantity * Decimal(str(scale_factor)) * Decimal(str(num_batches))
        # ... FIFO consumption ...

    # Create ProductionRun with snapshot link
    production_run = ProductionRun(
        recipe_id=recipe_id,
        recipe_snapshot_id=snapshot_id,  # NEW
        # ...
    )
```

### Migration Backfill Pattern (WP04)
```python
def _create_backfill_snapshot(run: ProductionRun, recipe: Recipe, session) -> RecipeSnapshot:
    """Create a backfilled snapshot for a historical production run."""
    # Build recipe_data from CURRENT recipe state
    recipe_data = {
        "name": recipe.name,
        # ...
    }

    # Build ingredients_data from CURRENT recipe state
    ingredients_data = [...]

    # Create snapshot with is_backfilled=True
    snapshot = RecipeSnapshot(
        recipe_id=recipe.id,
        production_run_id=run.id,
        scale_factor=1.0,  # Historical runs didn't have scale_factor
        snapshot_date=run.produced_at or utc_now(),  # Use production date
        recipe_data=json.dumps(recipe_data),
        ingredients_data=json.dumps(ingredients_data),
        is_backfilled=True  # Mark as backfilled
    )

    session.add(snapshot)
    session.flush()
    return snapshot
```

### Create Recipe from Snapshot Pattern (WP08)
```python
def create_recipe_from_snapshot(snapshot_id: int, session=None) -> dict:
    """Create a new recipe from historical snapshot data."""
    # Get snapshot
    snapshot = session.query(RecipeSnapshot).filter_by(id=snapshot_id).first()
    if not snapshot:
        raise SnapshotNotFoundError(snapshot_id)

    # Extract recipe data
    recipe_data = snapshot.get_recipe_data()

    # Create new recipe
    new_recipe = Recipe(
        name=f"{recipe_data['name']} (from snapshot)",
        category=recipe_data.get("category"),
        # ... copy all fields
        is_production_ready=False  # Always start as experimental
    )

    session.add(new_recipe)
    session.flush()

    # Restore ingredients
    ingredients_data = snapshot.get_ingredients_data()
    for ing in ingredients_data:
        ri = RecipeIngredient(
            recipe_id=new_recipe.id,
            ingredient_id=ing["ingredient_id"],
            quantity=Decimal(str(ing["quantity"])),
            unit=ing["unit"],
            notes=ing.get("notes")
        )
        session.add(ri)

    return {...}
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F037-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 037 - Recipe Template & Snapshot System

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 037-recipe-template-snapshot
**Branch/Worktree:** `.worktrees/037-recipe-template-snapshot`

## Summary

[Brief overview of findings - is the template/snapshot architecture correctly implemented? Are there any issues?]

## Verification Results

### Module Import Validation
- recipe_snapshot.py: [PASS/FAIL]
- recipe_snapshot_service.py: [PASS/FAIL]
- batch_production_service.py: [PASS/FAIL]
- migrate_production_snapshots.py: [PASS/FAIL]
- recipe_history_view.py: [PASS/FAIL]
- record_production_dialog.py: [PASS/FAIL]

### Test Results
- Snapshot service tests: [X passed, Y failed]
- Migration script tests: [X passed, Y failed]
- Full test suite: [X passed, Y skipped, Z failed]

### Code Pattern Validation
- Model layer (WP01): [correct/issues found]
- Snapshot service (WP02): [correct/issues found]
- Production integration (WP03): [correct/issues found]
- Migration script (WP04): [correct/issues found]
- Scale factor UI (WP05): [correct/issues found]
- Variant service & UI (WP06): [correct/issues found]
- Production readiness (WP07): [correct/issues found]
- Recipe history view (WP08): [correct/issues found]

## Findings

### Critical Issues
[Any blocking issues that must be fixed before merge]

### Warnings
[Non-blocking concerns that should be addressed]

### Observations
[General observations about code quality, patterns, potential improvements]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/models/recipe_snapshot.py | [status] | [notes] |
| src/models/recipe.py | [status] | [notes] |
| src/models/production_run.py | [status] | [notes] |
| src/services/recipe_snapshot_service.py | [status] | [notes] |
| src/services/batch_production_service.py | [status] | [notes] |
| src/services/recipe_service.py | [status] | [notes] |
| scripts/migrate_production_snapshots.py | [status] | [notes] |
| src/ui/forms/record_production_dialog.py | [status] | [notes] |
| src/ui/views/recipe_history_view.py | [status] | [notes] |
| src/tests/services/test_recipe_snapshot_service.py | [status] | [notes] |
| src/tests/scripts/test_migrate_production_snapshots.py | [status] | [notes] |

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: Immutable snapshot created at production | [PASS/FAIL] | [evidence] |
| FR-002: Snapshot contains denormalized recipe/ingredient JSON | [PASS/FAIL] | [evidence] |
| FR-003: Snapshots cannot be edited after creation | [PASS/FAIL] | [evidence] |
| FR-004: Costs calculated from snapshot data | [PASS/FAIL] | [evidence] |
| FR-005: scale_factor stored with snapshot | [PASS/FAIL] | [evidence] |
| FR-006: ProductionRun links to snapshot, not recipe | [PASS/FAIL] | [evidence] |
| FR-007: num_batches and scale_factor are separate parameters | [PASS/FAIL] | [evidence] |
| FR-008: Expected yield = base x scale x batches | [PASS/FAIL] | [evidence] |
| FR-009: Ingredient consumption = base x scale x batches | [PASS/FAIL] | [evidence] |
| FR-010: base_recipe_id supports variants | [PASS/FAIL] | [evidence] |
| FR-014: is_production_ready flag exists | [PASS/FAIL] | [evidence] |
| FR-017: Snapshot history accessible | [PASS/FAIL] | [evidence] |
| FR-018: New recipe can be created from snapshot | [PASS/FAIL] | [evidence] |
| Session management pattern followed | [PASS/FAIL] | [evidence] |
| All existing tests pass (no regressions) | [PASS/FAIL] | [evidence] |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Models Layer | [PASS/FAIL] | [notes] |
| WP02: Snapshot Service | [PASS/FAIL] | [notes] |
| WP03: Production Integration | [PASS/FAIL] | [notes] |
| WP04: Migration Script | [PASS/FAIL] | [notes] |
| WP05: Scale Factor UI | [PASS/FAIL] | [notes] |
| WP06: Variant Service & UI | [PASS/FAIL] | [notes] |
| WP07: Production Readiness | [PASS/FAIL] | [notes] |
| WP08: Recipe History View | [PASS/FAIL] | [notes] |

## Code Quality Assessment

### Model Layer (WP01)
| Item | Status | Notes |
|------|--------|-------|
| RecipeSnapshot model exists | [Yes/No] | [notes] |
| JSON helper methods exist | [Yes/No] | [notes] |
| is_backfilled flag exists | [Yes/No] | [notes] |
| ProductionRun.recipe_snapshot_id exists | [Yes/No] | [notes] |
| Recipe variant fields exist | [Yes/No] | [notes] |
| Recipe readiness flag exists | [Yes/No] | [notes] |

### Snapshot Service (WP02)
| Item | Status | Notes |
|------|--------|-------|
| create_recipe_snapshot() exists | [Yes/No] | [notes] |
| Denormalizes recipe data to JSON | [Yes/No] | [notes] |
| Denormalizes ingredients to JSON | [Yes/No] | [notes] |
| get_recipe_snapshots() exists | [Yes/No] | [notes] |
| get_snapshot_by_production_run() exists | [Yes/No] | [notes] |
| NO update methods exist | [Yes/No] | [notes] |
| Session management pattern | [Yes/No] | [notes] |

### Production Integration (WP03)
| Item | Status | Notes |
|------|--------|-------|
| Snapshot created FIRST | [Yes/No] | [notes] |
| Costs from snapshot data | [Yes/No] | [notes] |
| scale_factor parameter added | [Yes/No] | [notes] |
| Expected yield calculation correct | [Yes/No] | [notes] |
| ProductionRun.recipe_snapshot_id set | [Yes/No] | [notes] |

### Migration Script (WP04)
| Item | Status | Notes |
|------|--------|-------|
| Script exists | [Yes/No] | [notes] |
| dry_run mode works | [Yes/No] | [notes] |
| is_backfilled=True for backfills | [Yes/No] | [notes] |
| Uses produced_at for snapshot_date | [Yes/No] | [notes] |
| Handles deleted recipes | [Yes/No] | [notes] |
| Idempotent | [Yes/No] | [notes] |

### Recipe History View (WP08)
| Item | Status | Notes |
|------|--------|-------|
| RecipeHistoryView exists | [Yes/No] | [notes] |
| Shows snapshot list | [Yes/No] | [notes] |
| View Details works | [Yes/No] | [notes] |
| Create from snapshot works | [Yes/No] | [notes] |
| Backfilled badge shown | [Yes/No] | [notes] |

## Potential Issues

### Session Management
[Any concerns about session handling in the new functions]

### Edge Cases
[Any edge cases that may not be handled properly]

### Data Integrity
[Any concerns about snapshot immutability or data consistency]

### FK Cycle Warning
[Note: There is a known FK cycle between production_runs and recipe_snapshots tables that causes test teardown warnings - this is expected]

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing
- The worktree is isolated from main branch at `.worktrees/037-recipe-template-snapshot`
- Layered architecture: UI -> Services -> Models -> Database
- Session management is CRITICAL: functions must accept optional `session` parameter and pass it through
- All existing tests must pass (no regressions)
- The template/snapshot pattern separates mutable recipe definitions from immutable production snapshots
- Backfilled snapshots use current recipe data as best approximation for historical runs
- UI must NOT contain business logic - only display service results
- There is a known FK cycle between production_runs and recipe_snapshots that causes test teardown warnings (non-blocking)
