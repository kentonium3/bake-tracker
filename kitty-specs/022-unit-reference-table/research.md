# Research: Unit Reference Table & UI Dropdowns

**Feature**: 022-unit-reference-table
**Date**: 2025-12-16
**Status**: Complete

## Executive Summary

This feature replaces free-form unit text entry with database-backed dropdown selection. Research confirms the approach is straightforward: create a new Unit model, seed with existing constants.py data, and modify UI forms to use CTkComboBox dropdowns.

## Research Questions & Decisions

### RQ-1: How should units be stored in the database?

**Decision**: New `units` table with simple structure following existing model patterns.

**Rationale**:
- Follows existing BaseModel pattern (id, uuid, created_at, updated_at)
- Minimal required fields: code, display_name, symbol, category
- Optional UN/CEFACT code for future international standard compliance
- No foreign key relationships needed (units are referenced by string code, not FK)

**Alternatives Considered**:
- **Enum-only (no table)**: Rejected because spec requires database-backed storage for future extensibility
- **Complex unit hierarchy**: Rejected as over-engineering for 27 fixed units

**Evidence**: [E-001] Existing model patterns in `src/models/base.py`, `src/models/ingredient.py`

---

### RQ-2: How should units be seeded on application startup?

**Decision**: Idempotent seeding in `init_database()` using existing constants.py definitions.

**Rationale**:
- Constants.py already has all 27 units properly categorized
- Seeding during init_database() ensures units exist before any UI loads
- Idempotent approach (check if empty) prevents duplicate entries on restart
- Single source of truth remains in constants.py (database mirrors it)

**Alternatives Considered**:
- **Migration script**: Rejected per Constitution VI - desktop apps use export/reset/import
- **Lazy seeding on first dropdown open**: Rejected - adds complexity, potential race conditions
- **Move unit definitions to database only**: Rejected - import validation still needs constants.py

**Evidence**: [E-002] Existing `init_database()` pattern in `src/services/database.py`

---

### RQ-3: What UI component should be used for dropdowns?

**Decision**: CTkComboBox with category headers as non-selectable separators.

**Rationale**:
- User confirmed simple approach is acceptable
- CTkComboBox already used throughout codebase (e.g., `ingredient_form.py:126`)
- Category headers provide visual grouping without custom widget complexity
- Can revisit with custom searchable dropdown if user testing reveals issues

**Alternatives Considered**:
- **Custom CTkToplevel popup**: More polished but significantly more code
- **Third-party autocomplete widget**: Adds dependency, integration risk

**Evidence**: [E-003] Existing dropdown patterns in `src/ui/forms/ingredient_form.py`

---

### RQ-4: How should dropdowns filter units by context?

**Decision**: Pass appropriate unit lists to dropdown based on field context.

**Filtering Rules**:
| Field | Categories Shown | Rationale |
|-------|------------------|-----------|
| Product.package_unit | ALL | Products can be purchased in any unit |
| Ingredient.density_volume_unit | VOLUME only | Density requires volume component |
| Ingredient.density_weight_unit | WEIGHT only | Density requires weight component |
| RecipeIngredient.unit | WEIGHT + VOLUME + COUNT | Recipe quantities use measurement units, not package types |

**Rationale**:
- Prevents invalid unit selections at input time
- Matches existing validation logic in constants.py
- Recipe ingredients don't use "bag", "box" etc. (those are package units)

**Evidence**: [E-004] Existing filtering in `ingredient_form.py:247` (volume_units), `ingredient_form.py:270` (weight_units)

---

### RQ-5: Should existing data be migrated or validated?

**Decision**: No migration needed. Existing data with valid units remains unchanged.

**Rationale**:
- TD-002 (completed) already standardized all unit values
- Existing valid unit strings match what will be in units table
- No FK relationship means no referential integrity to enforce
- Edge case (invalid unit in legacy data) handled by preserving as-is

**Evidence**: [E-005] TD-002 completion in `docs/technical-debt/TD-002_unit_standardization.md`

---

## Open Questions

None - all questions resolved during planning interrogation.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Category headers confuse users | Low | Low | Can add tooltip/help text if needed |
| Performance of 27-item dropdown | Very Low | Low | Negligible - CTkComboBox handles this easily |
| Future unit additions break dropdown | Low | Medium | Document process: add to constants.py, restart seeds |

## References

- [E-001] `src/models/base.py` - BaseModel pattern
- [E-002] `src/services/database.py:90-113` - init_database() function
- [E-003] `src/ui/forms/ingredient_form.py:126-133` - CTkComboBox usage
- [E-004] `src/ui/forms/ingredient_form.py:247-278` - Unit filtering patterns
- [E-005] `docs/technical-debt/TD-002_unit_standardization.md` - Completed prerequisite
