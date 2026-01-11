# Code Review: F048 - Materials UI Rebuild

**Reviewer:** Cursor
**Date:** 2026-01-11
**Commit Range:** main..048-materials-ui-rebuild
**Feature Spec:** /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/048-materials-ui-rebuild/kitty-specs/048-materials-ui-rebuild/spec.md

## Executive Summary
The new three-tab Materials UI largely mirrors the Ingredients pattern (tabview, sortable `Treeview` grids, cascading L0/L1 filters, modal CRUD dialogs) and passed all verification commands. However, key spec requirements for the catalog filter set and edit dialogs are missing: the Level filter is not implemented, and both material and product edit dialogs render the name field read-only (and the material base unit selector is ignored on save), blocking required edit flows.

## Blockers
- None observed beyond the critical issues below.

## Critical Issues
- **Missing Level filter on Materials Catalog (FR-004)**
  - **Location:** `src/ui/materials_tab.py` (`MaterialsCatalogTab._create_filter_bar`)
  - **Problem:** The catalog filter bar omits the Level dropdown (All Levels / Root Categories / Subcategories / Materials) mandated by FR-004 and the spec’s acceptance scenarios. Only search + L0/L1 + Clear are present.
  - **Impact:** Users cannot filter by hierarchy level as required; spec compliance failure.
  - **Recommendation:** Add the Level filter control matching `IngredientsTab` (values: All Levels, Root Categories (L0), Subcategories (L1), Materials (L2)), wire it into `_apply_filters`, and update status text to reflect active filters.

- **Material edit dialog prevents renaming and silently drops base unit changes**
  - **Location:** `MaterialFormDialog._create_form/_save`
  - **Problem:** In edit mode the Name field is rendered read-only (label instead of entry), so users cannot rename a material (spec User Story 2, Acceptance 4). Additionally, the dialog collects a “Default Unit” but `_save` passes `base_unit_type` while `material_catalog_service.update_material` ignores that field, so any base-unit change is silently discarded.
  - **Impact:** Required edit capability is blocked; unit changes appear to succeed but are not persisted, leading to user confusion and inconsistent data.
  - **Recommendation:** Make Name editable in edit mode and pass it to `update_material`. Either disable Default Unit editing when updating (and hide the control), or add an explicit service path to change `base_unit_type` with validation/error if disallowed—do not silently ignore the value.

- **Product edit dialog prevents renaming**
  - **Location:** `MaterialProductFormDialog._create_form/_save`
  - **Problem:** In edit mode the Product Name is rendered read-only (label only). Spec User Story 4 (Acceptance 4) requires opening an edit dialog pre-populated and allowing edits.
  - **Impact:** Users cannot rename products; spec-required edit flow is blocked.
  - **Recommendation:** Allow name editing in edit mode and persist via `update_product`.

## Major Concerns
- **No Level filter means “filter state” status is minimal**
  - Status bar currently shows counts but not which filters are active. Once Level filtering is added, consider mirroring the Ingredients status messaging to make active filters obvious. (Non-blocking once Level filter exists.)

## Minor Issues
- None noted beyond the UI omissions above.

## Positive Observations
- Three-tab structure, sortable `Treeview` grids, cascading L0/L1 filters, and modal CRUD dialogs closely follow the Ingredients pattern.
- Inventory and cost formatting match spec examples (e.g., `"4,724.5 inches"`, `"$0.0016"`).
- Buttons correctly gate actions on selection (Edit/Record Purchase/Adjust Inventory).
- Record Purchase dialog autocalculates total units and unit cost live from packages and price inputs.

## Recommendations
- Implement the Level filter end-to-end to satisfy FR-004 and acceptance scenarios.
- Enable editable names in material/product edit dialogs and ensure base unit changes are either persisted with validation or explicitly disabled with clear messaging.
- After fixes, rerun a quick manual check against the acceptance scenarios, especially filtering by level and editing existing records.

## Questions for Implementer
- Should material `base_unit_type` be immutable after creation (as the service currently enforces)? If so, can we hide/disable that field in edit mode to avoid implying it will change?

## Verification Results
- `/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.ui.materials_tab import MaterialsTab, MaterialFormDialog, MaterialProductFormDialog, RecordPurchaseDialog, AdjustInventoryDialog, MaterialUnitFormDialog; print('Materials UI imports OK')"` → Materials UI imports OK
- `/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services import material_catalog_service, material_purchase_service, material_unit_service, supplier_service; print('Material services import OK')"` → Material services import OK
- `/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests -v --tb=short -q | tail -10` → 1958 passed, 14 skipped (TD-001 skips), 0 failures

## Files Reviewed
- `src/ui/materials_tab.py` — New 3-tab UI, dialogs, grids, filtering/sorting, status bars.
- `src/ui/materials_tab_old.py` — Archived reference (tree-based).
- `src/ui/ingredients_tab.py` — Pattern reference for parity checks.
- `src/services/material_catalog_service.py`, `src/models/material.py` — To confirm base_unit_type behavior and edit mutability expectations.

## Overall Assessment
Needs revision. Core structure and behavior align with the Ingredients pattern, and verification/tests are green, but missing Level filtering and locked/ignored edits on material/product dialogs block spec-required workflows. Address the critical UI gaps, then this should be ready to ship.
