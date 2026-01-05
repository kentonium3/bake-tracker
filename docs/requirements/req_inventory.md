# Inventory - Requirements Document

**Component:** Inventory (Ingredient Inventory Management)
**Version:** 0.2
**Last Updated:** 2025-01-05
**Status:** Current
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Inventory is the **ingredient tracking system** in bake-tracker that manages raw materials from purchase through consumption in production. The inventory system uses FIFO (First-In, First-Out) methodology to ensure accurate cost tracking and proper ingredient rotation.

### 1.2 Business Purpose

The Inventory system serves critical business functions:

1. **Ingredient Tracking:** Know what ingredients are available and in what quantities
2. **FIFO Cost Accuracy:** Track ingredient costs accurately using first-in, first-out methodology
3. **Depletion Management:** Automatically deplete inventory when recipes are executed
4. **Expiration Awareness:** Track shelf life and freshness of ingredients (F041)
5. **Purchase Planning:** Identify what needs to be purchased based on gaps

### 1.3 Design Rationale

**FIFO Methodology:** Unlike finished goods (which use simple counts), ingredient inventory requires FIFO tracking because:
- Ingredients purchased at different times have different costs
- Older ingredients should be used first (freshness, rotation)
- Cost of goods sold (COGS) must be calculated accurately

**Purchase-Based Tracking:** Inventory is tracked at the purchase level, not aggregated. Each purchase becomes an inventory item with its own:
- Purchase date
- Purchase price
- Quantity remaining
- Shelf life / expiration date (F041)

---

## 2. Inventory Model

### 2.1 Core Concepts

**Purchase:** A transaction where ingredients are acquired
- Links to Product (which ingredient was purchased)
- Quantity and unit
- Purchase price (total cost)
- Purchase date
- Vendor (optional)
- Shelf life override (F041 - optional)

**Inventory Item:** A purchase that has remaining quantity
- Initially: inventory_quantity = purchase_quantity
- As consumed: inventory_quantity decreases
- When depleted: inventory_quantity = 0 (archived)

**FIFO Depletion:** When a recipe consumes ingredients:
- System finds oldest purchases first (by purchase_date)
- Depletes from oldest until quantity needed is satisfied
- May span multiple purchases for a single recipe execution

### 2.2 Hierarchy

```
Ingredient (catalog - what can be purchased)
  └─ Product (catalog - specific purchasable item)
       └─ Purchase (transaction - when/how much was bought)
            └─ InventoryItem (current state - how much remains)
                 └─ InventoryDepletion (transaction - consumption history)
```

---

## 3. Scope & Boundaries

### 3.1 In Scope

**Purchase Management:**
- ✅ Create purchases linked to products
- ✅ Track purchase quantity, unit, price, date
- ✅ Optional vendor assignment
- ✅ Optional shelf life override per purchase (F041)
- ✅ Edit purchases (before consumption begins)

**Inventory Tracking:**
- ✅ Automatic inventory item creation from purchase
- ✅ Track remaining quantity per purchase
- ✅ FIFO depletion when recipes consume ingredients
- ✅ Depletion history (who consumed, when, how much)
- ✅ Multi-purchase spanning (recipe needs more than one purchase has)

**Inventory Queries:**
- ✅ Current inventory by ingredient
- ✅ Current inventory by product
- ✅ Available quantity for ingredient (across all purchases)
- ✅ Expiration/freshness status (F041)
- ✅ Low stock alerts (future)

**FIFO Operations:**
- ✅ Automatic FIFO selection on depletion
- ✅ Multi-purchase depletion in single operation
- ✅ Partial depletion (consume portion of purchase)
- ✅ Cost calculation (weighted average from FIFO depletes)

### 3.2 Out of Scope (Phase 2)

**Phase 2 (Now In Scope):**
- ✅ Manual inventory adjustments (spoilage, gifts, corrections, ad hoc usage outside app)

