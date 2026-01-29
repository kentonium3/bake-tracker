---
work_package_id: WP04
title: UI – yield_type Dropdown
lane: "for_review"
dependencies: [WP02]
base_branch: 083-dual-yield-recipe-output-support-WP02
base_commit: 9fbd6fa7c444ee009fa1e3a150e27f381f400fa2
created_at: '2026-01-29T17:34:12.053054+00:00'
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - Integration
assignee: ''
agent: ''
shell_pid: "73866"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-29T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – UI – yield_type Dropdown

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you begin addressing feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP02 - branch from WP02 completion
spec-kitty implement WP04 --base WP02
```

**Note**: WP04 can run in parallel with WP03 after WP02 completes.

---

## Objectives & Success Criteria

Add yield_type dropdown to recipe form; update displays to show yield_type:

- [ ] YieldTypeRow component has yield_type dropdown
- [ ] Column headers include "Type" column
- [ ] Form validation requires yield_type selection
- [ ] Saving persists yield_type correctly
- [ ] Recipe detail view shows yield_type
- [ ] Data table shows yield_type in yield info column

**Success metrics**:
- User can select "EA" or "SERVING" for each finished unit
- Default selection is "SERVING"
- yield_type value persists after save
- Existing recipes display correctly (all show "SERVING")

---

## Context & Constraints

**Reference documents**:
- `kitty-specs/083-dual-yield-recipe-output-support/research.md` - UI patterns (Q5)
- `.kittify/memory/constitution.md` - User-centric design principles

**Current YieldTypeRow layout** (research.md Q5):
```
| Name (display_name) | Unit (item_unit) | Qty (items_per_batch) | Remove |
```

**New layout**:
```
| Name | Unit | Type (EA/SERVING) | Qty | Remove |
```

**Current grid configuration**:
```python
self.grid_columnconfigure(0, weight=3)  # Name (wider)
self.grid_columnconfigure(1, weight=1)  # Unit
self.grid_columnconfigure(2, weight=1)  # Quantity
self.grid_columnconfigure(3, weight=0)  # Remove button
```

**New grid configuration** (add column 2 for Type, shift Qty to 3, Remove to 4):
```python
self.grid_columnconfigure(0, weight=3)  # Name (wider)
self.grid_columnconfigure(1, weight=1)  # Unit
self.grid_columnconfigure(2, weight=1)  # Type (NEW)
self.grid_columnconfigure(3, weight=1)  # Quantity
self.grid_columnconfigure(4, weight=0)  # Remove button
```

---

## Subtasks & Detailed Guidance

### Subtask T015 – Add yield_type dropdown to YieldTypeRow component

**Purpose**: Allow user to select yield_type for each finished unit.

**Steps**:
1. Open `src/ui/forms/recipe_form.py`
2. Locate the `YieldTypeRow` class (around line 392)
3. Add `yield_type` parameter to `__init__`:

```python
def __init__(
    self,
    parent,
    remove_callback,
    finished_unit_id: Optional[int] = None,
    display_name: str = "",
    item_unit: str = "",
    items_per_batch: int = 1,
    yield_type: str = "SERVING",  # NEW PARAMETER
    readonly_structure: bool = False,
):
```

4. Create the dropdown widget after the unit entry:

```python
# yield_type dropdown (NEW)
self.yield_type_dropdown = ctk.CTkOptionMenu(
    self,
    values=["SERVING", "EA"],
    width=100,
)
self.yield_type_dropdown.set(yield_type)
self.yield_type_dropdown.grid(row=0, column=2, padx=5, pady=2, sticky="ew")

# Handle readonly for variants
if readonly_structure:
    self.yield_type_dropdown.configure(state="disabled", fg_color="gray25")
```

5. Update `get_data()` method to include yield_type:

```python
def get_data(self) -> Optional[Dict[str, Any]]:
    name = self.name_entry.get().strip()
    unit = self.unit_entry.get().strip()
    quantity_str = self.quantity_entry.get().strip()
    yield_type = self.yield_type_dropdown.get()  # NEW

    # ... existing validation ...

    return {
        "id": self.finished_unit_id,
        "display_name": name,
        "item_unit": unit,
        "items_per_batch": items_per_batch,
        "yield_type": yield_type,  # NEW
    }
