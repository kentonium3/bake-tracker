# Cursor Code Review Prompt - Feature 038: UI Mode Restructure

## Role

You are a senior software engineer performing an independent code review of Feature 038 (ui-mode-restructure). This feature transforms the application's flat 11-tab navigation into a 5-mode workflow-oriented architecture (CATALOG, PLAN, SHOP, PRODUCE, OBSERVE).

## Feature Summary

**Core Changes:**
1. Base Classes (WP01): BaseMode, BaseDashboard, StandardTabLayout in `src/ui/base/`
2. Main Window Navigation (WP02): ModeManager, mode bar, keyboard shortcuts Ctrl+1-5
3. CATALOG Mode (WP03): 6 tabs - Ingredients, Products, Recipes, Finished Units, Finished Goods, Packages
4. OBSERVE Mode (WP04): Dashboard with event progress, Event Status tab, Reports placeholder
5. PLAN Mode (WP05): Events tab, Planning Workspace placeholder
6. SHOP Mode (WP06): Shopping Lists, Purchases, Inventory tabs
7. PRODUCE Mode (WP07): Production Runs, Assembly, Packaging, Recipients tabs
8. Integration & Polish (WP08): Old navigation removed, cleanup, unsaved changes infrastructure

**Problem Being Solved:**
- Current flat navigation has no workflow guidance (11 tabs at same level)
- Inconsistent tab layouts force users to relearn each screen
- No visibility into system state without clicking through multiple tabs
- Unclear entry points for common tasks like planning events

**Solution:**
- 5-mode workflow architecture (CATALOG, PLAN, SHOP, PRODUCE, OBSERVE)
- Mode-specific dashboards with at-a-glance stats
- Consistent tab layout patterns within each mode
- Keyboard shortcuts Ctrl+1-5 for mode switching
- Tab state preservation across mode switches
- OBSERVE as default mode on launch

## Files to Review

### Base Classes (WP01)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/base/__init__.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/base/base_mode.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/base/standard_tab_layout.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/dashboards/base_dashboard.py`

### Mode Manager & Main Window (WP02)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/mode_manager.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/main_window.py`

### Mode Implementations (WP03-WP07)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/modes/__init__.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/modes/catalog_mode.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/modes/observe_mode.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/modes/plan_mode.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/modes/shop_mode.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/modes/produce_mode.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/modes/placeholder_mode.py`

