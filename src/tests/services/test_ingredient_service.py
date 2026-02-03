"""
Tests for Ingredient Service.

Tests cover:
- validate_density_fields() all-or-nothing validation
- Positive value validation
- Unit validation
"""

import pytest

from src.services.ingredient_service import (
    validate_density_fields,
    create_ingredient,
    update_ingredient,
    can_delete_ingredient,
    delete_ingredient_safe,
)
from src.services.exceptions import IngredientInUse, IngredientNotFound
from src.models import (
    Product,
    RecipeIngredient,
    Recipe,
    IngredientAlias,
    IngredientCrosswalk,
)
from src.models.inventory_snapshot import SnapshotIngredient, InventorySnapshot
from src.models.ingredient import Ingredient


class TestValidateDensityFields:
    """Tests for density field validation."""

    def test_validate_density_fields_all_empty(self):
        """Empty density fields are valid."""
        is_valid, error = validate_density_fields(None, None, None, None)
        assert is_valid
        assert error == ""

    def test_validate_density_fields_all_filled(self):
        """All density fields filled with valid data."""
        is_valid, error = validate_density_fields(1.0, "cup", 4.25, "oz")
        assert is_valid
        assert error == ""

    def test_validate_density_fields_partial_volume_only(self):
        """Partial density fields (volume only) fail validation."""
        is_valid, error = validate_density_fields(1.0, "cup", None, None)
        assert not is_valid
        assert "All density fields must be provided together" in error

    def test_validate_density_fields_partial_weight_only(self):
        """Partial density fields (weight only) fail validation."""
        is_valid, error = validate_density_fields(None, None, 4.25, "oz")
        assert not is_valid
        assert "All density fields must be provided together" in error

    def test_validate_density_fields_partial_missing_unit(self):
        """Partial density fields (missing unit) fail validation."""
        is_valid, error = validate_density_fields(1.0, None, 4.25, "oz")
        assert not is_valid
        assert "All density fields must be provided together" in error

    def test_validate_density_fields_zero_volume(self):
        """Zero volume value fails validation."""
        is_valid, error = validate_density_fields(0, "cup", 4.25, "oz")
        assert not is_valid
        # Zero is treated as "not filled" so it's a partial fill error
        assert "All density fields must be provided together" in error

    def test_validate_density_fields_negative_volume(self):
        """Negative volume value fails validation."""
        is_valid, error = validate_density_fields(-1.0, "cup", 4.25, "oz")
        assert not is_valid
        assert "greater than zero" in error

    def test_validate_density_fields_negative_weight(self):
        """Negative weight value fails validation."""
        is_valid, error = validate_density_fields(1.0, "cup", -1.0, "oz")
        assert not is_valid
        assert "greater than zero" in error

    def test_validate_density_fields_invalid_volume_unit(self):
        """Invalid volume unit fails validation."""
        is_valid, error = validate_density_fields(1.0, "invalid", 4.25, "oz")
        assert not is_valid
        assert "Invalid volume unit" in error

    def test_validate_density_fields_invalid_weight_unit(self):
        """Invalid weight unit fails validation."""
        is_valid, error = validate_density_fields(1.0, "cup", 4.25, "invalid")
        assert not is_valid
        assert "Invalid weight unit" in error

    def test_validate_density_fields_weight_unit_as_volume(self):
        """Using weight unit in volume field fails validation."""
        is_valid, error = validate_density_fields(1.0, "oz", 4.25, "oz")
        assert not is_valid
        assert "Invalid volume unit" in error

    def test_validate_density_fields_volume_unit_as_weight(self):
        """Using volume unit in weight field fails validation."""
        is_valid, error = validate_density_fields(1.0, "cup", 4.25, "cup")
        assert not is_valid
        assert "Invalid weight unit" in error

    def test_validate_density_fields_empty_string_treated_as_none(self):
        """Empty strings are treated as None."""
        is_valid, error = validate_density_fields("", "", "", "")
        assert is_valid  # All empty is valid
        assert error == ""

    def test_validate_density_fields_mixed_empty_string(self):
        """Mixed empty strings are treated as partial."""
        is_valid, error = validate_density_fields(1.0, "", 4.25, "oz")
        assert not is_valid
        assert "All density fields must be provided together" in error

    def test_validate_density_fields_all_valid_units(self):
        """Test various valid unit combinations."""
        valid_combos = [
            (1.0, "cup", 4.25, "oz"),
            (1.0, "tbsp", 14.0, "g"),
            (1.0, "ml", 1.0, "g"),
            (1.0, "tsp", 5.0, "g"),
            (1.0, "l", 1000.0, "kg"),
        ]
        for vol_val, vol_unit, wt_val, wt_unit in valid_combos:
            is_valid, error = validate_density_fields(vol_val, vol_unit, wt_val, wt_unit)
            assert (
                is_valid
            ), f"Expected valid: {vol_val} {vol_unit} = {wt_val} {wt_unit}, got error: {error}"

    def test_validate_density_fields_case_insensitive(self):
        """Unit validation is case insensitive."""
        is_valid, error = validate_density_fields(1.0, "CUP", 4.25, "OZ")
        assert is_valid
        assert error == ""


