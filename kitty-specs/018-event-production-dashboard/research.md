# Research: Event Production Dashboard

**Feature**: 018-event-production-dashboard
**Date**: 2025-12-12

## Research Questions

### 1. What EventService methods exist for progress tracking?

**Decision**: Use existing methods from Feature 016

**Findings**:
- `get_production_progress(event_id)` - Returns list of recipe targets with produced_batches, progress_pct, is_complete
- `get_assembly_progress(event_id)` - Returns list of finished good targets with assembled_quantity, progress_pct, is_complete
- `get_event_overall_progress(event_id)` - Returns aggregated counts: production/assembly targets complete, package fulfillment counts

**Location**: `src/services/event_service.py` lines 1799-2060

**Rationale**: These methods provide all the data needed for individual event progress. Feature 018 needs to call these for multiple events efficiently.

### 2. What is the current ProductionDashboardTab structure?

**Decision**: Enhance existing tab rather than creating new one

**Findings**:
- Feature 017 already created `ProductionDashboardTab` as first/default tab
- Current implementation has single-event selector dropdown
- Progress bars display for one selected event at a time
- Production/Assembly history tables in sub-tabs below

**Location**: `src/ui/production_dashboard_tab.py`

**Rationale**: The tab infrastructure exists. Feature 018 transforms the single-event selector into a multi-event status board.

### 3. How to implement expandable cards in CustomTkinter?

**Decision**: Toggle visibility using pack_forget() / pack()

**Alternatives Considered**:
1. **Separate collapsed/expanded card classes** - More code, harder to manage state
2. **CTkScrollableFrame with dynamic content** - Overkill for simple expand/collapse
3. **Click-to-navigate to Event Detail** - Changes UX, loses inline expansion value

**Rationale**: Toggle visibility is the simplest pattern in Tkinter/CustomTkinter. Create detail frame on init, hide by default, show on click.

### 4. What color values for status indicators?

**Decision**: Use hex color codes in constants.py

**Color Scheme**:
| Status | Color | Hex Code | Rationale |
|--------|-------|----------|-----------|
| Not Started (0%) | Gray | #808080 | Neutral, indicates no action taken |
| In Progress (1-99%) | Orange/Amber | #FFA500 | Warm color indicates ongoing work |
| Complete (100%) | Green | #28A745 | Standard success color |
| Exceeded (>100%) | Light Green/Teal | #20B2AA | Subtle distinction from complete per clarification |

**Rationale**: Standard progress indicator colors. Light green/teal for exceeded was user-specified during clarification session.

### 5. How to filter events by date/status?

**Decision**: Add service method with filter parameters

**Implementation**:
```python
def get_events_with_progress(
    filter_type: str = "active_future",
    date_from: date = None,
    date_to: date = None
) -> List[Dict[str, Any]]
```

**Filter Logic**:
- `"active_future"`: event_date >= today OR event has incomplete targets
- `"past"`: event_date < today AND all targets complete (or no targets)
- `"all"`: No date filter
- Date range: event_date BETWEEN date_from AND date_to

**Rationale**: Centralize filtering logic in service layer. UI just passes filter parameters.

### 6. How do existing dialogs handle event pre-selection?

**Decision**: Existing dialogs already support event_id parameter

**Findings**:
- `RecordProductionDialog` has `event_id` parameter in constructor
- `RecordAssemblyDialog` has `event_id` parameter in constructor
- Both dialogs pre-select the event in their dropdown when event_id is provided

**Location**: `src/ui/dialogs/record_production_dialog.py`, `src/ui/dialogs/record_assembly_dialog.py`

**Rationale**: Quick actions can pass event_id directly to existing dialogs. No dialog modifications needed.

## Dependencies Verified

| Dependency | Status | Notes |
|------------|--------|-------|
| EventService progress methods | EXISTS | Feature 016 |
| ProductionDashboardTab | EXISTS | Feature 017 |
| RecordProductionDialog | EXISTS | Feature 014 |
| RecordAssemblyDialog | EXISTS | Feature 014 |
| Event.event_date field | EXISTS | Original schema |
| FulfillmentStatus enum | EXISTS | Feature 016 |

## Open Questions (Resolved)

None - all research questions answered.
