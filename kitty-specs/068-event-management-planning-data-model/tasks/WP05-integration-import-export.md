---
work_package_id: WP05
title: Integration & Import/Export
lane: "doing"
dependencies:
- WP03
base_branch: 068-event-management-planning-data-model-WP03
base_commit: 91aea46bcfa7d839a18b7f2a11f0debdbcbd7004
created_at: '2026-01-26T21:42:23.850498+00:00'
subtasks:
- T027
- T028
- T029
- T030
- T031
phase: Phase 3 - Integration
assignee: ''
agent: ''
shell_pid: "99642"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-26T19:16:03Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Integration & Import/Export

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

**Depends on WP03 AND WP04** - Branch from merged WP03+WP04:

If WP03 and WP04 have been merged to a common branch:
```bash
spec-kitty implement WP05 --base WP04
```

Or if merging both into main first:
```bash
spec-kitty implement WP05
```

**Agent Assignment**: Claude (lead) - Integration requires careful coordination.

---

## Objectives & Success Criteria

**Goal**: Wire Planning tab into the application, update import/export for new tables, and validate complete workflow.

**Success Criteria**:
- [ ] Planning tab visible in main application window
- [ ] Create/Edit/Delete dialogs work from Planning tab
- [ ] New planning tables included in export
- [ ] New planning tables imported correctly
- [ ] Full CRUD workflow: Create → View → Edit → Delete
- [ ] Cascade delete removes all associations
- [ ] Export/Import preserves all planning data

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/068-event-management-planning-data-model/spec.md` (all user stories)
- Plan: `kitty-specs/068-event-management-planning-data-model/plan.md`
- Data model: `kitty-specs/068-event-management-planning-data-model/data-model.md` (Import/Export Order section)
- Constitution: `.kittify/memory/constitution.md` (Principle VI: Export/Reset/Import)

**Key Files to Modify**:
- `src/main.py` or main window class - Add Planning tab
- `src/services/import_export_service.py` - Add new tables
- WP03's `src/ui/planning_tab.py` - Wire callbacks
- WP04's `src/ui/forms/event_planning_form.py` - Ensure ready

**Constraints**:
- Follow Constitution Principle VI for schema changes
- Import/export order must respect FK dependencies
- Integration must not break existing functionality

---

## Subtasks & Detailed Guidance

### Subtask T027 – Add Planning Tab to Main Application Window

**Purpose**: Make Planning tab visible and accessible in the application.

**Steps**:
1. Find the main application window (likely `src/main.py` or `src/ui/main_window.py`)
2. Study how existing tabs are added (likely notebook widget or tab control)
3. Import PlanningTab:

```python
from src.ui.planning_tab import PlanningTab
```

4. Add the Planning tab to the notebook/tab control:

```python
# Example pattern (adjust to match existing code):
self.planning_tab = PlanningTab(
    self.notebook,  # or self.tab_control
    on_create_event=self._on_create_planning_event,
    on_edit_event=self._on_edit_planning_event,
    on_delete_event=self._on_delete_planning_event,
)
self.notebook.add(self.planning_tab, text="Planning")
```

5. Implement callback handlers that open dialogs:

```python
from src.ui.forms.event_planning_form import EventPlanningForm, DeleteEventDialog

def _on_create_planning_event(self) -> None:
    """Open Create Event dialog."""
    EventPlanningForm.create_event(
        master=self,
        on_save=self._on_planning_event_saved,
    )

def _on_edit_planning_event(self, event: Event) -> None:
    """Open Edit Event dialog."""
    EventPlanningForm.edit_event(
        master=self,
        event=event,
        on_save=self._on_planning_event_saved,
    )

def _on_delete_planning_event(self, event: Event) -> None:
    """Open Delete Event confirmation."""
    DeleteEventDialog(
        master=self,
        event=event,
        on_confirm=lambda: self._on_planning_event_deleted(event.name),
    )

def _on_planning_event_saved(self, result: dict) -> None:
    """Handle event save completion."""
    self.planning_tab.refresh()
    self.planning_tab._update_status(
        f"Event '{result['name']}' {result['action']}."
    )

def _on_planning_event_deleted(self, event_name: str) -> None:
    """Handle event deletion."""
    self.planning_tab.refresh()
    self.planning_tab._update_status(f"Event '{event_name}' deleted.")
