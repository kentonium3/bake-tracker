# Bug Fix: Add Import Support for Inventory and Purchase View Files

**Branch**: `bugfix/import-inventory-purchases-views`  
**Priority**: CRITICAL (blocks AI augmentation workflow)  
**Estimated Effort**: 2-3 hours

## Context

Feature 030 (Enhanced Export/Import) created denormalized export views for AI augmentation:
- ✅ `export_products_view()` - Exports view_products.json
- ✅ `export_inventory_view()` - Exports view_inventory.json  
- ✅ `export_purchases_view()` - Exports view_purchases.json

**Problem**: The import service was never completed to handle these view files. It only imports catalog data (ingredients, products, suppliers), not transactional data (inventory items, purchases).

**Impact**: After AI augmentation of price/purchase data in view files, there's no way to import the changes back into the database.

## Current State vs Required

### What Works (Catalog Imports) ✅
- Import ingredients from catalog files
- Import products from catalog files
- Import suppliers from catalog files

### What's Missing (View Imports) ❌
- ❌ Import inventory items from view_inventory.json
- ❌ Import purchases from view_purchases.json
- ❌ Import product updates from view_products.json (e.g., AI-augmented GTIN codes)

## Required Implementation

### 1. Add View Type Support to Import Service
**File**: Import service (location TBD - find it)

Add three new import handlers:

```python
def import_products_view(
    file_path: str,
    session: Optional[Session] = None
) -> ImportResult:
    """
    Import product updates from view_products.json.
    
    Updates existing products with AI-augmented data:
    - GTIN codes
    - UPC codes  
    - Brand corrections
    - Package information
    - Notes
    
    Uses product_slug for FK resolution.
    """
    
def import_inventory_view(
    file_path: str,
    session: Optional[Session] = None
) -> ImportResult:
    """
    Import inventory items from view_inventory.json.
    
    Creates new inventory items or updates existing ones.
    Uses product_slug → product_id FK resolution.
    """

def import_purchases_view(
    file_path: str,
    session: Optional[Session] = None  
) -> ImportResult:
    """
    Import purchases from view_purchases.json.
    
    Creates new purchase records.
    Uses product_slug → product_id FK resolution.
    """
```

### 2. Handle Foreign Key Resolution
**Critical requirement**: View files use slugs, database uses IDs

**FK Resolution needed**:
- `product_slug` → `product.id`
- `ingredient_slug` → `ingredient.id` (for products view)
- `supplier_name` → `supplier.id` (for purchases view)

**Pattern** (from existing catalog imports):
```python
def _resolve_product_id(session: Session, product_slug: str) -> Optional[int]:
    """Resolve product slug to ID."""
    product = session.query(Product).filter(
        Product.product_slug == product_slug
    ).first()
    
    if not product:
        raise ValidationError(f"Product not found: {product_slug}")
    
    return product.id
```

### 3. Update UI to Support View Imports
**File**: `src/ui/import_export_dialog.py` (or similar)

Current import dialog likely only shows catalog import options. Add:
- "Import Products View" button
- "Import Inventory View" button  
- "Import Purchases View" button

Or extend existing import to detect view_*.json files automatically.

### 4. Handle Editable vs Readonly Fields
**Important**: View files have `_meta` sections defining editable fields

**Products View** - Only update these fields:
```python
EDITABLE = [
    "brand", "product_name", "package_size", "package_type",
    "package_unit", "package_unit_quantity", "upc_code", "gtin",
    "notes", "preferred", "is_hidden"
]
```

**Inventory View** - Only update these fields:
```python
EDITABLE = [
    "quantity", "location", "expiration_date", "opened_date",
    "notes", "lot_or_batch"
]
```

**Purchases View** - All fields are typically editable for new purchases

### 5. Add Import Validation
**Required validations**:
- File format validation (JSON structure)
- Required field validation
- FK resolution validation (product exists)
- Data type validation (dates, decimals, etc.)
- Duplicate detection (for purchases)

## Implementation Tasks

### Task 1: Locate and Examine Import Service
**File**: Find the import service file

1. Search for existing import service
2. Review catalog import implementation
3. Understand FK resolution patterns
4. Identify where to add view import functions

### Task 2: Implement Products View Import
**File**: Import service

