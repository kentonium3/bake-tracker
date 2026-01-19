# Materials Requirements v3.0 - Final Version Ready for Review

**Document**: `/docs/requirements/req_materials.md`
**Date**: 2026-01-18
**Status**: READY FOR REVIEW

---

## Changes Applied

### 1. ✅ Unit Conversion System - Metric Base Storage

**Changed**: Base unit types from imperial (inches) to metric (cm)

**New base_unit_types**:
- `"each"` - Discrete items (unchanged)
- `"linear_cm"` - Linear centimeters (was `"linear_inches"`)
- `"square_cm"` - Square centimeters (was `"square_inches"`)

**Supported input units**:
- **Metric**: cm, meters, mm (linear); square_cm, square_meters (area)
- **Imperial**: inches, feet, yards (linear); square_inches, square_feet (area)
- **System converts all inputs to cm for storage**

**Rationale**: 
- User enters materials in preferred units (metric or imperial)
- System stores in cm (consistent base)
- Supports both measurement systems equally

**Updated Sections**:
- REQ-M-001: Material hierarchy (base_unit_type options)
- REQ-M-005: Inherited unit type example
- REQ-M-006: **Completely rewritten** with cm-based storage and comprehensive conversion tables
- REQ-M-039: Material unit type display example
- REQ-M-041: Import validation
- REQ-M-046: Unit type validation
- Import/export format examples

---

### 2. ✅ Inventory Display Location Corrected

**Changed**: Inventory view location from "Make > Inventory" to "Purchase > Inventory"

**Clarification Added**:
- MaterialInventoryService provides primitives for querying inventory
- Planning/production services call MaterialInventoryService for availability checks
- Follows same pattern as food inventory (ProductInventoryItem)

**Rationale**: Parallels food inventory display (Purchase > Inventory shows ProductInventoryItem)

**Updated Sections**:
- REQ-M-010: Inventory aggregation and display locations
- Section 4.1: Success criteria (#21)

---

### 3. ✅ Removed Incorrect Immutability Requirements

**Removed**: All references to Material.base_unit_type being immutable

**Rationale** (Kent's architectural insight):
> "Changes to definitions should not affect production or history if instantiations are used correctly."

**Why It's Safe to Change base_unit_type Anytime**:
- Material.base_unit_type is a **DEFINITION** (what units mean)
- MaterialInventoryItem has **immutable snapshots** (quantity_purchased, quantity_remaining)
- MaterialConsumption has **immutable snapshots** (quantity_consumed, cost_per_unit)
- display_name_snapshot preserves human-readable context
- Historical data lives in instantiation layer (unaffected by definition changes)

**Example**:
```
Year 1: Material "Red Ribbon" created with base_unit_type = "each" (mistake)
Year 1: Purchase 100 units, consume 50
  → MaterialInventoryItem: quantity_purchased = 100 (immutable)
  → MaterialConsumption: quantity_consumed = 50 (immutable)

Year 2: User fixes mistake, changes base_unit_type = "linear_cm"
  → Historical inventory: STILL shows 100 (preserved)
  → Historical consumption: STILL shows 50 (preserved)
  → New purchases: Use linear_cm (correct going forward)
```

**Removed**:
- Problem statement: "Material.base_unit_type cannot be changed" line
- Success criteria: Immutability criterion (#20)
- Documentation criteria: "Unit type immutability rules documented" (#7)
- Changelog: REQ-M-032-033 references

**Note**: The actual REQ-M-032 and REQ-M-033 requirements don't exist in the document (may have been from a draft that was never committed), so only references to them were removed.

---

## Document Status

**All corrections applied**:
- ✅ Metric conversion system (cm-based storage)
- ✅ Inventory display location (Purchase > Inventory)
- ✅ Removed immutability constraints

**Document is now**:
- Constitutionally compliant (strict definition/instantiation separation)
- Architecturally sound (definitions mutable, instantiations immutable)
- Parallel to ingredient system (LIFO tracking, same patterns)
- User-friendly (accepts both metric and imperial inputs)

---

## Key Architectural Principles Confirmed

1. **Definition/Instantiation Separation**
   - Definitions (Material, MaterialProduct, MaterialUnit) = mutable
   - Instantiations (MaterialInventoryItem, MaterialConsumption) = immutable snapshots
   - Historical data preserved regardless of definition changes

2. **LIFO Inventory Tracking**
   - MaterialInventoryItem table (parallel to ProductInventoryItem)
   - Last In, First Out consumption
   - Actual costs tracked (not weighted average)

3. **Unit Type Inheritance**
   - Material.base_unit_type inherited by all products and units
   - System converts inputs to base unit automatically
   - Clear UI display of inherited types

4. **First-Class Materials Support**
   - Import/export equal to ingredients
   - Service layer provides primitives
   - Planning/production integration

---

## Ready for Review

**Next Steps**:
1. Kent reviews final requirements document
2. Approve or request additional changes
3. Create implementation specifications based on approved requirements
4. Queue for development via spec-kitty

---

**END OF SUMMARY**
