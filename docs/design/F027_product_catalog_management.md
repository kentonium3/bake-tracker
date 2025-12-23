# Feature 027: Product Catalog Management

**Created:** 2025-12-22  
**Status:** DESIGN  
**Priority:** HIGH  
**Complexity:** HIGH

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

Product and inventory management workflows have critical gaps blocking effective user testing:

**Current Workflow Failures:**
1. **No standalone product management:** Cannot add products to catalog independently
2. **Forced ingredient-first entry:** Adding inventory blocked if ingredient has no products
3. **No price history:** Cannot track price changes over time (critical for FIFO costing)
4. **No product-first workflow:** User must navigate Ingredient → Product → Add Inventory
5. **No product catalog maintenance:** Cannot hide obsolete products, filter by category/supplier

**User Impact:**
- "I just shopped at Costco with 20 items" → 40+ minutes of data entry
- Cannot answer "What did I pay for chocolate chips last time?"
- Price volatility (tariffs, inflation) makes cost tracking critical: $300 → $600 for same product
- Ingredient list too granular (20 categories, hundreds of items) creates dropdown friction
- Testing blocked: cannot populate inventory with realistic prices without product catalog

**Real-World Example:**
> User testing revealed: Marianne clicks "Add Inventory Item" → dropdown shows "no products available" for selected ingredient → cannot proceed. Must exit, navigate to (non-existent) Products tab, create product with all details, return to inventory addition. This loop repeated 20+ times after a shopping trip.

---

## Solution Overview

Three-feature implementation addressing product catalog, purchase tracking, and streamlined inventory entry:

**Feature 027: Product Catalog Management** (Foundation)
- New Products tab with CRUD operations
- Filter by ingredient, category, supplier
- Hide/unhide products (preserve history)
- Purchase history display in product detail view

**Feature 028: Purchase Tracking & Enhanced Costing** (Data Model)
- Purchase entity (shopping transaction records)
- Supplier entity (store/location tracking)
- Link inventory additions to purchases (FIFO cost basis)
- Price history and suggestion logic

**Feature 029: Streamlined Inventory Entry** (Workflow)
- Product-first entry (type-ahead search)
- Inline product creation (no modal switching)
- Price auto-suggestion from last purchase
- Session-based supplier memory

**Core Principle:** Build Option A architecture (purchase-based tracking) from the start. This enables future supplier analytics, shopping list optimization, and bulk discount tracking without later refactoring.

---

## Scope

### In Scope

**Schema Changes:**
- New `Supplier` table (name, street_address, city, state, zip)
- New `Purchase` table (product, supplier, date, unit_price, quantity_purchased)
- Modify `Product` table (add preferred_supplier_id, is_hidden)
- Modify `InventoryAddition` table (add purchase_id FK, remove price_paid)

**Service Layer:**
- New `product_service.py` with CRUD operations
- New `supplier_service.py` for supplier management
- Update `inventory_service.py` to create Purchase records
- Purchase history queries (by product, by supplier, by date range)
- Price suggestion logic (last paid at supplier)

**UI Changes:**
- New "Products" tab with grid view and filters
- Product detail view with purchase history table
- "Add Product" modal with validation
- Hide/delete actions with referential integrity checks
- Search products by name (type-ahead)

**Business Rules:**
- Product requires: name, ingredient_id, package_unit, package_unit_quantity
- Product can have preferred_supplier_id (optional)
- Cannot delete product if purchases or inventory exist (offer Hide instead)
- Supplier requires: name, city, state, zip (street address optional)
- Purchase links: product_id, supplier_id, date, unit_price, quantity_purchased
- InventoryAddition always creates Purchase (no standalone price_paid)

### Out of Scope

**Current Phase:**
- Inventory addition workflow changes (Feature 029)
- Price suggestion UI (Feature 029)
- Inline product creation during inventory addition (Feature 029)
- Supplier-based shopping list grouping (future feature)
- Purchase pattern analytics ("you usually buy this at Costco")
- Bulk purchase discounts tracking
- Receipt scanning/OCR integration
- Automated price population from web scraping

**Future Considerations:**
- Multi-supplier price comparison views
- Predictive purchasing ("you'll need butter in 2 weeks based on event schedule")
- Integration with store loyalty programs
- Inventory reorder point alerts
- Product lifecycle management (introduction → active → phasing out → discontinued)

---

## Technical Design

### Schema Changes

#### New Supplier Table

```python
class Supplier(Base):
    """
    Supplier model for tracking stores and vendors.
    
    Represents physical or online locations where products are purchased.
    Multiple products can share a supplier, and products can be purchased
    from different suppliers over time.
    
    Attributes:
        name: Store or vendor name (e.g., "Costco", "Wegmans")
        street_address: Optional street address
        city: City name (required)
        state: Two-letter state code (required)
        zip_code: 5 or 9-digit ZIP code (required)
        notes: Optional notes about supplier
        is_active: Whether supplier is currently active (soft delete)
    """
    
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    
    # Required fields
    name = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)  # Two-letter code
    zip_code = Column(String(10), nullable=False)
    
    # Optional fields
    street_address = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products_preferred = relationship(
        "Product",
        back_populates="preferred_supplier",
        foreign_keys="Product.preferred_supplier_id"
    )
    purchases = relationship("Purchase", back_populates="supplier")
    
    # Constraints
    __table_args__ = (
        Index("idx_supplier_name_city", "name", "city"),
        Index("idx_supplier_active", "is_active"),
        CheckConstraint("state = UPPER(state)", name="ck_supplier_state_uppercase"),
        CheckConstraint("LENGTH(state) = 2", name="ck_supplier_state_length"),
    )
    
    def __repr__(self) -> str:
        """String representation of supplier."""
        return f"Supplier(id={self.id}, name='{self.name}', city='{self.city}', state='{self.state}')"
    
    @property
    def display_name(self) -> str:
        """Human-readable supplier identification."""
        return f"{self.name} ({self.city}, {self.state})"
```

**Design Rationale:**

1. **City/State/Zip Required:** Enables future shipping cost calculations, regional pricing analysis
2. **Street Address Optional:** Many users won't know exact address (especially for chains)
3. **is_active Soft Delete:** Preserves historical purchase data while hiding from dropdowns
4. **State Constraints:** Uppercase validation prevents data quality issues
5. **Composite Index:** Efficient lookup by name+city (common query pattern)

#### New Purchase Table

