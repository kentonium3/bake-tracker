---
work_package_id: "WP04"
subtasks:
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
title: "Product Catalog Service"
phase: "Phase 2 - Service Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-22T14:35:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Product Catalog Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Implement product_catalog_service.py with CRUD, filtering, and purchase history.

**Success Criteria**:
- [ ] Product listing with filters and search works (FR-014 through FR-018)
- [ ] Hide/unhide products works (FR-003)
- [ ] Delete blocked when dependencies exist (FR-004, FR-005)
- [ ] Purchase history retrieval works (FR-012)
- [ ] Test coverage >70%

## Context & Constraints

**Reference Documents**:
- Session Management: `CLAUDE.md` (CRITICAL)
- Spec requirements: FR-001 through FR-006, FR-011 through FR-013
- Query patterns: `kitty-specs/027-product-catalog-management/data-model.md`

**Note**: This service works with the EXISTING Product model (enhanced in WP02), not creating a new one.

## Subtasks & Detailed Guidance

### T028 – Create product_catalog_service.py

**Purpose**: Establish service file with session pattern.

**Steps**:
1. Create `src/services/product_catalog_service.py`
2. Add imports:
```python
from typing import Optional, List, Dict, Any
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import Product, Purchase, Ingredient, InventoryAddition
from src.services.database import session_scope
```

**Files**: `src/services/product_catalog_service.py` (NEW)

### T029 – Implement get_products with filters

**Purpose**: Retrieve products with optional filtering (FR-014 through FR-018).

**Steps**:
```python
def get_products(
    include_hidden: bool = False,
    ingredient_id: Optional[int] = None,
    category: Optional[str] = None,
    supplier_id: Optional[int] = None,
    search: Optional[str] = None,
    session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Get products with optional filters and last purchase price."""
    ...
    query = session.query(Product)

    # Filter hidden (FR-018)
    if not include_hidden:
        query = query.filter(Product.is_hidden == False)

    # Filter by ingredient (FR-014)
    if ingredient_id:
        query = query.filter(Product.ingredient_id == ingredient_id)

    # Filter by category via ingredient (FR-015)
    if category:
        query = query.join(Ingredient).filter(Ingredient.category == category)

    # Filter by preferred supplier (FR-016)
    if supplier_id:
        query = query.filter(Product.preferred_supplier_id == supplier_id)

    # Search by name (FR-017)
    if search:
        query = query.filter(Product.product_name.ilike(f"%{search}%"))

    products = query.order_by(Product.product_name).all()

    # Enrich with last price
    result = []
    for p in products:
        data = p.to_dict()
        last_purchase = _get_last_purchase(p.id, session)
        data["last_price"] = last_purchase["unit_price"] if last_purchase else None
        data["last_purchase_date"] = last_purchase["purchase_date"] if last_purchase else None
        result.append(data)
    return result
```

### T030 – Implement get_product_with_last_price

**Purpose**: Get single product with its most recent purchase price.

**Steps**:
```python
def get_product_with_last_price(
    product_id: int,
    session: Optional[Session] = None
) -> Optional[Dict[str, Any]]:
    """Get product by ID with last purchase price."""
    ...
    product = session.query(Product).get(product_id)
    if not product:
        return None
    data = product.to_dict()
    last_purchase = _get_last_purchase(product_id, session)
    data["last_price"] = last_purchase["unit_price"] if last_purchase else None
    data["last_purchase_date"] = last_purchase["purchase_date"] if last_purchase else None
    return data

def _get_last_purchase(product_id: int, session: Session) -> Optional[Dict[str, Any]]:
    """Internal helper to get most recent purchase."""
    purchase = session.query(Purchase).filter(
        Purchase.product_id == product_id
    ).order_by(Purchase.purchase_date.desc()).first()
    return purchase.to_dict() if purchase else None
```

### T031 – Implement create_product

**Purpose**: Create new product (FR-001, FR-002).

**Steps**:
```python
def create_product(
    product_name: str,
    ingredient_id: int,
    package_unit: str,
    package_quantity: float,
    preferred_supplier_id: Optional[int] = None,
    brand: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict[str, Any]:
    """Create a new product."""
    ...
    product = Product(
        product_name=product_name,
        ingredient_id=ingredient_id,
        package_unit=package_unit,
        package_quantity=package_quantity,
        preferred_supplier_id=preferred_supplier_id,
        brand=brand,
        is_hidden=False
    )
    session.add(product)
    session.flush()
    return product.to_dict()
```

### T032 – Implement update_product

**Purpose**: Update product attributes.

**Steps**:
```python
def update_product(
    product_id: int,
    session: Optional[Session] = None,
    **kwargs
) -> Dict[str, Any]:
    """Update product attributes."""
    ...
    product = session.query(Product).get(product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")

    allowed_fields = {
        "product_name", "ingredient_id", "package_unit",
        "package_quantity", "preferred_supplier_id", "brand"
    }
    for key, value in kwargs.items():
        if key in allowed_fields:
            setattr(product, key, value)
    session.flush()
    return product.to_dict()
```

