---
work_package_id: "WP04"
subtasks:
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
title: "Material Products Tab"
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

# Work Package Prompt: WP04 - Material Products Tab

## Objectives & Success Criteria

- Implement Material Products tab with grid, filters, and formatting
- Grid displays Material/Name/Inventory/Cost/Supplier columns
- Material filter dropdown works
- Inventory formatted as "4,724 inches", cost as "$0.0016"

**Success**: User Story 3 acceptance scenarios 1-4 pass:
1. Grid shows Material, Product Name, Inventory, Unit Cost, Supplier columns
2. Material dropdown filters products by linked material
3. Inventory displays with quantity + unit formatting
4. Unit cost displays as currency

## Context & Constraints

- **Grid columns per plan.md D3**: material, name, inventory, unit_cost, supplier
- **Inventory format**: `f"{qty:,.1f} {unit}"` (e.g., "4,724.0 inches")
- **Cost format**: `f"${cost:.4f}"` (e.g., "$0.0016") or "-" if None
- **Services**: `material_catalog_service.list_products(material_id)`

**Key Files**:
- Target: `src/ui/materials_tab.py` (MaterialProductsTab class)
- Services: `src/services/material_catalog_service.py`

## Subtasks & Detailed Guidance

### Subtask T030 - Implement products grid columns

- **Purpose**: Configure grid with correct columns
- **Steps**:
  1. Define columns: `("material", "name", "inventory", "unit_cost", "supplier")`
  2. Configure headings: "Material", "Product Name", "Inventory", "Unit Cost", "Supplier"
  3. Set widths: 150, 150, 120, 100, 120
  4. Bind selection and double-click events
- **Files**: `src/ui/materials_tab.py`

### Subtask T031 - Implement _load_all_products

- **Purpose**: Fetch products across all materials
- **Steps**:
  1. Create `_load_all_products()` method
  2. Get all materials (iterate categories -> subcategories -> materials)
  3. For each material: `material_catalog_service.list_products(material.id)`
  4. Build list of product dicts with: id, name, material_name, inventory, cost, supplier
  5. Store in `self.products`
- **Files**: `src/ui/materials_tab.py`
- **Notes**: May be slow with many products; acceptable for expected scale

### Subtask T032 - Implement inventory formatting

- **Purpose**: Format inventory with quantity and unit
- **Steps**:
  1. Get `product.current_inventory` (Decimal)
  2. Get unit from `product.material.base_unit`
  3. Format as `f"{qty:,.1f} {unit}"` (thousand separators, 1 decimal)
  4. Handle None/0 as "0 {unit}"
- **Files**: `src/ui/materials_tab.py`
- **Example**: 4724.5 + "inches" -> "4,724.5 inches"

### Subtask T033 - Implement cost formatting

- **Purpose**: Format unit cost as currency
- **Steps**:
  1. Get `product.weighted_avg_cost` (Decimal or None)
  2. If None: display "-"
  3. Else: format as `f"${cost:.4f}"` (4 decimal places)
- **Files**: `src/ui/materials_tab.py`
- **Example**: 0.00163 -> "$0.0016"

### Subtask T034 - Implement products _update_display

- **Purpose**: Apply filters and populate grid
- **Steps**:
  1. Clear existing grid items
  2. Call `_apply_filters()` to get filtered products
  3. For each product, format and insert row:
     - material: product.material.name
     - name: product.display_name
     - inventory: formatted string
     - unit_cost: formatted string
     - supplier: product.supplier.name or "-"
  4. Use product.id as row iid
  5. Update status bar
- **Files**: `src/ui/materials_tab.py`

### Subtask T035 - Implement Material filter dropdown

- **Purpose**: Filter products by linked material
- **Steps**:
  1. Create `_load_material_dropdown()` method
  2. Build list of all material names
  3. Add "All Materials" option at start
  4. Create `CTkOptionMenu` with these values
  5. Create `_material_map: Dict[str, int]` mapping name to ID
  6. Implement `_on_material_filter_change()` to trigger update
  7. In `_apply_filters()`, filter by selected material
- **Files**: `src/ui/materials_tab.py`

### Subtask T036 - Implement product search filter (Parallel)

- **Purpose**: Filter products by name
- **Steps**:
  1. Add search entry in filter frame
  2. Bind `<KeyRelease>` to `_on_search()`
  3. In `_apply_filters()`, filter by normalized search text
  4. Copy `normalize_for_search()` if not already present
- **Files**: `src/ui/materials_tab.py`
- **Parallel?**: Yes (independent of material filter)

### Subtask T037 - Implement products Clear button

- **Purpose**: Reset all filters
- **Steps**:
  1. Add Clear button in filter frame
  2. Implement `_clear_filters()`:
     - Clear search entry
     - Reset material filter to "All Materials"
  3. Call `_update_display()`
- **Files**: `src/ui/materials_tab.py`

### Subtask T038 - Implement products selection and buttons

- **Purpose**: Track selection and manage button states
- **Steps**:
  1. Add state: `selected_product_id: Optional[int]`
  2. Implement `_on_select()` handler
  3. Implement `_on_double_click()` handler
  4. Create action buttons frame with:
     - Add Product (always enabled)
     - Edit (selection-dependent)
     - Record Purchase (selection-dependent)
     - Adjust Inventory (selection-dependent)
  5. Implement `_enable_selection_buttons()`, `_disable_selection_buttons()`
- **Files**: `src/ui/materials_tab.py`
- **Notes**: Purchase and Adjust handlers wired in WP05

## Risks & Mitigations

- **Risk**: Performance loading many products
  - **Mitigation**: ttk.Treeview handles large datasets; same pattern as Ingredients Products
- **Risk**: Missing material or supplier data
  - **Mitigation**: Handle None values gracefully (display "-")

## Definition of Done Checklist

- [ ] T030: Grid displays 5 columns with correct headers
- [ ] T031: All products load across all materials
- [ ] T032: Inventory shows "4,724.5 inches" format
- [ ] T033: Cost shows "$0.0016" format or "-"
- [ ] T034: Grid populates correctly
- [ ] T035: Material dropdown filters products
- [ ] T036: Search filters by product name
- [ ] T037: Clear resets all filters
- [ ] T038: Selection tracked, buttons enable/disable
- [ ] All User Story 3 acceptance scenarios pass

## Review Guidance

- Verify inventory and cost formatting exactly matches spec
- Verify material filter shows only products for selected material
- Verify missing supplier shows "-"
- Verify buttons enable only when product selected

## Activity Log

- 2026-01-11T07:09:48Z - system - lane=planned - Prompt created.
- 2026-01-11T13:55:47Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-11T14:03:40Z – unknown – lane=for_review – Implementation complete: Inventory formatted as '4,724.5 inches', cost formatted as '$0.0016', Adjust Inventory button added. Tests pass (1958/1958).
- 2026-01-11T15:39:37Z – agent – lane=doing – Started review via workflow command
- 2026-01-11T15:39:56Z – unknown – lane=done – Review passed: All 9 subtasks verified. Products grid with inventory/cost formatting, material filter, search, and selection handling.
