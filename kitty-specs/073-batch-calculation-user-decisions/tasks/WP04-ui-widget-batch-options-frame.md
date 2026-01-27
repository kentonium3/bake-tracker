---
work_package_id: WP04
title: UI Widget - BatchOptionsFrame
lane: "done"
dependencies:
- WP02
base_branch: 073-batch-calculation-user-decisions-WP02
base_commit: b677bf1dc01b0d67138f79ac23cea9e677de0c60
created_at: '2026-01-27T19:45:35.264547+00:00'
subtasks:
- T022
- T023
- T024
- T025
- T026
- T027
- T028
- T029
phase: Phase 2 - UI Layer
assignee: ''
agent: "claude"
shell_pid: "24108"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-27T18:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – UI Widget - BatchOptionsFrame

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

This WP depends on WP02 (BatchOptionsResult dataclass).

```bash
spec-kitty implement WP04
```

---

## Objectives & Success Criteria

**Primary Objective**: Create the UI widget for displaying and selecting batch options with clear visual indicators for shortfalls and exact matches.

**Success Criteria**:
1. Widget displays all FUs with their batch options
2. Radio buttons allow single selection per FU
3. Shortfall options have visual warning indicator (red text/icon)
4. Exact match options have visual highlight (green text/checkmark)
5. Selection change triggers callback to parent
6. `get_selections()` returns current user choices

---

## Context & Constraints

**Why this is needed**: Users need a clear, intuitive interface to see their batch options and make selections with full awareness of trade-offs.

**Key Documents**:
- `src/ui/forms/finished_good_form.py:182-209` - Radio button pattern
- `kitty-specs/073-batch-calculation-user-decisions/quickstart.md` - Widget code example
- `kitty-specs/073-batch-calculation-user-decisions/data-model.md` - BatchOptionsResult structure

**Constraints**:
- Use CTkRadioButton pattern from existing codebase
- Follow existing UI styling conventions
- Widget must be embeddable in planning_tab.py

---

## Subtasks & Detailed Guidance

### Subtask T022 – Create batch_options_frame.py module

**Purpose**: Set up the new widget file with imports.

**Steps**:
1. Create `src/ui/widgets/batch_options_frame.py`
2. Add imports:

```python
"""Widget for displaying and selecting batch options."""
from typing import Callable, Dict, List, Optional
import customtkinter as ctk

from src.services.planning_service import BatchOption, BatchOptionsResult


# Visual styling constants
SHORTFALL_COLOR = "#FF6B6B"  # Red for shortfall warning
EXACT_MATCH_COLOR = "#4CAF50"  # Green for exact match
SURPLUS_COLOR = "#888888"  # Gray for surplus (neutral)
```

**Files**: `src/ui/widgets/batch_options_frame.py` (NEW)
**Parallel?**: No - must be first

---

### Subtask T023 – Implement BatchOptionsFrame class structure

**Purpose**: Define the widget class with constructor.

**Steps**:
1. Add the class definition:

```python
class BatchOptionsFrame(ctk.CTkScrollableFrame):
    """
    Widget for displaying and selecting batch options.

    Displays batch options for each FinishedUnit with radio button selection.
    Shows shortfall warnings and exact match highlights.
    """

    def __init__(
        self,
        parent,
        on_selection_change: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ):
        """
        Initialize BatchOptionsFrame.

        Args:
            parent: Parent widget
            on_selection_change: Callback when user selects an option.
                                 Called with (finished_unit_id, batches)
            **kwargs: Additional arguments passed to CTkScrollableFrame
        """
        super().__init__(parent, **kwargs)

        self._selection_callback = on_selection_change
        self._option_vars: Dict[int, ctk.StringVar] = {}  # fu_id -> StringVar
        self._options_data: Dict[int, List[BatchOption]] = {}  # fu_id -> options
        self._fu_frames: Dict[int, ctk.CTkFrame] = {}  # fu_id -> frame

        # Configure grid
        self.columnconfigure(0, weight=1)
```

**Files**: `src/ui/widgets/batch_options_frame.py`
**Parallel?**: No - depends on T022

---

### Subtask T024 – Implement populate() method

