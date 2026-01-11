---
work_package_id: WP03
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
- T026
- T027
- T028
- T029
title: Material Form Dialog
phase: Phase 2 - Materials Catalog Tab
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
work_package_id: "WP03"
subtasks:
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
title: "Material Form Dialog"
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
# Work Package Prompt: WP03 - Material Form Dialog

## Objectives & Success Criteria

- Implement `MaterialFormDialog` for add/edit materials
- Cascading L0/L1 dropdowns in form
- CRUD operations wired to grid
- Delete with confirmation

**Success**: User Story 2 acceptance scenarios 1-5 pass:
1. Add Material opens dialog with Name, L0, L1, Default Unit, Notes fields
2. L0 selection cascades to L1 dropdown
3. Save creates material and it appears in grid
4. Edit/double-click opens pre-populated dialog
5. Delete prompts confirmation and removes material

## Context & Constraints

- **Reference**: Copy dialog pattern from `IngredientFormDialog` (lines 1048-1741)
- **Modal pattern**: `withdraw()` -> build UI -> `deiconify()` -> `grab_set()`
- **Services**: `material_catalog_service.create_material()`, `.update_material()`, `.delete_material()`
- **Base Unit options**: `["linear_inches", "each", "sheets", "sq_inches"]`

**Key Files**:
- Target: `src/ui/materials_tab.py` (MaterialFormDialog class)
- Reference: `src/ui/ingredients_tab.py` (IngredientFormDialog)
- Services: `src/services/material_catalog_service.py`

## Subtasks & Detailed Guidance

### Subtask T020 - Create MaterialFormDialog class

- **Purpose**: Modal dialog for add/edit materials
- **Steps**:
  1. Create `MaterialFormDialog(ctk.CTkToplevel)` class
  2. Accept `parent`, `material: Optional[dict] = None`, `title: str = "Add Material"`
  3. Store `self.material`, `self.result = None`, `self.deleted = False`
  4. Configure window: title, geometry "500x400", resizable False
  5. Use modal pattern: `withdraw()`, build UI, `deiconify()`, `grab_set()`
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 1055-1112

### Subtask T021 - Implement form fields

- **Purpose**: Create form layout with all required fields
- **Steps**:
  1. Create form frame with `grid_columnconfigure(1, weight=1)`
  2. Add fields:
     - Name: `CTkEntry` (required) - editable only when adding
     - L0 Category: `CTkComboBox` (dropdown)
     - L1 Subcategory: `CTkComboBox` (dropdown, cascading)
     - Base Unit: `CTkOptionMenu` with values `["linear_inches", "each", "sheets", "sq_inches"]`
     - Notes: `CTkEntry` (optional)
  3. Label column width ~120px
  4. Add required field indicators ("*")
  5. **FR-016**: Display computed level (always "L2 - Material" since materials always have L1 parent subcategory)
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 1114-1304

### Subtask T022 - Implement _build_l0_options

- **Purpose**: Populate L0 dropdown with categories
- **Steps**:
  1. Create `_build_l0_options() -> Dict[str, int]` method
  2. Call `material_catalog_service.list_categories()`
  3. Return dict mapping category name to category ID
  4. Store in `self._l0_options`
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 1344-1357

### Subtask T023 - Implement _on_l0_change cascade

- **Purpose**: Populate L1 when L0 changes
- **Steps**:
  1. Implement `_on_l0_change(value: str)` callback
  2. If "(None)" or not in options: disable L1, set "(Select L0 first)"
  3. Else: get subcategories for selected category
  4. Populate L1 dropdown with subcategory names
  5. Enable L1 dropdown
  6. Store in `self._l1_options: Dict[str, int]`
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 1446-1477

### Subtask T024 - Implement _populate_form

- **Purpose**: Pre-fill form when editing
- **Steps**:
  1. Create `_populate_form()` method
  2. If `self.material` is None, return
  3. Set name (read-only in edit mode - show as label)
  4. Look up category/subcategory from material's hierarchy
  5. Set L0 dropdown, trigger cascade, set L1 dropdown
  6. Set base_unit dropdown
  7. Set notes if present
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 1486-1543

### Subtask T025 - Implement _validate_and_save

