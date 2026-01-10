# Requirements: Materials Management System

**Document ID**: REQ-MATERIALS-001
**Version**: 2.1
**Date**: 2026-01-10
**Status**: Pending Approval
**Feature ID**: F047 (Packaging Materials Foundation)
**Changelog**: v2.1 - Added identity snapshot principle (REQ-M-042); Updated REQ-M-012, REQ-M-013, REQ-M-020, REQ-M-041 for complete identity capture

---

## 1. Executive Summary

### 1.1 Purpose

Implement a comprehensive materials management system that parallels the existing ingredient management system, enabling proper handling of non-edible materials (ribbon, boxes, bags, tissue, etc.) used in baking assemblies.

### 1.2 Problem Statement

**Current State:**
- Materials are incorrectly modeled as Ingredients (temporary workaround)
- Cannot properly track packaging materials with appropriate metadata
- Pollutes ingredient model with non-food items
- Blocks complete FinishedGood assemblies (cannot add ribbon/boxes)

**Required State:**
- Separate materials ontology and product catalog
- Materials purchasing, inventory, and consumption workflows
- Materials integrated into assembly cost calculations
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
Materials MUST parallel Ingredient model exactly to ensure:
- Consistent workflows (catalog, purchasing, inventory)
- Unified UI patterns (users understand one, understand both)
- Observability parity (reports show food + materials side-by-side)
- Extensibility for web/commerce features

---

## 2. Scope

### 2.1 In Scope

**Data Model:**
- ✅ Materials ontology hierarchy (3 levels: Category → Subcategory → Material)
- ✅ MaterialProduct catalog (physical purchasable items)
- ✅ MaterialUnit model (atomic consumption units, parallel to FinishedUnit)
- ✅ Materials purchasing workflow (packages → atomic units)
- ✅ Materials inventory system (weighted average costing)
- ✅ Materials consumption tracking in AssemblyRun
- ✅ Materials cost calculations (alongside ingredient costs)
- ✅ **Deferred material decision workflow** (generic placeholders)

**Integration:**
- ✅ FinishedGood compositions (FinishedUnits + MaterialUnits + Material placeholders)
- ✅ AssemblyRun enhancements (component costs + material costs)
- ✅ Event planning cost calculations (include materials, estimated vs actual)
- ✅ Import/export (catalog + view data)
- ✅ **Assembly hard stop** (enforce material resolution)

**UI:**
- ✅ Materials ontology management (categories, subcategories)
- ✅ MaterialProduct catalog CRUD
- ✅ MaterialUnit catalog CRUD
- ✅ Materials purchasing workflow
- ✅ Materials inventory view
- ✅ Manual inventory adjustments
- ✅ Material selection in FinishedGood composition (specific/generic/none)
- ✅ **Pending decision indicators** (⚠️ throughout workflow)
- ✅ **Material assignment interface** (quick assign at assembly)
- ✅ Materials costs in assembly recording (actual vs estimated)
- ✅ Materials costs in event planning

### 2.2 Out of Scope (Deferred)

**Deferred to Future Features:**
- ❌ Rich metadata (structured dimensions, color, material_type fields)
- ❌ Unit conversions beyond feet↔inches
- ❌ "Packaging" vs "Materials" differentiation (keep generic "Materials")
- ❌ Materials-specific reporting/analytics (beyond cost reporting)
- ❌ Lot tracking for materials (use aggregate inventory only)
- ❌ FIFO costing for materials (use weighted average)
- ❌ Low stock alerts
- ❌ Automated reordering
- ❌ **Automatic assignment algorithms** (F026 deferred)
- ❌ **Packaging templates** (F026 deferred)
- ❌ **Partial commitment** (F026 deferred)

**Not Required:**
- ❌ Migration from "packaging ingredients" (no existing data)
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
Material (Level 3 - Abstract)
  Examples: "Red Satin Ribbon", "Small Gift Box 6x6x3", "6\" Cellophane Bag"
  ↓
MaterialProduct (Physical - Purchasable)
  Examples: "Michaels Red Satin 100ft Roll", "Amazon 6x6x3 White Box 50pk"
```

**REQ-M-002: Parallel to Ingredient Structure**

The materials ontology SHALL exactly parallel the ingredient ontology structure:
- MaterialCategory ↔ IngredientCategory
- MaterialSubcategory ↔ IngredientSubcategory  
- Material ↔ Ingredient
- MaterialProduct ↔ Product

**REQ-M-003: Shared Supplier Table**

Materials and ingredients SHALL share a single Suppliers table:
- No separate MaterialSupplier table
- Supplier.supplier_type NOT required (one supplier can provide both)
- Maintains single vendor management system

---

### 3.2 MaterialProduct Catalog

**REQ-M-004: Product-Level Inventory Tracking**

Inventory SHALL be tracked at MaterialProduct level (NOT Material level):
```
Material: "Red Satin Ribbon" (abstract)
  ↓
MaterialProduct: "Michaels Red Satin 100ft Roll"
  - inventory_count: 250.0 (linear_feet)
  - current_unit_cost: $0.12 (per linear_foot)
  
MaterialProduct: "Amazon Red Satin 50ft Roll"  
  - inventory_count: 100.0 (linear_feet)
  - current_unit_cost: $0.10 (per linear_foot)
```

**REQ-M-005: Essential Product Attributes**

MaterialProduct SHALL have:
- display_name (required)
- material_id (FK to Material, required)
- default_unit (required: "each", "linear_inches", "square_feet")
- inventory_count (aggregate, Decimal, default 0.0)
- current_unit_cost (weighted average, Decimal)
- supplier_id (FK to Supplier, optional)
- notes (freeform text for dimensions, color, etc.)

**REQ-M-006: Product Type Differentiation**

Product table SHALL have product_type field:
- Values: "food", "material"
- Enables unified Product table OR separate MaterialProduct table
- Decision: Use separate MaterialProduct table for clarity

---

### 3.3 Materials Purchasing Workflow

**REQ-M-007: Package-Based Purchasing**

Materials purchasing SHALL track both package-level and atomic-level quantities:

```python
MaterialPurchase:
    material_product_id: int          # What was purchased
    package_unit_count: Decimal       # e.g., 25 (bags per pack)
    packages_purchased: Decimal       # e.g., 4 (packs bought)
    total_units: Decimal              # 100 (calculated: 25 × 4)
    calculated_unit_cost: Decimal     # $0.40/bag (calculated)
    total_cost: Decimal               # $40.00 (entered by user)
    purchased_at: DateTime            # When purchased
    supplier_id: int                  # Optional supplier