### Dashboard Implementations

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/dashboards/__init__.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/dashboards/catalog_dashboard.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/dashboards/observe_dashboard.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/dashboards/plan_dashboard.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/dashboards/shop_dashboard.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/dashboards/produce_dashboard.py`

### New Tab Implementations

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/tabs/__init__.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/tabs/event_status_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/tabs/reports_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/tabs/planning_workspace_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/tabs/shopping_lists_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/tabs/purchases_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/tabs/assembly_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/src/ui/tabs/packaging_tab.py`

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/kitty-specs/038-ui-mode-restructure/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/kitty-specs/038-ui-mode-restructure/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/kitty-specs/038-ui-mode-restructure/tasks.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure/kitty-specs/038-ui-mode-restructure/data-model.md`

## Review Checklist

### 1. Base Classes (WP01)

- [ ] `BaseMode` class exists with activate/deactivate methods
- [ ] `BaseMode` provides tab state management (get_current_tab_index, set_current_tab_index)
- [ ] `BaseDashboard` provides add_stat, update_stat, refresh methods
- [ ] `BaseDashboard` supports collapse/expand functionality
- [ ] `StandardTabLayout` provides consistent layout regions (if implemented)
- [ ] All base classes have proper type hints and docstrings

### 2. Mode Manager & Navigation (WP02)

- [ ] `ModeManager` tracks current mode and mode widgets
- [ ] Mode switching hides current mode and shows target mode
- [ ] Tab state preserved across mode switches (FR-004)
- [ ] Keyboard shortcuts Ctrl+1-5 switch modes (FR-003)
- [ ] Active mode button highlighted (FR-002)
- [ ] OBSERVE is default mode on launch (FR-005)
- [ ] Mode bar displays 5 mode buttons

### 3. CATALOG Mode (WP03)

- [ ] `CatalogMode` extends `BaseMode`
- [ ] `CatalogDashboard` shows entity counts (ingredients, products, recipes, etc.)
- [ ] All 6 tabs accessible: Ingredients, Products, Recipes, Finished Units, Finished Goods, Packages
- [ ] Existing tab functionality preserved

### 4. OBSERVE Mode (WP04)

- [ ] `ObserveMode` extends `BaseMode`
- [ ] `ObserveDashboard` shows event progress percentages (shopping, production, assembly, packaging)
- [ ] Dashboard tab accessible
- [ ] Event Status tab shows per-event breakdown
- [ ] Reports tab exists (placeholder acceptable)

### 5. PLAN Mode (WP05)

- [ ] `PlanMode` extends `BaseMode`
- [ ] `PlanDashboard` shows upcoming events and attention indicators
- [ ] Events tab accessible and functional
- [ ] Planning Workspace tab exists (placeholder acceptable)

### 6. SHOP Mode (WP06)

- [ ] `ShopMode` extends `BaseMode`
- [ ] `ShopDashboard` shows shopping summary and inventory alerts
- [ ] Shopping Lists tab exists
- [ ] Purchases tab exists
- [ ] Inventory tab accessible and functional

### 7. PRODUCE Mode (WP07)

- [ ] `ProduceMode` extends `BaseMode`
- [ ] `ProduceDashboard` shows production stats
- [ ] Production Runs tab accessible
- [ ] Assembly tab exists
- [ ] Packaging tab exists
- [ ] Recipients tab accessible and functional

### 8. Integration & Polish (WP08)

- [ ] Old flat navigation removed from main_window.py
- [ ] No unused imports in main_window.py
- [ ] Unsaved changes check infrastructure added to ModeManager
- [ ] All modes accessible via buttons and keyboard shortcuts
- [ ] No linting errors (run flake8)

### 9. Code Quality

- [ ] Feature comments reference "F038" or "Feature 038"
- [ ] Docstrings present for new classes and public methods
- [ ] No unused imports in modified files
- [ ] No debug print statements left in code
- [ ] Layered architecture preserved (UI -> Services -> Models)
- [ ] No business logic in UI layer

## Verification Commands

**IMPORTANT**: Run these commands outside the sandbox so venv activation will work. If any command fails, STOP and report the blocker before fixing anything.

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/038-ui-mode-restructure

# Activate virtual environment
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify all mode modules import correctly
PYTHONPATH=. python3 -c "
from src.ui.mode_manager import ModeManager
from src.ui.modes import CatalogMode, ObserveMode, PlanMode, ShopMode, ProduceMode
from src.ui.dashboards import BaseDashboard, CatalogDashboard, ObserveDashboard, PlanDashboard, ShopDashboard, ProduceDashboard
from src.ui.tabs import AssemblyTab, PackagingTab, PlanningWorkspaceTab, PurchasesTab, ShoppingListsTab
from src.ui.main_window import MainWindow
print('All imports successful')
"

# Verify BaseMode class structure
grep -n "class BaseMode" src/ui/base/base_mode.py
grep -n "def activate\|def deactivate\|def get_current_tab_index\|def set_current_tab_index" src/ui/base/base_mode.py

# Verify BaseDashboard class structure
grep -n "class BaseDashboard" src/ui/dashboards/base_dashboard.py
grep -n "def add_stat\|def update_stat\|def refresh" src/ui/dashboards/base_dashboard.py

# Verify ModeManager class structure
grep -n "class ModeManager" src/ui/mode_manager.py
grep -n "def switch_mode\|def register_mode\|current_mode" src/ui/mode_manager.py

# Verify all 5 mode classes exist
grep -n "class CatalogMode" src/ui/modes/catalog_mode.py
grep -n "class ObserveMode" src/ui/modes/observe_mode.py
grep -n "class PlanMode" src/ui/modes/plan_mode.py
grep -n "class ShopMode" src/ui/modes/shop_mode.py
grep -n "class ProduceMode" src/ui/modes/produce_mode.py

# Verify keyboard shortcuts in main_window
grep -n "Control-Key-1\|Control-Key-2\|Control-Key-3\|Control-Key-4\|Control-Key-5" src/ui/main_window.py

# Verify default OBSERVE mode
grep -n "OBSERVE" src/ui/mode_manager.py | head -5

# Verify mode bar creation
grep -n "CATALOG.*PLAN.*SHOP\|mode_bar\|mode_configs" src/ui/main_window.py | head -10

# Verify no old PlaceholderMode usage in main_window
grep -n "PlaceholderMode" src/ui/main_window.py

# Run flake8 on key files
flake8 src/ui/main_window.py src/ui/mode_manager.py --max-line-length=100 2>&1 | head -20

# Run full test suite (IMPORTANT: If this fails, STOP and report)
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -40

# Check git log for F038 commits
git log --oneline -20
```

