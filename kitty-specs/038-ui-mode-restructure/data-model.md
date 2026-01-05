# Data Model: UI Mode Restructure

**Feature**: 038-ui-mode-restructure
**Date**: 2026-01-05
**Type**: UI Entities (no database changes)

## Overview

This feature introduces UI-layer entities for the mode-based navigation architecture. These are Python classes, not database models.

## UI Entity Definitions

### BaseMode

**Purpose**: Abstract base class for all mode containers

**Location**: `src/ui/base/base_mode.py`

```python
class BaseMode(ctk.CTkFrame):
    """Base class for mode containers.

    Attributes:
        name: str - Mode identifier (CATALOG, PLAN, SHOP, PRODUCE, OBSERVE)
        dashboard: BaseDashboard - Mode-specific dashboard widget
        tabview: ctk.CTkTabview - Tab container for mode's tabs
        current_tab_index: int - Currently selected tab index
        tabs: List[Tab] - List of tab instances

    Methods:
        activate() -> None - Called when mode becomes active
        deactivate() -> None - Called when mode becomes inactive
        get_current_tab_index() -> int - Returns current tab selection
        set_current_tab_index(index: int) -> None - Restores tab selection
        refresh_dashboard() -> None - Updates dashboard statistics
    """
```

**Relationships**:
- Contains 1 dashboard (BaseDashboard subclass)
- Contains 1+ tabs (StandardTabLayout subclasses)

### StandardTabLayout

**Purpose**: Consistent layout pattern for all tabs

**Location**: `src/ui/base/standard_tab_layout.py`

```python
class StandardTabLayout(ctk.CTkFrame):
    """Standard tab layout with consistent regions.

    Regions:
        action_bar: CTkFrame - Top-left for Add/Edit/Delete buttons
        refresh_area: CTkFrame - Top-right for Refresh button
        filter_bar: CTkFrame - Below action bar for search/filters
        content_area: CTkFrame - Main content area for data grid
        status_bar: CTkFrame - Bottom for status information

    Attributes:
        action_buttons: List[CTkButton] - Action buttons in action bar
        refresh_button: CTkButton - Refresh button
        search_entry: CTkEntry - Search input field
        filter_widgets: List[Widget] - Filter controls
        data_grid: Widget - Main data display (TreeView or similar)
        status_label: CTkLabel - Status text

    Methods:
        set_action_buttons(buttons: List[Dict]) -> None
        set_filters(filters: List[Dict]) -> None
        set_content(widget: Widget) -> None
        set_status(text: str) -> None
        get_search_text() -> str
        refresh() -> None - Abstract, implemented by subclass
    """
```

**Layout Regions** (grid layout):
```
Row 0: [action_bar (col 0-1, sticky W)] [refresh_area (col 2, sticky E)]
Row 1: [filter_bar (col 0-2, sticky EW)]
Row 2: [content_area (col 0-2, sticky NSEW, weight=1)]
Row 3: [status_bar (col 0-2, sticky EW)]
```

### BaseDashboard

**Purpose**: Abstract base class for mode dashboards

**Location**: `src/ui/dashboards/base_dashboard.py`

```python
class BaseDashboard(ctk.CTkFrame):
    """Base class for mode-specific dashboards.

    Attributes:
        is_collapsed: bool - Dashboard visibility state
        stats_frame: CTkFrame - Container for statistics widgets
        actions_frame: CTkFrame - Container for quick action buttons

    Methods:
        refresh() -> None - Abstract, updates dashboard data
        collapse() -> None - Hides dashboard content
        expand() -> None - Shows dashboard content
        toggle() -> None - Toggle collapsed state
    """
```

### ModeManager

**Purpose**: Coordinates mode switching and state preservation

**Location**: `src/ui/main_window.py` (integrated)

```python
class ModeManager:
    """Manages mode switching and state.

    Attributes:
        current_mode: str - Active mode name
        modes: Dict[str, BaseMode] - Mode instances by name
        mode_tab_state: Dict[str, int] - Last tab index per mode

    Methods:
        switch_mode(mode_name: str) -> None
        get_current_mode() -> BaseMode
        save_tab_state() -> None
        restore_tab_state() -> None
    """
```

## Mode Implementations

### CatalogMode

**Inherits**: BaseMode
**Location**: `src/ui/modes/catalog_mode.py`

**Dashboard Stats**:
- Ingredient count
- Product count
- Recipe count
- Finished Unit count
- Finished Good count
- Package count

**Tabs** (6):
1. Ingredients (existing: `ingredients_tab.py`)
2. Products (existing: `products_tab.py`)
3. Recipes (existing: `recipes_tab.py`)
4. Finished Units (existing: `finished_units_tab.py`)
5. Finished Goods (existing: `finished_goods_tab.py`)
6. Packages (existing: `packages_tab.py`)

### PlanMode

**Inherits**: BaseMode
**Location**: `src/ui/modes/plan_mode.py`

**Dashboard Stats**:
- Upcoming event count
- Events needing attention
- Next event date

