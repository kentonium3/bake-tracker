---
work_package_id: "WP06"
subtasks:
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
title: "Refactor UI to Use New Orchestration"
phase: "Phase 2 - Integration"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
history:
  - timestamp: "2026-02-08T17:14:59Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Refactor UI to Use New Orchestration

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` above.

---

## Review Feedback

*[Empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP06 --base WP02
```

Depends on WP02 (orchestration function must exist). Can proceed in parallel with WP03-WP05.

---

## Objectives & Success Criteria

Replace `recipes_tab.py._save_yield_types()` with a call to `recipe_service.save_recipe_with_yields()`, completing the UI-to-service architecture fix. The UI passes data; the service handles all business logic.

**Success criteria:**
- `_save_yield_types()` removed from `recipes_tab.py`
- `_add_recipe()` calls `save_recipe_with_yields()` for atomic recipe creation
- `_edit_recipe()` calls `save_recipe_with_yields()` for atomic recipe update
- No `finished_unit_service` imports in `recipes_tab.py`
- Error handling catches `ServiceError` and displays user-friendly messages
- User experience unchanged (same dialog flow, same error messages)

## Context & Constraints

**Key documents:**
- Plan: `kitty-specs/098-auto-generation-finished-goods/plan.md` (Design Decision D2)
- Constitution: `.kittify/memory/constitution.md` (Principle V — layered architecture)

**Current code to study:**
- `src/ui/recipes_tab.py` lines 444-506 (`_add_recipe()`)
- `src/ui/recipes_tab.py` lines 508-577 (`_edit_recipe()`)
- `src/ui/recipes_tab.py` lines 660-718 (`_save_yield_types()`)
- `src/ui/recipes_tab.py` line 14 (import of `session_scope`) and line ~672 (import of `finished_unit_service`)

**Current `_add_recipe()` flow:**
```python
def _add_recipe(self):
    result = dialog.get_result()
    yield_types = result.get("yield_types", [])
    recipe = recipe_service.create_recipe(recipe_data, ingredients_data)
    # ... add components ...
    self._save_yield_types(recipe.id, yield_types)
    self._refresh_recipe_list()
```

**Target `_add_recipe()` flow:**
```python
def _add_recipe(self):
    result = dialog.get_result()
    yield_types = result.get("yield_types", [])
    recipe = recipe_service.save_recipe_with_yields(
        recipe_data, yield_types, ingredients_data
    )
    self._refresh_recipe_list()
```

## Subtasks & Detailed Guidance

### Subtask T031 - Refactor `_add_recipe()` to use orchestration

**Purpose**: Replace multi-step recipe creation with single service call.

**Steps**:
1. Read `src/ui/recipes_tab.py` `_add_recipe()` (lines 444-506) carefully
2. Identify ALL data passed to `create_recipe()` and `_save_yield_types()`:
   - `recipe_data`: dict with name, category, instructions, etc.
   - `ingredients_data`: list of ingredient dicts
   - `yield_types`: list of yield type dicts from dialog
   - Components (sub-recipes): may be handled separately via `add_recipe_component()`
3. Replace the separate calls with:
   ```python
   recipe = recipe_service.save_recipe_with_yields(
       recipe_data=recipe_data,
       yield_types=yield_types,
       ingredients_data=ingredients_data,
   )
   ```
4. Handle recipe components (sub-recipes) — check if these need to be part of the orchestration or remain separate
5. Update error handling to catch `ServiceError` subclasses

**Files**: `src/ui/recipes_tab.py`
**Notes**: Be careful with the dialog result structure. Map field names from dialog result to service parameters. Also check if `add_recipe_component()` calls need to be included in the orchestration or if they're independent.

### Subtask T032 - Refactor `_edit_recipe()` to use orchestration

**Purpose**: Same as T031 but for the update path.

