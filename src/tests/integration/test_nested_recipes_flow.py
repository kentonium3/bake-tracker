"""
Integration tests for the Nested Recipes (012) feature.

These tests validate the quickstart.md scenarios and cover:
- T044: Quickstart checklist scenarios
- T045: 3-level nesting end-to-end
- T046: Import/export round-trip
- T047: Backward compatibility
"""

import json
import os
import tempfile

import pytest

from src.services import recipe_service, import_export_service, ingredient_service
from src.services.exceptions import ValidationError
from src.models import Recipe, RecipeIngredient, RecipeComponent

@pytest.fixture
def test_ingredient(test_db):
    """Create a test ingredient with pricing."""
    # Ensure 'Flour' root category exists
    ingredient_service.create_ingredient({"display_name": "Flour (Category)", "category": "Flour", "hierarchy_level": 0, "slug": "flour-category"})
    return ingredient_service.create_ingredient({
        "display_name": "Flour",
        "category": "Flour",
        "slug": "flour"
    })

@pytest.fixture
def test_ingredient_sugar(test_db):
    """Create a sugar ingredient."""
    # Ensure 'Sugar' root category exists
    ingredient_service.create_ingredient({"display_name": "Sugar (Category)", "category": "Sugar", "hierarchy_level": 0, "slug": "sugar-category"})
    return ingredient_service.create_ingredient({
        "display_name": "Sugar",
        "category": "Sugar",
        "slug": "sugar"
    })

@pytest.fixture
def test_ingredient_butter(test_db):
    """Create a butter ingredient."""
    # Ensure 'Dairy' root category exists
    ingredient_service.create_ingredient({"display_name": "Dairy (Category)", "category": "Dairy", "hierarchy_level": 0, "slug": "dairy-category"})
    return ingredient_service.create_ingredient({
        "display_name": "Butter",
        "category": "Dairy",
        "slug": "butter"
    })

@pytest.fixture
def test_ingredient_milk(test_db):
    """Create a milk ingredient."""
    # Ensure 'Dairy' root category exists
    # This will be skipped if Dairy (Category) was already created by test_ingredient_butter
    try:
        ingredient_service.create_ingredient({"display_name": "Dairy (Category)", "category": "Dairy", "hierarchy_level": 0, "slug": "dairy-category"})
    except ValidationError:
        pass # Already exists
    return ingredient_service.create_ingredient({
        "display_name": "Milk",
        "category": "Dairy",
        "slug": "milk"
    })

# =============================================================================
# T044: Quickstart Checklist Tests
# =============================================================================

