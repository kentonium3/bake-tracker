---
work_package_id: WP03
title: Planning Tab UI
lane: "for_review"
dependencies: [WP02]
base_branch: 068-event-management-planning-data-model-WP02
base_commit: 73589fea0d3b81e174fd1e517a791c76bcf877d1
created_at: '2026-01-26T21:27:41.668699+00:00'
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - UI Layer
assignee: ''
agent: ''
shell_pid: "96745"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-26T19:16:03Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Planning Tab UI

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

**Depends on WP02** - Branch from WP02's completed work:
```bash
spec-kitty implement WP03 --base WP02
```

**🔀 PARALLELIZABLE**: This WP can run simultaneously with WP04 (Event CRUD Dialogs). Both depend on WP02 but work on different files.

**Agent Assignment**: Gemini (parallel worker)

---

## Objectives & Success Criteria

**Goal**: Create the Planning workspace tab with event list view and action buttons.

**Success Criteria**:
- [ ] Planning tab displays in application window
- [ ] Event list shows all events with Name, Date, Attendees, Plan State columns
- [ ] Events sorted by date (most recent first)
- [ ] NULL expected_attendees displays as "-"
- [ ] Single event selection working
- [ ] Action buttons (Create, Edit, Delete) visible
- [ ] Status bar shows feedback messages
- [ ] Refresh updates list after changes

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/068-event-management-planning-data-model/spec.md` (User Stories 1-4)
- Plan: `kitty-specs/068-event-management-planning-data-model/plan.md` (UI patterns)
- Research: `kitty-specs/068-event-management-planning-data-model/research.md` (RQ4: UI patterns)

**Key Patterns to Follow**:
- Study `src/ui/recipes_tab.py` for tab structure (~500+ lines)
- Study `src/ui/widgets/data_table.py` for list widget
- Follow existing CustomTkinter patterns

**Constraints**:
- Do NOT implement dialog logic (that's WP04)
- Do NOT wire to main app window (that's WP05)
- Focus ONLY on the tab component itself
- Use service layer for data access, not direct DB queries

**File Boundary**: This WP owns `src/ui/planning_tab.py` ONLY

---

## Subtasks & Detailed Guidance

### Subtask T015 – Create Planning Tab Skeleton

**Purpose**: Establish the basic tab structure following existing patterns.

**Steps**:
1. Create new file `src/ui/planning_tab.py`
2. Set up the basic class structure:

```python
"""
Planning Tab - Event management for production planning.

Feature 068: Event Management & Planning Data Model
"""

import customtkinter as ctk
from typing import Optional, Callable
from datetime import date

from src.services.event_service import EventService
from src.services.database import session_scope
from src.models import Event, PlanState


class PlanningTab(ctk.CTkFrame):
    """
    Planning workspace tab for event management.

    Displays list of events with planning-related fields and provides
    CRUD actions for event management.
    """

    def __init__(
        self,
        master: ctk.CTk,
        on_create_event: Optional[Callable] = None,
        on_edit_event: Optional[Callable[[Event], None]] = None,
        on_delete_event: Optional[Callable[[Event], None]] = None,
        **kwargs,
    ):
        """
        Initialize Planning tab.

        Args:
            master: Parent widget
            on_create_event: Callback when Create button clicked
            on_edit_event: Callback when Edit button clicked (receives Event)
            on_delete_event: Callback when Delete button clicked (receives Event)
        """
        super().__init__(master, **kwargs)

        self.service = EventService()
        self.selected_event: Optional[Event] = None

        # Store callbacks
        self._on_create_event = on_create_event
        self._on_edit_event = on_edit_event
        self._on_delete_event = on_delete_event

        # Build UI
        self._create_widgets()
        self._layout_widgets()

        # Load initial data
        self.refresh()

    def _create_widgets(self) -> None:
        """Create all UI widgets."""
        # TODO: Implement in T016-T020
        pass

    def _layout_widgets(self) -> None:
        """Position widgets using grid layout."""
        # TODO: Implement in T016-T020
        pass

    def refresh(self) -> None:
        """Refresh the event list from database."""
        # TODO: Implement in T016
        pass

    def _update_status(self, message: str, is_error: bool = False) -> None:
        """Update status bar message."""
        # TODO: Implement in T020
        pass
```

**Files**: `src/ui/planning_tab.py` (new file, start with ~60 lines)
**Parallel?**: No - subsequent subtasks build on this
**Validation**: Class imports without error

---

### Subtask T016 – Implement Event List View Using DataTable

**Purpose**: Display events in a scrollable list with selectable rows.

**Steps**:
1. Study existing DataTable usage in `src/ui/recipes_tab.py`
2. Add DataTable import and creation in `_create_widgets`:

```python
from src.ui.widgets.data_table import DataTable

