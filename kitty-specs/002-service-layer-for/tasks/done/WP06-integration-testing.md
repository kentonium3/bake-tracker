---
work_package_id: "WP06"
subtasks: ["T070", "T071", "T072", "T073", "T074", "T075"]
title: "Integration Testing & Documentation"
phase: "Phase 3 - Validation & Polish"
lane: "done"
assignee: "Claude Code"
agent: "Claude Code"
shell_pid: ""
history:
  - timestamp: "2025-11-09T03:08:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-11-09T07:58:47Z"
    lane: "done"
    agent: "Claude Code"
    shell_pid: ""
    action: "Work package completed - all tasks implemented and integration tests passing"
---

# Work Package Prompt: WP06 – Integration Testing & Documentation

## Objectives & Success Criteria

Validate cross-service workflows and ensure comprehensive documentation for service layer.

**Success Criteria**:
- Integration tests pass for multi-service workflows
- All spec.md success criteria validated (SC-001 through SC-015)
- Documentation complete with API reference and usage examples
- Test coverage across all services exceeds 70% (per spec SC-002)
- FIFO ordering verified in integration scenarios (per spec SC-004)

## Context & Constraints

**Supporting Specs**:
- `kitty-specs/002-service-layer-for/spec.md` - Success criteria (15 items)
- `kitty-specs/002-service-layer-for/contracts/` - All service contracts for documentation

**Dependencies**: All services (WP02, WP03, WP04, WP05) must be complete

**Integration Test Strategy**:
- Use real database (not mocks) to test multi-service interactions
- Test realistic user workflows (ingredient → variant → pantry → consumption)
- Test edge cases (insufficient inventory, price volatility, expiration)

## Subtasks

### T070 – Integration test: Ingredient → Variant → Pantry flow

**Purpose**: Validate end-to-end inventory management workflow.

**Test file**: `src/tests/integration/test_inventory_flow.py`

**Test scenario**:
```python
def test_complete_inventory_workflow():
    """Test: Create ingredient → Create variant → Add to pantry → Query inventory."""

    # 1. Create ingredient
    ingredient_data = {
        "name": "All-Purpose Flour",
        "category": "Flour",
        "recipe_unit": "cup",
        "density_g_per_ml": 0.507
    }
    ingredient = ingredient_service.create_ingredient(ingredient_data)
    assert ingredient.slug == "all_purpose_flour"

    # 2. Create variant
    variant_data = {
        "brand": "King Arthur",
        "package_size": "25 lb bag",
        "purchase_unit": "lb",
        "purchase_quantity": Decimal("25.0"),
        "preferred": True
    }
    variant = variant_service.create_variant(ingredient.slug, variant_data)
    assert variant.preferred is True

    # 3. Add to pantry
    from datetime import date, timedelta
    pantry_item = pantry_service.add_to_pantry(
        variant_id=variant.id,
        quantity=Decimal("25.0"),
        unit="lb",
        purchase_date=date.today(),
        expiration_date=date.today() + timedelta(days=365),
        location="Main Pantry"
    )
    assert pantry_item.quantity == Decimal("25.0")

    # 4. Query total inventory
    total = pantry_service.get_total_quantity(ingredient.slug)
    assert total == Decimal("100.0")  # 25 lb = 100 cups at 4 cups/lb

    # 5. Get preferred variant
    preferred = variant_service.get_preferred_variant(ingredient.slug)
    assert preferred.id == variant.id
```

**Parallel**: Yes (can proceed alongside T071, T072)

---

### T071 – Integration test: Purchase → Price analysis flow

**Purpose**: Validate purchase recording and price trend detection.

**Test file**: `src/tests/integration/test_purchase_flow.py`

