---
work_package_id: "WP05"
subtasks:
  - "T039"
  - "T040"
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
  - "T049"
title: "Product CRUD & Purchase Recording"
phase: "Phase 3 - Material Products Tab"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-11T07:09:48Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Product CRUD & Purchase Recording

## Objectives & Success Criteria

- Implement product add/edit dialog
- Implement Record Purchase dialog with auto-calculations
- Implement Adjust Inventory dialog

**Success**: User Stories 4 & 5 acceptance scenarios pass:
- US4: Add/Edit product dialogs work correctly
- US5: Record Purchase auto-calculates units and cost, updates inventory

## Context & Constraints

- **Services**:
  - `material_catalog_service.create_product()`, `.update_product()`
  - `material_purchase_service.record_purchase()`, `.adjust_inventory()`
  - `supplier_service.get_all_suppliers()`
- **Auto-calculations**:
  - Total units = packages * package_quantity
  - Unit cost = total_price / total_units
- **Validation**: Required fields must be filled before submit

**Key Files**:
- Target: `src/ui/materials_tab.py` (dialogs and handlers)
- Services: `src/services/material_purchase_service.py`
- Reference: Current `materials_tab.py` dialogs (ProductDialog, PurchaseDialog, AdjustInventoryDialog)

## Subtasks & Detailed Guidance

### Subtask T039 - Create MaterialProductFormDialog

