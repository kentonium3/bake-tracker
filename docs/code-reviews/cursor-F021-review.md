# Cursor Code Review: Feature 021 - Field Naming Consistency

**Date:** 2025-12-15
**Reviewer:** Cursor (AI Code Review)
**Feature:** 021-field-naming-consistency
**Branch:** 021-field-naming-consistency

## Summary

This refactor is **not complete** per the spec/prompt. The Product model does introduce `package_unit` / `package_unit_quantity`, and many service/UI call sites have been updated, but there are still **live Python identifiers and JSON output keys** using `purchase_*`, the unified import/export service still hard-codes **v3.3** (not v3.4), and user-facing UI text in the Inventory/Pantry area regressed (shows “Inventory”).

## Verification Results

### grep Validation
(Computed by scanning the Feature 021 worktree contents.)

- `purchase_unit`/`purchase_quantity` in src/: **FAIL — 31 matches**
  - Files:
    - `src/models/recipe.py` (18)
    - `src/models/ingredient_legacy.py` (9)
    - `src/models/product.py` (2) *(comment-only; likely acceptable)*
    - `src/tests/test_validators.py` (2)

- `purchase_unit`/`purchase_quantity` in docs/: **PASS — 2 matches (changelog only)**
  - `docs/design/import_export_specification.md` documents the rename in the v3.4 changelog.

- `purchase_unit`/`purchase_quantity` in examples/test_data/: **PASS — 0 matches**

- `pantry` in tests (unacceptable matches): **PASS — 0 unacceptable matches**
  - Found **4** occurrences in `src/tests/`, but all were in **skip reason strings** referencing historical `PantryItem` (explicitly allowed by the plan).

### Test Results
- pytest result: **FAIL — 717 passed, 12 skipped, 19 failed, 48 errors**
  - Failures were dominated by `src/tests/test_catalog_import_service.py` (readonly DB / schema mismatch). The prompt flags this as a known pre-existing isolation issue.

## Findings

### Critical Issues

1) **`purchase_*` identifiers still exist in `RecipeIngredient` (violates SC-001 / Completeness)**
- **File**: `src/models/recipe.py`
- **Evidence**:
  - Local variable `purchase_unit = preferred_product.package_unit`
  - Method name `get_purchase_unit_quantity()`
  - Serialization key `result["purchase_unit_quantity"] = …`
- **Why it matters**: This directly violates “zero matches” success criteria, and it’s exactly the kind of mismatch that causes subtle JSON/schema drift.
- **Fix**: Rename to `package_unit` terminology consistently:
  - `purchase_unit` → `package_unit`
  - `get_purchase_unit_quantity()` → `get_package_unit_quantity()` (or `get_package_unit_amount()`)
  - `purchase_unit_quantity` output key → something explicitly named (e.g., `package_unit_quantity_needed`) to avoid confusing it with `Product.package_unit_quantity`.

2) **Unified import/export is still v3.3 (not v3.4) and still accepts only v3.3**
- **File**: `src/services/import_export_service.py`
- **Evidence**:
  - `export_all_to_json()` docstring says v3.3 and writes `"version": "3.3"`.
  - `import_all_from_json_v3()` rejects anything other than `"3.3"` and errors with “requires v3.3 format”.
- **Why it matters**: This contradicts Feature 021’s stated goal (spec + docs) and guarantees spec drift.
- **Fix**:
  - Update export header to `"version": "3.4"`.
  - Update version validation to require 3.4 (no backward compatibility per spec).
  - Update error messages accordingly.

3) **User-facing “Pantry” terminology regressed to “Inventory” inside the Pantry tab**
- **File**: `src/ui/inventory_tab.py`
- **Evidence**:
  - Header label text: `"Inventory Management"`
- **Why it matters**: Spec FR-015/016 require user-facing UI text to remain “Pantry”.
- **Fix**:
  - Change user-facing strings back to “Pantry …” (e.g., “Pantry Management”) while keeping internal variable names as inventory.

4) **Legacy model still defines `purchase_unit` / `purchase_quantity` as columns**
- **File**: `src/models/ingredient_legacy.py`
- **Evidence**:
  - `purchase_quantity = Column(Float, …)`
  - `purchase_unit = Column(String(50), …)`
  - Helper/serialization methods named with `purchase_*`.
