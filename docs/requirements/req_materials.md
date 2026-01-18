# Requirements: Materials Management System

**Document ID**: REQ-MATERIALS-001
**Version**: 3.0
**Date**: 2026-01-18
**Status**: Current
**Feature ID**: F047 (Packaging Materials Foundation)
**Changelog**: 
- v3.0 - BREAKING CHANGES: LIFO inventory tracking (parallel to ingredients), strict definition/instantiation separation, MaterialInventoryItem table required, unit type inheritance model, auto-conversion to base units
- v2.1 - Added identity snapshot principle (REQ-M-042); Updated REQ-M-012, REQ-M-013, REQ-M-020, REQ-M-041 for complete identity capture

---

## 1. Executive Summary

### 1.1 Purpose

Implement a comprehensive materials management system that **strictly parallels** the existing ingredient management system, enabling proper handling of non-edible materials (ribbon, boxes, bags, tissue, etc.) used in baking assemblies with **LIFO inventory tracking** and **strict definition/instantiation separation**.

### 1.2 Problem Statement

**Current State (v2.1 Issues Identified):**
- MaterialProduct has cost/inventory fields (violates definition/instantiation)
- Weighted average costing used instead of LIFO (breaks parallelism with ingredients)
- No MaterialInventoryItem table (inventory tracking incomplete)
- Material.base_unit_type inheritance not clear in UI
- MaterialUnit quantity_per_unit field confusing (no unit type shown)
- Material purchase UI missing entirely

**Required State:**
- Separate materials ontology and product catalog (definitions only)
- MaterialInventoryItem table for LIFO inventory tracking (parallel to ProductInventoryItem)
- Materials purchasing creates inventory items with cost snapshots
- Material.base_unit_type strictly inherited by products and units
- Materials integrated into assembly cost calculations (LIFO actual costs)
- Materials work alongside ingredients in all observability/reporting
- **Flexible material decision timing** (catalog or assembly stage)

### 1.3 Strategic Rationale

**Foundational Extensibility Architecture:**
This is NOT a simple feature - it establishes a critical architectural pattern for:
- Multi-user web version (future)
- Potential e-commerce layering (future)
- Professional kitchen/bakery operations (future)
- Dual supply chain management (food + materials)

**Architectural Decision:**
Materials MUST **strictly parallel** Ingredient model to ensure:
- **LIFO inventory tracking** (same as ingredients)
- **Definition/instantiation separation** (same as ingredients)
- Consistent workflows (catalog, purchasing, inventory, consumption)
- Unified UI patterns (users understand one, understand both)
- Observability parity (reports show food + materials side-by-side)
- Extensibility for web/commerce features

**Constitutional Compliance:**
- **Principle II (Data Integrity & FIFO Accuracy)**: LIFO consumption for materials matches ingredient pattern
- **Principle III (Definition/Instantiation)**: Strict separation maintained throughout materials domain
- **Principle V (Layered Architecture)**: Clean separation between catalog (definition) and inventory (instantiation)

---

## 2. Scope

### 2.1 In Scope

**Data Model:**
- ✅ Materials ontology hierarchy (3 levels: Category → Subcategory → Material)
- ✅ MaterialProduct catalog (physical purchasable items - **DEFINITIONS ONLY, NO COST/INVENTORY**)
- ✅ **MaterialInventoryItem table** (LIFO inventory tracking, parallel to ProductInventoryItem)
- ✅ MaterialUnit model (atomic consumption units, parallel to FinishedUnit)
- ✅ Materials purchasing workflow (creates MaterialInventoryItem records)
- ✅ Materials inventory system (**LIFO costing**, not weighted average)
- ✅ Materials consumption tracking in AssemblyRun (consumes from MaterialInventoryItem)
- ✅ Materials cost calculations (LIFO actual costs)
- ✅ **Deferred material decision workflow** (generic placeholders)
- ✅ **Unit type inheritance** (Material → MaterialProduct → MaterialUnit)
- ✅ **Auto-conversion to base units** (feet → inches, etc.)

**Integration:**
- ✅ FinishedGood compositions (FinishedUnits + MaterialUnits + Material placeholders)
- ✅ AssemblyRun enhancements (component costs + material costs, LIFO)
- ✅ Event planning cost calculations (include materials, estimated vs actual)
- ✅ Import/export (catalog + view data, **first-class materials support**)
- ✅ **Assembly hard stop** (enforce material resolution)

**UI:**
- ✅ Materials ontology management (categories, subcategories)
- ✅ MaterialProduct catalog CRUD (**NO cost/inventory display in catalog**)
- ✅ MaterialUnit catalog CRUD (shows inherited unit type)
- ✅ Materials purchasing workflow (creates inventory items)
- ✅ Materials inventory view (**Purchase mode**, shows MaterialInventoryItem lots)
- ✅ Manual inventory adjustments (creates/updates MaterialInventoryItem)
- ✅ Material selection in FinishedGood composition (specific/generic/none)
- ✅ **Pending decision indicators** (⚠️ throughout workflow)
- ✅ **Material assignment interface** (quick assign at assembly, shows LIFO inventory)
- ✅ Materials costs in assembly recording (LIFO actual costs)
- ✅ Materials costs in event planning

### 2.2 Out of Scope (Deferred)

**Deferred to Future Features:**
- ❌ Rich metadata (structured dimensions, color, material_type fields beyond notes)
- ❌ Unit conversions beyond feet↔inches for imperial, cm↔m for metric
- ❌ "Packaging" vs "Materials" differentiation (keep generic "Materials")
- ❌ Materials-specific reporting/analytics (beyond cost reporting)
- ❌ Low stock alerts
- ❌ Automated reordering
- ❌ **Automatic assignment algorithms** (F026 deferred)
- ❌ **Packaging templates** (F026 deferred)
- ❌ **Partial commitment** (F026 deferred)
- ❌ Lot numbers for MaterialInventoryItem (not needed)
- ❌ Expiration dates for MaterialInventoryItem (not needed)

**Not Required:**
- ❌ Migration from "packaging ingredients" (no existing data to migrate)
- ❌ Sample data generation (user will provide JSON file separately)

---

## 3. Detailed Requirements

### 3.1 Materials Ontology Hierarchy

**REQ-M-001: Three-Level Hierarchy**

Materials SHALL have a hierarchical ontology with exactly 3 levels:

```
MaterialCategory (Level 1)
  Examples: "Ribbons", "Boxes", "Tissue Paper", "Bags"
  ↓
MaterialSubcategory (Level 2)
  Examples: "Satin Ribbon", "Grosgrain Ribbon", "Gift Boxes", "Cellophane Bags"
  ↓
Material (Level 3 - Abstract Definition)
  Examples: "Red Satin Ribbon", "Small Gift Box 6x6x3", "6\" Cellophane Bag"
  base_unit_type: "each" | "linear_cm" | "square_cm"
  ↓
MaterialProduct (Physical Definition - Purchasable)
  Examples: "Michaels Red Satin 100ft Roll", "Amazon 6x6x3 White Box 50pk"
  Inherits base_unit_type from Material
  NO cost or inventory fields
  ↓
MaterialInventoryItem (Instantiation - Purchase Lot)
  quantity_purchased, quantity_remaining, cost_per_unit (snapshot)
  One item per purchase, LIFO consumption
```