```python
class Purchase(Base):
    """
    Purchase model for tracking shopping transaction details.
    
    Represents a single product purchased from a supplier on a specific date.
    Each inventory addition references a purchase for FIFO cost calculation.
    
    Design: One Purchase per product per shopping trip, even if multiple units.
    Example: Buying 5 bags of chocolate chips = 1 Purchase with quantity_purchased=5
    
    Attributes:
        product_id: Foreign key to Product purchased
        supplier_id: Foreign key to Supplier (where purchased)
        purchase_date: Date of purchase
        unit_price: Price per package unit
        quantity_purchased: Number of package units purchased
        notes: Optional purchase notes (sale info, discount codes, etc.)
    """
    
    __tablename__ = 'purchases'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    
    # Foreign keys
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    
    # Purchase data
    purchase_date = Column(Date, nullable=False)
    unit_price = Column(Numeric(10, 4), nullable=False)
    quantity_purchased = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="purchases")
    supplier = relationship("Supplier", back_populates="purchases")
    inventory_additions = relationship("InventoryAddition", back_populates="purchase")
    
    # Constraints and indexes
    __table_args__ = (
        Index("idx_purchase_product", "product_id"),
        Index("idx_purchase_supplier", "supplier_id"),
        Index("idx_purchase_date", "purchase_date"),
        Index("idx_purchase_product_date", "product_id", "purchase_date"),
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
            f"qty={self.quantity_purchased})"
        )
    
    @property
    def total_cost(self) -> Decimal:
        """Total cost of this purchase."""
        return self.unit_price * self.quantity_purchased
```

**Design Rationale:**

1. **Transaction-Level Record:** Matches real-world shopping behavior ("I bought 5 bags at Costco")
2. **Quantity Purchased:** Enables bulk purchase tracking, future discount analysis
3. **RESTRICT on Delete:** Preserve purchase history if product/supplier deleted
4. **Composite Index:** Efficient FIFO lookups (product + date)
5. **Immutable After Creation:** No updated_at timestamp (purchase history should not change)

#### Product Table Updates

```python
class Product(Base):
    """
    Product model (EXISTING - showing changes only).
    
    NEW FIELDS:
    - preferred_supplier_id: Default supplier for shopping list generation
    - is_hidden: Soft delete flag (preserves history)
    
    NEW RELATIONSHIPS:
    - preferred_supplier: Many-to-one relationship with Supplier
    - purchases: One-to-many relationship with Purchase
    """
    
    __tablename__ = 'products'
    
    # ... existing fields ...
    
    # NEW FIELDS
    preferred_supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_hidden = Column(Boolean, nullable=False, default=False)
    
    # NEW RELATIONSHIPS
    preferred_supplier = relationship(
        "Supplier",
        back_populates="products_preferred",
        foreign_keys=[preferred_supplier_id]
    )
    purchases = relationship(
        "Purchase",
        back_populates="product",
        order_by="desc(Purchase.purchase_date)"
    )
    
    # UPDATED INDEXES
    __table_args__ = (
        # ... existing indexes ...
        Index("idx_product_preferred_supplier", "preferred_supplier_id"),
        Index("idx_product_hidden", "is_hidden"),
    )
```

**Design Rationale:**

1. **preferred_supplier_id Nullable:** Products can exist without preferred supplier
2. **SET NULL on Delete:** If supplier deleted, product remains but loses preference
3. **is_hidden vs Deletion:** Preserves purchase history, recipe references
4. **Purchase Ordering:** Default descending by date (most recent first)

#### InventoryAddition Table Updates

```python
class InventoryAddition(Base):
    """
    InventoryAddition model (EXISTING - showing changes only).
    
    REMOVED FIELD:
    - price_paid: Deprecated; cost now derived from Purchase
    
    NEW FIELD:
    - purchase_id: Foreign key to Purchase (REQUIRED)
    
    NEW RELATIONSHIP:
    - purchase: Many-to-one relationship with Purchase
    """
    
    __tablename__ = 'inventory_additions'
    
    # ... existing fields ...
    
    # REMOVED: price_paid column (deprecated)
    
    # NEW FIELD
    purchase_id = Column(
        Integer,
        ForeignKey("purchases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    
    # NEW RELATIONSHIP
    purchase = relationship("Purchase", back_populates="inventory_additions")
    
    # UPDATED INDEXES
    __table_args__ = (
        # ... existing indexes ...
        Index("idx_inventory_addition_purchase", "purchase_id"),
    )
```

**Design Rationale:**

1. **purchase_id Required:** Every inventory addition must reference a purchase
2. **RESTRICT on Delete:** Cannot delete purchase if inventory additions exist
3. **No Dual Tracking:** Single source of truth for cost (Purchase.unit_price)
4. **Backward Compatibility:** Migration creates Purchase records for existing additions

### Service Layer Changes

#### New product_service.py

