---
work_package_id: "WP08"
subtasks:
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
title: "Import/Export"
phase: "Phase 4 - History"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "15592"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T17:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - Import/Export

## Objectives & Success Criteria

Implement import/export functionality for production and assembly history:
- Export to JSON with full consumption ledger details
- Import with referential integrity validation
- Round-trip data integrity (export -> import preserves all data)

**Success Criteria**:
- [ ] Export includes all fields including consumption ledgers
- [ ] Export uses UUIDs for cross-system compatibility
- [ ] Import validates all foreign key references exist
- [ ] Import handles duplicate detection via UUID
- [ ] Round-trip preserves 100% of data

## Context & Constraints

**Reference Documents**:
- `kitty-specs/013-production-inventory-tracking/spec.md` - User Story 6
- `src/models/base.py` - UUID field on all models

**Export Format**:
```json
{
  "version": "1.0",
  "exported_at": "2025-12-09T12:00:00Z",
  "production_runs": [
    {
      "uuid": "abc123...",
      "recipe_slug": "chocolate-chip-cookies",
      "finished_unit_slug": "chocolate-chip-cookie",
      "num_batches": 2,
      "expected_yield": 96,
      "actual_yield": 92,
      "produced_at": "2025-12-08T10:00:00Z",
      "notes": "Test batch",
      "total_ingredient_cost": "5.25",
      "per_unit_cost": "0.0571",
      "consumptions": [
        {
          "uuid": "def456...",
          "ingredient_slug": "flour",
          "quantity_consumed": "4.0",
          "unit": "cups",
          "total_cost": "2.50"
        }
      ]
    }
  ],
  "assembly_runs": [...]
}
```

**Constraints**:
- Use slugs instead of IDs for portability
- Decimal values serialized as strings to preserve precision
- UUIDs used for duplicate detection on import

## Subtasks & Detailed Guidance

### Subtask T041 - Implement export_production_history()
- **Purpose**: Serialize production runs to JSON format
- **File**: `src/services/batch_production_service.py`
- **Parallel?**: Yes

**Function Signature**:
```python
def export_production_history(
    *,
    recipe_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    session=None
) -> Dict[str, Any]:
```

**Implementation**:
```python
def export_production_history(...):
    runs = get_production_history(
        recipe_id=recipe_id,
        start_date=start_date,
        end_date=end_date,
        include_consumptions=True,
        limit=10000  # Export all matching
    )

    exported_runs = []
    for run in runs:
        exported_run = {
            "uuid": run["uuid"],
            "recipe_slug": run["recipe"]["slug"],  # Use slug not ID
            "finished_unit_slug": run["finished_unit"]["slug"],
            "num_batches": run["num_batches"],
            "expected_yield": run["expected_yield"],
            "actual_yield": run["actual_yield"],
            "produced_at": run["produced_at"],
            "notes": run.get("notes"),
            "total_ingredient_cost": str(run["total_ingredient_cost"]),
            "per_unit_cost": str(run["per_unit_cost"]),
            "consumptions": [
                {
                    "uuid": c["uuid"],
                    "ingredient_slug": c["ingredient_slug"],
                    "quantity_consumed": str(c["quantity_consumed"]),
                    "unit": c["unit"],
                    "total_cost": str(c["total_cost"])
                }
                for c in run.get("consumptions", [])
            ]
        }
        exported_runs.append(exported_run)

    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "production_runs": exported_runs
    }
```

### Subtask T042 - Implement import_production_history()
- **Purpose**: Deserialize and import production runs
- **File**: `src/services/batch_production_service.py`
- **Parallel?**: Yes

**Function Signature**:
```python
def import_production_history(
    data: Dict[str, Any],
    *,
    skip_duplicates: bool = True,
    session=None
) -> Dict[str, Any]:
```

**Implementation**:
```python
def import_production_history(data, *, skip_duplicates=True, session=None):
    imported = 0
    skipped = 0
    errors = []

    with session_scope() as session:
        for run_data in data.get("production_runs", []):
            try:
                # Check for duplicate by UUID
                existing = session.query(ProductionRun).filter_by(
                    uuid=run_data["uuid"]
                ).first()
                if existing:
                    if skip_duplicates:
                        skipped += 1
                        continue
                    else:
                        errors.append(f"Duplicate UUID: {run_data['uuid']}")
                        continue

                # Resolve recipe by slug
                recipe = session.query(Recipe).filter_by(
                    slug=run_data["recipe_slug"]
                ).first()
                if not recipe:
                    errors.append(f"Recipe not found: {run_data['recipe_slug']}")
                    continue

                # Resolve finished_unit by slug
                fu = session.query(FinishedUnit).filter_by(
                    slug=run_data["finished_unit_slug"]
                ).first()
                if not fu:
                    errors.append(f"FinishedUnit not found: {run_data['finished_unit_slug']}")
                    continue

                # Create ProductionRun
                run = ProductionRun(
                    uuid=run_data["uuid"],
                    recipe_id=recipe.id,
                    finished_unit_id=fu.id,
                    num_batches=run_data["num_batches"],
                    expected_yield=run_data["expected_yield"],
                    actual_yield=run_data["actual_yield"],
                    produced_at=datetime.fromisoformat(run_data["produced_at"]),
                    notes=run_data.get("notes"),
                    total_ingredient_cost=Decimal(run_data["total_ingredient_cost"]),
                    per_unit_cost=Decimal(run_data["per_unit_cost"])
                )
                session.add(run)
                session.flush()  # Get ID

                # Create consumptions
                for c_data in run_data.get("consumptions", []):
                    consumption = ProductionConsumption(
                        uuid=c_data["uuid"],
                        production_run_id=run.id,
                        ingredient_slug=c_data["ingredient_slug"],
                        quantity_consumed=Decimal(c_data["quantity_consumed"]),
                        unit=c_data["unit"],
                        total_cost=Decimal(c_data["total_cost"])
                    )
                    session.add(consumption)

                imported += 1

            except Exception as e:
                errors.append(f"Error importing {run_data.get('uuid', 'unknown')}: {str(e)}")

        session.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors
    }
```

