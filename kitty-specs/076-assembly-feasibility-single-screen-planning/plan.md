# Implementation Plan: Assembly Feasibility & Single-Screen Planning

**Branch**: `076-assembly-feasibility-single-screen-planning` | **Date**: 2026-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/076-assembly-feasibility-single-screen-planning/spec.md`

## Summary

This feature completes Phase 2 planning by integrating F068-F075 into a cohesive single-screen planning experience. Two main deliverables:

1. **Assembly Feasibility Service**: Calculate whether batch production decisions produce enough to fulfill finished goods requirements, with recursive bundle validation
2. **Single-Screen UI Integration**: Consolidate all planning sections (event, recipes, FGs, batches, shopping, assembly) on one screen with real-time update propagation

## Technical Context

**Language/Version**: Python 3.10+ (existing stack)
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x
**Storage**: SQLite with WAL mode (existing)
**Testing**: pytest
**Target Platform**: Desktop (Windows, macOS, Linux)
**Project Type**: Single desktop application
**Performance Goals**: UI updates < 500ms, no perceived lag
**Constraints**: Must fit on 1920x1080 desktop resolution
**Scale/Scope**: Single user, single event at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Single-screen reduces navigation; real-time updates match user expectations |
| II. Data Integrity | ✅ PASS | Uses existing data flow; no new FIFO implications |
| III. Future-Proof Schema | ✅ PASS | No schema changes; leverages existing models |
| IV. Test-Driven Development | ✅ PASS | Service layer will have unit tests; UI integration follows existing patterns |
| V. Layered Architecture | ✅ PASS | Assembly service in services layer; UI consumes service output |
| VI. Schema Change Strategy | ✅ PASS | No schema changes required |
| VII. Pragmatic Aspiration | ✅ PASS | Clean service layer supports web migration; UI-independent logic |

**Desktop Phase Gates:**
- Does this design block web deployment? → NO (service layer is UI-independent)
- Is the service layer UI-independent? → YES
- What's the web migration cost? → LOW (service becomes API endpoint)

## Project Structure

### Documentation (this feature)

```
kitty-specs/076-assembly-feasibility-single-screen-planning/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (N/A - no new models)
├── checklists/          # Quality checklists
└── tasks/               # Work package files
```

### Source Code (repository root)

```
src/
├── services/
│   └── assembly_feasibility_service.py   # NEW: F076 service
├── ui/
│   ├── planning_tab.py                   # MODIFY: Add shopping/assembly panels
│   ├── components/
│   │   ├── shopping_summary_frame.py     # NEW: Shopping list summary widget
│   │   └── assembly_status_frame.py      # NEW: Assembly feasibility widget
│   └── widgets/
└── tests/
    └── test_assembly_feasibility_service.py  # NEW: Service tests