```python
"""
Product catalog management service.

Provides CRUD operations for products with referential integrity checks,
filtering, and purchase history queries.
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from src.models import Product, Ingredient, Supplier, Purchase
from src.database import session_scope


class ProductNotFoundError(Exception):
    """Raised when product lookup fails."""
    pass


class ProductInUseError(Exception):
    """Raised when attempting to delete product with dependencies."""
    pass


def create_product(
    name: str,
    ingredient_id: int,
    package_unit: str,
    package_unit_quantity: Decimal,
    preferred_supplier_id: Optional[int] = None,
    upc: Optional[str] = None,
    product_name: Optional[str] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Product:
    """
    Create a new product in the catalog.
    
    Args:
        name: Product brand/name
        ingredient_id: Foreign key to Ingredient
        package_unit: Unit of measure (lb, oz, kg, etc.)
        package_unit_quantity: Quantity per package
        preferred_supplier_id: Optional default supplier
        upc: Optional barcode
        product_name: Optional product variant name
        notes: Optional notes
        session: Optional database session
        
    Returns:
        Created Product instance
        
    Raises:
        ValueError: If ingredient doesn't exist or units invalid
    """
    if session is not None:
        return _create_product_impl(
            name, ingredient_id, package_unit, package_unit_quantity,
            preferred_supplier_id, upc, product_name, notes, session
        )
    
    with session_scope() as session:
        return _create_product_impl(
            name, ingredient_id, package_unit, package_unit_quantity,
            preferred_supplier_id, upc, product_name, notes, session
        )


def _create_product_impl(
    name: str,
    ingredient_id: int,
    package_unit: str,
    package_unit_quantity: Decimal,
    preferred_supplier_id: Optional[int],
    upc: Optional[str],
    product_name: Optional[str],
    notes: Optional[str],
    session: Session
) -> Product:
    """Implementation using provided session."""
    
    # Validate ingredient exists
    ingredient = session.query(Ingredient).filter_by(id=ingredient_id).first()
    if not ingredient:
        raise ValueError(f"Ingredient with id {ingredient_id} not found")
    
    # Validate supplier if provided
    if preferred_supplier_id:
        supplier = session.query(Supplier).filter_by(id=preferred_supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier with id {preferred_supplier_id} not found")
    
    # TODO: Validate package_unit against units reference table
    
    # Create product
    product = Product(
        name=name,
        ingredient_id=ingredient_id,
        package_unit=package_unit,
        package_unit_quantity=package_unit_quantity,
        preferred_supplier_id=preferred_supplier_id,
        upc=upc,
        product_name=product_name,
        notes=notes,
        is_hidden=False
    )
    
    session.add(product)
    session.flush()
    
    return product


def get_product(
    product_id: int,
    include_purchase_history: bool = False,
    session: Optional[Session] = None
) -> Product:
    """
    Retrieve a product by ID.
    
    Args:
        product_id: Product ID to retrieve
        include_purchase_history: If True, eagerly load purchase history
        session: Optional database session
        
    Returns:
        Product instance
        
    Raises:
        ProductNotFoundError: If product doesn't exist
    """
    if session is not None:
        return _get_product_impl(product_id, include_purchase_history, session)
    
    with session_scope() as session:
        return _get_product_impl(product_id, include_purchase_history, session)


def _get_product_impl(
    product_id: int,
    include_purchase_history: bool,
    session: Session
) -> Product:
    """Implementation using provided session."""
    
    query = session.query(Product).filter_by(id=product_id)
    
    if include_purchase_history:
        query = query.options(
            joinedload(Product.purchases).joinedload(Purchase.supplier)
        )
    
    product = query.first()
    
    if not product:
        raise ProductNotFoundError(f"Product with id {product_id} not found")
    
    return product


def list_products(
    ingredient_id: Optional[int] = None,
    category: Optional[str] = None,
    supplier_id: Optional[int] = None,
    include_hidden: bool = False,
    search_term: Optional[str] = None,
    session: Optional[Session] = None
) -> List[Product]:
    """
    List products with optional filtering.
    
    Args:
        ingredient_id: Filter by ingredient
        category: Filter by ingredient category
        supplier_id: Filter by preferred supplier
        include_hidden: If True, include hidden products
        search_term: Search product names (case-insensitive)
        session: Optional database session
        
    Returns:
        List of Product instances matching filters
    """
    if session is not None:
        return _list_products_impl(
            ingredient_id, category, supplier_id, include_hidden, search_term, session
        )
    
    with session_scope() as session:
        return _list_products_impl(
            ingredient_id, category, supplier_id, include_hidden, search_term, session
        )


def _list_products_impl(
    ingredient_id: Optional[int],
    category: Optional[str],
    supplier_id: Optional[int],
    include_hidden: bool,
    search_term: Optional[str],
    session: Session
) -> List[Product]:
    """Implementation using provided session."""
    
    query = session.query(Product).join(Ingredient)
    
    # Apply filters
    if not include_hidden:
        query = query.filter(Product.is_hidden == False)
    
    if ingredient_id:
        query = query.filter(Product.ingredient_id == ingredient_id)
    
    if category:
        query = query.filter(Ingredient.category == category)
    
    if supplier_id:
        query = query.filter(Product.preferred_supplier_id == supplier_id)
    
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(Product.name.ilike(search_pattern))
    
    # Order by name
    query = query.order_by(Product.name)
    
    return query.all()


def update_product(
    product_id: int,
    name: Optional[str] = None,
    package_unit: Optional[str] = None,
    package_unit_quantity: Optional[Decimal] = None,
    preferred_supplier_id: Optional[int] = None,
    upc: Optional[str] = None,
    product_name: Optional[str] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Product:
    """
    Update product fields.
    
    Args:
        product_id: Product to update
        name: Optional new name
        package_unit: Optional new unit
        package_unit_quantity: Optional new quantity
        preferred_supplier_id: Optional new preferred supplier
        upc: Optional new UPC
        product_name: Optional new product name
        notes: Optional new notes
        session: Optional database session
        
    Returns:
        Updated Product instance
        
    Raises:
        ProductNotFoundError: If product doesn't exist
    """
    if session is not None:
        return _update_product_impl(
            product_id, name, package_unit, package_unit_quantity,
            preferred_supplier_id, upc, product_name, notes, session
        )
    
    with session_scope() as session:
        return _update_product_impl(
            product_id, name, package_unit, package_unit_quantity,
            preferred_supplier_id, upc, product_name, notes, session
        )


def _update_product_impl(
    product_id: int,
    name: Optional[str],
    package_unit: Optional[str],
    package_unit_quantity: Optional[Decimal],
    preferred_supplier_id: Optional[int],
    upc: Optional[str],
    product_name: Optional[str],
    notes: Optional[str],
    session: Session
) -> Product:
    """Implementation using provided session."""
    
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        raise ProductNotFoundError(f"Product with id {product_id} not found")
    
    # Update provided fields
    if name is not None:
        product.name = name
    if package_unit is not None:
        product.package_unit = package_unit
    if package_unit_quantity is not None:
        product.package_unit_quantity = package_unit_quantity
    if preferred_supplier_id is not None:
        product.preferred_supplier_id = preferred_supplier_id
    if upc is not None:
        product.upc = upc
    if product_name is not None:
        product.product_name = product_name
    if notes is not None:
        product.notes = notes
    
    session.flush()
    
    return product


def hide_product(
    product_id: int,
    session: Optional[Session] = None
) -> Product:
    """
    Hide a product (soft delete).
    
    Args:
        product_id: Product to hide
        session: Optional database session
        
    Returns:
        Updated Product instance
        
    Raises:
        ProductNotFoundError: If product doesn't exist
    """
    if session is not None:
        return _hide_product_impl(product_id, session)
    
    with session_scope() as session:
        return _hide_product_impl(product_id, session)


def _hide_product_impl(product_id: int, session: Session) -> Product:
    """Implementation using provided session."""
    
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        raise ProductNotFoundError(f"Product with id {product_id} not found")
    
    product.is_hidden = True
    session.flush()
    
    return product


def unhide_product(
    product_id: int,
    session: Optional[Session] = None
) -> Product:
    """
    Unhide a product (restore from soft delete).
    
    Args:
        product_id: Product to unhide
        session: Optional database session
        
    Returns:
        Updated Product instance
        
    Raises:
        ProductNotFoundError: If product doesn't exist
    """
    if session is not None:
        return _unhide_product_impl(product_id, session)
    
    with session_scope() as session:
        return _unhide_product_impl(product_id, session)


def _unhide_product_impl(product_id: int, session: Session) -> Product:
    """Implementation using provided session."""
    
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        raise ProductNotFoundError(f"Product with id {product_id} not found")
    
    product.is_hidden = False
    session.flush()
    
    return product


def delete_product(
    product_id: int,
    session: Optional[Session] = None
) -> None:
    """
    Delete a product (hard delete).
    
    Only allowed if product has no purchase history or inventory additions.
    If dependencies exist, raises ProductInUseError - caller should hide instead.
    
    Args:
        product_id: Product to delete
        session: Optional database session
        
    Raises:
        ProductNotFoundError: If product doesn't exist
        ProductInUseError: If product has dependencies
    """
    if session is not None:
        return _delete_product_impl(product_id, session)
    
    with session_scope() as session:
        return _delete_product_impl(product_id, session)


def _delete_product_impl(product_id: int, session: Session) -> None:
    """Implementation using provided session."""
    
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        raise ProductNotFoundError(f"Product with id {product_id} not found")
    
    # Check for dependencies
    purchase_count = session.query(Purchase).filter_by(product_id=product_id).count()
    if purchase_count > 0:
        raise ProductInUseError(
            f"Cannot delete product - {purchase_count} purchase(s) exist. "
            "Use hide_product() instead to preserve history."
        )
    
    # Safe to delete
    session.delete(product)
    session.flush()


def get_purchase_history(
    product_id: int,
    supplier_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    session: Optional[Session] = None
) -> List[Purchase]:
    """
    Get purchase history for a product.
    
    Args:
        product_id: Product to query
        supplier_id: Optional filter by supplier
        start_date: Optional filter by start date
        end_date: Optional filter by end date
        session: Optional database session
        
    Returns:
        List of Purchase instances sorted by date (newest first)
    """
    if session is not None:
        return _get_purchase_history_impl(
            product_id, supplier_id, start_date, end_date, session
        )
    
    with session_scope() as session:
        return _get_purchase_history_impl(
            product_id, supplier_id, start_date, end_date, session
        )


def _get_purchase_history_impl(
    product_id: int,
    supplier_id: Optional[int],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    session: Session
) -> List[Purchase]:
    """Implementation using provided session."""
    
    query = session.query(Purchase).filter_by(product_id=product_id)
    
    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)
    
    if start_date:
        query = query.filter(Purchase.purchase_date >= start_date)
    
    if end_date:
        query = query.filter(Purchase.purchase_date <= end_date)
    
    query = query.order_by(desc(Purchase.purchase_date))
    
    return query.all()


def get_last_purchase_price(
    product_id: int,
    supplier_id: Optional[int] = None,
    session: Optional[Session] = None
) -> Optional[Decimal]:
    """
    Get the most recent purchase price for a product.
    
    Args:
        product_id: Product to query
        supplier_id: Optional filter by supplier
        session: Optional database session
        
    Returns:
        Most recent unit_price, or None if no purchases
    """
    if session is not None:
        return _get_last_purchase_price_impl(product_id, supplier_id, session)
    
    with session_scope() as session:
        return _get_last_purchase_price_impl(product_id, supplier_id, session)


def _get_last_purchase_price_impl(
    product_id: int,
    supplier_id: Optional[int],
    session: Session
) -> Optional[Decimal]:
    """Implementation using provided session."""
    
    query = session.query(Purchase.unit_price).filter_by(product_id=product_id)
    
    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)
    
    query = query.order_by(desc(Purchase.purchase_date)).limit(1)
    
    result = query.first()
    
    return result[0] if result else None
```

