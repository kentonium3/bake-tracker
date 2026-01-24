---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "ProductionPlanSnapshot Model Cleanup"
phase: "Phase 1 - Model Changes (Foundation)"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-24T19:47:15Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – ProductionPlanSnapshot Model Cleanup

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# No dependencies - this is a foundation work package
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

Transform ProductionPlanSnapshot from a calculation cache into a lightweight container by removing all cache-related fields and methods.

**Success Criteria**:
- [ ] `calculation_results` JSON field removed from model
- [ ] Staleness tracking fields removed (requirements_updated_at, recipes_updated_at, bundles_updated_at)
- [ ] Staleness state fields removed (is_stale, stale_reason)
- [ ] Staleness-related methods removed (get_recipe_batches, get_shopping_list, get_aggregated_ingredients, mark_stale, mark_fresh)
- [ ] Model docstring updated to reflect "lightweight container" role
- [ ] No import errors or syntax errors after changes
- [ ] Existing tests updated to not reference removed fields/methods

## Context & Constraints

**Reference Documents**:
- `kitty-specs/065-production-plan-snapshot-refactor/data-model.md` - Schema changes specification
- `kitty-specs/065-production-plan-snapshot-refactor/research.md` - RQ-1 details current fields
- `.kittify/memory/constitution.md` - Principle II (Data Integrity), Principle VI (Schema Change Strategy)

**Key Constraints**:
- Use reset/re-import migration strategy (no Alembic scripts)
- Keep these fields: `event_id`, `calculated_at`, `input_hash`, `shopping_complete`, `shopping_completed_at`, `created_at`, `updated_at`
- This is foundation work - other WPs depend on this cleanup being complete

**Session Management**: Not applicable for model-only changes.

## Subtasks & Detailed Guidance

### Subtask T001 – Remove calculation_results JSON field

**Purpose**: The calculation_results field stores cached batch requirements, shopping list, and aggregated ingredients. This cache pattern is being replaced with on-demand calculation.

**Steps**:
1. Open `src/models/production_plan_snapshot.py`
2. Find the `calculation_results` Column definition:
   ```python
   calculation_results = Column(JSON, nullable=False)
   ```
3. Delete this line entirely
4. Search codebase for references to `calculation_results`:
   ```bash
   grep -r "calculation_results" src/
   ```
5. Note any references found - they will need updating in WP07/WP08

**Files**:
- `src/models/production_plan_snapshot.py` (modify)

**Parallel?**: Yes - can be done alongside T002, T003

**Notes**: The JSON stored recipe_batches, aggregated_ingredients, shopping_list. These will be calculated on-demand in WP07.

---

### Subtask T002 – Remove staleness tracking timestamp fields

**Purpose**: These timestamp fields track when requirements/recipes/bundles were last updated for staleness detection. With immutable snapshots, staleness detection is no longer needed.

**Steps**:
1. In `src/models/production_plan_snapshot.py`, find and remove:
   ```python
   requirements_updated_at = Column(DateTime, nullable=False)
   recipes_updated_at = Column(DateTime, nullable=False)
   bundles_updated_at = Column(DateTime, nullable=False)
   ```
2. Delete all three Column definitions
3. Search for references:
   ```bash
   grep -rE "(requirements_updated_at|recipes_updated_at|bundles_updated_at)" src/
   ```
4. Note references in planning_service.py - they will be removed in WP07

**Files**:
- `src/models/production_plan_snapshot.py` (modify)

**Parallel?**: Yes - can be done alongside T001, T003

**Notes**: These fields were populated by `_get_latest_requirements_timestamp()`, `_get_latest_recipes_timestamp()`, `_get_latest_bundles_timestamp()` in planning_service.py.

---

### Subtask T003 – Remove staleness state fields

**Purpose**: The is_stale boolean and stale_reason string track whether the cached calculation is outdated. With on-demand calculation, these are unnecessary.

**Steps**:
1. In `src/models/production_plan_snapshot.py`, find and remove:
   ```python
   is_stale = Column(Boolean, default=False, nullable=False)
   stale_reason = Column(String(200), nullable=True)
   ```
