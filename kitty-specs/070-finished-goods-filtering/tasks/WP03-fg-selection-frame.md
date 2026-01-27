---
work_package_id: WP03
title: FG Selection Frame UI Component
lane: "done"
dependencies:
- WP01
base_branch: 070-finished-goods-filtering-WP02
base_commit: 687d77aee3d684bc4073df548f9db8093524f42c
created_at: '2026-01-27T01:28:53.309541+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - UI Layer
assignee: ''
agent: "claude"
shell_pid: "31999"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-26T19:45:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – FG Selection Frame UI Component

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

**Depends on WP02** – Use `--base` flag:

```bash
spec-kitty implement WP03 --base WP02 --agent gemini
```

---

## Objectives & Success Criteria

**Objective**: Create `FGSelectionFrame` UI component for selecting finished goods from the filtered available list.

**Success Criteria**:
- [ ] `FGSelectionFrame(CTkFrame)` class created with proper structure
- [ ] `populate_finished_goods()` displays FG list with checkboxes
- [ ] Checkboxes allow independent selection of each FG
- [ ] Live count displays "X of Y selected"
- [ ] Save/Cancel buttons trigger callbacks
- [ ] All UI tests pass

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/070-finished-goods-filtering/spec.md` (FR-004, FR-005)
- Plan: `kitty-specs/070-finished-goods-filtering/plan.md` (WP03 section)
- Constitution: `.kittify/memory/constitution.md` (Principle V: Layered Architecture)

**Pattern to Follow**: `src/ui/components/recipe_selection_frame.py` (F069)

**Dependencies**:
- WP01 + WP02: Service layer methods for filtering (complete)
- This component is consumed by WP04 (Planning Tab Integration)

**UI Framework**: CustomTkinter (CTk)

**File Boundaries**:
- **Gemini (this WP)**: `src/ui/components/fg_selection_frame.py`, `src/tests/test_fg_selection_frame.py`
- Do NOT modify: `planning_tab.py` (WP04/Codex), `event_service.py` (WP01-02/Claude)

---

## Subtasks & Detailed Guidance

### Subtask T013 – Create FGSelectionFrame Class Structure

**Purpose**: Establish the component class with proper initialization and layout.

**Steps**:
1. Read `src/ui/components/recipe_selection_frame.py` for reference pattern
2. Create `src/ui/components/fg_selection_frame.py`:

```python
"""
FGSelectionFrame - UI component for selecting finished goods.

Part of F070: Finished Goods Filtering for Event Planning.
"""

import customtkinter as ctk
from typing import List, Callable, Optional, Dict
from src.models.finished_good import FinishedGood
from src.ui.constants import PADDING_SMALL, PADDING_MEDIUM, PADDING_LARGE