```

**Files**: `src/ui/forms/recipe_form.py`

**Notes**:
- Default to "SERVING" (most common case)
- "SERVING" listed first as recommended option
- Handle readonly_structure for variant recipes

---

### Subtask T016 – Update grid configuration and column headers

**Purpose**: Adjust layout to accommodate the new Type column.

**Steps**:
1. In `YieldTypeRow.__init__`, update grid configuration:

```python
# Configure columns (Name | Unit | Type | Qty | Remove)
self.grid_columnconfigure(0, weight=3)  # Name (wider)
self.grid_columnconfigure(1, weight=1)  # Unit
self.grid_columnconfigure(2, weight=1)  # Type (NEW)
self.grid_columnconfigure(3, weight=1)  # Quantity
self.grid_columnconfigure(4, weight=0)  # Remove button
```

2. Update the quantity entry grid position:

```python
# Move quantity to column 3
self.quantity_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
```

3. Update the remove button grid position:

```python
# Move remove button to column 4
self.remove_button.grid(row=0, column=4, padx=5, pady=2)
```

4. In `_create_yield_types_section()` (around line 783), update column labels:

```python
# Column labels header
labels_frame.grid_columnconfigure(0, weight=3)  # Name
labels_frame.grid_columnconfigure(1, weight=1)  # Unit
labels_frame.grid_columnconfigure(2, weight=1)  # Type (NEW)
labels_frame.grid_columnconfigure(3, weight=1)  # Qty
labels_frame.grid_columnconfigure(4, weight=0)  # Spacer

name_label = ctk.CTkLabel(labels_frame, text="Finished Unit Name", font=ctk.CTkFont(size=11))
name_label.grid(row=0, column=0, sticky="w", padx=5)

unit_label = ctk.CTkLabel(labels_frame, text="Unit", font=ctk.CTkFont(size=11))
unit_label.grid(row=0, column=1, sticky="w", padx=5)

type_label = ctk.CTkLabel(labels_frame, text="Type", font=ctk.CTkFont(size=11))  # NEW
type_label.grid(row=0, column=2, sticky="w", padx=5)

qty_label = ctk.CTkLabel(labels_frame, text="Qty/Batch", font=ctk.CTkFont(size=11))
qty_label.grid(row=0, column=3, sticky="w", padx=5)
```

**Files**: `src/ui/forms/recipe_form.py`

**Notes**:
- Keep consistent spacing with padx=5
- Labels should align with the row widgets below them

---

### Subtask T017 – Update form validation for yield_type

**Purpose**: Ensure yield_type is always selected (though dropdown should prevent empty).

**Steps**:
1. In `_validate_form()` method (around line 1424), the existing validation already checks that `get_data()` returns valid data
2. Since the dropdown always has a selection, no additional validation is needed for yield_type specifically
3. However, for belt-and-suspenders safety, add a check:

```python
# In _validate_form(), within the yield_types validation loop
for idx, row in enumerate(self.yield_type_rows):
    row_data = row.get_data()
    if row_data:
        # Validate yield_type is present
        if not row_data.get("yield_type"):
            show_error(
                "Validation Error",
                f"Yield type row {idx + 1}: Type selection is required.",
                parent=self,
            )
            return None
        yield_types.append(row_data)
```

**Files**: `src/ui/forms/recipe_form.py`

**Notes**:
- This is mostly defensive - the dropdown should always have a value
- Matches existing validation pattern

---

### Subtask T018 – Update _save_yield_types to persist yield_type

**Purpose**: Ensure yield_type is saved when creating/updating finished units.

**Steps**:
1. Open `src/ui/recipes_tab.py`
2. Locate `_save_yield_types()` method (around line 504)
3. Update the create and update calls to include yield_type:

```python
def _save_yield_types(self, recipe_id: int, yield_types: list) -> bool:
    """Save yield types for a recipe."""
    try:
        existing_units = finished_unit_service.get_units_by_recipe(recipe_id)
        existing_ids = {unit.id for unit in existing_units}
        keeping_ids = set()

        for data in yield_types:
            if data["id"] is None:
                # Create new finished unit
                finished_unit_service.create_finished_unit(
                    display_name=data["display_name"],
                    recipe_id=recipe_id,
                    item_unit=data["item_unit"],
                    items_per_batch=data["items_per_batch"],
                    yield_type=data["yield_type"],  # NEW
                )
            else:
                # Update existing finished unit
                keeping_ids.add(data["id"])
                finished_unit_service.update_finished_unit(
                    data["id"],
                    display_name=data["display_name"],
                    item_unit=data["item_unit"],
                    items_per_batch=data["items_per_batch"],
                    yield_type=data["yield_type"],  # NEW
                )

        # Delete removed yield types
        for unit in existing_units:
            if unit.id not in keeping_ids:
                finished_unit_service.delete_finished_unit(unit.id)

        return True
    except Exception as e:
        logger.error(f"Error saving yield types: {e}")
        return False
