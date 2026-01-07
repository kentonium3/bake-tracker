# TD-006: Deprecate expiration_date Field in Favor of Calculated Shelf Life

**Created**: 2026-01-06  
**Status**: Open  
**Priority**: Medium  
**Related Features**: F041 (Shelf Life & Freshness Tracking), F042 (Purchase Workflow)  
**Impact**: Data model, UI, import/export, AI-assisted workflows

---

## Problem Statement

Current `expiration_date` field in InventoryItem model has fundamental usability issues:

**Problem 1: Inconsistent Packaging Formats**
- Different manufacturers use different date formats
- Common variations: "Best By", "Use By", "Sell By", "Exp", "BB", "EXP"
- Date formats vary: MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, Julian dates
- Some products use coded dates requiring lookup tables

**Problem 2: AI Tool Limitations**
- OCR struggles with small, embossed, or faded text on packaging
- Barcode scanners don't capture expiration dates (not in UPC/GTIN)
- Manual AI-assisted entry still requires human interpretation of format

**Problem 3: Unacceptable User Effort**
- Manually entering expiration dates for 20+ items per shopping trip is tedious
- Error-prone: Easy to transpose dates, misread formats, or skip items
- User abandons feature after 1-2 attempts (observed in F029 user testing)

**Problem 4: Most Products Don't Have Printed Dates**
- Shelf-stable items often have no visible expiration date
- Many products rely on industry-standard shelf life assumptions
- Forces user to research and manually enter expected shelf life

---

## Proposed Solution

### New Architecture: Calculated Shelf Life

Replace manual `expiration_date` entry with calculated shelf life based on ingredient metadata:

```
Ingredient.shelf_life_days (e.g., 365 for flour, 730 for sugar)
    ↓ (inherited as passthrough)
Product.shelf_life_days (can override ingredient default)
    ↓ (calculated at purchase)
InventoryItem.calculated_expiration_date = purchase_date + shelf_life_days
    ↓ (optional manual override)
InventoryItem.expiration_date_override (user-entered actual date)
```

### Implementation Phases

**Phase 1: Add New Fields (Non-Breaking)**
- Add `Ingredient.shelf_life_days` (Integer, nullable, default NULL)
- Add `Product.shelf_life_days` (Integer, nullable, default NULL)
- Add `InventoryItem.calculated_expiration_date` (Date, computed field)
- Add `InventoryItem.expiration_date_override` (Date, nullable)
- Keep existing `InventoryItem.expiration_date` for backward compatibility

**Phase 2: Update Services**
- `IngredientService`: CRUD operations for shelf_life_days
- `ProductService`: Inherit shelf_life_days from ingredient (passthrough)
- `InventoryItemService`: Calculate expiration on creation
  - If product.shelf_life_days: use product value
  - Elif ingredient.shelf_life_days: use ingredient value
  - Else: calculated_expiration_date = NULL
- `InventoryItemService`: Property `effective_expiration_date`:
  ```python
  @property
  def effective_expiration_date(self) -> Optional[date]:
      """Return override if set, else calculated value."""
      return self.expiration_date_override or self.calculated_expiration_date
  ```

**Phase 3: Update UI**
- Ingredients tab: Add shelf_life_days column and edit field
- Products tab: Display inherited shelf_life_days (read-only)
- Inventory tab: Show calculated_expiration_date with "(calculated)" label
- Add Inventory dialog: Remove manual expiration entry, show calculated value
- Inventory detail: Allow manual override via "Override Expiration Date" button

**Phase 4: Migrate Data**
- Export current inventory_items.expiration_date values
- For items with explicit dates:
  - Set expiration_date_override = old expiration_date
  - Calculate shelf_life_days = (expiration - purchase_date).days
  - Update ingredient.shelf_life_days with average from products
- For items without dates: Leave NULL (no change)

**Phase 5: Deprecate Old Field**
- Mark `InventoryItem.expiration_date` as deprecated in code comments
- Update all queries to use `effective_expiration_date` property
- Update exports to use calculated + override pattern
- Keep field in schema (for data preservation)

**Phase 6: Remove Old Field (Future Breaking Change)**
- Drop `InventoryItem.expiration_date` column
- Remove from models, services, UI
- Bump schema version (e.g., v4.0 → v5.0)

---

## Impact Analysis

### Models Affected

**Ingredient Model:**
```python
class Ingredient(BaseModel):
    # ... existing fields ...
    shelf_life_days = Column(Integer, nullable=True)  # NEW
    # e.g., 365 for flour, 730 for sugar, 180 for chocolate chips
```