**REQ-M-002: Strict Parallel to Ingredient Structure**

The materials domain SHALL **exactly parallel** the ingredient domain structure:

| Ingredient Domain | Material Domain | Purpose |
|-------------------|-----------------|---------|
| IngredientCategory | MaterialCategory | Level 1 hierarchy |
| IngredientSubcategory | MaterialSubcategory | Level 2 hierarchy |
| Ingredient | Material | Abstract definition (with base_unit_type) |
| Product | MaterialProduct | Purchasable SKU definition (NO cost/inventory) |
| ProductInventoryItem | **MaterialInventoryItem** | Purchase lot (LIFO tracking) |
| Purchase | MaterialPurchase | Purchase transaction |
| ProductionConsumption | MaterialConsumption | Consumption from inventory (LIFO) |
| FinishedUnit | MaterialUnit | Consumption unit definition |

**Rationale**: Strict parallelism ensures:
- Users learn one system, understand both
- Developers reference validated ingredient patterns
- Future features (web, multi-user) apply equally to both domains
- No architectural drift between food and material management

**REQ-M-003: Shared Supplier Table**

Materials and ingredients SHALL share a single Suppliers table:
- No separate MaterialSupplier table
- Supplier.supplier_type NOT required (one supplier can provide both)
- Maintains single vendor management system

---

### 3.2 MaterialProduct Catalog (Definitions Only)

**REQ-M-004: MaterialProduct is DEFINITION ONLY**

MaterialProduct SHALL be a pure definition with **NO cost or inventory fields**:

```python
MaterialProduct:
    # Definition fields
    material_id: int (FK to Material, required)
    supplier_id: int (FK to Supplier, optional)
    name: str (required, e.g., "100ft Red Satin Roll")
    slug: str (unique, for import/export stability)
    brand: str (optional, e.g., "Michaels")
    sku: str (optional, supplier SKU)
    package_quantity: Decimal (e.g., 100.0)
    package_unit: str (e.g., "feet")
    quantity_in_base_units: Decimal (auto-calculated, e.g., 1200 inches)
    is_hidden: bool (default False)
    notes: str (freeform text)
    
    # NO cost fields ❌
    # NO inventory fields ❌
```

**Rationale**: 
- MaterialProduct defines "what can be purchased" (definition)
- Cost/inventory are outcomes of purchasing (instantiation)
- Strict definition/instantiation separation maintained

**REQ-M-005: Inherited Unit Type**

MaterialProduct SHALL inherit base_unit_type from parent Material:

```
Material "Red Ribbon":
  base_unit_type: "linear_cm"
  ↓ (inherited)
MaterialProduct "Michaels 100ft Roll":
  package_unit: "feet" (user enters)
  package_quantity: 100.0 (user enters)
  quantity_in_base_units: 3048 (auto-calculated: 100 feet × 30.48)
  ↑ All quantities interpreted in linear_cm (inherited)
```

**REQ-M-006: Auto-Conversion to Base Units**

System SHALL auto-convert package_unit to Material.base_unit_type:

**Base Unit Types**:
- **"each"**: No conversion, discrete items (bags, boxes, sheets)
- **"linear_cm"**: Linear centimeters (recommended for ribbons, twine)
- **"square_cm"**: Square centimeters (for flat materials like tissue paper)

**Supported Input Units** (all converted to base units for storage):

*For linear_cm base type:*
- Metric: cm (1:1), meters (×100), mm (÷10)
- Imperial: inches (×2.54), feet (×30.48), yards (×91.44)

*For square_cm base type:*
- Metric: square_cm (1:1), square_meters (×10000)
- Imperial: square_inches (×6.4516), square_feet (×929.03)

*For each base type:*
- No conversion: package_quantity = quantity_in_base_units

**Conversion Rules**:
1. User enters: package_quantity + package_unit (dropdown)
2. System validates: package_unit convertible to Material.base_unit_type
3. System calculates: quantity_in_base_units (converted to base unit type)
4. System stores: package values (for display) + base units (for inventory/consumption)

**Example 1 - Metric Input**:
```
Material: "Red Ribbon" (base_unit_type: "linear_cm")
MaterialProduct entry:
  package_quantity: 15
  package_unit: "cm" ← User enters metric
  
System calculates:
  quantity_in_base_units: 15 (no conversion needed)
  
Storage:
  package_quantity: 15.0
  package_unit: "cm"
  quantity_in_base_units: 15.0
```

**Example 2 - Imperial Input**:
```
Material: "Red Ribbon" (base_unit_type: "linear_cm")
MaterialProduct entry:
  package_quantity: 100
  package_unit: "feet" ← User enters imperial
  
System calculates:
  quantity_in_base_units: 3048 (100 × 30.48)
  
Storage:
  package_quantity: 100.0
  package_unit: "feet"
  quantity_in_base_units: 3048.0
  
Display (catalog):
  "100 feet per package (3048 cm)"
  
Inventory calculations:
  Use quantity_in_base_units (3048 cm)
```

**Rationale**: 
- Base storage in cm allows both metric and imperial inputs
- User can enter materials in their preferred units
- System handles conversion transparently
- All inventory/consumption calculations use cm (consistent base)

**REQ-M-007: Product Type Differentiation**

MaterialProduct SHALL be a separate table from Product:
- NO shared Product table with type discriminator
- Clean separation enables future material-specific fields
- Follows parallel architecture principle

---

### 3.3 MaterialInventoryItem (LIFO Tracking)

**REQ-M-008: MaterialInventoryItem Table**

System SHALL track material inventory using MaterialInventoryItem table (parallel to ProductInventoryItem):

```python
class MaterialInventoryItem:
    """
    Represents a single purchase lot of a material product.
    LIFO consumption: oldest items consumed first.
    """
    # Foreign keys
    material_product_id: int  # FK to MaterialProduct (definition)
    material_purchase_id: int  # FK to MaterialPurchase (transaction)
    
    # Quantity tracking
    quantity_purchased: Decimal  # Original purchase quantity (in base units)
    quantity_remaining: Decimal  # Current remaining (in base units)
    
    # Cost snapshot (immutable)
    cost_per_unit: Decimal  # Cost per base unit at purchase time
    
    # Metadata
    purchased_at: DateTime  # When purchased
    
    # NO lot_number field (not needed for materials)
    # NO expiration_date field (not needed for materials)
```

**REQ-M-009: LIFO Consumption**

MaterialConsumption SHALL consume from MaterialInventoryItem using LIFO (Last In, First Out):

**Consumption Algorithm**:
1. Get MaterialProduct for selected Material
2. Query MaterialInventoryItem where material_product_id = X AND quantity_remaining > 0
3. Order by purchased_at DESC (newest first = LIFO)
4. Consume from items in LIFO order until quantity satisfied
5. Create MaterialConsumption record(s) linking to consumed MaterialInventoryItem(s)
6. Decrement MaterialInventoryItem.quantity_remaining

**Example**:
```
MaterialInventoryItems for "Snowflake Bag 6\"":
  Item A: purchased 2024-12-01, qty_remaining: 50, cost: $0.24/each
  Item B: purchased 2024-12-10, qty_remaining: 30, cost: $0.26/each
  Item C: purchased 2024-12-15, qty_remaining: 20, cost: $0.28/each

Assembly needs: 40 bags

LIFO consumption:
  1. Consume 20 from Item C (newest) @ $0.28 = $5.60
  2. Consume 20 from Item B (next newest) @ $0.26 = $5.20
  Total cost: $10.80 (actual LIFO cost)

MaterialConsumption records created:
  - inventory_item_id: C, quantity: 20, cost_per_unit: $0.28
  - inventory_item_id: B, quantity: 20, cost_per_unit: $0.26
```

