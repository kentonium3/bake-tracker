---
work_package_id: "WP05"
subtasks:
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
title: "Delete Purchase"
phase: "Phase 3 - Secondary Features"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-08T22:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Delete Purchase

## Objectives & Success Criteria

Implement delete validation and confirmation flow (User Story 5).

**Agent Assignment**: Claude

**Success Criteria**:
- Delete consumed purchase → blocked with specific error (shows consumed qty and recipes)
- Delete unconsumed purchase → confirmation dialog → success
- Deleted purchase removed from list
- Linked inventory items cascade deleted

## Context & Constraints

**Reference Documents**:
- `kitty-specs/042-purchases-tab-crud-operations/data-model.md` - can_delete_purchase signature

**Key Constraints**:
- NEVER delete if any inventory has been consumed (FIFO integrity)
- Show specific usage details in error message
- Confirmation required before delete

## Subtasks & Detailed Guidance

### Subtask T034 - Implement Delete Handler

**Purpose**: Entry point for delete action.

**Steps**:
1. In `PurchasesTab`, implement `_on_delete()`:
   ```python
   def _on_delete(self):
       selected = self.tree.selection()
       if not selected:
           return

       # Get purchase ID from tree item
       item_values = self.tree.item(selected[0])["values"]
       purchase_id = self._get_purchase_id_from_selection(selected[0])

       # Check if can delete
       can_delete, reason = PurchaseService().can_delete_purchase(purchase_id)

       if not can_delete:
           self._show_delete_blocked_dialog(purchase_id, reason)
       else:
           self._show_delete_confirmation_dialog(purchase_id)
   ```

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (foundation)

### Subtask T035 - Validation Check

**Purpose**: Call can_delete_purchase() for validation.

**Steps**:
1. The validation is done in T034
2. Ensure purchase_id is correctly extracted from tree selection
3. Handle case where can_delete_purchase raises exception

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (part of T034)

### Subtask T036 - Error Dialog (Blocked)

**Purpose**: Show why deletion is blocked with usage details.

**Steps**:
1. Implement `_show_delete_blocked_dialog()`:
   ```python
   def _show_delete_blocked_dialog(self, purchase_id: int, reason: str):
       # Get additional details for the error message
       purchase = PurchaseService().get_purchase(purchase_id)
       usage_history = PurchaseService().get_purchase_usage_history(purchase_id)

       # Build detailed message
       message = f"Cannot Delete Purchase\n\n"
       message += f"{purchase.product.display_name}\n"
       message += f"Purchased: {purchase.purchase_date}\n\n"
       message += f"Reason: {reason}\n\n"

       if usage_history:
           message += "Usage Details:\n"
           for usage in usage_history[:5]:  # Show first 5
               message += f"  - {usage['recipe_name']}: {usage['quantity_used']} ({usage['depleted_at'].strftime('%m/%d/%Y')})\n"
           if len(usage_history) > 5:
               message += f"  ... and {len(usage_history) - 5} more\n"

       message += "\nYou can edit this purchase instead, or manually adjust inventory if needed."

       # Show dialog
       from tkinter import messagebox
       messagebox.showerror("Cannot Delete", message)
   ```

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (depends on T034)

### Subtask T037 - Confirmation Dialog (Allowed)

**Purpose**: Confirm before deleting.

**Steps**:
1. Implement `_show_delete_confirmation_dialog()`:
   ```python
   def _show_delete_confirmation_dialog(self, purchase_id: int):
       purchase = PurchaseService().get_purchase(purchase_id)
       remaining = PurchaseService().get_remaining_inventory(purchase_id)

       # Build confirmation message
       message = f"Delete this purchase?\n\n"
       message += f"{purchase.product.display_name}\n"
       message += f"Purchased: {purchase.purchase_date}\n"
       message += f"Price: ${purchase.unit_price:.2f}\n\n"

       if remaining > 0:
           message += f"This will also remove {remaining} {purchase.product.package_unit} from inventory.\n\n"

       message += "This action cannot be undone."

       from tkinter import messagebox
       if messagebox.askyesno("Confirm Delete", message):
           self._execute_delete(purchase_id)
   ```

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (depends on T034)

### Subtask T038 - Execute Delete

**Purpose**: Call delete_purchase() on confirmation.

**Steps**:
1. Implement `_execute_delete()`:
   ```python
   def _execute_delete(self, purchase_id: int):
       try:
           PurchaseService().delete_purchase(purchase_id)
           # Refresh list
           self._on_filter_change()
       except Exception as e:
           from tkinter import messagebox
           messagebox.showerror("Delete Failed", f"Failed to delete purchase: {str(e)}")
   ```

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (depends on T037)

### Subtask T039 - List Refresh

**Purpose**: Update list after successful deletion.

**Steps**:
1. The refresh is done in T038 via `_on_filter_change()`
2. Verify the deleted item is no longer in the list
3. Maintain scroll position if possible (or scroll to top)

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (verification)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Accidental deletion | Require explicit confirmation; show cascade impact |
| Race condition (consumed while confirming) | Re-check can_delete before executing |
| Cascade delete fails | Handle exception; show error message |

## Definition of Done Checklist

- [ ] Context menu Delete triggers validation
- [ ] Consumed purchases blocked with detailed error
- [ ] Unconsumed purchases show confirmation
- [ ] Delete cascades to inventory items
- [ ] List refreshes after deletion
- [ ] Error handling for failed deletes

## Review Guidance

- Test with fully consumed purchase (should be blocked)
- Test with partially consumed purchase (should be blocked)
- Test with unconsumed purchase (should succeed)
- Verify cascade delete removes inventory items

## Activity Log

- 2026-01-08T22:30:00Z - system - lane=planned - Prompt created.
- 2026-01-09T03:59:08Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-09T04:00:44Z – unknown – lane=for_review – Enhanced delete dialogs with product details, remaining inventory impact, race condition protection. All 45 tests pass.
- 2026-01-09T04:59:01Z – agent – lane=doing – Started review via workflow command
- 2026-01-09T04:59:12Z – unknown – lane=done – Review passed: Delete with validation, confirmation dialog, keyboard shortcuts implemented