**Product Model:**
```python
class Product(BaseModel):
    # ... existing fields ...
    shelf_life_days = Column(Integer, nullable=True)  # NEW
    # Inherited from ingredient, can override for specific brands
```

**InventoryItem Model:**
```python
class InventoryItem(BaseModel):
    # ... existing fields ...
    expiration_date = Column(Date, nullable=True)  # DEPRECATED
    calculated_expiration_date = Column(Date, nullable=True)  # NEW (computed)
    expiration_date_override = Column(Date, nullable=True)  # NEW (user override)
    
    @property
    def effective_expiration_date(self) -> Optional[date]:
        """Return override if set, else calculated value."""
        return self.expiration_date_override or self.calculated_expiration_date
```

### Services Affected

- `IngredientService`: Add shelf_life_days CRUD
- `ProductService`: Passthrough shelf_life_days from ingredient
- `InventoryItemService`: Calculate expiration on add_inventory()
- `PurchaseService`: No changes (calculation happens in inventory service)
- `PlanningService`: Use effective_expiration_date for freshness checks

### UI Affected

- **Ingredients Tab:**
  - Add "Shelf Life (days)" column
  - Add shelf_life_days field to ingredient edit form
  - Show common values as hints (365 for flour, 730 for sugar, etc.)

- **Products Tab:**
  - Display inherited shelf_life_days (read-only unless overriding)
  - Optional: Allow product-level override for specific brands
  
- **Inventory Tab:**
  - Replace "Expiration Date" column with "Best By (calculated)"
  - Show "(manual)" badge for overridden dates
  - Color coding: 🟢 Fresh / 🟡 Expiring Soon / 🔴 Expired
  
- **Add Inventory Dialog:**
  - Remove manual expiration date entry field
  - Show calculated expiration date preview: "(Best by: YYYY-MM-DD)"
  - Add optional "Override" button for edge cases

- **Inventory Item Detail:**
  - Show calculation: "Purchased: 2024-12-01 + 365 days = Best By: 2025-12-01"
  - Show "Override Expiration Date" button (opens date picker)
  - Display override status if set

### Import/Export Affected

**view_inventory.json (F030/F040):**
```json
{
  "inventory_id": 101,
  // ... context fields ...
  
  // Editable fields (UPDATED)
  "quantity": 2.5,
  "location": "Pantry Shelf 2",
  "calculated_expiration_date": "2025-12-01",  // NEW (computed)
  "expiration_date_override": null,             // NEW (user override)
  "expiration_date": "2025-12-01",              // DEPRECATED (kept for migration)
  "opened_date": null,
  "lot_or_batch": null,
  "notes": null
}
```

**editable_fields update:**
```json
"editable_fields": [
  "quantity",
  "location",
  "expiration_date_override",  // NEW (replaces expiration_date)
  "opened_date",
  "lot_or_batch",
  "notes"
]
```

---

## Migration Strategy

### Database Migration

**Step 1: Add New Columns (Non-Breaking)**
```sql
ALTER TABLE ingredients ADD COLUMN shelf_life_days INTEGER NULL;
ALTER TABLE products ADD COLUMN shelf_life_days INTEGER NULL;
ALTER TABLE inventory_items ADD COLUMN calculated_expiration_date DATE NULL;
ALTER TABLE inventory_items ADD COLUMN expiration_date_override DATE NULL;
```

**Step 2: Populate Shelf Life Defaults**
```python
# Example: Common shelf life values by category
SHELF_LIFE_DEFAULTS = {
    "Flours & Starches": 365,      # 1 year
    "Sugars & Sweeteners": 730,    # 2 years
    "Chocolate & Cocoa": 365,      # 1 year
    "Spices & Extracts": 1095,     # 3 years
    "Leavening Agents": 365,       # 1 year
    "Nuts & Seeds": 180,           # 6 months
    "Dairy & Eggs": 30,            # 1 month (refrigerated)
    "Fruits": 14,                  # 2 weeks (fresh)
    # ... etc
}

for ingredient in session.query(Ingredient):
    if not ingredient.shelf_life_days:
        # Use category default if available
        default = SHELF_LIFE_DEFAULTS.get(ingredient.category)
        if default:
            ingredient.shelf_life_days = default
```

**Step 3: Migrate Existing Expiration Dates**
```python
for item in session.query(InventoryItem).filter(
    InventoryItem.expiration_date.isnot(None)
):
    # Move explicit dates to override field
    item.expiration_date_override = item.expiration_date
    
    # Calculate shelf life if possible
    if item.purchase_date and item.expiration_date:
        days = (item.expiration_date - item.purchase_date).days
        
        # Update ingredient average if not set
        if not item.product.ingredient.shelf_life_days:
            item.product.ingredient.shelf_life_days = days
```

