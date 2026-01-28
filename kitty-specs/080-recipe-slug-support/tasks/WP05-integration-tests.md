---
work_package_id: WP05
title: Integration Tests & Validation
lane: "doing"
dependencies:
- WP03
base_branch: 080-recipe-slug-support-WP04
base_commit: e0b74ad8525ccbbc3834826e3a032f9915f90a56
created_at: '2026-01-28T17:49:52.672379+00:00'
subtasks:
- T026
- T027
- T028
- T029
phase: Phase 2 - Validation
assignee: ''
agent: ''
shell_pid: "60731"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T07:45:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Integration Tests & Validation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP03 and WP04 - implement after both complete
# If WP03 and WP04 were parallel from WP02, use the later one as base
spec-kitty implement WP05 --base WP04
```

---

## Objectives & Success Criteria

**Objective**: Validate end-to-end export/import round-trip with slugs and verify all edge cases.

**Success Criteria**:
- [ ] Round-trip test: export → fresh DB → import preserves all data
- [ ] Legacy import test: data without slugs imports via name fallback
- [ ] Previous_slug fallback test: renamed recipe resolves correctly
- [ ] All FK entities (FinishedUnit, ProductionRun, EventProductionTarget, RecipeComponent) resolve correctly
- [ ] All tests pass consistently (no flaky tests)

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/080-recipe-slug-support/spec.md` (Success Criteria SC-001 through SC-008)
- Plan: `kitty-specs/080-recipe-slug-support/plan.md`

**Test Location**: `src/tests/test_recipe_slug_integration.py` (new file)

**Test Dependencies**:
- WP01-WP04 must be complete
- Need pytest fixtures for session management
- Need tmp_path for export file operations

---

## Subtasks & Detailed Guidance

### Subtask T026 – Add Round-Trip Export/Import Test

**Purpose**: Verify complete data integrity through export → import cycle with slugs.

**Steps**:
1. Create new test file `src/tests/test_recipe_slug_integration.py`
2. Add comprehensive round-trip test:

   ```python
   """Integration tests for recipe slug support (F080)."""

   import json
   import pytest
   from pathlib import Path
   from datetime import datetime

   from src.models.recipe import Recipe, RecipeComponent
   from src.models.finished_unit import FinishedUnit
   from src.models.production_run import ProductionRun
   from src.models.event import Event, EventProductionTarget
   from src.services.coordinated_export_service import export_all_data
   from src.services.database import session_scope


   class TestRecipeSlugRoundTrip:
       """Test export/import round-trip preserves recipe slug data."""

       @pytest.fixture
       def populated_db(self, session):
           """Create test data with recipes and FK relationships."""
           # Create recipes
           recipe1 = Recipe(
               name="Chocolate Chip Cookies",
               slug="chocolate-chip-cookies",
               category="Cookies"
           )
           recipe2 = Recipe(
               name="Cookie Dough Base",
               slug="cookie-dough-base",
               category="Components"
           )
           session.add_all([recipe1, recipe2])
           session.flush()

           # Create component relationship
           component = RecipeComponent(
               recipe_id=recipe1.id,
               component_recipe_id=recipe2.id,
               quantity=1.0,
               unit="batch"
           )
           session.add(component)

           # Create finished unit
           fu = FinishedUnit(
               display_name="Chocolate Chip Cookies (Dozen)",
               slug="chocolate-chip-cookies-dozen",
               recipe_id=recipe1.id
           )
           session.add(fu)

           # Create event with production target
           event = Event(name="Holiday Baking 2025")
           session.add(event)
           session.flush()

           target = EventProductionTarget(
               event_id=event.id,
               recipe_id=recipe1.id,
               target_batches=10
           )
           session.add(target)

           # Create production run
           run = ProductionRun(
               recipe_id=recipe1.id,
               event_id=event.id,
               quantity_planned=48,
               quantity_actual=46
           )
           session.add(run)

           session.commit()
           return {
               "recipe1": recipe1,
               "recipe2": recipe2,
               "finished_unit": fu,
               "event": event,
               "target": target,
               "run": run
           }

       def test_full_round_trip_preserves_slugs(self, session, tmp_path, populated_db):
           """Test export -> fresh DB -> import preserves all slug data."""
           # Step 1: Export all data
           export_all_data(tmp_path, session)

           # Verify export files contain slugs
           recipes_file = tmp_path / "recipes.json"
           recipes_data = json.loads(recipes_file.read_text())

           assert len(recipes_data) >= 2
           recipe_slugs = {r["slug"] for r in recipes_data}
           assert "chocolate-chip-cookies" in recipe_slugs
           assert "cookie-dough-base" in recipe_slugs

           # Check component has slug
           parent = next(r for r in recipes_data if r["slug"] == "chocolate-chip-cookies")
           assert len(parent.get("components", [])) >= 1
           assert parent["components"][0]["component_recipe_slug"] == "cookie-dough-base"

           # Check FK entities have recipe_slug
           fu_file = tmp_path / "finished_units.json"
           fu_data = json.loads(fu_file.read_text())
           assert fu_data[0]["recipe_slug"] == "chocolate-chip-cookies"

           events_file = tmp_path / "events.json"
           events_data = json.loads(events_file.read_text())
           targets = events_data[0].get("production_targets", [])
           assert targets[0]["recipe_slug"] == "chocolate-chip-cookies"

           runs_file = tmp_path / "production_runs.json"
           runs_data = json.loads(runs_file.read_text())
           assert runs_data[0]["recipe_slug"] == "chocolate-chip-cookies"

           # Step 2: Clear database (simulate fresh DB)
           session.query(ProductionRun).delete()
           session.query(EventProductionTarget).delete()
           session.query(Event).delete()
           session.query(FinishedUnit).delete()
           session.query(RecipeComponent).delete()
           session.query(Recipe).delete()
           session.commit()

           # Verify empty
           assert session.query(Recipe).count() == 0

           # Step 3: Import data back
           from src.services.coordinated_export_service import import_all_data
           result = import_all_data(tmp_path, session)

           # Step 4: Verify all data restored with correct associations
           recipes = session.query(Recipe).all()
           assert len(recipes) >= 2

           # Check slugs preserved
           recipe1 = session.query(Recipe).filter(Recipe.slug == "chocolate-chip-cookies").first()
           assert recipe1 is not None
           assert recipe1.name == "Chocolate Chip Cookies"

           # Check component relationship restored
           assert len(recipe1.components) >= 1
           assert recipe1.components[0].component_recipe.slug == "cookie-dough-base"

           # Check finished unit FK restored
           fu = session.query(FinishedUnit).filter(FinishedUnit.slug == "chocolate-chip-cookies-dozen").first()
           assert fu is not None
           assert fu.recipe_id == recipe1.id

           # Check production target FK restored
           target = session.query(EventProductionTarget).first()
           assert target.recipe_id == recipe1.id

           # Check production run FK restored
           run = session.query(ProductionRun).first()
           assert run.recipe_id == recipe1.id
   ```