## Key Implementation Patterns

### Mode Switching Pattern (ModeManager)
```python
def switch_mode(self, target_mode: str) -> bool:
    if target_mode not in self.modes:
        return False
    if target_mode == self.current_mode:
        return False

    # Check for unsaved changes (edge case handling)
    if self._unsaved_changes_check and self._confirm_discard_callback:
        if self._unsaved_changes_check():
            if not self._confirm_discard_callback():
                return False

    # Save current mode's tab state
    current = self.modes.get(self.current_mode)
    if current:
        current.deactivate()
        self.mode_tab_state[self.current_mode] = current.get_current_tab_index()
        current.pack_forget()

    # Activate target mode
    target = self.modes[target_mode]
    target.pack(fill="both", expand=True)
    saved_index = self.mode_tab_state.get(target_mode, 0)
    target.set_current_tab_index(saved_index)
    target.activate()

    self.current_mode = target_mode
    self._update_mode_bar_highlight()
    return True
```

### BaseMode Pattern
```python
class BaseMode(ctk.CTkFrame):
    def __init__(self, master, name: str):
        super().__init__(master)
        self.name = name
        self.dashboard = None
        self.tabview = None
        self._tab_widgets = {}

    def activate(self) -> None:
        """Called when mode becomes active."""
        if self.dashboard:
            self.dashboard.refresh()

    def deactivate(self) -> None:
        """Called when mode is about to be hidden."""
        pass

    def get_current_tab_index(self) -> int:
        """Get current tab index for state preservation."""
        if self.tabview:
            return self.tabview.index(self.tabview.get())
        return 0
```

### Dashboard Pattern
```python
class BaseDashboard(ctk.CTkFrame):
    def add_stat(self, label: str, value: str) -> None:
        """Add a statistic display."""
        # Creates label/value pair in stats frame

    def update_stat(self, label: str, value: str) -> None:
        """Update a statistic value."""
        # Updates existing stat if present

    def refresh(self) -> None:
        """Refresh dashboard data - override in subclasses."""
        pass
```

## Output Format

**IMPORTANT**: Write your review to the main repo, NOT the worktree:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F038-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 038 - UI Mode Restructure

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 038-ui-mode-restructure
**Branch/Worktree:** `.worktrees/038-ui-mode-restructure`

## Summary

[Brief overview of findings - is the 5-mode architecture correctly implemented? Are there any issues?]

## Verification Results

### Module Import Validation
- mode_manager.py: [PASS/FAIL]
- catalog_mode.py: [PASS/FAIL]
- observe_mode.py: [PASS/FAIL]
- plan_mode.py: [PASS/FAIL]
- shop_mode.py: [PASS/FAIL]
- produce_mode.py: [PASS/FAIL]
- main_window.py: [PASS/FAIL]

### Test Results
- Full test suite: [X passed, Y skipped, Z failed]

### Code Pattern Validation
- Base classes (WP01): [correct/issues found]
- Mode navigation (WP02): [correct/issues found]
- CATALOG mode (WP03): [correct/issues found]
- OBSERVE mode (WP04): [correct/issues found]
- PLAN mode (WP05): [correct/issues found]
- SHOP mode (WP06): [correct/issues found]
- PRODUCE mode (WP07): [correct/issues found]
- Integration (WP08): [correct/issues found]

## Findings

### Critical Issues
[Any blocking issues that must be fixed before merge]

### Warnings
[Non-blocking concerns that should be addressed]

