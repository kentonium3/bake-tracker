# Quickstart: Finished Units Yield Type Management

**Feature**: 044-finished-units-yield-type-management
**Date**: 2026-01-09

## Overview

This feature enables bakers to define yield types (finished products) for recipes. The primary UI is an inline section in the Recipe Edit form. A read-only catalog tab provides overview.

## Prerequisites

- Python 3.10+ environment activated
- Dependencies installed: `pip install -r requirements.txt`
- Working in feature worktree: `.worktrees/044-finished-units-yield-type-management/`

## Quick Verification

```bash
# Verify existing infrastructure
python -c "from src.models.finished_unit import FinishedUnit; print('Model OK')"
python -c "from src.services.finished_unit_service import FinishedUnitService; print('Service OK')"
python -c "from src.ui.finished_units_tab import FinishedUnitsTab; print('Tab OK')"
```

## Implementation Map

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `src/models/finished_unit.py` | Modify | Change FK ondelete to CASCADE |
| `src/services/finished_unit_service.py` | Modify | Add name uniqueness validation |
| `src/ui/forms/recipe_form.py` | Modify | Add Yield Types section |
| `src/ui/finished_units_tab.py` | Modify | Convert to read-only catalog |

### Files to Create

| File | Description |
|------|-------------|
| `src/tests/test_finished_unit_recipe_integration.py` | Integration tests |

## Implementation Steps

### Step 1: Model Change (Cascade Delete)

```python
# src/models/finished_unit.py, line 84
# Change from:
recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
# To:
recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
```

### Step 2: Service Validation (Name Uniqueness)

Add to `FinishedUnitService.create_finished_unit()`:

```python
# Check name uniqueness within recipe
existing = session.query(FinishedUnit).filter(
    FinishedUnit.recipe_id == recipe_id,
    FinishedUnit.display_name == display_name.strip()
).first()
if existing:
    raise ValidationError(f"Yield type '{display_name}' already exists for this recipe")
```

### Step 3: Recipe Form - Yield Types Section

Add after Recipe Ingredients section (around line 660):

```python
# Yield Types section
yield_types_label = ctk.CTkLabel(
    parent,
    text="Yield Types",
    font=ctk.CTkFont(size=14, weight="bold"),
)
yield_types_label.grid(row=row, column=0, columnspan=2, sticky="w", ...)
row += 1

# Yield types container
self.yield_types_frame = ctk.CTkFrame(parent, fg_color="transparent")
self.yield_types_frame.grid(row=row, column=0, columnspan=2, sticky="ew", ...)
row += 1

# Add yield type button
add_yield_type_button = ctk.CTkButton(
    parent,
    text="➕ Add Yield Type",
    command=self._add_yield_type_row,
)
add_yield_type_button.grid(row=row, column=0, columnspan=2, ...)
row += 1
```

### Step 4: Finished Units Tab - Read-Only Conversion

Remove CRUD buttons, add info label:

```python
# In _create_action_buttons():
# Remove Add, Edit, Delete buttons
# Keep only Refresh button

# Add info label
info_label = ctk.CTkLabel(
    button_frame,
    text="Yield types are managed in Recipe Edit",
    text_color="gray",
)
info_label.grid(...)

# In _on_row_double_click():
# Navigate to parent Recipe Edit instead of detail dialog
recipe_id = finished_unit.recipe_id
# Open recipe edit form...
```

## Testing Commands

```bash
# Run all finished unit tests
pytest src/tests/test_finished_unit*.py -v

# Run with coverage
pytest src/tests/test_finished_unit*.py -v --cov=src/services/finished_unit_service

# Run specific test
pytest src/tests -v -k "test_create_finished_unit"
```

## Manual Testing Checklist

1. **Recipe Edit - Add Yield Type**
   - [ ] Open existing recipe in edit mode
   - [ ] See Yield Types section below ingredients
   - [ ] Add "Large Cookie" with 30 items per batch
   - [ ] Click Save Recipe
   - [ ] Reopen recipe - yield type persists

2. **Recipe Edit - Validation**
   - [ ] Try adding yield type with empty name → Error shown
   - [ ] Try adding yield type with 0 items per batch → Error shown
   - [ ] Try adding duplicate name → Error shown

3. **Finished Units Tab - Read-Only**
   - [ ] Open Finished Units tab
   - [ ] No Add/Edit/Delete buttons visible
   - [ ] See info message about Recipe Edit
   - [ ] Double-click row → Recipe Edit opens

4. **Cascade Delete**
   - [ ] Create recipe with yield types
   - [ ] Delete the recipe
   - [ ] Verify yield types also deleted

## Parallelization Notes

**Safe to work in parallel:**
- Recipe form changes (Claude)
- Tab changes + Service validation (Gemini)
- Unit tests (Gemini, after implementation)

**Must be sequential:**
- Integration testing (after all components)
- Manual acceptance testing (after integration)

## Key Code Patterns

### Inline Entry Row Pattern

Follow `RecipeIngredientRow` pattern from recipe_form.py:

```python
class YieldTypeRow(ctk.CTkFrame):
    def __init__(self, parent, remove_callback, ...):
        # Name entry
        self.name_entry = ctk.CTkEntry(self, placeholder_text="Yield type name")
        # Quantity entry
        self.quantity_entry = ctk.CTkEntry(self, placeholder_text="Items per batch")
        # Remove button
        self.remove_button = ctk.CTkButton(self, text="✕", command=...)

    def get_data(self) -> Optional[Dict[str, Any]]:
        # Validate and return data
        ...
```

### Service Integration Pattern

Follow existing service integrator pattern from finished_units_tab.py:

```python
result = self.service_integrator.execute_service_operation(
    operation_name="Create Yield Type",
    operation_type=OperationType.CREATE,
    service_function=lambda: finished_unit_service.create_finished_unit(...),
    parent_widget=self,
    error_context="Creating yield type",
)
```
