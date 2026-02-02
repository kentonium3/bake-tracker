---
work_package_id: "WP08"
subtasks:
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
title: "UI Migration - Forms Part 1"
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

# Work Package Prompt: WP08 – UI Migration - Forms Part 1

## Implementation Command

```bash
spec-kitty implement WP08 --base WP03
```

**Depends on**: WP03

---

## Objectives & Success Criteria

**Objective**: Update exception handling in product/supplier forms.

**Success Criteria**:
- [ ] `forms/add_product_dialog.py` updated (9 occurrences)
- [ ] `forms/product_detail_dialog.py` updated (6 occurrences)
- [ ] `forms/package_form.py` updated (6 occurrences)
- [ ] `forms/manage_suppliers_dialog.py` updated (6 occurrences)
- [ ] `forms/bundle_form.py` updated (1 occurrence)
- [ ] Form validation errors show field feedback

---

## Context & Constraints

**Import**:
```python
from src.ui.utils.error_handler import handle_error
from src.services.exceptions import ServiceError, ValidationError, SlugAlreadyExists
```

---

## Subtasks & Detailed Guidance

### Subtask T035 – Update forms/add_product_dialog.py

**Files**: `src/ui/forms/add_product_dialog.py`
**Occurrences**: 9
**Operations**: "Add product", "Validate barcode", "Check duplicate"

### Subtask T036 – Update forms/product_detail_dialog.py

**Files**: `src/ui/forms/product_detail_dialog.py`
**Occurrences**: 6
**Operations**: "Load product details", "Update product", "Delete product"

### Subtask T037 – Update forms/package_form.py

**Files**: `src/ui/forms/package_form.py`
**Occurrences**: 6
**Operations**: "Save package", "Add finished good", "Remove item"

### Subtask T038 – Update forms/manage_suppliers_dialog.py

**Files**: `src/ui/forms/manage_suppliers_dialog.py`
**Occurrences**: 6
**Operations**: "Load suppliers", "Add supplier", "Edit supplier", "Delete supplier"

### Subtask T039 – Update forms/bundle_form.py

**Files**: `src/ui/forms/bundle_form.py`
**Occurrences**: 1
**Operations**: "Save bundle"

---

## Definition of Done Checklist

- [ ] All files updated with handle_error()
- [ ] Test: Add product with duplicate name → shows "Duplicate" message
- [ ] Test: Save form with invalid data → shows validation errors

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