**Explicitly NOT Yet Supported (Future Phases):**
- ❌ Inventory transfers between locations
- ❌ Inventory reservations (allocation before consumption)
- ❌ Batch/lot number tracking
- ❌ Supplier quality tracking
- ❌ Inventory value reporting (total $ on hand)

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. Record purchases so I know what ingredients I have
2. See what's currently in inventory before planning
3. Have the system automatically deplete oldest ingredients first
4. Know when ingredients are expiring soon
5. See what I need to purchase based on planning gaps

**As a cost tracker, I want to:**
1. Know the total cost of ingredients used in a recipe
2. Calculate accurate COGS using FIFO methodology
3. Track ingredient price changes over time

**As an inventory manager, I want to:**
1. View all inventory for a specific ingredient
2. See purchase history and depletion history
3. Identify low stock items
4. Identify expiring items (F041)

### 4.2 Use Case: Record Purchase

**Actor:** Baker
**Precondition:** Products defined in system

**Main Flow (AI-Assisted Batch Import - Phase 2):**
1. User shops at store (Costco, Wegmans, etc.)
2. User opens Google AI Studio app on phone
3. For each item:
   a. User captures photo of product barcode (UPC)
   b. User captures photo of price tag
4. AI Studio extracts UPC codes and prices, generates JSON purchase list
5. User exports/uploads JSON file to sync folder (Dropbox/Google Drive)
6. Desktop app detects new purchase file in monitored folder
7. System matches UPCs to products via learned mappings:
   - Known UPCs: Auto-match to products
   - Unknown UPCs: Interactive resolution UI (map to existing product or create new)
8. System creates Purchase records with supplier, date, prices
9. System creates InventoryItem records linked to purchases
10. System propagates ingredient L0/L1/L2 from products
11. System calculates expiration dates from shelf life
12. User confirms import

**Alternative Flow (Manual Entry - Phase 2 Fallback):**
1. User opens Purchases tab
2. Clicks "Add Purchase"
3. Selects product: "King Arthur All-Purpose Flour 25lb"
4. Enters quantity: 25, unit: lb
5. Enters purchase price: $15.99
6. Enters purchase date: 2025-01-04
7. Optionally selects vendor: "Restaurant Depot"
8. Optionally overrides shelf life: 6 months (from product/ingredient default)
9. User saves

**Postconditions:**
- Purchase record(s) created
- Inventory item(s) created with quantities available
- Ingredient L0/L1/L2 propagated from products
- Expiration dates calculated (purchase_date + shelf_life)
- FIFO cost basis established

**Notes:**
- AI-assisted workflow reduces 30-45 minute manual entry to <5 minutes
- Proof of concept validated: AI Studio successfully generates JSON from photos
- Phase 2 implementation requires file monitoring and UPC matching logic
- Manual entry remains available for edge cases and low-volume purchases
- See F036 (Purchase Workflow & AI Assist) for detailed design

### 4.3 Use Case: FIFO Depletion During Production

**Actor:** System (automatic during production run)
**Precondition:** Recipe requires 10 cups flour, multiple purchases exist

**Main Flow:**
1. User executes production run for "Sugar Cookie" recipe
2. Recipe requires: 10 cups flour
3. System queries inventory for "flour" ingredient:
   - Purchase A: 2024-12-01, 5 cups remaining
   - Purchase B: 2024-12-15, 8 cups remaining
   - Purchase C: 2025-01-02, 20 cups remaining
4. System applies FIFO (oldest first):
   - Deplete 5 cups from Purchase A (now 0 remaining)
   - Deplete 5 cups from Purchase B (now 3 remaining)
5. System creates depletion records:
   - InventoryDepletion: Purchase A, -5 cups, ProductionRun #123
   - InventoryDepletion: Purchase B, -5 cups, ProductionRun #123
6. System calculates weighted cost:
   - Purchase A: 5 cups @ $0.50/cup = $2.50
   - Purchase B: 5 cups @ $0.60/cup = $3.00
   - Total cost: $5.50 for 10 cups

**Postconditions:**
- Inventory depleted via FIFO
- Depletion history recorded
- Accurate cost calculated
- Purchase A fully consumed (archived)
- Purchase B partially consumed

