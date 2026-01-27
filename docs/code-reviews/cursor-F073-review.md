# Code Review Report: F073 - Batch Calculation & User Decisions

**Reviewer**: Cursor  
**Date**: 2026-01-22  
**Verdict**: APPROVE WITH SUGGESTIONS

## Executive Summary
Batch calculation now produces floor/ceil options per FinishedUnit with shortfall awareness, and batch decisions persist via a dedicated service and model. Tests cover option generation, validation, session threading, and CRUD, all passing. A minor robustness gap remains: `batch_decision_service.save_batch_decision` doesn’t dedupe concurrent requests or enforce uniqueness beyond the DB constraint; defensive upsert logic could be tightened.

## Verification Results
- `/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/test_batch_calculation.py src/tests/test_batch_decision_service.py -v --tb=short`: **PASS** (49 tests; only existing SAWarnings on test teardown)

## Findings

### Critical Issues (must fix)
- None observed.

### Suggestions (should consider)
- Harden batch decision upsert against duplicate concurrent saves by normalizing to a single `event_id + recipe_id + finished_unit_id` decision (e.g., DB-level unique constraint already exists; consider explicit `merge`/`ON CONFLICT` style pattern or explicit delete-then-insert) to avoid IntegrityErrors if called in parallel.

### Observations (informational)
- Batch options use path-aware decomposition from F072; session parameter threads through calculate/save/get/delete APIs.
- Shortfall detection guards saves unless explicitly confirmed.
- Replace semantics for decisions per event/recipe/FU are exercised in tests.

## Areas Reviewed
- Services: `planning_service` batch option generation; `batch_decision_service` CRUD/validation
- Models: `batch_decision` export
- UI: `batch_options_frame` integration (brief scan, aligns with tests)
- Tests: `test_batch_calculation.py`, `test_batch_decision_service.py`

## Recommendation
APPROVE WITH SUGGESTIONS — ship, and consider tightening batch decision upsert to avoid duplicate inserts under concurrent calls.***
