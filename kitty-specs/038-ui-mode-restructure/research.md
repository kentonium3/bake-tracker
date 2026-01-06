# Research: UI Mode Restructure

**Feature**: 038-ui-mode-restructure
**Date**: 2026-01-05
**Status**: Complete

## Research Questions

### RQ-1: What CustomTkinter patterns exist for mode-based navigation?

**Decision**: Use `CTkFrame` as mode container with `CTkTabview` for inner tab navigation

**Rationale**:
- CustomTkinter's `CTkTabview` handles internal tab switching efficiently
- Mode switching uses frame visibility (pack/pack_forget or grid/grid_remove)
- This matches existing `main_window.py` patterns with notebook-style navigation

**Evidence**: Reviewed `src/ui/main_window.py` - current implementation uses CTkTabview

**Alternatives Considered**:
- Single CTkTabview with 17 tabs: Rejected (too many tabs, poor UX)
- Custom canvas-based navigation: Rejected (unnecessary complexity)

### RQ-2: What layout patterns do existing tabs use?

**Decision**: StandardTabLayout provides consistent structure via composition, not inheritance

**Rationale**:
- Existing tabs have inconsistent layouts (action buttons in different positions)
- StandardTabLayout creates container frame with predefined regions
- Existing tabs can be wrapped without full rewrites

**Evidence**: Analyzed existing tabs:
- `ingredients_tab.py`: Actions top-left, filters below, grid center - matches target
- `products_tab.py`: Similar pattern but filter placement varies
- `inventory_tab.py`: Complex multi-panel layout, needs careful integration
- Most tabs already have action bar + filter + grid + status pattern

**Pattern Extracted**:
```
┌─────────────────────────────────────────────────────────┐
│ [Add] [Edit] [Delete]              [Refresh] │ Action Bar
├─────────────────────────────────────────────────────────┤
│ Search: [________] Filter: [▼]              │ Filter Bar
├─────────────────────────────────────────────────────────┤
│                                                         │
│                    Data Grid                            │ Main Content
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Items: 42 | Selected: 1                     │ Status Bar
└─────────────────────────────────────────────────────────┘
```

### RQ-3: How should mode dashboards be structured?

**Decision**: Dashboard as collapsible frame at top of mode, showing summary stats and quick actions

**Rationale**:
- Dashboards provide at-a-glance information without tab switching
- Collapsible design preserves screen real estate when not needed
- Widget-based composition allows mode-specific customization

**Evidence**:
- Existing `dashboard_tab.py` and `production_dashboard_tab.py` provide reference patterns
- Summary stats use CTkLabel widgets in grid layout
- Quick actions use CTkButton widgets

**Dashboard Components**:
| Mode | Stats | Quick Actions |
|------|-------|---------------|
| CATALOG | Ingredient/Product/Recipe/FU/FG counts | Add Ingredient, Add Recipe |
| PLAN | Upcoming events with status | New Event |
| SHOP | Shopping lists by store, low inventory alerts | Generate List |
| PRODUCE | Pending production, assembly checklist | Start Batch |
| OBSERVE | Event readiness percentages | View Event |

### RQ-4: How to implement keyboard shortcuts (Ctrl+1-5)?

**Decision**: Bind shortcuts to root window, dispatch to mode switcher

**Rationale**:
- Root-level bindings ensure shortcuts work regardless of focus
- Text field focus should not block mode switching (per spec edge case)
- CustomTkinter inherits from tkinter, standard bind() works

**Evidence**: Tkinter binding patterns are well-documented

**Implementation**:
```python
# In main_window.py
self.bind_all("<Control-1>", lambda e: self.switch_mode("CATALOG"))
self.bind_all("<Control-2>", lambda e: self.switch_mode("PLAN"))
self.bind_all("<Control-3>", lambda e: self.switch_mode("SHOP"))
self.bind_all("<Control-4>", lambda e: self.switch_mode("PRODUCE"))
self.bind_all("<Control-5>", lambda e: self.switch_mode("OBSERVE"))
```

### RQ-5: What service methods are available for new tabs?

**Decision**: All required services exist - no service layer changes needed

**Evidence**: Code review of service layer:

| New Tab | Service | Methods Available |
|---------|---------|-------------------|
| Shopping Lists | `event_service.py` | `get_shopping_list(event_id, include_packaging)` returns organized list |
| Purchases | `purchase_service.py` | `record_purchase()`, `get_purchase_history()`, `get_most_recent_purchase()` |
| Assembly | `assembly_service.py` | `check_can_assemble()`, `record_assembly()`, `get_assembly_history()` |
| Packaging | `packaging_service.py` | `get_pending_requirements()`, `assign_materials()`, `get_assignment_summary()` |
| Event Status | `event_service.py` | `get_event_overall_progress()`, `get_production_progress()`, `get_assembly_progress()` |

### RQ-6: How should mode state be preserved?

**Decision**: Each mode maintains last-selected tab index in memory

**Rationale**:
- Per FR-004: "System MUST preserve tab selection when switching between modes and returning"
- Simple dictionary mapping mode -> tab_index
- State resets on application restart (acceptable per spec)

**Implementation**:
```python
class ModeManager:
    def __init__(self):
        self.mode_tab_state = {
            "CATALOG": 0,  # Default to first tab
            "PLAN": 0,
            "SHOP": 0,
            "PRODUCE": 0,
            "OBSERVE": 0,
        }
```

### RQ-7: What is the recipients tab's destination?

**Decision**: Recipients tab assigned to PRODUCE mode

**Rationale**:
- User clarification (2026-01-05): Recipients tab belongs in PRODUCE mode
- Recipients are relevant during production/packaging workflow (who receives packages)
- PRODUCE mode tabs: Production Runs, Assembly, Packaging, Recipients (4 tabs)

**Evidence**: User clarification during planning session

## Open Questions

1. ~~**Recipients Tab**~~: RESOLVED - Assigned to PRODUCE mode
2. **Reports Tab**: Reports are not yet defined - implement as placeholder tab in OBSERVE mode

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Existing tab refactoring breaks functionality | Medium | High | Test each tab after StandardTabLayout integration |
| Dashboard data loading slows mode switching | Low | Medium | Use progressive loading, cache dashboard data |
| Keyboard shortcuts conflict with text entry | Low | Low | Use Ctrl+Number which doesn't conflict with typing |
| Large inventory tab (103KB) complex integration | Medium | Medium | Test inventory tab integration thoroughly |

## Sources

- `src/ui/main_window.py` - Current navigation implementation
- `src/ui/ingredients_tab.py` - Example tab layout patterns
- `src/ui/dashboard_tab.py` - Dashboard widget patterns
- `src/services/event_service.py` - Event and shopping list services
- `src/services/purchase_service.py` - Purchase tracking services
- `src/services/assembly_service.py` - Assembly services
- `src/services/packaging_service.py` - Packaging services
- `docs/design/_F038_ui_mode_restructure.md` - Feature design document
