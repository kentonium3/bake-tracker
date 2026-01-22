---
work_package_id: WP10
title: DTO Cost Standardization
lane: "done"
dependencies:
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
subtasks:
- T049
- T050
- T051
- T052
- T053
- T054
phase: Phase 2 - Polish
assignee: 'claude-opus'
agent: "claude-opus"
shell_pid: "86119"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-22T15:30:43Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
- timestamp: '2026-01-22T22:00:00Z'
  lane: done
  agent: claude-opus
  shell_pid: '86119'
  action: Review passed, moved to done
---

# Work Package Prompt: WP10 – DTO Cost Standardization

## Implementation Command

```bash
spec-kitty implement WP10 --base WP09
```

**Note**: This WP depends on all service hardening WPs (WP02-WP09) being complete.

---

## Objectives & Success Criteria

Standardize all DTO cost values to 2-decimal string format for JSON serialization safety and consistency.

**Decision** (from spec phase): 2 decimal places, standard rounding

**Format**: `f"{cost:.2f}"` → `"12.34"` (string, not Decimal)

**Success Criteria**:
- [ ] Utility function `cost_to_string()` exists
- [ ] All `_to_dict` methods return costs as strings
- [ ] JSON serialization works without errors
- [ ] UI code handles string costs correctly
- [ ] Tests updated for string expectations

---

## Context & Constraints

**Current Problem**: Some services return `Decimal` objects, others return strings. This causes:
- JSON serialization errors (`Decimal` isn't JSON-serializable)
- Type mismatches in UI code
- Inconsistent API contract

**Solution**: Convert at DTO boundary (in `_to_dict` methods).

---

## Subtasks & Detailed Guidance

### Subtask T049 – Create cost_to_string utility function

**Location**: Create `src/services/utils.py` (or add to existing utils)

```python
"""Service layer utilities."""

from decimal import Decimal
from typing import Union


def cost_to_string(value: Union[Decimal, float, int, None]) -> str:
    """
    Convert a cost value to a 2-decimal string format.

    This is the standard format for cost values in service DTOs,
    ensuring JSON serialization safety and consistent formatting.

    Args:
        value: Cost value (Decimal, float, int, or None)

    Returns:
        String formatted as "12.34" (2 decimal places).
        Returns "0.00" if value is None.

    Examples:
        >>> cost_to_string(Decimal("12.345"))
        "12.35"
        >>> cost_to_string(12.3)
        "12.30"
        >>> cost_to_string(None)
        "0.00"
    """
    if value is None:
        return "0.00"
    return f"{Decimal(str(value)):.2f}"
```

**Files**: `src/services/utils.py` (new or existing)

---

### Subtask T050 – Audit batch_production_service DTOs

**File**: `src/services/batch_production_service.py`

**Search for `_to_dict` methods and Decimal returns**:
```bash
grep -n "Decimal\|_to_dict\|total_cost\|unit_cost" src/services/batch_production_service.py
```

**Functions to check**:
- `_production_run_to_dict` (line ~593)
- Any other dict-building functions

**Cost fields to convert**:
- `total_ingredient_cost`
- `unit_cost`
- Any other cost/price fields

**Files**: `src/services/batch_production_service.py`

---

### Subtask T051 – Audit assembly_service DTOs

**File**: `src/services/assembly_service.py`

**Search**:
```bash
grep -n "Decimal\|_to_dict\|total_cost\|unit_cost" src/services/assembly_service.py
```

**Functions to check**:
- `_assembly_run_to_dict`
- Other dict builders

**Cost fields to convert**:
- `total_component_cost`
- `total_packaging_cost`
- Any other cost fields

**Files**: `src/services/assembly_service.py`

---

### Subtask T052 – Audit event_service DTOs

**File**: `src/services/event_service.py`

**Search**:
```bash
grep -n "Decimal\|_to_dict\|cost\|total" src/services/event_service.py
```

**Functions/areas to check**:
- `get_event_summary` (returns cost totals)
- `get_event_cost_analysis`
- `get_shopping_list`
- Any other cost-returning functions

**Files**: `src/services/event_service.py`

---

### Subtask T053 – Update all _to_dict methods to use cost_to_string

**Steps**:
1. Add import: `from src.services.utils import cost_to_string`
2. Replace Decimal returns with `cost_to_string()` calls

**Example transformation**:

**Before**:
```python
def _production_run_to_dict(run: ProductionRun) -> Dict[str, Any]:
    return {
        "id": run.id,
        "total_ingredient_cost": run.total_ingredient_cost,  # Returns Decimal
        # ...
    }
```

**After**:
```python
from src.services.utils import cost_to_string

def _production_run_to_dict(run: ProductionRun) -> Dict[str, Any]:
    return {
        "id": run.id,
        "total_ingredient_cost": cost_to_string(run.total_ingredient_cost),  # Returns "12.34"
        # ...
    }
```

**Files**: All service files with `_to_dict` methods

---

### Subtask T054 – Update tests for string cost expectations

**Find tests asserting Decimal**:
```bash
grep -r "Decimal\|\.quantize\|total_cost" src/tests/ --include="*.py"
```

**Update assertions**:

**Before**:
```python
assert result["total_cost"] == Decimal("12.34")
```

**After**:
```python
assert result["total_cost"] == "12.34"
```

**Files**: Test files found by grep

---

## Test Strategy

```bash
./run-tests.sh -v

# Verify JSON serialization
python -c "import json; from src.services.batch_production_service import ...; print(json.dumps(result))"
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| UI expects Decimal | Runtime errors | Search UI for `.quantize()` or Decimal operations |
| Rounding errors | Incorrect displays | Use standard ROUND_HALF_UP |
| Missed cost field | Inconsistency | Comprehensive grep audit |

---

## Definition of Done Checklist

- [ ] `cost_to_string()` utility exists and is tested
- [ ] All `_to_dict` methods in batch_production_service use it
- [ ] All `_to_dict` methods in assembly_service use it
- [ ] All cost returns in event_service use it
- [ ] All tests updated and passing
- [ ] JSON serialization of service responses works

---

## Activity Log

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T21:33:49Z – claude-opus – shell_pid=64105 – lane=doing – Started implementation via workflow command
- 2026-01-22T22:47:27Z – claude-opus – shell_pid=64105 – lane=for_review – DTO cost standardization complete. All 103 event service tests pass. Creates cost_to_string utility, updates service DTOs to return string costs, fixes session parameter bug.
- 2026-01-22T22:54:37Z – claude-opus – shell_pid=86119 – lane=doing – Started review via workflow command
- 2026-01-22T22:55:28Z – claude-opus – shell_pid=86119 – lane=done – Review passed: cost_to_string utility created with ROUND_HALF_UP, all service DTOs updated (24 cost fields), 32 tests pass, bonus session bug fix included