**Rationale**: 
- LIFO provides actual cost tracking (not weighted average)
- Matches ingredient consumption pattern exactly
- Enables accurate historical cost analysis

**REQ-M-010: Inventory Aggregation**

System SHALL calculate available inventory by aggregating MaterialInventoryItem.quantity_remaining:

```python
def get_available_inventory(material_product_id: int) -> Decimal:
    """Get total available inventory for a material product."""
    return sum(
        item.quantity_remaining 
        for item in MaterialInventoryItem.query
        .filter_by(material_product_id=material_product_id)
        .all()
    )
```

**Display Locations**:
- **Purchase > Inventory**: Shows MaterialInventoryItem lots (detail view, parallel to food inventory)
- **Assembly**: Shows aggregate available inventory (summary view)
- **Catalog**: NO inventory display (definitions only)

**Service Layer**:
- MaterialInventoryService provides primitives for querying inventory
- Planning/production services call MaterialInventoryService for availability checks
- Follows same pattern as food inventory (ProductInventoryItem)

---

### 3.4 Materials Purchasing Workflow

**REQ-M-011: Purchase Creates Inventory Items**

MaterialPurchase SHALL create MaterialInventoryItem records (parallel to Purchase → ProductInventoryItem):

```python
MaterialPurchase:
    # Package information (user enters)
    material_product_id: int
    package_unit_count: Decimal  # e.g., 25 bags per pack
    packages_purchased: Decimal  # e.g., 4 packs
    total_units: Decimal  # Calculated: 100 bags (in base units)
    
    # Cost information (user enters)
    total_cost: Decimal  # e.g., $40.00
    
    # Calculated and stored
    calculated_unit_cost: Decimal  # e.g., $0.40/bag (total_cost ÷ total_units)
    
    # Metadata
    purchased_at: DateTime
    supplier_id: int (optional)
    notes: str (optional)

# On purchase creation:
MaterialInventoryItem.create(
    material_product_id=purchase.material_product_id,
    material_purchase_id=purchase.id,
    quantity_purchased=purchase.total_units,
    quantity_remaining=purchase.total_units,
    cost_per_unit=purchase.calculated_unit_cost,  # Snapshot
    purchased_at=purchase.purchased_at
)
```

**REQ-M-012: Unit Cost Calculation**

Unit cost SHALL be calculated at purchase time and stored as immutable snapshot:

```
Formula:
calculated_unit_cost = total_cost ÷ total_units

Example:
Package: 25 bags per pack
Purchased: 4 packs
Total: 100 bags
Cost: $40.00
Unit cost: $40.00 ÷ 100 = $0.40/bag

MaterialInventoryItem created with:
  cost_per_unit: $0.40 (immutable snapshot)
```

**REQ-M-013: Purchase Workflow**

Materials purchasing SHALL support multiple input methods:

**Method 1: Manual UI Entry (Purchase Mode)**
1. Select MaterialProduct (or create new)
2. Enter package_unit_count (e.g., "25 bags per pack")
3. Enter packages_purchased (e.g., "4 packs")
4. System calculates total_units (100 bags in base units)
5. Enter total_cost ($40.00)
6. System calculates unit_cost ($0.40/bag)
7. System creates MaterialPurchase record
8. System creates MaterialInventoryItem record (quantity_purchased = total_units)
9. User sees confirmation with calculated unit cost

**Method 2: CLI-Assisted Entry (BT Mobile Integration)**

CLI workflow SHALL support material purchases with provisional product creation:

1. **Product Resolution Phase**:
   - If MaterialProduct exists: Use existing product
   - If MaterialProduct NOT found: Create in **provisional state**
     - Provisional MaterialProduct fields: name, material_id, basic package info
     - Missing fields: Complete catalog metadata (brand, SKU, supplier details)
     - Marked with: `is_provisional = true` or equivalent flag

2. **Purchase Transaction Phase**:
   - CLI provides: product identifier, quantity purchased, total cost, purchase date
   - System matches existing OR creates provisional MaterialProduct
   - System creates MaterialPurchase record (links to product)
   - System creates MaterialInventoryItem record (LIFO tracking starts immediately)
   - Provisional products function identically to complete products for inventory/consumption

3. **Catalog Enhancement Phase (Later)**:
   - User enriches provisional MaterialProducts via Catalog UI (at desk)
   - User adds: brand, supplier, complete package details, notes
   - User removes provisional flag when metadata complete
   - Historical MaterialPurchase records remain linked (by material_product_id)
   - Historical MaterialInventoryItem records unchanged (immutable snapshots)

**Rationale**: 
- CLI workflow prioritizes speed during shopping (minimal data entry at store)
- Provisional products enable immediate inventory tracking without blocking purchase
- Catalog enrichment happens asynchronously (user convenience)
- Parallels food purchase CLI workflow (consistent product lifecycle pattern)

---

### 3.5 Definition/Instantiation Separation

**REQ-M-014: Strict Definition/Instantiation Boundary**

Materials SHALL follow strict definition/instantiation pattern (parallel to ingredients):

**Definition Layer (Catalog - NO stored costs/inventory)**:
- Material (abstract concept, includes base_unit_type)
- MaterialProduct (purchasable SKU definition)
- MaterialUnit (consumption unit definition)
- FinishedGood with Material/MaterialUnit components

**Instantiation Layer (Transactional - Cost/inventory snapshots)**:
- MaterialInventoryItem (purchase lot, LIFO tracking)
- MaterialPurchase (creates inventory items)
- MaterialConsumption (consumes from inventory items, LIFO)
- AssemblyRun (records total_material_cost at assembly time)

**Forbidden**:
- ❌ MaterialProduct.current_inventory field
- ❌ MaterialProduct.weighted_avg_cost field
- ❌ MaterialProduct.last_purchase_cost field
- ❌ MaterialUnit.current_cost field (must calculate dynamically)
- ❌ Any cost/inventory storage in definition layer

**Allowed**:
- ✅ Calculated current cost (query MaterialInventoryItem, LIFO order, take first)
- ✅ Calculated available inventory (sum MaterialInventoryItem.quantity_remaining)
- ✅ Display calculated values in Make mode (not Catalog mode)

**REQ-M-015: Cost Snapshot Immutability**

Instantiation costs SHALL be immutable snapshots:

1. **MaterialInventoryItem.cost_per_unit**: Snapshot at purchase time
   - Never recalculated
   - Immutable historical record
   
2. **MaterialConsumption.cost_per_unit**: Snapshot at assembly time
   - Copied from MaterialInventoryItem.cost_per_unit (LIFO)
   - Never updated when inventory costs change
   
3. **AssemblyRun.total_material_cost**: Sum of MaterialConsumption costs
   - Immutable snapshot of material costs at assembly time

