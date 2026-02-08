---
work_package_id: "WP08"
subtasks:
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
title: "Bulk Import Auto-Generation"
phase: "Phase 3 - Integration"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP03"]
history:
  - timestamp: "2026-02-08T17:14:59Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - Bulk Import Auto-Generation

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` above.

---

## Review Feedback

*[Empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP08 --base WP03
```

Depends on WP03 (auto-creation functions).

---

## Objectives & Success Criteria

Extend bulk recipe import to auto-generate FinishedUnit + bare FinishedGood pairs for each EA-yield recipe during import. Delivers User Story 5 (P3).

**Success criteria:**
- Each imported EA-yield recipe gets a FU + bare FG pair
- Import operates within single transaction (all or nothing)
- Duplicate names are disambiguated
- Existing import behavior preserved for non-EA recipes
- Performance acceptable for 100+ recipes

## Context & Constraints

**Key documents:**
- Spec: `kitty-specs/098-auto-generation-finished-goods/spec.md` (User Story 5)
- Research: `kitty-specs/098-auto-generation-finished-goods/research.md` (Question 7)

**Current import code:**
- `src/services/catalog_import_service.py` — `_import_recipes_impl()` (lines 1077-1276)
- Already operates within single session
- Creates Recipe + RecipeIngredients + RecipeComponents
- Does NOT currently create FinishedUnits or FinishedGoods
- Import data includes `yield_types` in recipe data (check JSON structure)

**Import data structure to study:**
- Find test fixtures or example import JSON to understand the yield_types format
- Check if `yield_types` is included in import/export data

## Subtasks & Detailed Guidance

### Subtask T042 - Extend import to create FUs during recipe import

**Purpose**: After creating a recipe during import, create its FinishedUnits from the yield_types data.

**Steps**:
1. Read `src/services/catalog_import_service.py` `_import_recipes_impl()` thoroughly
2. Identify where yield_types data is available in the import JSON:
   - Check existing import fixtures/examples for structure
   - Look for `yield_types`, `finished_units`, or similar keys
3. After recipe creation in the import loop, create FUs:
   ```python
   # After: session.add(recipe) + session.flush()
   yield_types_data = item.get("yield_types", [])
   for yt in yield_types_data:
       if yt.get("yield_type") == "EA":
           fu = create_finished_unit(
               display_name=yt["display_name"],
               recipe_id=recipe.id,
               yield_type=yt["yield_type"],
               items_per_batch=yt.get("items_per_batch", 1.0),
               item_unit=yt.get("item_unit"),
               session=session
           )
   ```
4. Pass the session from the import to FU creation (already available)

**Files**: `src/services/catalog_import_service.py`
**Notes**: The import may already handle FUs — check carefully before adding. Also check the export side to ensure yield_types are included in export data.

### Subtask T043 - Add auto-generation of bare FGs within import

**Purpose**: For each EA-yield FU created during import, auto-create a bare FG.

**Steps**:
1. After creating each FU in the import loop:
   ```python
   # After FU creation:
   existing_fg = find_bare_fg_for_unit(fu.id, session=session)
   if existing_fg is None:
       auto_create_bare_finished_good(
           finished_unit_id=fu.id,
           display_name=fu.display_name,
           category=fu.category,
           session=session
       )
   ```
2. Import `find_bare_fg_for_unit` and `auto_create_bare_finished_good` from `finished_good_service`
3. The session is already available in the import context — pass it through

**Files**: `src/services/catalog_import_service.py`
**Notes**: Check for existing bare FGs before creating (import may be re-importing data that already has FGs).

### Subtask T044 - Handle duplicate names during bulk creation

**Purpose**: When importing many recipes with similar names, ensure FG names/slugs remain unique.

**Steps**:
1. The slug generation with retry logic (from `finished_good_service`) handles uniqueness
2. Verify it works within a single session (slugs checked against DB + pending session objects)
3. If imported recipes have identical names, FGs get disambiguated slugs (e.g., `chocolate-cake`, `chocolate-cake-2`)
4. Test with a batch of identically-named recipes

**Files**: `src/services/catalog_import_service.py`
**Notes**: The `session.flush()` between iterations may be needed to make newly-created slugs visible for uniqueness checks.

### Subtask T045 - Write tests: bulk import with auto-generation

**Purpose**: Verify bulk import creates FU + bare FG pairs correctly.

**Steps**:
1. Test: import 5 recipes with EA yields → 5 FU + 5 bare FG pairs created
2. Test: import mix of EA and non-EA recipes → only EA recipes get FGs
3. Test: import recipes without yield_types data → recipes created, no FUs/FGs (backward compatible)
4. Test: verify all records in same transaction

**Files**: `src/tests/test_catalog_import_service.py`
**Notes**: Use existing import test fixtures as base. May need to extend fixtures with yield_types data.

### Subtask T046 - Write tests: rollback and duplicate handling

**Purpose**: Verify transactional integrity and duplicate name handling.

**Steps**:
1. Test: if one recipe fails validation, entire import rolls back (no FUs/FGs from successful recipes remain)
2. Test: duplicate recipe names → FG slugs are disambiguated
3. Test: re-import same data → no duplicate FGs created (existing FGs detected and skipped)
4. Test: import 100+ recipes (performance sanity check — should complete in reasonable time)

**Files**: `src/tests/test_catalog_import_service.py`

## Test Strategy

- **Run**: `./run-tests.sh -v -k "import" `
- **Full suite**: `./run-tests.sh -v`
- **Fixtures**: Extend existing import test data with yield_types

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Import JSON doesn't include yield_types | Check export side — may need to add to export first |
| Performance with 100+ recipes | Single session commit at end — batch should be fast |
| Slug uniqueness within batch | `session.flush()` between iterations or batch check |

## Definition of Done Checklist

- [ ] Import creates FUs from yield_types data
- [ ] Import auto-creates bare FGs for EA-yield FUs
- [ ] Duplicate names handled (disambiguated)
- [ ] Transactional integrity maintained (all or nothing)
- [ ] Backward compatible (recipes without yield_types still import)
- [ ] Tests cover bulk creation, rollback, and duplicates
- [ ] Full test suite passes

## Review Guidance

- Verify import JSON structure matches expected yield_types format
- Verify session is passed through all calls (no nested session_scope)
- Verify backward compatibility (existing import tests pass)
- Check that export includes yield_types data (for round-trip)

## Activity Log

- 2026-02-08T17:14:59Z - system - lane=planned - Prompt created.
