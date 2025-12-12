---
work_package_id: "WP03"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
title: "Dashboard Tab Enhancement"
phase: "Phase 2 - UI Integration"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "60768"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-12T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Dashboard Tab Enhancement

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Transform ProductionDashboardTab from single-event selector to multi-event status board with filters and quick actions.

**Success Criteria**:
- Dashboard shows multiple EventCard widgets in a scrollable container
- Filter dropdown changes visible events (Active & Future, Past, All)
- Date range picker filters by custom date range
- Quick action buttons open correct dialogs with event pre-selected
- Edge cases handled: no events, no targets, empty filter results
- Create Event button in header opens event creation dialog

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/018-event-production-dashboard/plan.md` - Dashboard enhancement approach
- `kitty-specs/018-event-production-dashboard/spec.md` - FR-016 through FR-023
- `src/ui/production_dashboard_tab.py` - Existing tab to modify

**Key Constraints**:
- Keep existing production/assembly history tables (sub-tabs) below the new event cards
- Use existing dialog infrastructure (RecordProductionDialog, RecordAssemblyDialog)
- Filter state resets to default on app restart (session-only)
- Follow layered architecture - no business logic in UI

**Architecture**:
- UI layer consumes `get_events_with_progress()` from WP01
- Uses EventCard widget from WP02
- Callbacks wire to existing dialogs

---

## Subtasks & Detailed Guidance

### Subtask T010 – Add filter controls frame

**Purpose**: Replace single-event selector with filter controls for multi-event display.

**Files**: `src/ui/production_dashboard_tab.py`

**Steps**:
1. Add imports at top:
```python
from datetime import date, datetime
from src.ui.widgets.event_card import EventCard
```

2. Replace `_create_event_progress_section()` with new filter controls. Find the method (around line 149) and replace:

```python
def _create_filter_controls(self):
    """Create filter controls for event selection (Feature 018)."""
    self.filter_frame = ctk.CTkFrame(self)
    self.filter_frame.grid(
        row=1, column=0, sticky="ew", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM)
    )

    # Filter type dropdown
    filter_row = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
    filter_row.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    ctk.CTkLabel(
        filter_row,
        text="Show Events:",
        font=ctk.CTkFont(size=14, weight="bold"),
    ).pack(side="left")

    self.filter_type_var = ctk.StringVar(value="Active & Future")
    self.filter_dropdown = ctk.CTkComboBox(
        filter_row,
        variable=self.filter_type_var,
        values=["Active & Future", "Past Events", "All Events"],
        command=self._on_filter_change,
        width=150,
    )
    self.filter_dropdown.pack(side="left", padx=(PADDING_MEDIUM, PADDING_LARGE))

    # Date range controls
    ctk.CTkLabel(filter_row, text="From:").pack(side="left")
    self.date_from_var = ctk.StringVar(value="")
    self.date_from_entry = ctk.CTkEntry(
        filter_row,
        textvariable=self.date_from_var,
        placeholder_text="YYYY-MM-DD",
        width=100,
    )
    self.date_from_entry.pack(side="left", padx=(5, PADDING_MEDIUM))

    ctk.CTkLabel(filter_row, text="To:").pack(side="left")
    self.date_to_var = ctk.StringVar(value="")
    self.date_to_entry = ctk.CTkEntry(
        filter_row,
        textvariable=self.date_to_var,
        placeholder_text="YYYY-MM-DD",
        width=100,
    )
    self.date_to_entry.pack(side="left", padx=(5, PADDING_MEDIUM))

    # Apply date filter button
    ctk.CTkButton(
        filter_row,
        text="Apply",
        width=60,
        command=self._apply_date_filter,
    ).pack(side="left", padx=(0, PADDING_MEDIUM))

    # Clear date filter button
    ctk.CTkButton(
        filter_row,
        text="Clear",
        width=60,
        fg_color="gray50",
        command=self._clear_date_filter,
    ).pack(side="left")
