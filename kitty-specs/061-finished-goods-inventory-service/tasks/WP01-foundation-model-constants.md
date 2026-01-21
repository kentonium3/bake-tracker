---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Foundation - Model and Constants"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "91740"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: []
history:
  - timestamp: "2026-01-21T19:33:38Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Foundation - Model and Constants

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
spec-kitty implement WP01
```

No dependencies - this is the starting work package.

---

## Objectives & Success Criteria

- ✅ `FinishedGoodsAdjustment` model created with all fields, relationships, and CHECK constraints
- ✅ `FinishedUnit` model has `inventory_adjustments` relationship
- ✅ `FinishedGood` model has `inventory_adjustments` relationship
- ✅ `DEFAULT_LOW_STOCK_THRESHOLD` and `FINISHED_GOODS_ADJUSTMENT_REASONS` constants added
- ✅ Service module skeleton exists with session pattern structure
- ✅ All imports work without circular dependencies

## Context & Constraints

**Reference Documents**:
- `kitty-specs/061-finished-goods-inventory-service/data-model.md` - Complete model definition
- `kitty-specs/061-finished-goods-inventory-service/research.md` - Session patterns and existing model analysis
- `kitty-specs/061-finished-goods-inventory-service/plan.md` - Service interface design
- `.kittify/memory/constitution.md` - Architecture principles

**Key Constraints**:
- Follow F060 session ownership pattern (helper function approach)
- Model inherits from `BaseModel` (provides id, uuid, created_at, updated_at)
- CHECK constraints must match data-model.md exactly
- Use `lazy="dynamic"` for potentially large adjustment collections

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create FinishedGoodsAdjustment Model

**Purpose**: Create the audit trail model that records every inventory change.

**Steps**:
1. Create file `src/models/finished_goods_adjustment.py`
2. Import required SQLAlchemy components and BaseModel
3. Define the model class with all fields from data-model.md:
   - `finished_unit_id` (FK, nullable, indexed)
   - `finished_good_id` (FK, nullable, indexed)
   - `quantity_change` (Integer, not null)
   - `previous_count` (Integer, not null)
   - `new_count` (Integer, not null)
   - `reason` (String(50), not null)
   - `notes` (Text, nullable)
   - `adjusted_at` (DateTime, not null, default=utc_now)
4. Add relationships with `back_populates`
5. Add CHECK constraints in `__table_args__`:
   - XOR constraint: exactly one FK must be set
   - Count consistency: `new_count = previous_count + quantity_change`
   - Non-negative: `new_count >= 0`
6. Add `item_type` and `item_name` properties
7. Add `to_dict()` method

**Files**:
- `src/models/finished_goods_adjustment.py` (new file, ~130 lines)

**Reference Code** (from data-model.md):
```python
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
)
from sqlalchemy.orm import relationship
from .base_model import BaseModel
from ..utils.datetime_utils import utc_now

class FinishedGoodsAdjustment(BaseModel):
    __tablename__ = "finished_goods_adjustments"
    # ... see data-model.md for full implementation