**Files**:
- `src/tests/test_recipe_slug_integration.py` (create)

**Notes**:
- Uses tmp_path fixture from pytest
- May need to adjust import paths based on actual function names
- Database cleanup simulates fresh DB scenario

---

### Subtask T027 – Add Legacy Import Test (Name Fallback)

**Purpose**: Verify imports without slug fields still work via name resolution.

**Steps**:
1. Add to test file:

   ```python
   class TestLegacyImportFallback:
       """Test imports without slugs fall back to name resolution."""

       def test_legacy_recipe_import_generates_slug(self, session, tmp_path):
           """Test importing recipe without slug auto-generates one."""
           # Create legacy export (no slug field)
           legacy_data = [
               {
                   "name": "Legacy Recipe",
                   "category": "Test",
                   # NO slug field - simulates pre-F080 export
               }
           ]
           recipes_file = tmp_path / "recipes.json"
           recipes_file.write_text(json.dumps(legacy_data))

           # Import
           from src.services.catalog_import_service import import_recipes
           import_recipes(tmp_path, session)

           # Verify slug was generated
           recipe = session.query(Recipe).filter(Recipe.name == "Legacy Recipe").first()
           assert recipe is not None
           assert recipe.slug == "legacy-recipe"  # Auto-generated

       def test_legacy_finished_unit_import_uses_name(self, session, tmp_path):
           """Test finished unit import falls back to recipe_name."""
           # Create recipe
           recipe = Recipe(name="Target Recipe", slug="target-recipe")
           session.add(recipe)
           session.commit()

           # Create legacy finished unit export (no recipe_slug)
           legacy_fu = [
               {
                   "display_name": "Legacy Finished Unit",
                   "slug": "legacy-fu",
                   "recipe_name": "Target Recipe",  # Name only, no slug
               }
           ]
           fu_file = tmp_path / "finished_units.json"
           fu_file.write_text(json.dumps(legacy_fu))

           # Import
           from src.services.coordinated_export_service import import_entity
           import_entity("finished_units", tmp_path, session)

           # Verify FK resolved via name
           fu = session.query(FinishedUnit).filter(FinishedUnit.slug == "legacy-fu").first()
           assert fu is not None
           assert fu.recipe_id == recipe.id

       def test_legacy_production_run_import_uses_name(self, session, tmp_path):
           """Test production run import falls back to recipe_name."""
           recipe = Recipe(name="Run Recipe", slug="run-recipe")
           session.add(recipe)
           session.commit()

           legacy_run = [
               {
                   "recipe_name": "Run Recipe",  # Name only
                   "quantity_planned": 10,
               }
           ]
           runs_file = tmp_path / "production_runs.json"
           runs_file.write_text(json.dumps(legacy_run))

           from src.services.coordinated_export_service import import_entity
           import_entity("production_runs", tmp_path, session)

           run = session.query(ProductionRun).first()
           assert run is not None
           assert run.recipe_id == recipe.id
   ```

