---
work_package_id: WP03
title: Export/Import – yield_type Field
lane: "doing"
dependencies: [WP02]
base_branch: 083-dual-yield-recipe-output-support-WP02
base_commit: 9fbd6fa7c444ee009fa1e3a150e27f381f400fa2
created_at: '2026-01-29T17:21:08.300878+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
phase: Phase 2 - Integration
assignee: ''
agent: ''
shell_pid: "71472"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-29T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Export/Import – yield_type Field

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you begin addressing feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP02 - branch from WP02 completion
spec-kitty implement WP03 --base WP02
```

---

## Objectives & Success Criteria

Update export to include yield_type; update import to read and validate yield_type:

- [ ] Export includes `yield_type` field in finished_units JSON
- [ ] Import reads `yield_type` with default='SERVING' for backward compatibility
- [ ] Import validates yield_type is 'EA' or 'SERVING'
- [ ] Import handles UNIQUE constraint violations gracefully
- [ ] Round-trip test: export → import preserves yield_type

**Success metrics**:
- Exported JSON contains yield_type for each finished_unit
- Import of old exports (without yield_type) succeeds with default 'SERVING'
- Import of invalid yield_type logs warning and uses default
- No data loss during export/import cycle

---

## Context & Constraints

**Reference documents**:
- `kitty-specs/083-dual-yield-recipe-output-support/research.md` - Export/import patterns (Q3)
- `kitty-specs/083-dual-yield-recipe-output-support/data-model.md` - Export format
- `.kittify/memory/constitution.md` - Principle VI: Schema Change Strategy

**Current export structure** (from research.md):
```json
{
  "slug": "cookies-24-pack",
  "display_name": "Cookies",
  "recipe_slug": "sugar-cookies",
  "yield_mode": "discrete_count",
  "items_per_batch": 24,
  "item_unit": "cookie",
  "inventory_count": 42
}
```

**New export structure**:
```json
{
  "slug": "cookies-24-pack",
  "display_name": "Cookies",
  "recipe_slug": "sugar-cookies",
  "yield_mode": "discrete_count",
  "yield_type": "SERVING",
  "items_per_batch": 24,
  "item_unit": "cookie",
  "inventory_count": 42
}
```

**Import file**: `src/services/coordinated_export_service.py`
- Export function: `_export_finished_units()` (lines 738-769)
- Import section: lines 1613-1657

---

## Subtasks & Detailed Guidance

### Subtask T010 – Update export to include yield_type field

**Purpose**: Ensure exported JSON contains yield_type for each finished_unit.

**Steps**:
1. Open `src/services/coordinated_export_service.py`
2. Locate `_export_finished_units()` function (around line 738)
3. Add yield_type to the exported dictionary:

```python
def _export_finished_units(output_dir: Path, session: Session) -> FileEntry:
    """Export all finished units to JSON file with FK resolution."""
    units = session.query(FinishedUnit).options(joinedload(FinishedUnit.recipe)).all()

    records = []
    for fu in units:
        records.append({
            "uuid": str(fu.uuid) if fu.uuid else None,
            "slug": fu.slug,
            "display_name": fu.display_name,
            "recipe_slug": fu.recipe.slug if fu.recipe else None,
            "recipe_name": fu.recipe.name if fu.recipe else None,
            "category": fu.category,
            "yield_mode": fu.yield_mode.value if fu.yield_mode else None,
            "yield_type": fu.yield_type,  # NEW FIELD
            "items_per_batch": fu.items_per_batch,
            "item_unit": fu.item_unit,
            "batch_percentage": float(fu.batch_percentage) if fu.batch_percentage else None,
            "portion_description": fu.portion_description,
            "inventory_count": fu.inventory_count,
            "description": fu.description,
            "notes": fu.notes,
        })

    return _write_entity_file(output_dir, "finished_units", records)
```

**Files**: `src/services/coordinated_export_service.py`

**Parallel**: Yes - can be developed alongside T011

**Notes**:
- yield_type is a simple string, no conversion needed
- Place after yield_mode for logical grouping

---

### Subtask T011 – Update import to read yield_type with default

**Purpose**: Enable importing finished_units with yield_type, with backward compatibility.

**Steps**:
1. Locate the finished_units import section (around line 1613)
2. Add yield_type extraction with default:

```python
elif entity_type == "finished_units":
    # ... existing code ...

    # Parse yield_type with default for backward compatibility
    yield_type = record.get("yield_type", "SERVING")

    # ... create FinishedUnit with yield_type ...
    obj = FinishedUnit(
        recipe_id=recipe_id,
        slug=record.get("slug"),
        display_name=record.get("display_name"),
        category=record.get("category"),
        yield_mode=yield_mode,
        yield_type=yield_type,  # NEW FIELD
        items_per_batch=record.get("items_per_batch"),
        item_unit=record.get("item_unit"),
        # ... rest of fields ...
    )
