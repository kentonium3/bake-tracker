# Quickstart: Complete F031 Hierarchy UI

## Prerequisites

- Python 3.10+ with venv activated
- Application running (`python src/main.py`)
- Sample data imported with hierarchy (`test_data/sample_data.json`)

## Key Service Functions

```python
from src.services import ingredient_hierarchy_service

# Get all root categories (L0)
categories = ingredient_hierarchy_service.get_root_ingredients()

# Get children of a parent
subcategories = ingredient_hierarchy_service.get_children(parent_id)

# Get ancestry chain (for display and pre-populating edit forms)
ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)
# Returns: [immediate_parent, grandparent, ...] ordered from closest to root

# Get ingredients at specific level
level_0 = ingredient_hierarchy_service.get_ingredients_by_level(0)  # Roots
level_1 = ingredient_hierarchy_service.get_ingredients_by_level(1)  # Subcategories
level_2 = ingredient_hierarchy_service.get_ingredients_by_level(2)  # Leaves

# Get only leaf ingredients (for product/recipe dropdowns)
leaves = ingredient_hierarchy_service.get_leaf_ingredients()
```

## Modal Dialog Pattern

For any new dialog with cascading dropdowns:

```python
class MyDialog(ctk.CTkToplevel):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Hide while building
        self.withdraw()
        self.transient(parent)

        # Build UI here...
        self._setup_ui()

        # Show after UI complete
        self.deiconify()
        self.update()
        try:
            self.wait_visibility()
            self.grab_set()
        except Exception:
            if not self.winfo_exists():
                return
        self.lift()
        self.focus_force()
```

## Testing

Run application and verify:

1. **Ingredients Tab**: Shows L0, L1, Name columns (not "Category")
2. **Level Filter**: Can filter by hierarchy level
3. **Edit Form**: Cascading L0 → L1 dropdowns work
4. **Products Tab**: Shows ingredient path, hierarchy filter works
5. **Inventory Tab**: Shows hierarchy, not category

## Reference Files

- Pattern reference: `src/ui/forms/add_product_dialog.py`
- Service functions: `src/services/ingredient_hierarchy_service.py`
- Bug spec with mockups: `docs/bugs/BUG_F031_incomplete_hierarchy_ui.md`