```

**REQ-M-008: Unit Cost Calculation**

Unit cost SHALL be stored in both locations:
1. **MaterialPurchase.calculated_unit_cost**: Historical record per purchase
2. **MaterialProduct.current_unit_cost**: Weighted average (updated on purchase)

**REQ-M-009: Weighted Average Costing**

MaterialProduct.current_unit_cost SHALL be recalculated on each purchase:

```
Formula:
new_weighted_avg = (
    (old_inventory × old_unit_cost) + (purchased_units × purchase_unit_cost)
) / (old_inventory + purchased_units)

Example:
Current: 200 bags @ $0.35 = $70.00
Purchase: 100 bags @ $0.40 = $40.00
New: 300 bags @ $0.3667 = $110.00
```

**REQ-M-010: Purchase Workflow**

User purchasing workflow SHALL:
1. Select MaterialProduct
2. Enter package_unit_count (e.g., "25 bags per pack")
3. Enter packages_purchased (e.g., "4 packs")
4. System calculates total_units (100 bags)
5. Enter total_cost ($40.00)
6. System calculates unit_cost ($0.40/bag)
7. System updates inventory_count (+100 bags)
8. System recalculates weighted average unit_cost

---


---

### 3.4 Definition/Instantiation Separation

**REQ-M-041: Definition/Instantiation Separation**

Materials SHALL follow the same definition/instantiation pattern as ingredients:

**Definition Layer (Catalog - NO stored costs):**
- Material (abstract concept)
- MaterialProduct (purchasable item)
- MaterialUnit (consumption unit)
- FinishedGood with Material/MaterialUnit components

Definition entities SHALL NOT store cost data. Cost calculations SHALL be dynamic:
- MaterialProduct.current_unit_cost: Weighted average (recalculated on purchase)
- MaterialUnit cost: Calculated from MaterialProduct.current_unit_cost
- FinishedGood material cost: Calculated from MaterialUnit costs (actual or estimated)

**Instantiation Layer (Transactional - Immutable cost snapshots):**
- MaterialPurchase (records calculated_unit_cost at purchase time)
- MaterialConsumption (records per_unit_cost at assembly time)
- AssemblyRun (records total_material_cost at assembly time)

**Cost Snapshot Rules:**

1. **MaterialPurchase** captures cost at purchase time:
   ```python
   MaterialPurchase:
       calculated_unit_cost: Decimal  # Snapshot: total_cost ÷ total_units
       # Never recalculated, immutable historical record
   ```

2. **MaterialConsumption** captures cost at assembly time:
   ```python
   MaterialConsumption:
       per_unit_cost: Decimal  # Snapshot: MaterialProduct.current_unit_cost
       # Frozen at assembly time, never updated
   ```

3. **AssemblyRun** captures aggregate material cost:
   ```python
   AssemblyRun:
       total_material_cost: Decimal  # Sum of MaterialConsumption costs
       # Immutable snapshot of material costs at assembly time
   ```



**Identity Snapshot Rules (Parallel to Cost Snapshots):**

Materials instantiations SHALL capture complete identity information, enabling historical reconstruction without catalog dependency:

1. **MaterialConsumption** captures identity at assembly time:
   ```python
   MaterialConsumption:
       material_id: int              # Material type (immutable)
       material_product_id: int      # Specific product (immutable)
       quantity_per_unit: Decimal    # Unit size (immutable)
       display_name_snapshot: str    # Name at consumption time (immutable)
       # Never updated when catalog changes
   ```

2. **AssemblyConsumption** captures identity at assembly time:
   ```python
   AssemblyConsumption:
       finished_unit_id: int         # Baked good consumed (immutable)
       quantity_consumed: int        # Quantity (immutable)
       per_unit_cost: Decimal        # Cost snapshot (immutable)
   ```

3. **Identity snapshot examples:**
   ```
   Year 1: Create MaterialProduct "Snowflake Bag 6""
   Year 1: Assemble gift boxes, consume Snowflake bags
   
   MaterialConsumption created:
       display_name_snapshot: "Snowflake Bag 6""  (frozen)
   
   Year 2: Rename MaterialProduct to "Winter Snowflake 6" Bag"
   
   # MaterialConsumption from Year 1 STILL shows "Snowflake Bag 6""
   # User can see exactly what they used, as it was called then
   ```

**Historical Reconstruction:**

User can answer years later:
- ✅ "What finished good did I make?" (AssemblyRun.finished_good_id)
- ✅ "Which recipe/variant?" (via FinishedGood → Recipe)
- ✅ "What baked goods did I use?" (AssemblyConsumption.finished_unit_id)
- ✅ "What materials did I use?" (MaterialConsumption.material_id, material_product_id)
- ✅ "What size/type?" (MaterialConsumption.quantity_per_unit)
- ✅ "What was it called then?" (MaterialConsumption.display_name_snapshot)
- ✅ "How much did it cost?" (MaterialConsumption.per_unit_cost)

**Parallel to Ingredients:**

| Question | Ingredients (ProductionRun) | Materials (AssemblyRun) |
|----------|----------------------------|------------------------|
| What did I make? | recipe_id, finished_unit_id ✅ | finished_good_id ✅ |
| Which variant? | recipe_variant_id ✅ | (via FinishedGood) ✅ |
| What products used? | product_id ✅ | material_product_id ✅ |
| What type/category? | (via Ingredient) ✅ | material_id ✅ |
| What size/quantity? | quantity_consumed ✅ | quantity_per_unit + quantity_consumed ✅ |
| What was it called? | (from Product, mutable) ⚠️ | display_name_snapshot ✅ |
| How much did it cost? | per_unit_cost ✅ | per_unit_cost ✅ |

**Examples:**

**Definition (Current/Live Costs):**
```
MaterialProduct "6\" Snowflake Bag":
  current_unit_cost: $0.25 (weighted average, recalculated on each purchase)
  