#### New supplier_service.py

```python
"""
Supplier management service.

Provides CRUD operations for suppliers (stores, vendors).
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models import Supplier, Product, Purchase
from src.database import session_scope


class SupplierNotFoundError(Exception):
    """Raised when supplier lookup fails."""
    pass


class SupplierInUseError(Exception):
    """Raised when attempting to delete supplier with dependencies."""
    pass


def create_supplier(
    name: str,
    city: str,
    state: str,
    zip_code: str,
    street_address: Optional[str] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Supplier:
    """
    Create a new supplier.
    
    Args:
        name: Store or vendor name
        city: City name
        state: Two-letter state code (will be uppercased)
        zip_code: 5 or 9-digit ZIP code
        street_address: Optional street address
        notes: Optional notes
        session: Optional database session
        
    Returns:
        Created Supplier instance
        
    Raises:
        ValueError: If state code invalid
    """
    if session is not None:
        return _create_supplier_impl(
            name, city, state, zip_code, street_address, notes, session
        )
    
    with session_scope() as session:
        return _create_supplier_impl(
            name, city, state, zip_code, street_address, notes, session
        )


def _create_supplier_impl(
    name: str,
    city: str,
    state: str,
    zip_code: str,
    street_address: Optional[str],
    notes: Optional[str],
    session: Session
) -> Supplier:
    """Implementation using provided session."""
    
    # Validate state code
    state = state.upper()
    if len(state) != 2:
        raise ValueError(f"State code must be 2 characters, got: {state}")
    
    # TODO: Validate state against valid US state codes
    
    supplier = Supplier(
        name=name,
        city=city,
        state=state,
        zip_code=zip_code,
        street_address=street_address,
        notes=notes,
        is_active=True
    )
    
    session.add(supplier)
    session.flush()
    
    return supplier


def get_supplier(
    supplier_id: int,
    session: Optional[Session] = None
) -> Supplier:
    """
    Retrieve a supplier by ID.
    
    Args:
        supplier_id: Supplier ID to retrieve
        session: Optional database session
        
    Returns:
        Supplier instance
        
    Raises:
        SupplierNotFoundError: If supplier doesn't exist
    """
    if session is not None:
        return _get_supplier_impl(supplier_id, session)
    
    with session_scope() as session:
        return _get_supplier_impl(supplier_id, session)


def _get_supplier_impl(supplier_id: int, session: Session) -> Supplier:
    """Implementation using provided session."""
    
    supplier = session.query(Supplier).filter_by(id=supplier_id).first()
    
    if not supplier:
        raise SupplierNotFoundError(f"Supplier with id {supplier_id} not found")
    
    return supplier


def list_suppliers(
    include_inactive: bool = False,
    session: Optional[Session] = None
) -> List[Supplier]:
    """
    List all suppliers.
    
    Args:
        include_inactive: If True, include inactive suppliers
        session: Optional database session
        
    Returns:
        List of Supplier instances sorted by name
    """
    if session is not None:
        return _list_suppliers_impl(include_inactive, session)
    
    with session_scope() as session:
        return _list_suppliers_impl(include_inactive, session)


def _list_suppliers_impl(include_inactive: bool, session: Session) -> List[Supplier]:
    """Implementation using provided session."""
    
    query = session.query(Supplier)
    
    if not include_inactive:
        query = query.filter(Supplier.is_active == True)
    
    query = query.order_by(Supplier.name, Supplier.city)
    
    return query.all()


def deactivate_supplier(
    supplier_id: int,
    session: Optional[Session] = None
) -> Supplier:
    """
    Deactivate a supplier (soft delete).
    
    Sets is_active = False and clears preferred_supplier_id on affected products.
    
    Args:
        supplier_id: Supplier to deactivate
        session: Optional database session
        
    Returns:
        Updated Supplier instance
        
    Raises:
        SupplierNotFoundError: If supplier doesn't exist
    """
    if session is not None:
        return _deactivate_supplier_impl(supplier_id, session)
    
    with session_scope() as session:
        return _deactivate_supplier_impl(supplier_id, session)


def _deactivate_supplier_impl(supplier_id: int, session: Session) -> Supplier:
    """Implementation using provided session."""
    
    supplier = session.query(Supplier).filter_by(id=supplier_id).first()
    if not supplier:
        raise SupplierNotFoundError(f"Supplier with id {supplier_id} not found")
    
    # Clear preferred_supplier_id on affected products
    affected_count = session.query(Product).filter_by(
        preferred_supplier_id=supplier_id
    ).update({Product.preferred_supplier_id: None})
    
    # Deactivate supplier
    supplier.is_active = False
    session.flush()
    
    return supplier
```

