---
work_package_id: WP05
title: Cascade Delete with Assembly Protection
lane: "done"
dependencies: [WP03]
base_branch: 098-auto-generation-finished-goods-WP03
base_commit: 6d8a6a7b0683eea30bb7e04824fc42ad02af0655
created_at: '2026-02-08T18:51:36.722783+00:00'
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
phase: Phase 2 - User Stories
assignee: ''
agent: ''
shell_pid: "51195"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-08T17:14:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 - Cascade Delete with Assembly Protection

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` above.

---

## Review Feedback

*[Empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP05 --base WP03
```

Depends on WP03 (uses `find_bare_fg_for_unit()`).

---

## Objectives & Success Criteria

When a FinishedUnit is deleted, cascade-delete its bare FinishedGood and Composition. But if the bare FG is used as a component in any assembled FinishedGood, block the deletion with a clear error message listing the affected assemblies. Delivers User Story 3 (P1).

**Success criteria:**
- FU deletion cascades to bare FG + Composition when no assembly refs exist
- Deletion blocked with descriptive error when bare FG is referenced by assemblies
- Error lists affected assembly names (not just IDs)
- Cascade operates within same transaction
- No orphaned records after deletion

## Context & Constraints

**Key documents:**
- Spec: `kitty-specs/098-auto-generation-finished-goods/spec.md` (User Story 3)
- Research: `kitty-specs/098-auto-generation-finished-goods/research.md` (Question 6)
- Data model: `kitty-specs/098-auto-generation-finished-goods/data-model.md` (Key Queries: "Find all assembly references")

**Existing delete behavior:**
- `delete_finished_unit()` already checks `Composition WHERE finished_unit_id = :fu_id` and raises `ReferencedUnitError` if any compositions exist
- The NEW check is different: we need to check if the **bare FG** (not the FU) is referenced as a **component** in any **assembled FG**
- Query: `Composition WHERE finished_good_id = :bare_fg_id` (bare FG used as component in assembly)

**Cascade order:**
1. Find bare FG for this FU
2. Check if bare FG is referenced by any assembly → block if yes
3. Delete Composition linking bare FG to FU (the `assembly_id` = bare_fg, `finished_unit_id` = fu)
4. Delete bare FG
5. Allow FU deletion to proceed (handled by existing `delete_finished_unit`)

## Subtasks & Detailed Guidance

### Subtask T025 - Create assembly reference check function

**Purpose**: Check if a bare FinishedGood is used as a component in any assembled FinishedGood.

**Steps**:
1. Add to `src/services/finished_good_service.py`:
   ```python
   def get_assembly_references(
       finished_good_id: int,
       session: Optional[Session] = None
   ) -> List[FinishedGood]:
       """
       Find all assembled FinishedGoods that use this FG as a component.

       Checks Composition table for records where finished_good_id matches
       (meaning this FG is used as a component in another FG's assembly).

       Returns list of parent FinishedGoods (assemblies) that reference this FG.
       """
   ```
2. Query:
   ```python
   compositions = (session.query(Composition)
       .filter(Composition.finished_good_id == finished_good_id)
       .all())

   # Get the parent assemblies
   assembly_ids = [c.assembly_id for c in compositions]
   if not assembly_ids:
       return []

   assemblies = (session.query(FinishedGood)
       .filter(FinishedGood.id.in_(assembly_ids))
       .all())
   return assemblies
   ```

**Files**: `src/services/finished_good_service.py`
**Parallel?**: Yes (with T026)
**Notes**: Important distinction — `Composition.finished_good_id` is where this FG is a **component**, not where it's the **assembly**. `Composition.assembly_id` is the parent assembly.

### Subtask T026 - Create `cascade_delete_bare_fg()`

**Purpose**: Delete bare FG and its Composition record, with assembly protection.

**Steps**:
1. Add to `src/services/finished_good_service.py`:
   ```python
   def cascade_delete_bare_fg(
       finished_unit_id: int,
       session: Optional[Session] = None
   ) -> bool:
       """
       Cascade-delete the bare FG for a FinishedUnit.

       Checks for assembly references first. If referenced, raises
       error with affected assembly names.

       Returns True if deleted, False if no bare FG existed.

       Raises:
           ValidationError: If bare FG is used in assembled FGs
       """
   ```
2. Implementation:
   ```python
   def _impl(sess):
       bare_fg = find_bare_fg_for_unit(finished_unit_id, session=sess)
       if bare_fg is None:
           return False  # No bare FG to delete

       # Check assembly references
       assemblies = get_assembly_references(bare_fg.id, session=sess)
       if assemblies:
           names = [a.display_name for a in assemblies]
           raise ValidationError([
               f"Cannot delete - this item is used in {len(assemblies)} "
               f"assembled product(s): {', '.join(names)}"
           ])

       # Delete Composition(s) linking bare FG to FU
       compositions = (sess.query(Composition)
           .filter(Composition.assembly_id == bare_fg.id)
           .all())
       for comp in compositions:
           sess.delete(comp)

       # Delete bare FG
       sess.delete(bare_fg)
       sess.flush()
       return True
   ```

