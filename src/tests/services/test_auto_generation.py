"""Tests for F098 auto-generation of bare FinishedGoods.

WP03 - F098: Auto-Generation of FinishedGoods
WP04 - F098: Propagate FU Updates to Bare FG
WP05 - F098: Cascade Delete with Assembly Protection
WP07 - F098: Migration of Existing Bare FinishedGoods

Tests verify:
- find_bare_fg_for_unit() lookup works correctly
- auto_create_bare_finished_good() creates FG + Composition atomically
- Integration with save_recipe_with_yields() for EA yield types
- Duplicate prevention (no duplicate bare FGs)
- Weight/SERVING yield types do NOT trigger auto-generation
- sync_bare_finished_good() propagates name and slug changes
- Name propagation within same transaction
- Edge cases: no bare FG, unchanged name, slug collision
- cascade_delete_bare_fg() cleans up bare FG and Composition
- Assembly protection blocks deletion when bare FG is referenced
- Error messages list affected assembly names
- identify_bare_fg_candidates() finds FGs needing reclassification
- migrate_bare_finished_goods() reclassifies BUNDLE->BARE and creates missing bare FGs

WP08 - F098: Bulk Import Auto-Generation

Tests verify:
- Bulk FU import auto-creates bare FGs for EA yield types
- Non-EA FUs do not get bare FGs during import
- Backward compatibility (FUs without yield_type still import)
- Duplicate handling and slug uniqueness during bulk import
- Transactional integrity (all or nothing)
- Re-import does not create duplicate FGs
"""

import pytest

from src.services.recipe_service import save_recipe_with_yields, create_recipe
from src.services import finished_unit_service, finished_good_service
from src.services.catalog_import_service import import_finished_units
from src.models import FinishedGood, FinishedUnit, Composition, AssemblyType, Recipe
from src.models.finished_unit import YieldMode
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
# WP04: Propagate FU Updates to Bare FG
# ============================================================================


