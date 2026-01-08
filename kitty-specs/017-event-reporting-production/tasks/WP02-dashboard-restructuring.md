---
work_package_id: WP02
title: Dashboard Restructuring
lane: done
history:
- timestamp: '2025-12-11T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 2 - Dashboard Restructuring
review_status: approved without changes
reviewed_by: claude-reviewer
shell_pid: '30686'
subtasks:
- T007
- T008
- T009
- T010
---

# Work Package Prompt: WP02 - Dashboard Restructuring

## Objectives & Success Criteria

**Objective**: Make Production Dashboard the default view and rename old Dashboard to "Summary".

**Success Criteria**:
- Application launches with Production tab selected by default (FR-001)
- "Summary" tab exists and shows ingredient count, recipe count, etc. (FR-002)
- Tab switching works correctly with refresh callbacks
- No regression in existing tab functionality

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md`
- Plan: `kitty-specs/017-event-reporting-production/plan.md`
- Spec: `kitty-specs/017-event-reporting-production/spec.md`
- Research: `kitty-specs/017-event-reporting-production/research.md` (Decision D1)

**Architectural Constraints**:
- Minimal code changes (tab reordering, not redesign)
- Preserve existing DashboardTab functionality (just rename)
- Update callbacks to use new tab name

**Current Tab Order** (from main_window.py):
1. Dashboard (DashboardTab) - to become "Summary"
2. My Ingredients
3. My Pantry
4. Recipes
5. Finished Units
6. Packages
7. Recipients
8. Events
9. Production (ProductionDashboardTab) - to become first
10. Reports (placeholder)

## Subtasks & Detailed Guidance

### Subtask T007 - Reorder tabs in main_window.py

**Purpose**: Make Production tab appear first in the tab bar.

**Steps**:
1. Open `src/ui/main_window.py`
2. Find the `_create_tabs()` method (~line 85)
3. Move the Production tab creation to be first:

**Before** (current order):
```python
def _create_tabs(self):
    """Create the tabbed interface."""
    self.tabview = ctk.CTkTabview(self, corner_radius=10)
    self.tabview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    # Add tabs (v0.4.0 architecture)
    self.tabview.add("Dashboard")
    self.tabview.add("My Ingredients")
    # ... other tabs ...
    self.tabview.add("Production")
    self.tabview.add("Reports")
```

**After** (new order):
```python
def _create_tabs(self):
    """Create the tabbed interface."""
    self.tabview = ctk.CTkTabview(self, corner_radius=10)
    self.tabview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    # Add tabs - Production first for immediate visibility (Feature 017)
    self.tabview.add("Production")
    self.tabview.add("Summary")  # Renamed from "Dashboard"
    self.tabview.add("My Ingredients")
    # ... rest of tabs unchanged ...
    self.tabview.add("Reports")
```

**Files**: `src/ui/main_window.py`
**Parallel?**: No (must complete before T008)

---

### Subtask T008 - Rename "Dashboard" tab to "Summary"

**Purpose**: Rename the tab to reflect its summary-focused content.

**Steps**:
1. In `_create_tabs()`, change:
   ```python
   # Old
   self.tabview.add("Dashboard")

   # New
   self.tabview.add("Summary")
   ```

2. Update the frame initialization:
   ```python
   # Old
   dashboard_frame = self.tabview.tab("Dashboard")

   # New
   summary_frame = self.tabview.tab("Summary")
   self.dashboard_tab = DashboardTab(summary_frame)  # Keep variable name for compatibility
   ```

3. Optionally update the variable name for clarity:
   ```python
   summary_frame = self.tabview.tab("Summary")
   self.summary_tab = DashboardTab(summary_frame)  # Renamed variable
   ```

4. If renaming variable, update `refresh_dashboard()` method:
   ```python
   def refresh_dashboard(self):
       """Refresh the summary tab with current data."""
       self.summary_tab.refresh()  # or keep self.dashboard_tab.refresh()
   ```

**Files**: `src/ui/main_window.py`
**Parallel?**: No (builds on T007)
**Notes**: The DashboardTab class itself doesn't need renaming - just the tab label.

---

### Subtask T009 - Update default tab selection

**Purpose**: Make Production the default selected tab on launch.

**Steps**:
1. Find the default tab selection (~line 147):
   ```python
   # Old
   self.tabview.set("Dashboard")

   # New
   self.tabview.set("Production")
   ```

**Files**: `src/ui/main_window.py`
**Parallel?**: No (builds on T007, T008)

---

### Subtask T010 - Update _on_tab_change callback

**Purpose**: Ensure Summary tab refresh still works after rename.

**Steps**:
1. Find `_on_tab_change()` method (~line 275):
   ```python
   def _on_tab_change(self):
       """Handle tab change event - refresh certain tabs when selected."""
       current_tab = self.tabview.get()
       if current_tab == "Dashboard":  # OLD
           self.dashboard_tab.refresh()
       elif current_tab == "Production":
           self.production_tab.refresh()
   ```

2. Update to use new tab name:
   ```python
   def _on_tab_change(self):
       """Handle tab change event - refresh certain tabs when selected."""
       current_tab = self.tabview.get()
       if current_tab == "Summary":  # RENAMED
           self.dashboard_tab.refresh()  # or self.summary_tab if renamed
       elif current_tab == "Production":
           self.production_tab.refresh()
   ```

**Files**: `src/ui/main_window.py`
**Parallel?**: No (builds on T008)

---

## Test Strategy

**Manual Testing** (UI changes - no automated tests):
1. Launch application: `python src/main.py`
2. Verify Production tab is selected by default
3. Click on Summary tab - verify content displays correctly
4. Click back to Production tab - verify content displays correctly
5. Navigate through all tabs to ensure nothing is broken
6. Verify refresh callbacks work (make changes elsewhere, switch tabs)

**Verification Checklist**:
- [ ] App launches with Production tab selected
- [ ] Summary tab shows ingredient count, recipe count, inventory value
- [ ] Tab switching works for all tabs
- [ ] Refresh callbacks trigger correctly
- [ ] No console errors during navigation

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Tab refresh breaks | Test _on_tab_change() with new tab name |
| Variable name confusion | Use clear comments explaining rename |
| Other code references "Dashboard" | Search codebase for string "Dashboard" |

## Definition of Done Checklist

- [ ] T007: Tabs reordered (Production first)
- [ ] T008: "Dashboard" renamed to "Summary"
- [ ] T009: Default tab is "Production"
- [ ] T010: Tab change callback works for "Summary"
- [ ] Manual testing confirms all tabs work
- [ ] No console errors during tab navigation
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Checkpoints**:
1. Launch app - Production tab should be visible first
2. Click Summary tab - should show original Dashboard content
3. Tab switching should be smooth with no errors
4. Check console for any "Dashboard" string errors

**Search for potential issues**:
```bash
grep -r "Dashboard" src/ui/ --include="*.py"
```

## Activity Log

- 2025-12-11T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-12T03:04:33Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-12T03:08:14Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-12T04:10:59Z – system – shell_pid= – lane=done – Code review approved: Tab restructuring correct, Production first, Summary renamed
