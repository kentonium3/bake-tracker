---
work_package_id: WP01
title: Service Layer Fixes
dependencies: []
base_branch: main
base_commit: 745d7a2241df121c90969d93eeb48b50c255311e
created_at: '2026-03-15T04:48:49.787341+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Service Layer
history:
- timestamp: '2026-03-15T04:45:47Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: ''
execution_mode: code_change
mission_id: 01KN5R6XFK0J69FPFVFD440R49
owned_files:
- kitty-specs/103-fix-plan-mode-fg-batch-scoping/plan.md
- kitty-specs/103-fix-plan-mode-fg-batch-scoping/research.md
- kitty-specs/103-fix-plan-mode-fg-batch-scoping/spec.md
- src/models/**
- src/services/event_service.py
- src/services/planning_service.py
- src/tests/services/test_event_service.py
- src/tests/services/test_planning_service.py
wp_code: WP01
---

# Work Package Prompt: WP01 -- Service Layer Fixes

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** -- Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Create a new service function that returns finished goods for an event's selected recipes (simple join, no recursive decomposition)
- Fix stale EventFinishedGood cleanup to use direct recipe_id check instead of assembly-oriented availability logic
- Add defense-in-depth recipe filtering to batch decomposition
- All changes covered by tests
- Existing planning tests continue to pass

## Context & Constraints

- **Spec**: `kitty-specs/103-fix-plan-mode-fg-batch-scoping/spec.md`
- **Plan**: `kitty-specs/103-fix-plan-mode-fg-batch-scoping/plan.md` (see D1-D3)
- **Research**: `kitty-specs/103-fix-plan-mode-fg-batch-scoping/research.md`
- **Constitution**: `.kittify/memory/constitution.md` -- session parameter pattern required, exception-based errors
- **Key constraint**: Do NOT remove existing `get_available_finished_goods()` or `check_fg_availability()` -- they may be needed for future assembly planning
- **Key constraint**: New functions MUST accept `session: Session` parameter per constitution VI-C
- **Key constraint**: The UI currently works with `FinishedGood` objects. T002 must return `FinishedGood` objects to preserve the UI contract

### Implementation command

```bash
spec-kitty implement WP01
```

## Subtasks & Detailed Guidance

### Subtask T001 -- Create `get_finished_units_for_event_recipes()`

- **Purpose**: Provide a simple query that returns all FinishedUnits whose parent recipe is selected for an event. This replaces the recursive assembly-oriented `get_available_finished_goods()` for recipe-level planning.

- **Steps**:
  1. Add function to `src/services/event_service.py` (after `get_filtered_available_fgs()`, around line 554)
  2. Query pattern:
     ```python
     def get_finished_units_for_event_recipes(
         event_id: int,
         session: Session,
         recipe_category: Optional[str] = None,
         yield_type: Optional[str] = None,
     ) -> List[FinishedUnit]:
         """
         Get all finished units whose recipe is selected for the event.

         Transaction boundary: Inherits session from caller (required parameter).
         Read-only query within the caller's transaction scope.
         """
     ```
  3. SQL logic:
     ```
     SELECT fu.*
     FROM finished_units fu
     JOIN recipes r ON fu.recipe_id = r.id
     JOIN event_recipes er ON er.recipe_id = r.id
     WHERE er.event_id = :event_id
       AND (:recipe_category IS NULL OR r.category = :recipe_category)
       AND (:yield_type IS NULL OR fu.yield_type = :yield_type)
     ORDER BY r.category, r.name, fu.display_name
     ```
  4. Validate event exists (raise `ValidationError` if not)
  5. Return empty list if no recipes selected

- **Files**: `src/services/event_service.py`
- **Parallel?**: Yes (independent of T003, T004)
- **Notes**: Import `FinishedUnit` model. The `yield_type` filter uses the string values "EA" or "SERVING".

### Subtask T002 -- Create `get_fgs_for_selected_recipes()` wrapper

- **Purpose**: The UI works with `FinishedGood` objects (not `FinishedUnit`). This wrapper calls T001's function, then maps each FinishedUnit back to its corresponding bare FinishedGood.

- **Steps**:
  1. Add function to `src/services/event_service.py` (after T001's function)
  2. Signature:
     ```python
     def get_fgs_for_selected_recipes(
         event_id: int,
         session: Session,
         recipe_category: Optional[str] = None,
         item_type: Optional[str] = None,
         yield_type: Optional[str] = None,
     ) -> List[FinishedGood]:
         """
         Get FinishedGoods for recipes selected in an event.

         Transaction boundary: Inherits session from caller (required parameter).
         """
     ```
  3. Implementation:
     - Call `get_finished_units_for_event_recipes(event_id, session, recipe_category, yield_type)`
     - For each FinishedUnit, find its bare FinishedGood via:
       ```python
       # FinishedGoodComponent links FU to FG
       component = session.query(FinishedGoodComponent).filter_by(
           finished_unit_id=fu.id
       ).first()
       if component:
           fg = session.query(FinishedGood).filter_by(id=component.finished_good_id).first()
       ```
     - Deduplicate (a FG might appear from multiple FUs)
     - Apply `item_type` filter if provided:
       - "Finished Units" -> `fg.assembly_type == AssemblyType.BARE`
       - "Assemblies" -> `fg.assembly_type == AssemblyType.BUNDLE`
     - Return list of FinishedGood objects

- **Files**: `src/services/event_service.py`
- **Parallel?**: No (depends on T001)
- **Notes**: Import `FinishedGoodComponent`, `FinishedGood`, `AssemblyType`. Check actual model field names -- `FinishedGoodComponent` may use different field names. Verify by reading the model file at `src/models/`.

### Subtask T003 -- Simplify `remove_invalid_fg_selections()`

- **Purpose**: The current cleanup uses `check_fg_availability()` which recursively decomposes FGs. For simple recipe planning, we need a direct check: is the FU's recipe_id still in EventRecipe?

- **Steps**:
  1. Locate `remove_invalid_fg_selections()` at `src/services/event_service.py` line 595
  2. Replace the `check_fg_availability()` call with a direct check:
     ```python
     # Get selected recipe IDs
     selected_recipe_ids = set(get_event_recipe_ids(session, event_id))

     for efg in current_fg_selections:
         # Get the FG's component FUs
         fg = session.query(FinishedGood).filter_by(id=efg.finished_good_id).first()
         if not fg:
             session.delete(efg)
             continue

         # Check if ANY component FU's recipe is in selected recipes
         has_valid_recipe = False
         for component in fg.components:
             if component.finished_unit_id:
                 fu = session.query(FinishedUnit).filter_by(id=component.finished_unit_id).first()
                 if fu and fu.recipe_id in selected_recipe_ids:
                     has_valid_recipe = True
                     break

         if not has_valid_recipe:
             removed_fgs.append(RemovedFGInfo(...))
             session.delete(efg)
     ```
  3. Keep the return type and `RemovedFGInfo` structure unchanged
  4. Keep `session.flush()` at end

- **Files**: `src/services/event_service.py`
- **Parallel?**: No (modifies same file as T001/T002, but different function)
- **Notes**: The existing `check_fg_availability()` function should NOT be deleted -- keep it for potential future assembly planning use. `RemovedFGInfo` still needs `missing_recipes` field populated -- use the recipe names for FUs whose recipes are no longer selected.

### Subtask T004 -- Add recipe-scoping filter to batch decomposition

- **Purpose**: Defense-in-depth: even if stale EventFinishedGood records survive cleanup, batch decomposition should not include them.

- **Steps**:
  1. Locate `_decompose_event_to_fu_requirements_impl()` in `src/services/planning_service.py` (around line 84)
  2. After querying EventFinishedGood records (line 96-98), get selected recipe IDs:
     ```python
     from src.services.event_service import get_event_recipe_ids
     selected_recipe_ids = set(get_event_recipe_ids(session, event_id))
     ```
  3. After decomposing each EFG to FURequirements, filter:
     ```python
     # Filter: only include FU requirements for selected recipes
     fu_requirements = [
         req for req in fu_requirements
         if req.recipe.id in selected_recipe_ids
     ]
     ```
  4. Alternative approach: filter BEFORE decomposition by checking each EFG's FG components

- **Files**: `src/services/planning_service.py`
- **Parallel?**: Yes (different file from T001-T003)
- **Notes**: Check if `get_event_recipe_ids` is already imported. The `FURequirement` dataclass has a `recipe` field (same as `finished_unit.recipe`).

### Subtask T005 -- Write service layer tests

- **Purpose**: Verify all three fixes work correctly with unit/integration tests.

- **Steps**:
  1. Create or extend test file for event service FG functions
  2. Test `get_finished_units_for_event_recipes()`:
     - Event with 3 recipes selected, each with 1 FU -> returns 3 FUs
     - Event with recipe deselected -> its FU not returned
     - Category filter -> only matching category FUs returned
     - No recipes selected -> empty list
  3. Test `get_fgs_for_selected_recipes()`:
     - Returns FinishedGood objects (not FinishedUnits)
     - Deduplication when recipe has multiple FUs
  4. Test `remove_invalid_fg_selections()`:
     - Deselect recipe -> its EventFinishedGood deleted
     - Keep recipe -> its EventFinishedGood preserved
     - Returns correct RemovedFGInfo
  5. Test batch decomposition filtering:
     - Stale EFG record exists -> not included in batch options
     - Valid EFG record -> included in batch options
  6. Run full test suite to check for regressions:
     ```bash
     ./run-tests.sh -v -k "planning or event_service or batch"
     ```

- **Files**: `src/tests/services/test_event_service.py` (extend), `src/tests/services/test_planning_service.py` (extend)
- **Parallel?**: No (depends on T001-T004)
- **Notes**: Use `test_db` fixture. Create test recipes, finished units, finished goods, events, and event recipes as fixtures. Follow existing test patterns in the codebase.

## Test Strategy

Tests are required per constitution Principle IV (Test-Driven Development).

- **Unit tests**: Each new/modified service function tested independently
- **Integration tests**: End-to-end flow: select recipes -> get FGs -> deselect recipe -> verify cleanup -> verify batch options
- **Regression**: Run `./run-tests.sh -v -k "planning or event"` to catch regressions
- **Fixtures**: Need Recipe, FinishedUnit, FinishedGood, FinishedGoodComponent, Event, EventRecipe, EventFinishedGood

## Risks & Mitigations

- **Risk**: `FinishedGoodComponent` model has different field names than expected. **Mitigation**: Read the model file before implementing T002.
- **Risk**: Existing tests depend on `get_available_finished_goods()` behavior. **Mitigation**: Don't modify existing function; new function is additive.
- **Risk**: Recipe-scoping filter in T004 breaks bundle decomposition. **Mitigation**: Filter at FURequirement level (post-decomposition), not at EFG level (pre-decomposition).

## Definition of Done Checklist

- [ ] `get_finished_units_for_event_recipes()` returns correct FUs for selected recipes
- [ ] `get_fgs_for_selected_recipes()` returns FinishedGood objects matching selected recipes
- [ ] `remove_invalid_fg_selections()` eagerly deletes stale EventFinishedGood records
- [ ] Batch decomposition excludes deselected recipes' FU requirements
- [ ] All new functions accept `session: Session` parameter
- [ ] All new functions have docstrings with transaction boundary documentation
- [ ] Tests pass for all new/modified functions
- [ ] Existing planning tests continue to pass
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify new functions don't modify or break existing `get_available_finished_goods()` or `check_fg_availability()`
- Check that `remove_invalid_fg_selections()` still returns `RemovedFGInfo` with populated `missing_recipes`
- Verify batch decomposition filter doesn't exclude valid FU requirements
- Run `./run-tests.sh -v -k "planning or event"` to confirm no regressions

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-03-15T04:45:47Z -- system -- lane=planned -- Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP01 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-03-15T04:48:50Z – claude-opus – shell_pid=25482 – lane=doing – Assigned agent via workflow command
- 2026-03-15T04:57:45Z – claude-opus – shell_pid=25482 – lane=for_review – Ready for review: new FG query, simplified cleanup, conditional batch filter, 13 tests all passing, 22 existing planning tests passing
- 2026-03-15T05:01:45Z – claude-opus – shell_pid=30811 – lane=doing – Started review via workflow command
- 2026-03-15T05:02:11Z – claude-opus – shell_pid=30811 – lane=done – Review passed: additive functions, session params, docstrings, conditional filter, 13 tests, no regressions
