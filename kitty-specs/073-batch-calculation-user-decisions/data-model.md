# Data Model: Batch Calculation & User Decisions

**Feature**: F073
**Date**: 2026-01-27

## F072 API Change (Prerequisite)

F072's current `calculate_recipe_requirements()` returns `Dict[Recipe, int]` which aggregates at the recipe level. This loses FU-level yield context needed when a recipe has multiple FUs with different yields (e.g., Large/Medium/Small Cake).

### Current F072 API (Broken for Mixed Yields)

```python
def calculate_recipe_requirements(event_id: int, session=None) -> Dict[Recipe, int]:
    """Returns recipe-level aggregation - LOSES FU yield context."""
```

**Problem example:**
- Event needs: 5 Large Cakes (yield 1/batch) + 10 Small Cakes (yield 4/batch)
- Current output: `{Cake Recipe: 15}` - meaningless, can't derive batch counts
- Required: 5 batches (large) + 3 batches (small) = 8 total batches

### New F072 API (FU-Level)

```python
@dataclass
class FURequirement:
    """Requirement for a single FinishedUnit from bundle decomposition."""
    finished_unit: FinishedUnit
    quantity_needed: int
    recipe: Recipe  # Convenience (same as finished_unit.recipe)

def decompose_event_to_fu_requirements(
    event_id: int,
    session: Session = None,
) -> List[FURequirement]:
    """
    Decompose event FG selections into FinishedUnit-level requirements.

    - Bundle decomposition still works (quantities multiply through nesting)
    - Returns FU-level data, not recipe-level aggregation
    - Preserves yield context for downstream batch calculation
    """
```

### F072 Changes Summary

| Aspect | Before | After |
|--------|--------|-------|
| Function name | `calculate_recipe_requirements()` | `decompose_event_to_fu_requirements()` |
| Return type | `Dict[Recipe, int]` | `List[FURequirement]` |
| Aggregation | By recipe (loses FU context) | None (FU-level preserved) |
| Tests impacted | 22 tests in test_planning_service.py | All need assertion updates |

---

## Schema Changes Required

### BatchDecision Model Modification

**Current Schema** (from F068):

```python
class BatchDecision(BaseModel):
    __tablename__ = "batch_decisions"

    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
    finished_unit_id = Column(Integer, ForeignKey("finished_units.id", ondelete="SET NULL"), nullable=True)  # NULLABLE
    batches = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", "recipe_id", name="uq_batch_decision_event_recipe"),  # RECIPE-BASED
        CheckConstraint("batches > 0", name="ck_batch_decision_batches_positive"),
    )
```

**Problem**: Unique constraint on `(event_id, recipe_id)` prevents:
- Small Cake (recipe=CakeRecipe, finished_unit=SmallCake): 3 batches
- Large Cake (recipe=CakeRecipe, finished_unit=LargeCake): 3 batches

Both have same `event_id` and `recipe_id` → constraint violation.

**New Schema**:

```python
class BatchDecision(BaseModel):
    __tablename__ = "batch_decisions"

    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
    finished_unit_id = Column(Integer, ForeignKey("finished_units.id", ondelete="CASCADE"), nullable=False)  # NOT NULL
    batches = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", "finished_unit_id", name="uq_batch_decision_event_fu"),  # FU-BASED
        CheckConstraint("batches > 0", name="ck_batch_decision_batches_positive"),
    )
```

**Changes**:
1. `finished_unit_id`: nullable=True → nullable=False
2. `finished_unit_id`: ondelete="SET NULL" → ondelete="CASCADE"
3. UniqueConstraint: `(event_id, recipe_id)` → `(event_id, finished_unit_id)`
4. Remove index on `recipe_id` (still useful but less critical)
5. Keep `recipe_id` column for convenience (denormalized from FU.recipe_id)

## Entity Relationships

```
Event (1) ──────────────── (N) EventFinishedGood
   │                              │
   │                              │ finished_good_id
   │                              ▼
   │                         FinishedUnit/FinishedGood
   │                              │
   │                              │ recipe_id
   │                              ▼
   │                           Recipe
   │                              ▲
   │                              │ recipe_id (denormalized)
   │                              │
   └──────────────────── (N) BatchDecision
                               │
                               │ finished_unit_id
                               ▼
                          FinishedUnit
```