class FGSelectionFrame(ctk.CTkFrame):
    """
    Frame for selecting finished goods from available list.

    Displays checkboxes for each available FG with live count and Save/Cancel buttons.
    """

    def __init__(
        self,
        master,
        on_save: Callable[[List[int]], None],
        on_cancel: Callable[[], None],
        **kwargs,
    ):
        """
        Initialize FG selection frame.

        Args:
            master: Parent widget
            on_save: Callback when Save clicked, receives list of selected FG IDs
            on_cancel: Callback when Cancel clicked
        """
        super().__init__(master, **kwargs)

        self._on_save = on_save
        self._on_cancel = on_cancel

        # Track checkboxes and their variables
        self._checkbox_vars: Dict[int, ctk.IntVar] = {}  # fg_id -> IntVar
        self._checkboxes: Dict[int, ctk.CTkCheckBox] = {}  # fg_id -> checkbox widget
        self._fg_data: Dict[int, FinishedGood] = {}  # fg_id -> FG object

        # Event name for header
        self._event_name: str = ""

        # Build UI
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Header label
        self._header_label = ctk.CTkLabel(
            self,
            text="Select Finished Goods",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self._header_label.grid(
            row=0, column=0, sticky="w",
            padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, PADDING_SMALL)
        )

        # Scrollable frame for checkboxes
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            height=200,
        )
        self._scroll_frame.grid(
            row=1, column=0, sticky="nsew",
            padx=PADDING_MEDIUM, pady=PADDING_SMALL
        )
        self._scroll_frame.grid_columnconfigure(0, weight=1)

        # Count label
        self._count_label = ctk.CTkLabel(
            self,
            text="0 of 0 selected",
        )
        self._count_label.grid(
            row=2, column=0, sticky="w",
            padx=PADDING_MEDIUM, pady=PADDING_SMALL
        )

        # Button frame
        self._button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._button_frame.grid(
            row=3, column=0, sticky="e",
            padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

        self._cancel_button = ctk.CTkButton(
            self._button_frame,
            text="Cancel",
            width=80,
            command=self._handle_cancel,
        )
        self._cancel_button.pack(side="left", padx=(0, PADDING_SMALL))

        self._save_button = ctk.CTkButton(
            self._button_frame,
            text="Save",
            width=80,
            command=self._handle_save,
        )
        self._save_button.pack(side="left")
```

3. Update `src/ui/components/__init__.py` to export:
```python
from .fg_selection_frame import FGSelectionFrame
```

**Files**: `src/ui/components/fg_selection_frame.py` (NEW), `src/ui/components/__init__.py`
**Parallel?**: Yes (structure can start immediately)
**Notes**:
- Follow same initialization pattern as `RecipeSelectionFrame`
- Use `CTkScrollableFrame` for FG list (handles large catalogs)
- Store checkbox vars by fg_id for easy lookup

---

### Subtask T014 – Implement populate_finished_goods()

**Purpose**: Method to populate the frame with available FGs.

**Steps**:
1. Add method to `FGSelectionFrame` class:

```python
def populate_finished_goods(
    self,
    finished_goods: List[FinishedGood],
    event_name: str = "",
) -> None:
    """
    Populate the frame with finished goods.

    Args:
        finished_goods: List of available FinishedGood objects to display
        event_name: Name of the event (for header display)
    """
    self._event_name = event_name

    # Update header
    if event_name:
        self._header_label.configure(text=f"Finished Goods for {event_name}")
    else:
        self._header_label.configure(text="Select Finished Goods")

    # Clear existing checkboxes
    for widget in self._scroll_frame.winfo_children():
        widget.destroy()
    self._checkbox_vars.clear()
    self._checkboxes.clear()
    self._fg_data.clear()

    # Create checkboxes for each FG
    for i, fg in enumerate(finished_goods):
        var = ctk.IntVar(value=0)
        self._checkbox_vars[fg.id] = var
        self._fg_data[fg.id] = fg

        checkbox = ctk.CTkCheckBox(
            self._scroll_frame,
            text=fg.display_name,
            variable=var,
            command=self._update_count,
        )
        checkbox.grid(
            row=i, column=0, sticky="w",
            padx=PADDING_SMALL, pady=2
        )
        self._checkboxes[fg.id] = checkbox

    # Update count display
    self._update_count()
```

**Files**: `src/ui/components/fg_selection_frame.py`
**Parallel?**: No (depends on T013)
**Notes**:
- Clears existing checkboxes before populating (supports re-population)
- Stores FG objects for later reference (e.g., getting names)
- Calls `_update_count()` to initialize count display

---

### Subtask T015 – Implement Checkbox Rendering

**Purpose**: Ensure checkboxes display FG names and support selection.

**Steps**:
1. Already implemented in T014 (checkbox creation)
2. Add helper methods for selection management:

```python
def set_selected(self, fg_ids: List[int]) -> None:
    """
    Set which FGs are selected.

    Args:
        fg_ids: List of FG IDs to mark as selected
    """
    selected_set = set(fg_ids)
    for fg_id, var in self._checkbox_vars.items():
        var.set(1 if fg_id in selected_set else 0)
    self._update_count()

def get_selected(self) -> List[int]:
    """
    Get list of selected FG IDs.

    Returns:
        List of FG IDs that are currently checked
    """
    return [
        fg_id
        for fg_id, var in self._checkbox_vars.items()
        if var.get() == 1
    ]
```

**Files**: `src/ui/components/fg_selection_frame.py`
**Parallel?**: No (depends on T014)
**Notes**:
- `set_selected()` used when loading existing selections
- `get_selected()` used when saving

---

### Subtask T016 – Implement Live Count Display

**Purpose**: Show "X of Y selected" that updates as user clicks checkboxes.

**Steps**:
1. Add `_update_count()` method:

```python
def _update_count(self) -> None:
    """Update the count label with current selection."""
    selected_count = sum(1 for var in self._checkbox_vars.values() if var.get() == 1)
    total_count = len(self._checkbox_vars)
    self._count_label.configure(text=f"{selected_count} of {total_count} selected")
```

**Files**: `src/ui/components/fg_selection_frame.py`
**Parallel?**: No (depends on T014)
**Notes**:
- Called from checkbox command (automatic update on click)
- Called from `set_selected()` and `populate_finished_goods()`

---

### Subtask T017 – Implement Save/Cancel Buttons

**Purpose**: Handle Save and Cancel button clicks with callbacks.

**Steps**:
1. Add handler methods:

```python
def _handle_save(self) -> None:
    """Handle Save button click."""
    selected_ids = self.get_selected()
    self._on_save(selected_ids)

def _handle_cancel(self) -> None:
    """Handle Cancel button click."""
    self._on_cancel()
```

**Files**: `src/ui/components/fg_selection_frame.py`
**Parallel?**: No (depends on T013)
**Notes**:
- Save passes selected FG IDs to callback
- Cancel just triggers callback (caller decides what to do)

---

### Subtask T018 – Write UI Tests

**Purpose**: Tests for FGSelectionFrame component.

**Steps**:
1. Create `src/tests/test_fg_selection_frame.py`:

```python
"""
Tests for FGSelectionFrame UI component (F070).
"""

import pytest
from unittest.mock import MagicMock, patch
from src.ui.components.fg_selection_frame import FGSelectionFrame


class TestFGSelectionFrameInit:
    """Tests for FGSelectionFrame initialization."""

    def test_creates_with_callbacks(self, mock_ctk_root):
        """Frame initializes with save and cancel callbacks."""
        on_save = MagicMock()
        on_cancel = MagicMock()

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=on_save,
            on_cancel=on_cancel,
        )

        assert frame._on_save is on_save
        assert frame._on_cancel is on_cancel

    def test_has_required_widgets(self, mock_ctk_root):
        """Frame contains all required UI elements."""
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )

        assert frame._header_label is not None
        assert frame._scroll_frame is not None
        assert frame._count_label is not None
        assert frame._save_button is not None
        assert frame._cancel_button is not None


