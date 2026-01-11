# Service Contract: MaterialCatalogService

**Module**: `src/services/material_catalog_service.py`
**Purpose**: CRUD operations for material hierarchy (categories, subcategories, materials, products)

## Interface

### Category Operations

```python
def create_category(
    name: str,
    slug: str | None = None,
    description: str | None = None,
    sort_order: int = 0,
    session: Session | None = None
) -> MaterialCategory:
    """Create a new material category."""

def get_category(
    category_id: int | None = None,
    slug: str | None = None,
    session: Session | None = None
) -> MaterialCategory | None:
    """Get category by ID or slug."""

def list_categories(
    session: Session | None = None
) -> list[MaterialCategory]:
    """List all categories ordered by sort_order."""

def update_category(
    category_id: int,
    name: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    session: Session | None = None
) -> MaterialCategory:
    """Update category fields."""

def delete_category(
    category_id: int,
    session: Session | None = None
) -> bool:
    """Delete category. Raises if has subcategories."""
```

### Subcategory Operations

```python
def create_subcategory(
    category_id: int,
    name: str,
    slug: str | None = None,
    description: str | None = None,
    sort_order: int = 0,
    session: Session | None = None
) -> MaterialSubcategory:
    """Create subcategory under category."""

def get_subcategory(
    subcategory_id: int | None = None,
    slug: str | None = None,
    session: Session | None = None
) -> MaterialSubcategory | None:
    """Get subcategory by ID or slug."""

def list_subcategories(
    category_id: int | None = None,
    session: Session | None = None
) -> list[MaterialSubcategory]:
    """List subcategories, optionally filtered by category."""

def update_subcategory(
    subcategory_id: int,
    name: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    session: Session | None = None
) -> MaterialSubcategory:
    """Update subcategory fields."""

def delete_subcategory(
    subcategory_id: int,
    session: Session | None = None
) -> bool:
    """Delete subcategory. Raises if has materials."""
```

### Material Operations

```python
def create_material(
    subcategory_id: int,
    name: str,
    base_unit_type: str,  # 'each', 'linear_inches', 'square_inches'
    slug: str | None = None,
    description: str | None = None,
    notes: str | None = None,
    session: Session | None = None
) -> Material:
    """Create material under subcategory."""

def get_material(
    material_id: int | None = None,
    slug: str | None = None,
    session: Session | None = None
) -> Material | None:
    """Get material by ID or slug."""

def list_materials(
    subcategory_id: int | None = None,
    category_id: int | None = None,
    session: Session | None = None
) -> list[Material]:
    """List materials with optional filtering."""

def update_material(
    material_id: int,
    name: str | None = None,
    description: str | None = None,
    notes: str | None = None,
    session: Session | None = None
) -> Material:
    """Update material fields. Cannot change base_unit_type after creation."""

def delete_material(
    material_id: int,
    session: Session | None = None
) -> bool:
    """Delete material. Raises if has products with inventory or used in compositions."""
```

### Product Operations

```python
def create_product(
    material_id: int,
    name: str,
    package_quantity: float,
    package_unit: str,
    brand: str | None = None,
    supplier_id: int | None = None,
    sku: str | None = None,
    notes: str | None = None,
    session: Session | None = None
) -> MaterialProduct:
    """Create product under material. Calculates quantity_in_base_units from package_unit."""

def get_product(
    product_id: int,
    session: Session | None = None
) -> MaterialProduct | None:
    """Get product by ID."""

def list_products(
    material_id: int | None = None,
    include_hidden: bool = False,
    session: Session | None = None
) -> list[MaterialProduct]:
    """List products with optional filtering."""

def update_product(
    product_id: int,
    name: str | None = None,
    brand: str | None = None,
    supplier_id: int | None = None,
    sku: str | None = None,
    is_hidden: bool | None = None,
    notes: str | None = None,
    session: Session | None = None
) -> MaterialProduct:
    """Update product fields. Cannot change package_quantity or package_unit."""

def delete_product(
    product_id: int,
    session: Session | None = None
) -> bool:
    """Delete product. Raises if current_inventory > 0."""
```

## Validation Rules

- Category/subcategory/material names must be unique within their parent scope
- Slugs are auto-generated from names if not provided
- base_unit_type must be one of: 'each', 'linear_inches', 'square_inches'
- package_unit is converted to base units using unit_converter

## Error Handling

All functions raise:
- `ValueError`: Invalid input parameters
- `IntegrityError`: Constraint violations (e.g., duplicate names)
- `ValidationError`: Business rule violations (e.g., delete with inventory)
