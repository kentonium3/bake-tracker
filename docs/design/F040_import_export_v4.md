# F040: Import/Export System Upgrade (v4.0)

**Feature ID**: F040
**Feature Name**: Import/Export System Upgrade (Schema v4.0)
**Priority**: **CRITICAL (P0 - BLOCKS USER TESTING)**
**Status**: Design Specification  
**Created**: 2026-01-06
**Dependencies**: F037 Recipe Redesign ✅, F039 Planning Workspace Spec ✅
**Blocks**: User testing of F037/F038/F039, Sample data imports

---

## Executive Summary

**THE BLOCKER**: F037 (Recipe Redesign) and F039 (Planning Workspace) introduce schema changes that break current import/export system. Cannot load sample data or test new features without this upgrade.

**THE SOLUTION**: Upgrade import/export to v4.0 schema supporting:
1. F037 recipe structure (template/snapshot, yield modes, variants)
2. F039 event requirements (output_mode, EventAssemblyTarget)
3. BT Mobile purchases (UPC matching)
4. BT Mobile inventory updates (percentage-based corrections)

**SCOPE**: Service layer only (no BT Mobile app development). Two separate import workflows (purchases vs inventory updates). CLI + programmatic interfaces. No backward compatibility (user refactors externally).

**EFFORT**: 36-49 hours (4.5-6 working days)

---

## Problem Statement

### Current Blocker Status

**F037 Recipe Import BROKEN:**
```python
# Current v3.6 recipe schema
{
  "name": "Sugar Cookie",
  "yield_quantity": 48,
  "ingredients": [...]  # Flat list
}

# New F037 recipe model
- yield_mode (fixed, scaled)
- base_yield, scaling_factor
- base_ingredients vs variant_ingredients
- variants[] with finished_unit linkages

# Result: Cannot import recipes with new schema
```

**F039 Event Import INCOMPLETE:**
```python
# Missing in v3.6
- Event.output_mode field
- EventAssemblyTarget properly structured

# Result: Cannot test Planning Workspace
```

**BT Mobile Workflows NOT SUPPORTED:**
```python
# Purchase import: UPC → Product matching needed
# Inventory updates: Percentage → Quantity calc needed

# Result: AI-assisted workflows blocked
```

### User Impact

**Cannot proceed with user testing:**
- F037 recipes cannot be imported → No recipe testing
- F039 events cannot be configured → No planning testing  
- Sample data outdated → Fresh start blocked
- BT Mobile workflows undefined → AI workflow blocked

**Manual workarounds too costly:**
- Recreating 50+ recipes manually: 8-10 hours
- Configuring 10+ events manually: 2-3 hours
- Total: 10-13 hours of manual data entry PER test cycle

---

## Solution Architecture

### Three-Part Solution

**Part 1: Core Schema Upgrade (F037/F039)**
- Update recipe import/export for new structure
- Update event import/export for output_mode
- Bump schema version to 4.0

**Part 2: BT Mobile Purchase Import**
- JSON schema for UPC-based purchases
- UPC → Product matching with resolution
- Auto-create InventoryItem from purchases

**Part 3: BT Mobile Inventory Updates**
- JSON schema for percentage-based updates
- Percentage → Quantity calculation
- FIFO inventory item selection + adjustment

### Service Organization

**Single service with separate handlers:**
```python
# src/services/import_export_service.py

# Main unified import (catalog + events)
def import_all_from_json_v4(file_path, mode="merge") -> ImportResult

# BT Mobile workflows
def import_purchases_from_bt_mobile(file_path) -> ImportResult
def import_inventory_updates_from_bt_mobile(file_path) -> ImportResult

# Export (updated for v4.0)
def export_all_to_json_v4(file_path) -> ExportResult
```

---

## Part 1: Core Schema Upgrade

### 1.1 Recipe Import Schema (NEW)

