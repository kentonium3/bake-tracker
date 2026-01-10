---
work_package_id: "WP02"
subtasks:
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Fix Composition & Package Models"
phase: "Phase 1 - Model Layer Fixes"
lane: "for_review"
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

# Work Package Prompt: WP02 - Fix Composition & Package Models

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Primary Goal**: Fix broken model methods in Composition and Package that reference removed `total_cost` and `unit_cost` fields.

**Success Criteria**:
1. `Composition.get_component_cost()` returns correct cost without AttributeError
2. `Composition.get_total_cost()` returns correct total without AttributeError
3. `Package.calculate_cost()` returns sum of FinishedGood costs (not hardcoded `0.00`)
4. `Package.get_cost_breakdown()` works without AttributeError
5. `PackageFinishedGood.get_line_cost()` works without AttributeError
6. Event planning page loads without crashes

## Context & Constraints

**Why This Matters**: F045 removed `total_cost` from FinishedGood and `unit_cost` from FinishedUnit, but the Composition and Package models still reference these fields, causing AttributeError crashes.

**Current Broken Code Examples**:
```python
# composition.py - BROKEN
return float(self.finished_unit_component.unit_cost or 0.0)  # AttributeError!
return float(self.finished_good_component.total_cost or 0.0)  # AttributeError!

# package.py - BROKEN
unit_cost = fg.total_cost or Decimal("0.00")  # AttributeError!
```

**Dependencies**: WP01 must be complete (provides `calculate_current_cost()` methods)

**Key Documents**:
- `kitty-specs/046-finished-goods-bundles-assembly/research/data-model.md` - contains fix specifications
- `kitty-specs/046-finished-goods-bundles-assembly/research/research.md` - Issue 2 and Issue 4

## Subtasks & Detailed Guidance

### Subtask T003 - Fix Composition.get_component_cost()

**Purpose**: Fix method that calculates unit cost of a single component.

**File**: `src/models/composition.py`

**Location**: Around lines 205-220 (search for `def get_component_cost`)

**Current Broken Code**:
```python
def get_component_cost(self) -> float:
    if self.finished_unit_component:
        return float(self.finished_unit_component.unit_cost or 0.0)  # BROKEN
    elif self.finished_good_component:
        return float(self.finished_good_component.total_cost or 0.0)  # BROKEN
    elif self.packaging_product:
        return float(self.packaging_product.purchase_price or 0.0)
    else:
        return 0.0
```

**Fixed Code**:
```python
def get_component_cost(self) -> float:
    """
    Get the unit cost of the referenced component.

    Returns:
        Unit cost for the component (uses dynamic calculation for FU/FG)
    """
    if self.finished_unit_component:
        return float(self.finished_unit_component.calculate_current_cost())
    elif self.finished_good_component:
        return float(self.finished_good_component.calculate_current_cost())
    elif self.packaging_product:
        # Packaging products have purchase_price per unit
        return float(self.packaging_product.purchase_price or 0.0)
    else:
        return 0.0
```

**Parallel?**: Yes - can run alongside T004

### Subtask T004 - Fix Composition.get_total_cost()

**Purpose**: Fix method that calculates total cost for this composition entry.

**File**: `src/models/composition.py`

**Location**: Around lines 222-230 (search for `def get_total_cost`)

**Current Code** (uses get_component_cost which we just fixed):
```python
def get_total_cost(self) -> float:
    unit_cost = self.get_component_cost()
    return unit_cost * self.component_quantity
```

**Verification**: This method delegates to `get_component_cost()`, so fixing T003 should fix this. Verify it still works correctly.

**Parallel?**: Yes - can run alongside T003 (both in same file but different methods)

### Subtask T005 - Fix Package.calculate_cost()

**Purpose**: Fix method to actually calculate cost from FinishedGoods instead of returning hardcoded zero.

**File**: `src/models/package.py`

**Location**: Search for `def calculate_cost`

**Current Broken Code**:
```python
def calculate_cost(self) -> Decimal:
    # Feature 045: Costs removed from definitions
    # This will be re-implemented in F046 with dynamic calculation
    return Decimal("0.00")
```

