---
work_package_id: "WP03"
subtasks:
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
title: "UI Layer Multi-Select"
phase: "Phase 2 - UI Layer"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-15T13:35:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - UI Layer Multi-Select

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Replace radio buttons with checkboxes for entity selection
- Add "All" checkbox that toggles all entity checkboxes
- Update entity list to show all 7 entity types
- Export handler processes all selected entities (sequential export)
- Validation prevents export when no entities selected
- Button text changed from "View" to "File"

**Success**: User can select multiple entities (or "All"), click export, and get separate `aug_*.json` files for each selected entity.

## Context & Constraints

**File to modify**: `src/ui/import_export_dialog.py`

**Reference**:
- `kitty-specs/053-context-rich-export-fixes/plan.md` - Implementation approach
- `kitty-specs/053-context-rich-export-fixes/spec.md` - User stories and acceptance criteria

**Dependencies**: WP01 and WP02 must be complete (service methods exist with new names)

**Framework**: CustomTkinter - use `ctk.CTkCheckBox` widgets

## Subtasks & Detailed Guidance

### Subtask T009 - Replace Radio Buttons with Checkboxes

**Purpose**: Enable multi-select instead of single-select.

**Steps**:
1. Open `src/ui/import_export_dialog.py`
2. Find `_setup_context_rich_tab()` method (around line 1633-1691)
3. Remove the `ctk.CTkRadioButton` widgets and `self.view_var` variable
4. Create a dict to hold checkbox variables: `self.context_rich_vars = {}`
5. For each entity type, create a `ctk.BooleanVar` and `ctk.CTkCheckBox`
6. Store vars in the dict with entity key (e.g., `"ingredients"`, `"products"`)

**Files**: `src/ui/import_export_dialog.py`
**Parallel?**: No - foundation for other UI subtasks

**Code pattern**:
```python
# Replace this:
self.view_var = ctk.StringVar(value="ingredients")
views = [("ingredients", "Ingredients..."), ...]
for value, label in views:
    rb = ctk.CTkRadioButton(frame, text=label, variable=self.view_var, value=value)

# With this:
self.context_rich_vars = {}
entities = [
    ("ingredients", "Ingredients (with products, inventory totals, costs)"),
    # ... all 7 entities
]
for key, label in entities:
    var = ctk.BooleanVar(value=False)
    self.context_rich_vars[key] = var
    cb = ctk.CTkCheckBox(frame, text=label, variable=var, command=self._on_entity_checkbox_changed)
    cb.pack(anchor="w", pady=2)
```

### Subtask T010 - Add "All" Checkbox

**Purpose**: Provide quick way to select/deselect all entities.

**Steps**:
1. Create `self.context_rich_all_var = ctk.BooleanVar(value=False)`
2. Create "All" checkbox at TOP of entity list
3. Wire to `_on_all_checkbox_changed` command
4. Add visual separator (horizontal line or spacing) below "All"

**Files**: `src/ui/import_export_dialog.py`
**Parallel?**: No - must be done with T009

**Code pattern**:
```python
# "All" checkbox
self.context_rich_all_var = ctk.BooleanVar(value=False)
self.all_checkbox = ctk.CTkCheckBox(
    frame,
    text="All",
    variable=self.context_rich_all_var,
    command=self._on_all_checkbox_changed
)
self.all_checkbox.pack(anchor="w", pady=(5, 2))

# Separator
separator = ctk.CTkFrame(frame, height=2, fg_color="gray50")
separator.pack(fill="x", pady=5)

# Then individual entity checkboxes...
```

### Subtask T011 - Implement "All" Toggle Logic

**Purpose**: Check/uncheck all entity checkboxes when "All" changes.

**Steps**:
1. Create method `_on_all_checkbox_changed(self)`
2. Get current state of `self.context_rich_all_var`
3. If True: set all entity vars to True
4. If False: set all entity vars to False

**Files**: `src/ui/import_export_dialog.py`
**Parallel?**: No

**Code pattern**:
```python
def _on_all_checkbox_changed(self):
    """Handle All checkbox state change."""
    all_selected = self.context_rich_all_var.get()
    for var in self.context_rich_vars.values():
        var.set(all_selected)
```

### Subtask T012 - Implement Individual Checkbox Sync

**Purpose**: Update "All" checkbox state when individual checkboxes change.

**Steps**:
1. Create method `_on_entity_checkbox_changed(self)`
2. Check if ALL entity checkboxes are currently selected
3. If all selected: set `context_rich_all_var` to True
4. If any unselected: set `context_rich_all_var` to False

**Files**: `src/ui/import_export_dialog.py`
**Parallel?**: No

**Code pattern**:
```python
def _on_entity_checkbox_changed(self):
    """Update All checkbox based on individual selections."""
    all_selected = all(var.get() for var in self.context_rich_vars.values())
    self.context_rich_all_var.set(all_selected)
```

