---
work_package_id: "WP03"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Recipe Edit Form - Yield Types Section"
phase: "Phase 2 - Core UI"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Recipe Edit Form - Yield Types Section

## Objectives & Success Criteria

**Primary Objective**: Add inline yield type management to the Recipe Edit form, allowing users to define what finished products a recipe produces.

**Success Criteria**:
- Yield Types section appears below Recipe Ingredients in the form
- Users can add new yield types with Name and Items Per Batch
- Users can edit existing yield types inline
- Users can delete yield types with confirmation
- Changes persist when recipe is saved
- Warning shown if recipe has no yield types on save
- Existing yield types load when editing a recipe

**User Story 1 (P1)**: A baker opens a recipe and defines the different finished products that recipe can produce, including the quantity each batch makes.

## Context & Constraints

**Feature**: 044-finished-units-yield-type-management
**File**: `src/ui/forms/recipe_form.py` (1262 lines)
**Research Reference**: [research.md](../research.md) - UI Layer section

**Key Design Decision**: User explicitly requested inline row entry, NOT modal dialogs.

**Pattern Reference**: Follow `RecipeIngredientRow` pattern (lines 168-388) for consistency.

**Current Form Section Order** (lines 497-793):
1. Basic Information
2. Yield Information
3. Recipe Ingredients
4. Sub-Recipes
5. Cost Summary
6. Notes

**New Section Order** (insert after Recipe Ingredients):
1. Basic Information
2. Yield Information
3. Recipe Ingredients
4. **Yield Types (NEW)** <- Insert here
5. Sub-Recipes
6. Cost Summary
7. Notes

**Dependencies**:
- WP02 must be complete for service validation to work
- Uses `finished_unit_service` for CRUD operations

## Subtasks & Detailed Guidance

### Subtask T005 - Create YieldTypeRow Widget Class

**Purpose**: Create an inline widget for displaying/editing a single yield type, following the RecipeIngredientRow pattern.

**Location**: Add as new class in `src/ui/forms/recipe_form.py` (before RecipeFormDialog class)

**Implementation**:
```python
class YieldTypeRow(ctk.CTkFrame):
    """Row widget for a single yield type in the Recipe Edit form."""

    def __init__(
        self,
        parent,
        remove_callback,
        finished_unit_id: Optional[int] = None,
        display_name: str = "",
        items_per_batch: int = 1,
    ):
        """
        Initialize yield type row.

        Args:
            parent: Parent widget
            remove_callback: Callback to remove this row
            finished_unit_id: ID if editing existing (None for new)
            display_name: Yield type name
            items_per_batch: Number of items per batch
        """
        super().__init__(parent)

        self.remove_callback = remove_callback
        self.finished_unit_id = finished_unit_id

        # Configure grid (Name / Items Per Batch / Remove)
        self.grid_columnconfigure(0, weight=3)  # Name (wider)
        self.grid_columnconfigure(1, weight=1)  # Quantity
        self.grid_columnconfigure(2, weight=0)  # Remove button

        # Name entry
        self.name_entry = ctk.CTkEntry(
            self,
            width=250,
            placeholder_text="Yield type name (e.g., Large Cookie)"
        )
        if display_name:
            self.name_entry.insert(0, display_name)
        self.name_entry.grid(row=0, column=0, padx=(0, PADDING_MEDIUM), pady=5, sticky="ew")

        # Items per batch entry
        self.quantity_entry = ctk.CTkEntry(
            self,
            width=100,
            placeholder_text="Per batch"
        )
        self.quantity_entry.insert(0, str(items_per_batch))
        self.quantity_entry.grid(row=0, column=1, padx=PADDING_MEDIUM, pady=5)

        # Remove button
        remove_button = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            command=lambda: remove_callback(self),
            fg_color="darkred",
            hover_color="red",
        )
        remove_button.grid(row=0, column=2, padx=(PADDING_MEDIUM, 0), pady=5)

    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Get yield type data from this row.

        Returns:
            Dictionary with id, display_name, items_per_batch, or None if invalid
        """
        name = self.name_entry.get().strip()
        quantity_str = self.quantity_entry.get().strip()

        # Validate name
        if not name:
            return None

        # Validate quantity
        try:
            items_per_batch = int(quantity_str)
            if items_per_batch <= 0:
                return None
        except ValueError:
            return None

        return {
            "id": self.finished_unit_id,
            "display_name": name,
            "items_per_batch": items_per_batch,
        }
```