**Purpose**: Populate the widget with batch options for all FUs.

**Steps**:
1. Add the method:

```python
def populate(self, options_results: List[BatchOptionsResult]) -> None:
    """
    Display batch options for all FUs.

    Args:
        options_results: List of BatchOptionsResult from calculate_batch_options()
    """
    # Clear existing content
    self.clear()

    # Create section for each FU
    for idx, result in enumerate(options_results):
        self._create_fu_section(result, idx)

def clear(self) -> None:
    """Clear all displayed options."""
    for widget in self.winfo_children():
        widget.destroy()
    self._option_vars.clear()
    self._options_data.clear()
    self._fu_frames.clear()
```

**Files**: `src/ui/widgets/batch_options_frame.py`
**Parallel?**: No - core method

---

### Subtask T025 – Implement _create_fu_section()

**Purpose**: Create the display section for one FinishedUnit.

**Steps**:
1. Add the method:

```python
def _create_fu_section(self, result: BatchOptionsResult, row: int) -> None:
    """
    Create section for one FU with header and radio options.

    Args:
        result: BatchOptionsResult for this FU
        row: Grid row index
    """
    # Frame for this FU
    fu_frame = ctk.CTkFrame(self)
    fu_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
    fu_frame.columnconfigure(0, weight=1)
    self._fu_frames[result.finished_unit_id] = fu_frame

    # Header: FU name + quantity needed
    header_text = f"{result.finished_unit_name}"
    header = ctk.CTkLabel(
        fu_frame,
        text=header_text,
        font=ctk.CTkFont(weight="bold", size=14),
        anchor="w",
    )
    header.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))

    # Subheader: quantity and yield info
    subheader_text = (
        f"Need {result.quantity_needed} {result.item_unit} "
        f"({result.yield_per_batch} per batch)"
    )
    subheader = ctk.CTkLabel(
        fu_frame,
        text=subheader_text,
        font=ctk.CTkFont(size=12),
        text_color="#888888",
        anchor="w",
    )
    subheader.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 5))

    # Store data for this FU
    self._options_data[result.finished_unit_id] = result.options

    # Radio buttons for options
    var = ctk.StringVar(value="")
    self._option_vars[result.finished_unit_id] = var

    for opt_idx, option in enumerate(result.options):
        self._create_option_radio(
            fu_frame,
            result.finished_unit_id,
            option,
            var,
            result.item_unit,
            opt_idx + 2,  # Start at row 2 (after header and subheader)
        )
```

**Files**: `src/ui/widgets/batch_options_frame.py`
**Parallel?**: Yes (can develop alongside T026-T028)

---

### Subtask T026 – Implement radio button selection with shortfall indicator

**Purpose**: Create radio buttons with visual shortfall warnings.

**Steps**:
1. Add the method:

```python
def _create_option_radio(
    self,
    parent: ctk.CTkFrame,
    fu_id: int,
    option: BatchOption,
    var: ctk.StringVar,
    item_unit: str,
    row: int,
) -> None:
    """
    Create a radio button for one batch option.

    Args:
        parent: Parent frame
        fu_id: FinishedUnit ID for callback
        option: BatchOption to display
        var: StringVar for radio group
        item_unit: Unit name for display (e.g., "cookie")
        row: Grid row
    """
    # Format option text
    text = self._format_option_text(option, item_unit)

    # Determine text color based on option type
    if option.is_shortfall:
        text_color = SHORTFALL_COLOR
    elif option.is_exact_match:
        text_color = EXACT_MATCH_COLOR
    else:
        text_color = SURPLUS_COLOR

    # Create radio button
    radio = ctk.CTkRadioButton(
        parent,
        text=text,
        variable=var,
        value=str(option.batches),
        command=lambda: self._on_option_selected(fu_id),
        text_color=text_color,
    )
    radio.grid(row=row, column=0, sticky="w", padx=20, pady=2)
```

**Files**: `src/ui/widgets/batch_options_frame.py`
**Parallel?**: Yes (with T025, T027, T028)

---

### Subtask T027 – Implement exact match highlighting

**Purpose**: Visually distinguish exact match options.

**Steps**:
1. The exact match highlighting is handled in T026 via text color
2. Optionally add a checkmark or icon:

```python
def _create_option_radio(
    self,
    parent: ctk.CTkFrame,
    fu_id: int,
    option: BatchOption,
    var: ctk.StringVar,
    item_unit: str,
    row: int,
) -> None:
    """..."""
    # ... (existing code from T026)

    # Add indicator icon if needed
    if option.is_exact_match:
        indicator = ctk.CTkLabel(
            parent,
            text="✓",
            text_color=EXACT_MATCH_COLOR,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        indicator.grid(row=row, column=1, sticky="w", padx=5)
    elif option.is_shortfall:
        indicator = ctk.CTkLabel(
            parent,
            text="⚠",
            text_color=SHORTFALL_COLOR,
            font=ctk.CTkFont(size=14),
        )
        indicator.grid(row=row, column=1, sticky="w", padx=5)
```

**Files**: `src/ui/widgets/batch_options_frame.py`
**Parallel?**: Yes (with T025, T026, T028)

---

### Subtask T028 – Implement _format_option_text()

**Purpose**: Format batch option for display.

**Steps**:
1. Add the method:

```python
def _format_option_text(self, option: BatchOption, item_unit: str) -> str:
    """
    Format option for display in radio button.

    Args:
        option: BatchOption to format
        item_unit: Unit name (e.g., "cookie", "cake")

    Returns:
        Formatted string like "3 batches = 72 cookies (+22 extra)"
    """
    # Pluralize unit if needed
    unit = item_unit if option.total_yield == 1 else f"{item_unit}s"

    # Base text
    base = f"{option.batches} batch{'es' if option.batches != 1 else ''} = {option.total_yield} {unit}"

    # Difference text
    if option.is_exact_match:
        diff_text = "(exact match)"
    elif option.is_shortfall:
        diff_text = f"({abs(option.difference)} short - SHORTFALL)"
    else:
        diff_text = f"(+{option.difference} extra)"

    return f"{base} {diff_text}"
```

**Files**: `src/ui/widgets/batch_options_frame.py`
**Parallel?**: Yes (with T025-T027)

---

### Subtask T029 – Add selection callback and get_selections()

**Purpose**: Wire up selection change events and provide method to get current selections.

**Steps**:
1. Add callback method:

```python
def _on_option_selected(self, fu_id: int) -> None:
    """
    Handle option selection change.

    Args:
        fu_id: FinishedUnit ID that was changed
    """
    if self._selection_callback is None:
        return

    var = self._option_vars.get(fu_id)
    if var is None:
        return

    value = var.get()
    if value:
        batches = int(value)
        self._selection_callback(fu_id, batches)
```

2. Add get_selections method:

```python
def get_selections(self) -> Dict[int, int]:
    """
    Get current user selections.

    Returns:
        Dict mapping finished_unit_id -> selected batches.
        Only includes FUs where user has made a selection.
    """
    selections = {}
    for fu_id, var in self._option_vars.items():
        value = var.get()
        if value:
            selections[fu_id] = int(value)
    return selections

def get_selection_with_shortfall_info(self) -> List[Dict]:
    """
    Get selections with shortfall information for validation.

    Returns:
        List of dicts with keys: finished_unit_id, batches, is_shortfall
    """
    results = []
    for fu_id, var in self._option_vars.items():
        value = var.get()
        if value:
            batches = int(value)
            options = self._options_data.get(fu_id, [])
            # Find the selected option to check shortfall
            is_shortfall = False
            for opt in options:
                if opt.batches == batches:
                    is_shortfall = opt.is_shortfall
                    break
            results.append({
                "finished_unit_id": fu_id,
                "batches": batches,
                "is_shortfall": is_shortfall,
            })
    return results
```

3. Add method to set selections (for loading existing decisions):

```python
def set_selection(self, fu_id: int, batches: int) -> None:
    """
    Set the selection for a FinishedUnit.

    Used when loading existing batch decisions.

    Args:
        fu_id: FinishedUnit ID
        batches: Number of batches to select
    """
    var = self._option_vars.get(fu_id)
    if var is not None:
        var.set(str(batches))
```

**Files**: `src/ui/widgets/batch_options_frame.py`
**Parallel?**: No - integrates other subtasks

