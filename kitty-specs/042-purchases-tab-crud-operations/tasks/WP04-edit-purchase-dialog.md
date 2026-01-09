---
work_package_id: "WP04"
subtasks:
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
title: "Edit Purchase Dialog"
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

# Work Package Prompt: WP04 - Edit Purchase Dialog

## Objectives & Success Criteria

Implement the Edit Purchase dialog for correcting errors (User Story 4).

**Agent Assignment**: Gemini (can run parallel with WP03 after WP01 completes)

**Success Criteria**:
- Select purchase → Edit → dialog opens with pre-filled fields
- Product field is read-only (cannot be changed)
- Quantity change blocked if new_qty < consumed_qty
- Price change triggers FIFO cost recalculation
- Save updates purchase and recalculates costs
- List refreshes after successful save

## Context & Constraints

**Reference Documents**:
- `kitty-specs/042-purchases-tab-crud-operations/data-model.md` - can_edit_purchase, update_purchase signatures
- `src/ui/dialogs/add_purchase_dialog.py` - Pattern reference (after WP03)

**Key Constraints**:
- Product cannot be changed (would break FIFO chain)
- Quantity validation: new_quantity >= consumed_quantity
- Must recalculate FIFO costs on price change

## Subtasks & Detailed Guidance

### Subtask T027 - Create EditPurchaseDialog Class

**Purpose**: Establish dialog structure similar to AddPurchaseDialog.

**Steps**:
1. Create `src/ui/dialogs/edit_purchase_dialog.py`
2. Class signature:
   ```python
   class EditPurchaseDialog(ctk.CTkToplevel):
       def __init__(self, parent, purchase_id: int, on_save: Optional[Callable] = None):
           super().__init__(parent)
           self.title("Edit Purchase")
           self.purchase_id = purchase_id
           self.on_save = on_save

           # Load purchase data
           self.purchase = PurchaseService().get_purchase(purchase_id)
           self.consumed_qty = self._get_consumed_quantity()

           # Make modal
           self.transient(parent)
           self.grab_set()

           self._create_widgets()
           self._layout_widgets()
           self._pre_fill_fields()
   ```

**Files**: `src/ui/dialogs/edit_purchase_dialog.py`
**Parallel?**: No (foundation)

### Subtask T028 - Pre-fill Fields

**Purpose**: Populate form with existing purchase data.

**Steps**:
1. Implement `_pre_fill_fields()`:
   ```python
   def _pre_fill_fields(self):
       # Product (display only)
       self.product_label.configure(text=self.purchase.product.display_name)

       # Date
       self.date_var.set(self.purchase.purchase_date.strftime("%Y-%m-%d"))

       # Quantity
       self.qty_var.set(str(self.purchase.quantity_purchased))

       # Unit price
       self.price_var.set(f"{self.purchase.unit_price:.2f}")

       # Supplier
       self.supplier_var.set(self.purchase.supplier.name)

       # Notes
       if self.purchase.notes:
           self.notes_text.insert("1.0", self.purchase.notes)
   ```

**Files**: `src/ui/dialogs/edit_purchase_dialog.py`
**Parallel?**: No (depends on T027)

### Subtask T029 - Read-only Product Field

**Purpose**: Display product without allowing changes.

**Steps**:
1. Use CTkLabel instead of dropdown:
   ```python
   product_frame = ctk.CTkFrame(form_frame)
   ctk.CTkLabel(product_frame, text="Product:").pack(side="left")
   self.product_label = ctk.CTkLabel(
       product_frame,
       text="",
       font=ctk.CTkFont(weight="bold")
   )
   self.product_label.pack(side="left", padx=10)

   # Add info text
   ctk.CTkLabel(
       product_frame,
       text="(cannot be changed)",
       text_color="gray",
       font=ctk.CTkFont(size=11)
   ).pack(side="left")
   ```

**Files**: `src/ui/dialogs/edit_purchase_dialog.py`
**Parallel?**: No (UI element)

### Subtask T030 - Quantity Validation

**Purpose**: Ensure new quantity >= consumed quantity.

**Steps**:
1. Calculate consumed quantity:
   ```python
   def _get_consumed_quantity(self) -> Decimal:
       """Get total quantity consumed from this purchase."""
       total_consumed = Decimal("0")
       for item in self.purchase.inventory_items:
           for depletion in item.depletions:
               total_consumed += abs(depletion.quantity_depleted)
       return total_consumed
   ```
2. In validation:
   ```python
   def _validate_quantity(self) -> Tuple[bool, str]:
       new_qty = Decimal(self.qty_var.get())
       package_qty = self.purchase.product.package_unit_quantity
       new_total = new_qty * package_qty

       if new_total < self.consumed_qty:
           return False, f"Cannot reduce below {self.consumed_qty} (already consumed)"
       return True, ""
   ```
3. Call `can_edit_purchase()` for server-side validation as backup