### 4.4 Use Case: Check Inventory Before Planning

**Actor:** Planning System (Automated - Phase 2)
**Precondition:** Event planning in progress, recipes selected

**Main Flow (Automated - Phase 2):**
1. User planning event via Planning Workspace (see req_planning.md)
2. System automatically aggregates ingredient requirements from selected recipes
3. System queries available inventory for each ingredient
4. System calculates gaps: required - available = gap
5. System presents integrated view:
   - Recipe requirements with batch calculations
   - Current inventory levels per ingredient
   - Purchase gaps highlighted
   - Shopping list auto-generated for gaps
6. User reviews and confirms production plan

**Alternative Flow (Manual Check - Phase 2 Supported):**
1. User opens Inventory tab manually
2. Filters by ingredient: "All-Purpose Flour"
3. System shows:
   - King Arthur AP 25lb: 15 cups (from 2 purchases)
   - Bob's Red Mill AP 5lb: 3 cups (from 1 purchase)
   - Total available: 18 cups
4. User manually compares to recipe requirements
5. User notes purchase needs

**Postconditions:**
- User aware of inventory status
- Purchase gaps identified automatically
- Shopping list generated from gaps
- Planning adjusted based on available inventory

**Notes:**
- Phase 2 prioritizes automated planning workflow (see req_planning.md)
- Manual inventory checking remains available for ad hoc verification
- System automatically accounts for FIFO depletion from existing inventory
- Planning system considers both on-hand and in-progress purchases

### 4.5 Use Case: Expiration Awareness (F041)

**Actor:** Baker
**Precondition:** Purchases have shelf life data

**Main Flow:**
1. User opens Inventory tab
2. System displays freshness indicators:
   - Flour (Purchase A): 🟢 Fresh (expires in 45 days)
   - Baking Powder (Purchase B): 🟡 Expiring Soon (expires in 5 days)
   - Vanilla Extract (Purchase C): 🔴 Expired (expired 2 days ago)
3. User prioritizes using Baking Powder before expiration
4. User notes Vanilla Extract for disposal/replacement

**Postconditions:**
- User aware of expiration status
- Can prioritize ingredient usage
- Can plan purchases for expiring items

---

## 5. Functional Requirements

### 5.1 Purchase Management

**REQ-INV-001:** System shall support purchase creation linked to a product
**REQ-INV-002:** Purchase shall record: product_id, quantity, unit, purchase_price, purchase_date
**REQ-INV-003:** Purchase shall optionally record: vendor_id, notes
**REQ-INV-004:** Purchase shall optionally override shelf_life_days (F041)
**REQ-INV-005:** System shall auto-propagate ingredient L0/L1/L2 from product
**REQ-INV-006:** System shall validate purchase quantity is positive
**REQ-INV-007:** System shall validate purchase price is non-negative
**REQ-INV-008:** System shall allow purchase editing before any depletion occurs
**REQ-INV-009:** System shall prevent purchase editing after depletion begins
**REQ-INV-010:** System shall allow purchase deletion if no depletion history exists

### 5.2 Inventory Item Creation

**REQ-INV-011:** System shall automatically create inventory item from purchase
**REQ-INV-012:** Initial inventory_quantity = purchase_quantity
**REQ-INV-013:** Inventory item shall track: purchase_id, current_quantity, unit
**REQ-INV-014:** Inventory item shall compute: expiration_date (purchase_date + shelf_life)
**REQ-INV-015:** System shall update inventory_quantity as depletions occur

### 5.3 FIFO Depletion

**REQ-INV-016:** System shall deplete inventory using FIFO methodology
**REQ-INV-017:** FIFO ordering: oldest purchase_date first
**REQ-INV-018:** System shall support partial depletion (consume portion of purchase)
**REQ-INV-019:** System shall support multi-purchase depletion (span multiple purchases)
**REQ-INV-020:** System shall validate sufficient inventory before depletion
**REQ-INV-021:** System shall create depletion record for each purchase consumed
**REQ-INV-022:** Depletion record shall track: inventory_item_id, quantity_depleted, depletion_reason, related_entity (production_run_id, etc.)