def _create_widgets(self) -> None:
    """Create all UI widgets."""
    # Event list using DataTable
    self.event_list = DataTable(
        self,
        columns=[
            ("Name", 200),
            ("Date", 100),
            ("Attendees", 100),
            ("Plan State", 120),
        ],
        show_header=True,
        on_select=self._on_event_select,
    )
```

3. Implement refresh method to load events:

```python
def refresh(self) -> None:
    """Refresh the event list from database."""
    with session_scope() as session:
        events = self.service.get_events_for_planning(session)

        # Clear and repopulate list
        self.event_list.clear()

        for event in events:
            # Format display values
            date_str = event.event_date.strftime("%Y-%m-%d") if event.event_date else "-"
            attendees_str = str(event.expected_attendees) if event.expected_attendees else "-"
            state_str = event.plan_state.value.replace("_", " ").title() if event.plan_state else "-"

            self.event_list.add_row(
                event.id,
                [event.name, date_str, attendees_str, state_str],
            )

    self.selected_event = None
    self._update_button_states()
```

**Files**: `src/ui/planning_tab.py` (modify)
**Parallel?**: No - depends on T015
**Notes**:
- If DataTable doesn't exist or has different API, use CTkScrollableFrame with labels
- Preserve event.id for selection handling

---

### Subtask T017 – Add Columns: Name, Date, Expected Attendees, Plan State

**Purpose**: Ensure all required columns are configured correctly.

**Steps**:
1. Verify column configuration in T016's DataTable setup
2. Column specifications:
   - **Name**: 200px width, left aligned
   - **Date**: 100px width, YYYY-MM-DD format
   - **Attendees**: 100px width, display "-" for NULL
   - **Plan State**: 120px width, human-readable (e.g., "In Production")

3. Format plan_state display:
```python
def _format_plan_state(self, state: PlanState) -> str:
    """Format plan state for display."""
    if not state:
        return "-"
    # Convert "in_production" -> "In Production"
    return state.value.replace("_", " ").title()
```

**Files**: `src/ui/planning_tab.py` (modify)
**Parallel?**: No - part of T016 work
**Notes**: This subtask ensures formatting is correct per spec

---

### Subtask T018 – Implement Event Selection Handling

**Purpose**: Track selected event and enable/disable action buttons.

**Steps**:
1. Add selection callback:

```python
def _on_event_select(self, event_id: Optional[int]) -> None:
    """Handle event selection in list."""
    if event_id is None:
        self.selected_event = None
    else:
        with session_scope() as session:
            self.selected_event = session.query(Event).filter(
                Event.id == event_id
            ).first()
            # Detach from session for use in callbacks
            if self.selected_event:
                session.expunge(self.selected_event)

    self._update_button_states()
```

2. Add button state management:

```python
def _update_button_states(self) -> None:
    """Update button states based on selection."""
    has_selection = self.selected_event is not None

    if hasattr(self, "edit_button"):
        self.edit_button.configure(state="normal" if has_selection else "disabled")
    if hasattr(self, "delete_button"):
        self.delete_button.configure(state="normal" if has_selection else "disabled")
```

**Files**: `src/ui/planning_tab.py` (modify)
**Parallel?**: No - depends on T016
**Notes**:
- Use `session.expunge()` to detach selected event from session
- This allows passing to callbacks outside session scope

---

### Subtask T019 – Add Action Buttons: Create, Edit, Delete

**Purpose**: Provide user actions for event CRUD operations.

**Steps**:
1. Create button frame in `_create_widgets`:

```python
# Button frame
self.button_frame = ctk.CTkFrame(self)

self.create_button = ctk.CTkButton(
    self.button_frame,
    text="Create Event",
    command=self._on_create_click,
)

self.edit_button = ctk.CTkButton(
    self.button_frame,
    text="Edit Event",
    command=self._on_edit_click,
    state="disabled",  # Disabled until selection
)

self.delete_button = ctk.CTkButton(
    self.button_frame,
    text="Delete Event",
    command=self._on_delete_click,
    state="disabled",  # Disabled until selection
    fg_color="darkred",
    hover_color="red",
)
```

2. Add button click handlers:

```python
def _on_create_click(self) -> None:
    """Handle Create button click."""
    if self._on_create_event:
        self._on_create_event()

