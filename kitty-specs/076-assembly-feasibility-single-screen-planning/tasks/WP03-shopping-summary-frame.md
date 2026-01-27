---
work_package_id: WP03
title: Shopping Summary Frame
lane: "doing"
dependencies: [WP01]
base_branch: 076-assembly-feasibility-single-screen-planning-WP01
base_commit: db69c6834888373acd24dc42ee1d6586c57e2d97
created_at: '2026-01-27T22:06:00.989815+00:00'
subtasks:
- T011
- T012
- T013
phase: Phase 2 - UI Components
assignee: ''
agent: ''
shell_pid: "46006"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-27T15:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Shopping Summary Frame

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

## Objectives & Success Criteria

Create a compact UI widget that displays shopping list summary (purchase required vs sufficient items).

**Success Criteria**:
- [ ] Widget displays "X items to purchase" count
- [ ] Widget displays "Y items sufficient" count
- [ ] Compact layout (~60px height)
- [ ] Integrates with GapAnalysisResult from inventory_gap_service

## Context & Constraints

**Reference Documents**:
- `kitty-specs/076-assembly-feasibility-single-screen-planning/plan.md` - D3 Layout Strategy
- `src/ui/components/fg_selection_frame.py` - Similar CustomTkinter component pattern
- `src/services/inventory_gap_service.py` - GapAnalysisResult dataclass

**UI Pattern**:
- Use CustomTkinter (ctk) widgets
- Follow existing component patterns in src/ui/components/
- Keep minimal height for compact display

## Subtasks & Detailed Guidance

### Subtask T011 – Create ShoppingSummaryFrame Class

**Purpose**: Create the base widget class with layout structure.

**Steps**:
1. Create new file `src/ui/components/shopping_summary_frame.py`:

```python
"""
Shopping Summary Frame - Compact display of shopping list status.

Feature 076: Assembly Feasibility & Single-Screen Planning
"""

import customtkinter as ctk
from typing import Optional

from src.services.inventory_gap_service import GapAnalysisResult


class ShoppingSummaryFrame(ctk.CTkFrame):
    """
    Compact widget displaying shopping list summary.

    Shows count of items needing purchase vs items already sufficient.
    Designed for single-screen planning layout integration.
    """

    def __init__(
        self,
        parent,
        **kwargs,
    ):
        """
        Initialize shopping summary frame.

        Args:
            parent: Parent widget
        """
        super().__init__(parent, **kwargs)

        # State
        self._purchase_count: int = 0
        self._sufficient_count: int = 0

        # Build UI
        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self) -> None:
        """Create internal widgets."""
        # Section label
        self._label = ctk.CTkLabel(
            self,
            text="Shopping List",
            font=ctk.CTkFont(weight="bold", size=14),
            anchor="w",
        )

        # Purchase count label
        self._purchase_label = ctk.CTkLabel(
            self,
            text="0 items to purchase",
            text_color="orange",
            anchor="w",
        )

        # Sufficient count label
        self._sufficient_label = ctk.CTkLabel(
            self,
            text="0 items sufficient",
            text_color="green",
            anchor="w",
        )

    def _layout_widgets(self) -> None:
        """Position widgets using grid layout."""
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self._label.grid(row=0, column=0, padx=(10, 20), pady=10, sticky="w")
        self._purchase_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        self._sufficient_label.grid(row=0, column=2, padx=10, pady=10, sticky="w")
```

**Files**: `src/ui/components/shopping_summary_frame.py` (new)

**Validation**:
- [ ] File created with proper imports
- [ ] Class inherits from ctk.CTkFrame
- [ ] Widgets created and laid out

---

### Subtask T012 – Add update_summary Method

**Purpose**: Add method to update the display based on GapAnalysisResult.

**Steps**:
1. Add the update method to ShoppingSummaryFrame:

```python
    def update_summary(self, gap_result: Optional[GapAnalysisResult]) -> None:
        """
        Update the summary display with gap analysis results.

        Args:
            gap_result: Result from analyze_inventory_gaps(), or None to clear
        """
        if gap_result is None:
            self._purchase_count = 0
            self._sufficient_count = 0
        else:
            self._purchase_count = len(gap_result.purchase_items)
            self._sufficient_count = len(gap_result.sufficient_items)

        self._update_display()

    def _update_display(self) -> None:
        """Update label text based on current counts."""
        # Purchase label
        if self._purchase_count == 0:
            self._purchase_label.configure(
                text="No purchases needed",
                text_color="green",
            )
        elif self._purchase_count == 1:
            self._purchase_label.configure(
                text="1 item to purchase",
                text_color="orange",
            )
        else:
            self._purchase_label.configure(
                text=f"{self._purchase_count} items to purchase",
                text_color="orange",
            )

        # Sufficient label
        if self._sufficient_count == 0:
            self._sufficient_label.configure(
                text="",  # Hide when no sufficient items
            )
        elif self._sufficient_count == 1:
            self._sufficient_label.configure(
                text="1 item sufficient",
                text_color="green",
            )
        else:
            self._sufficient_label.configure(
                text=f"{self._sufficient_count} items sufficient",
                text_color="green",
            )

    def clear(self) -> None:
        """Clear the summary display."""
        self.update_summary(None)
```

