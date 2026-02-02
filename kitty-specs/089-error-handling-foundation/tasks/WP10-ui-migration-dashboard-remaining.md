---
work_package_id: "WP10"
subtasks:
  - "T047"
  - "T048"
  - "T049"
  - "T050"
  - "T051"
  - "T052"
  - "T053"
  - "T054"
  - "T055"
title: "UI Migration - Dashboard & Remaining Tabs"
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

# Work Package Prompt: WP10 – UI Migration - Dashboard & Remaining Tabs

## Implementation Command

```bash
spec-kitty implement WP10 --base WP03
```

**Depends on**: WP03

---

## Objectives & Success Criteria

**Objective**: Update exception handling in dashboards and remaining tabs.

**Success Criteria**:
- [ ] `dashboard_tab.py` updated (5 occurrences)
- [ ] `ingredients_tab.py` updated (10 occurrences)
- [ ] `packages_tab.py` updated (7 occurrences)
- [ ] All dashboard files updated
- [ ] Dashboards degrade gracefully (show partial data on component errors)

---

## Context & Constraints

**Import**:
```python
from src.ui.utils.error_handler import handle_error
from src.services.exceptions import ServiceError, IngredientInUse
```

**Dashboard Pattern**: Dashboards aggregate multiple data sources. Consider:
```python
# For dashboard components, errors in one section shouldn't crash others
try:
    data = load_section_data()
except Exception as e:
    handle_error(e, parent=self, operation="Load section", show_dialog=False)
    data = []  # Graceful degradation
```

---

## Subtasks & Detailed Guidance

### Subtask T047 – Update dashboard_tab.py

**Files**: `src/ui/dashboard_tab.py`
**Occurrences**: 5
**Operations**: "Load dashboard", "Load statistics", "Load recent activity"

### Subtask T048 – Update ingredients_tab.py

**Files**: `src/ui/ingredients_tab.py`
**Occurrences**: 10
**Operations**: "Load ingredients", "Create ingredient", "Delete ingredient", "Search ingredients"

**Note**: `IngredientInUse` shows dependency counts via error handler.

### Subtask T049 – Update packages_tab.py

**Files**: `src/ui/packages_tab.py`
**Occurrences**: 7
**Operations**: "Load packages", "Create package", "Delete package"

### Subtask T050 – Update dashboards/catalog_dashboard.py

**Files**: `src/ui/dashboards/catalog_dashboard.py`
**Occurrences**: 1

### Subtask T051 – Update dashboards/observe_dashboard.py

**Files**: `src/ui/dashboards/observe_dashboard.py`
**Occurrences**: 2

### Subtask T052 – Update dashboards/plan_dashboard.py

**Files**: `src/ui/dashboards/plan_dashboard.py`
**Occurrences**: 2

### Subtask T053 – Update dashboards/purchase_dashboard.py

**Files**: `src/ui/dashboards/purchase_dashboard.py`
**Occurrences**: 3

### Subtask T054 – Update dashboards/make_dashboard.py

**Files**: `src/ui/dashboards/make_dashboard.py`
**Occurrences**: 4

### Subtask T055 – Update dashboards/base_dashboard.py

**Files**: `src/ui/dashboards/base_dashboard.py`
**Occurrences**: 1

---

## Definition of Done Checklist

- [ ] All files updated with handle_error()
- [ ] Test: Delete ingredient in use → shows dependency list
- [ ] Test: Dashboard loads even if one component fails (graceful degradation)

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
