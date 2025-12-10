---
work_package_id: "WP08"
subtasks:
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
title: "Production Dashboard Tab"
phase: "Phase 4 - Dashboard"
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

# Work Package Prompt: WP08 - Production Dashboard Tab

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the new Production Dashboard tab that:
- Shows recent production runs (last 30 days)
- Shows recent assembly runs (last 30 days)
- Provides navigation to FinishedUnits and FinishedGoods tabs
- Replaces old production_tab.py

**Success Criteria**:
- Tab displays in main window
- Two sub-tabs: Production Runs and Assembly Runs
- Recent runs load with proper formatting
- Navigation links work
- Old production_tab.py deprecated

## Context & Constraints

**Dependencies**:
- WP01: History tables (for consistent formatting)
- WP04, WP07: Should be complete so full workflow is testable

**Services Used**:
- `batch_production_service.get_production_history()`
- `assembly_service.get_assembly_history()`

**Replaces**: `src/ui/production_tab.py`

## Subtasks & Detailed Guidance

### Subtask T042 - Create ProductionDashboardTab Class

**File**: `src/ui/production_dashboard_tab.py`

**Implementation**:
```python
import customtkinter as ctk
from datetime import datetime, timedelta
from src.ui.widgets.production_history_table import ProductionHistoryTable
from src.ui.widgets.assembly_history_table import AssemblyHistoryTable
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import batch_production_service, assembly_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE

class ProductionDashboardTab(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.service_integrator = get_ui_service_integrator()

        self._setup_ui()
        self.refresh()

        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
```

---

### Subtask T043 - Implement CTkTabview Layout

**Implementation**:
```python
def _setup_ui(self):
    self.grid_columnconfigure(0, weight=1)
    self.grid_rowconfigure(1, weight=1)

    # Header with title and nav links
    self._create_header()

    # Tabview for Production/Assembly sub-tabs
    self.tabview = ctk.CTkTabview(self)
    self.tabview.grid(row=1, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    # Add tabs
    self.production_tab = self.tabview.add("Production Runs")
    self.assembly_tab = self.tabview.add("Assembly Runs")

    # Configure tab grids
    self.production_tab.grid_columnconfigure(0, weight=1)
    self.production_tab.grid_rowconfigure(0, weight=1)
    self.assembly_tab.grid_columnconfigure(0, weight=1)
    self.assembly_tab.grid_rowconfigure(0, weight=1)

    # Create tables in each tab
    self._create_production_table()
    self._create_assembly_table()

def _create_header(self):
    header_frame = ctk.CTkFrame(self, fg_color="transparent")
    header_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

    title = ctk.CTkLabel(
        header_frame,
        text="Production Dashboard",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    title.pack(side="left")

    # Navigation links frame
    nav_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    nav_frame.pack(side="right")

    ctk.CTkButton(
        nav_frame,
        text="Go to Finished Units",
        command=self._navigate_to_finished_units,
        width=150
    ).pack(side="left", padx=PADDING_MEDIUM)

    ctk.CTkButton(
        nav_frame,
        text="Go to Finished Goods",
        command=self._navigate_to_finished_goods,
        width=150
    ).pack(side="left", padx=PADDING_MEDIUM)
```

---

### Subtask T044 - Implement Production Runs Table

**Implementation**:
```python
def _create_production_table(self):
    self.production_table = ProductionHistoryTable(
        self.production_tab,
        on_row_double_click=self._on_production_double_click,
        height=400
    )
    self.production_table.grid(row=0, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

def _load_production_runs(self):
    # Get runs from last 30 days
    start_date = datetime.utcnow() - timedelta(days=30)

    runs = self.service_integrator.execute_service_operation(
        operation_name="Load Recent Production",
        operation_type=OperationType.READ,
        service_function=lambda: batch_production_service.get_production_history(
            start_date=start_date,
            limit=100,
            include_consumptions=False
        ),
        parent_widget=self,
        error_context="Loading recent production runs"
    )

    if runs:
        self.production_table.set_data(runs)
    else:
        self.production_table.clear()

def _on_production_double_click(self, run):
    # Optional: Open detail view for this run
    # For now, just show the run info
    pass
```

**Parallel**: Can proceed alongside T045

---

### Subtask T045 - Implement Assembly Runs Table