**Files**:
- `src/tests/test_recipe_slug_integration.py` (modify)

**Notes**:
- Simulates pre-F080 export files
- Verifies backward compatibility

---

### Subtask T028 – Add Previous_slug Fallback Test

**Purpose**: Verify renamed recipes can be resolved via previous_slug.

**Steps**:
1. Add to test file:

   ```python
   class TestPreviousSlugFallback:
       """Test imports resolve via previous_slug for renamed recipes."""

       def test_import_resolves_via_previous_slug(self, session, tmp_path):
           """Test import finds renamed recipe via previous_slug."""
           # Create recipe that was renamed (has previous_slug)
           recipe = Recipe(
               name="New Recipe Name",
               slug="new-recipe-name",
               previous_slug="old-recipe-name"
           )
           session.add(recipe)
           session.commit()

           # Create import data using OLD slug
           import_data = [
               {
                   "display_name": "Test FU",
                   "slug": "test-fu",
                   "recipe_slug": "old-recipe-name",  # Uses old slug
               }
           ]
           fu_file = tmp_path / "finished_units.json"
           fu_file.write_text(json.dumps(import_data))

           # Import
           from src.services.coordinated_export_service import import_entity
           import_entity("finished_units", tmp_path, session)

           # Verify resolved via previous_slug
           fu = session.query(FinishedUnit).filter(FinishedUnit.slug == "test-fu").first()
           assert fu is not None
           assert fu.recipe_id == recipe.id

       def test_slug_takes_precedence_over_previous_slug(self, session):
           """Test current slug is preferred over previous_slug match."""
           # Create two recipes where one's slug matches other's previous_slug
           recipe1 = Recipe(
               name="Current Recipe",
               slug="shared-slug",
               previous_slug=None
           )
           recipe2 = Recipe(
               name="Renamed Recipe",
               slug="renamed-slug",
               previous_slug="shared-slug"
           )
           session.add_all([recipe1, recipe2])
           session.commit()

           # Resolve should find recipe1 (current slug match)
           from src.services.coordinated_export_service import _resolve_recipe
           recipe_id = _resolve_recipe("shared-slug", None, session, "test")

           assert recipe_id == recipe1.id  # Current slug wins

       def test_previous_slug_logged_when_used(self, session, caplog):
           """Test fallback to previous_slug is logged."""
           import logging
           caplog.set_level(logging.INFO)

           recipe = Recipe(
               name="Renamed",
               slug="new-slug",
               previous_slug="old-slug"
           )
           session.add(recipe)
           session.commit()

           from src.services.coordinated_export_service import _resolve_recipe
           _resolve_recipe("old-slug", None, session, "TestContext")

           # Check log message
           assert "previous_slug" in caplog.text.lower() or "fallback" in caplog.text.lower()
   ```

**Files**:
- `src/tests/test_recipe_slug_integration.py` (modify)

**Notes**:
- Tests the one-rename grace period feature
- Verifies logging of fallback usage

---

### Subtask T029 – Add FK Entity Resolution Test

**Purpose**: Comprehensive test that all FK entities resolve correctly.