```

**Files**: `src/main.py` or `src/ui/main_window.py` (modify, ~50 lines)
**Parallel?**: No - core integration work
**Validation**: Application launches with Planning tab visible

---

### Subtask T028 – Add New Planning Tables to Import/Export Service

**Purpose**: Enable export and import of planning data for schema changes.

**Steps**:
1. Open `src/services/import_export_service.py`
2. Find the export table list/order
3. Add new tables in correct FK dependency order:

```python
# Add AFTER events but respecting FK dependencies:
# - event_recipes (depends on: events, recipes)
# - event_finished_goods (depends on: events, finished_goods)
# - batch_decisions (depends on: events, recipes, finished_units)
# - plan_amendments (depends on: events)

PLANNING_TABLES = [
    "event_recipes",
    "event_finished_goods",
    "batch_decisions",
    "plan_amendments",
]
```

4. Add to export method:

```python
# In export method, after existing tables:
for table_name in PLANNING_TABLES:
    self._export_table(session, table_name, export_data)
```

5. Add to import method (in correct order):

```python
# In import method, AFTER parent tables (events, recipes, finished_goods, finished_units):
for table_name in PLANNING_TABLES:
    if table_name in import_data:
        self._import_table(session, table_name, import_data[table_name])
```

6. Add model imports:

```python
from src.models import (
    EventRecipe,
    EventFinishedGood,
    BatchDecision,
    PlanAmendment,
)
```

7. Add table-to-model mapping if needed:

```python
TABLE_MODEL_MAP = {
    # ... existing mappings ...
    "event_recipes": EventRecipe,
    "event_finished_goods": EventFinishedGood,
    "batch_decisions": BatchDecision,
    "plan_amendments": PlanAmendment,
}
```

**Files**: `src/services/import_export_service.py` (modify, ~30 lines)
**Parallel?**: No - affects data integrity
**Notes**:
- Import order is critical - parent tables before child tables
- Export order doesn't matter as much but keep consistent

---

### Subtask T029 – Integration Test: Full CRUD Flow

**Purpose**: Verify the complete workflow works end-to-end.

**Steps**:
1. Create a manual test script or document test steps:

```python
"""
Integration Test: F068 Event Management CRUD

Prerequisites:
- Application starts without errors
- Planning tab visible

Test Steps:

1. CREATE EVENT
   - Click "Create Event" button
   - Enter: Name="Test Event", Date="2026-07-04", Attendees="50"
   - Click Save
   - Expected: Event appears in list, status shows "created"

2. VIEW EVENT
   - Verify event shows in list with correct data:
     - Name: "Test Event"
     - Date: "2026-07-04"
     - Attendees: "50"
     - Plan State: "Draft"

3. EDIT EVENT
   - Select event in list
   - Click "Edit Event" button
   - Change: Name="Updated Event", Attendees="75"
   - Click Save
   - Expected: Event updates in list, status shows "updated"

4. DELETE EVENT
   - Select event in list
   - Click "Delete Event" button
   - Confirm deletion
   - Expected: Event removed from list, status shows "deleted"

5. VALIDATION TESTS
   - Try Create with empty name → Error message
   - Try Create with empty date → Error message
   - Try Create with negative attendees → Error message
   - Try Create with non-numeric attendees → Error message
"""
```

2. Optionally create automated integration test:

```python
# src/tests/integration/test_planning_integration.py

def test_full_crud_workflow(app_fixture):
    """Test complete CRUD workflow for events."""
    # This would require UI testing framework (e.g., pytest-ctk)
    # Document manual test steps if automated testing not available
    pass
```

**Files**: `src/tests/integration/test_planning_integration.py` or manual test document
**Parallel?**: No - requires all components
**Validation**: All manual test steps pass

---

### Subtask T030 – Validate Import/Export Preserves Planning Data

**Purpose**: Ensure export/reset/import cycle preserves planning data.

**Steps**:
1. Create test scenario:

```
Test: Export/Import Planning Data

Setup:
1. Create event "Holiday 2026" with 50 attendees, date 2026-12-20
2. (Future: Add recipe selections, FG selections, batch decisions)

Export:
3. Export all data to JSON
4. Verify JSON contains:
   - events entry with expected_attendees and plan_state
   - event_recipes (empty for now, but key exists)
   - event_finished_goods (empty for now)
   - batch_decisions (empty for now)
   - plan_amendments (empty for now)

Reset:
5. Delete database
6. Recreate empty database

