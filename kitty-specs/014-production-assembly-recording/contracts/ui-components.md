# UI Component Contracts

**Feature**: 014-production-assembly-recording
**Date**: 2025-12-10

## Overview

This document defines the contracts (interfaces) for UI components in this feature. Since this is a desktop CustomTkinter application (not a web API), contracts are defined as Python class interfaces.

## Dialog Contracts

### RecordProductionDialog

```python
class RecordProductionDialog(ctk.CTkToplevel):
    """
    Modal dialog for recording batch production.

    Args:
        parent: Parent widget for modal positioning
        finished_unit: FinishedUnit object to record production for

    Returns via get_result():
        dict | None: Production parameters if confirmed, None if cancelled
        {
            "recipe_id": int,
            "finished_unit_id": int,
            "num_batches": int,
            "actual_yield": int,
            "notes": str | None
        }
    """

    def __init__(self, parent, finished_unit: FinishedUnit):
        ...

    def get_result(self) -> dict | None:
        """Return dialog result after wait_window()"""
        ...

    def refresh_availability(self) -> None:
        """Re-run availability check with current inputs"""
        ...
```

### RecordAssemblyDialog

```python
class RecordAssemblyDialog(ctk.CTkToplevel):
    """
    Modal dialog for recording assembly.

    Args:
        parent: Parent widget for modal positioning
        finished_good: FinishedGood object to record assembly for

    Returns via get_result():
        dict | None: Assembly parameters if confirmed, None if cancelled
        {
            "finished_good_id": int,
            "quantity": int,
            "notes": str | None
        }
    """

    def __init__(self, parent, finished_good: FinishedGood):
        ...

    def get_result(self) -> dict | None:
        """Return dialog result after wait_window()"""
        ...

    def refresh_availability(self) -> None:
        """Re-run availability check with current inputs"""
        ...
```

### FinishedUnitDetailDialog

```python
class FinishedUnitDetailDialog(ctk.CTkToplevel):
    """
    Modal dialog showing FinishedUnit details and production history.

    Args:
        parent: Parent widget for modal positioning
        finished_unit: FinishedUnit object to display
        on_inventory_changed: Optional callback when inventory changes

    No return value - dialog is for viewing and actions.
    """

    def __init__(
        self,
        parent,
        finished_unit: FinishedUnit,
        on_inventory_changed: Callable[[], None] | None = None
    ):
        ...

    def refresh(self) -> None:
        """Refresh all displayed data"""
        ...

    def _open_record_production(self) -> None:
        """Open production recording dialog"""
        ...
```

### FinishedGoodDetailDialog

```python
class FinishedGoodDetailDialog(ctk.CTkToplevel):
    """
    Modal dialog showing FinishedGood details and assembly history.

    Args:
        parent: Parent widget for modal positioning
        finished_good: FinishedGood object to display
        on_inventory_changed: Optional callback when inventory changes

    No return value - dialog is for viewing and actions.
    """

    def __init__(
        self,
        parent,
        finished_good: FinishedGood,
        on_inventory_changed: Callable[[], None] | None = None
    ):
        ...

    def refresh(self) -> None:
        """Refresh all displayed data"""
        ...

    def _open_record_assembly(self) -> None:
        """Open assembly recording dialog"""
        ...
```

## Widget Contracts

### AvailabilityDisplay

```python
class AvailabilityDisplay(ctk.CTkFrame):
    """
    Widget displaying availability check results with color coding.

    Args:
        parent: Parent widget
        title: Section title (e.g., "Ingredient Availability")

    Methods:
        set_availability(result): Update display with check results
        clear(): Clear all items
    """

    def __init__(self, parent, title: str = "Availability"):
        ...

    def set_availability(self, result: dict) -> None:
        """
        Update display with availability check results.

        Args:
            result: Dict from check_can_produce() or check_can_assemble()
                {
                    "can_produce": bool,  # or "can_assemble"
                    "missing": [
                        {
                            "ingredient_name": str,  # or "component_name"
                            "needed": Decimal | int,
                            "available": Decimal | int,
                            "unit": str  # optional
                        },
                        ...
                    ]
                }
        """
        ...

    def is_sufficient(self) -> bool:
        """Return True if all items have sufficient availability"""
        ...

    def clear(self) -> None:
        """Clear all displayed items"""
        ...
```

