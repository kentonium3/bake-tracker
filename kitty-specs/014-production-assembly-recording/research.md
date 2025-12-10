# Research: Production & Assembly Recording UI

**Feature**: 014-production-assembly-recording
**Date**: 2025-12-10
**Status**: Complete

## Executive Summary

This research documents the existing UI patterns, service integration approaches, and architectural decisions needed to implement the Production & Assembly Recording UI feature. The codebase has well-established patterns that should be followed for consistency.

## Research Findings

### 1. Dialog Form Pattern

**Decision**: Use `CTkToplevel` modal dialog pattern matching existing forms
**Rationale**: All existing dialogs (FinishedUnitFormDialog, EventFormDialog, etc.) follow this pattern consistently
**Alternatives Considered**:
- Slide-out panels (rejected: not consistent with existing UI)
- Page navigation (rejected: user confirmed modal preference)

**Pattern Details**:
- Inherit from `ctk.CTkToplevel`
- Modal setup: `transient(parent)` + `wait_visibility()` + `grab_set()` + `focus_force()`
- Center positioning relative to parent window
- `self.result` holds return data (dict or None)
- `_initializing` flag prevents callbacks during construction
- Grid-based layout with `PADDING_MEDIUM` and `PADDING_LARGE` constants

**Source**: `src/ui/forms/finished_unit_form.py`, `src/ui/forms/event_form.py`

### 2. Service Integration Pattern

**Decision**: Use `UIServiceIntegrator.execute_service_operation()` for all service calls
**Rationale**: Provides consistent error handling, logging, and user feedback
**Alternatives Considered**:
- Direct service calls with try/catch (rejected: inconsistent error handling)
- Custom error handling per dialog (rejected: duplication)

**Pattern Details**:
```python
from src.ui.service_integration import get_ui_service_integrator, OperationType

result = self.service_integrator.execute_service_operation(
    operation_name="Record Production",
    operation_type=OperationType.CREATE,
    service_function=lambda: batch_production_service.record_batch_production(...),
    parent_widget=self,
    error_context="Recording batch production",
    show_success_dialog=True
)
```

**Source**: `src/ui/service_integration.py`, `src/ui/finished_units_tab.py`

### 3. Data Table Pattern for History

**Decision**: Create specialized `DataTable` subclasses for production and assembly history
**Rationale**: Existing pattern uses subclasses that override `_get_row_values()` for custom formatting
**Alternatives Considered**:
- Simple CTkFrame with labels (rejected: lacks scroll, selection, sorting)
- CTkTextbox (rejected: no row selection capability)

**Pattern Details**:
- Inherit from base `DataTable` class
- Override `_get_row_values(item)` to format display strings
- Columns defined as tuples: `[(column_name, pixel_width), ...]`
- Support single-click select, double-click for details

**Source**: `src/ui/widgets/data_table.py`

### 4. Availability Check Display

**Decision**: Check availability on dialog open + manual "Refresh" button
**Rationale**: User confirmed this preference; avoids real-time API calls during typing
**Alternatives Considered**:
- Real-time debounced updates (rejected by user)
- Only on button click (rejected: user wants initial check)

**Implementation Approach**:
- Call `check_can_produce()` or `check_can_assemble()` when dialog opens
- Display results in scrollable frame with color-coded rows
- Green (`COLOR_SUCCESS`) for sufficient, Red (`COLOR_ERROR`) for insufficient
- "Refresh Availability" button triggers re-check with current batch/quantity values

### 5. Production Tab Replacement

**Decision**: Create new implementation to replace existing `production_tab.py`
**Rationale**: User confirmed "deprecate old" approach; existing tab has different purpose (event-based)
**Alternatives Considered**:
- Refactor in place (rejected: different data model)
- Keep both (rejected: confusing duplication)

**Migration Strategy**:
1. Create new `ProductionDashboardTab` class
2. Update `main_window.py` to use new tab
3. Mark old `production_tab.py` as deprecated (keep for reference initially)
4. Remove deprecated file after verification

### 6. Detail View vs Form Dialog

**Decision**: Create separate detail dialog classes (not extend form dialogs)
**Rationale**: User confirmed separation; detail views have different purpose (view + actions) vs forms (CRUD)
**Alternatives Considered**:
- Extend form dialogs with view mode (rejected by user)
- Combine into single class (rejected by user)

**Classes to Create**:
- `FinishedUnitDetailDialog` - shows info, history, "Record Production" button
- `FinishedGoodDetailDialog` - shows info, composition, history, "Record Assembly" button
- `RecordProductionDialog` - availability check, batch input, yield adjust, confirm
- `RecordAssemblyDialog` - availability check, quantity input, confirm

### 7. Modernized Styling

**Decision**: Follow existing patterns but modernize styling
**Rationale**: User confirmed this approach
**Implementation**:
- Use consistent corner_radius (8px for frames, 6px for buttons)
- Use CTkFont for consistent typography
- Maintain color scheme from constants
- Improve spacing and visual hierarchy where possible

## Service API Summary

### BatchProductionService (Feature 013)

| Function | Purpose | Returns |
|----------|---------|---------|
| `check_can_produce(recipe_id, num_batches)` | Availability check | `{"can_produce": bool, "missing": [...]}` |
| `record_batch_production(recipe_id, finished_unit_id, num_batches, actual_yield, notes)` | Record production | `{"production_run_id": int, ...}` |
| `get_production_history(finished_unit_id, limit, include_consumptions)` | Query history | `List[Dict]` |

### AssemblyService (Feature 013)

| Function | Purpose | Returns |
|----------|---------|---------|
| `check_can_assemble(finished_good_id, quantity)` | Availability check | `{"can_assemble": bool, "missing": [...]}` |
| `record_assembly(finished_good_id, quantity, notes)` | Record assembly | `{"assembly_run_id": int, ...}` |
| `get_assembly_history(finished_good_id, limit, include_consumptions)` | Query history | `List[Dict]` |

## Open Questions

None - all critical decisions resolved during planning interrogation.

## Risks

1. **Existing production_tab.py coupling**: May have external references that need updating
   - Mitigation: Search codebase for imports before deprecation

2. **Service API changes**: Feature 013 services are dependencies
   - Mitigation: Feature 013 is complete and stable; verify API compatibility

3. **UI consistency**: Modernized styling must not clash with existing UI
   - Mitigation: Incremental changes, review with user