```json
{
  "recipes": [
    {
      "name": "Sugar Cookie",
      "category": "Cookies",
      "yield_mode": "scaled",
      "base_yield": 48,
      "scaling_factor": 1.0,
      "yield_unit": "cookies",
      "base_ingredients": [
        {
          "ingredient_slug": "all_purpose_flour",
          "quantity": 2.0,
          "unit": "cup",
          "is_base": true
        }
      ],
      "variants": [
        {
          "name": "Chocolate Chip",
          "finished_unit_slug": "chocolate_chip_cookie",
          "ingredient_changes": [
            {
              "action": "add",
              "ingredient_slug": "chocolate_chips",
              "quantity": 0.5,
              "unit": "cup"
            }
          ]
        },
        {
          "name": "Plain",
          "finished_unit_slug": "plain_sugar_cookie",
          "ingredient_changes": []
        }
      ]
    }
  ]
}
```

**Import Logic:**
1. Create Recipe with yield_mode, base_yield, scaling_factor
2. Create RecipeIngredients with is_base=true flag
3. For each variant:
   - Link to finished_unit by slug
   - Create variant-specific ingredient additions/changes

**Validation:**
- yield_mode must be "fixed" or "scaled"
- base_yield required if yield_mode="scaled"
- All ingredient_slugs must reference existing L2 ingredients
- All finished_unit_slugs must reference existing FinishedUnits
- ingredient_changes.action must be "add", "remove", or "modify"

### 1.2 Event Import Schema (ENHANCED)

```json
{
  "events": [
    {
      "name": "Christmas 2025",
      "event_date": "2025-12-25",
      "year": 2025,
      "output_mode": "bundled",
      "notes": "Annual holiday gifts",
      "event_assembly_targets": [
        {
          "finished_good_slug": "holiday_gift_bag",
          "target_quantity": 50,
          "notes": "6 cookies + 3 brownies each"
        }
      ],
      "event_production_targets": []
    }
  ]
}
```

**Import Logic:**
1. Create Event with output_mode field
2. Create EventAssemblyTarget records (if output_mode="bundled")
3. Create EventProductionTarget records (if output_mode="bulk_count")

**Validation:**
- output_mode must be "bulk_count", "bundled", or "packaged"
- If output_mode="bundled", event_assembly_targets required
- If output_mode="bulk_count", event_production_targets required
- All finished_good_slugs must reference existing FinishedGoods
- All recipe_names must reference existing Recipes

---

## Part 2: BT Mobile Purchase Import

### 2.1 Purchase Import JSON Schema

```json
{
  "schema_version": "4.0",
  "import_type": "purchases",
  "created_at": "2026-01-06T14:30:00Z",
  "source": "bt_mobile",
  "supplier": "Costco Waltham MA",
  "purchases": [
    {
      "upc": "051000127952",
      "gtin": "00051000127952",
      "scanned_at": "2026-01-06T14:15:23Z",
      "unit_price": 7.99,
      "quantity_purchased": 1.0,
      "supplier": "Costco Waltham MA",
      "notes": "Weekly shopping"
    }
  ]
}
```

### 2.2 UPC Matching Algorithm

```python
def import_purchases_from_bt_mobile(file_path: str) -> ImportResult:
    """
    Import purchases from BT Mobile app.
    
    Workflow:
    1. Read purchases JSON, validate schema
    2. For each purchase:
       a. Try UPC match: products.upc_code == purchase.upc
       b. If no match: Collect for resolution
    3. Present resolution UI for unknown UPCs
    4. Create Purchase records + InventoryItems
    5. Return import summary
    """
    result = ImportResult()
    unmatched_upcs = []
    
    # Read JSON
    with open(file_path) as f:
        data = json.load(f)
    
    # Validate schema
    if data.get("schema_version") != "4.0":
        result.add_error("file", file_path, "Unsupported schema version")
        return result
    
    if data.get("import_type") != "purchases":
        result.add_error("file", file_path, "Wrong import type (expected 'purchases')")
        return result
    
    # Default supplier from top-level
    default_supplier = data.get("supplier")
    
    with session_scope() as session:
        for purchase_data in data.get("purchases", []):
            upc = purchase_data.get("upc")
            
            # Try UPC match
            product = session.query(Product).filter_by(upc_code=upc).first()
            
            if not product:
                # Collect for resolution
                unmatched_upcs.append(purchase_data)
                continue
            
            # Resolve supplier
            supplier_name = purchase_data.get("supplier", default_supplier)
            supplier = resolve_supplier(supplier_name, session)
            
            # Create Purchase
            purchase = Purchase(
                product_id=product.id,
                supplier_id=supplier.id,
                purchase_date=parse_date(purchase_data.get("scanned_at")),
                unit_price=Decimal(str(purchase_data.get("unit_price"))),
                quantity_purchased=Decimal(str(purchase_data.get("quantity_purchased"))),
                notes=purchase_data.get("notes")
            )
            session.add(purchase)
            session.flush()
            
            # Create InventoryItem
            inventory_item = InventoryItem(
                product_id=product.id,
                purchase_id=purchase.id,
                current_quantity=purchase.quantity_purchased,
                purchase_date=purchase.purchase_date
            )
            session.add(inventory_item)
            
            result.add_success("purchase")
        
        # Handle unmatched UPCs
        if unmatched_upcs:
            resolution = resolve_unknown_upcs(unmatched_upcs, session)
            result.merge(resolution)
        
        session.commit()
    
    return result
```

