---
work_package_id: "WP05"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
title: "UI Migration - Recipes & Production"
phase: "Phase 2 - UI Migration"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP03"]
history:
  - timestamp: "2026-02-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – UI Migration - Recipes & Production

## Implementation Command

```bash
spec-kitty implement WP05 --base WP03
```

**Depends on**: WP03

---

## Objectives & Success Criteria

**Objective**: Update exception handling in recipe and production UI files.

**Success Criteria**:
- [ ] `recipes_tab.py` updated (11 occurrences)
- [ ] `forms/recipe_form.py` updated (10 occurrences)
- [ ] `production_dashboard_tab.py` updated (1 occurrence)
- [ ] `forms/record_production_dialog.py` updated (3 occurrences)
- [ ] Validation errors show field-level feedback
- [ ] Insufficient inventory errors show quantities

---

## Context & Constraints

**Import**:
```python
from src.ui.utils.error_handler import handle_error
from src.services.exceptions import ServiceError, ValidationError
```

**Special Handling**: Recipe forms may have ValidationError catches with field highlighting - preserve that behavior.

---

## Subtasks & Detailed Guidance

### Subtask T022 – Update recipes_tab.py

**Files**: `src/ui/recipes_tab.py`
**Occurrences**: 11
**Operations**: "Load recipes", "Search recipes", "Delete recipe", "Copy recipe"

### Subtask T023 – Update forms/recipe_form.py

**Files**: `src/ui/forms/recipe_form.py`
**Occurrences**: 10
**Operations**: "Save recipe", "Add ingredient", "Update quantity", "Load recipe details"

**Note**: Preserve any field validation highlighting. Pattern:
```python
except ValidationError as e:
    handle_error(e, parent=self, operation="Save recipe")
    self._highlight_invalid_fields(e.errors)  # Preserve if exists
```

### Subtask T024 – Update production_dashboard_tab.py

**Files**: `src/ui/production_dashboard_tab.py`
**Occurrences**: 1
**Operations**: "Load production dashboard"

### Subtask T025 – Update forms/record_production_dialog.py

**Files**: `src/ui/forms/record_production_dialog.py`
**Occurrences**: 3
**Operations**: "Record production", "Check inventory", "Calculate yield"

**Note**: Watch for `InsufficientInventoryError` - error handler will show quantities.

---

## Definition of Done Checklist

- [ ] All files updated with handle_error()
- [ ] ValidationError field highlighting preserved
- [ ] Manual test: Create recipe with missing fields → validation message
- [ ] Manual test: Record production with low inventory → inventory message

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