class TestSyncBareFg:
    """Test sync_bare_finished_good() propagation (T023)."""

    def test_rename_fu_updates_bare_fg_display_name(self, test_db):
        """Renaming FU -> bare FG display_name updated."""
        test_db()

        recipe_data = {"name": "Original Cookie", "category": "Cookies"}
        yield_types = [
            {
                "id": None,
                "display_name": "Original Cookie",
                "yield_type": "EA",
                "items_per_batch": 24.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fu = fus[0]

        fg_before = finished_good_service.find_bare_fg_for_unit(fu.id)
        assert fg_before.display_name == "Original Cookie"

        # Rename via save_recipe_with_yields update path
        yield_types_update = [
            {
                "id": fu.id,
                "display_name": "Renamed Cookie",
                "yield_type": "EA",
                "items_per_batch": 24.0,
            },
        ]
        save_recipe_with_yields(
            {"name": "Original Cookie", "category": "Cookies"},
            yield_types_update,
            recipe_id=recipe.id,
        )

        fg_after = finished_good_service.find_bare_fg_for_unit(fu.id)
        assert fg_after.display_name == "Renamed Cookie"

    def test_rename_fu_regenerates_bare_fg_slug(self, test_db):
        """Renaming FU -> bare FG slug regenerated from new name."""
        test_db()

        recipe_data = {"name": "Slug Test", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Old Name",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fu = fus[0]

        fg_before = finished_good_service.find_bare_fg_for_unit(fu.id)
        old_slug = fg_before.slug
        assert "old-name" in old_slug

        # Rename
        yield_types_update = [
            {
                "id": fu.id,
                "display_name": "New Name",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        save_recipe_with_yields(
            {"name": "Slug Test", "category": "Test"},
            yield_types_update,
            recipe_id=recipe.id,
        )

        fg_after = finished_good_service.find_bare_fg_for_unit(fu.id)
        assert fg_after.slug != old_slug
        assert "new-name" in fg_after.slug

    def test_both_name_changes_propagated_atomically(self, test_db):
        """Name and slug update within same transaction."""
        test_db()

        recipe_data = {"name": "Atomic Test", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Before Rename",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fu = fus[0]

        # Rename atomically via session
        with session_scope() as sess:
            result = finished_good_service.sync_bare_finished_good(
                finished_unit_id=fu.id,
                display_name="After Rename",
                session=sess,
            )
            assert result is not None
            assert result.display_name == "After Rename"
            assert "after-rename" in result.slug

    def test_sync_all_changes_in_same_transaction(self, test_db):
        """Verify atomicity: all changes in single transaction."""
        test_db()

        recipe_data = {"name": "Tx Test", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Transaction Test",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fu = fus[0]

        fg_before = finished_good_service.find_bare_fg_for_unit(fu.id)
        assert fg_before.display_name == "Transaction Test"

        # Update via the integration path (save_recipe_with_yields)
        yield_types_update = [
            {
                "id": fu.id,
                "display_name": "Updated Transaction Test",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        save_recipe_with_yields(
            {"name": "Tx Test", "category": "Test"},
            yield_types_update,
            recipe_id=recipe.id,
        )

        fg_after = finished_good_service.find_bare_fg_for_unit(fu.id)
        assert fg_after.display_name == "Updated Transaction Test"
        assert fg_after.id == fg_before.id  # Same FG, not recreated


class TestSyncBareFgEdgeCases:
    """Test edge cases in propagation (T024)."""

    def test_sync_returns_none_for_serving_type(self, test_db):
        """FU with no bare FG (SERVING type) -> sync returns None, no error."""
        test_db()

        recipe_data = {"name": "Serving Sync", "category": "Test"}
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

        result = finished_good_service.sync_bare_finished_good(
            finished_unit_id=fu.id,
            display_name="New Name",
        )
        assert result is None

    def test_no_update_when_name_unchanged(self, test_db):
        """Update FU name but don't change it -> no unnecessary FG update."""
        test_db()

        recipe_data = {"name": "No Change", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Same Name",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        fu = fus[0]

        fg_before = finished_good_service.find_bare_fg_for_unit(fu.id)
        old_slug = fg_before.slug

        # Re-save with same name
        yield_types_update = [
            {
                "id": fu.id,
                "display_name": "Same Name",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        save_recipe_with_yields(
            {"name": "No Change", "category": "Test"},
            yield_types_update,
            recipe_id=recipe.id,
        )

        fg_after = finished_good_service.find_bare_fg_for_unit(fu.id)
        assert fg_after.slug == old_slug  # Slug unchanged
        assert fg_after.display_name == "Same Name"

    def test_rename_one_fu_only_its_bare_fg_affected(self, test_db):
        """Rename one FU -> only its bare FG affected, others unchanged."""
        test_db()

        recipe_data = {"name": "Multi FU", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Cookie A",
                "yield_type": "EA",
                "items_per_batch": 12.0,
            },
            {
                "id": None,
                "display_name": "Cookie B",
                "yield_type": "EA",
                "items_per_batch": 12.0,
            },
        ]
        recipe = save_recipe_with_yields(recipe_data, yield_types)
        fus = finished_unit_service.get_units_by_recipe(recipe.id)
        assert len(fus) == 2

        fu_a = next(fu for fu in fus if fu.display_name == "Cookie A")
        fu_b = next(fu for fu in fus if fu.display_name == "Cookie B")

        fg_b_before = finished_good_service.find_bare_fg_for_unit(fu_b.id)
        fg_b_slug_before = fg_b_before.slug

        # Rename only Cookie A
        yield_types_update = [
            {
                "id": fu_a.id,
                "display_name": "Cookie A Renamed",
                "yield_type": "EA",
                "items_per_batch": 12.0,
            },
            {
                "id": fu_b.id,
                "display_name": "Cookie B",
                "yield_type": "EA",
                "items_per_batch": 12.0,
            },
        ]
        save_recipe_with_yields(
            {"name": "Multi FU", "category": "Test"},
            yield_types_update,
            recipe_id=recipe.id,
        )

        fg_a_after = finished_good_service.find_bare_fg_for_unit(fu_a.id)
        fg_b_after = finished_good_service.find_bare_fg_for_unit(fu_b.id)

        assert fg_a_after.display_name == "Cookie A Renamed"
        assert fg_b_after.display_name == "Cookie B"
        assert fg_b_after.slug == fg_b_slug_before  # B unchanged

    def test_slug_collision_on_rename_resolved(self, test_db):
        """Slug collision on rename -> resolved with suffix."""
        test_db()

        # Create two recipes with different FU names
        recipe1 = save_recipe_with_yields(
            {"name": "Recipe 1", "category": "Test"},
            [
                {
                    "id": None,
                    "display_name": "Target Name",
                    "yield_type": "EA",
                    "items_per_batch": 1.0,
                },
            ],
        )
        recipe2 = save_recipe_with_yields(
            {"name": "Recipe 2", "category": "Test"},
            [
                {
                    "id": None,
                    "display_name": "Other Name",
                    "yield_type": "EA",
                    "items_per_batch": 1.0,
                },
            ],
        )

        fus2 = finished_unit_service.get_units_by_recipe(recipe2.id)
        fu2 = fus2[0]

        # Rename FU2 to same name as FU1 (slug collision)
        yield_types_update = [
            {
                "id": fu2.id,
                "display_name": "Target Name",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        save_recipe_with_yields(
            {"name": "Recipe 2", "category": "Test"},
            yield_types_update,
            recipe_id=recipe2.id,
        )

        fg2 = finished_good_service.find_bare_fg_for_unit(fu2.id)
        assert fg2.display_name == "Target Name"
        # Slug should be unique (e.g., "target-name-2")
        assert fg2.slug.startswith("target-name")

        # Verify both FGs have unique slugs
        fus1 = finished_unit_service.get_units_by_recipe(recipe1.id)
        fg1 = finished_good_service.find_bare_fg_for_unit(fus1[0].id)
        assert fg1.slug != fg2.slug

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


# ============================================================================
# WP07: Migration of Existing Bare FinishedGoods
# ============================================================================


class TestIdentifyBareFgCandidates:
    """Test identify_bare_fg_candidates() analysis function (T040)."""

    def test_finds_bundle_with_single_fu_component(self, test_db):
        """FG with single FU component + BUNDLE type -> identified as candidate."""
        test_db()

        # Manually create a BUNDLE FG with single FU component (pre-F098 pattern)
        recipe = create_recipe({"name": "Manual Recipe", "category": "Test"})
        fu = finished_unit_service.create_finished_unit(
            display_name="Manual Unit",
            recipe_id=recipe.id,
            yield_type="EA",
        )
        fg = finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Manual Bundle",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": fu.id, "quantity": 1}],
        )

        candidates = finished_good_service.identify_bare_fg_candidates()
        assert len(candidates) == 1
        assert candidates[0]["fg_id"] == fg.id
        assert candidates[0]["fu_id"] == fu.id
        assert candidates[0]["needs_reclassification"] is True

    def test_already_bare_identified_as_correct(self, test_db):
        """FG with BARE type -> identified but needs_reclassification=False."""
        test_db()

        recipe_data = {"name": "Auto Recipe", "category": "Test"}
        yield_types = [
            {
                "id": None,
                "display_name": "Auto Unit",
                "yield_type": "EA",
                "items_per_batch": 1.0,
            },
        ]
        save_recipe_with_yields(recipe_data, yield_types)

        candidates = finished_good_service.identify_bare_fg_candidates()
        assert len(candidates) == 1
        assert candidates[0]["needs_reclassification"] is False

    def test_multi_component_fg_not_identified(self, test_db):
        """FG with multiple components -> NOT a candidate."""
        test_db()

        recipe = create_recipe({"name": "Multi Recipe", "category": "Test"})
        fu1 = finished_unit_service.create_finished_unit(
            display_name="Unit A", recipe_id=recipe.id, yield_type="EA",
        )
        fu2 = finished_unit_service.create_finished_unit(
            display_name="Unit B", recipe_id=recipe.id, yield_type="EA",
        )
        finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Multi Bundle",
            assembly_type=AssemblyType.BUNDLE,
            components=[
                {"type": "finished_unit", "id": fu1.id, "quantity": 1},
                {"type": "finished_unit", "id": fu2.id, "quantity": 1},
            ],
        )

        candidates = finished_good_service.identify_bare_fg_candidates()
        assert len(candidates) == 0

    def test_empty_database(self, test_db):
        """Empty database -> no candidates, no error."""
        test_db()

        candidates = finished_good_service.identify_bare_fg_candidates()
        assert candidates == []


class TestMigrateBareFgs:
    """Test migrate_bare_finished_goods() migration function (T040)."""

    def test_reclassifies_bundle_to_bare(self, test_db):
        """FG with single FU component + BUNDLE -> reclassified to BARE."""
        test_db()

        recipe = create_recipe({"name": "Migrate Recipe", "category": "Test"})
        fu = finished_unit_service.create_finished_unit(
            display_name="Migrate Unit",
            recipe_id=recipe.id,
            yield_type="EA",
        )
        fg = finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Migrate Bundle",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": fu.id, "quantity": 1}],
        )

        result = finished_good_service.migrate_bare_finished_goods(dry_run=False)
        assert result["reclassified"] == 1
        assert result["already_correct"] == 0

        # Verify reclassification
        with session_scope() as sess:
            updated_fg = sess.get(FinishedGood, fg.id)
            assert updated_fg.assembly_type == AssemblyType.BARE

    def test_already_correct_skipped(self, test_db):
        """FG already BARE -> counted as already_correct, not modified."""
        test_db()

        save_recipe_with_yields(
            {"name": "Already Bare", "category": "Test"},
            [
                {
                    "id": None,
                    "display_name": "Already Bare Unit",
                    "yield_type": "EA",
                    "items_per_batch": 1.0,
                },
            ],
        )

        result = finished_good_service.migrate_bare_finished_goods(dry_run=False)
        assert result["reclassified"] == 0
        assert result["already_correct"] == 1

    def test_creates_bare_fg_for_orphaned_ea_fu(self, test_db):
        """EA FU without bare FG -> bare FG auto-created."""
        test_db()

        recipe = create_recipe({"name": "Orphan FU", "category": "Test"})
        fu = finished_unit_service.create_finished_unit(
            display_name="Lonely FU",
            recipe_id=recipe.id,
            yield_type="EA",
        )

        # Verify no bare FG yet
        assert finished_good_service.find_bare_fg_for_unit(fu.id) is None

        result = finished_good_service.migrate_bare_finished_goods(dry_run=False)
        assert result["fus_gained_bare_fg"] == 1

        # Verify bare FG now exists
        fg = finished_good_service.find_bare_fg_for_unit(fu.id)
        assert fg is not None
        assert fg.assembly_type == AssemblyType.BARE
        assert fg.display_name == "Lonely FU"

    def test_dry_run_reports_without_modifying(self, test_db):
        """dry_run=True reports changes without modifying data."""
        test_db()

        recipe = create_recipe({"name": "Dry Run", "category": "Test"})
        fu = finished_unit_service.create_finished_unit(
            display_name="Dry Run Unit",
            recipe_id=recipe.id,
            yield_type="EA",
        )
        fg = finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Dry Run Bundle",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": fu.id, "quantity": 1}],
        )

        result = finished_good_service.migrate_bare_finished_goods(dry_run=True)
        assert result["reclassified"] == 1

        # Verify NOT actually changed
        with session_scope() as sess:
            unchanged_fg = sess.get(FinishedGood, fg.id)
            assert unchanged_fg.assembly_type == AssemblyType.BUNDLE

    def test_idempotent_second_run(self, test_db):
        """Running migration twice produces same result."""
        test_db()

        recipe = create_recipe({"name": "Idempotent", "category": "Test"})
        fu = finished_unit_service.create_finished_unit(
            display_name="Idempotent Unit",
            recipe_id=recipe.id,
            yield_type="EA",
        )
        finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Idempotent Bundle",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": fu.id, "quantity": 1}],
        )

        # First run
        result1 = finished_good_service.migrate_bare_finished_goods(dry_run=False)
        assert result1["reclassified"] == 1

        # Second run - should be all already_correct
        result2 = finished_good_service.migrate_bare_finished_goods(dry_run=False)
        assert result2["reclassified"] == 0
        assert result2["already_correct"] == 1

    def test_serving_fu_not_given_bare_fg(self, test_db):
        """SERVING FUs are NOT given bare FGs during migration."""
        test_db()

        recipe = create_recipe({"name": "Serving", "category": "Test"})
        finished_unit_service.create_finished_unit(
            display_name="Serving Only",
            recipe_id=recipe.id,
            yield_type="SERVING",
        )

        result = finished_good_service.migrate_bare_finished_goods(dry_run=False)
        assert result["fus_gained_bare_fg"] == 0


