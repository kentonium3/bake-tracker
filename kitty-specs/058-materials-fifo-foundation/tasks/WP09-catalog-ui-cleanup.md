---
work_package_id: "WP09"
subtasks:
  - "T036"
  - "T037"
  - "T038"
title: "Catalog UI Cleanup"
phase: "Phase 4 - Polish"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
history:
  - timestamp: "2026-01-18T18:06:18Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 – Catalog UI Cleanup

## Implementation Command

```bash
spec-kitty implement WP09 --base WP02
```

## Objectives & Success Criteria

Remove cost and inventory columns from Materials Catalog view to reflect definition-only display.

**Success Criteria**:
- Catalog shows only: Name, Brand, SKU, Package (qty + unit), Supplier
- No columns for: current_inventory, weighted_avg_cost, inventory_value
- Column layout adjusted appropriately
- No runtime errors from missing fields

## Context & Constraints

**Reference Documents**:
- `kitty-specs/058-materials-fifo-foundation/spec.md` - User Story 4
- `src/ui/materials_tab.py` - Current UI implementation

**Key Constraints**:
- Catalog is for definitions only - no cost/inventory data
- Inventory view will be added in F059 (out of scope here)
- Keep UI simple and clean

## Subtasks & Detailed Guidance

### Subtask T036 – Remove cost/inventory columns from materials_tab.py

**Purpose**: Clean up catalog display to show only definition fields.

**Steps**:
1. Open `src/ui/materials_tab.py`
2. Find the treeview/table configuration for material products
3. Remove columns for:
   - current_inventory (or "Inventory" or "Qty on Hand")
   - weighted_avg_cost (or "Avg Cost" or "Cost")
   - inventory_value (or "Value" or "Total Value")

4. Look for column definitions like:
```python
# REMOVE THESE
columns = {
    # ... keep these ...
    "name": "Name",
    "brand": "Brand",
    "sku": "SKU",
    # ... REMOVE these ...
    "current_inventory": "Inventory",
    "weighted_avg_cost": "Avg Cost",
    "inventory_value": "Value",
}
```

5. Also remove from any row data population:
```python
# REMOVE references to these fields in row data
row = (
    product.name,
    product.brand,
    # REMOVE: product.current_inventory,
    # REMOVE: product.weighted_avg_cost,
    # REMOVE: product.inventory_value,
)
```

**Files**:
- Edit: `src/ui/materials_tab.py`

**Parallel?**: Yes (independent changes)

**Notes**:
- Search for "inventory", "cost", "value" in the file
- The exact column names may vary - check the current implementation

### Subtask T037 – Update column width/layout calculations

**Purpose**: Adjust layout after removing columns.

**Steps**:
1. In `src/ui/materials_tab.py`, find column width definitions
2. If widths are hardcoded, remove entries for deleted columns:
```python
# If widths are defined like this:
column_widths = {
    "name": 200,
    "brand": 100,
    "sku": 100,
    "package": 80,
    "supplier": 120,
    # REMOVE these:
    # "current_inventory": 80,
    # "weighted_avg_cost": 80,
    # "inventory_value": 80,
}
```

3. If using stretch/proportional widths, adjust remaining columns:
```python
# Example: redistribute width
column_widths = {
    "name": 250,      # Wider now
    "brand": 120,     # Wider now
    "sku": 100,
    "package": 100,
    "supplier": 150,  # Wider now
}
```

4. Test that the table displays properly without scrolling issues

**Files**:
- Edit: `src/ui/materials_tab.py`

**Parallel?**: Yes (same file but different concern)

### Subtask T038 – Remove inventory_value from denormalized export service

**Purpose**: Clean up any denormalized export that includes inventory_value.

**Steps**:
1. Check `src/services/denormalized_export_service.py` (if exists)
2. Search for references to MaterialProduct inventory fields:
```bash
grep -n "inventory_value\|current_inventory\|weighted_avg_cost" src/services/*
```

3. If found in denormalized export, remove:
```python
# In denormalized export function for materials
# REMOVE lines like:
# "inventory_value": product.inventory_value,
# "current_inventory": product.current_inventory,
# "weighted_avg_cost": str(product.weighted_avg_cost),
```

4. If the service doesn't export materials or doesn't include these fields, mark as N/A

**Files**:
- Edit: `src/services/denormalized_export_service.py` (if applicable)

**Parallel?**: Yes (different file)

**Notes**:
- This may not be applicable if materials aren't in denormalized export
- Document findings either way

## Test Strategy

Manual testing:
1. Run the application: `python src/main.py`
2. Navigate to Catalog > Materials > Material Products
3. Verify columns displayed: Name, Brand, SKU, Package, Supplier
4. Verify NO columns for: Inventory, Cost, Value
5. Verify table displays properly (no layout issues)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Column index errors | Test after changes to ensure no index out of range |
| Layout issues | Adjust column widths if table looks cramped |
| Missing data errors | Ensure code doesn't reference removed model fields |

## Definition of Done Checklist

- [ ] current_inventory column removed from UI
- [ ] weighted_avg_cost column removed from UI
- [ ] inventory_value column removed from UI
- [ ] Column widths adjusted appropriately
- [ ] No runtime errors when viewing catalog
- [ ] Denormalized export cleaned (if applicable)
- [ ] Manual UI test passed

## Review Guidance

**Key acceptance checkpoints**:
1. Launch app and navigate to Materials > Material Products
2. Verify only these columns visible: Name, Brand, SKU, Package info, Supplier
3. Verify no "Inventory", "Cost", "Value" columns
4. Verify table layout looks reasonable
5. Try adding/editing a product - should work without errors

## Activity Log

- 2026-01-18T18:06:18Z – system – lane=planned – Prompt created.
