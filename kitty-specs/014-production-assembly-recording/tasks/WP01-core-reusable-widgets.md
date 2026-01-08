---
work_package_id: WP01
title: Core Reusable Widgets
lane: done
history:
- timestamp: '2025-12-10T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: ''
phase: Phase 1 - Foundational Widgets
review_status: ''
reviewed_by: ''
shell_pid: '45064'
subtasks:
- T001
- T002
- T003
- T004
---

# Work Package Prompt: WP01 - Core Reusable Widgets

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the foundational UI widgets needed by all production and assembly dialogs:

1. **AvailabilityDisplay** - Reusable widget showing availability check results with color coding
2. **ProductionHistoryTable** - DataTable subclass for production run history
3. **AssemblyHistoryTable** - DataTable subclass for assembly run history

**Success Criteria**:
- Widgets can be instantiated with mock/real data and render correctly
- Color coding works (green for sufficient, red for insufficient)
- History tables format dates, quantities, and costs properly
- Widgets follow existing patterns from `src/ui/widgets/`

## Context & Constraints

**Reference Documents**:
- `kitty-specs/014-production-assembly-recording/plan.md` - Component specifications
- `kitty-specs/014-production-assembly-recording/contracts/ui-components.md` - Widget contracts
- `kitty-specs/014-production-assembly-recording/research.md` - Existing patterns

**Existing Patterns to Follow**:
- `src/ui/widgets/data_table.py` - Base DataTable class
- `src/utils/constants.py` - COLOR_SUCCESS, COLOR_ERROR, padding constants

**Architecture Constraint**: Widgets must not contain business logic - they only display data passed to them.

## Subtasks & Detailed Guidance

### Subtask T001 - Create AvailabilityDisplay Widget

**Purpose**: Reusable widget for showing ingredient/component availability with status indicators.

**File**: `src/ui/widgets/availability_display.py`

**Steps**:
1. Create new file with class `AvailabilityDisplay(ctk.CTkFrame)`
2. Implement `__init__(self, parent, title: str = "Availability")`
3. Create scrollable frame for item list
4. Implement `set_availability(self, result: dict)` method:
   - Parse `result["can_produce"]` or `result["can_assemble"]`
   - Parse `result["missing"]` list for insufficient items
   - Create status row for each item
5. Implement `is_sufficient(self) -> bool` property
6. Implement `clear(self)` method
7. Add overall status indicator (header shows green checkmark or red X)

**Item Row Format**:
```
[Icon] Item Name                    Need: X | Have: Y
```
- Green checkmark icon + green text when sufficient
- Red X icon + red text when insufficient
- Show "Need X, have Y" only for insufficient items

**Code Structure**:
```python
class AvailabilityDisplay(ctk.CTkFrame):
    def __init__(self, parent, title: str = "Availability"):
        super().__init__(parent)
        self._items = []
        self._is_sufficient = True
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        # Header with title and overall status
        # Scrollable frame for items
        pass

    def set_availability(self, result: dict) -> None:
        # Clear existing items
        # Parse result and create item rows
        # Update overall status
        pass

    def is_sufficient(self) -> bool:
        return self._is_sufficient

    def clear(self) -> None:
        # Remove all item widgets
        pass
```

**Notes**:
- Use `CTkScrollableFrame` for the item list
- Get colors from `src/utils/constants.py`
- Handle both production (ingredients) and assembly (components) data formats

---

### Subtask T002 - Create ProductionHistoryTable

**Purpose**: Display production run history with date, batches, yield, and cost columns.

**File**: `src/ui/widgets/production_history_table.py`

**Steps**:
1. Import base `DataTable` from `src/ui/widgets/data_table.py`
2. Create `ProductionHistoryTable(DataTable)` subclass
3. Define columns: `[("Date", 100), ("Batches", 70), ("Yield", 100), ("Cost", 80)]`
4. Override `_get_row_values(self, run: dict) -> tuple`
5. Add helper methods for date and currency formatting

