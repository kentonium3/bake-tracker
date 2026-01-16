# Tasks: Workflow-Aligned Navigation Cleanup

**Feature**: 055-workflow-aligned-navigation-cleanup
**Generated**: 2026-01-15
**Plan**: [plan.md](plan.md)

---

## Work Package Summary

| WP | Title | Subtasks | Files | Dependencies |
|----|-------|----------|-------|--------------|
| WP01 | Mode Navigation Reorder | 4 | 3 files + 1 new | None |
| WP02 | Purchase Mode Tab Reorder | 2 | 1 file | None |
| WP03 | Catalog Menu Restructure | 6 | 1 file + 3 new | WP01 (modes registered) |
| WP04 | Tree View Removal | 3 | 1 file | None |
| WP05 | Verification & Cleanup | 3 | 0 new files | WP01-WP04 |

---

## WP01: Mode Navigation Reorder

**Phase**: 1 | **Risk**: Low | **FR Coverage**: FR-001, FR-002, FR-003

### Subtasks

- [x] T001: Update MODE_ORDER in mode_manager.py to new order with DELIVER
- [x] T002: Add DELIVER to mode_tab_state initialization in mode_manager.py
- [x] T003: Create deliver_mode.py with placeholder content
- [x] T004: Update main_window.py mode_configs and grid columns

### Files

- `src/ui/mode_manager.py` - MODIFY
- `src/ui/main_window.py` - MODIFY
- `src/ui/modes/deliver_mode.py` - NEW

### Acceptance Criteria

- Modes appear in order: Observe, Catalog, Plan, Purchase, Make, Deliver
- Ctrl+1 through Ctrl+6 activate correct modes
- Deliver mode shows placeholder message

---

## WP02: Purchase Mode Tab Reorder

**Phase**: 2 | **Risk**: Low | **FR Coverage**: FR-011

### Subtasks

- [x] T005: Reorder tabview.add() calls in purchase_mode.py
- [x] T006: Verify lazy loading order in activate() method

### Files

- `src/ui/modes/purchase_mode.py` - MODIFY

### Acceptance Criteria

- Purchase tabs appear in order: Inventory, Purchases, Shopping Lists
- All existing tab functionality preserved

---

## WP03: Catalog Menu Restructure

**Phase**: 3 | **Risk**: Medium | **FR Coverage**: FR-004, FR-005, FR-007, FR-008 (FR-009, FR-010 deferred)

### Subtasks

- [x] T007: Create ingredients_group_tab.py with nested tabs
- [x] T008: Create recipes_group_tab.py with nested tabs
- [x] T009: Create packaging_group_tab.py (Food/Bundle split DEFERRED - model lacks distinction)
- [x] T010: Update catalog_mode.py to use 4 group tabs
- [x] T011: Update activate() and refresh_all_tabs() methods
- [x] T012: ~~Verify Finished Goods Food/Bundle filtering~~ DEFERRED per spec update

### Files

- `src/ui/tabs/ingredients_group_tab.py` - NEW
- `src/ui/tabs/recipes_group_tab.py` - NEW
- `src/ui/tabs/packaging_group_tab.py` - NEW
- `src/ui/modes/catalog_mode.py` - MODIFY

### Acceptance Criteria

- 4 groups visible: Ingredients, Materials, Recipes, Packaging
- Each group has correct sub-tabs
- ~~Finished Goods Food/Bundle split~~ DEFERRED - single Finished Goods tab
- All existing tabs accessible and functional

---

## WP04: Tree View Removal

**Phase**: 4 | **Risk**: Low | **FR Coverage**: FR-013

### Subtasks

- [x] T013: Remove _view_mode and view toggle from ingredients_tab.py
- [x] T014: Remove _create_tree_view() method and tree container
- [x] T015: Remove tree-related event handlers and search logic

### Files

- `src/ui/ingredients_tab.py` - MODIFY

### Acceptance Criteria

- No Flat/Tree toggle visible in Ingredients tab
- Grid view displays by default
- IngredientTreeWidget file preserved (used elsewhere)

---

## WP05: Verification & Cleanup

**Phase**: 5 | **Risk**: Low | **FR Coverage**: FR-012, FR-014

### Subtasks

- [x] T016: Verify F042 dashboard compaction is sufficient (FR-012)
- [x] T017: Run full application test suite
- [x] T018: Manual UI testing per Testing Strategy in plan.md

### Files

- No new files (verification only)

### Acceptance Criteria

- No broken "0 count" displays
- All tests pass
- All manual test scenarios verified
- 3-5 additional grid rows visible

---

## Parallelization Notes

**Safe to parallelize:**
- WP01, WP02, WP04 can run concurrently (no file conflicts)

**Must be sequential:**
- WP03 depends on WP01 (needs DeliverMode registered before catalog restructure)
- WP05 depends on WP01-WP04 (verification of all changes)

---

## Implementation Order (Recommended)

1. **Batch 1 (parallel)**: WP01 + WP02 + WP04
2. **Batch 2 (sequential)**: WP03
3. **Batch 3 (verification)**: WP05
