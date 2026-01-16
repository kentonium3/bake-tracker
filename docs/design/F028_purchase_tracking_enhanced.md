# Feature 028: Purchase Tracking & Enhanced Costing

**Created:** 2025-12-22  
**Status:** DESIGN  
**Priority:** HIGH  
**Complexity:** MEDIUM

---

## Important Note on Specification Approach

**This document contains detailed technical illustrations** including code samples, schema definitions, service method signatures, and UI mockups. These are provided as **examples and guidance**, not as prescriptive implementations.

**When using spec-kitty to implement this feature:**
- The code samples are **illustrative** - they show one possible approach
- Spec-kitty should **validate and rationalize** the technical approach during its planning phase
- Spec-kitty may **modify or replace** these examples based on:
  - Current codebase patterns and conventions
  - Better architectural approaches discovered during analysis
  - Constitution compliance verification
  - Test-driven development requirements

**The requirements and business logic are the source of truth** - the technical implementation details should be determined by spec-kitty's specification and planning phases.

---

## Problem Statement

Current inventory management lacks purchase transaction tracking, preventing accurate cost analysis and price history:

**Current State Issues:**
1. **No purchase history:** Cannot answer "What did I pay for chocolate chips last time?"
2. **No supplier tracking:** Cannot determine "Do I usually buy this at Costco or Wegmans?"
3. **Static price data:** InventoryAddition.price_paid is snapshot with no context (when, where, market conditions)
4. **FIFO accuracy limited:** Cost calculations use addition price, not purchase transaction context
5. **Price volatility invisible:** Tariff impacts ($300 → $600 chocolate example) not tracked over time

**User Impact:**
- Cannot make informed purchasing decisions based on price history
- Cannot optimize supplier selection (e.g., "Costco is cheaper for bulk chocolate")
- Cannot analyze cost trends for budgeting
- Cannot validate data entry (is $600 reasonable or data entry error?)
- User testing blocked: realistic price population requires purchase context

**Real-World Example:**
> Marianne buys chocolate chips at Costco in January ($300), June ($450), December ($600). Current system treats each as isolated addition. Cannot see: price trend, supplier consistency, or whether December price is market change vs data error.

---

## Solution Overview

Implement Purchase entity as first-class transaction record linking products to suppliers with temporal pricing context.

**Core Architecture:**
```
Shopping Trip → Purchase Record → Inventory Addition(s)
(real world)    (transaction)     (storage event)

Example:
"Bought 5 bags of chocolate chips at Costco on 2024-12-22 for $600/bag"
↓
Purchase(product=ChocChips, supplier=Costco, date=2024-12-22, price=$600, qty=5)
↓
InventoryAddition(ingredient=Chocolate, product=ChocChips, purchase_id=X, qty=5)
```

**Key Design Principle:** One Purchase per product per shopping transaction. Current implementation: Purchase.quantity = InventoryAddition.quantity (1:1 relationship). Future: Multiple additions can reference same purchase (bulk buying workflow).

**Feature 028 Focus:** Data model and basic queries. Workflow intelligence (smart defaults, session memory, UI enhancements) deferred to Feature 029.

---

## Scope

### In Scope

**Schema Changes:**
- Purchase table (product_id, supplier_id, purchase_date, unit_price, quantity_purchased, notes)
- InventoryAddition.purchase_id FK (replaces price_paid field)
- Supplier table (already created in Feature 027)

**Service Layer:**
- New `purchase_service.py` with CRUD operations
- Purchase history queries (by product, supplier, date range)
- Price suggestion queries (last paid at supplier, fallback to any supplier)
- Update `inventory_service.add_inventory()` to create Purchase records
- Update FIFO cost calculation to use Purchase.unit_price

**UI Changes (Minimal):**
- Add "Supplier" dropdown to existing Add Inventory dialog
- Price field becomes pre-filled (editable) based on purchase history
- Price hint text: "(last paid: $X.XX on DATE at SUPPLIER)"
- Supplier required field (no default selection)

**Business Rules:**
- Every InventoryAddition MUST reference a Purchase (FK constraint)
- Purchase.quantity_purchased = InventoryAddition.quantity (1:1 for now)
- Purchase.purchase_date defaults to today (date picker for override - future)
- Price suggestion: Try supplier-specific first, fallback to any supplier, else blank
- Allow $0.00 prices (donations, free samples) with validation warning

**Migration:**
- One Purchase per existing InventoryAddition
- purchase_date = addition.addition_date
- supplier_id = 1 ("Unknown Supplier" from F027 migration)
- unit_price = addition.price_paid
- quantity_purchased = addition.quantity

### Out of Scope

**Deferred to Feature 029 (Workflow Intelligence):**
- Session-based supplier memory ("last used: Costco")
- Enhanced ingredient-first workflow with type-ahead
- Product recency ranking in dropdowns
- Inline product creation during inventory addition
- Price variance alerts ($300 → $600 warning)
- Bulk purchase entry ("I bought 5 bags at once")
- Smart supplier defaults (preferred supplier auto-selection)

**Future Features:**
- Purchase editing/deletion (immutable for now)
- Purchase bulk import from CSV
- Receipt scanning/OCR integration
- Supplier performance analytics (average price, frequency)
- Price trend visualization (charts, forecasting)
- Multi-supplier price comparison dashboard

---

## Technical Design

### Schema Changes

#### Purchase Table (New)

```python
class Purchase(Base):
    """
    Purchase transaction record linking product to supplier with temporal pricing.
    
    Represents a single product purchased from a supplier on a specific date.
    Every inventory addition must reference a purchase for FIFO cost accuracy.
    
    Design: One Purchase per product per shopping transaction.
    Current: Purchase.quantity = InventoryAddition.quantity (1:1)
    Future: Multiple InventoryAdditions can reference same Purchase (bulk buying)
    
    Example:
        Buy 5 bags chocolate chips at Costco on 2024-12-22 for $600/bag
        → Purchase(product=ChocChips, supplier=Costco, date=2024-12-22, 
                    unit_price=600, quantity_purchased=5)
        → InventoryAddition(purchase_id=X, quantity=5, addition_date=2024-12-22)
    
    Attributes:
        product_id: Foreign key to Product purchased
        supplier_id: Foreign key to Supplier (store/vendor)
        purchase_date: Date of purchase transaction
        unit_price: Price per package unit (e.g., $600 per 10kg bag)
        quantity_purchased: Number of package units purchased
        notes: Optional transaction notes (sale info, coupon codes, etc.)
    """
    
    __tablename__ = 'purchases'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    
    # Foreign keys
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Purchase transaction data
    purchase_date = Column(Date, nullable=False, index=True)
    unit_price = Column(Numeric(10, 4), nullable=False)
    quantity_purchased = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Timestamps (immutable after creation)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="purchases")
    supplier = relationship("Supplier", back_populates="purchases")
    inventory_additions = relationship("InventoryAddition", back_populates="purchase")
    
    # Constraints and indexes
    __table_args__ = (
        # Composite index for FIFO queries (product + date)
        Index("idx_purchase_product_date", "product_id", "purchase_date"),
        
        # Constraints
        CheckConstraint("unit_price >= 0", name="ck_purchase_unit_price_non_negative"),
        CheckConstraint("quantity_purchased > 0", name="ck_purchase_quantity_positive"),
    )
    
    def __repr__(self) -> str:
        """String representation of purchase."""
        return (
            f"Purchase(id={self.id}, "
            f"product_id={self.product_id}, "
            f"supplier_id={self.supplier_id}, "
            f"date={self.purchase_date}, "
            f"price=${self.unit_price}, "
            f"qty={self.quantity_purchased})"
        )
    
    @property
    def total_cost(self) -> Decimal:
        """Total cost of this purchase transaction."""
        return self.unit_price * self.quantity_purchased
    
    @property
    def unit_price_display(self) -> str:
        """Formatted unit price for display."""
        return f"${self.unit_price:.2f}"
```