# =============================================================================
# Feature 031: Hierarchy Validation Tests
# =============================================================================


class TestCreateIngredientHierarchy:
    """Tests for create_ingredient with hierarchy fields."""

    def test_create_ingredient_with_valid_parent(self, test_db, hierarchy_ingredients):
        """Create ingredient with valid parent sets correct hierarchy_level."""
        # Create a new leaf under the mid-tier category
        new_ingredient = create_ingredient(
            {
                "display_name": "White Chocolate Chips",
                "category": "Chocolate",
                "parent_ingredient_id": hierarchy_ingredients.mid.id,
            }
        )
        assert new_ingredient.parent_ingredient_id == hierarchy_ingredients.mid.id
        assert new_ingredient.hierarchy_level == 2  # Parent is level 1, so child is level 2

    def test_create_ingredient_with_nonexistent_parent_fails(self, test_db):
        """Create ingredient with non-existent parent raises IngredientNotFound."""
        from src.services.exceptions import IngredientNotFound

        with pytest.raises(IngredientNotFound):
            create_ingredient(
                {
                    "display_name": "Orphan Ingredient",
                    "category": "Test",
                    "parent_ingredient_id": 99999,  # Non-existent ID
                }
            )

    def test_create_ingredient_exceeding_max_depth_fails(self, test_db, hierarchy_ingredients):
        """Create ingredient that would exceed max depth (3 levels) raises MaxDepthExceededError."""
        from src.services.exceptions import MaxDepthExceededError

        # hierarchy_ingredients.leaf1 is level 2; adding child would make level 3
        with pytest.raises(MaxDepthExceededError):
            create_ingredient(
                {
                    "display_name": "Too Deep Ingredient",
                    "category": "Chocolate",
                    "parent_ingredient_id": hierarchy_ingredients.leaf1.id,
                }
            )

    def test_create_ingredient_without_parent_defaults_to_leaf(self, test_db):
        """Create ingredient without parent defaults hierarchy_level to 2 (leaf)."""
        ingredient = create_ingredient(
            {
                "display_name": "Standalone Ingredient",
                "category": "Other",
            }
        )
        assert ingredient.hierarchy_level == 2
        assert ingredient.parent_ingredient_id is None


class TestUpdateIngredientHierarchy:
    """Tests for update_ingredient with hierarchy field changes."""

    def test_update_ingredient_parent_triggers_move(self, test_db, hierarchy_ingredients):
        """Update parent_ingredient_id triggers move_ingredient logic."""
        # Create a new mid-tier to move a leaf under
        from src.models.ingredient import Ingredient

        session = test_db()

        new_mid = Ingredient(
            display_name="New Mid Category",
            slug="new-mid-category",
            category="Chocolate",
            hierarchy_level=1,
            parent_ingredient_id=hierarchy_ingredients.root.id,
        )
        session.add(new_mid)
        session.commit()

        leaf_slug = hierarchy_ingredients.leaf1.slug
        leaf_id = hierarchy_ingredients.leaf1.id

        # Move leaf1 from dark_chocolate to new_mid
        updated = update_ingredient(leaf_slug, {"parent_ingredient_id": new_mid.id})

        # Verify it moved by querying fresh from the database
        moved_leaf = session.query(Ingredient).filter(Ingredient.id == leaf_id).first()
        assert moved_leaf.parent_ingredient_id == new_mid.id


