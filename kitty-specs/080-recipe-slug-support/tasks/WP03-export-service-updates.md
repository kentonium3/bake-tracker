---
work_package_id: WP03
title: Export Service Updates
lane: "for_review"
dependencies: [WP02]
base_branch: 080-recipe-slug-support-WP02
base_commit: 61d5b75fb0427629d1d27c3bebc919877fdb2e39
created_at: '2026-01-28T16:58:11.308273+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Export/Import
assignee: ''
agent: "claude-opus"
shell_pid: "50556"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T07:45:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Export Service Updates

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP02
spec-kitty implement WP03 --base WP02
```

---

## Objectives & Success Criteria

**Objective**: Add `recipe_slug` to all recipe and FK entity exports while maintaining backward compatibility with `recipe_name`.

**Success Criteria**:
- [ ] `recipes.json` export includes `slug` and `previous_slug` fields
- [ ] Recipe component exports include `component_recipe_slug`
- [ ] `finished_units.json` exports include `recipe_slug` alongside `recipe_name`
- [ ] `events.json` production targets include `recipe_slug`
- [ ] `production_runs.json` exports include `recipe_slug`
- [ ] All existing `recipe_name` fields preserved (backward compatibility)
- [ ] Export tests verify slug fields present

---

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/080-recipe-slug-support/plan.md`
- Data Model: `kitty-specs/080-recipe-slug-support/data-model.md`

**Key File**: `src/services/coordinated_export_service.py`

**Pattern**: Dual-field export - always include both name AND slug for backward compatibility.

**Current Export Locations** (from research.md):
| Entity | Current Export | Line | Field to Add |
|--------|---------------|------|--------------|
| Recipe | `_export_recipes()` | ~343 | `slug`, `previous_slug` |
| RecipeComponent | nested in recipes | ~332 | `component_recipe_slug` |
| FinishedUnit | `_export_finished_units()` | ~677 | `recipe_slug` |
| EventProductionTarget | `_export_events()` | ~711 | `recipe_slug` |
| ProductionRun | `_export_production_runs()` | ~765 | `recipe_slug` |

---

## Subtasks & Detailed Guidance

### Subtask T013 – Add `slug`, `previous_slug` to Recipe Export

**Purpose**: Include portable identifiers in recipe exports.

**Steps**:
1. Open `src/services/coordinated_export_service.py`
2. Find `_export_recipes()` function (around line 302-362)
3. Locate the dictionary being appended to `records` (around line 343)
4. Add slug fields after `name`:
   ```python
   records.append(
       {
           "uuid": str(r.uuid) if r.uuid else None,
           "name": r.name,
           "slug": r.slug,  # ADD THIS
           "previous_slug": r.previous_slug,  # ADD THIS
           "category": r.category,
           "source": r.source,
           # ... rest of fields unchanged
       }
   )
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify)

**Notes**:
- Place `slug` immediately after `name` for logical grouping
- Both fields should be present even if `previous_slug` is None

---

### Subtask T014 – Add `component_recipe_slug` to Recipe Component Export

**Purpose**: Enable slug-based resolution for nested recipe references.

**Steps**:
1. In `_export_recipes()`, find the component export section (around line 332)
2. Look for where `component_recipe_name` is exported
3. Add `component_recipe_slug`:
   ```python
   components = []
   for rc in r.components:
       components.append(
           {
               "component_recipe_slug": (  # ADD THIS
                   rc.component_recipe.slug if rc.component_recipe else None
               ),
               "component_recipe_name": (  # Keep for backward compat
                   rc.component_recipe.name if rc.component_recipe else None
               ),
               "quantity": float(rc.quantity) if rc.quantity else None,
               "unit": rc.unit,
               # ... other fields
           }
       )
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify)

**Notes**:
- Add `component_recipe_slug` BEFORE `component_recipe_name` (slug is primary)
- Keep `component_recipe_name` for legacy import support

---

### Subtask T015 – Add `recipe_slug` to FinishedUnit Export

**Purpose**: Enable slug-based recipe resolution when importing finished units.

