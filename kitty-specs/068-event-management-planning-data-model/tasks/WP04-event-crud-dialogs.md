---
work_package_id: WP04
title: Event CRUD Dialogs
lane: "doing"
dependencies: [WP02]
base_branch: 068-event-management-planning-data-model-WP02
base_commit: 73589fea0d3b81e174fd1e517a791c76bcf877d1
created_at: '2026-01-26T21:36:39.742396+00:00'
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
phase: Phase 2 - UI Layer
assignee: ''
agent: ''
shell_pid: "98418"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-26T19:16:03Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Event CRUD Dialogs

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
spec-kitty implement WP04 --base WP02
```

**🔀 PARALLELIZABLE**: This WP can run simultaneously with WP03 (Planning Tab UI). Both depend on WP02 but work on different files.

**Agent Assignment**: Codex (parallel worker)

---

## Objectives & Success Criteria

**Goal**: Create Create/Edit/Delete dialogs for event management.

**Success Criteria**:
- [ ] Create Event dialog opens and accepts name, date, attendees
- [ ] Edit Event dialog opens with pre-populated fields
- [ ] Delete confirmation dialog shows event name
- [ ] Name and date validation (required fields)
- [ ] Attendees validation (positive integer or empty)
- [ ] Validation feedback displays clearly
- [ ] Save triggers callback with result
- [ ] Cancel closes without changes

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/068-event-management-planning-data-model/spec.md` (User Stories 1, 3, 4)
- Plan: `kitty-specs/068-event-management-planning-data-model/plan.md` (UI patterns)
- Research: `kitty-specs/068-event-management-planning-data-model/research.md` (RQ4: Dialog patterns)

**Key Patterns to Follow**:
- Study `src/ui/forms/recipe_form.py` for dialog structure
- Use CTkToplevel for modal dialogs
- Follow existing validation patterns

