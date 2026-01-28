# Implementation Plan: Plan Snapshots & Amendments

**Branch**: `078-plan-snapshots-amendments` | **Date**: 2026-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/078-plan-snapshots-amendments/spec.md`

## Summary

Implement plan versioning and amendment tracking for mid-production changes. Key deliverables:

1. **PlanSnapshot model** - Store complete plan state as JSON when production starts
2. **Snapshot service** - Create snapshots on `start_production()` transition, retrieve for comparison
3. **Amendment service** - Create/query amendments with validation (IN_PRODUCTION state only)
4. **UI integration** - Amendment controls, history panel, and comparison view in planning tab

**Critical Finding:** The spec assumed both models exist from F068. Investigation revealed:
- `PlanAmendment` model EXISTS and is ready to use (correct enum, fields, relationships)
- `PlanSnapshot` model DOES NOT EXIST - must be created (ProductionPlanSnapshot is metadata only)

## Technical Context

**Language/Version**: Python 3.10+ (existing stack)
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode (existing database)
**Testing**: pytest (unit + integration tests)
**Target Platform**: Desktop (Windows/macOS)
**Project Type**: Single desktop application
**Performance Goals**: Snapshot creation < 500ms, amendment operations < 100ms
**Constraints**: JSON storage for plan state; append-only amendments
**Scale/Scope**: Single user, < 100 events, < 50 amendments per event

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Solves real workflow need (track production changes) |
| II. Data Integrity | ✅ PASS | Append-only amendments ensure audit trail integrity |
| III. Future-Proof Schema | ✅ PASS | JSON storage flexible for future amendment types |
| IV. Test-Driven Development | ✅ PASS | Service layer will have comprehensive tests |
| V. Layered Architecture | ✅ PASS | Services handle logic; UI displays results |
| VI. Schema Change Strategy | ✅ PASS | One new model (PlanSnapshot); uses existing PlanAmendment |
| VII. Pragmatic Aspiration | ✅ PASS | Web migration cost LOW (services already stateless) |

**Desktop Phase Gates:**
- Does this design block web deployment? → NO
- Is the service layer UI-independent? → YES
- What's the web migration cost? → LOW (JSON storage, stateless services)

## Project Structure

### Documentation (this feature)

```
kitty-specs/078-plan-snapshots-amendments/
├── spec.md              # Feature specification
├── plan.md              # This file
├── data-model.md        # PlanSnapshot model definition
├── checklists/          # Quality checklists
└── tasks/               # Work package files
```

### Source Code (repository root)

```
src/
├── models/
│   ├── plan_snapshot.py          # NEW: JSON snapshot of plan state
│   ├── plan_amendment.py         # EXISTS: Amendment records (F068)
│   └── __init__.py               # MODIFY: Export new model
├── services/
│   ├── plan_snapshot_service.py  # NEW: Snapshot CRUD and comparison
│   ├── plan_amendment_service.py # NEW: Amendment CRUD with validation
│   └── plan_state_service.py     # MODIFY: Hook snapshot creation
├── ui/
│   └── planning_tab.py           # MODIFY: Add amendment UI components
└── tests/
    ├── test_plan_snapshot_service.py    # NEW: Snapshot tests
    └── test_plan_amendment_service.py   # NEW: Amendment tests
```

**Structure Decision**: Extends existing single-project structure. One new model, two new services, UI modifications to planning_tab.py.

## Design Decisions

### D1: PlanSnapshot JSON Schema

**Decision**: Store complete plan state as a single JSON blob.

**Schema**:
```python
{
    "snapshot_version": "1.0",
    "created_at": "ISO-8601 timestamp",
    "recipes": [
        {"recipe_id": int, "recipe_name": str}
    ],
    "finished_goods": [
        {"fg_id": int, "fg_name": str, "quantity": int}
    ],
    "batch_decisions": [
        {"recipe_id": int, "batches": int, "yield_per_batch": int}
    ]
}
```

**Rationale**: Single JSON column is simpler than normalized tables. Snapshot is read-only after creation, so denormalized storage is appropriate.

### D2: Snapshot Creation Hook

**Decision**: Modify `start_production()` in plan_state_service.py to call snapshot creation.

**Approach**:
```python
def start_production(event_id: int, session: Session = None) -> Event:
    # Before state transition, create snapshot
    create_plan_snapshot(event_id, session)
    # Then transition state
    event.plan_state = PlanState.IN_PRODUCTION