MaterialUnit "6\" Snowflake Bag":
  cost: $0.25 (calculated from MaterialProduct, always current)
  
FinishedGood "Holiday Gift Box":
  material component cost: $0.25 (calculated from MaterialUnit, always current)
```

**Instantiation (Historical Snapshots):**
```
MaterialPurchase (Dec 1):
  calculated_unit_cost: $0.24 (snapshot, never changes)
  
MaterialPurchase (Dec 15):
  calculated_unit_cost: $0.27 (snapshot, never changes)
  
MaterialProduct.current_unit_cost: $0.25 (weighted average of both purchases)

AssemblyRun (Dec 20):
  MaterialConsumption:
    per_unit_cost: $0.25 (snapshot from MaterialProduct at assembly time)
  total_material_cost: $12.50 (50 units × $0.25, immutable)
  
MaterialPurchase (Dec 25):
  calculated_unit_cost: $0.30 (new purchase, new snapshot)
  
MaterialProduct.current_unit_cost: $0.26 (recalculated weighted average)

# AssemblyRun from Dec 20 STILL shows $12.50
# Cost does NOT change when MaterialProduct.current_unit_cost updates
```

**Parallel to Ingredients:**

| Ingredient System | Material System |
|-------------------|-----------------|
| **Definitions (no stored costs)** |
| Ingredient | Material |
| Product | MaterialProduct |
| FinishedUnit (cost calculated) | MaterialUnit (cost calculated) |
| **Instantiations (cost snapshots)** |
| Purchase (cost_per_unit snapshot) | MaterialPurchase (calculated_unit_cost snapshot) |
| ProductionConsumption (cost snapshot) | MaterialConsumption (per_unit_cost snapshot) |
| ProductionRun (immutable costs) | AssemblyRun (immutable costs) |

**Validation Rules:**

System SHALL enforce:
- Definition entities have NO cost fields (except weighted average on MaterialProduct)
- MaterialProduct.current_unit_cost is ONLY field with stored cost in definition layer
- MaterialProduct.current_unit_cost recalculated on EVERY purchase
- MaterialUnit.cost ALWAYS calculated dynamically (never stored)
- FinishedGood material cost ALWAYS calculated dynamically (never stored)
- Instantiation entities (MaterialPurchase, MaterialConsumption, AssemblyRun) have immutable cost snapshots
- Changing MaterialProduct.current_unit_cost does NOT affect historical MaterialConsumption or AssemblyRun costs

**UI Implications:**

1. **Catalog Mode (Definitions):**
   - MaterialProduct shows current_unit_cost (live, recalculates)
   - MaterialUnit shows calculated cost (live, from MaterialProduct)
   - FinishedGood shows material cost (live, calculated from components)
   - Footer note: "Current costs - may change with new purchases"

2. **Make Mode (Instantiations):**
   - MaterialPurchase shows calculated_unit_cost (historical, immutable)
   - AssemblyRun shows total_material_cost (historical, immutable)
   - MaterialConsumption shows per_unit_cost (historical, immutable)
   - No "recalculate costs" button (costs are snapshots, not recalculated)

**Constitutional Compliance:**

This requirement directly supports:
- **Principle III (Data Integrity)**: Immutable cost history prevents data corruption
- **Principle II (Future-Proof Schema)**: Pattern supports future audit/compliance needs
- **Principle VI (Consistency)**: Materials follow same pattern as ingredients

**Rationale:**

1. **Historical Accuracy**: AssemblyRun costs reflect actual costs at assembly time
2. **Audit Trail**: MaterialPurchase preserves actual purchase costs
3. **Cost Tracking**: Can analyze how material costs change over time
4. **No Retroactive Changes**: Updating MaterialProduct costs doesn't corrupt historical data
5. **Pattern Consistency**: Users understand material costing because it matches ingredient costing



---

**REQ-M-042: Identity Snapshot Principle**

Materials instantiations SHALL capture complete identity information to enable historical reconstruction:

**Requirements:**

1. **MaterialConsumption** SHALL record complete identity:
   - Material type (material_id) - enables "what type of material"
   - Specific product (material_product_id) - enables "which specific design/brand"
   - Unit size (quantity_per_unit) - enables "what size was it"
   - Display name snapshot (display_name_snapshot) - enables "what was it called"
   - Quantity consumed - enables "how much was used"
   - Cost snapshot - enables "how much did it cost"

2. **AssemblyConsumption** SHALL record complete identity:
   - Finished unit (finished_unit_id) - enables "which baked good"
   - Quantity consumed - enables "how many"
   - Cost snapshot - enables "how much did it cost"

3. **AssemblyRun** SHALL record complete identity:
   - Finished good (finished_good_id) - enables "what did I make"
   - Quantity assembled - enables "how many"
   - Cost totals - enables "total cost"
   - Material reconciliation flag - enables "was this completed"

4. **Display name snapshots** SHALL be immutable:
   - Captured at consumption time
   - Never updated when catalog definitions change
   - Enables historical lookup without dependency on current catalog state

5. **Identity fields** SHALL be non-nullable:
   - All identity fields required at creation time
   - No partial identity capture allowed
   - Ensures complete historical record

**Use Cases Enabled:**

User can query years after assembly:
- "What did I make for so-and-so's wedding?" → AssemblyRun.finished_good_id
- "What baked goods did I use?" → AssemblyConsumption.finished_unit_id  
- "What materials did I use?" → MaterialConsumption with all identity fields
- "Which specific products?" → MaterialConsumption.material_product_id + display_name_snapshot
- "What size were they?" → MaterialConsumption.quantity_per_unit
- "How much did everything cost?" → Cost snapshots in consumption records

**Example Query:**

```sql
-- "What did I make for Christmas 2024 event and what materials did I use?"

SELECT 
    e.event_name,
    ar.assembled_at,
    fg.display_name as finished_good,
    mc.display_name_snapshot as material_used,
    mc.quantity_consumed as qty,
    mc.per_unit_cost as cost_per_unit
