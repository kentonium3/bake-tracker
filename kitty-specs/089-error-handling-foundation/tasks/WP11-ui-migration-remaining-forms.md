---
work_package_id: WP11
title: UI Migration - Remaining Forms
lane: "for_review"
dependencies: [WP03]
base_branch: 089-error-handling-foundation-WP03
base_commit: 845ab60ddd7c9705f76124df0d925332fc6b41b8
created_at: '2026-02-03T00:56:17.990212+00:00'
subtasks:
- T056
- T057
- T058
- T059
- T060
- T061
- T062
phase: Phase 2 - UI Migration
assignee: ''
agent: ''
shell_pid: "75375"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-02T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP11 – UI Migration - Remaining Forms

## Implementation Command

```bash
spec-kitty implement WP11 --base WP03
```

**Depends on**: WP03

---

## Objectives & Success Criteria

**Objective**: Update exception handling in remaining UI forms.

**Success Criteria**:
- [ ] All listed form files updated
- [ ] Each file uses handle_error() for exception handling
- [ ] Low occurrence count - straightforward updates

---

## Context & Constraints

**Import**:
```python
from src.ui.utils.error_handler import handle_error
from src.services.exceptions import ServiceError
```

---

## Subtasks & Detailed Guidance

### Subtask T056 – Update forms/finished_unit_form.py

**Files**: `src/ui/forms/finished_unit_form.py`
**Occurrences**: 1
**Operations**: "Save finished unit"

### Subtask T057 – Update forms/finished_good_detail.py

**Files**: `src/ui/forms/finished_good_detail.py`
**Occurrences**: 1
**Operations**: "Load finished good details"

### Subtask T058 – Update forms/finished_unit_detail.py

**Files**: `src/ui/forms/finished_unit_detail.py`
**Occurrences**: 1
**Operations**: "Load finished unit details"

### Subtask T059 – Update forms/record_assembly_dialog.py

**Files**: `src/ui/forms/record_assembly_dialog.py`
**Occurrences**: 3
**Operations**: "Record assembly", "Check components", "Calculate requirements"

**Note**: May have `InsufficientFinishedUnitError` - error handler shows quantities.

### Subtask T060 – Update forms/assignment_form.py

**Files**: `src/ui/forms/assignment_form.py`
**Occurrences**: 2
**Operations**: "Save assignment", "Validate assignment"

### Subtask T061 – Update forms/ingredient_form.py

**Files**: `src/ui/forms/ingredient_form.py`
**Occurrences**: 1
**Operations**: "Save ingredient"

### Subtask T062 – Update forms/variant_creation_dialog.py

**Files**: `src/ui/forms/variant_creation_dialog.py`
**Occurrences**: 1
**Operations**: "Create variant"

---

## Definition of Done Checklist

- [ ] All 7 files updated with handle_error()
- [ ] Test: Assembly with insufficient units → shows quantity message
- [ ] Low risk - single occurrence files mostly

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
- 2026-02-03T00:59:17Z – unknown – shell_pid=75375 – lane=for_review – Ready for review: Updated 7 form files (10 handlers) with three-tier exception handling pattern. All UI tests pass (67 tests).
