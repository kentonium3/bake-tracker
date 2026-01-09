---
work_package_id: "WP06"
subtasks:
  - "T040"
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
title: "View Details Dialog"
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

# Work Package Prompt: WP06 - View Details Dialog

## Objectives & Success Criteria

Implement purchase details with usage history (User Story 6).

**Agent Assignment**: Gemini (can run parallel with WP05 after WP01 completes)

**Success Criteria**:
- View Details shows purchase info (date, supplier, price, notes)
- Shows inventory tracking (original, used, remaining)
- Shows usage history table (date, recipe, quantity, cost)
- "Edit Purchase" button opens edit dialog

## Context & Constraints

**Reference Documents**:
- `kitty-specs/042-purchases-tab-crud-operations/data-model.md` - get_remaining_inventory, get_purchase_usage_history

**Key Constraints**:
- Read-only dialog (no save, just close)
- Performance: limit usage history to 50 items
- Edit button closes details and opens edit dialog

## Subtasks & Detailed Guidance

### Subtask T040 - Create PurchaseDetailsDialog Class

**Purpose**: Establish dialog structure.

**Steps**:
1. Create `src/ui/dialogs/purchase_details_dialog.py`
2. Class signature:
   ```python
   class PurchaseDetailsDialog(ctk.CTkToplevel):
       def __init__(self, parent, purchase_id: int, on_edit: Optional[Callable] = None):
           super().__init__(parent)
           self.title("Purchase Details")
           self.purchase_id = purchase_id
           self.on_edit = on_edit

           # Load data
           self.purchase = PurchaseService().get_purchase(purchase_id)
           self.remaining = PurchaseService().get_remaining_inventory(purchase_id)
           self.usage_history = PurchaseService().get_purchase_usage_history(purchase_id)

           # Make modal
           self.transient(parent)
           self.grab_set()

           self.geometry("500x600")
           self._center_on_parent(parent)

           self._create_widgets()
           self._layout_widgets()
   ```

**Files**: `src/ui/dialogs/purchase_details_dialog.py`
**Parallel?**: No (foundation)

### Subtask T041 - Purchase Info Section

**Purpose**: Display purchase details.

**Steps**:
1. Create info section:
   ```python
   def _create_info_section(self):
       info_frame = ctk.CTkFrame(self)

       # Product name (large, bold)
       product_label = ctk.CTkLabel(
           info_frame,
           text=self.purchase.product.display_name,
           font=ctk.CTkFont(size=18, weight="bold")
       )
       product_label.pack(anchor="w", pady=(10, 5))

       # Details grid
       details = [
           ("Date:", self.purchase.purchase_date.strftime("%B %d, %Y")),
           ("Supplier:", f"{self.purchase.supplier.name}"),
           ("Quantity:", f"{self.purchase.quantity_purchased} package(s)"),
           ("Unit Price:", f"${self.purchase.unit_price:.2f}"),
           ("Total Cost:", f"${self.purchase.total_cost:.2f}"),
       ]

       for label, value in details:
           row = ctk.CTkFrame(info_frame, fg_color="transparent")
           ctk.CTkLabel(row, text=label, width=100, anchor="w").pack(side="left")
           ctk.CTkLabel(row, text=value, anchor="w").pack(side="left")
           row.pack(fill="x", pady=2)

       # Notes (if present)
       if self.purchase.notes:
           ctk.CTkLabel(info_frame, text="Notes:", anchor="w").pack(anchor="w", pady=(10, 2))
           notes_box = ctk.CTkTextbox(info_frame, height=60)
           notes_box.insert("1.0", self.purchase.notes)
           notes_box.configure(state="disabled")
           notes_box.pack(fill="x", pady=2)

       return info_frame
   ```

**Files**: `src/ui/dialogs/purchase_details_dialog.py`
**Parallel?**: No (depends on T040)

### Subtask T042 - Inventory Tracking Section

**Purpose**: Show original, used, remaining quantities.

**Steps**:
1. Calculate values:
   ```python
   def _create_inventory_section(self):
       inv_frame = ctk.CTkFrame(self)

       ctk.CTkLabel(
           inv_frame,
           text="Inventory Tracking",
           font=ctk.CTkFont(size=14, weight="bold")
       ).pack(anchor="w", pady=(10, 5))

       # Calculate quantities
       package_qty = self.purchase.product.package_unit_quantity
       original = self.purchase.quantity_purchased * package_qty
       remaining = self.remaining
       used = original - remaining
       used_pct = (used / original * 100) if original > 0 else 0

       unit = self.purchase.product.package_unit

       # Display
       rows = [
           ("Original:", f"{original} {unit}"),
           ("Used:", f"{used} {unit} ({used_pct:.0f}%)"),
           ("Remaining:", f"{remaining} {unit}"),
       ]

       for label, value in rows:
           row = ctk.CTkFrame(inv_frame, fg_color="transparent")
           ctk.CTkLabel(row, text=label, width=100, anchor="w").pack(side="left")

           # Highlight remaining in different color if low
           color = "red" if remaining == 0 else ("orange" if remaining < original * 0.2 else None)
           ctk.CTkLabel(row, text=value, anchor="w", text_color=color).pack(side="left")
           row.pack(fill="x", pady=2)

       return inv_frame
   ```

