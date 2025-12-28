# Bug Fix: Add Filters and Sorting to My Pantry Tab

**Branch**: `bugfix/pantry-filters-and-sorting`  
**Priority**: Medium (usability improvement)  
**Estimated Effort**: 45 minutes

## Context

My Pantry tab needs better filtering and sorting capabilities to help users find inventory items quickly, especially as the pantry grows.

## Changes Required

### 1. Default Alphabetical Sort by Ingredient
**File**: `src/ui/inventory_tab.py`

**Current**: Items sorted by... (need to check current behavior)  
**New**: Items sorted alphabetically by Ingredient column by default

**Implementation**:
- When populating tree, sort inventory items by `product.ingredient.name`
- Or configure Treeview to allow column-based sorting
- Ingredient column should be primary sort

### 2. Add Ingredient Dropdown Filter
**File**: `src/ui/inventory_tab.py`

**New filter dropdown**: Ingredient

**Implementation**:
```python
# In _create_controls or similar method
ingredient_label = ctk.CTkLabel(controls_frame, text="Ingredient:")
ingredient_label.grid(row=0, column=N, padx=(15, 5), pady=5)

self.ingredient_var = ctk.StringVar(value="All Ingredients")
self.ingredient_dropdown = ctk.CTkOptionMenu(
    controls_frame,
    variable=self.ingredient_var,
    values=["All Ingredients"],  # Populated dynamically
    command=self._on_ingredient_filter_change,
    width=180,
)
self.ingredient_dropdown.grid(row=0, column=N+1, padx=5, pady=5)
```

**Populate dynamically**:
```python
def _load_filter_data(self):
    """Load filter dropdown data from inventory items."""
    # Get distinct ingredients from current inventory
    ingredients = set()
    for item in self.inventory_items:
        if item.product and item.product.ingredient:
            ingredients.add(item.product.ingredient.name)
    
    self.ingredients = sorted(list(ingredients))
    self.ingredient_dropdown.configure(
        values=["All Ingredients"] + self.ingredients
    )
```

**Filter logic**:
```python
def _on_ingredient_filter_change(self, value):
    """Handle ingredient filter change."""
    self._apply_filters()

def _apply_filters(self):
    """Apply all filters to inventory items."""
    filtered = self.inventory_items
    
    # Ingredient filter
    if self.ingredient_var.get() != "All Ingredients":
        ingredient_name = self.ingredient_var.get()
        filtered = [
            item for item in filtered
            if item.product and item.product.ingredient 
            and item.product.ingredient.name == ingredient_name
        ]
    
    # Category filter (existing)
    if self.category_var.get() != "All Categories":
        # ... existing category filter logic
    
    # Brand filter (see #3 below)
    if self.brand_var.get() != "All Brands":
        # ... brand filter logic
    
    # Search filter (existing)
    search_term = self.search_entry.get().strip().lower()
    if search_term:
        # ... existing search logic
    
    self.filtered_items = filtered
    self._populate_tree()
```

### 3. Add Brand Dropdown Filter
**File**: `src/ui/inventory_tab.py`

**New filter dropdown**: Brand

**Implementation**:
```python
# In _create_controls or similar method
brand_label = ctk.CTkLabel(controls_frame, text="Brand:")
brand_label.grid(row=0, column=N, padx=(15, 5), pady=5)

self.brand_var = ctk.StringVar(value="All Brands")
self.brand_dropdown = ctk.CTkOptionMenu(
    controls_frame,
    variable=self.brand_var,
    values=["All Brands"],  # Populated dynamically
    command=self._on_brand_filter_change,
    width=150,
)
self.brand_dropdown.grid(row=0, column=N+1, padx=5, pady=5)
```

**Populate dynamically**:
```python
def _load_filter_data(self):
    """Load filter dropdown data from inventory items."""
    # Get distinct ingredients
    ingredients = set()
    brands = set()
    
    for item in self.inventory_items:
        if item.product:
            if item.product.ingredient:
                ingredients.add(item.product.ingredient.name)
            if item.product.brand:
                brands.add(item.product.brand)
    
    self.ingredients = sorted(list(ingredients))
    self.brands = sorted(list(brands))
    
    self.ingredient_dropdown.configure(
        values=["All Ingredients"] + self.ingredients
    )
    self.brand_dropdown.configure(
        values=["All Brands"] + self.brands
    )
```

**Filter logic**:
```python
def _apply_filters(self):
    """Apply all filters to inventory items."""
    filtered = self.inventory_items
    
    # Ingredient filter
    if self.ingredient_var.get() != "All Ingredients":
        ingredient_name = self.ingredient_var.get()
        filtered = [
            item for item in filtered
            if item.product and item.product.ingredient 
            and item.product.ingredient.name == ingredient_name
        ]
    
    # Brand filter
    if self.brand_var.get() != "All Brands":
        brand_name = self.brand_var.get()
        filtered = [
            item for item in filtered
            if item.product and item.product.brand == brand_name
        ]
    
    # Category filter (existing)
    # Search filter (existing)
    
    self.filtered_items = filtered
    self._populate_tree()
```