**Example**:
```
Year 1: Purchase "Snowflake Bag 6\"" @ $0.24/each
  MaterialInventoryItem: cost_per_unit = $0.24 (immutable)

Year 1: Assemble gift boxes, consume 50 bags
  MaterialConsumption: cost_per_unit = $0.24 (snapshot from inventory item)
  AssemblyRun: total_material_cost = $12.00 (50 × $0.24, immutable)

Year 2: Purchase more "Snowflake Bag 6\"" @ $0.30/each
  New MaterialInventoryItem: cost_per_unit = $0.30 (immutable)

# Year 1 AssemblyRun STILL shows total_material_cost = $12.00
# Cost does NOT change when new inventory purchased
```

**REQ-M-016: Identity Snapshot Principle**

Materials instantiations SHALL capture complete identity information to enable historical reconstruction:

**MaterialConsumption SHALL record**:
- Material type (material_id) - enables "what type of material"
- Specific product (material_product_id) - enables "which specific design/brand"
- Inventory item (inventory_item_id) - enables "which purchase lot"
- Quantity consumed (quantity_consumed) - enables "how much was used"
- Cost snapshot (cost_per_unit) - enables "how much did it cost"
- Display name snapshot (display_name_snapshot) - enables "what was it called"

**Purpose**: User can query years later:
- "What materials did I use for so-and-so's wedding?"
- "Which specific product design?"
- "Which purchase lot (and cost)?"
- "What was it called then?" (immune to catalog changes)

---

### 3.6 MaterialUnit Model

**REQ-M-017: MaterialUnit as Consumption Definition**

MaterialUnit SHALL define consumption quantity (parallel to FinishedUnit):

```python
MaterialUnit:
    # Identity
    material_id: int  # FK to Material (NOT MaterialProduct)
    name: str  # e.g., "6-inch Red Ribbon"
    slug: str  # For import/export stability
    
    # Consumption definition
    quantity_per_unit: Decimal  # Interpreted in Material.base_unit_type
    
    # Display
    description: str (optional)
    
    # NO material_product_id (product selection deferred to assembly)
    # NO cost fields (calculated dynamically from inventory)
    # NO inventory fields (calculated from MaterialInventoryItem)
```

**Rationale**:
- MaterialUnit is a DEFINITION (template)
- Specific MaterialProduct chosen at assembly time
- Same unit can be fulfilled by multiple products
- Cost calculated from current LIFO inventory (not stored)

**REQ-M-018: Inherited Unit Type**

MaterialUnit.quantity_per_unit SHALL be interpreted in Material.base_unit_type:

```
Material "Red Ribbon":
  base_unit_type: "linear_inches"
  ↓ (inherited)
MaterialUnit "6-inch Red Ribbon":
  quantity_per_unit: 6.0
  ↑ Interpreted as: "6 linear_inches"

MaterialUnit "12-inch Red Ribbon":
  quantity_per_unit: 12.0
  ↑ Interpreted as: "12 linear_inches"
```

**REQ-M-019: "Each" vs "Variable" Validation**

System SHALL validate MaterialUnit.quantity_per_unit based on Material.base_unit_type:

**For "each" Materials**:
- MaterialUnit.quantity_per_unit MUST = 1
- UI shows field as read-only: "1 (each type)"
- Rationale: Discrete items always consumed as whole units

**For "variable" Materials** (linear_inches, square_inches):
- MaterialUnit.quantity_per_unit = user-defined (6.0, 12.0, etc.)
- UI shows field with inherited unit: "Quantity (in linear_inches): [6.0]"
- Rationale: Measured materials have variable consumption quantities

**REQ-M-020: MaterialUnit Inventory Calculation**

MaterialUnit available inventory SHALL be calculated by aggregating MaterialInventoryItem:

```python
def get_material_unit_inventory(material_unit_id: int) -> Decimal:
    """
    Calculate available inventory for a material unit.
    Aggregates ALL MaterialProducts of the associated Material.
    """
    material = MaterialUnit.query.get(material_unit_id).material
    quantity_per_unit = MaterialUnit.query.get(material_unit_id).quantity_per_unit
    
    # Sum inventory across ALL products of this material
    total_base_units = sum(
        item.quantity_remaining
        for product in material.products
        for item in product.inventory_items
    )
    
    # Convert to material units
    return total_base_units / quantity_per_unit

# Example:
# Material "Red Ribbon" has 3 MaterialProducts:
#   - Michaels: 1200 inches remaining
#   - Amazon: 600 inches remaining
#   - Joann's: 900 inches remaining
# Total: 2700 inches

# MaterialUnit "6-inch Red Ribbon":
#   quantity_per_unit: 6
#   Available: 2700 / 6 = 450 units
```

---

### 3.7 Materials in FinishedGood Composition

**REQ-M-021: Polymorphic Composition**

Composition table SHALL link to EITHER FinishedUnit OR MaterialUnit OR Material:

```python
Composition:
    finished_good_id: int
    finished_unit_id: int?  # Optional (if baked good)
    material_unit_id: int?  # Optional (if specific material)
    material_id: int?  # Optional (if generic placeholder)
    quantity: int  # Count of units
    
    # Constraint: EXACTLY ONE of finished_unit_id, material_unit_id, or material_id
```

**REQ-M-022: Flexible Material Assignment Timing**

Material selection SHALL support deferred decision workflow:

**Three material specification levels**:

1. **MaterialUnit (Specific)**: Fully specified material
   - Example: "6\" Snowflake Cellophane Bag"
   - Cost: Calculated from LIFO inventory
   - Inventory: Calculated from MaterialInventoryItem
   - Status: ✓ Ready for assembly

2. **Material (Generic/Placeholder)**: Abstract material type
   - Example: "6\" Cellophane Bag" (any product of this material)
   - Cost: Estimated from LIFO average of available products
   - Inventory: Aggregate across all products
   - Status: ⚠️ "Selection needed"

3. **Unassigned (None)**: No material specified
   - Cost: Not calculated
   - Inventory: Unknown
   - Status: ⚠️ "Material requirements needed"

**Assignment workflow**:
```
CATALOG Mode (FinishedGood definition):
  User CAN specify:
    - Specific MaterialUnit: "6\" Snowflake Bag" (fully decided)
    - Generic Material: "6\" Cellophane Bag" (deferred, placeholder)
    - Nothing: Leave blank (completely deferred)

PLAN Mode (Event planning):
  System shows:
    - Specific: Actual cost (LIFO), exact inventory
    - Generic: Estimated cost (LIFO average), aggregate inventory
    - Unassigned: Cost TBD, inventory unknown

MAKE Mode (Assembly stage):
  System ENFORCES decision:
    - BLOCKS assembly if generic/unassigned materials remain
    - User MUST assign specific MaterialProducts
    - Shows LIFO inventory for selection
    - "Record Assembly Anyway" bypass allowed (flags for reconciliation)
```

---

### 3.8 Materials in Assembly Workflow

**REQ-M-023: Material Service Primitives for Assembly**

MaterialInventoryService and MaterialConsumptionService SHALL provide primitives to support assembly operations:

**Service Primitives Required**:

1. **get_lifo_inventory(material_product_id)**: Query MaterialInventoryItem in LIFO order
   - Returns: List of inventory items ordered by purchased_at DESC
   - Used by: AssemblyService to check availability

2. **validate_inventory_availability(material_requirements)**: Check sufficient inventory
   - Input: List of (material_product_id, quantity_needed) tuples
   - Returns: bool (available/insufficient) + details
   - Used by: AssemblyService pre-assembly validation