**Files**: `src/ui/dialogs/purchase_details_dialog.py`
**Parallel?**: No (depends on T040)

### Subtask T043 - Usage History Table

**Purpose**: Show where inventory was consumed.

**Steps**:
1. Create usage history section:
   ```python
   def _create_usage_section(self):
       usage_frame = ctk.CTkFrame(self)

       ctk.CTkLabel(
           usage_frame,
           text="Usage History",
           font=ctk.CTkFont(size=14, weight="bold")
       ).pack(anchor="w", pady=(10, 5))

       if not self.usage_history:
           ctk.CTkLabel(
               usage_frame,
               text="No usage recorded yet",
               text_color="gray"
           ).pack(anchor="w")
           return usage_frame

       # Create treeview for usage
       columns = ("date", "recipe", "quantity", "cost")
       tree = ttk.Treeview(usage_frame, columns=columns, show="headings", height=8)

       tree.heading("date", text="Date")
       tree.heading("recipe", text="Recipe")
       tree.heading("quantity", text="Qty Used")
       tree.heading("cost", text="Cost")

       tree.column("date", width=100)
       tree.column("recipe", width=150)
       tree.column("quantity", width=80, anchor="e")
       tree.column("cost", width=80, anchor="e")

       # Populate (limit to 50)
       for usage in self.usage_history[:50]:
           tree.insert("", "end", values=(
               usage["depleted_at"].strftime("%m/%d/%Y"),
               usage["recipe_name"],
               f"{usage['quantity_used']:.1f}",
               f"${usage['cost']:.2f}"
           ))

       tree.pack(fill="both", expand=True)

       if len(self.usage_history) > 50:
           ctk.CTkLabel(
               usage_frame,
               text=f"Showing 50 of {len(self.usage_history)} usage records",
               text_color="gray"
           ).pack(anchor="w")

       return usage_frame
   ```

**Files**: `src/ui/dialogs/purchase_details_dialog.py`
**Parallel?**: No (depends on T040)

### Subtask T044 - Edit Purchase Quick Action

**Purpose**: Button to open edit dialog.

**Steps**:
1. Add buttons at bottom:
   ```python
   def _create_buttons(self):
       button_frame = ctk.CTkFrame(self, fg_color="transparent")

       edit_btn = ctk.CTkButton(
           button_frame,
           text="Edit Purchase",
           command=self._on_edit_click
       )
       edit_btn.pack(side="left", padx=5)

       close_btn = ctk.CTkButton(
           button_frame,
           text="Close",
           command=self.destroy
       )
       close_btn.pack(side="right", padx=5)

       return button_frame

   def _on_edit_click(self):
       self.destroy()
       if self.on_edit:
           self.on_edit(self.purchase_id)
   ```

**Files**: `src/ui/dialogs/purchase_details_dialog.py`
**Parallel?**: No (depends on T040)

### Subtask T045 - Wire View Details Action

**Purpose**: Connect context menu to dialog.

**Steps**:
1. In `PurchasesTab`, implement `_on_view_details()`:
   ```python
   def _on_view_details(self):
       selected = self.tree.selection()
       if not selected:
           return

       purchase_id = self._get_purchase_id_from_selection(selected[0])

       def on_edit(pid):
           from src.ui.dialogs.edit_purchase_dialog import EditPurchaseDialog
           dialog = EditPurchaseDialog(self, pid, on_save=self._on_filter_change)
           dialog.focus()

       from src.ui.dialogs.purchase_details_dialog import PurchaseDetailsDialog
       dialog = PurchaseDetailsDialog(self, purchase_id, on_edit=on_edit)
       dialog.focus()
   ```

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (integration)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large usage history slow | Limit to 50 records; show count of remaining |
| Dialog too tall for screen | Use scrollable frame or limit sections |
| Edit callback fails | Handle exception; show error |

## Definition of Done Checklist

- [ ] Dialog opens from context menu View Details
- [ ] Purchase info section complete
- [ ] Inventory tracking shows original/used/remaining
- [ ] Usage history table populated (or "no usage" message)
- [ ] Edit Purchase button opens edit dialog
- [ ] Close button dismisses dialog

## Review Guidance

- Test with purchase that has usage history
- Test with purchase that has no usage (unconsumed)
- Test edit button flow (close details, open edit)
- Verify remaining calculation matches reality

## Activity Log

- 2026-01-08T22:30:00Z - system - lane=planned - Prompt created.
- 2026-01-09T04:02:15Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-09T04:04:04Z – unknown – lane=for_review – PurchaseDetailsDialog with info/inventory/usage sections, Edit button, wired to PurchasesTab. All tests pass.
- 2026-01-09T04:59:16Z – agent – lane=doing – Started review via workflow command
- 2026-01-09T04:59:32Z – unknown – lane=done – Review passed: PurchaseDetailsDialog with purchase info, inventory tracking, usage history implemented