class TestCreateIngredientFieldNormalization:
    """Tests for F035: Field name normalization in create_ingredient."""

    def test_create_ingredient_with_name_field_normalized(self, test_db):
        """Create ingredient with 'name' field normalizes to 'display_name'."""
        # Use 'name' instead of 'display_name'
        ingredient = create_ingredient({"name": "Test Name Field", "category": "Flour"})
        assert ingredient.display_name == "Test Name Field"
        assert ingredient.slug == "test_name_field"

    def test_create_ingredient_with_display_name_field_unchanged(self, test_db):
        """Create ingredient with 'display_name' field still works (backward compat)."""
        ingredient = create_ingredient({"display_name": "Test Display Name", "category": "Sugars"})
        assert ingredient.display_name == "Test Display Name"
        assert ingredient.slug == "test_display_name"

    def test_create_ingredient_display_name_takes_precedence(self, test_db):
        """When both 'name' and 'display_name' present, display_name takes precedence."""
        ingredient = create_ingredient(
            {
                "name": "This Should Be Ignored",
                "display_name": "This Should Be Used",
                "category": "Seasonings",
            }
        )
        assert ingredient.display_name == "This Should Be Used"
        assert ingredient.slug == "this_should_be_used"


# =============================================================================
# Feature 035: Deletion Protection and Slug Tests
# =============================================================================


