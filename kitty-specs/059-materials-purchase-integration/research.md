# F059 Research: Materials Purchase Integration

**Feature**: 059-materials-purchase-integration
**Created**: 2026-01-18
**Purpose**: Pattern discovery for UI implementation

## Executive Summary

This research analyzed existing patterns in the Bake Tracker codebase to inform F059 implementation. Key findings:

1. **Purchase Form**: Extend `AddPurchaseDialog` with product type selector; F057 provisional pattern already exists
2. **Inventory Display**: Use `ttk.Treeview` pattern from `inventory_tab.py` with cascading filters
3. **Dialogs**: Follow `CTkToplevel` modal pattern with validation feedback and centering
4. **CLI**: Extend `import_export_cli.py` argparse structure; use `CLIFKResolver` prompt pattern
5. **MaterialUnit UI**: Gap identified - base_unit_type not displayed; F059 adds this

---

## 1. Purchase Form Patterns

### Source File
`/Users/kentgale/Vaults-repos/bake-tracker/src/ui/dialogs/add_purchase_dialog.py`

### Key Patterns to Reuse

**Form Structure:**
```
CTkToplevel (500x600px, modal)
├── title_label
├── form_frame (grid layout)
│   ├── Product dropdown (CTkComboBox)
│   ├── Date entry (CTkEntry with YYYY-MM-DD)
│   ├── Quantity entry (CTkEntry)
│   ├── Price entry (CTkEntry)
│   ├── Supplier dropdown (CTkComboBox)
│   └── Notes (CTkTextbox)
├── preview_frame (live calculations)
├── error_label (validation feedback)
└── button_frame (Cancel | Save)
```

**Calculated Fields Pattern:**
- Use `StringVar.trace_add("write", callback)` for real-time updates
- Display in separate preview frame with color-coded feedback:
  - Gray: Awaiting input
  - Green: Valid values
  - Orange: Warning
  - Red: Error

**Validation Pattern:**
- Validation on save only (not real-time button enable/disable)
- Returns `(is_valid: bool, error_message: str)`
- Error shown in red label via `_show_error()`

**F057 Provisional Product Pattern (Already Exists!):**
- Lines 545-970 implement inline provisional product creation
- Triggered when search text ≥3 chars with no matches
- Collapsible form with cascading ingredient selection (L0→L1→L2)
- Creates provisional product and auto-selects it

### Decision: Product Type Selector

**Approach**: Add radio buttons at top of form that show/hide field groups

```python
# Product Type Selection (always visible)
self.product_type_var = ctk.StringVar(value="food")
ctk.CTkRadioButton(form_frame, text="Food", variable=self.product_type_var,
                   value="food", command=self._on_product_type_change)
ctk.CTkRadioButton(form_frame, text="Material", variable=self.product_type_var,
                   value="material", command=self._on_product_type_change)

def _on_product_type_change(self):
    if self.product_type_var.get() == "material":
        self._show_material_fields()
        self._hide_food_fields()
    else:
        self._show_food_fields()
        self._hide_material_fields()
```

---

## 2. Inventory Display Patterns

### Source Files
- `/Users/kentgale/Vaults-repos/bake-tracker/src/ui/inventory_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/src/ui/products_tab.py`

### Key Patterns to Reuse

**Table Structure (ttk.Treeview):**
```python
columns = ("l0", "l1", "l2", "product", "brand", "qty_remaining", "purchased")
tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")

# Column configuration with sortable headers
tree.heading("product", text="Product", anchor="w", command=lambda: self._sort_tree("product"))
tree.column("product", width=200, minwidth=150)
```

**Sorting Pattern:**
- Click header to sort, click again to toggle direction
- Header text shows indicator: `"Product ^"` or `"Product v"`
- Case-insensitive string comparison

**Cascading Filters (L0→L1→L2):**
```python
# L0 always active
self.l0_filter_dropdown = ctk.CTkOptionMenu(command=self._on_l0_filter_change)

# L1 disabled until L0 selected
self.l1_filter_dropdown = ctk.CTkOptionMenu(state="disabled", command=self._on_l1_filter_change)

# Re-entry guard to prevent recursive updates
def _on_l0_filter_change(self, value):
    if self._updating_filters:
        return
    self._updating_filters = True
    try:
        # Update L1 options, reset L2
    finally:
        self._updating_filters = False
```

**Action Buttons:**
- Double-click row → Edit dialog
- Selection tracking for "Adjust" button
- Context menu (right-click) for Edit/Hide/Delete

**Status Label:**
```python
self.count_label.configure(text=f"{visible_count} items ({hidden_count} hidden)")
```