```

**Structure Decision**: Extends existing single-project structure with one new service and two new UI components.

## Design Decisions

### D1: Assembly Feasibility Calculation Strategy

**Decision**: Calculate production from BatchDecisions, compare against EventFinishedGood requirements

**Approach**:
1. Query BatchDecision records for event → get (finished_unit_id, batches) pairs
2. For each FG in EventFinishedGood:
   - Decompose FG to FinishedUnits using existing F072 decomposition
   - Sum up available production from batch decisions for each FU
   - Compare production vs quantity_needed
3. For bundles: recursively validate all component availability

**Key insight**: Reuse `decompose_event_to_fu_requirements()` from planning_service.py - it already handles bundle decomposition with quantity tracking.

### D2: Production Availability Tracking

**Decision**: Track production availability as (finished_unit_id → total_yield) map

**Formula**: For each BatchDecision:
```
total_yield = batches * yield_per_batch
where yield_per_batch = items_per_batch (or 1 for BATCH_PORTION mode)
```

This matches the existing `BatchOption.total_yield` calculation in planning_service.py.

### D3: Single-Screen Layout Strategy

**Decision**: Vertical stacking with compact sections, collapsible optional panels

**Layout order** (top to bottom):
1. Event header (always visible, compact)
2. Recipe selection (collapsible)
3. FG selection with quantities (collapsible)
4. Batch decisions (collapsible)
5. Shopping summary (new, compact)
6. Assembly status (new, prominent)

**Space optimization**: Shopping summary shows counts only ("3 items to purchase, 5 sufficient"). Assembly status shows overall indicator with expandable details.

### D4: Update Propagation Pattern

**Decision**: Cascade callbacks through existing planning_tab.py pattern

**Update chain**:
```
Recipe change → _refresh_fg_selection() → _load_batch_options() → _update_shopping_summary() → _update_assembly_status()
FG quantity change → _load_batch_options() → _update_shopping_summary() → _update_assembly_status()
Batch decision save → _update_shopping_summary() → _update_assembly_status()
```

**Implementation**: Add `_update_shopping_summary()` and `_update_assembly_status()` methods to planning_tab.py, call them after each relevant save operation.

### D5: Status Indicator Design

**Decision**: Use text-based status with color coding (fits CustomTkinter capabilities)

| Status | Display | Color |
|--------|---------|-------|
| All FGs can be assembled | "Ready to Assemble" | Green |
| Some FGs have shortfalls | "Shortfalls Detected" | Orange |
| Critical shortfalls | "Cannot Assemble" | Red |
| No batch decisions yet | "Awaiting Decisions" | Gray |

## Integration Points

### Existing Services Used

| Service | Function | Purpose in F076 |
|---------|----------|-----------------|
| planning_service | decompose_event_to_fu_requirements() | Get FU requirements from FG selections |
| planning_service | calculate_batch_options() | Reference for yield calculations |
| batch_decision_service | get_batch_decisions() | Get user's batch choices |
| inventory_gap_service | analyze_inventory_gaps() | Shopping list data |
| event_service | get_event_fg_quantities() | FG requirements |

### UI Components Extended

| Component | Modification |
|-----------|--------------|
| planning_tab.py | Add shopping summary panel, assembly status panel, update callbacks |
| RecipeSelectionFrame | No changes (uses existing callback) |
| FGSelectionFrame | No changes (uses existing callback) |
| BatchOptionsFrame | No changes (uses existing callback) |

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance with many FGs | UI lag | Batch calculations, debounce rapid changes |
| Layout overflow on small screens | Unusable UI | Collapsible sections, scrollable container |
| Complex bundle validation | Incorrect results | Reuse proven F072 decomposition logic |
| Session management bugs | Silent data loss | Follow session=None pattern consistently |

## Complexity Tracking

*No constitution violations - complexity is proportional to integration scope.*

| Area | Complexity | Justification |
|------|------------|---------------|
| New service | LOW | Single function, reuses existing primitives |
| UI integration | MEDIUM | Multiple panels, callback wiring |
| Testing | LOW | Service tests; UI follows existing patterns |

## Phase 0 Research: Complete

No research needed - this feature integrates existing, proven components.

## Phase 1 Design: Complete

### Data Model

No new database models required. F076 uses:
- EventFinishedGood (F071)
- BatchDecision (F073)
- FinishedUnit, FinishedGood, Recipe (existing)

### Service Interface

```python
# assembly_feasibility_service.py

@dataclass
class ComponentStatus:
    """Status of a single component in a bundle."""
    finished_unit_id: int
    finished_unit_name: str
    quantity_needed: int
    quantity_available: int
    is_sufficient: bool

@dataclass
class FGFeasibilityStatus:
    """Feasibility status for one finished good."""
    finished_good_id: int
    finished_good_name: str
    quantity_needed: int
    can_assemble: bool
    shortfall: int  # 0 if can_assemble
    components: List[ComponentStatus]  # Empty for non-bundles

@dataclass
class AssemblyFeasibilityResult:
    """Complete feasibility analysis for an event."""
    overall_feasible: bool
    finished_goods: List[FGFeasibilityStatus]
    decided_count: int  # How many FUs have batch decisions
    total_fu_count: int  # Total FUs needed

def calculate_assembly_feasibility(
    event_id: int,
    session: Session = None
) -> AssemblyFeasibilityResult:
    """Calculate assembly feasibility for all FGs in an event."""
```

### UI Components

**ShoppingSummaryFrame**: Compact widget showing:
- "X items to purchase" (count from gap_analysis.purchase_items)
- "Y items sufficient" (count from gap_analysis.sufficient_items)
- Expandable detail view (optional)

**AssemblyStatusFrame**: Prominent widget showing:
- Overall status indicator with color
- "X of Y finished goods ready"
- Expandable per-FG details with shortfall amounts

## Next Step

**Run `/spec-kitty.tasks`** to generate work packages for implementation.
