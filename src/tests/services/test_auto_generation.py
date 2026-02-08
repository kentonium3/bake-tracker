"""Tests for F098 auto-generation of bare FinishedGoods.

WP03 - F098: Auto-Generation of FinishedGoods
WP05 - F098: Cascade Delete with Assembly Protection

Tests verify:
- find_bare_fg_for_unit() lookup works correctly
- auto_create_bare_finished_good() creates FG + Composition atomically
- Integration with save_recipe_with_yields() for EA yield types
- Duplicate prevention (no duplicate bare FGs)
- Weight/SERVING yield types do NOT trigger auto-generation
- cascade_delete_bare_fg() cleans up bare FG and Composition
- Assembly protection blocks deletion when bare FG is referenced
- Error messages list affected assembly names
"""

import pytest

from src.services.recipe_service import save_recipe_with_yields, create_recipe
from src.services import finished_unit_service, finished_good_service
from src.models import FinishedGood, Composition, AssemblyType
from src.services.database import session_scope
from src.services.exceptions import ValidationError


class TestFindBareFgForUnit:
    """Test find_bare_fg_for_unit() lookup function."""

    def test_returns_none_when_no_bare_fg(self, test_db):
        """Returns None when no bare FG exists for the FU."""
        test_db()

        recipe_data = {"name": "Test Cake", "category": "Cakes"}
        yield_types = [
            {
                "id": None,
                "display_name": "Test Cake",
                "yield_type": "SERVING",
                "items_per_batch": 8.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 1

        result = finished_good_service.find_bare_fg_for_unit(fus[0].id)
        assert result is None

    def test_finds_bare_fg_for_unit(self, test_db):
        """Finds the bare FG linked to a FU via Composition."""
        test_db()

        recipe_data = {"name": "Test Cookie", "category": "Cookies"}
        yield_types = [
            {
                "id": None,
                "display_name": "Test Cookie",
                "yield_type": "EA",
                "items_per_batch": 24.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 1

        fg = finished_good_service.find_bare_fg_for_unit(fus[0].id)
        assert fg is not None
        assert fg.assembly_type == AssemblyType.BARE
        assert fg.display_name == "Test Cookie"

    def test_find_with_session_parameter(self, test_db):
        """find_bare_fg_for_unit works with provided session."""
        test_db()

        recipe_data = {"name": "Session Test", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Session Test",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)

        with session_scope() as sess:
            fg = finished_good_service.find_bare_fg_for_unit(fus[0].id, session=sess)
            assert fg is not None
            assert fg.assembly_type == AssemblyType.BARE


class TestAutoCreateBareFg:
    """Test auto_create_bare_finished_good() core function."""

    def _create_fu(self, yield_type="SERVING"):
        """Helper to create a recipe + FU without auto-generation."""
        recipe = create_recipe(
            {"name": f"Test Recipe {yield_type}", "category": "Test"}
        )
        fu = finished_unit_service.create_finished_unit(
            display_name=f"Manual FU {yield_type}",
            recipe_id=recipe.id,
            yield_type=yield_type,
        )
        return fu

    def test_creates_bare_fg_with_composition(self, test_db):
        """Creates bare FG + single Composition linking to FU."""
        test_db()

        fu = self._create_fu("SERVING")

        fg = finished_good_service.auto_create_bare_finished_good(
            finished_unit_id=fu.id,
            display_name=fu.display_name,
        )

        assert fg is not None
        assert fg.assembly_type == AssemblyType.BARE
        assert fg.display_name == fu.display_name
        assert fg.id is not None

        # Verify Composition exists
        with session_scope() as sess:
            comps = (
                sess.query(Composition)
                .filter_by(assembly_id=fg.id)
                .all()
            )
            assert len(comps) == 1
            assert comps[0].finished_unit_id == fu.id
            assert comps[0].component_quantity == 1

    def test_raises_on_duplicate(self, test_db):
        """Raises ValidationError if bare FG already exists for FU."""
        test_db()

        fu = self._create_fu("SERVING")

        # First creation succeeds
        finished_good_service.auto_create_bare_finished_good(
            finished_unit_id=fu.id,
            display_name=fu.display_name,
        )

        # Second creation raises
        with pytest.raises(ValidationError, match="already exists"):
            finished_good_service.auto_create_bare_finished_good(
                finished_unit_id=fu.id,
                display_name=fu.display_name,
            )

    def test_creates_with_session_parameter(self, test_db):
        """auto_create_bare_finished_good works with provided session."""
        test_db()

        fu = self._create_fu("SERVING")

        with session_scope() as sess:
            fg = finished_good_service.auto_create_bare_finished_good(
                finished_unit_id=fu.id,
                display_name=fu.display_name,
                session=sess,
            )
            assert fg in sess
            assert fg.assembly_type == AssemblyType.BARE


class TestAutoCreationIntegration:
    """Test auto-creation integration via save_recipe_with_yields()."""

    def test_ea_yield_creates_bare_fg(self, test_db):
        """Recipe with EA yield -> FU created -> bare FG created -> Composition links them."""
        test_db()

        recipe_data = {"name": "Chocolate Cake", "category": "Cakes"}
        yield_types = [
            {
                "id": None,
                "display_name": "Chocolate Cake",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]

        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 1

        fg = finished_good_service.find_bare_fg_for_unit(fus[0].id)
        assert fg is not None
        assert fg.assembly_type == AssemblyType.BARE
        assert fg.display_name == "Chocolate Cake"

        # Verify Composition
        with session_scope() as sess:
            comps = (
                sess.query(Composition)
                .filter_by(assembly_id=fg.id)
                .all()
            )
            assert len(comps) == 1
            assert comps[0].finished_unit_id == fus[0].id
            assert comps[0].component_quantity == 1

    def test_bare_fg_has_correct_assembly_type(self, test_db):
        """Bare FG uses AssemblyType.BARE enum (not string literal)."""
        test_db()

        recipe_data = {"name": "Sugar Cookie", "category": "Cookies"}
        yield_types = [
            {
                "id": None,
                "display_name": "Sugar Cookie",
                "yield_type": "EA",
                "items_per_batch": 12.0,
            },
        ]

        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fg = finished_good_service.find_bare_fg_for_unit(fus[0].id)

        assert fg.assembly_type == AssemblyType.BARE
        assert fg.assembly_type.value == "bare"

    def test_bare_fg_inherits_display_name(self, test_db):
        """Bare FG display_name matches the source FU display_name."""
        test_db()

        recipe_data = {"name": "Brownie", "category": "Bars"}
        yield_types = [
            {
                "id": None,
                "display_name": "Fudge Brownie",
                "yield_type": "EA",
                "items_per_batch": 16.0,
            },
        ]

        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fg = finished_good_service.find_bare_fg_for_unit(fus[0].id)

        assert fg.display_name == "Fudge Brownie"
        assert fus[0].display_name == "Fudge Brownie"

    def test_multiple_ea_yields_create_separate_bare_fgs(self, test_db):
        """Recipe with multiple EA yields creates separate FU+FG pairs."""
        test_db()

        recipe_data = {"name": "Variety Pack", "category": "Cookies"}
        yield_types = [
            {
                "id": None,
                "display_name": "Chocolate Chip",
                "yield_type": "EA",
                "items_per_batch": 24.0,
            },
            {
                "id": None,
                "display_name": "Oatmeal Raisin",
                "yield_type": "EA",
                "items_per_batch": 24.0,
            },
        ]

        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 2

        for fu in fus:
            fg = finished_good_service.find_bare_fg_for_unit(fu.id)
            assert fg is not None
            assert fg.assembly_type == AssemblyType.BARE
            assert fg.display_name == fu.display_name


class TestAutoCreationEdgeCases:
    """Test edge cases: duplicate prevention, SERVING/weight skipping."""

    def test_second_save_no_duplicate_bare_fg(self, test_db):
        """Second save of same recipe doesn't create duplicate bare FG."""
        test_db()

        recipe_data = {"name": "Resave Test", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Resave Unit",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]

        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fg1 = finished_good_service.find_bare_fg_for_unit(fus[0].id)
        assert fg1 is not None

        # Re-save with same FU (id provided = update, not create)
        yield_types_update = [
            {
                "id": fus[0].id,
                "display_name": "Resave Unit",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        save_recipe_with_yields(
            {"name": "Resave Test", "category": "Test"},
            yield_types_update,
            recipe_id=recipe.id,
        )

        # Still exactly one bare FG
        fg2 = finished_good_service.find_bare_fg_for_unit(fus[0].id)
        assert fg2 is not None
        assert fg2.id == fg1.id

    def test_serving_yield_no_bare_fg(self, test_db):
        """Recipe with SERVING yield type -> FU created, NO bare FG."""
        test_db()

        recipe_data = {"name": "Serving Only", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Serving Only",
                "yield_type": "SERVING",
                "items_per_batch": 8.0,
            },
        ]

        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 1

        fg = finished_good_service.find_bare_fg_for_unit(fus[0].id)
        assert fg is None

    def test_mixed_yields_only_ea_gets_bare_fg(self, test_db):
        """Recipe with EA + SERVING -> only EA yield gets bare FG."""
        test_db()

        recipe_data = {"name": "Mixed Yields", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "EA Unit",
                "yield_type": "EA",
                "items_per_batch": 12.0,
            },
            {
                "id": None,
                "display_name": "Serving Unit",
                "yield_type": "SERVING",
                "items_per_batch": 6.0,
            },
        ]

        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 2

        ea_fu = next(fu for fu in fus if fu.yield_type == "EA")
        serving_fu = next(fu for fu in fus if fu.yield_type == "SERVING")

        assert finished_good_service.find_bare_fg_for_unit(ea_fu.id) is not None
        assert finished_good_service.find_bare_fg_for_unit(serving_fu.id) is None

    def test_bare_fg_slug_unique_for_similar_names(self, test_db):
        """Bare FGs get unique slugs even with similar display names."""
        test_db()

        # Create two recipes with same display_name for their FUs
        for i in range(2):
            recipe_data = {"name": f"Cookie Recipe {i+1}", "category": "Cookies"}
            yield_types = [
                {
                    "id": None,
                    "display_name": "Chocolate Chip Cookie",
                    "yield_type": "EA",
                    "items_per_batch": 24.0,
                },
            ]
            save_recipe_with_yields(recipe_data, yield_types)

        # Both FGs should exist with unique slugs
        with session_scope() as sess:
            bare_fgs = (
                sess.query(FinishedGood)
                .filter(FinishedGood.assembly_type == AssemblyType.BARE)
                .all()
            )
            assert len(bare_fgs) == 2
            slugs = {fg.slug for fg in bare_fgs}
            assert len(slugs) == 2  # Slugs are unique

    def test_no_yield_types_no_bare_fg(self, test_db):
        """Recipe with no yield types creates no FUs and no bare FGs."""
        test_db()

        recipe_data = {"name": "Empty Recipe", "category": "Test"}
        recipe = save_recipe_with_yields(recipe_data, [])

        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 0

        # No bare FGs should exist
        with session_scope() as sess:
            bare_fgs = (
                sess.query(FinishedGood)
                .filter(FinishedGood.assembly_type == AssemblyType.BARE)
                .all()
            )
            assert len(bare_fgs) == 0


# ============================================================================
# WP05: Cascade Delete with Assembly Protection
# ============================================================================


class TestCascadeDeleteBareFg:
    """Test cascade_delete_bare_fg() clean deletion (T029)."""

    def test_cascade_deletes_bare_fg_and_composition(self, test_db):
        """Delete FU -> bare FG and Composition both deleted."""
        test_db()

        recipe_data = {"name": "Delete Test", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Delete Me",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fu = fus[0]

        fg = finished_good_service.find_bare_fg_for_unit(fu.id)
        assert fg is not None
        fg_id = fg.id

        # Cascade delete
        result = finished_good_service.cascade_delete_bare_fg(fu.id)
        assert result is True

        # Bare FG gone
        assert finished_good_service.find_bare_fg_for_unit(fu.id) is None

        # No orphaned Compositions
        with session_scope() as sess:
            comps = (
                sess.query(Composition)
                .filter(Composition.assembly_id == fg_id)
                .all()
            )
            assert len(comps) == 0

    def test_cascade_returns_false_when_no_bare_fg(self, test_db):
        """FU with no bare FG (SERVING type) -> returns False, no error."""
        test_db()

        recipe_data = {"name": "Serving Delete", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Serving Only",
                "yield_type": "SERVING",
                "items_per_batch": 8.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fu = fus[0]

        result = finished_good_service.cascade_delete_bare_fg(fu.id)
        assert result is False

    def test_recipe_delete_cascades_to_bare_fg(self, test_db):
        """Removing EA yield from recipe -> bare FG deleted via cascade."""
        test_db()

        recipe_data = {"name": "Cascade Via Recipe", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Will Be Removed",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fu = fus[0]
        fg = finished_good_service.find_bare_fg_for_unit(fu.id)
        assert fg is not None

        # Remove the yield type (empty list = delete all)
        save_recipe_with_yields(
            {"name": "Cascade Via Recipe", "category": "Test"},
            [],
            recipe_id=recipe.id,
        )

        # Both FU and bare FG gone
        remaining_fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(remaining_fus) == 0

        with session_scope() as sess:
            bare_fgs = (
                sess.query(FinishedGood)
                .filter(FinishedGood.assembly_type == AssemblyType.BARE)
                .all()
            )
            assert len(bare_fgs) == 0

    def test_no_orphaned_records_after_delete(self, test_db):
        """After deletion, no orphaned Composition records remain."""
        test_db()

        recipe_data = {"name": "Orphan Check", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Orphan Test",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)

        # Record composition count before
        with session_scope() as sess:
            comp_count_before = sess.query(Composition).count()
            assert comp_count_before >= 1  # At least the bare FG composition

        # Delete via recipe update (remove yield type)
        save_recipe_with_yields(
            {"name": "Orphan Check", "category": "Test"},
            [],
            recipe_id=recipe.id,
        )

        # All compositions for this recipe's FGs gone
        with session_scope() as sess:
            bare_fgs = (
                sess.query(FinishedGood)
                .filter(FinishedGood.assembly_type == AssemblyType.BARE)
                .all()
            )
            assert len(bare_fgs) == 0
            # No compositions left since we deleted everything
            comp_count_after = sess.query(Composition).count()
            assert comp_count_after == 0


class TestAssemblyProtection:
    """Test deletion blocked by assembly reference (T030)."""

    def _create_recipe_with_bare_fg(self, name="Test Recipe"):
        """Helper: create recipe with EA yield, return (recipe, fu, bare_fg)."""
        recipe = save_recipe_with_yields(
            {"name": name, "category": "Test"},
            [
                {
                    "id": None,
                    "display_name": f"{name} Unit",
                    "yield_type": "EA",
                    "items_per_batch": 1.0,
                },
            ],
        )
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fu = fus[0]
        fg = finished_good_service.find_bare_fg_for_unit(fu.id)
        return recipe, fu, fg

    def test_deletion_blocked_when_bare_fg_in_assembly(self, test_db):
        """Deletion blocked with ValidationError when bare FG used in assembly."""
        test_db()

        recipe, fu, bare_fg = self._create_recipe_with_bare_fg("Protected Item")

        # Create an assembled FG that uses the bare FG as component
        assembled_fg = finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Holiday Gift Box",
            assembly_type=AssemblyType.BUNDLE,
            components=[
                {"type": "finished_good", "id": bare_fg.id, "quantity": 2},
            ],
        )

        # Attempting to cascade-delete should be blocked
        with pytest.raises(ValidationError, match="Cannot delete"):
            finished_good_service.cascade_delete_bare_fg(fu.id)

    def test_error_message_lists_assembly_names(self, test_db):
        """Error message includes assembly display names."""
        test_db()

        recipe, fu, bare_fg = self._create_recipe_with_bare_fg("Named Item")

        finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Gift Basket Alpha",
            assembly_type=AssemblyType.BUNDLE,
            components=[
                {"type": "finished_good", "id": bare_fg.id, "quantity": 1},
            ],
        )

        with pytest.raises(ValidationError, match="Gift Basket Alpha"):
            finished_good_service.cascade_delete_bare_fg(fu.id)

    def test_records_intact_after_blocked_deletion(self, test_db):
        """After blocked deletion, all records still intact."""
        test_db()

        recipe, fu, bare_fg = self._create_recipe_with_bare_fg("Intact Check")
        bare_fg_id = bare_fg.id

        finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Blocking Assembly",
            assembly_type=AssemblyType.BUNDLE,
            components=[
                {"type": "finished_good", "id": bare_fg.id, "quantity": 1},
            ],
        )

        # Attempt deletion (will be blocked)
        with pytest.raises(ValidationError):
            finished_good_service.cascade_delete_bare_fg(fu.id)

        # Bare FG still exists
        fg_after = finished_good_service.find_bare_fg_for_unit(fu.id)
        assert fg_after is not None
        assert fg_after.id == bare_fg_id

        # Composition still exists
        with session_scope() as sess:
            comps = (
                sess.query(Composition)
                .filter(Composition.assembly_id == bare_fg_id)
                .all()
            )
            assert len(comps) == 1

    def test_multiple_assemblies_listed_in_error(self, test_db):
        """With 2 assemblies referencing, both names listed in error."""
        test_db()

        recipe, fu, bare_fg = self._create_recipe_with_bare_fg("Multi Ref")

        # Create two assemblies referencing the same bare FG
        finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Assembly One",
            assembly_type=AssemblyType.BUNDLE,
            components=[
                {"type": "finished_good", "id": bare_fg.id, "quantity": 1},
            ],
        )
        finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Assembly Two",
            assembly_type=AssemblyType.BUNDLE,
            components=[
                {"type": "finished_good", "id": bare_fg.id, "quantity": 1},
            ],
        )

        with pytest.raises(ValidationError, match="2 assembled product") as exc_info:
            finished_good_service.cascade_delete_bare_fg(fu.id)

        error_msg = exc_info.value.errors[0]
        assert "Assembly One" in error_msg
        assert "Assembly Two" in error_msg

    def test_recipe_update_blocked_when_removing_referenced_fu(self, test_db):
        """Removing a yield type whose bare FG is in an assembly -> blocked."""
        test_db()

        recipe, fu, bare_fg = self._create_recipe_with_bare_fg("Recipe Block")

        finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Blocking Box",
            assembly_type=AssemblyType.BUNDLE,
            components=[
                {"type": "finished_good", "id": bare_fg.id, "quantity": 1},
            ],
        )

        # Try removing the yield type via recipe update
        with pytest.raises(ValidationError, match="Cannot delete"):
            save_recipe_with_yields(
                {"name": "Recipe Block", "category": "Test"},
                [],
                recipe_id=recipe.id,
            )


class TestGetAssemblyReferences:
    """Test get_assembly_references() function."""

    def test_returns_empty_when_no_references(self, test_db):
        """No assemblies reference this FG -> returns empty list."""
        test_db()

        recipe_data = {"name": "No Refs", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Unreferenced",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fg = finished_good_service.find_bare_fg_for_unit(fus[0].id)

        refs = finished_good_service.get_assembly_references(fg.id)
        assert refs == []

    def test_returns_referencing_assemblies(self, test_db):
        """Returns list of assemblies that use this FG as component."""
        test_db()

        recipe_data = {"name": "Referenced", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Component FG",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fg = finished_good_service.find_bare_fg_for_unit(fus[0].id)

        assembled = finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Parent Assembly",
            assembly_type=AssemblyType.BUNDLE,
            components=[
                {"type": "finished_good", "id": fg.id, "quantity": 1},
            ],
        )

        refs = finished_good_service.get_assembly_references(fg.id)
        assert len(refs) == 1
        assert refs[0].display_name == "Parent Assembly"