### Observations
[General observations about code quality, patterns, potential improvements]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/ui/base/base_mode.py | [status] | [notes] |
| src/ui/mode_manager.py | [status] | [notes] |
| src/ui/main_window.py | [status] | [notes] |
| src/ui/modes/catalog_mode.py | [status] | [notes] |
| src/ui/modes/observe_mode.py | [status] | [notes] |
| src/ui/modes/plan_mode.py | [status] | [notes] |
| src/ui/modes/shop_mode.py | [status] | [notes] |
| src/ui/modes/produce_mode.py | [status] | [notes] |
| src/ui/dashboards/*.py | [status] | [notes] |
| src/ui/tabs/*.py | [status] | [notes] |

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: 5-mode workflow | [PASS/FAIL] | [evidence] |
| FR-002: Active mode highlighting | [PASS/FAIL] | [evidence] |
| FR-003: Keyboard shortcuts Ctrl+1-5 | [PASS/FAIL] | [evidence] |
| FR-004: Tab state preservation | [PASS/FAIL] | [evidence] |
| FR-005: OBSERVE default on launch | [PASS/FAIL] | [evidence] |
| FR-007: CATALOG dashboard shows counts | [PASS/FAIL] | [evidence] |
| FR-008: PLAN dashboard shows events | [PASS/FAIL] | [evidence] |
| FR-009: SHOP dashboard shows shopping summary | [PASS/FAIL] | [evidence] |
| FR-010: PRODUCE dashboard shows production stats | [PASS/FAIL] | [evidence] |
| FR-011: OBSERVE dashboard shows progress | [PASS/FAIL] | [evidence] |
| FR-031: Old navigation removed | [PASS/FAIL] | [evidence] |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Base Classes | [PASS/FAIL] | [notes] |
| WP02: Main Window Navigation | [PASS/FAIL] | [notes] |
| WP03: CATALOG Mode | [PASS/FAIL] | [notes] |
| WP04: OBSERVE Mode | [PASS/FAIL] | [notes] |
| WP05: PLAN Mode | [PASS/FAIL] | [notes] |
| WP06: SHOP Mode | [PASS/FAIL] | [notes] |
| WP07: PRODUCE Mode | [PASS/FAIL] | [notes] |
| WP08: Integration & Polish | [PASS/FAIL] | [notes] |

## Code Quality Assessment

### BaseMode Class
| Item | Status | Notes |
|------|--------|-------|
| activate() method | [Yes/No] | [notes] |
| deactivate() method | [Yes/No] | [notes] |
| get_current_tab_index() | [Yes/No] | [notes] |
| set_current_tab_index() | [Yes/No] | [notes] |
| Tab widget management | [Yes/No] | [notes] |

### ModeManager Class
| Item | Status | Notes |
|------|--------|-------|
| switch_mode() method | [Yes/No] | [notes] |
| register_mode() method | [Yes/No] | [notes] |
| Tab state preservation | [Yes/No] | [notes] |
| Mode button highlighting | [Yes/No] | [notes] |
| Unsaved changes check hook | [Yes/No] | [notes] |

### Dashboard Implementations
| Dashboard | Has refresh() | Shows correct stats | Notes |
|-----------|---------------|---------------------|-------|
| CatalogDashboard | [Yes/No] | [Yes/No] | [notes] |
| ObserveDashboard | [Yes/No] | [Yes/No] | [notes] |
| PlanDashboard | [Yes/No] | [Yes/No] | [notes] |
| ShopDashboard | [Yes/No] | [Yes/No] | [notes] |
| ProduceDashboard | [Yes/No] | [Yes/No] | [notes] |

### Mode Implementations
| Mode | Extends BaseMode | Has Dashboard | Tab Count Correct | Notes |
|------|-----------------|---------------|-------------------|-------|
| CatalogMode | [Yes/No] | [Yes/No] | 6 tabs | [notes] |
| ObserveMode | [Yes/No] | [Yes/No] | 3 tabs | [notes] |
| PlanMode | [Yes/No] | [Yes/No] | 2 tabs | [notes] |
| ShopMode | [Yes/No] | [Yes/No] | 3 tabs | [notes] |
| ProduceMode | [Yes/No] | [Yes/No] | 4 tabs | [notes] |

## Potential Issues

### Unused Imports
[List any F401 flake8 warnings that should be addressed]

### Missing Type Hints
[Any missing type annotations]

### Architecture Concerns
[Any concerns about layered architecture compliance]

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing
- The worktree is isolated from main branch at `.worktrees/038-ui-mode-restructure`
- Layered architecture: UI -> Services -> Models -> Database
- Primary user is a non-technical baker (Marianne)
- This feature transforms 11 flat tabs into 5 workflow-oriented modes
- All existing tests must pass (no regressions)
- Placeholder tabs (Planning Workspace, Shopping Lists, Purchases, Assembly, Packaging) show "Coming Soon" messages
- Dashboard performance should be < 1 second (SC-005)
- UI must NOT contain business logic - only display service results
