# Quickstart: Ingredient Hierarchy Taxonomy

**Feature**: 031-ingredient-hierarchy-taxonomy
**Date**: 2025-12-30

---

## Overview

This feature adds a three-tier hierarchy to the ingredient catalog, transforming the flat 487-item list into a navigable tree structure.

---

## Key Concepts

### Hierarchy Levels

| Level | Name | Example | Can Have Products? | Can Be In Recipes? |
|-------|------|---------|--------------------|--------------------|
| 0 | Root | Chocolate | No | No |
| 1 | Mid-tier | Dark Chocolate | No | No |
| 2 | Leaf | Semi-Sweet Chocolate Chips | **Yes** | **Yes** |

**Critical Rule**: Only leaf ingredients (level 2) can have Products or be used in Recipes.

---

## File Locations

### New Files

```
src/services/ingredient_hierarchy_service.py   # Tree traversal & validation
src/ui/widgets/ingredient_tree_widget.py       # Reusable tree widget
scripts/migrate_hierarchy/                      # Migration tooling
```

### Modified Files

```
src/models/ingredient.py          # +parent_ingredient_id, +hierarchy_level
src/services/ingredient_service.py # +hierarchy validation on create/update
src/services/recipe_service.py     # +leaf-only validation
src/services/product_service.py    # +leaf-only validation
src/ui/ingredients_tab.py          # Use tree widget
```

---

## Quick Examples

### Check if Ingredient is Leaf

```python
from src.services.ingredient_hierarchy_service import is_leaf

if is_leaf(ingredient_id):
    # Can add to recipe
else:
    # Need to select a more specific ingredient
```

### Get Breadcrumb Path

```python
from src.services.ingredient_hierarchy_service import get_ancestors

ancestors = get_ancestors(ingredient_id)
path = " → ".join([a["display_name"] for a in reversed(ancestors)])
# "Chocolate → Dark Chocolate → Semi-Sweet Chocolate Chips"
```

### Populate Tree Widget

```python
from src.services.ingredient_hierarchy_service import get_root_ingredients, get_children

# Get root nodes
roots = get_root_ingredients()

# Lazy-load children on expand
def on_expand(parent_id):
    return get_children(parent_id)
```

---

## Testing

```bash
# Run hierarchy service tests
pytest src/tests/services/test_ingredient_hierarchy_service.py -v

# Run all tests
pytest src/tests -v
```

---

## Migration Process

1. **Export**: Run `scripts/migrate_hierarchy/export_ingredients.py`
2. **AI Categorization**: Use external AI to generate hierarchy suggestions
3. **Transform**: Run `scripts/migrate_hierarchy/transform_hierarchy.py`
4. **Validate**: Run `scripts/migrate_hierarchy/validate_hierarchy.py`
5. **Import**: Use standard import with new schema

See `scripts/prompts/hierarchy_categorization_prompt.md` for AI prompt template.

---

## Common Patterns

### Adding Ingredient to Recipe (with validation)

```python
def add_ingredient_to_recipe(recipe_id, ingredient_id, quantity, unit):
    # Validate leaf-only
    if not is_leaf(ingredient_id):
        suggestions = get_leaf_ingredients(parent_id=ingredient_id)[:3]
        raise ValidationError(
            f"Please select a specific ingredient. "
            f"Try: {', '.join(s['display_name'] for s in suggestions)}"
        )

    # Proceed with add
    ...
```

### Creating Child Ingredient

```python
from src.services.ingredient_service import create_ingredient

# Parent must be level 0 or 1
new_ingredient = create_ingredient({
    "display_name": "Extra Dark Chocolate",
    "slug": "extra_dark_chocolate",
    "parent_ingredient_id": dark_chocolate_id,  # Auto-calculates level
    # hierarchy_level will be set automatically based on parent
})
```

---

## Troubleshooting

### "Cannot add category to recipe"

**Cause**: Selected ingredient is level 0 or 1, not a leaf.

**Solution**: Navigate to a level 2 (leaf) ingredient.

### "Maximum hierarchy depth exceeded"

**Cause**: Trying to add child to a level 2 ingredient.

**Solution**: Level 2 ingredients cannot have children. The tree is limited to 3 levels.

### "Circular reference detected"

**Cause**: Trying to move an ingredient under itself or its descendant.

**Solution**: Select a different parent that isn't in the ingredient's subtree.