**Implementation**:
```python
def _create_assembly_table(self):
    self.assembly_table = AssemblyHistoryTable(
        self.assembly_tab,
        on_row_double_click=self._on_assembly_double_click,
        height=400
    )
    self.assembly_table.grid(row=0, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

def _load_assembly_runs(self):
    start_date = datetime.utcnow() - timedelta(days=30)

    runs = self.service_integrator.execute_service_operation(
        operation_name="Load Recent Assembly",
        operation_type=OperationType.READ,
        service_function=lambda: assembly_service.get_assembly_history(
            start_date=start_date,
            limit=100,
            include_consumptions=False
        ),
        parent_widget=self,
        error_context="Loading recent assembly runs"
    )

    if runs:
        self.assembly_table.set_data(runs)
    else:
        self.assembly_table.clear()

def _on_assembly_double_click(self, run):
    pass
```

**Parallel**: Can proceed alongside T044

---

### Subtask T046 - Add Navigation Links

**Implementation**:
```python
def _navigate_to_finished_units(self):
    # Access parent tab control and switch to FinishedUnits tab
    # This depends on main_window structure
    main_window = self._get_main_window()
    if main_window and hasattr(main_window, 'tabview'):
        main_window.tabview.set("Finished Units")

def _navigate_to_finished_goods(self):
    main_window = self._get_main_window()
    if main_window and hasattr(main_window, 'tabview'):
        main_window.tabview.set("Finished Goods")

def _get_main_window(self):
    # Traverse up widget hierarchy to find main window
    parent = self.master
    while parent:
        if hasattr(parent, 'tabview'):
            return parent
        parent = getattr(parent, 'master', None)
    return None
```

**Note**: Navigation implementation depends on main_window structure. May need adjustment.

---

### Subtask T047 - Update main_window.py

**File**: `src/ui/main_window.py`

**Steps**:
1. Import new ProductionDashboardTab
2. Replace old production_tab import
3. Update tab creation code

**Changes**:
```python
# Old:
from src.ui.production_tab import ProductionTab

# New:
from src.ui.production_dashboard_tab import ProductionDashboardTab

# In tab creation:
# Old:
self.production_tab = ProductionTab(self.tabview.tab("Production"))

# New:
self.production_tab = ProductionDashboardTab(self.tabview.tab("Production"))
```

---

### Subtask T048 - Deprecate Old production_tab.py

**Steps**:
1. Search codebase for any remaining imports of production_tab
2. Update any references found
3. Add deprecation notice to old file header
4. Optionally rename to `production_tab_deprecated.py` or move to archive folder

**Deprecation Notice**:
```python
"""
DEPRECATED: This module has been replaced by production_dashboard_tab.py
as part of Feature 014 (Production & Assembly Recording UI).

This file is retained for reference only and will be removed in a future version.
"""
```

---

## Refresh Method

```python
def refresh(self):
    """Refresh both production and assembly tables."""
    self._load_production_runs()
    self._load_assembly_runs()
```

---

## Test Strategy

**Manual Testing**:
1. Verify Production tab appears in main window
2. Switch between Production Runs and Assembly Runs sub-tabs
3. Verify data loads for last 30 days
4. Click navigation links, verify correct tab activates
5. Record production/assembly elsewhere, verify dashboard updates on refresh

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Old tab has external references | Search codebase thoroughly |
| Navigation depends on main_window structure | Review main_window.py before implementing |
| Tab naming conflict | Use consistent naming with other tabs |

## Definition of Done Checklist

- [ ] T042: ProductionDashboardTab class created
- [ ] T043: CTkTabview layout with sub-tabs
- [ ] T044: Production runs table loads data
- [ ] T045: Assembly runs table loads data
- [ ] T046: Navigation links work
- [ ] T047: main_window.py updated
- [ ] T048: Old production_tab.py deprecated
- [ ] Full end-to-end workflow testable
- [ ] No references to old production_tab remain

## Review Guidance

- Verify both sub-tabs function correctly
- Test navigation to other tabs
- Verify data filtering (30 days)
- Check for any remaining old tab references
- Test full production workflow end-to-end

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-10T15:12:04Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-10T15:14:09Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-10T15:25:36Z – system – shell_pid= – lane=done – Code review approved - Production Dashboard with sub-tabs and navigation implemented
