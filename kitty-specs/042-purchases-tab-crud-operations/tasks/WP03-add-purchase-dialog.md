---
work_package_id: "WP03"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
title: "Add Purchase Dialog"
phase: "Phase 2 - Core UI"
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

# Work Package Prompt: WP03 - Add Purchase Dialog

## Objectives & Success Criteria

Implement the Add Purchase dialog for primary data entry (User Story 3).

**Success Criteria**:
- Click "Add Purchase" → dialog opens
- Select product → price auto-fills from last purchase
- Select product with preferred supplier → supplier auto-selects
- Fill form → click "Add Purchase" → purchase created + inventory updated
- Validation: future date rejected, zero/negative quantity rejected
- List refreshes after successful save

## Context & Constraints

**Reference Documents**:
- `kitty-specs/042-purchases-tab-crud-operations/research.md` - AdjustmentDialog pattern
- `src/ui/dialogs/adjustment_dialog.py` - Pattern reference

**Key Constraints**:
- Modal dialog (transient + grab_set)
- Quantity allows 1 decimal place
- Date cannot be in the future
- Callback pattern for refresh

## Subtasks & Detailed Guidance

### Subtask T016 - Create AddPurchaseDialog Class Structure

**Purpose**: Establish dialog frame and modal behavior.

**Steps**:
1. Create `src/ui/dialogs/add_purchase_dialog.py`
2. Import dependencies:
   ```python
   import customtkinter as ctk
   from datetime import date
   from decimal import Decimal
   from typing import Optional, Callable
   from src.services.purchase_service import PurchaseService
   from src.services.product_service import ProductService
   from src.services.supplier_service import SupplierService
   ```
3. Create class:
   ```python
   class AddPurchaseDialog(ctk.CTkToplevel):
       def __init__(self, parent, on_save: Optional[Callable] = None):
           super().__init__(parent)
           self.title("Add Purchase")
           self.on_save = on_save

           # Make modal
           self.transient(parent)
           self.grab_set()

           # Size and position
           self.geometry("450x550")
           self._center_on_parent(parent)

           # Load data
           self._load_products()
           self._load_suppliers()

           # Create UI
           self._create_widgets()
           self._layout_widgets()
           self._bind_events()
   ```

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Parallel?**: No (foundation)

### Subtask T017 - Product Dropdown with Type-ahead

**Purpose**: Searchable product selection.

**Steps**:
1. Load products: `ProductService().get_all_products()`
2. Create ComboBox with product names:
   ```python
   self.product_var = ctk.StringVar()
   self.product_combo = ctk.CTkComboBox(
       form_frame,
       variable=self.product_var,
       values=[p.display_name for p in self.products],
       command=self._on_product_selected
   )
   ```
3. Enable type-ahead filtering (if CTkComboBox supports, or use ttk.Combobox)
4. Store product mapping: `self.product_map = {p.display_name: p for p in products}`

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Parallel?**: Yes (independent field)

### Subtask T018 - Date Picker

**Purpose**: Purchase date selection with validation.

**Steps**:
1. Create date entry (default to today):
   ```python
   self.date_var = ctk.StringVar(value=date.today().strftime("%Y-%m-%d"))
   self.date_entry = ctk.CTkEntry(form_frame, textvariable=self.date_var)
   ```
2. Add date picker button (optional - can use tkcalendar if available)
3. Validate in `_validate()`: date <= today

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Parallel?**: Yes (independent field)

### Subtask T019 - Quantity Entry

**Purpose**: Quantity input with 1 decimal place.

**Steps**:
1. Create entry:
   ```python
   self.qty_var = ctk.StringVar(value="1")
   self.qty_entry = ctk.CTkEntry(form_frame, textvariable=self.qty_var)
   ```
2. Validate: must be > 0, allow 1 decimal place
3. Show unit label next to entry (e.g., "packages")

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Parallel?**: Yes (independent field)

### Subtask T020 - Unit Price with Auto-fill

**Purpose**: Price entry with smart defaults.

**Steps**:
1. Create entry:
   ```python
   self.price_var = ctk.StringVar(value="")
   self.price_entry = ctk.CTkEntry(form_frame, textvariable=self.price_var)
   ```
2. In `_on_product_selected()`:
   ```python
   def _on_product_selected(self, product_name: str):
       product = self.product_map.get(product_name)
       if product:
           # Auto-fill price
           last_price = PurchaseService().get_last_price_any_supplier(product.id)
           if last_price:
               self.price_var.set(f"{last_price['unit_price']:.2f}")

           # Auto-fill supplier
           if product.preferred_supplier_id:
               supplier = self.supplier_map.get(product.preferred_supplier_id)
               if supplier:
                   self.supplier_var.set(supplier.name)

       self._update_preview()
   ```

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Parallel?**: Yes (independent field)

### Subtask T021 - Supplier Dropdown

**Purpose**: Supplier selection with preferred default.

**Steps**:
1. Load suppliers: `SupplierService().get_all_suppliers()`
2. Create dropdown:
   ```python
   self.supplier_var = ctk.StringVar()
   self.supplier_combo = ctk.CTkComboBox(
       form_frame,
       variable=self.supplier_var,
       values=[s.name for s in self.suppliers]
   )
   ```
3. Store mapping: `self.supplier_map = {s.name: s for s in suppliers}`

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Parallel?**: Yes (independent field)

### Subtask T022 - Notes Text Area

**Purpose**: Optional notes field.

**Steps**:
1. Create text box:
   ```python
   self.notes_text = ctk.CTkTextbox(form_frame, height=60)
   ```
