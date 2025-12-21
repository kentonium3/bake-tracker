# Research Decision Log

Document the outcomes of Phase 0 discovery work. Capture every clarification resolved and the supporting evidence that backs each decision.

## Summary

- **Feature**: 025-production-loss-tracking
- **Date**: 2025-12-21
- **Researchers**: Claude Code (lead agent)
- **Open Questions**: None - all planning questions resolved

## Decisions & Rationale

| Decision | Rationale | Evidence | Status |
|----------|-----------|----------|--------|
| Hybrid schema (status on ProductionRun, details in ProductionLoss) | Balance of query simplicity for common operations (status check) and flexibility for detailed loss records | User confirmed; matches spec's mention of both entities | final |
| Python Enum + String column for loss categories | Simple implementation, no extra table, matches "Present-Simple Implementation" constitution principle | User confirmed; custom categories explicitly out of scope in spec | final |
| Expandable UI section for loss details | Clean default view, reveals details only when needed, matches spec's "optional details section" description | User confirmed; spec mentions checkbox "Record loss details" | final |
| Defer reporting to separate feature | Robust reporting feature exists on feature map; keeps F025 focused on core recording | User confirmed; removes P3 scope (US6, US7) from F025 | final |

## Evidence Highlights

Key findings from codebase research:

- **ProductionRun model** (`src/models/production_run.py:27-154`) - Existing entity has `expected_yield`, `actual_yield`, `per_unit_cost`, `total_ingredient_cost` fields. No loss tracking fields yet. Adding `production_status` and `loss_quantity` fits naturally.

- **batch_production_service** (`src/services/batch_production_service.py:183-353`) - `record_batch_production()` function handles production recording with FIFO consumption. Already validates `actual_yield >= 0` but doesn't enforce `actual_yield <= expected_yield`. Loss validation and recording logic will extend this function.

- **RecordProductionDialog** (`src/ui/forms/record_production_dialog.py:25-450`) - Current dialog has batch count, expected yield (read-only), actual yield (editable), notes, and event selector. Loss section will be inserted between notes and availability display.

- **Constitution check** - Principle VI (Schema Change Strategy) confirms export/reset/import cycle for schema changes. No Alembic migrations needed.

- **Risks/Concerns**:
  - Session management - must follow session passing pattern per CLAUDE.md to avoid detached object issues
  - Import/export - must update production export/import to include new loss fields

## Next Actions

Phase 0 complete. Proceed to Phase 1 (Design & Contracts):

1. Generate `data-model.md` with ProductionRun enhancements and ProductionLoss entity
2. Update `plan.md` with implementation approach
3. Run agent context update script

> Keep this document living. As more evidence arrives, update decisions and rationale so downstream implementers can trust the history.
