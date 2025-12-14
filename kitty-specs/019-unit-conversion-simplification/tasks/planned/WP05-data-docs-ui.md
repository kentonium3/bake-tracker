---
work_package_id: "WP05"
subtasks:
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
title: "Data Files, Documentation & UI Cleanup"
phase: "Phase 4 - Finalization"
lane: "planned"
assignee: ""
agent: "claude-opus-4-5-20251101"
shell_pid: ""
review_status: "has_feedback"
reviewed_by: "claude-opus-4-5-20251101"
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

## Review Feedback

**Status**: ❌ **Needs Changes**

**Key Issues**:
1. `docs/design/import_export_specification.md` has stale `unit_conversions` references:
   - Line 586: In import dependency order list (should be removed)
   - Line 644: In referential integrity rules (should be removed)
   - Lines 790-797: In sample JSON example (should be removed)

2. `docs/feature_proposal_catalog_import.md` still has `unit_conversions` examples:
   - Lines 323 and 352: JSON examples include `unit_conversions` array

**What Was Done Well**:
- ✅ `sample_data.json` correctly updated to v3.3 with no `unit_conversions`
- ✅ `import_export_specification.md` header, changelog, and entity definitions correctly updated
- ✅ `inventory_tab.py` UI display fixed for multi-unit totals
- ✅ All 706 tests pass (12 expected skips)
- ✅ `recipe_unit` references in UI are valid variable/parameter names (not `Ingredient.recipe_unit`)

**Action Items** (must complete before re-review):
- [ ] Remove `unit_conversions` from import dependency order in `import_export_specification.md`
- [ ] Remove `unit_conversions` from referential integrity rules in `import_export_specification.md`
- [ ] Remove `unit_conversions` from sample JSON in `import_export_specification.md`
- [ ] Update `feature_proposal_catalog_import.md` to remove `unit_conversions` from examples