```

**Files**: `src/services/coordinated_export_service.py`

**Parallel**: Yes - can be developed alongside T010

**Notes**:
- Default to 'SERVING' if yield_type is missing (old exports)
- This ensures backward compatibility

---

### Subtask T012 – Add import validation for yield_type values

**Purpose**: Validate yield_type during import and handle invalid values gracefully.

**Steps**:
1. After extracting yield_type (from T011), add validation:

```python
# Validate yield_type
VALID_YIELD_TYPES = ("EA", "SERVING")
yield_type = record.get("yield_type", "SERVING")

if yield_type not in VALID_YIELD_TYPES:
    logger.warning(
        f"Invalid yield_type '{yield_type}' for finished_unit '{record.get('slug', 'unknown')}', "
        f"defaulting to 'SERVING'"
    )
    yield_type = "SERVING"
```

**Files**: `src/services/coordinated_export_service.py`

**Notes**:
- Log warning but don't fail import
- Default to 'SERVING' for invalid values
- Include the slug in warning for debugging

---

### Subtask T013 – Handle UNIQUE constraint violations during import

**Purpose**: Gracefully handle duplicate (recipe_id, item_unit, yield_type) during import.

**Steps**:
1. Before adding the FinishedUnit, check for existing duplicate:

```python
# Check for duplicate (recipe_id, item_unit, yield_type)
existing = (
    session.query(FinishedUnit)
    .filter(
        FinishedUnit.recipe_id == recipe_id,
        FinishedUnit.item_unit == record.get("item_unit"),
        FinishedUnit.yield_type == yield_type,
    )
    .first()
)

if existing:
    logger.warning(
        f"Skipping duplicate finished_unit: recipe_id={recipe_id}, "
        f"item_unit='{record.get('item_unit')}', yield_type='{yield_type}' "
        f"(slug: {record.get('slug', 'unknown')})"
    )
    continue  # Skip this record
```

2. Alternatively, use the existing skip_duplicates pattern if it checks by slug only - in that case, just ensure the UNIQUE constraint error is caught:

```python
try:
    session.add(obj)
    session.flush()  # Force constraint check
    imported_count += 1
except IntegrityError as e:
    session.rollback()
    if "uq_finished_unit_recipe_item_unit_yield_type" in str(e):
        logger.warning(
            f"Skipping duplicate finished_unit: {record.get('slug', 'unknown')} - "
            f"duplicate (recipe_id, item_unit, yield_type)"
        )
    else:
        raise
```

**Files**: `src/services/coordinated_export_service.py`

**Notes**:
- Don't fail entire import for one duplicate
- Log sufficient detail for debugging
- Continue processing remaining records

---

### Subtask T014 – Write export/import round-trip tests

**Purpose**: Verify yield_type is preserved through export/import cycle.

**Steps**:
1. Create or update `src/tests/services/test_export_import_yield_type.py`:

```python
"""Tests for yield_type export/import functionality."""
import json
import tempfile
from pathlib import Path

import pytest

from src.models.finished_unit import FinishedUnit
from src.models.recipe import Recipe
from src.services.coordinated_export_service import (
    export_complete,
    import_complete,
)
from src.utils.db import session_scope


