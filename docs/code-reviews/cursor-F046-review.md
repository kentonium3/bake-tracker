# Code Review: F046 - Finished Goods, Bundles & Assembly Tracking

**Reviewer:** Cursor
**Date:** 2026-01-10
**Commit Range:** main..046-finished-goods-bundles-assembly

## Executive Summary
F046 successfully replaces the post-F045 “zero-cost placeholder” paths by adding dynamic `calculate_current_cost()` methods and wiring assembly cost capture to real computed costs. Verification commands pass cleanly, but there are a few spec-alignment concerns around what “current cost” means (ingredient price changes vs historical production averages), nested FinishedGood handling (out-of-scope) and precision/ledger completeness.

## Blockers
- None found based on verification commands and review of the changed files.

## Critical Issues

### “Current cost” semantics may not satisfy spec’s “ingredient prices change → cost updates”
- **Where:** `src/models/finished_unit.py` (`calculate_current_cost`)
- **Problem:** `FinishedUnit.calculate_current_cost()` is implemented as a weighted average of historical `ProductionRun.per_unit_cost` values. If ingredient purchase prices change (but no new production runs are recorded), this value will not change.
- **Impact:** User Story 3 / FR-014/FR-016 expectation (“ingredient prices change ⇒ package cost reflects updated prices”) may not be met depending on intended meaning of “current prices”.
- **Recommendation:** Clarify intended behavior:
  - If “current cost” should reflect **existing stock cost**, then this approach is reasonable (it’s effectively a historical average).
  - If “current cost” should reflect **today’s ingredient costs for planning**, cost should be derived from current inventory/purchases/recipe costing, not past production snapshots.

### Nested FinishedGoods are handled but are explicitly out-of-scope; ledger coverage is incomplete for them
- **Where:** `src/services/assembly_service.py` (`_record_assembly_impl`)
- **Problem:** The code decrements nested FinishedGood inventory and charges cost for nested assemblies, but contains a “KNOWN LIMITATION: No consumption ledger entry is created for nested FGs.” The spec explicitly lists multi-stage assemblies as out-of-scope; if nested assemblies remain possible, the audit trail is incomplete.
- **Impact:** Potential mismatch with FR-018 (“audit trail of component consumption per assembly”) and unclear product behavior vs scope boundaries.
- **Recommendation:** Either:
  - Prevent nested FinishedGoods in compositions for F046 (enforce “FinishedUnits only”), or
  - Fully support nested assemblies including ledger entries and cycle safety.

## Recommendations

### Quantize snapshot costs before persistence for consistency
- **Where:** `src/services/assembly_service.py` (per-unit cost computation and AssemblyRun fields)
- **Suggestion:** Quantize `total_component_cost` / `per_unit_cost` to `Decimal("0.0001")` before persisting so stored values match the intended precision and are stable across DB adapters.

### Reduce float/Decimal precision hazards for component quantities
- **Where:** `src/models/composition.py` (`component_quantity` is `Float`), `src/services/assembly_service.py` (`needed = int(comp.component_quantity * quantity)`)
- **Concern:** Using `Float` quantities and then truncating via `int(...)` can under-consume if non-integer or float imprecision slips in. For FinishedUnit components, the domain is effectively integer counts.
- **Suggestion:** Consider storing FinishedUnit component quantities as `Integer` (or explicitly rounding) and validate at service/UI boundaries.

### Avoid emitting keys named `unit_cost`/`total_cost` in computed dictionaries if import/export rejections are strict
- **Where:** `src/models/composition.py` (`to_dict` adds `"unit_cost"` and `"total_cost"`)
- **Concern:** These are computed (not stored) but the field names overlap with the deprecated “stored cost” vocabulary from F045. If any JSON export path uses `to_dict()`, it could reintroduce those keys and conflict with strict import/versioning expectations.
- **Suggestion:** Keep computed values internal, rename keys (e.g., `computed_unit_cost`), or ensure export serializers never call these `to_dict()` fields.

## Questions for Implementer
1. For User Story 3: should “current cost” be based on **current ingredient prices** (planning) or **historical cost of produced units** (inventory valuation)? The current implementation picks the latter.
2. Are nested FinishedGoods intended to be disallowed for F046 (per out-of-scope), or supported? Current code supports them partially.
3. Should AssemblyRun snapshot costs be rounded/quantized to 4 dp at write time for consistency?

## Verification Results

Ran outside sandbox from `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly`:

```bash
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.models import FinishedUnit, FinishedGood, Composition, Package; print('Models import OK')"
```

Output:
- `Models import OK`

```bash
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.models import FinishedUnit, FinishedGood; assert hasattr(FinishedUnit, 'calculate_current_cost'); assert hasattr(FinishedGood, 'calculate_current_cost'); print('New methods exist OK')"
```

Output:
- `New methods exist OK`

```bash
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_assembly_service.py -v --tb=short -q 2>&1 | tail -5
```

Output:
- `29 passed` (warnings present, no failures)

## Files Reviewed
- `src/models/finished_unit.py` (adds `calculate_current_cost()` from production history)
- `src/models/finished_good.py` (adds `calculate_current_cost()` from component costs)
- `src/models/composition.py` (fixes component cost lookup to use `calculate_current_cost()`)
- `src/models/package.py` (fixes package cost calculations to use dynamic costs)
- `src/services/assembly_service.py` (records real cost snapshots + consumption costs, removes hardcoded zeros)

