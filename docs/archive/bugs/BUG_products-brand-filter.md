# Bug Fix: Add Brand Filter to Products Tab

**Branch**: `bugfix/products-brand-filter`  
**Priority**: Low (nice to have, may already exist)  
**Estimated Effort**: 15-30 minutes

## Context

Products tab needs a Brand dropdown filter to help users find products from specific brands quickly.

**Note**: Based on earlier code analysis, this filter may already exist in the codebase. This task is to verify it exists and works correctly, or add it if missing.

## Expected Behavior

**Filter location**: In the filter controls row, alongside existing filters  
**Functionality**: Filter products list to show only selected brand  
**Dropdown values**: "All Brands" + distinct brands from products in database

## Implementation Tasks

### Task 1: Check if Brand Filter Exists
**File**: `src/ui/products_tab.py`

1. Search for brand filter dropdown
2. Check if it's already implemented
3. If exists: Verify it works correctly
4. If missing: Implement it

### Task 2: Add Brand Filter (If Missing)
**File**: `src/ui/products_tab.py`

```python
# In _create_filters or similar method

# Brand filter
brand_label = ctk.CTkLabel(filter_frame, text="Brand:")
brand_label.pack(side="left", padx=(15, 2), pady=5)

self.brand_var = ctk.StringVar(value="All Brands")
self.brand_dropdown = ctk.CTkOptionMenu(
    filter_frame,
    variable=self.brand_var,
    values=["All Brands"],  # Populated dynamically
    command=self._on_filter_change,
    width=150,
)
self.brand_dropdown.pack(side="left", padx=5, pady=5)
```

### Task 3: Populate Brand Filter Dynamically
**File**: `src/ui/products_tab.py`

```python
def _load_filter_data(self):
    """Load filter dropdown data from products."""
    with session_scope() as session:
        # Load products
        self.products = product_catalog_service.get_all_products(session)
        
        # Get distinct brands
        brands = set()
        for product in self.products:
            if product.brand:
                brands.add(product.brand)
        
        self.brands = sorted(list(brands))
        
        # Update dropdown
        self.brand_dropdown.configure(
            values=["All Brands"] + self.brands
        )
```

### Task 4: Apply Brand Filter
**File**: `src/ui/products_tab.py`

```python
def _apply_filters(self):
    """Apply current filters to products list."""
    filtered = self.products
    
    # Ingredient filter (existing)
    if self.ingredient_var.get() != "All":
        # ... existing logic
    
    # Category filter (existing)
    if self.category_var.get() != "All":
        # ... existing logic
    
    # Brand filter
    if self.brand_var.get() != "All Brands":
        brand_name = self.brand_var.get()
        filtered = [p for p in filtered if p.brand == brand_name]
    
    # Supplier filter (existing)
    if self.supplier_var.get() != "All":
        # ... existing logic
    
    # Search filter (existing)
    search_term = self.search_entry.get().strip().lower()
    if search_term:
        # ... existing logic
    
    self.filtered_products = filtered
    self._populate_grid()
```

## Testing Checklist

### If Filter Already Exists
- [ ] Brand filter dropdown is visible
- [ ] Dropdown shows "All Brands" + actual brands
- [ ] Selecting brand filters products correctly
- [ ] "All Brands" shows all products
- [ ] Filter combines with other filters (ingredient, category, supplier)
- [ ] Dropdown updates when products change

### If Filter Needs to be Added
- [ ] Brand filter dropdown added to filter row
- [ ] Dropdown positioned appropriately (good spacing)
- [ ] Dropdown shows "All Brands" + distinct brands from database
- [ ] Selecting brand filters products correctly
- [ ] "All Brands" shows all products
- [ ] Filter combines with other filters correctly
- [ ] Dropdown updates when new products added
- [ ] Clear/Refresh buttons reset brand filter

### General
- [ ] Filter row layout looks clean (not crowded)
- [ ] All filters work together (AND logic)
- [ ] Performance is good even with many products
- [ ] No errors in console

## Success Criteria

1. **Filter Exists**: Brand filter dropdown is present and visible
2. **Filter Works**: Correctly filters products by brand
3. **Dynamic Data**: Dropdown populated from actual product brands
4. **Combined Filtering**: Works with other filters (ingredient, category, supplier, search)
5. **Good UX**: Easy to find and use

## Implementation Notes

### Expected Filter Row Layout

```
[Add Product] [Manage Suppliers] [Refresh]

Ingredient: [All ▼]  Category: [All ▼]  Brand: [All Brands ▼]  Supplier: [All ▼]

Search: [_______________]  Show Hidden: [☐]
```

### Filter Pattern (Existing in Codebase)

```python
# All filters call same handler
def _on_filter_change(self, value=None):
    """Handle any filter change."""
    self._apply_filters()

# Apply all filters together
def _apply_filters(self):
    filtered = self.products
    
    # Apply each active filter
    # ... ingredient filter
    # ... category filter
    # ... brand filter (add this)
    # ... supplier filter
    # ... search filter
    
    self.filtered_products = filtered
    self._populate_grid()
```

## Related Files

**Primary File**:
- `src/ui/products_tab.py` - Add/verify brand filter

**Reference**:
- `src/ui/inventory_tab.py` - Has brand filter (can copy pattern)

## Git Workflow

```bash
git checkout -b bugfix/products-brand-filter

# If adding filter
git commit -m "feat: add brand filter dropdown to products tab"

# If fixing existing filter
git commit -m "fix: brand filter functionality in products tab"

git push
```

---

**Quick Win**: Simple filter addition (or verification) that improves product findability.