FROM events e
JOIN packages pkg ON e.id = pkg.event_id
JOIN assembly_runs ar ON pkg.finished_good_id = ar.finished_good_id
JOIN finished_goods fg ON ar.finished_good_id = fg.id
JOIN material_consumption mc ON ar.id = mc.assembly_run_id
WHERE e.event_name = 'Christmas 2024'
ORDER BY ar.assembled_at, mc.display_name_snapshot;

-- Result (even if catalog changed since 2024):
-- event_name    | assembled_at | finished_good      | material_used        | qty | cost
-- Christmas 2024| 2024-12-20   | Holiday Gift Box   | 6" Snowflake Bag    | 30  | 0.24
-- Christmas 2024| 2024-12-20   | Holiday Gift Box   | 6" Holly Bag        | 20  | 0.26
-- Christmas 2024| 2024-12-20   | Holiday Gift Box   | Red Ribbon 12"      | 50  | 0.15
```

**Constitutional Compliance:**

This requirement directly supports:
- **Principle III (Data Integrity)**: Immutable identity history prevents data loss
- **Principle II (Future-Proof Schema)**: Enables audit trail and compliance reporting
- **Principle VI (Consistency)**: Materials match ingredient pattern (identity + cost capture)

**Rationale:**

1. **User Need**: "What did I make 2 years ago?" requires complete identity capture
2. **Catalog Independence**: Display name snapshots immune to catalog reorganization
3. **Audit Trail**: Complete material provenance for quality/cost analysis
4. **Pattern Consistency**: Parallels ProductionConsumption (ingredient tracking)
5. **Historical Accuracy**: User sees materials "as they were" not "as they are now"


### 3.5 MaterialUnit Model

**REQ-M-011: MaterialUnit as Atomic Consumption Unit**

MaterialUnit SHALL exist as parallel to FinishedUnit:

```
FinishedUnit: "Large Cookie" (produced from Recipe)
  ↓ consumed in
AssemblyConsumption

MaterialUnit: "6\" Red Ribbon" (defined from Material)
  ↓ consumed in  
MaterialConsumption
```

**REQ-M-012: MaterialUnit Definition**

MaterialUnit SHALL have:
```python
MaterialUnit:
    display_name: str             # "6\" Red Ribbon"
    material_id: int              # Links to Material (abstract)
    quantity_per_unit: Decimal    # 6.0 (inches)
    unit_type: str                # "each", "linear_inches"
    notes: str                    # Optional
    
    # NOTE: No material_product_id - MaterialUnit is a DEFINITION
    # Specific MaterialProduct selected at consumption time (assembly)
```

**Rationale:**
- MaterialUnit defines "how much material per unit" (definition layer)
- Specific MaterialProduct choice deferred until assembly (instantiation layer)
- Supports F026 deferred decision pattern (user picks product at assembly)
- MaterialConsumption captures actual product used (identity snapshot)

**REQ-M-013: MaterialUnit Inventory**

MaterialUnit inventory SHALL be calculated by aggregating ALL MaterialProducts of the associated Material:

```python
# MaterialUnit does NOT have its own inventory_count field
# Instead, calculated by aggregating MaterialProduct inventories

MaterialUnit "6\" Red Ribbon":
    material: "Red Ribbon" (abstract)
    quantity_per_unit: 6.0 inches
    
Available MaterialUnits = SUM(
    MaterialProduct.inventory_count for each product of "Red Ribbon" material
) / MaterialUnit.quantity_per_unit

Example:
Material "Red Ribbon" has 3 MaterialProducts:
  - Michaels 100ft Roll: 1200 inches
  - Amazon 50ft Roll: 600 inches  
  - Joann's 75ft Roll: 900 inches
  Total: 2700 inches

MaterialUnit "6\" Red Ribbon" (6 inches per unit):
  Available units: 2700 / 6 = 450 units

Example:
MaterialProduct inventory: 1200 linear_inches
MaterialUnit needs: 6 inches
Available MaterialUnits: 1200 / 6 = 200 units
```

**REQ-M-014: MaterialUnit Usage Types**

MaterialUnits SHALL support two consumption types:

1. **"Each" Materials** (discrete items):
   - Example: "6\" Cellophane Bag", "Snowflake Sticker", "Small Gift Box"
   - Consumed as whole units
   - Inventory tracked as count

2. **"Variable" Materials** (measured quantities):
   - Example: "6\" Red Ribbon", "12\" Wax Paper", "18\" Bubble Wrap"  
   - Consumed by measurement (linear_inches)
   - Inventory tracked as continuous quantity

---

### 3.6 Materials in FinishedGood Composition

**REQ-M-015: Polymorphic Composition with Three Target Types**

Composition table SHALL link to EITHER FinishedUnit OR MaterialUnit OR Material:

```python
Composition:
    finished_good_id: int
    finished_unit_id: int?        # Optional (if baked good)
    material_unit_id: int?        # Optional (if specific material)
    material_id: int?             # Optional (if generic placeholder)
    quantity: int                 # Count of units
    
    # Constraint: EXACTLY ONE of finished_unit_id, material_unit_id, or material_id
```

**REQ-M-016: FinishedGood Example**

```
FinishedGood: "Holiday Gift Box"
  Components (FinishedUnits):
    - 6 × Large Cookie
    - 3 × Brownie
  Components (MaterialUnits - Specific):
    - 2 × Tissue Paper Sheet (each)
  Components (Material - Generic Placeholder):
    - 1 × "6\" Cellophane Bag" (deferred decision)