class TestExportYieldType:
    """Test yield_type is included in exports."""

    def test_export_includes_yield_type(self, test_db):
        """Exported finished_units.json includes yield_type field."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = FinishedUnit(
                slug="test-fu",
                display_name="Test FU",
                recipe_id=recipe.id,
                item_unit="cookie",
                items_per_batch=24,
                yield_type="EA",
            )
            session.add(fu)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            fu_file = tmp_path / "finished_units.json"
            assert fu_file.exists()

            with open(fu_file) as f:
                records = json.load(f)

            fu_record = next(r for r in records if r["slug"] == "test-fu")
            assert "yield_type" in fu_record
            assert fu_record["yield_type"] == "EA"


class TestImportYieldType:
    """Test yield_type is read correctly during import."""

    def test_import_with_yield_type(self, test_db):
        """Import correctly reads yield_type from JSON."""
        # Create recipe first
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.commit()

        # Create export with yield_type
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Write finished_units.json
            fu_data = [{
                "slug": "test-fu",
                "display_name": "Test FU",
                "recipe_slug": "test-recipe",
                "yield_mode": "discrete_count",
                "yield_type": "EA",
                "items_per_batch": 1,
                "item_unit": "cake",
                "inventory_count": 0,
            }]
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Import
            import_complete(tmp_path)

        # Verify
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(slug="test-fu").first()
            assert fu is not None
            assert fu.yield_type == "EA"

    def test_import_without_yield_type_defaults_to_serving(self, test_db):
        """Import without yield_type defaults to SERVING."""
        # Create recipe first
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.commit()

        # Create export WITHOUT yield_type (old format)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            fu_data = [{
                "slug": "test-fu",
                "display_name": "Test FU",
                "recipe_slug": "test-recipe",
                "yield_mode": "discrete_count",
                # NO yield_type field
                "items_per_batch": 24,
                "item_unit": "cookie",
                "inventory_count": 0,
            }]
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            import_complete(tmp_path)

        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(slug="test-fu").first()
            assert fu is not None
            assert fu.yield_type == "SERVING"  # Default

    def test_import_with_invalid_yield_type_defaults_to_serving(self, test_db):
        """Import with invalid yield_type defaults to SERVING."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.commit()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            fu_data = [{
                "slug": "test-fu",
                "display_name": "Test FU",
                "recipe_slug": "test-recipe",
                "yield_mode": "discrete_count",
                "yield_type": "INVALID",  # Invalid value
                "items_per_batch": 24,
                "item_unit": "cookie",
                "inventory_count": 0,
            }]
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            import_complete(tmp_path)

        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(slug="test-fu").first()
            assert fu is not None
            assert fu.yield_type == "SERVING"  # Defaulted


class TestExportImportRoundTrip:
    """Test full export/import cycle preserves yield_type."""

    def test_round_trip_preserves_yield_type(self, test_db):
        """Export → import preserves yield_type values."""
        # Create test data
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu_ea = FinishedUnit(
                slug="test-fu-ea",
                display_name="Test (EA)",
                recipe_id=recipe.id,
                item_unit="cake",
                items_per_batch=1,
                yield_type="EA",
            )
            fu_serving = FinishedUnit(
                slug="test-fu-serving",
                display_name="Test (Serving)",
                recipe_id=recipe.id,
                item_unit="slice",
                items_per_batch=8,
                yield_type="SERVING",
            )
            session.add_all([fu_ea, fu_serving])
            session.commit()

        # Export
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            export_complete(tmp_path)

            # Clear database
            with session_scope() as session:
                session.query(FinishedUnit).delete()
                session.query(Recipe).delete()
                session.commit()

            # Re-create recipe for FK
            with session_scope() as session:
                recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
                session.add(recipe)
                session.commit()

            # Import
            import_complete(tmp_path)

        # Verify
        with session_scope() as session:
            fu_ea = session.query(FinishedUnit).filter_by(slug="test-fu-ea").first()
            fu_serving = session.query(FinishedUnit).filter_by(slug="test-fu-serving").first()

            assert fu_ea is not None
            assert fu_ea.yield_type == "EA"

            assert fu_serving is not None
            assert fu_serving.yield_type == "SERVING"
```

**Files**: `src/tests/services/test_export_import_yield_type.py` (new file)

**Notes**:
- Test export includes yield_type
- Test import reads yield_type
- Test backward compatibility (missing yield_type)
- Test invalid yield_type handling
- Test full round-trip cycle

---

## Test Strategy

**Required tests** (T014):
- `TestExportYieldType` - Export includes yield_type
- `TestImportYieldType` - Import reads and validates yield_type
- `TestExportImportRoundTrip` - Full cycle preserves data

**Run tests**:
```bash
./run-tests.sh src/tests/services/test_export_import_yield_type.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Old exports don't have yield_type | Default to 'SERVING' during import |
| Invalid yield_type in export | Log warning, default to 'SERVING', don't fail |
| UNIQUE constraint violation | Skip duplicate, log warning, continue import |

---

## Definition of Done Checklist

- [ ] T010: Export includes yield_type field
- [ ] T011: Import reads yield_type with default
- [ ] T012: Import validates yield_type values
- [ ] T013: UNIQUE violations handled gracefully
- [ ] T014: All round-trip tests pass
- [ ] Backward compatibility maintained
- [ ] No data loss during export/import cycle

---

## Review Guidance

**Reviewers should verify**:
1. Export includes yield_type in correct position
2. Import defaults to 'SERVING' when yield_type missing
3. Invalid values logged but don't fail import
4. Round-trip test proves no data loss

---

## Activity Log

- 2026-01-29T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
