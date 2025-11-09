# Service Contract: PurchaseService

**Module**: `src/services/purchase_service.py`
**Pattern**: Functional (module-level functions)
**Dependencies**: `src/models.Purchase`, `src/services.database.session_scope`, `src/services.exceptions`, `src/services.variant_service`, `decimal.Decimal`, `datetime`, `statistics`

## Function Signatures

### record_purchase

```python
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
    """
    Record a purchase transaction for a variant.

    Args:
        variant_id: ID of variant purchased
        purchase_date: Date of purchase
        quantity: Amount purchased
        unit: Unit of quantity (e.g., "lb", "bag", "box")
        unit_cost: Cost per unit
        total_cost: Total purchase cost (auto-calculated as quantity * unit_cost if not provided)
        store: Optional store name where purchased
        notes: Optional user notes

    Returns:
        Purchase: Created purchase record

    Raises:
        VariantNotFound: If variant_id doesn't exist
        ValidationError: If quantity <= 0, unit_cost < 0, or invalid date
        DatabaseError: If database operation fails

    Note:
        If total_cost not provided, auto-calculated as quantity * unit_cost.
        If provided, validated against calculation (warning if mismatch > $0.10 for manual discount tracking).

    Example:
        >>> from decimal import Decimal
        >>> from datetime import date
        >>> purchase = record_purchase(
        ...     variant_id=123,
        ...     purchase_date=date(2025, 11, 1),
        ...     quantity=Decimal("25.0"),
        ...     unit="lb",
        ...     unit_cost=Decimal("0.76"),
        ...     store="Costco"
        ... )
        >>> purchase.total_cost
        Decimal('19.00')
    """
```

---

### get_purchase

```python
def get_purchase(purchase_id: int) -> Purchase:
    """
    Retrieve purchase by ID.

    Args:
        purchase_id: Purchase identifier

    Returns:
        Purchase: Purchase object with variant relationship eager-loaded

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist

    Example:
        >>> purchase = get_purchase(456)
        >>> purchase.store
        'Costco'
        >>> purchase.variant.brand
        'King Arthur'
    """
```

---

### get_purchase_history

```python
def get_purchase_history(
    variant_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: Optional[int] = None
) -> List[Purchase]:
    """
    Retrieve purchase history for a variant, sorted by date descending (most recent first).

    Args:
        variant_id: Variant identifier
        start_date: Optional filter for purchases on or after this date
        end_date: Optional filter for purchases on or before this date
        limit: Optional maximum number of results

    Returns:
        List[Purchase]: Purchase records ordered by purchase_date DESC

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Example:
        >>> history = get_purchase_history(variant_id=123, limit=10)
        >>> [f"${p.total_cost} on {p.purchase_date}" for p in history]
        ['$19.00 on 2025-11-01', '$18.50 on 2025-10-15', '$19.99 on 2025-09-30']
    """
```

---

### get_most_recent_purchase

```python
def get_most_recent_purchase(variant_id: int) -> Optional[Purchase]:
    """
    Get the most recent purchase for a variant.

    Args:
        variant_id: Variant identifier

    Returns:
        Optional[Purchase]: Most recent purchase, or None if no purchases exist

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Example:
        >>> recent = get_most_recent_purchase(123)
        >>> recent.unit_cost if recent else Decimal("0.00")
        Decimal('0.76')
    """
```

---

### calculate_average_price

```python
def calculate_average_price(
    variant_id: int,
    days: int = 60
) -> Decimal:
    """
    Calculate average unit cost over specified time period.

    Args:
        variant_id: Variant identifier
        days: Number of days back from today to include in average (default 60)

    Returns:
        Decimal: Average unit_cost over time period, or Decimal("0.00") if no purchases

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Note:
        Only includes purchases within the specified time period (purchase_date >= today - days).
        Average calculated as mean of unit_cost values, NOT total_cost/total_quantity
        (because unit sizes may vary across purchases).

    Example:
        >>> avg = calculate_average_price(variant_id=123, days=90)
        >>> avg
        Decimal('0.73')  # Average of $0.76, $0.74, $0.80, $0.70, $0.69
    """
```

---

### detect_price_change

```python
def detect_price_change(
    variant_id: int,
    threshold_percent: Decimal = Decimal("20.0")
) -> Optional[Dict[str, Any]]:
    """
    Detect significant price changes compared to recent average.

    Args:
        variant_id: Variant identifier
        threshold_percent: Percentage change threshold (default 20.0%)

    Returns:
        Optional[Dict]: If price change detected, returns:
            {
                "current_price": Decimal,
                "average_price": Decimal,
                "change_percent": Decimal,
                "direction": str ("increase" or "decrease"),
                "alert_level": str ("warning" or "critical")
            }
        Returns None if no significant change or insufficient data.

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Note:
        Compares most recent purchase to 60-day average.
        Alert levels: "warning" (20-40%), "critical" (>40%)

    Example:
        >>> alert = detect_price_change(variant_id=123, threshold_percent=Decimal("20.0"))
        >>> alert
        {
            "current_price": Decimal("1.00"),
            "average_price": Decimal("0.75"),
            "change_percent": Decimal("33.33"),
            "direction": "increase",
            "alert_level": "warning"
        }
    """
```

---

### get_price_trend

