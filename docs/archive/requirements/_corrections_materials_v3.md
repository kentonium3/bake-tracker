# Materials Requirements v3.0 - Corrections Applied

**Date**: 2026-01-18
**Status**: CORRECTED

## Corrections Made

### 1. ✅ Fixed: Inventory Display Location
**Old**: "Make > Inventory shows MaterialInventoryItem lots"  
**New**: "Purchase > Inventory shows MaterialInventoryItem lots (parallel to food)"

**Added**: Service layer clarification
- MaterialInventoryService provides primitives
- Planning/production services query MaterialInventoryService
- Follows same pattern as ProductInventoryItem

**Location**: REQ-M-010

---

### 2. ✅ Fixed: Metric Conversions
**Old**: Limited metric conversions (only meters ↔ cm)  
**New**: Comprehensive metric conversions:
- Linear: meters ↔ centimeters, kilometers ↔ meters
- Area: square_meters ↔ square_centimeters, square_kilometers ↔ square_meters

**Location**: REQ-M-006

---

### 3. ⚠️ NEEDS REMOVAL: Material.base_unit_type Immutability

**Problem**: REQ-M-032 and REQ-M-033 contradict strict definition/instantiation separation.

**Kent's Insight**: 
> "Changes to definitions should not affect production or history if instantiations are used correctly."

**Why Current Requirements Are Wrong**:

If definition/instantiation is properly implemented:
- Material.base_unit_type is a DEFINITION (can change anytime)
- MaterialInventoryItem has immutable snapshots (quantity_purchased, quantity_remaining)
- MaterialConsumption has immutable snapshots (quantity_consumed, cost_per_unit, display_name_snapshot)
- Historical data preserved in instantiation layer regardless of definition changes

**Example Why It's Safe**:
```
Year 1: Material "Red Ribbon" created with base_unit_type = "each" (WRONG)
Year 1: Purchase 100 "each"
  → MaterialInventoryItem: quantity_purchased = 100 (immutable snapshot)
Year 1: Consume 50 "each"  
  → MaterialConsumption: quantity_consumed = 50 (immutable snapshot)

Year 2: User realizes mistake, changes Material.base_unit_type = "linear_inches"
  → MaterialInventoryItem from Year 1: STILL shows quantity_purchased = 100
  → MaterialConsumption from Year 1: STILL shows quantity_consumed = 50
  → Historical data UNCHANGED (snapshots are immutable)

Year 2: New purchase with correct unit type
  → MaterialInventoryItem: quantity_purchased = 1200 (linear_inches, new snapshot)
  
User can see:
- Old inventory items: 100 (from when it was "each")
- Old consumption: 50 (from when it was "each")
- New inventory items: 1200 linear_inches (current definition)
```

**Correct Behavior**:
- Material.base_unit_type can be changed ANYTIME
- Historical MaterialInventoryItem records preserve original quantities
- Historical MaterialConsumption records preserve original quantities
- display_name_snapshot preserves human-readable context ("100 each" vs "1200 linear_inches")

**Sections to Remove/Rewrite**:
- REQ-M-032: "Material.base_unit_type Immutability with Exceptions" ❌ DELETE
- REQ-M-033: "Export/Transform/Import Fix Path" ❌ DELETE
- Any UI requirements about "cannot change after creation" ❌ UPDATE

**New Requirement to Add**:
```
REQ-M-032: Material.base_unit_type Is Mutable (Definition Layer)

Material.base_unit_type SHALL be editable at any time:

**Rationale**: 
- Material.base_unit_type is a definition (describes what units mean)
- Historical data preserved in MaterialInventoryItem (immutable snapshots)
- Historical consumption preserved in MaterialConsumption (immutable snapshots)
- Changing definition does not affect instantiation data

**User Impact**:
- Old inventory items keep original quantity values
- Old consumption records keep original quantity values
- New purchases use new unit type
- display_name_snapshot provides human-readable context for historical records

**UI Behavior**:
- Material edit dialog: base_unit_type is editable dropdown (always)
- Warning shown: "Changing unit type affects new purchases only. Historical data unchanged."
- No blocking, no export/import required
```

---

### 4. Follow-Up Question for Kent

**Does Ingredient follow same pattern?**

If strict definition/instantiation is correct for materials, should the same apply to ingredients?

**Ingredient Domain**:
- Ingredient properties (category, unit type, etc.) = definitions
- ProductInventoryItem = instantiations (quantity snapshots)
- ProductionConsumption = instantiations (quantity snapshots)

**Question**: Should Ingredient properties be freely changeable since historical data lives in instantiations?

**If YES**: We may have a similar issue in ingredient system that needs fixing.
**If NO**: What makes ingredients different from materials?

---

## Summary of Changes

| Section | Change | Status |
|---------|--------|--------|
| REQ-M-006 | Add metric conversions | ✅ DONE |
| REQ-M-010 | Fix inventory display location | ✅ DONE |
| REQ-M-032 | Remove immutability rules | ⚠️ NEEDS DOING |
| REQ-M-033 | Remove export/transform path | ⚠️ NEEDS DOING |
| NEW REQ-M-032 | Add mutability principle | ⚠️ NEEDS ADDING |

## Next Steps

1. Remove old REQ-M-032 and REQ-M-033 from document
2. Add new REQ-M-032 (Material.base_unit_type Is Mutable)
3. Update any UI requirements referencing immutability
4. Update success criteria if needed
5. Review parallel issue in ingredient system

---

**END OF CORRECTIONS DOCUMENT**