3. **consume_material_lifo(material_product_id, quantity, assembly_run_id)**: Perform LIFO consumption
   - Creates MaterialConsumption record(s) with inventory_item_id linkage
   - Decrements MaterialInventoryItem.quantity_remaining
   - Returns: Total cost (sum of LIFO costs), list of MaterialConsumption records
   - Used by: AssemblyService during assembly execution

4. **calculate_material_costs(material_consumption_records)**: Calculate cost totals
   - Input: List of MaterialConsumption records
   - Returns: Total material cost
   - Used by: AssemblyService for AssemblyRun.total_material_cost

**Assembly Service Responsibilities**:
- Read FinishedGood definition (MaterialUnits + Material placeholders)
- Enforce business rules (block if placeholders exist)
- Call MaterialInventoryService.validate_inventory_availability()
- For each MaterialUnit: Call MaterialInventoryService.consume_material_lifo()
- Calculate AssemblyRun.total_material_cost using returned costs
- Create AssemblyRun record with material cost totals

**Separation of Concerns**:
- **MaterialInventoryService**: Owns LIFO consumption logic, inventory tracking
- **MaterialConsumptionService**: Owns MaterialConsumption records, cost snapshots
- **AssemblyService** (future): Owns assembly workflow, business rules, orchestration

**REQ-M-024: Enhanced AssemblyRun Model**

AssemblyRun SHALL track costs separately:

```python
AssemblyRun:
    # Existing (F046)
    total_component_cost: Decimal  # FinishedUnit costs (LIFO)
    
    # Materials (F047)
    total_material_cost: Decimal  # Material costs (LIFO)
    
    # Totals
    total_assembly_cost: Decimal  # Components + materials
    per_unit_assembly_cost: Decimal  # Total cost per assembled unit
    
    # Reconciliation flag
    requires_material_reconciliation: bool  # True if "Record Anyway" bypass used
```

**REQ-M-025: MaterialConsumption Model**

MaterialConsumption SHALL track material usage with complete identity:

```python
MaterialConsumption:
    assembly_run_id: int  # FK to AssemblyRun
    
    # IDENTITY CAPTURE (immutable snapshots)
    material_id: int  # Material type (abstract)
    material_product_id: int  # Specific product used
    inventory_item_id: int  # FK to MaterialInventoryItem (LIFO tracking)
    display_name_snapshot: str  # Name at consumption time
    
    # QUANTITY
    quantity_consumed: Decimal  # Units consumed (in base units)
    
    # COST SNAPSHOT (immutable, from MaterialInventoryItem)
    cost_per_unit: Decimal  # Cost at assembly time (LIFO)
```

**REQ-M-026: Assembly Cost Example**

```
AssemblyRun: "Holiday Gift Box" × 50

Component costs (LIFO from FinishedUnits):
  300 cookies @ $0.42 = $126.00
  150 brownies @ $0.65 = $97.50
  Subtotal: $223.50

Material costs (LIFO from MaterialInventoryItem):
  50 bags @ $0.28 (Item C, newest) = $14.00
  100 tissue sheets @ $0.05 (Item A) = $5.00
  Subtotal: $19.00

Total assembly cost: $242.50
Per unit cost: $4.85
```

---

### 3.9 Materials Inventory Management

**REQ-M-027: Inventory View Location**

Materials inventory SHALL be displayed in Make mode ONLY (not Catalog):

**Make > Materials > Inventory**:
- Shows MaterialInventoryItem lots (detail view)
- Columns: Product, Purchase Date, Qty Purchased, Qty Remaining, Cost/Unit, Total Value
- Sorted by: product_name, purchased_at DESC (newest first)
- Enables manual adjustments (creates/updates MaterialInventoryItem)

**Catalog > Materials > Material Products**:
- Shows product definitions ONLY
- Columns: Name, Brand, SKU, Package Info, Supplier
- NO cost columns ❌
- NO inventory columns ❌
- Link to "View Inventory" → redirects to Make mode

**REQ-M-028: Manual Inventory Adjustments**

Manual inventory adjustments SHALL create/update MaterialInventoryItem records:

**For "Each" Materials**:
- Adjustment by count (+10 bags, -5 boxes)
- Creates MaterialInventoryItem with:
  - quantity_purchased = adjustment quantity
  - quantity_remaining = adjustment quantity
  - cost_per_unit = 0 (or estimated)
  - purchased_at = adjustment timestamp

**For "Variable" Materials**:
- Adjustment by percentage ("50% of roll remains")
- Updates existing MaterialInventoryItem.quantity_remaining
- Calculation: new_remaining = current_remaining × percentage
- NO cost change (keeps original cost_per_unit)

**REQ-M-029: Adjustment Workflow**

```
Material: "Red Ribbon" (base_unit_type: "linear_inches")
MaterialProduct: "Michaels 100ft Roll"

Current MaterialInventoryItem:
  quantity_purchased: 1200 inches
  quantity_remaining: 800 inches
  cost_per_unit: $0.10/inch

User adjusts: "Used ribbon on personal project, about 20% remaining"

System calculates:
  new_remaining = 800 × 0.20 = 160 inches

Updates MaterialInventoryItem:
  quantity_remaining: 160 inches
  cost_per_unit: $0.10/inch (unchanged)
```

---

### 3.10 Materials in Cost Reporting

**REQ-M-030: Integrated Cost Reporting**

Materials costs SHALL appear alongside food costs using LIFO actual costs:

1. **FinishedGood BOM View (estimated)**:
```
Holiday Gift Box BOM:
  Food components: $4.47 (estimated, from current LIFO inventory)
  Material components: $0.50 (estimated, weighted avg if generic)
  Total: $4.97 (estimated)
```

2. **Event Cost Summary (estimated vs actual)**:
```
Christmas 2025 Event:
  Ingredient costs: $567.00 (actual LIFO)
  Material costs: $143.00 (estimated if generic, actual if specific)
  Total event cost: $710.00
```

3. **Assembly Cost Breakdown (actual)**:
```
AssemblyRun: 50 Holiday Gift Boxes
  Component costs: $223.50 (actual LIFO)
  Material costs: $19.00 (actual LIFO)
  Total: $242.50 (actual)
```

**REQ-M-031: No Separate Material Reports (Initially)**

Dedicated material reports SHALL be deferred:
- No material-specific inventory reports (beyond basic Make > Inventory view)
- No material purchase history reports (beyond purchase list)
- No material cost trend analysis
- Rationale: Materials costs reported in context with food costs

---

### 3.12 Materials UI Requirements

**REQ-M-034: Materials Tab (CATALOG Mode)**

CATALOG mode SHALL have Materials tab with:
- MaterialProduct management (CRUD, NO cost/inventory display)
- MaterialUnit management (CRUD, shows inherited unit type)

**Note**: Material hierarchy management (Categories, Subcategories, Materials) already exists in **Catalog > Materials Hierarchy** menu.

**Catalog > Materials > Material Products**:
- Columns: Name, Brand, SKU, Package (qty + unit), Supplier, Actions
- NO cost column ❌
- NO inventory column ❌
- Link button: "View Inventory" → Purchase > Inventory

**REQ-M-035: Materials Purchasing (PURCHASE Mode)**

