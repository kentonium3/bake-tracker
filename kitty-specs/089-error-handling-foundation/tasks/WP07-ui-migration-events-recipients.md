---
work_package_id: WP07
title: UI Migration - Events & Recipients
lane: "doing"
dependencies: [WP03]
base_branch: 089-error-handling-foundation-WP03
base_commit: 845ab60ddd7c9705f76124df0d925332fc6b41b8
created_at: '2026-02-03T00:28:01.136691+00:00'
subtasks:
- T030
- T031
- T032
- T033
- T034
phase: Phase 2 - UI Migration
assignee: ''
agent: ''
shell_pid: "67118"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-02T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – UI Migration - Events & Recipients

## Implementation Command

```bash
spec-kitty implement WP07 --base WP03
```

**Depends on**: WP03

---

## Objectives & Success Criteria

**Objective**: Update exception handling in event and recipient management UI.

**Success Criteria**:
- [ ] `events_tab.py` updated (5 occurrences)
- [ ] `event_detail_window.py` updated (19 occurrences)
- [ ] `recipients_tab.py` updated (6 occurrences)
- [ ] `forms/event_planning_form.py` updated (2 occurrences)
- [ ] `tabs/event_status_tab.py` updated (2 occurrences)
- [ ] Plan state errors show "plan is locked" messages

---

## Context & Constraints

**Import**:
```python
from src.ui.utils.error_handler import handle_error
from src.services.exceptions import ServiceError, PlanStateError
```

**Special Cases**:
- `PlanStateError` shows plan state (e.g., "Cannot modify: plan is locked")
- `event_detail_window.py` has 19 occurrences - highest in this batch

---

## Subtasks & Detailed Guidance

### Subtask T030 – Update events_tab.py

**Files**: `src/ui/events_tab.py`
**Occurrences**: 5
**Operations**: "Load events", "Create event", "Delete event"

### Subtask T031 – Update event_detail_window.py

**Files**: `src/ui/event_detail_window.py`
**Occurrences**: 19 (highest - review carefully)
**Operations**: "Load event details", "Update event", "Add assignment", "Set targets"

**Note**: This file has many operations - ensure each `operation=` parameter is descriptive.

### Subtask T032 – Update recipients_tab.py

**Files**: `src/ui/recipients_tab.py`
**Occurrences**: 6
**Operations**: "Load recipients", "Create recipient", "Delete recipient"

### Subtask T033 – Update forms/event_planning_form.py

**Files**: `src/ui/forms/event_planning_form.py`
**Occurrences**: 2
**Operations**: "Save event plan", "Load plan data"

### Subtask T034 – Update tabs/event_status_tab.py

**Files**: `src/ui/tabs/event_status_tab.py`
**Occurrences**: 2
**Operations**: "Load event status", "Update status"

---

## Definition of Done Checklist

- [ ] All files updated with handle_error()
- [ ] Test: Modify locked plan → shows "Cannot [action]: plan is locked"
- [ ] Test: Delete recipient with assignments → shows conflict message

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