**Files**: `src/services/finished_good_service.py`
**Parallel?**: Yes (with T025)
**Notes**: Delete Compositions first (child records), then FG (parent). Session flush ensures deletes are committed before FU deletion proceeds.

### Subtask T027 - Integrate cascade delete into delete path

**Purpose**: Call `cascade_delete_bare_fg()` during yield type deletion in the orchestration.

**Steps**:
1. In `src/services/recipe_service.py`, within `_reconcile_yield_types()`:
   ```python
   # Before deleting orphaned FUs:
   for fu_id in ids_to_delete:
       # First try to cascade-delete bare FG
       cascade_delete_bare_fg(fu_id, session=session)

       # Then delete the FU itself
       delete_finished_unit(fu_id, session=session)
   ```
2. The `cascade_delete_bare_fg` runs BEFORE `delete_finished_unit` so that:
   - Assembly protection check happens before any deletion
   - The Composition linking bare FG to FU is deleted before FU deletion
   - FU deletion won't hit `ReferencedUnitError` for the bare FG's composition
3. If `cascade_delete_bare_fg` raises `ValidationError`, the entire operation rolls back

**Files**: `src/services/recipe_service.py`
**Parallel?**: No (depends on T025, T026)

### Subtask T028 - Implement error message with assembly listing

**Purpose**: When deletion is blocked, provide a clear error listing all affected assemblies.

**Steps**:
1. The error is raised in T026's `cascade_delete_bare_fg()` — verify the message format:
   - "Cannot delete - this item is used in 2 assembled product(s): Holiday Cookie Box, Gift Basket"
2. In the UI layer (WP06 will handle this), the error is caught and displayed to the user
3. For now, ensure the `ValidationError` message is clear and includes assembly display names
4. Test: error message lists all affected assemblies correctly

**Files**: `src/services/finished_good_service.py`
**Parallel?**: No (depends on T026)

### Subtask T029 - Write tests: clean cascade delete

**Purpose**: Verify cascade delete works when no assembly references exist.

**Steps**:
1. Test: create recipe with EA yield → FU + bare FG created → delete recipe → FU, bare FG, and Composition all deleted
2. Test: after deletion, `find_bare_fg_for_unit()` returns None
3. Test: no orphaned Composition records remain
4. Test: FU with no bare FG (SERVING type) → deletion proceeds without error

**Files**: `src/tests/test_finished_good_service.py`

### Subtask T030 - Write tests: deletion blocked by assembly reference

**Purpose**: Verify deletion is blocked with correct error when bare FG is referenced.

**Steps**:
1. Setup: create recipe → FU → bare FG → create assembled FG using bare FG as component
2. Test: attempt to delete recipe → `ValidationError` raised
3. Test: error message lists the assembled FG's name
4. Test: after blocked deletion, all records still intact (nothing partially deleted)
5. Test: with 2 assemblies referencing → both names listed in error

**Files**: `src/tests/test_finished_good_service.py`

## Test Strategy

- **Run**: `./run-tests.sh -v -k "cascade_delete or assembly_ref or assembly_protect"`
- **Full suite**: `./run-tests.sh -v`

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Wrong Composition field queried | `finished_good_id` = FG as component (not assembly_id). Verify with data model. |
| Partial deletion on error | Single session — rollback handles everything |
| FU delete_finished_unit raises ReferencedUnitError | Delete bare FG's Composition BEFORE deleting FU to avoid this |

## Definition of Done Checklist

- [ ] `get_assembly_references()` correctly finds parent assemblies
- [ ] `cascade_delete_bare_fg()` deletes FG + Compositions when no refs
- [ ] Deletion blocked with descriptive error when referenced by assemblies
- [ ] Integrated into delete path in `save_recipe_with_yields()`
- [ ] Error message includes assembly display names
- [ ] Tests cover both clean delete and blocked delete
- [ ] Full test suite passes

## Review Guidance

- Verify `Composition.finished_good_id` is the correct field for "FG used as component"
- Verify cascade order: check refs → delete compositions → delete FG → delete FU
- Verify error message is user-friendly with assembly names
- Check that partial deletion cannot occur (transaction atomicity)

## Activity Log

- 2026-02-08T17:14:59Z - system - lane=planned - Prompt created.
- 2026-02-08T19:02:54Z – unknown – shell_pid=51195 – lane=for_review – All subtasks done. get_assembly_references(), cascade_delete_bare_fg() with assembly protection. 11 new tests, 3563 full suite pass.
- 2026-02-08T19:44:25Z – unknown – shell_pid=51195 – lane=done – Review passed: all 11 WP05 tests pass, full suite clean (3612 passed), code follows session management and exception patterns correctly, assembly protection logic verified against Composition model semantics