2. Get value: `self.notes_text.get("1.0", "end-1c").strip() or None`

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Parallel?**: Yes (independent field)

### Subtask T023 - Live Preview

**Purpose**: Show calculated values before save.

**Steps**:
1. Create preview frame at bottom:
   ```python
   preview_frame = ctk.CTkFrame(self)
   self.preview_label = ctk.CTkLabel(preview_frame, text="")
   ```
2. Implement `_update_preview()`:
   ```python
   def _update_preview(self):
       try:
           qty = Decimal(self.qty_var.get() or "0")
           price = Decimal(self.price_var.get() or "0")
           total = qty * price

           product = self.product_map.get(self.product_var.get())
           if product:
               units = qty * product.package_unit_quantity
               self.preview_label.configure(
                   text=f"Total: ${total:.2f}\n"
                        f"Adds {units} {product.package_unit} to inventory"
               )
       except:
           self.preview_label.configure(text="Enter valid values to see preview")
   ```
3. Bind to field changes via trace or KeyRelease

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Parallel?**: No (depends on T017-T022)

### Subtask T024 - Validation and Error Display

**Purpose**: Validate all fields before save.

**Steps**:
1. Implement `_validate() -> Tuple[bool, str]`:
   ```python
   def _validate(self) -> Tuple[bool, str]:
       # Product selected?
       if not self.product_var.get():
           return False, "Please select a product"

       # Date valid?
       try:
           purchase_date = datetime.strptime(self.date_var.get(), "%Y-%m-%d").date()
           if purchase_date > date.today():
               return False, "Purchase date cannot be in the future"
       except ValueError:
           return False, "Invalid date format (use YYYY-MM-DD)"

       # Quantity valid?
       try:
           qty = Decimal(self.qty_var.get())
           if qty <= 0:
               return False, "Quantity must be greater than 0"
       except:
           return False, "Invalid quantity"

       # Price valid?
       try:
           price = Decimal(self.price_var.get())
           if price < 0:
               return False, "Price cannot be negative"
       except:
           return False, "Invalid price"

       # Supplier selected?
       if not self.supplier_var.get():
           return False, "Please select a supplier"

       return True, ""
   ```
2. Show error in preview area with red color

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Parallel?**: No (depends on T017-T022)

### Subtask T025 - Save Handler

**Purpose**: Create purchase and inventory on save.

**Steps**:
1. Implement `_on_save()`:
   ```python
   def _on_save(self):
       valid, error = self._validate()
       if not valid:
           self._show_error(error)
           return

       product = self.product_map[self.product_var.get()]
       supplier = self.supplier_map[self.supplier_var.get()]

       try:
           purchase = PurchaseService().record_purchase(
               product_id=product.id,
               quantity=Decimal(self.qty_var.get()),
               total_cost=Decimal(self.qty_var.get()) * Decimal(self.price_var.get()),
               purchase_date=datetime.strptime(self.date_var.get(), "%Y-%m-%d").date(),
               store=supplier.name,
               notes=self.notes_text.get("1.0", "end-1c").strip() or None
           )

           # Callback to refresh list
           if self.on_save:
               self.on_save()

           self.destroy()
       except Exception as e:
           self._show_error(f"Failed to save: {str(e)}")
   ```
2. Add Save and Cancel buttons:
   ```python
   cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=self.destroy)
   save_btn = ctk.CTkButton(button_frame, text="Add Purchase", command=self._on_save)
   ```

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Parallel?**: No (integration)

### Subtask T026 - Wire Add Button in PurchasesTab

**Purpose**: Connect "Add Purchase" button to dialog.

**Steps**:
1. In `PurchasesTab`, implement `_on_add_purchase()`:
   ```python
   def _on_add_purchase(self):
       from src.ui.dialogs.add_purchase_dialog import AddPurchaseDialog
       dialog = AddPurchaseDialog(self, on_save=self._on_filter_change)
       dialog.focus()
   ```
2. Verify button is wired in `_create_controls()`

**Files**: `src/ui/tabs/purchases_tab.py`
**Parallel?**: No (integration)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Product dropdown slow with many products | Lazy load; limit to recent + search results |
| Date validation edge cases | Use proper datetime parsing; test edge cases |
| Price auto-fill fails silently | Show placeholder text "Enter price" if no history |

## Definition of Done Checklist

- [ ] Dialog opens when clicking "Add Purchase"
- [ ] Product dropdown shows all products
- [ ] Price auto-fills from last purchase
- [ ] Supplier defaults to preferred_supplier
- [ ] Date validates (not future)
- [ ] Quantity validates (> 0, 1 decimal)
- [ ] Price validates (>= 0)
- [ ] Preview shows total and inventory impact
- [ ] Save creates purchase + inventory
- [ ] List refreshes after save
- [ ] Cancel closes without saving

## Review Guidance

- Test with product that has no purchase history (no auto-fill)
- Test with product that has preferred supplier
- Test validation edge cases (future date, zero qty)
- Verify callback triggers list refresh

## Activity Log

- 2026-01-08T22:30:00Z - system - lane=planned - Prompt created.
- 2026-01-09T03:47:01Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-09T03:49:28Z – unknown – lane=for_review – AddPurchaseDialog implemented with all 11 subtasks: form fields, auto-fill price/supplier, validation, live preview, save handler, wired to PurchasesTab. All 45 tests pass.
- 2026-01-09T04:58:34Z – agent – lane=doing – Started review via workflow command
- 2026-01-09T04:58:57Z – unknown – lane=done – Review passed: AddPurchaseDialog with modal, validation, price/supplier auto-fill implemented
