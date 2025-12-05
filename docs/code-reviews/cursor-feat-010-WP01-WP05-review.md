# Feature 010 (WP01-WP05) - Independent Code Review

**Reviewer:** Cursor
**Date:** 2025-12-05
**Scope:** WP01 Model/Constants, WP02 Unit Converter, WP03 Ingredient Service, WP04 Import/Export, WP05 UI Density Input
**Status:** Needs attention (see checklist)

---

## Executive Summary

The 4-field density model is wired through models, services, import/export, and the UI. Core logic and tests generally align with the spec, but a few regressions and mismatches will block correct density-driven conversions and accurate UI display.

---

## Findings (ordered by severity)

### Critical / High

- **Density still resolves to zero in recipe flows**
  - `src/services/unit_converter.py` keeps a deprecated `get_ingredient_density()` stub that always returns `0.0`.
  - `src/services/recipe_service.py` and `src/models/unit_conversion.py` still import/use this stub, so density-dependent conversions will silently compute with zero density (bad quantities/costs) instead of using the new 4-field model or raising for missing density.
  - Impact: incorrect recipe scaling/shopping math anywhere cross-unit conversions require density.

- **UI cannot show actual density values**
  - `ingredient_service.get_all_ingredients()` returns dicts without `density_g_per_ml`; `src/ui/ingredients_tab.py` expects that key, so every ingredient displays “No density” even when density is set. User feedback and validation cues are misleading.

### Medium

- **Legacy density export path still advertises `density_g_per_cup`**
  - The legacy (v1.0) ingredient export still emits `density_g_per_cup` while the new model is 4-field. If the legacy export path is invoked, density data won’t round-trip. Consider emitting both or deprecating/guarding the old path to avoid silent data loss.

- **Doc/usage drift**
  - `ingredient_service` module docstring still references `density_g_per_ml` in examples. Low functional risk but can mislead implementers and testers.

---

## Recommendations Checklist

- [ ] Remove the deprecated `get_ingredient_density()` stub from `unit_converter.py`; migrate remaining call sites (`recipe_service.py`, `models/unit_conversion.py`) to use `Ingredient.get_density_g_per_ml()` or updated converter APIs, and fail clearly when density is missing.
- [ ] Include `density_g_per_ml` (computed) in the dict returned by `ingredient_service.get_all_ingredients()` so `ingredients_tab` displays actual densities.
- [ ] If the legacy export path is still supported, emit the 4-field density (and optionally legacy for backward compatibility) or block the path with a clear error to prevent silent density loss.
- [ ] Update documentation/examples in `ingredient_service` (and any user-facing help) to reflect the 4-field density model and `format_density_display()`.

---

## Tests Observed

- `python -m pytest src/tests/models/test_ingredient.py -q` (previous run): pass.
- Unit converter tests (`src/tests/test_unit_converter.py`) cover new density functions, but recipe/service paths still depend on the deprecated stub—no test presently guards those call sites against zero-density behavior.

---

## Residual Risks

- Until the deprecated stub is removed and call sites are migrated, density-based conversions remain incorrect in recipe and conversion helpers.
- UI density display remains misleading until the service returns the computed density.
- Legacy export path may drop density data if used.

