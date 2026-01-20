# Research: Architecture Hardening - Service Boundaries & Session Management

**Feature**: 060-architecture-hardening-service-boundaries
**Date**: 2026-01-20
**Status**: Complete

## Executive Summary

Comprehensive codebase research completed to understand existing mature patterns, identify services needing updates, catalog production service callers, and assess staleness detection gaps.

---

## 1. Session Threading Pattern Analysis

### Decision: Use `nullcontext` pattern from batch_production_service

### Rationale
The `batch_production_service.py` implements the most mature and elegant session handling pattern in the codebase. It uses `nullcontext` for conditional session ownership, which eliminates verbose if/else blocks.

### Gold Standard Pattern (Lines 279-281)

```python
from contextlib import nullcontext

def record_batch_production(..., session=None):
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # All operations use same session
        result = inventory_item_service.consume_fifo(..., session=session)
```

### Key Elements

1. **Optional session parameter**: `session=None`
2. **Conditional context manager**: `nullcontext(session) if session is not None else session_scope()`
3. **Downstream session passing**: All called services receive `session=session`
4. **No internal commits**: When session provided, caller controls transaction
5. **Cost snapshots**: Captured in consumption records at operation time

### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| Verbose if/else pattern | More code, higher maintenance burden |
| Decorator approach | Hides session handling, harder to debug |
| Always require session | Breaks backward compatibility |

---

## 2. Services Inventory

### Decision: Update 3 event service methods + remove 2 shopping_list commits

### Services Already Correct (No Changes Needed)

| Service | Key Methods | Pattern |
|---------|-------------|---------|
| `batch_production_service.py` | `check_can_produce()`, `record_batch_production()` | nullcontext |
| `assembly_service.py` | `check_can_assemble()`, `record_assembly()` | if/else session |
| `recipe_service.py` | `get_aggregated_ingredients()` | if/else session |
| `ingredient_service.py` | `get_ingredient()` | if/else session |
| `inventory_item_service.py` | `consume_fifo()` | if/else session |
| `recipe_snapshot_service.py` | Various | session param |
| `packaging_service.py` | Various | session param |
| `unit_service.py` | Various | session param |
| `supplier_service.py` | Various | session param |

### Services Needing Session Parameter (FR-7)

| Service | Method | Line | Issue |
|---------|--------|------|-------|
| `event_service.py` | `get_production_progress()` | 1927 | Opens own session |
| `event_service.py` | `get_assembly_progress()` | 2005 | Opens own session |
| `event_service.py` | `get_shopping_list()` | 946 | Opens own session |

### Services With Internal Commits (FR-5)

| Service | Method | Line | Issue |
|---------|--------|------|-------|
| `planning/shopping_list.py` | `_mark_shopping_complete_impl()` | 223 | `session.commit()` |
| `planning/shopping_list.py` | `_unmark_shopping_complete_impl()` | 266 | `session.commit()` |

### Planning Services Status

| Service | Session Param | Internal Commit | Status |
|---------|---------------|-----------------|--------|
| `planning_service.py` | YES | NO | OK |
| `progress.py` | YES | NO | Needs event_service update |
| `shopping_list.py` | YES | YES (2) | Needs commit removal |
| `feasibility.py` | YES | NO | OK |
| `batch_calculation.py` | YES | NO | OK |

---

## 3. Production Service Caller Analysis

### Decision: Full deprecation safe - only 1 active caller in deprecated file

### Active Callers

| File | Line | Function | Status |
|------|------|----------|--------|
| `src/ui/production_tab.py` | 337 | `_record_production()` | File DEPRECATED |

### Already Migrated

| File | Line | Function | Uses |
|------|------|----------|------|
| `src/ui/forms/record_production_dialog.py` | 379 | `_on_confirm()` | `batch_production_service` |

### Test References (Need Migration)

| File | References | Status |
|------|------------|--------|
| `src/tests/services/test_production_service.py` | 14+ | Need migration to batch_production |

### Migration Risk Assessment

**RISK: LOW**

- Only 1 active UI caller
- That file (`production_tab.py`) is already marked DEPRECATED
- Modern UI already uses `batch_production_service`
- Tests are the main migration work