**Test scenario**:
```python
def test_purchase_and_price_analysis():
    """Test: Record purchases → Calculate averages → Detect price changes."""

    # Setup: Create ingredient and variant
    # (use fixtures from test_inventory_flow)

    # 1. Record historical purchases
    from datetime import date, timedelta
    purchases = []
    base_date = date.today() - timedelta(days=90)

    for i in range(6):
        purchase = purchase_service.record_purchase(
            variant_id=variant.id,
            purchase_date=base_date + timedelta(days=i * 15),
            quantity=Decimal("25.0"),
            unit="lb",
            unit_cost=Decimal(f"0.{70 + i*2}")  # $0.70, $0.72, $0.74, ...
        )
        purchases.append(purchase)

    # 2. Calculate average price
    avg_price = purchase_service.calculate_average_price(variant.id, days=60)
    assert Decimal("0.70") <= avg_price <= Decimal("0.80")

    # 3. Record new purchase with significant price increase
    new_purchase = purchase_service.record_purchase(
        variant_id=variant.id,
        purchase_date=date.today(),
        quantity=Decimal("25.0"),
        unit="lb",
        unit_cost=Decimal("1.00")  # ~35% increase
    )

    # 4. Detect price change alert
    alert = purchase_service.detect_price_change(variant.id, threshold_percent=Decimal("20.0"))
    assert alert is not None
    assert alert["alert_level"] == "warning"
    assert alert["direction"] == "increase"

    # 5. Get price trend
    trend = purchase_service.get_price_trend(variant.id, months=6)
    assert trend["trend"] == "increasing"
    assert trend["purchase_count"] >= 6
```

**Parallel**: Yes

---

### T072 – Integration test: FIFO consumption scenarios

**Purpose**: Validate FIFO algorithm with complex real-world scenarios.

**Test file**: `src/tests/integration/test_fifo_scenarios.py`

**Test scenarios**:
```python
def test_fifo_multiple_lots_partial_consumption():
    """Test: Multiple lots → Partial consumption → Verify oldest consumed first."""

    # Setup: Create ingredient, variant
    # Add lot 1: 10.0 lb on 2025-01-01
    # Add lot 2: 15.0 lb on 2025-01-15
    # Add lot 3: 20.0 lb on 2025-02-01

    # Consume 12.0 lb (should deplete lot 1, partially consume lot 2)
    result = pantry_service.consume_fifo(ingredient.slug, Decimal("12.0"))

    assert result["consumed"] == Decimal("12.0")
    assert result["satisfied"] is True
    assert result["shortfall"] == Decimal("0.0")

    # Verify breakdown
    assert len(result["breakdown"]) == 2
    assert result["breakdown"][0]["lot_date"] == date(2025, 1, 1)  # Oldest first
    assert result["breakdown"][0]["remaining_in_lot"] == Decimal("0.0")  # Fully consumed
    assert result["breakdown"][1]["lot_date"] == date(2025, 1, 15)
    assert result["breakdown"][1]["remaining_in_lot"] == Decimal("13.0")  # Partial

def test_fifo_insufficient_inventory():
    """Test: Consume more than available → Verify shortfall calculation."""
    # Add lot: 10.0 lb
    # Consume 15.0 lb
    result = pantry_service.consume_fifo(ingredient.slug, Decimal("15.0"))

    assert result["consumed"] == Decimal("10.0")
    assert result["satisfied"] is False
    assert result["shortfall"] == Decimal("5.0")

def test_fifo_with_expiring_items():
    """Test: Expiring items consumed first (if FIFO by expiration implemented)."""
    # Future enhancement: Add expiration_date ordering to FIFO
```

**Parallel**: Yes

---

### T073 – Update service layer documentation

**Purpose**: Create comprehensive API reference for all services.

**Files**:
- Create: `docs/services/README.md`
- Create: `docs/services/api-reference.md`

**Content for README.md**:
```markdown
# Service Layer Documentation

## Architecture

The Bake Tracker service layer implements business logic using functional patterns:

- **Stateless functions**: No service classes, explicit parameters
- **Transaction management**: `session_scope()` context manager
- **Separation of concerns**: Services don't import UI code
- **Type safety**: Full type hints using Python 3.10+ syntax

## Services

### IngredientService
Manages generic ingredient catalog (flour, sugar, etc.)
- [API Reference](api-reference.md#ingredientservice)

### VariantService
Manages brand-specific product variants (King Arthur flour, Bob's Red Mill, etc.)
- [API Reference](api-reference.md#variantservice)

### PantryService
Manages inventory tracking with FIFO consumption
- [API Reference](api-reference.md#pantryservice)

### PurchaseService
Tracks purchase history and price trends
- [API Reference](api-reference.md#purchaseservice)

## Usage Patterns

See [examples.md](examples.md) for common usage patterns.
```

