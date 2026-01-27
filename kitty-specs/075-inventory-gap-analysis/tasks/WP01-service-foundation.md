---
work_package_id: WP01
title: Service Foundation & Gap Calculation
lane: "done"
dependencies: []
base_branch: main
base_commit: d79ee82fbc98842196707709c9112e4be7cd209d
created_at: '2026-01-27T21:23:57.183293+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Foundation
assignee: ''
agent: "gemini"
shell_pid: "39276"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-27T23:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Service Foundation & Gap Calculation

## Implementation Command

```bash
spec-kitty implement WP01
```

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the inventory gap analysis service with:
1. `GapItem` dataclass for individual ingredient gap results
2. `GapAnalysisResult` dataclass for structured return values
3. Service file following CLAUDE.md session management pattern
4. Function to look up inventory by ingredient_id
5. Function to calculate gap (needed - on_hand)
6. Main public function `analyze_inventory_gaps(event_id, session=None)`

**Success Criteria:**
- [ ] Service file exists at `src/services/inventory_gap_service.py`
- [ ] All public functions accept `session=None` parameter
- [ ] Gap calculation correct: `gap = max(0, needed - on_hand)`
- [ ] Missing inventory treated as zero (not error)
- [ ] Return type is `GapAnalysisResult` with purchase_items and sufficient_items lists
- [ ] Consumes F074's `aggregate_ingredients_for_event()` output correctly

## Context & Constraints

**Reference Documents:**
- `kitty-specs/075-inventory-gap-analysis/spec.md` - FR-001 through FR-007
- `kitty-specs/075-inventory-gap-analysis/plan.md` - Design decisions D1-D5
- `CLAUDE.md` - Session management pattern (CRITICAL)

**Key Constraints:**
- Pure calculation service - NO database writes
- Follow existing patterns in `src/services/ingredient_aggregation_service.py` (F074)
- Use existing `get_total_quantity(slug)` from inventory_item_service
- Unit matching is exact string comparison (no conversion)

**Architecture:**
```
F074 Output: Dict[(ingredient_id, unit), IngredientTotal]
    │
    ▼
For each (ingredient_id, unit):
    │
    ├─ Query Ingredient by ID → get slug
    │
    ├─ Call get_total_quantity(slug) → Dict[str, Decimal] by unit
    │
    ├─ Look up inventory[unit] (default 0 if missing)
    │
    ├─ Calculate: gap = max(0, needed - on_hand)
    │
    └─ Create GapItem
    │
    ▼
Partition into: purchase_items (gap > 0) | sufficient_items (gap == 0)
    │
    ▼
Return GapAnalysisResult
```

## Subtasks & Detailed Guidance

### Subtask T001 – Create GapItem Dataclass

**Purpose**: Define the data structure for a single ingredient's gap analysis result.

**Steps**:
1. Create `src/services/inventory_gap_service.py`
2. Add imports: `from dataclasses import dataclass` and `from typing import List`
3. Define dataclass:

```python
@dataclass
class GapItem:
    """Gap analysis result for a single ingredient."""
    ingredient_id: int
    ingredient_name: str
    unit: str
    quantity_needed: float
    quantity_on_hand: float
    gap: float  # max(0, needed - on_hand)
```

**Files**: `src/services/inventory_gap_service.py` (new file)
**Parallel?**: No - must be created first

---

### Subtask T002 – Create GapAnalysisResult Dataclass

**Purpose**: Define the return type for the gap analysis function.

**Steps**:
1. Add to the same file:

```python
@dataclass
class GapAnalysisResult:
    """Complete gap analysis result with categorized items."""
    purchase_items: List[GapItem]   # Items where gap > 0
    sufficient_items: List[GapItem]  # Items where gap == 0
```

**Files**: `src/services/inventory_gap_service.py`
**Parallel?**: No - follows T001

---

### Subtask T003 – Create Service File Structure with Session Pattern

**Purpose**: Establish service file following CLAUDE.md session management pattern.

**Steps**:
1. Add module docstring explaining F075 purpose
2. Add required imports:

```python
"""
Inventory Gap Analysis Service for F075.

Compares F074's aggregated ingredient totals against current inventory
to identify items requiring purchase vs items already sufficient.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from src.models import Ingredient
from src.services.database import session_scope
from src.services.exceptions import ValidationError
from src.services.ingredient_aggregation_service import (
    aggregate_ingredients_for_event,
    IngredientTotal,
    IngredientKey,
)
from src.services.inventory_item_service import get_total_quantity
```

**Files**: `src/services/inventory_gap_service.py`
**Parallel?**: No - follows T002

---

### Subtask T004 – Implement Inventory Lookup Helper

**Purpose**: Create helper to get inventory quantity for an ingredient by ID and unit.

**Steps**:
1. Create internal helper function:

```python
def _get_inventory_for_ingredient(
    ingredient_id: int,
    unit: str,
    session: Session,
) -> float:
    """
    Get current inventory quantity for an ingredient in specified unit.

    Args:
        ingredient_id: Ingredient to look up
        unit: Unit to match (exact string match)
        session: Database session

    Returns:
        Quantity on hand in the specified unit, or 0.0 if none found
    """
    # Get ingredient to access slug
    ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if ingredient is None:
        return 0.0

    # Query inventory by slug
    try:
        inventory_by_unit = get_total_quantity(ingredient.slug)
    except Exception:
        # If ingredient not found in inventory, treat as zero
        return 0.0

    # Look up specific unit (exact match)
    quantity = inventory_by_unit.get(unit, Decimal("0.0"))
    return float(quantity)
```

**Key Details**:
- `get_total_quantity(slug)` returns `Dict[str, Decimal]` keyed by unit
- Handle missing ingredient gracefully (return 0)
- Handle missing unit gracefully (return 0)
- Convert Decimal to float for consistency with GapItem

**Files**: `src/services/inventory_gap_service.py`
**Parallel?**: No - needed by T006

---

### Subtask T005 – Implement Gap Calculation Logic

**Purpose**: Create function to calculate gap for a single ingredient.

**Steps**:
1. Create helper function:

```python
def _calculate_gap(
    ingredient_total: IngredientTotal,
    on_hand: float,
) -> GapItem:
    """
    Calculate gap between needed and on-hand quantities.

    Args:
        ingredient_total: Aggregated ingredient need from F074
        on_hand: Current inventory quantity in matching unit

    Returns:
        GapItem with gap = max(0, needed - on_hand)
    """
    needed = ingredient_total.total_quantity
    gap = max(0.0, needed - on_hand)

    return GapItem(
        ingredient_id=ingredient_total.ingredient_id,
        ingredient_name=ingredient_total.ingredient_name,
        unit=ingredient_total.unit,
        quantity_needed=needed,
        quantity_on_hand=on_hand,
        gap=round(gap, 3),  # Maintain 3 decimal precision
    )
```

**Key Details**:
- Gap is never negative: `max(0, needed - on_hand)`
- Round to 3 decimals for consistency with F074
- Preserve all context fields for display

**Files**: `src/services/inventory_gap_service.py`
**Parallel?**: No - needed by T006

---

### Subtask T006 – Implement analyze_inventory_gaps() Main Function

**Purpose**: Main public function following session management pattern.

**Steps**:
1. Create public function with session pattern:

```python
def analyze_inventory_gaps(
    event_id: int,
    session: Session = None,
) -> GapAnalysisResult:
    """
    Analyze inventory gaps for an event's ingredient needs.

    Takes F074's aggregated ingredient totals, queries current inventory,
    and calculates gaps (needed - on_hand) for each ingredient.

    Args:
        event_id: Event to analyze
        session: Optional session for transaction sharing

    Returns:
        GapAnalysisResult with purchase_items and sufficient_items lists

    Raises:
        ValidationError: If event not found (propagated from F074)
    """
    if session is not None:
        return _analyze_inventory_gaps_impl(event_id, session)
    with session_scope() as session:
        return _analyze_inventory_gaps_impl(event_id, session)
```

2. Create implementation function:

```python
def _analyze_inventory_gaps_impl(
    event_id: int,
    session: Session,
) -> GapAnalysisResult:
    """Internal implementation of analyze_inventory_gaps."""
    # Get aggregated ingredient totals from F074
    totals = aggregate_ingredients_for_event(event_id, session=session)

    # Handle empty event
    if not totals:
        return GapAnalysisResult(purchase_items=[], sufficient_items=[])

    # Calculate gaps for each ingredient
    gap_items: List[GapItem] = []

    for (ingredient_id, unit), ingredient_total in totals.items():
        # Get inventory for this ingredient+unit
        on_hand = _get_inventory_for_ingredient(ingredient_id, unit, session)

        # Calculate gap
        gap_item = _calculate_gap(ingredient_total, on_hand)
        gap_items.append(gap_item)

    # Partition into purchase vs sufficient
    # (T007 handles this)
    return _partition_results(gap_items)
```

**Key Details**:
- Pass session to F074's function to share transaction
- Iterate over F074's output dictionary
- Call helper functions for each ingredient

**Files**: `src/services/inventory_gap_service.py`
**Parallel?**: No - core implementation

---

### Subtask T007 – Implement Result Partitioning

**Purpose**: Partition gap items into purchase required vs sufficient lists.

**Steps**:
1. Create helper function:

```python
def _partition_results(gap_items: List[GapItem]) -> GapAnalysisResult:
    """
    Partition gap items into purchase_items and sufficient_items.

    Args:
        gap_items: All calculated gap items

    Returns:
        GapAnalysisResult with items categorized by gap > 0 vs gap == 0
    """
    purchase_items = []
    sufficient_items = []

    for item in gap_items:
        if item.gap > 0:
            purchase_items.append(item)
        else:
            sufficient_items.append(item)

    return GapAnalysisResult(
        purchase_items=purchase_items,
        sufficient_items=sufficient_items,
    )
```

**Key Details**:
- Simple categorization: gap > 0 → purchase, gap == 0 → sufficient
- Every item ends up in exactly one list (per spec requirement)
- No sorting required (can be added later if needed)

**Files**: `src/services/inventory_gap_service.py`
**Parallel?**: No - completes the implementation

---

## Test Strategy

**Run service with:**
```bash
./run-tests.sh src/tests/test_inventory_gap_service.py -v
```

**Manual verification:**
After completing WP01, you can manually verify by adding a simple test at the end of the service file (temporary, remove before commit):

```python
if __name__ == "__main__":
    # Quick manual test - requires an event with batch decisions
    result = analyze_inventory_gaps(1)  # Adjust event_id as needed
    print(f"Purchase items: {len(result.purchase_items)}")
    print(f"Sufficient items: {len(result.sufficient_items)}")
```

**Expected results:**
- Service imports without errors
- Dataclasses instantiate correctly
- Empty event returns empty result

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| get_total_quantity may raise exception for unknown ingredient | Wrap in try/except, return 0.0 |
| Session detachment from nested calls | Pass session to F074 function |
| Circular import | Import IngredientTotal from F074 service |

## Definition of Done Checklist

- [ ] `src/services/inventory_gap_service.py` created
- [ ] `GapItem` dataclass defined with all fields
- [ ] `GapAnalysisResult` dataclass defined
- [ ] `analyze_inventory_gaps()` accepts `session=None`
- [ ] Gap calculation correct: `max(0, needed - on_hand)`
- [ ] Missing inventory returns 0 (not error)
- [ ] Empty event returns empty result
- [ ] Code follows existing service patterns

## Review Guidance

**Key checkpoints:**
1. Session management pattern matches CLAUDE.md exactly
2. GapItem has correct field types (int, str, str, float, float, float)
3. Gap calculation is `max(0, needed - on_hand)` not `needed - on_hand`
4. Missing inventory handled gracefully (0, not exception)
5. F074 integration passes session parameter

## Activity Log

- 2026-01-27T23:30:00Z – system – lane=planned – Prompt created.
- 2026-01-27T21:28:20Z – unknown – shell_pid=37873 – lane=for_review – Service implementation complete: GapItem, GapAnalysisResult dataclasses, analyze_inventory_gaps() with session pattern
- 2026-01-27T21:28:51Z – gemini – shell_pid=39276 – lane=doing – Started review via workflow command
- 2026-01-27T21:31:22Z – gemini – shell_pid=39276 – lane=done – Review passed: All criteria met - GapItem/GapAnalysisResult dataclasses correct, session=None pattern implemented correctly, gap calculation uses max(0, needed-on_hand), missing inventory returns 0 gracefully, F074 integration passes session parameter
