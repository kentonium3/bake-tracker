# Implementation Plan: Inventory Gap Analysis

**Branch**: `075-inventory-gap-analysis` | **Date**: 2026-01-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/075-inventory-gap-analysis/spec.md`
**Depends On**: F074 (Ingredient Aggregation)

## Summary

Create an inventory gap analysis service that compares F074's aggregated ingredient totals against current inventory levels to generate a shopping list. The service calculates gaps (needed - on_hand) for each ingredient and categorizes results into "purchase required" and "sufficient" lists.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, existing F074 service, existing inventory_item_service
**Storage**: SQLite (existing database)
**Testing**: pytest with >70% service coverage
**Target Platform**: Desktop (CustomTkinter)
**Project Type**: Single project (existing structure)
**Performance Goals**: Process 100 ingredients in under 2 seconds
**Constraints**: Must follow session management pattern, read-only service (no DB writes)
**Scale/Scope**: Single user, single event at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Direct user value - turns ingredient needs into actionable shopping list |
| II. Data Integrity | ✅ PASS | Read-only service, no data modification |
| III. Future-Proof Schema | ✅ PASS | No schema changes required |
| IV. Test-Driven Development | ✅ PASS | Will include unit tests for service layer |
| V. Layered Architecture | ✅ PASS | Service layer only, UI integration via existing patterns |
| VI. Schema Change Strategy | ✅ N/A | No schema changes |
| VII. Pragmatic Aspiration | ✅ PASS | Supports web migration (stateless service) |

**Phase-Specific Checks (Desktop Phase):**
- Does this design block web deployment? → NO (stateless service, API-ready)
- Is the service layer UI-independent? → YES (pure calculation service)
- Does this support AI-assisted JSON import? → YES (structured output)
- What's the web migration cost? → LOW (service becomes API endpoint)

## Project Structure

### Documentation (this feature)

```
kitty-specs/075-inventory-gap-analysis/
├── plan.md              # This file
├── spec.md              # Feature specification
├── checklists/          # Quality checklists
│   └── requirements.md
└── tasks/               # Work package prompts (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/              # No changes required
├── services/
│   ├── ingredient_aggregation_service.py  # F074 (dependency)
│   ├── inventory_item_service.py          # Existing (query inventory)
│   ├── ingredient_service.py              # Existing (get_ingredient by slug)
│   └── inventory_gap_service.py           # NEW - gap analysis service
└── ui/
    └── planning_tab.py  # Existing - add shopping list display

src/tests/
└── test_inventory_gap_service.py          # NEW - unit tests
```

**Structure Decision**: Follows existing single-project layout. New service file added to `src/services/`, new test file added to `src/tests/`.

## Design Decisions

### D1: Service Architecture

**Decision**: Create `inventory_gap_service.py` as a pure calculation service following existing patterns.

**Rationale**:
- Matches existing service patterns (session=None parameter)
- Read-only service (no database writes)
- Consumes F074 output directly
- Clean separation of concerns

### D2: Data Structures

**Decision**: Create dataclasses for structured output:

```python
@dataclass
class GapItem:
    ingredient_id: int
    ingredient_name: str
    unit: str
    quantity_needed: float
    quantity_on_hand: float
    gap: float  # max(0, needed - on_hand)

@dataclass
class GapAnalysisResult:
    purchase_items: List[GapItem]   # gap > 0
    sufficient_items: List[GapItem]  # gap == 0
```

**Rationale**: Dataclasses match F074's pattern, provide type safety, and enable clean UI binding.

### D3: Inventory Lookup Strategy

**Decision**: Query inventory by ingredient_id through Product relationship.

**Challenge**: F074 outputs `ingredient_id`, but `get_total_quantity()` expects `ingredient_slug`.

**Solution**: For each ingredient in F074 output:
1. Query Ingredient model by ID to get slug
2. Call `get_total_quantity(slug)` to get inventory by unit
3. Match units between F074 output and inventory

**Alternative Considered**: Add `get_total_quantity_by_id()` function - rejected to avoid modifying existing service.

### D4: Unit Matching

**Decision**: Exact unit string matching only (no automatic conversion).

**Rationale**:
- Matches spec FR-006 requirement
- Consistent with F074's approach (different units stay separate)
- Avoids complexity of unit conversion

**Implication**: If F074 shows "2 cups flour" but inventory is tracked in "lb", they won't match. This is intentional - user must ensure consistency.

### D5: Missing Inventory Handling

**Decision**: Treat missing inventory as zero quantity.

**Rationale**:
- Matches spec FR-002 requirement
- Common case for new or seasonal ingredients
- Graceful degradation (no errors)

## Integration Points

### Input: F074 Ingredient Aggregation

```python
from src.services.ingredient_aggregation_service import (
    aggregate_ingredients_for_event,
    IngredientTotal,
)