class TestMigrateBareFgsEdgeCases:
    """Test migration edge cases (T041)."""

    def test_preserves_notes_during_reclassification(self, test_db):
        """User-added notes preserved when reclassifying BUNDLE -> BARE."""
        test_db()

        recipe = create_recipe({"name": "Notes Test", "category": "Test"})
        fu = finished_unit_service.create_finished_unit(
            display_name="Notes Unit",
            recipe_id=recipe.id,
            yield_type="EA",
        )
        fg = finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Notes Bundle",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": fu.id, "quantity": 1}],
            notes="User added these notes",
        )

        finished_good_service.migrate_bare_finished_goods(dry_run=False)

        with session_scope() as sess:
            updated_fg = sess.get(FinishedGood, fg.id)
            assert updated_fg.assembly_type == AssemblyType.BARE
            assert updated_fg.notes == "User added these notes"

    def test_preserves_description_during_reclassification(self, test_db):
        """User-added description preserved when reclassifying BUNDLE -> BARE."""
        test_db()

        recipe = create_recipe({"name": "Desc Test", "category": "Test"})
        fu = finished_unit_service.create_finished_unit(
            display_name="Desc Unit",
            recipe_id=recipe.id,
            yield_type="EA",
        )
        fg = finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Desc Bundle",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": fu.id, "quantity": 1}],
            description="A detailed description",
        )

        finished_good_service.migrate_bare_finished_goods(dry_run=False)

        with session_scope() as sess:
            updated_fg = sess.get(FinishedGood, fg.id)
            assert updated_fg.assembly_type == AssemblyType.BARE
            assert updated_fg.description == "A detailed description"

    def test_quantity_greater_than_one_not_candidate(self, test_db):
        """FG with single FU component but quantity > 1 -> NOT a candidate."""
        test_db()

        recipe = create_recipe({"name": "Qty Test", "category": "Test"})
        fu = finished_unit_service.create_finished_unit(
            display_name="Qty Unit",
            recipe_id=recipe.id,
            yield_type="EA",
        )
        # Create BUNDLE with quantity=2 (not bare pattern)
        fg = finished_good_service.FinishedGoodService.create_finished_good(
            display_name="Qty Bundle",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": fu.id, "quantity": 2}],
        )

        candidates = finished_good_service.identify_bare_fg_candidates()
        fg_ids = [c["fg_id"] for c in candidates]
        assert fg.id not in fg_ids

    def test_empty_database_migration(self, test_db):
        """Empty database -> migration completes without error."""
        test_db()

        result = finished_good_service.migrate_bare_finished_goods(dry_run=False)
        assert result["reclassified"] == 0
        assert result["already_correct"] == 0
        assert result["fus_gained_bare_fg"] == 0
        assert result["orphaned_bare_fgs"] == 0


