---
work_package_id: WP01
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
title: Core Tab Structure
phase: Phase 1 - Core Tab Structure
lane: "done"
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-11T07:09:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
activity_log: "  - timestamp: \"2026-01-11T15:49:00Z\"\n    lane: \"planned\"\n  \
  \  agent: \"system\"\n    shell_pid: \"47812\"\n    action: \"Auto-repaired lane\
  \ metadata (was: done)\"\n"
---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Core Tab Structure"
phase: "Phase 1 - Core Tab Structure"
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
# Work Package Prompt: WP01 - Core Tab Structure

## Objectives & Success Criteria

- Create new `MaterialsTab` class with 3-tab structure using `CTkTabview`
- Establish inner class pattern for each tab: `MaterialsCatalogTab`, `MaterialProductsTab`, `MaterialUnitsTab`
- Each tab displays an empty grid with correct column headers
- Wire up lazy loading and refresh patterns

**Success**: Materials tab opens with 3 visible sub-tabs; each tab shows an empty grid with correct column headers; refresh propagates to all tabs.

## Context & Constraints

- **Reference**: Copy patterns from `src/ui/ingredients_tab.py` exactly
- **Replace**: Entire `src/ui/materials_tab.py` (backup existing first)
- **No tree view**: Flat grid views only per plan.md D2
- **Grid columns per plan.md D3**:
  - Materials Catalog: l0, l1, name, base_unit
  - Material Products: material, name, inventory, unit_cost, supplier
  - Material Units: material, name, qty_per_unit, available, cost

**Key Files**:
- Target: `src/ui/materials_tab.py` (replace)
- Reference: `src/ui/ingredients_tab.py`
- Spec: `kitty-specs/048-materials-ui-rebuild/spec.md`
- Plan: `kitty-specs/048-materials-ui-rebuild/plan.md`

## Subtasks & Detailed Guidance

### Subtask T001 - Create new MaterialsTab class structure

- **Purpose**: Establish the parent container class that holds the 3-tab structure
- **Steps**:
  1. Rename existing `src/ui/materials_tab.py` to `src/ui/materials_tab_old.py` for reference
  2. Create new `src/ui/materials_tab.py` with imports from ingredients_tab.py
  3. Create `MaterialsTab(ctk.CTkFrame)` class with `__init__` signature matching `IngredientsTab`
  4. Configure grid layout: `grid_columnconfigure(0, weight=1)`, 2 rows (title, tabview)
- **Files**: `src/ui/materials_tab.py`
- **Parallel?**: No (foundation for all other tasks)

### Subtask T002 - Implement CTkTabview with 3 tabs

- **Purpose**: Create the 3-tab container matching spec requirements
- **Steps**:
  1. Create `CTkTabview` widget in `_create_tabview()` method
  2. Add tabs: "Materials Catalog", "Material Products", "Material Units"
  3. Grid tabview to fill available space
- **Files**: `src/ui/materials_tab.py`
- **Parallel?**: No

### Subtask T003 - Create MaterialsCatalogTab inner class (Parallel)

- **Purpose**: Skeleton for Materials Catalog grid view
- **Steps**:
  1. Create inner class `MaterialsCatalogTab` that receives parent tab frame
  2. Configure grid: 4 rows (filter, buttons, grid, status)
  3. Create `ttk.Treeview` with columns: `("l0", "l1", "name", "base_unit")`
  4. Configure headings: "Category (L0)", "Subcategory (L1)", "Material Name", "Default Unit"
  5. Configure column widths: 150, 150, 200, 100
  6. Add vertical scrollbar
- **Files**: `src/ui/materials_tab.py`
- **Parallel?**: Yes (independent inner class)

### Subtask T004 - Create MaterialProductsTab inner class (Parallel)

- **Purpose**: Skeleton for Material Products grid view
- **Steps**:
  1. Create inner class `MaterialProductsTab` that receives parent tab frame
  2. Configure grid: 4 rows (filter, buttons, grid, status)
  3. Create `ttk.Treeview` with columns: `("material", "name", "inventory", "unit_cost", "supplier")`
  4. Configure headings: "Material", "Product Name", "Inventory", "Unit Cost", "Supplier"
  5. Configure column widths: 150, 150, 120, 100, 120
  6. Add vertical scrollbar
