# Quickstart: Feature 027 - Product Catalog Management

**Branch**: `027-product-catalog-management`
**Worktree**: `.worktrees/027-product-catalog-management/`

## Prerequisites

- Python 3.10+
- Virtual environment activated
- Dependencies installed: `pip install -r requirements.txt`

## Key Files to Review

Before implementing, read these files:

1. **Specification**: `kitty-specs/027-product-catalog-management/spec.md`
2. **Data Model**: `kitty-specs/027-product-catalog-management/data-model.md`
3. **Research Decisions**: `kitty-specs/027-product-catalog-management/research.md`
4. **Session Management**: `CLAUDE.md` (Session Management section - CRITICAL)

## Development Setup

```bash
# Navigate to worktree
cd .worktrees/027-product-catalog-management

# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Verify you're on the feature branch
git branch --show-current  # Should show: 027-product-catalog-management

# Run existing tests to ensure clean baseline
pytest src/tests -v
```

## New Models Overview

### Supplier (`src/models/supplier.py`)

```python
class Supplier(BaseModel):
    name: str              # Required: "Costco", "Wegmans"
    city: str              # Required: "Waltham"
    state: str             # Required: 2-letter code "MA"
    zip_code: str          # Required: "02451"
    street_address: str    # Optional
    is_active: bool        # Default True, soft delete flag
```

### Purchase (`src/models/purchase.py`)

```python
class Purchase(BaseModel):
    product_id: int        # FK to Product, RESTRICT delete
    supplier_id: int       # FK to Supplier, RESTRICT delete
    purchase_date: date    # When purchased
    unit_price: Decimal    # Price per package unit
    quantity_purchased: int # Number of units
```

### Product Updates (`src/models/product.py`)

```python
# Add to existing Product model:
preferred_supplier_id: int  # FK to Supplier, SET NULL on delete
is_hidden: bool             # Default False, soft delete flag
```

### InventoryAddition Updates (`src/models/inventory_addition.py`)

```python
# Add to existing InventoryAddition model:
purchase_id: int            # FK to Purchase, RESTRICT delete
# Deprecate: price_paid (migrate to Purchase.unit_price)
```

## Service Patterns

All service functions MUST follow the session pattern per CLAUDE.md:

```python
def create_supplier(
    name: str,
    city: str,
    state: str,
    zip_code: str,
    session: Optional[Session] = None  # REQUIRED parameter
) -> Supplier:
    if session is not None:
        return _create_supplier_impl(name, city, state, zip_code, session)
    with session_scope() as session:
        return _create_supplier_impl(name, city, state, zip_code, session)
```

## Testing Commands

```bash
# Run all tests
pytest src/tests -v

# Run with coverage
pytest src/tests -v --cov=src --cov-report=term-missing

# Run specific service tests
pytest src/tests/services/test_supplier_service.py -v
pytest src/tests/services/test_product_catalog_service.py -v

# Run integration tests
pytest src/tests/integration/test_product_catalog.py -v
```

## Work Package Sequence

1. **WP01**: Supplier Model → verify imports
2. **WP02**: Purchase Model + Product/InventoryAddition updates → verify relationships
3. **WP03**: Supplier Service → verify tests pass
4. **WP04**: Product Catalog Service → verify >70% coverage
5. **WP05**: Products Tab Frame → verify renders
6. **WP06**: Add Product Dialog → verify form works
7. **WP07**: Product Detail Dialog → verify history displays
8. **WP08**: Import/Export Updates → verify round-trip
9. **WP09**: Migration Transformation → verify data preserved

## Common Gotchas

1. **Session detachment**: Never modify ORM objects after exiting `session_scope()`. Pass session to nested functions.

2. **State code validation**: Supplier.state must be 2-letter uppercase. Validate in service layer.

3. **RESTRICT deletes**: Cannot delete Product/Supplier with purchases. Offer hide/deactivate instead.

4. **Migration order**: Export data BEFORE modifying models. Transform JSON BEFORE import.

## Quick Reference

| Entity | Table | Key Fields |
|--------|-------|------------|
| Supplier | suppliers | name, city, state, zip_code, is_active |
| Purchase | purchases | product_id, supplier_id, purchase_date, unit_price |
| Product (modified) | products | +preferred_supplier_id, +is_hidden |
| InventoryAddition (modified) | inventory_additions | +purchase_id, -price_paid |

## Getting Help

- **Spec questions**: See `spec.md` User Stories and Edge Cases
- **Data model questions**: See `data-model.md` Entity definitions
- **Architecture questions**: See `research.md` Decisions
- **Session management**: See `CLAUDE.md` Session Management section
