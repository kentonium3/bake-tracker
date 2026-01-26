# Code Review Report: F068 - Event Management & Planning Data Model

**Reviewer**: Cursor  
**Date**: 2026-01-22  
**Verdict**: REQUEST CHANGES

## Executive Summary
Planning data model tables, event planning fields, and import/export coverage are in place and the F068 test suite passes. However, planning event creation/update skips basic validation of required fields and defers to the database to enforce non-null constraints, producing IntegrityErrors instead of the spec-required ValidationError UX. Also, the new `expected_attendees` field lacks a database-level guard, so imports or direct inserts can persist negative/zero values despite service-level checks. Address these to meet spec requirements for validation and data integrity.

## Verification Results
- `./run-tests.sh -v -k "test_event_exports_expected_attendees"`: **PASS**
- `./run-tests.sh src/tests/integration/test_import_export_planning.py -v`: **PASS** (11 passed; SAWarning about drop_all cycle already known)

## Findings

### Critical Issues (must fix)
- **Missing validation for required event fields (spec FR-001/FR-002)**: `event_service.create_planning_event` and `update_planning_event` do not validate `name` or `event_date`. Empty/None values flow to the DB and raise IntegrityErrors instead of the expected `ValidationError` UX. This violates the spec’s required-field validation and will surface as unhandled DB errors in UI/API callers. Add explicit validation mirroring legacy event creation (non-empty name, valid date) before flushing.

### Suggestions (should consider)
- **Enforce attendee positivity at the DB layer**: `expected_attendees` is nullable but unconstrained; imports/direct inserts can persist negative or zero values, bypassing service validation. Add a `CheckConstraint(expected_attendees > 0)` (allowing NULL) to `events` to keep planning data clean.
- **Harmonize planning event validation errors**: The new `_validate_expected_attendees` returns a list of errors, but missing-name/date paths currently raise single strings elsewhere. Standardize the error payload format so UI error handling remains consistent across planning vs legacy event flows.

### Observations (informational)
- Planning import/export coverage looks complete: events include `expected_attendees`/`plan_state`; new planning tables (event_recipes, event_finished_goods, batch_decisions, plan_amendments) export/import and round-trip as verified by `test_import_export_planning`.
- UI `PlanningTab` displays plan_state and attendees with sensible formatting and uses `session_scope` per existing UI pattern; no blocking issues observed here for F068.
- Existing SAWarning during test DB teardown (cycle between assembly_runs/production_runs/finished_good_snapshots/recipe_snapshots) persists; unrelated to F068 but still present.

## Areas Reviewed
- Models: `event.py`, `event_recipe.py`, `event_finished_good.py`, `batch_decision.py`, `plan_amendment.py`, `planning_snapshot.py`, `models/__init__.py`
- Services: `event_service` (planning methods), `import_export_service` (planning export/import)
- UI: `ui/planning_tab.py`
- Tests: `src/tests/integration/test_import_export_planning.py`
- Verification commands as specified in the prompt

## Recommendation
REQUEST CHANGES — Add required-field validation for planning event create/update (returning `ValidationError`) and tighten attendee integrity (DB check + consistent error payloads). After these are fixed, re-run the F068 verification commands.***
