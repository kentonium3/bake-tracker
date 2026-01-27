# Research: Batch Calculation & User Decisions

**Feature**: F073
**Date**: 2026-01-27

## Research Questions Resolved

### Q1: What is the output structure of F072 `calculate_recipe_requirements()`?

**Finding**: Returns `Dict[Recipe, int]` - Recipe objects mapped to total quantities needed.

**Location**: `src/services/planning_service.py:34-59`

**Critical Issue Identified**: F072's recipe-level aggregation breaks when a recipe has multiple FinishedUnits with different yields (e.g., Large/Medium/Small Cake). Aggregating "5 large cakes + 10 small cakes = 15" loses the yield context needed for batch calculation.

**Resolution (included in F073 WP01)**:
- Change F072 return type from `Dict[Recipe, int]` to `List[FURequirement]`
- Rename function to `decompose_event_to_fu_requirements()`
- Preserve bundle decomposition logic, remove recipe-level aggregation
- Update all 22 F072 tests for new return type
- F073 batch calculation can then use F072 output directly

### Q2: What is the BatchDecision model structure?

**Finding**: Model exists from F068 with the following structure:

```python
class BatchDecision(BaseModel):
    event_id: FK to Event (CASCADE)
    recipe_id: FK to Recipe (RESTRICT)
    finished_unit_id: FK to FinishedUnit (SET NULL, nullable)
    batches: Integer (must be > 0)
    created_at, updated_at: timestamps

    # Constraint: UniqueConstraint("event_id", "recipe_id")
```

**Location**: `src/models/batch_decision.py`

**Issue Identified**: Current unique constraint on `(event_id, recipe_id)` prevents multiple batch decisions for the same recipe per event. This blocks the use case where Small Cake and Large Cake (same recipe, different yields) both need batch decisions.

**Decision**: Modify constraint to `(event_id, finished_unit_id)` and make `finished_unit_id` NOT NULL.

### Q3: How does FinishedUnit store yield information?

**Finding**: FinishedUnit has two yield modes:

```python
class YieldMode(enum.Enum):
    DISCRETE_COUNT = "discrete_count"  # Cookies, truffles
    BATCH_PORTION = "batch_portion"    # Cakes

class FinishedUnit:
    yield_mode: YieldMode
    items_per_batch: Integer  # For DISCRETE_COUNT
    batch_percentage: Decimal  # For BATCH_PORTION

    def calculate_batches_needed(self, quantity: int) -> float:
        # Already implemented!
```

**Location**: `src/models/finished_unit.py:42-178`

**Key Discovery**: `calculate_batches_needed()` method already exists! Returns float (raw division result). F073 needs floor/ceil options from this.

### Q4: What UI patterns exist for option selection?

**Finding**: Radio button pattern in `src/ui/forms/finished_good_form.py:182-209`:

```python
# StringVar for tracking selection
self.yield_mode_var = ctk.StringVar(value="discrete_count")

# Radio buttons with shared variable
discrete_radio = ctk.CTkRadioButton(
    parent,
    text="Option label",
    variable=self.yield_mode_var,
    value="option_value",
    command=lambda: self._on_change("option_value"),
)
```

### Q5: What confirmation dialog patterns exist?

**Finding**: Simple confirmation via `src/ui/widgets/dialogs.py`:

```python
def show_confirmation(title: str, message: str, parent=None) -> bool:
    return messagebox.askyesno(title, message, parent=parent)
```

### Q6: What CRUD patterns exist for planning data?

**Finding**: Pattern in `src/services/event_service.py`:

1. Validate parent entity exists
2. Validate FK references
3. Delete existing (for replace operations)
4. Insert new records
5. `session.flush()` before return
6. Raise `ValidationError` for business rule violations
7. Accept optional `session` parameter

## Technology Decisions

### Batch Calculation Algorithm

**Decision**: Use `math.floor()` and `math.ceil()` on `FinishedUnit.calculate_batches_needed()` result.

**Rationale**:
- Existing method handles both yield modes (discrete_count, batch_portion)
- Standard library functions, no dependencies
- Clear semantics for floor (may shortfall) vs ceil (meets/exceeds)

### Service Layer Organization

**Decision**: Create new `batch_decision_service.py` for CRUD operations.

**Alternatives Considered**:
- Add to `planning_service.py` - rejected because planning_service handles recipe decomposition (F072), different concern
- Add to `event_service.py` - rejected because event_service is already large

### Schema Change Approach

**Decision**: Modify BatchDecision via export/reset/import cycle per Constitution VI.

**Migration Steps**:
1. Export all data via import_export_service
2. Modify `batch_decision.py`:
   - Change `finished_unit_id` to NOT NULL
   - Update UniqueConstraint to `(event_id, finished_unit_id)`
3. Delete database, recreate with new schema
4. Transform export data (if any batch_decisions exist)
5. Import transformed data

**Note**: Since batch_decisions table is likely empty (F068 created schema but no UI uses it yet), migration is trivial.

## Existing Code to Reuse

| Component | Location | Reuse |
|-----------|----------|-------|
| `FinishedUnit.calculate_batches_needed()` | `models/finished_unit.py:158` | Core calculation |
| `CTkRadioButton` pattern | `ui/forms/finished_good_form.py:182` | Option selection UI |
| `show_confirmation()` | `ui/widgets/dialogs.py` | Shortfall warning |
| CRUD patterns | `services/event_service.py:3008+` | Batch decision persistence |
| `session_scope()` | `utils/database.py` | Transaction management |
| Status bar pattern | `ui/planning_tab.py:552` | User feedback |

## Open Questions (None)

All research questions resolved. Ready for Phase 1 design.