**Steps**:
1. Find `_export_finished_units()` function (around line 665-690)
2. Locate where `recipe_name` is exported (around line 677)
3. Add `recipe_slug` field:
   ```python
   records.append(
       {
           "uuid": str(fu.uuid) if fu.uuid else None,
           "slug": fu.slug,
           "display_name": fu.display_name,
           "recipe_slug": fu.recipe.slug if fu.recipe else None,  # ADD THIS
           "recipe_name": fu.recipe.name if fu.recipe else None,  # Keep for backward compat
           "category": fu.category,
           # ... rest unchanged
       }
   )
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify)

**Parallel**: Yes - can be done alongside T016, T017

---

### Subtask T016 – Add `recipe_slug` to EventProductionTarget Export

**Purpose**: Enable slug-based recipe resolution for event production targets.

**Steps**:
1. Find `_export_events()` function (around line 693-740)
2. Locate production targets export section (around line 708-715)
3. Add `recipe_slug` field:
   ```python
   production_targets = []
   for pt in e.production_targets:
       production_targets.append(
           {
               "recipe_slug": pt.recipe.slug if pt.recipe else None,  # ADD THIS
               "recipe_name": pt.recipe.name if pt.recipe else None,  # Keep
               "target_batches": pt.target_batches,
               "notes": pt.notes,
           }
       )
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify)

**Parallel**: Yes - can be done alongside T015, T017

---

### Subtask T017 – Add `recipe_slug` to ProductionRun Export

**Purpose**: Enable slug-based recipe resolution when importing production runs.

**Steps**:
1. Find `_export_production_runs()` function (around line 755-795)
2. Locate where `recipe_name` is exported (around line 765)
3. Add `recipe_slug` field:
   ```python
   records.append(
       {
           "uuid": str(r.uuid) if r.uuid else None,
           "recipe_slug": r.recipe.slug if r.recipe else None,  # ADD THIS
           "recipe_name": r.recipe.name if r.recipe else None,  # Keep
           "event_name": r.event.name if r.event else None,
           "quantity_planned": r.quantity_planned,
           "quantity_actual": r.quantity_actual,
           # ... rest unchanged
       }
   )
   ```

**Files**:
- `src/services/coordinated_export_service.py` (modify)

**Parallel**: Yes - can be done alongside T015, T016

---

### Subtask T018 – Add Unit Test for Export Changes

**Purpose**: Verify all exports include recipe_slug fields.

