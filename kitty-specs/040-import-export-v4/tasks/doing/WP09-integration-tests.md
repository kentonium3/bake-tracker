---
work_package_id: "WP09"
subtasks:
  - "T038"
  - "T039"
  - "T040"
  - "T041"
title: "Integration Tests"
phase: "Phase 3 - Integration & Documentation"
lane: "doing"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 - Integration Tests

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- End-to-end tests validating full export/import round-trips
- Verify data integrity across all entity types
- Test both merge and replace import modes
- Confirm F037 and F039 fields survive round-trip

**Success Criteria**:
- Full database export -> reset -> import preserves all data
- Recipe variants maintain relationships after round-trip
- Event output_mode preserved after round-trip
- Merge mode adds without duplicating, replace mode clears first

## Context & Constraints

**Related Documents**:
- `kitty-specs/040-import-export-v4/spec.md` - Acceptance criteria
- `kitty-specs/040-import-export-v4/data-model.md` - Complete schema

**Key Constraints**:
- Use fresh test database per test run
- Compare entity counts and key fields
- Verify FK relationships intact
- Follow existing integration test patterns

**File to Create/Modify**: `src/tests/integration/test_import_export_v4.py`

**Dependencies**: WP01-WP04 (core schema complete)

## Subtasks & Detailed Guidance

### Subtask T038 - Full export -> import round-trip test

**Purpose**: Verify complete data preservation across export/import cycle.

**Steps**:
1. Create comprehensive test database with all entity types:
   - Ingredients (including hierarchy)
   - Products (with UPCs)
   - Recipes (with ingredients, finished units)
   - Events (with targets)
   - Suppliers
   - Purchases
   - InventoryItems
2. Export to JSON file
3. Reset database (clear all tables)
4. Import from JSON file
5. Compare counts and key fields

**Code Pattern**:
```python
import pytest
from decimal import Decimal
from src.services.import_export_service import export_all_to_json, import_all_from_json_v4
from src.services.database import session_scope

class TestImportExportV4Integration:

    def test_full_export_import_round_trip(self, db_session, tmp_path):
        """Test complete export -> import preserves all data."""
        # Create comprehensive test data
        self._create_test_database(db_session)

        # Capture counts before export
        counts_before = self._get_entity_counts(db_session)

        # Export
        export_path = tmp_path / "export.json"
        export_all_to_json(str(export_path))

        # Clear database
        self._clear_database(db_session)

        # Verify empty
        counts_after_clear = self._get_entity_counts(db_session)
        assert all(c == 0 for c in counts_after_clear.values())

        # Import
        result = import_all_from_json_v4(str(export_path))
        assert result.error_count == 0

        # Compare counts
        counts_after = self._get_entity_counts(db_session)
        for entity, count in counts_before.items():
            assert counts_after[entity] == count, f"{entity} count mismatch"

    def _create_test_database(self, session):
        """Create comprehensive test data."""
        # Ingredients
        flour = Ingredient(name="All-Purpose Flour", slug="all-purpose-flour")
        sugar = Ingredient(name="Sugar", slug="sugar")
        session.add_all([flour, sugar])

        # Products with UPCs
        product = Product(
            name="Gold Medal Flour 5lb",
            ingredient_id=flour.id,
            upc_code="016000196100"
        )
        session.add(product)

        # Recipe with variant fields
        base_recipe = Recipe(
            name="Basic Cookie",
            slug="basic-cookie",
            is_production_ready=True
        )
        session.add(base_recipe)
        session.flush()

        # FinishedUnit with yield_mode
        finished_unit = FinishedUnit(
            recipe_id=base_recipe.id,
            slug="basic-cookie-dozen",
            name="Dozen",
            yield_mode=YieldMode.DISCRETE_COUNT,
            unit_yield_quantity=Decimal("12")
        )
        session.add(finished_unit)

        # Event with output_mode
        event = Event(
            name="Holiday Sale",
            output_mode=OutputMode.BUNDLED
        )
        session.add(event)

        session.commit()

    def _get_entity_counts(self, session):
        """Get counts of all entity types."""
        from src.models import (
            Ingredient, Product, Recipe, FinishedUnit,
            Event, Supplier, Purchase, InventoryItem
        )
        return {
            "ingredients": session.query(Ingredient).count(),
            "products": session.query(Product).count(),
            "recipes": session.query(Recipe).count(),
            "finished_units": session.query(FinishedUnit).count(),
            "events": session.query(Event).count(),
            "suppliers": session.query(Supplier).count(),
            "purchases": session.query(Purchase).count(),
            "inventory_items": session.query(InventoryItem).count(),
        }
```

