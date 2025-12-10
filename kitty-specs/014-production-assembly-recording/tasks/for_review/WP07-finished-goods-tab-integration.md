---
work_package_id: "WP07"
subtasks:
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
title: "FinishedGoods Tab Integration"
phase: "Phase 3 - Assembly Recording"
lane: "for_review"
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

# Work Package Prompt: WP07 - FinishedGoods Tab Integration

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Wire the FinishedGoodsTab to open the detail dialog:
- Add "View Details" button
- Open dialog on button click or double-click
- Refresh list after inventory changes

**Success Criteria**:
- View Details button in action bar
- Double-click opens detail dialog
- List refreshes after assembly recorded

## Context & Constraints

**Dependencies**:
- WP06: FinishedGoodDetailDialog

**File to Modify**: `src/ui/finished_goods_tab.py`

**Note**: This file may need to be created or may exist. Check first.

## Subtasks & Detailed Guidance

### Subtask T037 - Add View Details Button

**File**: `src/ui/finished_goods_tab.py`

Same pattern as WP04:
```python
self.details_btn = ctk.CTkButton(
    self.button_frame,
    text="View Details",
    command=self._show_detail_dialog,
    width=150,
    state="disabled"
)
self.details_btn.pack(side="left", padx=PADDING_MEDIUM)
```

---

### Subtask T038 - Implement Show Detail Dialog

```python
def _show_detail_dialog(self):
    if not self.selected_finished_good:
        show_error("No Selection", "Please select a finished good first.", parent=self)
        return

    from src.ui.forms.finished_good_detail import FinishedGoodDetailDialog

    dialog = FinishedGoodDetailDialog(
        self,
        self.selected_finished_good,
        on_inventory_changed=self.refresh
    )
    self.wait_window(dialog)
```

---

### Subtask T039 - Wire Double-Click Handler

```python
def _on_row_double_click(self, finished_good):
    self.selected_finished_good = finished_good
    self._show_detail_dialog()
```

---

### Subtask T040 - Callback for Refresh

Pass `self.refresh` to dialog as `on_inventory_changed` callback.

---

### Subtask T041 - Update Form Exports

**File**: `src/ui/forms/__init__.py`

```python
from src.ui.forms.finished_good_detail import FinishedGoodDetailDialog
from src.ui.forms.record_assembly_dialog import RecordAssemblyDialog
```

---

## Handling Missing Tab

If `finished_goods_tab.py` doesn't exist or has minimal implementation:
1. Check existing structure
2. May need to create basic tab structure first
3. Follow pattern from `finished_units_tab.py`

**Minimum Implementation**:
```python
class FinishedGoodsTab(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.selected_finished_good = None
        self.service_integrator = get_ui_service_integrator()

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        # Search bar
        # Action buttons (Add, Edit, Delete, View Details)
        # Data table
        # Status bar
        pass

    def refresh(self):
        # Load finished goods from service
        pass
```

---

## Definition of Done Checklist

- [ ] T037: View Details button added
- [ ] T038: `_show_detail_dialog()` implemented
- [ ] T039: Double-click wired
- [ ] T040: Callback refreshes list
- [ ] T041: Form exports updated
- [ ] Tab exists and functions properly
- [ ] Button state managed correctly

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-10T07:17:40Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-10T15:11:36Z – system – shell_pid= – lane=for_review – Moved to for_review
