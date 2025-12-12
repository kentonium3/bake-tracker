---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
title: "Service Layer Foundation"
phase: "Phase 1 - Foundation"
lane: "doing"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-12T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Service Layer Foundation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Add foundational service layer components that enable the UI work in subsequent packages.

**Success Criteria**:
- STATUS_COLORS dictionary added to constants.py with correct hex values
- `get_events_with_progress()` method returns events with production/assembly progress data
- Filter logic works correctly: "active_future", "past", "all", date range
- Unit tests pass for new service method
- No regressions in existing event service tests

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/018-event-production-dashboard/plan.md` - Technical approach
- `kitty-specs/018-event-production-dashboard/spec.md` - FR-009 (colors), FR-016-019 (filtering)
- `kitty-specs/018-event-production-dashboard/research.md` - Color decisions

**Key Constraints**:
- Must use existing `get_production_progress()`, `get_assembly_progress()`, `get_event_overall_progress()` methods
- No new database schema or migrations
- Follow session management patterns per CLAUDE.md

**Architecture**:
- Services layer only - no UI code in this package
- All progress calculations stay in EventService (per layered architecture)

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add STATUS_COLORS to constants.py

**Purpose**: Define color constants for progress status indicators used across UI.

**Files**: `src/utils/constants.py`

**Steps**:
1. Open `src/utils/constants.py`
2. Add the following dictionary after existing constants:

```python
# Progress status colors (Feature 018)
STATUS_COLORS = {
    "not_started": "#808080",      # Gray - 0% progress
    "in_progress": "#FFA500",      # Orange/Amber - 1-99% progress
    "complete": "#28A745",         # Green - 100% progress
    "exceeded": "#20B2AA",         # Light green/teal - >100% progress
}
```

3. Verify import works: `from src.utils.constants import STATUS_COLORS`

**Parallel?**: Yes - can be done independently

**Notes**: Colors match clarification from spec: "Light green/teal (subtle distinction from complete)"

---

### Subtask T002 – Implement get_events_with_progress()

**Purpose**: Provide batch method to fetch multiple events with their progress data efficiently.

**Files**: `src/services/event_service.py`

**Steps**:
1. Add imports at top of file (if not present):
```python
from datetime import date
from typing import List, Dict, Any
```

2. Add the new function after `get_event_overall_progress()` (around line 2060):

```python
# ============================================================================
# Feature 018: Batch Event Progress
# ============================================================================


def get_events_with_progress(
    filter_type: str = "active_future",
    date_from: date = None,
    date_to: date = None
) -> List[Dict[str, Any]]:
    """
    Get all events matching filter with their progress summaries.

    Args:
        filter_type: One of "active_future" (default), "past", "all"
        date_from: Optional start date for date range filter
        date_to: Optional end date for date range filter

    Returns:
        List of dicts with:
        - event: Event instance
        - event_id: int
        - event_name: str
        - event_date: date
        - production_progress: list (from get_production_progress)
        - assembly_progress: list (from get_assembly_progress)
        - overall_progress: dict (from get_event_overall_progress)
    """
    try:
        with session_scope() as session:
            today = date.today()

            # Build base query
            query = session.query(Event)

            # Apply filter based on filter_type
            if filter_type == "active_future":
                query = query.filter(Event.event_date >= today)
            elif filter_type == "past":
                query = query.filter(Event.event_date < today)
            # "all" - no date filter

            # Apply date range if provided
            if date_from:
                query = query.filter(Event.event_date >= date_from)
            if date_to:
                query = query.filter(Event.event_date <= date_to)

            # Order by date, then name
            query = query.order_by(Event.event_date.asc(), Event.name.asc())

            events = query.all()

            # Build result list with progress data
            results = []
            for event in events:
                # Detach event data before session closes
                event_data = {
                    "event": event,
                    "event_id": event.id,
                    "event_name": event.name,
                    "event_date": event.event_date,
                }

            # Close session, then fetch progress (each has own session)
            # This avoids nested session issues per CLAUDE.md

        # Now fetch progress for each event (outside session)
        for event_data in results:
            event_id = event_data["event_id"]
            event_data["production_progress"] = get_production_progress(event_id)
            event_data["assembly_progress"] = get_assembly_progress(event_id)
            event_data["overall_progress"] = get_event_overall_progress(event_id)

        return results

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get events with progress: {str(e)}")
```

**IMPORTANT**: The implementation above has a bug - the `results` list append is missing inside the first loop. Here's the corrected version:

```python
            # Build result list with progress data
            results = []
            for event in events:
                # Capture event data before session closes
                results.append({
                    "event_id": event.id,
                    "event_name": event.name,
                    "event_date": event.event_date,
                })

        # Now fetch progress for each event (outside session)
        for event_data in results:
            event_id = event_data["event_id"]
            event_data["production_progress"] = get_production_progress(event_id)
            event_data["assembly_progress"] = get_assembly_progress(event_id)
            event_data["overall_progress"] = get_event_overall_progress(event_id)

        return results