### UI Changes

#### Products Tab (New)

```python
"""
Products tab for catalog management.

Displays product grid with filtering, search, and CRUD operations.
"""

import customtkinter as ctk
from typing import List, Optional, Callable
from src.models import Product, Ingredient, Supplier
from src.services import product_service, supplier_service, ingredient_service


class ProductsTab(ctk.CTkFrame):
    """
    Products catalog management tab.
    
    Features:
    - Grid view of products with sortable columns
    - Filter by ingredient, category, supplier
    - Search by product name
    - Add/Edit/Hide/Delete operations
    - Product detail view with purchase history
    """
    
    def __init__(self, master, service_integrator, **kwargs):
        super().__init__(master, **kwargs)
        
        self.service_integrator = service_integrator
        self.current_filters = {
            'ingredient_id': None,
            'category': None,
            'supplier_id': None,
            'include_hidden': False,
            'search_term': None
        }
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Configure tab layout."""
        
        # Header with Add button
        header = ctk.CTkFrame(self)
        header.pack(fill='x', padx=10, pady=5)
        
        ctk.CTkLabel(header, text="Products", font=("", 20, "bold")).pack(side='left')
        ctk.CTkButton(header, text="+ Add Product", command=self._show_add_product_dialog).pack(side='right')
        
        # Filters section
        filters = ctk.CTkFrame(self)
        filters.pack(fill='x', padx=10, pady=5)
        
        # Search box
        search_frame = ctk.CTkFrame(filters)
        search_frame.pack(fill='x', pady=(0, 5))
        
        ctk.CTkLabel(search_frame, text="Search:").pack(side='left', padx=(0, 5))
        self.search_entry = ctk.CTkEntry(search_frame, width=300)
        self.search_entry.pack(side='left', padx=(0, 5))
        self.search_entry.bind('<KeyRelease>', self._on_search_changed)
        
        ctk.CTkButton(search_frame, text="Clear", command=self._clear_search, width=60).pack(side='left')
        
        # Dropdown filters
        filter_row = ctk.CTkFrame(filters)
        filter_row.pack(fill='x')
        
        ctk.CTkLabel(filter_row, text="Ingredient:").pack(side='left', padx=(0, 5))
        self.ingredient_filter = ctk.CTkComboBox(filter_row, width=200, command=self._on_filter_changed)
        self.ingredient_filter.pack(side='left', padx=(0, 10))
        
        ctk.CTkLabel(filter_row, text="Category:").pack(side='left', padx=(0, 5))
        self.category_filter = ctk.CTkComboBox(filter_row, width=150, command=self._on_filter_changed)
        self.category_filter.pack(side='left', padx=(0, 10))
        
        ctk.CTkLabel(filter_row, text="Supplier:").pack(side='left', padx=(0, 5))
        self.supplier_filter = ctk.CTkComboBox(filter_row, width=200, command=self._on_filter_changed)
        self.supplier_filter.pack(side='left', padx=(0, 10))
        
        self.show_hidden_var = ctk.BooleanVar(value=False)
        self.show_hidden_check = ctk.CTkCheckBox(
            filter_row,
            text="Show Hidden",
            variable=self.show_hidden_var,
            command=self._on_filter_changed
        )
        self.show_hidden_check.pack(side='left', padx=(10, 0))
        
        # Products grid (using ttk.Treeview for sortable table)
        from tkinter import ttk
        
        grid_frame = ctk.CTkFrame(self)
        grid_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(grid_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Treeview
        columns = ('name', 'ingredient', 'category', 'pref_supplier', 'last_purchase', 'last_price')
        self.tree = ttk.Treeview(grid_frame, columns=columns, show='headings', yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.tree.yview)
        
        # Column headings
        self.tree.heading('name', text='Name')
        self.tree.heading('ingredient', text='Ingredient')
        self.tree.heading('category', text='Category')
        self.tree.heading('pref_supplier', text='Preferred Supplier')
        self.tree.heading('last_purchase', text='Last Purchase')
        self.tree.heading('last_price', text='Last Price')
        
        # Column widths
        self.tree.column('name', width=200)
        self.tree.column('ingredient', width=150)
        self.tree.column('category', width=100)
        self.tree.column('pref_supplier', width=150)
        self.tree.column('last_purchase', width=100)
        self.tree.column('last_price', width=80)
        
        self.tree.pack(fill='both', expand=True)
        
        # Double-click to view details
        self.tree.bind('<Double-Button-1>', self._on_product_double_click)
    
    def _load_data(self):
        """Load products and populate grid."""
        
        # Load filter options
        ingredients = self.service_integrator.execute_operation(
            operation_type=OperationType.LIST_INGREDIENTS
        )
        self.ingredient_filter.configure(values=['All'] + [i.display_name for i in ingredients])
        self.ingredient_filter.set('All')
        
        categories = list(set(i.category for i in ingredients))
        self.category_filter.configure(values=['All'] + sorted(categories))
        self.category_filter.set('All')
        
        suppliers = self.service_integrator.execute_operation(
            operation_type=OperationType.LIST_SUPPLIERS
        )
        self.supplier_filter.configure(values=['All'] + [s.display_name for s in suppliers])
        self.supplier_filter.set('All')
        
        # Load products
        self._refresh_grid()
    
    def _refresh_grid(self):
        """Reload products based on current filters."""
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Load filtered products
        products = self.service_integrator.execute_operation(
            operation_type=OperationType.LIST_PRODUCTS,
            **self.current_filters
        )
        
        # Populate grid
        for product in products:
            # Get last purchase info
            last_purchase = self._get_last_purchase(product)
            
            values = (
                product.name,
                product.ingredient.display_name,
                product.ingredient.category,
                product.preferred_supplier.display_name if product.preferred_supplier else '-',
                last_purchase['date'] if last_purchase else '-',
                f"${last_purchase['price']:.2f}" if last_purchase else '-'
            )
            
            item_id = self.tree.insert('', 'end', values=values, tags=(str(product.id),))
            
            # Visual indicator for hidden products
            if product.is_hidden:
                self.tree.item(item_id, tags=(str(product.id), 'hidden'))
        
        # Apply styling
        self.tree.tag_configure('hidden', foreground='gray')
    
    def _get_last_purchase(self, product: Product) -> Optional[dict]:
        """Get last purchase info for a product."""
        purchases = self.service_integrator.execute_operation(
            operation_type=OperationType.GET_PURCHASE_HISTORY,
            product_id=product.id,
            limit=1
        )
        
        if purchases:
            purchase = purchases[0]
            return {
                'date': purchase.purchase_date.strftime('%Y-%m-%d'),
                'price': purchase.unit_price
            }
        
        return None
    
    def _on_filter_changed(self, *args):
        """Handle filter selection change."""
        
        # Update filter dict
        ingredient_val = self.ingredient_filter.get()
        self.current_filters['ingredient_id'] = self._get_ingredient_id(ingredient_val) if ingredient_val != 'All' else None
        
        category_val = self.category_filter.get()
        self.current_filters['category'] = category_val if category_val != 'All' else None
        
        supplier_val = self.supplier_filter.get()
        self.current_filters['supplier_id'] = self._get_supplier_id(supplier_val) if supplier_val != 'All' else None
        
        self.current_filters['include_hidden'] = self.show_hidden_var.get()
        
        # Refresh grid
        self._refresh_grid()
    
    def _on_search_changed(self, event):
        """Handle search box input."""
        search_term = self.search_entry.get().strip()
        self.current_filters['search_term'] = search_term if search_term else None
        self._refresh_grid()
    
    def _clear_search(self):
        """Clear search box and refresh."""
        self.search_entry.delete(0, 'end')
        self.current_filters['search_term'] = None
        self._refresh_grid()
    
    def _show_add_product_dialog(self):
        """Show dialog for adding new product."""
        dialog = AddProductDialog(self, self.service_integrator)
        self.wait_window(dialog)
        
        # Refresh grid if product was added
        if dialog.result:
            self._refresh_grid()
    
    def _on_product_double_click(self, event):
        """Handle double-click on product row."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        product_id = int(item['tags'][0])
        
        # Show product detail dialog
        dialog = ProductDetailDialog(self, self.service_integrator, product_id)
        self.wait_window(dialog)
        
        # Refresh grid if changes made
        if dialog.modified:
            self._refresh_grid()
```

