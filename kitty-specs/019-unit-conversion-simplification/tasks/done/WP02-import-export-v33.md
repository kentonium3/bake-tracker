---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Import/Export v3.3 Update"
phase: "Phase 2 - Service Updates"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "22254"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Import/Export v3.3 Update

## Objectives & Success Criteria

- Remove all `unit_conversions` handling from import/export service
- Update format version from 3.2 to 3.3
- Remove `recipe_unit` field from ingredient export/import
- Reject v3.2 files with clear error message

**Success Test**:
1. Export produces JSON with `"version": "3.3"` and no `unit_conversions` key
2. Importing a v3.2 file raises `ImportVersionError`

## Context & Constraints

- **Spec**: `kitty-specs/019-unit-conversion-simplification/spec.md` (FR-003, FR-005)
- **Plan**: `kitty-specs/019-unit-conversion-simplification/plan.md`
- **Depends on**: WP01 (UnitConversion model must be deleted first)

**Current v3.2 Structure** (to be removed):
```json
{
  "version": "3.2",
  "ingredients": [{"slug": "...", "recipe_unit": "cup", ...}],
  "unit_conversions": [{"ingredient_slug": "...", "from_unit": "lb", ...}]
}
```

**New v3.3 Structure**:
```json
{
  "version": "3.3",
  "ingredients": [{"slug": "...", ...}]  // No recipe_unit field
  // No unit_conversions array
}
```

## Subtasks & Detailed Guidance

### Subtask T005 – Remove UnitConversion import

- **Purpose**: Remove the import of the deleted model.
- **Steps**:
  1. Open `src/services/import_export_service.py`
  2. Find and delete: `from src.models.unit_conversion import UnitConversion` (line ~24)
- **Files**: `src/services/import_export_service.py` (EDIT)
- **Parallel?**: No - must be first
- **Notes**: This will cause errors until the rest of the cleanup is done.

### Subtask T006 – Remove unit_conversions export logic

- **Purpose**: Stop exporting unit_conversions array.
- **Steps**:
  1. Find the export function (likely `export_all_to_json_v3` or similar)
  2. Remove initialization of `unit_conversions` in export_data dict (~line 1020)
  3. Remove the loop that populates unit_conversions (~lines 1180-1185)
  4. Remove the count logging for unit_conversions (~lines 1325, 1349)
- **Files**: `src/services/import_export_service.py` (EDIT)
- **Parallel?**: Yes - can be done with T007
- **Notes**: Search for `unit_conversion` (singular and plural) to find all references.

### Subtask T007 – Remove unit_conversions import logic

- **Purpose**: Stop importing unit_conversions from JSON files.
- **Steps**:
  1. Find the import section that handles unit_conversions (~lines 2300-2330)
  2. Delete the entire `if "unit_conversions" in data:` block
  3. Remove any references to unit_conversion in the import dependency order comments
- **Files**: `src/services/import_export_service.py` (EDIT)
- **Parallel?**: Yes - can be done with T006
- **Notes**: The comment at ~line 2205 lists import order - update to remove unit_conversions.

### Subtask T008 – Update version constant to 3.3

- **Purpose**: Change the required version for import/export.
- **Steps**:
  1. Find the version check in `import_all_from_json_v3` (~line 2245)
  2. Change `if version != "3.2":` to `if version != "3.3":`
  3. Update the error message to say "requires v3.3 format"
  4. Find the export version assignment and change `"3.2"` to `"3.3"`
- **Files**: `src/services/import_export_service.py` (EDIT)
- **Parallel?**: No - should be done after T006/T007
- **Notes**: Search for `"3.2"` to find all version references.

### Subtask T009 – Remove recipe_unit from ingredient export

- **Purpose**: Stop exporting the recipe_unit field for ingredients.
- **Steps**:
  1. Find where ingredient data is assembled for export
  2. Remove any line that includes `"recipe_unit": ingredient.recipe_unit` or similar
  3. Search for `recipe_unit` in the export function to ensure complete removal
- **Files**: `src/services/import_export_service.py` (EDIT)
- **Parallel?**: No
- **Notes**: The field may be in a dict comprehension or explicit assignment.

### Subtask T010 – Remove recipe_unit from ingredient import

- **Purpose**: Stop expecting recipe_unit field during import.
- **Steps**:
  1. Find where Ingredient objects are created during import
  2. Remove any `recipe_unit=ing.get("recipe_unit")` or similar parameter
  3. Search for `recipe_unit` in the import section to ensure complete removal
- **Files**: `src/services/import_export_service.py` (EDIT)
- **Parallel?**: No
- **Notes**: The import may use a dict or explicit parameters - check both patterns.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking change for users | Clear error message directing to re-export |
| Incomplete removal | Grep for `unit_conversion` and `recipe_unit` after changes |
| Export format regression | Manual test export and inspect JSON |

## Definition of Done Checklist

- [ ] No `UnitConversion` import in file
- [ ] Export produces no `unit_conversions` key in JSON
- [ ] Export produces `"version": "3.3"`
- [ ] Import rejects v3.2 files with clear error
- [ ] No `recipe_unit` in exported ingredient data
- [ ] No `recipe_unit` handling in import logic
- [ ] `grep -r "unit_conversion" src/services/import_export_service.py` returns nothing

## Review Guidance

- Test export and inspect JSON output manually
- Test import of a v3.2 file - should fail with version error
- Verify no orphaned references to removed functionality
- Check that ingredient export/import still works correctly

## Activity Log

- 2025-12-14T12:00:00Z – system – lane=planned – Prompt created.
- 2025-12-14T07:38:23Z – claude – shell_pid=22254 – lane=doing – Moved to doing
- 2025-12-14T19:51:27Z – claude – shell_pid=22254 – lane=for_review – Implementation complete, ready for review
- 2025-12-14T19:52:56Z – claude – shell_pid=22254 – lane=done – Code review APPROVED: v3.3 format, UnitConversion removed, recipe_unit removed
