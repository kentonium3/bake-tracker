## Code Review: Feature 017 — Event Reporting & Production Dashboard

**Worktree reviewed**: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/017-event-reporting-production/`

### Scope / Files Reviewed

- **Services**: `src/services/event_service.py`
  - `export_shopping_list_csv()`
  - `get_recipient_history()`
  - `get_event_cost_analysis()`
  - Progress helpers used by UI: `get_production_progress()`, `get_assembly_progress()`, `get_event_overall_progress()`
- **UI**:
  - `src/ui/main_window.py` (tab order / default tab)
  - `src/ui/production_dashboard_tab.py` (event progress selector + progress bars)
  - `src/ui/event_detail_window.py` (CSV export button + enhanced summary)
  - `src/ui/recipients_tab.py` (recipient history dialog)
- **Tests**: `src/tests/services/test_event_service_reporting.py` (17 tests)

---

## 1) Critical issues (must fix before merge)

### 1.1 CSV export can report success without creating a file

In `event_service.export_shopping_list_csv()`, if the shopping list has no items and no packaging, the function returns `True` **before** opening/writing the file.

- File: `src/services/event_service.py`
- Behavior:
  - If the user selects a new filename in the save dialog, the UI can show **“Export Successful”** but the CSV may **not exist** (because nothing was written).

**Relevant code (excerpt):**

```python
shopping_data = get_shopping_list(event_id, include_packaging=True)

if not shopping_data["items"] and not shopping_data.get("packaging"):
    # Nothing to export - still return True (empty export is valid)
    return True

with open(file_path, "w", newline="", encoding="utf-8-sig") as csvfile:
    ...
```

**Fix direction (pick one):**
- **Preferred**: Always create the file and write at least the header row (even if no data rows).
- Alternative: Treat as “nothing to export” and have the UI show a friendly message (and do not claim export success).

### 1.2 Python 3.10 compatibility: `datetime.UTC` in tests

The repo declares Python **>= 3.10**, but the new tests use `UTC` from `datetime`, which is **not available** in Python 3.10.

- File: `src/tests/services/test_event_service_reporting.py`
- Code:

```python
from datetime import date, datetime, UTC
...
produced_at=datetime.now(UTC)
```

**Fix direction:** Replace with `timezone.utc`:

```python
from datetime import timezone
...
produced_at=datetime.now(timezone.utc)
```

### 1.3 Likely N+1 query pattern for progress computations (performance risk)

`get_production_progress()` and `get_assembly_progress()` execute aggregate queries **inside a loop over targets**, producing **O(N) queries**. The Production Dashboard calls both methods on event selection, so this can become slow as targets scale.

- File: `src/services/event_service.py`
- Pattern:
  - Query all targets
  - For each target, run a `SUM(...)` query

**Fix direction:** Rewrite to a single aggregated query using `GROUP BY` (e.g., group `ProductionRun` by `recipe_id` for the event) and then merge with targets in Python.

---

## 2) Recommendations (non-blocking)

### 2.1 Session management: avoid composing service functions that each open their own `session_scope()`

The repo’s documented guidance warns against nested/independent `session_scope()` usage for service composition.

- `get_event_cost_analysis()` opens `session_scope()` and then calls `get_shopping_list()`, which itself can open another `session_scope()`.
- This is probably safe right now because the call path is read-only and not modifying tracked ORM objects afterward, but it violates the “service composition should accept `session=None`” rule and is a future foot-gun.

**Recommendation:** For new reporting APIs that may be called from other services, add an optional `session` parameter and reuse it.

### 2.2 Docstring / spec drift (clarity)

- `get_event_cost_analysis()` docstring says it uses `ProductionRun.total_cost` / `AssemblyRun.total_cost`, but implementation actually sums:
  - `ProductionRun.total_ingredient_cost`
  - `AssemblyRun.total_component_cost`
- `export_shopping_list_csv()` docstring says it raises `EventNotFoundError`, but current behavior inherits “missing event → empty list → success” semantics from `get_shopping_list()` / `get_recipe_needs()`.

**Recommendation:** Align docstrings/spec with actual behavior (or adjust code to match the intended behavior).

### 2.3 UI error handling: avoid `print()` in UI layer

`production_dashboard_tab.py` uses `print()` for error cases when loading events/progress.

**Recommendation:** Use existing user-facing patterns (`messagebox`, status bar, service integrator) so failures are visible and actionable.

### 2.4 Consider CSV “formula injection” hardening (Excel)

If exported cells can begin with `=`, `+`, `-`, or `@`, Excel may treat them as formulas.

**Recommendation:** Optionally prefix those values with a leading apostrophe (`'`) to force literal interpretation.

