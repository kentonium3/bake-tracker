---
work_package_id: "WP08"
subtasks:
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
title: "UI Layer Updates"
phase: "Phase 5 - UI Updates"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP07"]
history:
  - timestamp: "2026-01-24T19:47:15Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – UI Layer Updates

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Implementation Command

```bash
# Depends on WP07 (get_plan_summary() exists)
spec-kitty implement WP08 --base WP07
```

---

## Objectives & Success Criteria

Update UI to use on-demand calculation and remove staleness-related displays.

**Success Criteria**:
- [ ] Plan display uses get_plan_summary() instead of cached results
- [ ] Shopping list UI uses on-demand calculation
- [ ] Staleness warning UI components removed
- [ ] UI responsiveness meets <5 second target
- [ ] No errors when viewing existing plans

## Context & Constraints

**Reference Documents**:
- `kitty-specs/065-production-plan-snapshot-refactor/spec.md` - User Story 3, SC-005
- `kitty-specs/065-production-plan-snapshot-refactor/plan.md` - Phase 5 details

**Architecture Principle** (from constitution):
- UI layer (`src/ui/`) must NOT contain business logic
- Services layer provides calculated data; UI displays it

**Key Constraints**:
- Maintain existing user workflows (just change data source)
- Handle loading state while calculation runs
- Graceful degradation for errors

## Subtasks & Detailed Guidance

### Subtask T035 – Identify UI components referencing removed fields

**Purpose**: Find all UI code that accesses calculation_results or staleness fields.

**Steps**:
1. Search for calculation_results references:
   ```bash
   grep -rn "calculation_results" src/ui/
   grep -rn "get_recipe_batches\|get_shopping_list\|get_aggregated_ingredients" src/ui/
   ```

2. Search for staleness references:
   ```bash
   grep -rn "is_stale\|stale_reason\|staleness" src/ui/
   ```

3. Document findings:
   ```
   # Files referencing calculation_results:
   - src/ui/planning/plan_view.py:45 - displays recipe_batches
   - src/ui/planning/shopping_view.py:30 - displays shopping_list
   ...

   # Files referencing staleness:
   - src/ui/planning/plan_view.py:120 - staleness warning banner
   ...
   ```

4. Create list of files to modify in subsequent subtasks

**Files**:
- Document findings (no code changes yet)

**Parallel?**: No - must complete before T036-T038

---

### Subtask T036 – Update plan display to use get_plan_summary()

**Purpose**: Replace snapshot.get_recipe_batches() with service call.

**Steps**:
1. In identified plan view file (likely `src/ui/planning/plan_view.py` or similar):

2. Change from:
   ```python
   # Old pattern - using cached results
   plan_snapshot = get_production_plan_snapshot(event_id)
   recipe_batches = plan_snapshot.get_recipe_batches()
   # ... display recipe_batches
   ```

3. To:
   ```python
   # New pattern - on-demand calculation
   from src.services.planning.planning_service import get_plan_summary

   plan_data = get_plan_summary(event_id)
   recipe_batches = plan_data["recipe_batches"]
   # ... display recipe_batches
   ```

4. Handle loading state:
   ```python
   def _load_plan_data(self, event_id):
       """Load plan data asynchronously to maintain UI responsiveness."""
       self._show_loading_indicator()
       try:
           plan_data = get_plan_summary(event_id)
           self._display_recipe_batches(plan_data["recipe_batches"])
       except Exception as e:
           self._show_error(f"Failed to load plan: {e}")
       finally:
           self._hide_loading_indicator()
   ```

5. Verify displayed data matches old format

**Files**:
- `src/ui/planning/` (identified files from T035)

**Parallel?**: Yes - can be done alongside T037, T038

---

### Subtask T037 – Update shopping list generation to use on-demand calculation

**Purpose**: Replace snapshot.get_shopping_list() with service call.

**Steps**:
1. In shopping list view file:

2. Change from:
   ```python
   # Old pattern
   plan_snapshot = get_production_plan_snapshot(event_id)
   shopping_list = plan_snapshot.get_shopping_list()
   ```

3. To:
   ```python
   # New pattern
   plan_data = get_plan_summary(event_id)
   shopping_list = plan_data["shopping_list"]
   ```

4. If shopping list view is separate from plan view, make separate service call:
   ```python
   def _refresh_shopping_list(self):
       plan_data = get_plan_summary(self.event_id)
       self._display_shopping_list(plan_data["shopping_list"])
   ```

