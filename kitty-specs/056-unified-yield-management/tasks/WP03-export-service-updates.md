---
work_package_id: "WP03"
subtasks:
  - "T009"
  - "T010"
  - "T011"
title: "Export Service Updates"
phase: "Phase 3 - Import/Export Service Updates"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "N/A"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-16T22:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Export Service Updates

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Enable export of FinishedUnits in coordinated backup/export operations so that data can be preserved and restored.

**Success Criteria**:
1. Export includes `finished_units.json` file with all FinishedUnit records
2. Export fields include: uuid, slug, display_name, recipe_name, category, yield_mode, items_per_batch, item_unit, batch_percentage, portion_description, inventory_count, is_archived
3. Recipe reference uses `recipe_name` for lookup during import
4. Existing export functionality continues to work
5. Tests verify FinishedUnit export structure and content

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/056-unified-yield-management/spec.md`
- Plan: `kitty-specs/056-unified-yield-management/plan.md`
- Data Model: `kitty-specs/056-unified-yield-management/data-model.md`
- Research: `kitty-specs/056-unified-yield-management/research.md`

**Architectural Constraints**:
- Layered architecture: Services handle export logic
- Constitution VI: Export must preserve all data for later import
- Follow existing patterns in `coordinated_export_service.py`

**Key Design Decision**: FinishedUnits are exported after recipes in dependency order because they reference recipes.

## Subtasks & Detailed Guidance

### Subtask T009 – Add _export_finished_units() function to coordinated_export_service.py

**Purpose**: Create the export function that serializes FinishedUnit records to JSON.

**Steps**:
1. Open `src/services/coordinated_export_service.py`
2. Locate the existing export functions (e.g., `_export_recipes()`)
3. Add new function following the same pattern:
   ```python
   def _export_finished_units(session, export_path: Path) -> int:
       """
       Export all FinishedUnit records to JSON.

       Args:
           session: SQLAlchemy session
           export_path: Directory to write finished_units.json

       Returns:
           Number of records exported
       """
       from src.models.finished_unit import FinishedUnit

       finished_units = session.query(FinishedUnit).all()

       data = []
       for fu in finished_units:
           record = {
               'uuid': str(fu.uuid) if fu.uuid else None,
               'slug': fu.slug,
               'display_name': fu.display_name,
               'recipe_name': fu.recipe.name if fu.recipe else None,
               'category': fu.category,
               'yield_mode': fu.yield_mode.value if fu.yield_mode else None,
               'items_per_batch': fu.items_per_batch,
               'item_unit': fu.item_unit,
               'batch_percentage': float(fu.batch_percentage) if fu.batch_percentage else None,
               'portion_description': fu.portion_description,
               'inventory_count': fu.inventory_count,
               'is_archived': fu.is_archived
           }
           data.append(record)

       output_file = export_path / 'finished_units.json'
       with open(output_file, 'w', encoding='utf-8') as f:
           json.dump(data, f, indent=2, ensure_ascii=False)

       return len(data)
   ```
4. Add necessary imports at top of file if not present

**Files**: `src/services/coordinated_export_service.py`
**Parallel?**: No (blocking change)
**Notes**: Follow existing export function patterns for consistency.

### Subtask T010 – Add "finished_units" to DEPENDENCY_ORDER after "recipes"

**Purpose**: Ensure FinishedUnits are exported in correct order relative to recipes.

**Steps**:
1. Open `src/services/coordinated_export_service.py`
2. Locate `DEPENDENCY_ORDER` constant (should be near top of file)
3. Add "finished_units" after "recipes":
   ```python
   DEPENDENCY_ORDER = [
       "suppliers",
       "ingredients",
       "products",
       "recipes",
       "finished_units",  # NEW: Must be after recipes
       "material_categories",
       "material_subcategories",
       "materials",
       "material_products",
       # ... rest of order
   ]
   ```
4. Locate the export dispatch logic and add handling for "finished_units":
   ```python
   elif entity_type == "finished_units":
       count = _export_finished_units(session, export_path)
   ```

**Files**: `src/services/coordinated_export_service.py`
**Parallel?**: No (depends on T009)
**Notes**: Dependency order is critical for import to work correctly.

### Subtask T011 – Add tests for FinishedUnit export

**Purpose**: Ensure export functionality works correctly with comprehensive test coverage.

**Steps**:
1. Open `src/tests/services/test_coordinated_export.py`
2. Add test class for FinishedUnit export:
   ```python
   class TestFinishedUnitExport:
       """Tests for FinishedUnit export functionality."""

       def test_export_finished_units_creates_file(self, session, tmp_path):
           """Export should create finished_units.json file."""
           # Setup: Create a recipe and finished unit
           from src.models.recipe import Recipe
           from src.models.finished_unit import FinishedUnit
           from src.models.finished_unit import YieldMode

           recipe = Recipe(
               name="Test Recipe",
               slug="test_recipe",
               category="test",
               yield_quantity=12,
               yield_unit="each"
           )
           session.add(recipe)
           session.flush()

           fu = FinishedUnit(
               recipe_id=recipe.id,
               slug="test_recipe_standard",
               display_name="Standard Test Recipe",
               yield_mode=YieldMode.DISCRETE_COUNT,
               items_per_batch=12,
               item_unit="cookie"
           )
           session.add(fu)
           session.flush()

           # Execute
           count = _export_finished_units(session, tmp_path)

           # Verify
           assert count == 1
           assert (tmp_path / 'finished_units.json').exists()

       def test_export_finished_units_contains_required_fields(self, session, tmp_path):
           """Exported JSON should contain all required fields."""
           # Setup: Create recipe and finished unit
           # ... similar to above

           # Execute
           _export_finished_units(session, tmp_path)

           # Verify
           with open(tmp_path / 'finished_units.json') as f:
               data = json.load(f)

           assert len(data) == 1
           record = data[0]
           assert 'slug' in record
           assert 'display_name' in record
           assert 'recipe_name' in record
           assert 'yield_mode' in record
           assert 'items_per_batch' in record
           assert 'item_unit' in record

       def test_export_finished_units_uses_recipe_name(self, session, tmp_path):
           """Export should use recipe.name for recipe_name field."""
           # Setup: Create recipe with specific name
           # ... setup code

           # Execute
           _export_finished_units(session, tmp_path)

           # Verify
           with open(tmp_path / 'finished_units.json') as f:
               data = json.load(f)

           assert data[0]['recipe_name'] == "Test Recipe"
   ```

**Files**: `src/tests/services/test_coordinated_export.py`
**Parallel?**: Yes (can proceed alongside T009/T010)
**Notes**: May need to import `_export_finished_units` or test via public API.

## Test Strategy

**Required Tests**:
1. Export creates `finished_units.json` file
2. Export contains all required fields
3. Export uses `recipe_name` (not `recipe_id`) for FK reference
4. Export handles empty FinishedUnit table gracefully
5. Export handles null fields correctly
6. Dependency order includes "finished_units" after "recipes"

**Commands**:
```bash
./run-tests.sh src/tests/services/test_coordinated_export.py -v
./run-tests.sh -v --cov=src/services/coordinated_export_service
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing recipe reference | Use recipe.name as FK lookup key; handle None gracefully |
| Enum serialization issues | Use `.value` to convert YieldMode to string |
| Decimal serialization | Convert batch_percentage to float for JSON |

## Definition of Done Checklist

- [ ] T009: `_export_finished_units()` function exists and works
- [ ] T010: "finished_units" added to DEPENDENCY_ORDER after "recipes"
- [ ] T011: Tests written and passing for export functionality
- [ ] Existing export tests still pass
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Checkpoints**:
1. Verify export function follows existing patterns
2. Verify dependency order is correct (after recipes)
3. Verify all required fields are exported
4. Verify recipe reference uses name, not id

## Activity Log

- 2026-01-16T22:00:00Z – system – lane=planned – Prompt created.
- 2026-01-17T03:19:28Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-17T03:32:58Z – claude – lane=for_review – All subtasks complete: T009-T011. Export function added, dependency order updated, and tests added.
- 2026-01-17T17:59:40Z – claude – lane=doing – Starting review
- 2026-01-17T18:00:18Z – claude – lane=done – Review passed: Export function exists with all required fields. Dependency order correct (after recipes). 5 tests pass. Recipe reference uses name correctly.
