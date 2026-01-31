# F086: Fix MaterialUnit Management and Entry UX

**Version**: 1.0
**Date**: 2026-01-30
**Priority**: HIGH
**Type**: Bug Fix + UX Enhancement

---

## Executive Summary

Following the F085 MaterialUnit Schema Refactor, several UX issues emerged that prevent users from effectively managing MaterialUnits for linear products (ribbon, twine, etc.). These issues block the primary user workflow of defining consumption units.

Current gaps:
- ❌ Material Units tab shows no units (broken query after F085 schema change)
- ❌ Edit/Delete buttons disabled for linear product MaterialUnits (selection handler bug)
- ❌ Add Unit dialog requires manual cm conversion (poor UX for "8-inch ribbon")
- ❌ No visual feedback showing what value will be stored

This spec fixes the broken functionality and adds user-friendly unit entry with automatic conversion.

---

## Problem Statement

**Current State (BROKEN):**
```
Material Units Tab
├─ ❌ Shows empty list (detached ORM objects after F085 FK change)
├─ ❌ Query retrieves units but relationships not loaded
└─ Users cannot browse existing MaterialUnits

Edit Product Dialog - Material Units Section
├─ ✅ Units display correctly for selected product
├─ ❌ Edit button stays disabled after selecting a unit
├─ ❌ Delete button stays disabled after selecting a unit
└─ Button state not updating on tree selection

Add Unit Dialog (Linear Products)
├─ ❌ Requires manual cm conversion (8 inches = 20.32 cm)
├─ ❌ Placeholder text shows confusing example
├─ ❌ No unit selector dropdown
└─ Users must use calculator for every entry

User Pain Points:
- Cannot see what MaterialUnits exist across products
- Cannot edit "6-inch Red Ribbon" even though it displays
- Creating "8-inch ribbon" requires knowing 8 * 2.54 = 20.32
- Creating "14-inch ribbon" requires knowing 14 * 2.54 = 35.56
```

**Target State (FIXED):**
```
Material Units Tab
├─ ✅ Shows all MaterialUnits with eager loading
├─ ✅ Displays product name for each unit
└─ ✅ Users can browse complete unit inventory

Edit Product Dialog - Material Units Section
├─ ✅ Units display correctly
├─ ✅ Edit button enables on selection
├─ ✅ Delete button enables on selection
└─ ✅ Button state updates immediately via update_idletasks()

Add Unit Dialog (Linear Products)
├─ ✅ Unit selector dropdown (cm, in, ft, yd, m)
├─ ✅ Enter "8" + select "inches" → saves as 20.32 cm
├─ ✅ Live preview shows "= 20.32 cm (stored value)"
├─ ✅ Helpful placeholder text
└─ ✅ Zero calculator needed

Benefits:
- Complete visibility into MaterialUnit inventory
- Full CRUD operations work for all product types
- User-friendly entry matches mental model ("8-inch ribbon")
- Automatic conversion eliminates calculation errors
```

---

## Root Cause Analysis

### Issue 1: Empty Material Units Tab

**Root Cause**: After F085 changed MaterialUnit.material_id to MaterialUnit.material_product_id, the query in `list_units()` retrieves units correctly but the ORM objects become detached when accessing relationships outside the session scope.

**Fix**: Add eager loading with `joinedload()` to load MaterialProduct and Material relationships within the session.

### Issue 2: Disabled Edit/Delete Buttons

**Root Cause**: The `_on_units_tree_select()` handler correctly sets button state, but CustomTkinter doesn't always reflect state changes immediately without explicit update.

**Fix**: Call `update_idletasks()` after setting button state, and ensure `_update_add_unit_button_visibility()` is called after form population.

### Issue 3: Manual Centimeter Conversion

**Root Cause**: The Add Unit dialog was designed before considering that users think in inches/feet/yards, not centimeters. No conversion layer exists.

**Fix**: Add unit conversion service with dropdown selector and automatic conversion on save.

---

## Requirements

### Functional Requirements

- **FR-001**: Material Units tab MUST display all MaterialUnits from the database with their associated product name via eager loading
- **FR-002**: System MUST enable Edit and Delete buttons when a MaterialUnit is selected in the Edit Product dialog's Material Units section
- **FR-003**: Add Unit dialog MUST display a unit selector dropdown for linear products with options: Centimeters (cm), Inches (in), Feet (ft), Yards (yd), Meters (m)
- **FR-004**: System MUST automatically convert user-entered quantities to centimeters before storing in quantity_per_unit field
- **FR-005**: Add Unit dialog MUST show live conversion preview (e.g., "= 20.32 cm") as user types
- **FR-006**: Unit selector dropdown MUST only appear for linear products (base_unit_type = 'linear_cm')
- **FR-007**: "Each" type products MUST NOT show unit dropdown (direct numeric entry only)

### Conversion Factors (for FR-004)

| Unit | To Centimeters |
|------|----------------|
| 1 inch | 2.54 cm |
| 1 foot | 30.48 cm |
| 1 yard | 91.44 cm |
| 1 meter | 100 cm |
| 1 mm | 0.1 cm |

### Non-Functional Requirements

- **NFR-001**: Button state changes MUST be visible within 100ms of user selection
- **NFR-002**: Conversion preview MUST update on every keystroke (no lag)
- **NFR-003**: Service layer MUST use Decimal for conversion to avoid floating point errors

---

## Implementation Components

### WP01: Fix Material Units Tab Query
- Add `include_relationships` parameter to `list_units()`
- Use SQLAlchemy `joinedload()` for MaterialProduct and Material
- Update UI to pass `include_relationships=True`

### WP02: Fix Edit/Delete Button Enablement
- Add `update_idletasks()` calls after button state changes
- Ensure visibility update called after form population

### WP03: Create Unit Conversion Service
- Add `get_linear_unit_options()` returning (code, display_name) tuples
- Add `convert_to_cm(value, from_unit)` wrapper function
- Store conversion factors as Decimal for precision

### WP04: Enhance MaterialUnit Dialog
- Detect linear products via `material.base_unit_type`
- Add CTkComboBox for unit selection
- Implement conversion on save
- Add live preview label

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All MaterialUnits appear in Material Units tab (100% visibility)
- **SC-002**: Edit/Delete buttons enable immediately upon unit selection
- **SC-003**: Users can create "8-inch ribbon" by entering "8" and selecting "inches"
- **SC-004**: Conversion preview shows correct cm value before save
- **SC-005**: All values stored in database are in centimeters (base unit)
- **SC-006**: No unit dropdown appears for "each" type products

---

## Dependencies

- **F085**: MaterialUnit Schema Refactor (prerequisite - defines MaterialUnit.material_product_id FK)

---

## Testing Notes

### Manual Test Cases

1. **Material Units Tab**: Open tab, verify all units display with product names
2. **Button Enablement**: Select unit in Edit Product dialog, verify Edit/Delete enable
3. **Unit Dropdown**: Add unit to linear product, verify dropdown appears with 5 options
4. **Conversion**: Enter "8" + "inches", verify preview shows "= 20.32 cm"
5. **Save**: Save unit, query database to confirm quantity_per_unit = 20.32
6. **Each Type**: Add unit to "each" product, verify NO dropdown appears
