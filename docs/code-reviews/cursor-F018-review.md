## Code Review: Feature 018 — Event Production Dashboard

**Worktree reviewed**: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/018-event-production-dashboard/`

### Scope / Files Reviewed (in requested order)

1. `src/utils/constants.py` (STATUS_COLORS)
2. `src/services/event_service.py` (`get_events_with_progress()`)
3. `src/tests/services/test_event_service_progress.py` (new tests for `get_events_with_progress()`)
4. `src/ui/widgets/event_card.py` (new widget)
5. `src/ui/widgets/__init__.py` (exports)
6. `src/ui/production_dashboard_tab.py` (multi-event dashboard)
7. `src/ui/main_window.py` (tab ordering/default)

---

## 1) Summary (Approve / Needs Changes / Reject)

**Needs Changes**

The overall design is good (clean UI composition and a sensible service API). However, there is a **blocking session-management issue**: progress APIs return ORM objects that are then returned to UI outside the session, which violates the project’s documented rules and can cause detached-object / lazy-load problems.

There is also a **performance risk** for the “50 events < 2s” requirement due to per-event overall-progress computation patterns.

---

## 2) Strengths

- **Spec-compliant progress colors**
  - File: `src/utils/constants.py`
  - `STATUS_COLORS` matches the spec:
    - gray: `#808080`
    - orange: `#FFA500`
    - green: `#28A745`
    - teal: `#20B2AA`

- **Architecture / separation of concerns looks healthy**
  - `EventCard` is a presentational widget that renders provided data + invokes callbacks; it does not call services.
  - `ProductionDashboardTab` owns fetching data, building widgets, and routing navigation/dialog actions.

- **Filtering and ordering are straightforward**
  - File: `src/services/event_service.py`
  - `get_events_with_progress(filter_type="active_future"|"past"|"all", date_from/date_to)` reads clearly and is easy to extend.

- **Improved query efficiency for per-event production/assembly progress**
  - File: `src/services/event_service.py`
  - `get_production_progress()` and `get_assembly_progress()` use `GROUP BY` aggregation to avoid N+1 queries per target.

- **UI: default filter and default tab appear correct**
  - `Production` tab is first and selected by default in `src/ui/main_window.py`.
  - Filter dropdown defaults to “Active & Future” in `src/ui/production_dashboard_tab.py`.

- **Tests exist and are meaningful**
  - File: `src/tests/services/test_event_service_progress.py`
  - `TestGetEventsWithProgress` covers:
    - empty DB
    - active_future/past/all
    - date range
    - ordering by (date, name)
    - return data shape + types
    - default filter behavior

---

## 3) Issues (bugs / code smells / concerns)

### 3.1 BLOCKING: Returning ORM objects outside session scope (session management rule violation)

**Problem:** `get_events_with_progress()` returns a structure containing `production_progress` and `assembly_progress`. Those progress lists currently include ORM objects (recipe / finished_good) that were loaded inside `session_scope()` and then returned.

- File: `src/services/event_service.py`
  - `get_production_progress()` adds `{"recipe": target.recipe, ...}`
  - `get_assembly_progress()` adds `{"finished_good": target.finished_good, ...}`
  - `get_events_with_progress()` appends these progress lists onto its returned DTOs.

**Why it matters:** This project explicitly warns about detached objects and requires service methods to avoid returning ORM objects that will be used later outside the session. This is especially risky for UI code (accidental lazy load, attribute access errors, unexpected stale values).

**Recommended fix:** Make reporting/progress APIs return DTOs only.
- Replace `recipe` with `recipe_id` (+ `recipe_name` already present)
- Replace `finished_good` with `finished_good_id` (+ `finished_good_name` already present)

### 3.2 Performance risk vs FR-024 (50 events < 2 seconds)

`get_events_with_progress()` loops events and calls three per-event functions:
- `get_production_progress(event_id)`
- `get_assembly_progress(event_id)`
- `get_event_overall_progress(event_id)`

Even after the GROUP BY improvements for production/assembly, `get_event_overall_progress()` still performs per-target aggregate queries in loops (classic N+1 pattern), and is invoked once per event.

- File: `src/services/event_service.py`
  - `get_event_overall_progress()` still does sum queries inside loops over targets.

**Impact:** With dozens of events, each with multiple targets, this can exceed the 2s dashboard goal.

**Recommended fix:**
- Refactor `get_event_overall_progress()` to use GROUP BY aggregation (similar to production/assembly methods), **and/or**
- Add a batch method to compute overall counts for multiple events in one pass (preferred if FR-024 is strict).

### 3.3 UI error handling uses `print()`

- File: `src/ui/production_dashboard_tab.py`
  - `_rebuild_event_cards()` catches exceptions, prints error, then shows an error message.

**Recommendation:** Use consistent app-level logging and/or the existing service integrator patterns; avoid console-only output in user-facing UI.

### 3.4 Date range validation incomplete

- UI validates date format, but does not validate `from <= to`.
- Service accepts any `filter_type` string; unknown values fall through to “all” semantics.

**Recommendation:**
- Validate `date_from <= date_to` (UI: show messagebox warning; service: optionally raise ValidationError).
- Define behavior for unknown `filter_type` (raise vs default).

---

## 4) Suggestions (non-blocking)

- **Status thresholds in UI**: `EventCard._get_status_color()` uses exact equality checks (`progress_pct == 100`). This is probably fine given the current calculation, but `>= 100` is more robust if computation changes.
- **Additional test cases** (if desired):
  - invalid `filter_type`
  - `date_from > date_to`
  - behavior when `event_date` is NULL (if allowed by schema)
- **Deprecation warnings**: tests use `datetime.utcnow()` in many fixtures; consider migrating to timezone-aware UTC datetimes to reduce noise in CI.

---

## 5) Questions / Clarifications

1. **Service contract:** Is the reporting layer expected to return only DTOs (recommended), or are ORM instances considered acceptable for read-only UI use?
2. **FR-024 strictness:** Is the “50 events < 2s” goal hard? If yes, the overall-progress computation likely needs batching.
3. **Date range UX:** If users enter `from > to`, should we show an error or treat it as an empty result set?

---

## Notes

- `pytest -q src/tests/services/test_event_service_progress.py` passes in this worktree (26 tests).
- The above issues are about correctness/robustness and future safety, not test pass/fail.