- **Why it matters**: Even if “legacy”, it violates the feature’s explicit success criteria and keeps confusing terminology in the codebase.
- **Fix**:
  - Either remove this module from the codebase (if truly unused) or refactor it to the new terminology / move it out of `src/models/` if it is purely archival.

5) **Validator test still uses `purchase_unit_size` key**
- **File**: `src/tests/test_validators.py`
- **Evidence**: `"purchase_unit_size": "50 lb"`
- **Why it matters**: This is a direct leftover from the old schema and will confuse future maintainers.
- **Fix**: Rename test data key to match current schema (or remove if it’s for deprecated behavior).

### Warnings

- **Sample JSON versions not updated**: `test_data/sample_data.json` still declares `"version": "3.3"`, and `test_data/baking_ingredients_v32.json` is `"version": "3.2"`.
  - If Feature 021 is enforcing v3.4-only, these fixtures must be updated (or clearly marked as legacy/non-importable examples).

- **UI wording mismatch**: `IngredientFormDialog` still uses “Purchase Information” and help text referencing “purchase unit”. This isn’t a strict `purchase_unit` identifier issue, but it’s inconsistent with the new “package” terminology.

### Observations

- **Product model change looks correct**: `Product.package_unit` and `Product.package_unit_quantity` are present and used by services.
- **Catalog import service already uses package fields**: `src/services/catalog_import_service.py` uses `package_unit` / `package_unit_quantity` for products.

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/models/product.py | ⚠️ Changes needed | New fields present; contains comment with old names (acceptable), but overall feature still fails SC-001. |
| src/models/recipe.py | ❌ Needs revision | Still uses `purchase_unit*` names and emits `purchase_unit_quantity` in `to_dict()`. |
| src/services/product_service.py | ✅ Approved | Uses `package_unit` / `package_unit_quantity`. |
| src/services/import_export_service.py | ❌ Needs revision | Still exports/imports v3.3; must be v3.4 per spec/docs. |
| src/services/recipe_service.py | ✅ Approved | No obvious `purchase_*` field usage; relies on product package fields. |
| src/services/inventory_item_service.py | ✅ Approved | Uses product package fields for units. |
| src/services/finished_unit_service.py | ✅ Approved | No field rename issues spotted. |
| src/services/event_service.py | ✅ Approved | No field rename issues spotted in reviewed portion. |
| src/services/catalog_import_service.py | ✅ Approved | Uses `package_unit` / `package_unit_quantity`. |
| src/services/assembly_service.py | ✅ Approved | Uses `product.package_unit` when consuming packaging. |
| src/ui/inventory_tab.py | ❌ Needs revision | User-facing text shows “Inventory”; should remain “Pantry”. |
| src/ui/ingredients_tab.py | ✅ Approved | No `purchase_*` naming problems observed. |
| src/ui/forms/recipe_form.py | ✅ Approved | Uses package-unit naming when checking conversions. |
| src/ui/forms/ingredient_form.py | ⚠️ Changes suggested | Still says “Purchase Information” (wording). |
| src/ui/widgets/data_table.py | ✅ Approved | No naming issues observed. |
| src/utils/validators.py | ✅ Approved | No `purchase_*` identifier issues observed. |
| src/tests/conftest.py | ✅ Approved | Provides in-memory DB isolation for many tests. |
| src/tests/test_models.py | ✅ Approved | Uses new package fields for Product tests. |
| src/tests/test_validators.py | ❌ Needs revision | Contains `purchase_unit_size` key and skip text referencing old field name. |
| docs/design/import_export_specification.md | ✅ Approved | Bumped to v3.4 and documents rename. |
| test_data/sample_data.json | ❌ Needs revision | Still v3.3, not v3.4. |

## Conclusion

**NEEDS REVISION**

Feature 021 has the right intent and partial implementation, but it currently fails the key “zero old field name identifiers” checks and leaves import/export at v3.3. Fixing `recipe.py` + `ingredient_legacy.py` + `import_export_service.py` versioning + the Pantry-facing UI strings should bring it into spec compliance.
