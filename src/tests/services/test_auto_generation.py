"""Tests for F098 auto-generation of bare FinishedGoods.

WP03 - F098: Auto-Generation of FinishedGoods

Tests verify:
- find_bare_fg_for_unit() lookup works correctly
- auto_create_bare_finished_good() creates FG + Composition atomically
- Integration with save_recipe_with_yields() for EA yield types
- Duplicate prevention (no duplicate bare FGs)
- Weight/SERVING yield types do NOT trigger auto-generation

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
