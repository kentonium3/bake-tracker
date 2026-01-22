# Research: Service Session Consistency Hardening

**Feature**: 062-service-session-consistency-hardening
**Date**: 2026-01-22
**Status**: Complete (patterns already established)

## Research Summary

This feature requires minimal research because the session discipline patterns are already established in the codebase through F060/F061 and documented in CLAUDE.md.

## Prior Art Analysis

### Correct Session Pattern (Reference)

**File**: `src/services/batch_production_service.py`
**Function**: `record_batch_production()` (lines 212-469)

```python
def record_batch_production(
    recipe_id: int,
    finished_unit_id: int,
    num_batches: int,
    actual_yield: int,
    *,
    # ... other params
    session=None,  # Optional session parameter
) -> Dict[str, Any]:
    # Honor passed session per CLAUDE.md session management pattern
    cm = nullcontext(session) if session is not None else session_scope()
    with cm as session:
        # All database operations use provided session
        # No internal commits
        # Session threaded to downstream calls
```

**Key Pattern Elements**:
- Accept `session=None` parameter
- Use `nullcontext(session) if session else session_scope()` idiom
- Never commit internally
- Thread session to all downstream service calls

### Incorrect Pattern (Bug to Fix)

**File**: `src/services/batch_production_service.py`
**Function**: `get_production_history()` (lines 490-548)

```python
def get_production_history(
    *,
    # ... filter params
    session=None,  # Session parameter EXISTS but is IGNORED
) -> List[Dict[str, Any]]:
    with session_scope() as session:  # BUG: shadows the parameter!
        # Uses new session instead of provided one
```

**Issue**: Function accepts `session=None` but immediately shadows it with `with session_scope() as session:`, completely ignoring the caller's session.

### Same Bug Locations

| File | Function | Line | Issue |
|------|----------|------|-------|
| `batch_production_service.py` | `get_production_history` | 519 | Ignores session param |
| `batch_production_service.py` | `get_production_run` | 573 | Ignores session param |
| `assembly_service.py` | `get_assembly_history` | 599 | Ignores session param |
| `assembly_service.py` | `get_assembly_run` | 654 | Ignores session param |

## Event Service Gap Analysis

**File**: `src/services/event_service.py`

### Functions Without Session Parameter (~40+)

Based on grep analysis, these function categories need session parameters added:

**CRUD Operations**:
- `create_event`
- `get_event_by_id`
- `get_event_by_name`
- `get_all_events`
- `get_events_by_year`
- `get_available_years`
- `update_event`
- `delete_event`

**Assignment Operations**:
- `assign_package_to_recipient`
- `update_assignment`
- `remove_assignment`
- `get_event_assignments`
- `get_recipient_assignments_for_event`

**Calculation Operations**:
- `get_event_total_cost`
- `get_event_recipient_count`
- `get_event_package_count`
- `get_event_summary`
- `get_recipe_needs`

**Progress Operations**:
- `get_event_overall_progress`
- `get_events_with_progress`
- `get_event_cost_analysis`

**Target Operations**:
- `set_production_target`
- `set_assembly_target`
- `get_production_targets`
- `get_assembly_targets`
- `delete_production_target`
- `delete_assembly_target`

**Status Operations**:
- `update_fulfillment_status`
- `get_packages_by_status`

**Other**:
- `clone_event`
- `export_shopping_list_csv`
- `get_event_packaging_needs`
- `get_event_packaging_breakdown`
- `get_recipient_history`

### Functions WITH Session Parameter (Already Correct)

- `get_shopping_list` (line 946) - accepts `session=None`
- `get_production_progress` (line 1943) - accepts `session=None`
- `get_assembly_progress` (line 2030) - accepts `session=None`

## Production Service Gap

**File**: `src/services/production_service.py`

Functions needing session parameter:
- `get_production_records`
- `get_production_total`
- `can_assemble_package`
- `update_package_status`
- `get_production_progress`
- `get_dashboard_summary`
- `get_recipe_cost_breakdown`
- `get_event_assignments`

## Technical Decisions

### D1: Required vs Optional Session

**Decision**: Required (no default `session=None`)

**Rationale**:
- Desktop app = we control all callers
- Eliminates "should I pass session?" ambiguity
- Type system catches missing args at dev time
- Cleaner pattern than optional with nullcontext idiom

**Rejected Alternative**: Keep `session=None` with nullcontext
- Would maintain backward compatibility
- But perpetuates ambiguity about transaction ownership
- Spec explicitly requires "required sessions only"

### D2: UI Session Context Manager

**Decision**: Create utility in UI layer

**Pattern**:
```python
# In src/ui/utils/session_utils.py (or similar)
from contextlib import contextmanager
from src.services.database import session_scope

@contextmanager
def ui_session():
    """Session context manager for UI operations."""
    with session_scope() as session:
        yield session
        # Commit happens automatically on success
        # Rollback happens automatically on exception
```

**Usage in UI**:
```python
from src.ui.utils.session_utils import ui_session

def handle_save_click(self):
    with ui_session() as session:
        event_service.create_event(..., session=session)
        event_service.assign_package_to_recipient(..., session=session)
        # All operations in same transaction
```

### D3: DTO Cost Format

**Decision**: 2 decimal places, string representation

**Format**: `f"{cost:.2f}"` → `"12.34"`

**Conversion Location**: At DTO boundary in service layer (in `_to_dict` methods)

## No Further Research Required

All patterns are established. Implementation can proceed with task decomposition.

---

**Research Status**: COMPLETE
**Next Step**: `/spec-kitty.tasks` to generate work packages
