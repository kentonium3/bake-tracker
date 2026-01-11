# Code Review: F047A - Materials Management System (Re-review)

**Reviewer:** Cursor
**Date:** 2026-01-11
**Commit Range:** main..047-materials-management-system
**Feature Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/047-materials-management-system/kitty-specs/047-materials-management-system/spec.md`

## Executive Summary
Re-review of F047 after fixes landed in response to my prior review (`cursor-F047-review.md`). The previously reported **blockers and critical issue are resolved**: generic materials now support split allocation across multiple products, material purchases are included in coordinated export, and `MaterialConsumption.to_dict(include_relationships=True)` no longer references a non-existent `run_date`.

## Blockers
- None found in this re-review.

## Critical Issues
- None found in this re-review.

## Major Concerns

### `Composition` still calls service-layer functions and swallows exceptions
- **Where:** `src/models/composition.py` (`get_component_cost`, `get_component_availability`)
- **Status vs prior review:** Not addressed (still present)
- **Why it matters:** It can hide real failures behind `0` cost/availability and creates extra sessions when called in bulk. This is more of a maintainability/debuggability risk than a correctness blocker.
- **Recommendation:** Move these computations to the service/UI layer where a session is already available; avoid blanket `except Exception: return 0`.

## Minor Issues

### MaterialUnit “needed units” rounding semantics
- **Where:** `src/services/material_consumption_service.py` (`raw_needed = comp.component_quantity * assembly_quantity; needed_units = round(raw_needed)`)
- **Concern:** `round()` can mask non-integer `component_quantity` values rather than rejecting them. If the domain is “count of units,” it may be better to validate integer-ness explicitly.
- **Recommendation:** Validate that `raw_needed` is near an integer (within epsilon) or enforce integer quantities at input/model level.

## Positive Observations

### Split allocation support is now implemented end-to-end (fixes prior blocker)
- **Where:**
  - `src/ui/forms/record_assembly_dialog.py` (`PendingMaterialsDialog` now collects per-product quantities)
  - `src/services/material_consumption_service.py` (`material_assignments` supports `composition_id -> {product_id: qty}` with sum validation + per-allocation consumption)
- **Why it’s good:** This directly satisfies the spec scenario (e.g., “30 from Snowflakes, 20 from Holly”) and matches the “hard stop” workflow (validation enforces exact totals and sufficient inventory).

### Material purchases are now exported (fixes prior blocker)
- **Where:** `src/services/coordinated_export_service.py`
- **Details:** Adds `material_purchases` to `DEPENDENCY_ORDER` and exports `material_purchases.json` with `product_slug` and `supplier_name` fields for FK resolution.

### MaterialConsumption relationship serialization bug fixed (fixes prior critical issue)
- **Where:** `src/models/material_consumption.py`
- **Details:** `to_dict(include_relationships=True)` now includes `assembly_run.assembled_at` instead of `run_date`.

## Recommendations
- Consider also importing `material_purchases` if you want round-trip portability for purchase history (spec only requires purchases in view export, but this may become important for full backups).
- Keep tightening numeric/rounding boundaries (counts vs continuous base-units) to prevent gradual drift.

## Questions for Implementer
1. Should the coordinated import layer eventually support `material_purchases.json` (full backup/restore), or is export-only sufficient for now?
2. For MaterialUnit compositions: should `component_quantity` be strictly integer in the UI/model?

## Verification Results

Ran outside sandbox from `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/047-materials-management-system`:

```bash
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.models import MaterialCategory, MaterialSubcategory, Material, MaterialProduct, MaterialUnit, MaterialPurchase, MaterialConsumption; print('Material models import OK')"
```

Output:
- `Material models import OK`

```bash
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services import material_catalog_service, material_purchase_service, material_unit_service, material_consumption_service; print('Material services import OK')"
```

Output:
- `Material services import OK`

```bash
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_material_catalog_service.py -v --tb=short -q 2>&1 | tail -5
```

Output:
- `46 passed` (warnings present, no failures)

Additional (not required by prompt, but run for confidence):

```bash
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_material_consumption_service.py -q --tb=short
```

Output:
- `23 passed`

```bash
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/services/test_coordinated_export.py -q --tb=short
```

Output:
- `27 passed`

## Files Reviewed
- `src/services/material_consumption_service.py` (split allocation support + validation)
- `src/ui/forms/record_assembly_dialog.py` (split allocation UI + plumbing to `assembly_service.record_assembly`)
- `src/services/coordinated_export_service.py` (material purchases export)
- `src/models/material_consumption.py` (relationship serialization fix)
- `src/models/composition.py` (constraint/wiring sanity; remaining layering concern)

## Overall Assessment
**Pass with minor fixes** (remaining concerns are primarily layering/numeric-validation polish, not correctness blockers).

