# Work Packages: Catalog Tab Layout Standardization

**Inputs**: Design documents from `/kitty-specs/087-catalog-tab-layout-standardization/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md

**Tests**: No explicit testing work required - existing tests validate regressions.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Include precise file paths or modules.

---

## Work Package WP01: RecipesTab ttk.Treeview Conversion (Priority: P1) 🎯 MVP

**Goal**: Replace RecipeDataTable with ttk.Treeview for native trackpad scrolling support.
**Independent Test**: Open Recipes tab, scroll with trackpad two-finger swipe - should scroll smoothly.
**Prompt**: `tasks/WP01-recipes-treeview-conversion.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T001 Create ttk.Treeview with columns (Name, Category, Yield) in `src/ui/recipes_tab.py`
- [x] T002 Add vertical scrollbar configuration for native trackpad scrolling
- [x] T003 Implement column header click-to-sort functionality
- [x] T004 Implement row selection callback (<<TreeviewSelect>>)
- [x] T005 Implement double-click callback (<Double-1>) for edit dialog
- [x] T006 Implement variant grouping (sort variants after base, prefix with "↳")
- [x] T007 Remove RecipeDataTable import and update grid placement

### Implementation Notes
- Copy ttk.Treeview pattern from IngredientsTab (lines 234-296)
- Preserve column widths: Name 330, Category 120, Yield 150
- Variant sorting: base recipes first, variants sorted after their base
- Status bar and recipe count must continue working

### Parallel Opportunities
- None - this WP must complete first to validate the pattern.

### Dependencies
- None (starting package).

### Risks & Mitigations
- Variant grouping logic is complex - test thoroughly with recipes that have variants
- Column sorting must toggle ascending/descending correctly

---

## Work Package WP02: IngredientsTab Layout Cleanup (Priority: P2)

**Goal**: Remove title label and standardize layout to 3-row pattern.
**Independent Test**: Open Ingredients tab - no "My Ingredients" title, search at top.
**Prompt**: `tasks/WP02-ingredients-cleanup.md`
**Estimated Size**: ~250 lines

### Included Subtasks
- [x] T008 [P] Remove "My Ingredients" title label from `src/ui/ingredients_tab.py`
- [x] T009 [P] Update grid row indices (shift all rows up by 1)
- [x] T010 [P] Update grid_rowconfigure calls (row 0→search, row 1→buttons, row 2→grid, row 3→status)
- [x] T011 [P] Reduce vertical padding to PADDING_MEDIUM consistently

### Implementation Notes
- Remove _create_title() method and its grid() call
- Update row indices in grid() calls: 1→0, 2→1, 3→2, 4→3
- Verify search/filter controls appear at row 0 after change

### Parallel Opportunities
- All subtasks can proceed after WP01 completes (validates ttk.Treeview pattern).

### Dependencies
- Depends on WP01 (pattern validation).

### Risks & Mitigations
- Row index errors will break layout - verify each control is correctly placed

---

## Work Package WP03: ProductsTab Row Consolidation (Priority: P2)