# =============================================================================
# WP08 - Bulk Import Auto-Generation Tests
# =============================================================================


def _create_test_recipe(name="Import Test Recipe", category="Test"):
    """Helper to create a recipe for import tests."""
    with session_scope() as session:
        recipe = Recipe(name=name, category=category)
        session.add(recipe)
        session.flush()
        return recipe.id, recipe.name


class TestBulkImportAutoGeneration:
    """WP08: Test auto-generation of bare FGs during bulk FU import."""

    def test_import_ea_fu_creates_bare_fg(self, test_db):
        """Import of EA yield_type FU auto-creates a bare FinishedGood."""
        test_db()
        recipe_id, recipe_name = _create_test_recipe()

        data = [
            {
                "slug": "import-ea-cookie",
                "display_name": "Imported EA Cookie",
                "recipe_name": recipe_name,
                "yield_type": "EA",
                "yield_mode": "discrete_count",
                "items_per_batch": 24,
                "item_unit": "cookie",
            }
        ]

        result = import_finished_units(data, mode="add")

        assert result.entity_counts["finished_units"].added == 1
        assert result.has_errors is False

        # Verify FU was created with correct yield_type
        with session_scope() as sess:
            fu = sess.query(FinishedUnit).filter_by(slug="import-ea-cookie").first()
            assert fu is not None
            assert fu.yield_type == "EA"

            # Verify bare FG was auto-created
            fg = finished_good_service.find_bare_fg_for_unit(fu.id, session=sess)
            assert fg is not None
            assert fg.assembly_type == AssemblyType.BARE
            assert fg.display_name == "Imported EA Cookie"

            # Verify Composition links them
            comp = (
                sess.query(Composition)
                .filter_by(assembly_id=fg.id, finished_unit_id=fu.id)
                .first()
            )
            assert comp is not None
            assert comp.component_quantity == 1

    def test_import_serving_fu_no_bare_fg(self, test_db):
        """Import of SERVING yield_type FU does NOT create a bare FG."""
        test_db()
        recipe_id, recipe_name = _create_test_recipe()

        data = [
            {
                "slug": "import-serving-slice",
                "display_name": "Imported Cake Slice",
                "recipe_name": recipe_name,
                "yield_type": "SERVING",
                "yield_mode": "discrete_count",
                "items_per_batch": 8,
                "item_unit": "slice",
            }
        ]

        result = import_finished_units(data, mode="add")

        assert result.entity_counts["finished_units"].added == 1

        with session_scope() as sess:
            fu = sess.query(FinishedUnit).filter_by(slug="import-serving-slice").first()
            assert fu is not None
            assert fu.yield_type == "SERVING"

            fg = finished_good_service.find_bare_fg_for_unit(fu.id, session=sess)
            assert fg is None

    def test_import_without_yield_type_defaults_to_serving(self, test_db):
        """FU imported without yield_type defaults to SERVING (backward compat)."""
        test_db()
        recipe_id, recipe_name = _create_test_recipe()

        data = [
            {
                "slug": "import-no-yield-type",
                "display_name": "Legacy FU",
                "recipe_name": recipe_name,
                "yield_mode": "discrete_count",
                "items_per_batch": 12,
                "item_unit": "piece",
            }
        ]

        result = import_finished_units(data, mode="add")

        assert result.entity_counts["finished_units"].added == 1

        with session_scope() as sess:
            fu = sess.query(FinishedUnit).filter_by(slug="import-no-yield-type").first()
            assert fu is not None
            assert fu.yield_type == "SERVING"

            # No bare FG for SERVING default
            fg = finished_good_service.find_bare_fg_for_unit(fu.id, session=sess)
            assert fg is None

    def test_bulk_import_multiple_ea_creates_multiple_bare_fgs(self, test_db):
        """Import of 5 EA FUs creates 5 corresponding bare FGs."""
        test_db()
        recipe_id, recipe_name = _create_test_recipe()

        data = []
        for i in range(5):
            data.append(
                {
                    "slug": f"bulk-ea-{i+1}",
                    "display_name": f"Bulk Cookie {i+1}",
                    "recipe_name": recipe_name,
                    "yield_type": "EA",
                    "yield_mode": "discrete_count",
                    "items_per_batch": 24,
                    "item_unit": "cookie",
                }
            )

        result = import_finished_units(data, mode="add")

        assert result.entity_counts["finished_units"].added == 5
        assert result.has_errors is False

        with session_scope() as sess:
            for i in range(5):
                fu = sess.query(FinishedUnit).filter_by(slug=f"bulk-ea-{i+1}").first()
                assert fu is not None
                fg = finished_good_service.find_bare_fg_for_unit(fu.id, session=sess)
                assert fg is not None
                assert fg.assembly_type == AssemblyType.BARE
                assert fg.display_name == f"Bulk Cookie {i+1}"

    def test_mixed_ea_and_serving_import(self, test_db):
        """Import mix of EA and SERVING FUs -> only EA get bare FGs."""
        test_db()
        recipe_id, recipe_name = _create_test_recipe()

        data = [
            {
                "slug": "mix-ea-1",
                "display_name": "EA Item",
                "recipe_name": recipe_name,
                "yield_type": "EA",
                "yield_mode": "discrete_count",
                "items_per_batch": 1,
            },
            {
                "slug": "mix-serving-1",
                "display_name": "Serving Item",
                "recipe_name": recipe_name,
                "yield_type": "SERVING",
                "yield_mode": "discrete_count",
                "items_per_batch": 8,
            },
            {
                "slug": "mix-ea-2",
                "display_name": "EA Item 2",
                "recipe_name": recipe_name,
                "yield_type": "EA",
                "yield_mode": "discrete_count",
                "items_per_batch": 12,
            },
        ]

        result = import_finished_units(data, mode="add")

        assert result.entity_counts["finished_units"].added == 3

        with session_scope() as sess:
            ea_fu_1 = sess.query(FinishedUnit).filter_by(slug="mix-ea-1").first()
            serving_fu = sess.query(FinishedUnit).filter_by(slug="mix-serving-1").first()
            ea_fu_2 = sess.query(FinishedUnit).filter_by(slug="mix-ea-2").first()

            assert finished_good_service.find_bare_fg_for_unit(
                ea_fu_1.id, session=sess
            ) is not None
            assert finished_good_service.find_bare_fg_for_unit(
                serving_fu.id, session=sess
            ) is None
            assert finished_good_service.find_bare_fg_for_unit(
                ea_fu_2.id, session=sess
            ) is not None

    def test_import_transaction_integrity(self, test_db):
        """All FUs and FGs from a single import share the same transaction."""
        test_db()
        recipe_id, recipe_name = _create_test_recipe()

        data = [
            {
                "slug": "tx-ea-1",
                "display_name": "TX Cookie 1",
                "recipe_name": recipe_name,
                "yield_type": "EA",
                "yield_mode": "discrete_count",
                "items_per_batch": 24,
            },
            {
                "slug": "tx-ea-2",
                "display_name": "TX Cookie 2",
                "recipe_name": recipe_name,
                "yield_type": "EA",
                "yield_mode": "discrete_count",
                "items_per_batch": 12,
            },
        ]

        # Import within a single session to verify atomicity
        with session_scope() as sess:
            result = import_finished_units(data, mode="add", session=sess)
            assert result.entity_counts["finished_units"].added == 2

            # Both FUs and FGs should be visible in same session
            fu1 = sess.query(FinishedUnit).filter_by(slug="tx-ea-1").first()
            fu2 = sess.query(FinishedUnit).filter_by(slug="tx-ea-2").first()
            assert fu1 is not None
            assert fu2 is not None

            fg1 = finished_good_service.find_bare_fg_for_unit(fu1.id, session=sess)
            fg2 = finished_good_service.find_bare_fg_for_unit(fu2.id, session=sess)
            assert fg1 is not None
            assert fg2 is not None