**Files**: `src/tests/integration/test_import_export_v4.py`
**Parallel?**: Yes - independent of other tests

### Subtask T039 - Recipe variants round-trip

**Purpose**: Verify variant recipe relationships preserved.

**Steps**:
1. Create base recipe and variant recipe
2. Verify base_recipe_id FK set correctly
3. Export
4. Clear and import
5. Verify base_recipe_slug resolved correctly
6. Verify FK relationship intact

**Code Pattern**:
```python
def test_recipe_variants_round_trip(self, db_session, tmp_path):
    """Test base/variant recipe relationships preserved."""
    # Create base recipe
    base = Recipe(
        name="Sugar Cookie Base",
        slug="sugar-cookie-base",
        is_production_ready=True
    )
    db_session.add(base)
    db_session.flush()

    # Create variant
    variant = Recipe(
        name="Frosted Sugar Cookie",
        slug="frosted-sugar-cookie",
        variant_name="Frosted",
        base_recipe_id=base.id,
        is_production_ready=False
    )
    db_session.add(variant)
    db_session.commit()

    # Export
    export_path = tmp_path / "recipes.json"
    export_all_to_json(str(export_path))

    # Verify export contains base_recipe_slug
    with open(export_path) as f:
        data = json.load(f)
    variant_export = next(r for r in data["recipes"] if r["slug"] == "frosted-sugar-cookie")
    assert variant_export["base_recipe_slug"] == "sugar-cookie-base"
    assert variant_export["variant_name"] == "Frosted"

    # Clear and import
    self._clear_database(db_session)
    result = import_all_from_json_v4(str(export_path))
    assert result.error_count == 0

    # Verify relationships
    imported_base = db_session.query(Recipe).filter_by(slug="sugar-cookie-base").first()
    imported_variant = db_session.query(Recipe).filter_by(slug="frosted-sugar-cookie").first()

    assert imported_variant.base_recipe_id == imported_base.id
    assert imported_variant.variant_name == "Frosted"
```

**Files**: `src/tests/integration/test_import_export_v4.py`
**Parallel?**: Yes - independent

### Subtask T040 - Event output_mode round-trip

**Purpose**: Verify F039 output_mode field preserved.

**Steps**:
1. Create events with different output_modes (bundled, bulk_count, None)
2. Create matching targets (assembly for bundled, production for bulk)
3. Export
4. Verify JSON contains output_mode
5. Clear and import
6. Verify output_mode values match

**Code Pattern**:
```python
def test_event_output_mode_round_trip(self, db_session, tmp_path):
    """Test event output_mode preserved after round-trip."""
    # Create events with different modes
    bundled_event = Event(
        name="Gift Set Event",
        output_mode=OutputMode.BUNDLED
    )
    bulk_event = Event(
        name="Bulk Order",
        output_mode=OutputMode.BULK_COUNT
    )
    null_event = Event(
        name="Legacy Event",
        output_mode=None
    )
    db_session.add_all([bundled_event, bulk_event, null_event])
    db_session.commit()

    # Export
    export_path = tmp_path / "events.json"
    export_all_to_json(str(export_path))

    # Verify export
    with open(export_path) as f:
        data = json.load(f)
    events = {e["name"]: e for e in data["events"]}
    assert events["Gift Set Event"]["output_mode"] == "bundled"
    assert events["Bulk Order"]["output_mode"] == "bulk_count"
    assert events["Legacy Event"]["output_mode"] is None

    # Clear and import
    self._clear_database(db_session)
    result = import_all_from_json_v4(str(export_path))
    assert result.error_count == 0

    # Verify imported values
    imported = {e.name: e for e in db_session.query(Event).all()}
    assert imported["Gift Set Event"].output_mode == OutputMode.BUNDLED
    assert imported["Bulk Order"].output_mode == OutputMode.BULK_COUNT
    assert imported["Legacy Event"].output_mode is None
```