### Decision: Materials Inventory Columns

| Column | Width | Source |
|--------|-------|--------|
| Product Name | 200 | MaterialProduct.name |
| Brand | 120 | MaterialProduct.brand |
| Purchased | 100 | MaterialInventoryItem.purchased_at |
| Qty Purchased | 120 | quantity_purchased + unit |
| Qty Remaining | 120 | quantity_remaining + unit |
| Cost/Unit | 100 | cost_per_unit formatted |
| Total Value | 100 | remaining × cost |
| Actions | 80 | Adjust button |

---

## 3. Dialog Patterns (CTkToplevel)

### Source Files
- `/Users/kentgale/Vaults-repos/bake-tracker/src/ui/widgets/dialogs.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/src/ui/dialogs/` (multiple)

### Key Patterns to Reuse

**Modal Setup (CRITICAL ORDER):**
```python
self.transient(parent)  # 1. Stay on top of parent
self.grab_set()         # 2. Block interaction with other windows
self.wait_visibility()  # 3. Wait for window to be visible
self.focus_force()      # 4. Force focus
self.bind("<Escape>", lambda e: self._on_cancel())  # 5. Escape to close
```

**Button Frame:**
```python
button_frame = ctk.CTkFrame(self, fg_color="transparent")
button_frame.pack(fill="x", padx=20, pady=20)

cancel_btn = ctk.CTkButton(button_frame, text="Cancel", fg_color="gray", command=self._on_cancel)
cancel_btn.pack(side="left", padx=5)

save_btn = ctk.CTkButton(button_frame, text="Save", command=self._on_save)
save_btn.pack(side="right", padx=5)
```

**Validation Feedback Colors:**
- Red (`"red"`): Error
- Orange (`"orange"`): Warning
- Gray (`("gray10", "gray90")`): Normal/inactive
- Green (`"#00AA00"`): Success

**Center on Parent:**
```python
def _center_on_parent(self, parent):
    parent.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
    self.geometry(f"+{max(0, x)}+{max(0, y)}")
```

### Decision: Adjustment Dialog Structure

**For "each" materials (discrete):**
```
Dialog (450x350px)
├── Current State Display
│   ├── "Current remaining: 50 bags"
│   ├── "Original quantity: 100 bags"
│   └── "Purchased: 2026-01-15"
├── Adjustment Controls
│   ├── Radio: ○ Add  ○ Subtract  ○ Set to
│   └── Quantity Entry (integer)
├── Preview (live)
│   └── "New remaining: 75 bags" (color-coded)
├── Notes Entry (optional)
└── Buttons: [Cancel] [Save]
```

**For variable materials (linear_cm, square_cm):**
```
Dialog (450x350px)
├── Current State Display
│   └── "Current: 1524 cm remaining"
├── Percentage Input
│   └── Entry: [50] % remaining
├── Preview (live)
│   └── "New: 762 cm (50% of current)"
├── Notes Entry (optional)
└── Buttons: [Cancel] [Save]
```

---

## 4. CLI Infrastructure

### Source File
`/Users/kentgale/Vaults-repos/bake-tracker/src/utils/import_export_cli.py`

### Key Patterns to Reuse

**Command Structure (argparse):**
```python
parser = argparse.ArgumentParser(description="Bake Tracker CLI")
subparsers = parser.add_subparsers(dest="command")

# Add command
purchase_parser = subparsers.add_parser("purchase", help="Record a purchase")
purchase_parser.add_argument("--type", choices=["food", "material"], required=True)
purchase_parser.add_argument("--name", help="Product name")
purchase_parser.add_argument("--qty", type=float, help="Quantity")
purchase_parser.add_argument("--cost", type=float, help="Total cost")
```

**Interactive Prompts (CLIFKResolver pattern):**
```python
def _prompt_for_material_type(self) -> int:
    print("\nMaterial not found. Create provisional?")
    print("Available material types:")
    for i, mat in enumerate(self.materials, 1):
        print(f"  [{i}] {mat['name']} ({mat['base_unit_type']})")

    while True:
        choice = input("\nEnter number (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            return None
        try:
            idx = int(choice)
            if 1 <= idx <= len(self.materials):
                return self.materials[idx - 1]['id']
        except ValueError:
            pass
        print("Invalid choice. Try again.")
```

**Output Pattern:**
```python
def _report_success(self, purchase):
    print(f"\n✓ Purchase recorded successfully")
    print(f"  Product: {purchase['product_name']}")
    print(f"  Quantity: {purchase['quantity']} {purchase['unit']}")
    print(f"  Total: ${purchase['total_cost']:.2f}")
    print(f"  Unit cost: ${purchase['unit_cost']:.4f}/{purchase['unit']}")
```

