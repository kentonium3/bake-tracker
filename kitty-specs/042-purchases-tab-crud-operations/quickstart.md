# Quickstart: Purchases Tab with CRUD Operations

**Feature**: 042-purchases-tab-crud-operations
**Date**: 2026-01-08

## TL;DR

Implement Purchases tab with full CRUD. Extend PurchaseService, create PurchasesTab + 3 dialogs.

## File Checklist

| File | Action | Agent |
|------|--------|-------|
| `src/services/purchase_service.py` | EXTEND | Claude |
| `src/ui/tabs/purchases_tab.py` | CREATE | Claude |
| `src/ui/dialogs/add_purchase_dialog.py` | CREATE | Claude |
| `src/ui/dialogs/edit_purchase_dialog.py` | CREATE | Gemini |
| `src/ui/dialogs/purchase_details_dialog.py` | CREATE | Gemini |
| `src/ui/dashboards/purchase_dashboard.py` | MODIFY | Claude |
| `src/tests/unit/test_purchase_service.py` | EXTEND | Claude |

## Pattern Quick Reference

### Session Management (REQUIRED)

```python
def new_method(..., session: Optional[Session] = None) -> ReturnType:
    def _impl(sess: Session) -> ReturnType:
        # All queries/updates use sess
        purchase = sess.query(Purchase).filter(...).first()
        return result

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Dialog Pattern

```python
class SomeDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save: Optional[Callable] = None):
        super().__init__(parent)
        self.on_save = on_save
        self.transient(parent)
        self.grab_set()
        self._create_widgets()
        self._layout_widgets()
```

### Tab Pattern

```python
class SomeTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Content expands
        self._create_header()
        self._create_controls()
        self._create_item_list()
```

## Key Clarifications

1. **Quantity**: Allow 1 decimal place (e.g., 1.5 packages for bulk)
2. **Default filter**: "Last 30 days"
3. **Delete**: Block if ANY consumption exists; cascade to InventoryItem

## Service Methods to Add

```python
# In purchase_service.py

def get_purchases_filtered(date_range, supplier_id, search, session=None) -> List[Dict]
def get_remaining_inventory(purchase_id, session=None) -> Decimal
def can_edit_purchase(purchase_id, new_quantity, session=None) -> Tuple[bool, str]
def can_delete_purchase(purchase_id, session=None) -> Tuple[bool, str]
def update_purchase(purchase_id, updates, session=None) -> Purchase
def get_purchase_usage_history(purchase_id, session=None) -> List[Dict]
```

## Test Coverage Targets

- `get_purchases_filtered`: filter combinations, empty results
- `can_edit_purchase`: allowed edit, blocked edit (consumed), edge cases
- `can_delete_purchase`: allowed delete, blocked delete (consumed)
- `update_purchase`: field updates, FIFO cost recalculation
- `get_purchase_usage_history`: with depletions, without depletions

## UI Integration Point

In `purchase_dashboard.py`, add Purchases tab:

```python
# After Inventory tab
self.purchases_tab = self.tabview.add("Purchases")
from src.ui.tabs.purchases_tab import PurchasesTab
self.purchases = PurchasesTab(self.purchases_tab)
```

## Parallelization Handoff

**When service layer is complete**, Gemini can start on:
- `edit_purchase_dialog.py` (uses `can_edit_purchase`, `update_purchase`)
- `purchase_details_dialog.py` (uses `get_purchase`, `get_remaining_inventory`, `get_purchase_usage_history`)

Both dialogs are independent and can be built in parallel with Tab UI.
