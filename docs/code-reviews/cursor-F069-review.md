# Code Review Report: F069 - Recipe Selection for Event Planning

**Reviewer**: Cursor  
**Date**: 2026-01-22  
**Verdict**: APPROVE WITH SUGGESTIONS

## Executive Summary
Recipe selection flows are implemented end-to-end: event recipe IDs can be read/written atomically, the new RecipeSelectionFrame UI provides explicit per-recipe checkboxes with base/variant distinction and live counts, and selection persistence/round-trip is covered by service and UI tests. Tests and verification commands pass. One minor robustness gap remains: duplicate recipe IDs in `set_event_recipes` can raise an IntegrityError due to the unique constraint; deduping inputs would harden the API surface.

## Verification Results
- `./run-tests.sh -v -k "test_returns_empty_list_when_no_selections"`: **PASS** (1 selected, SAWarning from test teardown cycles)
- `./run-tests.sh src/tests/test_recipe_selection.py src/tests/test_recipe_selection_frame.py -v`: **PASS** (27 passed, same teardown SAWarnings)

## Findings

### Critical Issues (must fix)
- None observed given current scope and passing tests.

### Suggestions (should consider)
- **Deduplicate recipe IDs before insert**: `set_event_recipes` deletes then re-inserts all selections but does not dedupe `recipe_ids`. If a caller ever passes duplicates (e.g., via API misuse), the unique constraint on `event_recipes` will raise an IntegrityError. Deduping upfront (while preserving validation of all supplied IDs) would make the API more robust without changing intended behavior.

### Observations (informational)
- UI meets spec intent: flat list, base/variant distinction via indent/label, independent checkboxes, live count, cancel reverts to last-saved selection, and selections replace rather than append.
- Service methods validate event existence and recipe IDs before mutation and perform replace semantics in a single transaction.
- SAWarning about cyclic FK teardown persists from existing test infrastructure; unrelated to this feature.

## Areas Reviewed
- Services: `event_service.get_event_recipe_ids`, `set_event_recipes`
- UI: `src/ui/components/recipe_selection_frame.py`, `src/ui/planning_tab.py` integration
- Models/exports: event-related planning models already established in F068
- Tests: `src/tests/test_recipe_selection.py`, `src/tests/test_recipe_selection_frame.py`

## Recommendation
APPROVE WITH SUGGESTIONS — ship as-is, with a small hardening follow-up to dedupe recipe IDs in `set_event_recipes` to avoid potential IntegrityErrors from duplicate inputs.***