Import:
7. Import JSON data
8. Verify:
   - Event "Holiday 2026" exists
   - expected_attendees = 50
   - plan_state = "draft"
   - event_date = 2026-12-20
```

2. Add test to verify new fields export correctly:

```python
def test_event_planning_fields_export():
    """Verify expected_attendees and plan_state export."""
    with session_scope() as session:
        # Create event with planning fields
        service = EventService()
        event = service.create_planning_event(
            session,
            name="Test Export",
            event_date=date(2026, 12, 20),
            expected_attendees=50,
        )
        session.commit()

        # Export
        export_service = ImportExportService()
        data = export_service.export_all(session)

        # Verify
        events = data.get("events", [])
        test_event = next((e for e in events if e["name"] == "Test Export"), None)

        assert test_event is not None
        assert test_event["expected_attendees"] == 50
        assert test_event["plan_state"] == "draft"
```

**Files**: `src/tests/test_import_export_planning.py` (new or extend existing)
**Parallel?**: No - requires export/import complete
**Validation**: Export JSON contains new fields, import restores them

---

### Subtask T031 – Final UI Polish and Edge Case Handling

**Purpose**: Address edge cases and polish user experience.

**Steps**:
1. Handle edge cases in Planning tab:

```python
# Empty state - no events
if len(events) == 0:
    self._update_status("No events found. Click 'Create Event' to start planning.")

# Many events - consider pagination (document for future)
# For F068, just load all events (expected <50 per year)
```

2. Verify NULL handling:
   - expected_attendees = NULL displays as "-"
   - notes = NULL doesn't cause errors

3. Verify date formatting consistency:
   - All dates show as YYYY-MM-DD
   - Date picker/entry accepts YYYY-MM-DD

4. Verify plan_state display:
   - "draft" → "Draft"
   - "locked" → "Locked"
   - "in_production" → "In Production"
   - "completed" → "Completed"

5. Add keyboard shortcuts (optional enhancement):
   - Enter in dialog saves
   - Escape in dialog cancels

```python
# In EventPlanningForm.__init__:
self.bind("<Return>", lambda e: self._on_save_click())
self.bind("<Escape>", lambda e: self._on_close())
```

6. Verify error recovery:
   - Database error during save shows message, doesn't crash
   - Network timeout (if applicable) shows message

**Files**: Various UI files (minor tweaks)
**Parallel?**: No - final polish
**Validation**: All edge cases handled gracefully

---

## Test Strategy

**Manual Testing Checklist**:

| Test | Expected Result | Pass? |
|------|-----------------|-------|
| App launches with Planning tab | Tab visible | |
| Create Event button works | Dialog opens | |
| Create with valid data | Event added to list | |
| Create with empty name | Validation error | |
| Create with empty date | Validation error | |
| Create with invalid date | Validation error | |
| Create with negative attendees | Validation error | |
| Edit Event button (with selection) | Dialog opens with data | |
| Edit saves changes | List updates | |
| Delete Event button (with selection) | Confirmation dialog | |
| Delete confirms and removes | Event gone from list | |
| Export includes planning tables | JSON has keys | |
| Import restores planning data | Data matches original | |
| Refresh button updates list | List reloads | |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Main window structure differs from expected | Study existing tabs before modifying |
| Import/export order breaks FK constraints | Test import with fresh database |
| WP03/WP04 merge conflicts | Coordinate file boundaries; they touch different files |

---

## Definition of Done Checklist

- [ ] Planning tab visible in application
- [ ] Create Event works end-to-end
- [ ] Edit Event works end-to-end
- [ ] Delete Event works with confirmation
- [ ] List refreshes after changes
- [ ] Status bar shows feedback
- [ ] New tables in export JSON
- [ ] Import restores planning data
- [ ] Cascade delete removes associations
- [ ] Edge cases handled gracefully
- [ ] All existing functionality still works
- [ ] Manual test checklist passes

---

## Review Guidance

**Reviewers should verify**:
1. Planning tab integrated correctly (matches other tabs)
2. Dialogs open from correct button clicks
3. Callbacks refresh list and show status
4. Import/export order respects FK dependencies
5. No regressions in existing functionality
6. Error handling prevents crashes
7. Constitution Principle VI: Export/Reset/Import works

---

## Activity Log

- 2026-01-26T19:16:03Z – system – lane=planned – Prompt created.