class TestQuickstartChecklist:
    """Tests that validate the quickstart.md testing checklist."""

    def test_create_two_simple_recipes(self, test_ingredient):
        """Create two simple recipes (A and B)."""
        recipe_a = recipe_service.create_recipe(
            {"name": "Recipe A", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )
        recipe_b = recipe_service.create_recipe(
            {"name": "Recipe B", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.5, "unit": "cup"}]
        )

        assert recipe_a.id is not None
        assert recipe_b.id is not None
        assert recipe_a.name == "Recipe A"
        assert recipe_b.name == "Recipe B"

    def test_add_recipe_b_as_component_of_a_with_quantity_2(self, test_ingredient):
        """Add recipe B as component of recipe A with quantity 2."""
        # Create recipes
        recipe_a = recipe_service.create_recipe(
            {"name": "Recipe A", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )
        recipe_b = recipe_service.create_recipe(
            {"name": "Recipe B", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.5, "unit": "cup"}]
        )

        # Add B as component of A with quantity 2
        component = recipe_service.add_recipe_component(
            recipe_a.id, recipe_b.id, quantity=2.0
        )

        assert component is not None
        assert component.recipe_id == recipe_a.id
        assert component.component_recipe_id == recipe_b.id
        assert component.quantity == 2.0

        # Verify cost calculation (B's cost x 2)
        components = recipe_service.get_recipe_components(recipe_a.id)
        assert len(components) == 1
        assert components[0].quantity == 2.0

    def test_circular_reference_ab_blocked(self, test_ingredient):
        """Try adding A as component of B (should fail: circular reference)."""
        # Create recipes
        recipe_a = recipe_service.create_recipe(
            {"name": "Recipe A", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )
        recipe_b = recipe_service.create_recipe(
            {"name": "Recipe B", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.5, "unit": "cup"}]
        )

        # Add B as component of A
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id, quantity=1.0)

        # Try to add A as component of B (should fail)
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.add_recipe_component(recipe_b.id, recipe_a.id, quantity=1.0)

        assert "circular" in str(exc_info.value).lower()

    def test_circular_reference_transitive_blocked(self, test_ingredient):
        """Create C, add B as component, then try adding C to A (circular)."""
        # Create recipes A, B, C
        recipe_a = recipe_service.create_recipe(
            {"name": "Recipe A", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )
        recipe_b = recipe_service.create_recipe(
            {"name": "Recipe B", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.5, "unit": "cup"}]
        )
        recipe_c = recipe_service.create_recipe(
            {"name": "Recipe C", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.25, "unit": "cup"}]
        )

        # A includes B, C includes B
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id, quantity=1.0)
        recipe_service.add_recipe_component(recipe_c.id, recipe_b.id, quantity=1.0)

        # Now try to add C to A - this is NOT circular, should succeed
        # (A -> B, C -> B, A -> C creates A -> B and A -> C -> B, no cycles)
        component = recipe_service.add_recipe_component(recipe_a.id, recipe_c.id, quantity=1.0)
        assert component is not None

        # But now try to add A to C - THAT is circular (A -> C -> A)
        with pytest.raises(ValidationError):
            recipe_service.add_recipe_component(recipe_c.id, recipe_a.id, quantity=1.0)

    def test_depth_exceeded_blocked(self, test_ingredient):
        """Create 3-level hierarchy, then try 4th level (should fail)."""
        # Create 4 recipes
        recipe_d = recipe_service.create_recipe(
            {"name": "Recipe D", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.1, "unit": "cup"}]
        )
        recipe_e = recipe_service.create_recipe(
            {"name": "Recipe E", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.1, "unit": "cup"}]
        )
        recipe_f = recipe_service.create_recipe(
            {"name": "Recipe F", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.1, "unit": "cup"}]
        )
        recipe_g = recipe_service.create_recipe(
            {"name": "Recipe G", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.1, "unit": "cup"}]
        )

        # Create D -> E -> F (3 levels - level 1, 2, 3)
        recipe_service.add_recipe_component(recipe_e.id, recipe_f.id, quantity=1.0)  # E includes F (2 levels)
        recipe_service.add_recipe_component(recipe_d.id, recipe_e.id, quantity=1.0)  # D includes E (3 levels)

        # Now try to add G above D, creating G -> D -> E -> F (4 levels) - should fail
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.add_recipe_component(recipe_g.id, recipe_d.id, quantity=1.0)

        assert "depth" in str(exc_info.value).lower() or "level" in str(exc_info.value).lower()

    def test_delete_recipe_in_use_blocked(self, test_ingredient):
        """Delete recipe B (should fail: used in A)."""
        # Create recipes
        recipe_a = recipe_service.create_recipe(
            {"name": "Recipe A", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )
        recipe_b = recipe_service.create_recipe(
            {"name": "Recipe B", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.5, "unit": "cup"}]
        )

        # Add B as component of A
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id, quantity=1.0)

        # Try to delete B (should fail)
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.delete_recipe(recipe_b.id)

        assert "used" in str(exc_info.value).lower() or "component" in str(exc_info.value).lower()

    def test_remove_component_then_delete_succeeds(self, test_ingredient):
        """Remove B from A, then delete B (should succeed)."""
        # Create recipes
        recipe_a = recipe_service.create_recipe(
            {"name": "Recipe A", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )
        recipe_b = recipe_service.create_recipe(
            {"name": "Recipe B", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.5, "unit": "cup"}]
        )

        # Add B as component of A
        recipe_service.add_recipe_component(recipe_a.id, recipe_b.id, quantity=1.0)

        # Remove B from A
        result = recipe_service.remove_recipe_component(recipe_a.id, recipe_b.id)
        assert result is True

        # Now delete B (should succeed)
        recipe_service.delete_recipe(recipe_b.id)

        # Verify B is gone (get_recipe raises RecipeNotFound, get_recipe_by_name returns None)
        deleted = recipe_service.get_recipe_by_name("Recipe B")
        assert deleted is None

# =============================================================================
# T045: 3-Level Nesting End-to-End Tests
# =============================================================================

