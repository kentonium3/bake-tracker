---
work_package_id: "WP02"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
title: "Materials Catalog Grid & Filters"
phase: "Phase 2 - Materials Catalog Tab"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-11T07:09:48Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Materials Catalog Grid & Filters

## Objectives & Success Criteria

- Implement full Materials Catalog tab matching Ingredients pattern
- Grid displays materials with L0/L1/Name/Unit columns
- Cascading L0/L1 category filters work correctly
- Search, level filter, and Clear button functional
- Column header sorting works

**Success**: User Story 1 acceptance scenarios 1-6 pass:
1. Grid shows Category (L0), Subcategory (L1), Material Name, Default Unit columns
2. Search box filters materials by name in real-time
3. L0 dropdown filters and populates L1 with subcategories
4. L1 dropdown filters to subcategory
5. (Skip - no tree view per plan)
6. Clear resets all filters

## Context & Constraints

- **Reference**: Copy filter patterns from `src/ui/ingredients_tab.py` lines 127-212
- **Services**: Use `material_catalog_service.list_categories()`, `.list_subcategories()`, `.list_materials()`
- **Hierarchy display**: Build L0/L1 display values from hierarchy (materials are L2)
- **No tree view**: Flat grid only per plan.md D2

**Key Files**:
- Target: `src/ui/materials_tab.py` (MaterialsCatalogTab class)
- Reference: `src/ui/ingredients_tab.py`
- Services: `src/services/material_catalog_service.py`

## Subtasks & Detailed Guidance

### Subtask T008 - Implement grid columns

- **Purpose**: Configure grid with correct columns and widths
- **Steps**:
  1. Define columns tuple: `("l0", "l1", "name", "base_unit")`
  2. Configure headings with click-to-sort callbacks
  3. Set column widths: l0=150, l1=150, name=200, base_unit=100
  4. Bind `<<TreeviewSelect>>` and `<Double-1>` events
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 257-294

### Subtask T009 - Implement _load_all_materials

- **Purpose**: Fetch all materials across all subcategories
- **Steps**:
  1. Create `_load_all_materials()` method
  2. Get all categories via `material_catalog_service.list_categories()`
  3. For each category, get subcategories via `.list_subcategories(cat.id)`
  4. For each subcategory, get materials via `.list_materials(subcat.id)`
  5. Build list of material dicts with id, name, base_unit, category_id, subcategory_id
  6. Store in `self.materials` list
- **Files**: `src/ui/materials_tab.py`
- **Notes**: May need to capture category/subcategory names for display

### Subtask T010 - Implement _build_hierarchy_cache

- **Purpose**: Map material ID to L0/L1 display values for grid
- **Steps**:
  1. Create `_build_hierarchy_cache()` returning `Dict[int, Dict[str, str]]`
  2. For each material, store `{"l0": category_name, "l1": subcategory_name}`
  3. Cache is rebuilt on refresh
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 333-380

### Subtask T011 - Implement _update_display

- **Purpose**: Apply filters and populate grid
- **Steps**:
  1. Clear existing grid items
  2. Rebuild hierarchy cache
  3. Call `_apply_filters()` to get filtered list
  4. For each material, insert row with (l0, l1, name, base_unit) values
  5. Restore selection if still present
  6. Update status bar with count
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 533-602

### Subtask T012 - Implement search filter (Parallel)

- **Purpose**: Filter materials by name in real-time
- **Steps**:
  1. Add search entry widget in filter frame
  2. Bind `<KeyRelease>` to `_on_search()` handler
  3. In `_apply_filters()`, filter by normalized search text
  4. Use diacritical normalization (copy `normalize_for_search` function)
- **Files**: `src/ui/materials_tab.py`
- **Parallel?**: Yes (independent of dropdown filters)
- **Reference**: `ingredients_tab.py` lines 16-35, 619-627

### Subtask T013 - Implement L0 cascading dropdown

- **Purpose**: Filter by root category and populate L1
- **Steps**:
  1. Create `_load_filter_data()` to populate L0 dropdown from categories
  2. Create `_l0_map: Dict[str, dict]` mapping category name to data
  3. Add L0 dropdown with "All Categories" default
  4. Implement `_on_l0_filter_change()`:
     - If "All Categories": disable L1, clear L1 map
     - Else: get subcategories, populate L1 dropdown, enable it
  5. Use `_updating_filters` re-entry guard
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 502-524, 734-765