### 2.5 Prefer DTOs over detached ORM objects for UI consumption

`get_recipient_history()` returns ORM objects (`event`, `package`) that will be detached once `session_scope()` exits.

**Recommendation:** Return primitive fields (e.g., `event_name`, `event_date`, `package_name`, ids, status) to reduce accidental lazy-load issues and tighten UI/service boundaries.

---

## 3) Observations about code quality & patterns

### 3.1 Layered architecture

- Overall dependency direction looks correct: UI calls service methods; services use models.
- The CSV export is appropriately implemented in the service layer; UI only triggers export and shows dialogs.

### 3.2 UX requirements match implementation

- **Tab order / default tab**: Production is first and selected by default.
- **Progress bars**: Visual fill is capped at 100%, while text shows the real percentage (supports over-production).
- **CSV encoding**: Uses `utf-8-sig` for Excel compatibility, consistent with the stated design decision.

### 3.3 Cost calculation design decision is implemented (with naming mismatch)

Implementation uses historical cost fields (`total_ingredient_cost` / `total_component_cost`), consistent with the “use cost_at_time from consumption records” intent. The docstrings/spec text should be updated to avoid confusion.

---

## 4) Test coverage review

### 4.1 What’s covered

- `get_event_cost_analysis()` happy paths and basic invariants (returns `Decimal`, variance behavior).
- `get_recipient_history()` includes `fulfillment_status` and date ordering.

### 4.2 Gaps / improvements

- **CSV export creates file when empty** is not actually validated, because the tests use `NamedTemporaryFile()` (the file already exists). Add a test that exports to a path that does **not** already exist and asserts the file is created and contains at least the header.
- The “IO error” test notes it doesn’t truly force an error. Consider mocking `open()` or using an unwritable directory to exercise the exception branch.
- Add (or ensure CI has) a Python 3.10 run to match `requires-python` and catch `datetime.UTC` regressions.

---

## 5) Questions / design clarifications

1. **Empty export behavior**: When there’s nothing to export, should we:
   - Still create a CSV (header-only), or
   - Show “Nothing to export” and skip file creation?

2. **Nonexistent event behavior**: Should `export_shopping_list_csv()` raise `EventNotFoundError` (as docstring says) or be “empty success” (as current code/tests behave)?

3. **Estimated cost semantics**: `get_shopping_list()` computes `total_estimated_cost` only for items with `product_status == 'preferred'`. Is variance intended to exclude “multiple/none/sufficient” items? If yes, consider clarifying in UI text and docstrings so variance isn’t misinterpreted as a full budget delta.

---

## Suggested next steps (actionable checklist)

- [ ] Fix `export_shopping_list_csv()` to always write a file or change UI messaging for empty export
- [ ] Update tests to validate empty export file creation for non-existent file paths
- [ ] Replace `datetime.UTC` usage with Python 3.10 compatible timezone handling
- [ ] Refactor progress services to avoid per-target aggregate queries (use `GROUP BY`)
- [ ] Replace `print()` error handling in `production_dashboard_tab.py` with user-visible messaging
- [ ] Align cost analysis docstrings/spec text with actual fields (`total_ingredient_cost`, `total_component_cost`)