---

## 4. Staleness Detection Analysis

### Decision: Add Composition.updated_at + check FinishedUnit.updated_at

### Currently Tracked Mutations

| Source | Field Checked | Implementation |
|--------|---------------|----------------|
| Event | `last_modified` | `_check_staleness_impl()` line 515 |
| EventAssemblyTarget | `updated_at` | `_check_staleness_impl()` line 523 |
| EventProductionTarget | `updated_at` | `_check_staleness_impl()` line 531 |
| Recipe | `last_modified` | `_check_staleness_impl()` line 539 |
| FinishedGood | `updated_at` | `_check_staleness_impl()` line 547 |
| Composition | `created_at` only | `_check_staleness_impl()` line 555 |

### Missing Mutation Detection (FR-6)

| Source | Field | Issue | Fix |
|--------|-------|-------|-----|
| Composition | `updated_at` | **Field doesn't exist** | Add to model |
| FinishedUnit | `updated_at` | Field exists, not checked | Add check |
| Aggregated ingredients | N/A | TODO placeholder empty | Populate in WP04 |

### Model Field Status

| Model | `created_at` | `updated_at` | Action |
|-------|--------------|--------------|--------|
| Event | `date_added` | `last_modified` | OK |
| Recipe | `date_added` | `last_modified` | OK |
| FinishedGood | YES | YES | OK |
| FinishedUnit | YES | YES | Need to check |
| Composition | YES | **NO** | **ADD** |
| EventProductionTarget | YES (BaseModel) | YES (BaseModel) | OK |
| EventAssemblyTarget | YES (BaseModel) | YES (BaseModel) | OK |

### Schema Change Impact

Adding `Composition.updated_at`:
- **Model change**: Add `updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)`
- **Migration**: Via export/reset/import (per constitution)
- **Risk**: Low - standard pattern, nullable-friendly

---

## 5. Assembly Nested FG Ledger Gap

### Decision: Follow packaging consumption pattern

### Current State

Assembly service creates consumption records for:
- Packaging products (via `AssemblyPackagingConsumption`)
- Materials (via `material_consumption_service`)
- Finished units (via `AssemblyFinishedUnitConsumption`)

**GAP**: Nested finished goods consumed but NO ledger entry created.

### Pattern to Follow (Lines 456-464)

```python
for pkg_data in pkg_consumptions:
    consumption = AssemblyPackagingConsumption(
        assembly_run_id=assembly_run.id,
        product_id=pkg_data["product_id"],
        quantity_consumed=pkg_data["quantity_consumed"],
        unit=pkg_data["unit"],
        total_cost=pkg_data["total_cost"],  # Cost snapshot
    )
    session.add(consumption)
```

### Required Changes

1. Identify nested FG consumption point in `_record_assembly_impl()`
2. Create consumption record with:
   - `assembly_run_id`
   - `finished_good_id` (nested FG)
   - `quantity_consumed`
   - `total_cost` (snapshotted at consumption)
   - `lot_id` (if lot tracking enabled)
3. Update export/import for nested consumption records

---

## 6. Research Conclusions

### Summary Table

| Area | Decision | Confidence |
|------|----------|------------|
| Session pattern | Use nullcontext from batch_production | HIGH |
| Event service | Add session param to 3 methods | HIGH |
| Shopping list | Remove 2 internal commits | HIGH |
| Production deprecation | Safe - only 1 caller in deprecated file | HIGH |
| Composition model | Add updated_at field | HIGH |
| Staleness detection | Add 2 new timestamp checks | HIGH |
| Nested FG ledger | Follow packaging consumption pattern | HIGH |

### Open Questions

None - all research questions resolved.

### References

- `src/services/batch_production_service.py` (lines 279-281, 371-372)
- `src/services/assembly_service.py` (lines 456-464)
- `src/services/event_service.py` (lines 946, 1927, 2005)
- `src/services/planning/shopping_list.py` (lines 223, 266)
- `src/services/planning/planning_service.py` (line 293 TODO, lines 500-562)
- `src/models/composition.py` (line 99)
- `src/ui/production_tab.py` (line 337, file deprecated)
