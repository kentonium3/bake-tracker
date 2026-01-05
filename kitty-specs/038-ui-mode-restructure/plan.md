# Implementation Plan: UI Mode Restructure

**Branch**: `038-ui-mode-restructure` | **Date**: 2026-01-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/038-ui-mode-restructure/spec.md`

## Summary

Transform the application's flat 11-tab navigation into a 5-mode workflow-oriented architecture (CATALOG, PLAN, SHOP, PRODUCE, OBSERVE). This is primarily a UI restructuring effort - all required services already exist. Key deliverables: BaseMode/StandardTabLayout base classes, 5 mode containers with dashboards, migration of 12 existing tabs, creation of 5 new functional tabs (Shopping Lists, Purchases, Assembly, Packaging, Event Status).

## Technical Context

**Language/Version**: Python 3.10+ (existing project requirement)
**Primary Dependencies**: CustomTkinter (existing UI framework)
**Storage**: SQLite with WAL mode (no schema changes required - UI-only feature)
**Testing**: pytest (existing framework)
**Target Platform**: Desktop (Windows/macOS/Linux via PyInstaller)
**Project Type**: Single desktop application
**Performance Goals**: Mode dashboards display within 1 second (SC-005 from spec)
**Constraints**: No business logic in UI layer; all new tabs use existing services
**Scale/Scope**: 5 modes, 17 total tabs (12 migrated + 5 new)

### Service Layer Status (Validated)

All services required for new tabs exist and are functional:

| New Tab | Service | Key Functions |
|---------|---------|---------------|
| Shopping Lists | `event_service.py` | `get_shopping_list()` |
| Purchases | `purchase_service.py` | `record_purchase()`, `get_purchase_history()` |
| Assembly | `assembly_service.py` | `check_can_assemble()`, `record_assembly()` |
| Packaging | `packaging_service.py` | `get_pending_requirements()`, `assign_materials()` |
| Event Status | `event_service.py` | `get_event_overall_progress()`, `get_production_progress()` |

### Existing UI Tabs to Migrate

| Current Tab | Target Mode | File |
|-------------|-------------|------|
| ingredients_tab.py | CATALOG | 58KB |
| products_tab.py | CATALOG | 37KB |
| recipes_tab.py | CATALOG | 19KB |
| finished_units_tab.py | CATALOG | 27KB |
| finished_goods_tab.py | CATALOG | 14KB |
| packages_tab.py | CATALOG | 17KB |
| events_tab.py | PLAN | 11KB |
| inventory_tab.py | SHOP | 103KB |
| production_tab.py | PRODUCE | 30KB |
| production_dashboard_tab.py | PRODUCE | 21KB |
| dashboard_tab.py | OBSERVE | 9KB |
| recipients_tab.py | PRODUCE | 18KB |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Mode-based navigation reduces cognitive load; Primary user (Marianne) is non-technical |
| II. Data Integrity & FIFO | ✅ N/A | No data changes - UI restructuring only |
| III. Future-Proof Schema | ✅ N/A | No schema changes required |
| IV. Test-Driven Development | ✅ PASS | UI base classes will have unit tests; service layer already tested |
| V. Layered Architecture | ✅ PASS | New UI tabs use existing services; no business logic in UI |
| VI. Schema Change Strategy | ✅ N/A | No database changes |
| VII. Pragmatic Aspiration | ✅ PASS | Service layer separation enables future web migration |

**Gate Result**: PASSED - No violations. Feature is UI-only restructuring using existing service layer.

## Project Structure

### Documentation (this feature)

```
kitty-specs/038-ui-mode-restructure/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (UI entities)
├── quickstart.md        # Phase 1 output
├── checklists/          # Quality checklists
│   └── requirements.md
└── tasks/               # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/                    # No changes (UI-only feature)
├── services/                  # No changes (services already exist)
├── ui/
│   ├── base/                  # NEW: Base classes for mode architecture
│   │   ├── __init__.py
│   │   ├── base_mode.py       # BaseMode class - mode container
│   │   └── standard_tab_layout.py  # StandardTabLayout - consistent tab pattern
│   ├── modes/                 # NEW: Mode implementations
│   │   ├── __init__.py
│   │   ├── catalog_mode.py    # CATALOG: definitions management
│   │   ├── plan_mode.py       # PLAN: event planning
│   │   ├── shop_mode.py       # SHOP: shopping/inventory
│   │   ├── produce_mode.py    # PRODUCE: production execution
│   │   └── observe_mode.py    # OBSERVE: status/progress
│   ├── dashboards/            # NEW: Mode-specific dashboards
│   │   ├── __init__.py
│   │   ├── catalog_dashboard.py
│   │   ├── plan_dashboard.py
│   │   ├── shop_dashboard.py
│   │   ├── produce_dashboard.py
│   │   └── observe_dashboard.py
│   ├── tabs/                  # NEW: New functional tabs
│   │   ├── __init__.py
│   │   ├── shopping_lists_tab.py   # SHOP mode
│   │   ├── purchases_tab.py        # SHOP mode
│   │   ├── assembly_tab.py         # PRODUCE mode
│   │   ├── packaging_tab.py        # PRODUCE mode
│   │   └── event_status_tab.py     # OBSERVE mode
│   ├── main_window.py         # MODIFY: Replace flat tabs with mode bar
│   ├── ingredients_tab.py     # MODIFY: Adapt to StandardTabLayout
│   ├── products_tab.py        # MODIFY: Adapt to StandardTabLayout
│   ├── recipes_tab.py         # MODIFY: Adapt to StandardTabLayout
│   ├── finished_units_tab.py  # MODIFY: Adapt to StandardTabLayout
│   ├── finished_goods_tab.py  # MODIFY: Adapt to StandardTabLayout
│   ├── packages_tab.py        # MODIFY: Adapt to StandardTabLayout
│   ├── events_tab.py          # MODIFY: Adapt to StandardTabLayout
│   ├── inventory_tab.py       # MODIFY: Adapt to StandardTabLayout
│   ├── production_tab.py      # MODIFY: Adapt to StandardTabLayout
│   ├── production_dashboard_tab.py  # MODIFY: Merge into PRODUCE mode
│   └── dashboard_tab.py       # MODIFY: Enhance for OBSERVE mode
└── tests/
    └── ui/                    # NEW: UI base class tests
        ├── test_base_mode.py
        └── test_standard_tab_layout.py