**Fixed Code**:
```python
def calculate_cost(self) -> Decimal:
    """
    Calculate total package cost from FinishedGood component costs.

    Uses dynamic cost calculation from FinishedGood.calculate_current_cost().

    Returns:
        Decimal: Total cost for the package, or Decimal("0.00") if no contents
    """
    if not self.package_finished_goods:
        return Decimal("0.00")

    total = Decimal("0.00")
    for pfg in self.package_finished_goods:
        if pfg.finished_good:
            unit_cost = pfg.finished_good.calculate_current_cost()
            total += unit_cost * Decimal(str(pfg.quantity))

    return total.quantize(Decimal("0.01"))
```

**Note**: Uses 2 decimal places for package-level costs (user-facing display)

**Parallel?**: No - should be done before T006/T007 (related methods)

### Subtask T006 - Fix Package.get_cost_breakdown()

**Purpose**: Fix method that returns cost breakdown by FinishedGood.

**File**: `src/models/package.py`

**Location**: Search for `def get_cost_breakdown`

**Current Broken Code** (typical pattern):
```python
unit_cost = fg.total_cost or Decimal("0.00")  # BROKEN - total_cost doesn't exist
```

**Fix Pattern**: Replace `fg.total_cost` with `fg.calculate_current_cost()`

```python
unit_cost = fg.calculate_current_cost()
```

**Parallel?**: No - should follow T005

### Subtask T007 - Fix PackageFinishedGood.get_line_cost()

**Purpose**: Fix method that calculates line cost for a single FinishedGood in a package.

**File**: `src/models/package.py`

**Location**: Search for `class PackageFinishedGood` then find `def get_line_cost`

**Current Broken Code**:
```python
def get_line_cost(self) -> Decimal:
    unit_cost = self.finished_good.total_cost or Decimal("0.00")  # BROKEN
    return unit_cost * Decimal(str(self.quantity))
```

**Fixed Code**:
```python
def get_line_cost(self) -> Decimal:
    """
    Calculate line cost for this finished good entry.

    Returns:
        Decimal: Unit cost * quantity, or Decimal("0.00") if no finished good
    """
    if not self.finished_good:
        return Decimal("0.00")
    unit_cost = self.finished_good.calculate_current_cost()
    return (unit_cost * Decimal(str(self.quantity))).quantize(Decimal("0.01"))
```

**Parallel?**: No - should follow T005/T006

## Test Strategy

**Minimal Verification**:
1. Run existing tests: `pytest src/tests -v -k "composition or package"`
2. Manual verification in Python REPL:
```python
from src.models import Composition, Package, FinishedGood
from src.services.database import session_scope

with session_scope() as session:
    # Test Composition
    comp = session.query(Composition).first()
    if comp:
        print(f"Component cost: {comp.get_component_cost()}")
        print(f"Total cost: {comp.get_total_cost()}")

    # Test Package
    pkg = session.query(Package).first()
    if pkg:
        print(f"Package cost: {pkg.calculate_cost()}")
```

**Critical Test**: Navigate to Event Planning in the UI and assign a package - it should not crash.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Package has no package_finished_goods | Low | Added null check |
| FinishedGood relationship not loaded | Medium | Eager loading exists in relationships |
| Decimal precision mismatch | Low | Standardized to 2 decimal places for user-facing |

## Definition of Done Checklist

- [ ] T003: `Composition.get_component_cost()` fixed
- [ ] T004: `Composition.get_total_cost()` verified working
- [ ] T005: `Package.calculate_cost()` returns actual cost
- [ ] T006: `Package.get_cost_breakdown()` fixed
- [ ] T007: `PackageFinishedGood.get_line_cost()` fixed
- [ ] Existing tests pass: `pytest src/tests -v`
- [ ] Event planning page loads without errors
- [ ] No new linting errors

## Review Guidance

**Key Checkpoints**:
1. All references to `total_cost` and `unit_cost` replaced with `calculate_current_cost()`
2. Null checks added where relationships might not be loaded
3. Decimal precision appropriate (4 for internal, 2 for user-facing)
4. No new imports needed (Decimal already imported in both files)

**Quick Grep Check**:
```bash
grep -n "total_cost\|unit_cost" src/models/package.py src/models/composition.py
```
Should return NO results for `total_cost` or `unit_cost` attribute access.

## Activity Log

- 2026-01-10T07:30:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-10T12:52:16Z – claude – lane=doing – Started implementation
- 2026-01-10T13:01:41Z – claude – lane=for_review – Moved to for_review
