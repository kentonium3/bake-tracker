# Cursor Code Review: Feature 022 - Unit Reference Table

**Date:** 2025-12-16
**Reviewer:** Cursor (AI Code Review)
**Feature:** 022-unit-reference-table
**Branch:** 022-unit-reference-table

## Summary

Feature 022 is largely well-executed and matches the intent: a DB-backed `Unit` reference table seeded on initialization, a small `unit_service` for query helpers, and UI dropdowns that constrain unit entry (including header/non-selectable separators for the grouped dropdowns). Unit-specific tests are solid and the full suite passes.

Main concerns are minor UX/consistency drift rather than correctness:
- Some UI labels/variable names still use “Purchase …” terminology even though the model uses `package_unit` / `package_unit_quantity`.
- The recipe form’s `yield_unit` is still a readonly dropdown (spec says yield_unit stays free-form). This appears pre-existing, but the file is being touched for unit dropdown work so it’s worth calling out.

## Verification Results

### Unit Count Validation
(Executed from the Feature 022 worktree with `BAKING_TRACKER_ENV=development` and database initialization.)

- Total units: **27** (expected 27)
- Weight: **4** (expected 4)
- Volume: **9** (expected 9)
- Count: **4** (expected 4)
- Package: **10** (expected 10)

### Test Results
- pytest result: **PASS — 812 passed, 12 skipped, 0 failed**
- Unit-specific tests: **PASS — 49 passed** (`test_unit_model.py`, `test_unit_seeding.py`, `test_unit_service.py`)

### grep Validation
(The prompt’s directory-wide grep checks appeared to skip `.worktrees/` paths in this environment, so I used a local scan of `src/ui/` within the Feature 022 worktree.)

- CTkOptionMenu remaining: **12 occurrences** across 6 files
  - These appear to be unrelated UI dropdowns (filters / non-unit fields). Unit fields in scope are implemented with `CTkComboBox`.
- Hardcoded unit constants in UI: **ACCEPTABLE (with notes)**
  - References remain in `src/ui/forms/ingredient_form.py`, `src/ui/forms/recipe_form.py`, `src/ui/ingredients_tab.py`.
  - In-scope unit fields use `unit_service` for dropdown values; constants remain for other contexts and for backward-compat.

## Findings

### Critical Issues
None found.

### Warnings

1) **Yield unit is still constrained in recipe form**
- **File**: `src/ui/forms/recipe_form.py`
- **Observation**: `yield_unit` is implemented as a readonly `CTkComboBox` with a predefined list.
- **Spec alignment**: The spec explicitly says yield_unit remains free-form text (descriptive yields like “cookies”).
- **Recommendation**: Confirm whether this is intentional legacy behavior. If not, change `yield_unit` back to a free-form entry (or at least allow arbitrary text).

2) **Terminology drift: “Purchase Quantity” label for product package units**
- **File**: `src/ui/ingredients_tab.py`
- **Observation**: Product dialog labels and variable names still say “Purchase Quantity” even though the value is stored as `package_unit_quantity`.
- **Recommendation**: Consider renaming labels to “Package Quantity” for consistency (this overlaps with Feature 021’s naming cleanup goals).

3) **Seeding log message / idempotency**
- **File**: `src/services/database.py`
- **Observation**: `init_database()` logs “Seeding unit reference table” every time even though `seed_units()` may immediately skip when non-empty.
- **Recommendation**: Either adjust log level/message or log only when seeding actually occurs.

### Observations

- **Model design**: `Unit` follows BaseModel inheritance and has the expected fields (`code`, `display_name`, `symbol`, `category`, `un_cefact_code`, `sort_order`).
- **Seeding**: `seed_units()` is idempotent (count check) and seeds from `constants.py` with metadata mapping. It is called from `init_database()` after `create_all()`.
- **Service layer**: `unit_service` follows the `session=None` pattern and orders units by `sort_order` within category; `get_units_for_dropdown()` returns headers plus codes, and preserves category order as passed in.
- **UI dropdown behavior**:
  - Product package unit dropdown uses `get_units_for_dropdown(["weight","volume","count","package"])` (31 items) and prevents selecting headers via callback + save-time validation.
  - Recipe ingredient unit dropdown uses `get_units_for_dropdown(["weight","volume","count"])` and prevents selecting headers.
  - Ingredient density unit dropdowns use `get_units_by_category("volume")` and `get_units_by_category("weight")` (no headers; readonly).

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/models/unit.py | ✅ Approved | Clean model; expected fields; BaseModel inheritance. |
| src/models/__init__.py | ✅ Approved | `Unit` exported. |
| src/services/database.py | ✅ Approved | `seed_units()` exists, idempotent, called from `init_database()`. |
| src/services/unit_service.py | ✅ Approved | Session parameter pattern used; dropdown formatting matches prompt. |
| src/ui/ingredients_tab.py | ✅ Approved (minor concerns) | Product package unit dropdown uses DB + header prevention; “Purchase Quantity” label drift. |
| src/ui/forms/ingredient_form.py | ✅ Approved | Density unit dropdowns populated from DB categories; readonly. |
| src/ui/forms/recipe_form.py | ✅ Approved (minor concerns) | Recipe ingredient unit dropdown uses DB + header prevention; yield_unit still constrained. |
| src/tests/test_unit_model.py | ✅ Approved | Covers creation/uniqueness/BaseModel fields. |
| src/tests/test_unit_seeding.py | ✅ Approved | Covers 27-unit seed + idempotency + category counts + metadata. |
| src/tests/test_unit_service.py | ✅ Approved | Covers all query helpers + dropdown formatting + session arg. |

## Architecture Assessment

### Session Management
PASS. All `unit_service` functions accept `session: Optional[Session] = None` and only open a `session_scope()` when session is not provided.

### UI Consistency
PASS for the fields in Feature 022 scope (product package_unit, ingredient density units, recipe ingredient unit). Header selection prevention is implemented where headers exist.

### Test Coverage
PASS. Dedicated tests for model/service/seeding + full suite regression green.

## Conclusion

**APPROVED (with minor concerns)**

Feature 022 meets the core requirements and is regression-safe (812 tests passing). Follow-up improvements are mostly around terminology polish and confirming the intended behavior of `yield_unit` in the recipe form.
