# Quickstart: Batch Calculation & User Decisions

**Feature**: F073
**Date**: 2026-01-27

## Prerequisites

- F068 Event Management complete (provides BatchDecision model)
- F072 Recipe Decomposition complete (will be modified in WP01)
- Existing EventFinishedGood records for test event

## Implementation Order

### Phase 0: F072 API Fix (WP01 - Critical Foundation)

F072's current API returns `Dict[Recipe, int]` which loses FU-level yield context. This must be fixed before batch calculation can work correctly.

**File**: `src/services/planning_service.py`

1. Add `FURequirement` dataclass:
   ```python
   @dataclass
   class FURequirement:
       finished_unit: FinishedUnit
       quantity_needed: int
       recipe: Recipe
   ```

2. Rename `calculate_recipe_requirements()` → `decompose_event_to_fu_requirements()`

3. Change return type from `Dict[Recipe, int]` to `List[FURequirement]`

4. Modify `_decompose_fg_to_recipes()` → `_decompose_fg_to_fus()`:
   - Instead of aggregating by recipe at the end
   - Return list of FURequirements preserving FU identity

**File**: `src/tests/test_planning_service.py`

5. Update all 22 tests to use new return type:
   - Change assertions from dict-based to list-based
   - Verify FU identity is preserved (not just recipe)

**Test**: All 22 existing F072 tests pass with new assertions.

### Phase 1: Schema Modification

**File**: `src/models/batch_decision.py`

1. Change `finished_unit_id` to `nullable=False`
2. Change `ondelete="SET NULL"` to `ondelete="CASCADE"`
3. Update UniqueConstraint from `(event_id, recipe_id)` to `(event_id, finished_unit_id)`
4. Update constraint name to `uq_batch_decision_event_fu`

**Test**: Create fresh database, verify constraint works.

### Phase 2: Service Layer - Calculation

**File**: `src/services/planning_service.py` (add functions)

```python
import math
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class BatchOption:
    batches: int
    total_yield: int
    quantity_needed: int
    difference: int
    is_shortfall: bool
    is_exact_match: bool
    yield_per_batch: int

def calculate_batch_options_for_fu(
    finished_unit: FinishedUnit,
    quantity_needed: int,
) -> List[BatchOption]:
    """Calculate floor/ceil batch options for a single FU."""
    if quantity_needed <= 0:
        return []

    # Use existing method
    raw_batches = finished_unit.calculate_batches_needed(quantity_needed)

    if raw_batches <= 0:
        return []

    yield_per_batch = finished_unit.items_per_batch or 1
    if finished_unit.yield_mode == YieldMode.BATCH_PORTION:
        yield_per_batch = 1  # One batch = one portion

    options = []

    # Floor option
    floor_batches = math.floor(raw_batches)
    if floor_batches > 0:
        floor_yield = floor_batches * yield_per_batch
        floor_diff = floor_yield - quantity_needed
        options.append(BatchOption(
            batches=floor_batches,
            total_yield=floor_yield,
            quantity_needed=quantity_needed,
            difference=floor_diff,
            is_shortfall=floor_diff < 0,
            is_exact_match=floor_diff == 0,
            yield_per_batch=yield_per_batch,
        ))

    # Ceil option (if different)
    ceil_batches = math.ceil(raw_batches)
    if ceil_batches != floor_batches:
        ceil_yield = ceil_batches * yield_per_batch
        ceil_diff = ceil_yield - quantity_needed
        options.append(BatchOption(
            batches=ceil_batches,
            total_yield=ceil_yield,
            quantity_needed=quantity_needed,
            difference=ceil_diff,
            is_shortfall=False,  # Ceil never shortfalls
            is_exact_match=ceil_diff == 0,
            yield_per_batch=yield_per_batch,
        ))

    return options
```

**Test**: Unit tests for various scenarios (exact match, shortfall, multiple options).

### Phase 3: Service Layer - CRUD

**File**: `src/services/batch_decision_service.py` (new file)

Follow patterns from `event_service.py`:
- Accept optional `session` parameter
- Validate parent entities exist
- Use `session.flush()` before return
- Raise `ValidationError` for business rules

Key functions:
- `save_batch_decision(event_id, decision, session=None)`
- `get_batch_decisions(event_id, session=None)`
- `delete_batch_decisions(event_id, session=None)`

**Test**: CRUD operations with various scenarios.

### Phase 4: UI - Batch Options Widget

**File**: `src/ui/widgets/batch_options_frame.py` (new file)