Purchase mode SHALL provide materials purchasing workflow:
- Product type selector: ○ Food  ○ Material
- When Material selected:
  - MaterialProduct dropdown
  - Package quantity fields (count + unit)
  - Total cost field
  - System calculates unit cost
  - Creates MaterialPurchase + MaterialInventoryItem

**REQ-M-036: Materials Inventory (PURCHASE Mode)**

Purchase > Inventory SHALL show MaterialInventoryItem lots:
- Columns: Product, Purchased Date, Qty Purchased, Qty Remaining, Cost/Unit, Total Value
- Filter by: MaterialProduct, Date range
- Sort by: Product name, Purchase date
- Manual adjustment button (opens adjustment dialog)
- Shows LIFO order visually (newest first)

**REQ-M-037: Material Selection in FinishedGood**

FinishedGood edit dialog SHALL allow material selection:
- **Radio button choice**: ○ Specific MaterialUnit  ○ Generic Material  ○ None
- If Specific MaterialUnit:
  - Dropdown shows MaterialUnits
  - Shows calculated inventory (from MaterialInventoryItem aggregate)
  - Shows calculated cost (LIFO)
- If Generic Material:
  - Dropdown shows Materials
  - Shows aggregate inventory: "Available: 82 bags (across 4 products)"
  - Shows estimated cost (weighted average)
- If None: No material selected (completely deferred)

**REQ-M-038: Materials in Assembly Recording**

Assembly recording dialog SHALL:
- **HARD STOP**: Block assembly if generic/unassigned materials remain
- Display warning: "⚠️ Packaging not finalized"
- Provide **quick assignment interface**:
  - List unassigned materials
  - Show available MaterialProducts with LIFO inventory
  - Checkbox selection + quantity entry
  - Running total: "Assigned: X / Y needed"
- Actions:
  - "Assign Materials" (completes assignment, proceeds)
  - "Record Assembly Anyway" (bypass, sets requires_material_reconciliation = true)
- Show material costs (LIFO actual costs)
- Display total assembly cost (components + materials)

**REQ-M-039: Material Unit Type Display**

Material Unit creation/edit dialog SHALL clearly show inherited unit type:

**When Material selected**:
```
Material: [Red Ribbon ▼]  ← Dropdown
Unit type: linear_cm (inherited from Red Ribbon)  ← Read-only display

Quantity per unit (in linear_cm): [15.0]  ← Dynamic label
Preview: "This unit will consume 15 cm of Red Ribbon"
```

**For "each" Materials**:
```
Material: [Gift Box 6x6x3 ▼]
Unit type: each (inherited from Gift Box 6x6x3)

Quantity per unit: 1 (each type)  ← Read-only, always 1
Preview: "This unit will consume 1 Gift Box 6x6x3"
```

---

### 3.13 Materials Import/Export

**REQ-M-040: First-Class Import/Export Support**

Materials import/export SHALL be equal to ingredients import/export:

**Catalog Import (ADD_ONLY mode)**:
- MaterialCategory import
- MaterialSubcategory import (with category references)
- Material import (with subcategory references, base_unit_type required)
- MaterialProduct import (with material references, NO cost/inventory fields)
- MaterialUnit import (with material references)

**View Import/Export**:
- MaterialPurchase import/export (creates MaterialInventoryItem on import)
- MaterialInventoryItem snapshot export (for backup/analysis)

**Export Format v4.3**:
```json
{
  "version": "4.3",
  "exported_at": "2026-01-18T10:00:00Z",
  "material_categories": [...],
  "material_subcategories": [...],
  "materials": [
    {
      "slug": "red-satin-ribbon",
      "name": "Red Satin Ribbon",
      "base_unit_type": "linear_cm",  // Required
      "subcategory_slug": "satin-ribbons"
    }
  ],
  "material_products": [
    {
      "slug": "michaels-red-satin-100ft",
      "name": "100ft Red Satin Roll",
      "material_slug": "red-satin-ribbon",
      "package_quantity": 100.0,
      "package_unit": "feet",
      "quantity_in_base_units": 3048.0,  // Auto-calculated (100 ft × 30.48)
      // NO cost fields
      // NO inventory fields
    }
  ],
  "material_units": [
    {
      "slug": "15cm-red-ribbon",
      "name": "15cm Red Ribbon",
      "material_slug": "red-satin-ribbon",
      "quantity_per_unit": 15.0  // Interpreted in linear_cm
    }
  ]
}
```

**REQ-M-041: Import Validation**

Material import SHALL validate:
- base_unit_type is one of: "each", "linear_cm", "square_cm"
- MaterialProduct.package_unit is convertible to Material.base_unit_type
- MaterialProduct.quantity_in_base_units matches conversion (auto-correct if different)
- MaterialUnit.quantity_per_unit = 1 if Material.base_unit_type = "each"

---

### 3.14 Validation & Business Rules

**REQ-M-042: Inventory Constraints and Service Boundaries**

**MaterialInventoryService SHALL enforce**:
- MaterialInventoryItem.quantity_remaining >= 0 (cannot go negative)
- Provides `validate_sufficient_inventory(material_product_id, quantity)` primitive
- Provides `can_delete_material_product(material_product_id)` check
- Returns: False if MaterialInventoryItem records exist for product

**MaterialCatalogService SHALL enforce**:
- Cannot delete MaterialProduct if MaterialInventoryItem exists (calls MaterialInventoryService)
- Cannot delete MaterialProduct if used in MaterialUnit (calls MaterialUnitService)
- Cannot delete MaterialUnit if used in FinishedGood composition (calls CompositionService)
- Cannot delete Material if used in Composition as placeholder (calls CompositionService)

**Assembly-Related Constraints** (enforced by future AssemblyService):
- Check insufficient material inventory using MaterialInventoryService.validate_sufficient_inventory()
- Check generic/unassigned materials using CompositionService.has_unresolved_materials()
- AssemblyService owns business rules (when to block, when to allow bypass)
- MaterialInventoryService provides data primitives only

**Separation of Concerns**:
- **MaterialInventoryService**: Data integrity, LIFO logic, inventory queries
- **MaterialCatalogService**: Catalog operations, deletion constraints (delegates to other services)
- **AssemblyService** (future): Assembly workflow, business rules, orchestration

**REQ-M-043: Purchase Validation**

System SHALL validate:
- package_unit_count > 0
- packages_purchased > 0
- total_cost >= 0
- calculated_unit_cost >= 0
- package_unit is convertible to Material.base_unit_type

**REQ-M-044: Composition Constraints**

System SHALL enforce:
- Composition has EXACTLY ONE of finished_unit_id, material_unit_id, or material_id
- quantity > 0
- Cannot delete FinishedUnit/MaterialUnit/Material if used in active FinishedGood

**REQ-M-045: Assembly Service Integration Requirements**

**MaterialInventoryService SHALL provide** primitives for AssemblyService:

1. **validate_material_availability(requirements)**:
   - Input: List of (material_product_id, quantity_needed)
   - Returns: `{available: bool, details: {...}}`
   - Used by AssemblyService for pre-assembly validation

2. **check_unresolved_materials(finished_good_id)**:
   - Queries Composition table for material_id placeholders (generic materials)
   - Returns: List of unresolved material references
   - Used by AssemblyService to detect incomplete definitions