```

**Files**: `src/ui/recipes_tab.py`

**Notes**:
- Pass yield_type to both create and update
- Follows existing pattern

---

### Subtask T019 – Update recipe detail display to show yield_type

**Purpose**: Show yield_type in the recipe info dialog.

**Steps**:
1. In `src/ui/recipes_tab.py`, locate the recipe detail display (around line 573)
2. Update the yield info display to include yield_type:

```python
# Show FinishedUnit yield types
recipe_fus = recipe_service.get_finished_units(recipe.id)
base_yields = recipe_service.get_base_yield_structure(recipe.id)

if recipe_fus and base_yields:
    details.append("Yield Types:")
    for fu, y in zip(recipe_fus, base_yields):
        items = y.get("items_per_batch")
        unit = y.get("item_unit", "")
        yield_type = fu.get("yield_type", "SERVING")  # NEW
        if items:
            details.append(f"  - {fu['display_name']}: {items} {unit}/batch ({yield_type})")
        else:
            details.append(f"  - {fu['display_name']}: Yield not specified ({yield_type})")
else:
    details.append("Yield Types: None defined (edit recipe to add)")
```

**Files**: `src/ui/recipes_tab.py`

**Notes**:
- Show yield_type in parentheses after the yield info
- Format: "24 cookie/batch (SERVING)" or "1 cake/batch (EA)"

---

### Subtask T020 – Update FinishedGoodDataTable yield info display

**Purpose**: Show yield_type in the finished units data table.

**Steps**:
1. Open `src/ui/widgets/data_table.py`
2. Locate `FinishedGoodDataTable` class (around line 453)
3. Update the yield info display (around line 575):

```python
# Get yield info based on mode
if row_data.yield_mode.value == "discrete_count":
    yield_type_display = f" ({row_data.yield_type})" if row_data.yield_type else ""
    yield_info = f"{row_data.items_per_batch} {row_data.item_unit}/batch{yield_type_display}"
    type_display = "Discrete Items"
else:
    yield_type_display = f" ({row_data.yield_type})" if row_data.yield_type else ""
    yield_info = f"{row_data.batch_percentage}% of batch{yield_type_display}"
    type_display = "Batch Portion"
```

**Files**: `src/ui/widgets/data_table.py`

**Parallel**: Yes - can be developed alongside T015-T019 (separate file)

**Notes**:
- Append yield_type in parentheses to existing yield info
- Format: "24 cookie/batch (SERVING)"

---

## Test Strategy

**Manual testing** (no automated UI tests required):
1. Open recipe form, verify Type dropdown appears
2. Create new finished unit with EA, verify it saves
3. Edit existing finished unit, change type to EA, verify it persists
4. View recipe detail, verify yield_type shows in info
5. View finished units table, verify yield_type shows in yield info column

**Test scenarios**:
- New recipe: Add finished unit with "EA" type
- Existing recipe: Edit to change type from "SERVING" to "EA"
- Variant recipe: Verify type dropdown is disabled
- Multiple yields: Add both EA and SERVING for same item_unit

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Grid layout breaks | Test on multiple window sizes |
| Variant recipes affected | readonly_structure disables dropdown |
| User confusion | "SERVING" as default matches most use cases |

---

## Definition of Done Checklist

- [ ] T015: yield_type dropdown added to YieldTypeRow
- [ ] T016: Grid configuration and headers updated
- [ ] T017: Form validation includes yield_type
- [ ] T018: _save_yield_types persists yield_type
- [ ] T019: Recipe detail shows yield_type
- [ ] T020: Data table shows yield_type in yield info
- [ ] Manual testing confirms all scenarios work
- [ ] Layout looks correct at various window sizes

---

## Review Guidance

**Reviewers should verify**:
1. Dropdown default is "SERVING"
2. Column headers align with row widgets
3. Variant recipes have dropdown disabled
4. yield_type persists after save and re-open
5. Display format is clear and consistent

---

## Activity Log

- 2026-01-29T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-29T17:50:15Z – unknown – shell_pid=73866 – lane=for_review – Ready for review: UI dropdown for yield_type, recipe detail display, FinishedGoodDataTable display. All tests pass (3220).