### Subtask T013 - Update Entity List to 7 Items

**Purpose**: Include all entity types in selection.

**Steps**:
1. Update the entities list to include all 7 types:
   - ingredients, products, recipes, finished_units, finished_goods, materials, material_products
2. Provide descriptive labels for each

**Files**: `src/ui/import_export_dialog.py`
**Parallel?**: No - part of T009 implementation

**Entity list**:
```python
entities = [
    ("ingredients", "Ingredients (with products, inventory totals, costs)"),
    ("products", "Products (with ingredient context, supplier, inventory)"),
    ("recipes", "Recipes (with ingredients, computed costs)"),
    ("finished_units", "Finished Units (with recipe, yield information)"),
    ("finished_goods", "Finished Goods (with components, assembly context)"),
    ("materials", "Materials (with hierarchy paths, products)"),
    ("material_products", "Material Products (with material context, supplier)"),
]
```

### Subtask T014 - Update Export Handler for Multi-Select

**Purpose**: Process all selected entities sequentially.

**Steps**:
1. Find `_export_context_rich()` method (around line 1798-1850)
2. Replace single-entity logic with iteration over selected entities
3. For each selected entity, call the corresponding service method
4. Collect results and show summary message

**Files**: `src/ui/import_export_dialog.py`
**Parallel?**: No

**Code pattern**:
```python
def _export_context_rich(self):
    """Export selected context-rich entity types."""
    # Get selected entities
    selected = [key for key, var in self.context_rich_vars.items() if var.get()]

    if not selected:
        # Show validation error (T015)
        return

    # Map entity keys to service methods
    export_methods = {
        "ingredients": self.export_service.export_ingredients_context_rich,
        "products": self.export_service.export_products_context_rich,
        "recipes": self.export_service.export_recipes_context_rich,
        "finished_units": self.export_service.export_finished_units_context_rich,
        "finished_goods": self.export_service.export_finished_goods_context_rich,
        "materials": self.export_service.export_materials_context_rich,
        "material_products": self.export_service.export_material_products_context_rich,
    }

    results = []
    for entity_key in selected:
        method = export_methods.get(entity_key)
        if method:
            result = method(output_dir)
            results.append((entity_key, result))

    # Show summary message
    self._show_export_summary(results)
```

### Subtask T015 - Add Validation for Selection

**Purpose**: Prevent export when no entities selected.

**Steps**:
1. In `_export_context_rich()`, check if any entities are selected
2. If none selected, show error message using messagebox
3. Return early without attempting export

**Files**: `src/ui/import_export_dialog.py`
**Parallel?**: No - part of T014

**Code pattern**:
```python
if not selected:
    messagebox.showwarning(
        "No Selection",
        "Please select at least one entity type to export."
    )
    return
```

### Subtask T016 - Change Button Text

**Purpose**: Use "File" instead of "View" for consistency.

**Steps**:
1. Find the export button creation in `_setup_context_rich_tab()`
2. Change text from "Export Context-Rich View..." to "Export Context-Rich File..."

**Files**: `src/ui/import_export_dialog.py`
**Parallel?**: No - simple change

**Note**: Search for `"Export Context-Rich View"` to find the button.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| "All" checkbox behavior confusing | Follow standard pattern; behavior matches user expectations |
| Export handler errors on individual entities | Handle errors gracefully, continue with remaining entities, report failures |
| Performance with many entities | Sequential export is acceptable per user; no parallelism needed |

## Definition of Done Checklist

- [ ] Radio buttons replaced with checkboxes
- [ ] "All" checkbox added at top with separator
- [ ] Clicking "All" checks/unchecks all entity checkboxes
- [ ] Individual checkbox changes update "All" state correctly
- [ ] All 7 entity types listed with descriptive labels
- [ ] Export handler processes all selected entities
- [ ] Validation message shown when no entities selected
- [ ] Button text reads "Export Context-Rich File..."
- [ ] Application launches and export dialog displays correctly
- [ ] Multi-select export produces correct `aug_*.json` files

## Review Guidance

- Verify "All" checkbox toggle works in both directions
- Verify individual checkbox changes sync with "All" state
- Test exporting 1, 3, and all 7 entities
- Verify validation prevents empty export
- Check button text is correct

## Activity Log

- 2026-01-15T13:35:00Z - system - lane=planned - Prompt created.
- 2026-01-15T19:16:29Z – claude – lane=doing – Starting WP03 implementation
- 2026-01-15T19:18:35Z – claude – lane=for_review – Implemented T009-T016: Radio buttons replaced with checkboxes, All checkbox with toggle logic, 7 entity types listed, multi-select export handler, validation for empty selection
- 2026-01-15T21:11:40Z – claude – lane=doing – Started review via workflow command
- 2026-01-15T21:15:36Z – claude – lane=done – Review passed: Checkboxes with All toggle, 7 entity types, multi-select export handler, validation message, correct button text