## Implementation Tasks

### Task 1: Implement Default Alphabetical Sort
**File**: `src/ui/inventory_tab.py`

1. Find where inventory items are loaded
2. Sort by `product.ingredient.name` before populating tree
3. Test that items appear alphabetically by ingredient

### Task 2: Add Ingredient Filter
**File**: `src/ui/inventory_tab.py`

1. Add ingredient dropdown to controls section
2. Position after existing filters (check layout)
3. Implement `_load_filter_data()` to populate dropdown
4. Implement `_on_ingredient_filter_change()` handler
5. Update `_apply_filters()` to include ingredient filtering
6. Call `_load_filter_data()` during refresh

### Task 3: Add Brand Filter
**File**: `src/ui/inventory_tab.py`

1. Add brand dropdown to controls section
2. Position after ingredient filter
3. Update `_load_filter_data()` to populate brands
4. Implement `_on_brand_filter_change()` handler
5. Update `_apply_filters()` to include brand filtering

### Task 4: Refactor Filter Application
**File**: `src/ui/inventory_tab.py`

1. Ensure all filters work together
2. Filters should be cumulative (AND logic)
3. "Clear Filters" button should reset all dropdowns
4. Refresh should reload filter dropdown options

### Task 5: Adjust Layout
**File**: `src/ui/inventory_tab.py`

1. Verify filter controls fit on one row
2. Adjust column widths if needed
3. Ensure proper spacing and alignment
4. Test on different window sizes

## Testing Checklist

### Sorting
- [ ] Items display alphabetically by Ingredient by default
- [ ] Sorting is case-insensitive (Almond before Butter)
- [ ] Empty/null ingredients handled gracefully

### Ingredient Filter
- [ ] Dropdown shows "All Ingredients" plus distinct ingredient names
- [ ] Selecting ingredient filters list to show only that ingredient
- [ ] "All Ingredients" shows all items
- [ ] Dropdown updates when inventory changes

### Brand Filter
- [ ] Dropdown shows "All Brands" plus distinct brand names
- [ ] Selecting brand filters list to show only that brand
- [ ] "All Brands" shows all items
- [ ] Dropdown updates when inventory changes

### Combined Filters
- [ ] Ingredient + Brand filters work together (AND logic)
- [ ] Ingredient + Category filters work together
- [ ] Ingredient + Brand + Category + Search all work together
- [ ] Clear Filters button resets all dropdowns
- [ ] Filters persist during view mode toggle (Detail/Aggregate)

### Layout
- [ ] All filters visible on one row
- [ ] Dropdowns properly sized
- [ ] No overlap or crowding
- [ ] Responsive to window resize

## Success Criteria

1. **Alphabetical Sort**: Items sorted by ingredient name by default
2. **Ingredient Filter**: Working dropdown with dynamic options
3. **Brand Filter**: Working dropdown with dynamic options
4. **Combined Filtering**: All filters work together correctly
5. **Usability**: Easy to find specific items quickly
6. **Performance**: Filtering is fast even with 100+ items

## Implementation Notes

### Filter Pattern (Reference from Products Tab)

Products tab already has brand filtering - use same pattern:

```python
# From products_tab.py
def _on_filter_change(self, value=None):
    """Handle any filter change."""
    self._apply_filters()

def _apply_filters(self):
    """Apply current filters to products list."""
    filtered = self.products
    
    # Apply each filter
    if self.ingredient_var.get() != "All":
        filtered = [p for p in filtered if ...]
    
    if self.brand_var.get() != "All":
        filtered = [p for p in filtered if ...]
    
    self.filtered_products = filtered
    self._populate_grid()
```

### Sorting

```python
# Sort inventory items by ingredient name
sorted_items = sorted(
    self.inventory_items,
    key=lambda item: (
        item.product.ingredient.name.lower() 
        if item.product and item.product.ingredient 
        else "zzz"  # Push items without ingredient to end
    )
)
```

## Related Files

**Primary File**:
- `src/ui/inventory_tab.py` - All changes here

**Reference Files**:
- `src/ui/products_tab.py` - Brand filter pattern

## Git Workflow

```bash
git checkout -b bugfix/pantry-filters-and-sorting
git commit -m "feat: add default alphabetical sort by ingredient to pantry"
git commit -m "feat: add ingredient filter dropdown to pantry"
git commit -m "feat: add brand filter dropdown to pantry"
git commit -m "refactor: improve combined filter logic in pantry"
git push
```

---

**Usability Enhancement**: Makes finding items in pantry much faster as inventory grows.