2. Delete both Column definitions
3. Search for references:
   ```bash
   grep -rE "(is_stale|stale_reason)" src/
   ```
4. Note any UI references - staleness warnings will be removed in WP08

**Files**:
- `src/models/production_plan_snapshot.py` (modify)

**Parallel?**: Yes - can be done alongside T001, T002

**Notes**: UI components may display staleness warnings based on is_stale - those will be removed in WP08.

---

### Subtask T004 – Remove staleness-related methods

**Purpose**: Methods that access calculation_results or manage staleness state are no longer needed after fields are removed.

**Steps**:
1. In `src/models/production_plan_snapshot.py`, find and remove these methods:

   ```python
   def get_recipe_batches(self) -> list:
       """Extract recipe batches from calculation_results."""
       # ... implementation

   def get_shopping_list(self) -> list:
       """Extract shopping list from calculation_results."""
       # ... implementation

   def get_aggregated_ingredients(self) -> list:
       """Extract aggregated ingredients from calculation_results."""
       # ... implementation

   def mark_stale(self, reason: str) -> None:
       """Mark this snapshot as stale with a reason."""
       # ... implementation

   def mark_fresh(self) -> None:
       """Mark this snapshot as fresh (not stale)."""
       # ... implementation
   ```

2. Delete entire method definitions (including docstrings)

3. Search for method usage:
   ```bash
   grep -rE "(get_recipe_batches|get_shopping_list|get_aggregated_ingredients|mark_stale|mark_fresh)" src/
   ```

4. Update model docstring to reflect new purpose:
   ```python
   class ProductionPlanSnapshot(BaseModel):
       """Lightweight container linking an event to its planning timestamp.

       References snapshots via EventProductionTarget.recipe_snapshot_id
       and EventAssemblyTarget.finished_good_snapshot_id.

       Calculation results are computed on-demand via get_plan_summary(),
       not cached in this model.
       """
   ```

**Files**:
- `src/models/production_plan_snapshot.py` (modify)

**Parallel?**: No - should be done after T001-T003 (methods reference removed fields)

**Notes**:
- `get_recipe_batches()` etc. are called from UI and planning_service - those callers will be updated in WP07/WP08
- This completes the model transformation from "cache" to "container"

---

## Test Strategy

**Unit Tests to Update**:
- Find tests that create ProductionPlanSnapshot with calculation_results
- Find tests that call get_recipe_batches(), get_shopping_list(), etc.
- Either remove these tests or update them to not use removed fields/methods

**Search for affected tests**:
```bash
grep -r "ProductionPlanSnapshot" src/tests/
grep -r "calculation_results" src/tests/
grep -r "get_recipe_batches\|get_shopping_list\|mark_stale" src/tests/
```

**Verification**:
```bash
# After changes, ensure no import/syntax errors
python -c "from src.models.production_plan_snapshot import ProductionPlanSnapshot; print('OK')"

# Run existing tests (some may fail - document which ones)
./run-tests.sh src/tests/ -v -k "production_plan" 2>&1 | head -100
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Other code references removed fields | Search codebase first; document references for later WPs |
| Tests fail after removal | Update tests in this WP; complex test fixes deferred to WP09 |
| Import errors from other modules | Check for imports of removed items |

## Definition of Done Checklist

- [ ] All 6 fields removed from ProductionPlanSnapshot model
- [ ] All 5 methods removed from ProductionPlanSnapshot model
- [ ] Model docstring updated to describe lightweight container role
- [ ] No syntax errors: `python -c "from src.models.production_plan_snapshot import ProductionPlanSnapshot"`
- [ ] References to removed fields/methods documented for later WPs
- [ ] `tasks.md` updated with completion status
- [ ] Activity log entry added below

## Review Guidance

Reviewers should verify:
1. Only the specified fields were removed (keep event_id, calculated_at, etc.)
2. Methods removed completely (no orphaned code)
3. Docstring accurately describes new role
4. No unintended side effects in model file

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-24T19:47:15Z – system – lane=planned – Prompt created.