```

**Structure Decision**: Extends existing single-project structure with new `ui/base/`, `ui/modes/`, `ui/dashboards/`, and `ui/tabs/` directories for organizational clarity.

## Complexity Tracking

*No constitution violations requiring justification.*

| Consideration | Decision | Rationale |
|---------------|----------|-----------|
| New directory structure | Add `ui/base/`, `ui/modes/`, `ui/dashboards/`, `ui/tabs/` | Keeps existing tabs in place for minimal disruption; new structure for new components |
| Tab refactoring scope | Minimal changes to existing tabs | StandardTabLayout adapts via composition, not inheritance rewrite |

## Implementation Strategy

### Parallelization Opportunities

Per spec section "Parallelization Opportunities", these work streams are independent:

1. **Base Classes** (must complete first): BaseMode, StandardTabLayout
2. **CATALOG Mode** (after base classes): 6 existing tabs, dashboard
3. **OBSERVE Mode** (after base classes): Dashboard, Event Status, Reports
4. **PLAN Mode** (after base classes): Events, Planning Workspace
5. **SHOP Mode** (after base classes): Shopping Lists, Purchases, Inventory
6. **PRODUCE Mode** (after base classes): Production Runs, Assembly, Packaging

Recommended parallelization:
- Claude: Base classes + main_window integration + PRODUCE mode
- Gemini: CATALOG mode tab migrations + OBSERVE mode

### Migration Approach

Big-bang replacement per clarified requirement:
1. Complete all 5 modes with dashboards and tabs
2. Update main_window.py to use mode navigation
3. Remove old flat tab navigation in single commit
4. Test full workflow before merge

## Phase 0 Research Notes

Research focus areas for `/spec-kitty.research`:
1. CustomTkinter tab widget patterns for mode containers
2. Existing tab structure for StandardTabLayout abstraction
3. Dashboard widget composition patterns
4. Keyboard shortcut implementation (Ctrl+1-5)

## Phase 1 Design Artifacts

To be generated:
- `data-model.md`: UI entity definitions (Mode, Dashboard, StandardTabLayout)
- `quickstart.md`: Development setup and testing guide
- No `/contracts/` needed (UI-only feature, no API changes)
