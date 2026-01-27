# Code Review Report: F071 - Finished Goods Quantity Specification

**Reviewer**: Cursor  
**Date**: 2026-01-22  
**Verdict**: APPROVE WITH SUGGESTIONS

## Executive Summary
Quantity entry for finished goods works end-to-end: UI now includes per-FG quantity inputs with inline validation and save/cancel, quantities load and save via service APIs, and planning tab wiring refreshes availability and preserves cancel state. All F071 tests and required imports pass. One robustness gap remains: duplicate FG IDs passed to `set_event_fg_quantities` would rely on the DB unique constraint and could raise; deduping inputs would harden the API.

## Verification Results
- `./venv/bin/python -c "from src.services.event_service import get_event_fg_quantities, set_event_fg_quantities; print('Service imports OK')"` → **PASS**
- `./venv/bin/python -c "from src.ui.components.fg_selection_frame import FGSelectionFrame; print('UI imports OK')"` → **PASS**
- `./venv/bin/pytest src/tests/test_event_fg_quantities.py src/tests/test_fg_selection_frame.py src/tests/test_planning_tab_fg.py -v --tb=short` → **PASS** (61 passed; existing SAWarning on teardown cycle)

## Findings

### Critical Issues (must fix)
- None observed given current scope and passing tests.

### Suggestions (should consider)
- **Deduplicate FG IDs before insert**: `set_event_fg_quantities` filters invalid IDs/quantities but doesn’t dedupe, so callers passing duplicates could hit the unique constraint on `event_finished_goods`. Deduping valid pairs before insert would make the API more robust without changing intended behavior.

### Observations (informational)
- UI validation: inline “Must be > 0” / “Integer only” feedback plus `has_validation_errors()` gating saves; `get_selected()` excludes invalid/empty quantities, aligning with FR-002/FR-003.
- Persistence: replace-not-append semantics implemented (DELETE + INSERT), empty clears selections; unavailable FGs are filtered via `get_available_finished_goods`, consistent with F070.
- Loading: quantities pre-populate on event selection; cancel reverts to last saved state; notifications for removed FGs remain from F070.
- Tests cover service filtering of invalid FG IDs/quantities, replacement semantics, UI validation, and planning tab integration flow.

## Areas Reviewed
- Services: `get_event_fg_quantities`, `set_event_fg_quantities`, `remove_event_fg`, availability filtering interplay
- UI: `fg_selection_frame` quantity inputs, validation, selection tuple handling; `planning_tab` FG load/save/cancel integration
- Tests: `test_event_fg_quantities.py`, `test_fg_selection_frame.py`, `test_planning_tab_fg.py`

## Recommendation
APPROVE WITH SUGGESTIONS — proceed, and consider deduping FG IDs in `set_event_fg_quantities` to avoid potential unique-constraint errors from duplicate inputs.***
