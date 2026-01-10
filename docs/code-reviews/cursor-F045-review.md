# Code Review: F045 - Cost Architecture Refactor

**Reviewer:** Cursor
**Date:** 2026-01-10
**Commit Range:** main..045-cost-architecture-refactor

## Executive Summary
The branch makes meaningful progress on “costs on instances, not definitions” by removing `unit_cost`/`total_cost` from the definition models and bumping export version to **4.1**. However, there are multiple blockers: service-layer APIs still accept and set removed fields (likely runtime crashes), import/version rejection behavior required by the spec is not implemented, and cost columns remain visible in catalog tables.

## Blockers

1. **`FinishedUnitService` is incompatible with the updated `FinishedUnit` model**
   - The model no longer has a `unit_cost` column, but `FinishedUnitService.create_finished_unit()` still takes `unit_cost`, includes it in `unit_data`, and calls `finished_unit.update_unit_cost_from_recipe()` (method removed from the model).
   - This likely causes immediate runtime failures when creating finished units/yield types (regression risk for F044 yield-type persistence).

2. **Spec-required import rejection behavior is not implemented**
   - Spec requires rejecting v4.0 or lower and rejecting deprecated `unit_cost`/`total_cost` fields with clear messages referencing v4.1.
   - Current import path (`import_all_from_json_v4`) does not appear to validate the top-level `version` field; the unit tests explicitly describe version as “informational only, no validation.”

3. **Spec-required UI catalog cleanup is not implemented**
   - Spec requires Finished Units and Recipes catalogs to show **no cost columns**.
   - `RecipeDataTable` still displays “Total Cost” and “Cost/Unit”.
   - `FinishedGoodDataTable` still displays “Cost/Item” (and this table is used by the Finished Units catalog in current UI wiring).

4. **Spec requires a DB migration script; plan/implementation do not provide one**
   - The spec’s FR-003 calls for a migration that drops columns safely; the plan/research proposes a “reset DB + re-import” workflow instead.
   - This is either a spec deviation that must be approved, or missing implementation.

## Critical Issues

### Service-layer stale cost references (high crash risk)
- **Where:**
  - `src/services/finished_unit_service.py`
  - `src/services/finished_good_service.py` (minor remnants)
- **What:**
  - `FinishedUnitService.create_finished_unit(... unit_cost=...)` builds `unit_data` with `unit_cost` and calls `update_unit_cost_from_recipe()`.
  - `FinishedUnitService.update_finished_unit()` still validates `"unit_cost" in updates`.
  - `FinishedGoodService.update_finished_good()` still validates `"total_cost" in updates`.
- **Why it matters:** The model fields/methods were removed, so passing these values will raise exceptions; UI flows that create finished units are likely broken.
- **Recommendation:**
  - Remove `unit_cost` and all cost-related params/logic from the FinishedUnit service surface area (including legacy compatibility helpers).
  - Remove `total_cost` update validation from FinishedGood service.
  - Add at least one test that exercises the create/update paths so this doesn’t regress again.

### Import/export version bump is only half implemented
- **Where:** `src/services/import_export_service.py`, `src/tests/services/test_import_export_service.py`, `src/tests/integration/test_import_export_v4.py`
- **What:**
  - Export version is bumped to `"4.1"` (good).
  - Import appears to accept files without validating `data["version"]` (tests say version is informational).
- **Recommendation:** Align code + tests with the spec:
  - Validate `data["version"] >= 4.1` for the v4 import path.
  - Produce explicit errors when deprecated cost fields are present in finished_units/finished_goods entries.

### Catalog cost columns remain visible (spec mismatch)
- **Where:** `src/ui/widgets/data_table.py`
- **What:**
  - `RecipeDataTable` columns include “Total Cost” and “Cost/Unit”.
  - `FinishedGoodDataTable` includes “Cost/Item”.
- **Recommendation:**
  - Remove these columns (or gate them behind “computed costs” UX that is explicitly out-of-scope for this feature). As written, it conflicts with FR-013/FR-014.

## Recommendations

- **Clarify source-of-truth between spec vs plan**
  - The spec calls for migration + explicit import validation errors; the plan/research says no migration and “schema validation only”.
  - Decide which is correct, update docs/tests accordingly, and ensure the prompt/spec used for review matches the intended implementation.

- **Strengthen regression coverage**
  - Add tests that call `finished_unit_service.create_finished_unit()` and verify it does not accept or attempt to persist cost fields.
  - Add a test that ensures importing a v4.0 file fails with a helpful message (if spec stands).

## Questions for Implementer

1. **Migration:** Is the “reset DB + re-import” workflow the intended final decision? If so, can we update `spec.md` to remove FR-003 and the migration acceptance scenarios?
2. **Import behavior:** Should `import_all_from_json_v4` enforce version checks (>= 4.1) and reject deprecated fields as the spec requires, or is “informational version only” still desired?
3. **Catalog UI:** Are recipe computed costs still supposed to be shown? The spec says “no cost columns” even if dynamic.
4. **Service contracts:** Should `FinishedUnitService` keep any cost-calculation helpers for future features (F046+), or should those be moved to instance services (production/assembly) now?

## Verification Results

Ran outside sandbox from `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/045-cost-architecture-refactor`:

```bash
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.models import FinishedUnit, FinishedGood; print('Models import OK')"
```

Output:
- `Models import OK`

```bash
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_assembly_service.py -v --tb=short -q 2>&1 | tail -5
```

Output:
- `29 passed` (warnings present, no failures)

## Files Reviewed

- **Models**
  - `src/models/finished_unit.py` (unit_cost removed; cost architecture docstring added)
  - `src/models/finished_good.py` (total_cost removed; some docstrings still mention costs)
  - `src/models/package.py` (touched in branch; not a primary focus beyond cost-field adjacency)
- **Services**
  - `src/services/finished_unit_service.py` (**blocker**: still uses unit_cost/update_unit_cost_from_recipe)
  - `src/services/finished_good_service.py` (minor leftover validation for total_cost)
  - `src/services/import_export_service.py` (export version bumped to 4.1; import version validation appears missing)
- **UI**
  - `src/ui/forms/finished_unit_detail.py` (cost display removed)
  - `src/ui/forms/finished_good_detail.py` (cost display removed)
  - `src/ui/widgets/data_table.py` (**spec mismatch**: cost columns still present)
- **Tests**
  - `src/tests/services/test_import_export_service.py` (states version is informational only)
  - `src/tests/integration/test_import_export_v4.py` (expects export version 4.1)
- **Data**
  - `test_data/sample_data_min.json` (version 4.1; no unit_cost/total_cost in finished units/goods)
  - `test_data/sample_data_all.json` (version 4.1; no unit_cost/total_cost in finished units/goods)

