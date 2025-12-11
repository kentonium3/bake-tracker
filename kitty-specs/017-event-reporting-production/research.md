# Research: Event Reporting & Production Dashboard

**Feature**: 017-event-reporting-production
**Date**: 2025-12-11
**Status**: Complete

## Research Summary

Feature 017 builds on Feature 016's event-centric production model to provide reporting and dashboard improvements. Research confirms that most required service-layer functionality already exists.

## Key Decisions

### D1: Dashboard Restructuring Approach

**Decision**: Tab Reordering (Option A)
- Move Production Dashboard to first tab position
- Rename existing Dashboard to "Summary"
- Update `main_window.py` tab order and default selection

**Rationale**: Minimal code changes, aligns with constitution's "present-simple implementation" principle. The Production Dashboard already has sub-tabs internally for Production/Assembly runs.

**Alternatives Considered**:
- Unified Dashboard with sub-tabs: Rejected due to unnecessary refactoring complexity

### D2: Event Progress Display Location

**Decision**: Add to Production Dashboard (Option A)
- Add event selector dropdown to ProductionDashboardTab
- Display production/assembly progress with progress bars
- Immediate visibility on app launch

**Rationale**: Delivers on SC-007 ("answer 'Where do I stand for Christmas 2025?' within 5 seconds of opening app"). Event Detail window's Targets tab remains as secondary access point.

**Alternatives Considered**:
- Event Detail only: Rejected because requires navigation, doesn't meet 5-second requirement

### D3: CSV Export Location

**Decision**: Event Detail Shopping Tab (Option A)
- Add "Export CSV" button directly on Shopping List tab
- User exports what they're viewing
- Simple, context-aware UX

**Rationale**: File menu export is for full database backup. Shopping list export is event-specific, belongs in event context.

**Alternatives Considered**:
- File menu: Rejected - inconsistent with existing export pattern (full database vs. single list)
- Both locations: Rejected - unnecessary complexity

### D4: Service Layer Assessment

**Decision**: Minimal new service methods required

**Existing Methods (from Feature 016)**:
| Method | Location | Status |
|--------|----------|--------|
| `get_production_progress()` | event_service.py:1713 | Exists |
| `get_assembly_progress()` | event_service.py:1780 | Exists |
| `get_event_overall_progress()` | event_service.py:1843 | Exists |
| `get_shopping_list()` | event_service.py:940 | Exists |
| `get_recipient_history()` | event_service.py:1449 | Exists |
| `get_event_summary()` | event_service.py:751 | Exists |

**New Methods Needed**:
| Method | Purpose |
|--------|---------|
| `export_shopping_list_csv()` | Generate CSV from shopping list data |
| `get_event_cost_analysis()` | Aggregate costs from ProductionConsumption/AssemblyConsumption |

### D5: Cost Analysis Data Source

**Decision**: Use `cost_at_time` from consumption records

**Rationale**:
- ProductionConsumption records store `cost_at_time` when ingredients are consumed
- AssemblyFinishedUnitConsumption/AssemblyPackagingConsumption similarly store costs
- Using historical costs (not current prices) gives accurate actual vs estimated comparison

**Data Model**:
- ProductionRun.total_cost = sum of ProductionConsumption.cost_at_time * quantity
- AssemblyRun.total_cost = sum of all consumption records

## Existing Infrastructure Analysis

### main_window.py Tab Structure (line 85-148)
```python
# Current tab order:
1. "Dashboard" (DashboardTab) - line 92
2. "My Ingredients"
3. "My Pantry"
4. "Recipes"
5. "Finished Units"
6. "Packages"
7. "Recipients"
8. "Events"
9. "Production" (ProductionDashboardTab) - line 101
10. "Reports" (placeholder) - line 102

# Default: line 147
self.tabview.set("Dashboard")
```

**Required Changes**:
1. Rename "Dashboard" to "Summary"
2. Reorder tabs: Production first
3. Change default: `self.tabview.set("Production")`

### ProductionDashboardTab (production_dashboard_tab.py)
- Already has sub-tabs: "Production Runs" and "Assembly Runs"
- Shows recent activity (last 30 days)
- **Enhancement needed**: Add event selector + progress section

### Event Service Methods

**Shopping List** (`get_shopping_list()` line 940):
- Returns dict with `items`, `total_estimated_cost`, `items_count`, `items_with_shortfall`
- Each item has: `ingredient_name`, `unit`, `quantity_needed`, `quantity_on_hand`, `shortfall`, `product_recommendation`
- **CSV export just needs to format this data**

**Progress Methods** (lines 1713-1947):
- `get_production_progress()`: Returns recipe targets with batches produced
- `get_assembly_progress()`: Returns finished good targets with quantity assembled
- `get_event_overall_progress()`: Aggregates production, assembly, package status

**Recipient History** (`get_recipient_history()` line 1449):
- Already returns event, package, quantity, notes per assignment
- **Enhancement needed**: Add fulfillment_status to returned data

## Open Questions

### Resolved

1. **Q**: Should Production Dashboard be renamed?
   **A**: No - keep "Production" tab name, it's descriptive

2. **Q**: What happens with unassigned production (no event_id)?
   **A**: Show in separate "Unassigned" section on dashboard (existing behavior)

3. **Q**: How to handle events with no targets?
   **A**: Show helpful message with link to Event Detail → Targets tab

### Deferred to Implementation

1. Progress bar styling (visual design details)
2. CSV column order and formatting specifics
3. Cost analysis table layout

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tab reordering breaks refresh callbacks | Low | Low | Existing `_on_tab_change()` handles by tab name |
| CSV export fails silently | Low | Medium | Use try/catch with user notification |
| Performance with large event data | Low | Low | Existing queries are indexed |

## References

- Feature 016 spec: `kitty-specs/016-event-centric-production/spec.md`
- Schema v0.6 design: `docs/design/schema_v0.6_design.md`
- Event service: `src/services/event_service.py`
- Production dashboard: `src/ui/production_dashboard_tab.py`
- Main window: `src/ui/main_window.py`