### Subtask T006 - Add Yield Types Section Header and Container

**Purpose**: Add the section UI structure to the form.

**Location**: Inside `_create_form_fields()` method, after Recipe Ingredients section (around line 660)

**Implementation**:
```python
# Yield Types section (insert after ingredients section)
yield_types_label = ctk.CTkLabel(
    parent,
    text="Yield Types",
    font=ctk.CTkFont(size=14, weight="bold"),
)
yield_types_label.grid(
    row=row,
    column=0,
    columnspan=2,
    sticky="w",
    padx=PADDING_MEDIUM,
    pady=(PADDING_LARGE, PADDING_MEDIUM),
)
row += 1

# Yield types container
self.yield_types_frame = ctk.CTkFrame(parent, fg_color="transparent")
self.yield_types_frame.grid(
    row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5
)
self.yield_types_frame.grid_columnconfigure(0, weight=1)
row += 1

# Add yield type button
add_yield_type_button = ctk.CTkButton(
    parent,
    text="+ Add Yield Type",
    command=self._add_yield_type_row,
    width=150,
)
add_yield_type_button.grid(row=row, column=0, columnspan=2, padx=PADDING_MEDIUM, pady=5)
row += 1
```

**Note**: Also initialize `self.yield_type_rows: List[YieldTypeRow] = []` in `__init__` alongside `self.ingredient_rows`.

### Subtask T007 - Implement Add/Remove Row Methods

**Purpose**: Handle adding and removing yield type rows dynamically.

**Location**: Add methods to `RecipeFormDialog` class

**Implementation**:
```python
def _add_yield_type_row(
    self,
    finished_unit_id: Optional[int] = None,
    display_name: str = "",
    items_per_batch: int = 1,
):
    """
    Add a new yield type row.

    Args:
        finished_unit_id: ID if editing existing (None for new)
        display_name: Yield type name
        items_per_batch: Number of items per batch
    """
    row = YieldTypeRow(
        self.yield_types_frame,
        self._remove_yield_type_row,
        finished_unit_id,
        display_name,
        items_per_batch,
    )
    row.grid(row=len(self.yield_type_rows), column=0, sticky="ew", pady=2)
    self.yield_type_rows.append(row)

def _remove_yield_type_row(self, row: YieldTypeRow):
    """
    Remove a yield type row.

    Args:
        row: Row to remove
    """
    if row in self.yield_type_rows:
        self.yield_type_rows.remove(row)
        row.destroy()
        # Re-grid remaining rows
        for idx, remaining_row in enumerate(self.yield_type_rows):
            remaining_row.grid(row=idx, column=0, sticky="ew", pady=2)
```

### Subtask T008 - Persist Yield Types on Recipe Save

**Purpose**: When the recipe is saved, create/update/delete yield types via the service.

**Location**: Modify `_save()` method or create helper `_save_yield_types()`

**Implementation Strategy**:
```python
def _save_yield_types(self, recipe_id: int):
    """
    Persist yield type changes for the recipe.

    Handles:
    - Creating new yield types (id=None)
    - Updating existing yield types (id set)
    - Deleting removed yield types
    """
    from src.services import finished_unit_service

    # Collect current yield type data from UI
    current_data = []
    for row in self.yield_type_rows:
        data = row.get_data()
        if data:
            current_data.append(data)

    # Get existing yield types for this recipe
    existing_units = finished_unit_service.get_units_by_recipe(recipe_id)
    existing_ids = {unit.id for unit in existing_units}

    # Track which IDs we're keeping
    keeping_ids = set()

    for data in current_data:
        if data["id"] is None:
            # Create new
            finished_unit_service.create_finished_unit(
                display_name=data["display_name"],
                recipe_id=recipe_id,
                items_per_batch=data["items_per_batch"],
            )
        else:
            # Update existing
            keeping_ids.add(data["id"])
            finished_unit_service.update_finished_unit(
                data["id"],
                display_name=data["display_name"],
                items_per_batch=data["items_per_batch"],
            )

    # Delete removed yield types
    for unit in existing_units:
        if unit.id not in keeping_ids:
            finished_unit_service.delete_finished_unit(unit.id)
```

