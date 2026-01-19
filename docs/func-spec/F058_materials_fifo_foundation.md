# F058: Materials FIFO Foundation (Schema & Services)

**Version**: 1.0
**Priority**: HIGH
**Type**: Schema Migration + Service Layer

---

## Executive Summary

Materials v2.1 violates definition/instantiation separation by storing cost and inventory in MaterialProduct (definition layer). This breaks constitutional principles and prevents FIFO inventory tracking parallel to ingredients.

Current gaps:
- ❌ MaterialProduct has cost/inventory fields (violates definition/instantiation)
- ❌ No MaterialInventoryItem table (inventory tracking incomplete)
- ❌ Weighted average costing instead of FIFO (breaks parallelism with ingredients)
- ❌ No service primitives for FIFO consumption
- ❌ Base unit types are imperial (inches) instead of metric (cm)

This spec implements FIFO foundation by creating MaterialInventoryItem table, removing cost/inventory from MaterialProduct, building service primitives for FIFO consumption, and establishing strict definition/instantiation separation.

---

## Problem Statement

**Current State (v2.1 BROKEN):**
```
Materials Domain
├─ ✅ Material hierarchy (Categories, Subcategories, Materials)
├─ ✅ MaterialProduct catalog exists
│   └─ ❌ Has current_inventory field (WRONG - definition layer)
│   └─ ❌ Has weighted_avg_cost field (WRONG - definition layer)
├─ ✅ MaterialUnit model exists
├─ ✅ MaterialPurchase model exists
├─ ❌ MaterialInventoryItem table DOESN'T EXIST
├─ ❌ No FIFO consumption capability
├─ ❌ MaterialConsumption lacks inventory_item_id FK
└─ ❌ Services use weighted average (not FIFO)

Constitutional Violation:
❌ Principle III: Definition/Instantiation separation violated
```

