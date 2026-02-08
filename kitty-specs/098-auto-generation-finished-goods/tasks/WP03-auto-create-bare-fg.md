---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "Auto-Create Bare FinishedGood on FU Creation"
phase: "Phase 1 - Core Feature"
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

# Work Package Prompt: WP03 - Auto-Create Bare FinishedGood on FU Creation

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` above.

---

## Review Feedback

*[Empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

Depends on WP02 (recipe save orchestration).

---

## Objectives & Success Criteria

When a FinishedUnit is created (via recipe save), automatically create a corresponding bare FinishedGood (`assembly_type=BARE`) with a single Composition link. This is the **core feature** delivering User Story 1 (P1).

**Success criteria:**
- FU creation triggers bare FG creation within same transaction
- Bare FG has `assembly_type=AssemblyType.BARE`
- Exactly one Composition record links bare FG to source FU (`quantity=1`)
- Bare FG inherits `display_name` and `category` from FU
- No duplicate bare FGs for same FU
- Weight-yield FUs do NOT trigger auto-generation

## Context & Constraints

**Key documents:**
- Spec: `kitty-specs/098-auto-generation-finished-goods/spec.md` (User Story 1)
- Data model: `kitty-specs/098-auto-generation-finished-goods/data-model.md` (Key Queries section)
- Research: `kitty-specs/098-auto-generation-finished-goods/research.md` (Questions 1, 2, 3)

**Existing code to study:**
- `src/services/finished_good_service.py` — `create_finished_good()` (line 226+) and `_create_composition()` (line 1515+)
- `src/models/assembly_type.py` — `AssemblyType.BARE` metadata (line 156+)
- `src/models/composition.py` — `create_unit_composition()` factory method (line 490+)

**Component creation pattern (from existing code):**
```python
# How finished_good_service creates FG + Composition:
finished_good = FinishedGood(display_name=name, assembly_type=assembly_type, ...)
session.add(finished_good)
session.flush()  # Get finished_good.id

