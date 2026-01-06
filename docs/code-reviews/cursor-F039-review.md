# Cursor Code Review: Feature 039 - Planning Workspace (Service Layer)

**Date:** 2026-01-06
**Reviewer:** Cursor (AI Code Review)
**Feature:** 039-planning-workspace
**Branch/Worktree:** `.worktrees/039-planning-workspace`
**Scope:** Service Layer Only (WP01-WP06) - UI work packages (WP07-WP09) pending

## Summary

F039’s service-layer foundation is in good shape: batch calculations **always round up**, bundle explosion supports nesting with cycle detection, feasibility/progress DTOs are present, and staleness detection correctly normalizes timezone-aware vs naive datetimes. All requested verification commands passed, including the full test suite.

Main gaps/risk areas before UI work begins:
- `calculate_plan()` currently persists **empty** `shopping_list` and `aggregated_ingredients` (explicit TODOs), which will likely block a useful Planning Workspace UI until wired up.
- Several wrappers accept `session` but call `event_service` functions that **do not accept sessions**, so the “session passthrough” contract is only partially satisfied and may cause transaction-boundary surprises.

## Verification Results

### Module Import Validation
- production_plan_snapshot.py: **PASS**
- batch_calculation.py: **PASS**
- shopping_list.py: **PASS**
- feasibility.py: **PASS**
- progress.py: **PASS**
- planning_service.py: **PASS**

### Test Results
- Batch calculation tests: **28 passed, 0 failed**
- Shopping list tests: **25 passed, 0 failed**
- Feasibility tests: **18 passed, 0 failed**
- Progress tests: **29 passed, 0 failed**
- Planning service tests: **27 passed, 0 failed**
- Full test suite: **1672 passed, 14 skipped, 0 failed**

### Code Pattern Validation
- Model layer (WP01): **mostly correct**
- Batch calculation (WP02): **correct**
- Shopping list (WP03): **correct DTOs + correct gap math; session passthrough is partial**
- Feasibility (WP04): **correct core logic; partial “max assemblable” can overestimate when packaging is limiting**
- Progress (WP05): **correct DTOs; session passthrough is partial**
- Planning facade (WP06): **correct core orchestration + staleness normalization; persisted `shopping_list`/`aggregated_ingredients` not yet wired**

## Findings

### Critical Issues

None found (no test/import blockers; full suite passed).

### Warnings

1. **`calculate_plan()` persists empty `shopping_list` and `aggregated_ingredients`**
   - Evidence: `src/services/planning/planning_service.py` builds `calculation_results` with:
     - `"aggregated_ingredients": [],  # TODO: Populate from recipe aggregation`
     - `"shopping_list": [],  # Will be populated if event_service has data`
   - Impact: UI work (WP07-WP09) won’t be able to display the key “Need/Have/Buy” shopping list or ingredient aggregation unless this is implemented.
   - Recommendation: In `_calculate_plan_impl`, call the shopping list service (`src/services/planning/shopping_list.py`) and persist the computed DTOs (or a serializable dict form). For `aggregated_ingredients`, either populate via a dedicated aggregation service or explicitly scope it out in the spec/contract.

2. **Session passthrough is only partially honored due to `event_service` API limitations**
   - Evidence:
     - `src/services/planning/shopping_list.py` notes it cannot pass session through to `event_service.get_shopping_list(...)`.
     - `src/services/planning/progress.py` similarly calls `event_service.get_production_progress(...)` / `get_assembly_progress(...)` without passing session.
   - Impact: Callers passing a `session` may expect all reads to occur within that transaction; instead, `event_service` may open its own session and observe different data or break consistency in tests/operations.
   - Recommendation: Add optional `session` parameters to the relevant `event_service` functions and thread the session through, or refactor planning services to query the underlying models directly when `session` is supplied.

3. **Feasibility “max assemblable” can overestimate when packaging is the limiting component**
   - Evidence: `src/services/planning/feasibility.py::_calculate_max_assemblable()` skips `packaging_product_id` components entirely, while `assembly_service.check_can_assemble()` can fail due to packaging shortages.
   - Impact: `can_assemble` may be reported as non-zero (or high) even when real assembly is blocked by packaging inventory, leading to incorrect `FeasibilityStatus` and misleading UI.
   - Recommendation: Either:
     - compute `can_assemble` via a true binary-search using `assembly_service.check_can_assemble(qty, session=session)` (which accounts for packaging), or
     - incorporate packaging availability into the “min across components” calculation with a proper inventory lookup.

4. **Test warnings: known FK cycle during SQLite schema teardown**
   - Evidence: pytest warnings include “unresolvable foreign key dependency exists between tables: production_runs, recipe_snapshots”.
   - Impact: Non-blocking for now, but can hide real teardown issues and slow down test runs with noisy output.
   - Recommendation: Keep as known/accepted warning for Phase 2; consider longer-term schema-cycle mitigation (`use_alter=True`) or controlled FK disable during drops if needed.

### Observations

- **Timezone handling is done thoughtfully**: `_normalize_datetime()` converts aware datetimes to naive UTC, avoiding SQLite naive/aware comparison errors.
- **Bundle recursion + cycle detection**: `explode_bundle_requirements()` uses a `_visited` set to detect circular references and raises `ValueError` when detected.
- **Over-production handling**: Progress calculations allow percentages > 100% for individual targets but cap at 100% when averaging overall progress—good UX for dashboards.

## Files Reviewed