class TestPopulateFinishedGoods:
    """Tests for populate_finished_goods method."""

    def test_displays_fg_names(self, mock_ctk_root, mock_fgs):
        """Populates checkboxes with FG display names."""
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )

        frame.populate_finished_goods(mock_fgs, "Test Event")

        assert len(frame._checkbox_vars) == len(mock_fgs)
        for fg in mock_fgs:
            assert fg.id in frame._checkbox_vars

    def test_updates_header_with_event_name(self, mock_ctk_root, mock_fgs):
        """Updates header label with event name."""
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )

        frame.populate_finished_goods(mock_fgs, "Holiday Event")

        # Header should include event name
        header_text = frame._header_label.cget("text")
        assert "Holiday Event" in header_text

    def test_clears_previous_checkboxes(self, mock_ctk_root, mock_fgs):
        """Clears existing checkboxes when repopulated."""
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )

        # Populate twice with different data
        frame.populate_finished_goods(mock_fgs[:2], "Event 1")
        first_count = len(frame._checkbox_vars)

        frame.populate_finished_goods(mock_fgs, "Event 2")
        second_count = len(frame._checkbox_vars)

        assert first_count == 2
        assert second_count == len(mock_fgs)


class TestSelection:
    """Tests for selection methods."""

    def test_set_selected_checks_specified_fgs(self, mock_ctk_root, mock_fgs):
        """set_selected checks only specified FG IDs."""
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        # Select first two
        frame.set_selected([mock_fgs[0].id, mock_fgs[1].id])

        selected = frame.get_selected()
        assert mock_fgs[0].id in selected
        assert mock_fgs[1].id in selected
        assert mock_fgs[2].id not in selected

    def test_get_selected_returns_checked_fg_ids(self, mock_ctk_root, mock_fgs):
        """get_selected returns IDs of checked FGs."""
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        # Manually set checkbox values
        frame._checkbox_vars[mock_fgs[0].id].set(1)
        frame._checkbox_vars[mock_fgs[2].id].set(1)

        selected = frame.get_selected()
        assert set(selected) == {mock_fgs[0].id, mock_fgs[2].id}