**Design Rationale:**

1. **Immutable Transaction Record:** No updated_at timestamp. Purchases are historical facts.
2. **RESTRICT on Delete:** Cannot delete product/supplier if purchases exist (preserve history)
3. **Composite Index:** (product_id, purchase_date) enables efficient FIFO and price history queries
4. **Non-Negative Price:** Allow $0.00 for donations/samples, prevent negative (data error)
5. **Positive Quantity:** Must purchase at least 1 unit
6. **Notes Optional:** Transaction metadata (sale details, coupon codes) not always relevant

#### InventoryAddition Updates

```python
class InventoryAddition(Base):
    """
    InventoryAddition model (EXISTING - showing changes only).
    
    REMOVED FIELD:
    - price_paid: Deprecated; cost now derived from Purchase.unit_price
    
    NEW FIELD:
    - purchase_id: Foreign key to Purchase (REQUIRED after migration)
    
    NEW RELATIONSHIP:
    - purchase: Many-to-one relationship with Purchase
    """
    
    __tablename__ = 'inventory_additions'
    
    # ... existing fields ...
    
    # REMOVED: price_paid = Column(Numeric(10, 4), nullable=True)
    
    # NEW FIELD
    purchase_id = Column(
        Integer,
        ForeignKey("purchases.id", ondelete="RESTRICT"),
        nullable=False,  # After migration complete
        index=True
    )
    
    # NEW RELATIONSHIP
    purchase = relationship("Purchase", back_populates="inventory_additions")
    
    # UPDATED INDEXES
    __table_args__ = (
        # ... existing indexes ...
        Index("idx_inventory_addition_purchase", "purchase_id"),
    )
```

**Migration Note:** During migration, purchase_id temporarily nullable. After Purchase records created, make NOT NULL and drop price_paid column.

### Service Layer

#### New purchase_service.py

```python
"""
Purchase transaction management service.

Handles creation and querying of purchase records for inventory cost tracking
and price history analysis.
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_

from src.models import Purchase, Product, Supplier
from src.database import session_scope


class PurchaseNotFoundError(Exception):
    """Raised when purchase lookup fails."""
    pass


def create_purchase(
    product_id: int,
    supplier_id: int,
    purchase_date: date,
    unit_price: Decimal,
    quantity_purchased: int,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Purchase:
    """
    Create a new purchase transaction record.
    
    Args:
        product_id: Product purchased
        supplier_id: Supplier where purchased
        purchase_date: Date of purchase
        unit_price: Price per package unit
        quantity_purchased: Number of package units
        notes: Optional transaction notes
        session: Optional database session
        
    Returns:
        Created Purchase instance
        
    Raises:
        ValueError: If product/supplier doesn't exist or values invalid
    """
    if session is not None:
        return _create_purchase_impl(
            product_id, supplier_id, purchase_date, unit_price,
            quantity_purchased, notes, session
        )
    
    with session_scope() as session:
        return _create_purchase_impl(
            product_id, supplier_id, purchase_date, unit_price,
            quantity_purchased, notes, session
        )


def _create_purchase_impl(
    product_id: int,
    supplier_id: int,
    purchase_date: date,
    unit_price: Decimal,
    quantity_purchased: int,
    notes: Optional[str],
    session: Session
) -> Purchase:
    """Implementation using provided session."""
    
    # Validate product exists
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        raise ValueError(f"Product with id {product_id} not found")
    
    # Validate supplier exists
    supplier = session.query(Supplier).filter_by(id=supplier_id).first()
    if not supplier:
        raise ValueError(f"Supplier with id {supplier_id} not found")
    
    # Validate values
    if unit_price < 0:
        raise ValueError(f"Unit price cannot be negative: {unit_price}")
    
    if quantity_purchased <= 0:
        raise ValueError(f"Quantity must be positive: {quantity_purchased}")
    
    # Create purchase
    purchase = Purchase(
        product_id=product_id,
        supplier_id=supplier_id,
        purchase_date=purchase_date,
        unit_price=unit_price,
        quantity_purchased=quantity_purchased,
        notes=notes
    )
    
    session.add(purchase)
    session.flush()
    
    return purchase


def get_purchase(
    purchase_id: int,
    session: Optional[Session] = None
) -> Purchase:
    """
    Retrieve a purchase by ID.
    
    Args:
        purchase_id: Purchase ID to retrieve
        session: Optional database session
        
    Returns:
        Purchase instance
        
    Raises:
        PurchaseNotFoundError: If purchase doesn't exist
    """
    if session is not None:
        return _get_purchase_impl(purchase_id, session)
    
    with session_scope() as session:
        return _get_purchase_impl(purchase_id, session)


def _get_purchase_impl(purchase_id: int, session: Session) -> Purchase:
    """Implementation using provided session."""
    
    purchase = session.query(Purchase).filter_by(id=purchase_id).first()
    
    if not purchase:
        raise PurchaseNotFoundError(f"Purchase with id {purchase_id} not found")
    
    return purchase


def get_purchase_history(
    product_id: int,
    supplier_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: Optional[int] = None,
    session: Optional[Session] = None
) -> List[Purchase]:
    """
    Get purchase history for a product with optional filters.
    
    Results sorted by purchase_date DESC (most recent first).
    
    Args:
        product_id: Product to query
        supplier_id: Optional filter by supplier
        start_date: Optional filter by start date (inclusive)
        end_date: Optional filter by end date (inclusive)
        limit: Optional max results
        session: Optional database session
        
    Returns:
        List of Purchase instances sorted by date descending
    """
    if session is not None:
        return _get_purchase_history_impl(
            product_id, supplier_id, start_date, end_date, limit, session
        )
    
    with session_scope() as session:
        return _get_purchase_history_impl(
            product_id, supplier_id, start_date, end_date, limit, session
        )


def _get_purchase_history_impl(
    product_id: int,
    supplier_id: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
    limit: Optional[int],
    session: Session
) -> List[Purchase]:
    """Implementation using provided session."""
    
    query = session.query(Purchase).filter_by(product_id=product_id)
    
    # Apply filters
    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)
    
    if start_date:
        query = query.filter(Purchase.purchase_date >= start_date)
    
    if end_date:
        query = query.filter(Purchase.purchase_date <= end_date)
    
    # Sort by date descending (most recent first)
    query = query.order_by(desc(Purchase.purchase_date))
    
    # Apply limit
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_last_purchase_price(
    product_id: int,
    supplier_id: int,
    session: Optional[Session] = None
) -> Optional[Decimal]:
    """
    Get the most recent purchase price for product at specific supplier.
    
    Args:
        product_id: Product to query
        supplier_id: Supplier to filter by
        session: Optional database session
        
    Returns:
        Most recent unit_price at supplier, or None if no history
    """
    if session is not None:
        return _get_last_purchase_price_impl(product_id, supplier_id, session)
    
    with session_scope() as session:
        return _get_last_purchase_price_impl(product_id, supplier_id, session)


def _get_last_purchase_price_impl(
    product_id: int,
    supplier_id: int,
    session: Session
) -> Optional[Decimal]:
    """Implementation using provided session."""
    
    query = session.query(Purchase.unit_price).filter(
        and_(
            Purchase.product_id == product_id,
            Purchase.supplier_id == supplier_id
        )
    ).order_by(desc(Purchase.purchase_date)).limit(1)
    
    result = query.first()
    
    return result[0] if result else None


def get_last_purchase_price_any_supplier(
    product_id: int,
    session: Optional[Session] = None
) -> Optional[Dict[str, Any]]:
    """
    Get most recent purchase price from any supplier (fallback query).
    
    Used when no purchase history exists at selected supplier.
    Returns full context to display helpful hint to user.
    
    Args:
        product_id: Product to query
        session: Optional database session
        
    Returns:
        Dict with keys: 'price', 'supplier_name', 'supplier_city', 
        'supplier_state', 'purchase_date'
        Returns None if no purchase history at all
    """
    if session is not None:
        return _get_last_purchase_price_any_supplier_impl(product_id, session)
    
    with session_scope() as session:
        return _get_last_purchase_price_any_supplier_impl(product_id, session)


def _get_last_purchase_price_any_supplier_impl(
    product_id: int,
    session: Session
) -> Optional[Dict[str, Any]]:
    """Implementation using provided session."""
    
    query = session.query(
        Purchase.unit_price,
        Supplier.name,
        Supplier.city,
        Supplier.state,
        Purchase.purchase_date
    ).join(Supplier).filter(
        Purchase.product_id == product_id
    ).order_by(desc(Purchase.purchase_date)).limit(1)
    
    result = query.first()
    
    if result:
        return {
            'price': result[0],
            'supplier_name': result[1],
            'supplier_city': result[2],
            'supplier_state': result[3],
            'purchase_date': result[4]
        }
    
    return None


def get_recent_purchases(
    product_id: int,
    limit: int = 5,
    session: Optional[Session] = None
) -> List[Purchase]:
    """
    Get most recent purchases for a product (for tooltips, history display).
    
    Args:
        product_id: Product to query
        limit: Max number of purchases to return (default 5)
        session: Optional database session
        
    Returns:
        List of recent Purchase instances sorted by date descending
    """
    return get_purchase_history(
        product_id=product_id,
        limit=limit,
        session=session
    )
```

