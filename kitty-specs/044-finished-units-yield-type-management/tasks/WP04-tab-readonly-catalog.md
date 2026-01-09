---
work_package_id: "WP04"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Finished Units Tab - Read-Only Catalog"
phase: "Phase 1 - Parallel Foundation"
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

# Work Package Prompt: WP04 - Finished Units Tab - Read-Only Catalog

## Objectives & Success Criteria

**Primary Objective**: Convert the existing FinishedUnitsTab from full CRUD to a read-only catalog view with navigation to parent recipes.

**Success Criteria**:
- Add, Edit, Delete buttons are removed (FR-016)
- Info label indicates yield types are managed in Recipe Edit (FR-017)
- Recipe column shows in the data table (FR-012)
- Double-click opens parent Recipe Edit form (FR-015)
- Recipe filter dropdown allows filtering by recipe (FR-014)
- Search by name still works (FR-013)
- Refresh button remains functional

**User Story 2 (P2)**: A baker wants to see all the finished products defined across all recipes in one place to understand what they can produce.

## Context & Constraints

**Feature**: 044-finished-units-yield-type-management
**File**: `src/ui/finished_units_tab.py` (726 lines)
**Research Reference**: [research.md](../research.md) - UI Layer - Finished Units Tab section

**Current Tab State**:
- Full CRUD interface with Add, Edit, Delete, View Details, Refresh buttons
- Search by name with category filter
- Double-click opens detail dialog

**Target Tab State**:
- Read-only catalog (no CRUD buttons except Refresh)
- Search by name with recipe filter
- Info message about Recipe Edit
- Double-click navigates to Recipe Edit form

## Subtasks & Detailed Guidance

### Subtask T011 - Remove Add/Edit/Delete Buttons

**Purpose**: Convert tab to read-only by removing CRUD action buttons.

**Location**: `_create_action_buttons()` method (lines 201-254)

**Changes Required**:
1. Remove Add button creation and grid placement
2. Remove Edit button creation (self.edit_button) and grid placement
3. Remove Delete button creation (self.delete_button) and grid placement
4. Keep Refresh button
5. Optionally keep View Details button (read-only operation)

**Before** (conceptual):
```python
def _create_action_buttons(self):
    # Add button - REMOVE
    # Edit button - REMOVE
    # Delete button - REMOVE
    # View Details button - KEEP (optional)
    # Refresh button - KEEP
```

**After**:
```python
def _create_action_buttons(self):
    """Create action buttons for read-only catalog."""
    button_frame = ctk.CTkFrame(self, fg_color="transparent")
    button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

    # View Details button (optional - read-only)
    self.details_button = ctk.CTkButton(
        button_frame,
        text="View Details",
        command=self._view_details,
        width=ButtonWidths.DETAILS_BUTTON,
        state="disabled",
    )
    self.details_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

    # Refresh button
    refresh_button = ctk.CTkButton(
        button_frame,
        text="Refresh",
        command=self.refresh,
        width=ButtonWidths.STANDARD_BUTTON,
    )
    refresh_button.grid(row=0, column=1, padx=PADDING_MEDIUM)
```

**Also Remove**: References to `self.edit_button` and `self.delete_button` in `_on_row_select()` method.

### Subtask T012 - Add Info Label

**Purpose**: Inform users that yield types are managed through Recipe Edit.

**Location**: Add to `_create_action_buttons()` or create separate method

**Implementation**:
```python
# Add info label below buttons or at top of button frame
info_label = ctk.CTkLabel(
    button_frame,
    text="Yield types are managed in Recipe Edit. Double-click to open recipe.",
    text_color="gray",
    font=ctk.CTkFont(size=11),
)
info_label.grid(row=0, column=2, padx=PADDING_LARGE, sticky="w")
```

**Alternative Placement**: Could be placed above the data table as a prominent notice.

### Subtask T013 - Add Recipe Column to Data Table

**Purpose**: Display the parent recipe name for each yield type.

**Location**: `_create_data_table()` method and/or data table widget configuration

**Context**: The data table widget `FinishedUnitDataTable` (imported from widgets) may need modification, or the data passed to it needs to include recipe name.

**Approach Options**:

**Option A - Modify Data Preparation**:
If the data table accepts column configuration, ensure recipe name is included:
```python
# When setting data, ensure recipe relationship is loaded
# The FinishedUnit model has: recipe = relationship("Recipe", back_populates="finished_units")
# So finished_unit.recipe.name should be accessible
```

**Option B - Modify Widget**:
If `FinishedGoodDataTable` (aliased as `FinishedUnitDataTable`) needs modification:
- Add "Recipe" column to column headers
- Include `recipe.name` in row data

**Implementation Hint**:
```python
# The service already supports eager loading of recipe
# Check if get_all_finished_units returns units with recipe loaded
# If so, just need to update table display configuration
```

### Subtask T014 - Change Double-Click to Open Recipe Edit

**Purpose**: Navigate to the parent recipe when user double-clicks a yield type row.

**Location**: `_on_row_double_click()` method (line 336)

**Current Behavior**:
```python
def _on_row_double_click(self, finished_unit: FinishedUnit) -> None:
    self.selected_finished_unit = finished_unit
    self._view_details()  # Opens detail dialog
```