**Steps**:
1. Add to test file:

   ```python
   class TestAllFKEntityResolution:
       """Test all FK entities correctly resolve recipe by slug."""

       @pytest.fixture
       def recipe_with_slug(self, session):
           """Create a recipe with known slug."""
           recipe = Recipe(
               name="Universal Recipe",
               slug="universal-recipe",
               category="Test"
           )
           session.add(recipe)
           session.commit()
           return recipe

       def test_finished_unit_resolves_recipe_slug(self, session, tmp_path, recipe_with_slug):
           """Test FinishedUnit import resolves recipe by slug."""
           data = [{
               "display_name": "FU Test",
               "slug": "fu-test",
               "recipe_slug": "universal-recipe",
               "recipe_name": "Wrong Name"  # Should be ignored
           }]
           (tmp_path / "finished_units.json").write_text(json.dumps(data))

           from src.services.coordinated_export_service import import_entity
           import_entity("finished_units", tmp_path, session)

           fu = session.query(FinishedUnit).first()
           assert fu.recipe_id == recipe_with_slug.id

       def test_production_run_resolves_recipe_slug(self, session, tmp_path, recipe_with_slug):
           """Test ProductionRun import resolves recipe by slug."""
           data = [{
               "recipe_slug": "universal-recipe",
               "quantity_planned": 10,
           }]
           (tmp_path / "production_runs.json").write_text(json.dumps(data))

           from src.services.coordinated_export_service import import_entity
           import_entity("production_runs", tmp_path, session)

           run = session.query(ProductionRun).first()
           assert run.recipe_id == recipe_with_slug.id

       def test_event_production_target_resolves_recipe_slug(self, session, tmp_path, recipe_with_slug):
           """Test EventProductionTarget import resolves recipe by slug."""
           # Create event
           event = Event(name="Test Event")
           session.add(event)
           session.commit()

           data = [{
               "name": "Test Event",
               "production_targets": [{
                   "recipe_slug": "universal-recipe",
                   "target_batches": 5
               }]
           }]
           (tmp_path / "events.json").write_text(json.dumps(data))

           from src.services.coordinated_export_service import import_entity
           import_entity("events", tmp_path, session)

           target = session.query(EventProductionTarget).first()
           assert target.recipe_id == recipe_with_slug.id

       def test_recipe_component_resolves_slug(self, session, tmp_path, recipe_with_slug):
           """Test RecipeComponent import resolves component_recipe by slug."""
           # Create parent recipe
           parent = Recipe(name="Parent", slug="parent-recipe")
           session.add(parent)
           session.commit()

           data = [{
               "name": "Parent",
               "slug": "parent-recipe",
               "components": [{
                   "component_recipe_slug": "universal-recipe",
                   "quantity": 1.0,
                   "unit": "batch"
               }]
           }]
           (tmp_path / "recipes.json").write_text(json.dumps(data))

           from src.services.catalog_import_service import import_recipes
           import_recipes(tmp_path, session, import_mode="AUGMENT")

           # Reload parent to get component
           session.refresh(parent)
           assert len(parent.components) >= 1
           assert parent.components[0].component_recipe_id == recipe_with_slug.id

       def test_missing_recipe_slug_skips_record(self, session, tmp_path, caplog):
           """Test missing recipe slug causes record to be skipped with log."""
           import logging
           caplog.set_level(logging.ERROR)

           data = [{
               "display_name": "Orphan FU",
               "slug": "orphan-fu",
               "recipe_slug": "nonexistent-recipe",
           }]
           (tmp_path / "finished_units.json").write_text(json.dumps(data))

           from src.services.coordinated_export_service import import_entity
           import_entity("finished_units", tmp_path, session)

           # Verify record was NOT created
           fu = session.query(FinishedUnit).filter(FinishedUnit.slug == "orphan-fu").first()
           assert fu is None

           # Verify error was logged
           assert "not found" in caplog.text.lower() or "nonexistent" in caplog.text.lower()
   ```

**Files**:
- `src/tests/test_recipe_slug_integration.py` (modify)

**Notes**:
- Tests each FK entity type independently
- Verifies error handling for missing recipes
- Uses caplog fixture to verify logging

---

## Test Strategy

**Run all integration tests**:
```bash
./run-tests.sh src/tests/test_recipe_slug_integration.py -v
```

**Run with coverage**:
```bash
./run-tests.sh src/tests/test_recipe_slug_integration.py -v --cov=src/services
```

**Expected test count**: ~15-20 tests across 4 test classes

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Flaky tests due to ordering | Use deterministic test data, explicit cleanup |
| Slow tests | Use in-memory SQLite, minimal test data |
| Import function names may differ | Check actual function signatures before testing |
| Missing fixtures | Follow existing test patterns in codebase |

---

## Definition of Done Checklist

- [ ] T026: Round-trip export/import test passes
- [ ] T027: Legacy import (name fallback) tests pass
- [ ] T028: Previous_slug fallback tests pass
- [ ] T029: All FK entity resolution tests pass
- [ ] All tests run consistently (no flaky failures)
- [ ] Test coverage for slug-related code > 80%
- [ ] Tests documented with clear assertions

---

## Review Guidance

**Reviewers should verify**:
1. Tests cover all Success Criteria from spec.md
2. Round-trip test is comprehensive (all entity types)
3. Legacy compatibility verified (pre-F080 exports)
4. Error cases handled (missing recipes, invalid slugs)
5. Tests are deterministic and fast

---

## Activity Log

- 2026-01-28T07:45:00Z – system – lane=planned – Prompt created.