### Subtask T014 - Implement L1 cascading dropdown

- **Purpose**: Filter by subcategory
- **Steps**:
  1. Add L1 dropdown with "All" default, initially disabled
  2. Create `_l1_map: Dict[str, dict]` mapping subcategory name to data
  3. Implement `_on_l1_filter_change()` to trigger display update
  4. In `_apply_filters()`, filter by selected L1 subcategory
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 767-775

### Subtask T015 - Implement level filter dropdown

- **Purpose**: Filter by hierarchy level
- **Steps**:
  1. Add level filter dropdown with options:
     - "All Levels", "Categories (L0)", "Subcategories (L1)", "Materials (L2)"
  2. Implement `_on_level_filter_change()` handler
  3. In `_apply_filters()`, filter by hierarchy level (0, 1, or 2)
- **Files**: `src/ui/materials_tab.py`
- **Notes**: Materials are L2, their parents are L1/L0. Filter shows materials with matching level.
- **Reference**: `ingredients_tab.py` lines 177-191, 730-732

### Subtask T016 - Implement Clear button

- **Purpose**: Reset all filters to defaults
- **Steps**:
  1. Add Clear button at end of filter frame
  2. Implement `_clear_filters()`:
     - Clear search entry
     - Reset L0 to "All Categories"
     - Reset L1 to "All", disable it
     - Reset level filter to "All Levels"
     - Use `_updating_filters` guard
  3. Call `_update_display()`
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 794-824

### Subtask T017 - Implement column header sorting

- **Purpose**: Click column header to sort
- **Steps**:
  1. Add `sort_column` and `sort_ascending` state variables
  2. Implement `_on_header_click(sort_key)` handler
  3. Toggle ascending/descending on same column click
  4. In `_apply_filters()`, sort filtered list by sort_key
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 324-331, 630-667

### Subtask T018 - Implement selection handling

- **Purpose**: Track selected material and enable edit
- **Steps**:
  1. Add `selected_material_id: Optional[int]` state
  2. Implement `_on_select()` for `<<TreeviewSelect>>` event
  3. Implement `_on_double_click()` for `<Double-1>` event (opens edit)
  4. Update `selected_material_id` on selection
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 382-398

### Subtask T019 - Implement button state management

- **Purpose**: Enable/disable Edit button based on selection
- **Steps**:
  1. Create Edit button in action buttons frame (initially disabled)
  2. Implement `_enable_selection_buttons()` - enables Edit
  3. Implement `_disable_selection_buttons()` - disables Edit, clears selection
  4. Call enable on selection, disable on deselection
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 848-856

## Risks & Mitigations

- **Risk**: Service API doesn't return hierarchy data as expected
  - **Mitigation**: Services already work; verify method signatures in `material_catalog_service.py`
- **Risk**: Cascading filter causes infinite loop
  - **Mitigation**: Use `_updating_filters` re-entry guard (copy from ingredients)

## Definition of Done Checklist

- [ ] T008: Grid displays 4 columns with correct headers
- [ ] T009: All materials load from database
- [ ] T010: L0/L1 values display correctly in grid
- [ ] T011: Grid populates with materials
- [ ] T012: Search filters by name in real-time
- [ ] T013: L0 dropdown filters and cascades to L1
- [ ] T014: L1 dropdown filters materials
- [ ] T015: Level filter works (All, L0, L1, L2)
- [ ] T016: Clear button resets all filters
- [ ] T017: Column headers sort on click
- [ ] T018: Selection tracked correctly
- [ ] T019: Edit button enables/disables with selection
- [ ] All User Story 1 acceptance scenarios pass

## Review Guidance

- Verify cascading filter behavior: L0 change populates L1
- Verify Clear resets all filters including search
- Verify sorting works on all columns
- Verify status bar shows correct count

## Activity Log

- 2026-01-11T07:09:48Z - system - lane=planned - Prompt created.
- 2026-01-11T13:27:47Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-11T13:43:20Z – unknown – lane=for_review – Implementation complete: Added column header sorting to all three tabs (MaterialsCatalogTab, MaterialProductsTab, MaterialUnitsTab). All filters and grids working. Tests pass (1958/1958).
- 2026-01-11T15:38:43Z – agent – lane=doing – Started review via workflow command
- 2026-01-11T15:39:04Z – unknown – lane=done – Review passed: All 12 subtasks verified. Cascading L0/L1 filters, level filter, search, sorting, and selection handling all implemented.
