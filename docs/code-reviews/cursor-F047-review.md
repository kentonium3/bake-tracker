# Code Review: F047 - Materials Management System

**Reviewer:** Cursor
**Date:** 2026-01-10
**Commit Range:** main..047-materials-management-system
**Feature Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/047-materials-management-system/kitty-specs/047-materials-management-system/spec.md`

## Executive Summary
F047 is a substantial, well-structured addition: it introduces a dedicated materials hierarchy, weighted-average inventory, and assembly-time material consumption with denormalized history snapshots. Verification commands passed, but there are a few **spec compliance gaps** (notably multi-product assignment during assembly and material purchases export) plus a concrete correctness bug in `MaterialConsumption.to_dict()` when including relationships.

## Blockers

### Generic material assignment cannot be split across multiple products (spec scenario)
- **Spec:** User Story 6, Acceptance Scenario 3 (“30 from Snowflakes, 20 from Holly”), FR-014/FR-015
- **Where:** `src/services/material_consumption_service.py` (`material_assignments: Dict[composition_id -> product_id]`), `src/ui/forms/record_assembly_dialog.py` (`PendingMaterialsDialog`), `src/models/composition.py` uniqueness `uq_composition_assembly_material`
- **Problem:** A generic `Material` placeholder can only be assigned to **one** `MaterialProduct` per composition, and the DB uniqueness constraint prevents using multiple placeholder rows to emulate split allocation.
- **Impact:** The user cannot record assemblies that require splitting the same pending material across multiple products to match available stock; this is explicitly described in the spec’s acceptance scenario.
- **Recommendation:** Change the assignment contract to support per-composition allocation, e.g. `Dict[composition_id -> Dict[product_id -> base_units_consumed]]` (or a list of allocations), validate totals, and record one `MaterialConsumption` row per allocation.

### Export does not include material purchases (spec requirement)
- **Spec:** FR-020 (“System MUST include material purchases in view data export”)
- **Where:** `src/services/coordinated_export_service.py` (no `MaterialPurchase` export), `src/services/material_purchase_service.py` (no export integration)
- **Problem:** The coordinated export adds material catalog entities, but there is no export (or import) path for material purchases.
- **Impact:** Backups / data transfers will lose material purchase history and therefore lose the “weighted-average state” provenance that drives costs.
- **Recommendation:** Add export support for `MaterialPurchase` (and corresponding import if required), or document clearly that “view data export” is handled elsewhere—and implement it there.

## Critical Issues

### `MaterialConsumption.to_dict(include_relationships=True)` references a non-existent field
- **Where:** `src/models/material_consumption.py` (`to_dict` include_relationships branch)
- **Problem:** It reads `self.assembly_run.run_date`, but `AssemblyRun` uses `assembled_at`.
- **Impact:** Any UI/view/export path that calls `to_dict(include_relationships=True)` will raise at runtime.
- **Recommendation:** Use `assembled_at` (or remove this block if not used).

## Major Concerns

### Layering violation + error masking in `Composition` model
- **Where:** `src/models/composition.py` (`get_component_cost`, `get_component_availability`)
- **Problem:** The model imports and calls service functions (`material_unit_service.get_current_cost/get_available_inventory`) without passing a session, and catches `Exception` and returns `0`.
- **Impact:** Hidden failures are hard to debug (“why is cost 0?”), and it risks inconsistent session handling / performance (extra session creation) when these methods are called in bulk.
- **Recommendation:** Move cost/availability computation into service/UI layer where a session is available, and avoid blanket exception swallowing.

### Type/rounding risks around “unit” quantities
- **Where:** `src/models/composition.py` uses `Float component_quantity`; `src/services/material_consumption_service.py` does `needed_units = int(comp.component_quantity * assembly_quantity)`
- **Problem:** Truncation via `int(...)` and float arithmetic can under-consume or under-validate in edge cases.
- **Impact:** Inventory and cost can drift over time if fractional values slip through UI/service validation.
- **Recommendation:** For MaterialUnit compositions, require integer quantities (store as `Integer`), or round explicitly and validate at input boundaries.

### Base unit type naming differs from spec
- **Spec:** assumptions mention `square_feet`; implementation uses `square_inches` for base storage
- **Where:** `src/models/material.py` constraint; `src/services/material_catalog_service.py` docs/validation; `src/services/material_purchase_service.py` conversion
- **Concern:** This is likely fine (internal storage in sq-in is sensible), but it’s not aligned with the spec naming and could confuse future features/UI if they expose the enum directly.

## Minor Issues
- **MaterialConsumption immutability**: setting `updated_at = None` is a soft convention; immutability is not enforced at the DB level.
- **Proportional consumption precision**: `MaterialUnit` proportional consumption uses floats; consider handling tiny remainder/epsilon and/or quantizing stored costs consistently.
- **Assembly “can assemble” UI**: the confirm button’s enablement appears driven by `assembly_service.check_can_assemble()` (food/packaging) and doesn’t pre-check material sufficiency; materials are still blocked at save (good), but UX could be improved with earlier feedback.

## Positive Observations
- **Clean data model intent**: mandatory category→subcategory→material hierarchy and product-level inventory matches spec well.
- **Hard-stop enforcement**: `material_consumption_service.record_material_consumption()` validates availability and throws `ValidationError` (no “bypass”), matching the spirit of FR-014/FR-015.
- **History snapshots**: `MaterialConsumption` captures product/material/category/subcategory/supplier names at consumption time, aligning with the historical accuracy goal.
- **Export/import foundations**: coordinated export + catalog import add slug-based FK resolution fields (`category_slug`, `subcategory_slug`, `material_slug`, `supplier_name`) and test coverage for those paths.

## Recommendations
- **Assignment model**: implement split allocations for generic materials (blocker above).
- **Export scope**: implement material purchase export (and import as needed) or align the spec to the actual export mechanism.
- **Fix `MaterialConsumption.to_dict`**: swap `run_date` to `assembled_at`.
- **Move computation out of model**: stop calling services from `Composition` and stop swallowing exceptions.
- **Tighten numeric semantics**: prefer integer counts where domain is count-like; otherwise, validate and round explicitly.

## Questions for Implementer
1. Should generic materials allow **split allocation** across products (as the spec’s scenario suggests), or should the spec be revised to “pick exactly one product” for now?
2. What is the intended “view data export” mechanism for FR-020—should it be `coordinated_export_service`, or some other export (e.g., the JSON v4.x export)?
3. Are “area” materials intended to be modeled internally as `square_inches` (current approach), with UI presenting square-feet inputs? If so, can we align naming/documentation to reduce confusion?

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

## Files Reviewed
- `src/models/composition.py` (extended component XOR constraint + material component support)
- `src/models/material_category.py`, `src/models/material_subcategory.py`, `src/models/material.py`, `src/models/material_product.py`, `src/models/material_unit.py` (new hierarchy + product inventory model)
- `src/models/material_consumption.py` (new denormalized history snapshot model)
- `src/services/material_purchase_service.py` (weighted average + conversion + adjustments)
- `src/services/material_unit_service.py` (aggregated availability + weighted cost per unit)
- `src/services/material_consumption_service.py` (hard-stop validation + consumption recording + snapshots)
- `src/services/assembly_service.py` (integrates material consumption and cost totals)
- `src/services/catalog_import_service.py`, `src/services/coordinated_export_service.py` (materials catalog export/import)
- `src/ui/forms/record_assembly_dialog.py` (pending material selection dialog + assignments)

## Overall Assessment
**Needs revision** due to the blockers above (split allocation for generic materials and material purchase export requirement), plus the `MaterialConsumption.to_dict()` correctness issue.

