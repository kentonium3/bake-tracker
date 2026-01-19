# Bug Fix: Product GTIN Unique Constraint Error on Edit

**Branch**: `bugfix/product-gtin-unique-constraint`  
**Priority**: Critical (blocks product editing)  
**Estimated Effort**: 30 minutes

## Problem

When editing an existing product and saving with the same GTIN value, getting SQLite IntegrityError instead of a clear user-friendly error message:

```
(sqlite3.IntegrityError) UNIQUE constraint failed: products.gtin
[SQL: UPDATE products SET product_name=?, gtin=?, last_modified=?, updated_at=? WHERE products.id = ?]
```

**User Confirmation**: Deleting the GTIN allows the product to save successfully, confirming the GTIN is the issue.

**Error Details**:
- Product: "Rich Terracotta" (Wincrest brand)
- GTIN: `718444190707`
- The GTIN already belongs to this product OR another product
- User gets raw SQL error instead of helpful message

## Root Causes

### Primary Issue: GTIN Uniqueness Validation Missing or Incomplete

The product service's GTIN uniqueness validation during update has one of two problems:

**Problem A**: No validation exists, so database constraint violation bubbles up as raw SQL error

**Problem B**: Validation exists but doesn't exclude the current product being edited

### Secondary Issue: Poor Error Messages

Even if validation exists, the error message is not user-friendly. Should say:
- "GTIN 718444190707 is already used by product 'X' (Brand: Y)"
- NOT: "sqlite3.IntegrityError UNIQUE constraint failed"

## Expected Behavior vs Actual

**Expected**:
1. User edits product, keeps same GTIN → Saves successfully (validation excludes current product)
2. User edits product, changes to duplicate GTIN → Clear error: "GTIN XXX is already used by product 'Y'"
3. User edits product, changes to unique GTIN → Saves successfully