### 5.4 Inventory Queries

**REQ-INV-023:** System shall query inventory by ingredient (across all products)
**REQ-INV-024:** System shall query inventory by product (specific product only)
**REQ-INV-025:** System shall calculate available quantity (sum of remaining quantities)
**REQ-INV-026:** System shall filter inventory by freshness status (fresh, expiring, expired) (F041)
**REQ-INV-027:** System shall show inventory sorted by purchase_date (FIFO order)
**REQ-INV-028:** System shall show depletion history per inventory item

### 5.5 Cost Calculation

**REQ-INV-029:** System shall calculate unit cost per purchase (purchase_price / purchase_quantity)
**REQ-INV-030:** System shall calculate weighted cost when depleting across purchases
**REQ-INV-031:** Weighted cost = sum(quantity_from_purchase × unit_cost_of_purchase)
**REQ-INV-032:** System shall track total cost per depletion operation

### 5.6 Shelf Life Integration (F041)

**REQ-INV-033:** System shall compute expiration_date from purchase_date + effective_shelf_life
**REQ-INV-034:** Effective shelf life priority: Purchase override > Ingredient (Product is immutable pass-through)
**REQ-INV-035:** System shall display freshness indicators in inventory list
**REQ-INV-036:** System shall calculate days_until_expiration for each inventory item
**REQ-INV-037:** Freshness status: FRESH (>7 days), EXPIRING_SOON (0-7 days), EXPIRED (<0 days)

---

## 6. Non-Functional Requirements

### 6.1 Performance

**REQ-INV-NFR-001:** FIFO query shall complete in <100ms for 1000+ inventory items
**REQ-INV-NFR-002:** Depletion operation shall complete in <200ms for multi-purchase spanning
**REQ-INV-NFR-003:** Inventory availability query shall complete in <50ms

### 6.2 Data Integrity

**REQ-INV-NFR-004:** Inventory quantity shall never be negative (enforced)
**REQ-INV-NFR-005:** Depletion records shall be immutable (audit trail)
**REQ-INV-NFR-006:** Purchase deletion shall cascade to inventory items (if no depletions)
**REQ-INV-NFR-007:** FIFO ordering shall be deterministic (no ambiguity)

### 6.3 Accuracy

**REQ-INV-NFR-008:** Cost calculations shall be accurate to 2 decimal places
**REQ-INV-NFR-009:** Quantity tracking shall be accurate to unit precision
**REQ-INV-NFR-010:** FIFO depletion shall always consume oldest purchases first

---

## 7. Data Model Summary

### 7.1 Purchase Table Structure

```
Purchase
├─ id (PK)
├─ uuid (unique)
├─ product_id (FK → Product, required)
├─ ingredient_id (FK → Ingredient L2, propagated from product)
├─ ingredient_l0_id (FK → Ingredient L0, propagated)
├─ ingredient_l1_id (FK → Ingredient L1, propagated)
├─ purchase_quantity (decimal, required)
├─ purchase_unit (text, required)
├─ purchase_price (decimal, required)
├─ purchase_date (date, required)
├─ vendor_id (FK → Vendor, optional)
├─ shelf_life_days (int, optional override) [F041]
├─ notes (text, optional)
└─ timestamps
```

### 7.2 Inventory Item Structure (Derived from Purchase)

```
InventoryItem (computed/view or separate table)
├─ purchase_id (FK → Purchase)
├─ product_id (denormalized from purchase)
├─ ingredient_id (denormalized from purchase)
├─ current_quantity (decimal, updated on depletion)
├─ unit (denormalized from purchase)
├─ purchase_date (denormalized from purchase)
├─ unit_cost (computed: purchase_price / purchase_quantity)
├─ expiration_date (computed: purchase_date + effective_shelf_life) [F041]
├─ days_until_expiration (computed: expiration_date - today) [F041]
├─ freshness_status (computed: FRESH/EXPIRING_SOON/EXPIRED) [F041]
```

### 7.3 Inventory Depletion Structure