5. Consider caching within UI session if multiple views use same data:
   ```python
   # Cache for current session (not persistent)
   self._cached_plan_data = None

   def _get_plan_data(self):
       if self._cached_plan_data is None:
           self._cached_plan_data = get_plan_summary(self.event_id)
       return self._cached_plan_data
   ```

**Files**:
- `src/ui/planning/` (shopping-related views)

**Parallel?**: Yes - can be done alongside T036, T038

---

### Subtask T038 – Remove staleness warning UI components

**Purpose**: Remove UI elements that display staleness information.

**Steps**:
1. Find staleness warning components (from T035 findings):
   - Warning banners ("Plan is stale, recalculate?")
   - Staleness indicators (icons, badges)
   - Recalculate buttons (if triggered by staleness)

2. Remove or comment out staleness UI code:
   ```python
   # REMOVE this code block
   if plan_snapshot.is_stale:
       self._show_staleness_warning(plan_snapshot.stale_reason)
   ```

3. Remove staleness-related methods:
   ```python
   # REMOVE these methods if only used for staleness
   def _show_staleness_warning(self, reason):
       ...

   def _on_recalculate_clicked(self):
       ...
   ```

4. Remove staleness-related UI elements from layout:
   ```python
   # REMOVE staleness banner from layout
   self.staleness_banner = ctk.CTkLabel(...)
   ```

5. Keep any "refresh" functionality that makes sense without staleness:
   - "Regenerate plan" button can stay (calls create_plan with force_recreate=True)
   - Just remove the "stale" concept

**Files**:
- `src/ui/planning/` (identified files from T035)

**Parallel?**: Yes - can be done alongside T036, T037

---

### Subtask T039 – Verify UI responsiveness meets target

**Purpose**: Ensure UI remains responsive when loading plan data.

**Steps**:
1. Manual testing:
   - Open plan view for event with many targets (10-20 recipes)
   - Verify plan data displays within 5 seconds
   - Verify UI doesn't freeze during calculation

2. Add loading indicators if not already present:
   ```python
   def _load_plan_data(self):
       # Show loading state
       self.loading_label.configure(text="Loading plan...")
       self.loading_label.pack()

       # Disable interactions during load
       self.refresh_button.configure(state="disabled")

       # Load data (consider threading for responsiveness)
       self.after(100, self._do_load_plan_data)

   def _do_load_plan_data(self):
       try:
           plan_data = get_plan_summary(self.event_id)
           self._display_plan_data(plan_data)
       finally:
           self.loading_label.pack_forget()
           self.refresh_button.configure(state="normal")
   ```

3. Consider threading if UI freezes:
   ```python
   import threading

   def _load_plan_data_threaded(self):
       def load():
           plan_data = get_plan_summary(self.event_id)
           self.after(0, lambda: self._display_plan_data(plan_data))

       thread = threading.Thread(target=load)
       thread.start()
   ```

4. Document any performance issues for WP09 or future optimization

**Files**:
- `src/ui/planning/` (main plan views)

**Parallel?**: No - requires T036-T038 complete

---

## Test Strategy

**Manual Testing Checklist**:
- [ ] Create event with targets
- [ ] Create plan (via UI or service)
- [ ] View plan - recipe batches display correctly
- [ ] View shopping list - items display correctly
- [ ] No staleness warnings appear
- [ ] Modify recipe definition
- [ ] View plan again - still shows original snapshot data (immutability)
- [ ] Load time <5 seconds

**Automated Tests** (if UI tests exist):
```bash
./run-tests.sh src/tests/ui/ -v -k "planning"
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI freeze during calculation | Use threading or async loading |
| Missing data fields | Verify get_plan_summary return format matches expectations |
| Broken layout after removing staleness | Test thoroughly; preserve layout structure |

## Definition of Done Checklist

- [ ] All calculation_results references replaced with get_plan_summary()
- [ ] Shopping list uses on-demand calculation
- [ ] Staleness warning UI removed
- [ ] Loading indicators present
- [ ] UI loads in <5 seconds
- [ ] No visual regressions
- [ ] Manual testing complete
- [ ] Activity log entry added

## Review Guidance

Reviewers should verify:
1. No references to removed model fields/methods
2. Service calls follow layer architecture (UI → Services)
3. Error handling present
4. Loading states implemented
5. Layout preserved (no visual regressions)

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-24T19:47:15Z – system – lane=planned – Prompt created.