```python
def import_products_view(file_path: str, session: Optional[Session] = None) -> ImportResult:
    """Import product updates from AI-augmented view_products.json."""
    
    managed_session = session is None
    if managed_session:
        session = Session()
    
    try:
        # Load view file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        products_data = data.get('products', [])
        editable_fields = data.get('_meta', {}).get('editable_fields', PRODUCTS_VIEW_EDITABLE)
        
        updated_count = 0
        errors = []
        
        for item in products_data:
            try:
                # Find product by slug
                product_slug = item.get('product_slug')
                product = session.query(Product).filter(
                    Product.product_slug == product_slug
                ).first()
                
                if not product:
                    errors.append(f"Product not found: {product_slug}")
                    continue
                
                # Update only editable fields
                for field in editable_fields:
                    if field in item and field != 'product_slug':
                        setattr(product, field, item[field])
                
                updated_count += 1
                
            except Exception as e:
                errors.append(f"Error updating {item.get('product_slug')}: {e}")
        
        if managed_session:
            session.commit()
        
        return ImportResult(
            view_type="products",
            records_processed=len(products_data),
            records_imported=updated_count,
            errors=errors
        )
        
    finally:
        if managed_session:
            session.close()
```

### Task 3: Implement Inventory View Import
**File**: Import service

```python
def import_inventory_view(file_path: str, session: Optional[Session] = None) -> ImportResult:
    """Import inventory items from view_inventory.json."""
    
    managed_session = session is None
    if managed_session:
        session = Session()
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        inventory_data = data.get('inventory', [])
        created_count = 0
        updated_count = 0
        errors = []
        
        for item in inventory_data:
            try:
                # Resolve product FK
                product_slug = item.get('product_slug')
                product = session.query(Product).filter(
                    Product.product_slug == product_slug
                ).first()
                
                if not product:
                    errors.append(f"Product not found: {product_slug}")
                    continue
                
                # Check if inventory item exists by UUID
                item_uuid = item.get('uuid')
                inventory_item = None
                if item_uuid:
                    inventory_item = session.query(InventoryItem).filter(
                        InventoryItem.uuid == item_uuid
                    ).first()
                
                if inventory_item:
                    # Update existing
                    for field in INVENTORY_VIEW_EDITABLE:
                        if field in item:
                            setattr(inventory_item, field, item[field])
                    updated_count += 1
                else:
                    # Create new
                    inventory_item = InventoryItem(
                        product_id=product.id,
                        quantity=item.get('quantity'),
                        location=item.get('location'),
                        expiration_date=item.get('expiration_date'),
                        # ... other fields
                    )
                    session.add(inventory_item)
                    created_count += 1
                    
            except Exception as e:
                errors.append(f"Error importing inventory item: {e}")
        
        if managed_session:
            session.commit()
        
        return ImportResult(
            view_type="inventory",
            records_processed=len(inventory_data),
            records_imported=created_count + updated_count,
            records_created=created_count,
            records_updated=updated_count,
            errors=errors
        )
        
    finally:
        if managed_session:
            session.close()
```

### Task 4: Implement Purchases View Import
**File**: Import service

```python
def import_purchases_view(file_path: str, session: Optional[Session] = None) -> ImportResult:
    """Import purchase records from view_purchases.json."""
    
    managed_session = session is None
    if managed_session:
        session = Session()
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        purchases_data = data.get('purchases', [])
        created_count = 0
        errors = []
        
        for item in purchases_data:
            try:
                # Resolve product FK
                product_slug = item.get('product_slug')
                product = session.query(Product).filter(
                    Product.product_slug == product_slug
                ).first()
                
                if not product:
                    errors.append(f"Product not found: {product_slug}")
                    continue
                
                # Resolve supplier FK (optional)
                supplier_id = None
                supplier_name = item.get('supplier_name')
                if supplier_name:
                    supplier = session.query(Supplier).filter(
                        Supplier.name == supplier_name
                    ).first()
                    if supplier:
                        supplier_id = supplier.id
                
                # Create purchase record
                purchase = Purchase(
                    product_id=product.id,
                    supplier_id=supplier_id,
                    purchase_date=item.get('purchase_date'),
                    quantity_purchased=item.get('quantity_purchased'),
                    unit_price=item.get('unit_price'),
                    total_cost=item.get('total_cost'),
                    store_or_supplier=item.get('store_or_supplier'),
                    # ... other fields
                )
                
                session.add(purchase)
                created_count += 1
                
            except Exception as e:
                errors.append(f"Error importing purchase: {e}")
        
        if managed_session:
            session.commit()
        
        return ImportResult(
            view_type="purchases",
            records_processed=len(purchases_data),
            records_imported=created_count,
            errors=errors
        )
        
    finally:
        if managed_session:
            session.close()
```