```

**Validation**:
- [ ] Model can be imported without errors
- [ ] All fields have correct types and constraints
- [ ] CHECK constraints are syntactically correct

---

### Subtask T002 – Add Relationship to FinishedUnit

**Purpose**: Add the back-reference relationship so FinishedUnit can access its adjustment history.

**Steps**:
1. Open `src/models/finished_unit.py`
2. Add import for the relationship (if not using string reference)
3. Add the relationship after existing relationships:
   ```python
   inventory_adjustments = relationship(
       "FinishedGoodsAdjustment",
       back_populates="finished_unit",
       cascade="all, delete-orphan",
       lazy="dynamic"
   )
   ```

**Files**:
- `src/models/finished_unit.py` (modify, ~5 lines added)

**Parallel**: Yes - can proceed alongside T003, T004 after T001

**Validation**:
- [ ] Relationship added after existing relationships
- [ ] `back_populates` matches the name in FinishedGoodsAdjustment
- [ ] `cascade="all, delete-orphan"` for cleanup on delete

---

### Subtask T003 – Add Relationship to FinishedGood

**Purpose**: Add the back-reference relationship so FinishedGood can access its adjustment history.

**Steps**:
1. Open `src/models/finished_good.py`
2. Add the relationship after existing relationships:
   ```python
   inventory_adjustments = relationship(
       "FinishedGoodsAdjustment",
       back_populates="finished_good",
       cascade="all, delete-orphan",
       lazy="dynamic"
   )
   ```

**Files**:
- `src/models/finished_good.py` (modify, ~5 lines added)

**Parallel**: Yes - can proceed alongside T002, T004 after T001

**Validation**:
- [ ] Relationship added after existing relationships
- [ ] `back_populates` matches the name in FinishedGoodsAdjustment

---

### Subtask T004 – Add Inventory Constants

**Purpose**: Add the threshold and reason constants used by the service.

**Steps**:
1. Open `src/utils/constants.py`
2. Find a suitable location (after existing constants, before helper functions)
3. Add section header and constants:
   ```python
   # ============================================================================
   # Inventory Constants
   # ============================================================================

   # Default threshold for low stock alerts (finished goods)
   DEFAULT_LOW_STOCK_THRESHOLD = 5

   # Valid adjustment reasons for finished goods inventory
   FINISHED_GOODS_ADJUSTMENT_REASONS = [
       "production",   # Production run completed
       "assembly",     # Assembly operation (consume component or create good)
       "consumption",  # Manual consumption
       "spoilage",     # Damaged or expired
       "gift",         # Given away
       "adjustment",   # Manual correction
   ]
   ```

**Files**:
- `src/utils/constants.py` (modify, ~15 lines added)

**Parallel**: Yes - independent of other subtasks

**Validation**:
- [ ] Constants can be imported: `from src.utils.constants import DEFAULT_LOW_STOCK_THRESHOLD, FINISHED_GOODS_ADJUSTMENT_REASONS`
- [ ] Threshold is an integer
- [ ] Reasons list contains all 6 values from spec

---

### Subtask T005 – Create Service Module Skeleton

**Purpose**: Create the service file with imports, docstring, and helper function pattern ready for implementation.

**Steps**:
1. Create file `src/services/finished_goods_inventory_service.py`
2. Add module docstring explaining purpose
3. Add imports:
   - SQLAlchemy components (joinedload)
   - session_scope from database
   - Models (FinishedUnit, FinishedGood, FinishedGoodsAdjustment)
   - Constants (DEFAULT_LOW_STOCK_THRESHOLD, FINISHED_GOODS_ADJUSTMENT_REASONS)
   - Decimal for cost calculations
   - Custom exceptions (create stubs or import existing)
4. Define function stubs with signatures from plan.md:
   - `get_inventory_status(item_type=None, item_id=None, exclude_zero=False, session=None)`
   - `get_low_stock_items(threshold=None, item_type=None, session=None)`
   - `get_total_inventory_value(session=None)`
   - `check_availability(item_type, item_id, quantity, session=None)`
   - `validate_consumption(item_type, item_id, quantity, session=None)`
   - `adjust_inventory(item_type, item_id, quantity, reason, notes=None, session=None)`
5. Each function should have:
   - Docstring explaining purpose, parameters, return value
   - Helper function pattern skeleton:
     ```python
     def public_function(..., session=None):
         """..."""
         if session is not None:
             return _public_function_impl(..., session)
         with session_scope() as session:
             return _public_function_impl(..., session)

     def _public_function_impl(..., session):
         # TODO: Implement in WP02/WP03
         raise NotImplementedError()
     ```

**Files**:
- `src/services/finished_goods_inventory_service.py` (new file, ~150 lines skeleton)

**Validation**:
- [ ] Module imports without errors
- [ ] All 6 public functions defined with correct signatures
- [ ] Helper function pattern in place for each
- [ ] Docstrings document parameters and return types

---

## Test Strategy

No tests required for this WP - foundation only. Tests are in WP07.

Validation:
```python
# Quick import check
from src.models.finished_goods_adjustment import FinishedGoodsAdjustment
from src.models.finished_unit import FinishedUnit
from src.models.finished_good import FinishedGood
from src.utils.constants import DEFAULT_LOW_STOCK_THRESHOLD, FINISHED_GOODS_ADJUSTMENT_REASONS
from src.services import finished_goods_inventory_service

# Verify relationships exist
assert hasattr(FinishedUnit, 'inventory_adjustments')
assert hasattr(FinishedGood, 'inventory_adjustments')
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Use string references in relationships ("FinishedGoodsAdjustment") |
| Model registration | WP06 handles __init__.py updates; skeleton works without it |
| CHECK constraint syntax | Copy pattern from existing models (FinishedUnit has examples) |

---

## Definition of Done Checklist

- [ ] T001: FinishedGoodsAdjustment model created with all fields and constraints
- [ ] T002: FinishedUnit has inventory_adjustments relationship
- [ ] T003: FinishedGood has inventory_adjustments relationship
- [ ] T004: Constants added to constants.py
- [ ] T005: Service skeleton created with all function stubs
- [ ] All imports work without circular dependency errors
- [ ] Code follows existing project patterns

---

## Review Guidance

**Key checkpoints**:
1. Model matches data-model.md exactly
2. CHECK constraints are correct SQL syntax
3. Relationships use correct `back_populates` names
4. Service functions have correct signatures from plan.md
5. Helper function pattern is correct (caller session vs own session)

---

## Activity Log

- 2026-01-21T19:33:38Z – system – lane=planned – Prompt created.
- 2026-01-21T19:54:56Z – claude-opus – shell_pid=88715 – lane=doing – Started implementation via workflow command
- 2026-01-21T20:02:58Z – claude-opus – shell_pid=88715 – lane=for_review – Ready for review: Created FinishedGoodsAdjustment model with CHECK constraints, added inventory_adjustments relationships to FinishedUnit and FinishedGood, added inventory constants, and created service skeleton with 6 function stubs following helper function session pattern. All imports work, all 2581 tests pass.
- 2026-01-21T20:06:19Z – claude-opus – shell_pid=91740 – lane=doing – Started review via workflow command
- 2026-01-21T20:07:48Z – claude-opus – shell_pid=91740 – lane=done – Review passed: Model matches data-model.md with correct CHECK constraints (XOR, count consistency, non-negative). Relationships correctly configured with lazy=dynamic. All 6 service functions have correct signatures per plan.md with helper function session pattern. All imports work, 2581 tests pass.