# Returns: Dict[(ingredient_id, unit), IngredientTotal]
totals = aggregate_ingredients_for_event(event_id, session=session)
```

### Query: Inventory Item Service

```python
from src.services.inventory_item_service import get_total_quantity

# Returns: Dict[str, Decimal] - quantities by unit
inventory = get_total_quantity(ingredient_slug)
# Example: {"cups": Decimal("2.5"), "lb": Decimal("5.0")}
```

### Query: Ingredient Service

```python
from src.services.ingredient_service import get_ingredient

# Get ingredient by ID to access slug
ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
slug = ingredient.slug
```

## API Design

### Public Function

```python
def analyze_inventory_gaps(
    event_id: int,
    session: Session = None,
) -> GapAnalysisResult:
    """
    Analyze inventory gaps for an event's ingredient needs.

    Takes F074's aggregated ingredient totals, queries current inventory,
    and calculates gaps (needed - on_hand) for each ingredient.

    Args:
        event_id: Event to analyze
        session: Optional session for transaction sharing

    Returns:
        GapAnalysisResult with purchase_items and sufficient_items lists

    Raises:
        ValidationError: If event not found
    """
```

### Internal Flow

1. Call `aggregate_ingredients_for_event(event_id, session)` to get totals
2. For each `(ingredient_id, unit)` in totals:
   a. Query Ingredient by ID to get slug
   b. Call `get_total_quantity(slug)` to get inventory
   c. Look up quantity for matching unit (default 0 if missing)
   d. Calculate gap = max(0, needed - on_hand)
   e. Create GapItem with all fields
3. Partition GapItems into purchase_items (gap > 0) and sufficient_items (gap == 0)
4. Return GapAnalysisResult

## Test Strategy

### Unit Tests (test_inventory_gap_service.py)

1. **test_gap_calculation_shortfall** - 6 needed, 2 on hand = 4 gap
2. **test_gap_calculation_sufficient** - 3 needed, 5 on hand = 0 gap
3. **test_missing_inventory_treated_as_zero** - no inventory record = full amount is gap
4. **test_all_items_categorized** - every input appears in exactly one output list
5. **test_empty_event_returns_empty** - no batch decisions = empty result
6. **test_mixed_results** - some sufficient, some need purchase
7. **test_unit_mismatch_treated_as_zero** - cups needed but only lb in inventory

### Test Fixtures

- Reuse F074's test fixtures (Event, Recipe, Ingredient, etc.)
- Add InventoryItem fixtures for inventory levels
- Mock `get_total_quantity` where needed for isolation

## Complexity Tracking

*No constitution violations requiring justification.*

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Unit mismatch between recipe and inventory | Medium | Medium | Document in UI; user responsible for consistency |
| Performance with many ingredients | Low | Low | Already tested F074 with 10 recipes; inventory query is O(1) |
| Session detachment in nested calls | Medium | High | Follow session=None pattern; pass session through all calls |

## Phase 0: Research

**No research needed** - all technical decisions resolved through codebase analysis:

- F074 output structure confirmed (IngredientTotal dataclass)
- Inventory service interface confirmed (get_total_quantity by slug)
- Ingredient model has slug field confirmed
- Session management pattern understood

## Phase 1: Design Artifacts

### data-model.md

Not needed - no new database entities. Using existing models (Ingredient, InventoryItem, Product).

### contracts/

Not needed - internal service, not an API.

### quickstart.md

Not needed - simple service with single public function.

---

## Next Steps

Run `/spec-kitty.tasks` to generate work packages for implementation.

**Estimated Work Packages**:
- WP01: Service foundation (dataclasses, skeleton)
- WP02: Gap calculation logic with tests
- WP03: UI integration (optional, may be separate feature)