**Step 4: Calculate Missing Expiration Dates**
```python
for item in session.query(InventoryItem):
    if not item.calculated_expiration_date and item.purchase_date:
        # Get shelf life from product or ingredient
        shelf_life = (
            item.product.shelf_life_days or
            item.product.ingredient.shelf_life_days
        )
        if shelf_life:
            item.calculated_expiration_date = (
                item.purchase_date + timedelta(days=shelf_life)
            )
```

**Step 5: Deprecate Old Field (Future)**
```sql
-- Mark column as deprecated (comment only, keep data)
COMMENT ON COLUMN inventory_items.expiration_date IS 
    'DEPRECATED: Use calculated_expiration_date + expiration_date_override instead';
```

---

## User Impact

### Positive Impacts

1. **Eliminates Manual Entry Pain Point**
   - No more typing dates for 20+ items per shopping trip
   - Automatic calculation based on purchase date + shelf life
   - Reduces user effort by 90% (observed in F029 testing)

2. **AI-Assisted Workflow Unblocked**
   - BT Mobile can scan UPCs without needing OCR for dates
   - Purchase imports auto-calculate expiration dates
   - User only intervenes for edge cases (manual override)

3. **Consistent Expiration Logic**
   - Same flour brand always gets same shelf life
   - No user confusion about "Best By" vs "Use By" vs "Sell By"
   - Ingredient-level defaults ensure consistency

4. **Supports Freshness Tracking (F041)**
   - Foundation for shelf life intelligence
   - Planning service can warn about approaching expirations
   - Inventory reports show freshness scores

### Negative Impacts (Mitigated)

1. **Loss of Precision for Some Products**
   - Mitigation: Manual override available for actual printed dates
   - Mitigation: Product-level shelf_life_days overrides for specific brands

2. **Migration Complexity**
   - Mitigation: Phased rollout keeps old field during transition
   - Mitigation: Existing dates preserved via expiration_date_override

3. **User Education Required**
   - Mitigation: UI tooltips explain calculated dates
   - Mitigation: Clear "(calculated)" vs "(manual)" badges

---

## Effort Estimate

**Phase 1 (Schema):** 2-3 hours
- Add columns to models
- Update Alembic migrations
- Update test fixtures

**Phase 2 (Services):** 6-8 hours
- Add shelf_life_days CRUD operations
- Implement calculation logic in inventory service
- Add effective_expiration_date property
- Update all service methods to use new field

**Phase 3 (UI):** 8-12 hours
- Update ingredients tab (add shelf_life_days)
- Update inventory tab (show calculated dates)
- Update add inventory dialog (remove manual entry)
- Add override functionality (button + date picker)

**Phase 4 (Migration):** 4-6 hours
- Write migration script
- Export current data
- Run calculations for averages
- Populate new fields
- Validate results

**Phase 5 (Testing):** 6-8 hours
- Unit tests for calculation logic
- Integration tests for service methods
- UI tests for display and override
- Migration validation

**Total Estimate:** 26-37 hours (3.5-5 working days)

---

## Dependencies

**Upstream (Required Before This):**
- None - can be implemented anytime

**Downstream (Blocked Until This):**
- F041: Shelf Life & Freshness Tracking (depends on shelf_life_days field)
- F042: Purchase Workflow & AI Assist (benefits from auto-calculation)

**Related Technical Debt:**
- TD-001: unit_price field naming (similar usability confusion)

---

## Related Documents

- **Requirements:** `docs/requirements/req_inventory.md` Section 2.4 (Expiration Tracking)
- **Feature Spec:** `docs/design/_F042_shelf_life_freshness_tracking.md` (partial spec exists)
- **Constitution:** Principle I (User-Centric Design - reduce manual entry friction)
- **User Testing:** `docs/user_testing/2025-12-25_inventory_entry_session.md` (expiration pain point identified)

---

## Recommendation

**Priority: Medium** - Should be addressed before F041/F042 implementation.

**Rationale:**
- Solves real user pain point (manual date entry friction)
- Enables AI-assisted workflows (BT Mobile purchase imports)
- Foundation for shelf life intelligence (F041)
- Non-breaking migration path available

**Suggested Timeline:**
- Implement during F041 (Shelf Life & Freshness Tracking) development
- Deprecation complete before F042 (Purchase Workflow) rollout
- Field removal deferred to schema v5.0 (post-Phase 3)

---

**END OF TECHNICAL DEBT DOCUMENT**