### T033 – Implement hide_product and unhide_product

**Purpose**: Soft delete/restore products (FR-003).

**Steps**:
```python
def hide_product(product_id: int, session: Optional[Session] = None) -> Dict[str, Any]:
    """Hide product (soft delete)."""
    ...
    product.is_hidden = True
    session.flush()
    return product.to_dict()

def unhide_product(product_id: int, session: Optional[Session] = None) -> Dict[str, Any]:
    """Unhide product (restore)."""
    ...
    product.is_hidden = False
    session.flush()
    return product.to_dict()
```

### T034 – Implement delete_product with dependency check

**Purpose**: Hard delete only if no dependencies (FR-004, FR-005).

**Steps**:
```python
def delete_product(product_id: int, session: Optional[Session] = None) -> bool:
    """Delete product if no purchases or inventory exist."""
    ...
    # Check for purchases (FR-004)
    purchase_count = session.query(Purchase).filter(
        Purchase.product_id == product_id
    ).count()
    if purchase_count > 0:
        raise ValueError(f"Cannot delete product with {purchase_count} purchases. Hide instead.")

    # Check for inventory
    inventory_count = session.query(InventoryAddition).filter(
        InventoryAddition.product_id == product_id
    ).count()
    if inventory_count > 0:
        raise ValueError(f"Cannot delete product with {inventory_count} inventory items. Hide instead.")

    session.delete(product)
    session.flush()
    return True
```

### T035 – Implement get_purchase_history

**Purpose**: Get all purchases for a product (FR-012).

**Steps**:
```python
def get_purchase_history(
    product_id: int,
    session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Get purchase history for product, sorted by date DESC."""
    ...
    purchases = session.query(Purchase).filter(
        Purchase.product_id == product_id
    ).order_by(Purchase.purchase_date.desc()).all()

    result = []
    for p in purchases:
        data = p.to_dict()
        # Include supplier name for display
        if p.supplier:
            data["supplier_name"] = p.supplier.name
            data["supplier_location"] = f"{p.supplier.city}, {p.supplier.state}"
        result.append(data)
    return result
```

### T036 – Implement create_purchase

**Purpose**: Record a new purchase transaction (FR-011).

**Steps**:
```python
def create_purchase(
    product_id: int,
    supplier_id: int,
    purchase_date: date,
    unit_price: Decimal,
    quantity_purchased: int,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict[str, Any]:
    """Create a purchase record."""
    ...
    if unit_price < 0:
        raise ValueError("Unit price cannot be negative")
    if quantity_purchased <= 0:
        raise ValueError("Quantity must be positive")

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
    return purchase.to_dict()
```

### T037 – Implement get_products_by_category

**Purpose**: Convenience method for category filtering.

**Steps**:
```python
def get_products_by_category(
    category: str,
    include_hidden: bool = False,
    session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Get products by ingredient category."""
    return get_products(category=category, include_hidden=include_hidden, session=session)
```

### T038 – Write product catalog service tests

**Purpose**: Achieve >70% coverage.

**Steps**:
Create `src/tests/services/test_product_catalog_service.py`:
- `test_get_products_excludes_hidden`
- `test_get_products_includes_hidden`
- `test_get_products_filter_by_ingredient`
- `test_get_products_filter_by_category`
- `test_get_products_filter_by_supplier`
- `test_get_products_search`
- `test_get_product_with_last_price`
- `test_create_product`
- `test_update_product`
- `test_hide_product`
- `test_unhide_product`
- `test_delete_product_success`
- `test_delete_product_with_purchases_fails`
- `test_delete_product_with_inventory_fails`
- `test_get_purchase_history`
- `test_create_purchase`
- `test_create_purchase_validates_price`

**Files**: `src/tests/services/test_product_catalog_service.py` (NEW)

## Test Strategy

**Coverage Target**: >70% for product_catalog_service.py

**Commands**:
```bash
pytest src/tests/services/test_product_catalog_service.py -v --cov=src.services.product_catalog_service
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| N+1 query for last_price | Could optimize with subquery; acceptable for holiday scale |
| Session detachment | Return dicts consistently |
| Category filter misses products | Ensure join is correct; test explicitly |

## Definition of Done Checklist

- [ ] All service functions implemented with session pattern
- [ ] get_products supports all filter combinations
- [ ] Hide/unhide toggle works
- [ ] Delete checks purchases AND inventory
- [ ] Purchase history returns sorted by date DESC
- [ ] Tests pass with >70% coverage

## Review Guidance

**Key Checkpoints**:
1. Every function follows session pattern
2. get_products enriches with last_price
3. delete_product checks both purchases AND inventory
4. Purchase history includes supplier name
5. Run coverage report

## Activity Log

- 2025-12-22T14:35:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
