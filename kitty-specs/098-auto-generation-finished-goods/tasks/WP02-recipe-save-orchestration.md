---
work_package_id: WP02
title: Recipe Save Orchestration
lane: "doing"
dependencies: [WP01]
base_branch: 098-auto-generation-finished-goods-WP01
base_commit: 5c7a242e9c98aa9dc3bfb31df13eeacbf7a5a6b9
created_at: '2026-02-08T17:46:58.533771+00:00'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-opus"
shell_pid: "42991"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T17:14:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 - Recipe Save Orchestration

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to **Review Feedback** immediately.

---

## Review Feedback

*[Empty initially. Reviewers populate if work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 (session parameter on `finished_unit_service`).

---

## Objectives & Success Criteria

Create `save_recipe_with_yields()` in `recipe_service.py` that orchestrates the entire recipe save (recipe + yield types + FinishedUnits) in a single atomic transaction. This moves business logic from the UI layer (`recipes_tab._save_yield_types()`) into the service layer, fixing a Constitution Principle V violation.

**Success criteria:**
- Recipe + yield types + FUs all created/updated/deleted in single transaction
- Transaction rolls back atomically on any failure (no partial state)
- Function handles both create and update flows
- Yield type reconciliation logic matches current behavior (add new, update existing, delete removed)
- All operations share the same session

## Context & Constraints

**Key documents:**
- Plan: `kitty-specs/098-auto-generation-finished-goods/plan.md` (Design Decision D2, D5)
- Research: `kitty-specs/098-auto-generation-finished-goods/research.md` (Question 3)
- Data model: `kitty-specs/098-auto-generation-finished-goods/data-model.md`

**Current code to study:**
- `src/ui/recipes_tab.py` lines 444-506 (`_add_recipe()`) — current UI orchestration for creating recipes
- `src/ui/recipes_tab.py` lines 508-577 (`_edit_recipe()`) — current UI orchestration for updating recipes
- `src/ui/recipes_tab.py` lines 660-718 (`_save_yield_types()`) — yield type reconciliation logic to port
- `src/services/recipe_service.py` — existing `create_recipe()` and `update_recipe()` functions

**The reconciliation pattern in `_save_yield_types()`:**
```
1. Get existing FUs for this recipe
2. Build set of IDs to keep
3. For each yield type in the new list:
   - If id is None → create new FU
   - If id exists → update existing FU, add to keep set
4. For each existing FU not in keep set → delete
```

This pattern moves to the service layer as-is.

## Subtasks & Detailed Guidance

### Subtask T007 - Design and implement `save_recipe_with_yields()` signature

**Purpose**: Create the orchestration function that replaces separate UI calls with a single service entry point.

**Steps**:
1. Read `src/services/recipe_service.py` to understand existing patterns
2. Design function signature:
   ```python
   def save_recipe_with_yields(
       recipe_data: Dict,
       yield_types: List[Dict],
       ingredients_data: Optional[List[Dict]] = None,
       recipe_id: Optional[int] = None,  # None = create, int = update
       session: Optional[Session] = None
   ) -> Recipe:
       """
       Orchestrate recipe save with yield types atomically.

       Creates or updates a recipe along with its yield types (FinishedUnits)
       in a single transaction. If recipe_id is provided, updates existing recipe;
       otherwise creates new.

       Transaction boundary: Single session for all operations. Either all succeed
       or entire operation rolls back.

       Args:
           recipe_data: Dict with recipe fields (name, category, etc.)
           yield_types: List of yield type dicts with keys:
               - id: Optional[int] (None = new, int = update existing)
               - display_name: str
               - item_unit: Optional[str]
               - items_per_batch: float
               - yield_type: str ("EA" or "SERVING")
           ingredients_data: Optional list of ingredient dicts
           recipe_id: If provided, update this recipe; otherwise create new
           session: Optional session for transaction composition

       Returns:
           The created or updated Recipe object

       Raises:
           ValidationError: If recipe or yield type data is invalid
           ServiceError: If creation/update fails
       """
   ```
3. Implement the `_impl` pattern (accept session or create session_scope)

**Files**: `src/services/recipe_service.py`
**Notes**: The function must handle both create and update — study how `_add_recipe()` and `_edit_recipe()` differ in what they pass.

### Subtask T008 - Implement yield type reconciliation logic

**Purpose**: Port the reconciliation logic from `recipes_tab._save_yield_types()` into the service layer.

**Steps**:
1. Read `src/ui/recipes_tab.py` lines 660-718 carefully
2. Within `_save_recipe_with_yields_impl()`, after recipe create/update:
   ```python
   # Get existing FUs for this recipe
   existing_fus = get_units_by_recipe(recipe.id, session=session)
   existing_fu_map = {fu.id: fu for fu in existing_fus}
   keeping_ids = set()

   for yt in yield_types:
       yt_id = yt.get("id")
       if yt_id is None:
           # New yield type → create FU
           fu = create_finished_unit(
               display_name=yt["display_name"],
               recipe_id=recipe.id,
               item_unit=yt.get("item_unit"),
               items_per_batch=yt.get("items_per_batch"),
               yield_type=yt.get("yield_type", "EA"),
               session=session
           )
       else:
           # Existing yield type → update FU
           fu = update_finished_unit(
               finished_unit_id=yt_id,
               display_name=yt["display_name"],
               item_unit=yt.get("item_unit"),
               items_per_batch=yt.get("items_per_batch"),
               yield_type=yt.get("yield_type"),
               session=session
           )
           keeping_ids.add(yt_id)

   # Delete removed yield types
   for fu_id, fu in existing_fu_map.items():
       if fu_id not in keeping_ids:
           delete_finished_unit(fu_id, session=session)
   ```
3. Ensure all FU service calls pass the session parameter (from WP01)

**Files**: `src/services/recipe_service.py`
**Notes**: Import `finished_unit_service` functions. Check what `get_units_by_recipe()` looks like — it may also need a session parameter (check and add if needed).

### Subtask T009 - Wire FU create/update/delete within single session

**Purpose**: Ensure the entire orchestration (recipe + ingredients + yield types) shares one session.

**Steps**:
1. In the `_impl` function, the session flows through:
   ```python
   def _save_recipe_with_yields_impl(recipe_data, yield_types, ingredients_data, recipe_id, session):
       if recipe_id:
           recipe = update_recipe(recipe_id, recipe_data, ingredients_data, session=session)
       else:
           recipe = create_recipe(recipe_data, ingredients_data, session=session)

       session.flush()  # Ensure recipe.id is available

       # Reconcile yield types (T008 logic here)
       _reconcile_yield_types(recipe.id, yield_types, session)

       return recipe
   ```
2. Verify `create_recipe()` and `update_recipe()` in `recipe_service.py` accept `session` parameter
   - If they don't, add it (same `_impl` pattern from WP01)
   - They likely already use `session_scope()` internally — refactor to accept external session
3. Call `session.flush()` after recipe creation to get `recipe.id` before creating FUs

**Files**: `src/services/recipe_service.py`
**Notes**: `create_recipe()` may need the same session parameter refactoring as WP01 did for `finished_unit_service`. Check first — if it already accepts session, just pass it through.

### Subtask T010 - Write tests: atomic recipe+yield creation

**Purpose**: Verify recipe and yield types are created in a single atomic transaction.

**Steps**:
1. Write test in `src/tests/test_recipe_service.py`:
   ```python
   def test_save_recipe_with_yields_creates_all_atomically():
       recipe_data = {"name": "Test Cake", "category": "Cakes"}
       yield_types = [
           {"id": None, "display_name": "Test Cake", "yield_type": "EA", "items_per_batch": 1.0},
       ]
       recipe = save_recipe_with_yields(recipe_data, yield_types)

       # Verify recipe exists
       assert recipe.id is not None
       assert recipe.name == "Test Cake"

       # Verify FU exists and links to recipe
       fus = get_units_by_recipe(recipe.id)
       assert len(fus) == 1
       assert fus[0].display_name == "Test Cake"
   ```
2. Test with multiple yield types (EA + SERVING)
3. Test create vs update paths

**Files**: `src/tests/test_recipe_service.py`

### Subtask T011 - Write tests: yield reconciliation

**Purpose**: Verify the reconciliation pattern (add new, update existing, remove old) works correctly.

**Steps**:
1. Test adding a new yield type to existing recipe
2. Test updating an existing yield type's name
3. Test removing a yield type (not in new list → deleted)
4. Test mixed operations (add one, update one, remove one in same call)

**Files**: `src/tests/test_recipe_service.py`

### Subtask T012 - Write tests: transaction rollback on failure

**Purpose**: Verify that if any step fails, the entire operation rolls back.

**Steps**:
1. Test: invalid yield type data → recipe not created
2. Test: FU creation fails → recipe creation rolled back
3. Test: FU deletion fails (reference error) → recipe update rolled back
4. Verify no partial state remains after rollback

**Files**: `src/tests/test_recipe_service.py`

## Test Strategy

- **Unit tests**: `src/tests/test_recipe_service.py`
- **Run**: `./run-tests.sh src/tests/test_recipe_service.py -v`
- **Full suite**: `./run-tests.sh -v` after all changes

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `create_recipe()` doesn't accept session | Refactor it same as WP01 pattern — add session param |
| `get_units_by_recipe()` doesn't accept session | Add session param if needed |
| Subtle behavior diff vs UI code | Test same scenarios that UI tests cover |
| session.flush() timing | Flush after recipe create/update to get recipe.id before FU creation |

## Definition of Done Checklist

- [ ] `save_recipe_with_yields()` function exists in `recipe_service.py`
- [ ] Handles both create and update flows
- [ ] Yield type reconciliation matches current `_save_yield_types()` behavior
- [ ] All operations share single session
- [ ] Tests verify atomic creation, reconciliation, and rollback
- [ ] Full test suite passes

## Review Guidance

- Compare reconciliation logic with original `_save_yield_types()` — should be functionally identical
- Verify session flows through all calls (no nested `session_scope()`)
- Check that `recipe_service` doesn't import UI components (architecture compliance)
- Verify both create and update paths are tested

## Activity Log

- 2026-02-08T17:14:59Z - system - lane=planned - Prompt created.
- 2026-02-08T17:46:59Z – claude-opus – shell_pid=42991 – lane=doing – Assigned agent via workflow command
