# Implementation Plan: Finished Goods Quantity Specification

**Branch**: `071-finished-goods-quantity-specification` | **Date**: 2026-01-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/071-finished-goods-quantity-specification/spec.md`

## Summary

Add quantity input fields to the Planning Tab's finished goods selection UI, allowing users to specify how many of each finished good to produce for an event. This completes the basic event definition workflow (recipes + FGs + quantities).

**Technical Approach:**
1. Extend `FGSelectionFrame` UI component to display quantity inputs alongside each FG checkbox
2. Extend `event_service.py` with quantity-aware CRUD methods
3. Follow existing validation patterns (CTkEntry + try/except + colored text feedback)
4. Leverage existing `EventFinishedGood` model which already has `quantity` column with CHECK constraint

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x
**Storage**: SQLite with WAL mode
**Testing**: pytest
**Target Platform**: Desktop (Windows, macOS, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Responsive UI (<100ms input feedback)
**Constraints**: Single-user desktop app, offline-capable
**Scale/Scope**: Personal use tool, ~50 FGs max per event

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Completes event definition workflow for primary user |
| II. Data Integrity & FIFO | PASS | Positive integer validation enforced at UI, service, and DB levels |
| III. Future-Proof Schema | PASS | `EventFinishedGood.quantity` already exists from F068 |
| IV. Test-Driven Development | PASS | Will add unit tests for new service methods |
| V. Layered Architecture | PASS | UI handles input/display, service handles persistence, model defines schema |
| VI. Schema Change Strategy | N/A | No schema changes required |
| VII. Pragmatic Aspiration | PASS | Service layer remains UI-independent; web migration cost is low |

**Desktop Phase Checks:**
- Does this design block web deployment? → NO (service layer is UI-independent)
- Is the service layer UI-independent? → YES
- Does this support AI-assisted JSON import? → YES (existing import/export patterns)
- What's the web migration cost? → LOW (service methods become API endpoints)

## Project Structure

### Documentation (this feature)

```
kitty-specs/071-finished-goods-quantity-specification/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: Pattern research findings
├── data-model.md        # Phase 1: Entity documentation
├── checklists/          # Validation checklists
│   └── requirements.md
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   └── event_finished_good.py    # EXISTS - already has quantity column
├── services/
│   └── event_service.py          # MODIFY - add quantity-aware methods
├── ui/
│   ├── planning_tab.py           # MODIFY - integrate quantity UI
│   └── components/
│       └── fg_selection_frame.py # MODIFY - add quantity inputs
└── tests/
    └── test_event_service.py     # ADD - tests for new methods
```

**Structure Decision**: Standard bake-tracker structure. All changes are modifications to existing files except new test file.

## Implementation Approach

### UI Layer Changes (FGSelectionFrame)

**File**: `src/ui/components/fg_selection_frame.py`

1. Add `CTkEntry(width=80)` quantity input next to each FG checkbox
2. Track quantity values with `Dict[int, ctk.StringVar]` (fg_id → quantity string)
3. Add live validation on keystroke:
   - Empty → valid (FG not selected)
   - Positive integer → valid
   - Zero/negative/non-integer → orange error text
4. Pre-populate from loaded quantities
5. Update `get_selected()` to return `List[Tuple[int, int]]` (fg_id, quantity)

**Validation Pattern** (from `adjustment_dialog.py`):
```python
try:
    qty = int(entry.get().strip())
    if qty <= 0:
        show_error("Must be positive")
except ValueError:
    show_error("Must be integer")
```

### Service Layer Changes (event_service)

**File**: `src/services/event_service.py`

Add three new methods following existing patterns:

1. `get_event_fg_quantities(session, event_id) -> List[Tuple[FinishedGood, int]]`
   - Query EventFinishedGood joined with FinishedGood
   - Return list of (FG object, quantity) tuples

2. `set_event_fg_quantities(session, event_id, fg_quantities: List[Tuple[int, int]]) -> int`
   - Delete existing EventFinishedGood records for event
   - Insert new records with quantities
   - Follow "replace not append" pattern from existing `set_event_finished_goods()`
   - Return count of records created

3. `remove_event_fg(session, event_id, fg_id) -> bool`
   - Delete single EventFinishedGood record
   - Return True if deleted, False if not found

**Session Management**: All methods accept `session` parameter per project conventions.

### Integration (Planning Tab)

**File**: `src/ui/planning_tab.py`

1. Update `_show_fg_selection()` to load quantities via `get_event_fg_quantities()`
2. Update `_on_fg_selection_save()` to save quantities via `set_event_fg_quantities()`
3. Status bar feedback for save success/error

## Complexity Tracking

*No constitution violations - no entries needed.*

## Parallel Work Analysis

*Single developer feature - no parallel work streams needed.*

This feature is small enough for sequential implementation:
1. Service layer methods + tests (foundation)
2. UI component enhancement (depends on service)
3. Integration + manual testing

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| User enters large quantities accidentally | User confirmed: no limit, trust the user |
| Lost quantities when FG becomes unavailable | Acceptable - F070 already notifies user of removal |
| Validation too strict for work-in-progress | Allow saving with empty quantities; validate completeness at higher level |

## References

- **F068 PlanningService patterns**: `src/services/planning/planning_service.py:217-327`
- **EventFinishedGood model**: `src/models/event_finished_good.py`
- **FGSelectionFrame**: `src/ui/components/fg_selection_frame.py`
- **Numeric validation pattern**: `src/ui/dialogs/adjustment_dialog.py:258-306`
- **Quantity input example**: `src/ui/forms/package_form.py:36-143`