### 2.3 Unknown UPC Resolution

**Resolution Dialog:**
```
┌─ Unknown UPCs Found ───────────────────────────────┐
│                                                     │
│ 3 products could not be matched automatically.     │
│ Please resolve each item:                          │
│                                                     │
│ UPC: 028000215316                                  │
│ Price: $4.29 (scanned at 14:18:45)                 │
│                                                     │
│ ○ Map to existing product:                         │
│   [Search products... ▼]                           │
│                                                     │
│ ○ Create new product:                              │
│   Ingredient: [Select ▼]                           │
│   Brand: [______]                                  │
│   Product Name: [______]                           │
│   Package Size: [______]                           │
│                                                     │
│ ○ Skip this purchase                               │
│                                                     │
│ [< Previous] [Next >] [Apply]                      │
└─────────────────────────────────────────────────────┘
```

**Resolution Logic:**
```python
def resolve_unknown_upcs(unmatched: List[Dict], session) -> ImportResult:
    """
    Present UI for mapping unknown UPCs to products.
    
    Options:
    1. Map to existing product (select from dropdown)
    2. Create new product (fill form, auto-assign UPC)
    3. Skip purchase
    """
    result = ImportResult()
    
    for purchase_data in unmatched:
        # Show dialog, get user choice
        choice = show_upc_resolution_dialog(purchase_data)
        
        if choice.action == "map_existing":
            product = choice.product
            # Create purchase with mapped product
            create_purchase(product, purchase_data, session)
            result.add_success("purchase")
            
        elif choice.action == "create_new":
            # Create product with UPC
            product = Product(
                ingredient_id=choice.ingredient_id,
                brand=choice.brand,
                product_name=choice.product_name,
                upc_code=purchase_data["upc"],
                **choice.product_details
            )
            session.add(product)
            session.flush()
            
            # Create purchase
            create_purchase(product, purchase_data, session)
            result.add_success("product")
            result.add_success("purchase")
            
        elif choice.action == "skip":
            result.add_skip("purchase", purchase_data["upc"], "Skipped by user")
    
    return result
```

---

## Part 3: BT Mobile Inventory Updates

### 3.1 Inventory Update JSON Schema

```json
{
  "schema_version": "4.0",
  "import_type": "inventory_updates",
  "created_at": "2026-01-06T09:15:00Z",
  "source": "bt_mobile",
  "inventory_updates": [
    {
      "upc": "051000127952",
      "gtin": "00051000127952",
      "scanned_at": "2026-01-06T09:10:12Z",
      "remaining_percentage": 30,
      "update_method": "percentage_based",
      "notes": "Pre-production check"
    }
  ]
}
```

### 3.2 Percentage → Quantity Algorithm