**Target State (v3.0 COMPLIANT):**
```
Materials Domain
├─ ✅ Material hierarchy (unchanged)
├─ ✅ MaterialProduct (definitions only, NO cost/inventory)
├─ ✅ MaterialUnit (unchanged)
├─ ✅ MaterialPurchase creates MaterialInventoryItem
├─ ✅ MaterialInventoryItem table (FIFO tracking)
│   ├─ quantity_purchased (immutable snapshot)
│   ├─ quantity_remaining (decremented on consumption)
│   └─ cost_per_unit (immutable snapshot)
├─ ✅ MaterialConsumption links to MaterialInventoryItem
├─ ✅ MaterialInventoryService (FIFO primitives)
├─ ✅ MaterialConsumptionService (consumption records)
└─ ✅ MaterialCatalogService (definitions only, no cost logic)

Constitutional Compliance:
✅ Principle III: Strict definition/instantiation separation
✅ Principle II: FIFO tracking matches ingredients (data integrity)
✅ Principle V: Layered architecture (service separation)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Ingredient FIFO Pattern (PRIMARY REFERENCE)**
   - Find ProductInventoryItem model (parallel to MaterialInventoryItem)
   - Find Purchase → ProductInventoryItem creation pattern
   - Study FIFO consumption logic for ingredients
   - Note cost snapshot immutability pattern
   - **THIS IS THE GOLD STANDARD - COPY EXACTLY**

2. **Service Layer Architecture**
   - Find ingredient inventory service
   - Study service primitives pattern (what methods other services call)
   - Understand session management in services
   - Note eager loading patterns for performance

3. **Definition/Instantiation Examples**
   - Find Product model (definition - NO cost/inventory fields)
   - Find ProductInventoryItem model (instantiation - HAS cost/inventory)
   - Study Ingredient → Product → ProductInventoryItem hierarchy
   - Note how MaterialProduct must parallel Product exactly

4. **Import/Export Service**
   - Find existing import/export service (already handles materials)
   - Study MaterialProduct export format
   - Understand catalog import/export patterns
   - Note field filtering approach (for excluding removed fields)

---

## Requirements Reference

This specification implements:
- **REQ-M-001 through REQ-M-003**: Materials hierarchy (no changes)
- **REQ-M-004**: MaterialProduct is definition only (BREAKING CHANGE)
- **REQ-M-005 through REQ-M-007**: Unit type inheritance and conversion
- **REQ-M-008 through REQ-M-010**: MaterialInventoryItem table and FIFO
- **REQ-M-011 through REQ-M-013**: Purchase creates inventory items
- **REQ-M-014 through REQ-M-016**: Definition/instantiation separation
- **REQ-M-023**: Material service primitives for assembly

From: `docs/requirements/req_materials.md` (v3.0)

---

## Functional Requirements

### FR-1: Remove Cost/Inventory from MaterialProduct (BREAKING CHANGE)

**What it must do:**
- DROP MaterialProduct.current_inventory field
- DROP MaterialProduct.weighted_avg_cost field
- MaterialProduct becomes pure definition (name, brand, SKU, package info, supplier only)
- Remove all cost/inventory calculation logic from MaterialCatalogService

**Pattern reference:** Study Product model - it has NO cost or inventory fields

**Success criteria:**
- [ ] MaterialProduct schema has NO current_inventory field
- [ ] MaterialProduct schema has NO weighted_avg_cost field
- [ ] MaterialCatalogService has NO cost calculation methods
- [ ] Catalog UI shows definitions only (verified in FR-7)

---

### FR-2: Create MaterialInventoryItem Table

**What it must do:**
- Create MaterialInventoryItem table with fields:
  - material_product_id (FK to MaterialProduct)
  - material_purchase_id (FK to MaterialPurchase)
  - quantity_purchased (Decimal, base units, immutable)
  - quantity_remaining (Decimal, base units, mutable)
  - cost_per_unit (Decimal, immutable snapshot)
  - purchased_at (DateTime)
  - created_at, updated_at (standard timestamps)
- MaterialInventoryItem created automatically when MaterialPurchase created
- One MaterialInventoryItem per MaterialPurchase (1:1 relationship)

**Pattern reference:** Copy ProductInventoryItem table structure EXACTLY - replace "product" with "material_product"

**Business rules:**
- quantity_purchased never changes after creation (immutable)
- quantity_remaining decremented on consumption (mutable)
- cost_per_unit never changes after creation (immutable snapshot)
- quantity_remaining must be >= 0 (cannot go negative)

**Success criteria:**
- [ ] MaterialInventoryItem table exists with correct fields
- [ ] MaterialInventoryItem created when MaterialPurchase created
- [ ] Relationships configured (FK constraints working)
- [ ] Immutability rules enforced

---

### FR-3: Update MaterialConsumption for FIFO Tracking

**What it must do:**
- ADD MaterialConsumption.inventory_item_id (FK to MaterialInventoryItem)
- MaterialConsumption records which MaterialInventoryItem it consumed from
- Each consumption links to specific inventory lot for traceability

**Pattern reference:** Study ProductionConsumption model - it links to ProductInventoryItem

**Success criteria:**
- [ ] MaterialConsumption has inventory_item_id FK
- [ ] FK constraint to MaterialInventoryItem working
- [ ] Relationship configured properly

---

### FR-4: Implement Unit Type System with Metric Base

**What it must do:**
- Change Material.base_unit_type from imperial to metric:
  - "linear_inches" → "linear_cm"
  - "square_inches" → "square_cm"
  - "each" → "each" (unchanged)
- Implement conversion factors for input units:
  - Imperial linear: feet→cm (×30.48), inches→cm (×2.54), yards→cm (×91.44)
  - Imperial area: square_feet→square_cm (×929.03), square_inches→square_cm (×6.4516)
  - Metric linear: meters→cm (×100), mm→cm (÷10)
  - Metric area: square_meters→square_cm (×10000)
- MaterialProduct stores:
  - package_quantity (user input, e.g. "100")
  - package_unit (user input, e.g. "feet")
  - quantity_in_base_units (calculated, e.g. "3048 cm")
- System validates package_unit is convertible to Material.base_unit_type

**Pattern reference:** Study any existing unit conversion code, or implement new conversion utility

**Conversion logic:**
- User enters: "100 feet"
- Material has: base_unit_type = "linear_cm"
- System calculates: 100 × 30.48 = 3048 cm
- System stores: package_quantity=100, package_unit="feet", quantity_in_base_units=3048

**Success criteria:**
- [ ] Material.base_unit_type accepts "each", "linear_cm", "square_cm"
- [ ] Conversion factors correct (tested with unit tests)
- [ ] MaterialProduct.quantity_in_base_units calculated correctly
- [ ] Validation rejects incompatible unit conversions
- [ ] All inventory calculations use base units (cm)

---

### FR-5: Build MaterialInventoryService

**What it must do:**
- Create MaterialInventoryService with FIFO primitives:
  - `get_fifo_inventory(material_product_id)` - Returns list ordered by purchased_at DESC
  - `validate_inventory_availability(requirements)` - Checks if sufficient inventory
  - `consume_material_fifo(material_product_id, quantity, assembly_run_id)` - Performs FIFO consumption
  - `calculate_available_inventory(material_product_id)` - Sums quantity_remaining
  - `create_inventory_item(purchase)` - Creates MaterialInventoryItem from purchase
  - `adjust_inventory(material_product_id, adjustment_data)` - Manual adjustments
- Service provides primitives OTHER services call (AssemblyService, PlanningService)
- Service owns ALL inventory queries and mutations

**Pattern reference:** Study ingredient inventory service - copy primitives pattern

**FIFO Consumption Algorithm:**
1. Query MaterialInventoryItem where material_product_id = X AND quantity_remaining > 0
2. Order by purchased_at ASC (oldest first = FIFO)
3. Consume from items in FIFO order until quantity satisfied
4. Create MaterialConsumption record(s) with inventory_item_id linkage
5. Decrement MaterialInventoryItem.quantity_remaining
6. Return total cost (sum of FIFO costs) and MaterialConsumption records

**Success criteria:**
- [ ] MaterialInventoryService class exists
- [ ] All 6 primitives implemented and working
- [ ] FIFO consumption tested with multiple purchase lots
- [ ] Service uses proper session management
- [ ] Primitives callable by other services (integration tested)

---

### FR-6: Build MaterialConsumptionService

**What it must do:**
- Create MaterialConsumptionService for consumption records:
  - `create_consumption_record(inventory_item, quantity, cost, assembly_run_id)` - Creates record
  - `get_consumption_history(material_product_id)` - Retrieves history
- Service owns MaterialConsumption CRUD operations

**Pattern reference:** Study how ingredient consumption records are created/managed

**Success criteria:**
- [ ] MaterialConsumptionService class exists
- [ ] create_consumption_record working
- [ ] get_consumption_history working
- [ ] Consumption records have correct snapshots (cost, quantity, inventory_item_id)

---

### FR-7: Refactor MaterialCatalogService

**What it must do:**
- REMOVE all cost calculation methods
- REMOVE all inventory calculation methods
- REMOVE weighted average costing logic
- ADD `create_provisional_product(minimal_data)` - Creates product with is_provisional=True
- ADD `enrich_provisional_product(material_product_id, full_data)` - Updates provisional product
- KEEP definition-only operations (CRUD for catalog entities)

**Pattern reference:** Study Product catalog service - it has NO cost/inventory methods

**Success criteria:**
- [ ] MaterialCatalogService has NO cost methods
- [ ] MaterialCatalogService has NO inventory methods
- [ ] Provisional product creation working
- [ ] Provisional product enrichment working
- [ ] Definition CRUD operations unchanged

---

### FR-8: Update MaterialPurchase to Create Inventory Items

**What it must do:**
- When MaterialPurchase created:
  1. Calculate calculated_unit_cost (total_cost ÷ total_units)
  2. Call MaterialInventoryService.create_inventory_item(purchase)
  3. MaterialInventoryItem created with:
     - quantity_purchased = purchase.total_units (in base units)
     - quantity_remaining = purchase.total_units (initially full)
     - cost_per_unit = purchase.calculated_unit_cost (snapshot)
     - purchased_at = purchase.purchased_at
- Purchase workflow unchanged from user perspective (UI in F059)

**Pattern reference:** Study how Purchase creates ProductInventoryItem

**Success criteria:**
- [ ] MaterialPurchase creation triggers inventory item creation
- [ ] MaterialInventoryItem has correct values
- [ ] Unit cost snapshot immutable
- [ ] Quantities in base units (cm)

---

### FR-9: Update Catalog UI to Remove Cost/Inventory Display

**What it must do:**
- Catalog > Materials > Material Products view:
  - REMOVE cost column (if present)
  - REMOVE inventory column (if present)
  - SHOW only definition fields: Name, Brand, SKU, Package (qty + unit), Supplier
  - UPDATE "View Inventory" link text to "View Inventory (Purchase Mode)"
- NO new UI components (just removing columns)

**Pattern reference:** Study Catalog > Food > Products view - it shows definitions only

**Success criteria:**
- [ ] Catalog UI shows NO cost information
- [ ] Catalog UI shows NO inventory information
- [ ] "View Inventory" link present (target updated in F059)
- [ ] Definition fields clearly displayed

---

### FR-10: Update Import/Export for Schema Changes

**What it must do:**
- Update existing import/export services to handle MaterialProduct schema changes:
  - Export: Ensure MaterialProduct exports WITHOUT current_inventory and weighted_avg_cost fields
  - Import: Ignore/skip current_inventory and weighted_avg_cost fields if present in old JSON
  - Validation: Verify MaterialProduct imports work with new schema
- Create schema migration script:
  - DROP MaterialProduct.current_inventory field
  - DROP MaterialProduct.weighted_avg_cost field
  - Add MaterialInventoryItem table (if not handled by ORM migrations)
- Update migration documentation for users

**Pattern reference:** Study existing import/export service - materials catalog export/import already exists, just needs schema field updates

**Existing Capabilities (NO NEW IMPLEMENTATION NEEDED):**
- ✅ Full backup export/import (already exists)
- ✅ Catalog-only export/import (already exists)
- ✅ Context-rich JSON format (already exists)
- ✅ Materials catalog export/import (already exists)

**What's Actually Needed:**
- Update MaterialProduct export to exclude removed fields
- Update MaterialProduct import to handle old JSONs gracefully
- Schema migration script (drop 2 fields, add 1 table)

**Success criteria:**
- [ ] MaterialProduct catalog export excludes removed fields
- [ ] MaterialProduct catalog import handles old JSONs (ignores removed fields)
- [ ] Schema migration script drops fields without errors
- [ ] Materials catalog export/import tested with new schema
- [ ] Migration tested: export v2.1 → migrate schema → import to v3.0

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Purchase mode UI (F059 handles this)
- ❌ Purchase form workflows (F059 handles this)
- ❌ Inventory display in Purchase mode (F059 handles this)
- ❌ Manual inventory adjustment UI (F059 handles this)
- ❌ Assembly integration (separate feature after F059)
- ❌ FinishedGood composition with materials (separate feature)
- ❌ Event planning cost calculations (separate feature)
- ❌ CLI-assisted purchasing workflow (F059 handles this)

---

## Success Criteria

**Complete when:**

### Schema Changes
- [ ] MaterialProduct has NO current_inventory field
- [ ] MaterialProduct has NO weighted_avg_cost field
- [ ] MaterialInventoryItem table exists with correct structure
- [ ] MaterialConsumption has inventory_item_id FK
- [ ] Material.base_unit_type uses cm-based values

### Service Layer
- [ ] MaterialInventoryService exists with 6 primitives
- [ ] MaterialConsumptionService exists
- [ ] MaterialCatalogService refactored (no cost/inventory logic)
- [ ] FIFO consumption algorithm working correctly
- [ ] Unit conversion working (imperial/metric → cm)

### Purchase Integration
- [ ] MaterialPurchase creates MaterialInventoryItem automatically
- [ ] Cost snapshots immutable
- [ ] Quantities stored in base units (cm)

### Data Migration
- [ ] MaterialProduct export excludes removed fields (current_inventory, weighted_avg_cost)
- [ ] MaterialProduct import handles old JSONs gracefully (ignores removed fields)
- [ ] Schema migration script drops fields successfully
- [ ] Materials catalog export/import working with new schema

### Catalog UI
- [ ] Catalog shows definitions only (no cost/inventory)
- [ ] "View Inventory" link present

### Quality
- [ ] FIFO logic validated with unit tests (multiple purchase lots)
- [ ] Unit conversion tested (all supported units)
- [ ] Service primitives integration tested
- [ ] Pattern consistency with ingredient system verified
- [ ] No code duplication (DRY principle)

---

## Architecture Principles

### Definition/Instantiation Separation

**Strict Boundary:**
- **Definition Layer** (MaterialProduct): Name, brand, SKU, package info - MUTABLE
- **Instantiation Layer** (MaterialInventoryItem): Quantities, costs - IMMUTABLE SNAPSHOTS
- MaterialProduct changes do NOT affect historical MaterialInventoryItem records

**Rationale:** Historical data preserved in instantiation layer regardless of definition changes

### FIFO Inventory Tracking

**Algorithm:**
- Consume from newest inventory first (FIFO = First In, First Out)
- Matches ingredient system exactly
- Enables actual cost tracking (not weighted average)

**Rationale:** Provides accurate historical cost analysis, parallels food domain

### Pattern Matching

**MaterialInventoryItem must match ProductInventoryItem exactly:**
- Same field structure (quantity_purchased, quantity_remaining, cost_per_unit)
- Same relationships (material_product_id ↔ product_id, material_purchase_id ↔ purchase_id)
- Same immutability rules (snapshots never change)
- Same FIFO consumption logic (newest first)
- Same service primitive patterns

**Rationale:** Users learn one system, understand both; developers reference validated patterns

### Metric Base Units

**Storage:**
- Base unit types: "linear_cm", "square_cm", "each"
- All inventory calculations in base units
- User input converted to base units on entry

**Rationale:** Supports both imperial and metric inputs, consistent internal calculations

---

## Constitutional Compliance

✅ **Principle II (Data Integrity & FIFO Accuracy)**
- FIFO consumption for materials matches ingredient pattern
- Cost snapshots immutable (historical accuracy preserved)
- Quantities tracked in base units (consistent calculations)

✅ **Principle III (Definition/Instantiation)**
- Strict separation: MaterialProduct (definition), MaterialInventoryItem (instantiation)
- Cost stored ONLY in instantiation layer
- Definition changes don't corrupt historical data

✅ **Principle V (Layered Architecture)**
- Service layer separation: MaterialInventoryService, MaterialConsumptionService, MaterialCatalogService
- Each service has clear responsibilities
- Services provide primitives for other services to call

✅ **Principle VI (Parallel Architecture)**
- Materials strictly parallel ingredients
- Same patterns, same structure, same logic
- Users understand one system → understand both

---

## Risk Considerations

**Risk: BREAKING CHANGE migration loses purchase history**
- Current v2.1 MaterialPurchase records exist
- Migration script intentionally does NOT migrate old purchases to new MaterialInventoryItem
- Users must re-enter MaterialPurchases after migration (or do physical inventory count)
- **Mitigation approach**: Clear migration documentation, export catalog before migration, accept fresh start for inventory

**Risk: FIFO logic complexity**
- FIFO consumption across multiple inventory lots more complex than weighted average
- Must handle partial consumption correctly (consume 50 from lot with 30 remaining = consume all 30, then 20 from next lot)
- **Mitigation approach**: Copy validated ingredient FIFO pattern exactly, comprehensive unit tests with multiple scenarios

**Risk: Unit conversion errors**
- Imperial/metric conversions must be accurate
- Wrong conversion factor breaks all inventory calculations
- **Mitigation approach**: Unit tests for all conversion factors, reference authoritative sources for conversion values

**Risk: Pattern drift from ingredient system**
- Materials must EXACTLY parallel ingredients for constitutional compliance
- Deviation breaks user mental model
- **Mitigation approach**: Reference ingredient code continuously during implementation, code review validates parallelism

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study ProductInventoryItem model → apply to MaterialInventoryItem (exact structure)
- Study Purchase → ProductInventoryItem creation → apply to MaterialPurchase → MaterialInventoryItem
- Study ingredient FIFO service → apply to MaterialInventoryService (same primitives)
- Study Product model → verify MaterialProduct becomes definition-only (same fields, no cost/inventory)

**Key Patterns to Copy:**
- ProductInventoryItem structure → MaterialInventoryItem structure (EXACT parallel)
- Ingredient FIFO consumption logic → Material FIFO consumption logic (EXACT algorithm)
- Product catalog service → MaterialCatalogService (definitions only, no cost methods)

**Focus Areas:**
- FIFO consumption algorithm correctness (multiple inventory lots, partial consumption)
- Unit conversion accuracy (all imperial/metric factors correct)
- Service primitive design (other services call these methods)
- Immutability enforcement (quantity_purchased, cost_per_unit never change)
- Base unit storage (everything stored in cm)

**Service Primitive Design Pattern:**
```
MaterialInventoryService provides primitives:
  ↓
AssemblyService (future) calls primitives:
  - validate_inventory_availability() before assembly
  - consume_material_fifo() during assembly
  
PlanningService calls primitives:
  - calculate_available_inventory() for event planning
```

**Unit Conversion Implementation Note:**
- Create conversion utility/module
- Define conversion factors as constants
- Validation: check if package_unit compatible with base_unit_type before converting
- Example: Can convert "feet" to "linear_cm", CANNOT convert "feet" to "square_cm"

---

**END OF SPECIFICATION**