class TestCountDisplay:
    """Tests for count display."""

    def test_count_updates_on_selection(self, mock_ctk_root, mock_fgs):
        """Count label updates when selection changes."""
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        # Initial count
        assert "0 of" in frame._count_label.cget("text")

        # Select one
        frame.set_selected([mock_fgs[0].id])
        assert "1 of" in frame._count_label.cget("text")


class TestCallbacks:
    """Tests for button callbacks."""

    def test_save_calls_callback_with_selected_ids(self, mock_ctk_root, mock_fgs):
        """Save button calls on_save with selected FG IDs."""
        on_save = MagicMock()
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=on_save,
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)
        frame.set_selected([mock_fgs[0].id])

        frame._handle_save()

        on_save.assert_called_once_with([mock_fgs[0].id])

    def test_cancel_calls_callback(self, mock_ctk_root, mock_fgs):
        """Cancel button calls on_cancel."""
        on_cancel = MagicMock()
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=on_cancel,
        )

        frame._handle_cancel()

        on_cancel.assert_called_once()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_ctk_root():
    """Create a mock CTk root for testing."""
    with patch("customtkinter.CTk") as mock_ctk:
        root = MagicMock()
        mock_ctk.return_value = root
        yield root


@pytest.fixture
def mock_fgs():
    """Create mock FinishedGood objects for testing."""
    fgs = []
    for i in range(3):
        fg = MagicMock()
        fg.id = i + 1
        fg.display_name = f"Test FG {i + 1}"
        fgs.append(fg)
    return fgs
```

**Files**: `src/tests/test_fg_selection_frame.py` (NEW)
**Parallel?**: Yes (can write alongside T013-T17)
**Notes**:
- Uses MagicMock for CTk root (avoids GUI in tests)
- Tests component logic, not visual rendering
- Pattern follows `test_recipe_selection_frame.py`

---

## Test Strategy

**Run tests**:
```bash
./run-tests.sh src/tests/test_fg_selection_frame.py -v
```

**Expected results**: ~13 tests pass

**Manual validation** (after WP04 integration):
1. Launch app, go to Planning Tab
2. Select an event
3. Select some recipes
4. Verify FG selection frame appears with available FGs
5. Check/uncheck FGs, verify count updates
6. Click Save, verify selections persist
7. Click Cancel, verify selections revert

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large FG catalog performance | Use CTkScrollableFrame (virtualized) |
| Checkbox state not updating | Bind IntVar to checkbox, call `_update_count()` |
| Memory leaks on repopulate | Clear all widgets and dicts in `populate_finished_goods()` |

---

## Definition of Done Checklist

- [ ] T013: Class structure created with widgets
- [ ] T014: `populate_finished_goods()` implemented
- [ ] T015: `set_selected()` and `get_selected()` implemented
- [ ] T016: `_update_count()` implemented, count updates live
- [ ] T017: Save/Cancel handlers call callbacks
- [ ] T018: All 13 UI tests pass
- [ ] Component exported from `__init__.py`
- [ ] No imports from `event_service.py` (UI doesn't call service directly)

---

## Review Guidance

**Key acceptance checkpoints**:
1. Verify component follows `RecipeSelectionFrame` pattern
2. Verify no service imports in UI component (layered architecture)
3. Verify `populate_finished_goods()` clears old state
4. Verify callbacks pass correct data types
5. Run tests with `./run-tests.sh src/tests/test_fg_selection_frame.py -v`

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Initial entry**:
- 2026-01-26T19:45:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-27T01:31:44Z – unknown – shell_pid=31081 – lane=for_review – Ready for review: FGSelectionFrame UI component with 14 passing tests
- 2026-01-27T01:32:32Z – claude – shell_pid=31999 – lane=doing – Started review via workflow command
- 2026-01-27T01:33:17Z – claude – shell_pid=31999 – lane=done – Review passed: Follows RecipeSelectionFrame pattern. No service imports (layered arch). Clears old state on repopulate. All 14 tests pass. Properly exported.