```

**Rationale**: Ensures snapshot is always created atomically with state transition. Single transaction guarantees consistency.

### D3: Amendment Application Strategy

**Decision**: Amendments modify live data AND create amendment record.

**Approach**:
- DROP_FG: Delete EventFinishedGood record, create amendment
- ADD_FG: Insert EventFinishedGood record, create amendment
- MODIFY_BATCH: Update BatchDecision record, create amendment

**Rationale**: Live data reflects current plan; snapshot preserves original. Comparison shows diff between snapshot and live data.

### D4: Amendment Validation

**Decision**: Validate in service layer, not model.

**Rules**:
- Event must be in IN_PRODUCTION state
- Reason must be non-empty
- DROP_FG: FG must exist in current plan
- ADD_FG: FG must not already exist in current plan
- MODIFY_BATCH: Recipe must have existing batch decision

### D5: Comparison View Data Structure

**Decision**: Return structured comparison result, not raw diff.

**Dataclass**:
```python
@dataclass
class PlanComparison:
    original_fgs: List[FGComparisonItem]  # From snapshot
    current_fgs: List[FGComparisonItem]   # From live data
    dropped_fgs: List[FGComparisonItem]   # In original, not in current
    added_fgs: List[FGComparisonItem]     # In current, not in original
    modified_batches: List[BatchComparisonItem]  # Changed batch counts
```

## Integration Points

### Existing Services Used

| Service | Function | Purpose in F078 |
|---------|----------|-----------------|
| plan_state_service | start_production() | Hook for snapshot creation |
| event_service | get_event_recipes(), get_event_fg_quantities() | Data for snapshot |
| batch_decision_service | get_batch_decisions() | Batch data for snapshot |

### Existing Models Used

| Model | Purpose |
|-------|---------|
| Event | Parent for snapshots and amendments |
| EventRecipe | Captured in snapshot |
| EventFinishedGood | Captured in snapshot; modified by amendments |
| BatchDecision | Captured in snapshot; modified by amendments |
| PlanAmendment | Already exists - use as-is |

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Large JSON snapshots | Slow queries | Limit to essential fields; lazy load in UI |
| Session management bugs | Silent data loss | Follow session=None pattern; comprehensive tests |
| Amendment race conditions | Data corruption | Validate state before each operation |
| UI complexity | Poor UX | Collapsible panels; progressive disclosure |

## Complexity Tracking

*No constitution violations - complexity is proportional to feature scope.*

| Area | Complexity | Justification |
|------|------------|---------------|
| New model | LOW | Single table with JSON column |
| Services | MEDIUM | Two new services, one hook modification |
| UI | MEDIUM | Three new panels in planning_tab |
| Testing | MEDIUM | Multiple scenarios for each amendment type |

## Parallel Work Analysis

### Dependency Graph

```
WP01: PlanSnapshot Model (Foundation)
  ↓
WP02: Snapshot Service + Hook (depends on WP01)
  ↓
WP03: Amendment Service (can parallel with WP04)  |  WP04: Amendment UI (can parallel with WP03)
  ↓                                                ↓
WP05: Comparison View + Integration (depends on WP02, WP03, WP04)
```

### Work Distribution

- **Sequential (lead agent)**: WP01 → WP02 (model and service foundation)
- **Parallel streams**: WP03 (amendment service) || WP04 (amendment UI)
- **Integration (lead agent)**: WP05 (comparison view, final integration)

### Coordination Points

- After WP02: Both agents can start WP03/WP04 in parallel
- After WP03+WP04: Integration in WP05

## Phase Outputs

### Phase 0: Research (Complete)

No external research needed. All patterns are established:
- JSON storage: Follow existing ProductionPlanSnapshot pattern
- Service pattern: Follow plan_state_service.py structure
- Session management: Accept session=None, use session_scope if None
- UI pattern: Follow planning_tab.py frame structure

### Phase 1: Design Artifacts

**Data Model** (see data-model.md):
- `PlanSnapshot`: New model for JSON plan state storage
- `PlanAmendment`: EXISTS - no changes needed

**Service Interfaces**:

```python
# plan_snapshot_service.py
def create_plan_snapshot(event_id: int, session: Session = None) -> PlanSnapshot
def get_plan_snapshot(event_id: int, session: Session = None) -> Optional[PlanSnapshot]
def get_plan_comparison(event_id: int, session: Session = None) -> PlanComparison

# plan_amendment_service.py
def create_amendment(
    event_id: int,
    amendment_type: AmendmentType,
    amendment_data: dict,
    reason: str,
    session: Session = None
) -> PlanAmendment
def get_amendments(event_id: int, session: Session = None) -> List[PlanAmendment]
def drop_finished_good(event_id: int, fg_id: int, reason: str, session: Session = None) -> PlanAmendment
def add_finished_good(event_id: int, fg_id: int, quantity: int, reason: str, session: Session = None) -> PlanAmendment
def modify_batch_decision(event_id: int, recipe_id: int, new_batches: int, reason: str, session: Session = None) -> PlanAmendment
```

## Next Step

**Run `/spec-kitty.tasks`** to generate work packages for implementation.
