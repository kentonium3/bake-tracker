"""
Material Catalog Service - CRUD operations for material hierarchy.

This service provides CRUD operations for the material catalog hierarchy:
MaterialCategory > MaterialSubcategory > Material > MaterialProduct

Part of Feature 047: Materials Management System.

Session Management Pattern:
- All functions accept optional `session` parameter
- If session is provided, use it directly (allows callers to manage transactions)
- If session is None, create a new session_scope for the operation
"""

import re
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models import (
    MaterialCategory,
    MaterialSubcategory,
    Material,
    MaterialProduct,
    Composition,
)
from src.services.database import session_scope
from src.services.exceptions import ValidationError


# ============================================================================
# Utility Functions
# ============================================================================


def slugify(name: str) -> str:
    """
    Convert a name to a URL-friendly slug.

    Args:
        name: Display name to convert

    Returns:
        Lowercase slug with underscores (e.g., "Red Satin Ribbon" -> "red_satin_ribbon")
    """
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and hyphens with underscores
    slug = re.sub(r"[\s\-]+", "_", slug)
    # Remove any character that isn't alphanumeric or underscore
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    # Remove consecutive underscores
    slug = re.sub(r"_+", "_", slug)
    # Strip leading/trailing underscores
    slug = slug.strip("_")
    return slug


def _generate_unique_slug(
    base_slug: str,
    model_class,
    session: Session,
    exclude_id: Optional[int] = None,
) -> str:
    """
    Generate a unique slug by appending a number suffix if needed.

    Args:
        base_slug: The base slug to make unique
        model_class: SQLAlchemy model class with a slug column
        session: Database session
        exclude_id: ID to exclude from uniqueness check (for updates)

    Returns:
        Unique slug (e.g., "red_satin" or "red_satin_2")
    """
    slug = base_slug
    counter = 1

    while True:
        query = session.query(model_class).filter(model_class.slug == slug)
        if exclude_id is not None:
            query = query.filter(model_class.id != exclude_id)

        if query.first() is None:
            return slug

        counter += 1
        slug = f"{base_slug}_{counter}"


# ============================================================================
# Category Operations
# ============================================================================


def create_category(
    name: str,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    sort_order: int = 0,
    session: Optional[Session] = None,
) -> MaterialCategory:
    """
    Create a new material category.

    Args:
        name: Category display name (e.g., "Ribbons")
        slug: URL-friendly identifier (auto-generated if not provided)
        description: Optional description
        sort_order: Display ordering (default 0)
        session: Optional database session

    Returns:
        Created MaterialCategory instance

    Raises:
        ValidationError: If name is empty
    """
    if not name or not name.strip():
        raise ValidationError(["Category name cannot be empty"])

    def _impl(sess: Session) -> MaterialCategory:
        base_slug = slug or slugify(name)
        unique_slug = _generate_unique_slug(base_slug, MaterialCategory, sess)

        category = MaterialCategory(
            name=name.strip(),
            slug=unique_slug,
            description=description,
            sort_order=sort_order,
        )
        sess.add(category)
        sess.flush()
        sess.refresh(category)
        return category

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def get_category(
    category_id: Optional[int] = None,
    slug: Optional[str] = None,
    session: Optional[Session] = None,
) -> Optional[MaterialCategory]:
    """
    Get category by ID or slug.

    Args:
        category_id: Category ID (optional)
        slug: Category slug (optional)
        session: Optional database session

    Returns:
        MaterialCategory or None if not found
    """
    if category_id is None and slug is None:
        return None

    def _impl(sess: Session) -> Optional[MaterialCategory]:
        query = sess.query(MaterialCategory)
        if category_id is not None:
            return query.filter(MaterialCategory.id == category_id).first()
        return query.filter(MaterialCategory.slug == slug).first()

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def list_categories(session: Optional[Session] = None) -> List[MaterialCategory]:
    """
    List all categories ordered by sort_order.

    Args:
        session: Optional database session

    Returns:
        List of MaterialCategory objects
    """

    def _impl(sess: Session) -> List[MaterialCategory]:
        categories = (
            sess.query(MaterialCategory)
            .order_by(MaterialCategory.sort_order, MaterialCategory.name)
            .all()
        )
        return categories

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def update_category(
    category_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    sort_order: Optional[int] = None,
    session: Optional[Session] = None,
) -> MaterialCategory:
    """
    Update category fields.

    Args:
        category_id: Category ID to update
        name: New name (optional)
        description: New description (optional)
        sort_order: New sort order (optional)
        session: Optional database session

    Returns:
        Updated MaterialCategory instance

    Raises:
        ValidationError: If category not found or name is empty
    """

    def _impl(sess: Session) -> MaterialCategory:
        category = sess.query(MaterialCategory).filter(MaterialCategory.id == category_id).first()
        if category is None:
            raise ValidationError([f"Category with ID {category_id} not found"])

        if name is not None:
            if not name.strip():
                raise ValidationError(["Category name cannot be empty"])
            category.name = name.strip()

        if description is not None:
            category.description = description

        if sort_order is not None:
            category.sort_order = sort_order

        sess.flush()
        sess.refresh(category)
        return category

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def delete_category(category_id: int, session: Optional[Session] = None) -> bool:
    """
    Delete category. Raises if has subcategories.

    Args:
        category_id: Category ID to delete
        session: Optional database session

    Returns:
        True if deleted successfully

    Raises:
        ValidationError: If category not found or has subcategories
    """

    def _impl(sess: Session) -> bool:
        category = sess.query(MaterialCategory).filter(MaterialCategory.id == category_id).first()
        if category is None:
            raise ValidationError([f"Category with ID {category_id} not found"])

        if category.subcategories:
            raise ValidationError(
                [
                    f"Cannot delete category '{category.name}': "
                    f"has {len(category.subcategories)} subcategory(ies)"
                ]
            )

        sess.delete(category)
        return True

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


