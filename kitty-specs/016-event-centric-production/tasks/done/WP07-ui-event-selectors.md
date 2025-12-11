---
work_package_id: "WP07"
subtasks:
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
title: "UI - Event Selectors"
phase: "Phase 5 - UI Event Selectors"
lane: "done"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - UI - Event Selectors

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Add event selector dropdowns to Record Production and Record Assembly dialogs.

**Success Criteria**:
- Event selector appears in both dialogs
- Events listed in event_date ascending order (nearest upcoming first)
- "(None - standalone)" option available and is default
- Selected event_id passed to service on confirm
- Standalone production works (event_id=None)

## Context & Constraints

**Reference Documents**:
- `kitty-specs/016-event-centric-production/spec.md` - FR-023, FR-024, User Stories 1-2
- `kitty-specs/016-event-centric-production/quickstart.md` - Event selector pattern

**Existing Code**:
- `src/ui/forms/record_production_dialog.py`
- `src/ui/forms/record_assembly_dialog.py`

**UI Pattern**:
```
┌─────────────────────────────────────────────┐
│ Record Production: Sugar Cookies            │
├─────────────────────────────────────────────┤
│ Event (optional): [None - standalone    ▼]  │  ← NEW
│                                             │
│ Batches: [2    ]                            │
│ ...                                         │
└─────────────────────────────────────────────┘
```

**Dependencies**: WP02 (service methods accept event_id)

---

## Subtasks & Detailed Guidance

### Subtask T036 - Add event selector dropdown to RecordProductionDialog

**Purpose**: Allow user to optionally link production to an event.

**Steps**:
1. Open `src/ui/forms/record_production_dialog.py`
2. In `__init__` or setup method, load events:
   ```python
   from src.services import event_service
   from datetime import datetime

   # Load events sorted by date
   self.events = event_service.get_all_events()
   self.events.sort(key=lambda e: e.event_date or datetime.max)
   ```
3. Create dropdown widget after header, before batch input:
   ```python
   # Event selector
   event_label = ctk.CTkLabel(self, text="Event (optional):")
   event_label.pack(padx=10, pady=(10, 0), anchor="w")

   event_options = ["(None - standalone)"] + [e.name for e in self.events]
   self.event_var = ctk.StringVar(value=event_options[0])
   self.event_dropdown = ctk.CTkOptionMenu(
       self,
       variable=self.event_var,
       values=event_options,
       width=250
   )
   self.event_dropdown.pack(padx=10, pady=5)
   ```
4. Add helper method:
   ```python
   def _get_selected_event_id(self) -> Optional[int]:
       """Get the event_id for the selected event, or None for standalone."""
       selected = self.event_var.get()
       if selected == "(None - standalone)":
           return None
       for event in self.events:
           if event.name == selected:
               return event.id
       return None
   ```

**Files**: `src/ui/forms/record_production_dialog.py`
**Parallel?**: No (foundational UI change)
**Notes**: Position event selector prominently but make it clearly optional.

---

### Subtask T037 - Add event selector dropdown to RecordAssemblyDialog

**Purpose**: Allow user to optionally link assembly to an event.

**Steps**:
1. Open `src/ui/forms/record_assembly_dialog.py`
2. Apply same pattern as T036:
   - Load events sorted by date
   - Create event selector dropdown
   - Add `_get_selected_event_id()` helper

**Files**: `src/ui/forms/record_assembly_dialog.py`
**Parallel?**: Yes (can proceed with T036)
**Notes**: Same implementation pattern as production dialog.

---

### Subtask T038 - Implement event list loading sorted by event_date

**Purpose**: Ensure events are ordered nearest-first for user convenience.

**Steps**:
1. Verify EventService has `get_all_events()` method (or add if missing)
2. In both dialogs, sort events:
   ```python
   from datetime import datetime

   self.events = event_service.get_all_events()
   # Sort by event_date ascending; events without date go to end
   self.events.sort(key=lambda e: e.event_date or datetime.max)
   ```
3. Verify the sort works correctly with test data

**Files**: `src/ui/forms/record_production_dialog.py`, `src/ui/forms/record_assembly_dialog.py`
**Parallel?**: No
**Notes**: datetime.max ensures events without dates appear last.

---

### Subtask T039 - Pass selected event_id to service methods on confirm

**Purpose**: Connect UI selection to service layer.

**Steps**:
1. In RecordProductionDialog, find `_on_confirm()` method
2. Get selected event_id and pass to service:
   ```python
   def _on_confirm(self):
       # ... existing validation ...

       event_id = self._get_selected_event_id()

       result = batch_production_service.record_batch_production(
           recipe_id=self.recipe_id,
           num_batches=num_batches,
           actual_yield=actual_yield,
           notes=notes,
           event_id=event_id  # NEW parameter
       )
       # ... rest of method ...
   ```
3. Apply same pattern to RecordAssemblyDialog

**Files**: `src/ui/forms/record_production_dialog.py`, `src/ui/forms/record_assembly_dialog.py`
**Parallel?**: No
**Notes**: Ensure event_id is passed even when None.

---

### Subtask T040 - Manual UI testing checklist

**Purpose**: Verify UI works correctly across scenarios.

**Testing Checklist**:
1. [ ] Open Record Production dialog
2. [ ] Verify event dropdown appears
3. [ ] Verify "(None - standalone)" is default
4. [ ] Verify events are sorted by date (nearest first)
5. [ ] Select an event, confirm production
6. [ ] Verify ProductionRun has correct event_id in database
7. [ ] Record production with standalone selected
8. [ ] Verify ProductionRun has event_id = NULL
9. [ ] Repeat steps 1-8 for Record Assembly dialog
10. [ ] Test with no events in system
11. [ ] Test with events that have no date set

**Files**: N/A (manual testing)
**Parallel?**: No
**Notes**: Create test events with various dates before testing.

---

## Test Strategy

**Manual UI Testing** (no automated UI tests for this project):
- Follow checklist in T040
- Test edge cases: no events, events without dates

**Verify Database**:
```sql
SELECT id, recipe_id, event_id FROM production_run ORDER BY id DESC LIMIT 5;
SELECT id, finished_good_id, event_id FROM assembly_run ORDER BY id DESC LIMIT 5;
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Events not loading | Add error handling, show message if load fails |
| Layout issues | Test on different window sizes |
| Wrong event selected | Use event.id not name for matching |

---

## Definition of Done Checklist

- [ ] Event selector in Record Production dialog
- [ ] Event selector in Record Assembly dialog
- [ ] Events sorted by date (nearest first)
- [ ] "(None - standalone)" is default
- [ ] event_id passed to service on confirm
- [ ] Manual testing checklist complete
- [ ] Standalone production works
- [ ] Event-linked production works
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Reviewers should verify**:
1. Dropdown placement is logical
2. Events sorted correctly (check with multiple dates)
3. Default is standalone
4. Event_id correctly passed to service
5. UI handles empty event list gracefully

---

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-11T04:19:09Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-11T17:20:21Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-11T17:51:26Z – system – shell_pid= – lane=done – Code review approved - event selectors in both dialogs, syntax verified