- **Purpose**: Validate required fields and save
- **Steps**:
  1. Create `_save()` method
  2. Get name (from entry if adding, from stored if editing)
  3. Validate name is not empty
  4. Get selected subcategory_id from L1 dropdown
  5. Validate subcategory selected (materials must have L1 parent)
  6. Get base_unit from dropdown
  7. Build result dict: `{"name": ..., "subcategory_id": ..., "base_unit": ...}`
  8. Store in `self.result` and call `self.destroy()`
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 1584-1651

### Subtask T026 - Implement Delete with confirmation

- **Purpose**: Delete material with confirmation prompt
- **Steps**:
  1. Add Delete button (only in edit mode) - left side, red color
  2. Create `_delete()` method
  3. Show confirmation dialog: "Are you sure you want to delete '{name}'?"
  4. If confirmed: call `material_catalog_service.delete_material(material_id)`
  5. Set `self.deleted = True`, destroy dialog
  6. Handle exception if material has products (show error)
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 1658-1702

### Subtask T027 - Wire _add_material handler

- **Purpose**: Open dialog and create material
- **Steps**:
  1. Add "Add Material" button in MaterialsCatalogTab action buttons
  2. Create `_add_material()` method
  3. Open `MaterialFormDialog(self, title="Add Material")`
  4. Call `self.wait_window(dialog)`
  5. If `dialog.result`: call `material_catalog_service.create_material()`
  6. Call `self.refresh()` and show success message
  7. Handle ValidationError, show error message
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 857-884

### Subtask T028 - Wire _edit_material handler

- **Purpose**: Open dialog with existing data and update
- **Steps**:
  1. Create `_edit_material()` method
  2. Get material data by ID from service
  3. Open `MaterialFormDialog(self, material=data, title="Edit Material")`
  4. Call `self.wait_window(dialog)`
  5. Check `dialog.deleted` - if True, refresh and return
  6. If `dialog.result`: call `material_catalog_service.update_material()`
  7. Call `self.refresh()` and show success message
- **Files**: `src/ui/materials_tab.py`
- **Reference**: `ingredients_tab.py` lines 886-952

### Subtask T029 - Wire delete flow

- **Purpose**: Handle delete from dialog callback
- **Steps**:
  1. In `_edit_material()`, check `dialog.deleted` flag after wait_window
  2. If deleted: clear selection, refresh grid, update status
  3. Error handling if delete fails (material has products)
- **Files**: `src/ui/materials_tab.py`
- **Notes**: Delete is handled inside dialog; parent just needs to refresh

## Risks & Mitigations

- **Risk**: Delete fails on material with products
  - **Mitigation**: Service raises exception; show user-friendly error message
- **Risk**: L1 cascade doesn't populate correctly
  - **Mitigation**: Copy pattern exactly from ingredients; test with multiple categories

## Definition of Done Checklist

- [ ] T020: Dialog opens as modal with correct title
- [ ] T021: All form fields present with correct layout
- [ ] T022: L0 dropdown populated with categories
- [ ] T023: L1 cascades correctly when L0 changes
- [ ] T024: Edit mode pre-populates all fields
- [ ] T025: Save validates and creates/updates material
- [ ] T026: Delete prompts and removes material
- [ ] T027: Add Material button opens dialog and creates
- [ ] T028: Edit button opens pre-populated dialog
- [ ] T029: Delete from dialog refreshes grid
- [ ] All User Story 2 acceptance scenarios pass

## Review Guidance

- Verify L0/L1 cascade works in both add and edit modes
- Verify required field validation shows error
- Verify Delete confirmation dialog appears
- Verify grid refreshes after all CRUD operations

## Activity Log

- 2026-01-11T07:09:48Z - system - lane=planned - Prompt created.
- 2026-01-11T13:43:32Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-11T13:55:34Z – unknown – lane=for_review – Implementation complete: MaterialFormDialog with cascading L0/L1 dropdowns, add/edit/delete functionality. Tests pass (1958/1958).
- 2026-01-11T15:39:10Z – agent – lane=doing – Started review via workflow command
- 2026-01-11T15:39:31Z – unknown – lane=done – Review passed: All 10 subtasks verified. MaterialFormDialog with cascading L0/L1, CRUD operations wired. Cursor fix applied: name editable, base_unit disabled in edit mode.
- 2026-01-11T15:50:10Z – agent – lane=doing – Started review via workflow command
- 2026-01-11T15:50:15Z – unknown – lane=done – Review passed (re-run after validate-tasks --fix reset)