```

3. Update `_setup_ui()` to call new method instead of old one:
   - Find `self._create_event_progress_section()` call
   - Replace with `self._create_filter_controls()`

**Parallel?**: Yes - can start as soon as WP01/WP02 interface is known

**Notes**: Date entry uses simple text input with YYYY-MM-DD format validation.

---

### Subtask T011 – Create scrollable EventCard container

**Purpose**: Container to hold multiple EventCard widgets with scrolling.

**Files**: `src/ui/production_dashboard_tab.py`

**Steps**:
1. Add after filter controls in `_setup_ui()`:

```python
def _create_event_cards_container(self):
    """Create scrollable container for EventCard widgets (Feature 018)."""
    # Container frame with label
    cards_section = ctk.CTkFrame(self, fg_color="transparent")
    cards_section.grid(
        row=2, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM)
    )
    cards_section.grid_columnconfigure(0, weight=1)
    cards_section.grid_rowconfigure(1, weight=1)

    ctk.CTkLabel(
        cards_section,
        text="Event Status Board",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).grid(row=0, column=0, sticky="w", pady=(0, PADDING_MEDIUM))

    # Scrollable frame for cards
    self.cards_container = ctk.CTkScrollableFrame(
        cards_section,
        height=300,
    )
    self.cards_container.grid(row=1, column=0, sticky="nsew")
    self.cards_container.grid_columnconfigure(0, weight=1)

    # Track card widgets for cleanup
    self._event_cards = []
```

2. Update `_setup_ui()` to call this method and adjust row weights:

```python
def _setup_ui(self):
    """Set up the tab UI layout."""
    self.grid_columnconfigure(0, weight=1)
    self.grid_rowconfigure(3, weight=1)  # History tables get remaining space

    # Header with title and navigation links
    self._create_header()

    # Filter controls (Feature 018 - replaces single event selector)
    self._create_filter_controls()

    # Event cards container (Feature 018)
    self._create_event_cards_container()

    # Tabview for Production/Assembly history sub-tabs (keep existing)
    self.tabview = ctk.CTkTabview(self)
    self.tabview.grid(
        row=3, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
    )
    # ... rest of existing tabview setup