def _on_edit_click(self) -> None:
    """Handle Edit button click."""
    if self.selected_event and self._on_edit_event:
        self._on_edit_event(self.selected_event)

def _on_delete_click(self) -> None:
    """Handle Delete button click."""
    if self.selected_event and self._on_delete_event:
        self._on_delete_event(self.selected_event)
```

3. Layout buttons in `_layout_widgets`:

```python
def _layout_widgets(self) -> None:
    """Position widgets using grid layout."""
    # Configure grid
    self.grid_columnconfigure(0, weight=1)
    self.grid_rowconfigure(1, weight=1)

    # Button frame at top
    self.button_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
    self.create_button.pack(side="left", padx=5)
    self.edit_button.pack(side="left", padx=5)
    self.delete_button.pack(side="left", padx=5)

    # Event list takes remaining space
    self.event_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

    # Status bar at bottom
    self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
```

**Files**: `src/ui/planning_tab.py` (modify)
**Parallel?**: No - depends on T016-T018
**Notes**:
- Delete button styled with red colors for warning
- Callbacks are optional; UI still works without them wired

---

### Subtask T020 – Add Status Bar and Refresh Functionality

**Purpose**: Provide user feedback and list refresh capability.

**Steps**:
1. Add status bar widget in `_create_widgets`:

```python
# Status bar
self.status_bar = ctk.CTkLabel(
    self,
    text="",
    anchor="w",
    text_color="gray",
)
```

2. Implement status update method:

```python
def _update_status(self, message: str, is_error: bool = False) -> None:
    """
    Update status bar message.

    Args:
        message: Status message to display
        is_error: If True, display in red
    """
    color = "red" if is_error else "gray"
    self.status_bar.configure(text=message, text_color=color)

    # Auto-clear after delay (optional)
    if message:
        self.after(5000, lambda: self._update_status(""))
```

3. Add refresh button (optional but recommended):

```python
# In _create_widgets, add to button_frame:
self.refresh_button = ctk.CTkButton(
    self.button_frame,
    text="↻ Refresh",
    command=self.refresh,
    width=80,
)

# In _layout_widgets:
self.refresh_button.pack(side="right", padx=5)
```

4. Update refresh to show status:

```python
def refresh(self) -> None:
    """Refresh the event list from database."""
    try:
        with session_scope() as session:
            events = self.service.get_events_for_planning(session)

            self.event_list.clear()

            for event in events:
                date_str = event.event_date.strftime("%Y-%m-%d") if event.event_date else "-"
                attendees_str = str(event.expected_attendees) if event.expected_attendees else "-"
                state_str = self._format_plan_state(event.plan_state)

                self.event_list.add_row(
                    event.id,
                    [event.name, date_str, attendees_str, state_str],
                )

            self._update_status(f"Loaded {len(events)} events")

    except Exception as e:
        self._update_status(f"Error loading events: {e}", is_error=True)

    self.selected_event = None
    self._update_button_states()
```

**Files**: `src/ui/planning_tab.py` (modify)
**Parallel?**: No - finalizes the tab
**Notes**:
- Status auto-clears after 5 seconds
- Error handling prevents crashes on database issues

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| DataTable API differs from expected | Check existing usage in recipes_tab.py; adapt accordingly |
| Session management in callbacks | Use expunge() to detach objects before passing to callbacks |
| CustomTkinter version differences | Test with project's installed version |

---

## Definition of Done Checklist

- [ ] PlanningTab class created and importable
- [ ] Event list displays with 4 columns
- [ ] Events sorted by date (most recent first)
- [ ] NULL attendees display as "-"
- [ ] Plan state displays human-readable (e.g., "In Production")
- [ ] Single selection works
- [ ] Create button always enabled
- [ ] Edit/Delete buttons enabled only when event selected
- [ ] Status bar shows feedback messages
- [ ] Refresh button/method updates list
- [ ] No direct database access (uses service layer)
- [ ] Code follows existing UI patterns

---

## Review Guidance

**Reviewers should verify**:
1. Tab follows existing patterns (recipes_tab.py)
2. Service layer used for all data access
3. Session management correct (no leaked sessions)
4. Column formatting matches spec
5. Button states update correctly
6. Error handling present for database operations
7. Callbacks are optional (tab works standalone)

---

## Activity Log

- 2026-01-26T19:16:03Z – system – lane=planned – Prompt created.
- 2026-01-26T21:31:24Z – unknown – shell_pid=96745 – lane=for_review – Ready for review: PlanningTab UI component with event list, CRUD buttons, status bar. 331 lines following existing patterns.
