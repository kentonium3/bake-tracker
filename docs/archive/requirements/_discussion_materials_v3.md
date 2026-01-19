# Materials System Requirements Discussion v3.0

**Document ID**: DISC-MATERIALS-v3
**Date**: 2026-01-18
**Purpose**: Address fundamental design issues identified during user testing
**Status**: DISCUSSION DRAFT

---

## Context

The current materials implementation (v2.1) has fundamental issues discovered during first-time user testing. These issues stem from insufficient requirements work before implementation, resulting in violations of the definition/instantiation principle and unclear unit handling.

## Identified Issues

### Issue 1: MaterialProduct Cost/Inventory Display Violation

**Problem**: The Materials Product catalog (Catalog>Materials>Material Products) shows cost and inventory columns directly on product definitions.

**Current State**:
```
MaterialProduct table shows:
- Product name
- Cost column         ← VIOLATION (instantiation data on definition)
- Inventory column    ← VIOLATION (instantiation data on definition)
```

**Constitutional Violation**: 
- Principle II (Definition/Instantiation Separation)
- REQ-M-041 explicitly states definitions SHALL NOT store cost data

**Analysis**:
This is actually **partially correct** and **partially wrong**:

**CORRECT**: MaterialProduct.current_inventory and MaterialProduct.weighted_avg_cost exist as fields
- These are aggregate tracking fields (similar to Product for ingredients)
- They're updated as purchases occur
- REQ-M-041 allows "weighted average on MaterialProduct" as the ONE exception

**WRONG**: Showing these in the catalog UI without clear distinction
- Catalog is definition layer - should show structure not current state
- Current costs/inventory should be in Make mode (Inventory view)
- UI conflates definition (what can exist) with instantiation (what exists now)

**Resolution Options**:

A. **Remove from catalog UI completely**
   - Move cost/inventory display to Make > Materials > Inventory view
   - Catalog shows only definitions (name, unit type, supplier reference)
   - Pros: Clean separation, constitutional compliance
   - Cons: Harder to see "do I have this?" while browsing catalog

B. **Keep but clearly label as "current state"**
   - Add footer: "Cost/inventory shown are current values, updated by purchases"
   - Use different visual styling (lighter text, background tint)
   - Pros: User convenience, matches ingredient product UI pattern
   - Cons: Still mixing concerns in one view

C. **Add view mode toggle**
   - "Definition View" (no costs/inventory) vs "Status View" (with costs/inventory)
   - Clear label indicating which mode active
   - Pros: Flexibility, educational value
   - Cons: UI complexity, may confuse users

**Discussion Questions**:
1. Is MaterialProduct.weighted_avg_cost actually a definition field or instantiation field?
2. Should catalog UI EVER show instantiation data, even labeled?
3. Does the ingredient Product catalog have the same issue?

---

### Issue 2: Material Unit Type Confusion

**Problem**: Add Material Unit dialog has no way to specify if unit type is "each" vs "linear_inches"

**Current State**:
```
Material definition:
  base_unit_type: "linear_inches"  ← Defined at Material level
  
MaterialUnit definition:
  quantity_per_unit: 6.0           ← Just a number, no unit type field
```

**Analysis**:

The unit type is **inherited from Material.base_unit_type**, not stored on MaterialUnit. This is architecturally correct (MaterialUnit is a quantity of the Material's base unit), but the UI doesn't make this clear.

**Example Flow**:
```
1. Create Material "Red Ribbon"
   - base_unit_type: "linear_inches"
   
2. Create MaterialUnit "6-inch Red Ribbon"
   - material_id: → "Red Ribbon"
   - quantity_per_unit: 6.0
   - Unit type is INHERITED: "linear_inches"
   - Meaning: "6 linear inches of Red Ribbon"

3. Create MaterialUnit "12-inch Red Ribbon"  
   - material_id: → "Red Ribbon"
   - quantity_per_unit: 12.0
   - Unit type is INHERITED: "linear_inches"
   - Meaning: "12 linear inches of Red Ribbon"
```

**UI Issue**: The Add Material Unit dialog doesn't show:
- What unit type the parent Material has
- That the quantity_per_unit value is interpreted in that unit type
- That ALL MaterialUnits of a Material share the same unit type

**Resolution Options**:

A. **Display Material unit type in dialog**
   - When Material selected, show: "Unit type: linear_inches (from Red Ribbon)"
   - Quantity field labeled: "Quantity per unit (in linear_inches)"
   - Pros: Clear inheritance, minimal code change
   - Cons: Still no way to override (but that's by design)

B. **Add unit type to MaterialUnit table (NOT RECOMMENDED)**
   - Store redundant unit_type on MaterialUnit
   - Validate it matches Material.base_unit_type
   - Pros: Explicit at every level
   - Cons: Denormalization, introduces constraint that can be violated

C. **Add unit type display to MaterialUnit name**
   - Auto-append unit: "6-inch Red Ribbon (linear_inches)"
   - Or require format: "[quantity] [unit] [material]"
   - Pros: Self-documenting
   - Cons: Cluttered names, user may not follow convention

**Recommendation**: Option A - Display inherited unit type clearly in UI

**Discussion Questions**:
1. Should MaterialUnit EVER have a different unit type than its parent Material?
2. Is the current inheritance model architecturally sound?
3. How do we handle mixed-unit scenarios (e.g., ribbon sold by foot but measured by inch)?

---

### Issue 3: Qty/Unit Field Split Required

**Problem**: Add Material Unit dialog has single "Qty/Unit" field instead of two fields for quantity and unit.

**Current State**:
```
Qty/Unit: [6.0]  ← Single field, unit type implicit
```

**Desired State**:
```
Quantity: [6]
Unit: [linear_inches] ← Inherited from Material, display only?
```

**Analysis**:

This connects to Issue 2. The field is actually architecturally correct (just a quantity), but UI presentation is confusing.

**Problem Scenarios**:
- User sees "6" and wonders "6 what?"
- User wants "10 inches" but field says "Qty/Unit" not "Quantity (in inches)"
- No visual connection between Material.base_unit_type and this quantity

**Resolution Options**:

A. **Split into Quantity + Unit Display**
   ```
   Quantity per unit: [6.0]
   Unit type: linear_inches (from Red Ribbon) [read-only]
   ```
   - Pros: Explicit, educational
   - Cons: More screen space

B. **Dynamic label based on Material**
   ```
   [Material dropdown: Red Ribbon selected]
   ↓
   Quantity (in linear_inches): [6.0]
   ```
   - Pros: Compact, clear
   - Cons: Label changes as Material selection changes

C. **Add preview text**
   ```
   Quantity per unit: [6.0]
   Preview: "This unit will consume 6 linear_inches of Red Ribbon"
   ```
   - Pros: Explicit without changing field structure
   - Cons: Verbose

**Recommendation**: Combine A + B - Split field with dynamic unit display

**Discussion Questions**:
1. Is it ever valid to specify a unit different from Material.base_unit_type?
2. Should quantity_per_unit support decimals (e.g., 6.5 inches)?
3. How do we handle "each" materials (where quantity = 1 always)?

---

### Issue 4: Material Purchase Integration Missing

**Problem**: Purchase > Purchases > Add Purchase form has no way to select/add a material product purchase.

**Current State**:
- Purchase form only shows food products
- No material product selector
- MaterialPurchase table exists but no UI

**Analysis**:

This is a straightforward **missing feature**, not a design issue.

**Required Changes**:

1. **Add product type selector to Purchase form**
   ```
   Product type: ○ Food  ○ Material
   ```

2. **Material product selector** (when Material selected)
   ```
   Material Product: [dropdown of MaterialProducts]
   Package quantity: [25] bags per pack
   Packages purchased: [4] packs
   Total units: 100 bags (calculated)
   Total cost: [$40.00]
   Unit cost: $0.40/bag (calculated)
   ```

3. **Update service layer**
   - MaterialPurchaseService.create_purchase() exists
   - Needs UI integration only

**Resolution**: This is implementation work, not requirements clarification.

**Discussion Questions**:
1. Should food and material purchases be in same form or separate tabs?
2. Should UI prevent mixing food/material purchases in same transaction?
3. How do we handle returns/adjustments for material purchases?

---

### Issue 5: Material Default Unit Immutability

**Problem**: Material edit dialog says default unit cannot be changed after creation, but all materials have "each" unit type (which is wrong for ribbons/twines).

**Current State**:
```
Material "Red Ribbon":
  base_unit_type: "each"  ← WRONG, should be "linear_inches"
  UI says: "Cannot change after creation"
```

**Analysis**:

This is a **data integrity concern** masquerading as a UI restriction.

**Why Immutability**:
1. MaterialProduct uses Material.base_unit_type for conversions
2. MaterialUnit.quantity_per_unit is interpreted in Material.base_unit_type  
3. Changing base_unit_type invalidates ALL existing products and units
4. Historical MaterialConsumption records would become nonsensical

**Example of Why It's Dangerous**:
```
Initial state:
  Material "Red Ribbon": base_unit_type = "linear_inches"
  MaterialUnit "6-inch ribbon": quantity_per_unit = 6
  MaterialProduct: current_inventory = 1200 (inches)
  
User changes Material to base_unit_type = "each":
  MaterialUnit "6-inch ribbon": quantity_per_unit = 6 (now means "6 each"???)
  MaterialProduct: current_inventory = 1200 (now means "1200 each"???)
  Historical consumption: "Used 6 linear_inches" (now wrong)
```

**Root Cause**: Initial materials created with wrong unit type (blind spot in requirements).

**Resolution Options**:

A. **Allow change if no products/units/consumption exist**
   - Check: material.products.count == 0 AND material.units.count == 0
   - If true: Allow change
   - If false: Block with explanation
   - Pros: Flexible when safe, strict when risky
   - Cons: User may have entered products already

B. **Allow change with cascade update** (RISKY)
   - Update Material.base_unit_type
   - Recalculate all MaterialProduct.quantity_in_base_units
   - Recalculate all inventory levels
   - Update ALL MaterialConsumption records
   - Pros: User can fix mistakes
   - Cons: High risk of data corruption, complex logic

C. **Require delete/recreate Material**
   - Force user to:
     1. Delete Material (cascade deletes products/units)
     2. Recreate with correct unit type
     3. Re-enter products/units
   - Pros: Clean slate, no corruption risk
   - Cons: User loses purchase history

D. **Export/reset/import with transformation**
   - Export MaterialProduct catalog
   - Delete Material
   - Recreate with correct unit type
   - Transform JSON (convert quantities)
   - Import transformed data
   - Pros: Preserves data with transformation
   - Cons: Complex user workflow

**Recommendation**: Option A (allow if empty) + Option D (fix existing via export)

**Discussion Questions**:
1. Can we EVER safely change base_unit_type after products exist?
2. Should Material creation have a "preview and confirm" step?
3. Should we add Material.base_unit_type validation (list of allowed types)?
4. Should materials be created with a "draft" status until first product added?

---

## Cross-Cutting Issues

### Issue 6: Definition vs Instantiation Confusion

**Broader Problem**: The entire materials system conflates definition and instantiation in subtle ways.

**Examples**:

1. **MaterialProduct has both definition and instantiation aspects**:
   - Definition: name, brand, package_quantity, package_unit
   - Instantiation: current_inventory, weighted_avg_cost
   - Hybrid: Is this a problem or acceptable?

2. **MaterialUnit appears to be pure definition but depends on instantiation**:
   - Definition: quantity_per_unit
   - Computed: available_inventory (depends on MaterialProduct.current_inventory)
   - Is computed inventory display mixing concerns?

3. **Material has no instantiation at all**:
   - Pure definition: category, name, unit type
   - No purchases, no inventory
   - Is this correct?

**Discussion Questions**:
1. Should we split MaterialProduct into definition + inventory tables?
2. Is weighted_avg_cost actually a definition field (describes "current definition") or instantiation?
3. Does the ingredient system have the same conceptual split? (Product vs ProductInventoryItem?)

### Issue 7: "Each" vs "Variable" Material Handling

**Problem**: The system theoretically supports "each" (discrete) and "variable" (measured) materials, but the implementation is unclear.

**Current Understanding**:

**"Each" Materials**:
- Material.base_unit_type = "each"
- MaterialUnit.quantity_per_unit = 1 (always?)
- MaterialProduct.current_inventory = count of items
- Example: "Gift Box", "Tissue Sheet", "Sticker"

**"Variable" Materials**:
- Material.base_unit_type = "linear_inches", "square_inches", etc.
- MaterialUnit.quantity_per_unit = measurement (6.0, 12.0, etc.)
- MaterialProduct.current_inventory = total measurement
- Example: "Ribbon", "Wax Paper", "Bubble Wrap"

**Unclear Aspects**:

1. Can "each" materials have quantity_per_unit != 1?
   - Example: "3 tissue sheets" as a unit?
   
2. How do we handle materials that are SOLD as "each" but MEASURED as "variable"?
   - Example: Ribbon sold by spool (each) but measured by inch?
   
3. Should MaterialProduct.package_unit always match Material.base_unit_type?
   - Current: MaterialProduct.package_unit is freeform ("feet", "yards", "each")
   - Conversion: quantity_in_base_units handles conversion
   - Problem: User must know conversion factor

**Discussion Questions**:
1. Should we restrict MaterialProduct.package_unit to match Material.base_unit_type?
2. Should system provide unit conversion (feet → inches) or require user input?
3. How do we handle "each" materials that come in packs (e.g., "50-pack of tissue")?

---

## Architectural Questions

### Question 1: What IS a MaterialProduct?

**Option A: Physical Item Definition**
- A MaterialProduct is a specific SKU from a supplier
- Example: "Michaels Red Satin 100ft Roll SKU 12345"
- inventory/cost are PART OF the definition (current state of this product)
- When you buy more, you're adding to THIS EXACT PRODUCT's inventory

**Option B: Abstract Product Type + Instances**
- A MaterialProduct is an abstract purchasable type
- Example: "100ft Red Satin Roll" (concept)
- inventory/cost should be in MaterialProductInstance table
- Each purchase creates a new instance (lot tracking)

**Option C: Hybrid (Current Implementation)**
- MaterialProduct is a specific SKU (Option A)
- But uses weighted average costing (implies aggregation like Option B)
- No lot tracking, so functionally Option A

**Discussion**: Which model should we commit to?

### Question 2: Is Weighted Average Cost a Definition?

Philosophically:

**Arguments FOR "weighted_avg_cost is definition"**:
- It describes the "current identity" of this product
- "This product currently costs $X per unit"
- When you look up a product in catalog, you want to know current cost
- It's a cached aggregate, but it's still describing the product

**Arguments AGAINST "weighted_avg_cost is definition"**:
- It's derived from transactional data (purchases)
- It changes over time based on transactions
- "True" definitions are immutable (name, unit type)
- Cost is an OUTCOME of purchasing, not a property of the product itself

**Current Constitution Says**:
> REQ-M-041: MaterialProduct.current_unit_cost is ONLY field with stored cost in definition layer

This implies it's ALLOWED in definition layer as an exception, not that it's ideal.

**Discussion**: Should we treat weighted_avg_cost as a special case (allowed but not ideal)?

### Question 3: Should MaterialUnit Have a material_product_id?

**Current State**: NO
- MaterialUnit only references Material (abstract)
- Specific product chosen at assembly time

**Arguments FOR adding material_product_id**:
- Would enable "default product" for a unit
- Would simplify cost calculations (direct lookup)
- Would match user intuition ("6-inch Snowflake Bag" = specific product + quantity)

**Arguments AGAINST adding material_product_id**:
- Defeats purpose of deferred decision pattern
- MaterialUnit is supposed to be a template, not instance
- Would create dependency on product existence
- REQ-M-012 explicitly excludes it

**Discussion**: Is the current "no material_product_id" design correct?

---

## Path Forward

### Immediate Clarifications Needed

1. **Definition/Instantiation Boundary**
   - Clearly define what belongs in definition layer
   - Document why weighted_avg_cost is allowed exception
   - Update UI to visually separate definition from current state

2. **Unit Type Inheritance**
   - Document that MaterialUnit inherits Material.base_unit_type
   - Update UI to show inheritance clearly
   - Add validation that prevents unit type mismatches

3. **Material.base_unit_type Immutability**
   - Define conditions under which change is allowed
   - Implement safety checks (no products/units/consumption)
   - Provide export/transform/import path for fixing mistakes

4. **Missing UI Features**
   - Material purchase form (straightforward implementation)
   - Material unit type display (UI clarity)
   - Definition vs current state visual separation

### Longer-Term Considerations

1. **Catalog UI Redesign**
   - Separate "Definition View" (structure) from "Inventory View" (current state)
   - Consider tabs: "Definitions" | "Inventory" | "Purchase History"

2. **Material Creation Workflow**
   - Add "review and confirm" step
   - Preview unit type implications
   - Warn about immutability

3. **Unit Conversion System**
   - Define supported conversions (feet ↔ inches, yards ↔ inches)
   - Auto-convert MaterialProduct.package_unit to Material.base_unit_type
   - Remove user burden of manual conversion

---

## Next Steps

**Before updating req_materials.md**:

1. **Answer architectural questions** (above)
2. **Decide on definition/instantiation split**
3. **Clarify unit type model**
4. **Define MaterialProduct identity**

**Then update requirements**:

1. Add clear section: "Definition vs Instantiation in Materials"
2. Strengthen REQ-M-002 (unit type inheritance)
3. Add REQ for base_unit_type immutability with exceptions
4. Update UI requirements to show distinction
5. Add Material creation workflow requirements

**Then create feature specs**:

Multiple small features rather than one large refactor:

- F0XX: Materials Catalog UI Rationalization (definition vs state)
- F0XX: Material Unit Type Clarity (UI + validation)
- F0XX: Material Purchase Form Integration
- F0XX: Material base_unit_type Safety (immutability + fixes)

---

## Questions for Kent

1. **Definition/Instantiation Split**:
   - Is MaterialProduct.weighted_avg_cost actually a definition field or not?
   - Should catalog UI EVER show instantiation data (cost/inventory)?

2. **Unit Type Model**:
   - Is Material.base_unit_type inheritance to MaterialUnit correct?
   - Should we allow unit type changes under any conditions?

3. **MaterialUnit Identity**:
   - Should MaterialUnit have a default material_product_id?
   - Or is the current "abstract until assembly" model correct?

4. **Each vs Variable**:
   - How do we handle materials sold as "each" but measured as "variable"?
   - Should we restrict package_unit to match base_unit_type?

5. **Priority**:
   - Which issue is MOST urgent to fix for current user?
   - Are some of these architectural concerns but not UX blockers?

---

**END OF DISCUSSION DOCUMENT**