**Steps**:
1. Read `src/ui/recipes_tab.py` `_edit_recipe()` (lines 508-577)
2. Replace separate `update_recipe()` + `_save_yield_types()` calls with:
   ```python
   recipe = recipe_service.save_recipe_with_yields(
       recipe_data=recipe_data,
       yield_types=yield_types,
       ingredients_data=ingredients_data,
       recipe_id=existing_recipe.id,
   )
   ```
3. The `recipe_id` parameter tells the orchestration to update (vs create)
4. Update error handling

**Files**: `src/ui/recipes_tab.py`
**Notes**: Check how the edit dialog provides existing yield type IDs (for the reconciliation to know which FUs to update vs create).

### Subtask T033 - Remove `_save_yield_types()` method

**Purpose**: Delete the method that contained the business logic violation.

**Steps**:
1. Delete `_save_yield_types()` (lines ~660-718)
2. Remove the `finished_unit_service` import (line ~672, local import inside the deleted method)
3. Remove any other now-unused imports (check `session_scope` usage — if only used by deleted code, remove)
4. Verify no other methods call `_save_yield_types()`

**Files**: `src/ui/recipes_tab.py`
**Notes**: Search the entire file for `_save_yield_types` references before deleting. May be called from other methods.

### Subtask T034 - Update UI error handling

**Purpose**: Ensure service exceptions are caught and displayed as user-friendly messages.

**Steps**:
1. In `_add_recipe()` and `_edit_recipe()`, catch service exceptions:
   ```python
   try:
       recipe = recipe_service.save_recipe_with_yields(...)
   except ValidationError as e:
       self._show_error(f"Validation failed: {', '.join(e.errors)}")
       return
   except ServiceError as e:
       self._show_error(str(e))
       return
   ```
2. Handle the assembly protection error specifically (from WP05):
   - "Cannot delete - this item is used in X assembled product(s): ..."
   - This shows when removing a yield type whose bare FG is used in assemblies
3. Ensure error messages match current user experience

**Files**: `src/ui/recipes_tab.py`
**Notes**: Check how errors are currently displayed (`_show_error`, `messagebox`, etc.). Match the existing pattern.

### Subtask T035 - Write integration tests

**Purpose**: Verify the full UI→Service→DB flow works correctly end-to-end.

**Steps**:
1. Test: add recipe via UI flow → recipe + FU + bare FG all created
2. Test: edit recipe via UI flow → updates propagated correctly
3. Test: remove yield type via UI flow → FU + bare FG deleted (or blocked if referenced)
4. Test: error handling → validation error displayed correctly
5. Note: these may be manual tests if UI testing framework isn't set up

**Files**: `src/tests/test_recipes_tab.py` or manual testing documentation
**Notes**: If UI integration tests exist, extend them. If not, document manual test steps.

## Test Strategy

- **Automated**: `./run-tests.sh -v -k "recipe"` to verify no regressions
- **Manual**: Test recipe create/edit/delete through the UI
- **Full suite**: `./run-tests.sh -v`

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Dialog result format mismatch | Carefully map dialog fields to service params |
| Recipe components not included | Check if `add_recipe_component()` needs orchestration inclusion |
| Different error message format | Match current UI error display patterns |
| Removing code used elsewhere | Search for all references before deleting |

## Definition of Done Checklist

- [ ] `_add_recipe()` uses `save_recipe_with_yields()`
- [ ] `_edit_recipe()` uses `save_recipe_with_yields()`
- [ ] `_save_yield_types()` removed from `recipes_tab.py`
- [ ] No `finished_unit_service` imports in `recipes_tab.py`
- [ ] Error handling catches `ServiceError` and displays user-friendly messages
- [ ] No regressions in recipe management functionality
- [ ] Full test suite passes

## Review Guidance

- Verify NO business logic remains in UI layer
- Verify `recipes_tab.py` does NOT import `finished_unit_service`
- Verify error messages are user-friendly (not stack traces)
- Verify dialog result mapping is correct (field names match)
- Check that recipe component handling is not broken

## Activity Log

- 2026-02-08T17:14:59Z - system - lane=planned - Prompt created.