class TestThreeLevelNesting:
    """Tests for 3-level nesting functionality."""

    def test_create_three_level_hierarchy(
        self, test_ingredient, test_ingredient_sugar, test_ingredient_butter, test_ingredient_milk
    ):
        """Create hierarchy: Grandchild -> Child -> Parent."""
        # Create Grandchild recipe
        grandchild = recipe_service.create_recipe(
            {"name": "Grandchild", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [
                {"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"},
                {"ingredient_id": test_ingredient_sugar.id, "quantity": 0.5, "unit": "cup"},
            ]
        )

        # Create Child recipe
        child = recipe_service.create_recipe(
            {"name": "Child", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient_butter.id, "quantity": 1.0, "unit": "cup"}]
        )

        # Create Parent recipe
        parent = recipe_service.create_recipe(
            {"name": "Parent", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient_milk.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Build hierarchy: Child includes Grandchild, Parent includes Child
        recipe_service.add_recipe_component(child.id, grandchild.id, quantity=1.0)
        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0)

        # Verify hierarchy
        parent_components = recipe_service.get_recipe_components(parent.id)
        assert len(parent_components) == 1
        assert parent_components[0].component_recipe.name == "Child"
        assert parent_components[0].quantity == 2.0

        child_components = recipe_service.get_recipe_components(child.id)
        assert len(child_components) == 1
        assert child_components[0].component_recipe.name == "Grandchild"

    def test_three_level_cost_calculation(
        self, test_ingredient, test_ingredient_sugar, test_ingredient_butter, test_ingredient_milk
    ):
        """Verify cost calculation includes all levels."""
        # Create hierarchy
        grandchild = recipe_service.create_recipe(
            {"name": "Grandchild", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [
                {"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"},
                {"ingredient_id": test_ingredient_sugar.id, "quantity": 0.5, "unit": "cup"},
            ]
        )
        child = recipe_service.create_recipe(
            {"name": "Child", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient_butter.id, "quantity": 1.0, "unit": "cup"}]
        )
        parent = recipe_service.create_recipe(
            {"name": "Parent", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient_milk.id, "quantity": 2.0, "unit": "cup"}]
        )

        recipe_service.add_recipe_component(child.id, grandchild.id, quantity=1.0)
        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0)

        # Calculate total cost for parent
        cost_data = recipe_service.calculate_total_cost_with_components(parent.id)

        # Verify cost structure exists
        assert "direct_ingredient_cost" in cost_data
        assert "total_component_cost" in cost_data
        assert "total_cost" in cost_data

        # Total should be direct + component costs
        expected_total = cost_data["direct_ingredient_cost"] + cost_data["total_component_cost"]
        assert abs(cost_data["total_cost"] - expected_total) < 0.01

    def test_three_level_ingredient_aggregation(
        self, test_ingredient, test_ingredient_sugar, test_ingredient_butter, test_ingredient_milk
    ):
        """Verify shopping list aggregates all ingredients from all levels."""
        # Create hierarchy
        grandchild = recipe_service.create_recipe(
            {"name": "Grandchild", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [
                {"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"},
                {"ingredient_id": test_ingredient_sugar.id, "quantity": 0.5, "unit": "cup"},
            ]
        )
        child = recipe_service.create_recipe(
            {"name": "Child", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient_butter.id, "quantity": 1.0, "unit": "cup"}]
        )
        parent = recipe_service.create_recipe(
            {"name": "Parent", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient_milk.id, "quantity": 2.0, "unit": "cup"}]
        )

        recipe_service.add_recipe_component(child.id, grandchild.id, quantity=1.0)
        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0)

        # Get aggregated ingredients
        aggregated = recipe_service.get_aggregated_ingredients(parent.id)

        # Should have 4 unique ingredients
        ingredient_names = [ing["ingredient"].display_name for ing in aggregated]
        assert "Milk" in ingredient_names
        assert "Butter" in ingredient_names
        assert "Flour" in ingredient_names
        assert "Sugar" in ingredient_names

        # Verify quantities are multiplied correctly
        # Parent has 2x Child, Child has 1x Grandchild
        # So Parent should aggregate: 2 cups milk (direct), 2 cups butter (1 * 2),
        # 2 cups flour (1 * 1 * 2), 1 cup sugar (0.5 * 1 * 2)
        flour_entry = next(ing for ing in aggregated if ing["ingredient"].display_name == "Flour")
        sugar_entry = next(ing for ing in aggregated if ing["ingredient"].display_name == "Sugar")
        butter_entry = next(ing for ing in aggregated if ing["ingredient"].display_name == "Butter")
        milk_entry = next(ing for ing in aggregated if ing["ingredient"].display_name == "Milk")

        assert flour_entry["total_quantity"] == 2.0  # 1 * 1 * 2
        assert sugar_entry["total_quantity"] == 1.0  # 0.5 * 1 * 2
        assert butter_entry["total_quantity"] == 2.0  # 1 * 2
        assert milk_entry["total_quantity"] == 2.0  # direct