```

**REQ-M-017: Flexible Material Assignment Timing** ⭐ **UPDATED WITH F026 PATTERN**

Material selection SHALL support deferred decision workflow using Material-as-placeholder pattern:

**Three material specification levels:**

1. **MaterialUnit (Specific)**: Fully specified material
   - Example: "6\" Snowflake Cellophane Bag" (specific MaterialProduct)
   - Used when: Material choice already decided
   - Cost: Actual unit cost from MaterialProduct
   - Indicator: ✓ (ready for assembly)

2. **Material (Generic/Placeholder)**: Abstract material type
   - Example: "6\" Cellophane Bag" (any MaterialProduct of this Material)
   - Used when: Material choice deferred
   - Cost: Weighted average across available MaterialProducts
   - Indicator: ⚠️ "Selection needed"

3. **Unassigned (None)**: No material specified
   - Used when: Material requirements completely unknown
   - Cost: Not calculated
   - Indicator: ⚠️ "Material requirements needed"

**Assignment workflow:**

```
CATALOG Mode (FinishedGood definition):
  User CAN specify:
    - Specific MaterialUnit: "6\" Snowflake Bag" (fully decided)
    - Generic Material: "6\" Cellophane Bag" (deferred, placeholder)
    - Nothing: Leave blank (completely deferred)

PLAN Mode (Event planning):
  System shows:
    - Specific: Actual cost, exact inventory
    - Generic: Estimated cost, aggregate inventory ("82 bags, 4 designs")
    - Unassigned: Cost TBD, inventory unknown
  
  Visual indicators:
    - Specific: ✓ (green check)
    - Generic: ⚠️ (yellow warning) "Selection pending"
    - Unassigned: ⚠️ (yellow warning) "Requirements needed"

MAKE Mode (Production dashboard):
  System shows:
    - Pending indicator for productions with generic/unassigned materials
    - Clickable link to assignment screen
    - Production can continue, assembly blocked until resolved

MAKE Mode (Assembly stage):
  System ENFORCES decision:
    - BLOCKS assembly if generic/unassigned materials remain
    - User MUST assign specific MaterialProducts before recording assembly
    - Quick assign interface provided
    - "Record Assembly Anyway" bypass allowed (flags for later reconciliation)
```

**Example progression:**

```
Day 1 - CATALOG mode:
  Define FinishedGood "Holiday Gift Box"
    Components: 6 cookies, 3 brownies
    Materials: "6\" Cellophane Bag" (GENERIC - deferred)
  
Day 5 - PLAN mode:
  Event: Christmas 2025, need 50 gift boxes
  System shows:
    - "6\" Cellophane Bag: 50 needed"
    - "Available: 82 bags (4 designs) ✓"  
    - "Est. cost: $12.50" (average of 4 designs)
    - ⚠️ Indicator: "Selection pending"

Day 10 - MAKE mode (Production):
  Bake 300 cookies ✓
  Bake 150 brownies ✓
  Dashboard shows: ⚠️ "Packaging needs selection"

Day 15 - MAKE mode (Assembly):
  Record assembly: "50 Holiday Gift Boxes"
  System BLOCKS: "⚠️ Packaging not finalized"
  
  Assignment interface:
    ☐ Snowflake design (30 available) [30]
    ☑ Holly design (25 available) [20]
    ☐ Star design (20 available) [__]
    Total: 50 / 50 ✓
  
  User assigns materials → Assembly proceeds
  System records:
    - MaterialConsumption: 30 Snowflake @ $0.24 = $7.20
    - MaterialConsumption: 20 Holly @ $0.26 = $5.20
    - Total material cost: $12.40 (actual, not estimated)
```

**Cost calculation rules:**

1. **Specific MaterialUnit**: Use MaterialProduct.current_unit_cost
2. **Generic Material**: Calculate weighted average across all MaterialProducts of that Material
3. **Unassigned**: Cost = 0, flagged as incomplete

---

### 3.7 Materials in Assembly Workflow

**REQ-M-018: Auto-Calculated Material Consumption**

When recording an assembly, system SHALL:
1. Read FinishedGood definition (FinishedUnits + MaterialUnits + Material placeholders)
2. **If Material placeholders exist: BLOCK assembly, require resolution**
3. Multiply MaterialUnit quantities by assembly quantity
4. Check MaterialProduct inventory availability
5. Capture current_unit_cost as snapshot (weighted average at assembly time)
6. Create MaterialConsumption records
7. Decrement MaterialProduct.inventory_count

**REQ-M-019: Enhanced AssemblyRun Model**

AssemblyRun SHALL track costs separately:

```python
AssemblyRun:
    # Existing (F046)
    total_component_cost: Decimal     # FinishedUnit costs
    per_assembly_cost: Decimal        # Components only (legacy)
    
    # NEW (F047)
    total_material_cost: Decimal      # Material costs
    total_assembly_cost: Decimal      # Components + materials
    per_unit_assembly_cost: Decimal   # Total cost per assembled unit
    
    # NEW (F047 - deferred decision tracking)
    requires_material_reconciliation: bool  # True if "Record Anyway" bypass used
```

**REQ-M-020: MaterialConsumption Model**

MaterialConsumption SHALL track material usage with complete identity capture:

```python
MaterialConsumption:
    assembly_run_id: int
    
    # IDENTITY CAPTURE (immutable snapshot)
    material_id: int              # Material type (abstract)
    material_product_id: int      # Specific product used
    quantity_per_unit: Decimal    # Unit size (e.g., 6 inches)
    display_name_snapshot: str    # Human-readable name at consumption time
    
    # QUANTITY
    quantity_consumed: Decimal    # Units consumed
    
    # COST SNAPSHOT (immutable)
    per_unit_cost: Decimal        # Cost at assembly time
```

**Identity fields rationale:**
- `material_id`: Enables lookup of material type without catalog dependency
- `material_product_id`: Captures actual product used (may differ from any MaterialUnit default)
- `quantity_per_unit`: Preserves unit size (was it 6" or 12" ribbon?)
- `display_name_snapshot`: Human-readable identity, immune to catalog changes

**Example:**
```
AssemblyRun #15 used:
  MaterialConsumption record 1:
    - material_id: "6\" Cellophane Bag"
    - material_product_id: "Snowflake Design"
    - quantity_per_unit: 1 (each)
    - display_name_snapshot: "6\" Snowflake Bag"
    - quantity_consumed: 30
    - per_unit_cost: $0.24
  
  MaterialConsumption record 2:
    - material_id: "6\" Cellophane Bag"
    - material_product_id: "Holly Design"
    - quantity_per_unit: 1 (each)
    - display_name_snapshot: "6\" Holly Bag"
    - quantity_consumed: 20
    - per_unit_cost: $0.26
