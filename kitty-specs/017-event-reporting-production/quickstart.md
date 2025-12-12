# Quickstart: Feature 017 - Event Reporting & Production Dashboard

## Overview

Feature 017 enhances the application with production-focused dashboard and event reporting capabilities. It builds on Feature 016's event-centric production model.

## Key Changes

### 1. Dashboard Restructuring

**Before**: Dashboard tab shows static summary stats (ingredient count, recipe count, etc.)
**After**:
- Production Dashboard becomes default/first tab
- Old Dashboard renamed to "Summary" tab
- Production Dashboard gains event progress section

### 2. Production Dashboard Enhancements

New UI elements on ProductionDashboardTab:
- Event selector dropdown (filter by event)
- Production progress section (recipes: target vs produced)
- Assembly progress section (finished goods: target vs assembled)
- "No targets set" message with navigation link

### 3. Shopping List CSV Export

New button on Event Detail → Shopping tab:
- "Export CSV" button
- Saves to user-selected file location
- Columns: Ingredient, Quantity, Unit, Brand, Cost

### 4. Event Summary Enhancements

Enhanced Summary tab in Event Detail showing:
- Planned vs actual production
- Planned vs actual assembly
- Package fulfillment counts
- Cost variance (estimated vs actual)

### 5. Recipient History

Enhanced recipient detail showing:
- Package history across all events
- Includes fulfillment status per package

## Files to Modify

| File | Changes |
|------|---------|
| `src/ui/main_window.py` | Tab order, default tab |
| `src/ui/production_dashboard_tab.py` | Event selector, progress bars |
| `src/ui/dashboard_tab.py` | Rename to Summary |
| `src/ui/event_detail_window.py` | CSV export button, enhanced summary |
| `src/ui/recipients_tab.py` | Package history section |
| `src/services/event_service.py` | export_shopping_list_csv(), get_event_cost_analysis() |

## New Dependencies

None - uses existing Python stdlib for CSV export:
```python
import csv
from tkinter import filedialog
```

## Testing Strategy

1. **Unit tests** for new service methods
2. **Manual testing** for UI changes:
   - Tab order verification
   - Event selector functionality
   - Progress bar accuracy
   - CSV export file verification
   - Recipient history display

## Development Sequence

1. Service layer: Add CSV export and cost analysis methods
2. Main window: Reorder tabs, rename Dashboard to Summary
3. Production dashboard: Add event selector and progress section
4. Event detail: Add CSV export button, enhance summary
5. Recipients: Add package history section
6. Tests: Unit tests for new service methods

## Quick Reference

### Existing Methods to Use

```python
from src.services import event_service

# Progress tracking (Feature 016)
event_service.get_production_progress(event_id)
event_service.get_assembly_progress(event_id)
event_service.get_event_overall_progress(event_id)

# Shopping list
event_service.get_shopping_list(event_id)

# Recipient history
event_service.get_recipient_history(recipient_id)
```

### New Methods to Add

```python
# CSV export
event_service.export_shopping_list_csv(event_id, file_path)

# Cost analysis
event_service.get_event_cost_analysis(event_id)
```