class TestBulkImportDuplicateHandling:
    """WP08: Test duplicate handling during bulk import auto-generation."""

    def test_reimport_same_data_no_duplicate_fgs(self, test_db):
        """Re-importing same FU data skips FU (ADD_ONLY) and creates no new FGs."""
        test_db()
        recipe_id, recipe_name = _create_test_recipe()

        data = [
            {
                "slug": "reimport-ea-1",
                "display_name": "Reimport Cookie",
                "recipe_name": recipe_name,
                "yield_type": "EA",
                "yield_mode": "discrete_count",
                "items_per_batch": 24,
            },
        ]

        # First import
        result1 = import_finished_units(data, mode="add")
        assert result1.entity_counts["finished_units"].added == 1

        with session_scope() as sess:
            fu = sess.query(FinishedUnit).filter_by(slug="reimport-ea-1").first()
            fg1 = finished_good_service.find_bare_fg_for_unit(fu.id, session=sess)
            assert fg1 is not None
            fg1_id = fg1.id

        # Second import -- should skip the FU (already exists)
        result2 = import_finished_units(data, mode="add")
        assert result2.entity_counts["finished_units"].added == 0
        assert result2.entity_counts["finished_units"].skipped == 1

        # Verify no duplicate FGs created
        with session_scope() as sess:
            fu = sess.query(FinishedUnit).filter_by(slug="reimport-ea-1").first()
            fg2 = finished_good_service.find_bare_fg_for_unit(fu.id, session=sess)
            assert fg2 is not None
            assert fg2.id == fg1_id  # Same FG, not a new one

            # Count total bare FGs
            bare_count = (
                sess.query(FinishedGood)
                .filter(FinishedGood.assembly_type == AssemblyType.BARE)
                .count()
            )
            assert bare_count == 1

    def test_duplicate_display_names_get_unique_fg_slugs(self, test_db):
        """FUs with same display_name get FGs with disambiguated slugs."""
        test_db()
        # Create two recipes so we can have two FUs with the same display_name
        _, recipe_name_1 = _create_test_recipe("Recipe A", "Test")
        _, recipe_name_2 = _create_test_recipe("Recipe B", "Test")

        data = [
            {
                "slug": "dup-name-1",
                "display_name": "Chocolate Chip Cookie",
                "recipe_name": recipe_name_1,
                "yield_type": "EA",
                "yield_mode": "discrete_count",
                "items_per_batch": 24,
            },
            {
                "slug": "dup-name-2",
                "display_name": "Chocolate Chip Cookie",
                "recipe_name": recipe_name_2,
                "yield_type": "EA",
                "yield_mode": "discrete_count",
                "items_per_batch": 24,
            },
        ]

        result = import_finished_units(data, mode="add")

        assert result.entity_counts["finished_units"].added == 2

        with session_scope() as sess:
            fu1 = sess.query(FinishedUnit).filter_by(slug="dup-name-1").first()
            fu2 = sess.query(FinishedUnit).filter_by(slug="dup-name-2").first()

            fg1 = finished_good_service.find_bare_fg_for_unit(fu1.id, session=sess)
            fg2 = finished_good_service.find_bare_fg_for_unit(fu2.id, session=sess)

            assert fg1 is not None
            assert fg2 is not None
            # Both exist with unique slugs
            assert fg1.slug != fg2.slug
            # Both have same display_name
            assert fg1.display_name == "Chocolate Chip Cookie"
            assert fg2.display_name == "Chocolate Chip Cookie"

    def test_large_batch_import_performance(self, test_db):
        """Import 100+ EA FUs completes without error (performance sanity check)."""
        test_db()
        recipe_id, recipe_name = _create_test_recipe()

        data = []
        for i in range(100):
            data.append(
                {
                    "slug": f"perf-ea-{i+1:03d}",
                    "display_name": f"Perf Cookie {i+1}",
                    "recipe_name": recipe_name,
                    "yield_type": "EA",
                    "yield_mode": "discrete_count",
                    "items_per_batch": 24,
                }
            )

        result = import_finished_units(data, mode="add")

        assert result.entity_counts["finished_units"].added == 100
        assert result.has_errors is False

        # Verify all bare FGs created
        with session_scope() as sess:
            bare_count = (
                sess.query(FinishedGood)
                .filter(FinishedGood.assembly_type == AssemblyType.BARE)
                .count()
            )
            assert bare_count == 100

    def test_dry_run_no_bare_fgs_created(self, test_db):
        """Dry run does not create FUs or bare FGs."""
        test_db()
        recipe_id, recipe_name = _create_test_recipe()

        data = [
            {
                "slug": "dryrun-ea-1",
                "display_name": "Dry Run Cookie",
                "recipe_name": recipe_name,
                "yield_type": "EA",
                "yield_mode": "discrete_count",
                "items_per_batch": 24,
            },
        ]

        result = import_finished_units(data, mode="add", dry_run=True)

        # dry_run rolls back, so nothing persists
        with session_scope() as sess:
            fu = sess.query(FinishedUnit).filter_by(slug="dryrun-ea-1").first()
            assert fu is None

            bare_count = (
                sess.query(FinishedGood)
                .filter(FinishedGood.assembly_type == AssemblyType.BARE)
                .count()
            )
            assert bare_count == 0
