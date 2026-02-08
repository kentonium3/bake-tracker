---
work_package_id: WP07
title: Migration of Existing Bare FinishedGoods
lane: "done"
dependencies: [WP03]
base_branch: 098-auto-generation-finished-goods-WP03
base_commit: 6d8a6a7b0683eea30bb7e04824fc42ad02af0655
created_at: '2026-02-08T19:03:27.939298+00:00'
subtasks:
- T036
- T037
- T038
- T039
- T040
- T041
phase: Phase 3 - Data Migration
assignee: ''
agent: ''
shell_pid: "53440"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-08T17:14:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 - Migration of Existing Bare FinishedGoods

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` above.

---

## Review Feedback

*[Empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP07 --base WP03
```

Depends on WP03 (auto-creation functions for validation).

---

## Objectives & Success Criteria

Identify and convert existing manually-created bare FinishedGoods to auto-managed status, establishing the 1:1 FU linkage retroactively. Delivers User Story 4 (P2).

**Success criteria:**
- All existing single-FU-component FGs correctly identified
- Misclassified FGs (BUNDLE with single FU component) reclassified to BARE
- 1:1 FU↔FG linkage verified/established
- User metadata (notes, description) preserved during migration
- Edge cases flagged for manual review (not silently skipped)
- Migration is idempotent (safe to run multiple times)

## Context & Constraints

**Key documents:**
- Spec: `kitty-specs/098-auto-generation-finished-goods/spec.md` (User Story 4)
- Research: `kitty-specs/098-auto-generation-finished-goods/research.md` (Question 8)

**Identification criteria:**
- FinishedGood with exactly one Composition record
- That Composition has `finished_unit_id` set (not null)
- Composition has no other component types set (XOR constraint)
- Quantity = 1
- These are functionally "bare" — may have `assembly_type=BUNDLE` if created via builder

**Current data state:**
- Existing bare FGs may have been created manually via the builder
- They may have `assembly_type=BUNDLE` (builder default) instead of `BARE`
- They may have user-added notes or descriptions that must be preserved

## Subtasks & Detailed Guidance

### Subtask T036 - Create migration function to identify bare FGs

**Purpose**: Find all FGs that are functionally bare but may not be correctly classified.

**Steps**:
1. Create function in `src/services/finished_good_service.py` (or a new migration utility):
   ```python
   def identify_bare_fg_candidates(
       session: Optional[Session] = None
   ) -> List[Dict]:
       """
       Identify FinishedGoods that should be classified as BARE.

       Returns list of dicts with:
         - fg_id: FinishedGood ID
         - fg_name: FinishedGood display_name
         - current_assembly_type: current classification
         - fu_id: linked FinishedUnit ID
         - fu_name: FinishedUnit display_name
         - needs_reclassification: bool (BUNDLE → BARE)
         - has_matching_fu: bool
       """
   ```
2. Query logic:
   ```python
   # Find FGs with exactly one composition that is a FU
   subquery = (session.query(
       Composition.assembly_id,
       func.count(Composition.id).label('comp_count')
   ).group_by(Composition.assembly_id)
   .having(func.count(Composition.id) == 1)
   .subquery())

   candidates = (session.query(FinishedGood, Composition)
       .join(subquery, FinishedGood.id == subquery.c.assembly_id)
       .join(Composition, FinishedGood.id == Composition.assembly_id)
       .filter(Composition.finished_unit_id.isnot(None))
       .all())
   ```
3. Return analysis results for each candidate

**Files**: `src/services/finished_good_service.py`
**Notes**: This is a read-only analysis function. No modifications yet.

### Subtask T037 - Implement reclassification logic

**Purpose**: Change `assembly_type` from BUNDLE to BARE for identified candidates.

**Steps**:
1. Create function:
   ```python
   def migrate_bare_finished_goods(
       dry_run: bool = True,
       session: Optional[Session] = None
   ) -> Dict:
       """
       Migrate existing bare FGs to correct classification.

       Args:
           dry_run: If True, report what would change without modifying data
           session: Optional session

       Returns:
           Dict with counts: reclassified, already_correct, flagged_for_review
       """
   ```
2. For each candidate from T036:
   - If `assembly_type == BARE` → already correct, skip
   - If `assembly_type == BUNDLE` and single FU component → reclassify to BARE
   - If ambiguous → flag for review (log warning)
3. Support dry_run mode for safety

**Files**: `src/services/finished_good_service.py`

### Subtask T038 - Verify/establish 1:1 FU-FG linkage

