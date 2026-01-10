---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
title: "Dynamic Cost Calculation Methods"
phase: "Phase 1 - Model Layer Fixes"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-10T07:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Dynamic Cost Calculation Methods

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Primary Goal**: Add `calculate_current_cost()` methods to FinishedUnit and FinishedGood models. These methods are the foundation for all cost fixes in F046.

**Success Criteria**:
1. `FinishedUnit.calculate_current_cost()` returns weighted average cost from ProductionRun history
2. `FinishedGood.calculate_current_cost()` returns sum of component costs via Composition
3. Both methods return `Decimal("0.0000")` when no cost data available
4. Both methods use 4 decimal places for precision (`Decimal("0.0001")` quantization)
5. Existing tests continue to pass

## Context & Constraints

**Why This Matters**: F045 removed stored `total_cost` and `unit_cost` fields from definition models, but did not add replacement dynamic calculation methods. This left multiple code paths broken.

**Architecture Principle**: "Costs on Instances, Not Definitions" - definitions don't store costs; costs are calculated dynamically from production/assembly history.

**Key Documents**:
- `kitty-specs/046-finished-goods-bundles-assembly/research/data-model.md` - contains exact implementation code
- `kitty-specs/046-finished-goods-bundles-assembly/plan.md` - overall implementation plan
- `kitty-specs/046-finished-goods-bundles-assembly/spec.md` - user stories and acceptance criteria

**Cost Calculation Chain**:
```
ProductionRun.per_unit_cost (captured at production time)
    ↓ weighted average
FinishedUnit.calculate_current_cost()
    ↓ summed by composition
FinishedGood.calculate_current_cost()
```

## Subtasks & Detailed Guidance

### Subtask T001 - Add FinishedUnit.calculate_current_cost()

**Purpose**: Calculate the current average cost per finished unit based on production history.

**File**: `src/models/finished_unit.py`

**Algorithm**:
1. Query `self.production_runs` relationship (already exists on model)
2. For each run where `actual_yield > 0` and `per_unit_cost` exists:
   - Add `run.per_unit_cost * run.actual_yield` to running total
   - Add `run.actual_yield` to yield total
3. Return `total_cost / total_yield` with 4 decimal places
4. Return `Decimal("0.0000")` if no valid runs

**Implementation**:
```python
from decimal import Decimal

def calculate_current_cost(self) -> Decimal:
    """
    Calculate current average cost per unit from production history.

    Uses weighted average of per_unit_cost from ProductionRuns,
    weighted by actual_yield.

    Returns:
        Decimal: Average cost per unit, or Decimal("0.0000") if no production history
    """
    if not self.production_runs:
        return Decimal("0.0000")

    total_cost = Decimal("0.0000")
    total_yield = 0

    for run in self.production_runs:
        if run.actual_yield and run.actual_yield > 0 and run.per_unit_cost:
            total_cost += run.per_unit_cost * run.actual_yield
            total_yield += run.actual_yield

    if total_yield == 0:
        return Decimal("0.0000")

    return (total_cost / Decimal(str(total_yield))).quantize(Decimal("0.0001"))
```

**Location in file**: Add after the `is_available()` method (around line 180)

**Parallel?**: No - must complete before T002

**Verification**: Create a test script or use Python REPL to verify:
```python
from src.models import FinishedUnit
from src.services.database import session_scope

with session_scope() as session:
    fu = session.query(FinishedUnit).first()
    cost = fu.calculate_current_cost()
    print(f"Cost for {fu.display_name}: {cost}")
```

### Subtask T002 - Add FinishedGood.calculate_current_cost()

**Purpose**: Calculate the current total cost to assemble one FinishedGood from its components.

**File**: `src/models/finished_good.py`

**Algorithm**:
1. Iterate through `self.components` (Composition relationships)
2. For each composition:
   - If `finished_unit_component` exists: get `calculate_current_cost() * component_quantity`
   - If `finished_good_component` exists (nested): get `calculate_current_cost() * component_quantity` (recursive)
   - Ignore `packaging_product_id` (out of F046 scope)