```
InventoryDepletion
├─ id (PK)
├─ uuid (unique)
├─ inventory_item_id / purchase_id (FK)
├─ quantity_depleted (decimal, negative value)
├─ depletion_date (timestamp)
├─ depletion_reason (enum: production, assembly, adjustment, spoilage, gift)
├─ related_entity_type (enum: production_run, assembly_run, manual)
├─ related_entity_id (polymorphic FK)
├─ cost (decimal, computed at depletion time)
└─ timestamps (immutable)
```

### 7.4 Key Relationships

```
Product
  └─ purchases (many)
       └─ inventory_items (1:1, derived)
            └─ depletions (many)

Ingredient
  └─ purchases (many, via product propagation)
       └─ inventory_items (many)

ProductionRun
  └─ inventory_depletions (many, via related_entity)
```

---

## 8. FIFO Algorithm

### 8.1 FIFO Depletion Process

```python
def deplete_inventory_fifo(ingredient_id, quantity_needed, depletion_reason, related_entity):
    """
    Deplete inventory using FIFO methodology.

    Args:
        ingredient_id: Which ingredient to deplete
        quantity_needed: How much to consume
        depletion_reason: Why (production, assembly, etc.)
        related_entity: What triggered it (production_run, etc.)

    Returns:
        depletions: List of depletion records created
        total_cost: Weighted cost of depleted inventory

    Raises:
        InsufficientInventoryError: Not enough available
    """

    # Step 1: Query available inventory (FIFO order)
    inventory_items = session.query(InventoryItem).filter(
        InventoryItem.ingredient_id == ingredient_id,
        InventoryItem.current_quantity > 0
    ).order_by(
        InventoryItem.purchase_date.asc()  # FIFO: oldest first
    ).all()

    # Step 2: Validate sufficient inventory
    total_available = sum(item.current_quantity for item in inventory_items)
    if total_available < quantity_needed:
        raise InsufficientInventoryError(
            f"Need {quantity_needed}, only {total_available} available"
        )

    # Step 3: Deplete from oldest purchases first
    remaining_needed = quantity_needed
    depletions = []
    total_cost = Decimal(0)

    for item in inventory_items:
        if remaining_needed <= 0:
            break

        # How much to take from this purchase
        quantity_from_this = min(item.current_quantity, remaining_needed)

        # Calculate cost for this portion
        cost_from_this = quantity_from_this * item.unit_cost

        # Create depletion record
        depletion = InventoryDepletion(
            inventory_item_id=item.id,
            quantity_depleted=-quantity_from_this,  # Negative = consumed
            depletion_date=datetime.now(),
            depletion_reason=depletion_reason,
            related_entity_type=related_entity.__class__.__name__,
            related_entity_id=related_entity.id,
            cost=cost_from_this
        )
        session.add(depletion)
        depletions.append(depletion)

        # Update inventory item
        item.current_quantity -= quantity_from_this

        # Accumulate
        remaining_needed -= quantity_from_this
        total_cost += cost_from_this

    session.commit()

    return {
        'depletions': depletions,
        'total_cost': total_cost,
        'quantity_depleted': quantity_needed
    }
```

### 8.2 FIFO Query for Available Inventory

```python
def get_available_inventory(ingredient_id):
    """
    Get available inventory for ingredient, FIFO ordered.

    Returns:
        inventory: [
            {
                purchase_id,
                purchase_date,
                product_name,
                current_quantity,
                unit,
                unit_cost,
                expiration_date,
                freshness_status
            }
        ]
    """
    items = session.query(InventoryItem).filter(
        InventoryItem.ingredient_id == ingredient_id,
        InventoryItem.current_quantity > 0
    ).order_by(
        InventoryItem.purchase_date.asc()
    ).all()

    return [
        {
            'purchase_id': item.purchase_id,
            'purchase_date': item.purchase_date,
            'product_name': item.product.display_name,
            'current_quantity': item.current_quantity,
            'unit': item.unit,
            'unit_cost': item.unit_cost,
            'expiration_date': item.expiration_date,
            'freshness_status': item.freshness_status
        }
        for item in items
    ]
```