```python
def import_inventory_updates_from_bt_mobile(file_path: str) -> ImportResult:
    """
    Import inventory level updates from BT Mobile app.
    
    Workflow:
    1. Read inventory_updates JSON, validate schema
    2. For each update:
       a. Lookup Product by UPC
       b. Find active inventory items (current_quantity > 0)
       c. Calculate adjustment: target - current
       d. Create InventoryDepletion (or addition if positive)
       e. Update current_quantity
    3. Return import summary
    """
    result = ImportResult()
    
    # Read JSON
    with open(file_path) as f:
        data = json.load(f)
    
    # Validate schema
    if data.get("schema_version") != "4.0":
        result.add_error("file", file_path, "Unsupported schema version")
        return result
    
    if data.get("import_type") != "inventory_updates":
        result.add_error("file", file_path, "Wrong import type")
        return result
    
    with session_scope() as session:
        for update_data in data.get("inventory_updates", []):
            upc = update_data.get("upc")
            remaining_pct = update_data.get("remaining_percentage")
            
            # Lookup Product by UPC
            product = session.query(Product).filter_by(upc_code=upc).first()
            if not product:
                result.add_error("inventory_update", upc, f"Product not found for UPC {upc}")
                continue
            
            # Find active inventory items
            inventory_items = session.query(InventoryItem).filter(
                InventoryItem.product_id == product.id,
                InventoryItem.current_quantity > 0
            ).order_by(InventoryItem.purchase_date.asc()).all()  # FIFO order
            
            if not inventory_items:
                result.add_warning("inventory_update", upc, "No active inventory found")
                continue
            
            # Handle multiple inventory items
            if len(inventory_items) > 1:
                # TODO: Prompt user to select which bag
                # For now: Apply to oldest (FIFO)
                inventory_item = inventory_items[0]
            else:
                inventory_item = inventory_items[0]
            
            # Calculate adjustment
            adjustment = calculate_percentage_adjustment(
                inventory_item,
                remaining_pct
            )
            
            if adjustment == 0:
                result.add_skip("inventory_update", upc, "No adjustment needed")
                continue
            
            # Apply adjustment
            apply_inventory_adjustment(
                inventory_item,
                adjustment,
                reason="physical_count_correction",
                notes=update_data.get("notes"),
                session=session
            )
            
            result.add_success("inventory_update")
        
        session.commit()
    
    return result


def calculate_percentage_adjustment(
    inventory_item: InventoryItem,
    remaining_percentage: int
) -> Decimal:
    """
    Calculate quantity adjustment based on percentage.
    
    Logic:
    1. Get original quantity from linked purchase
    2. Calculate target = original * (percentage / 100)
    3. Calculate adjustment = target - current
    4. Return adjustment (negative = depletion, positive = addition)
    
    Example:
    - Original: 25 lbs flour (from purchase)
    - Current: 18 lbs (user has been using it)
    - User scans: "30% remaining"
    - Target: 25 * 0.30 = 7.5 lbs
    - Adjustment: 7.5 - 18 = -10.5 lbs
    - System depletes 10.5 lbs
    """
    if not inventory_item.purchase_id:
        raise ValueError("Cannot calculate percentage - no linked purchase")
    
    purchase = inventory_item.purchase
    original_quantity = purchase.quantity_purchased
    
    # Calculate target
    target_quantity = original_quantity * (Decimal(remaining_percentage) / Decimal(100))
    
    # Calculate adjustment
    current_quantity = inventory_item.current_quantity
    adjustment = target_quantity - current_quantity
    
    return adjustment


def apply_inventory_adjustment(
    inventory_item: InventoryItem,
    adjustment: Decimal,
    reason: str,
    notes: str,
    session
):
    """
    Apply inventory adjustment via InventoryDepletion record.
    
    Creates depletion record, updates current_quantity.
    Supports both depletions (negative) and additions (positive).
    """
    # Validate won't go negative
    new_quantity = inventory_item.current_quantity + adjustment
    if new_quantity < 0:
        raise ValueError(
            f"Adjustment would result in negative inventory: "
            f"{inventory_item.current_quantity} + {adjustment} = {new_quantity}"
        )
    
    # Create depletion record
    depletion = InventoryDepletion(
        inventory_item_id=inventory_item.id,
        purchase_id=inventory_item.purchase_id,
        quantity_depleted=adjustment,  # Can be positive or negative
        depletion_date=datetime.now(),
        depletion_reason=reason,
        related_entity_type="bt_mobile_update",
        related_entity_id=None,
        notes=notes,
        cost=abs(adjustment) * inventory_item.unit_cost
    )
    session.add(depletion)
    
    # Update current quantity
    inventory_item.current_quantity = new_quantity
```