**Layout Diagram:**

```
┌────────────────────────────────────────────────────────────────┐
│ Products                                        [+ Add Product] │
├────────────────────────────────────────────────────────────────┤
│ Search: [________________________]  [Clear]                    │
│                                                                 │
│ Ingredient: [All ▼]  Category: [All ▼]  Supplier: [All ▼]     │
│ ☐ Show Hidden Products                                         │
├────────────────────────────────────────────────────────────────┤
│ Name           │Ingredient│Category│Pref Supp│Last Purch│Price│
├────────────────────────────────────────────────────────────────┤
│ Choc Chips 10kg│Semisw Ch│Baking  │Costco   │2024-12-15│$600 │
│ AP Flour 10lb  │AP Flour │Baking  │Wegmans  │2024-11-20│$8.99│
│ Butter 1lb     │Butter   │Dairy   │-        │2024-12-10│$4.50│
│ ...            │...      │...     │...      │...       │...  │
└────────────────────────────────────────────────────────────────┘
```

---

## Migration Strategy

Per Constitution VI (Schema Change Strategy), schema changes handled via export/reset/import cycle.

### Step 1: Pre-Migration Export

```bash
# Export all data before schema change
python -m src.cli.main export --output docs/migrations/pre_f027_export.json
```

### Step 2: Schema Update

1. Create Supplier table
2. Create Purchase table
3. Add Product.preferred_supplier_id (nullable)
4. Add Product.is_hidden (default False)
5. Add InventoryAddition.purchase_id (temporarily nullable for migration)
6. Keep InventoryAddition.price_paid (temporarily for migration)

### Step 3: Data Transformation

```python
# docs/migrations/transform_f027_data.py

def transform_for_f027(export_data: dict) -> dict:
    """
    Transform exported data for Feature 027 schema.
    
    Creates:
    - "Unknown Supplier" for historical purchases
    - Purchase record for each InventoryAddition
    - Links InventoryAddition.purchase_id to new Purchase
    """
    
    # Create Unknown Supplier
    unknown_supplier = {
        'id': 1,
        'uuid': str(uuid4()),
        'name': 'Unknown',
        'city': 'Unknown',
        'state': 'XX',
        'zip_code': '00000',
        'street_address': None,
        'notes': 'Default supplier for migrated inventory additions',
        'is_active': True,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    export_data['suppliers'] = [unknown_supplier]
    
    # Create Purchase records from InventoryAdditions
    purchases = []
    purchase_id = 1
    
    for addition in export_data.get('inventory_additions', []):
        if 'price_paid' in addition and addition['price_paid'] is not None:
            purchase = {
                'id': purchase_id,
                'uuid': str(uuid4()),
                'product_id': addition['product_id'],
                'supplier_id': 1,  # Unknown Supplier
                'purchase_date': addition['addition_date'],
                'unit_price': addition['price_paid'],
                'quantity_purchased': 1,  # Assume 1 unit per addition
                'notes': None,
                'created_at': addition.get('created_at', datetime.utcnow().isoformat())
            }
            purchases.append(purchase)
            
            # Link addition to purchase
            addition['purchase_id'] = purchase_id
            
            purchase_id += 1
    
    export_data['purchases'] = purchases
    
    # Update products
    for product in export_data.get('products', []):
        product['preferred_supplier_id'] = None
        product['is_hidden'] = False
    
    # Remove price_paid from inventory_additions (now in Purchase)
    for addition in export_data.get('inventory_additions', []):
        if 'price_paid' in addition:
            del addition['price_paid']
    
    return export_data
```

### Step 4: Import Transformed Data

```bash
# Reset database (delete and recreate with new schema)
python -m src.cli.main db reset

# Transform exported data
python docs/migrations/transform_f027_data.py \
    --input docs/migrations/pre_f027_export.json \
    --output docs/migrations/f027_transformed_export.json

# Import transformed data
python -m src.cli.main import --input docs/migrations/f027_transformed_export.json
```

### Step 5: Schema Finalization

After successful import:
1. Make InventoryAddition.purchase_id NOT NULL
2. Drop InventoryAddition.price_paid column
3. Add foreign key constraints

### Step 6: Validation