| File                                       | Status            | Notes                                                                                                                |
| ------------------------------------------ | ----------------- | -------------------------------------------------------------------------------------------------------------------- |
| src/models/production_plan_snapshot.py     | OK                | Required fields and helper methods present; JSON blob contract is clear.                                             |
| src/models/event.py                        | OK                | `OutputMode` added and `Event.output_mode` + snapshots relationship present.                                         |
| src/services/planning/batch_calculation.py | OK                | Uses `math.ceil` for round-up; recursion + cycle detection implemented.                                              |
| src/services/planning/shopping_list.py     | OK (with warning) | Correct `Decimal` usage and gap math; cannot pass session into `event_service`.                                      |
| src/services/planning/feasibility.py       | OK (with warning) | Partial assembly “min across components” logic works for FinishedUnit/FinishedGood; packaging case can overestimate. |
| src/services/planning/progress.py          | OK (with warning) | DTOs are correct; `available_to_assemble` defaults to 0; underlying `event_service` calls ignore supplied session.   |
| src/services/planning/planning_service.py  | OK (with warning) | Orchestration works; staleness normalization is good; snapshot currently stores empty shopping/aggregation lists.    |
| src/services/planning/__init__.py          | OK                | Public exports appear consistent with prompt import list.                                                            |
| src/tests/services/planning/*.py           | OK                | Strong coverage for rounding, nesting, staleness, progress edge cases.                                               |

## Functional Requirements Verification

| Requirement                                   | Status                               | Evidence                                                                                                    |
| --------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| FR-001: Batch calculation always rounds UP    | PASS                                 | `batch_calculation.calculate_batches()` uses `math.ceil` and tests assert no shortfall.                     |
| FR-002: Waste percentage calculated correctly | PASS                                 | `calculate_waste()` returns `(waste_units, waste_percent)`; tested with tolerances.                         |
| FR-003: Bundle explosion handles nesting      | PASS                                 | Nested bundle test in `test_batch_calculation.py`.                                                          |
| FR-004: Circular reference detection          | PASS (not directly tested)           | `_visited` set check in `explode_bundle_requirements()` raises `ValueError`. Consider adding explicit test. |
| FR-005: Shopping gap never negative           | PASS                                 | `calculate_purchase_gap()` uses `max(Decimal(0), needed - in_stock)` and has tests.                         |
| FR-006: Feasibility status accurate           | PASS (with packaging caveat)         | Tests cover AWAITING_PRODUCTION/PARTIAL/CAN_ASSEMBLE; packaging edge case not covered.                      |
| FR-007: Partial assembly calculation correct  | PASS                                 | Tests verify min across components.                                                                         |
| FR-008: Progress tracking accurate            | PASS                                 | Unit tests validate percent calculations and overall status logic.                                          |
| FR-009: Staleness detection works             | PASS                                 | `_normalize_datetime()` + timestamp comparisons; tests cover modified-event staleness.                      |
| FR-010: Plan persists to snapshot             | PASS (with data completeness caveat) | Snapshot is created and flushed; persisted payload currently omits shopping/ingredient aggregates.          |
| Session management pattern followed           | PARTIAL                              | Many services accept `session`; some delegate to `event_service` that does not accept session.              |
| All existing tests pass (no regressions)      | PASS                                 | Full suite: 1672 passed, 14 skipped, 0 failed.                                                              |

## Work Package Verification

| Work Package                    | Status              | Notes                                                                                             |
| ------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------- |
| WP01: Model Foundation          | PASS                | Snapshot model + event output mode + relationship present.                                        |
| WP02: Batch Calculation Service | PASS                | Round-up, waste, nesting, aggregation all present and tested.                                     |
| WP03: Shopping List Service     | PASS (with warning) | Correct behavior; session passthrough limitation stems from `event_service`.                      |
| WP04: Feasibility Service       | PASS (with warning) | Correct core behavior; packaging component handling may misreport `can_assemble`.                 |
| WP05: Progress Service          | PASS (with warning) | Correct calculations; `available_to_assemble` placeholder (0) may need enhancement for UI.        |
| WP06: Planning Service Facade   | PASS (with warning) | Orchestration and staleness are solid; needs wiring for persisted shopping/ingredient aggregates. |

## Code Quality Assessment

### Session Management

Session pattern is used consistently at the function boundaries, but the contract is weakened where underlying dependencies don’t accept `session`. This should be addressed before UI work depends on strong transactional behavior.

### Edge Cases

- Circular reference detection exists but lacks an explicit unit test.
- Packaging-limited assembly feasibility may be misrepresented by `can_assemble` math.

### Data Types

- `Decimal` is used for shopping quantities and gap calculation (good).
- Datetime comparisons normalize aware/naive correctly for SQLite.

### Test Coverage

Test coverage is strong for the core algorithms (round-up math, nesting, staleness, progress). Consider adding:
- a dedicated circular-reference test for bundle explosion
- a packaging-limited feasibility test to prevent overestimated `can_assemble`

## Potential Issues

### Datetime Handling

Looks correct: `_normalize_datetime()` provides consistent comparisons between SQLite-naive and app-aware datetimes.

### Decimal Precision

Shopping list gap logic uses `Decimal` and preserves precision; conversion from event_service floats is done via `Decimal(str(...))`, which is the right pattern.

### Error Handling

Exceptions are defined and used for missing events/output_mode. Some “missing records” paths return empty results (e.g., missing FinishedGood in bundle explosion) which is acceptable but should be consistent with UI expectations.

## Conclusion

**APPROVED WITH CHANGES**

**Next Steps:**
- Wire `calculate_plan()` to actually populate and persist `shopping_list` and `aggregated_ingredients` (or explicitly remove from the contract until implemented).
- Improve session passthrough by adding `session` support in `event_service` methods used by planning wrappers.
- Fix/clarify feasibility `can_assemble` for packaging-limited scenarios (prefer a correctness-first approach using `assembly_service.check_can_assemble`).