---

## 9. UI Requirements

### 9.1 Inventory Tab (List View)

**Display:**
- List of inventory items with current quantities
- Columns: Ingredient | Product | Quantity | Unit | Purchase Date | Freshness | Actions
- Filter: By ingredient (cascading L0/L1/L2), by freshness status
- Sort: By purchase date (FIFO order default), by expiration date

**Freshness Column (F041):**
- 🟢 FRESH (>7 days until expiration)
- 🟡 EXPIRING_SOON (0-7 days until expiration)
- 🔴 EXPIRED (past expiration date)
- (blank) No shelf life data

**Actions:**
- View depletion history
- View purchase details
- (Phase 3: Manual adjustment)

### 9.2 Purchase Entry Form

**Fields:**
- Product: Cascading selector (L0 → L1 → L2 → Product)
- Quantity: Number input
- Unit: Dropdown or auto-fill from product
- Purchase Price: Currency input
- Purchase Date: Date picker (default: today)
- Vendor: Optional dropdown
- Shelf Life Override: Optional time input (days/weeks/months/years) (F041)
- Notes: Optional text area

**Behavior:**
- Auto-populate ingredient from product selection
- Auto-create inventory item on save
- Calculate expiration date from shelf life

### 9.3 Inventory Detail View

**Display:**
- Purchase information (product, date, price, vendor)
- Current quantity remaining
- Original purchase quantity
- Unit cost
- Expiration date and freshness status (F041)
- Depletion history table

**Depletion History Table:**
- Columns: Date | Reason | Related Entity | Quantity | Cost
- Example: "2025-01-04 | Production | Sugar Cookie Batch #123 | -5 cups | $2.50"

---

## 10. Validation Rules

### 10.1 Purchase Validation

| Rule ID     | Validation                  | Error Message                                 |
| ----------- | --------------------------- | --------------------------------------------- |
| VAL-INV-001 | Product required            | "Product must be selected"                    |
| VAL-INV-002 | Quantity must be positive   | "Purchase quantity must be greater than zero" |
| VAL-INV-003 | Price must be non-negative  | "Purchase price cannot be negative"           |
| VAL-INV-004 | Purchase date required      | "Purchase date must be specified"             |
| VAL-INV-005 | Cannot edit after depletion | "Cannot edit: purchase has depletion history" |

### 10.2 Depletion Validation

| Rule ID     | Validation                           | Error Message                                  |
| ----------- | ------------------------------------ | ---------------------------------------------- |
| VAL-INV-006 | Sufficient inventory required        | "Insufficient inventory: need {X}, have {Y}"   |
| VAL-INV-007 | Quantity to deplete must be positive | "Depletion quantity must be greater than zero" |
| VAL-INV-008 | Cannot deplete more than available   | "Cannot deplete {X}: only {Y} available"       |

---

## 11. Acceptance Criteria

### 11.1 Phase 2 (Current) Acceptance

**Must Have:**
- [ ] Purchase creation with product linkage
- [ ] Automatic inventory item creation from purchase
- [ ] FIFO depletion during production runs
- [ ] Multi-purchase spanning in single depletion
- [ ] Depletion history tracking (immutable audit trail)
- [ ] Inventory query by ingredient (available quantity)
- [ ] Weighted cost calculation from FIFO depletions
- [ ] Shelf life integration (F041) with freshness indicators
- [ ] Inventory list view with freshness column
- [ ] Manual inventory adjustments (spoilage, gifts, corrections, ad hoc usage)
- [ ] AI-assisted batch purchase import (Google AI Studio → JSON → import)
- [ ] Automated inventory checking via Planning system (see req_planning.md)

**Should Have:**
- [ ] Purchase editing (before depletion)
- [ ] Depletion history display per purchase
- [ ] Filter inventory by freshness status
- [ ] Low stock alerts (configurable threshold)
- [ ] UPC matching with learned mappings for AI-assisted import

**Nice to Have:**
- [ ] Inventory value reporting (total $ on hand)
- [ ] Purchase price history chart
- [ ] Ingredient usage trends