**Files**: `src/ui/dialogs/edit_purchase_dialog.py`
**Parallel?**: No (depends on T028)

### Subtask T031 - Preview Changes

**Purpose**: Show impact of edits before saving.

**Steps**:
1. Create preview section:
   ```python
   preview_frame = ctk.CTkFrame(self)
   self.preview_label = ctk.CTkLabel(preview_frame, text="")
   ```
2. Implement `_update_preview()`:
   ```python
   def _update_preview(self):
       try:
           new_qty = Decimal(self.qty_var.get())
           new_price = Decimal(self.price_var.get())
           old_price = self.purchase.unit_price

           changes = []

           # Price change?
           if new_price != old_price:
               changes.append(f"Unit price: ${old_price:.2f} -> ${new_price:.2f}")
               changes.append("FIFO costs will be recalculated")

           # Quantity change?
           old_qty = self.purchase.quantity_purchased
           if new_qty != old_qty:
               changes.append(f"Quantity: {old_qty} -> {new_qty}")
               # Calculate inventory impact
               package_qty = self.purchase.product.package_unit_quantity
               diff = (new_qty - old_qty) * package_qty
               if diff > 0:
                   changes.append(f"+{diff} {self.purchase.product.package_unit} to inventory")
               else:
                   changes.append(f"{diff} {self.purchase.product.package_unit} from inventory")

           if changes:
               self.preview_label.configure(text="\n".join(changes))
           else:
               self.preview_label.configure(text="No changes detected")
       except:
           pass
   ```
3. Bind to field changes

**Files**: `src/ui/dialogs/edit_purchase_dialog.py`
**Parallel?**: No (depends on T028)

### Subtask T032 - Save Handler

**Purpose**: Apply edits via update_purchase().

**Steps**:
1. Implement `_on_save()`:
   ```python
   def _on_save(self):
       # Validate
       valid, error = self._validate()
       if not valid:
           self._show_error(error)
           return

       # Build updates dict
       updates = {}

       new_date = datetime.strptime(self.date_var.get(), "%Y-%m-%d").date()
       if new_date != self.purchase.purchase_date:
           updates["purchase_date"] = new_date

       new_qty = Decimal(self.qty_var.get())
       if new_qty != self.purchase.quantity_purchased:
           updates["quantity_purchased"] = new_qty

       new_price = Decimal(self.price_var.get())
       if new_price != self.purchase.unit_price:
           updates["unit_price"] = new_price

       new_supplier = self.supplier_map[self.supplier_var.get()]
       if new_supplier.id != self.purchase.supplier_id:
           updates["supplier_id"] = new_supplier.id

       new_notes = self.notes_text.get("1.0", "end-1c").strip() or None
       if new_notes != self.purchase.notes:
           updates["notes"] = new_notes

       if not updates:
           self.destroy()
           return

       try:
           PurchaseService().update_purchase(self.purchase_id, updates)
           if self.on_save:
               self.on_save()
           self.destroy()
       except Exception as e:
           self._show_error(f"Failed to save: {str(e)}")
   ```

**Files**: `src/ui/dialogs/edit_purchase_dialog.py`
**Parallel?**: No (integration)

### Subtask T033 - Wire Edit Action

**Purpose**: Connect context menu Edit to dialog.

**Steps**:
1. In `PurchasesTab`, implement `_on_edit()`:
   ```python
   def _on_edit(self):
       selected = self.tree.selection()
       if not selected:
           return

       purchase_id = int(self.tree.item(selected[0])["values"][0])  # Assuming ID is stored

       from src.ui.dialogs.edit_purchase_dialog import EditPurchaseDialog
       dialog = EditPurchaseDialog(self, purchase_id, on_save=self._on_filter_change)
       dialog.focus()
   ```
2. Also bind double-click to edit:
   ```python
   self.tree.bind("<Double-1>", lambda e: self._on_edit())
   ```

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (integration)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FIFO recalculation complexity | Delegate to update_purchase(); show clear preview |
| User confusion about read-only product | Clear visual indicator + explanation text |
| Consumed quantity race condition | Re-validate on save; show current consumed in dialog |

## Definition of Done Checklist

- [ ] Dialog opens from context menu Edit
- [ ] Product field is read-only with explanation
- [ ] All editable fields pre-fill correctly
- [ ] Quantity validation prevents going below consumed
- [ ] Preview shows impact of changes
- [ ] Save updates purchase and recalculates costs
- [ ] List refreshes after save
- [ ] Double-click opens edit dialog

## Review Guidance

- Test editing purchase with partial consumption
- Verify quantity validation blocks invalid edits
- Check FIFO cost recalculation on price change
- Test editing a fully consumed purchase (should still allow date/notes changes)

## Activity Log

- 2026-01-08T22:30:00Z - system - lane=planned - Prompt created.
- 2026-01-09T03:49:37Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-09T05:03:37Z – unknown – lane=done – Review passed: EditPurchaseDialog with validation, read-only product, update_purchase integration implemented