3. **consume_materials_lifo(consumption_requests, assembly_run_id)**:
   - Executes LIFO consumption for multiple materials
   - Creates MaterialConsumption records
   - Returns: Total cost, list of consumption records
   - Called by AssemblyService during assembly execution

**AssemblyService SHALL enforce** (business rules):
- **BLOCK assembly** if check_unresolved_materials() returns any placeholders
- **BLOCK assembly** if any Composition has NULL material references
- **BLOCK assembly** if validate_material_availability() returns insufficient inventory
- User MUST resolve to specific material_unit_id before proceeding
- UNLESS user selects "Record Assembly Anyway" bypass:
  - AssemblyRun.requires_material_reconciliation = true
  - Cost calculations exclude unassigned materials
  - AssemblyService logs warning, proceeds with partial data

**Separation of Concerns**:
- **MaterialInventoryService**: Provides data queries, LIFO consumption primitives
- **CompositionService**: Manages Composition records, provides unresolved material checks
- **AssemblyService** (future): Owns assembly business logic, enforces workflow rules, orchestrates materials/components consumption

**REQ-M-046: Unit Type Validation**

System SHALL validate:
- Material.base_unit_type in ("each", "linear_cm", "square_cm")
- MaterialUnit.quantity_per_unit = 1 if Material.base_unit_type = "each"
- MaterialProduct.package_unit convertible to Material.base_unit_type
- MaterialProduct.quantity_in_base_units = package_quantity × conversion_factor

---

## 4. Success Criteria

### 4.1 Functional Acceptance Criteria

Feature F047 is considered complete when:

1. ✅ Materials ontology hierarchy exists (3 levels with base_unit_type)
2. ✅ MaterialProduct catalog operational (CRUD + UI, NO cost/inventory display)
3. ✅ **MaterialInventoryItem table exists and functional**
4. ✅ MaterialUnit catalog operational (CRUD + UI, shows inherited unit type)
5. ✅ **Can purchase materials, creates MaterialInventoryItem (LIFO)**
6. ✅ **Unit type inheritance enforced** (Material → Product → Unit)
7. ✅ **Auto-conversion to base units functional** (feet → inches)
8. ✅ Can add MaterialUnits to FinishedGood composition
9. ✅ Can add generic Material placeholders to FinishedGood composition
10. ✅ Planning shows estimated costs for generic materials
11. ✅ **Assembly hard stop enforces material resolution**
12. ✅ **LIFO consumption from MaterialInventoryItem functional**
13. ✅ Can record assembly with materials, **LIFO costs captured**
14. ✅ AssemblyRun shows component costs + material costs separately (both LIFO)
15. ✅ **MaterialInventoryItem.quantity_remaining decrements on assembly**
16. ✅ Cannot assemble if insufficient material inventory (LIFO check)
17. ✅ Materials costs appear in event planning (LIFO actual costs)
18. ✅ **Import/export works for materials catalog (first-class support)**
19. ✅ Manual inventory adjustment works (creates/updates MaterialInventoryItem)
20. ✅ **Catalog UI shows NO cost/inventory** (definition layer clean)
21. ✅ **Purchase > Inventory shows MaterialInventoryItem lots** (instantiation layer)

### 4.2 Quality Criteria

1. ✅ Materials model **strictly parallels** Ingredient model (LIFO, definition/instantiation)
2. ✅ **MaterialInventoryItem structure matches ProductInventoryItem**
3. ✅ **LIFO consumption logic identical to ingredients**
4. ✅ All business rules enforced (validation constraints)
5. ✅ UI follows existing patterns (users understand by analogy)
6. ✅ No material data in ingredient tables (strict separation)
7. ✅ **Cost calculations accurate (LIFO verified, not weighted average)**
8. ✅ Assembly workflow consistent (matches food pattern)
9. ✅ **Unit type inheritance clear in UI**
10. ✅ **Auto-conversion calculations correct**

### 4.3 Documentation Criteria

1. ✅ Materials ontology management documented (with unit type inheritance)
2. ✅ Materials purchasing workflow documented (LIFO inventory creation)
3. ✅ MaterialUnit creation workflow documented (unit type inheritance)
4. ✅ **LIFO consumption explained** (parallel to ingredients)
5. ✅ **Definition/instantiation boundary documented**
6. ✅ Import/export format documented (with base_unit_type, no cost/inventory)
7. ✅ **Auto-conversion rules documented**

---

## 5. Dependencies & Constraints

### 5.1 Prerequisites

- ✅ F046 (Finished Goods, Bundles & Assembly Tracking) - Complete
- ✅ F026 (Deferred Packaging Decisions) - Pattern validated
- ✅ Ingredient LIFO system - Functional (pattern to copy)

### 5.2 Enables

- F048: Shopping Lists Tab Implementation (needs material requirements)
- F049: Assembly Workflows Enhancement (needs material tracking)
- Future: Multi-user web version (materials infrastructure ready, LIFO intact)
- Future: E-commerce integration (dual supply chain ready)

### 5.3 Technical Constraints

**Database:**
- SQLite (current), PostgreSQL (web version)
- Must support Decimal for cost accuracy
- Must support LIFO queries (ORDER BY purchased_at DESC)
- Composition table requires THREE optional foreign keys (finished_unit_id, material_unit_id, material_id)

**UI:**
- CustomTkinter (current desktop)
- Must follow existing catalog patterns
- Must integrate into existing CATALOG/MAKE modes
- **Must clearly separate Catalog (definitions) from Make (instantiations)**
- **Must support LIFO inventory display**

**Import/Export:**
- JSON format (existing)
- Must maintain version compatibility (v4.3+)
- **Must NOT import/export cost/inventory in catalog**

---

## 6. Migration from v2.1 to v3.0

### 6.1 Breaking Changes

**Schema Changes Required**:

1. **DROP from MaterialProduct**:
   ```sql
   ALTER TABLE material_products DROP COLUMN current_inventory;
   ALTER TABLE material_products DROP COLUMN weighted_avg_cost;
   ```

2. **CREATE MaterialInventoryItem table**:
   ```sql
   CREATE TABLE material_inventory_items (
       id INTEGER PRIMARY KEY,
       material_product_id INTEGER NOT NULL,
       material_purchase_id INTEGER NOT NULL,
       quantity_purchased DECIMAL(10,3) NOT NULL,
       quantity_remaining DECIMAL(10,3) NOT NULL,
       cost_per_unit DECIMAL(10,4) NOT NULL,
       purchased_at DATETIME NOT NULL,
       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
       updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (material_product_id) REFERENCES material_products(id),
       FOREIGN KEY (material_purchase_id) REFERENCES material_purchases(id)
   );
   ```

3. **UPDATE MaterialConsumption**:
   ```sql
   ALTER TABLE material_consumption 
   ADD COLUMN inventory_item_id INTEGER REFERENCES material_inventory_items(id);
   ```

### 6.2 Data Migration Strategy

**Option A: Fresh Start (RECOMMENDED for v2.1 users)**:
1. Export MaterialProduct catalog (definitions only)
2. Reset database (drop materials tables)
3. Import MaterialProduct catalog
4. User re-enters MaterialPurchases (creates MaterialInventoryItem)

**Option B: Historical Purchase Conversion**:
1. For each MaterialPurchase in v2.1:
   - Create MaterialInventoryItem with:
     - quantity_purchased = total_units
     - quantity_remaining = 0 (already consumed)
     - cost_per_unit = calculated_unit_cost
     - purchased_at = purchased_at