# =============================================================================
# T046: Import/Export Round-Trip Tests
# =============================================================================

class TestImportExportRoundTrip:
    """Tests for import/export functionality with recipe components."""

    def test_export_recipe_with_components_structure(self, test_ingredient):
        """Verify export includes component relationships."""
        # Create parent and child recipes
        child = recipe_service.create_recipe(
            {"name": "Child Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.5, "unit": "cup"}]
        )
        parent = recipe_service.create_recipe(
            {"name": "Parent Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )
        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0, notes="Test note")

        # Export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name

        try:
            result = import_export_service.export_recipes_to_json(export_file)
            assert result.success

            # Read and verify
            with open(export_file) as f:
                data = json.load(f)

            # Find parent recipe in export
            parent_data = next(
                r for r in data["recipes"] if r["name"] == "Parent Recipe"
            )
            assert "components" in parent_data
            assert len(parent_data["components"]) == 1
            assert parent_data["components"][0]["recipe_name"] == "Child Recipe"
            assert parent_data["components"][0]["quantity"] == 2.0
            assert parent_data["components"][0]["notes"] == "Test note"
        finally:
            os.unlink(export_file)

    def test_full_roundtrip_preserves_hierarchy(self, test_ingredient, test_ingredient_sugar):
        """Export then import preserves all component relationships."""
        # Create 3-level hierarchy
        grandchild = recipe_service.create_recipe(
            {"name": "Grandchild Export", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.25, "unit": "cup"}]
        )
        child = recipe_service.create_recipe(
            {"name": "Child Export", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient_sugar.id, "quantity": 0.5, "unit": "cup"}]
        )
        parent = recipe_service.create_recipe(
            {"name": "Parent Export", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )

        recipe_service.add_recipe_component(child.id, grandchild.id, quantity=1.0)
        recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0, notes="Double batch")

        # Export all to v3.2 format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name

        try:
            export_result = import_export_service.export_all_to_json(export_file)
            assert export_result.success

            # Delete the recipes
            recipe_service.remove_recipe_component(parent.id, child.id)
            recipe_service.remove_recipe_component(child.id, grandchild.id)
            recipe_service.delete_recipe(parent.id)
            recipe_service.delete_recipe(child.id)
            recipe_service.delete_recipe(grandchild.id)

            # Verify deleted
            assert recipe_service.get_recipe_by_name("Parent Export") is None

            # Re-import using the current importer with merge mode
            import_result = import_export_service.import_all_from_json_v4(export_file, mode="merge")
            assert import_result.successful > 0

            # Verify hierarchy restored
            imported_parent = recipe_service.get_recipe_by_name("Parent Export")
            assert imported_parent is not None

            parent_components = recipe_service.get_recipe_components(imported_parent.id)
            assert len(parent_components) == 1
            assert parent_components[0].component_recipe.name == "Child Export"
            assert parent_components[0].quantity == 2.0
            assert parent_components[0].notes == "Double batch"

            # Verify child has grandchild
            child_components = recipe_service.get_recipe_components(
                parent_components[0].component_recipe_id
            )
            assert len(child_components) == 1
            assert child_components[0].component_recipe.name == "Grandchild Export"
        finally:
            os.unlink(export_file)

# =============================================================================
# T047: Backward Compatibility Tests
# =============================================================================