**Files**: `src/ui/components/shopping_summary_frame.py`

**Validation**:
- [ ] update_summary accepts GapAnalysisResult or None
- [ ] Labels update with correct text
- [ ] Colors change based on status

---

### Subtask T013 – Add Compact Styling

**Purpose**: Ensure the widget fits the compact layout requirements.

**Steps**:
1. Add height constraint and styling:

```python
    def __init__(
        self,
        parent,
        height: int = 50,  # Compact default height
        **kwargs,
    ):
        """
        Initialize shopping summary frame.

        Args:
            parent: Parent widget
            height: Fixed height in pixels (default 50)
        """
        # Set height
        kwargs.setdefault("height", height)

        super().__init__(parent, **kwargs)

        # ... rest of __init__
```

2. Update `_layout_widgets` for tighter spacing:

```python
    def _layout_widgets(self) -> None:
        """Position widgets using grid layout."""
        # Prevent frame from shrinking
        self.grid_propagate(False)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self._label.grid(row=0, column=0, padx=(10, 20), pady=5, sticky="w")
        self._purchase_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self._sufficient_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")
```

3. Optionally add a subtle border or background to distinguish the section:

```python
        # In __init__, before super().__init__
        kwargs.setdefault("fg_color", ("gray90", "gray20"))  # Light/dark mode colors
        kwargs.setdefault("corner_radius", 8)
```

**Files**: `src/ui/components/shopping_summary_frame.py`

**Validation**:
- [ ] Widget height is compact (~50-60px)
- [ ] Widget fills horizontal space
- [ ] Looks consistent with other planning sections

## Final Complete File

After all subtasks, the file should look like:

```python
"""
Shopping Summary Frame - Compact display of shopping list status.

Feature 076: Assembly Feasibility & Single-Screen Planning
"""

import customtkinter as ctk
from typing import Optional

from src.services.inventory_gap_service import GapAnalysisResult


class ShoppingSummaryFrame(ctk.CTkFrame):
    """
    Compact widget displaying shopping list summary.

    Shows count of items needing purchase vs items already sufficient.
    Designed for single-screen planning layout integration.
    """

    def __init__(
        self,
        parent,
        height: int = 50,
        **kwargs,
    ):
        """
        Initialize shopping summary frame.

        Args:
            parent: Parent widget
            height: Fixed height in pixels
        """
        kwargs.setdefault("height", height)
        kwargs.setdefault("fg_color", ("gray90", "gray20"))
        kwargs.setdefault("corner_radius", 8)

        super().__init__(parent, **kwargs)

        self._purchase_count: int = 0
        self._sufficient_count: int = 0

        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self) -> None:
        """Create internal widgets."""
        self._label = ctk.CTkLabel(
            self,
            text="Shopping List",
            font=ctk.CTkFont(weight="bold", size=14),
            anchor="w",
        )

        self._purchase_label = ctk.CTkLabel(
            self,
            text="0 items to purchase",
            text_color="orange",
            anchor="w",
        )

        self._sufficient_label = ctk.CTkLabel(
            self,
            text="0 items sufficient",
            text_color="green",
            anchor="w",
        )

    def _layout_widgets(self) -> None:
        """Position widgets using grid layout."""
        self.grid_propagate(False)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self._label.grid(row=0, column=0, padx=(10, 20), pady=5, sticky="w")
        self._purchase_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self._sufficient_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")

    def update_summary(self, gap_result: Optional[GapAnalysisResult]) -> None:
        """Update display with gap analysis results."""
        if gap_result is None:
            self._purchase_count = 0
            self._sufficient_count = 0
        else:
            self._purchase_count = len(gap_result.purchase_items)
            self._sufficient_count = len(gap_result.sufficient_items)

        self._update_display()

    def _update_display(self) -> None:
        """Update label text based on current counts."""
        if self._purchase_count == 0:
            self._purchase_label.configure(
                text="No purchases needed",
                text_color="green",
            )
        elif self._purchase_count == 1:
            self._purchase_label.configure(
                text="1 item to purchase",
                text_color="orange",
            )
        else:
            self._purchase_label.configure(
                text=f"{self._purchase_count} items to purchase",
                text_color="orange",
            )

        if self._sufficient_count == 0:
            self._sufficient_label.configure(text="")
        elif self._sufficient_count == 1:
            self._sufficient_label.configure(
                text="1 item sufficient",
                text_color="green",
            )
        else:
            self._sufficient_label.configure(
                text=f"{self._sufficient_count} items sufficient",
                text_color="green",
            )

    def clear(self) -> None:
        """Clear the summary display."""
        self.update_summary(None)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Layout overflow | Use fixed height, test on target resolution |
| Import circular | Import GapAnalysisResult type only |

## Definition of Done Checklist

- [ ] File created at correct path
- [ ] Widget displays purchase and sufficient counts
- [ ] update_summary method works with GapAnalysisResult
- [ ] Compact height (~50px)
- [ ] No linting errors

## Review Guidance

- Test widget instantiation manually if possible
- Verify color coding matches plan.md D5
- Check that clear() resets display properly

## Activity Log

- 2026-01-27T15:30:00Z – system – lane=planned – Prompt created.
