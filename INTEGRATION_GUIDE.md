# v0.4.0 Architecture Integration Guide

This guide explains how to integrate the Recipe and Events tabs with the new v0.4.0 Ingredient/Variant/Pantry architecture.

## Architecture Overview

### v0.3.0 (OLD - Being Phased Out)
- Single `Ingredient` model with brand, size, cost embedded
- Single `Inventory` tab for all ingredient management
- Direct ingredient-to-recipe relationships

### v0.4.0 (NEW - Current)
- **Ingredient**: Generic ingredient (e.g., "All-Purpose Flour") - what recipes use
- **Variant**: Brand-specific product (e.g., "King Arthur All-Purpose Flour, 5 lb bag")
- **PantryItem**: Individual inventory lot with purchase date, expiration, quantity

## Key Concepts

### Generic Ingredients
Recipes should reference **generic ingredients**, not specific brands. This allows users to substitute brands without changing recipes.

Example:
- ✅ Recipe calls for "All-Purpose Flour" (generic ingredient)
- ✅ User can fulfill with any variant: King Arthur, Bob's Red Mill, store brand, etc.
- ❌ Recipe should NOT call for "King Arthur All-Purpose Flour, 5 lb bag"

### Preferred Variants
Each generic ingredient can have ONE variant marked as `is_preferred=True`. This is used for:
- Cost calculations when no pantry inventory exists
- Shopping list recommendations
- Default selection in ingredient forms

### FIFO Cost Calculation
Recipe costs should prioritize actual pantry inventory (FIFO) over preferred variant pricing:
1. If ingredient has pantry inventory → use FIFO average cost from pantry
2. If no pantry inventory → use preferred variant's unit cost
3. If no preferred variant → use $0.00 or show "No cost data"

---

## Integration Points for Recipe Tab

### 1. Ingredient Selector in Recipe Form

**Current Implementation** (needs update):
```python
# OLD: Uses legacy ingredient model
ingredients = inventory_service.get_all_ingredients()
```

**New Implementation** (v0.4.0):
```python
from src.services import ingredient_service

# Get generic ingredients for recipe selector
ingredients = ingredient_service.get_all_ingredients()

# Display format: "{ingredient.name} ({ingredient.category})"
# Store in recipe: ingredient.slug (unique identifier)
```

**File to Update**: `src/ui/forms/recipe_form.py`

### 2. Recipe Cost Calculation

**Current Implementation** (needs update):
```python
# OLD: Uses ingredient.unit_cost directly
recipe_data = recipe_service.get_recipe_with_costs(recipe_id)
```

**New Implementation** (v0.4.0):
The `recipe_service.get_recipe_with_costs()` should be updated to:

```python
from src.services import pantry_service, variant_service
from decimal import Decimal

def get_recipe_with_costs(recipe_id: int) -> dict:
    recipe = get_recipe(recipe_id)
    total_cost = Decimal('0.0')
    ingredients_with_costs = []

    for ing in recipe.ingredients:
        ingredient = ingredient_service.get_ingredient(ing.ingredient_slug)

        # Try FIFO from pantry first
        pantry_cost = pantry_service.get_fifo_average_cost(
            ingredient.slug,
            quantity=ing.quantity,
            unit=ing.unit
        )

        if pantry_cost:
            # Use actual pantry cost
            cost = pantry_cost
            cost_source = "Pantry (FIFO)"
        else:
            # Fall back to preferred variant
            preferred = variant_service.get_preferred_variant(ingredient.slug)
            if preferred:
                # Convert quantity to purchase unit and calculate cost
                converted_qty = convert_unit(
                    ing.quantity,
                    ing.unit,
                    preferred.purchase_unit,
                    ingredient.slug
                )
                cost = converted_qty * preferred.unit_cost
                cost_source = f"Preferred: {preferred.brand}"
            else:
                cost = Decimal('0.0')
                cost_source = "No cost data"

        ingredients_with_costs.append({
            'ingredient': ingredient,
            'quantity': ing.quantity,
            'unit': ing.unit,
            'cost': cost,
            'cost_source': cost_source
        })
        total_cost += cost

    return {
        'recipe': recipe,
        'ingredients': ingredients_with_costs,
        'total_cost': total_cost,
        'cost_per_unit': total_cost / recipe.yield_quantity
    }
```

**File to Update**: `src/services/recipe_service.py`

### 3. Recipe Details Display

Update the cost breakdown display to show cost source:

```python
# Show cost source in details
for ing in recipe_data["ingredients"]:
    ing_name = ing["ingredient"].name
    ing_qty = ing["quantity"]
    ing_unit = ing["unit"]
    ing_cost = ing["cost"]
    cost_source = ing["cost_source"]

    details.append(
        f"  • {ing_qty} {ing_unit} {ing_name} "
        f"(${ing_cost:.2f} - {cost_source})"
    )
```