class TestBackwardCompatibility:
    """Tests to ensure existing recipes without components still work."""

    def test_recipe_without_components_works(self, test_ingredient):
        """Recipe without components behaves identically to before feature."""
        # Create simple recipe without components
        recipe = recipe_service.create_recipe(
            {"name": "Simple Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # All operations should work
        assert recipe_service.get_recipe(recipe.id) is not None
        assert len(recipe_service.get_recipe_components(recipe.id)) == 0

        # Update should work (need to include all required fields)
        updated = recipe_service.update_recipe(
            recipe.id,
            {
                "name": "Updated Simple",
                "category": "Cookies",
                "yield_quantity": 1,
                "yield_unit": "batch"
            },
            [{"ingredient_id": test_ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )
        assert updated.name == "Updated Simple"

        # Delete should work
        recipe_service.delete_recipe(recipe.id)
        assert recipe_service.get_recipe_by_name("Updated Simple") is None

    def test_recipe_cost_without_components_unchanged(self, test_ingredient):
        """Cost calculation unchanged for recipes without components."""
        recipe = recipe_service.create_recipe(
            {"name": "Cost Test Recipe", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 2.0, "unit": "cup"}]
        )

        # Calculate using new method
        cost_data = recipe_service.calculate_total_cost_with_components(recipe.id)

        # Component cost should be 0
        assert cost_data["total_component_cost"] == 0

        # Total should equal direct ingredient cost
        assert cost_data["total_cost"] == cost_data["direct_ingredient_cost"]

    def test_existing_recipe_export_import_without_components(self, test_ingredient):
        """Export/import works for recipes without components."""
        recipe = recipe_service.create_recipe(
            {"name": "Export Test Simple", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name

        try:
            # Export all to v3.2 format
            export_result = import_export_service.export_all_to_json(export_file)
            assert export_result.success

            # Verify export has empty components array
            with open(export_file) as f:
                data = json.load(f)

            recipe_data = next(r for r in data["recipes"] if r["name"] == "Export Test Simple")
            assert "components" in recipe_data
            assert len(recipe_data["components"]) == 0

            # Delete and reimport using current importer
            recipe_service.delete_recipe(recipe.id)
            import_result = import_export_service.import_all_from_json_v4(export_file, mode="merge")
            assert import_result.successful > 0

            # Verify restored
            restored = recipe_service.get_recipe_by_name("Export Test Simple")
            assert restored is not None
            assert len(recipe_service.get_recipe_components(restored.id)) == 0
        finally:
            os.unlink(export_file)

    def test_aggregated_ingredients_without_components(self, test_ingredient, test_ingredient_sugar):
        """get_aggregated_ingredients works for recipes without components."""
        recipe = recipe_service.create_recipe(
            {"name": "Aggregation Test", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [
                {"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"},
                {"ingredient_id": test_ingredient_sugar.id, "quantity": 0.5, "unit": "cup"},
            ]
        )

        # Get aggregated - should just return direct ingredients
        aggregated = recipe_service.get_aggregated_ingredients(recipe.id)

        assert len(aggregated) == 2
        ingredient_names = [ing["ingredient"].display_name for ing in aggregated]
        assert "Flour" in ingredient_names
        assert "Sugar" in ingredient_names

# =============================================================================
# Additional Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Additional edge case tests for robustness."""

    def test_cannot_add_recipe_to_itself(self, test_ingredient):
        """Recipe cannot include itself as a component."""
        recipe = recipe_service.create_recipe(
            {"name": "Self Reference", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )

        with pytest.raises(ValidationError):
            recipe_service.add_recipe_component(recipe.id, recipe.id, quantity=1.0)

    def test_cannot_add_same_component_twice(self, test_ingredient):
        """Cannot add same sub-recipe twice to same parent."""
        parent = recipe_service.create_recipe(
            {"name": "Parent Dup", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )
        child = recipe_service.create_recipe(
            {"name": "Child Dup", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.5, "unit": "cup"}]
        )

        # First add succeeds
        recipe_service.add_recipe_component(parent.id, child.id, quantity=1.0)

        # Second add should fail
        with pytest.raises(ValidationError) as exc_info:
            recipe_service.add_recipe_component(parent.id, child.id, quantity=2.0)

        assert "already" in str(exc_info.value).lower() or "exists" in str(exc_info.value).lower()

    def test_quantity_must_be_positive(self, test_ingredient):
        """Batch quantity must be greater than 0."""
        parent = recipe_service.create_recipe(
            {"name": "Parent Qty", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )
        child = recipe_service.create_recipe(
            {"name": "Child Qty", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.5, "unit": "cup"}]
        )

        # Zero quantity should fail
        with pytest.raises(ValidationError):
            recipe_service.add_recipe_component(parent.id, child.id, quantity=0)

        # Negative quantity should fail
        with pytest.raises(ValidationError):
            recipe_service.add_recipe_component(parent.id, child.id, quantity=-1.0)

    def test_update_component_quantity(self, test_ingredient):
        """Can update component quantity."""
        parent = recipe_service.create_recipe(
            {"name": "Parent Update", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 1.0, "unit": "cup"}]
        )
        child = recipe_service.create_recipe(
            {"name": "Child Update", "category": "Cookies", "yield_quantity": 1, "yield_unit": "batch"},
            [{"ingredient_id": test_ingredient.id, "quantity": 0.5, "unit": "cup"}]
        )

        recipe_service.add_recipe_component(parent.id, child.id, quantity=1.0)

        # Update quantity
        updated = recipe_service.update_recipe_component(parent.id, child.id, quantity=3.0)
        assert updated.quantity == 3.0

        # Verify persisted
        components = recipe_service.get_recipe_components(parent.id)
        assert components[0].quantity == 3.0