```

**Note**: We don't return the Event object since it would be detached. Return only primitive/dict data.

**Parallel?**: No - core implementation

**Notes**:
- Each event makes 3 calls to existing progress methods - acceptable for typical 2-10 events
- For 50+ events, consider batch optimization in future
- Follow session management pattern from CLAUDE.md to avoid detached object issues

---

### Subtask T003 – Add tests for get_events_with_progress()

**Purpose**: Verify filter logic and data structure correctness.

**Files**: `src/tests/test_event_service.py`

**Steps**:
1. Add test class after existing event service tests:

```python
class TestGetEventsWithProgress:
    """Tests for get_events_with_progress() - Feature 018."""

    def test_returns_empty_list_when_no_events(self, session):
        """Should return empty list when no events exist."""
        result = event_service.get_events_with_progress()
        assert result == []

    def test_active_future_filter_excludes_past_events(self, session, sample_events):
        """Default filter should only return today's and future events."""
        # sample_events fixture creates past and future events
        result = event_service.get_events_with_progress(filter_type="active_future")

        today = date.today()
        for event_data in result:
            assert event_data["event_date"] >= today

    def test_past_filter_returns_only_past_events(self, session, sample_events):
        """Past filter should only return events before today."""
        result = event_service.get_events_with_progress(filter_type="past")

        today = date.today()
        for event_data in result:
            assert event_data["event_date"] < today

    def test_all_filter_returns_all_events(self, session, sample_events):
        """All filter should return all events regardless of date."""
        result = event_service.get_events_with_progress(filter_type="all")

        # Should have same count as all events
        all_events = event_service.get_all_events()
        assert len(result) == len(all_events)

    def test_date_range_filter(self, session, sample_events):
        """Date range should filter events within bounds."""
        date_from = date(2025, 12, 1)
        date_to = date(2025, 12, 31)

        result = event_service.get_events_with_progress(
            filter_type="all",
            date_from=date_from,
            date_to=date_to
        )

        for event_data in result:
            assert date_from <= event_data["event_date"] <= date_to

    def test_returns_progress_data_structure(self, session, event_with_targets):
        """Should return correct data structure with progress."""
        result = event_service.get_events_with_progress(filter_type="all")

        assert len(result) > 0
        event_data = result[0]

        # Check required keys
        assert "event_id" in event_data
        assert "event_name" in event_data
        assert "event_date" in event_data
        assert "production_progress" in event_data
        assert "assembly_progress" in event_data
        assert "overall_progress" in event_data

        # Check types
        assert isinstance(event_data["production_progress"], list)
        assert isinstance(event_data["assembly_progress"], list)
        assert isinstance(event_data["overall_progress"], dict)

    def test_events_ordered_by_date_then_name(self, session, sample_events):
        """Should return events sorted by date ascending, then name."""
        result = event_service.get_events_with_progress(filter_type="all")

        if len(result) > 1:
            for i in range(len(result) - 1):
                curr = result[i]
                next_evt = result[i + 1]

                # Either date is earlier, or same date with alphabetical name
                assert (curr["event_date"] < next_evt["event_date"] or
                        (curr["event_date"] == next_evt["event_date"] and
                         curr["event_name"] <= next_evt["event_name"]))
```

2. Add fixtures if not present (in conftest.py or test file):

```python
@pytest.fixture
def sample_events(session):
    """Create sample events in past, present, and future."""
    from datetime import timedelta
    today = date.today()

    past_event = event_service.create_event(
        name="Past Event",
        event_date=today - timedelta(days=30)
    )
    future_event = event_service.create_event(
        name="Future Event",
        event_date=today + timedelta(days=30)
    )
    today_event = event_service.create_event(
        name="Today Event",
        event_date=today
    )

    return [past_event, today_event, future_event]

@pytest.fixture
def event_with_targets(session, sample_recipe, sample_finished_good):
    """Create event with production and assembly targets."""
    event = event_service.create_event(
        name="Event With Targets",
        event_date=date.today() + timedelta(days=7)
    )

    event_service.set_production_target(
        event_id=event.id,
        recipe_id=sample_recipe.id,
        target_batches=4
    )

    event_service.set_assembly_target(
        event_id=event.id,
        finished_good_id=sample_finished_good.id,
        target_quantity=10
    )

    return event
```

**Parallel?**: No - depends on T002

**Notes**:
- Adapt fixtures to use existing test infrastructure
- May need to import `from datetime import date, timedelta`

---

## Test Strategy

- Run tests: `pytest src/tests/test_event_service.py -v -k "TestGetEventsWithProgress"`
- Run all event tests: `pytest src/tests/test_event_service.py -v`
- Run full suite: `pytest src/tests -v`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session management issues | Follow CLAUDE.md patterns - don't return ORM objects, return primitive data |
| N+1 query performance | Acceptable for typical 2-10 events; document optimization path for future |
| Filter logic edge cases | Comprehensive tests cover each filter type |

---

## Definition of Done Checklist

- [ ] T001: STATUS_COLORS added to constants.py
- [ ] T002: get_events_with_progress() implemented and works manually
- [ ] T003: All tests pass for new method
- [ ] Existing event service tests still pass (no regressions)
- [ ] Code formatted with black, passes flake8

---

## Review Guidance

**Key Checkpoints**:
1. Verify STATUS_COLORS hex values match spec (gray, orange, green, teal)
2. Verify filter logic handles all cases: active_future, past, all, date range
3. Verify session management follows CLAUDE.md pattern (no detached objects)
4. Verify tests cover all filter combinations

---

## Activity Log

- 2025-12-12T00:00:00Z – system – lane=planned – Prompt created.
- 2025-12-12T20:34:21Z – system – shell_pid= – lane=doing – Moved to doing
