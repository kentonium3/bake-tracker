# Implementation Plan: Event Reporting & Production Dashboard

**Branch**: `017-event-reporting-production` | **Date**: 2025-12-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/017-event-reporting-production/spec.md`

## Summary

Feature 017 makes the Production Dashboard the default view on app launch and enhances it with event-specific progress tracking. Additionally, it adds shopping list CSV export, event summary reports with cost analysis, and recipient package history. The feature builds on Feature 016's event-centric production model and requires minimal new service methods.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x, csv (stdlib)
**Storage**: SQLite with WAL mode
**Testing**: pytest
**Target Platform**: Desktop (macOS, Windows, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Dashboard load < 2 seconds, CSV export < 5 seconds for typical event
**Constraints**: UI must be intuitive for non-technical user
**Scale/Scope**: Single user, ~5-20 events, ~50-200 recipes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Production status on launch answers daily "where do I stand?" question |
| II. Data Integrity & FIFO | PASS | Cost analysis uses historical cost_at_time from consumption records |
| III. Future-Proof Schema | PASS | No new tables needed; uses existing v0.6 schema |
| IV. Test-Driven Development | PASS | New service methods will have unit tests |
| V. Layered Architecture | PASS | CSV export logic in services, UI just triggers and saves file |
| VI. Migration Safety | N/A | No schema changes |
| VII. Pragmatic Aspiration | PASS | Simple implementation, web migration cost is low |

**Desktop Phase Checks**:
- Does this design block web deployment? **NO** - Service layer is UI-independent
- Is the service layer UI-independent? **YES** - All business logic in event_service.py
- Are business rules in services, not UI? **YES** - UI only displays data and triggers exports
- What's the web migration cost? **LOW** - Service methods can become API endpoints

## Project Structure

### Documentation (this feature)

```
kitty-specs/017-event-reporting-production/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data model (no new tables)
├── quickstart.md        # Developer quickstart guide
├── research/            # Evidence and source tracking
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/              # No changes needed
├── services/
│   └── event_service.py # Add export_shopping_list_csv(), get_event_cost_analysis()
├── ui/
│   ├── main_window.py              # Tab order, default tab
│   ├── production_dashboard_tab.py # Event selector, progress bars
│   ├── dashboard_tab.py            # Rename class comments
│   ├── event_detail_window.py      # CSV export button, enhanced summary
│   └── recipients_tab.py           # Package history section
└── tests/
    └── services/
        └── test_event_service.py   # Tests for new methods
```

**Structure Decision**: Single desktop application - all changes within existing src/ structure.

## Complexity Tracking

*No Constitution Check violations. No complexity justifications needed.*

## Implementation Phases

### Phase 1: Service Layer (Priority: P1)

**Goal**: Add CSV export and cost analysis service methods.

**Tasks**:
1. Add `export_shopping_list_csv(event_id, file_path)` to event_service.py
2. Add `get_event_cost_analysis(event_id)` to event_service.py
3. Enhance `get_recipient_history()` to include fulfillment_status
4. Add unit tests for new methods

**Dependencies**: None (uses existing schema)

### Phase 2: Dashboard Restructuring (Priority: P1)

**Goal**: Make Production Dashboard the default view.

**Tasks**:
1. Update main_window.py tab order (Production first)
2. Rename "Dashboard" tab to "Summary"
3. Update default tab selection
4. Update tab change callback

**Dependencies**: None

### Phase 3: Production Dashboard Enhancement (Priority: P1)

**Goal**: Add event progress tracking to Production Dashboard.

**Tasks**:
1. Add event selector dropdown to ProductionDashboardTab
2. Add production progress section with progress bars
3. Add assembly progress section with progress bars
4. Handle "no targets" case with helpful message
5. Add navigation link to Event Detail for target management

**Dependencies**: Phase 1 (service methods)

### Phase 4: CSV Export (Priority: P2)

**Goal**: Add shopping list CSV export to Event Detail.

**Tasks**:
1. Add "Export CSV" button to Shopping tab in EventDetailWindow
2. Implement file save dialog with default filename
3. Call service method and handle errors
4. Show success/failure notification

**Dependencies**: Phase 1 (export_shopping_list_csv)

### Phase 5: Event Summary Enhancement (Priority: P2)

**Goal**: Enhance event summary with planned vs actual reporting.

**Tasks**:
1. Add planned vs actual production section
2. Add planned vs actual assembly section
3. Add package fulfillment status counts
4. Add cost variance display (estimated vs actual)

**Dependencies**: Phase 1 (get_event_cost_analysis)

### Phase 6: Recipient History (Priority: P3)

**Goal**: Add package history to recipient detail.

**Tasks**:
1. Add history section to recipient detail view
2. Display events, packages, quantities, fulfillment status
3. Sort by event date descending

**Dependencies**: Phase 1 (enhanced get_recipient_history)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Tab reordering breaks refresh callbacks | Test tab switching with `_on_tab_change()` method |
| CSV export fails | Use try/catch with user notification, test with various file paths |
| Progress bars overflow with >100% | Display percentage as-is (show over-production) |
| Performance with large events | Existing queries are indexed; monitor and optimize if needed |

## Testing Strategy

### Unit Tests (Service Layer)
- `test_export_shopping_list_csv_success`
- `test_export_shopping_list_csv_event_not_found`
- `test_export_shopping_list_csv_io_error`
- `test_get_event_cost_analysis_with_production`
- `test_get_event_cost_analysis_no_production`
- `test_get_recipient_history_with_fulfillment_status`

### Manual Tests (UI)
- [ ] App opens to Production Dashboard
- [ ] Summary tab shows previous Dashboard content
- [ ] Event selector populates with events
- [ ] Progress bars display correctly
- [ ] CSV export creates valid file
- [ ] Event summary shows variance
- [ ] Recipient history displays correctly

## Success Criteria Verification

| Criterion | Verification Method |
|-----------|---------------------|
| SC-001: Dashboard load < 2s | Manual timing |
| SC-002: CSV readable in Excel | Open exported file in Excel |
| SC-003: Progress matches calculation | Unit test assertions |
| SC-004: Cost totals match | Unit test assertions |
| SC-005: Existing tests pass | `pytest src/tests -v` |
| SC-006: New methods >80% coverage | `pytest --cov` |
| SC-007: 5-second answer time | Manual user testing |

## Artifacts Generated

- `kitty-specs/017-event-reporting-production/research.md` - Research decisions
- `kitty-specs/017-event-reporting-production/data-model.md` - Data model documentation
- `kitty-specs/017-event-reporting-production/quickstart.md` - Developer guide
- `kitty-specs/017-event-reporting-production/research/evidence-log.csv` - Evidence tracking
- `kitty-specs/017-event-reporting-production/research/source-register.csv` - Source references
