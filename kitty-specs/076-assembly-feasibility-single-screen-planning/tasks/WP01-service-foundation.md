---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Assembly Feasibility Service Foundation"
phase: "Phase 1 - Service Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-27T15:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Assembly Feasibility Service Foundation

## Implementation Command

```bash
spec-kitty implement WP01
```

## Objectives & Success Criteria

Create `src/services/assembly_feasibility_service.py` that calculates whether batch production decisions produce enough items to fulfill finished goods requirements.

**Success Criteria**:
- [ ] Service returns AssemblyFeasibilityResult with overall_feasible flag
- [ ] Per-FG status shows quantity_needed, can_assemble, shortfall
- [ ] Bundle components validated recursively
- [ ] Edge cases handled gracefully (empty event, missing decisions)
- [ ] Follows session=None pattern from CLAUDE.md

## Context & Constraints

**Reference Documents**:
- `kitty-specs/076-assembly-feasibility-single-screen-planning/spec.md` - FR-1 Assembly Feasibility Service
- `kitty-specs/076-assembly-feasibility-single-screen-planning/plan.md` - D1, D2 design decisions
- `.kittify/memory/constitution.md` - Layered architecture, test requirements

**Key Integration Points**:
- `src/services/planning_service.py` - Reuse `decompose_event_to_fu_requirements()`
- `src/services/batch_decision_service.py` - Use `get_batch_decisions()`
- `src/models/finished_unit.py` - YieldMode enum for yield calculation

**Session Management Pattern** (from CLAUDE.md):
```python
def some_function(event_id: int, session: Session = None) -> Result:
    if session is not None:
        return _some_function_impl(event_id, session)
    with session_scope() as session:
        return _some_function_impl(event_id, session)
```

## Subtasks & Detailed Guidance

### Subtask T001 – Create Service Dataclasses

**Purpose**: Define the data structures returned by the service.

**Steps**:
1. Create new file `src/services/assembly_feasibility_service.py`
2. Add imports:
   ```python
   from dataclasses import dataclass
   from typing import List, Dict, Optional
   from sqlalchemy.orm import Session
   from src.services.database import session_scope
   ```
3. Define dataclasses:

```python
@dataclass
class ComponentStatus:
    """Status of a single FinishedUnit component."""
    finished_unit_id: int
    finished_unit_name: str
    quantity_needed: int
    quantity_available: int  # From batch decision yields
    is_sufficient: bool  # quantity_available >= quantity_needed

@dataclass
class FGFeasibilityStatus:
    """Feasibility status for one finished good."""
    finished_good_id: int
    finished_good_name: str
    quantity_needed: int  # From EventFinishedGood.quantity
    can_assemble: bool  # All components sufficient
    shortfall: int  # max(0, quantity_needed - min_available)
    components: List[ComponentStatus]  # FU components with status

@dataclass
class AssemblyFeasibilityResult:
    """Complete feasibility analysis for an event."""
    overall_feasible: bool  # All FGs can be assembled
    finished_goods: List[FGFeasibilityStatus]
    decided_count: int  # FUs with batch decisions
    total_fu_count: int  # Total FUs required
```

**Files**: `src/services/assembly_feasibility_service.py` (new file)

**Validation**:
- [ ] All dataclasses have docstrings
- [ ] Types match plan.md Service Interface section

---

### Subtask T002 – Implement Production Availability Calculation

**Purpose**: Calculate how many items each FinishedUnit can produce based on batch decisions.

**Steps**:
1. Add helper function `_get_production_availability()`:

```python
def _get_production_availability(
    event_id: int,
    session: Session,
) -> Dict[int, int]:
    """
    Build map of finished_unit_id → total_yield from batch decisions.

    Args:
        event_id: Event to analyze
        session: Database session

    Returns:
        Dict mapping finished_unit_id to total items that will be produced
    """
    from src.services.batch_decision_service import get_batch_decisions
    from src.models.finished_unit import YieldMode

    decisions = get_batch_decisions(event_id, session=session)

    availability: Dict[int, int] = {}
    for bd in decisions:
        fu = bd.finished_unit
        if fu is None:
            continue

        # Calculate yield per batch (match planning_service.py logic)
        yield_per_batch = fu.items_per_batch or 1
        if fu.yield_mode == YieldMode.BATCH_PORTION:
            yield_per_batch = 1

        total_yield = bd.batches * yield_per_batch

        # Accumulate (same FU may appear in multiple batch decisions)
        availability[fu.id] = availability.get(fu.id, 0) + total_yield

    return availability
```

**Files**: `src/services/assembly_feasibility_service.py`

**Validation**:
- [ ] Yield calculation matches BatchOption.total_yield formula
- [ ] Handles YieldMode.BATCH_PORTION correctly
- [ ] Returns empty dict for event with no decisions

---

### Subtask T003 – Implement FG Feasibility Calculation

**Purpose**: Calculate feasibility for a single FinishedGood by checking all its components.

**Steps**:
1. Add helper function `_calculate_fg_feasibility()`:

```python
def _calculate_fg_feasibility(
    fg_id: int,
    quantity_needed: int,
    availability: Dict[int, int],
    session: Session,
) -> FGFeasibilityStatus:
    """
    Calculate feasibility for one FinishedGood.

    Uses F072 decomposition to get FU requirements, then checks
    if production availability meets those requirements.
    """
    from src.models import FinishedGood
    from src.services.planning_service import _decompose_fg_to_fus

    # Get FG for name
    fg = session.query(FinishedGood).filter(FinishedGood.id == fg_id).first()
    fg_name = fg.name if fg else f"FG#{fg_id}"

    # Decompose to FU requirements (handles bundles recursively)
    try:
        fu_requirements = _decompose_fg_to_fus(
            fg_id,
            quantity_needed,
            session,
            set(),  # Fresh path for cycle detection
            0,      # Start at depth 0
        )
    except Exception:
        # If decomposition fails, treat as infeasible
        return FGFeasibilityStatus(
            finished_good_id=fg_id,
            finished_good_name=fg_name,
            quantity_needed=quantity_needed,
            can_assemble=False,
            shortfall=quantity_needed,
            components=[],
        )

    # Build component status list
    components: List[ComponentStatus] = []
    min_ratio = float('inf')  # Track limiting factor

    for fu_req in fu_requirements:
        fu = fu_req.finished_unit
        needed = fu_req.quantity_needed
        available = availability.get(fu.id, 0)
        is_sufficient = available >= needed

        components.append(ComponentStatus(
            finished_unit_id=fu.id,
            finished_unit_name=fu.display_name,
            quantity_needed=needed,
            quantity_available=available,
            is_sufficient=is_sufficient,
        ))

        # Track ratio for shortfall calculation
        if needed > 0:
            ratio = available / needed
            min_ratio = min(min_ratio, ratio)

    # Determine overall feasibility
    can_assemble = all(c.is_sufficient for c in components)

    # Calculate shortfall (how many FGs we can't make)
    if min_ratio == float('inf'):
        shortfall = 0  # No components needed
    elif min_ratio >= 1.0:
        shortfall = 0  # Can make all
    else:
        # Shortfall = needed - (what we can actually make)
        achievable = int(quantity_needed * min_ratio)
        shortfall = quantity_needed - achievable

    return FGFeasibilityStatus(
        finished_good_id=fg_id,
        finished_good_name=fg_name,
        quantity_needed=quantity_needed,
        can_assemble=can_assemble,
        shortfall=shortfall,
        components=components,
    )
```

**Files**: `src/services/assembly_feasibility_service.py`

**Notes**:
- Reuses `_decompose_fg_to_fus` from planning_service.py (handles bundles)
- Component status includes both needed and available quantities
- Shortfall calculation considers limiting component

**Validation**:
- [ ] Bundle decomposition works for nested FGs
- [ ] Shortfall correctly identifies minimum achievable

---

### Subtask T004 – Implement Main Public Function