2. Current inventory lost (acceptable - user does physical count)

**Recommendation**: Option A - Clean migration, minimal risk

---

## 7. Non-Functional Requirements

### 7.1 Performance

- Materials catalog search: < 100ms for 1000+ products
- **LIFO inventory query: < 50ms for 100+ inventory items**
- **MaterialInventoryItem aggregation: < 100ms**
- Assembly cost calculation: < 500ms for 20+ materials
- Generic material aggregate inventory calculation: < 50ms
- Assignment interface load: < 200ms for 100+ MaterialProducts

### 7.2 Usability

- Materials UI mirrors ingredients UI (LIFO patterns identical)
- Ontology navigation follows same patterns
- Purchase workflow familiar (creates inventory items)
- **Catalog clearly shows "definitions only" (no cost/inventory)**
- **Make mode clearly shows "current state" (inventory lots)**
- **Unit type inheritance visually clear**
- **Auto-conversion transparent to user**

### 7.3 Extensibility

- Architecture supports future e-commerce integration
- LIFO pattern enables audit trail (web version)
- MaterialInventoryItem supports future fields (color, dimensions)
- **Strict definition/instantiation enables multi-user (web version)**

### 7.4 Data Integrity

- Strict separation prevents material/ingredient mixing
- **LIFO costing maintains accuracy (matches ingredients)**
- Inventory constraints prevent negative stock (MaterialInventoryItem.quantity_remaining >= 0)
- Assembly enforcement prevents incomplete data
- **MaterialConsumption always has resolved material_unit_id (never material_id)**
- **Cost snapshots immutable (historical accuracy preserved)**

---

## 8. Assumptions

1. Users will manually enter package quantities (no barcode scanning)
2. **LIFO costing acceptable for materials** (matches ingredient pattern)
3. Percentage-based adjustment sufficient for variable materials
4. No existing v2.1 materials data to migrate (or users accept fresh start)
5. Sample data will be provided separately by user
6. Users comfortable with "estimated" vs "actual" cost distinction
7. "Record Assembly Anyway" bypass rarely used (exceptional cases only)
8. **Users understand Catalog = definitions, Make = current state**
9. **Auto-conversion (feet → inches) acceptable to users**

---

## 9. Risks & Mitigation

### Risk 1: Migration Complexity

**Risk**: v2.1 → v3.0 migration requires MaterialInventoryItem creation

**Mitigation**:
- Recommend fresh start (export definitions, reset, import)
- Provide clear migration documentation
- User does physical inventory count post-migration
- Estimated effort: 2-4 hours for migration script

### Risk 2: LIFO Implementation Complexity

**Risk**: LIFO consumption logic more complex than weighted average

**Mitigation**:
- Copy validated ingredient LIFO pattern (already works)
- Comprehensive unit tests (parallel to ingredient tests)
- User testing with sample assemblies before production use
- Estimated effort: 4-6 hours for LIFO service layer

### Risk 3: Unit Type Confusion

**Risk**: Users may not understand Material.base_unit_type inheritance

**Mitigation**:
- Clear UI labels ("inherited from X")
- Preview text showing interpretation
- Documentation with examples
- Validation prevents mismatches

### Risk 4: Auto-Conversion Errors

**Risk**: Package unit conversion to base units may be incorrect

**Mitigation**:
- Supported conversions only (feet↔inches, yards↔inches, etc.)
- Show calculated quantity_in_base_units for verification
- Unit tests for all conversion factors
- User can verify in UI: "100 feet = 1200 inches"

### Risk 5: UI Complexity

**Risk**: Catalog vs Make separation may confuse users

**Mitigation**:
- Clear mode labels (CATALOG vs MAKE)
- Footer text: "Catalog shows definitions only"
- "View Inventory" link connects concepts
- User testing with Marianne validates clarity

---

## 10. Open Questions & Decisions

### 10.1 Resolved

- ✅ Parallel to Ingredient model (Yes - **strict parallelism**, LIFO required)
- ✅ MaterialInventoryItem needed (Yes - **separate table**, parallel to ProductInventoryItem)
- ✅ MaterialUnit model needed (Yes)
- ✅ Ontology levels (3: Category → Subcategory → Material with base_unit_type)
- ✅ Inventory tracking (LIFO via MaterialInventoryItem, not weighted average)
- ✅ Composition links (MaterialUnit OR Material, deferred decision)
- ✅ Variable material adjustment (Percentage-based)
- ✅ Material decision timing (Flexible: catalog or assembly)
- ✅ **Definition/instantiation split** (Strict - MaterialProduct has NO cost/inventory)
- ✅ **Unit type inheritance** (Material.base_unit_type → all products/units)
- ✅ **Auto-conversion** (System converts package_unit to base_unit_type)
- ✅ **MaterialUnit.quantity_per_unit** (1 for "each", user-defined for "variable")

### 10.2 Deferred to Specification Phase

- **MaterialInventoryItem lot display details** (columns, sorting, filters)
- **LIFO consumption UI** (how to show which lots consumed)
- Specific UI layout/mockups
- Error message wording
- Specific validation error codes
- Quick assignment interface detailed design
- Import/export JSON schema details (v4.3 format)

---

## 11. Approval

**Requirements Author**: Claude (Anthropic AI)
**Requirements Reviewer**: Kent Gale
**Date**: 2026-01-18

**Status**: ⏳ DRAFT - Under Review

**Changes from v2.1**:

**BREAKING CHANGES**:
- ✅ MaterialProduct: REMOVED current_inventory and weighted_avg_cost fields
- ✅ MaterialInventoryItem: NEW table for LIFO inventory tracking
- ✅ MaterialConsumption: Added inventory_item_id for LIFO linkage
- ✅ Purchasing: Creates MaterialInventoryItem (not updating MaterialProduct fields)
- ✅ Consumption: LIFO from MaterialInventoryItem (not weighted average)

**NEW REQUIREMENTS**:
- ✅ REQ-M-005: Inherited unit type (Material → MaterialProduct)
- ✅ REQ-M-006: Auto-conversion to base units (cm-based storage, imperial/metric inputs)
- ✅ REQ-M-008-010: MaterialInventoryItem table and LIFO consumption
- ✅ REQ-M-014-016: Strict definition/instantiation separation
- ✅ REQ-M-018-019: Unit type inheritance and validation
- ✅ REQ-M-039: Material unit type display (UI shows inheritance)
- ✅ REQ-M-040-041: First-class import/export (catalog only, no cost/inventory)

**UPDATED REQUIREMENTS**:
- Updated REQ-M-001: Added base_unit_type to Material
- Updated REQ-M-004: MaterialProduct is definition only (removed cost/inventory)
- Updated REQ-M-011-013: Purchasing creates MaterialInventoryItem
- Updated REQ-M-023-026: Assembly uses LIFO consumption
- Updated REQ-M-027-029: Inventory view in Make mode only
- Updated REQ-M-034-036: UI requirements (Catalog vs Make separation)

**Next Steps**:
1. Kent reviews requirements v3.0
2. Approve or request changes
3. Create F0XX migration specification (v2.1 → v3.0)
4. Create F0XX materials LIFO implementation specification
5. Queue for implementation via spec-kitty

---

**END OF REQUIREMENTS DOCUMENT**