composition = Composition.create_unit_composition(
    assembly_id=finished_good.id,
    finished_unit_id=fu_id,
    quantity=1
)
session.add(composition)
```

## Subtasks & Detailed Guidance

### Subtask T013 - Create `find_bare_fg_for_unit()` lookup

**Purpose**: Find the bare FinishedGood linked to a given FinishedUnit via Composition join. This is used by all subsequent WPs (propagation, delete, migration).

**Steps**:
1. Add to `src/services/finished_good_service.py`:
   ```python
   def find_bare_fg_for_unit(finished_unit_id: int, session: Optional[Session] = None) -> Optional[FinishedGood]:
       """
       Find the bare FinishedGood linked to a FinishedUnit.

       Returns None if no bare FG exists for this FU (instead of raising exception,
       since "not found" is a valid state during creation flow).

       Transaction boundary: Read-only query within provided or new session.
       """
   ```
2. Query pattern:
   ```python
   composition = (session.query(Composition)
       .join(FinishedGood, FinishedGood.id == Composition.assembly_id)
       .filter(Composition.finished_unit_id == finished_unit_id)
       .filter(FinishedGood.assembly_type == AssemblyType.BARE.value)
       .first())
   if composition:
       return composition.assembly  # The FinishedGood
   return None
   ```
3. Follow `_impl` pattern for session handling

**Files**: `src/services/finished_good_service.py`
**Parallel?**: Yes (independent of T014)
**Notes**: Returns `Optional[FinishedGood]` (not exception) because "not found" is valid during creation flow. Verify the exact relationship attribute name — it might be `assembly` or accessed differently. Check `Composition` model relationships.

### Subtask T014 - Create `auto_create_bare_finished_good()`

**Purpose**: Create a bare FG + single Composition for a given FU. The core auto-generation function.

**Steps**:
1. Add to `src/services/finished_good_service.py`:
   ```python
   def auto_create_bare_finished_good(
       finished_unit_id: int,
       display_name: str,
       category: Optional[str] = None,
       session: Optional[Session] = None
   ) -> FinishedGood:
       """
       Auto-create a bare FinishedGood for a FinishedUnit.

       Creates a FinishedGood with assembly_type=BARE and a single
       Composition linking to the source FinishedUnit.

       Transaction boundary: Uses provided session or creates new.
       All operations atomic within the session.

       Raises:
           ValidationError: If bare FG already exists for this FU
       """
   ```
2. Implementation:
   ```python
   def _impl(sess):
       # Check for existing bare FG (prevent duplicates)
       existing = find_bare_fg_for_unit(finished_unit_id, session=sess)
       if existing:
           raise ValidationError([f"Bare FinishedGood already exists for FinishedUnit {finished_unit_id}"])

       # Create bare FG using existing service
       component_spec = {
           "type": "finished_unit",
           "id": finished_unit_id,
           "quantity": 1,
       }
       fg = create_finished_good(
           display_name=display_name,
           assembly_type=AssemblyType.BARE,
           components=[component_spec],
           session=sess,
           # Pass category and other fields as needed
       )
       return fg
   ```
3. Leverage existing `create_finished_good()` which handles FG creation + Composition atomically

**Files**: `src/services/finished_good_service.py`
**Parallel?**: Yes (independent of T013 if coded against the interface)
**Notes**: Reuse `create_finished_good()` rather than duplicating FG creation logic. Pass `assembly_type=AssemblyType.BARE`. Check what kwargs `create_finished_good` accepts for category.

### Subtask T015 - Integrate auto-creation into orchestration

**Purpose**: Hook auto-creation into `save_recipe_with_yields()` so bare FGs are created when FUs are created.

**Steps**:
1. In `src/services/recipe_service.py`, within `_reconcile_yield_types()`:
   ```python
   # After creating a new FU:
   fu = create_finished_unit(display_name=..., recipe_id=..., session=session)

   # Auto-create bare FG if yield_type is EA
   if yt.get("yield_type") == "EA":
       auto_create_bare_finished_good(
           finished_unit_id=fu.id,
           display_name=fu.display_name,
           category=fu.category,
           session=session
       )
   ```
2. Add import for `auto_create_bare_finished_good` from `finished_good_service`
3. Only trigger for EA yield types (not SERVING or weight-based)

**Files**: `src/services/recipe_service.py`
**Parallel?**: No (depends on T013, T014)
**Notes**: The FU must be flushed (`session.flush()`) before creating the bare FG so `fu.id` is available. Check if `create_finished_unit()` already flushes.

### Subtask T016 - Handle duplicate prevention

**Purpose**: If auto-creation is triggered but a bare FG already exists for this FU, skip creation gracefully.

**Steps**:
1. In the orchestration, wrap auto-creation with existence check:
   ```python
   existing_fg = find_bare_fg_for_unit(fu.id, session=session)
   if existing_fg is None:
       auto_create_bare_finished_good(...)
   else:
       logger.info(f"Bare FG already exists for FU {fu.id}, skipping auto-creation")
   ```
2. This handles re-saves, imports of existing data, and edge cases
3. Log a warning/info when skipping (for debugging)

**Files**: `src/services/recipe_service.py`
**Parallel?**: No (depends on T015)
**Notes**: Use `find_bare_fg_for_unit()` before calling `auto_create_bare_finished_good()` — don't rely on the validation error.

### Subtask T017 - Write tests: auto-creation happy path

**Purpose**: Verify the core auto-generation flow works end-to-end.

**Steps**:
1. Test: create recipe with EA yield → FU created → bare FG created → Composition links them
2. Test: bare FG has `assembly_type=BARE`
3. Test: bare FG has correct `display_name` and `category`
4. Test: exactly one Composition exists, `quantity=1`, `finished_unit_id` correct
5. Test: recipe variant creates separate FU+FG pair

**Files**: `src/tests/test_finished_good_service.py` or `src/tests/test_auto_generation.py`

### Subtask T018 - Write tests: edge cases

**Purpose**: Verify duplicate prevention, weight-yield skipping, and other edge cases.

**Steps**:
1. Test: second save of same recipe doesn't create duplicate bare FG
2. Test: recipe with SERVING yield type → FU created, NO bare FG created
3. Test: recipe with weight yield → NO FU, NO bare FG
4. Test: recipe with mixed yields (EA + SERVING) → only EA gets bare FG
5. Test: bare FG slug is unique even if display names are similar

**Files**: `src/tests/test_finished_good_service.py` or `src/tests/test_auto_generation.py`

## Test Strategy

- **Unit tests**: Test auto-creation functions in isolation
- **Integration tests**: Test full recipe save → FU → bare FG flow
- **Run**: `./run-tests.sh -v -k "auto_create or bare_fg or auto_generation"`

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Slug collision with existing FGs | Use existing slug generation with retry logic |
| `create_finished_good()` side effects | Study what else it does (logging, audit) and verify appropriate for auto-creation |
| FU.id not available before FG creation | Ensure `session.flush()` after FU creation |

## Definition of Done Checklist

- [ ] `find_bare_fg_for_unit()` returns correct bare FG or None
- [ ] `auto_create_bare_finished_good()` creates FG + Composition atomically
- [ ] Integrated into `save_recipe_with_yields()` create path
- [ ] Duplicate prevention works (no duplicate bare FGs)
- [ ] Only EA yield types trigger auto-generation
- [ ] Tests cover happy path and edge cases
- [ ] Full test suite passes

## Review Guidance

- Verify bare FG uses `AssemblyType.BARE` (not a string literal)
- Verify Composition is created via existing factory method
- Verify duplicate check runs before creation (not after)
- Check that weight/SERVING yields don't trigger auto-creation

## Activity Log

- 2026-02-08T17:14:59Z - system - lane=planned - Prompt created.
