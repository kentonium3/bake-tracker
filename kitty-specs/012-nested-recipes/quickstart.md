# Quickstart: Nested Recipes (Sub-Recipe Components)

**Feature**: 012-nested-recipes
**Date**: 2025-12-09

## What This Feature Does

Allows recipes to include other recipes as components. A "Frosted Layer Cake" recipe can include "Chocolate Cake Layers", "Vanilla Cake Layers", and "Buttercream Frosting" as sub-recipes.

## Key User Workflows

### 1. Adding a Sub-Recipe to a Recipe

1. Open or create a recipe in the Recipe Form
2. Scroll to the "Sub-Recipes" section (below Ingredients)
3. Select a recipe from the dropdown
4. Enter batch quantity (e.g., "2" for 2 batches of frosting)
5. Optionally add notes (e.g., "prepare day before")
6. Click "Add Sub-Recipe"
7. Save the recipe

### 2. Viewing Recipe Cost with Sub-Recipes

1. Open a recipe that has sub-recipes
2. The cost display shows:
   - Direct ingredient cost
   - Each sub-recipe with its cost contribution
   - Total cost (ingredients + all sub-recipes)
   - Cost per unit

### 3. Generating Shopping List

1. Select recipes for an event (existing workflow)
2. Shopping list now includes:
   - Ingredients from the main recipe
   - Ingredients from all sub-recipes
   - Quantities aggregated (same ingredient from multiple sources combined)

### 4. Reusing Sub-Recipes

1. Create a base recipe (e.g., "Buttercream Frosting")
2. Add it as a component to multiple parent recipes
3. When "Buttercream Frosting" costs change, all parent recipes automatically reflect updated costs

## UI Changes

### Recipe Form

```
┌─────────────────────────────────────────────────────────┐
│ Recipe: Frosted Layer Cake                              │
├─────────────────────────────────────────────────────────┤
│ Name: [Frosted Layer Cake          ]                    │
│ Category: [Cakes ▼]                                     │
│ Yield: [1] [cake ▼]                                     │
│                                                         │
│ ═══════════════════════════════════════════════════════ │
│ INGREDIENTS                                             │
│ ─────────────────────────────────────────────────────── │
│ [Ingredient dropdown] [qty] [unit] [Add]                │
│                                                         │
│   • Flour, 2 cups                              [Remove] │
│   • Sugar, 1 cup                               [Remove] │
│   • ...                                                 │
│                                                         │
│ ═══════════════════════════════════════════════════════ │
│ SUB-RECIPES                                             │
│ ─────────────────────────────────────────────────────── │
│ [Recipe dropdown   ▼] [qty] batches [Add]               │
│                                                         │
│   • Chocolate Cake Layers (1x)      $5.00      [Remove] │
│   • Buttercream Frosting (2x)       $6.00      [Remove] │
│                                                         │
│ ═══════════════════════════════════════════════════════ │
│ COST SUMMARY                                            │
│ ─────────────────────────────────────────────────────── │
│   Direct ingredients:              $8.00                │
│   Sub-recipes:                    $11.00                │
│   ─────────────────────────────────                     │
│   Total:                          $19.00                │
│   Per unit:                       $19.00/cake           │
│                                                         │
│                              [Cancel] [Save]            │
└─────────────────────────────────────────────────────────┘
```

### Recipe Detail View

```
┌─────────────────────────────────────────────────────────┐
│ FROSTED LAYER CAKE                                      │
│ Category: Cakes | Yields: 1 cake                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ INGREDIENTS                                             │
│   • 2 cups Flour                                        │
│   • 1 cup Sugar                                         │
│   • ...                                                 │
│                                                         │
│ SUB-RECIPES                                             │
│   • 1x Chocolate Cake Layers            $5.00           │
│   • 2x Buttercream Frosting             $6.00           │
│                                                         │
│ TOTAL COST: $19.00 ($19.00/cake)                        │
│                                                         │
│                                     [Edit] [Delete]     │
└─────────────────────────────────────────────────────────┘
```

## Validation Rules

| Rule | User Feedback |
|------|---------------|
| Cannot add recipe to itself | "Recipe cannot include itself as a component" |
| Cannot create circular reference | "Cannot add 'X': would create circular reference" |
| Cannot exceed 3 levels | "Cannot add 'X': would exceed maximum nesting depth of 3 levels" |
| Cannot add same sub-recipe twice | "'X' is already a component of this recipe" |
| Cannot delete recipe used as component | "Cannot delete 'X': used as component in: Y, Z" |
| Quantity must be positive | "Batch quantity must be greater than 0" |

## Import/Export

### Export Format

Recipes with sub-recipes export with a `components` array:

```json
{
  "name": "Frosted Layer Cake",
  "category": "Cakes",
  "ingredients": [...],
  "components": [
    {
      "recipe_name": "Chocolate Cake Layers",
      "quantity": 1.0,
      "notes": null
    },
    {
      "recipe_name": "Buttercream Frosting",
      "quantity": 2.0,
      "notes": "prepare day before"
    }
  ]
}
```

### Import Behavior

- Sub-recipes must be imported before parent recipes
- If a referenced sub-recipe doesn't exist, a warning is logged and the component is skipped
- The parent recipe is still imported with its direct ingredients

## Limitations

1. **Maximum 3 levels of nesting**: Parent → Child → Grandchild
2. **Batch multipliers only**: No volume/weight units for sub-recipes
3. **No automatic scaling**: Sub-recipe quantities are fixed (not scaled to parent yield)

## Quick Testing Checklist

- [ ] Create two simple recipes (A and B)
- [ ] Add recipe B as component of recipe A with quantity 2
- [ ] Verify cost shows B's cost × 2
- [ ] Try adding A as component of B (should fail: circular reference)
- [ ] Create recipe C, add B as component, then try adding C to A (should fail: circular reference)
- [ ] Create 3-level hierarchy: A → B → C, then try A → D → E → F (should fail: depth exceeded)
- [ ] Delete recipe B (should fail: used in A)
- [ ] Remove B from A, then delete B (should succeed)
- [ ] Export recipe with components, reimport to fresh database
