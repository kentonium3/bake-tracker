# Research: Fix MaterialUnit Management and Entry UX

**Feature**: 086-fix-material-unit-management-ux
**Date**: 2026-01-30

## Overview

This feature addresses bugs and UX issues in MaterialUnit management after the F084 schema refactor. Research is minimal as the issues are well-understood from user investigation.

## Issue 1: Material Units Tab Empty

### Investigation Findings

**Symptom**: Material Units tab shows no units despite units existing in the database.

**Root Cause**: Likely the tab's query still references the old `Material.units` relationship that was removed in F084. MaterialUnits are now children of MaterialProduct, not Material.

**Evidence**: The F084 schema change moved MaterialUnit from Material to MaterialProduct:
- Old: `Material` → `MaterialUnit` (one-to-many)
- New: `MaterialProduct` → `MaterialUnit` (one-to-many)

**Solution Approach**:
1. Locate the query populating the Material Units tab listing
2. Update to query `MaterialUnit` joined with `MaterialProduct`
3. Display product name alongside unit details for context

### Decision

- **Decision**: Update tab query to use `MaterialProduct.material_units` relationship
- **Rationale**: Aligns with F084 schema; no alternative approaches needed
- **Alternatives considered**: None - this is the only correct approach

---

## Issue 2: Edit/Delete Buttons Disabled

### Investigation Findings

**Symptom**: When user selects a MaterialUnit in the Edit Product dialog (for linear products), Edit and Delete buttons remain disabled.

**Code Review** (`src/ui/materials_tab.py:794-804`):
```python
def _on_units_tree_select(self, event=None):
    """Update button states based on selection."""
    if not self.units_tree:
        return

    selection = self.units_tree.selection()
    state = "normal" if selection else "disabled"
    if self.edit_unit_btn:
        self.edit_unit_btn.configure(state=state)
    if self.delete_unit_btn:
        self.delete_unit_btn.configure(state=state)
```

**Hypothesis**: The handler logic appears correct. Potential causes:
1. Event binding not working for the units tree in linear product context
2. `self.units_tree` or button references are None
3. Handler not being called at all

**Solution Approach**:
1. Add debug logging to verify handler is called
2. Verify button references are valid
3. Check if there's conditional logic elsewhere affecting button state

### Decision

- **Decision**: Debug and fix event binding/handler execution
- **Rationale**: The handler code is correct; execution path needs investigation
- **Alternatives considered**: Rewrite handler - rejected as unnecessary complexity

---

## Issue 3: Unit Conversion UX

### Investigation Findings

**Symptom**: Users must manually convert measurements to centimeters when creating MaterialUnits for linear products (e.g., 8 inches → 20.32 cm).

**Current Dialog** (`src/ui/dialogs/material_unit_dialog.py`):
- Asks for "Qty per Unit" with placeholder "e.g., 0.1524 (6 inches in meters)" - which is incorrect and confusing
- No unit selector - assumes cm input
- User must perform manual conversion

**Solution Approach**:
1. Create conversion service to maintain layered architecture
2. Add dropdown with common linear units: cm, inches, feet, yards, meters
3. Show dropdown only for linear products (determined by material's base_unit_type)
4. Convert to cm on save

### Conversion Factors (Standard)

| Unit | Symbol | cm Equivalent |
|------|--------|---------------|
| Centimeter | cm | 1.0 |
| Inch | in | 2.54 |
| Foot | ft | 30.48 |
| Yard | yd | 91.44 |
| Meter | m | 100.0 |

### Decision

- **Decision**: Create `unit_conversion_service.py` with conversion functions
- **Rationale**: Keeps business logic in service layer per constitution; reusable for future features
- **Alternatives considered**:
  - Inline conversion in dialog - rejected (violates layered architecture)
  - Pre-defined unit constants only - rejected (less flexible)

---

## Summary

| Issue | Root Cause | Solution | Complexity |
|-------|------------|----------|------------|
| Tab empty | Old query after F084 | Update query path | Low |
| Buttons disabled | Event binding issue | Debug and fix | Low |
| Manual conversion | No unit dropdown | Add dropdown + service | Medium |

All issues are straightforward fixes with no architectural unknowns.
