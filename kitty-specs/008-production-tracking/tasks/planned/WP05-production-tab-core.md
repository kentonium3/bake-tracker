---
work_package_id: "WP05"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
title: "Production Tab UI - Core"
phase: "Phase 3 - UI Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Production Tab UI - Core

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create ProductionTab with event list showing progress
- Implement recipe production recording form
- Integrate into MainWindow navigation
- UI must be intuitive for non-technical user
- No business logic in UI layer (all logic in service layer)

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md` (Principle I: Layered Architecture, Principle IV: User-Centric Design)
- Spec: `kitty-specs/008-production-tracking/spec.md` (User Story 4 - Dashboard)

**Architecture Constraints**:
- UI layer (`src/ui/`) MUST NOT contain business logic
- All data comes from production_service functions
- Follow existing CustomTkinter patterns in other tabs

**Existing UI Patterns** (reference these):
- `src/ui/events_tab.py` - Tab structure with data table
- `src/ui/pantry_tab.py` - Forms and dialogs
- `src/ui/main_window.py` - Tab integration

---

## Subtasks & Detailed Guidance

### Subtask T019 - Create ProductionTab Frame Structure [P]

**Purpose**: Basic tab structure with layout regions.

**Steps**:
1. Create `src/ui/production_tab.py`
2. Define `ProductionTab(ctk.CTkFrame)` class
3. Create layout regions:
   - Left panel: Event list with progress
   - Right panel: Detail view (production form, package status)
4. Add refresh mechanism

```python
"""
Production Tab - Dashboard for production tracking.

Provides:
- Event list with production progress
- Recipe production recording
- Package status management
- Cost comparison display
"""

import customtkinter as ctk
from typing import Optional, Callable

from src.services import production_service