**Purpose**: Ensure every FU has a corresponding bare FG (create if missing), and every bare FG has a valid FU.

**Steps**:
1. After reclassification, check all FUs:
   ```python
   # Find FUs without bare FGs
   all_fus = session.query(FinishedUnit).filter(FinishedUnit.yield_type == "EA").all()
   for fu in all_fus:
       bare_fg = find_bare_fg_for_unit(fu.id, session=session)
       if bare_fg is None:
           # FU exists without bare FG → create one
           auto_create_bare_finished_good(fu.id, fu.display_name, fu.category, session=session)
   ```
2. Check bare FGs without valid FU:
   ```python
   # Find bare FGs whose FU no longer exists
   bare_fgs = session.query(FinishedGood).filter(
       FinishedGood.assembly_type == AssemblyType.BARE.value
   ).all()
   for fg in bare_fgs:
       # Check if linked FU exists
       # Flag orphaned bare FGs for review
   ```
3. Report: X FUs gained bare FGs, Y orphaned bare FGs flagged

**Files**: `src/services/finished_good_service.py`

### Subtask T039 - Preserve user metadata during migration

**Purpose**: Ensure notes, description, and other user-added data are not lost during reclassification.

**Steps**:
1. When reclassifying BUNDLE → BARE:
   - Only change `assembly_type` field
   - DO NOT modify `display_name`, `description`, `notes`, `slug`
   - DO NOT modify Composition records
2. When creating bare FGs for orphaned FUs (T038):
   - Use FU's `display_name` and `category` as source
   - Leave notes/description empty (no data to inherit)
3. Log all changes for audit trail

**Files**: `src/services/finished_good_service.py`
**Notes**: The key principle is "only change what needs changing" — `assembly_type` field only.

### Subtask T040 - Write tests: migration correctness

**Purpose**: Verify migration identifies and converts bare FGs correctly.

**Steps**:
1. Test: FG with single FU component + BUNDLE type → reclassified to BARE
2. Test: FG with single FU component + BARE type → already correct, no change
3. Test: FG with multiple components → NOT reclassified (correctly assembled)
4. Test: FU without bare FG → bare FG auto-created
5. Test: dry_run mode reports changes without modifying data
6. Test: idempotent — running twice produces same result

**Files**: `src/tests/test_finished_good_service.py` or `src/tests/test_migration.py`

### Subtask T041 - Write tests: edge cases

**Purpose**: Verify edge cases are handled gracefully.

**Steps**:
1. Test: bare FG with no matching FU (orphaned) → flagged for review
2. Test: user-added notes preserved during reclassification
3. Test: user-added description preserved during reclassification
4. Test: FG with material component (not FU) → NOT reclassified
5. Test: empty database → migration completes without error

**Files**: `src/tests/test_finished_good_service.py` or `src/tests/test_migration.py`

## Test Strategy

- **Run**: `./run-tests.sh -v -k "migrat"`
- **Full suite**: `./run-tests.sh -v`

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Misidentifying assembled FGs as bare | Strict criteria: exactly 1 comp, type=FU, qty=1 |
| Data loss during migration | Only change assembly_type — preserve all other fields |
| Non-idempotent migration | Check before modify; skip already-correct records |

## Definition of Done Checklist

- [ ] `identify_bare_fg_candidates()` correctly finds candidates
- [ ] `migrate_bare_finished_goods()` reclassifies correctly
- [ ] 1:1 FU↔FG linkage verified and established
- [ ] User metadata preserved
- [ ] Dry run mode works
- [ ] Edge cases flagged for review (not silently skipped)
- [ ] Tests cover all scenarios
- [ ] Full test suite passes

## Review Guidance

- Verify strict identification criteria (no false positives)
- Verify only `assembly_type` changes (no other field modifications)
- Verify dry_run mode is accurate
- Check orphaned record handling (flagged, not deleted)

## Activity Log

- 2026-02-08T17:14:59Z - system - lane=planned - Prompt created.
- 2026-02-08T19:29:05Z – unknown – shell_pid=53440 – lane=for_review – Migration functions complete: identify_bare_fg_candidates(), migrate_bare_finished_goods() with dry_run, orphan detection. 14 tests, 3615 full suite pass.
- 2026-02-08T19:46:55Z – unknown – shell_pid=53440 – lane=done – Review passed: Migration functions correct (identify_bare_fg_candidates, migrate_bare_finished_goods), session parameter pattern followed, dry_run verified, orphan detection works, metadata preservation confirmed, idempotent. 14 WP07 tests pass, 3615 full suite pass.
