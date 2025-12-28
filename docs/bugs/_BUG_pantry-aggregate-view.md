# Bug Fix: Fix Aggregate View in My Pantry Tab

**Branch**: `bugfix/pantry-aggregate-view`  
**Priority**: Medium (feature is broken, needs fixing)  
**Estimated Effort**: 1 hour

## Context

My Pantry tab has a View Mode toggle (Detail/Aggregate) but Aggregate view is currently broken. 

**Intended behavior**:
- **Detail View**: One row per inventory lot (multiple rows for same product bought at different times)
- **Aggregate View**: One row per product (sum all lots of same product)

## Current State vs Expected

### Detail View (Working)
Shows individual lots:
```
Ingredient | Product               | Brand      | Qty Remaining | Purchased
-----------+-----------------------+------------+---------------+------------
Chocolate  | Dark Choc Chips       | Ghirardelli| 1.5 jars (42oz)| 2024-11-15
Chocolate  | Dark Choc Chips       | Ghirardelli| 1.0 jar (28oz) | 2024-12-01
Chocolate  | Dark Choc Chips       | Ghirardelli| 1.0 jar (28oz) | 2024-12-10
```

### Aggregate View (Should Show)
Combines lots of same product:
```
Ingredient | Product               | Brand      | Qty Remaining
-----------+-----------------------+------------+---------------
Chocolate  | Dark Choc Chips       | Ghirardelli| 3.5 jars (98oz)
```

**Note**: Purchased column should be hidden in Aggregate view (not meaningful for aggregated data)

## Implementation Requirements

### 1. Aggregate Data by Product
**File**: `src/ui/inventory_tab.py`

When Aggregate view is selected:
1. Group inventory items by product (same product_id)
2. Sum `quantity_remaining` for each product group
3. Calculate total amount in package units
4. Display one row per unique product

### 2. Hide Purchased Column in Aggregate View
**File**: `src/ui/inventory_tab.py`

**Columns in Detail View**:
- Ingredient, Product, Brand, Qty Remaining, Purchased

**Columns in Aggregate View**:
- Ingredient, Product, Brand, Qty Remaining (NO Purchased column)

### 3. View Mode Toggle Behavior
**File**: `src/ui/inventory_tab.py`

**Current**: View mode dropdown with "Detail" and "Aggregate" options (already exists)

**Should do**:
- Switching to Aggregate → Groups data and hides Purchased column
- Switching to Detail → Shows individual lots with Purchased column
- Filters should work in both views
- Sorting should work in both views

## Implementation Tasks

### Task 1: Implement Aggregation Logic
**File**: `src/ui/inventory_tab.py`

Add method to aggregate inventory items by product:

```python
def _aggregate_by_product(self, items):
    """
    Aggregate inventory items by product.
    
    Groups items by product and sums quantities.
    
    Args:
        items: List of InventoryItem objects
        
    Returns:
        List of aggregated data dicts
    """
    from collections import defaultdict
    from decimal import Decimal
    
    # Group by product
    product_groups = defaultdict(list)
    for item in items:
        if item.product:
            product_groups[item.product.id].append(item)
    
    # Aggregate each group
    aggregated = []
    for product_id, product_items in product_groups.items():
        # Use first item as template
        first = product_items[0]
        product = first.product
        
        # Sum quantities
        total_qty = sum(
            item.quantity_remaining for item in product_items
        )
        
        # Calculate total in package units
        total_amount = total_qty * product.package_unit_quantity
        
        # Build aggregated row data
        aggregated.append({
            'product_id': product_id,
            'ingredient': product.ingredient.name if product.ingredient else "Unknown",
            'product': product.product_name,
            'brand': product.brand or '',
            'qty_remaining': total_qty,
            'qty_display': format_qty_remaining(total_qty, product),
            'package_type': product.package_type,
            'package_unit': product.package_unit,
        })
    
    # Sort by ingredient, then product
    aggregated.sort(key=lambda x: (x['ingredient'].lower(), x['product'].lower()))
    
    return aggregated
```

### Task 2: Update Tree Population for Aggregate View
**File**: `src/ui/inventory_tab.py`

Modify `_populate_tree()` to handle both views:

```python
def _populate_tree(self):
    """Populate tree with inventory items based on current view mode."""
    # Clear existing items
    for item in self.tree.get_children():
        self.tree.delete(item)
    
    if self.view_mode == "aggregate":
        self._populate_aggregate_view()
    else:
        self._populate_detail_view()


def _populate_detail_view(self):
    """Populate tree with individual inventory lots."""
    # Configure columns for detail view
    self.tree.configure(columns=('ingredient', 'product', 'brand', 'qty_remaining', 'purchased'))
    
    # Set headings
    self.tree.heading('ingredient', text='Ingredient')
    self.tree.heading('product', text='Product')
    self.tree.heading('brand', text='Brand')
    self.tree.heading('qty_remaining', text='Qty Remaining')
    self.tree.heading('purchased', text='Purchased')
    
    # Set column widths
    self.tree.column('ingredient', width=150)
    self.tree.column('product', width=200)
    self.tree.column('brand', width=120)
    self.tree.column('qty_remaining', width=150)
    self.tree.column('purchased', width=100)
    
    # Populate rows
    for item in self.filtered_items:
        product = item.product
        ingredient_name = product.ingredient.name if product and product.ingredient else "Unknown"
        
        qty_display = format_qty_remaining(item.quantity_remaining, product)
        purchased_display = item.purchase_date.strftime('%Y-%m-%d') if item.purchase_date else ''
        
        self.tree.insert('', 'end', values=(
            ingredient_name,
            product.product_name if product else '',
            product.brand if product else '',
            qty_display,
            purchased_display
        ))


def _populate_aggregate_view(self):
    """Populate tree with aggregated product totals."""
    # Configure columns for aggregate view (NO purchased column)
    self.tree.configure(columns=('ingredient', 'product', 'brand', 'qty_remaining'))
    
    # Set headings
    self.tree.heading('ingredient', text='Ingredient')
    self.tree.heading('product', text='Product')
    self.tree.heading('brand', text='Brand')
    self.tree.heading('qty_remaining', text='Qty Remaining')
    
    # Set column widths (adjust since purchased column is gone)
    self.tree.column('ingredient', width=180)
    self.tree.column('product', width=220)
    self.tree.column('brand', width=140)
    self.tree.column('qty_remaining', width=180)
    
    # Aggregate data
    aggregated = self._aggregate_by_product(self.filtered_items)
    
    # Populate rows
    for item in aggregated:
        self.tree.insert('', 'end', values=(
            item['ingredient'],
            item['product'],
            item['brand'],
            item['qty_display']
        ))
```

### Task 3: Update View Mode Change Handler
**File**: `src/ui/inventory_tab.py`

```python
def _on_view_mode_change(self, value):
    """Handle view mode dropdown change."""
    # Update view mode
    if value == "Aggregate":
        self.view_mode = "aggregate"
    else:
        self.view_mode = "detail"
    
    # Repopulate tree with new view
    self._populate_tree()
```

### Task 4: Ensure Filters Work in Both Views
**File**: `src/ui/inventory_tab.py`

Filters should apply to `self.filtered_items` before aggregation:

```python
def _apply_filters(self):
    """Apply filters to inventory items."""
    filtered = self.inventory_items
    
    # Apply ingredient filter
    if self.ingredient_var.get() != "All Ingredients":
        # ... filter logic
    
    # Apply brand filter
    if self.brand_var.get() != "All Brands":
        # ... filter logic
    
    # Apply category filter
    # Apply search filter
    
    self.filtered_items = filtered
    
    # Repopulate tree (handles both detail and aggregate)
    self._populate_tree()
```

## Testing Checklist

### Detail View
- [ ] Shows individual lots (one row per purchase)
- [ ] Purchased column visible
- [ ] All 5 columns display correctly
- [ ] Same product bought at different times shows multiple rows
- [ ] Quantities are per-lot, not aggregated

### Aggregate View
- [ ] Shows one row per product (lots combined)
- [ ] Purchased column hidden
- [ ] Only 4 columns display
- [ ] Quantities are summed correctly
- [ ] Same product from different purchases shows as one row

### View Mode Toggle
- [ ] Switching Detail → Aggregate works correctly
- [ ] Switching Aggregate → Detail works correctly
- [ ] Columns reconfigure properly on switch
- [ ] Data updates correctly on switch
- [ ] No errors during switch

### Filters in Aggregate View
- [ ] Ingredient filter works
- [ ] Brand filter works
- [ ] Category filter works
- [ ] Search filter works
- [ ] Filters combine correctly (AND logic)
- [ ] Clear filters works

### Data Accuracy
- [ ] Spot check: Aggregate quantities = sum of detail quantities
- [ ] Format: "3.5 jars (98 oz)" style maintained
- [ ] Sorting works in aggregate view
- [ ] Empty states handled (no inventory items)

## Success Criteria

1. **Aggregate Works**: View mode toggle actually aggregates data
2. **Column Visibility**: Purchased column hidden in aggregate, visible in detail
3. **Accurate Sums**: Quantities correctly summed by product
4. **Filters Work**: All filters functional in both views
5. **Smooth Toggle**: Switching views is smooth and error-free
6. **User Validation**: Primary user confirms aggregate view is useful

## Implementation Notes

### Grouping Logic

```python
# Group by product ID
product_groups = defaultdict(list)
for item in items:
    product_groups[item.product.id].append(item)

# Sum quantities per group
for product_id, items in product_groups.items():
    total = sum(item.quantity_remaining for item in items)
```

### Format in Aggregate View

Use same `format_qty_remaining()` function, but with aggregated quantity:

```python
qty_display = format_qty_remaining(total_qty, product)
# Example: "3.5 jars (98 oz)"
```

## Related Files

**Primary File**:
- `src/ui/inventory_tab.py` - All changes here

## Git Workflow

```bash
git checkout -b bugfix/pantry-aggregate-view
git commit -m "feat: implement aggregate view data grouping"
git commit -m "feat: hide purchased column in aggregate view"
git commit -m "fix: ensure filters work in both detail and aggregate views"
git push
```

---

**Fix Broken Feature**: Makes aggregate view actually work as intended for quick pantry overview.