### 11.2 Phase 3 (Future) Acceptance

**Advanced Features:**
- [ ] Inventory reservations (allocate before depletion)
- [ ] Inventory transfers between locations
- [ ] Batch/lot number tracking
- [ ] Supplier quality tracking
- [ ] Automatic unit conversion using ingredient density
- [ ] Inventory alerts (low stock, expiring soon)
- [ ] Purchase price trends and forecasting

---

## 12. Dependencies

### 12.1 Upstream Dependencies (Blocks This)

- ✅ Ingredient hierarchy (req_ingredients.md)
- ✅ Product catalog (req_products.md)
- ✅ Shelf life tracking (F041)
- ⏳ Vendor management (future)

### 12.2 Downstream Dependencies (This Blocks)

- Production execution (requires inventory depletion)
- Planning (requires inventory availability queries)
- Shopping list generation (requires gap analysis)
- Cost tracking (requires FIFO cost calculations)

---

## 13. Testing Requirements

### 13.1 Test Coverage

**Unit Tests:**
- FIFO ordering logic
- Multi-purchase depletion spanning
- Partial depletion calculations
- Weighted cost calculations
- Freshness status computation (F041)

**Integration Tests:**
- Purchase → Inventory item creation
- Production run → FIFO depletion
- Depletion across multiple purchases
- Inventory queries with filtering

**User Acceptance Tests:**
- Record purchase and verify inventory created
- Execute production and verify FIFO depletion
- Check inventory before planning
- View depletion history
- Filter inventory by freshness status

---

## 14. Open Questions & Future Considerations

### 14.1 Open Questions

**Q1:** Should system allow LIFO (Last-In, First-Out) as alternative to FIFO?
**A1:** No. FIFO is standard for food ingredients (rotation, freshness, cost accuracy).

**Q2:** How to handle unit conversions during depletion (recipe uses cups, purchase in lbs)?
**A2:** Phase 2: Require matching units or manual conversion. Phase 3: Automatic unit conversion using density.

**Q3:** Should expired inventory be automatically excluded from FIFO queries?
**A3:** No. Show expired items with indicators, let user decide usage. Some ingredients usable past expiration.

**Q4:** How to handle partial package opens (bag of flour opened, exposed to air)?
**A4:** Phase 3 feature. Track "opened date" separate from purchase date for freshness calculations.

### 14.2 Future Enhancements

**Phase 3 Candidates:**
- Automatic unit conversion using ingredient density
- Inventory alerts (low stock, expiring soon)
- Inventory value reporting (total $ on hand)
- Purchase price trends and forecasting
- Batch/lot tracking for quality issues

**Phase 4 Candidates:**
- Multi-location inventory tracking
- Inventory transfer workflows
- Consignment inventory (vendor-owned)
- Just-in-time purchasing recommendations
- Integration with vendor ordering systems

---

## 15. Change Log

| Version | Date       | Author    | Changes                                        |
| ------- | ---------- | --------- | ---------------------------------------------- |
| 0.1     | 2025-01-04 | Kent Gale | Initial seeded draft from documented knowledge |

---

## 16. Approval & Sign-off

**Document Owner:** Kent Gale
**Last Review Date:** 2025-01-04
**Next Review Date:** TBD (after extension and refinement)
**Status:** 📝 DRAFT - SEEDED

---

## 17. Related Documents

- **Requirements:** `req_ingredients.md` (ingredient hierarchy)
- **Requirements:** `req_products.md` (product catalog)
- **Requirements:** `req_planning.md` (inventory gap analysis)
- **Design Specs:** `_F041_shelf_life_freshness_tracking.md` (expiration tracking)
- **Design Specs:** `F028_purchase_tracking_enhanced_costing.md` (purchase system)
- **Design Specs:** `F029_streamlined_inventory_entry.md` (inventory workflows)
- **Constitution:** `/.kittify/memory/constitution.md` (FIFO principles)

---

**END OF REQUIREMENTS DOCUMENT (DRAFT - SEEDED)**
