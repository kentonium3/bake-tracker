# Quickstart: Event Production Dashboard

**Feature**: 018-event-production-dashboard
**Date**: 2025-12-12

## Overview

This feature enhances the Production Dashboard tab to show a multi-event status board instead of single-event selection. Users see all active/future events at a glance with expandable cards for details.

## Prerequisites

- Python 3.10+ with venv activated
- All dependencies installed (`pip install -r requirements.txt`)
- Feature 016 and 017 merged to main (event-centric production model)

## Quick Test

```bash
# Run the app to see current Production Dashboard (Feature 017)
python src/main.py

# Run tests to verify existing functionality
pytest src/tests/test_event_service.py -v
```

## Key Files to Modify

| File | Change |
|------|--------|
| `src/services/event_service.py` | Add `get_events_with_progress()` method |
| `src/utils/constants.py` | Add `STATUS_COLORS` dict |
| `src/ui/widgets/event_card.py` | NEW - Expandable event card widget |
| `src/ui/production_dashboard_tab.py` | Replace single-event selector with card grid |
| `src/tests/test_event_service.py` | Add tests for new service method |

## Implementation Order

1. **Service Layer** (enables UI development)
   - Add `get_events_with_progress()` to event_service.py
   - Add tests for the new method

2. **Constants** (enables UI styling)
   - Add `STATUS_COLORS` to constants.py

3. **Widget** (reusable component)
   - Create `EventCard` widget class
   - Implement collapsed/expanded toggle
   - Add color-coded progress bars

4. **Tab Enhancement** (main UI)
   - Add filter controls
   - Replace event selector with scrollable card container
   - Wire up quick action callbacks

5. **Integration Testing**
   - Test with sample data
   - Verify filter behavior
   - Test edge cases (no events, no targets, exceeded)

## Useful Commands

```bash
# Run specific test file
pytest src/tests/test_event_service.py -v

# Run tests matching pattern
pytest src/tests -v -k "event_progress"

# Run app in debug mode
python src/main.py --debug

# Format code
black src/

# Type check
mypy src/
```

## Sample Test Data Setup

```python
# In Python shell or test setup
from src.services import event_service

# Create test event
event = event_service.create_event(
    name="Test Event",
    event_date=date(2025, 12, 25),
    notes="Testing dashboard"
)

# Add production target
event_service.set_production_target(
    event_id=event.id,
    recipe_id=1,  # Existing recipe
    target_batches=4
)

# Record partial production
batch_production_service.record_batch_production(
    recipe_id=1,
    num_batches=2,
    actual_yield=48,
    event_id=event.id
)

# Now get_events_with_progress() should show 50% progress
```

## Expected Behavior

| Scenario | Expected Result |
|----------|-----------------|
| No events exist | "No events found. Create your first event." |
| Event with no targets | Card shows "No targets set" with link to details |
| 0% progress | Gray progress bar, "Not Started" label |
| 50% progress | Orange progress bar, "In Progress" label |
| 100% progress | Green progress bar, "Complete" label |
| 125% progress | Light green/teal bar, "Exceeded" label |
| Filter: Active & Future | Shows today's events and future events |
| Filter: Past | Shows only events before today |
| Quick Action: Record Production | Opens dialog with event pre-selected |