**Goal**: Remove title and consolidate 5 rows to 3 rows.
**Independent Test**: Open Products tab - no "Product Catalog" title, controls in 2 rows, grid fills space.
**Prompt**: `tasks/WP03-products-consolidation.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [x] T012 [P] Remove "Product Catalog" header in `src/ui/products_tab.py`
- [x] T013 [P] Merge toolbar + filters + search into 2 rows (filters+search row 0, toolbar row 1)
- [x] T014 [P] Update grid row indices (header removed, controls consolidated)
- [x] T015 [P] Update grid_rowconfigure calls (row 0→filters, row 1→buttons, row 2→grid)
- [x] T016 [P] Reduce vertical padding to PADDING_MEDIUM

### Implementation Notes
- Current structure: header(0), toolbar(1), filters(2), search(3), grid(4)
- Target structure: filters+search(0), buttons(1), grid(2)
- Move Add Product button from toolbar to search/button row
- Keep all filter dropdowns (L0, L1, L2, Brand, Supplier) in row 0

### Parallel Opportunities
- Can proceed in parallel with WP02 and WP04 after WP01 completes.

### Dependencies
- Depends on WP01 (pattern validation).

### Risks & Mitigations
- Many controls to reorganize - verify all filters work after consolidation

---

## Work Package WP04: MaterialsTab and Sub-tabs Standardization (Priority: P2)

**Goal**: Remove outer title and apply 3-row pattern to all 3 sub-tabs.
**Independent Test**: Open Materials tab - no "Materials Catalog" title, all sub-tabs have consistent layout.
**Prompt**: `tasks/WP04-materials-standardization.md`
**Estimated Size**: ~500 lines

### Included Subtasks
- [ ] T017 [P] Remove "Materials Catalog" title from `src/ui/materials_tab.py` (lines 86-93)
- [ ] T018 [P] Update outer grid_rowconfigure (tabview at row 0 with weight=1)
- [ ] T019 [P] Apply 3-row pattern to MaterialsCatalogTab (filters row 0, buttons row 1, grid row 2)
- [ ] T020 [P] Apply 3-row pattern to MaterialProductsTab
- [ ] T021 [P] Apply 3-row pattern to MaterialUnitsTab
- [ ] T022 [P] Verify ttk.Treeview grids use weight=1 in all sub-tabs

### Implementation Notes
- MaterialsTab outer: remove _create_title(), shift tabview to row 0
- Each sub-tab class needs its own row consolidation
- Sub-tabs are defined within materials_tab.py (MaterialsCatalogTab, MaterialProductsTab, MaterialUnitsTab)
- Pattern should match IngredientsTab (after WP02 cleanup)

### Parallel Opportunities
- Can proceed in parallel with WP02 and WP03 after WP01 completes.
- T017-T18 (outer) can proceed independently of T19-T22 (sub-tabs).

### Dependencies
- Depends on WP01 (pattern validation).

### Risks & Mitigations
- Three sub-tabs to update - systematic checklist to avoid missing one
- Test each sub-tab individually after changes

---

## Dependency & Execution Summary

- **Sequence**: WP01 (blocking) → WP02, WP03, WP04 (parallel)
- **Parallelization**: After WP01 completes, WP02/WP03/WP04 can run in parallel
- **MVP Scope**: WP01 (trackpad scrolling is the primary user fix)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create ttk.Treeview in RecipesTab | WP01 | P1 | No |
| T002 | Add vertical scrollbar | WP01 | P1 | No |
| T003 | Implement column header sorting | WP01 | P1 | No |
| T004 | Implement row selection callback | WP01 | P1 | No |
| T005 | Implement double-click callback | WP01 | P1 | No |
| T006 | Implement variant grouping | WP01 | P1 | No |
| T007 | Remove RecipeDataTable import | WP01 | P1 | No |
| T008 | Remove IngredientsTab title | WP02 | P2 | Yes |
| T009 | Update IngredientsTab row indices | WP02 | P2 | Yes |
| T010 | Update IngredientsTab rowconfigure | WP02 | P2 | Yes |
| T011 | Reduce IngredientsTab padding | WP02 | P2 | Yes |
| T012 | Remove ProductsTab header | WP03 | P2 | Yes |
| T013 | Merge ProductsTab control rows | WP03 | P2 | Yes |
| T014 | Update ProductsTab row indices | WP03 | P2 | Yes |
| T015 | Update ProductsTab rowconfigure | WP03 | P2 | Yes |
| T016 | Reduce ProductsTab padding | WP03 | P2 | Yes |
| T017 | Remove MaterialsTab title | WP04 | P2 | Yes |
| T018 | Update MaterialsTab rowconfigure | WP04 | P2 | Yes |
| T019 | Apply pattern to MaterialsCatalogTab | WP04 | P2 | Yes |
| T020 | Apply pattern to MaterialProductsTab | WP04 | P2 | Yes |
| T021 | Apply pattern to MaterialUnitsTab | WP04 | P2 | Yes |
| T022 | Verify grid weight=1 in sub-tabs | WP04 | P2 | Yes |