3. Sum all component costs
4. Return sum with 4 decimal places

**Implementation**:
```python
from decimal import Decimal

def calculate_current_cost(self) -> Decimal:
    """
    Calculate current cost from component costs (dynamic, not stored).

    Sums the costs of all FinishedUnit and FinishedGood components,
    multiplied by their quantities in the composition.

    For internal use during assembly recording and event planning.
    NOT displayed in catalog UI.

    Returns:
        Decimal: Total cost for one assembly, or Decimal("0.0000") if no components
    """
    if not self.components:
        return Decimal("0.0000")

    total = Decimal("0.0000")

    for composition in self.components:
        if composition.finished_unit_component:
            unit_cost = composition.finished_unit_component.calculate_current_cost()
            total += unit_cost * Decimal(str(composition.component_quantity))
        elif composition.finished_good_component:
            # Recursive call for nested FinishedGoods
            unit_cost = composition.finished_good_component.calculate_current_cost()
            total += unit_cost * Decimal(str(composition.component_quantity))
        # packaging_product_id ignored per F046 scope (deferred to F04X)

    return total.quantize(Decimal("0.0001"))
```

**Location in file**: Add after the `can_assemble()` method (search for "def can_assemble")

**Parallel?**: No - depends on T001 being complete (uses FinishedUnit.calculate_current_cost())

**Verification**:
```python
from src.models import FinishedGood
from src.services.database import session_scope

with session_scope() as session:
    fg = session.query(FinishedGood).first()
    cost = fg.calculate_current_cost()
    print(f"Cost for {fg.display_name}: {cost}")
```

## Test Strategy

**Minimal Verification** (no formal tests required unless requested):
1. Run existing tests: `pytest src/tests -v -k "finished_unit or finished_good"`
2. Manual verification with REPL as shown above
3. Verify no import errors when loading models

**Edge Cases to Consider**:
- FinishedUnit with no production runs -> returns `Decimal("0.0000")`
- FinishedUnit with runs but all have zero yield -> returns `Decimal("0.0000")`
- FinishedGood with no components -> returns `Decimal("0.0000")`
- FinishedGood with nested FinishedGood components -> recursive calculation works

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Import errors from Decimal | High | Decimal already imported in both files |
| Performance with large history | Medium | Consider limiting to recent runs in future if needed |
| Circular references in nested FGs | Low | Model already has `validate_no_circular_reference()` |

## Definition of Done Checklist

- [ ] T001: `FinishedUnit.calculate_current_cost()` method added
- [ ] T002: `FinishedGood.calculate_current_cost()` method added
- [ ] Both methods return `Decimal("0.0000")` for empty cases
- [ ] Both methods use 4 decimal places
- [ ] Existing tests pass: `pytest src/tests -v`
- [ ] Manual verification shows correct cost calculations
- [ ] No new linting errors: `flake8 src/models/finished_unit.py src/models/finished_good.py`

## Review Guidance

**Key Checkpoints for Reviewers**:
1. Verify method signatures match the specification
2. Check that Decimal precision is consistent (4 decimal places)
3. Verify edge cases handled (empty lists, zero yields)
4. Confirm no changes to existing methods or relationships
5. Verify production_runs relationship is used correctly (lazy loading may apply)

**Context to Revisit**:
- `research/data-model.md` contains the exact implementation specification
- F045 removed `total_cost` and `unit_cost` fields - these methods replace them

## Activity Log

- 2026-01-10T07:30:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-10T12:49:17Z – claude – lane=doing – Started implementation
- 2026-01-10T12:52:11Z – claude – lane=for_review – Ready for review - all subtasks complete, tests pass
- 2026-01-10T13:29:07Z – claude – lane=done – Code review approved: Both calculate_current_cost() methods implemented correctly, tests pass