class TestDeletionProtectionAndSlug:
    """Tests for F035: Deletion protection and slug generation features."""

    # -------------------------------------------------------------------------
    # T024 - Delete Blocked by Products
    # -------------------------------------------------------------------------

    def test_delete_blocked_by_products(self, test_db):
        """Verify deletion is blocked when Products reference the ingredient.

        T024: When an ingredient has associated Product records, deletion must
        be blocked and return the count of blocking products.
        """
        session = test_db()

        # Arrange: Create an ingredient
        ingredient = create_ingredient(
            {"display_name": "Test Flour for Product Block", "category": "Flour"}
        )

        # Create a Product referencing this ingredient
        product = Product(
            ingredient_id=ingredient.id,
            brand="Test Brand",
            package_size="5 lb",
            package_unit="lb",
            package_unit_quantity=5.0,
        )
        session.add(product)
        session.commit()

        # Act: Check if deletion is allowed - should raise IngredientInUse
        with pytest.raises(IngredientInUse) as exc_info:
            can_delete_ingredient(ingredient.id, session=session)

        # Assert: Exception contains correct details
        assert exc_info.value.deps["products"] == 1

        # Also verify delete_ingredient_safe raises IngredientInUse
        with pytest.raises(IngredientInUse) as exc_info2:
            delete_ingredient_safe(ingredient.id, session=session)
        assert exc_info2.value.deps["products"] == 1

    # -------------------------------------------------------------------------
    # T025 - Delete Blocked by Recipes
    # -------------------------------------------------------------------------

    def test_delete_blocked_by_recipes(self, test_db):
        """Verify deletion is blocked when RecipeIngredient records reference ingredient.

        T025: When an ingredient is used in recipes via RecipeIngredient,
        deletion must be blocked and return the count of blocking recipes.
        """
        session = test_db()

        # Arrange: Create an ingredient
        ingredient = create_ingredient(
            {"display_name": "Test Vanilla for Recipe Block", "category": "Extracts"}
        )

        # Create a Recipe and RecipeIngredient
        # F056: yield_quantity, yield_unit removed from Recipe model
        recipe = Recipe(
            name="Test Vanilla Cake",
            category="Cakes",
        )
        session.add(recipe)
        session.flush()

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id, ingredient_id=ingredient.id, quantity=1.0, unit="tsp"
        )
        session.add(recipe_ingredient)
        session.commit()

        # Act: Check if deletion is allowed - should raise IngredientInUse
        with pytest.raises(IngredientInUse) as exc_info:
            can_delete_ingredient(ingredient.id, session=session)

        # Assert: Exception contains correct details
        assert exc_info.value.deps["recipes"] == 1

    # -------------------------------------------------------------------------
    # T026 - Delete Blocked by Children
    # -------------------------------------------------------------------------

    def test_delete_blocked_by_children(self, test_db):
        """Verify deletion is blocked when ingredient has child ingredients.

        T026: Parent ingredients cannot be deleted if they have children.
        This prevents orphaning child ingredients.
        """
        session = test_db()

        # Arrange: Create parent ingredient
        parent = create_ingredient(
            {"display_name": "Test Parent Category", "category": "Test", "hierarchy_level": 0}
        )

        # Create child ingredient referencing the parent
        child = Ingredient(
            slug="test-child-ingredient",
            display_name="Test Child Ingredient",
            category="Test",
            hierarchy_level=1,
            parent_ingredient_id=parent.id,
        )
        session.add(child)
        session.commit()

        # Act: Check if deletion is allowed - should raise IngredientInUse
        with pytest.raises(IngredientInUse) as exc_info:
            can_delete_ingredient(parent.id, session=session)

        # Assert: Exception contains correct details
        assert exc_info.value.deps["children"] == 1

    # -------------------------------------------------------------------------
    # T027 - Delete with Snapshots Denormalizes
    # -------------------------------------------------------------------------

    def test_delete_with_snapshots_denormalizes(self, test_db):
        """Verify snapshot records preserve ingredient names on deletion.

        T027: When an ingredient with snapshot references is deleted,
        the snapshot records should have their names denormalized to preserve
        historical data, and the ingredient_id should be set to NULL.
        """
        session = test_db()

        # Arrange: Create a 3-level hierarchy
        l0 = Ingredient(
            slug="test-baking-category",
            display_name="Baking",
            category="Baking",
            hierarchy_level=0,
            parent_ingredient_id=None,
        )
        session.add(l0)
        session.flush()

        l1 = Ingredient(
            slug="test-flour-category",
            display_name="Flour",
            category="Baking",
            hierarchy_level=1,
            parent_ingredient_id=l0.id,
        )
        session.add(l1)
        session.flush()

        l2 = Ingredient(
            slug="test-all-purpose",
            display_name="All-Purpose",
            category="Baking",
            hierarchy_level=2,
            parent_ingredient_id=l1.id,
        )
        session.add(l2)
        session.flush()

        # Create an inventory snapshot
        snapshot = InventorySnapshot(name="Test Snapshot for Denorm", description="Test snapshot")
        session.add(snapshot)
        session.flush()

        # Create snapshot ingredient referencing the leaf ingredient
        snapshot_ingredient = SnapshotIngredient(
            snapshot_id=snapshot.id, ingredient_id=l2.id, quantity=5.0
        )
        session.add(snapshot_ingredient)
        session.commit()

        snapshot_ingredient_id = snapshot_ingredient.id
        l2_id = l2.id

        # Act: Delete the leaf ingredient (no blocking references other than snapshot)
        delete_ingredient_safe(l2_id, session=session)

        # Assert: Snapshot record should be preserved with denormalized names
        updated = (
            session.query(SnapshotIngredient)
            .filter(SnapshotIngredient.id == snapshot_ingredient_id)
            .first()
        )

        assert updated is not None
        assert updated.ingredient_id is None  # FK should be nullified
        assert updated.ingredient_name_snapshot == "All-Purpose"
        assert updated.parent_l1_name_snapshot == "Flour"
        assert updated.parent_l0_name_snapshot == "Baking"

    # -------------------------------------------------------------------------
    # T028 - Delete Cascades Aliases
    # -------------------------------------------------------------------------

    def test_delete_cascades_aliases(self, test_db):
        """Verify IngredientAlias records are cascade-deleted.

        T028: When an ingredient is deleted, all associated IngredientAlias
        records should be automatically removed (cascade delete via DB FK).

        Note: This test verifies the database-level CASCADE DELETE works correctly.
        The FK constraint on IngredientAlias.ingredient_id has ondelete="CASCADE".
        """
        session = test_db()

        # Arrange: Create an ingredient directly (not via service to avoid caching)
        ingredient = Ingredient(
            slug="test-powdered-sugar",
            display_name="Powdered Sugar",
            category="Sugars",
            hierarchy_level=2,
        )
        session.add(ingredient)
        session.flush()
        ingredient_id = ingredient.id

        # Create an alias for the ingredient
        alias = IngredientAlias(ingredient_id=ingredient_id, alias="Confectioner's Sugar")
        session.add(alias)
        session.commit()
        alias_id = alias.id

        # Verify alias exists
        assert (
            session.query(IngredientAlias).filter(IngredientAlias.id == alias_id).first()
            is not None
        )

        # Act: Delete the ingredient directly with session (bypassing ORM relationship handling)
        # This tests the database CASCADE constraint
        session.execute(Ingredient.__table__.delete().where(Ingredient.id == ingredient_id))
        session.commit()

        # Assert: Alias should be cascade-deleted by database FK constraint
        remaining = session.query(IngredientAlias).filter(IngredientAlias.id == alias_id).first()
        assert remaining is None

    # -------------------------------------------------------------------------
    # T029 - Delete Cascades Crosswalks
    # -------------------------------------------------------------------------

    def test_delete_cascades_crosswalks(self, test_db):
        """Verify IngredientCrosswalk records are cascade-deleted.

        T029: When an ingredient is deleted, all associated IngredientCrosswalk
        records should be automatically removed (cascade delete via DB FK).

        Note: This test verifies the database-level CASCADE DELETE works correctly.
        The FK constraint on IngredientCrosswalk.ingredient_id has ondelete="CASCADE".
        """
        session = test_db()

        # Arrange: Create an ingredient directly (not via service to avoid caching)
        ingredient = Ingredient(
            slug="test-honey", display_name="Honey", category="Sweeteners", hierarchy_level=2
        )
        session.add(ingredient)
        session.flush()
        ingredient_id = ingredient.id

        # Create a crosswalk entry for the ingredient
        crosswalk = IngredientCrosswalk(
            ingredient_id=ingredient_id, system="FoodOn", code="FOODON_12345"
        )
        session.add(crosswalk)
        session.commit()
        crosswalk_id = crosswalk.id

        # Verify crosswalk exists
        assert (
            session.query(IngredientCrosswalk)
            .filter(IngredientCrosswalk.id == crosswalk_id)
            .first()
            is not None
        )

        # Act: Delete the ingredient directly with session (bypassing ORM relationship handling)
        # This tests the database CASCADE constraint
        session.execute(Ingredient.__table__.delete().where(Ingredient.id == ingredient_id))
        session.commit()

        # Assert: Crosswalk should be cascade-deleted by database FK constraint
        remaining = (
            session.query(IngredientCrosswalk)
            .filter(IngredientCrosswalk.id == crosswalk_id)
            .first()
        )
        assert remaining is None

    # -------------------------------------------------------------------------
    # T030 - Slug Auto-Generation
    # -------------------------------------------------------------------------

    def test_slug_auto_generation(self, test_db):
        """Verify slugs are auto-generated from display_name.

        T030: When creating an ingredient, the slug should be automatically
        generated from the display_name using the project's slugification rules.
        """
        # Arrange & Act: Create an ingredient
        ingredient = create_ingredient({"display_name": "Brown Sugar", "category": "Sugars"})

        # Assert: Slug should be auto-generated from display_name
        assert ingredient.slug is not None
        assert ingredient.slug == "brown_sugar"

    # -------------------------------------------------------------------------
    # T031 - Slug Conflict Resolution
    # -------------------------------------------------------------------------

    def test_slug_conflict_resolution(self, test_db):
        """Verify slug conflicts are resolved with numeric suffixes.

        T031: When slugs would conflict (from similar display_names),
        subsequent slugs should have numeric suffixes (_1, _2, etc.).

        Note: display_name has a UNIQUE constraint, so we test with similar
        but not identical names that generate the same base slug.
        """
        # Arrange: Create first ingredient - base slug "vanilla_extract"
        first = create_ingredient({"display_name": "Vanilla Extract", "category": "Extracts"})
        assert first.slug == "vanilla_extract"

        # Act: Create second ingredient with name that would generate same base slug
        # "Vanilla-Extract" with hyphen becomes "vanilla_extract" base slug
        second = create_ingredient({"display_name": "Vanilla-Extract", "category": "Extracts"})

        # Assert: Second should have suffix due to slug collision
        assert second.slug == "vanilla_extract_1"

        # Act: Create third ingredient with another variant
        # "Vanilla  Extract" (double space) also becomes "vanilla_extract"
        third = create_ingredient({"display_name": "Vanilla  Extract", "category": "Extracts"})

        # Assert: Third should have incremented suffix
        assert third.slug == "vanilla_extract_2"

    # -------------------------------------------------------------------------
    # T032 - Field Name Normalization
    # -------------------------------------------------------------------------

    def test_field_name_normalization(self, test_db):
        """Verify 'name' field is normalized to 'display_name'.

        T032: For backward compatibility, when creating an ingredient with
        'name' instead of 'display_name', the field should be normalized.
        """
        # Arrange & Act: Use "name" instead of "display_name"
        ingredient = create_ingredient(
            {"name": "Cinnamon", "category": "Spices"}  # UI-style field name
        )

        # Assert: Should work with 'name' field
        assert ingredient.display_name == "Cinnamon"
        assert ingredient.slug == "cinnamon"