---

## Implementation Phases

### Phase 1: Core Schema Updates (12-16 hours)

**WP01: F037 Recipe Import/Export (6-8 hrs)**
- Update `export_recipes_to_json()` for new schema
- Update recipe import in `import_all_from_json_v4()`
- Handle yield_mode, base_ingredients, variants
- Create finished_unit linkages
- Validation: yield_mode, ingredient_slugs, finished_unit_slugs

**WP02: F039 Event Import/Export (4-6 hrs)**
- Add output_mode to event export
- Update event import for output_mode
- Integrate EventAssemblyTarget (already in v3.6)
- Validation: output_mode matches targets

**WP03: Schema Version Bump (2 hrs)**
- Version "4.0" in exports
- Rename functions: `_v3()` → `_v4()`
- Update documentation

### Phase 2: BT Mobile Workflows (10-14 hours)

**WP04: Purchase Import (6-8 hrs)**
- `import_purchases_from_bt_mobile()` method
- UPC matching logic
- Unknown UPC resolution dialog
- Create Purchase + InventoryItem

**WP05: Inventory Update Import (4-6 hrs)**
- `import_inventory_updates_from_bt_mobile()` method
- Percentage → quantity calculation
- FIFO inventory item selection
- Create InventoryDepletion + update quantity

### Phase 3: Testing & Documentation (8-12 hours)

**WP06: Unit Tests (4-6 hrs)**
- Recipe import (yield modes, variants)
- Event import (output_mode, targets)
- Purchase import (UPC matching)
- Inventory update (percentage calc)

**WP07: Integration Tests (2-3 hrs)**
- Full export → import round-trip
- Mode testing (merge vs replace)
- Error handling and rollback

**WP08: Sample Data & Docs (2-3 hrs)**
- Update `import_template.json` to v4.0
- Create `sample_catalog_v4.json`
- Update import/export docs
- CLI usage examples

---

## Success Criteria

**Must Have:**
- [ ] F037 recipe import/export with new schema
- [ ] F039 event import/export with output_mode
- [ ] UPC-based purchase imports with resolution
- [ ] Percentage-based inventory updates
- [ ] Both CLI and programmatic access
- [ ] Round-trip export → import preserves data
- [ ] Error messages actionable and specific

**Should Have:**
- [ ] Import template v4.0
- [ ] Sample data files updated
- [ ] Documentation comprehensive
- [ ] Unknown UPC resolution UI polished

**Nice to Have:**
- [ ] File monitoring for auto-import (deferred to F042)
- [ ] Bulk validation preview
- [ ] Import conflict resolution UI

---

## CLI Usage

```bash
# Main catalog import/export
bake-tracker export-catalog catalog_v4.json
bake-tracker import-catalog catalog_v4.json --mode merge

# BT Mobile workflows
bake-tracker import-purchases purchases_20260106_143000.json
bake-tracker import-inventory-update inventory_update_20260106_091500.json

# Auto-detect type
bake-tracker import-bt-mobile <file.json>
```

---

## Constitutional Compliance

**Principle I (Data Integrity):**
- ✓ FK validation before Purchase/InventoryItem creation
- ✓ Depletion records immutable (audit trail)
- ✓ Validation prevents negative inventory

**Principle V (Layered Architecture):**
- ✓ Service methods in import_export_service
- ✓ UI calls service, doesn't do business logic
- ✓ Existing models reused (no schema changes)

---

## Dependencies

**Upstream (Blocks This):**
- ✅ F037 Recipe Redesign (schema exists)
- ✅ F039 Planning Workspace (spec complete)

**Downstream (This Blocks):**
- ❌ User testing (cannot load sample data)
- ❌ F042 BT Mobile Integration (needs import handlers)

---

## Related Documents

- **Requirements:** `docs/requirements/req_inventory.md` Section 3.2
- **BT Mobile Workflows:** `BT_MOBILE_WORKFLOWS.md` (this session)
- **Discovery:** `IMPORT_EXPORT_DISCOVERY_PLAN.md` (this session)
- **Constitution:** `.kittify/memory/constitution.md`

---

**END OF SPECIFICATION**