**Constraints**:
- Do NOT modify Planning tab (that's WP03)
- Do NOT wire to main app (that's WP05)
- Focus ONLY on dialog components
- Use service layer for save operations

**File Boundary**: This WP owns `src/ui/forms/event_planning_form.py` ONLY

---

## Subtasks & Detailed Guidance

### Subtask T021 – Create Event Planning Form Base

**Purpose**: Establish the base dialog class with common functionality.

**Steps**:
1. Create new file `src/ui/forms/event_planning_form.py`
2. Set up the base class:

```python
"""
Event Planning Form - Create/Edit event dialogs.

Feature 068: Event Management & Planning Data Model
"""

import customtkinter as ctk
from typing import Optional, Callable, Dict, Any
from datetime import date, datetime

from src.services.event_service import EventService
from src.services.database import session_scope
from src.services.exceptions import ValidationError
from src.models import Event


class EventPlanningForm(ctk.CTkToplevel):
    """
    Base form for event creation and editing.

    Handles common form setup, validation, and save logic.
    Subclasses (or mode parameter) control Create vs Edit behavior.
    """

    def __init__(
        self,
        master: ctk.CTk,
        event: Optional[Event] = None,
        on_save: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """
        Initialize event form.

        Args:
            master: Parent window
            event: Event to edit (None for create mode)
            on_save: Callback with save result dict
            on_cancel: Callback on cancel
        """
        super().__init__(master, **kwargs)

        self.service = EventService()
        self.event = event
        self._on_save = on_save
        self._on_cancel = on_cancel

        # Determine mode
        self.is_edit_mode = event is not None

        # Configure window
        self.title("Edit Event" if self.is_edit_mode else "Create Event")
        self.geometry("450x350")
        self.resizable(False, False)

        # Make modal
        self.transient(master)
        self.grab_set()

        # Build UI
        self._create_widgets()
        self._layout_widgets()

        # Populate if editing
        if self.is_edit_mode:
            self._populate_form()

        # Focus first field
        self.name_entry.focus_set()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self) -> None:
        """Create form widgets."""
        # Form title
        title_text = "Edit Event" if self.is_edit_mode else "Create New Event"
        self.title_label = ctk.CTkLabel(
            self,
            text=title_text,
            font=ctk.CTkFont(size=18, weight="bold"),
        )

        # Name field
        self.name_label = ctk.CTkLabel(self, text="Event Name *")
        self.name_entry = ctk.CTkEntry(self, width=300, placeholder_text="e.g., Christmas 2026")

        # Date field
        self.date_label = ctk.CTkLabel(self, text="Event Date * (YYYY-MM-DD)")
        self.date_entry = ctk.CTkEntry(self, width=300, placeholder_text="2026-12-20")

        # Expected Attendees field
        self.attendees_label = ctk.CTkLabel(self, text="Expected Attendees (optional)")
        self.attendees_entry = ctk.CTkEntry(self, width=300, placeholder_text="Leave empty if unknown")

        # Notes field
        self.notes_label = ctk.CTkLabel(self, text="Notes (optional)")
        self.notes_entry = ctk.CTkTextbox(self, width=300, height=60)

        # Validation message
        self.validation_label = ctk.CTkLabel(
            self,
            text="",
            text_color="red",
            wraplength=350,
        )

        # Buttons
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.save_button = ctk.CTkButton(
            self.button_frame,
            text="Save",
            command=self._on_save_click,
            width=100,
        )
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self._on_close,
            width=100,
            fg_color="gray",
        )

    def _layout_widgets(self) -> None:
        """Position widgets in form."""
        padding = {"padx": 20, "pady": 5}

        self.title_label.pack(pady=(20, 10))

        self.name_label.pack(anchor="w", **padding)
        self.name_entry.pack(**padding)

        self.date_label.pack(anchor="w", **padding)
        self.date_entry.pack(**padding)

        self.attendees_label.pack(anchor="w", **padding)
        self.attendees_entry.pack(**padding)

        self.notes_label.pack(anchor="w", **padding)
        self.notes_entry.pack(**padding)

        self.validation_label.pack(pady=5)

        self.button_frame.pack(pady=15)
        self.save_button.pack(side="left", padx=10)
        self.cancel_button.pack(side="left", padx=10)

    def _populate_form(self) -> None:
        """Populate form with existing event data."""
        if not self.event:
            return

        self.name_entry.insert(0, self.event.name or "")

        if self.event.event_date:
            self.date_entry.insert(0, self.event.event_date.strftime("%Y-%m-%d"))

        if self.event.expected_attendees:
            self.attendees_entry.insert(0, str(self.event.expected_attendees))

        if self.event.notes:
            self.notes_entry.insert("1.0", self.event.notes)

    def _validate(self) -> Optional[str]:
        """
        Validate form input.

        Returns:
            Error message if validation fails, None if valid
        """
        # TODO: Implement in T025
        pass

    def _on_save_click(self) -> None:
        """Handle save button click."""
        # TODO: Implement in T022/T023
        pass

    def _on_close(self) -> None:
        """Handle cancel/close."""
        if self._on_cancel:
            self._on_cancel()
        self.destroy()
```

**Files**: `src/ui/forms/event_planning_form.py` (new file, ~150 lines)
**Parallel?**: No - subsequent subtasks build on this
**Validation**: Class imports and window opens without error

---

### Subtask T022 – Implement Create Event Dialog

**Purpose**: Enable creating new events from the form.

**Steps**:
1. Update `_on_save_click` for create mode:

```python
def _on_save_click(self) -> None:
    """Handle save button click."""
    # Validate
    error = self._validate()
    if error:
        self.validation_label.configure(text=error)
        return

    # Clear validation message
    self.validation_label.configure(text="")

    # Get form data
    name = self.name_entry.get().strip()
    date_str = self.date_entry.get().strip()
    attendees_str = self.attendees_entry.get().strip()
    notes = self.notes_entry.get("1.0", "end-1c").strip()

    # Parse date
    try:
        event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        self.validation_label.configure(text="Invalid date format. Use YYYY-MM-DD.")
        return

    # Parse attendees
    expected_attendees = None
    if attendees_str:
        try:
            expected_attendees = int(attendees_str)
        except ValueError:
            self.validation_label.configure(text="Expected attendees must be a number.")
            return

    # Save
    try:
        with session_scope() as session:
            if self.is_edit_mode:
                # Update existing
                result = self.service.update_planning_event(
                    session,
                    self.event.id,
                    name=name,
                    event_date=event_date,
                    expected_attendees=expected_attendees if attendees_str else 0,  # 0 clears
                    notes=notes or None,
                )
                session.commit()
                result_data = {"id": result.id, "name": result.name, "action": "updated"}
            else:
                # Create new
                result = self.service.create_planning_event(
                    session,
                    name=name,
                    event_date=event_date,
                    expected_attendees=expected_attendees,
                    notes=notes or None,
                )
                session.commit()
                result_data = {"id": result.id, "name": result.name, "action": "created"}

        # Callback and close
        if self._on_save:
            self._on_save(result_data)
        self.destroy()

    except ValidationError as e:
        self.validation_label.configure(text=str(e))
    except Exception as e:
        self.validation_label.configure(text=f"Error saving: {e}")
```

2. Add convenience factory method:

```python
@classmethod
def create_event(
    cls,
    master: ctk.CTk,
    on_save: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> "EventPlanningForm":
    """
    Factory method to create a Create Event dialog.

    Args:
        master: Parent window
        on_save: Callback with created event data
        on_cancel: Callback on cancel

    Returns:
        EventPlanningForm instance in create mode
    """
    return cls(master, event=None, on_save=on_save, on_cancel=on_cancel)
```

**Files**: `src/ui/forms/event_planning_form.py` (modify)
**Parallel?**: No - depends on T021
**Validation**: Create dialog saves new event to database

---

### Subtask T023 – Implement Edit Event Dialog

**Purpose**: Enable editing existing events from the form.

**Steps**:
1. The core save logic is already in T022 (handles both modes)
2. Add convenience factory method:

```python
@classmethod
def edit_event(
    cls,
    master: ctk.CTk,
    event: Event,
    on_save: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> "EventPlanningForm":
    """
    Factory method to create an Edit Event dialog.

    Args:
        master: Parent window
        event: Event to edit
        on_save: Callback with updated event data
        on_cancel: Callback on cancel

    Returns:
        EventPlanningForm instance in edit mode
    """
    return cls(master, event=event, on_save=on_save, on_cancel=on_cancel)
```

3. Verify pre-population works correctly (from T021's `_populate_form`)

**Files**: `src/ui/forms/event_planning_form.py` (modify)
**Parallel?**: No - depends on T022
**Validation**: Edit dialog shows existing values and updates correctly

---

### Subtask T024 – Implement Delete Confirmation Dialog

**Purpose**: Confirm before deleting an event.

**Steps**:
1. Create a separate simple dialog class:

```python
class DeleteEventDialog(ctk.CTkToplevel):
    """
    Confirmation dialog for event deletion.
    """

    def __init__(
        self,
        master: ctk.CTk,
        event: Event,
        on_confirm: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """
        Initialize delete confirmation dialog.

        Args:
            master: Parent window
            event: Event to delete
            on_confirm: Callback when delete confirmed
            on_cancel: Callback on cancel
        """
        super().__init__(master, **kwargs)

        self.service = EventService()
        self.event = event
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        # Configure window
        self.title("Delete Event")
        self.geometry("350x180")
        self.resizable(False, False)

        # Make modal
        self.transient(master)
        self.grab_set()

        # Build UI
        self._create_widgets()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Warning icon/message
        warning_label = ctk.CTkLabel(
            self,
            text="⚠️ Delete Event?",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        warning_label.pack(pady=(20, 10))

        # Event name
        name_label = ctk.CTkLabel(
            self,
            text=f'"{self.event.name}"',
            font=ctk.CTkFont(size=14),
        )
        name_label.pack(pady=5)

        # Warning text
        info_label = ctk.CTkLabel(
            self,
            text="This will also delete all associated\nrecipes, finished goods, and batch decisions.",
            text_color="gray",
        )
        info_label.pack(pady=10)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=15)

        delete_button = ctk.CTkButton(
            button_frame,
            text="Delete",
            command=self._on_delete_click,
            fg_color="darkred",
            hover_color="red",
            width=100,
        )
        delete_button.pack(side="left", padx=10)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_close,
            fg_color="gray",
            width=100,
        )
        cancel_button.pack(side="left", padx=10)

    def _on_delete_click(self) -> None:
        """Handle delete confirmation."""
        try:
            with session_scope() as session:
                self.service.delete_planning_event(session, self.event.id)
                session.commit()

            if self._on_confirm:
                self._on_confirm()
            self.destroy()

        except Exception as e:
            # Show error (could add error label, but keep simple for now)
            print(f"Error deleting event: {e}")

    def _on_close(self) -> None:
        """Handle cancel/close."""
        if self._on_cancel:
            self._on_cancel()
        self.destroy()
```

**Files**: `src/ui/forms/event_planning_form.py` (add class, ~80 lines)
**Parallel?**: No - depends on T021-T023
**Notes**:
- Shows event name being deleted
- Warns about cascade deletion of associations
- Red delete button for visual warning

---

### Subtask T025 – Add Validation Feedback

**Purpose**: Implement form validation with clear error messages.

**Steps**:
1. Implement `_validate` method in EventPlanningForm:

```python
def _validate(self) -> Optional[str]:
    """
    Validate form input.

    Returns:
        Error message if validation fails, None if valid
    """
    # Name is required
    name = self.name_entry.get().strip()
    if not name:
        return "Event name is required."

    # Date is required
    date_str = self.date_entry.get().strip()
    if not date_str:
        return "Event date is required."

    # Date format validation
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD."

    # Attendees must be positive if provided
    attendees_str = self.attendees_entry.get().strip()
    if attendees_str:
        try:
            attendees = int(attendees_str)
            if attendees <= 0:
                return "Expected attendees must be a positive number."
        except ValueError:
            return "Expected attendees must be a number."

    return None  # All valid
```

2. Update save handler to use validation (already done in T022)

3. Add visual feedback on field focus (optional enhancement):

```python
def _clear_validation_on_change(self, event=None) -> None:
    """Clear validation message when user types."""
    self.validation_label.configure(text="")

# In _create_widgets, bind to entry fields:
self.name_entry.bind("<Key>", self._clear_validation_on_change)
self.date_entry.bind("<Key>", self._clear_validation_on_change)
self.attendees_entry.bind("<Key>", self._clear_validation_on_change)
```

**Files**: `src/ui/forms/event_planning_form.py` (modify)
**Parallel?**: No - part of form completion
**Validation**:
- Empty name shows "Event name is required."
- Empty date shows "Event date is required."
- Invalid date shows format error
- Negative attendees shows positive number error

---

### Subtask T026 – Wire Dialogs to Planning Tab Action Buttons

**Purpose**: Connect dialogs to the Planning tab callbacks.

**Steps**:
1. This subtask documents HOW to wire the dialogs; actual wiring happens in WP05.
2. Add documentation/example in the file header:

```python
"""
Event Planning Form - Create/Edit event dialogs.

Feature 068: Event Management & Planning Data Model

Usage in Planning Tab:
----------------------
```python
from src.ui.forms.event_planning_form import EventPlanningForm, DeleteEventDialog

# Create event
def on_create():
    EventPlanningForm.create_event(
        master=self,
        on_save=lambda result: self._on_event_saved(result),
    )

# Edit event
def on_edit(event: Event):
    EventPlanningForm.edit_event(
        master=self,
        event=event,
        on_save=lambda result: self._on_event_saved(result),
    )

# Delete event
def on_delete(event: Event):
    DeleteEventDialog(
        master=self,
        event=event,
        on_confirm=lambda: self._on_event_deleted(),
    )
```
"""
```

3. Ensure factory methods are exported (for easy imports):

```python
__all__ = ["EventPlanningForm", "DeleteEventDialog"]
```

**Files**: `src/ui/forms/event_planning_form.py` (modify header)
**Parallel?**: No - final documentation
**Notes**: Actual wiring is in WP05; this ensures dialogs are ready

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Date picker not available | Use text entry with validation; works cross-platform |
| Modal dialog doesn't grab focus | Use transient() and grab_set() per CustomTkinter patterns |
| Session issues in dialogs | Create new session scope for each operation |

---

## Definition of Done Checklist

- [ ] EventPlanningForm class created with create/edit modes
- [ ] DeleteEventDialog class created
- [ ] Name validation (required)
- [ ] Date validation (required, format YYYY-MM-DD)
- [ ] Attendees validation (positive integer or empty)
- [ ] Validation errors display clearly in red
- [ ] Create mode saves new event
- [ ] Edit mode updates existing event
- [ ] Delete confirms before deleting
- [ ] Factory methods available for easy instantiation
- [ ] Modal dialogs (grab focus, block parent)
- [ ] Cancel closes without changes
- [ ] Save callback provides result data

---

## Review Guidance

**Reviewers should verify**:
1. Dialog follows existing form patterns (recipe_form.py)
2. Validation covers all spec requirements
3. Error messages are clear and helpful
4. Service layer used (no direct DB access)
5. Session management correct
6. Modal behavior works (focus, blocking)
7. Cancel/close doesn't save partial data
8. Factory methods simplify usage

---

## Activity Log

- 2026-01-26T19:16:03Z – system – lane=planned – Prompt created.
