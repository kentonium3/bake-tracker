---
work_package_id: "WP08"
subtasks:
  - "T054"
  - "T055"
  - "T056"
  - "T057"
  - "T058"
  - "T059"
title: "UI - Events Tab"
phase: "Phase 3 - UI Layer"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "9077"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2025-12-03"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - UI - Events Tab

## Objectives & Success Criteria

- Restore/update Events tab with year filtering
- Enable opening EventDetailWindow on event selection

**Success Criteria**:
- User can create, edit, delete events
- Year filter shows only events from selected year (FR-020)
- Delete with assignments shows cascade confirmation (FR-022)
- Double-click opens EventDetailWindow

## Context & Constraints

**Key Documents**:
- `kitty-specs/006-event-planning-restoration/spec.md` - User Story 4 acceptance scenarios
- `kitty-specs/006-event-planning-restoration/contracts/event_service.md` - Service interface

**Dependencies**: Requires WP04 complete (EventService).

## Subtasks & Detailed Guidance

### Subtask T054 - Review existing `src/ui/events_tab.py` for reusable patterns

**Purpose**: Determine what can be reused.

**Steps**:
1. Check if `src/ui/events_tab.py` exists
2. If exists, identify:
   - UI patterns
   - Any Bundle references
   - Reusable layout code
3. Plan updates needed

**Files**: `src/ui/events_tab.py`

### Subtask T055 - Create/update EventsTab frame with event list view

**Purpose**: Main tab showing events.

**Steps**:
1. Create EventsTab class extending CTkFrame
2. Create event list showing: name, event_date, year, assignment count
3. Add "Add Event" button
4. Load events via EventService.get_all_events()

**Files**: `src/ui/events_tab.py`

### Subtask T056 - Implement Add Event dialog with name, event_date, year, notes

**Purpose**: Dialog for creating events.

**Steps**:
1. Create AddEventDialog class (CTkToplevel)
2. Fields:
   - Name (required)
   - Event Date (date picker or formatted entry)
   - Year (auto-populate from date, but editable)
   - Notes (optional)
3. Save calls EventService.create_event()

**Files**: `src/ui/events_tab.py` or `src/ui/dialogs/event_dialog.py`

### Subtask T057 - Implement year filter dropdown (FR-020)

**Purpose**: Filter events by year.

**Steps**:
1. Add year filter dropdown above event list
2. Populate with EventService.get_available_years()
3. Add "All Years" option
4. On change, filter list:
   ```python
   def on_year_filter_change(self, year):
       if year == "All Years":
           events = EventService.get_all_events()
       else:
           events = EventService.get_events_by_year(int(year))
       self.update_event_list(events)
   ```

**Files**: `src/ui/events_tab.py`

### Subtask T058 - Implement Edit/Delete event functionality with cascade confirmation

**Purpose**: CRUD with cascade delete confirmation (FR-022).

**Steps**:
1. Edit: Populate dialog with existing values
2. Delete:
   ```python
   def on_delete_click(self, event_id):
       event = EventService.get_event_by_id(event_id)
       if event.event_recipient_packages:
           if not show_confirmation(
               f"Event has {len(event.event_recipient_packages)} assignments. "
               "Delete event and all assignments?"
           ):
               return
           EventService.delete_event(event_id, cascade_assignments=True)
       else:
           EventService.delete_event(event_id)
       self.load_events()
   ```

**Files**: `src/ui/events_tab.py`

### Subtask T059 - Implement double-click to open EventDetailWindow

**Purpose**: Navigate to event details.

**Steps**:
1. Bind double-click event on list items:
   ```python
   def on_event_double_click(self, event_id):
       EventDetailWindow(self, event_id)
   ```
2. Ensure EventDetailWindow is imported
3. Handle window closing/refresh

**Files**: `src/ui/events_tab.py`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| EventDetailWindow not yet implemented | Depends on WP09, can stub for testing |

## Definition of Done Checklist

- [ ] Event list displays correctly
- [ ] Add/Edit/Delete operations work
- [ ] Year filter works (FR-020)
- [ ] Cascade delete with confirmation (FR-022)
- [ ] Double-click opens EventDetailWindow
- [ ] User Story 4 acceptance scenarios pass
- [ ] `tasks.md` updated with status change

## Review Guidance

- Test year filter with multiple years
- Verify cascade delete removes all assignments
- Check EventDetailWindow opens correctly

## Activity Log

- 2025-12-03 - system - lane=planned - Prompt created.
- 2025-12-04T02:52:23Z – claude – shell_pid=9077 – lane=for_review – Completed: EventsTab imports fixed (EventNotFoundError)
- 2025-12-04T03:01:38Z – claude – shell_pid=9077 – lane=done – Approved: EventsTab implemented (351 lines)
