---
work_package_id: WP06
subtasks:
- T050
- T051
- T052
- T053
- T054
- T055
- T056
- T057
- T058
- T059
title: Material Units Tab
phase: Phase 4 - Material Units Tab
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
work_package_id: "WP06"
subtasks:
  - "T050"
  - "T051"
  - "T052"
  - "T053"
  - "T054"
  - "T055"
  - "T056"
  - "T057"
  - "T058"
  - "T059"
title: "Material Units Tab"
phase: "Phase 4 - Material Units Tab"
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
# Work Package Prompt: WP06 - Material Units Tab

## Objectives & Success Criteria

- Implement Material Units tab with grid and filters
- Grid displays Material/Name/Qty per Unit/Available/Cost columns
- Available and Cost computed from service
- Add/Edit unit functionality

**Note**: This work package implements the Material Units tab (third tab per plan.md D1). While spec.md User Story 6 focuses on "Adjust Inventory", that functionality is covered by WP05 (T047-T048). This WP covers the Material Units management which enables unit-based inventory tracking.

**Success**: User Story 6 acceptance scenarios pass:
1. Adjust dialog shows current inventory
2. Adjustment amount and reason required
3. Adjustment updates inventory correctly

Plus: Unit grid displays correctly, add/edit works.

## Context & Constraints

- **Grid columns per plan.md D3**: material, name, qty_per_unit, available, cost
- **Computed values**:
  - Available: `material_unit_service.get_available_inventory(unit.id)`
  - Cost: `material_unit_service.get_current_cost(unit.id)`
- **Services**: `material_unit_service.list_units()`, `.create_unit()`, `.update_unit()`

**Key Files**:
- Target: `src/ui/materials_tab.py` (MaterialUnitsTab class)
- Services: `src/services/material_unit_service.py`
- Reference: Current `materials_tab.py` units section

## Subtasks & Detailed Guidance

### Subtask T050 - Implement units grid columns

- **Purpose**: Configure grid with correct columns
- **Steps**:
  1. Define columns: `("material", "name", "qty_per_unit", "available", "cost")`
  2. Configure headings: "Material", "Unit Name", "Qty/Unit", "Available", "Cost/Unit"
  3. Set widths: 150, 150, 80, 80, 100
  4. Bind selection and double-click events
- **Files**: `src/ui/materials_tab.py`

### Subtask T051 - Implement _load_all_units

- **Purpose**: Fetch units across all materials
- **Steps**:
  1. Create `_load_all_units()` method
  2. Get all materials (iterate categories -> subcategories -> materials)
  3. For each material: `material_unit_service.list_units(material.id)`
  4. Build list of unit dicts with: id, name, material_name, material_id, quantity_per_unit
  5. Store in `self.units`
- **Files**: `src/ui/materials_tab.py`

### Subtask T052 - Implement available inventory computation

- **Purpose**: Get available inventory for each unit
- **Steps**:
  1. For each unit in display: `material_unit_service.get_available_inventory(unit.id)`
  2. Format as integer or float with 1 decimal
  3. Handle exceptions (return 0 on error)
- **Files**: `src/ui/materials_tab.py`
- **Notes**: Called per-row; may be slow with many units

### Subtask T053 - Implement cost computation

- **Purpose**: Get current cost for each unit
- **Steps**:
  1. For each unit in display: `material_unit_service.get_current_cost(unit.id)`
  2. Format as `f"${cost:.4f}"` or "-" if None
  3. Handle exceptions (return "-" on error)
- **Files**: `src/ui/materials_tab.py`

### Subtask T054 - Implement units _update_display

- **Purpose**: Apply filters and populate grid
- **Steps**:
  1. Clear existing grid items
  2. Call `_apply_filters()` to get filtered units
  3. For each unit:
     - Get available (T052) and cost (T053)
     - Insert row: (material, name, qty_per_unit, available, cost)
  4. Use unit.id as row iid
  5. Update status bar
- **Files**: `src/ui/materials_tab.py`

### Subtask T055 - Implement units Material filter dropdown

- **Purpose**: Filter units by linked material
- **Steps**:
  1. Create `_load_material_dropdown()` method
  2. Build list of all material names
  3. Add "All Materials" option at start
  4. Create `CTkOptionMenu` with values
  5. Create `_material_map: Dict[str, int]`
  6. Implement `_on_material_filter_change()`
  7. In `_apply_filters()`, filter by selected material