## Data Transfer Objects

### BatchOption (calculation output)

```python
@dataclass
class BatchOption:
    """One batch option for user selection."""
    batches: int           # Number of batches
    total_yield: int       # batches × yield_per_batch
    quantity_needed: int   # From EventFinishedGood.quantity
    difference: int        # total_yield - quantity_needed
    is_shortfall: bool     # difference < 0
    is_exact_match: bool   # difference == 0
    yield_per_batch: int   # From FinishedUnit (for display)

@dataclass
class BatchOptionsResult:
    """Batch options for one FinishedUnit."""
    finished_unit_id: int
    finished_unit_name: str
    recipe_id: int
    recipe_name: str
    quantity_needed: int
    yield_per_batch: int
    yield_mode: str        # "discrete_count" or "batch_portion"
    item_unit: str         # "cookie", "cake", etc.
    options: List[BatchOption]
```

### BatchDecisionInput (save input)

```python
@dataclass
class BatchDecisionInput:
    """User's batch decision for one FU."""
    finished_unit_id: int
    batches: int
    confirmed_shortfall: bool = False  # True if user confirmed shortfall
```

## Service API

### Calculation Functions

```python
def calculate_batch_options(
    event_id: int,
    session: Session = None,
) -> List[BatchOptionsResult]:
    """
    Calculate batch options for all FUs in an event.

    Returns list of BatchOptionsResult, one per EventFinishedGood.
    Each contains floor/ceil options with shortfall flags.
    """

def calculate_batch_options_for_fu(
    finished_unit: FinishedUnit,
    quantity_needed: int,
) -> List[BatchOption]:
    """
    Calculate floor/ceil batch options for a single FU.

    Returns 1-2 options:
    - Floor option (may shortfall)
    - Ceil option (if different from floor)
    """
```

### CRUD Functions

```python
def save_batch_decision(
    event_id: int,
    decision: BatchDecisionInput,
    session: Session = None,
) -> BatchDecision:
    """
    Save or update a single batch decision.

    Validates:
    - Event exists
    - FinishedUnit exists and is in event's FG selections
    - Batches > 0
    - If shortfall, confirmed_shortfall must be True
    """

def save_all_batch_decisions(
    event_id: int,
    decisions: List[BatchDecisionInput],
    session: Session = None,
) -> int:
    """
    Replace all batch decisions for an event.

    Validates all FUs have decisions before committing.
    Returns count of decisions saved.
    """

def get_batch_decisions(
    event_id: int,
    session: Session = None,
) -> List[BatchDecision]:
    """Get all batch decisions for an event."""

def get_batch_decision(
    event_id: int,
    finished_unit_id: int,
    session: Session = None,
) -> Optional[BatchDecision]:
    """Get batch decision for a specific FU in an event."""

def delete_batch_decisions(
    event_id: int,
    session: Session = None,
) -> int:
    """Delete all batch decisions for an event. Returns count deleted."""
```

## Validation Rules

| Rule | Enforcement |
|------|-------------|
| batches > 0 | Database CHECK constraint |
| finished_unit_id NOT NULL | Database NOT NULL |
| One decision per FU per event | Database UNIQUE constraint |
| FU must be in event's FG selections | Service layer validation |
| Shortfall requires confirmation | Service layer validation |
| Event must exist | Service layer validation |

## Migration Notes

Per Constitution VI (Schema Change Strategy), migration is handled via export/reset/import:

1. **Check existing data**: Query `SELECT COUNT(*) FROM batch_decisions`
   - If 0: No migration needed, just update model
   - If >0: Export, transform, import

2. **Model update**: Modify `src/models/batch_decision.py` with new schema

3. **Database reset**: Delete `bake_tracker.db`, run app to recreate

4. **Data transformation** (if needed):
   ```python
   # For any existing batch_decisions without finished_unit_id:
   # - Look up recipe_id → find first FinishedUnit with that recipe
   # - Set finished_unit_id to that FU
   # - If multiple FUs exist, log warning for manual review
   ```

**Expected case**: batch_decisions table is empty (F068 created schema, no UI uses it yet), so transformation is unnecessary.
