# Code Review Report: F058 - Materials FIFO Foundation

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-18
**Feature Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/058-materials-fifo-foundation/spec.md`

## Executive Summary
Materials FIFO plumbing largely mirrors the ingredient pattern, but several regressions block core workflows: metric base units are rejected by the UI, FIFO consumption only works for linear units, coordinated exports omit material inventory and even crash on material purchases, and the Materials UI still calls removed inventory adjustment APIs. These issues risk user-facing failures, data loss in backups, and unusable flows; fixes are required before release.

## Review Scope

**Primary Files Modified:**
- `src/models/material_inventory_item.py`
- `src/models/material_product.py`
- `src/models/material_consumption.py`
- `src/models/material.py`
- `src/models/material_purchase.py`
- `src/models/__init__.py`
- `src/services/material_inventory_service.py`
- `src/services/material_purchase_service.py`
- `src/services/material_consumption_service.py`
- `src/services/material_unit_converter.py`
- `src/services/material_unit_service.py`
- `src/services/material_catalog_service.py`
- `src/services/denormalized_export_service.py`
- `src/services/import_export_service.py`
- `src/services/catalog_import_service.py`
- `src/services/coordinated_export_service.py`
- `src/ui/materials_tab.py`
- Tests under `src/tests/**` for materials FIFO

**Additional Code Examined:**
- Ingredient FIFO services for pattern parity
- Legacy UI patterns for Materials tab

## Environment Verification

**Setup Process:**
```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/058-materials-fifo-foundation-WP01
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/test_material_fifo_integration.py -v --tb=short
```

**Results:**
- Passed: 11 tests (FIFO integration suite). Warnings about FK drop ordering only.

---

## Findings

### Critical Issues

**UI base-unit options reject metric units**
- **Location:** `src/ui/materials_tab.py` (`MATERIAL_BASE_UNITS`)
- **Problem:** Dropdown lists `["each","linear_inches","square_inches"]` while the model constraint requires metric (`each|linear_cm|square_cm`). Users cannot create/edit materials with valid units; attempts will fail validation.
- **Impact:** Material creation/edit in UI fails; blocks metric adoption and any new material setup.
- **Recommendation:** Update UI options and defaults to `each`, `linear_cm`, `square_cm`; validate against the model constraint before submit.

**Material product listing crashes when inventory exists**
- **Location:** `src/services/material_catalog_service.py` (`list_products`)
- **Problem:** Weighted cost calculation uses `item.unit_cost`, but `MaterialInventoryItem` exposes `cost_per_unit`. Any inventory lot triggers AttributeError, breaking Materials tab and service callers.
- **Impact:** Product lists fail as soon as inventory exists; Materials UI unusable after first purchase.
- **Recommendation:** Use `item.cost_per_unit` consistently; add null guards and tests with inventory present.

**FIFO consumption hardcodes linear cm**
- **Location:** `src/services/material_consumption_service.py` (`_decrement_inventory`)
- **Problem:** Calls `consume_material_fifo(..., target_unit="cm")` regardless of material base_unit_type. For `square_cm` or `each`, unit conversion rejects the request.
- **Impact:** FIFO consumption only works for linear materials; area/each materials always fail, blocking assemblies and consumption flows.
- **Recommendation:** Pass the material’s base unit / appropriate target unit to `consume_material_fifo`; add coverage for `square_cm` and `each`.

**Coordinated export fails and drops material inventory**
- **Location:** `src/services/coordinated_export_service.py` (`_export_material_purchases`; no export for `MaterialInventoryItem`)
- **Problem:** Exports reference nonexistent fields `base_units_purchased` / `cost_per_base_unit` (actual fields are `units_added` / `unit_cost`), causing export errors. Material inventory lots are not exported at all, so backups lose FIFO data.
- **Impact:** Backup/restore for materials is broken and data-lossy; exports crash on purchases and cannot restore inventory or costing.
- **Recommendation:** Align material purchase export fields with the model; add `MaterialInventoryItem` export/import in coordinated flows with import_order dependency; extend tests.

**Materials UI still calls removed inventory adjustment**
- **Location:** `src/ui/materials_tab.py` (`_adjust_inventory`)
- **Problem:** UI invokes `material_purchase_service.adjust_inventory`, which is NotImplemented after FIFO shift; dialog also relies on obsolete `inventory` field.
- **Impact:** Clicking “Adjust Inventory” raises, confusing users and leaving dead UI.
- **Recommendation:** Remove/disable the adjust-inventory action until a FIFO-compatible adjustment path exists, or reimplement against inventory items.

### Major Concerns

**Spec parity for base-unit metric conversion**
- Some UI text still references imperial units; ensure user-facing copy and defaults reflect metric requirement (`linear_cm`, `square_cm`).

**Export/import schema coverage**
- Context-rich and catalog exports intentionally drop deprecated fields, but coordinated backup currently omits the new `MaterialInventoryItem` entity and material consumption linkages; parity with ingredient backups is incomplete.

### Minor Issues

- Minor naming drift: cost fields sometimes converted to strings vs Decimals inconsistently; standardize for API/UI expectations.

### Positive Observations

- Core FIFO model and service pattern match the ingredient system (new `MaterialInventoryItem`, FIFO service, converter tests).
- Integration tests cover multi-lot FIFO, cost calculation, and end-to-end purchase→consume flows for linear units.

## Spec Compliance Analysis
- Core FIFO behaviors (lot creation on purchase, oldest-first consumption, cost tracking) are implemented and tested for linear units.
- Metric base-unit requirement is violated in UI and some service callers; area/each paths fail consumption due to hardcoded `"cm"`.
- Inventory separation is reflected in models/services, but UI still exposes legacy inventory adjustments.
- Backup/import parity for materials is incomplete: inventory lots not exported/imported; purchase export fields wrong.
- Edge cases from spec (insufficient inventory messaging, zero-cost purchases) are partly covered in tests; UI gaps and export omissions remain.

## Code Quality Assessment

**Consistency with Codebase:** Service/session patterns follow existing conventions. UI still carries legacy widgets and naming, diverging from the new metric/FIFO model.

**Maintainability:** FIFO service mirrors ingredient pattern, aiding comprehension. UI and export code need cleanup to remove deprecated flows and align types.

**Test Coverage:** Strong integration coverage for FIFO linear flows. Missing tests for `square_cm`/`each` consumption, UI-layer metric validation, and coordinated export of material inventory.

**Dependencies & Integration:** Tight coupling between UI and now-removed `current_inventory`; coordinated export missing new entity integration breaks backup flows.

## Recommendations Priority

**Must Fix Before Merge:**
1. Fix UI base-unit options to `each|linear_cm|square_cm` and validate accordingly.
2. Replace `unit_cost` with `cost_per_unit` in material product inventory cost calculation.
3. Make FIFO consumption unit-aware (handle `square_cm` and `each`).
4. Repair coordinated export/import: correct material purchase fields and include `MaterialInventoryItem` lots (with import order/deps).
5. Remove/disable legacy “Adjust Inventory” UI that calls NotImplemented.

**Should Fix Soon:**
1. Update user-facing copy/defaults to reflect metric units.
2. Add tests for area/each FIFO flows and material inventory export/import.

**Consider for Future:**
1. Provide a FIFO-friendly inventory adjustment/transfer UI for materials.
2. Harmonize money/Decimal formatting across material services/exports.

## Overall Assessment
Needs revision. Core FIFO engine works for linear materials, but UI validation, unit handling, and backup/export coverage have critical gaps that will block users, break consumption for area/each materials, and lose inventory data in backups. Address the must-fix items before shipping to ensure metric compliance, reliable FIFO across unit types, and safe backups.