---

## Test Strategy

**Manual Testing** (UI widgets are typically tested manually):
1. Create test window with BatchOptionsFrame
2. Populate with sample BatchOptionsResult data
3. Verify:
   - All FUs display with headers
   - Radio buttons work (single selection per FU)
   - Shortfall options show red text
   - Exact match options show green text
   - Selection callback fires on change
   - get_selections() returns correct data

**Test Script** (optional, for quick validation):

```python
# Quick manual test script
if __name__ == "__main__":
    import customtkinter as ctk
    from src.services.planning_service import BatchOption, BatchOptionsResult

    # Sample data
    test_results = [
        BatchOptionsResult(
            finished_unit_id=1,
            finished_unit_name="Sugar Cookies",
            recipe_id=1,
            recipe_name="Sugar Cookie Recipe",
            quantity_needed=50,
            yield_per_batch=24,
            yield_mode="discrete_count",
            item_unit="cookie",
            options=[
                BatchOption(batches=2, total_yield=48, quantity_needed=50,
                           difference=-2, is_shortfall=True, is_exact_match=False,
                           yield_per_batch=24),
                BatchOption(batches=3, total_yield=72, quantity_needed=50,
                           difference=22, is_shortfall=False, is_exact_match=False,
                           yield_per_batch=24),
            ],
        ),
        BatchOptionsResult(
            finished_unit_id=2,
            finished_unit_name="Chocolate Cake",
            recipe_id=2,
            recipe_name="Chocolate Cake Recipe",
            quantity_needed=3,
            yield_per_batch=1,
            yield_mode="batch_portion",
            item_unit="cake",
            options=[
                BatchOption(batches=3, total_yield=3, quantity_needed=3,
                           difference=0, is_shortfall=False, is_exact_match=True,
                           yield_per_batch=1),
            ],
        ),
    ]

    def on_change(fu_id, batches):
        print(f"Selection changed: FU {fu_id} = {batches} batches")

    root = ctk.CTk()
    root.geometry("500x400")
    root.title("BatchOptionsFrame Test")

    frame = BatchOptionsFrame(root, on_selection_change=on_change)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    frame.populate(test_results)

    root.mainloop()
```

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| UI styling inconsistent | Medium | Use existing CTk patterns from codebase |
| Performance with many FUs | Low | Use scrollable frame; lazy loading if >50 FUs |
| Color accessibility | Medium | Use distinct colors + text indicators |

---

## Definition of Done Checklist

- [ ] batch_options_frame.py created
- [ ] BatchOptionsFrame class implemented
- [ ] populate() displays all FUs
- [ ] _create_fu_section() creates headers and options
- [ ] Radio button selection works
- [ ] Shortfall indicator (red) implemented
- [ ] Exact match highlight (green) implemented
- [ ] _format_option_text() formats correctly
- [ ] Selection callback fires on change
- [ ] get_selections() returns current choices
- [ ] set_selection() allows pre-selecting
- [ ] Manual testing completed

---

## Review Guidance

**Key Checkpoints**:
1. **Visual clarity**: Shortfall and exact match are clearly distinguishable
2. **Usability**: Selection is intuitive and responsive
3. **Integration**: Widget can be embedded in planning_tab.py
4. **State management**: Selections tracked correctly

**Questions for Review**:
- Are the color choices accessible?
- Is the text formatting clear and informative?
- Does the widget handle edge cases (no options, many FUs)?

---

## Activity Log

- 2026-01-27T18:00:00Z – system – lane=planned – Prompt created.
- 2026-01-27T19:47:18Z – claude – shell_pid=23225 – lane=for_review – All 8 subtasks complete (T022-T029), BatchOptionsFrame widget with shortfall/exact match indicators, selection callback, get_selections methods
- 2026-01-27T19:47:23Z – claude – shell_pid=24108 – lane=doing – Started review via workflow command
- 2026-01-27T19:47:41Z – claude – shell_pid=24108 – lane=done – Review passed: BatchOptionsFrame widget complete with all 8 subtasks (T022-T029), visual indicators for shortfall/exact match, radio selection, callback support, get_selections and set_selection methods