```

**User can query:** "What materials did I use in AssemblyRun #15 two years ago?"
- Answer: "30 Snowflake bags and 20 Holly bags (6\" cellophane)"
- No catalog dependency - all identity preserved in snapshot

**REQ-M-021: Assembly Cost Example**

```
AssemblyRun: "Holiday Gift Box" × 50

Component costs (FinishedUnits):
  300 cookies @ $0.42 = $126.00
  150 brownies @ $0.65 = $97.50
  Subtotal: $223.50

Material costs (MaterialUnits):
  50 gift boxes @ $0.80 = $40.00
  50 ribbons (12") @ $0.72 = $36.00
  100 tissue sheets @ $0.05 = $5.00
  Subtotal: $81.00

Total assembly cost: $304.50
Per unit cost: $6.09
```

---

### 3.8 Materials Inventory Management

**REQ-M-022: Aggregate Inventory Only**

Materials inventory SHALL use aggregate counts (no lot tracking):
- MaterialProduct.inventory_count (single field)
- No MaterialInventoryItem table (unlike ingredients)
- Weighted average costing (not FIFO)
- Rationale: Materials non-perishable, lot tracking unnecessary

**REQ-M-023: Inventory Adjustments**

Manual inventory adjustments SHALL follow food pattern:

**For "Each" Materials:**
- Adjustment by count (+10 bags, -5 boxes)
- Similar to food count adjustments

**For "Variable" Materials:**
- Adjustment by percentage ("50% of roll remains")
- Rationale: User cannot precisely measure remaining ribbon length
- System calculates: new_inventory = current_inventory × percentage

**REQ-M-024: Adjustment Workflow**

```
Material: "Red Ribbon"
MaterialProduct: "Michaels Red Satin 100ft Roll"
Current inventory: 800 linear_inches

User adjusts: "Used ribbon on personal project, about 20% remaining"

System calculates:
800 × 0.20 = 160 linear_inches remaining
Adjustment: -640 linear_inches

New inventory: 160 linear_inches
```

---

### 3.9 Materials in Cost Reporting

**REQ-M-025: Integrated Cost Reporting with Estimated vs Actual**

Materials costs SHALL appear alongside food costs in:

1. **FinishedGood BOM View:**
```
Holiday Gift Box BOM:
  Food components: $4.47 (actual)
  Material components: $1.05 (estimated) ← If generic materials
  Material components: $1.12 (actual) ← If specific materials
  Total: $5.52 (estimated) or $5.59 (actual)
```

2. **Event Cost Summary:**
```
Christmas 2025 Event:
  Ingredient costs: $567.00 (actual)
  Material costs: $143.00 (estimated) ← Before assembly
  Material costs: $148.50 (actual) ← After assembly
  Total event cost: $710.00 (estimated) or $715.50 (actual)
```

3. **Assembly Cost Breakdown:**
```
AssemblyRun: 50 Holiday Gift Boxes
  Component costs: $223.50 (actual)
  Material costs: $81.00 (actual) ← Always actual in AssemblyRun
  Total: $304.50 (actual)
```

**Cost labeling rules:**
- Generic Material in FinishedGood: Label "estimated"
- Specific MaterialUnit in FinishedGood: Calculate actual, label "actual"
- MaterialConsumption in AssemblyRun: Always actual (snapshot)

**REQ-M-026: No Separate Material Reports (Initially)**

Dedicated material reports SHALL be deferred:
- No material-specific inventory reports
- No material purchase history reports (beyond basic list)
- No material cost trend analysis
- Rationale: Materials costs reported in context with food costs

---

### 3.10 Materials UI Requirements

**REQ-M-027: Materials Tab (CATALOG Mode)**

CATALOG mode SHALL have Materials tab with:
- MaterialCategory management (CRUD)
- MaterialSubcategory management (CRUD)
- Material management (CRUD with ontology navigation)
- MaterialProduct management (CRUD)
- MaterialUnit management (CRUD)

**REQ-M-028: Materials Purchasing**

UI SHALL provide materials purchasing workflow:
- Record MaterialPurchase (package quantities)
- View purchase history (list with filters)
- Purchase entry form mirrors food purchase form

**REQ-M-029: Materials Inventory**

UI SHALL provide inventory management:
- Current inventory view (list with quantities)
- Manual adjustment dialog (count or percentage)
- Inventory view mirrors food inventory view

**REQ-M-030: Material Selection in FinishedGood** ⭐ **UPDATED**

FinishedGood edit dialog SHALL allow:
- **Radio button choice**: ○ Specific MaterialUnit  ○ Generic Material  ○ None
- If Specific MaterialUnit: Dropdown shows MaterialUnits, exact inventory
- If Generic Material: Dropdown shows Materials, aggregate inventory display
  - "Available: 82 bags (4 designs)"
  - Shows designs: "Snowflakes (30), Holly (25), Stars (20), Snowmen (7)"
  - Shows estimated cost (weighted average)
- If None: No material selected (completely deferred)
- Quantity entry (integer count)

**REQ-M-031: Materials in Assembly Recording** ⭐ **UPDATED**

Assembly recording dialog SHALL:
- **HARD STOP**: Block assembly if generic/unassigned materials remain
- Display warning: "⚠️ Packaging not finalized"
- Provide **quick assignment interface**:
  - List unassigned materials
  - Checkbox selection of available MaterialProducts
  - Quantity entry per product
  - Running total: "Assigned: X / Y needed"
  - Validation: Must assign total needed
- Actions:
  - "Assign Materials" button (completes assignment, proceeds with assembly)
  - "Assembly Details" link (opens full assignment screen)
  - "Record Assembly Anyway" button (bypass, flags requires_material_reconciliation)
- Show material costs alongside component costs
- Display total assembly cost (components + materials)

**REQ-M-032: Materials in Event Planning** ⭐ **UPDATED**

Event planning (PLAN mode) SHALL show:
- Material costs in package calculations (estimated or actual)
- Material costs in event totals (estimated or actual)
- Material inventory requirements
- **Visual indicators**:
  - ✓ Specific materials (ready)
  - ⚠️ Generic materials (selection pending)
  - ⚠️ Unassigned materials (requirements needed)

**REQ-M-033: Production Dashboard Indicators** ⭐ **NEW**

Production dashboard SHALL display:
- ⚠️ Icon on productions with pending material decisions
- Clickable link to assignment screen
- Tooltip: "Packaging needs selection"
- Production can continue (not blocked)
- Assembly blocked until materials resolved

---

### 3.11 Materials Import/Export

**REQ-M-034: Catalog Import/Export**

Materials catalog import/export SHALL work identically to ingredients:

**Catalog Import (ADD_ONLY mode):**
- MaterialCategory import
- MaterialSubcategory import (with category references)
- Material import (with subcategory references)
- MaterialProduct import (with material references)

**Export Format:**
```json
{
  "version": "4.2",
  "material_categories": [...],
  "material_subcategories": [...],
  "materials": [...],
  "material_products": [...],
  "material_units": [...]
}
```

**REQ-M-035: View Import/Export**

Materials view import/export SHALL work identically to ingredients:
- MaterialPurchase import/export
- MaterialInventory snapshot export
- MaterialUnit definition export

---

### 3.12 Validation & Business Rules

**REQ-M-036: Inventory Constraints**

System SHALL enforce:
- MaterialProduct.inventory_count >= 0 (cannot go negative)
- **Assembly blocked if insufficient material inventory**
- **Assembly blocked if generic/unassigned materials exist** (unless bypassed)
- Cannot delete MaterialProduct if inventory > 0
- Cannot delete MaterialProduct if used in MaterialUnit
- Cannot delete MaterialUnit if used in FinishedGood composition
- Cannot delete Material if used in Composition as placeholder

**REQ-M-037: Purchase Validation**

System SHALL validate:
- package_unit_count > 0
- packages_purchased > 0
- total_cost >= 0
- calculated_unit_cost >= 0

**REQ-M-038: Composition Constraints**

System SHALL enforce:
- Composition has EXACTLY ONE of finished_unit_id, material_unit_id, or material_id
- quantity > 0
- Cannot delete FinishedUnit/MaterialUnit/Material if used in active FinishedGood

**REQ-M-039: Assembly Stage Enforcement** ⭐ **NEW**

System SHALL enforce at assembly time:
- **BLOCK assembly** if any Composition has material_id (generic placeholder)
- **BLOCK assembly** if any Composition has NULL material references
- User MUST resolve to specific material_unit_id before proceeding
- UNLESS user selects "Record Assembly Anyway" bypass:
  - AssemblyRun.requires_material_reconciliation = true
  - System flags assembly for later review
  - Cost calculations exclude unassigned materials

**REQ-M-040: Strict Separation**

Materials and Ingredients SHALL be strictly separated:
- No shared tables (except Supplier)
- MaterialProduct != Product (separate tables)
- Material != Ingredient (separate tables)
- Rationale: Data integrity, future extensibility

---

## 4. Success Criteria

### 4.1 Functional Acceptance Criteria

Feature F047 is considered complete when:

1. ✅ Materials ontology hierarchy exists (3 levels)
2. ✅ MaterialProduct catalog operational (CRUD + UI)
3. ✅ MaterialUnit catalog operational (CRUD + UI)
4. ✅ Can purchase materials, inventory updates correctly (weighted average)
5. ✅ Can add MaterialUnits to FinishedGood composition
6. ✅ **Can add generic Material placeholders to FinishedGood composition**
7. ✅ **Planning shows estimated costs for generic materials**
8. ✅ **Production dashboard shows ⚠️ pending indicators**
9. ✅ **Assembly hard stop enforces material resolution**
10. ✅ **Quick assignment interface functional at assembly stage**
11. ✅ Can record assembly with materials, costs captured correctly
12. ✅ AssemblyRun shows component costs + material costs separately
13. ✅ MaterialProduct inventory decrements on assembly
14. ✅ Cannot assemble if insufficient material inventory
15. ✅ Materials costs appear in event planning (estimated and actual)
16. ✅ Import/export works for materials catalog
17. ✅ Manual inventory adjustment works (count and percentage)

### 4.2 Quality Criteria

1. ✅ Materials model exactly parallels Ingredient model (structural consistency)
2. ✅ All business rules enforced (validation constraints)
3. ✅ UI follows existing patterns (users understand by analogy)
4. ✅ No material data in ingredient tables (strict separation)
5. ✅ Cost calculations accurate (weighted average verified)
6. ✅ Assembly workflow consistent (matches food pattern)
7. ✅ **Deferred decision workflow matches F026 validated pattern**
8. ✅ **Visual indicators clear and consistent (✓ vs ⚠️)**
9. ✅ **Cost labeling accurate (estimated vs actual)**

### 4.3 Documentation Criteria

1. ✅ Materials ontology management documented in user guide
2. ✅ Materials purchasing workflow documented
3. ✅ MaterialUnit creation workflow documented
4. ✅ Import/export format documented (with examples)
5. ✅ **Deferred decision workflow documented (generic vs specific)**
6. ✅ **Material assignment workflow documented (assembly stage)**

---

## 5. Dependencies & Constraints

### 5.1 Prerequisites

- ✅ F046 (Finished Goods, Bundles & Assembly Tracking) - Complete
- ✅ F026 (Deferred Packaging Decisions) - Pattern validated

### 5.2 Enables

- F048: Shopping Lists Tab Implementation (needs material requirements)
- F049: Assembly Workflows Enhancement (needs material tracking)
- Future: Multi-user web version (materials infrastructure ready)
- Future: E-commerce integration (dual supply chain ready)

### 5.3 Technical Constraints

**Database:**
- SQLite (current), PostgreSQL (web version)
- Must support Decimal for cost accuracy
- Must support weighted average calculation
- Composition table requires THREE optional foreign keys (finished_unit_id, material_unit_id, material_id)

**UI:**
- CustomTkinter (current desktop)
- Must follow existing catalog patterns
- Must integrate into existing CATALOG/MAKE modes
- **Must support ⚠️ indicators throughout workflow**
- **Must support quick assignment interface (inline at assembly)**

**Import/Export:**
- JSON format (existing)
- Must maintain version compatibility (v4.2)

---

## 6. Non-Functional Requirements

### 6.1 Performance

- Materials catalog search: < 100ms for 1000+ products
- Weighted average calculation: < 10ms per purchase
- Assembly cost calculation: < 500ms for 20+ materials
- **Generic material aggregate inventory calculation: < 50ms**
- **Assignment interface load: < 200ms for 100+ MaterialProducts**

### 6.2 Usability

- Materials UI mirrors ingredients UI (users learn by analogy)
- Ontology navigation follows same patterns
- Purchase workflow familiar to existing users
- **Visual indicators immediately recognizable (⚠️ = action needed)**
- **Quick assignment interface intuitive (checkbox + quantity)**

### 6.3 Extensibility

- Architecture supports future e-commerce integration
- Product_type field enables unified Product table (if needed)
- Ontology structure supports future taxonomies
- **Deferred decision pattern extensible (future: partial commitment, templates)**

### 6.4 Data Integrity

- Strict separation prevents material/ingredient mixing
- Weighted average costing maintains accuracy
- Inventory constraints prevent negative stock
- **Assembly enforcement prevents incomplete data**
- **MaterialConsumption always has resolved material_unit_id (never material_id)**

---

## 7. Assumptions

1. Users will manually enter package quantities (no barcode scanning)
2. Weighted average costing sufficient (FIFO unnecessary for materials)
3. Percentage-based adjustment sufficient for variable materials
4. No existing "packaging ingredient" data to migrate
5. Sample data will be provided separately by user
6. **Users comfortable with "estimated" vs "actual" cost distinction**
7. **"Record Assembly Anyway" bypass rarely used (exceptional cases only)**

---

## 8. Risks & Mitigation

### Risk 1: Complexity Underestimation

**Risk**: Full parallel to Ingredient model + deferred decision pattern = significant scope

**Mitigation**:
- Start with minimal UI (catalog CRUD only)
- Defer advanced features (reporting, analytics, templates)
- Follow existing patterns (leverage ingredient code, F026 pattern)
- Estimated: 28-32 hours implementation (increased from 20-24 due to deferred decision complexity)

### Risk 2: MaterialUnit Inventory Calculation

**Risk**: Calculating MaterialUnit inventory from MaterialProduct may confuse users

**Mitigation**:
- Clear UI messaging ("Available: 200 units based on 1200 inches in stock")
- Documentation with examples
- Consistent with FinishedUnit pattern (users already understand)

### Risk 3: Weighted Average Costing

**Risk**: Users accustomed to FIFO may expect lot-level accuracy

**Mitigation**:
- Document cost methodology clearly
- Show weighted average calculation in UI
- Emphasize: "Materials non-perishable, weighted average sufficient"

### Risk 4: Deferred Decision Workflow Confusion ⭐ **NEW**

**Risk**: Users may not understand when to use generic vs specific materials

**Mitigation**:
- Clear UI labels: "Specific" vs "Generic (defer decision)"
- ⚠️ Indicators provide clear feedback (action needed)
- Documentation with workflow examples (F026 pattern validated)
- Quick assignment interface at assembly makes resolution easy

### Risk 5: Assembly Hard Stop Frustration ⭐ **NEW**

**Risk**: Users annoyed by assembly blocking when materials not resolved

**Mitigation**:
- Clear error messaging: "Packaging not finalized" (not generic error)
- Quick assignment interface (resolve without leaving screen)
- "Record Assembly Anyway" bypass for exceptional cases
- F026 pattern already validated with users (accepted workflow)

---

## 9. Open Questions & Decisions

### 9.1 Resolved

- ✅ Parallel to Ingredient model (Yes - foundational architecture)
- ✅ MaterialUnit model needed (Yes)
- ✅ Ontology levels (3: Category → Subcategory → Material)
- ✅ Inventory at MaterialProduct level (Yes, like Product)
- ✅ Package + atomic storage (Yes, store both)
- ✅ Composition links to MaterialUnit (Yes)
- ✅ Variable material adjustment (Percentage-based)
- ✅ **Material decision timing (Flexible: catalog or assembly)**
- ✅ **Deferred decision pattern (F026 generic placeholder approach)**

### 9.2 Deferred to Specification Phase

- Unit conversion details (feet↔inches mechanism)
- Specific UI layout/mockups
- Import/export JSON schema details
- Error message wording
- Specific validation error codes
- **Quick assignment interface detailed design**
- **Aggregate inventory calculation implementation**

---

## 10. Approval

**Requirements Author**: Claude (Anthropic AI)
**Requirements Reviewer**: Kent Gale
**Date**: 2026-01-10

**Status**: ⏳ PENDING APPROVAL

**Changes from v1.0:**
- Updated REQ-M-015: Composition supports three target types (added material_id)
- Updated REQ-M-012: Removed material_product_id from MaterialUnit (generic definition)
- Updated REQ-M-013: MaterialUnit inventory aggregates across all MaterialProducts
- Updated REQ-M-017: Flexible material assignment timing (F026 pattern)
- Updated REQ-M-020: Added identity snapshot fields to MaterialConsumption
- Updated REQ-M-041: Added identity capture to definition/instantiation principle
- Added REQ-M-042: Identity snapshot principle (NEW)
- Updated REQ-M-025: Estimated vs actual cost reporting
- Updated REQ-M-030: Material selection UI (radio button specific/generic/none)
- Updated REQ-M-031: Assembly hard stop + quick assignment interface
- Updated REQ-M-032: Event planning visual indicators
- Added REQ-M-033: Production dashboard indicators
- Added REQ-M-039: Assembly stage enforcement
- Updated success criteria (added deferred decision requirements)
- Updated risks (added deferred decision risks)
- Updated effort estimate (28-32 hours from 20-24 hours)

**Next Steps**:
1. User reviews requirements v2.0
2. Approve or request changes
3. Create F047 feature specification based on approved requirements
4. Queue for implementation via spec-kitty

---

**END OF REQUIREMENTS DOCUMENT**