- **Purpose**: Dialog for add/edit material products
- **Steps**:
  1. Create `MaterialProductFormDialog(ctk.CTkToplevel)`
  2. Accept `parent`, `product: Optional[dict]`, `title`, `material_id: Optional[int]`
  3. Form fields:
     - Material dropdown (required, pre-selected if material_id provided)
     - Product Name entry (required)
     - Package Quantity entry (required, numeric)
     - Package Unit entry (defaults to material's base_unit)
     - Supplier dropdown (from supplier_service)
     - SKU entry (optional)
     - Notes entry (optional)
  4. Use modal pattern
- **Files**: `src/ui/materials_tab.py`
- **Reference**: Current `ProductDialog` class

### Subtask T040 - Implement product _populate_form

- **Purpose**: Pre-fill form when editing
- **Steps**:
  1. Create `_populate_form()` method
  2. Set material dropdown to product's material
  3. Set product name (read-only in edit mode)
  4. Set package quantity, unit, supplier, SKU, notes
- **Files**: `src/ui/materials_tab.py`

### Subtask T041 - Implement product _validate_and_save

- **Purpose**: Validate and create/update product
- **Steps**:
  1. Validate material selected
  2. Validate product name not empty
  3. Validate package quantity is positive number
  4. Get supplier_id from dropdown (may be None)
  5. Build result dict
  6. Store in `self.result` and destroy
- **Files**: `src/ui/materials_tab.py`

### Subtask T042 - Wire product add/edit handlers

- **Purpose**: Connect buttons to dialogs
- **Steps**:
  1. In MaterialProductsTab, implement `_add_product()`:
     - Open dialog
     - If result: `material_catalog_service.create_product(...)`
     - Refresh grid, show success
  2. Implement `_edit_product()`:
     - Get product data by ID
     - Open dialog with data
     - If result: `material_catalog_service.update_product(...)`
     - Refresh grid, show success
  3. Wire to Add Product and Edit buttons
- **Files**: `src/ui/materials_tab.py`

### Subtask T043 - Create RecordPurchaseDialog

- **Purpose**: Dialog for recording material purchases
- **Steps**:
  1. Create `RecordPurchaseDialog(ctk.CTkToplevel)`
  2. Accept `parent`, `product: dict` (pre-selected product)
  3. Form fields:
     - Product display (read-only label showing name)
     - Supplier dropdown (required)
     - Purchase Date entry (default today, format YYYY-MM-DD)
     - Packages Purchased entry (required, positive integer)
     - Total Price entry (required, numeric)
     - Notes entry (optional)
  4. Add calculated display fields (updated on input change)
- **Files**: `src/ui/materials_tab.py`
- **Reference**: Current `PurchaseDialog` class

### Subtask T044 - Implement total units calculation

- **Purpose**: Auto-calculate total units from packages
- **Steps**:
  1. Get `package_quantity` from product
  2. Bind `<KeyRelease>` on packages entry
  3. Calculate: `total_units = packages * package_quantity`
  4. Display in read-only label: "Total Units: {total_units:.1f} {unit}"
- **Files**: `src/ui/materials_tab.py`
- **Formula**: FR-019

### Subtask T045 - Implement unit cost calculation

- **Purpose**: Auto-calculate unit cost from total price
- **Steps**:
  1. Bind `<KeyRelease>` on price entry
  2. Calculate: `unit_cost = total_price / total_units` (if total_units > 0)
  3. Display in read-only label: "Unit Cost: ${unit_cost:.4f}"
  4. Handle division by zero (show "-")
- **Files**: `src/ui/materials_tab.py`
- **Formula**: FR-020

### Subtask T046 - Wire _record_purchase handler

- **Purpose**: Connect button to dialog and service
- **Steps**:
  1. In MaterialProductsTab, implement `_record_purchase()`:
     - Get selected product data
     - Open `RecordPurchaseDialog(self, product=data)`
     - If result: call `material_purchase_service.record_purchase()`
       - product_id, supplier_id, purchase_date, packages_purchased, package_price, notes
     - Refresh grid, show success
  2. Wire to Record Purchase button (selection-dependent)
  3. Handle validation errors from service
- **Files**: `src/ui/materials_tab.py`
- **Service**: `material_purchase_service.record_purchase()`

### Subtask T047 - Create AdjustInventoryDialog

- **Purpose**: Dialog for direct inventory adjustment
- **Steps**:
  1. Create `AdjustInventoryDialog(ctk.CTkToplevel)`
  2. Accept `parent`, `product: dict`
  3. Display current inventory (read-only)
  4. Form fields:
     - Mode: radio buttons "Set to value" / "Set to percentage"
     - Value entry (required, numeric)
     - Notes entry (optional)
  5. Use modal pattern
- **Files**: `src/ui/materials_tab.py`
- **Reference**: Current `AdjustInventoryDialog` class

### Subtask T048 - Wire _adjust_inventory handler

- **Purpose**: Connect button to dialog and service
- **Steps**:
  1. In MaterialProductsTab, implement `_adjust_inventory()`:
     - Get selected product data
     - Open `AdjustInventoryDialog(self, product=data)`
     - If result: call `material_purchase_service.adjust_inventory()`
       - If mode="set": pass `new_quantity=value`
       - If mode="percentage": pass `percentage=value`
     - Refresh grid, show success
  2. Wire to Adjust Inventory button (selection-dependent)
- **Files**: `src/ui/materials_tab.py`
- **Service**: `material_purchase_service.adjust_inventory()`

### Subtask T049 - Implement purchase/adjust button states

- **Purpose**: Enable buttons only when product selected
- **Steps**:
  1. In `_enable_selection_buttons()`: enable Edit, Record Purchase, Adjust Inventory
  2. In `_disable_selection_buttons()`: disable all three
  3. Buttons start disabled
  4. Selection triggers enable, deselection triggers disable
- **Files**: `src/ui/materials_tab.py`

## Risks & Mitigations

- **Risk**: Purchase validation fails
  - **Mitigation**: Show error message, keep dialog open for correction
- **Risk**: Division by zero in unit cost calculation
  - **Mitigation**: Guard with `if total_units > 0` else show "-"

## Definition of Done Checklist

- [ ] T039: Product dialog opens with all fields
- [ ] T040: Edit mode pre-populates correctly
- [ ] T041: Validation prevents invalid saves
- [ ] T042: Add/Edit wired and working
- [ ] T043: Purchase dialog opens with product info
- [ ] T044: Total units calculates in real-time
- [ ] T045: Unit cost calculates in real-time
- [ ] T046: Record Purchase saves and updates inventory
- [ ] T047: Adjust dialog shows current inventory
- [ ] T048: Adjust saves correctly (set or percentage)
- [ ] T049: Buttons enable only with selection
- [ ] All User Story 4 & 5 acceptance scenarios pass

## Review Guidance

- Verify auto-calculations update as user types
- Verify purchase date defaults to today
- Verify inventory updates after purchase record
- Verify percentage adjustment works correctly

## Activity Log

- 2026-01-11T07:09:48Z - system - lane=planned - Prompt created.
- 2026-01-11T14:03:54Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-11T14:13:11Z – unknown – lane=for_review – Implementation complete: MaterialProductFormDialog, RecordPurchaseDialog, AdjustInventoryDialog with auto-calculations. All handlers wired. Tests pass (1958/1958).
- 2026-01-11T15:40:02Z – agent – lane=doing – Started review via workflow command
- 2026-01-11T15:40:27Z – unknown – lane=done – Review passed: All 11 subtasks verified. Product dialogs with auto-calculations, purchase recording, and inventory adjustment.