**Integration Point**: Call `_save_yield_types(recipe_id)` after the recipe itself is saved (need to have the recipe ID for new recipes).

### Subtask T009 - Load Yield Types When Editing

**Purpose**: Populate the yield types section when opening an existing recipe for editing.

**Location**: Modify `_populate_form()` method

**Implementation**:
```python
# In _populate_form(), add after other field population:

# Load yield types
from src.services import finished_unit_service

yield_types = finished_unit_service.get_units_by_recipe(self.recipe.id)
for yt in yield_types:
    self._add_yield_type_row(
        finished_unit_id=yt.id,
        display_name=yt.display_name,
        items_per_batch=yt.items_per_batch or 1,
    )
```

### Subtask T010 - Add Warning for No Yield Types

**Purpose**: Warn users when saving a recipe without any yield types (soft enforcement per planning decision).

**Location**: Modify `_validate_form()` method

**Implementation**:
```python
# In _validate_form(), after ingredient validation (around line 1227):

# Validate yield types (warning, not blocking)
yield_types = []
for row in self.yield_type_rows:
    data = row.get_data()
    if data:
        yield_types.append(data)

if not yield_types:
    confirmed = show_confirmation(
        "No Yield Types",
        "This recipe has no yield types defined.\n\n"
        "Yield types specify what finished products this recipe produces "
        "(e.g., '30 Large Cookies per batch').\n\n"
        "Continue without yield types?",
        parent=self,
    )
    if not confirmed:
        return None

# Add yield_types to return data
return {
    "name": name,
    "category": category,
    # ... other fields ...
    "yield_types": yield_types,  # Add this
}
```

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Form becomes too tall | Medium | Low | Already uses scrollable frame |
| Validation error on save | Medium | Medium | Service validates; UI displays error |
| Race condition on save | Low | Medium | Save within single transaction |

## Definition of Done Checklist

- [ ] T005: YieldTypeRow class implemented following RecipeIngredientRow pattern
- [ ] T006: Yield Types section appears in form after ingredients
- [ ] T007: Add/remove yield type rows works correctly
- [ ] T008: Yield types persist when recipe is saved
- [ ] T009: Existing yield types load when editing recipe
- [ ] T010: Warning shown when saving without yield types
- [ ] UI matches existing form styling
- [ ] No regression in existing recipe functionality

## Review Guidance

**Key Verification Points**:
1. Section appears in correct location (after ingredients, before sub-recipes)
2. Add/Edit/Delete operations work correctly
3. Changes persist after save and reload
4. Warning appears but doesn't block save
5. Validation errors display appropriately

**Test Scenarios**:
1. Create new recipe with 2 yield types - verify saved
2. Edit recipe, add yield type - verify added
3. Edit recipe, remove yield type - verify removed
4. Edit recipe, change yield type name/quantity - verify updated
5. Save recipe with no yield types - verify warning appears
6. Enter invalid data (empty name, 0 quantity) - verify not saved

## Activity Log

- 2026-01-09T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-09T18:15:58Z – unknown – lane=doing – Starting implementation of Yield Types section in Recipe Edit form
- 2026-01-09T19:30:00Z – claude – lane=for_review – Completed all subtasks: T005 (YieldTypeRow class), T006 (Section UI), T007 (Add/Remove methods), T008 (Persistence in recipes_tab.py), T009 (Load existing on edit), T010 (Warning validation)
- 2026-01-09T18:37:44Z – claude – lane=for_review – Implementation complete: All subtasks T005-T010 completed. YieldTypeRow widget, section UI, persistence, and validation.
- 2026-01-09T18:37:48Z – claude – lane=done – Code review complete: Approved. YieldTypeRow class, section UI, add/remove methods, persistence in recipes_tab.py, loading on edit, and warning validation all implemented correctly.
