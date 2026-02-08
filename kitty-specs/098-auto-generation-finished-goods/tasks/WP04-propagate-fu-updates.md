---
work_package_id: WP04
title: Propagate FU Updates to Bare FG
lane: "done"
dependencies: [WP03]
base_branch: 098-auto-generation-finished-goods-WP03
base_commit: 6d8a6a7b0683eea30bb7e04824fc42ad02af0655
created_at: '2026-02-08T18:37:19.692801+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
phase: Phase 2 - User Stories
assignee: ''
agent: "claude-opus"
shell_pid: "53922"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-08T17:14:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 - Propagate FU Updates to Bare FG

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` above.

---

## Review Feedback

*[Empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

Depends on WP03 (uses `find_bare_fg_for_unit()`).

---

## Objectives & Success Criteria

When a FinishedUnit's name or category changes during recipe update, automatically propagate the change to the corresponding bare FinishedGood within the same transaction. Delivers User Story 2 (P1).

**Success criteria:**
- FU name change → bare FG `display_name` and `slug` updated in same transaction
- FU category change → bare FG category updated in same transaction
- Only bare FGs affected (never assembled FGs)
- Only changed fields updated (no unnecessary writes)
- Unrelated FUs/FGs unaffected

## Context & Constraints

**Key documents:**
- Spec: `kitty-specs/098-auto-generation-finished-goods/spec.md` (User Story 2)
- Research: `kitty-specs/098-auto-generation-finished-goods/research.md` (Question 5)

**From WP03:** `find_bare_fg_for_unit(finished_unit_id, session)` returns the bare FG for a given FU.

**Slug regeneration:** When `display_name` changes, the slug must be regenerated. Study how `finished_good_service.update_finished_good()` handles slug updates — likely calls a slug generation utility. Reuse that.

## Subtasks & Detailed Guidance

### Subtask T019 - Create `sync_bare_finished_good()`

**Purpose**: Function that propagates FU field changes to the corresponding bare FG.

**Steps**:
1. Add to `src/services/finished_good_service.py`:
   ```python
   def sync_bare_finished_good(
       finished_unit_id: int,
       display_name: Optional[str] = None,
       category: Optional[str] = None,
       session: Optional[Session] = None
   ) -> Optional[FinishedGood]:
       """
       Sync bare FinishedGood with FinishedUnit changes.

       Finds the bare FG for the given FU and updates display_name
       and/or category if they've changed. Returns None if no bare FG exists.

       Transaction boundary: Uses provided session or creates new.
       """
   ```
2. Implementation:
   ```python
   def _impl(sess):
       bare_fg = find_bare_fg_for_unit(finished_unit_id, session=sess)
       if bare_fg is None:
           return None  # No bare FG to sync (normal for non-EA yields)

       updated = False
       if display_name and bare_fg.display_name != display_name:
           bare_fg.display_name = display_name
           bare_fg.slug = _generate_unique_slug(display_name, sess, exclude_id=bare_fg.id)
           updated = True
       if category is not None and getattr(bare_fg, 'category', None) != category:
           # Update category field (check actual field name on FinishedGood model)
           updated = True

       if updated:
           sess.flush()
       return bare_fg
   ```
3. Handle slug regeneration using existing utilities

**Files**: `src/services/finished_good_service.py`
**Notes**: Check how `update_finished_good()` handles slug regeneration. The FinishedGood model may store category differently (check the actual model). `_generate_unique_slug` needs `exclude_id` to avoid flagging the FG's own current slug as a duplicate.

### Subtask T020 - Integrate sync into update path

**Purpose**: Call `sync_bare_finished_good()` during yield type updates in the orchestration.

**Steps**:
1. In `src/services/recipe_service.py`, within `_reconcile_yield_types()`:
   ```python
   # After updating an existing FU:
   fu = update_finished_unit(finished_unit_id=yt_id, session=session, ...)

   # Sync bare FG if this is an EA yield
   if fu.yield_type == "EA":
       sync_bare_finished_good(
           finished_unit_id=fu.id,
           display_name=fu.display_name,
           category=fu.category,
           session=session
       )
   ```
2. Add import for `sync_bare_finished_good`
3. Only sync for EA yield types

**Files**: `src/services/recipe_service.py`
**Parallel?**: No (depends on T019)

### Subtask T021 - Implement name propagation with slug regeneration

**Purpose**: When FU name changes, update bare FG display_name and regenerate its slug.

**Steps**:
1. Verify slug generation utility is available (check `finished_good_service.py` for `_generate_unique_slug` or similar)
2. In `sync_bare_finished_good()`, ensure:
   - `display_name` is updated on the FG object
   - Slug is regenerated from the new name
   - `exclude_id` is passed to avoid self-collision
3. Test that slug uniqueness is maintained

**Files**: `src/services/finished_good_service.py`
**Parallel?**: Yes (with T022)

### Subtask T022 - Implement category propagation

**Purpose**: When FU category changes, update bare FG category.

**Steps**:
1. Read `src/models/finished_good.py` to find the category field name
   - It might be a direct field or a relationship (check if it's a FK to a category table)
2. Update the category field on the bare FG
3. Handle null/empty category gracefully

**Files**: `src/services/finished_good_service.py`
**Parallel?**: Yes (with T021)
**Notes**: FinishedGood may not have a simple `category` string field — it might work differently. Study the model carefully.

### Subtask T023 - Write tests: propagation within transaction

**Purpose**: Verify name and category changes propagate correctly within same transaction.

**Steps**:
1. Test: rename FU → bare FG display_name updated
2. Test: rename FU → bare FG slug regenerated
3. Test: change category → bare FG category updated
4. Test: both name and category change → both propagated
5. Test: all changes in same transaction (verify atomicity)

**Files**: `src/tests/test_finished_good_service.py`

### Subtask T024 - Write tests: edge cases

**Purpose**: Verify edge cases in propagation.

**Steps**:
1. Test: FU with no bare FG (SERVING type) → sync returns None, no error
2. Test: update FU name but don't change it → no unnecessary FG update
3. Test: rename one FU → only its bare FG affected, others unchanged
4. Test: slug collision on rename → resolved with suffix

**Files**: `src/tests/test_finished_good_service.py`

## Test Strategy

- **Run**: `./run-tests.sh -v -k "sync_bare or propagat"`
- **Full suite**: `./run-tests.sh -v`

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Slug collision on rename | Use `exclude_id` in slug generation |
| Category field structure unknown | Read model before implementing — may need FK lookup |
| Unnecessary updates | Compare values before writing |

## Definition of Done Checklist

- [ ] `sync_bare_finished_good()` function exists and works
- [ ] Integrated into update path in `save_recipe_with_yields()`
- [ ] Name propagation with slug regeneration works
- [ ] Category propagation works
- [ ] Only bare FGs affected
- [ ] Tests cover happy path and edge cases
- [ ] Full test suite passes

## Review Guidance

- Verify only changed fields are updated (no unnecessary writes)
- Verify slug regeneration uses `exclude_id`
- Verify only EA yield types trigger sync
- Check category field implementation matches actual model

## Activity Log

- 2026-02-08T17:14:59Z - system - lane=planned - Prompt created.
- 2026-02-08T18:50:49Z – unknown – shell_pid=49344 – lane=for_review – All subtasks done. sync_bare_finished_good() propagates display_name and slug. 8 new tests, 3563 full suite pass.
- 2026-02-08T19:03:57Z – claude-opus – shell_pid=53922 – lane=doing – Started review via workflow command
- 2026-02-08T19:05:32Z – claude-opus – shell_pid=53922 – lane=done – Review passed: sync_bare_finished_good() correctly propagates display_name and slug changes from FU to bare FG. 8 new tests all pass. T022 (category) correctly N/A since FinishedGood has no category field. Session management, slug collision handling, and EA-only gating all verified. Full suite 3609 passed.
