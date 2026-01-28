# Code Review Report: F078 Plan Snapshots & Amendments

**Reviewer**: Cursor  
**Date**: 2026-01-22  
**Commit**: [not provided]

## Summary
Plan snapshots are captured at production start and amendments (drop/add FG, modify batches) are recorded with required reasons during production. Comparison utilities detect plan deltas. Tests for snapshot creation, comparison, amendment validation, and amendment CRUD all pass. Overall implementation aligns with the spec; a couple of UX/guard improvements are suggested.

## Blockers
None.

## Critical Issues
- None observed in code or tests.

## Recommendations
- Surface clearer errors in `plan_amendment_service` when invoked outside IN_PRODUCTION (current rejection is correct but messaging could guide users to state transitions).
- Consider including snapshot metadata (creator/timestamp) in comparison output to aid audit, if not already captured elsewhere.

## Observations
- Snapshot creation is idempotent and triggered on start_production; snapshot JSON includes recipes, FGs, and batches, with comparison detecting added/dropped/unchanged items.
- Amendments enforce non-empty reasons and valid states; batch modifications validate positive counts.
- Amendments returned in chronological order; data classes for comparison and amendments are clear and test-covered.
- Tests: `test_plan_snapshot_service.py` and `test_plan_amendment_service.py` all passed (31 tests; known SAWarnings on teardown).

## Verification Results
- Imports: `PlanSnapshot`, `plan_snapshot_service`, `plan_amendment_service` **OK**
- Tests: `pytest src/tests/test_plan_snapshot_service.py src/tests/test_plan_amendment_service.py -v --tb=short` **PASS** (31 passed; SAWarnings from teardown remain).***
