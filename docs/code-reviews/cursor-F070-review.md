# Code Review Report: F070 - Finished Goods Filtering for Event Planning

**Reviewer**: Cursor  
**Date**: 2026-01-22  
**Verdict**: REQUEST CHANGES

## Executive Summary
Filtering, cascade removal, UI integration, and notifications all work per tests: service/UI imports succeed and the F070 test suites pass. However, the bundle decomposition logic (`get_required_recipes`) marks reuse of the same finished good in different branches as a circular reference because `_visited` is global and never popped. This falsely blocks valid bundles that share a component FG, contradicting the spec requirement to show available bundles whenever all atomic recipes are present. Fix the traversal to track recursion path (push/pop) or use a per-branch path set so shared-but-acyclic graphs don’t raise `CircularReferenceError`.

## Verification Results
- `./venv/bin/python -c "from src.services.event_service import get_required_recipes, check_fg_availability, get_available_finished_goods, set_event_finished_goods; print('Service imports OK')"` → **PASS**
- `./venv/bin/python -c "from src.ui.components.fg_selection_frame import FGSelectionFrame; print('UI imports OK')"` → **PASS**
- `./venv/bin/pytest src/tests/test_fg_availability.py src/tests/test_fg_selection_frame.py src/tests/test_planning_tab_fg.py -v --tb=short` → **PASS** (45 tests; existing SAWarning on teardown cycle)

## Findings

### Critical Issues (must fix)
- **False circular detection on shared components**: `get_required_recipes` uses a global `_visited` set without backtracking. If a bundle reuses the same FG in multiple branches (a valid acyclic DAG), the second visit triggers `CircularReferenceError`, treating the FG as unavailable and potentially deleting user selections. This violates FR-001/FR-002/FR-004 by hiding makeable FGs. Fix by tracking the current recursion path (push/pop) or cloning the path set per branch so only true cycles are flagged.

### Suggestions (should consider)
- None beyond the above fix.

### Observations (informational)
- Cascade removal of invalid FGs after recipe changes works and returns descriptive `RemovedFGInfo` used for UI notifications.
- FGSelectionFrame covers explicit checkboxes, selection counts, save/cancel callbacks, and empty-state messaging; PlanningTab integrates refresh/show/hide and removal notifications.
- `set_event_recipes` now returns `(count, removed_fgs)` and tests cover the new contract.

## Areas Reviewed
- Services: FG availability and decomposition (`get_required_recipes`, `check_fg_availability`, `get_available_finished_goods`, `remove_invalid_fg_selections`), recipe/FG selection APIs
- UI: `fg_selection_frame`, `planning_tab` FG integration
- Tests: `test_fg_availability.py`, `test_fg_selection_frame.py`, `test_planning_tab_fg.py`

## Recommendation
REQUEST CHANGES — Correct the bundle traversal to only treat true cycles as errors and allow reuse of the same FG in multiple branches. Re-run the F070 test suite after the fix.***