# ============================================================================
# Subcategory Operations
# ============================================================================


def create_subcategory(
    category_id: int,
    name: str,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    sort_order: int = 0,
    session: Optional[Session] = None,
) -> MaterialSubcategory:
    """
    Create subcategory under category.

    Args:
        category_id: Parent category ID
        name: Subcategory display name (e.g., "Satin")
        slug: URL-friendly identifier (auto-generated if not provided)
        description: Optional description
        sort_order: Display ordering (default 0)
        session: Optional database session

    Returns:
        Created MaterialSubcategory instance

    Raises:
        ValidationError: If name is empty or category not found
    """
    if not name or not name.strip():
        raise ValidationError(["Subcategory name cannot be empty"])

    def _impl(sess: Session) -> MaterialSubcategory:
        # Verify category exists
        category = sess.query(MaterialCategory).filter(MaterialCategory.id == category_id).first()
        if category is None:
            raise ValidationError([f"Category with ID {category_id} not found"])

        base_slug = slug or slugify(name)
        unique_slug = _generate_unique_slug(base_slug, MaterialSubcategory, sess)

        subcategory = MaterialSubcategory(
            category_id=category_id,
            name=name.strip(),
            slug=unique_slug,
            description=description,
            sort_order=sort_order,
        )
        sess.add(subcategory)
        sess.flush()
        sess.refresh(subcategory)
        return subcategory

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def get_subcategory(
    subcategory_id: Optional[int] = None,
    slug: Optional[str] = None,
    session: Optional[Session] = None,
) -> Optional[MaterialSubcategory]:
    """
    Get subcategory by ID or slug.

    Args:
        subcategory_id: Subcategory ID (optional)
        slug: Subcategory slug (optional)
        session: Optional database session

    Returns:
        MaterialSubcategory or None if not found
    """
    if subcategory_id is None and slug is None:
        return None

    def _impl(sess: Session) -> Optional[MaterialSubcategory]:
        query = sess.query(MaterialSubcategory)
        if subcategory_id is not None:
            return query.filter(MaterialSubcategory.id == subcategory_id).first()
        return query.filter(MaterialSubcategory.slug == slug).first()

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def list_subcategories(
    category_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> List[dict]:
    """
    List subcategories, optionally filtered by category.

    Args:
        category_id: Filter by category (optional)
        session: Optional database session

    Returns:
        List of subcategory dictionaries with keys: id, name, slug, category_id, description, sort_order
    """

    def _impl(sess: Session) -> List[dict]:
        query = sess.query(MaterialSubcategory)
        if category_id is not None:
            query = query.filter(MaterialSubcategory.category_id == category_id)
        subcategories = query.order_by(MaterialSubcategory.sort_order, MaterialSubcategory.name).all()
        # Convert to dicts before session closes to avoid detachment issues
        return [
            {
                "id": sub.id,
                "name": sub.name,
                "slug": sub.slug,
                "category_id": sub.category_id,
                "description": sub.description,
                "sort_order": sub.sort_order,
            }
            for sub in subcategories
        ]

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def update_subcategory(
    subcategory_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    sort_order: Optional[int] = None,
    session: Optional[Session] = None,
) -> MaterialSubcategory:
    """
    Update subcategory fields.

    Args:
        subcategory_id: Subcategory ID to update
        name: New name (optional)
        description: New description (optional)
        sort_order: New sort order (optional)
        session: Optional database session

    Returns:
        Updated MaterialSubcategory instance

    Raises:
        ValidationError: If subcategory not found or name is empty
    """

    def _impl(sess: Session) -> MaterialSubcategory:
        subcategory = (
            sess.query(MaterialSubcategory)
            .filter(MaterialSubcategory.id == subcategory_id)
            .first()
        )
        if subcategory is None:
            raise ValidationError([f"Subcategory with ID {subcategory_id} not found"])

        if name is not None:
            if not name.strip():
                raise ValidationError(["Subcategory name cannot be empty"])
            subcategory.name = name.strip()

        if description is not None:
            subcategory.description = description

        if sort_order is not None:
            subcategory.sort_order = sort_order

        sess.flush()
        sess.refresh(subcategory)
        return subcategory

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def delete_subcategory(subcategory_id: int, session: Optional[Session] = None) -> bool:
    """
    Delete subcategory. Raises if has materials.

    Args:
        subcategory_id: Subcategory ID to delete
        session: Optional database session

    Returns:
        True if deleted successfully

    Raises:
        ValidationError: If subcategory not found or has materials
    """

    def _impl(sess: Session) -> bool:
        subcategory = (
            sess.query(MaterialSubcategory)
            .filter(MaterialSubcategory.id == subcategory_id)
            .first()
        )
        if subcategory is None:
            raise ValidationError([f"Subcategory with ID {subcategory_id} not found"])

        if subcategory.materials:
            raise ValidationError(
                [
                    f"Cannot delete subcategory '{subcategory.name}': "
                    f"has {len(subcategory.materials)} material(s)"
                ]
            )

        sess.delete(subcategory)
        return True

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


# ============================================================================
# Material Operations
# ============================================================================


# Feature 058: Updated to metric base units (cm, sq cm)
# Matches Material model check constraint
VALID_BASE_UNIT_TYPES = {"each", "linear_cm", "square_cm"}


def create_material(
    subcategory_id: int,
    name: str,
    base_unit_type: str,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> Material:
    """
    Create material under subcategory.

    Args:
        subcategory_id: Parent subcategory ID
        name: Material display name (e.g., "Red Satin Ribbon")
        base_unit_type: Unit type ('each', 'linear_inches', 'square_inches')
        slug: URL-friendly identifier (auto-generated if not provided)
        description: Optional description
        notes: Optional notes
        session: Optional database session

    Returns:
        Created Material instance

    Raises:
        ValidationError: If name is empty, subcategory not found, or invalid base_unit_type
    """
    if not name or not name.strip():
        raise ValidationError(["Material name cannot be empty"])

    if base_unit_type not in VALID_BASE_UNIT_TYPES:
        raise ValidationError(
            [f"Invalid base_unit_type '{base_unit_type}'. Must be one of: {VALID_BASE_UNIT_TYPES}"]
        )

    def _impl(sess: Session) -> Material:
        # Verify subcategory exists
        subcategory = (
            sess.query(MaterialSubcategory)
            .filter(MaterialSubcategory.id == subcategory_id)
            .first()
        )
        if subcategory is None:
            raise ValidationError([f"Subcategory with ID {subcategory_id} not found"])

        base_slug = slug or slugify(name)
        unique_slug = _generate_unique_slug(base_slug, Material, sess)

        material = Material(
            subcategory_id=subcategory_id,
            name=name.strip(),
            slug=unique_slug,
            description=description,
            base_unit_type=base_unit_type,
            notes=notes,
        )
        sess.add(material)
        sess.flush()
        sess.refresh(material)
        return material

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def get_material(
    material_id: Optional[int] = None,
    slug: Optional[str] = None,
    session: Optional[Session] = None,
) -> Optional[Material]:
    """
    Get material by ID or slug.

    Args:
        material_id: Material ID (optional)
        slug: Material slug (optional)
        session: Optional database session

    Returns:
        Material or None if not found
    """
    if material_id is None and slug is None:
        return None

    def _impl(sess: Session) -> Optional[Material]:
        query = sess.query(Material)
        if material_id is not None:
            return query.filter(Material.id == material_id).first()
        return query.filter(Material.slug == slug).first()

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def list_materials(
    subcategory_id: Optional[int] = None,
    category_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> List[dict]:
    """
    List materials with optional filtering.

    Args:
        subcategory_id: Filter by subcategory (optional)
        category_id: Filter by category (optional)
        session: Optional database session

    Returns:
        List of material dictionaries with keys: id, name, slug, subcategory_id, base_unit_type, description, notes
    """

    def _impl(sess: Session) -> List[dict]:
        query = sess.query(Material)

        if subcategory_id is not None:
            query = query.filter(Material.subcategory_id == subcategory_id)
        elif category_id is not None:
            # Filter by category through subcategory relationship
            query = query.join(MaterialSubcategory).filter(
                MaterialSubcategory.category_id == category_id
            )

        materials = query.order_by(Material.name).all()
        # Convert to dicts before session closes to avoid detachment issues
        return [
            {
                "id": mat.id,
                "name": mat.name,
                "slug": mat.slug,
                "subcategory_id": mat.subcategory_id,
                "base_unit_type": mat.base_unit_type,
                "description": mat.description,
                "notes": mat.notes,
            }
            for mat in materials
        ]

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def update_material(
    material_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> Material:
    """
    Update material fields. Cannot change base_unit_type after creation.

    Args:
        material_id: Material ID to update
        name: New name (optional)
        description: New description (optional)
        notes: New notes (optional)
        session: Optional database session

    Returns:
        Updated Material instance

    Raises:
        ValidationError: If material not found or name is empty
    """

    def _impl(sess: Session) -> Material:
        material = sess.query(Material).filter(Material.id == material_id).first()
        if material is None:
            raise ValidationError([f"Material with ID {material_id} not found"])

        if name is not None:
            if not name.strip():
                raise ValidationError(["Material name cannot be empty"])
            material.name = name.strip()

        if description is not None:
            material.description = description

        if notes is not None:
            material.notes = notes

        sess.flush()
        sess.refresh(material)
        return material

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def delete_material(material_id: int, session: Optional[Session] = None) -> bool:
    """
    Delete material. Raises if has products with inventory or used in compositions.

    Args:
        material_id: Material ID to delete
        session: Optional database session

    Returns:
        True if deleted successfully

    Raises:
        ValidationError: If material not found, has products with inventory, or used in compositions
    """

    def _impl(sess: Session) -> bool:
        material = sess.query(Material).filter(Material.id == material_id).first()
        if material is None:
            raise ValidationError([f"Material with ID {material_id} not found"])

        # Check for products with inventory
        products_with_inventory = [p for p in material.products if p.current_inventory > 0]
        if products_with_inventory:
            raise ValidationError(
                [
                    f"Cannot delete material '{material.name}': "
                    f"{len(products_with_inventory)} product(s) have inventory"
                ]
            )

        # Check for compositions using this material (generic placeholder)
        # Note: material_id column added to Composition in WP05
        if hasattr(Composition, 'material_id') and Composition.material_id is not None:
            composition_count = (
                sess.query(Composition).filter(Composition.material_id == material_id).count()
            )
            if composition_count > 0:
                raise ValidationError(
                    [
                        f"Cannot delete material '{material.name}': "
                        f"used in {composition_count} composition(s)"
                    ]
                )

        sess.delete(material)
        return True

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


# ============================================================================
# Product Operations
# ============================================================================


# Feature 058: Use metric base units (cm, sq cm) via material_unit_converter
# Count units remain unchanged
COUNT_UNITS = {"each", "ea", "count", "piece", "pieces", "pc", "pcs"}


def _convert_to_base_units(
    package_quantity: float, package_unit: str, base_unit_type: str
) -> float:
    """
    Convert package quantity and unit to metric base units.

    Feature 058: Updated to use material_unit_converter for metric base units
    (linear_cm, square_cm) instead of imperial (linear_inches, square_inches).

    Args:
        package_quantity: Amount per package
        package_unit: Unit of the package (e.g., 'feet', 'yards', 'each')
        base_unit_type: Material's base unit type ('each', 'linear_cm', 'square_cm')

    Returns:
        Quantity in base units (cm for linear, sq cm for area, count for each)

    Raises:
        ValidationError: If unit conversion is not possible
    """
    package_unit_lower = package_unit.lower()

    if base_unit_type == "each":
        # For "each" items, just use the package quantity
        if package_unit_lower in COUNT_UNITS:
            return package_quantity
        # Allow numeric quantities even if unit isn't explicitly "each"
        return package_quantity

    # Feature 058: Use material_unit_converter for metric conversions
    from . import material_unit_converter

    # Validate unit compatibility
    is_valid, error = material_unit_converter.validate_unit_compatibility(
        package_unit_lower, base_unit_type
    )
    if not is_valid:
        raise ValidationError([error])

    # Convert to base units
    success, result, error = material_unit_converter.convert_to_base_units(
        Decimal(str(package_quantity)),
        package_unit_lower,
        base_unit_type,
    )
    if not success:
        raise ValidationError([error])

    return float(result)


def create_product(
    material_id: int,
    name: str,
    package_quantity: float,
    package_unit: str,
    brand: Optional[str] = None,
    supplier_id: Optional[int] = None,
    sku: Optional[str] = None,
    slug: Optional[str] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> MaterialProduct:
    """
    Create product under material. Calculates quantity_in_base_units from package_unit.

    Args:
        material_id: Parent material ID
        name: Product display name (e.g., "100ft Red Satin Roll")
        package_quantity: Quantity per package (e.g., 100)
        package_unit: Unit of package (e.g., 'feet', 'yards', 'each')
        brand: Brand name (optional)
        supplier_id: Preferred supplier ID (optional)
        sku: Supplier SKU (optional)
        slug: URL-friendly identifier (auto-generated if not provided)
        notes: Optional notes
        session: Optional database session

    Returns:
        Created MaterialProduct instance

    Raises:
        ValidationError: If name is empty, material not found, or invalid unit conversion
    """
    if not name or not name.strip():
        raise ValidationError(["Product name cannot be empty"])

    if package_quantity <= 0:
        raise ValidationError(["Package quantity must be positive"])

    def _impl(sess: Session) -> MaterialProduct:
        # Get material to determine base_unit_type
        material = sess.query(Material).filter(Material.id == material_id).first()
        if material is None:
            raise ValidationError([f"Material with ID {material_id} not found"])

        # Convert package to base units
        quantity_in_base_units = _convert_to_base_units(
            package_quantity, package_unit, material.base_unit_type
        )

        # Generate unique slug if not provided
        product_slug = slug
        if not product_slug:
            base_slug = slugify(name.strip())
            # Ensure uniqueness across all products
            existing = sess.query(MaterialProduct).filter(
                MaterialProduct.slug == base_slug
            ).first()
            if existing:
                counter = 1
                while True:
                    candidate = f"{base_slug}_{counter}"
                    if not sess.query(MaterialProduct).filter(
                        MaterialProduct.slug == candidate
                    ).first():
                        product_slug = candidate
                        break
                    counter += 1
            else:
                product_slug = base_slug

        # Feature 058: Removed current_inventory and weighted_avg_cost
        # (now tracked via MaterialInventoryItem using FIFO)
        product = MaterialProduct(
            material_id=material_id,
            name=name.strip(),
            slug=product_slug,
            brand=brand.strip() if brand else None,
            sku=sku,
            package_quantity=package_quantity,
            package_unit=package_unit,
            quantity_in_base_units=quantity_in_base_units,
            supplier_id=supplier_id,
            notes=notes,
        )
        sess.add(product)
        sess.flush()
        sess.refresh(product)
        return product

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def get_product(
    product_id: int,
    session: Optional[Session] = None,
) -> Optional[MaterialProduct]:
    """
    Get product by ID.

    Args:
        product_id: Product ID
        session: Optional database session

    Returns:
        MaterialProduct or None if not found
    """

    def _impl(sess: Session) -> Optional[MaterialProduct]:
        return sess.query(MaterialProduct).filter(MaterialProduct.id == product_id).first()

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def list_products(
    material_id: Optional[int] = None,
    include_hidden: bool = False,
    session: Optional[Session] = None,
) -> List[dict]:
    """
    List products with optional filtering.

    Args:
        material_id: Filter by material (optional)
        include_hidden: Include hidden products (default False)
        session: Optional database session

    Returns:
        List of product dictionaries with all product fields plus supplier_name
    """
    from sqlalchemy.orm import joinedload

    def _impl(sess: Session) -> List[dict]:
        query = sess.query(MaterialProduct).options(joinedload(MaterialProduct.supplier))

        if material_id is not None:
            query = query.filter(MaterialProduct.material_id == material_id)

        if not include_hidden:
            query = query.filter(MaterialProduct.is_hidden == False)  # noqa: E712

        products = query.order_by(MaterialProduct.name).all()
        # Convert to dicts before session closes to avoid detachment issues
        return [
            {
                "id": prod.id,
                "name": prod.name,
                "slug": prod.slug,
                "material_id": prod.material_id,
                "brand": prod.brand,
                "sku": prod.sku,
                "package_quantity": prod.package_quantity,
                "package_unit": prod.package_unit,
                "quantity_in_base_units": prod.quantity_in_base_units,
                "supplier_id": prod.supplier_id,
                "supplier_name": prod.supplier.name if prod.supplier else None,
                "current_inventory": prod.current_inventory,
                "weighted_avg_cost": prod.weighted_avg_cost,
                "is_hidden": prod.is_hidden,
                "notes": prod.notes,
            }
            for prod in products
        ]

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def update_product(
    product_id: int,
    name: Optional[str] = None,
    brand: Optional[str] = None,
    supplier_id: Optional[int] = None,
    sku: Optional[str] = None,
    is_hidden: Optional[bool] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> MaterialProduct:
    """
    Update product fields. Cannot change package_quantity or package_unit.

    Args:
        product_id: Product ID to update
        name: New name (optional)
        brand: New brand (optional)
        supplier_id: New supplier ID (optional)
        sku: New SKU (optional)
        is_hidden: Hide/show product (optional)
        notes: New notes (optional)
        session: Optional database session

    Returns:
        Updated MaterialProduct instance

    Raises:
        ValidationError: If product not found or name is empty
    """

    def _impl(sess: Session) -> MaterialProduct:
        product = sess.query(MaterialProduct).filter(MaterialProduct.id == product_id).first()
        if product is None:
            raise ValidationError([f"Product with ID {product_id} not found"])

        if name is not None:
            if not name.strip():
                raise ValidationError(["Product name cannot be empty"])
            product.name = name.strip()

        if brand is not None:
            product.brand = brand.strip() if brand else None

        if supplier_id is not None:
            product.supplier_id = supplier_id

        if sku is not None:
            product.sku = sku

        if is_hidden is not None:
            product.is_hidden = is_hidden

        if notes is not None:
            product.notes = notes

        sess.flush()
        sess.refresh(product)
        return product

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def delete_product(product_id: int, session: Optional[Session] = None) -> bool:
    """
    Delete product. Raises if current_inventory > 0.

    Args:
        product_id: Product ID to delete
        session: Optional database session

    Returns:
        True if deleted successfully

    Raises:
        ValidationError: If product not found or has inventory
    """

    def _impl(sess: Session) -> bool:
        product = sess.query(MaterialProduct).filter(MaterialProduct.id == product_id).first()
        if product is None:
            raise ValidationError([f"Product with ID {product_id} not found"])

        if product.current_inventory > 0:
            raise ValidationError(
                [
                    f"Cannot delete product '{product.name}': "
                    f"has {product.current_inventory} units in inventory"
                ]
            )

        sess.delete(product)
        return True

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)
