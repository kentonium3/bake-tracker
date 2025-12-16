# Claude Code Prompt: TD-002 Unit Standardization

## Context

Refer to `.kittify/memory/constitution.md` for project principles.

This is a **Technical Debt** task, not a feature. The goal is to close gaps identified in `docs/research/unit_handling_analysis_report.md`.

Reference documents:
- `docs/design/unit_codes_reference.md` — target unit standards
- `docs/design/import_export_specification.md` — v3.4 import/export spec
- `src/utils/constants.py` — ALL_UNITS, WEIGHT_UNITS, VOLUME_UNITS, etc.
- `src/utils/validators.py` — existing validate_unit() function

## Scope

Three tasks, in order:

### Task 1: Fix sample_data.json

**File:** `test_data/sample_data.json`

**Issue:** Vanilla extract (approx. line 189) uses `"package_unit": "oz"` but vanilla extract is a liquid and should use `"fl oz"`.

**Action:** 
- Change `"package_unit": "oz"` to `"package_unit": "fl oz"` for the McCormick vanilla extract product
- Scan for any other liquid ingredients incorrectly using "oz" instead of "fl oz"
- Document any other changes made

### Task 2: Add Import Validation for Units

**Issue:** Import service (`src/services/import_export_service.py`) accepts unit values without validation. Invalid units can enter the database.

**Action:** Add validation for all unit fields during import:

| Entity | Field(s) to Validate |
|--------|---------------------|
| `products` | `package_unit` |
| `ingredients` | `density_volume_unit`, `density_weight_unit` |
| `recipes.ingredients[]` | `unit` |

**Requirements:**
1. Use existing `validate_unit()` from `src/utils/validators.py`
2. Collect all validation errors before failing (don't fail on first error)
3. Return clear error messages: `"Invalid unit '{value}' for {entity}.{field}. Valid units: {list}"`
4. Density unit validation should allow None/null (density fields are optional)
5. Add tests for invalid unit rejection

**Validation rules per field:**
- `package_unit`: Must be in ALL_UNITS (weight, volume, count, or package units all valid)
- `density_volume_unit`: Must be in VOLUME_UNITS (if provided)
- `density_weight_unit`: Must be in WEIGHT_UNITS (if provided)
- Recipe ingredient `unit`: Must be in WEIGHT_UNITS or VOLUME_UNITS or COUNT_UNITS

### Task 3: Database Audit

**Action:** Create and run a script to identify any non-standard unit values currently in the database.

1. Create `src/utils/audit_units.py` with a function that:
   - Queries all unit columns across all tables
   - Compares values against ALL_UNITS from constants.py
   - Reports any non-standard values with table, column, record ID, and value

2. Tables/columns to audit:
   - `products.package_unit`
   - `ingredients.density_volume_unit`
   - `ingredients.density_weight_unit`
   - `recipe_ingredients.unit`
   - `recipes.yield_unit`
   - `finished_units.item_unit`
   - `production_consumptions.unit`
   - `assembly_packaging_consumptions.unit`

3. Output format:
   ```
   Unit Audit Report
   =================
   
   Non-standard units found: X
   
   Table: products
     ID 5: package_unit = "ounces" (not in ALL_UNITS)
   
   Table: recipe_ingredients
     ID 12: unit = "C" (not in ALL_UNITS)
   
   Standard units reference: oz, lb, g, kg, tsp, tbsp, cup, ml, l, fl oz, ...
   ```

4. If non-standard values are found, create a separate migration script to fix them (do not auto-fix without review)

## Deliverables

1. Updated `test_data/sample_data.json` with corrected units
2. Updated `src/services/import_export_service.py` with unit validation
3. New tests in `tests/` for import unit validation
4. New `src/utils/audit_units.py` script
5. Audit report output (save to `docs/research/unit_audit_results.md`)
6. Migration script if non-standard values found (optional, for review)

## Testing

1. Run existing test suite — all tests must pass
2. Add test cases for:
   - Import with valid units succeeds
   - Import with invalid `package_unit` fails with clear message
   - Import with invalid recipe ingredient `unit` fails
   - Import with invalid density units fails
   - Import with null density units succeeds (they're optional)
3. Run unit audit against test database

## Out of Scope

- UI changes (future Feature 023)
- Units reference table (future Feature 023)
- UN/CEFACT code adoption (future)
- Changes to unit conversion logic