**Files**: `src/tests/integration/test_import_export_v4.py`
**Parallel?**: Yes - independent

### Subtask T041 - Mode testing: merge vs replace

**Purpose**: Verify correct behavior for different import modes.

**Steps**:
1. Create initial database with known records
2. Export to file A
3. Modify database (add new, modify existing)
4. Export to file B (different content)
5. Test merge mode: import A on top of modified DB, verify additions without replacement
6. Test replace mode: import A replacing modified DB, verify clean slate

**Code Pattern**:
```python
def test_import_merge_mode(self, db_session, tmp_path):
    """Test merge mode adds without replacing existing."""
    # Create initial ingredient
    flour = Ingredient(name="Flour", slug="flour")
    db_session.add(flour)
    db_session.commit()

    # Export (just flour)
    export_path = tmp_path / "initial.json"
    export_all_to_json(str(export_path))

    # Add another ingredient
    sugar = Ingredient(name="Sugar", slug="sugar")
    db_session.add(sugar)
    db_session.commit()

    assert db_session.query(Ingredient).count() == 2

    # Import in merge mode (default)
    result = import_all_from_json_v4(str(export_path), mode="merge")

    # Both should exist (flour not duplicated, sugar preserved)
    assert db_session.query(Ingredient).count() == 2
    assert db_session.query(Ingredient).filter_by(slug="flour").count() == 1
    assert db_session.query(Ingredient).filter_by(slug="sugar").count() == 1

def test_import_replace_mode(self, db_session, tmp_path):
    """Test replace mode clears existing data first."""
    # Create initial ingredient
    flour = Ingredient(name="Flour", slug="flour")
    db_session.add(flour)
    db_session.commit()

    # Export (just flour)
    export_path = tmp_path / "initial.json"
    export_all_to_json(str(export_path))

    # Add another ingredient
    sugar = Ingredient(name="Sugar", slug="sugar")
    db_session.add(sugar)
    db_session.commit()

    assert db_session.query(Ingredient).count() == 2

    # Import in replace mode
    result = import_all_from_json_v4(str(export_path), mode="replace")

    # Only flour should exist (sugar removed)
    assert db_session.query(Ingredient).count() == 1
    assert db_session.query(Ingredient).filter_by(slug="flour").count() == 1
    assert db_session.query(Ingredient).filter_by(slug="sugar").count() == 0
```

**Files**: `src/tests/integration/test_import_export_v4.py`
**Parallel?**: No - tests build on each other conceptually

## Test Strategy

**Required Tests**:
```bash
pytest src/tests/integration/test_import_export_v4.py -v
```

**Test Setup**:
- Use pytest fixtures for database setup
- Each test should run in isolation
- Use tmp_path fixture for JSON files

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Test database pollution | Use rollback or fresh DB per test |
| FK ordering issues | Import in correct dependency order |
| Large test data | Keep test data minimal but representative |

## Definition of Done Checklist

- [ ] T038: Full round-trip test passes
- [ ] T039: Variant recipes preserved
- [ ] T040: Event output_mode preserved
- [ ] T041: Merge/replace modes work correctly
- [ ] All tests run in isolation
- [ ] No flaky tests

## Review Guidance

- Check test isolation (no shared state)
- Verify assertions cover key relationships
- Confirm FK resolution order is correct
- Test with real-ish data shapes

## Activity Log

- 2026-01-06T12:00:00Z - system - lane=planned - Prompt created.
- 2026-01-07T03:44:11Z – system – shell_pid= – lane=doing – Moved to doing