**New Behavior**:
```python
def _on_row_double_click(self, finished_unit: FinishedUnit) -> None:
    """
    Handle row double-click - open parent Recipe Edit form.
    """
    self.selected_finished_unit = finished_unit
    self._open_recipe_edit(finished_unit.recipe_id)

def _open_recipe_edit(self, recipe_id: int):
    """
    Open the Recipe Edit form for the given recipe.

    Args:
        recipe_id: ID of the recipe to edit
    """
    from src.services import recipe_service
    from src.ui.forms.recipe_form import RecipeFormDialog

    try:
        # Load the recipe
        recipe = recipe_service.get_recipe_by_id(recipe_id)
        if not recipe:
            show_error("Recipe Not Found", "The parent recipe could not be found.", parent=self)
            return

        # Open recipe edit dialog
        dialog = RecipeFormDialog(
            self,
            recipe=recipe,
            title=f"Edit Recipe: {recipe.name}",
        )
        self.wait_window(dialog)
        result = dialog.get_result()

        if result:
            # Recipe was saved - refresh to show any yield type changes
            self.refresh()

    except Exception as e:
        logging.exception("Failed to open recipe edit")
        show_error("Error", f"Could not open recipe: {e}", parent=self)
```

**Note**: Use deferred import for `RecipeFormDialog` to avoid circular imports.

### Subtask T015 - Add Recipe Filter Dropdown

**Purpose**: Allow filtering yield types by parent recipe.

**Location**: Modify `_create_search_bar()` method or add separate filter widget

**Current State**: SearchBar has search text and category filter

**Required**: Add recipe dropdown filter

**Implementation Options**:

**Option A - Modify SearchBar Widget**:
If SearchBar supports additional filters, add recipe list

**Option B - Add Separate Dropdown**:
```python
def _create_search_bar(self):
    """Create search bar with recipe filter."""
    # Existing search bar
    self.search_bar = SearchBar(
        self,
        search_callback=self._on_search,
        categories=["All Categories"] + self.recipe_categories,
        placeholder="Search by yield type name...",
    )
    self.search_bar.grid(row=0, column=0, sticky="ew", ...)

    # Add recipe filter dropdown below or beside search bar
    filter_frame = ctk.CTkFrame(self, fg_color="transparent")
    filter_frame.grid(row=0, column=1, sticky="e", padx=PADDING_LARGE)

    recipe_label = ctk.CTkLabel(filter_frame, text="Recipe:")
    recipe_label.pack(side="left", padx=5)

    self.recipe_filter = ctk.CTkComboBox(
        filter_frame,
        values=["All Recipes"] + self._get_recipe_names(),
        command=self._on_recipe_filter_change,
        width=200,
    )
    self.recipe_filter.set("All Recipes")
    self.recipe_filter.pack(side="left", padx=5)

def _get_recipe_names(self) -> List[str]:
    """Get list of recipe names for filter dropdown."""
    from src.services import recipe_service
    try:
        recipes = recipe_service.get_all_recipes()
        return sorted([r.name for r in recipes])
    except Exception:
        return []

def _on_recipe_filter_change(self, selected_recipe: str):
    """Handle recipe filter selection."""
    # Trigger search with recipe filter
    self._on_search(
        self.search_bar.get_search_text(),
        self.search_bar.get_category(),
    )
```

**Modify `_on_search`** to include recipe filter:
```python
def _on_search(self, search_text: str, category: Optional[str] = None) -> None:
    # Get recipe filter
    recipe_filter = None
    if hasattr(self, 'recipe_filter'):
        selected = self.recipe_filter.get()
        if selected and selected != "All Recipes":
            recipe_filter = selected

    # Call service with recipe filter
    finished_units = finished_unit_service.get_all_finished_units(
        name_search=search_text if search_text else None,
        category=category_filter,
        recipe_name=recipe_filter,  # Add this parameter if service supports it
    )
```

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular import with RecipeFormDialog | Medium | Medium | Use deferred import |
| Recipe not found on double-click | Low | Low | Show error message |
| Data table widget incompatible | Low | Medium | Check widget interface first |

## Definition of Done Checklist

- [ ] T011: Add, Edit, Delete buttons removed from tab
- [ ] T012: Info label visible explaining Recipe Edit
- [ ] T013: Recipe column shows in data table
- [ ] T014: Double-click opens Recipe Edit form
- [ ] T015: Recipe filter dropdown works
- [ ] Search by name still works
- [ ] Refresh button still works
- [ ] No regression in tab functionality

## Review Guidance

**Key Verification Points**:
1. No way to create/edit/delete from this tab (read-only)
2. Info message is visible and clear
3. Double-click successfully opens Recipe Edit
4. Recipe filter correctly filters the list
5. Tab loads within 1 second (SC-002)

**Test Scenarios**:
1. Open tab - verify no Add/Edit/Delete buttons
2. See info message about Recipe Edit
3. See Recipe column in data
4. Double-click row - Recipe Edit opens
5. Select recipe in filter - list filters correctly
6. Search by name - results filter correctly
7. Click Refresh - data reloads

## Activity Log

- 2026-01-09T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-09T18:11:05Z – unknown – lane=doing – Delegating to Gemini for parallel work
- 2026-01-09T18:15:45Z – unknown – lane=for_review – Converted to read-only catalog. Removed CRUD buttons, added info label, double-click opens Recipe Edit, added recipe filter.
- 2026-01-09T18:37:38Z – claude – lane=done – Code review complete: Approved. Read-only catalog with recipe filter, info label, and double-click navigation implemented.