- **Files**: `src/ui/materials_tab.py`
- **Parallel?**: Yes (independent inner class)

### Subtask T005 - Create MaterialUnitsTab inner class (Parallel)

- **Purpose**: Skeleton for Material Units grid view
- **Steps**:
  1. Create inner class `MaterialUnitsTab` that receives parent tab frame
  2. Configure grid: 4 rows (filter, buttons, grid, status)
  3. Create `ttk.Treeview` with columns: `("material", "name", "qty_per_unit", "available", "cost")`
  4. Configure headings: "Material", "Unit Name", "Qty/Unit", "Available", "Cost/Unit"
  5. Configure column widths: 150, 150, 80, 80, 100
  6. Add vertical scrollbar
- **Files**: `src/ui/materials_tab.py`
- **Parallel?**: Yes (independent inner class)

### Subtask T006 - Wire up lazy loading and refresh pattern

- **Purpose**: Ensure data loads correctly when tab is selected
- **Steps**:
  1. Add `_data_loaded` flag to `MaterialsTab`
  2. Implement `refresh()` method that calls `refresh()` on each inner tab
  3. Add `refresh()` stub to each inner tab class
  4. Ensure refresh is called when Materials tab is first shown
- **Files**: `src/ui/materials_tab.py`
- **Parallel?**: No (depends on T001-T005)
- **Reference**: See `IngredientsTab.__init__` and `refresh()` pattern

### Subtask T007 - Add status bar to each tab

- **Purpose**: Display item count and filter status
- **Steps**:
  1. Add `_create_status_bar()` method to each inner tab
  2. Create `CTkLabel` at bottom of each tab grid
  3. Add `update_status(message: str)` method to each tab
  4. Initialize with "Ready" or "Loading..."
- **Files**: `src/ui/materials_tab.py`
- **Parallel?**: No (depends on T003-T005)
- **Reference**: See `IngredientsTab._create_status_bar()` at line 462

## Risks & Mitigations

- **Risk**: Breaking existing functionality during replacement
  - **Mitigation**: Preserve current file as `materials_tab_old.py`; test app launch before proceeding
- **Risk**: Import errors from removed dependencies
  - **Mitigation**: Compare imports between old and new file; remove unused, add needed

## Definition of Done Checklist

- [ ] T001: MaterialsTab class created with correct structure
- [ ] T002: CTkTabview displays 3 tabs correctly
- [ ] T003: MaterialsCatalogTab shows grid with 4 column headers
- [ ] T004: MaterialProductsTab shows grid with 5 column headers
- [ ] T005: MaterialUnitsTab shows grid with 5 column headers
- [ ] T006: refresh() method wired and callable
- [ ] T007: Status bar visible on each tab
- [ ] App launches without errors
- [ ] Old materials_tab_old.py preserved for reference

## Review Guidance

- Verify all 3 tabs are visible and selectable
- Verify grid column headers match spec (exact text)
- Verify no console errors on tab switch
- Verify refresh() can be called without error

## Activity Log

- 2026-01-11T07:09:48Z - system - lane=planned - Prompt created.
- 2026-01-11T07:37:47Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-11T13:20:40Z – unknown – lane=for_review – Implementation complete: 3-tab MaterialsTab with MaterialsCatalogTab, MaterialProductsTab, MaterialUnitsTab. All grids have correct columns per spec. Tests pass (1958/1958).
- 2026-01-11T15:37:41Z – agent – lane=doing – Started review via workflow command
- 2026-01-11T15:38:36Z – unknown – lane=done – Review passed: All 7 subtasks verified. 3-tab structure with correct columns, refresh wiring, and status bars.
- 2026-01-11T15:49:54Z – agent – lane=doing – Started review via workflow command
- 2026-01-11T15:50:02Z – unknown – lane=done – Review passed (re-run after validate-tasks --fix reset)
