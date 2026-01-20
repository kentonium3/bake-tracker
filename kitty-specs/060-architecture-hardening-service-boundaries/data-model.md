# Data Model Changes: Architecture Hardening

**Feature**: 060-architecture-hardening-service-boundaries
**Date**: 2026-01-20
**Status**: Design Complete

## Overview

This feature requires one model change: adding `updated_at` timestamp to the `Composition` model to support staleness detection for BOM mutations.

---

## Model Change: Composition

### Current State

```python
# src/models/composition.py (line 99)
class Composition(BaseModel):
    __tablename__ = "composition"

    # ... existing fields ...
    created_at = Column(DateTime, nullable=False, default=utc_now)
    # NOTE: No updated_at field
```

### Target State

```python
# src/models/composition.py
class Composition(BaseModel):
    __tablename__ = "composition"

    # ... existing fields ...
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
```

### Field Specification

| Field | Type | Nullable | Default | OnUpdate | Purpose |
|-------|------|----------|---------|----------|---------|
| `updated_at` | DateTime | NO | `utc_now` | `utc_now` | Track last modification for staleness detection |

### Rationale

The `Composition` model represents recipe component relationships (linking recipes to ingredients or nested recipes). Current staleness detection only tracks `created_at`, which means:

- New compositions trigger staleness (correct)
- **Modified compositions do NOT trigger staleness (incorrect)**
- Deleted compositions are not explicitly tracked (acceptable - query returns empty)

Adding `updated_at` enables detection of:
- Quantity changes in existing compositions
- Unit changes
- Component reference changes (e.g., different ingredient slug)
- Notes/metadata changes

### Migration Strategy

Per constitution principle VI (Schema Change Strategy for Desktop Phase):

1. **Export** all data to JSON before schema change
2. **Reset** database (delete and recreate)
3. **Import** data back (new field gets default value)

No Alembic migration script needed.

### Impact Analysis

| Area | Impact |
|------|--------|
| Export/Import | None - field auto-populated on import |
| Existing data | All existing compositions get `updated_at = created_at` equivalent |
| API contract | None - internal model change only |
| UI | None - field not displayed |
| Tests | Add tests for updated_at auto-update |

---

## No Other Model Changes Required

The following models already have the required timestamp fields:

| Model | Has `updated_at` | Used in Staleness | Status |
|-------|------------------|-------------------|--------|
| Event | `last_modified` | YES | OK |
| Recipe | `last_modified` | YES | OK |
| FinishedGood | YES | YES | OK |
| FinishedUnit | YES | **NO** | Add check in code |
| EventProductionTarget | YES (BaseModel) | YES | OK |
| EventAssemblyTarget | YES (BaseModel) | YES | OK |

**Note**: `FinishedUnit.updated_at` exists but is not checked in staleness detection. This is a **code change**, not a model change. WP05 will add the staleness check.

---

## New Consumption Records (No Schema Change)

WP06 (Assembly Nested FG Ledger) will create consumption records for nested finished goods. This uses the **existing** `AssemblyFinishedUnitConsumption` model or a similar pattern - no new tables or fields required.

If a new consumption type is needed, it would follow this pattern:

```python
# Hypothetical - if needed
class AssemblyNestedFGConsumption(BaseModel):
    __tablename__ = "assembly_nested_fg_consumption"

    assembly_run_id = Column(Integer, ForeignKey("assembly_run.id"), nullable=False)
    finished_good_id = Column(Integer, ForeignKey("finished_good.id"), nullable=False)
    quantity_consumed = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(50), nullable=False)
    total_cost = Column(Numeric(10, 2), nullable=True)  # Cost snapshot
    lot_id = Column(Integer, ForeignKey("lot.id"), nullable=True)  # Optional lot tracking
```

This will be determined during WP06 implementation based on existing ledger patterns.

---

## Planning Snapshot Extensions (No Schema Change)

WP04 (Aggregated Ingredients) populates an existing TODO placeholder in `calculation_results` JSON field. This is a **data structure change**, not a schema change.

Current state (line 293 of planning_service.py):
```python
"aggregated_ingredients": []  # TODO: Populate from recipe aggregation
```

Target state:
```python
"aggregated_ingredients": [
    {
        "ingredient_slug": "flour-all-purpose",
        "display_name": "All-Purpose Flour",
        "quantity": 2.5,
        "unit": "kg",
        "cost_per_unit": 1.50
    },
    # ... more ingredients
]
```

This is stored in the existing `calculation_results` JSON column - no schema change needed.

---

## Summary

| Change Type | Count | Details |
|-------------|-------|---------|
| Model field additions | 1 | `Composition.updated_at` |
| New tables | 0 | None |
| JSON structure changes | 1 | `aggregated_ingredients` in snapshot |
| Migration scripts | 0 | Export/reset/import per constitution |
