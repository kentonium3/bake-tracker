# Bug Fix: Force Delete Products with Safety Checks

**Branch**: `bugfix/product-force-delete`  
**Priority**: MEDIUM (data cleanup needed, but not blocking)  
**Estimated Effort**: 1.5 hours

## Context

**Problem**: Invalid test/AI-generated products exist in database that need to be removed, but cannot be deleted due to referential integrity constraints (products with purchases cannot be deleted).

**Examples of invalid products**:
- Wegmans Self-Rising Flour (Wegmans doesn't make this)
- Other AI-generated products that don't match actual brand offerings
- Test products from development/import experiments

**Current behavior**:
- Products with purchases have `ondelete="RESTRICT"` → Cannot delete
- Soft delete (hide) exists but doesn't remove invalid data
- No way to force delete with associated data

**User need**: Remove truly invalid products while being warned about data loss.

**CRITICAL RULE**: Products used in recipes CANNOT be force-deleted. If used in recipes, the product is real (or must stay for recipe integrity).

## Current State vs Expected

### Current (Blocked)
```
User tries to delete invalid product
→ Error: "Cannot delete - product has purchases"
→ Suggestion: "Hide product instead"
→ Invalid data remains in database ❌
```

### Expected (Safe Force Delete)
```
User selects "Delete Product"
→ System checks dependencies:
   - 0 recipes (REQUIRED to proceed)
   - 1 purchase record (no price, no supplier)
   - 1 inventory item
→ Warning dialog:
   "This will permanently delete:
    • 1 purchase record
    • 1 inventory item
    • Product: Wegmans Self-Rising Flour
    
    This action cannot be undone.
    Are you sure?"
→ [Cancel] [Delete Permanently]
→ If Delete: Removes all related data ✅
```

### Blocked (Used in Recipe)
```
User selects "Delete Product" on product used in recipe
→ System checks dependencies:
   - 1 recipe found ❌
→ Error dialog:
   "Cannot Delete Product
   
    This product is used in 1 recipe(s):
    • Chocolate Chip Cookies
    
    Products used in recipes cannot be deleted.
    If this product is truly invalid, please:
    1. Remove it from all recipes first, OR
    2. Use 'Hide Product' instead"
→ [OK]
```

## Requirements

### 1. Dependency Analysis Function

**Create service method** to analyze product dependencies:

```python
from dataclasses import dataclass
from typing import List

@dataclass
class ProductDependencies:
    """Analysis of product dependencies for deletion."""
    product_id: int
    product_name: str
    brand: str
    
    # Counts
    purchase_count: int
    inventory_count: int
    recipe_count: int
    
    # Details
    purchases: List[dict]  # [{id, date, supplier, price, qty}]
    inventory_items: List[dict]  # [{id, qty, location}]
    recipes: List[str]  # [recipe names]
    
    # Safety flags
    has_valid_purchases: bool  # Has purchases with price > 0
    has_supplier_data: bool    # Has purchases with supplier
    is_used_in_recipes: bool   # Used in any recipes
    
    @property
    def can_force_delete(self) -> bool:
        """Can only force delete if NOT used in recipes."""
        return not self.is_used_in_recipes
    
    @property
    def deletion_risk_level(self) -> str:
        """Risk level: LOW, MEDIUM, BLOCKED."""
        if self.is_used_in_recipes:
            return "BLOCKED"  # Cannot delete at all
        if self.has_valid_purchases or self.has_supplier_data:
            return "MEDIUM"
        return "LOW"


def analyze_product_dependencies(
    session,
    product_id: int
) -> ProductDependencies:
    """
    Analyze what will be deleted if product is force-deleted.
    
    Returns detailed dependency information for user confirmation.
    """
    from src.models.product import Product
    from src.models.purchase import Purchase
    from src.models.inventory_item import InventoryItem
    from src.models.recipe_ingredient import RecipeIngredient
    
    product = session.query(Product).get(product_id)
    if not product:
        raise ProductNotFound(f"Product {product_id} not found")
    
    # Get all purchases
    purchases = session.query(Purchase).filter(
        Purchase.product_id == product_id
    ).all()
    
    purchase_details = [{
        'id': p.id,
        'date': p.purchase_date,
        'supplier': p.supplier.name if p.supplier else None,
        'price': float(p.unit_price or 0),
        'quantity': float(p.quantity_purchased or 0)
    } for p in purchases]
    
    # Get inventory items
    inventory = session.query(InventoryItem).filter(
        InventoryItem.product_id == product_id
    ).all()
    
    inventory_details = [{
        'id': i.id,
        'qty': float(i.quantity_remaining or 0),
        'location': i.location
    } for i in inventory]
    
    # Get recipes using this product
    recipe_ingredients = session.query(RecipeIngredient).filter(
        RecipeIngredient.product_id == product_id
    ).all()
    
    recipe_names = [
        ri.recipe.name for ri in recipe_ingredients
        if ri.recipe
    ]
    
    # Analyze data quality
    has_valid_purchases = any(p['price'] > 0 for p in purchase_details)
    has_supplier_data = any(p['supplier'] for p in purchase_details)
    
    return ProductDependencies(
        product_id=product_id,
        product_name=product.product_name,
        brand=product.brand or "Unknown",
        purchase_count=len(purchases),
        inventory_count=len(inventory),
        recipe_count=len(recipe_names),
        purchases=purchase_details,
        inventory_items=inventory_details,
        recipes=recipe_names,
        has_valid_purchases=has_valid_purchases,
        has_supplier_data=has_supplier_data,
        is_used_in_recipes=bool(recipe_names)
    )
```

### 2. Force Delete Function

**Create service method** for cascading delete:

```python
def force_delete_product(
    session,
    product_id: int,
    confirmed: bool = False
) -> ProductDependencies:
    """
    Force delete a product and all dependent data.
    
    CRITICAL: Cannot delete products used in recipes.
    
    WARNING: This permanently deletes:
    - Purchase records
    - Inventory items
    - The product itself
    
    Args:
        session: Database session
        product_id: Product to delete
        confirmed: Must be True to actually delete (safety check)
    
    Returns:
        ProductDependencies object showing what was/would be deleted
    
    Raises:
        ValueError: If confirmed=False (must confirm deletion)
        ValueError: If product is used in recipes (cannot delete)
        ProductNotFound: If product doesn't exist
    """
    # Analyze dependencies first
    deps = analyze_product_dependencies(session, product_id)
    
    # CRITICAL CHECK: Cannot delete if used in recipes
    if deps.is_used_in_recipes:
        recipe_list = ", ".join(deps.recipes)
        raise ValueError(
            f"Cannot delete product used in {deps.recipe_count} recipe(s): {recipe_list}. "
            f"Remove product from recipes first, or use hide_product() instead."
        )
    
    if not confirmed:
        raise ValueError(
            "Force delete requires confirmed=True. "
            "User must confirm deletion after seeing dependencies."
        )
    
    # Delete in correct order (respect FK constraints)
    # NOTE: No recipe ingredient deletion - already verified count is 0
    
    # 1. Delete inventory items (which link to purchases)
    session.query(InventoryItem).filter(
        InventoryItem.product_id == product_id
    ).delete()
    
    # 2. Delete purchases
    session.query(Purchase).filter(
        Purchase.product_id == product_id
    ).delete()
    
    # 3. Delete the product itself
    session.query(Product).filter(
        Product.id == product_id
    ).delete()
    
    session.commit()
    
    logger.warning(
        f"FORCE DELETED product {product_id}: {deps.product_name} "
        f"({deps.purchase_count} purchases, {deps.inventory_count} inventory)"
    )
    
    return deps
```

### 3. Confirmation Dialog UI

**Update delete handler** in Products tab:

```python
def _on_delete_product(self):
    """Handle delete product with force delete option."""
    
    selected = self.get_selected_product_id()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a product to delete")
        return
    
    try:
        with session_scope() as session:
            # Try normal delete first
            try:
                product_catalog_service.delete_product(session, selected)
                messagebox.showinfo("Success", "Product deleted")
                self.refresh()
                return
            
            except IntegrityError:
                # Has dependencies - analyze them
                pass
        
        # Analyze dependencies
        with session_scope() as session:
            deps = product_catalog_service.analyze_product_dependencies(
                session, selected
            )
        
        # Check if used in recipes - BLOCKED
        if deps.is_used_in_recipes:
            self._show_recipe_block_dialog(deps)
            return
        
        # Not in recipes - show force delete confirmation
        self._show_force_delete_confirmation(deps)
    
    except Exception as e:
        messagebox.showerror("Error", f"Delete failed: {e}")


def _show_recipe_block_dialog(self, deps: ProductDependencies):
    """Show dialog explaining product cannot be deleted (used in recipes)."""
    
    dialog = ctk.CTkToplevel(self)
    dialog.title("Cannot Delete Product")
    dialog.geometry("500x400")
    dialog.transient(self)
    dialog.grab_set()
    
    # Header
    header = ctk.CTkLabel(
        dialog,
        text="🚫 Cannot Delete Product",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="red"
    )
    header.pack(pady=15)
    
    # Product info
    product_label = ctk.CTkLabel(
        dialog,
        text=f"Product: {deps.product_name}\nBrand: {deps.brand}",
        font=ctk.CTkFont(size=12, weight="bold")
    )
    product_label.pack(pady=10)
    
    # Explanation
    explanation = ctk.CTkLabel(
        dialog,
        text=f"This product is used in {deps.recipe_count} recipe(s):",
        font=ctk.CTkFont(size=11)
    )
    explanation.pack(pady=5)
    
    # Recipe list
    recipe_frame = ctk.CTkScrollableFrame(dialog, height=150)
    recipe_frame.pack(padx=20, pady=10, fill="both", expand=True)
    
    for recipe in deps.recipes:
        recipe_label = ctk.CTkLabel(
            recipe_frame,
            text=f"• {recipe}",
            anchor="w"
        )
        recipe_label.pack(anchor="w", padx=10, pady=2)
    
    # Instructions
    instructions = ctk.CTkLabel(
        dialog,
        text=(
            "Products used in recipes cannot be deleted.\n\n"
            "To remove this product:\n"
            "1. Remove it from all recipes listed above, OR\n"
            "2. Use 'Hide Product' to keep it but hide from lists"
        ),
        justify="left"
    )
    instructions.pack(pady=15, padx=20)
    
    # OK button
    ok_btn = ctk.CTkButton(
        dialog,
        text="OK",
        command=dialog.destroy,
        width=150
    )
    ok_btn.pack(pady=15)


def _show_force_delete_confirmation(self, deps: ProductDependencies):
    """Show detailed force delete confirmation dialog."""
    
    # Create custom dialog
    dialog = ctk.CTkToplevel(self)
    dialog.title("Confirm Force Delete")
    dialog.geometry("600x500")
    dialog.transient(self)
    dialog.grab_set()
    
    # Header
    header = ctk.CTkLabel(
        dialog,
        text="⚠️ Force Delete Product",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="red"
    )
    header.pack(pady=15)
    
    # Product info
    product_frame = ctk.CTkFrame(dialog)
    product_frame.pack(padx=20, pady=10, fill="x")
    
    product_label = ctk.CTkLabel(
        product_frame,
        text=f"Product: {deps.product_name}\nBrand: {deps.brand}",
        font=ctk.CTkFont(size=12, weight="bold")
    )
    product_label.pack(pady=10)
    
    # Risk level indicator
    risk_color = {
        "LOW": "green",
        "MEDIUM": "orange"
    }
    
    risk_label = ctk.CTkLabel(
        product_frame,
        text=f"Risk Level: {deps.deletion_risk_level}",
        text_color=risk_color[deps.deletion_risk_level],
        font=ctk.CTkFont(size=11, weight="bold")
    )
    risk_label.pack()
    
    # Scrollable details
    details_frame = ctk.CTkScrollableFrame(dialog, height=250)
    details_frame.pack(padx=20, pady=10, fill="both", expand=True)
    
    # Build warning message
    warning_text = "This will permanently delete:\n\n"
    
    # Purchases
    if deps.purchase_count > 0:
        warning_text += f"📦 {deps.purchase_count} Purchase Record(s):\n"
        for p in deps.purchases:
            supplier = p['supplier'] or 'No supplier'
            price = f"${p['price']:.2f}" if p['price'] > 0 else "No price"
            warning_text += f"   • {p['date']}: {p['quantity']} pkg, {price}, {supplier}\n"
        warning_text += "\n"
    
    # Inventory
    if deps.inventory_count > 0:
        warning_text += f"📊 {deps.inventory_count} Inventory Item(s):\n"
        for i in deps.inventory_items:
            location = i['location'] or 'No location'
            warning_text += f"   • {i['qty']} remaining, {location}\n"
        warning_text += "\n"
    
    # Add specific warnings
    if deps.has_valid_purchases:
        warning_text += "⚠️ Has purchases with price data - you will lose cost history\n"
    if deps.has_supplier_data:
        warning_text += "⚠️ Has supplier information - you will lose this data\n"
    
    warning_text += "\n❌ This action CANNOT be undone!"
    
    details_label = ctk.CTkLabel(
        details_frame,
        text=warning_text,
        justify="left",
        anchor="w"
    )
    details_label.pack(padx=10, pady=10, fill="both")
    
    # Buttons
    button_frame = ctk.CTkFrame(dialog)
    button_frame.pack(pady=15)
    
    def on_confirm():
        dialog.destroy()
        self._execute_force_delete(deps.product_id)
    
    def on_cancel():
        dialog.destroy()
    
    cancel_btn = ctk.CTkButton(
        button_frame,
        text="Cancel",
        command=on_cancel,
        width=150
    )
    cancel_btn.pack(side="left", padx=10)
    
    delete_btn = ctk.CTkButton(
        button_frame,
        text="Delete Permanently",
        command=on_confirm,
        fg_color="red",
        hover_color="darkred",
        width=150
    )
    delete_btn.pack(side="left", padx=10)


def _execute_force_delete(self, product_id: int):
    """Execute the force delete after confirmation."""
    try:
        with session_scope() as session:
            deps = product_catalog_service.force_delete_product(
                session,
                product_id,
                confirmed=True  # User confirmed via dialog
            )
        
        messagebox.showinfo(
            "Deleted",
            f"Product '{deps.product_name}' and all related data deleted.\n"
            f"Deleted: {deps.purchase_count} purchases, "
            f"{deps.inventory_count} inventory items"
        )
        self.refresh()
        
    except ValueError as e:
        # Should not happen (already checked recipes) but handle anyway
        messagebox.showerror("Cannot Delete", str(e))
    except Exception as e:
        messagebox.showerror("Error", f"Force delete failed: {e}")
```

## Implementation Tasks

### Task 1: Add Dependency Analysis
**File**: `src/services/product_catalog_service.py`

1. Add `ProductDependencies` dataclass
2. Implement `analyze_product_dependencies()` function
3. Add `can_force_delete` property (checks recipes)
4. Update `deletion_risk_level` to include "BLOCKED"
5. Test with various products

### Task 2: Add Force Delete Function
**File**: Same service file

1. Implement `force_delete_product()` function
2. **Add recipe check that raises ValueError**
3. Ensure correct deletion order (respect FKs)
4. Add logging for audit trail
5. Require explicit confirmation parameter

### Task 3: Update Delete Handler
**File**: Products tab UI file

1. Modify existing delete handler
2. Try normal delete first
3. On IntegrityError, analyze dependencies
4. **If used in recipes → show block dialog**
5. **If not in recipes → show force delete dialog**

### Task 4: Create Block Dialog
**File**: Same UI file

1. Create "Cannot Delete" dialog
2. List all recipes using the product
3. Explain why deletion is blocked
4. Suggest alternatives (remove from recipes or hide)
5. Single OK button to close

### Task 5: Create Confirmation Dialog
**File**: Same UI file

1. Create scrollable confirmation dialog (for non-recipe products)
2. Show all dependencies with details
3. Color-code risk level (LOW/MEDIUM only, no BLOCKED)
4. Require explicit confirmation click
5. Execute force delete on confirmation

### Task 6: Add Tests
**File**: Test files

```python
def test_cannot_delete_product_in_recipe():
    """Test that products used in recipes cannot be force deleted."""
    # Create product used in recipe
    with pytest.raises(ValueError, match="Cannot delete product used in.*recipe"):
        force_delete_product(session, product_id, confirmed=True)

def test_can_force_delete_without_recipes():
    """Test that products NOT in recipes can be force deleted."""
    # Create product with purchases but no recipes
    deps = force_delete_product(session, product_id, confirmed=True)
    
    # Verify all deleted
    assert session.query(Product).get(product_id) is None
    assert session.query(Purchase).filter(...).count() == 0

def test_analyze_dependencies_blocks_recipes():
    """Test that dependency analysis correctly identifies recipe usage."""
    deps = analyze_product_dependencies(session, product_id_in_recipe)
    assert deps.can_force_delete is False
    assert deps.deletion_risk_level == "BLOCKED"
```

## Testing Checklist

### Dependency Analysis
- [ ] Correctly counts purchases
- [ ] Correctly counts inventory items
- [ ] Correctly identifies recipes
- [ ] `can_force_delete` is False when recipes > 0
- [ ] `deletion_risk_level` is "BLOCKED" when recipes > 0
- [ ] Risk level calculated correctly for non-recipe products

### Force Delete Function
- [ ] Raises ValueError if product used in recipes
- [ ] Requires confirmed=True
- [ ] Deletes in correct order
- [ ] Removes all dependencies (except recipes)
- [ ] Commits transaction
- [ ] Logs deletion for audit

### UI - Recipe Block Dialog
- [ ] Shows when product used in recipes
- [ ] Lists all recipe names
- [ ] Explains why deletion blocked
- [ ] Suggests alternatives
- [ ] OK button closes dialog
- [ ] No delete button shown

### UI - Force Delete Dialog
- [ ] Only shows when product NOT in recipes
- [ ] Shows risk level (LOW or MEDIUM)
- [ ] Lists all purchases with details
- [ ] Lists all inventory items
- [ ] Highlights valuable data (prices, suppliers)
- [ ] Delete button requires confirmation
- [ ] Cancel button works
- [ ] List refreshes after delete

### Edge Cases
- [ ] Product with 0 dependencies (should delete normally)
- [ ] Product with purchases, no recipes (force delete allowed)
- [ ] Product with recipes (blocked, shows recipe list)
- [ ] Product with 10+ recipes (dialog scrolls)

## Success Criteria

1. **Recipe Protection**: Products in recipes CANNOT be force-deleted
2. **Clear Blocking**: User understands why deletion is blocked
3. **Safe Deletion**: Can delete invalid test products not in recipes
4. **Detailed Preview**: All dependencies shown with specifics
5. **Explicit Confirmation**: Cannot accidentally force delete
6. **Complete Removal**: Cascade delete works correctly
7. **User Validation**: Primary user can clean up invalid products

## Usage Examples

### Example 1: Invalid Product Not in Recipes (Allowed)
```
User workflow:
1. Select "Wegmans Self-Rising Flour" in Products tab
2. Click Delete button
3. See error: "Cannot delete - has dependencies"
4. Dialog appears showing:
   Risk: LOW
   1 purchase (no price, no supplier, 2024-12-21)
   1 inventory item (0 remaining)
   0 recipes ✅
5. User confirms: "Delete Permanently"
6. Product and all related data removed
7. Success message shown
```

### Example 2: Product Used in Recipe (Blocked)
```
User workflow:
1. Select product in Products tab
2. Click Delete button
3. Dialog appears:
   "Cannot Delete Product
    This product is used in 1 recipe(s):
    • Chocolate Chip Cookies
    
    To remove: remove from recipe or hide product"
4. User clicks OK
5. Product remains in database
6. User must remove from recipe first, or use Hide instead
```

## Related Files

**Primary Files**:
- `src/services/product_catalog_service.py` - Analysis and force delete
- Products tab UI file - Delete handler and dialogs
- `src/models/product.py` - Reference for relationships

**Related Functions**:
- Existing `delete_product()` - Normal delete (keep this)
- Existing `hide_product()` - Soft delete (keep this, recommend for recipe products)

## Git Workflow

```bash
git checkout -b bugfix/product-force-delete
git commit -m "feat: add product dependency analysis with recipe blocking"
git commit -m "feat: add force delete that blocks recipe products"
git commit -m "feat: add recipe block dialog"
git commit -m "feat: add force delete confirmation dialog"
git commit -m "test: add force delete test coverage with recipe tests"
git push
```

---

**DATA CLEANUP FEATURE**: Enables safe removal of invalid test/AI-generated products while **protecting recipe integrity** - products in recipes cannot be deleted.