### Subtask T043 - Implement export_assembly_history()
- **Purpose**: Serialize assembly runs to JSON format
- **File**: `src/services/assembly_service.py`
- **Parallel?**: Yes

**Implementation**: Similar pattern to T041, but with:
- finished_good_slug instead of recipe_slug
- finished_unit_consumptions and packaging_consumptions arrays

### Subtask T044 - Implement import_assembly_history()
- **Purpose**: Deserialize and import assembly runs
- **File**: `src/services/assembly_service.py`
- **Parallel?**: Yes

**Implementation**: Similar pattern to T042, but with:
- Resolve FinishedGood by slug
- Resolve FinishedUnit components by slug
- Resolve packaging Product by slug or ingredient_slug

### Subtask T045 - Add tests for import/export round-trip
- **Purpose**: Verify data integrity through export-import cycle
- **File**: Add to existing test files
- **Parallel?**: No

**Tests**:
```python
def test_export_import_production_roundtrip(production_runs_with_consumptions):
    """Export -> Import preserves all data."""
    # Export
    exported = batch_production_service.export_production_history()
    assert len(exported["production_runs"]) > 0

    # Store original data for comparison
    original_runs = exported["production_runs"].copy()

    # Clear and reimport (or import to fresh DB)
    # ... clear production_runs table ...

    result = batch_production_service.import_production_history(exported)
    assert result["imported"] == len(original_runs)
    assert result["errors"] == []

    # Verify data matches
    reimported = batch_production_service.export_production_history()
    assert len(reimported["production_runs"]) == len(original_runs)

    for orig, reimp in zip(original_runs, reimported["production_runs"]):
        assert orig["uuid"] == reimp["uuid"]
        assert orig["actual_yield"] == reimp["actual_yield"]
        assert orig["total_ingredient_cost"] == reimp["total_ingredient_cost"]

def test_import_skips_duplicates(production_run):
    """Import with skip_duplicates=True skips existing UUIDs."""
    exported = batch_production_service.export_production_history()
    result = batch_production_service.import_production_history(exported)
    assert result["skipped"] == len(exported["production_runs"])
    assert result["imported"] == 0

def test_import_validates_references(db_session):
    """Import fails gracefully with missing references."""
    data = {
        "version": "1.0",
        "production_runs": [{
            "uuid": "test-uuid",
            "recipe_slug": "nonexistent-recipe",
            "finished_unit_slug": "nonexistent-fu",
            ...
        }]
    }
    result = batch_production_service.import_production_history(data)
    assert result["imported"] == 0
    assert len(result["errors"]) > 0
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Decimal precision loss | Serialize as strings, parse with Decimal() |
| Missing slug on entities | Ensure Recipe, FinishedUnit, FinishedGood all have slug fields |
| Partial import on error | Transaction rollback on any error (or continue with error collection) |
| Large dataset memory | Stream export/import for large datasets (future enhancement) |

## Definition of Done Checklist

- [ ] T041: export_production_history() with full consumption details
- [ ] T042: import_production_history() with validation
- [ ] T043: export_assembly_history() with full consumption details
- [ ] T044: import_assembly_history() with validation
- [ ] T045: Round-trip tests pass with 100% data preservation
- [ ] Duplicate detection via UUID works
- [ ] Reference validation reports clear errors
- [ ] `tasks.md` updated

## Review Guidance

**Reviewer Checklist**:
- [ ] Export uses slugs not IDs
- [ ] Decimal values serialized as strings
- [ ] Import validates all references before creating records
- [ ] Duplicate UUID detection works
- [ ] Error collection allows partial success reporting

## Activity Log

- 2025-12-09T17:30:00Z - system - lane=planned - Prompt created.
- 2025-12-10T03:49:18Z – claude – shell_pid=15592 – lane=doing – Implementation complete - export/import functions with UUID-based duplicate detection