**Notes**:
- `baking_ingredients_v32.json` doesn't exist in worktree (only in main repo) - will be handled at merge
- `catalog_import_status.md` doesn't exist in worktree - out of scope
- Archive files with `unit_conversions` are acceptable (they're archived historical content)

---

# Work Package Prompt: WP05 – Data Files, Documentation & UI Cleanup

## Objectives & Success Criteria

- Convert test data files to v3.3 format
- Update all documentation to reference v3.3
- Remove recipe_unit references from UI files
- Consistent documentation across all affected files

**Success Test**:
1. JSON files parse correctly and have `"version": "3.3"`
2. No documentation references v3.2 or unit_conversions
3. Application runs without UI errors

## Context & Constraints

- **Spec**: `kitty-specs/019-unit-conversion-simplification/spec.md` (SC-004)
- **Plan**: `kitty-specs/019-unit-conversion-simplification/plan.md`
- **Depends on**: WP01-WP04 (all code changes complete)

**Test Data Files**:
- `test_data/baking_ingredients_v32.json` (160 ingredients, 69 unit_conversions)
- `test_data/sample_data.json` (if applicable)

**Documentation Files**:
- `docs/import_export_specification.md`
- `docs/feature_proposal_catalog_import.md`
- `docs/catalog_import_status.md`

**UI Files to Review**:
- `src/ui/inventory_tab.py`
- `src/ui/forms/recipe_form.py`
- `src/ui/event_detail_window.py`

## Subtasks & Detailed Guidance

### Subtask T024 – Convert baking_ingredients JSON to v3.3

- **Purpose**: Update the main ingredient catalog to new format.
- **Steps**:
  1. Open `test_data/baking_ingredients_v32.json`
  2. Change `"version": "3.2"` to `"version": "3.3"`
  3. Delete the entire `"unit_conversions": [...]` array
  4. For each ingredient in the `"ingredients"` array, remove the `"recipe_unit"` field if present
  5. Rename file to `baking_ingredients_v33.json` (or keep name if preferred)
  6. Validate JSON: `python -c "import json; json.load(open('test_data/baking_ingredients_v33.json'))"`
- **Files**: `test_data/baking_ingredients_v32.json` (EDIT/RENAME)
- **Parallel?**: No - primary data file
- **Notes**: The file has 69 unit_conversions to remove. Ingredients may or may not have recipe_unit - remove if present.

### Subtask T025 – Update sample_data.json

- **Purpose**: Update sample data if it contains unit_conversions.
- **Steps**:
  1. Check if `test_data/sample_data.json` exists and contains unit_conversions
  2. If yes: update version, remove unit_conversions array, remove recipe_unit from ingredients
  3. If no unit_conversions present: just update version number
  4. Validate JSON after changes
- **Files**: `test_data/sample_data.json` (EDIT if applicable)
- **Parallel?**: Yes
- **Notes**: This may be a smaller test file - changes should be minimal.

### Subtask T026 – Update import_export_specification.md

- **Purpose**: Document the v3.3 format specification.
- **Steps**:
  1. Open `docs/import_export_specification.md`
  2. Update version references from 3.2 to 3.3
  3. Remove the `unit_conversions` section from the schema documentation
  4. Remove `recipe_unit` from the ingredient field documentation
  5. Add a note about backward compatibility (v3.2 no longer supported)
  6. Update any examples to show v3.3 format
- **Files**: `docs/import_export_specification.md` (EDIT)
- **Parallel?**: Yes
- **Notes**: This is the authoritative format documentation.

### Subtask T027 – Update catalog_import proposal

- **Purpose**: Remove UnitConversion references from the catalog import proposal.
- **Steps**:
  1. Open `docs/feature_proposal_catalog_import.md`
  2. Search for `UnitConversion` and `unit_conversion`
  3. Remove or update sections that discuss unit conversion import
  4. Update any format examples to v3.3
  5. Simplify scope description (no longer need to handle conversions)
- **Files**: `docs/feature_proposal_catalog_import.md` (EDIT)
- **Parallel?**: Yes
- **Notes**: This proposal was written before the simplification - update to reflect new reality.

### Subtask T028 – Update catalog_import_status.md

- **Purpose**: Note the format change and update resume checklist.
- **Steps**:
  1. Open `docs/catalog_import_status.md`
  2. Update the "Known Gap" section - unit conversions are no longer needed
  3. Update the "Resume Checklist" to reflect v3.3 format
  4. Note that the 69 unit_conversions in the original file will be removed
  5. Update any file references if renamed to v33
- **Files**: `docs/catalog_import_status.md` (EDIT)
- **Parallel?**: Yes
- **Notes**: This file was created earlier today - update to reflect this feature.

### Subtask T029 – Clean inventory_tab.py

- **Purpose**: Remove recipe_unit references from UI.
- **Steps**:
  1. Open `src/ui/inventory_tab.py`
  2. Grep for `recipe_unit`
  3. Remove any UI elements that display or edit recipe_unit
  4. Update any form fields that include recipe_unit
- **Files**: `src/ui/inventory_tab.py` (EDIT)
- **Parallel?**: Yes
- **Notes**: Changes may be minimal - assess impact before modifying.

### Subtask T030 – Clean recipe_form.py

- **Purpose**: Remove recipe_unit references from recipe form.
- **Steps**:
  1. Open `src/ui/forms/recipe_form.py`
  2. Grep for `recipe_unit`
  3. Remove any form fields or displays related to recipe_unit
  4. Recipes use RecipeIngredient.unit, so recipe_unit may not be heavily used here
- **Files**: `src/ui/forms/recipe_form.py` (EDIT)
- **Parallel?**: Yes
- **Notes**: This form handles recipe creation - likely minimal impact.

### Subtask T031 – Clean event_detail_window.py

- **Purpose**: Remove recipe_unit references from event detail UI.
- **Steps**:
  1. Open `src/ui/event_detail_window.py`
  2. Grep for `recipe_unit`
  3. Remove any displays or calculations using recipe_unit
- **Files**: `src/ui/event_detail_window.py` (EDIT)
- **Parallel?**: Yes
- **Notes**: Event details aggregate recipe data - check unit displays.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| JSON syntax error | Validate after editing |
| Documentation inconsistency | Search all docs for "3.2" |
| UI breaks | Test application startup and navigation |

## Definition of Done Checklist

- [ ] `test_data/baking_ingredients_v33.json` exists with correct format
- [ ] No `unit_conversions` in any test data files
- [ ] `docs/import_export_specification.md` documents v3.3
- [ ] `docs/feature_proposal_catalog_import.md` updated
- [ ] `docs/catalog_import_status.md` reflects v3.3 format
- [ ] No `recipe_unit` references in UI files
- [ ] `grep -r "3.2" docs/` returns no format references
- [ ] Application starts and runs without errors

## Review Guidance

- Verify JSON files are valid (run python json.load)
- Check documentation for consistent v3.3 references
- Test UI navigation after changes
- Ensure catalog_import_status.md checklist is current

## Activity Log

- 2025-12-14T12:00:00Z – system – lane=planned – Prompt created.
- 2025-12-14T08:16:44Z – system – shell_pid= – lane=for_review – Moving to for_review for code review
- 2025-12-14T08:22:00Z – claude-opus-4-5-20251101 – lane=planned – Code review: NEEDS CHANGES. Found stale unit_conversions references in import_export_specification.md (lines 586, 644, 790-797) and feature_proposal_catalog_import.md (lines 323, 352). Tests pass (706/706). See Review Feedback section for action items.