**Steps**:
1. Find or create export tests (check `src/tests/test_coordinated_export*.py` or `src/tests/test_import_export.py`)
2. Add test verifying slug fields in exports:
   ```python
   import json
   import pytest
   from pathlib import Path
   from src.services.coordinated_export_service import export_all_data


   class TestRecipeSlugExport:
       """Tests for recipe slug fields in exports."""

       def test_recipes_export_includes_slug(self, session, tmp_path):
           """Test recipes.json includes slug and previous_slug fields."""
           # Create a recipe
           from src.models.recipe import Recipe
           recipe = Recipe(name="Test Recipe", slug="test-recipe", previous_slug=None)
           session.add(recipe)
           session.commit()

           # Export
           export_all_data(tmp_path, session)

           # Verify
           recipes_file = tmp_path / "recipes.json"
           assert recipes_file.exists()
           data = json.loads(recipes_file.read_text())
           assert len(data) >= 1
           assert "slug" in data[0]
           assert data[0]["slug"] == "test-recipe"
           assert "previous_slug" in data[0]

       def test_finished_units_export_includes_recipe_slug(self, session, tmp_path):
           """Test finished_units.json includes recipe_slug field."""
           # Create recipe and finished unit
           from src.models.recipe import Recipe
           from src.models.finished_unit import FinishedUnit

           recipe = Recipe(name="Cookie Recipe", slug="cookie-recipe")
           session.add(recipe)
           session.flush()

           fu = FinishedUnit(
               display_name="Cookies",
               slug="cookies",
               recipe_id=recipe.id
           )
           session.add(fu)
           session.commit()

           # Export
           export_all_data(tmp_path, session)

           # Verify
           fu_file = tmp_path / "finished_units.json"
           data = json.loads(fu_file.read_text())
           assert "recipe_slug" in data[0]
           assert data[0]["recipe_slug"] == "cookie-recipe"
           assert "recipe_name" in data[0]  # Backward compat

       def test_events_export_includes_recipe_slug_in_targets(self, session, tmp_path):
           """Test events.json production targets include recipe_slug."""
           # Create event with production target
           from src.models.recipe import Recipe
           from src.models.event import Event, EventProductionTarget

           recipe = Recipe(name="Pie Recipe", slug="pie-recipe")
           session.add(recipe)

           event = Event(name="Holiday Event")
           session.add(event)
           session.flush()

           target = EventProductionTarget(
               event_id=event.id,
               recipe_id=recipe.id,
               target_batches=5
           )
           session.add(target)
           session.commit()

           # Export
           export_all_data(tmp_path, session)

           # Verify
           events_file = tmp_path / "events.json"
           data = json.loads(events_file.read_text())
           targets = data[0].get("production_targets", [])
           assert len(targets) >= 1
           assert "recipe_slug" in targets[0]
           assert targets[0]["recipe_slug"] == "pie-recipe"

       def test_production_runs_export_includes_recipe_slug(self, session, tmp_path):
           """Test production_runs.json includes recipe_slug field."""
           from src.models.recipe import Recipe
           from src.models.production_run import ProductionRun

           recipe = Recipe(name="Bread Recipe", slug="bread-recipe")
           session.add(recipe)
           session.flush()

           run = ProductionRun(
               recipe_id=recipe.id,
               quantity_planned=10
           )
           session.add(run)
           session.commit()

           # Export
           export_all_data(tmp_path, session)

           # Verify
           runs_file = tmp_path / "production_runs.json"
           data = json.loads(runs_file.read_text())
           assert "recipe_slug" in data[0]
           assert data[0]["recipe_slug"] == "bread-recipe"

       def test_recipe_components_include_slug(self, session, tmp_path):
           """Test recipe components include component_recipe_slug."""
           from src.models.recipe import Recipe, RecipeComponent

           # Create parent and component recipes
           component = Recipe(name="Dough", slug="dough")
           parent = Recipe(name="Bread", slug="bread")
           session.add_all([component, parent])
           session.flush()

           # Link as component
           rc = RecipeComponent(
               recipe_id=parent.id,
               component_recipe_id=component.id,
               quantity=1.0,
               unit="batch"
           )
           session.add(rc)
           session.commit()

           # Export
           export_all_data(tmp_path, session)

           # Verify
           recipes_file = tmp_path / "recipes.json"
           data = json.loads(recipes_file.read_text())

           # Find parent recipe
           parent_data = next(r for r in data if r["slug"] == "bread")
           components = parent_data.get("components", [])
           assert len(components) >= 1
           assert "component_recipe_slug" in components[0]
           assert components[0]["component_recipe_slug"] == "dough"
   ```

**Files**:
- `src/tests/test_export_recipe_slug.py` (create) or add to existing export tests

**Notes**:
- Tests may need fixtures for session and tmp_path
- Check existing test patterns in codebase for fixtures

---

## Test Strategy

**Run after implementation**:
```bash
./run-tests.sh src/tests/test_export*.py -v
./run-tests.sh src/tests/test_coordinated_export*.py -v
```

**Manual verification**:
```bash
# Start app, create some recipes, export via UI or CLI
# Check JSON files for slug fields
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing imports | Keep all `recipe_name` fields; slug is additive |
| Recipe without slug | Recipe model auto-generates slug; this shouldn't happen |
| Missing FK relationship | Check for None before accessing `.slug` |

---

## Definition of Done Checklist

- [ ] T013: `slug`, `previous_slug` added to recipe export
- [ ] T014: `component_recipe_slug` added to component export
- [ ] T015: `recipe_slug` added to finished_units export
- [ ] T016: `recipe_slug` added to event production targets
- [ ] T017: `recipe_slug` added to production_runs export
- [ ] T018: Export tests pass verifying slug fields
- [ ] All existing export tests still pass
- [ ] Code passes linting

---

## Review Guidance

**Reviewers should verify**:
1. All `recipe_name` fields preserved (backward compatibility)
2. New `recipe_slug` fields added before `recipe_name` in JSON
3. Null checks present for FK relationships (`.slug if .recipe else None`)
4. Tests cover all export locations
5. Manual export produces valid JSON with slug fields

---

## Activity Log

- 2026-01-28T07:45:00Z – system – lane=planned – Prompt created.
- 2026-01-28T17:02:54Z – claude-opus – shell_pid=50556 – lane=for_review – All T013-T018 subtasks implemented. 53 tests pass (46 existing export + 7 new slug tests).