```python
# Verify migration success
def validate_f027_migration(session):
    """Validate Feature 027 migration."""
    
    from src.models import Product, Supplier, Purchase, InventoryAddition
    
    # Verify all products have required fields
    products = session.query(Product).all()
    for product in products:
        assert product.is_hidden is not None
        # preferred_supplier_id can be NULL
    
    # Verify Unknown Supplier exists
    unknown = session.query(Supplier).filter_by(name='Unknown').first()
    assert unknown is not None
    assert unknown.city == 'Unknown'
    
    # Verify all inventory additions have purchase_id
    additions = session.query(InventoryAddition).all()
    for addition in additions:
        assert addition.purchase_id is not None
        
        # Verify purchase exists
        purchase = session.query(Purchase).get(addition.purchase_id)
        assert purchase is not None
    
    print(f"✓ Validated {len(products)} products")
    print(f"✓ Validated {len(additions)} inventory additions")
    print(f"✓ All inventory additions linked to purchases")
```

---

## Testing Strategy

### Unit Tests

**Service Layer:**

```python
# tests/services/test_product_service.py

class TestProductService:
    """Test suite for product catalog management."""
    
    def test_create_product(self, session, test_ingredient):
        """Verify product creation with required fields."""
        product = product_service.create_product(
            name="Test Flour 10lb",
            ingredient_id=test_ingredient.id,
            package_unit="lb",
            package_unit_quantity=Decimal("10.0"),
            session=session
        )
        
        assert product.id is not None
        assert product.name == "Test Flour 10lb"
        assert product.ingredient_id == test_ingredient.id
        assert product.is_hidden == False
        assert product.preferred_supplier_id is None
    
    def test_create_product_with_preferred_supplier(self, session, test_ingredient, test_supplier):
        """Verify product creation with optional preferred supplier."""
        product = product_service.create_product(
            name="Test Flour 10lb",
            ingredient_id=test_ingredient.id,
            package_unit="lb",
            package_unit_quantity=Decimal("10.0"),
            preferred_supplier_id=test_supplier.id,
            session=session
        )
        
        assert product.preferred_supplier_id == test_supplier.id
        assert product.preferred_supplier.name == test_supplier.name
    
    def test_list_products_filter_by_ingredient(self, session, multiple_products):
        """Verify filtering products by ingredient."""
        flour_products = product_service.list_products(
            ingredient_id=multiple_products['flour_ingredient'].id,
            session=session
        )
        
        assert len(flour_products) == 2  # Two flour products in fixture
        assert all(p.ingredient_id == multiple_products['flour_ingredient'].id for p in flour_products)
    
    def test_list_products_exclude_hidden(self, session, hidden_product, active_product):
        """Verify hidden products excluded by default."""
        products = product_service.list_products(
            include_hidden=False,
            session=session
        )
        
        assert active_product in products
        assert hidden_product not in products
    
    def test_hide_product(self, session, test_product):
        """Verify product hiding (soft delete)."""
        product_service.hide_product(test_product.id, session=session)
        
        session.refresh(test_product)
        assert test_product.is_hidden == True
    
    def test_delete_product_without_dependencies(self, session, test_product):
        """Verify product deletion when no dependencies exist."""
        product_id = test_product.id
        
        product_service.delete_product(product_id, session=session)
        
        # Product should not exist
        product = session.query(Product).get(product_id)
        assert product is None
    
    def test_delete_product_with_purchases_fails(self, session, product_with_purchases):
        """Verify deletion blocked when purchases exist."""
        with pytest.raises(ProductInUseError, match="purchase"):
            product_service.delete_product(product_with_purchases.id, session=session)
    
    def test_get_purchase_history(self, session, product_with_multiple_purchases):
        """Verify purchase history retrieval sorted by date."""
        history = product_service.get_purchase_history(
            product_id=product_with_multiple_purchases.id,
            session=session
        )
        
        assert len(history) == 3
        # Verify sorted by date descending
        assert history[0].purchase_date > history[1].purchase_date
        assert history[1].purchase_date > history[2].purchase_date
    
    def test_get_last_purchase_price(self, session, product_with_multiple_purchases):
        """Verify last purchase price retrieval."""
        last_price = product_service.get_last_purchase_price(
            product_id=product_with_multiple_purchases.id,
            session=session
        )
        
        # Should return most recent purchase price
        assert last_price == Decimal("600.00")  # From fixture
    
    def test_get_last_purchase_price_by_supplier(self, session, product_with_multiple_suppliers):
        """Verify last purchase price filtered by supplier."""
        costco_price = product_service.get_last_purchase_price(
            product_id=product_with_multiple_suppliers.id,
            supplier_id=product_with_multiple_suppliers['costco_id'],
            session=session
        )
        
        wegmans_price = product_service.get_last_purchase_price(
            product_id=product_with_multiple_suppliers.id,
            supplier_id=product_with_multiple_suppliers['wegmans_id'],
            session=session
        )
        
        assert costco_price != wegmans_price
```

**Supplier Service:**

```python
# tests/services/test_supplier_service.py

class TestSupplierService:
    """Test suite for supplier management."""
    
    def test_create_supplier(self, session):
        """Verify supplier creation with required fields."""
        supplier = supplier_service.create_supplier(
            name="Test Store",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session
        )
        
        assert supplier.id is not None
        assert supplier.name == "Test Store"
        assert supplier.state == "MA"
        assert supplier.is_active == True
    
    def test_create_supplier_uppercases_state(self, session):
        """Verify state code is uppercased."""
        supplier = supplier_service.create_supplier(
            name="Test Store",
            city="Boston",
            state="ma",
            zip_code="02101",
            session=session
        )
        
        assert supplier.state == "MA"
    
    def test_deactivate_supplier_clears_product_preferences(self, session, supplier_with_preferred_products):
        """Verify deactivating supplier clears product.preferred_supplier_id."""
        supplier = supplier_with_preferred_products['supplier']
        product_ids = supplier_with_preferred_products['product_ids']
        
        supplier_service.deactivate_supplier(supplier.id, session=session)
        
        # Verify supplier deactivated
        session.refresh(supplier)
        assert supplier.is_active == False
        
        # Verify products' preferred_supplier_id cleared
        for product_id in product_ids:
            product = session.query(Product).get(product_id)
            assert product.preferred_supplier_id is None
```

### Integration Tests

**UI Workflow:**

```python
# tests/integration/test_products_tab_ui.py

class TestProductsTabUI:
    """Integration tests for Products tab UI."""
    
    def test_filter_by_ingredient(self, products_tab, flour_products):
        """Verify ingredient filter updates grid."""
        # Select ingredient in filter
        products_tab.ingredient_filter.set("All-Purpose Flour")
        products_tab._on_filter_changed()
        
        # Verify grid shows only flour products
        items = products_tab.tree.get_children()
        assert len(items) == len(flour_products)
    
    def test_search_products(self, products_tab):
        """Verify search box filters by name."""
        # Enter search term
        products_tab.search_entry.insert(0, "chocolate")
        products_tab._on_search_changed(None)
        
        # Verify only chocolate products shown
        items = products_tab.tree.get_children()
        for item in items:
            values = products_tab.tree.item(item)['values']
            assert 'chocolate' in values[0].lower()
    
    def test_show_hidden_products(self, products_tab, hidden_product):
        """Verify Show Hidden checkbox reveals hidden products."""
        # Initially hidden product not shown
        items = products_tab.tree.get_children()
        visible_ids = [products_tab.tree.item(item)['tags'][0] for item in items]
        assert str(hidden_product.id) not in visible_ids
        
        # Enable Show Hidden
        products_tab.show_hidden_var.set(True)
        products_tab._on_filter_changed()
        
        # Now hidden product visible
        items = products_tab.tree.get_children()
        visible_ids = [products_tab.tree.item(item)['tags'][0] for item in items]
        assert str(hidden_product.id) in visible_ids
```