**Tabs** (2):
1. Events (existing: `events_tab.py`)
2. Planning Workspace (NEW: shows calculated batch requirements)

### ShopMode

**Inherits**: BaseMode
**Location**: `src/ui/modes/shop_mode.py`

**Dashboard Stats**:
- Shopping lists by store
- Low inventory alerts count
- Pending purchase items

**Tabs** (3):
1. Shopping Lists (NEW: `shopping_lists_tab.py`)
2. Purchases (NEW: `purchases_tab.py`)
3. Inventory - My Pantry (existing: `inventory_tab.py`)

### ProduceMode

**Inherits**: BaseMode
**Location**: `src/ui/modes/produce_mode.py`

**Dashboard Stats**:
- Pending production batches
- Assembly checklist items
- Packaging checklist items

**Tabs** (4):
1. Production Runs (existing: `production_tab.py` + `production_dashboard_tab.py` merged)
2. Assembly (NEW: `assembly_tab.py`)
3. Packaging (NEW: `packaging_tab.py`)
4. Recipients (existing: `recipients_tab.py`)

### ObserveMode

**Inherits**: BaseMode
**Location**: `src/ui/modes/observe_mode.py`

**Dashboard Stats**:
- Event readiness percentages (shopping, production, assembly, packaging)
- Today's activity summary

**Tabs** (3):
1. Dashboard (existing: `dashboard_tab.py` enhanced)
2. Event Status (NEW: `event_status_tab.py`)
3. Reports (summary views)

## New Tab Entities

### ShoppingListsTab

**Location**: `src/ui/tabs/shopping_lists_tab.py`
**Mode**: SHOP
**Service**: `event_service.get_shopping_list()`

**Data Display**:
- Group items by store/supplier
- Show: ingredient name, quantity needed, unit, product options
- Support: generate list, print list, mark as purchased

### PurchasesTab

**Location**: `src/ui/tabs/purchases_tab.py`
**Mode**: SHOP
**Service**: `purchase_service`

**Data Display**:
- Purchase history list
- Show: date, product, quantity, price, supplier
- Support: record purchase, edit, delete

### AssemblyTab

**Location**: `src/ui/tabs/assembly_tab.py`
**Mode**: PRODUCE
**Service**: `assembly_service`

**Data Display**:
- Checklist of finished goods ready for assembly
- Show: finished good name, quantity available, components status
- Support: record assembly, view requirements

### PackagingTab

**Location**: `src/ui/tabs/packaging_tab.py`
**Mode**: PRODUCE
**Service**: `packaging_service`

**Data Display**:
- Packaging checklist
- Show: package name, items to include, event assignment
- Support: assign materials, mark complete

### EventStatusTab

**Location**: `src/ui/tabs/event_status_tab.py`
**Mode**: OBSERVE
**Service**: `event_service.get_event_overall_progress()`

**Data Display**:
- Per-event progress tracking
- Show: event name, date, shopping %, production %, assembly %, packaging %
- Support: drill-down to event details

## Relationships Diagram

```
MainWindow
    └── ModeManager
            └── mode_bar: CTkFrame (mode buttons)
            └── modes: Dict[str, BaseMode]
                    ├── CatalogMode
                    │       ├── CatalogDashboard (BaseDashboard)
                    │       └── CTkTabview
                    │               ├── IngredientsTab (StandardTabLayout)
                    │               ├── ProductsTab
                    │               ├── RecipesTab
                    │               ├── FinishedUnitsTab
                    │               ├── FinishedGoodsTab
                    │               └── PackagesTab
                    ├── PlanMode
                    │       ├── PlanDashboard
                    │       └── CTkTabview
                    │               ├── EventsTab
                    │               └── PlanningWorkspaceTab (NEW)
                    ├── ShopMode
                    │       ├── ShopDashboard
                    │       └── CTkTabview
                    │               ├── ShoppingListsTab (NEW)
                    │               ├── PurchasesTab (NEW)
                    │               └── InventoryTab
                    ├── ProduceMode
                    │       ├── ProduceDashboard
                    │       └── CTkTabview
                    │               ├── ProductionRunsTab (merged)
                    │               ├── AssemblyTab (NEW)
                    │               ├── PackagingTab (NEW)
                    │               └── RecipientsTab (existing)
                    └── ObserveMode
                            ├── ObserveDashboard
                            └── CTkTabview
                                    ├── DashboardTab (enhanced)
                                    ├── EventStatusTab (NEW)
                                    └── ReportsTab
```

## State Management

**Mode State** (preserved during session):
- Current mode selection
- Per-mode tab selection

**Not Preserved** (resets on restart):
- Dashboard collapse state
- Filter/search state within tabs
- Scroll positions

## Migration Notes

### Existing Tabs Integration

Existing tabs will be minimally modified:
1. Ensure they work within StandardTabLayout container OR
2. Wrap them in StandardTabLayout adapter if needed

Priority approach: Composition over refactoring
- Existing tabs remain largely unchanged
- StandardTabLayout provides container structure
- Gradual standardization in future iterations if desired