#### Updated inventory_service.py

```python
"""
Inventory management service (EXISTING - showing changes only).

Modified to create Purchase records when adding inventory.
"""

from src.services import purchase_service


def add_inventory(
    ingredient_id: int,
    product_id: int,
    supplier_id: int,  # NEW - REQUIRED
    quantity: int,
    unit_price: Decimal,  # RENAMED from price_paid
    purchase_date: Optional[date] = None,  # NEW - defaults to today
    notes: Optional[str] = None,
    event_id: Optional[int] = None,
    session: Optional[Session] = None
) -> InventoryAddition:
    """
    Add inventory with automatic purchase record creation.
    
    Creates two records atomically:
    1. Purchase record (product, supplier, date, price, quantity)
    2. InventoryAddition record (ingredient, product, purchase_id, quantity)
    
    Args:
        ingredient_id: Ingredient being added
        product_id: Product being added
        supplier_id: Supplier where purchased (REQUIRED)
        quantity: Number of package units
        unit_price: Price per package unit
        purchase_date: Date of purchase (defaults to today)
        notes: Optional notes (stored on InventoryAddition, not Purchase)
        event_id: Optional event association
        session: Optional database session
        
    Returns:
        Created InventoryAddition with linked Purchase
        
    Raises:
        ProductNotFoundError: If product doesn't exist
        SupplierNotFoundError: If supplier doesn't exist
        ValueError: If quantity or unit_price invalid
    """
    if session is not None:
        return _add_inventory_impl(
            ingredient_id, product_id, supplier_id, quantity, unit_price,
            purchase_date, notes, event_id, session
        )
    
    with session_scope() as session:
        return _add_inventory_impl(
            ingredient_id, product_id, supplier_id, quantity, unit_price,
            purchase_date, notes, event_id, session
        )


def _add_inventory_impl(
    ingredient_id: int,
    product_id: int,
    supplier_id: int,
    quantity: int,
    unit_price: Decimal,
    purchase_date: Optional[date],
    notes: Optional[str],
    event_id: Optional[int],
    session: Session
) -> InventoryAddition:
    """Implementation using provided session."""
    
    # Validate ingredient exists (existing logic)
    ingredient = session.query(Ingredient).filter_by(id=ingredient_id).first()
    if not ingredient:
        raise IngredientNotFoundError(ingredient_id)
    
    # Validate product exists (existing logic)
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        raise ProductNotFoundError(product_id)
    
    # Default purchase_date to today if not provided (NEW)
    if purchase_date is None:
        purchase_date = date.today()
    
    # Create Purchase record (NEW)
    purchase = purchase_service.create_purchase(
        product_id=product_id,
        supplier_id=supplier_id,
        purchase_date=purchase_date,
        unit_price=unit_price,
        quantity_purchased=quantity,
        notes=None,  # Purchase notes left NULL for now
        session=session
    )
    
    # Create InventoryAddition (MODIFIED - link to purchase)
    addition = InventoryAddition(
        ingredient_id=ingredient_id,
        product_id=product_id,
        purchase_id=purchase.id,  # NEW - link to Purchase
        quantity=quantity,
        addition_date=purchase_date,  # Match purchase date
        event_id=event_id,
        notes=notes  # Notes stored on addition, not purchase
    )
    
    session.add(addition)
    session.flush()
    
    return addition
```

**Key Changes:**
1. New required parameter: `supplier_id`
2. Renamed parameter: `price_paid` → `unit_price` (clarity)
3. New optional parameter: `purchase_date` (defaults to today)
4. Creates Purchase before InventoryAddition
5. Links InventoryAddition.purchase_id to created Purchase
6. Removed: Direct assignment of price_paid to InventoryAddition

#### FIFO Cost Calculation Updates

```python
"""
Batch production service (EXISTING - showing FIFO changes only).

Modified to get cost from Purchase.unit_price instead of InventoryAddition.price_paid.
"""

def _perform_fifo_consumption(recipe_id: int, num_batches: int, session: Session):
    """
    Perform FIFO consumption of ingredients with cost calculation.
    
    MODIFIED in Feature 028: Get cost from Purchase.unit_price via 
    InventoryAddition.purchase relationship.
    """
    
    recipe = session.query(Recipe).get(recipe_id)
    consumption_results = []
    
    for composition in recipe.compositions:
        # Calculate required quantity (unchanged)
        required_quantity = composition.quantity * num_batches
        
        # Get oldest inventory additions (unchanged)
        additions = session.query(InventoryAddition).filter_by(
            ingredient_id=composition.ingredient_id
        ).order_by(InventoryAddition.addition_date.asc()).all()
        
        # Consume from oldest first (FIFO)
        remaining_needed = required_quantity
        total_cost = Decimal('0.0000')
        
        for addition in additions:
            if remaining_needed <= 0:
                break
            
            # MODIFIED: Get cost from Purchase instead of addition.price_paid
            purchase = session.query(Purchase).get(addition.purchase_id)
            if not purchase:
                raise ValueError(f"InventoryAddition {addition.id} missing Purchase link")
            
            cost_per_unit = purchase.unit_price  # ← CHANGED from addition.price_paid
            
            # Consume logic (unchanged)
            consume_quantity = min(remaining_needed, addition.quantity)
            addition.quantity -= consume_quantity
            remaining_needed -= consume_quantity
            
            # Cost calculation (unchanged except source)
            total_cost += cost_per_unit * consume_quantity
        
        # Record consumption (unchanged)
        consumption_results.append({
            'ingredient_slug': composition.ingredient.slug,
            'quantity_consumed': required_quantity - remaining_needed,
            'unit': composition.unit,
            'total_cost': total_cost
        })
    
    return consumption_results
```