```python
class BatchOptionsFrame(ctk.CTkFrame):
    """Widget for displaying and selecting batch options."""

    def __init__(
        self,
        parent,
        on_selection_change: Callable[[int, int], None],  # (fu_id, batches)
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self._selection_callback = on_selection_change
        self._option_vars = {}  # fu_id -> StringVar
        self._options_data = {}  # fu_id -> List[BatchOption]

    def populate(self, options_results: List[BatchOptionsResult]):
        """Display batch options for all FUs."""
        # Clear existing
        for widget in self.winfo_children():
            widget.destroy()

        for result in options_results:
            self._create_fu_section(result)

    def _create_fu_section(self, result: BatchOptionsResult):
        """Create section for one FU with radio options."""
        # Frame for this FU
        fu_frame = ctk.CTkFrame(self)
        fu_frame.pack(fill="x", padx=10, pady=5)

        # Header: FU name + quantity needed
        header = ctk.CTkLabel(
            fu_frame,
            text=f"{result.finished_unit_name} (need {result.quantity_needed})",
            font=ctk.CTkFont(weight="bold"),
        )
        header.pack(anchor="w", padx=10, pady=5)

        # Radio buttons for options
        var = ctk.StringVar(value="")
        self._option_vars[result.finished_unit_id] = var
        self._options_data[result.finished_unit_id] = result.options

        for option in result.options:
            text = self._format_option_text(option, result.item_unit)
            radio = ctk.CTkRadioButton(
                fu_frame,
                text=text,
                variable=var,
                value=str(option.batches),
                command=lambda fuid=result.finished_unit_id: self._on_option_selected(fuid),
            )
            radio.pack(anchor="w", padx=20, pady=2)

    def _format_option_text(self, option: BatchOption, unit: str) -> str:
        """Format option for display."""
        diff_text = ""
        if option.is_exact_match:
            diff_text = "(exact match!)"
        elif option.is_shortfall:
            diff_text = f"({abs(option.difference)} short - SHORTFALL)"
        else:
            diff_text = f"({option.difference} extra)"

        return f"{option.batches} batches = {option.total_yield} {unit} {diff_text}"
```

### Phase 5: UI - Integration

**File**: `src/ui/planning_tab.py` (modify)

1. Add BatchOptionsFrame to planning tab layout
2. Load batch options when event is selected
3. Handle selection changes
4. Show shortfall confirmation dialog
5. Save batch decisions

### Phase 6: Integration Testing

- End-to-end flow: Select FGs → Calculate options → Select options → Save
- Shortfall confirmation flow
- Load existing decisions on event open
- Modify decisions after initial save

## Key Patterns to Follow

### Session Management

```python
def my_function(event_id: int, session: Session = None):
    if session is not None:
        return _my_function_impl(event_id, session)
    with session_scope() as session:
        return _my_function_impl(event_id, session)
```

### Validation

```python
from src.utils.errors import ValidationError

def validate_stuff(thing):
    if not thing:
        raise ValidationError(["Thing is required"])
```

### Confirmation Dialog

```python
from src.ui.widgets.dialogs import show_confirmation

if option.is_shortfall:
    if not show_confirmation(
        "Shortfall Warning",
        f"This will produce {option.total_yield} but you need {option.quantity_needed}. "
        f"You'll be {abs(option.difference)} short. Confirm?",
        parent=self,
    ):
        return  # User cancelled
```

## Test Data Setup

```python
# Create test event with FG selections
event = Event(name="Holiday 2026", event_date=date(2026, 12, 25))
session.add(event)

# Create recipe with FU
recipe = Recipe(name="Sugar Cookies", slug="sugar-cookies")
session.add(recipe)

fu = FinishedUnit(
    slug="sugar-cookies-standard",
    display_name="Sugar Cookies",
    recipe=recipe,
    yield_mode=YieldMode.DISCRETE_COUNT,
    items_per_batch=24,
    item_unit="cookie",
)
session.add(fu)

# Add FG to event
efg = EventFinishedGood(event=event, finished_good=fu, quantity=100)
session.add(efg)

session.commit()

# Now test batch calculation
options = calculate_batch_options(event.id)
# Expected: floor=4 batches (96 cookies, 4 short), ceil=5 batches (120 cookies, 20 extra)
```

## Definition of Done

- [ ] F072 API changed to return `List[FURequirement]` (FU-level, not recipe-level)
- [ ] All 22 F072 tests updated and passing with new return type
- [ ] BatchDecision schema change applied and tested
- [ ] Batch calculation service functions with >70% test coverage
- [ ] CRUD functions for batch decisions with tests
- [ ] UI widget displays options correctly
- [ ] Shortfall confirmation dialog works
- [ ] Decisions persist and load correctly
- [ ] Integration with planning_tab.py complete
- [ ] All tests pass
