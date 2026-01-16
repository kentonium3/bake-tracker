# Code Review Report: F055 - Workflow-Aligned Navigation Cleanup

**Reviewer:** Cursor (independent review)
**Date:** 2026-01-15
**Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/kitty-specs/055-workflow-aligned-navigation-cleanup/spec.md`

## Summary
Navigation reordering and new Deliver placeholder are present, and purchase tabs were reordered. However, the app will crash when building the Catalog mode because `MainWindow` still expects the old flat tab attributes that were removed by the new grouped Catalog mode. Catalog packaging fails the spec’s “Food Only vs Bundles” split. Several refresh/navigation helpers still reference missing tabs, so even if creation were fixed, backward-compatibility helpers would break. These must be resolved before release.

## Verification
- `/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.ui.mode_manager import ModeManager; from src.ui.modes.deliver_mode import DeliverMode; print('Imports OK')"` ✅
- `/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/services/test_ingredient_service.py -v --ignore=src/tests/migration -x` ✅ (captured via head, pytest exit code 0)

## Findings

### Critical
1) **App crash on startup: Main window still expects old Catalog tab attributes**
`CatalogMode` now exposes grouped tabs (`ingredients_group`, `materials_tab`, etc.), but `MainWindow._create_catalog_mode` still reads `mode.ingredients_tab`, `mode.products_tab`, `mode.recipes_tab`, `mode.finished_units_tab`, and `mode.packages_tab`. These attributes no longer exist, so main window initialization raises `AttributeError` before the UI appears.
```190:206:src/ui/main_window.py
        mode = CatalogMode(self.mode_content)

        # Store tab references for backward compatibility
        self.ingredients_tab = mode.ingredients_tab
        self.products_tab = mode.products_tab
        self.recipes_tab = mode.recipes_tab
        self.finished_units_tab = mode.finished_units_tab
        self.packages_tab = mode.packages_tab
```

2) **Spec gap: Packaging group missing Food vs Bundle split**
Spec FR-008/FR-009/FR-010 require separate “Finished Goods (Food Only)” and “Finished Goods (Bundles)” sub-tabs. Implementation combines them into a single Finished Goods tab and notes the split as a future enhancement, leaving the acceptance criteria unmet.
```3:10:src/ui/tabs/packaging_group_tab.py
Feature 055: Groups Finished Goods and Packages tabs under single
Note: The spec called for separate "Finished Goods (Food Only)" and
"Finished Goods (Bundles)" sub-tabs, but the current FinishedGood model
doesn't have a clear bundle vs food distinction. This implementation uses
a single Finished Goods tab for now.
```

3) **Back-compat refresh/navigation helpers still target removed tabs**
Even after fixing creation, multiple refresh/navigation helpers still reference the removed flat tabs (`ingredients_tab`, `products_tab`, etc.). Calls to `_refresh_all_tabs`, `_refresh_catalog_tabs`, and navigation helpers will fail once invoked.
```457:476:src/ui/main_window.py
        self.ingredients_tab.refresh()
        self.products_tab.refresh()
        self.recipes_tab.refresh()
        self.inventory_tab.refresh()
...
        self.finished_units_tab.refresh()
        self.packages_tab.refresh()
```

### Major
4) **Mode list text and stored refs out of sync with grouped Catalog layout**
Main window docstring and mode comments still describe Catalog as six flat tabs, but the implementation now nests tabs into four groups. Beyond the crash above, stored references for tab access (e.g., `self._tab_refs["recipes"] = self.recipes_tab`) are gone, so any caller relying on those keys will break. Consider exposing equivalent references (e.g., recipe/finished-unit tabs) or adjusting callers.

5) **Deliver placeholder has no dashboard/tab plumbing**
`DeliverMode` overrides BaseMode but skips dashboard and tabview setup. That’s fine for a placeholder, but the mode manager’s tab-state preservation assumes `get_current_tab_index`/`set_current_tab_index` work. Current stubs always return 0 and ignore input; harmless now, but note that adding tabs later will require updating the stub to avoid losing tab state.

### Minor
6) **Spec wording vs implementation (Purchase tab counts)**
Purchase tab order matches the spec (Inventory → Purchases → Shopping Lists). No functional issues noted; included here as a confirmation.

## Recommendations
- Fix the Catalog mode wiring in `MainWindow`: either expose the old tab attributes from `CatalogMode` (mapping to sub-tabs within the new groups) or update `MainWindow` to use the new group structure and adjust refresh/navigation helpers accordingly. This is required to avoid startup crashes.
- Implement the Packaging split per spec (Food Only vs Bundles) or add a temporary filter flag with clear labeling; update docs/help to match actual behavior if full split is deferred.
- Update refresh/navigation helpers to the new grouped tab structure; ensure `_tab_refs` and public navigation methods continue to work or deprecate them explicitly.
- Align comments/help text with the new Catalog grouping to avoid confusion.
- Keep Deliver placeholder minimal but be mindful of tab-state plumbing when real tabs arrive.

## Overall Assessment
Blocked by critical defects (startup crash, missing spec-mandated Packaging split). Fix the Catalog wiring and Packaging split (or adjust spec/UX) before release.