### Task 5: Add UI Support
**File**: `src/ui/import_export_dialog.py` or similar

Add import buttons/handlers for view files:

```python
# In import section of dialog

view_import_label = ctk.CTkLabel(frame, text="Import AI-Augmented Views:")
view_import_label.grid(...)

products_view_btn = ctk.CTkButton(
    frame,
    text="Import Products View",
    command=self._import_products_view
)

inventory_view_btn = ctk.CTkButton(
    frame,
    text="Import Inventory View",  
    command=self._import_inventory_view
)

purchases_view_btn = ctk.CTkButton(
    frame,
    text="Import Purchases View",
    command=self._import_purchases_view
)
```

### Task 6: Add Tests
**File**: Test file for import service

```python
def test_import_products_view():
    """Test importing AI-augmented product data."""
    # Create test view file with updated GTIN
    # Import view file
    # Verify product updated
    # Verify readonly fields not changed

def test_import_inventory_view():
    """Test importing inventory from view."""
    # Create test view file
    # Import inventory
    # Verify items created with correct product FKs

def test_import_purchases_view():
    """Test importing purchase records."""
    # Create test view file
    # Import purchases
    # Verify purchase records created
```

## Testing Checklist

### Products View Import
- [ ] Imports products view file successfully
- [ ] Updates only editable fields
- [ ] Readonly fields remain unchanged
- [ ] FK resolution works (ingredient_slug, supplier_name)
- [ ] Validation prevents invalid data
- [ ] Error messages are clear
- [ ] AI-augmented GTINs/UPCs import correctly

### Inventory View Import
- [ ] Imports inventory view file successfully
- [ ] Creates new inventory items
- [ ] Updates existing items (by UUID)
- [ ] Product FK resolution works
- [ ] Quantities and dates import correctly
- [ ] Validation prevents invalid data

### Purchases View Import
- [ ] Imports purchases view file successfully
- [ ] Creates purchase records
- [ ] Product FK resolution works
- [ ] Supplier FK resolution works (optional)
- [ ] Prices and dates import correctly
- [ ] Duplicate detection works

### Integration
- [ ] Can export → augment → import round-trip
- [ ] UI shows import options
- [ ] Import results display correctly
- [ ] Errors reported clearly
- [ ] Database state correct after import

## Success Criteria

1. **Completes Feature 030**: Import service matches export service capabilities
2. **AI Workflow Works**: Can export → AI augment → import successfully
3. **FK Resolution Works**: Slugs correctly resolve to IDs
4. **Editable Fields Respected**: Only updates fields marked as editable
5. **Validation Robust**: Prevents bad data from corrupting database
6. **UI Accessible**: Import functions available in UI
7. **Error Handling**: Clear error messages when imports fail
8. **Tests Pass**: Comprehensive test coverage

## Data Classes Needed

```python
@dataclass
class ImportResult:
    """Result of a view import operation."""
    view_type: str
    records_processed: int
    records_imported: int
    records_created: int = 0
    records_updated: int = 0
    errors: List[str] = field(default_factory=list)
    import_date: str = field(default_factory=lambda: datetime.now().isoformat())
```

## Related Files

**Primary Files to Modify/Create**:
- Import service file (find location)
- `src/ui/import_export_dialog.py` - Add UI buttons
- Test file for import service

**Reference Files**:
- `src/services/denormalized_export_service.py` - View export implementation
- Existing catalog import code - FK resolution patterns

## Git Workflow

```bash
git checkout -b bugfix/import-inventory-purchases-views
git commit -m "feat: add import support for products view"
git commit -m "feat: add import support for inventory view"
git commit -m "feat: add import support for purchases view"
git commit -m "feat: add UI buttons for view imports"
git commit -m "test: add comprehensive import tests"
git push
```

---

**CRITICAL**: This completes Feature 030 and unblocks the AI augmentation workflow. Without this, exported views cannot be imported back after augmentation.