**Parallel**: Yes

---

### T074 – Create usage examples

**Purpose**: Provide copy-paste examples for common service operations.

**File**: `docs/services/examples.md`

**Example content**:
```markdown
# Service Layer Examples

## Creating an Ingredient and Variant

\`\`\`python
from src.services import ingredient_service, variant_service
from decimal import Decimal

# Create ingredient
ingredient_data = {
    "name": "All-Purpose Flour",
    "category": "Flour",
    "recipe_unit": "cup",
    "density_g_per_ml": 0.507
}
ingredient = ingredient_service.create_ingredient(ingredient_data)

# Create variant
variant_data = {
    "brand": "King Arthur",
    "package_size": "25 lb bag",
    "purchase_unit": "lb",
    "purchase_quantity": Decimal("25.0"),
    "preferred": True
}
variant = variant_service.create_variant(ingredient.slug, variant_data)
\`\`\`

## FIFO Inventory Consumption

\`\`\`python
from src.services import pantry_service

# Consume 12.0 cups of flour
result = pantry_service.consume_fifo("all_purpose_flour", Decimal("12.0"))

if result["satisfied"]:
    print(f"Consumed {result['consumed']} cups from {len(result['breakdown'])} lots")
else:
    print(f"Insufficient inventory: {result['shortfall']} cups short")
\`\`\`

## Price Alert Detection

\`\`\`python
from src.services import purchase_service

alert = purchase_service.detect_price_change(variant_id=123)

if alert:
    print(f"{alert['alert_level'].upper()}: Price {alert['direction']} by {alert['change_percent']:.1f}%")
\`\`\`
```

**Parallel**: Yes

---

### T075 – Validate all success criteria

**Purpose**: Systematically verify all 15 success criteria from spec.md are met.

**Checklist** (per spec.md):
- [x] **SC-001**: Service functions importable without errors
- [x] **SC-002**: Test coverage >70% (run `pytest --cov=src/services`)
- [x] **SC-003**: Slug generation handles Unicode correctly (test with "Jalapeño")
- [x] **SC-004**: FIFO ordering correct in 100% of test cases
- [x] **SC-005**: Preferred variant toggle works atomically
- [x] **SC-006**: Ingredient deletion blocked when variants exist
- [x] **SC-007**: Variant deletion blocked when pantry items/purchases exist
- [x] **SC-008**: All monetary calculations use Decimal (no floats)
- [x] **SC-009**: Price trend analysis requires ≥3 data points
- [x] **SC-010**: Pantry shortfall calculations accurate to 0.001
- [x] **SC-011**: session_scope() commits on success, rollbacks on error
- [x] **SC-012**: All service functions have type hints and docstrings
- [x] **SC-013**: No circular import issues (test: `python -m src.services`)
- [x] **SC-014**: Unit conversion integrated in pantry operations
- [x] **SC-015**: Purchase history sorted by date descending

**Validation script**: Create `src/tests/test_success_criteria.py` with automated checks

**Parallel**: No - depends on all other tasks completing

## Test Strategy

**Integration test execution**:
```bash
# Run all integration tests
pytest src/tests/integration/ -v

# Run with coverage
pytest src/tests/ -v --cov=src/services --cov-report=term-missing

# Verify coverage threshold
pytest src/tests/ --cov=src/services --cov-fail-under=70
```

**Expected results**:
- All integration tests pass
- Coverage >70%
- No import errors
- All success criteria validated

## Definition of Done Checklist

- [x] All 6 subtasks completed
- [x] Integration tests pass for all workflows
- [x] Documentation complete (README, API reference, examples)
- [x] All 15 success criteria validated
- [x] Test coverage >70% across all services
- [x] No outstanding bugs or edge cases

## Review Guidance

**Acceptance checkpoints**:
1. Integration tests demonstrate realistic workflows
2. Documentation is clear and copy-paste friendly
3. Success criteria validation is comprehensive
4. Code is production-ready (no TODO comments remaining)

## Activity Log

- 2025-11-09T03:08:51Z – system – lane=planned – Prompt created.
- 2025-11-09T08:02:39Z – Claude Code – lane=done – Work package completed. All tasks implemented and integration tests passing.