- **Files**: `src/ui/materials_tab.py`

### Subtask T056 - Implement units search filter (Parallel)

- **Purpose**: Filter units by name
- **Steps**:
  1. Add search entry in filter frame
  2. Bind `<KeyRelease>` to `_on_search()`
  3. In `_apply_filters()`, filter by normalized search text
- **Files**: `src/ui/materials_tab.py`
- **Parallel?**: Yes (independent of material filter)

### Subtask T057 - Implement units selection and buttons

- **Purpose**: Track selection and manage button states
- **Steps**:
  1. Add state: `selected_unit_id: Optional[int]`
  2. Implement `_on_select()` handler
  3. Implement `_on_double_click()` handler
  4. Create action buttons frame with:
     - Add Unit (always enabled)
     - Edit (selection-dependent)
  5. Implement `_enable_selection_buttons()`, `_disable_selection_buttons()`
- **Files**: `src/ui/materials_tab.py`

### Subtask T058 - Create MaterialUnitFormDialog

- **Purpose**: Dialog for add/edit material units
- **Steps**:
  1. Create `MaterialUnitFormDialog(ctk.CTkToplevel)`
  2. Accept `parent`, `unit: Optional[dict]`, `title`, `material_id: Optional[int]`
  3. Form fields:
     - Material dropdown (required, pre-selected if material_id provided)
     - Unit Name entry (required)
     - Quantity per Unit entry (required, positive numeric)
     - Description entry (optional)
  4. Use modal pattern
  5. Implement validation
- **Files**: `src/ui/materials_tab.py`
- **Reference**: Current `UnitDialog` class

### Subtask T059 - Wire unit add/edit handlers

- **Purpose**: Connect buttons to dialogs
- **Steps**:
  1. Implement `_add_unit()`:
     - Get selected material from grid if any
     - Open `MaterialUnitFormDialog(self, material_id=selected_material_id)`
     - If result: `material_unit_service.create_unit(...)`
     - Refresh grid, show success
  2. Implement `_edit_unit()`:
     - Get unit data by ID
     - Open dialog with data
     - If result: `material_unit_service.update_unit(...)`
     - Refresh grid, show success
  3. Wire to Add Unit and Edit buttons
- **Files**: `src/ui/materials_tab.py`

## Risks & Mitigations

- **Risk**: Performance with many units (computed columns)
  - **Mitigation**: Expected scale is small (~10-50 units); if slow, cache values
- **Risk**: Service methods raise exceptions
  - **Mitigation**: Wrap in try/except, display "-" on error

## Definition of Done Checklist

- [ ] T050: Grid displays 5 columns with correct headers
- [ ] T051: All units load across all materials
- [ ] T052: Available shows computed inventory
- [ ] T053: Cost shows computed cost or "-"
- [ ] T054: Grid populates correctly
- [ ] T055: Material dropdown filters units
- [ ] T056: Search filters by unit name
- [ ] T057: Selection tracked, buttons enable/disable
- [ ] T058: Unit dialog opens with all fields
- [ ] T059: Add/Edit wired and working
- [ ] User Story 6 acceptance scenarios pass

## Review Guidance

- Verify computed Available and Cost values are correct
- Verify material filter shows only units for selected material
- Verify unit dialog validates required fields
- Verify grid refreshes after add/edit

## Activity Log

- 2026-01-11T07:09:48Z - system - lane=planned - Prompt created.
- 2026-01-11T14:13:33Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-11T14:21:01Z – unknown – lane=for_review – Implementation complete: MaterialUnitFormDialog with add/edit functionality. Handlers wired. Tests pass (1958/1958).
- 2026-01-11T15:40:33Z – agent – lane=doing – Started review via workflow command
- 2026-01-11T15:40:49Z – unknown – lane=done – Review passed: All 10 subtasks verified. MaterialUnitsTab with computed values, material filter, and MaterialUnitFormDialog.
- 2026-01-11T15:50:28Z – agent – lane=doing – Started review via workflow command
- 2026-01-11T15:50:33Z – unknown – lane=done – Review passed (re-run after validate-tasks --fix reset)
