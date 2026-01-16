---
id: WP02
title: Purchase Mode Tab Reorder
lane: "done"
agent: null
review_status: null
created_at: 2026-01-15
---

# WP02: Purchase Mode Tab Reorder

**Feature**: 055-workflow-aligned-navigation-cleanup
**Phase**: 2 | **Risk**: Low
**FR Coverage**: FR-011

---

## Objective

Reorder Purchase mode tabs to match natural shopping workflow: check inventory first, then purchases, then create shopping lists.

---

## Context

### Current State (purchase_mode.py:59-80)
1. Shopping Lists (line 60)
2. Purchases (line 68)
3. Inventory (line 76)

### Target State
1. Inventory
2. Purchases
3. Shopping Lists

---

## Subtasks

- [ ] T005: Reorder tabview.add() calls in setup_tabs()
- [ ] T006: Verify lazy loading order in activate()

---

## Implementation Details

### T005: Reorder tabview.add() calls

In `src/ui/modes/purchase_mode.py`, update the `setup_tabs()` method to call `tabview.add()` in the new order:

```python
def setup_tabs(self):
    """Set up the purchase mode tabs."""
    self.tabview = ctk.CTkTabview(self.content_frame)
    self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

    # Add tabs in workflow order
    self.tabview.add("Inventory")      # First: check what you have
    self.tabview.add("Purchases")      # Second: record purchases
    self.tabview.add("Shopping Lists") # Third: plan what to buy

    # Tab content setup follows same order...
```

### T006: Verify lazy loading order

Check the `activate()` method to ensure lazy loading references match the new tab order. The tab widget references (e.g., `self.inventory_tab`, `self.purchases_tab`, `self.shopping_lists_tab`) should be created in the same order.

---

## Files to Modify

| File | Action | Lines |
|------|--------|-------|
| `src/ui/modes/purchase_mode.py` | MODIFY | 59-80 (setup_tabs) |

---

## Acceptance Criteria

- [ ] Purchase mode tabs appear in order: Inventory, Purchases, Shopping Lists
- [ ] Inventory tab is selected by default when entering Purchase mode
- [ ] All tab functionality works unchanged
- [ ] Tab switching works correctly

---

## Testing

```bash
# Run app and verify:
# 1. Switch to Purchase mode
# 2. Verify tab order: Inventory, Purchases, Shopping Lists
# 3. Click each tab - verify content loads
# 4. Test CRUD operations on each tab
```

---

## Notes

This is a simple reorder with no logic changes. The existing tab widgets (InventoryTab, PurchasesTab, ShoppingListsTab) are unchanged - only the order of `tabview.add()` calls changes.

## Activity Log

- 2026-01-16T02:37:29Z – null – lane=doing – Started implementation via workflow command
- 2026-01-16T02:38:19Z – null – lane=for_review – Completed Purchase mode tab reorder: Inventory, Purchases, Shopping Lists
- 2026-01-16T04:30:34Z – null – lane=doing – Started review
- 2026-01-16T04:30:42Z – null – lane=done – Review passed: tab order verified as Inventory, Purchases, Shopping Lists