### Decision: CLI Command Structure

```bash
# Record material purchase (existing product)
bt purchase material --product "Snowflake Bags" --qty 100 --cost 25.00

# Record material purchase (provisional product)
bt purchase material --name "New Bag Style" --qty 100 --cost 25.00
# → Prompts for material type if product not found
# → Creates provisional MaterialProduct
# → Records purchase and inventory
```

---

## 5. MaterialUnit UI Patterns

### Source File
`/Users/kentgale/Vaults-repos/bake-tracker/src/ui/materials_tab.py` (lines 1304-1562)

### Current Implementation

**Form Fields:**
- Material (CTkComboBox) - dropdown from hierarchy
- Name (CTkEntry/Label) - editable on add, read-only on edit
- Qty/Unit (CTkEntry) - base units consumed per unit
- Description (CTkEntry) - optional

**Gap Identified:**
The material's `base_unit_type` is loaded but NOT displayed to users. Users must know their material's unit type to enter meaningful quantities.

### Decision: Enhanced MaterialUnit UI (FR-019 to FR-022)

**Add after Material selection:**
```python
def _on_material_selected(self, choice):
    material = self._materials.get(choice)
    if material:
        base_unit = material["base_unit"]
        self.unit_type_label.configure(
            text=f"Unit type: {base_unit} (inherited from {choice})"
        )

        # Update quantity label dynamically
        self.qty_label.configure(text=f"Quantity per unit (in {base_unit}):")

        # For "each" materials, lock quantity to 1
        if base_unit == "each":
            self.qty_entry.configure(state="disabled")
            self.qty_var.set("1")
            self.preview_label.configure(
                text=f"This unit will consume 1 {choice}"
            )
        else:
            self.qty_entry.configure(state="normal")
            self._update_preview()
```

---

## 6. Service Integration Points

### Existing Services to Use

| Service | Location | Purpose |
|---------|----------|---------|
| MaterialInventoryService | `src/services/material_inventory_service.py` | FIFO inventory operations |
| MaterialPurchaseService | `src/services/material_purchase_service.py` | Purchase recording |
| MaterialCatalogService | `src/services/material_catalog_service.py` | Product CRUD |
| MaterialUnitService | `src/services/material_unit_service.py` | Unit management |

### Session Pattern (CRITICAL)
From CLAUDE.md - services accept optional `session` parameter:
```python
def some_function(..., session=None):
    if session is not None:
        return _impl(..., session)
    with session_scope() as session:
        return _impl(..., session)
```

---

## 7. File Changes Summary

### Files to Modify

| File | Changes |
|------|---------|
| `src/ui/dialogs/add_purchase_dialog.py` | Add product type selector, material fields |
| `src/ui/tabs/purchases_tab.py` | Add Materials inventory section/tab |
| `src/ui/materials_tab.py` | Enhance MaterialUnit form (unit type display) |
| `src/utils/import_export_cli.py` | Add material purchase command |
| `src/services/material_catalog_service.py` | Add provisional product support |

### Files to Create

| File | Purpose |
|------|---------|
| `src/ui/dialogs/material_adjustment_dialog.py` | Manual adjustment dialog |
| `src/ui/widgets/material_inventory_table.py` | (Optional) Reusable table widget |

---

## 8. Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Form complexity with conditional fields | Clear visual grouping, complete hide of irrelevant fields |
| FIFO order confusion (display vs consumption) | Clear labeling: "Sorted by date (newest first)" |
| Provisional product workflow confusion | Clear indicator icon + "Needs enrichment" badge |
| Unit type inheritance unclear | Prominent display + preview text |

---

## Appendix: Key Code References

### Add Purchase Dialog
- File: `src/ui/dialogs/add_purchase_dialog.py`
- Product dropdown: lines 145-158
- Validation: lines 447-493
- Live preview: lines 398-445
- Provisional creation: lines 545-970

### Inventory Tab
- File: `src/ui/inventory_tab.py`
- Treeview setup: grid_container pattern
- Sorting: `_sort_tree()` method
- Cascading filters: L0/L1/L2 pattern

### Materials Tab
- File: `src/ui/materials_tab.py`
- MaterialUnitFormDialog: lines 1304-1562
- MaterialsCatalogTab: lines 1564-2121
- MaterialProductsTab: lines 2122-2630

### CLI
- File: `src/utils/import_export_cli.py`
- CLIFKResolver: lines 1568-1762
- Export purchases: lines 597-647