### ProductionHistoryTable

```python
class ProductionHistoryTable(DataTable):
    """
    DataTable subclass for displaying production run history.

    Columns:
        Date | Batches | Yield | Cost

    Row data: ProductionRun dict from get_production_history()
    """

    COLUMNS = [
        ("Date", 100),
        ("Batches", 70),
        ("Yield", 100),
        ("Cost", 80)
    ]

    def _get_row_values(self, run: dict) -> tuple:
        """Format production run for display"""
        return (
            self._format_date(run["produced_at"]),
            str(run["num_batches"]),
            f"{run['actual_yield']} / {run['expected_yield']}",
            self._format_currency(run["total_ingredient_cost"])
        )
```

### AssemblyHistoryTable

```python
class AssemblyHistoryTable(DataTable):
    """
    DataTable subclass for displaying assembly run history.

    Columns:
        Date | Quantity | Cost

    Row data: AssemblyRun dict from get_assembly_history()
    """

    COLUMNS = [
        ("Date", 100),
        ("Quantity", 80),
        ("Cost", 80)
    ]

    def _get_row_values(self, run: dict) -> tuple:
        """Format assembly run for display"""
        return (
            self._format_date(run["assembled_at"]),
            str(run["quantity_assembled"]),
            self._format_currency(run["total_component_cost"])
        )
```

## Tab Contract

### ProductionDashboardTab

```python
class ProductionDashboardTab(ctk.CTkFrame):
    """
    Tab showing recent production and assembly activity.

    Replaces old production_tab.py.

    Layout:
        - Header with title and navigation links
        - CTkTabview with "Production Runs" and "Assembly Runs" tabs
        - Each sub-tab has DataTable with recent runs (30 days)
    """

    def __init__(self, parent, **kwargs):
        ...

    def refresh(self) -> None:
        """Refresh both production and assembly tables"""
        ...

    def _load_production_runs(self) -> None:
        """Load recent production runs into table"""
        ...

    def _load_assembly_runs(self) -> None:
        """Load recent assembly runs into table"""
        ...

    def _navigate_to_finished_units(self) -> None:
        """Navigate to FinishedUnits tab"""
        ...

    def _navigate_to_finished_goods(self) -> None:
        """Navigate to FinishedGoods tab"""
        ...
```

## Service Integration Contract

All UI components use the existing `UIServiceIntegrator` pattern:

```python
# Import
from src.ui.service_integration import get_ui_service_integrator, OperationType

# In __init__
self.service_integrator = get_ui_service_integrator()

# For operations
result = self.service_integrator.execute_service_operation(
    operation_name: str,           # Human-readable name for logs
    operation_type: OperationType, # CREATE, READ, UPDATE, DELETE, SEARCH
    service_function: Callable,    # Lambda wrapping service call
    parent_widget: Widget,         # For error dialog positioning
    success_message: str = None,   # Optional success toast
    error_context: str = None,     # Context for error messages
    show_success_dialog: bool = False,
    log_level: int = logging.INFO,
    suppress_exception: bool = False
) -> Any  # Returns service function result or raises
```

## Callback Contracts

### Inventory Changed Callback

Used to notify parent when inventory has been modified:

```python
# Type
OnInventoryChanged = Callable[[], None]

# Usage in detail dialogs
def __init__(self, ..., on_inventory_changed: OnInventoryChanged | None = None):
    self._on_inventory_changed = on_inventory_changed

def _after_recording_success(self):
    self.refresh()  # Refresh own display
    if self._on_inventory_changed:
        self._on_inventory_changed()  # Notify parent

# Usage in tabs
def _show_detail_dialog(self, item):
    dialog = FinishedUnitDetailDialog(
        self,
        item,
        on_inventory_changed=self._refresh_list
    )
    dialog.wait_window()
```