class ProductionTab(ctk.CTkFrame):
    """
    Production tracking dashboard tab.

    Displays active events with production progress and allows
    recording production and managing package status.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.selected_event_id: Optional[int] = None

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """Initialize UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # Left panel - Event list
        self.event_panel = ctk.CTkFrame(self)
        self.event_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Right panel - Detail view
        self.detail_panel = ctk.CTkFrame(self)
        self.detail_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self._setup_event_panel()
        self._setup_detail_panel()

    def _setup_event_panel(self):
        """Setup event list with progress indicators."""
        # Header
        header = ctk.CTkLabel(
            self.event_panel,
            text="Active Events",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        header.pack(pady=10)

        # Refresh button
        refresh_btn = ctk.CTkButton(
            self.event_panel,
            text="Refresh",
            command=self._load_data,
            width=100
        )
        refresh_btn.pack(pady=5)

        # Event list frame (scrollable)
        self.event_list_frame = ctk.CTkScrollableFrame(self.event_panel)
        self.event_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def _setup_detail_panel(self):
        """Setup detail view placeholder."""
        self.detail_label = ctk.CTkLabel(
            self.detail_panel,
            text="Select an event to view details",
            font=ctk.CTkFont(size=14)
        )
        self.detail_label.pack(pady=20)

    def _load_data(self):
        """Load dashboard summary data."""
        # Clear existing event cards
        for widget in self.event_list_frame.winfo_children():
            widget.destroy()

        try:
            summaries = production_service.get_dashboard_summary()

            if not summaries:
                no_data = ctk.CTkLabel(
                    self.event_list_frame,
                    text="No events with packages found"
                )
                no_data.pack(pady=20)
                return

            for summary in summaries:
                self._create_event_card(summary)

        except Exception as e:
            error_label = ctk.CTkLabel(
                self.event_list_frame,
                text=f"Error loading data: {str(e)}",
                text_color="red"
            )
            error_label.pack(pady=20)

    def _create_event_card(self, summary: dict):
        """Create a clickable event card with progress."""
        # Implementation in T020
        pass

    def _select_event(self, event_id: int):
        """Handle event selection."""
        self.selected_event_id = event_id
        self._load_event_detail(event_id)

    def _load_event_detail(self, event_id: int):
        """Load detailed view for selected event."""
        # Implementation in T020/T021
        pass

    def refresh(self):
        """Public method to refresh tab data."""
        self._load_data()
```

**Files**: `src/ui/production_tab.py` (NEW)

**Parallel?**: Yes - can develop structure independently

---

### Subtask T020 - Implement Event List with Progress [P]

**Purpose**: Display events with visual progress indicators.

**Steps**:
1. Implement `_create_event_card()` method
2. Show event name, date, progress bars
3. Make cards clickable to select event
4. Color-code by completion status

```python
def _create_event_card(self, summary: dict):
    """Create a clickable event card with progress."""
    card = ctk.CTkFrame(self.event_list_frame)
    card.pack(fill="x", pady=5, padx=5)

    # Event name and date
    name_label = ctk.CTkLabel(
        card,
        text=f"{summary['event_name']}",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    name_label.pack(anchor="w", padx=10, pady=(10, 0))

    date_label = ctk.CTkLabel(
        card,
        text=f"Date: {summary['event_date']}",
        font=ctk.CTkFont(size=12)
    )
    date_label.pack(anchor="w", padx=10)

    # Recipe progress
    recipe_text = f"Recipes: {summary['recipes_complete']}/{summary['recipes_total']}"
    recipe_label = ctk.CTkLabel(card, text=recipe_text)
    recipe_label.pack(anchor="w", padx=10)

    # Package progress
    pkg = summary
    pkg_text = f"Packages: {pkg['packages_delivered']} delivered, {pkg['packages_assembled']} assembled, {pkg['packages_pending']} pending"
    pkg_label = ctk.CTkLabel(card, text=pkg_text, font=ctk.CTkFont(size=11))
    pkg_label.pack(anchor="w", padx=10)

    # Cost summary
    actual = float(summary['actual_cost'])
    planned = float(summary['planned_cost'])
    cost_text = f"Cost: ${actual:.2f} / ${planned:.2f} planned"
    cost_label = ctk.CTkLabel(card, text=cost_text, font=ctk.CTkFont(size=11))
    cost_label.pack(anchor="w", padx=10)

    # Completion indicator
    if summary['is_complete']:
        status_label = ctk.CTkLabel(card, text="COMPLETE", text_color="green")
    else:
        status_label = ctk.CTkLabel(card, text="In Progress", text_color="orange")
    status_label.pack(anchor="w", padx=10, pady=(0, 10))

    # Make card clickable
    card.bind("<Button-1>", lambda e: self._select_event(summary['event_id']))
    for child in card.winfo_children():
        child.bind("<Button-1>", lambda e, eid=summary['event_id']: self._select_event(eid))
```

**Files**: `src/ui/production_tab.py` (ADD)

---

### Subtask T021 - Implement Recipe Production Form [P]

**Purpose**: Form to record batches produced for a recipe.

**Steps**:
1. Create production form in detail panel
2. Select recipe from dropdown
3. Enter batch count
4. Record button calls production_service.record_production()
5. Show success/error feedback

```python
def _load_event_detail(self, event_id: int):
    """Load detailed view for selected event."""
    # Clear detail panel
    for widget in self.detail_panel.winfo_children():
        widget.destroy()

    try:
        progress = production_service.get_production_progress(event_id)

        # Event header
        header = ctk.CTkLabel(
            self.detail_panel,
            text=f"Event: {progress['event_name']}",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        header.pack(pady=10)

        # Production recording form
        self._create_production_form(event_id, progress)

        # Recipe progress list
        self._create_recipe_progress_list(progress['recipes'])

    except Exception as e:
        error_label = ctk.CTkLabel(
            self.detail_panel,
            text=f"Error: {str(e)}",
            text_color="red"
        )
        error_label.pack(pady=20)


def _create_production_form(self, event_id: int, progress: dict):
    """Create form to record production."""
    form_frame = ctk.CTkFrame(self.detail_panel)
    form_frame.pack(fill="x", padx=10, pady=10)

    form_header = ctk.CTkLabel(
        form_frame,
        text="Record Production",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    form_header.pack(pady=5)

    # Recipe dropdown
    recipe_label = ctk.CTkLabel(form_frame, text="Recipe:")
    recipe_label.pack(anchor="w", padx=10)

    recipe_names = [r['recipe_name'] for r in progress['recipes']]
    recipe_ids = [r['recipe_id'] for r in progress['recipes']]

    self.recipe_var = ctk.StringVar(value=recipe_names[0] if recipe_names else "")
    self.recipe_dropdown = ctk.CTkComboBox(
        form_frame,
        values=recipe_names,
        variable=self.recipe_var,
        width=200
    )
    self.recipe_dropdown.pack(padx=10, pady=5)
    self._recipe_id_map = dict(zip(recipe_names, recipe_ids))

    # Batch count
    batch_label = ctk.CTkLabel(form_frame, text="Batches:")
    batch_label.pack(anchor="w", padx=10)

    self.batch_entry = ctk.CTkEntry(form_frame, width=100, placeholder_text="1")
    self.batch_entry.pack(padx=10, pady=5)

    # Record button
    record_btn = ctk.CTkButton(
        form_frame,
        text="Record Production",
        command=lambda: self._record_production(event_id)
    )
    record_btn.pack(pady=10)

    # Status message
    self.status_label = ctk.CTkLabel(form_frame, text="")
    self.status_label.pack(pady=5)


def _record_production(self, event_id: int):
    """Handle production recording."""
    try:
        recipe_name = self.recipe_var.get()
        recipe_id = self._recipe_id_map.get(recipe_name)

        batches_str = self.batch_entry.get()
        batches = int(batches_str) if batches_str else 1

        # Call service
        record = production_service.record_production(
            event_id=event_id,
            recipe_id=recipe_id,
            batches=batches
        )

        self.status_label.configure(
            text=f"Recorded {batches} batch(es). Cost: ${float(record.actual_cost):.2f}",
            text_color="green"
        )

        # Refresh data
        self._load_data()
        self._load_event_detail(event_id)

    except Exception as e:
        self.status_label.configure(text=f"Error: {str(e)}", text_color="red")


def _create_recipe_progress_list(self, recipes: list):
    """Display recipe progress list."""
    list_frame = ctk.CTkFrame(self.detail_panel)
    list_frame.pack(fill="both", expand=True, padx=10, pady=10)

    header = ctk.CTkLabel(
        list_frame,
        text="Recipe Progress",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    header.pack(pady=5)

    for recipe in recipes:
        row = ctk.CTkFrame(list_frame)
        row.pack(fill="x", pady=2)

        name = ctk.CTkLabel(row, text=recipe['recipe_name'], width=150)
        name.pack(side="left", padx=5)

        progress_text = f"{recipe['batches_produced']}/{recipe['batches_required']} batches"
        progress = ctk.CTkLabel(row, text=progress_text)
        progress.pack(side="left", padx=5)

        if recipe['is_complete']:
            status = ctk.CTkLabel(row, text="Done", text_color="green")
        else:
            status = ctk.CTkLabel(row, text="Pending", text_color="orange")
        status.pack(side="right", padx=5)
```

**Files**: `src/ui/production_tab.py` (ADD)

---

### Subtask T022 - Add Production Tab to MainWindow

**Purpose**: Integrate ProductionTab into main navigation.

**Steps**:
1. Open `src/ui/main_window.py`
2. Import ProductionTab
3. Add to tab creation (similar to other tabs)

```python
# In main_window.py imports
from src.ui.production_tab import ProductionTab

# In _create_tabs() or similar method
self.production_tab = ProductionTab(self.tabview.tab("Production"))
self.production_tab.pack(fill="both", expand=True)
```

**Files**: `src/ui/main_window.py` (MODIFY)

---

### Subtask T023 - Wire Up Callbacks to Service

**Purpose**: Ensure all UI actions call appropriate service functions.

**Steps**:
1. Verify _record_production calls production_service.record_production
2. Verify _load_data calls production_service.get_dashboard_summary
3. Verify _load_event_detail calls production_service.get_production_progress
4. Add error handling with user-friendly messages

**Files**: `src/ui/production_tab.py` (VERIFY)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Business logic creeping into UI | Review all data operations go through service |
| Non-intuitive for non-technical user | Keep layout simple, use clear labels |
| Performance with many events | Use lazy loading, only load detail on selection |

---

## Definition of Done Checklist

- [ ] ProductionTab displays in main window
- [ ] Event list shows all events with packages
- [ ] Event cards show progress (recipes, packages, costs)
- [ ] Production form allows recording batches
- [ ] Recording calls service and refreshes display
- [ ] Error messages are user-friendly
- [ ] No business logic in UI layer
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

- Verify no imports from services except through function calls
- Verify error handling shows friendly messages
- Test click interactions work correctly
- Verify refresh updates all displays

---

## Activity Log

- 2025-12-04T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