**Actual**:
1. User edits product, keeps same GTIN → Raw SQL error (validation fails or doesn't exclude current product)
2. User edits product, deletes GTIN → Saves successfully (confirms GTIN is the problem)

## Files to Check

**Primary File**: `src/services/product_catalog_service.py` (or similar)
- Locate the `update_product()` method
- Check if GTIN uniqueness validation exists
- If exists: verify it excludes current product
- If missing: add validation before database update
- Ensure validation throws user-friendly exception, not SQL error

## Implementation Tasks

### Task 1: Locate and Examine Product Update Logic
**File**: `src/services/product_catalog_service.py` or similar

1. Find `update_product()` method (or similar name)
2. Check if GTIN uniqueness validation exists
3. Determine which problem we have:
   - **No validation** → SQL constraint is only check (Problem A)
   - **Has validation** → But doesn't exclude current product (Problem B)

### Task 2: Add or Fix GTIN Uniqueness Validation
**File**: Same service file

#### If No Validation Exists (Problem A):
Add validation BEFORE the database update:

```python
def update_product(session, product_id: int, **updates) -> Product:
    """Update an existing product."""
    product = session.query(Product).get(product_id)
    if not product:
        raise ProductNotFound(f"Product {product_id} not found")
    
    # ADD THIS: Validate GTIN uniqueness if being updated
    new_gtin = updates.get('gtin')
    if new_gtin:  # If GTIN is being set (not None, not empty)
        # Check for duplicates, excluding current product
        duplicate = session.query(Product).filter(
            Product.gtin == new_gtin,
            Product.id != product_id  # Exclude current product
        ).first()
        
        if duplicate:
            raise GTINAlreadyExists(
                f"GTIN {new_gtin} is already used by product "
                f"'{duplicate.product_name}' (Brand: {duplicate.brand or 'Unknown'}). "
                f"GTINs must be unique across all products."
            )
    
    # Rest of update logic...
```

#### If Validation Exists (Problem B):
Fix existing validation to exclude current product:

```python
# Before (WRONG - doesn't exclude current product)
if gtin:
    existing = session.query(Product).filter(Product.gtin == gtin).first()
    if existing:
        raise GTINAlreadyExists(f"Product with GTIN {gtin} already exists")

# After (CORRECT - excludes current product)
if gtin:
    existing = session.query(Product).filter(
        Product.gtin == gtin,
        Product.id != product_id  # KEY: Exclude the product being updated
    ).first()
    if existing:
        raise GTINAlreadyExists(
            f"GTIN {gtin} is already used by product "
            f"'{existing.product_name}' (Brand: {existing.brand or 'Unknown'}). "
            f"GTINs must be unique across all products."
        )
```

### Task 3: Ensure User-Friendly Exception Exists
**File**: `src/services/exceptions.py`

1. Check if `GTINAlreadyExists` exception exists
2. If not, create it:

```python
class GTINAlreadyExists(ValidationError):
    """Raised when attempting to use a GTIN that already exists."""
    pass
```

3. Ensure this exception is caught in UI layer and displayed nicely

### Task 4: Verify UI Error Handling
**File**: Product edit form/dialog

1. Find where product save is called
2. Ensure `GTINAlreadyExists` exception is caught
3. Display error to user via messagebox or inline error
4. Keep form open so user can correct the GTIN

Example:
```python
try:
    product_service.update_product(session, product_id, **form_data)
    messagebox.showinfo("Success", "Product updated successfully")
    self.destroy()
except GTINAlreadyExists as e:
    messagebox.showerror("Duplicate GTIN", str(e))
    # Form stays open for user to fix
except ValidationError as e:
    messagebox.showerror("Validation Error", str(e))
except Exception as e:
    messagebox.showerror("Error", f"Failed to update product: {e}")
```

### Task 5: Apply Same Pattern to UPC and Other Unique Fields
**File**: Same service file

If UPC or other fields have UNIQUE constraints:
1. Add same validation pattern
2. Exclude current product from uniqueness check
3. Provide clear error messages

### Task 6: Add/Update Tests
**File**: `src/tests/services/test_product_catalog_service.py` or similar

Add comprehensive test cases:
```python
def test_update_product_keeps_same_gtin():
    """Test that updating a product with its existing GTIN succeeds."""
    # Create product with GTIN
    with session_scope() as session:
        product = product_service.create_product(
            session, 
            name="Rich Terracotta",
            gtin="718444190707"
        )
        product_id = product.id
    
    # Update other fields, keep same GTIN
    with session_scope() as session:
        product_service.update_product(
            session, 
            product_id, 
            name="Rich Terracotta Updated",
            gtin="718444190707"  # Same GTIN
        )
        updated = product_service.get_product(session, product_id)
    
    # Should succeed without error
    assert updated.name == "Rich Terracotta Updated"
    assert updated.gtin == "718444190707"

def test_update_product_duplicate_gtin_fails_with_clear_message():
    """Test that using another product's GTIN fails with helpful error."""
    # Create two products
    with session_scope() as session:
        product1 = product_service.create_product(
            session,
            name="Product 1",
            brand="Brand A",
            gtin="123456789"
        )
        product2 = product_service.create_product(
            session,
            name="Product 2", 
            gtin="987654321"
        )
        product2_id = product2.id
    
    # Try to update product2 with product1's GTIN
    with session_scope() as session:
        with pytest.raises(GTINAlreadyExists) as exc_info:
            product_service.update_product(
                session,
                product2_id,
                gtin="123456789"  # Duplicate!
            )
        
        # Verify error message is helpful
        error_msg = str(exc_info.value)
        assert "123456789" in error_msg
        assert "Product 1" in error_msg
        assert "Brand A" in error_msg

def test_update_product_change_to_unique_gtin():
    """Test that changing to a unique GTIN succeeds."""
    with session_scope() as session:
        product = product_service.create_product(
            session,
            name="Test Product",
            gtin="111111111"
        )
        product_id = product.id
    
    # Change to different unique GTIN
    with session_scope() as session:
        product_service.update_product(
            session,
            product_id,
            gtin="999999999"
        )
        updated = product_service.get_product(session, product_id)
    
    assert updated.gtin == "999999999"

def test_update_product_clear_gtin():
    """Test that clearing GTIN succeeds."""
    with session_scope() as session:
        product = product_service.create_product(
            session,
            name="Test Product",
            gtin="111111111"
        )
        product_id = product.id
    
    # Clear GTIN
    with session_scope() as session:
        product_service.update_product(
            session,
            product_id,
            gtin=""  # or None
        )
        updated = product_service.get_product(session, product_id)
    
    assert updated.gtin in (None, "")
```

## Testing Checklist

### Basic Functionality
- [ ] Edit product, change name only (no GTIN change) - saves successfully
- [ ] Edit product, keep same GTIN - saves successfully (KEY TEST)
- [ ] Edit product, clear GTIN (set to empty) - saves successfully
- [ ] Edit product, add new GTIN (was previously empty) - saves successfully

### Uniqueness Validation
- [ ] Edit product, change to GTIN that another product has - fails with CLEAR error message
- [ ] Error message includes: duplicate GTIN value, other product name, other product brand
- [ ] Error message does NOT show raw SQL error
- [ ] Edit product, change to unique GTIN (not used elsewhere) - saves successfully
- [ ] Create new product with duplicate GTIN - fails with clear error

### Edge Cases
- [ ] Edit product with no GTIN, keep it empty - saves successfully
- [ ] Edit product, set GTIN to None - saves successfully
- [ ] Edit product, set GTIN to empty string - saves successfully
- [ ] Multiple edits in sequence maintain GTIN correctly

### Error Message Quality
- [ ] No raw SQL errors shown to user
- [ ] Error messages identify which product has the duplicate GTIN
- [ ] Error messages are actionable (user knows what to do)
- [ ] Form stays open after validation error (doesn't close)

### Similar Fields
- [ ] UPC field behaves same way (if has unique constraint)
- [ ] Product slug validation excludes current product
- [ ] Any other unique fields follow same pattern

## Success Criteria

1. **Can Edit with Same GTIN**: Updating product with its existing GTIN succeeds without error
2. **Clear Error Messages**: Duplicate GTIN shows user-friendly error with product name/brand
3. **No SQL Errors**: Users never see raw sqlite3.IntegrityError messages
4. **Duplicate Detection Works**: Changing to another product's GTIN fails appropriately
5. **Form Stays Open**: Validation errors keep form open for correction
6. **No Regressions**: Product creation still validates GTIN uniqueness
7. **Tests Pass**: All product update tests pass
8. **Consistent Pattern**: All unique fields use same validation approach

## Error Message Requirements

### Bad Error Message (Current):
```
Failed to save product: (sqlite3.IntegrityError) UNIQUE constraint failed: products.gtin
[SQL: UPDATE products SET product_name=?, gtin=?, last_modified=?, updated_at=? WHERE products.id = ?]
```

### Good Error Message (Required):
```
GTIN 718444190707 is already used by product 'Dark Chocolate Chips' (Brand: Ghirardelli). 
GTINs must be unique across all products.
```

### Even Better Error Message (Ideal):
```
GTIN 718444190707 is already used by:
  • Product: Dark Chocolate Chips
  • Brand: Ghirardelli
  • Supplier: Costco

Please use a different GTIN or leave this field blank.
```

## Expected Code Pattern

```python
def update_product(session, product_id: int, **updates) -> Product:
    """Update an existing product."""
    product = session.query(Product).get(product_id)
    if not product:
        raise ProductNotFound(f"Product {product_id} not found")
    
    # Validate GTIN uniqueness (if being updated)
    new_gtin = updates.get('gtin')
    if new_gtin:  # If GTIN is being set (not None, not empty string)
        # Check for duplicates, excluding current product
        duplicate = session.query(Product).filter(
            Product.gtin == new_gtin,
            Product.id != product_id  # KEY: Exclude current product
        ).first()
        
        if duplicate:
            # Build helpful error message
            error_msg = (
                f"GTIN {new_gtin} is already used by product "
                f"'{duplicate.product_name}'"
            )
            if duplicate.brand:
                error_msg += f" (Brand: {duplicate.brand})"
            error_msg += ". GTINs must be unique across all products."
            
            raise GTINAlreadyExists(error_msg)
    
    # Apply updates
    for key, value in updates.items():
        if hasattr(product, key):
            setattr(product, key, value)
    
    # Update timestamp
    from datetime import datetime
    product.updated_at = datetime.now()
    
    session.commit()
    return product
```

## Related Files

**Primary Files**:
- `src/services/product_catalog_service.py` - Contains update logic (add/fix validation)
- `src/services/exceptions.py` - Define GTINAlreadyExists exception
- Product edit form/dialog - Handle exception with messagebox

**Test Files**:
- `src/tests/services/test_product_catalog_service.py` - Add comprehensive test cases

**Models** (reference only):
- `src/models/product.py` - GTIN field definition and constraints

## Git Workflow

```bash
# Create bug fix branch
git checkout -b bugfix/product-gtin-unique-constraint

# Commit with clear message
git commit -m "fix: validate GTIN uniqueness with clear error messages

- Add GTIN uniqueness check that excludes current product
- Replace raw SQL errors with user-friendly messages
- Error messages identify conflicting product name and brand
- Add comprehensive tests for GTIN validation scenarios"

# Test thoroughly
# Merge to main
```

## Investigation Steps for Claude Code

1. **Find the update method**: Locate `update_product()` in product service
2. **Check for validation**: Does GTIN validation exist?
   - If NO → Add validation (Problem A)
   - If YES → Fix to exclude current product (Problem B)
3. **Verify exception handling**: Is GTINAlreadyExists defined and caught?
4. **Test with real scenario**: 
   - Edit product with GTIN, keep same GTIN → should save
   - Edit product, use another product's GTIN → should fail with clear message
5. **Check error messages**: No raw SQL errors should reach user

---

**Critical Bug**: Blocks editing products with GTINs and shows confusing error messages. Should be fixed immediately.

**User Workaround Confirmed**: Deleting GTIN allows save, confirming the diagnosis.