---

## Acceptance Criteria

### Must Have (MVP)

1. ✅ Schema updated with Supplier, Purchase tables
2. ✅ Product table has preferred_supplier_id, is_hidden fields
3. ✅ InventoryAddition references purchase_id (not price_paid)
4. ✅ product_service.py implements CRUD operations
5. ✅ supplier_service.py implements supplier management
6. ✅ Products tab displays grid with filtering
7. ✅ Filter by ingredient, category, supplier works
8. ✅ Search by product name works
9. ✅ Show/hide hidden products toggle works
10. ✅ Product detail view shows purchase history
11. ✅ Hide product (soft delete) preserves history
12. ✅ Delete product blocked if purchases exist
13. ✅ Service layer tests achieve >70% coverage
14. ✅ Migration script transforms existing data successfully
15. ✅ All existing tests pass after migration

### Should Have (Post-MVP)

1. ⬜ Bulk product import from CSV
2. ⬜ Product duplicate detection ("similar product exists")
3. ⬜ Purchase history export to CSV
4. ⬜ Supplier performance metrics (avg price, purchase frequency)

### Could Have (Future)

1. ⬜ Product barcode scanning integration
2. ⬜ Automated price updates from web scraping
3. ⬜ Multi-supplier price comparison view
4. ⬜ Product lifecycle status (active/phasing out/discontinued)
5. ⬜ Inventory reorder point alerts

---

## Risks and Mitigation

### Risk: Migration Complexity

**Risk:** Transforming InventoryAddition.price_paid to Purchase records could fail for edge cases.

**Mitigation:**
- Comprehensive validation script post-migration
- Unknown Supplier created for all historical data (acceptable tradeoff)
- Export/import cycle allows rollback to pre-migration state
- Dry-run transformation script before actual migration

### Risk: Performance with Large Product Catalogs

**Risk:** Product grid could become slow with 1000+ products.

**Mitigation:**
- Pagination implemented if >100 products (future enhancement)
- Filtering reduces result set before display
- Database indexes on commonly filtered columns
- Grid virtualization (only render visible rows)

### Risk: Supplier Data Quality

**Risk:** Users may enter inconsistent supplier names ("Costco" vs "Costco Wholesale").

**Mitigation:**
- Type-ahead supplier selection (reduces duplicates)
- Display name includes city/state for disambiguation
- Future: Supplier merge tool for cleanup
- Accept imperfection for MVP (can clean up later)

### Risk: Price History Data Volume

**Risk:** Purchase table could grow large over time (thousands of records).

**Mitigation:**
- Indexes on product_id and purchase_date enable efficient queries
- UI limits purchase history display to most recent N records
- Archival strategy deferred to web phase (not needed for desktop)

---

## Open Questions

1. **Supplier Disambiguation:**
   Should "Costco Waltham MA" and "Costco Burlington MA" be separate suppliers or same supplier with different locations?
   - **Recommendation:** Separate suppliers. City/state required fields support this model. Future: add supplier_chain_id for grouping.

2. **Purchase Quantity Granularity:**
   If user buys 5 bags of flour but adds them to inventory over time (e.g., 2 today, 3 tomorrow), should we split the purchase?
   - **Recommendation:** No. One purchase = one shopping transaction. User can create multiple inventory additions referencing the same purchase. FIFO handles timing.

3. **Price Update Frequency:**
   Should UI prompt user to update product prices when they vary significantly from last purchase?
   - **Recommendation:** Not in Feature 027. Feature 029 will show last price as suggestion; user can override. Variance alerts deferred to future analytics.

4. **Hidden Product Unhide Workflow:**
   Should unhiding a product require confirmation or just be a single-click action?
   - **Recommendation:** Single-click via Products tab filter. Unhiding is low-risk (doesn't affect historical data).

5. **Preferred Supplier Auto-Assignment:**
   When creating product inline (Feature 029), should preferred_supplier_id be set to first purchase supplier?
   - **Decision made:** Yes (Option A). User can change later via Product Management.

---

## References

### Existing Features

- **Feature 020:** Enhanced Data Import (catalog import foundation)
- **Feature 021:** Field Naming Consistency (package_unit terminology)
- **Feature 013:** Production & Inventory Tracking (FIFO consumption)

### Architecture Documents

- **Constitution Principle II:** Data Integrity & FIFO Accuracy
- **Constitution Principle III:** Future-Proof Schema
- **Constitution Principle VI:** Schema Change Strategy (export/reset/import)

### Code References

- `src/models/product.py` - Product model
- `src/models/inventory_addition.py` - InventoryAddition model
- `src/services/inventory_service.py` - Existing inventory operations
- `src/ui/tabs/inventory_tab.py` - Current inventory UI

---

## Appendix: Schema SQL

```sql
-- Supplier table
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    street_address TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL CHECK (LENGTH(state) = 2 AND state = UPPER(state)),
    zip_code TEXT NOT NULL,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_supplier_name_city ON suppliers(name, city);
CREATE INDEX idx_supplier_active ON suppliers(is_active);

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

CREATE INDEX idx_purchase_product ON purchases(product_id);
CREATE INDEX idx_purchase_supplier ON purchases(supplier_id);
CREATE INDEX idx_purchase_date ON purchases(purchase_date);
CREATE INDEX idx_purchase_product_date ON purchases(product_id, purchase_date);

-- Product table updates
ALTER TABLE products
ADD COLUMN preferred_supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL;

ALTER TABLE products
ADD COLUMN is_hidden INTEGER NOT NULL DEFAULT 0;

CREATE INDEX idx_product_preferred_supplier ON products(preferred_supplier_id);
CREATE INDEX idx_product_hidden ON products(is_hidden);

-- InventoryAddition table updates
ALTER TABLE inventory_additions
ADD COLUMN purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE RESTRICT;

CREATE INDEX idx_inventory_addition_purchase ON inventory_additions(purchase_id);

-- Drop price_paid column (after migration complete)
-- ALTER TABLE inventory_additions DROP COLUMN price_paid;
```

---

**Version:** 1.0  
**Last Updated:** 2025-12-22  
**Next Feature:** 028 - Purchase Tracking & Enhanced Costing
