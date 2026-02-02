---
work_package_id: "WP06"
subtasks:
  - "T026"
  - "T027"
  - "T028"
  - "T029"
title: "UI Migration - Products & Finished Goods"
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

# Work Package Prompt: WP06 – UI Migration - Products & Finished Goods

## Implementation Command

```bash
spec-kitty implement WP06 --base WP03
```

**Depends on**: WP03

---

## Objectives & Success Criteria

**Objective**: Update exception handling in product and finished goods UI files.

**Success Criteria**:
- [ ] `products_tab.py` updated (12 occurrences)
- [ ] `finished_goods_tab.py` updated (7 occurrences)
- [ ] `finished_units_tab.py` updated (6 occurrences)
- [ ] `bundles_tab.py` updated (7 occurrences)
- [ ] "In use" errors show dependency counts
- [ ] Circular reference errors show clear message

---

## Context & Constraints

**Import**:
```python
from src.ui.utils.error_handler import handle_error
from src.services.exceptions import ServiceError, ProductInUse
```

**Special Cases**:
- `ProductInUse` should show dependency counts (error handler does this)
- `CircularReferenceError` for finished goods composition

---

## Subtasks & Detailed Guidance

### Subtask T026 – Update products_tab.py

**Files**: `src/ui/products_tab.py`
**Occurrences**: 12
**Operations**: "Load products", "Create product", "Delete product", "Search products"

### Subtask T027 – Update finished_goods_tab.py

**Files**: `src/ui/finished_goods_tab.py`
**Occurrences**: 7
**Operations**: "Load finished goods", "Create finished good", "Add component", "Delete finished good"

### Subtask T028 – Update finished_units_tab.py

**Files**: `src/ui/finished_units_tab.py`
**Occurrences**: 6
**Operations**: "Load finished units", "Create finished unit", "Link recipe"

### Subtask T029 – Update bundles_tab.py

**Files**: `src/ui/bundles_tab.py`
**Occurrences**: 7
**Operations**: "Load bundles", "Create bundle", "Add items to bundle"

---

## Definition of Done Checklist

- [ ] All files updated with handle_error()
- [ ] Test: Delete product in use → shows "Cannot Delete" with dependency list
- [ ] Test: Create circular finished good → shows "Invalid Operation"

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