```python
def get_price_trend(
    variant_id: int,
    months: int = 6
) -> Dict[str, Any]:
    """
    Calculate price trend statistics over specified months.

    Args:
        variant_id: Variant identifier
        months: Number of months back to analyze (default 6)

    Returns:
        Dict containing:
            - "purchase_count": int (number of purchases in period)
            - "min_price": Decimal (lowest unit_cost)
            - "max_price": Decimal (highest unit_cost)
            - "avg_price": Decimal (mean unit_cost)
            - "std_dev": Decimal (standard deviation of unit_cost)
            - "trend": str ("increasing", "decreasing", "stable", or "insufficient_data")
            - "trend_slope": Decimal (positive = increasing, negative = decreasing)

    Raises:
        VariantNotFound: If variant_id doesn't exist

    Note:
        Trend determined by simple linear regression on purchase dates vs. unit costs.
        "stable" if slope magnitude < 0.01 (less than 1 cent change per month).
        "insufficient_data" if fewer than 3 purchases in period.

    Example:
        >>> trend = get_price_trend(variant_id=123, months=12)
        >>> trend
        {
            "purchase_count": 8,
            "min_price": Decimal("0.69"),
            "max_price": Decimal("0.82"),
            "avg_price": Decimal("0.75"),
            "std_dev": Decimal("0.045"),
            "trend": "increasing",
            "trend_slope": Decimal("0.012")
        }
    """
```

---

### delete_purchase

```python
def delete_purchase(purchase_id: int) -> bool:
    """
    Delete purchase record.

    Args:
        purchase_id: Purchase identifier

    Returns:
        bool: True if deletion successful

    Raises:
        PurchaseNotFound: If purchase_id doesn't exist
        DatabaseError: If database operation fails

    Note:
        Purchase records are historical data. Deletion should be rare (data entry errors only).
        Consider soft-delete or archiving for audit trail purposes.

    Example:
        >>> delete_purchase(789)
        True
    """
```

---

## Exception Mapping

| Exception | HTTP Status (future) | User Message |
|-----------|---------------------|--------------|
| `PurchaseNotFound` | 404 Not Found | "Purchase with ID {id} not found" |
| `VariantNotFound` | 404 Not Found | "Variant with ID {id} not found" |
| `ValidationError` | 400 Bad Request | "Validation failed: {error_details}" |
| `DatabaseError` | 500 Internal Server Error | "Database operation failed" |

---

## Implementation Notes

### Price Calculation
```python
# Auto-calculate total_cost if not provided
if total_cost is None:
    total_cost = quantity * unit_cost

# Validate if provided (warn if mismatch for manual discount tracking)
elif abs(total_cost - (quantity * unit_cost)) > Decimal("0.10"):
    # Log warning: manual adjustment detected
    pass
```

### Average Price Calculation
```python
from statistics import mean

purchases = session.query(Purchase)\
    .filter(Purchase.variant_id == variant_id)\
    .filter(Purchase.purchase_date >= cutoff_date)\
    .all()

if not purchases:
    return Decimal("0.00")

return Decimal(str(mean([float(p.unit_cost) for p in purchases])))
```

### Trend Detection
```python
from statistics import linear_regression

# Get purchases sorted by date
purchases = [...ordered by purchase_date ASC...]

if len(purchases) < 3:
    return {"trend": "insufficient_data", ...}

# Convert dates to days since first purchase
x_vals = [(p.purchase_date - purchases[0].purchase_date).days for p in purchases]
y_vals = [float(p.unit_cost) for p in purchases]

slope, intercept = linear_regression(x_vals, y_vals)

if abs(slope) < 0.01:
    trend = "stable"
elif slope > 0:
    trend = "increasing"
else:
    trend = "decreasing"
```

---

## Validation Rules

### record_purchase
- `variant_id`: Must reference existing Variant
- `purchase_date`: Must be valid date (allow future dates for pre-orders)
- `quantity`: Must be > 0 (positive)
- `unit`: Must be valid unit from unit_converter.py
- `unit_cost`: Must be >= 0 (allow zero for free/donated items)
- `total_cost`: If provided, should be close to quantity * unit_cost (within $0.10)

### Price Calculation
- Use Decimal for all monetary calculations (no float)
- Round to 2 decimal places for currency display
- Preserve full precision in calculations

---

## Performance Considerations

- **Index on variant_id**: Foreign key provides this automatically
- **Index on purchase_date**: Critical for date range queries and trend analysis
- **Composite index on (variant_id, purchase_date DESC)**: Optimizes get_purchase_history() queries
- **Query optimization**: Use LIMIT clause for recent purchase queries
- **Caching**: Consider caching average prices (60-day window) with TTL=1 day
- **Batch operations**: If recording multiple purchases, use single transaction

---

## Statistical Analysis Notes

### Linear Regression for Trend
- Simple linear regression: y = mx + b where y=price, x=days
- Slope (m) indicates price change rate per day
- Positive slope = increasing prices, negative = decreasing
- Small slope (< 0.01) = stable prices

### Standard Deviation
- Measures price volatility
- High std_dev = volatile prices (shop around)
- Low std_dev = stable prices (consistent supplier)

### Alert Thresholds
- **Warning**: 20-40% price change
- **Critical**: >40% price change
- Based on percentage change from 60-day average

---

**Contract Status**: ✅ Defined - 8 functions with complete type signatures, price analysis algorithms documented