**File to Update**: `src/ui/recipes_tab.py` (lines 370-396)

### 4. Cross-Tab Navigation

Add clickable links to navigate from recipe ingredient to My Ingredients tab:

```python
# In recipe details or form, add navigation button
def _navigate_to_ingredient(self, ingredient_slug: str):
    """Navigate to My Ingredients tab with ingredient selected."""
    main_window = self.winfo_toplevel()
    if hasattr(main_window, 'navigate_to_ingredient'):
        main_window.navigate_to_ingredient(ingredient_slug)
```

**File to Update**: `src/ui/recipes_tab.py`, `src/ui/forms/recipe_form.py`

---

## Integration Points for Events Tab

### 1. Shopping List Display

**Current Implementation** (needs update):
Shopping list likely shows generic ingredients without variant recommendations.

**New Implementation** (v0.4.0):
```python
from src.services import variant_service

def get_event_shopping_list(event_id: int) -> dict:
    """Get shopping list with preferred variant recommendations."""
    # Calculate ingredient needs from all assigned packages
    ingredient_needs = calculate_ingredient_needs(event_id)

    shopping_list = []
    for need in ingredient_needs:
        ingredient = ingredient_service.get_ingredient(need['ingredient_slug'])

        # Get preferred variant for recommendation
        preferred = variant_service.get_preferred_variant(ingredient.slug)

        if preferred:
            recommendation = {
                'brand': preferred.brand,
                'package_size': preferred.package_size,
                'purchase_unit': preferred.purchase_unit,
                'unit_cost': preferred.unit_cost,
                'total_cost': calculate_packages_needed(need['quantity'], preferred) * preferred.total_cost
            }
        else:
            recommendation = None

        shopping_list.append({
            'ingredient': ingredient,
            'quantity_needed': need['quantity'],
            'unit': need['unit'],
            'recommended_variant': recommendation
        })

    return shopping_list
```

**File to Update**: `src/services/event_service.py`

### 2. Shopping List Display in UI

Format shopping list with preferred variant recommendations:

```python
# Display in EventDetailWindow
for item in shopping_list:
    ingredient = item['ingredient']
    qty_needed = item['quantity_needed']
    unit = item['unit']

    # Display ingredient need
    display = f"{qty_needed} {unit} {ingredient.name}"

    # Add recommendation if available
    if item['recommended_variant']:
        rec = item['recommended_variant']
        display += (
            f"\n  → Recommended: {rec['brand']} - {rec['package_size']} "
            f"(${rec['unit_cost']:.2f}/{rec['purchase_unit']})"
        )

        # Add clickable link to variant
        # (Implementation depends on UI framework)
```

**File to Update**: `src/ui/event_detail_window.py`

### 3. Cross-Tab Navigation from Shopping List

Add navigation from shopping list to My Ingredients tab:

```python
def _navigate_to_variant(self, ingredient_slug: str, variant_id: Optional[int] = None):
    """Navigate to My Ingredients tab with ingredient/variant selected."""
    main_window = self.winfo_toplevel()
    if hasattr(main_window, 'navigate_to_ingredient'):
        main_window.navigate_to_ingredient(ingredient_slug, variant_id)
```

**File to Update**: `src/ui/event_detail_window.py`

---

## Navigation Helpers in MainWindow

Add these helper methods to `main_window.py`:

```python
def navigate_to_ingredient(self, ingredient_slug: str, variant_id: Optional[int] = None):
    """
    Navigate to My Ingredients tab with specific ingredient selected.

    Args:
        ingredient_slug: Slug of ingredient to select
        variant_id: Optional variant ID to highlight
    """
    # Switch to My Ingredients tab
    self.switch_to_tab("My Ingredients")

    # Tell ingredients tab to select the ingredient
    if hasattr(self.ingredients_tab, 'select_ingredient'):
        self.ingredients_tab.select_ingredient(ingredient_slug, variant_id)

def navigate_to_pantry(self, ingredient_slug: Optional[str] = None):
    """
    Navigate to My Pantry tab, optionally filtered by ingredient.

    Args:
        ingredient_slug: Optional ingredient slug to filter by
    """
    # Switch to My Pantry tab
    self.switch_to_tab("My Pantry")

    # Tell pantry tab to filter by ingredient
    if ingredient_slug and hasattr(self.pantry_tab, 'filter_by_ingredient'):
        self.pantry_tab.filter_by_ingredient(ingredient_slug)
```

---

## "Used in Recipes" Feature

Add to My Ingredients tab to show which recipes use an ingredient:

```python
def _show_used_in_recipes(self, ingredient_slug: str):
    """Show list of recipes that use this ingredient."""
    from src.services import recipe_service

    recipes = recipe_service.get_recipes_using_ingredient(ingredient_slug)

    if not recipes:
        show_info("Used in Recipes", "This ingredient is not used in any recipes yet.")
        return

    # Build list of recipes with links
    recipe_list = []
    for recipe in recipes:
        recipe_list.append(f"• {recipe.name} ({recipe.category})")

    message = f"This ingredient is used in {len(recipes)} recipe(s):\n\n"
    message += "\n".join(recipe_list)

    # Show dialog with recipe links
    # (Could be enhanced with clickable links using custom dialog)
    show_info("Used in Recipes", message)
```

**File to Add**: Method in `src/ui/ingredients_tab.py`

**Service Method (Already Exists)**:
```python
# In src/services/recipe_service.py
# This method already exists:
def get_recipes_using_ingredient(ingredient_id: int) -> List[Recipe]:
    """Get all recipes that use a specific ingredient."""
    return get_all_recipes(ingredient_id=ingredient_id)

# To use with ingredient slug, first get the ingredient:
from src.services import ingredient_service

ingredient = ingredient_service.get_ingredient(ingredient_slug)
recipes = recipe_service.get_recipes_using_ingredient(ingredient.id)
```

---

## Service Methods Needed

These service methods need to be added or are already available:

### ingredient_service.py
- ✅ `get_all_ingredients()` - Returns list of generic ingredients
- ✅ `get_ingredient(slug)` - Get ingredient by slug

### variant_service.py
- ✅ `get_preferred_variant(ingredient_slug)` - Get preferred variant for ingredient
- ✅ `get_all_variants(ingredient_slug)` - Get all variants for an ingredient

### pantry_service.py
- ✅ `get_fifo_average_cost(ingredient_slug, quantity, unit)` - Get average FIFO cost
- ✅ `get_total_quantity(ingredient_slug)` - Get total pantry inventory

### recipe_service.py
- ✅ `get_recipes_using_ingredient(ingredient_id)` - Get recipes using ingredient (accepts ingredient ID, not slug)

---

## Testing Integration

### End-to-End Workflow Test

1. **Create Generic Ingredient** (My Ingredients tab)
   - Add "All-Purpose Flour"
   - Set recipe_unit = "cup"

2. **Add Variants** (My Ingredients tab)
   - Add "King Arthur AP Flour, 5 lb bag" ($6.99, mark as preferred)
   - Add "Bob's Red Mill AP Flour, 5 lb bag" ($7.49)

3. **Add Pantry Inventory** (My Pantry tab)
   - Add 25 lb of King Arthur variant
   - Purchase date: 2024-01-15

4. **Create Recipe** (Recipes tab)
   - Recipe: "Chocolate Chip Cookies"
   - Ingredient selector should show "All-Purpose Flour" (generic)
   - Add 2 cups All-Purpose Flour

5. **View Recipe Costs** (Recipes tab)
   - Cost should use FIFO from pantry (King Arthur, purchased 2024-01-15)
   - Display: "2 cups All-Purpose Flour ($X.XX - Pantry FIFO)"

6. **Create Event** (Events tab)
   - Add event "Holiday Bake Sale"
   - Assign "Chocolate Chip Cookies" package

7. **View Event Shopping List** (Events tab)
   - Should show "All-Purpose Flour" needed
   - Should recommend "King Arthur AP Flour, 5 lb bag" (preferred)
   - Clicking recommendation should navigate to My Ingredients tab

8. **Cross-Tab Navigation**
   - From Recipe details, click ingredient → opens My Ingredients tab
   - From Shopping list, click variant → opens My Ingredients tab with variant selected

---

## Migration Notes

### Database Schema Changes
All database migrations are already complete. No schema changes needed.

### Legacy Code Removal
- ✅ `inventory_tab.py` removed from main_window.py
- ✅ Legacy "Inventory" tab removed from UI
- ✅ All references to `inventory_tab` removed

### Backward Compatibility
The old v0.3.0 data model is no longer supported. If migrating from v0.3.0:
1. Run migration wizard (Tools → Migration Wizard)
2. Migration will convert old Ingredient records to Ingredient + Variant + PantryItem

---

## Questions?

If you have questions about integrating with the v0.4.0 architecture, consult:
- `src/services/ingredient_service.py` - Generic ingredient operations
- `src/services/variant_service.py` - Brand-specific product operations
- `src/services/pantry_service.py` - Inventory management with FIFO
- `src/ui/ingredients_tab.py` - Reference implementation of v0.4.0 UI patterns
- `src/ui/pantry_tab.py` - Reference implementation of pantry management
