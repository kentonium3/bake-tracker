---
work_package_id: WP09
title: UI Migration - Dialogs
lane: "doing"
dependencies: [WP03]
base_branch: 089-error-handling-foundation-WP03
base_commit: 845ab60ddd7c9705f76124df0d925332fc6b41b8
created_at: '2026-02-03T00:35:54.142499+00:00'
subtasks:
- T040
- T041
- T042
- T043
- T044
- T045
- T046
phase: Phase 2 - UI Migration
assignee: ''
agent: ''
shell_pid: "70349"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-02T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 – UI Migration - Dialogs

## Implementation Command

```bash
spec-kitty implement WP09 --base WP03
```

**Depends on**: WP03

---

## Objectives & Success Criteria

**Objective**: Update exception handling in purchase and material dialogs.

**Success Criteria**:
- [ ] `dialogs/add_purchase_dialog.py` updated (7 occurrences)
- [ ] `dialogs/edit_purchase_dialog.py` updated (5 occurrences)
- [ ] `dialogs/purchase_details_dialog.py` updated (1 occurrence)
- [ ] `dialogs/upc_resolution_dialog.py` updated (4 occurrences)
- [ ] `dialogs/material_product_popup.py` updated (3 occurrences)
- [ ] `dialogs/material_unit_dialog.py` updated (2 occurrences)
- [ ] `dialogs/material_adjustment_dialog.py` updated (1 occurrence)

---

## Context & Constraints

**Import**:
```python
from src.ui.utils.error_handler import handle_error
from src.services.exceptions import ServiceError
```

**Special Cases**:
- UPC resolution dialog may have barcode-specific errors - preserve any custom messages
- Material dialogs deal with inventory adjustments

---

## Subtasks & Detailed Guidance

### Subtask T040 – Update dialogs/add_purchase_dialog.py

**Files**: `src/ui/dialogs/add_purchase_dialog.py`
**Occurrences**: 7
**Operations**: "Add purchase", "Validate product", "Save purchase"

### Subtask T041 – Update dialogs/edit_purchase_dialog.py

**Files**: `src/ui/dialogs/edit_purchase_dialog.py`
**Occurrences**: 5
**Operations**: "Load purchase", "Update purchase", "Delete purchase"

### Subtask T042 – Update dialogs/purchase_details_dialog.py

**Files**: `src/ui/dialogs/purchase_details_dialog.py`
**Occurrences**: 1
**Operations**: "Load purchase details"

### Subtask T043 – Update dialogs/upc_resolution_dialog.py

**Files**: `src/ui/dialogs/upc_resolution_dialog.py`
**Occurrences**: 4
**Operations**: "Resolve UPC", "Lookup product", "Create product from UPC"

### Subtask T044 – Update dialogs/material_product_popup.py

**Files**: `src/ui/dialogs/material_product_popup.py`
**Occurrences**: 3
**Operations**: "Load material product", "Select product"

### Subtask T045 – Update dialogs/material_unit_dialog.py

**Files**: `src/ui/dialogs/material_unit_dialog.py`
**Occurrences**: 2
**Operations**: "Load material unit", "Update unit"

### Subtask T046 – Update dialogs/material_adjustment_dialog.py

**Files**: `src/ui/dialogs/material_adjustment_dialog.py`
**Occurrences**: 1
**Operations**: "Adjust material quantity"

---

## Definition of Done Checklist

- [ ] All files updated with handle_error()
- [ ] Test: Add purchase with invalid supplier → shows "Not Found"
- [ ] Test: UPC not found → shows appropriate message (not barcode exception)

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
