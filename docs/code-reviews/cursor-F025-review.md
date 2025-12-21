# Cursor Code Review: Feature 025 - Production Loss Tracking

**Date:** 2025-12-21
**Reviewer:** Cursor (AI Code Review)
**Feature:** 025-production-loss-tracking
**Branch:** 025-production-loss-tracking

## Summary

Feature 025 is implemented end-to-end (models → service → UI → export/import → migration script) and the feature-specific test suite passes. The loss workflow is solid: yield is validated fail-fast, loss quantity is auto-derived, status is derived consistently, and costs are computed using the same per-unit snapshot used for good units.

Two issues remain important:
- **Audit-trail delete semantics are contradictory**: the schema indicates “preserve losses when ProductionRun deleted” (`ondelete="SET NULL"`), but the ORM relationship uses `cascade="all, delete-orphan"` which will delete loss records when deleting a `ProductionRun` via ORM.
- **Exported loss UUIDs are present but `None`** (loss records’ `uuid` is not exported from the DB), which weakens portability and stable identity for loss records.

## Verification Results

### Module Import Validation
- ProductionLoss model: **PASS**
- ProductionStatus enum: **PASS**
- LossCategory enum: **PASS**
- ActualYieldExceedsExpectedError: **PASS**

### Test Results
- pytest result: **PASS – 54 passed** (`python3 -m pytest src/tests/test_batch_production_service.py -v`)
- Feature 025 tests: **22+ loss/export/import tests passed** (see `TestProductionLossTracking`, `TestExportImportV11`)

### Code Pattern Validation
- Fail-fast yield validation: **present** (validation happens before ingredient aggregation/FIFO)
- Production status logic: **correct** (0 loss → complete; 0 actual → total_loss; else partial_loss)
- ProductionLoss creation: **correct** (created only when `loss_quantity > 0`, default category OTHER)
- Auto-expand UI: **present** (loss details frame `grid()` / `grid_remove()`; auto-expands when loss detected)
- Import version transform: **correct** (v1.0 defaults added in importer; separate migration script is idempotent)

## Findings

### Critical Issues

1) **Audit-trail requirement conflict: ORM cascade deletes losses**
- **Spec intent / prompt**: `ProductionLoss.production_run_id` uses `ondelete="SET NULL"` “to preserve audit trail”.
- **Implementation**:
  - `ProductionLoss.production_run_id` is nullable with `ondelete="SET NULL"` (good).
  - `ProductionRun.losses` relationship is `cascade="all, delete-orphan"`.
- **Impact**: Deleting a `ProductionRun` via ORM (`session.delete(run)`) will cascade-delete the associated `ProductionLoss` rows, contradicting FR-017 (“preserve loss records when production run is deleted”).
- **Recommendation**: Remove `delete-orphan` (and potentially `delete`) from the `ProductionRun.losses` cascade, and consider `passive_deletes=True` so DB-level `ON DELETE SET NULL` can do its job.

2) **Exported loss UUIDs are `None`**
- **Prompt requirement**: exported losses include `uuid`.
- **Observed**:
  - The export includes the `uuid` key for each loss, but it is `None` because the service’s `_production_run_to_dict()` does not include `loss.uuid`.
  - A concrete check in an isolated in-memory DB showed `loss uuid None` in exported output.
- **Impact**:
  - Loss records lose stable identity across export/import and cannot be reliably deduplicated or referenced externally.
  - Import currently passes through `uuid=None` (which may rely on ORM defaults), but round-trip identity is not preserved.
- **Recommendation**: Include `uuid` in the loss dict returned by `_production_run_to_dict()` (e.g. `str(loss.uuid)`), and add a unit test asserting exported loss UUID is non-null.

### Warnings

1) **`record_batch_production()` accepts `session` but does not honor it**
- Signature includes `session=None`, but the function unconditionally opens `with session_scope() as session:`.
- If a caller ever tries to compose this inside a larger transaction, it will ignore the provided session and can reintroduce nested-session risks. (You already pass `session` through to inner service calls, which is good—this is just the outer “accept session” contract not being met.)

2) **Export version check can fail against a pre-migration database**
- Calling `export_production_history()` against an existing DB that has not been reset/migrated can raise `sqlite3.OperationalError: no such column: production_runs.production_status`.
- This is consistent with the project’s “export/reset/import” schema strategy, but it’s worth ensuring docs/UX make the requirement explicit (they mostly do via the migration guide).

3) **Minor checklist drift: LossCategory import location**
- The prompt asked for `LossCategory` import from `src.models`; the UI imports `LossCategory` from `src.models.enums`.
- Functionally fine, but slightly deviates from the requested layering/consistency convention.

### Observations

