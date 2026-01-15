---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Service Layer Refactoring"
phase: "Phase 1 - Service Layer"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-15T13:35:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Service Layer Refactoring

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Rename all `*_VIEW_*` constants to `*_CONTEXT_RICH_*` naming convention
- Rename all `export_*_view()` methods to `export_*_context_rich()` naming convention
- Change file prefix from `view_` to `aug_` in all context-rich export file naming
- All existing export functionality continues to work with new names
- All callers updated to use new method names

**Success**: After this WP, running any context-rich export produces a file named `aug_<entity>.json` instead of `view_<entity>.json`.

## Context & Constraints

**File to modify**: `src/services/denormalized_export_service.py`
**Caller to update**: `src/ui/import_export_dialog.py` (method calls)

**Reference**:
- `kitty-specs/053-context-rich-export-fixes/plan.md` - Implementation approach
- `kitty-specs/053-context-rich-export-fixes/research.md` - Current implementation details

**Constraint**: Maintain backward compatibility in method signatures (only rename, don't change parameters).

## Subtasks & Detailed Guidance

### Subtask T001 - Rename EDITABLE Constants

**Purpose**: Deprecate "view" terminology in constant names.

**Steps**:
1. Open `src/services/denormalized_export_service.py`
2. Find all constants ending in `_VIEW_EDITABLE` (e.g., `PRODUCTS_VIEW_EDITABLE`, `INGREDIENTS_VIEW_EDITABLE`, etc.)
3. Rename each to `*_CONTEXT_RICH_EDITABLE`
4. Update all references to these constants within the file

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes - can proceed alongside T002

**Expected constants to rename**:
- `PRODUCTS_VIEW_EDITABLE` -> `PRODUCTS_CONTEXT_RICH_EDITABLE`
- `INGREDIENTS_VIEW_EDITABLE` -> `INGREDIENTS_CONTEXT_RICH_EDITABLE`
- `MATERIALS_VIEW_EDITABLE` -> `MATERIALS_CONTEXT_RICH_EDITABLE`
- `RECIPES_VIEW_EDITABLE` -> `RECIPES_CONTEXT_RICH_EDITABLE`
- `INVENTORY_VIEW_EDITABLE` -> `INVENTORY_CONTEXT_RICH_EDITABLE`
- `PURCHASES_VIEW_EDITABLE` -> `PURCHASES_CONTEXT_RICH_EDITABLE`
- (Plus any others found)

### Subtask T002 - Rename READONLY Constants

**Purpose**: Deprecate "view" terminology in constant names.

**Steps**:
1. Find all constants ending in `_VIEW_READONLY`
2. Rename each to `*_CONTEXT_RICH_READONLY`
3. Update all references to these constants within the file

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes - can proceed alongside T001

**Expected constants to rename**:
- `PRODUCTS_VIEW_READONLY` -> `PRODUCTS_CONTEXT_RICH_READONLY`
- `INGREDIENTS_VIEW_READONLY` -> `INGREDIENTS_CONTEXT_RICH_READONLY`
- (etc., matching pattern from T001)

### Subtask T003 - Rename Export Methods

**Purpose**: Deprecate "view" terminology in method names.

**Steps**:
1. Find all methods named `export_*_view()`
2. Rename each to `export_*_context_rich()`
3. Update internal calls (e.g., if `export_all_views()` calls other methods)
4. Update callers in `src/ui/import_export_dialog.py`

**Files**:
- `src/services/denormalized_export_service.py` (method definitions)
- `src/ui/import_export_dialog.py` (callers)

**Parallel?**: No - depends on T001/T002 being complete

**Methods to rename**:
- `export_ingredients_view()` -> `export_ingredients_context_rich()`
- `export_materials_view()` -> `export_materials_context_rich()`
- `export_recipes_view()` -> `export_recipes_context_rich()`
- `export_products_view()` -> `export_products_context_rich()`
- `export_inventory_view()` -> `export_inventory_context_rich()`
- `export_purchases_view()` -> `export_purchases_context_rich()`
- `export_all_views()` -> `export_all_context_rich()`

### Subtask T004 - Change File Prefix

**Purpose**: Use "aug_" prefix for augmentation files instead of "view_".

**Steps**:
1. In each `export_*_context_rich()` method, find where the filename is constructed
2. Change the prefix from `view_` to `aug_`
3. Example: `f"view_{entity_type}.json"` becomes `f"aug_{entity_type}.json"`
4. If there's a `view_type` field in the JSON output, consider renaming it or leaving as-is (document decision)

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: No - should be done with T003 as they touch the same methods

**Notes**:
- Search for string `"view_"` to find all occurrences
- The prefix appears in the filename construction, likely using f-strings

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing a caller that uses old method names | Search entire codebase for old method names before marking complete |
| Breaking tests that reference old names | Search test files for old method/constant names |
| Inconsistent naming if some references missed | Use IDE/grep to verify no "view" references remain in export context |

## Definition of Done Checklist

- [ ] All `*_VIEW_EDITABLE` constants renamed to `*_CONTEXT_RICH_EDITABLE`
- [ ] All `*_VIEW_READONLY` constants renamed to `*_CONTEXT_RICH_READONLY`
- [ ] All `export_*_view()` methods renamed to `export_*_context_rich()`
- [ ] All callers in UI layer updated to use new method names
- [ ] File prefix changed from `view_` to `aug_` in all export methods
- [ ] No remaining references to old "view" naming in export-related code
- [ ] Application launches without import errors
- [ ] Context-rich export produces `aug_*.json` files

## Review Guidance

- Verify no "view" terminology remains in denormalized_export_service.py
- Verify UI callers updated
- Run the app and test one context-rich export to confirm `aug_` prefix works
- Check for any test files that need updating

## Activity Log

- 2026-01-15T13:35:00Z - system - lane=planned - Prompt created.
- 2026-01-15T18:40:40Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-15T19:09:45Z – unknown – lane=for_review – Service layer refactoring complete: renamed all view terminology to context-rich, updated tests
- 2026-01-15T21:04:54Z – agent – lane=doing – Started review via workflow command
- 2026-01-15T21:10:33Z – unknown – lane=done – Review passed: All constants renamed, methods renamed, file prefix changed to aug_, UI callers updated, tests updated
