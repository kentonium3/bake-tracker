# Implementation Plan: Catalog Tab Layout Standardization

**Branch**: `087-catalog-tab-layout-standardization` | **Date**: 2026-01-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/087-catalog-tab-layout-standardization/spec.md`

## Summary

Standardize all Catalog tabs to use a consistent 3-row layout (filters, actions, grid), remove unnecessary title labels, convert RecipeDataTable to ttk.Treeview for trackpad scrolling, and reduce padding. This is a pure UI refactoring feature with no functionality changes.

The key technical challenge is replacing RecipeDataTable (custom CTkScrollableFrame widget) with ttk.Treeview while preserving variant grouping, sorting, selection, and double-click behavior.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter, tkinter (ttk.Treeview), SQLAlchemy
**Storage**: N/A (no database changes)
**Testing**: pytest - verify no regressions
**Target Platform**: macOS desktop (trackpad scrolling focus), Windows
**Project Type**: single (desktop application)
**Performance Goals**: Smooth trackpad scrolling, responsive UI
**Constraints**: Must preserve all existing functionality
**Scale/Scope**: 7 UI files modified, ~400 lines changed

## Constitution Check

*GATE: Must pass before Phase 0 research. ✅ Passed*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ | Improves UX with consistent layouts, trackpad scrolling |
| II. Data Integrity | ✅ | No data changes - pure UI refactoring |
| III. Future-Proof Schema | ✅ | No schema changes |
| IV. Test-Driven Development | ✅ | Existing tests validate no regressions |
| V. Layered Architecture | ✅ | Changes limited to UI layer only |
| VI. Schema Change Strategy | ✅ | N/A |
| VII. Pragmatic Aspiration | ✅ | Establishes pattern for future tabs (F088) |

**No constitution violations. No complexity tracking required.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/087-catalog-tab-layout-standardization/
├── plan.md              # This file
├── research.md          # Pattern analysis from source files
├── spec.md              # Feature specification
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks/               # Work packages (via /spec-kitty.tasks)
```

### Source Code (files to modify)

```
src/ui/
├── recipes_tab.py           # RecipeDataTable → ttk.Treeview (major change)
├── ingredients_tab.py       # Remove title, reduce padding
├── products_tab.py          # Remove title, consolidate control rows
├── materials_tab.py         # Remove outer title
└── tabs/
    ├── materials_catalog_tab.py   # Apply 3-row pattern
    ├── materials_products_tab.py  # Apply 3-row pattern
    └── materials_units_tab.py     # Apply 3-row pattern

src/ui/widgets/
└── data_table.py            # RecipeDataTable (to be deprecated)

src/utils/
└── constants.py             # PADDING_MEDIUM reference (read only)
```

**Structure Decision**: Single project layout. All changes are in `src/ui/` layer only.

## Implementation Strategy

### Phase 1: RecipesTab ttk.Treeview Conversion (Highest Priority/Risk)

**Why first**: This is the most complex change and the primary usability fix (trackpad scrolling). Validating this early de-risks the feature.

**Approach**:
1. Create ttk.Treeview with columns: Name (330), Category (120), Yield (150)
2. Add vertical scrollbar for native scroll support
3. Implement header click → sort functionality
4. Implement row selection callback (<<TreeviewSelect>>)
5. Implement double-click callback (<Double-1>)
6. Implement variant grouping: sort variants after base recipes, prefix with "↳ "
7. Preserve status bar and recipe count display

**Pattern source**: Copy from IngredientsTab ttk.Treeview implementation

### Phase 2: IngredientsTab Cleanup (Low Risk)

**Approach**:
1. Remove "My Ingredients" title label (row 0)
2. Shift search/filter controls to row 0
3. Shift action buttons to row 1
4. Shift grid to row 2
5. Update `grid_rowconfigure()` calls
6. Reduce `pady` values to PADDING_MEDIUM

### Phase 3: ProductsTab Consolidation (Medium Risk)

**Approach**:
1. Remove "Product Catalog" title label
2. Consolidate toolbar + filters + search into single filters row (row 0)
3. Move action buttons to row 1
4. Keep grid at row 2
5. Update row configurations

### Phase 4: MaterialsTab and Sub-tabs (Low-Medium Risk)

**Approach**:
1. Remove "Materials Catalog" title from outer container (lines 88-93)
2. Apply 3-row pattern to MaterialsCatalogTab
3. Apply 3-row pattern to MaterialProductsTab
4. Apply 3-row pattern to MaterialUnitsTab

## Work Package Strategy

Given the parallelization goal, structure work packages by tab independence:

| WP | Tab(s) | Parallelizable | Risk |
|----|--------|----------------|------|
| WP01 | RecipesTab | No (must complete first) | High |
| WP02 | IngredientsTab | Yes (after WP01 validates pattern) | Low |
| WP03 | ProductsTab | Yes (parallel with WP02) | Medium |
| WP04 | MaterialsTab + 3 sub-tabs | Yes (parallel with WP02/03) | Low |

After WP01 completes and validates the ttk.Treeview pattern, WP02-04 can run in parallel.

## Acceptance Criteria (from spec)

### Layout Consistency
- [ ] All catalog tabs have NO title labels
- [ ] All catalog tabs use 3-row layout (controls, actions, grid)
- [ ] All tabs use weight=0 for controls, weight=1 for grid
- [ ] Padding uses PADDING_MEDIUM consistently

### Trackpad Scrolling
- [ ] Recipes tab scrolls with trackpad gestures
- [ ] All ttk.Treeview grids support two-finger swipe

### Functionality Preserved
- [ ] Search works in all tabs
- [ ] Filters work correctly
- [ ] Action buttons work
- [ ] Grid selection works
- [ ] Double-click opens edit dialogs
- [ ] Sorting works (click column headers)
- [ ] Variant grouping works in Recipes tab

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| RecipeDataTable conversion breaks variant grouping | Explicitly test variant display order before marking complete |
| RecipeDataTable conversion breaks sorting | Test all column header sorts |
| Padding too cramped | Use PADDING_MEDIUM minimum; visual review |
| Grid doesn't expand on resize | Test window resize explicitly |
| Materials sub-tabs missed | Systematic checklist for all 3 sub-tabs |

## Data Model

**N/A** - This is a pure UI refactoring feature. No data model changes.

## Contracts

**N/A** - No API changes. No service layer changes.

## Quickstart

**Testing after implementation**:

```bash
# Run the app and verify:
./run-tests.sh  # No test failures
python src/main.py  # Visual verification

# In the app, verify for each Catalog tab:
# 1. No title label visible
# 2. Search/filter at top, buttons below, grid fills space
# 3. Two-finger trackpad scroll works (especially Recipes tab)
# 4. Window resize expands/contracts grid
# 5. All CRUD operations still work
```

---

**Plan Status**: Complete - Ready for `/spec-kitty.tasks`
