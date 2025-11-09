---
work_package_id: "WP05"
subtasks: ["T054", "T055", "T056", "T057", "T058", "T059", "T060", "T061", "T062", "T063", "T064", "T065", "T066", "T067", "T068", "T069"]
title: "PurchaseService Implementation"
phase: "Phase 2 - Service Implementation"
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

# Work Package Prompt: WP05 – PurchaseService Implementation

## Objectives & Success Criteria

Implement complete PurchaseService with 8 functions including price trend analysis and alert detection.

**Success Criteria**:
- All purchase operations use Decimal for monetary values
- Price trend analysis uses statistics.linear_regression correctly
- Alert thresholds (20% warning, 40% critical) trigger appropriately
- Purchase history sorted by date descending (most recent first)
- Total cost auto-calculation accurate within $0.10 tolerance

## Context & Constraints

**Contract**: `kitty-specs/002-service-layer-for/contracts/purchase_service.md`
**Data Model**: `kitty-specs/002-service-layer-for/data-model.md` - Purchase entity
**Research**: `kitty-specs/002-service-layer-for/research.md` - Decimal precision decision

**Dependencies**: WP01 (infrastructure), WP03 (VariantService)

**Key Implementation Notes**:
- All monetary values: Decimal (never float)
- Auto-calculate total_cost = quantity * unit_cost if not provided
- Validate total_cost within $0.10 of calculation if provided (manual discount tracking)
- Linear regression requires ≥3 data points (return "insufficient_data" otherwise)

## Subtasks

### T054-T055: record_purchase()

**Tests**:
- Successful purchase recording
- Auto-calculation of total_cost
- Validation warning when provided total_cost differs from calculation
- ValidationError for quantity <= 0, unit_cost < 0
- VariantNotFound for invalid variant_id

**Implementation**:
```python
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any
from src.models import Purchase
from src.services import session_scope, ValidationError, VariantNotFound
from src.services.variant_service import get_variant

def record_purchase(
    variant_id: int,
    purchase_date: date,
    quantity: Decimal,
    unit: str,
    unit_cost: Decimal,
    total_cost: Optional[Decimal] = None,
    store: Optional[str] = None,
    notes: Optional[str] = None
) -> Purchase:
    """Record a purchase transaction for a variant."""
    # Validate variant exists
    variant = get_variant(variant_id)

    # Validate quantities
    if quantity <= 0:
        raise ValidationError("Quantity must be positive")
    if unit_cost < 0:
        raise ValidationError("Unit cost cannot be negative")

    # Auto-calculate or validate total_cost
    calculated_total = quantity * unit_cost
    if total_cost is None:
        total_cost = calculated_total
    elif abs(total_cost - calculated_total) > Decimal("0.10"):
        # Log warning: manual adjustment detected
        import logging
        logging.warning(f"Total cost {total_cost} differs from calculated {calculated_total}")

    with session_scope() as session:
        purchase = Purchase(
            variant_id=variant_id,
            purchase_date=purchase_date,
            quantity=quantity,
            unit=unit,
            unit_cost=unit_cost,
            total_cost=total_cost,
            store=store,
            notes=notes
        )
        session.add(purchase)
        session.flush()
        return purchase
```

### T056-T057: get_purchase()

**Tests**: Retrieval by ID, eager-loaded variant, PurchaseNotFound

**Implementation**: Standard get pattern with joinedload

### T058-T059: get_purchase_history()

**Tests**: Date range filtering, limit enforcement, descending order

**Implementation**:
```python
from typing import List

def get_purchase_history(
    variant_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: Optional[int] = None
) -> List[Purchase]:
    """Retrieve purchase history for variant, most recent first."""
    from src.services.variant_service import get_variant

    variant = get_variant(variant_id)  # Validate exists

    with session_scope() as session:
        q = session.query(Purchase).filter_by(variant_id=variant_id)

        if start_date:
            q = q.filter(Purchase.purchase_date >= start_date)
        if end_date:
            q = q.filter(Purchase.purchase_date <= end_date)

        q = q.order_by(Purchase.purchase_date.desc())

        if limit:
            q = q.limit(limit)

        return q.all()
```

### T060-T061: get_most_recent_purchase()

**Tests**: Returns latest purchase, None if no purchases

**Implementation**: Use get_purchase_history with limit=1

### T062-T063: calculate_average_price()

**Tests**: 60-day window, empty result, multiple purchases

**Implementation**:
```python
from datetime import timedelta
from statistics import mean

def calculate_average_price(variant_id: int, days: int = 60) -> Decimal:
    """Calculate average unit cost over specified time period."""
    from datetime import date as date_type

    cutoff_date = date_type.today() - timedelta(days=days)
    purchases = get_purchase_history(variant_id, start_date=cutoff_date)

    if not purchases:
        return Decimal("0.00")

    # Calculate mean of unit_cost values
    unit_costs = [float(p.unit_cost) for p in purchases]
    avg = mean(unit_costs)

    return Decimal(str(round(avg, 2)))
```