```

**Parallel?**: Yes - can develop in parallel with T010

**Notes**: Container height of 300px is adjustable; uses grid_rowconfigure for responsive layout.

---

### Subtask T012 – Implement _rebuild_event_cards() method

**Purpose**: Fetch events and populate container with EventCard widgets.

**Files**: `src/ui/production_dashboard_tab.py`

**Steps**:
1. Add the rebuild method:

```python
def _rebuild_event_cards(self):
    """Rebuild event cards based on current filter (Feature 018)."""
    # Clear existing cards
    for card in self._event_cards:
        card.destroy()
    self._event_cards = []

    # Determine filter parameters
    filter_text = self.filter_type_var.get()
    filter_type_map = {
        "Active & Future": "active_future",
        "Past Events": "past",
        "All Events": "all",
    }
    filter_type = filter_type_map.get(filter_text, "active_future")

    # Parse date range
    date_from = self._parse_date(self.date_from_var.get())
    date_to = self._parse_date(self.date_to_var.get())

    # Fetch events with progress
    try:
        events_data = event_service.get_events_with_progress(
            filter_type=filter_type,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as e:
        print(f"Error loading events: {e}")
        self._show_error_message(str(e))
        return

    # Handle empty results
    if not events_data:
        self._show_empty_state(filter_type)
        return

    # Create EventCard for each event
    callbacks = self._get_event_card_callbacks()

    for event_data in events_data:
        card = EventCard(
            self.cards_container,
            event_data,
            callbacks,
        )
        card.pack(fill="x", padx=5, pady=5)
        self._event_cards.append(card)

def _parse_date(self, date_str: str):
    """Parse date string (YYYY-MM-DD) to date object."""
    if not date_str or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None
```

**Parallel?**: No - depends on T010, T011

**Notes**: Uses event_service.get_events_with_progress() from WP01.

---

### Subtask T013 – Wire filter change handlers

**Purpose**: Connect filter controls to rebuild event cards.

**Files**: `src/ui/production_dashboard_tab.py`

**Steps**:
1. Add filter change handlers:

```python
def _on_filter_change(self, value: str):
    """Handle filter dropdown change (Feature 018)."""
    self._rebuild_event_cards()

def _apply_date_filter(self):
    """Apply custom date range filter (Feature 018)."""
    # Validate date format
    date_from = self._parse_date(self.date_from_var.get())
    date_to = self._parse_date(self.date_to_var.get())

    if self.date_from_var.get() and not date_from:
        messagebox.showwarning(
            "Invalid Date",
            "From date must be in YYYY-MM-DD format",
        )
        return

    if self.date_to_var.get() and not date_to:
        messagebox.showwarning(
            "Invalid Date",
            "To date must be in YYYY-MM-DD format",
        )
        return

    self._rebuild_event_cards()

def _clear_date_filter(self):
    """Clear date range filter (Feature 018)."""
    self.date_from_var.set("")
    self.date_to_var.set("")
    self._rebuild_event_cards()
```

2. Update `refresh()` method to rebuild cards:

```python
def refresh(self):
    """Refresh event cards and history tables (Feature 018 enhanced)."""
    # Rebuild event cards
    self._rebuild_event_cards()

    # Refresh history tables (existing)
    self._load_production_runs()
    self._load_assembly_runs()
```

**Parallel?**: No - depends on T012

**Notes**: Date validation provides user feedback for invalid formats.

---

### Subtask T014 – Wire quick action callbacks to existing dialogs

**Purpose**: Connect EventCard quick actions to existing dialog infrastructure.

**Files**: `src/ui/production_dashboard_tab.py`

**Steps**:
1. Add callback method:

```python
def _get_event_card_callbacks(self) -> dict:
    """Get callback functions for EventCard quick actions (Feature 018)."""
    return {
        "on_record_production": self._on_record_production,
        "on_record_assembly": self._on_record_assembly,
        "on_shopping_list": self._on_shopping_list,
        "on_event_detail": self._on_event_detail,
        "on_fulfillment_click": self._on_fulfillment_click,
    }

def _on_record_production(self, event_id: int):
    """Open Record Production dialog with event pre-selected."""
    from src.ui.dialogs.record_production_dialog import RecordProductionDialog

    dialog = RecordProductionDialog(
        self,
        event_id=event_id,
        on_success=self.refresh,
    )
    dialog.grab_set()

def _on_record_assembly(self, event_id: int):
    """Open Record Assembly dialog with event pre-selected."""
    from src.ui.dialogs.record_assembly_dialog import RecordAssemblyDialog

    dialog = RecordAssemblyDialog(
        self,
        event_id=event_id,
        on_success=self.refresh,
    )
    dialog.grab_set()

def _on_shopping_list(self, event_id: int):
    """Navigate to shopping list for event."""
    # Option 1: Switch to Reports tab with shopping list
    main_window = self._get_main_window()
    if main_window and hasattr(main_window, "switch_to_tab"):
        main_window.switch_to_tab("Reports")
        messagebox.showinfo(
            "Shopping List",
            f"Use the Reports tab to generate a shopping list for this event.",
        )

def _on_event_detail(self, event_id: int):
    """Open Event Detail window for event."""
    from src.ui.event_detail_window import EventDetailWindow

    # Get event name for window title
    event_name = None
    for card in self._event_cards:
        if card.event_data.get("event_id") == event_id:
            event_name = card.event_data.get("event_name")
            break

    window = EventDetailWindow(
        self,
        event_id=event_id,
        event_name=event_name,
        on_close=self.refresh,
    )

def _on_fulfillment_click(self, event_id: int, status: str):
    """Handle click on fulfillment status - open event detail filtered."""
    # Open event detail with filter hint
    self._on_event_detail(event_id)
    # Note: Filtering by status would require EventDetailWindow enhancement
```

**Parallel?**: No - depends on T012

**Notes**:
- Import dialogs locally to avoid circular imports
- `on_success=self.refresh` ensures cards update after recording
- Shopping list navigation is simplified; could be enhanced in future

---

### Subtask T015 – Handle edge cases

**Purpose**: Show appropriate messages for empty states and errors.

**Files**: `src/ui/production_dashboard_tab.py`

**Steps**:
1. Add empty state and error handlers:

```python
def _show_empty_state(self, filter_type: str):
    """Show empty state message in cards container (Feature 018)."""
    # Clear any existing content
    for widget in self.cards_container.winfo_children():
        widget.destroy()

    empty_frame = ctk.CTkFrame(self.cards_container, fg_color="transparent")
    empty_frame.pack(expand=True, fill="both", pady=50)

    # Different messages based on filter
    if filter_type == "active_future":
        message = "No upcoming events found.\nCreate your first event to get started!"
        show_create = True
    elif filter_type == "past":
        message = "No past events found."
        show_create = False
    else:
        message = "No events found.\nCreate your first event to get started!"
        show_create = True

    ctk.CTkLabel(
        empty_frame,
        text=message,
        font=ctk.CTkFont(size=14),
        text_color="gray60",
        justify="center",
    ).pack(pady=10)

    if show_create:
        ctk.CTkButton(
            empty_frame,
            text="Create Event",
            command=self._on_create_event,
        ).pack(pady=10)

def _show_error_message(self, error: str):
    """Show error message in cards container (Feature 018)."""
    for widget in self.cards_container.winfo_children():
        widget.destroy()

    ctk.CTkLabel(
        self.cards_container,
        text=f"Error loading events: {error}",
        text_color="red",
    ).pack(pady=20)
```

**Parallel?**: Yes - can be done alongside T016

**Notes**: Empty state includes Create Event button for convenience.

---

### Subtask T016 – Add Create Event button to dashboard header

**Purpose**: Allow quick event creation from dashboard.

**Files**: `src/ui/production_dashboard_tab.py`

**Steps**:
1. Modify `_create_header()` to add Create Event button:

```python
def _create_header(self):
    """Create the header section with title and navigation links."""
    header_frame = ctk.CTkFrame(self, fg_color="transparent")
    header_frame.grid(
        row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE
    )

    title = ctk.CTkLabel(
        header_frame,
        text="Production Dashboard",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    title.pack(side="left")

    # Navigation links frame
    nav_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    nav_frame.pack(side="right")

    # Create Event button (Feature 018)
    ctk.CTkButton(
        nav_frame,
        text="Create Event",
        command=self._on_create_event,
        width=120,
        fg_color="#28A745",  # Green for primary action
    ).pack(side="left", padx=PADDING_MEDIUM)

    ctk.CTkButton(
        nav_frame,
        text="Go to Finished Units",
        command=self._navigate_to_finished_units,
        width=150,
    ).pack(side="left", padx=PADDING_MEDIUM)

    ctk.CTkButton(
        nav_frame,
        text="Go to Finished Goods",
        command=self._navigate_to_finished_goods,
        width=150,
    ).pack(side="left", padx=PADDING_MEDIUM)

    # Refresh button
    ctk.CTkButton(
        nav_frame,
        text="Refresh",
        command=self.refresh,
        width=100,
    ).pack(side="left", padx=PADDING_MEDIUM)

def _on_create_event(self):
    """Open dialog to create new event (Feature 018)."""
    # Navigate to Events tab for now
    # Could be enhanced to open a dialog directly
    main_window = self._get_main_window()
    if main_window and hasattr(main_window, "switch_to_tab"):
        main_window.switch_to_tab("Events")
        messagebox.showinfo(
            "Create Event",
            "Use the Events tab to create a new event.",
        )
```

**Parallel?**: Yes - can be done alongside T015

**Notes**: Create Event navigates to Events tab; could be enhanced to open dialog directly.

---

## Test Strategy

Manual testing:
1. Launch app and verify Production Dashboard is default tab
2. Check filter dropdown changes visible events
3. Enter date range and verify filtering works
4. Click each quick action button and verify correct dialog opens
5. Test with no events - verify empty state message
6. Test Create Event button

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Dialog import issues | Use local imports to avoid circular dependencies |
| Layout issues with many cards | CTkScrollableFrame handles scrolling; tested with 10+ cards |
| Date parsing errors | Validate format and show warning message |

---

## Definition of Done Checklist

- [ ] T010: Filter controls frame added and working
- [ ] T011: Scrollable cards container displays EventCard widgets
- [ ] T012: _rebuild_event_cards() populates cards correctly
- [ ] T013: Filter changes trigger card rebuild
- [ ] T014: Quick action buttons open correct dialogs
- [ ] T015: Empty states show appropriate messages
- [ ] T016: Create Event button in header works
- [ ] All filters work: Active & Future, Past, All, date range

---

## Review Guidance

**Key Checkpoints**:
1. Dashboard shows multiple events correctly
2. Filter dropdown changes visible events immediately
3. Date range filtering works with valid dates, shows warning for invalid
4. Quick actions pre-select the correct event in dialogs
5. Empty states are helpful and include Create Event where appropriate
6. Existing functionality (history tables) still works

---

## Activity Log

- 2025-12-12T00:00:00Z – system – lane=planned – Prompt created.
- 2025-12-12T20:50:22Z – claude – shell_pid=60768 – lane=doing – Started implementation
