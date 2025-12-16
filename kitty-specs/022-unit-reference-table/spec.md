# Feature Specification: Unit Reference Table & UI Dropdowns

**Feature Branch**: `022-unit-reference-table`
**Created**: 2025-12-16
**Status**: Draft
**Input**: User description: "Create database-backed unit reference table to replace free-form unit entry with searchable dropdowns in UI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Select Unit from Dropdown When Adding Product (Priority: P1)

When a user adds a new product to the catalog, they select the package unit from a dropdown menu instead of typing it manually. This prevents typos and ensures consistency across all products.

**Why this priority**: This is the most frequently used unit selection in the application. Products are added regularly, and package_unit errors propagate to inventory and cost calculations.

**Independent Test**: Can be fully tested by adding a new product and verifying the unit dropdown appears with all valid units, grouped by category, and the selected unit is stored correctly.

**Acceptance Scenarios**:

1. **Given** a user is on the Add Product form, **When** they click the package_unit field, **Then** a searchable dropdown appears showing all valid units grouped by category (Weight, Volume, Count, Package)
2. **Given** the unit dropdown is open, **When** the user types "oz", **Then** the dropdown filters to show "oz" (weight ounce) and "fl oz" (fluid ounce)
3. **Given** the user selects "lb" from the dropdown, **When** they save the product, **Then** "lb" is stored as the package_unit value

---

### User Story 2 - Select Density Units When Defining Ingredient (Priority: P2)

When a user defines an ingredient with density information, they select volume and weight units from appropriate dropdowns. Volume unit dropdown shows only volume units; weight unit dropdown shows only weight units.

**Why this priority**: Density information enables unit conversion for recipe scaling. Restricting to appropriate unit types prevents invalid density definitions.

**Independent Test**: Can be fully tested by editing an ingredient's density fields and verifying each dropdown shows only the appropriate unit category.

**Acceptance Scenarios**:

1. **Given** a user is editing an ingredient's density, **When** they click density_volume_unit, **Then** only volume units appear (tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal)
2. **Given** a user is editing an ingredient's density, **When** they click density_weight_unit, **Then** only weight units appear (oz, lb, g, kg)
3. **Given** the user sets density as "1 cup = 4.5 oz", **When** they save, **Then** both unit values are stored correctly

---

### User Story 3 - Select Unit When Adding Recipe Ingredient (Priority: P2)

When a user adds an ingredient to a recipe, they select the unit from a dropdown showing weight, volume, and count units (but not package units, which don't make sense for recipe quantities).

**Why this priority**: Recipe ingredient units directly affect shopping lists and production calculations. Consistent units are essential for accurate aggregation.

**Independent Test**: Can be fully tested by adding an ingredient to a recipe and verifying the unit dropdown shows appropriate measurement units.

**Acceptance Scenarios**:

1. **Given** a user is adding flour to a recipe, **When** they click the unit field, **Then** a dropdown shows weight, volume, and count units (not package units like "bag" or "box")
2. **Given** the dropdown is open, **When** the user selects "cup", **Then** "cup" is stored as the recipe ingredient unit
3. **Given** an existing recipe ingredient with unit "cup", **When** the user edits it, **Then** the dropdown shows "cup" pre-selected

---

### User Story 4 - Reference Table Seeded on First Launch (Priority: P1)

When the application starts with a new or migrated database, the units reference table is automatically populated with all standard units, ensuring dropdowns have data to display.

**Why this priority**: Without seed data, dropdowns would be empty and the feature non-functional. This is a prerequisite for all other stories.

**Independent Test**: Can be fully tested by starting with a fresh database and verifying all 27 units exist in the reference table.

**Acceptance Scenarios**:

1. **Given** a fresh database with no units table, **When** the application starts, **Then** the units table is created and populated with all standard units
2. **Given** an existing database with units table, **When** the application starts, **Then** existing unit data is preserved (no duplicates created)
3. **Given** the units table exists, **When** queried, **Then** it contains exactly 27 units across 4 categories (4 weight, 9 volume, 4 count, 10 package)

---

### Edge Cases

- What happens when existing data contains a unit not in the reference table?
  - Existing data is preserved; validation only applies to new entries via UI
- How does the system handle if a user somehow bypasses the dropdown?
  - Server-side validation rejects invalid units; import validation (from TD-002) already enforces this
- What if the units table is empty or corrupted?
  - Application detects missing seed data and re-populates on startup

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a reference table storing all valid measurement units with code, display name, symbol, and category
- **FR-002**: System MUST seed the reference table with standard units on first launch or migration (27 units: 4 weight, 9 volume, 4 count, 10 package)
- **FR-003**: System MUST provide a nullable field for future UN/CEFACT code storage without requiring it now
- **FR-004**: UI MUST replace free-form text entry with dropdown selection for package_unit field on products
- **FR-005**: UI MUST replace free-form text entry with dropdown selection for density_volume_unit field on ingredients (showing only volume units)
- **FR-006**: UI MUST replace free-form text entry with dropdown selection for density_weight_unit field on ingredients (showing only weight units)
- **FR-007**: UI MUST replace free-form text entry with dropdown selection for unit field on recipe ingredients (showing weight, volume, and count units)
- **FR-008**: Dropdowns MUST group units by category (Weight, Volume, Count, Package) for easier navigation; type-to-filter deferred to future enhancement based on user testing
- **FR-010**: System MUST preserve existing data with valid units without requiring re-entry
- **FR-011**: System MUST NOT modify yield_unit field behavior (remains free-form text for descriptive yields like "cookies")
- **FR-012**: Import/export functionality MUST continue to work with unit validation unchanged (uses existing TD-002 validation)

### Key Entities

- **Unit**: Represents a valid measurement unit with:
  - Unique code (e.g., "oz", "cup", "lb") - the stored value
  - Display name (e.g., "ounce", "cup", "pound") - human-readable full name
  - Symbol (e.g., "oz", "cup", "lb") - what appears in UI dropdowns
  - Category (weight, volume, count, package) - for grouping and filtering
  - UN/CEFACT code (optional) - for future international standard compliance

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can select units from dropdowns in under 3 seconds (faster than typing and fixing typos)
- **SC-002**: Zero unit entry errors possible through UI (all inputs constrained to valid values)
- **SC-003**: 100% of existing valid unit data remains functional after migration
- **SC-004**: All 27 standard units are available in appropriate dropdowns based on context
- **SC-005**: All existing tests continue to pass after implementation
- **SC-006**: Export/import round-trips preserve unit values exactly as before

## Assumptions

- The 27 units currently defined in `src/utils/constants.py` represent the complete set of valid units needed
- Users do not need to add custom units beyond the predefined set
- The existing import validation from TD-002 will continue to use constants.py (database queries not required for import)
- yield_unit intentionally allows free-form text for descriptive yields (confirmed by user)

## Out of Scope

- Full UN/CEFACT code enforcement (codes stored but not required)
- Unit conversion logic changes (stays in unit_converter.py)
- Import format changes (already standardized in TD-002)
- Localization/internationalization of unit names
- Custom unit creation by users
- yield_unit dropdown (remains free-form by design)

## Reference Documents

- `docs/design/feature_023_unit_reference_table.md` - Original feature proposal
- `docs/design/unit_codes_reference.md` - UN/CEFACT standard reference
- `docs/research/unit_handling_analysis_report.md` - Current state analysis
- `docs/technical-debt/TD-002_unit_standardization.md` - Completed prerequisite work