**Key Change:** Single line modification - get unit price from `Purchase.unit_price` instead of `InventoryAddition.price_paid`.

**Risk Assessment:** Very low. Purchase always exists (FK constraint enforced), query pattern identical.

---

## UI Changes

### Current Add Inventory Dialog

```
┌─────────────────────────────────────────────────┐
│ Add Inventory Item                              │
├─────────────────────────────────────────────────┤
│ Ingredient: [All-Purpose Flour           ▼]    │
│                                                  │
│ Product:    [Gold Medal AP Flour 10lb    ▼]    │
│                                                  │
│ Quantity:   [2]                                 │
│                                                  │
│ Price Paid: [$8.99]                             │
│                                                  │
│ Notes:      [_____________________________]     │
│                                                  │
│                         [Cancel]  [Add]         │
└─────────────────────────────────────────────────┘
```

### Feature 028 Modified Dialog

```
┌─────────────────────────────────────────────────┐
│ Add Inventory Item                              │
├─────────────────────────────────────────────────┤
│ Ingredient: [All-Purpose Flour           ▼]    │
│                                                  │
│ Product:    [Gold Medal AP Flour 10lb    ▼]    │
│                                                  │
│ Supplier:   [Costco Waltham MA           ▼]    │ ← NEW
│                                                  │
│ Price:      [$8.99]                             │ ← MODIFIED
│             (last paid: $8.50 on 2024-11-15)   │ ← NEW HINT
│                                                  │
│ Quantity:   [2]                                 │
│                                                  │
│ Notes:      [_____________________________]     │
│                                                  │
│                         [Cancel]  [Add]         │
└─────────────────────────────────────────────────┘
```

### Dialog Behavior

**On Dialog Open:**
1. Load suppliers: `supplier_service.list_suppliers()` → populate Supplier dropdown
2. Supplier dropdown alphabetically sorted (name, city, state)
3. No supplier pre-selected (user must choose)

**On Product Selected:**
- Nothing happens yet (wait for supplier selection)

**On Supplier Selected:**
1. Query last purchase price: `get_last_purchase_price(product_id, supplier_id)`
2. If found:
   - Pre-fill Price field with returned value
   - Show hint: "(last paid: $X.XX on YYYY-MM-DD)"
3. If not found at this supplier:
   - Query fallback: `get_last_purchase_price_any_supplier(product_id)`
   - If found:
     - Pre-fill Price field
     - Show hint: "(last paid: $X.XX at [Supplier] on YYYY-MM-DD)"
   - If not found at all:
     - Leave Price blank
     - Show hint: "(no purchase history)"