- Service-layer accounting is correct: inventory increments by `actual_yield` only; loss cost uses the same `per_unit_cost` snapshot as the run.
- UI behavior is user-friendly: loss details are hidden by default and auto-expanded when loss is detected.
- Versioning strategy is robust: importer applies v1.0 defaults and the migration script is idempotent.

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/models/enums.py | PASS | Enums are `(str, Enum)` and values match prompt. |
| src/models/production_loss.py | PASS | FK ondelete settings and constraints match prompt; uuid comes from BaseModel. |
| src/models/production_run.py | **NEEDS REVISION** | `losses` cascade includes `delete-orphan`, conflicting with audit-trail delete semantics. |
| src/models/__init__.py | PASS | Exports ProductionLoss, ProductionStatus, LossCategory. |
| src/services/batch_production_service.py | PASS (with warnings) | Core loss logic correct; export/import v1.1 present; `session` param not honored in `record_batch_production`. |
| src/ui/forms/record_production_dialog.py | PASS | Auto loss calculation + expandable details + confirmation includes loss info. |
| src/ui/widgets/production_history_table.py | PASS | Loss/Status columns and color/prefix mapping implemented. |
| src/tests/test_batch_production_service.py | PASS | Strong coverage for loss scenarios and export/import v1.1. |
| scripts/migrate_v1_0_to_v1_1.py | PASS | Works, idempotent, has usage docstring, executable bit set. |
| docs/migrations/v0.6_to_v0.7_production_loss.md | PASS | Step-by-step + rollback + verification checklist present. |

## Architecture Assessment

### Layered Architecture
**PASS**: Models are UI-free; services are UI-free; UI calls services via integrator.

### Session Management
**PASS (with caveat)**: Loss creation and ProductionRun creation occur within the same session and `flush()` is used before creating `ProductionLoss`. However, `record_batch_production()` does not honor an injected session.

### FK Cascade Behavior
**NEEDS REVISION**: DB-level `ON DELETE SET NULL` for `production_run_id` is undermined by ORM cascade delete-orphan on `ProductionRun.losses`.

### Error Handling
**PASS**: Yield validation is fail-fast and uses a specific exception carrying `actual_yield` and `expected_yield`.

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: Loss quantity auto-calculated | PASS | `loss_quantity = expected_yield - actual_yield`; UI uses `max(0, expected - actual)` |
| FR-002: actual_yield <= expected_yield enforced | PASS | Service raises `ActualYieldExceedsExpectedError`; UI validates too |
| FR-003: Fail-fast validation before FIFO | PASS | Validation occurs before `get_aggregated_ingredients()` / FIFO loop |
| FR-004: Production status derived correctly | PASS | COMPLETE / PARTIAL_LOSS / TOTAL_LOSS logic implemented |
| FR-005: ProductionLoss created on loss | PASS | Created only when `loss_quantity > 0` |
| FR-006: No ProductionLoss when no loss | PASS | No loss record for `loss_quantity == 0` |
| FR-007: Loss category dropdown in UI | PASS | Dropdown built from `LossCategory` values |
| FR-008: Loss notes optional | PASS | Notes textbox optional; stored as None when empty |
| FR-009: Default category is OTHER | PASS | Service uses `(loss_category or LossCategory.OTHER)` |
| FR-010: Per-unit cost snapshot on loss | PASS | `ProductionLoss.per_unit_cost = production_run.per_unit_cost` |
| FR-011: Total loss cost calculated | PASS | `loss_quantity * per_unit_cost` |
| FR-012: Cost breakdown in UI | PASS | “Good units / Lost units / Total batch cost” labels |
| FR-013: History shows Loss and Status columns | PASS | Table columns updated; formatting methods added |
| FR-014: Visual indicators for status | PASS | Color + “!” / “!!” prefixes |
| FR-015: Export includes loss data | PASS (with caveat) | Exports losses array and loss fields, but loss UUID values are `None` |
| FR-016: Import handles v1.0 and v1.1 | PASS | v1.0 defaults applied; v1.1 creates `ProductionLoss` rows |

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| SC-001: Loss recording adds <30s to workflow | PASS (qualitative) | Auto-calculation + auto-expand minimizes extra input |
| SC-002: All LossCategory values available | PASS | Enum + UI dropdown cover all categories |
| SC-003: Historical runs show COMPLETE status | PASS | v1.0 import defaults to `complete`, loss=0 |
| SC-004: Loss details auto-expand on detection | PASS | `_update_loss_quantity_display()` toggles frame |
| SC-005: Confirmation shows loss info | PASS | Confirmation message includes loss qty + category |
| SC-006: Export v1.1 with loss fields | PASS | Tests validate v1.1 export contains loss fields |
| SC-007: Import v1.0 backward compatible | PASS | Tests validate defaults applied |
| SC-008: Migration script idempotent | PASS | Verified by running transform twice |
| SC-009: 22+ unit tests pass | PASS | 54 tests passed in file, including Feature 025 sections |

## Conclusion

**APPROVED WITH CHANGES**

Core feature behavior is correct and well-tested. Before merge, address the audit-trail delete semantics (remove ORM delete-orphan cascade for losses or otherwise ensure `ProductionLoss` records survive `ProductionRun` deletion) and export real UUID values for loss records.

