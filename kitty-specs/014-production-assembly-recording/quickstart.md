# Quickstart: Production & Assembly Recording UI

**Feature**: 014-production-assembly-recording
**Date**: 2025-12-10

## Overview

This feature adds UI components for recording batch production and assembly operations in the Seasonal Baking Tracker. It creates modal dialogs for production/assembly recording, detail views for FinishedUnit and FinishedGood, and a Production Dashboard tab.

## Prerequisites

- Feature 013 complete (BatchProductionService, AssemblyService)
- Python 3.10+ with virtual environment activated
- All existing tests passing

## Quick Verification

```bash
# Verify Feature 013 services are available
python -c "from src.services.batch_production_service import check_can_produce, record_batch_production; print('Production service OK')"
python -c "from src.services.assembly_service import check_can_assemble, record_assembly; print('Assembly service OK')"

# Run existing tests to ensure baseline
pytest src/tests -v -k "batch_production or assembly"
```

## File Structure

```
src/ui/
├── forms/
│   ├── record_production_dialog.py   # NEW: Production recording dialog
│   ├── record_assembly_dialog.py     # NEW: Assembly recording dialog
│   ├── finished_unit_detail.py       # NEW: FinishedUnit detail modal
│   └── finished_good_detail.py       # NEW: FinishedGood detail modal
├── widgets/
│   └── availability_display.py       # NEW: Availability check display widget
├── production_dashboard_tab.py       # NEW: Replaces production_tab.py
├── finished_units_tab.py             # MODIFY: Add detail view trigger
├── finished_goods_tab.py             # MODIFY: Add detail view trigger
└── main_window.py                    # MODIFY: Use new production tab
```

## Key Components

### 1. RecordProductionDialog

Modal dialog for recording batch production.

**Inputs**: FinishedUnit object (from detail view)
**Displays**:
- FinishedUnit name, recipe name
- Batch count input (default: 1)
- Expected yield (calculated: batches x items_per_batch)
- Actual yield input (default: expected)
- Notes textarea
- Availability check display (refreshable)
- Confirm/Cancel buttons

**Behavior**:
- On open: calls `check_can_produce()` and displays results
- "Refresh" button: re-runs availability check with current batch count
- Confirm disabled if availability check fails
- On confirm: calls `record_batch_production()` via service integrator

### 2. RecordAssemblyDialog

Modal dialog for recording assembly.

**Inputs**: FinishedGood object (from detail view)
**Displays**:
- FinishedGood name
- Quantity input (default: 1)
- Notes textarea
- Availability check display (refreshable)
- Confirm/Cancel buttons

**Behavior**:
- On open: calls `check_can_assemble()` and displays results
- "Refresh" button: re-runs availability check with current quantity
- Confirm disabled if availability check fails
- On confirm: calls `record_assembly()` via service integrator

### 3. FinishedUnitDetailDialog

Modal showing FinishedUnit details with production capability.

**Displays**:
- Header: Display name, category
- Info section: Recipe (clickable?), inventory count, unit cost
- Production history table (DataTable subclass)
- "Record Production" button

**Behavior**:
- Double-click history row shows production run details
- "Record Production" opens RecordProductionDialog
- After recording, refreshes inventory display and history

### 4. FinishedGoodDetailDialog

Modal showing FinishedGood details with assembly capability.

**Displays**:
- Header: Display name
- Info section: Inventory count, total cost
- Composition section: List of components (FUs, FGs, packaging)
- Assembly history table (DataTable subclass)
- "Record Assembly" button

**Behavior**:
- "Record Assembly" opens RecordAssemblyDialog
- After assembly, refreshes inventory display and history

### 5. ProductionDashboardTab

New tab replacing old production_tab.py.

**Layout**:
- Two-column or tabbed view
- Left/Tab1: Recent Production Runs (last 30 days)
- Right/Tab2: Recent Assembly Runs (last 30 days)
- Navigation links to FinishedUnits and FinishedGoods tabs

**Behavior**:
- Auto-refresh on tab activation
- Click row to open detail dialog

### 6. AvailabilityDisplay Widget

Reusable widget for showing availability check results.

**Displays**:
- List of items with status indicators
- Green checkmark + name + "X available" for sufficient
- Red X + name + "Need X, have Y" for insufficient
- Overall status summary

## Service Integration

All service calls use `UIServiceIntegrator`:

```python
from src.ui.service_integration import get_ui_service_integrator, OperationType

# Example: Check availability
result = self.service_integrator.execute_service_operation(
    operation_name="Check Production Availability",
    operation_type=OperationType.READ,
    service_function=lambda: check_can_produce(recipe_id, num_batches),
    parent_widget=self,
    error_context="Checking ingredient availability"
)

# Example: Record production
result = self.service_integrator.execute_service_operation(
    operation_name="Record Production",
    operation_type=OperationType.CREATE,
    service_function=lambda: record_batch_production(
        recipe_id=recipe_id,
        finished_unit_id=finished_unit_id,
        num_batches=num_batches,
        actual_yield=actual_yield,
        notes=notes
    ),
    parent_widget=self,
    success_message=f"Recorded {num_batches} batch(es)",
    error_context="Recording batch production",
    show_success_dialog=True
)
```

## Testing Strategy

### Unit Tests
- Dialog initialization and field validation
- Availability display rendering with various states
- History table data formatting

### Integration Tests
- Dialog -> Service -> Database round-trip
- Inventory count updates after recording
- History display after recording

### Manual Tests
- Full workflow: List -> Detail -> Record -> Verify
- Edge cases: zero yield, insufficient inventory, concurrent access

## Development Order

1. **AvailabilityDisplay widget** - reusable component, needed by both dialogs
2. **RecordProductionDialog** - core P1 functionality
3. **FinishedUnitDetailDialog** - entry point for production
4. **Update FinishedUnitsTab** - trigger detail dialog
5. **RecordAssemblyDialog** - P2 functionality
6. **FinishedGoodDetailDialog** - entry point for assembly
7. **Update FinishedGoodsTab** - trigger detail dialog
8. **ProductionDashboardTab** - P3 overview
9. **Update main_window.py** - wire up new tab
10. **Deprecate old production_tab.py**