**Purpose**: Create the main entry point that orchestrates the feasibility calculation.

**Steps**:
1. Add the main public function:

```python
def calculate_assembly_feasibility(
    event_id: int,
    session: Session = None,
) -> AssemblyFeasibilityResult:
    """
    Calculate assembly feasibility for all FGs in an event.

    Args:
        event_id: Event to analyze
        session: Optional session for transaction sharing

    Returns:
        AssemblyFeasibilityResult with per-FG status and overall feasibility

    Raises:
        ValidationError: If event not found
    """
    if session is not None:
        return _calculate_assembly_feasibility_impl(event_id, session)
    with session_scope() as session:
        return _calculate_assembly_feasibility_impl(event_id, session)


def _calculate_assembly_feasibility_impl(
    event_id: int,
    session: Session,
) -> AssemblyFeasibilityResult:
    """Internal implementation."""
    from src.models import Event, EventFinishedGood
    from src.services.exceptions import ValidationError
    from src.services.planning_service import decompose_event_to_fu_requirements

    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])

    # Get production availability from batch decisions
    availability = _get_production_availability(event_id, session)

    # Get FG selections for this event
    efgs = (
        session.query(EventFinishedGood)
        .filter(EventFinishedGood.event_id == event_id)
        .all()
    )

    # Calculate feasibility for each FG
    fg_statuses: List[FGFeasibilityStatus] = []
    for efg in efgs:
        status = _calculate_fg_feasibility(
            efg.finished_good_id,
            efg.quantity,
            availability,
            session,
        )
        fg_statuses.append(status)

    # Determine overall feasibility
    overall_feasible = all(fg.can_assemble for fg in fg_statuses)

    # Count FU decision coverage
    fu_requirements = decompose_event_to_fu_requirements(event_id, session=session)
    total_fu_count = len(fu_requirements)
    unique_fu_ids = {req.finished_unit.id for req in fu_requirements}
    decided_count = len(unique_fu_ids & set(availability.keys()))

    return AssemblyFeasibilityResult(
        overall_feasible=overall_feasible,
        finished_goods=fg_statuses,
        decided_count=decided_count,
        total_fu_count=total_fu_count,
    )
```

**Files**: `src/services/assembly_feasibility_service.py`

**Validation**:
- [ ] Returns AssemblyFeasibilityResult
- [ ] overall_feasible is True only when ALL FGs can_assemble
- [ ] decided_count and total_fu_count are accurate

---

### Subtask T005 – Handle Edge Cases

**Purpose**: Ensure graceful handling of edge cases.

**Steps**:
1. Verify empty event handling (returns empty results, not error):
   - If no EventFinishedGoods: Return result with empty list, overall_feasible=True

2. Verify missing batch decisions:
   - If no BatchDecisions: availability is empty, all FGs have shortfall
   - decided_count should be 0

3. Verify zero quantity handling:
   - EventFinishedGood with quantity=0 should be skipped or return can_assemble=True

4. Add these edge case checks to the implementation if not already handled.

**Files**: `src/services/assembly_feasibility_service.py`

**Validation**:
- [ ] Empty event returns overall_feasible=True, empty fg list
- [ ] No decisions returns overall_feasible=False (unless no FGs)
- [ ] Zero quantity FGs handled gracefully

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Follow session=None pattern, pass session to all helpers |
| Circular bundle reference | F072's _decompose_fg_to_fus has cycle detection |
| Performance with many FGs | Batch queries where possible |

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] Service file created with proper imports
- [ ] All dataclasses defined with docstrings
- [ ] Session management pattern followed
- [ ] Edge cases handled
- [ ] No linting errors (run `flake8 src/services/assembly_feasibility_service.py`)

## Review Guidance

- Verify yield calculation matches planning_service.py exactly
- Check bundle decomposition reuses F072 logic
- Confirm session parameter threading
- Test edge cases manually if tests aren't written yet

## Activity Log

- 2026-01-27T15:30:00Z – system – lane=planned – Prompt created.
