---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Service Layer Foundation"
phase: "Phase 1 - Service Layer (Claude)"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "49117"
history:
  - timestamp: "2026-01-07T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Service Layer Foundation

## Objectives & Success Criteria

- Create DepletionReason enum with all required values (PRODUCTION, ASSEMBLY, SPOILAGE, GIFT, CORRECTION, AD_HOC_USAGE, OTHER)
- Create InventoryDepletion model with all attributes from data-model.md
- Export model for clean imports
- Establish relationship between InventoryDepletion and InventoryItem

**Success**: `from src.models import InventoryDepletion` and `from src.models.enums import DepletionReason` work correctly.

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md` (Principle II: Data Integrity, Principle V: Layered Architecture)
- Data Model: `kitty-specs/041-manual-inventory-adjustments/data-model.md`
- Plan: `kitty-specs/041-manual-inventory-adjustments/plan.md`
- Existing enums: `src/models/enums.py` (follow ProductionStatus/LossCategory pattern)
- Existing model: `src/models/inventory_item.py` (add relationship here)

**Constraints**:
- Follow existing `str(Enum)` pattern for DepletionReason
- Model must include UUID for future distributed scenarios (Constitution Principle III)
- Use Numeric(10,3) for quantity, Numeric(10,4) for cost (precision requirements)
- Include all indexes defined in data-model.md

## Subtasks & Detailed Guidance

### Subtask T001 - Add DepletionReason enum [P]

**Purpose**: Provide standardized reason values for both automatic and manual depletions.

**Steps**:
1. Open `src/models/enums.py`
2. Add DepletionReason class following existing pattern:
```python
class DepletionReason(str, Enum):
    """
    Reasons for inventory depletion.

    Automatic (system-generated):
    - PRODUCTION: Recipe execution consumed ingredients
    - ASSEMBLY: Bundle assembly consumed finished units

    Manual (user-initiated):
    - SPOILAGE: Ingredient went bad (mold, weevils, expiration)
    - GIFT: Gave to friend/family
    - CORRECTION: Physical count adjustment
    - AD_HOC_USAGE: Personal/testing usage outside app
    - OTHER: User-specified reason (requires notes)
    """
    # Automatic (system-generated)
    PRODUCTION = "production"
    ASSEMBLY = "assembly"

    # Manual (user-initiated)
    SPOILAGE = "spoilage"
    GIFT = "gift"
    CORRECTION = "correction"
    AD_HOC_USAGE = "ad_hoc_usage"
    OTHER = "other"
```

**Files**: `src/models/enums.py`
**Parallel?**: Yes - can be done independently of T002-T004

### Subtask T002 - Create InventoryDepletion model

**Purpose**: Provide immutable audit trail for all inventory depletions.

**Steps**:
1. Create new file `src/models/inventory_depletion.py`
2. Implement model per data-model.md schema:

```python
"""
InventoryDepletion model for tracking inventory reductions.

This module contains the InventoryDepletion model which provides an
immutable audit trail for all inventory depletions (automatic and manual).
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Index,
    Numeric,
    DateTime,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class InventoryDepletion(BaseModel):
    """
    InventoryDepletion model for immutable depletion audit trail.

    Records every inventory reduction with reason, quantity, cost, and
    user identifier. Supports both automatic depletions (production,
    assembly) and manual adjustments (spoilage, gifts, corrections).

    Attributes:
        inventory_item_id: FK to InventoryItem being depleted
        quantity_depleted: Amount reduced (positive number)
        depletion_reason: Enum value (spoilage, gift, correction, etc.)
        depletion_date: When depletion occurred
        notes: Optional user explanation (required for OTHER reason)
        cost: Calculated cost impact (quantity * unit_cost)
        created_by: User identifier for audit
        created_at: Record creation timestamp
    """

    __tablename__ = "inventory_depletions"

    # UUID for future distributed scenarios
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))

    # Foreign key to InventoryItem
    inventory_item_id = Column(
        Integer,
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Depletion data
    quantity_depleted = Column(Numeric(10, 3), nullable=False)
    depletion_reason = Column(String(50), nullable=False)
    depletion_date = Column(DateTime, nullable=False, default=datetime.now)
    notes = Column(Text, nullable=True)
    cost = Column(Numeric(10, 4), nullable=False)

    # Audit fields
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="depletions")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_depletion_inventory_item", "inventory_item_id"),
        Index("idx_depletion_reason", "depletion_reason"),
        Index("idx_depletion_date", "depletion_date"),
        CheckConstraint("quantity_depleted > 0", name="ck_depletion_quantity_positive"),
    )

    def __repr__(self) -> str:
        return (
            f"InventoryDepletion(id={self.id}, "
            f"inventory_item_id={self.inventory_item_id}, "
            f"quantity={self.quantity_depleted}, "
            f"reason='{self.depletion_reason}')"
        )
```

**Files**: `src/models/inventory_depletion.py` (NEW)
**Parallel?**: No - creates the model that T003, T004 depend on

### Subtask T003 - Export InventoryDepletion from __init__.py

**Purpose**: Enable clean imports like `from src.models import InventoryDepletion`.

**Steps**:
1. Open `src/models/__init__.py`
2. Add import for InventoryDepletion
3. Add to __all__ list if present

**Files**: `src/models/__init__.py`
**Parallel?**: No - must follow T002

### Subtask T004 - Add relationship to InventoryItem model

**Purpose**: Enable bidirectional navigation between InventoryItem and its depletions.

**Steps**:
1. Open `src/models/inventory_item.py`
2. Add relationship to depletions:
```python
# Add to relationships section
depletions = relationship("InventoryDepletion", back_populates="inventory_item")
```

**Files**: `src/models/inventory_item.py`
**Parallel?**: No - depends on T002 existing

## Test Strategy

Minimal testing at this stage - verification that imports work:
```python
# Quick verification (not formal test)
from src.models import InventoryDepletion
from src.models.enums import DepletionReason

assert DepletionReason.SPOILAGE.value == "spoilage"
assert hasattr(InventoryDepletion, "inventory_item_id")
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema change requires DB reset | Data loss | Export data before testing, reimport after |
| Circular import with InventoryItem | ImportError | Use string reference in relationship |
| UUID generation performance | Slow inserts | uuid4() is fast; not a concern for desktop |

## Definition of Done Checklist

- [ ] DepletionReason enum added to `src/models/enums.py`
- [ ] InventoryDepletion model created in `src/models/inventory_depletion.py`
- [ ] Model exported from `src/models/__init__.py`
- [ ] Relationship added to InventoryItem model
- [ ] `from src.models import InventoryDepletion` works
- [ ] `from src.models.enums import DepletionReason` works

## Review Guidance

- Verify enum values match data-model.md exactly
- Verify all model attributes match data-model.md
- Check indexes are defined per schema
- Verify relationship is bidirectional (back_populates on both sides)

## Activity Log

- 2026-01-07T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-07T16:46:58Z – claude – shell_pid=32899 – lane=doing – Started implementation of Service Layer Foundation
- 2026-01-07T16:53:35Z – claude – shell_pid=32899 – lane=for_review – Moved to for_review
- 2026-01-07T20:24:16Z – claude-reviewer – shell_pid=49117 – lane=done – Code review approved: All requirements met - DepletionReason enum and InventoryDepletion model correctly implemented