**On Price Changed (Manual Entry):**
- Allow user to override suggested price
- Remove hint text (user's entered value is intentional)
- Validate: Warn if $0.00 ("⚠️ Price is zero. Confirm?")
- Validate: Error if negative ("Price cannot be negative")

**On Add Clicked:**
1. Validate all fields populated
2. Call `inventory_service.add_inventory()` with supplier_id
3. Service creates Purchase, then InventoryAddition
4. Close dialog
5. Refresh inventory grid

### Implementation Notes

```python
class AddInventoryDialog(ctk.CTkToplevel):
    """
    Dialog for adding inventory items (EXISTING - showing changes only).
    """
    
    def __init__(self, master, service_integrator, **kwargs):
        super().__init__(master, **kwargs)
        # ... existing init ...
        
        # NEW: Supplier dropdown
        self.supplier_label = ctk.CTkLabel(self, text="Supplier:")
        self.supplier_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)
        
        self.supplier_var = ctk.StringVar()
        self.supplier_combo = ctk.CTkComboBox(
            self,
            variable=self.supplier_var,
            command=self._on_supplier_changed,
            state="readonly"
        )
        self.supplier_combo.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        
        # Load suppliers
        self._load_suppliers()
        
        # MODIFIED: Price field (now editable with hint)
        self.price_label = ctk.CTkLabel(self, text="Price:")
        self.price_label.grid(row=3, column=0, sticky="w", padx=10, pady=5)
        
        self.price_entry = ctk.CTkEntry(self)
        self.price_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=5)
        
        # NEW: Price hint label
        self.price_hint_label = ctk.CTkLabel(
            self,
            text="",
            font=("", 10),
            text_color="gray"
        )
        self.price_hint_label.grid(row=4, column=1, sticky="w", padx=10)
        
        # ... rest of existing fields ...
    
    def _load_suppliers(self):
        """Load suppliers into dropdown."""
        suppliers = self.service_integrator.execute_operation(
            operation_type=OperationType.LIST_SUPPLIERS
        )
        
        # Sort alphabetically by display name
        suppliers.sort(key=lambda s: (s.name, s.city, s.state))
        
        # Populate dropdown
        supplier_names = [s.display_name for s in suppliers]
        self.supplier_combo.configure(values=supplier_names)
        
        # Store mapping of display name to supplier ID
        self.supplier_map = {s.display_name: s.id for s in suppliers}
    
    def _on_supplier_changed(self, selected_name: str):
        """Handle supplier selection - update price suggestion."""
        product_id = self._get_selected_product_id()
        if not product_id:
            return
        
        supplier_id = self.supplier_map.get(selected_name)
        if not supplier_id:
            return
        
        # Try to get last price at this supplier
        last_price = self.service_integrator.execute_operation(
            operation_type=OperationType.GET_LAST_PURCHASE_PRICE,
            product_id=product_id,
            supplier_id=supplier_id
        )
        
        if last_price:
            # Found price at this supplier
            self.price_entry.delete(0, 'end')
            self.price_entry.insert(0, f"{last_price:.2f}")
            
            # Get last purchase date for hint
            history = self.service_integrator.execute_operation(
                operation_type=OperationType.GET_PURCHASE_HISTORY,
                product_id=product_id,
                supplier_id=supplier_id,
                limit=1
            )
            
            if history:
                date_str = history[0].purchase_date.strftime('%Y-%m-%d')
                self.price_hint_label.configure(
                    text=f"(last paid: ${last_price:.2f} on {date_str})"
                )
        else:
            # No price at this supplier - try fallback
            fallback = self.service_integrator.execute_operation(
                operation_type=OperationType.GET_LAST_PURCHASE_PRICE_ANY_SUPPLIER,
                product_id=product_id
            )
            
            if fallback:
                # Found price at different supplier
                self.price_entry.delete(0, 'end')
                self.price_entry.insert(0, f"{fallback['price']:.2f}")
                
                date_str = fallback['purchase_date'].strftime('%Y-%m-%d')
                supplier_display = f"{fallback['supplier_name']} ({fallback['supplier_city']}, {fallback['supplier_state']})"
                
                self.price_hint_label.configure(
                    text=f"(last paid: ${fallback['price']:.2f} at {supplier_display} on {date_str})"
                )
            else:
                # No purchase history at all
                self.price_entry.delete(0, 'end')
                self.price_hint_label.configure(text="(no purchase history)")
    
    def _validate_and_add(self):
        """Validate inputs and add inventory (MODIFIED)."""
        
        # Existing validation...
        
        # NEW: Validate supplier selected
        supplier_name = self.supplier_var.get()
        if not supplier_name:
            show_error(self, "Validation Error", "Please select a supplier")
            return
        
        supplier_id = self.supplier_map.get(supplier_name)
        if not supplier_id:
            show_error(self, "Validation Error", "Invalid supplier selection")
            return
        
        # NEW: Validate price
        try:
            unit_price = Decimal(self.price_entry.get())
            
            # Warn if zero
            if unit_price == 0:
                confirm = messagebox.askyesno(
                    "Confirm Zero Price",
                    "⚠️ Price is $0.00. This is unusual. Continue?"
                )
                if not confirm:
                    return
            
            # Error if negative
            if unit_price < 0:
                show_error(self, "Validation Error", "Price cannot be negative")
                return
                
        except (ValueError, InvalidOperation):
            show_error(self, "Validation Error", "Invalid price format")
            return
        
        # Call service (MODIFIED)
        try:
            addition = self.service_integrator.execute_operation(
                operation_type=OperationType.ADD_INVENTORY,
                ingredient_id=ingredient_id,
                product_id=product_id,
                supplier_id=supplier_id,  # NEW
                quantity=quantity,
                unit_price=unit_price,  # RENAMED from price_paid
                notes=notes,
                event_id=event_id
            )
            
            self.result = addition
            self.destroy()
            
        except Exception as e:
            show_error(self, "Add Inventory Failed", str(e))
```

---

## Migration Strategy

Per Constitution VI (Schema Change Strategy), schema changes handled via export/reset/import cycle.

### Step 1: Pre-Migration Export

```bash
# Export all data before schema change (assumes F027 complete)
python -m src.cli.main export --output docs/migrations/pre_f028_export.json
```

### Step 2: Schema Update

**Phase 1: Add new structures**
1. Create Purchase table (if not already created in F027)
2. Add InventoryAddition.purchase_id column (nullable for migration)
3. Keep InventoryAddition.price_paid column (for migration data source)

**Phase 2: After data transformation**
1. Make InventoryAddition.purchase_id NOT NULL
2. Drop InventoryAddition.price_paid column
3. Add Purchase foreign key constraint

### Step 3: Data Transformation

```python
# docs/migrations/transform_f028_data.py

import json
from decimal import Decimal
from datetime import datetime
from uuid import uuid4


def transform_for_f028(export_data: dict) -> dict:
    """
    Transform F027 data to F028 schema.
    
    Creates Purchase record for each InventoryAddition.
    Uses Unknown Supplier (id=1) for all historical purchases.
    
    Assumes:
    - F027 migration complete (Supplier table exists with Unknown)
    - InventoryAddition has price_paid field
    - InventoryAddition.purchase_id exists but NULL
    """
    
    # Verify Unknown Supplier exists
    suppliers = export_data.get('suppliers', [])
    unknown_supplier = next((s for s in suppliers if s['name'] == 'Unknown'), None)
    if not unknown_supplier:
        raise ValueError("F027 migration incomplete: Unknown Supplier not found")
    
    unknown_supplier_id = unknown_supplier['id']
    
    # Create Purchase for each InventoryAddition
    purchases = []
    purchase_id_counter = 1
    
    for addition in export_data.get('inventory_additions', []):
        # Skip if already has purchase_id (shouldn't happen in clean migration)
        if addition.get('purchase_id'):
            continue
        
        # Require price_paid for migration
        if 'price_paid' not in addition or addition['price_paid'] is None:
            raise ValueError(f"InventoryAddition {addition['id']} missing price_paid")
        
        # Create Purchase record
        purchase = {
            'id': purchase_id_counter,
            'uuid': str(uuid4()),
            'product_id': addition['product_id'],
            'supplier_id': unknown_supplier_id,
            'purchase_date': addition['addition_date'],
            'unit_price': str(addition['price_paid']),  # Convert Decimal to string for JSON
            'quantity_purchased': addition['quantity'],
            'notes': None,
            'created_at': addition.get('created_at', datetime.utcnow().isoformat())
        }
        
        purchases.append(purchase)
        
        # Link InventoryAddition to Purchase
        addition['purchase_id'] = purchase_id_counter
        
        purchase_id_counter += 1
    
    export_data['purchases'] = purchases
    
    # Remove price_paid from inventory_additions
    for addition in export_data.get('inventory_additions', []):
        if 'price_paid' in addition:
            del addition['price_paid']
    
    return export_data


def main():
    """Transform pre-F028 export to post-F028 schema."""
    
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python transform_f028_data.py <input.json> <output.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Load export data
    with open(input_file, 'r') as f:
        export_data = json.load(f)
    
    print(f"Loaded export from {input_file}")
    print(f"  Suppliers: {len(export_data.get('suppliers', []))}")
    print(f"  Inventory Additions: {len(export_data.get('inventory_additions', []))}")
    
    # Transform
    transformed = transform_for_f028(export_data)
    
    print(f"\nTransformation complete:")
    print(f"  Purchases created: {len(transformed.get('purchases', []))}")
    print(f"  Inventory additions linked: {sum(1 for a in transformed.get('inventory_additions', []) if a.get('purchase_id'))}")
    
    # Write transformed data
    with open(output_file, 'w') as f:
        json.dump(transformed, f, indent=2)
    
    print(f"\nTransformed data written to {output_file}")
    print("\nNext steps:")
    print("1. python -m src.cli.main db reset")
    print(f"2. python -m src.cli.main import --input {output_file}")
    print("3. Run validation: python docs/migrations/validate_f028_migration.py")


if __name__ == '__main__':
    main()
```

### Step 4: Import Transformed Data

```bash
# Reset database (delete and recreate with new schema)
python -m src.cli.main db reset

# Transform exported data
python docs/migrations/transform_f028_data.py \
    docs/migrations/pre_f028_export.json \
    docs/migrations/f028_transformed_export.json

# Import transformed data
python -m src.cli.main import --input docs/migrations/f028_transformed_export.json
```

### Step 5: Validation

```python
# docs/migrations/validate_f028_migration.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Purchase, InventoryAddition, Supplier, Product
from src.database import Base


def validate_f028_migration():
    """Validate Feature 028 migration success."""
    
    # Connect to database
    engine = create_engine('sqlite:///baketrack.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check 1: All InventoryAdditions have purchase_id
        additions_without_purchase = session.query(InventoryAddition).filter(
            InventoryAddition.purchase_id.is_(None)
        ).count()
        
        assert additions_without_purchase == 0, \
            f"Found {additions_without_purchase} inventory additions without purchase_id"
        
        print("✓ All inventory additions have purchase_id")
        
        # Check 2: All purchase_ids reference valid Purchases
        total_additions = session.query(InventoryAddition).count()
        for addition in session.query(InventoryAddition).all():
            purchase = session.query(Purchase).get(addition.purchase_id)
            assert purchase is not None, \
                f"InventoryAddition {addition.id} references non-existent Purchase {addition.purchase_id}"
        
        print(f"✓ All {total_additions} purchase_id references are valid")
        
        # Check 3: Purchase quantities match InventoryAddition quantities
        for addition in session.query(InventoryAddition).all():
            purchase = session.query(Purchase).get(addition.purchase_id)
            assert purchase.quantity_purchased == addition.quantity, \
                f"Quantity mismatch: Addition {addition.id} qty={addition.quantity}, Purchase {purchase.id} qty={purchase.quantity_purchased}"
        
        print(f"✓ All purchase quantities match inventory addition quantities")
        
        # Check 4: All Purchases reference valid Products
        total_purchases = session.query(Purchase).count()
        for purchase in session.query(Purchase).all():
            product = session.query(Product).get(purchase.product_id)
            assert product is not None, \
                f"Purchase {purchase.id} references non-existent Product {purchase.product_id}"
        
        print(f"✓ All {total_purchases} purchases reference valid products")
        
        # Check 5: Unknown Supplier exists and has purchases
        unknown = session.query(Supplier).filter_by(name='Unknown').first()
        assert unknown is not None, "Unknown Supplier not found"
        
        unknown_purchase_count = session.query(Purchase).filter_by(
            supplier_id=unknown.id
        ).count()
        
        print(f"✓ Unknown Supplier exists with {unknown_purchase_count} historical purchases")
        
        # Check 6: No negative prices
        negative_prices = session.query(Purchase).filter(
            Purchase.unit_price < 0
        ).count()
        
        assert negative_prices == 0, f"Found {negative_prices} purchases with negative prices"
        
        print("✓ No negative purchase prices")
        
        # Check 7: No zero quantities
        zero_quantities = session.query(Purchase).filter(
            Purchase.quantity_purchased <= 0
        ).count()
        
        assert zero_quantities == 0, f"Found {zero_quantities} purchases with zero/negative quantity"
        
        print("✓ All purchase quantities are positive")
        
        # Summary
        print("\n" + "="*60)
        print("MIGRATION VALIDATION PASSED")
        print("="*60)
        print(f"  Total Purchases: {total_purchases}")
        print(f"  Total Inventory Additions: {total_additions}")
        print(f"  Suppliers: {session.query(Supplier).count()}")
        print(f"  Products: {session.query(Product).count()}")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        return False
        
    finally:
        session.close()


if __name__ == '__main__':
    import sys
    success = validate_f028_migration()
    sys.exit(0 if success else 1)
```

---

## Testing Strategy

### Unit Tests

**purchase_service.py:**

```python
# tests/services/test_purchase_service.py

class TestPurchaseService:
    """Test suite for purchase transaction management."""
    
    def test_create_purchase(self, session, test_product, test_supplier):
        """Verify purchase creation with required fields."""
        from datetime import date
        
        purchase = purchase_service.create_purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date(2024, 12, 22),
            unit_price=Decimal("8.99"),
            quantity_purchased=2,
            session=session
        )
        
        assert purchase.id is not None
        assert purchase.product_id == test_product.id
        assert purchase.supplier_id == test_supplier.id
        assert purchase.unit_price == Decimal("8.99")
        assert purchase.quantity_purchased == 2
        assert purchase.total_cost == Decimal("17.98")
    
    def test_create_purchase_validates_product_exists(self, session, test_supplier):
        """Verify error when product doesn't exist."""
        with pytest.raises(ValueError, match="Product.*not found"):
            purchase_service.create_purchase(
                product_id=99999,  # Non-existent
                supplier_id=test_supplier.id,
                purchase_date=date.today(),
                unit_price=Decimal("10.00"),
                quantity_purchased=1,
                session=session
            )
    
    def test_create_purchase_validates_supplier_exists(self, session, test_product):
        """Verify error when supplier doesn't exist."""
        with pytest.raises(ValueError, match="Supplier.*not found"):
            purchase_service.create_purchase(
                product_id=test_product.id,
                supplier_id=99999,  # Non-existent
                purchase_date=date.today(),
                unit_price=Decimal("10.00"),
                quantity_purchased=1,
                session=session
            )
    
    def test_create_purchase_rejects_negative_price(self, session, test_product, test_supplier):
        """Verify error when price is negative."""
        with pytest.raises(ValueError, match="negative"):
            purchase_service.create_purchase(
                product_id=test_product.id,
                supplier_id=test_supplier.id,
                purchase_date=date.today(),
                unit_price=Decimal("-10.00"),
                quantity_purchased=1,
                session=session
            )
    
    def test_create_purchase_allows_zero_price(self, session, test_product, test_supplier):
        """Verify zero price allowed (donations, free samples)."""
        purchase = purchase_service.create_purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("0.00"),
            quantity_purchased=1,
            session=session
        )
        
        assert purchase.unit_price == Decimal("0.00")
    
    def test_get_last_purchase_price_with_history(self, session, product_with_purchases):
        """Verify returns most recent price at specified supplier."""
        # Fixture has purchases at different dates
        last_price = purchase_service.get_last_purchase_price(
            product_id=product_with_purchases['product'].id,
            supplier_id=product_with_purchases['costco'].id,
            session=session
        )
        
        # Should return most recent purchase price
        assert last_price == Decimal("600.00")  # From fixture: most recent
    
    def test_get_last_purchase_price_no_history_at_supplier(self, session, test_product, test_supplier):
        """Verify returns None when no purchase history at supplier."""
        last_price = purchase_service.get_last_purchase_price(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            session=session
        )
        
        assert last_price is None
    
    def test_get_last_purchase_price_any_supplier_fallback(self, session, product_with_purchases):
        """Verify fallback returns price from different supplier with metadata."""
        # Product has purchases at Costco, but query for Wegmans (no history)
        fallback = purchase_service.get_last_purchase_price_any_supplier(
            product_id=product_with_purchases['product'].id,
            session=session
        )
        
        assert fallback is not None
        assert 'price' in fallback
        assert 'supplier_name' in fallback
        assert 'purchase_date' in fallback
        assert fallback['price'] == Decimal("600.00")
    
    def test_get_purchase_history_sorted_by_date(self, session, product_with_multiple_purchases):
        """Verify purchase history sorted descending (newest first)."""
        history = purchase_service.get_purchase_history(
            product_id=product_with_multiple_purchases.id,
            session=session
        )
        
        assert len(history) == 3
        # Verify sorted by date descending
        assert history[0].purchase_date > history[1].purchase_date
        assert history[1].purchase_date > history[2].purchase_date
    
    def test_get_purchase_history_filtered_by_supplier(self, session, product_with_multi_supplier_purchases):
        """Verify purchase history can filter by supplier."""
        costco_id = product_with_multi_supplier_purchases['costco'].id
        
        history = purchase_service.get_purchase_history(
            product_id=product_with_multi_supplier_purchases['product'].id,
            supplier_id=costco_id,
            session=session
        )
        
        # All returned purchases should be from Costco
        assert all(p.supplier_id == costco_id for p in history)
    
    def test_get_purchase_history_limit(self, session, product_with_many_purchases):
        """Verify purchase history respects limit parameter."""
        history = purchase_service.get_purchase_history(
            product_id=product_with_many_purchases.id,
            limit=3,
            session=session
        )
        
        assert len(history) == 3
```

**inventory_service.py (Modified):**

```python
# tests/services/test_inventory_service.py

class TestInventoryServicePurchaseIntegration:
    """Test suite for inventory-purchase integration."""
    
    def test_add_inventory_creates_purchase(self, session, test_ingredient, test_product, test_supplier):
        """Verify adding inventory creates linked Purchase record."""
        from datetime import date
        
        initial_purchase_count = session.query(Purchase).count()
        
        addition = inventory_service.add_inventory(
            ingredient_id=test_ingredient.id,
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            quantity=2,
            unit_price=Decimal("8.99"),
            session=session
        )
        
        # Verify Purchase created
        assert session.query(Purchase).count() == initial_purchase_count + 1
        
        # Verify InventoryAddition links to Purchase
        assert addition.purchase_id is not None
        purchase = session.query(Purchase).get(addition.purchase_id)
        assert purchase is not None
        assert purchase.product_id == test_product.id
        assert purchase.supplier_id == test_supplier.id
        assert purchase.unit_price == Decimal("8.99")
        assert purchase.quantity_purchased == 2
    
    def test_add_inventory_defaults_purchase_date_to_today(self, session, test_ingredient, test_product, test_supplier):
        """Verify purchase_date defaults to today when not provided."""
        from datetime import date
        
        addition = inventory_service.add_inventory(
            ingredient_id=test_ingredient.id,
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            quantity=1,
            unit_price=Decimal("5.00"),
            # purchase_date not provided
            session=session
        )
        
        purchase = session.query(Purchase).get(addition.purchase_id)
        assert purchase.purchase_date == date.today()
    
    def test_add_inventory_respects_custom_purchase_date(self, session, test_ingredient, test_product, test_supplier):
        """Verify purchase_date parameter is respected."""
        from datetime import date
        
        custom_date = date(2024, 11, 15)
        
        addition = inventory_service.add_inventory(
            ingredient_id=test_ingredient.id,
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            quantity=1,
            unit_price=Decimal("5.00"),
            purchase_date=custom_date,
            session=session
        )
        
        purchase = session.query(Purchase).get(addition.purchase_id)
        assert purchase.purchase_date == custom_date
    
    def test_add_inventory_purchase_quantity_matches_addition(self, session, test_ingredient, test_product, test_supplier):
        """Verify Purchase.quantity_purchased = InventoryAddition.quantity."""
        addition = inventory_service.add_inventory(
            ingredient_id=test_ingredient.id,
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            quantity=5,
            unit_price=Decimal("10.00"),
            session=session
        )
        
        purchase = session.query(Purchase).get(addition.purchase_id)
        assert purchase.quantity_purchased == addition.quantity
        assert purchase.quantity_purchased == 5
```

**FIFO Cost Calculation:**

```python
# tests/services/test_batch_production_service.py

class TestFIFOWithPurchases:
    """Test FIFO cost calculation using Purchase.unit_price."""
    
    def test_fifo_uses_purchase_unit_price(self, session, production_scenario):
        """Verify FIFO cost uses Purchase.unit_price, not addition.price_paid."""
        # Setup: Add inventory with specific purchase price
        ingredient = production_scenario['ingredient']
        product = production_scenario['product']
        supplier = production_scenario['supplier']
        
        # Add inventory with known purchase price
        addition = inventory_service.add_inventory(
            ingredient_id=ingredient.id,
            product_id=product.id,
            supplier_id=supplier.id,
            quantity=10,
            unit_price=Decimal("5.00"),
            session=session
        )
        
        # Record production that consumes this inventory
        production_run = batch_production_service.record_production(
            recipe_id=production_scenario['recipe'].id,
            finished_unit_id=production_scenario['finished_unit'].id,
            num_batches=1,
            actual_yield=24,
            session=session
        )
        
        # Verify cost calculation used Purchase.unit_price
        consumption = session.query(ProductionConsumption).filter_by(
            production_run_id=production_run.id,
            ingredient_slug=ingredient.slug
        ).first()
        
        # Cost should be quantity_consumed * purchase.unit_price
        purchase = session.query(Purchase).get(addition.purchase_id)
        expected_cost = consumption.quantity_consumed * purchase.unit_price
        
        assert consumption.total_cost == expected_cost
    
    def test_fifo_with_multiple_purchases_different_prices(self, session, complex_scenario):
        """Verify FIFO correctly handles price variance across purchases."""
        # Setup: Add inventory from multiple purchases at different prices
        ingredient = complex_scenario['ingredient']
        product = complex_scenario['product']
        costco = complex_scenario['costco']
        wegmans = complex_scenario['wegmans']
        
        # Purchase 1: 10 units at $5.00 (Costco)
        addition1 = inventory_service.add_inventory(
            ingredient_id=ingredient.id,
            product_id=product.id,
            supplier_id=costco.id,
            quantity=10,
            unit_price=Decimal("5.00"),
            purchase_date=date(2024, 11, 1),
            session=session
        )
        
        # Purchase 2: 10 units at $6.00 (Wegmans)
        addition2 = inventory_service.add_inventory(
            ingredient_id=ingredient.id,
            product_id=product.id,
            supplier_id=wegmans.id,
            quantity=10,
            unit_price=Decimal("6.00"),
            purchase_date=date(2024, 11, 15),
            session=session
        )
        
        # Consume 15 units (should use all of Purchase 1 + 5 from Purchase 2)
        production_run = batch_production_service.record_production(
            recipe_id=complex_scenario['recipe'].id,
            finished_unit_id=complex_scenario['finished_unit'].id,
            num_batches=1,
            actual_yield=24,
            session=session
        )
        
        # Verify FIFO cost: (10 * $5.00) + (5 * $6.00) = $80.00
        consumption = session.query(ProductionConsumption).filter_by(
            production_run_id=production_run.id,
            ingredient_slug=ingredient.slug
        ).first()
        
        expected_cost = (10 * Decimal("5.00")) + (5 * Decimal("6.00"))
        assert consumption.total_cost == expected_cost
```

### Integration Tests

**UI Workflow:**

```python
# tests/integration/test_add_inventory_with_purchases.py

class TestAddInventoryDialogPurchaseIntegration:
    """Integration tests for Add Inventory dialog with purchase tracking."""
    
    def test_supplier_dropdown_populated(self, add_inventory_dialog):
        """Verify supplier dropdown loads and displays suppliers."""
        suppliers = add_inventory_dialog.supplier_combo.cget('values')
        
        assert len(suppliers) > 0
        assert "Costco (Waltham, MA)" in suppliers
        assert "Wegmans (Burlington, MA)" in suppliers
    
    def test_price_suggestion_on_supplier_selection(self, add_inventory_dialog, product_with_history):
        """Verify price pre-fills when supplier selected."""
        # Select product
        add_inventory_dialog._select_product(product_with_history.id)
        
        # Select supplier
        add_inventory_dialog.supplier_var.set("Costco (Waltham, MA)")
        add_inventory_dialog._on_supplier_changed("Costco (Waltham, MA)")
        
        # Verify price pre-filled
        price_text = add_inventory_dialog.price_entry.get()
        assert price_text == "600.00"
        
        # Verify hint displayed
        hint_text = add_inventory_dialog.price_hint_label.cget('text')
        assert "last paid:" in hint_text
        assert "$600.00" in hint_text
    
    def test_price_fallback_different_supplier(self, add_inventory_dialog, product_with_costco_history):
        """Verify price fallback when no history at selected supplier."""
        # Select product (has history at Costco only)
        add_inventory_dialog._select_product(product_with_costco_history.id)
        
        # Select Wegmans (no history there)
        add_inventory_dialog.supplier_var.set("Wegmans (Burlington, MA)")
        add_inventory_dialog._on_supplier_changed("Wegmans (Burlington, MA)")
        
        # Verify price pre-filled from Costco
        price_text = add_inventory_dialog.price_entry.get()
        assert price_text == "600.00"
        
        # Verify hint shows different supplier
        hint_text = add_inventory_dialog.price_hint_label.cget('text')
        assert "Costco" in hint_text
    
    def test_zero_price_warning(self, add_inventory_dialog):
        """Verify warning when user enters $0.00."""
        # Setup dialog with selections
        add_inventory_dialog._setup_for_add()
        
        # Enter zero price
        add_inventory_dialog.price_entry.delete(0, 'end')
        add_inventory_dialog.price_entry.insert(0, "0.00")
        
        # Attempt to add
        with patch('tkinter.messagebox.askyesno', return_value=False):
            add_inventory_dialog._validate_and_add()
            
            # Dialog should not close (user cancelled)
            assert add_inventory_dialog.winfo_exists()
```

---

## Acceptance Criteria

### Must Have (MVP)

1. ✅ Purchase table created with all specified fields and constraints
2. ✅ InventoryAddition.purchase_id FK replaces price_paid field
3. ✅ `purchase_service.py` implements all core methods (create, get, history, price queries)
4. ✅ `inventory_service.add_inventory()` creates Purchase before InventoryAddition
5. ✅ Supplier dropdown added to Add Inventory dialog (alphabetically sorted)
6. ✅ Price suggestion queries implemented (supplier-specific + fallback)
7. ✅ Price field pre-fills from last purchase with hint text
8. ✅ Price hint displays: "(last paid: $X.XX on DATE)" or "(last paid: $X.XX at SUPPLIER on DATE)"
9. ✅ FIFO cost calculation uses Purchase.unit_price via InventoryAddition.purchase relationship
10. ✅ Migration creates one Purchase per InventoryAddition with Unknown Supplier
11. ✅ All existing tests pass after migration
12. ✅ Service layer tests achieve >70% coverage
13. ✅ Purchase-InventoryAddition FK constraint validated (cannot delete purchase if additions exist)
14. ✅ Zero-price purchases allowed (with validation warning)
15. ✅ Negative-price purchases rejected (validation error)

### Should Have (Post-MVP)

1. ⬜ Purchase date picker in dialog (override today default)
2. ⬜ Price history tooltip (hover to see last 5 purchases)
3. ⬜ "No purchase history" explicit message when blank
4. ⬜ Purchase.notes field usage defined (currently NULL)
5. ⬜ Supplier "Unknown" sorting (last in dropdown)

### Could Have (Future/F029)

1. ⬜ Session-based supplier memory
2. ⬜ Price variance alerts (>50% change warning)
3. ⬜ Purchase editing interface
4. ⬜ Purchase deletion (with dependency checks)
5. ⬜ Bulk purchase entry ("I bought 5 bags at once")
6. ⬜ Price trend visualization
7. ⬜ Supplier performance dashboard

---

## Risks and Mitigation

### Risk: Migration Data Integrity

**Risk:** Creating Purchase records from InventoryAddition.price_paid could fail if price_paid is NULL or malformed.

**Mitigation:**
- Validation script checks price_paid exists before migration
- Explicit error messages if data incomplete
- Dry-run transformation validates all records transformable
- Export/import cycle allows rollback to pre-migration state

### Risk: FIFO Performance Degradation

**Risk:** Adding JOIN to Purchase table could slow FIFO cost calculations.

**Mitigation:**
- Composite index (product_id, purchase_date) enables efficient queries
- FK index on InventoryAddition.purchase_id speeds lookups
- Purchase records are immutable (no update overhead)
- Benchmarking before/after migration to validate performance

### Risk: UI Complexity (Supplier Selection)

**Risk:** Adding supplier dropdown increases cognitive load during inventory addition.

**Mitigation:**
- Alphabetical sorting makes supplier findable
- Price suggestion provides immediate value feedback
- Future F029 will add session memory (reduces repeated selections)
- User testing will validate workflow acceptance

### Risk: Historical Data Accuracy

**Risk:** All historical purchases assigned to "Unknown Supplier" loses actual supplier context.

**Mitigation:**
- Accept limitation for historical data (known tradeoff)
- Forward-looking data captures full context
- User can manually update historical purchases if critical (future feature)
- Documentation clearly states migration assigns Unknown Supplier

---

## Open Questions

**1. Purchase.notes vs InventoryAddition.notes:**
When user enters notes in Add Inventory dialog, where should they go?
- **Current implementation:** InventoryAddition.notes only
- **Future consideration:** Separate fields for purchase transaction notes vs inventory storage notes

**Resolution:** InventoryAddition.notes for MVP. Purchase.notes left NULL. Future enhancement.

**2. Supplier "Unknown" visibility:**
Should "Unknown" supplier appear in dropdown for new inventory additions?
- **Argument for Yes:** User might legitimately not know supplier
- **Argument for No:** Forces accurate data entry, "Unknown" is legacy artifact

**Resolution:** Yes, but sort last. Allows data entry flexibility.

**3. Price suggestion priority:**
When multiple price sources available, which takes precedence?
- Current: Supplier-specific → Any supplier → Blank
- Alternative: Supplier-specific → Product.preferred_supplier → Any supplier → Blank

**Resolution:** Current approach for F028. Preferred supplier intelligence deferred to F029.

---

## References

### Existing Features

- **Feature 027:** Product Catalog Management (schema foundation, Supplier table)
- **Feature 013:** Production & Inventory Tracking (FIFO consumption, cost calculation)
- **Feature 021:** Field Naming Consistency (package_unit terminology)

### Architecture Documents

- **Constitution Principle II:** Data Integrity & FIFO Accuracy (ingredient cost tracking)
- **Constitution Principle III:** Future-Proof Schema (industry practices, immutable records)
- **Constitution Principle VI:** Schema Change Strategy (export/reset/import cycle)

### Code References

- `src/models/inventory_addition.py` - InventoryAddition model
- `src/services/inventory_service.py` - Existing inventory operations
- `src/services/batch_production_service.py` - FIFO consumption logic
- `src/ui/forms/add_inventory_dialog.py` - Inventory addition UI

---

## Appendix: Schema SQL

```sql
-- Purchase table
CREATE TABLE purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    product_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    purchase_date DATE NOT NULL,
    unit_price NUMERIC(10, 4) NOT NULL CHECK (unit_price >= 0),
    quantity_purchased INTEGER NOT NULL CHECK (quantity_purchased > 0),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT
);

-- Indexes for Purchase
CREATE INDEX idx_purchase_product ON purchases(product_id);
CREATE INDEX idx_purchase_supplier ON purchases(supplier_id);
CREATE INDEX idx_purchase_date ON purchases(purchase_date);
CREATE INDEX idx_purchase_product_date ON purchases(product_id, purchase_date);

-- InventoryAddition updates
ALTER TABLE inventory_additions
ADD COLUMN purchase_id INTEGER REFERENCES purchases(id) ON DELETE RESTRICT;

CREATE INDEX idx_inventory_addition_purchase ON inventory_additions(purchase_id);

-- After migration complete:
-- 1. Make purchase_id NOT NULL
-- 2. Drop price_paid column
-- ALTER TABLE inventory_additions DROP COLUMN price_paid;
```

---

**Version:** 1.0  
**Last Updated:** 2025-12-22  
**Next Feature:** 029 - Streamlined Inventory Entry (Workflow Intelligence)