**Implementation**:
```python
from src.ui.widgets.data_table import DataTable
from datetime import datetime
from decimal import Decimal

class ProductionHistoryTable(DataTable):
    COLUMNS = [
        ("Date", 100),
        ("Batches", 70),
        ("Yield", 100),
        ("Cost", 80)
    ]

    def __init__(self, parent, on_row_select=None, on_row_double_click=None, height=200):
        super().__init__(parent, self.COLUMNS, on_row_select, on_row_double_click, height)

    def _get_row_values(self, run: dict) -> tuple:
        return (
            self._format_date(run.get("produced_at")),
            str(run.get("num_batches", 0)),
            f"{run.get('actual_yield', 0)} / {run.get('expected_yield', 0)}",
            self._format_currency(run.get("total_ingredient_cost", "0"))
        )

    def _format_date(self, date_str: str) -> str:
        # Parse ISO date and format as "Dec 10, 2025"
        pass

    def _format_currency(self, amount) -> str:
        # Format as "$15.50"
        pass
```

**Parallel**: Yes - can proceed alongside T003

---

### Subtask T003 - Create AssemblyHistoryTable

**Purpose**: Display assembly run history with date, quantity, and cost columns.

**File**: `src/ui/widgets/assembly_history_table.py`

**Steps**:
1. Import base `DataTable` from `src/ui/widgets/data_table.py`
2. Create `AssemblyHistoryTable(DataTable)` subclass
3. Define columns: `[("Date", 100), ("Quantity", 80), ("Cost", 80)]`
4. Override `_get_row_values(self, run: dict) -> tuple`
5. Reuse formatting helpers (consider extracting to base or utility)

**Implementation**:
```python
from src.ui.widgets.data_table import DataTable

class AssemblyHistoryTable(DataTable):
    COLUMNS = [
        ("Date", 100),
        ("Quantity", 80),
        ("Cost", 80)
    ]

    def __init__(self, parent, on_row_select=None, on_row_double_click=None, height=200):
        super().__init__(parent, self.COLUMNS, on_row_select, on_row_double_click, height)

    def _get_row_values(self, run: dict) -> tuple:
        return (
            self._format_date(run.get("assembled_at")),
            str(run.get("quantity_assembled", 0)),
            self._format_currency(run.get("total_component_cost", "0"))
        )
```

**Parallel**: Yes - can proceed alongside T002

---

### Subtask T004 - Update Widget Exports

**Purpose**: Export new widgets from the widgets package.

**File**: `src/ui/widgets/__init__.py`

**Steps**:
1. Add imports for new widgets
2. Add to `__all__` list if present

**Changes**:
```python
from src.ui.widgets.availability_display import AvailabilityDisplay
from src.ui.widgets.production_history_table import ProductionHistoryTable
from src.ui.widgets.assembly_history_table import AssemblyHistoryTable
```

---

## Test Strategy

**Unit Tests** (if time permits):
- Test AvailabilityDisplay with mock availability results
- Test history tables with mock run data
- Verify formatting helpers produce expected output

**Manual Verification**:
```python
# Quick test script
import customtkinter as ctk
from src.ui.widgets.availability_display import AvailabilityDisplay

root = ctk.CTk()
widget = AvailabilityDisplay(root, "Test Availability")
widget.set_availability({
    "can_produce": False,
    "missing": [
        {"ingredient_name": "Flour", "needed": 500, "available": 200, "unit": "g"},
        {"ingredient_name": "Sugar", "needed": 100, "available": 150, "unit": "g"}
    ]
})
widget.pack()
root.mainloop()
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| DataTable API differs from expected | Read data_table.py carefully before starting |
| Color constants missing | Define locally if not in constants.py |
| Scrollable frame sizing issues | Test with varying item counts |

## Definition of Done Checklist

- [ ] T001: AvailabilityDisplay widget created and functional
- [ ] T002: ProductionHistoryTable created and formats data correctly
- [ ] T003: AssemblyHistoryTable created and formats data correctly
- [ ] T004: Widget exports updated
- [ ] All widgets follow existing patterns
- [ ] Manual smoke test passes

## Review Guidance

- Verify color coding matches spec (green=sufficient, red=insufficient)
- Verify date formatting is user-friendly
- Verify currency formatting includes $ and 2 decimal places
- Check scrolling works with many items
- Ensure no business logic in widgets

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-10T06:49:10Z – claude – shell_pid=45064 – lane=doing – Started implementation of Core Reusable Widgets
- 2025-12-10T06:55:42Z – claude – shell_pid=45064 – lane=for_review – Completed implementation - T001, T002, T003, T004 all done
- 2025-12-10T15:20:36Z – claude – shell_pid=45064 – lane=done – Code review approved - all widgets implemented correctly with proper formatting