### T064-T065: detect_price_change()

**Tests**: Warning threshold (20-40%), Critical threshold (>40%), No alert (< 20%), Insufficient data

**Implementation**:
```python
def detect_price_change(
    variant_id: int,
    threshold_percent: Decimal = Decimal("20.0")
) -> Optional[Dict[str, Any]]:
    """Detect significant price changes compared to recent average."""
    recent = get_most_recent_purchase(variant_id)
    if not recent:
        return None

    avg_price = calculate_average_price(variant_id, days=60)
    if avg_price == Decimal("0.00"):
        return None

    current_price = recent.unit_cost
    change = ((current_price - avg_price) / avg_price) * 100

    if abs(change) < threshold_percent:
        return None

    # Determine alert level
    alert_level = "critical" if abs(change) > 40 else "warning"
    direction = "increase" if change > 0 else "decrease"

    return {
        "current_price": current_price,
        "average_price": avg_price,
        "change_percent": abs(change),
        "direction": direction,
        "alert_level": alert_level
    }
```

### T066-T067: get_price_trend()

**Tests**: Linear regression slope, insufficient data (<3 purchases), trend classification (increasing/decreasing/stable)

**Implementation**:
```python
from statistics import linear_regression, stdev

def get_price_trend(variant_id: int, months: int = 6) -> Dict[str, Any]:
    """Calculate price trend statistics over specified months."""
    from datetime import date as date_type, timedelta

    cutoff_date = date_type.today() - timedelta(days=months * 30)
    purchases = get_purchase_history(variant_id, start_date=cutoff_date)

    if len(purchases) < 3:
        return {
            "purchase_count": len(purchases),
            "min_price": Decimal("0.00"),
            "max_price": Decimal("0.00"),
            "avg_price": Decimal("0.00"),
            "std_dev": Decimal("0.00"),
            "trend": "insufficient_data",
            "trend_slope": Decimal("0.00")
        }

    # Sort by date ascending for regression
    sorted_purchases = sorted(purchases, key=lambda p: p.purchase_date)

    # Convert dates to days since first purchase
    first_date = sorted_purchases[0].purchase_date
    x_vals = [(p.purchase_date - first_date).days for p in sorted_purchases]
    y_vals = [float(p.unit_cost) for p in sorted_purchases]

    # Linear regression
    slope, intercept = linear_regression(x_vals, y_vals)

    # Statistics
    unit_costs = [float(p.unit_cost) for p in purchases]
    min_price = Decimal(str(round(min(unit_costs), 2)))
    max_price = Decimal(str(round(max(unit_costs), 2)))
    avg_price = Decimal(str(round(mean(unit_costs), 2)))
    std_deviation = Decimal(str(round(stdev(unit_costs), 3)))

    # Trend classification
    if abs(slope) < 0.01:
        trend = "stable"
    elif slope > 0:
        trend = "increasing"
    else:
        trend = "decreasing"

    return {
        "purchase_count": len(purchases),
        "min_price": min_price,
        "max_price": max_price,
        "avg_price": avg_price,
        "std_dev": std_deviation,
        "trend": trend,
        "trend_slope": Decimal(str(round(slope, 4)))
    }
```

### T068-T069: delete_purchase()

**Tests**: Successful deletion, PurchaseNotFound

**Implementation**: Standard delete pattern

## Test Strategy

**Test file**: `src/tests/test_purchase_service.py`

**Price Analysis Test Scenarios**:
```python
def test_calculate_average_price():
    """Test average price calculation over 60-day window."""
    # Create purchases: $0.76, $0.74, $0.80 within 60 days
    # Create purchase: $0.65 (65 days ago, excluded)
    # Assert average = ($0.76 + $0.74 + $0.80) / 3

def test_detect_price_change_warning():
    """Test warning alert at 25% increase."""
    # Create historical purchases: $0.75 average
    # Create new purchase: $0.95 (26.67% increase)
    # Assert alert_level="warning", direction="increase"

def test_get_price_trend_increasing():
    """Test linear regression detects increasing trend."""
    # Create 6 purchases with increasing prices
    # Assert trend="increasing", slope > 0
```

## Definition of Done Checklist

- [x] All 16 subtasks completed
- [x] `src/services/purchase_service.py` created with 8 functions
- [x] All monetary values use Decimal
- [x] Price trend analysis works correctly (≥3 data points)
- [x] Alert thresholds trigger appropriately
- [x] All tests pass with >70% coverage

## Activity Log

- 2025-11-09T03:08:51Z – system – lane=planned – Prompt created.
- 2025-11-09T08:02:39Z – Claude Code – lane=done – Work package completed. All tasks implemented and integration tests passing.

