"""
Material hierarchy service for Feature 052.

Provides service layer methods for fetching materials with their
Category/Subcategory hierarchy context pre-computed for efficient display.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session, joinedload

from src.models.material import Material
from src.models.material_subcategory import MaterialSubcategory
from src.models.material_category import MaterialCategory
from src.services.database import session_scope


def get_materials_with_parents(
    category_filter: Optional[str] = None, session=None
) -> List[Dict]:
    """
    Get all materials with pre-resolved category and subcategory names.

    Feature 052: Optimized method for Materials tab display that returns
    materials with their hierarchy context pre-computed to avoid N+1 queries.

    Args:
        category_filter: Optional - filter by category name
        session: Optional SQLAlchemy session

    Returns:
        List of dicts with keys:
        - category_name: str - Top-level category name
        - subcategory_name: str - Subcategory name
        - material_name: str - Material name
        - material: dict - Full material dict from to_dict()
    """

    def _impl(session):
        # Get all materials with eager-loaded subcategory and category
        materials = (
            session.query(Material)
            .options(joinedload(Material.subcategory).joinedload(MaterialSubcategory.category))
            .order_by(Material.name)
            .all()
        )

        result = []
        for mat in materials:
            subcat = mat.subcategory
            cat = subcat.category if subcat else None

            category_name = cat.name if cat else ""
            subcategory_name = subcat.name if subcat else ""

            # Apply category filter if specified
            if category_filter is not None:
                if category_name != category_filter:
                    continue

            result.append(
                {
                    "category_name": category_name,
                    "subcategory_name": subcategory_name,
                    "material_name": mat.name,
                    "material": mat.to_dict(),
                }
            )

        return result

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_material_with_parents(material_id: int, session=None) -> Optional[Dict]:
    """
    Get a single material with its category and subcategory names resolved.

    Feature 052: Helper for detailed material display.

    Args:
        material_id: ID of material to retrieve
        session: Optional SQLAlchemy session

    Returns:
        Dict with keys: category_name, subcategory_name, material_name, material
        Or None if material not found
    """

    def _impl(session):
        material = (
            session.query(Material)
            .filter(Material.id == material_id)
            .options(joinedload(Material.subcategory).joinedload(MaterialSubcategory.category))
            .first()
        )

        if not material:
            return None

        subcat = material.subcategory
        cat = subcat.category if subcat else None

        return {
            "category_name": cat.name if cat else "",
            "subcategory_name": subcat.name if subcat else "",
            "material_name": material.name,
            "material": material.to_dict(),
        }

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_category_hierarchy(session=None) -> List[Dict]:
    """
    Get the full category > subcategory hierarchy tree.

    Feature 052: Used for hierarchy admin tree view.

    Returns:
        List of category dicts, each with 'subcategories' list
    """

    def _impl(session):
        categories = (
            session.query(MaterialCategory)
            .options(joinedload(MaterialCategory.subcategories))
            .order_by(MaterialCategory.sort_order, MaterialCategory.name)
            .all()
        )

        result = []
        for cat in categories:
            cat_dict = cat.to_dict()
            cat_dict["subcategories"] = sorted(
                [
                    {
                        "id": sub.id,
                        "name": sub.name,
                        "slug": sub.slug,
                        "material_count": len(sub.materials),
                    }
                    for sub in cat.subcategories
                ],
                key=lambda x: (x.get("name", "") or "").lower(),
            )
            result.append(cat_dict)

        return result

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_hierarchy_tree(session=None) -> List[Dict]:
    """
    Get full material tree structure for admin UI.

    Feature 052: Returns nested tree structure matching ingredient tree format
    for consistent UI rendering in Hierarchy Admin.

    Returns:
        List of category nodes, each with subcategories containing materials:
        [{
            "id": int,
            "name": str,
            "type": "category",
            "children": [{
                "id": int,
                "name": str,
                "type": "subcategory",
                "children": [{
                    "id": int,
                    "name": str,
                    "type": "material",
                    "children": [],
                    "material": dict
                }],
                "subcategory": dict
            }],
            "category": dict
        }]
    """

    def _impl(session):
        categories = (
            session.query(MaterialCategory)
            .order_by(MaterialCategory.sort_order, MaterialCategory.name)
            .all()
        )

        result = []
        for cat in categories:
            subcategories = (
                session.query(MaterialSubcategory)
                .filter(MaterialSubcategory.category_id == cat.id)
                .order_by(MaterialSubcategory.sort_order, MaterialSubcategory.name)
                .all()
            )

            subcat_nodes = []
            for subcat in subcategories:
                materials = (
                    session.query(Material)
                    .filter(Material.subcategory_id == subcat.id)
                    .order_by(Material.name)
                    .all()
                )

                mat_nodes = [
                    {
                        "id": mat.id,
                        "name": mat.name,
                        "type": "material",
                        "children": [],
                        "material": mat.to_dict(),
                    }
                    for mat in materials
                ]

                subcat_nodes.append(
                    {
                        "id": subcat.id,
                        "name": subcat.name,
                        "type": "subcategory",
                        "children": mat_nodes,
                        "subcategory": subcat.to_dict(),
                    }
                )

            result.append(
                {
                    "id": cat.id,
                    "name": cat.name,
                    "type": "category",
                    "children": subcat_nodes,
                    "category": cat.to_dict(),
                }
            )

        return result

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_usage_counts(material_id: int, session=None) -> Dict[str, int]:
    """
    Get product count for a material.

    Feature 052: Used in Hierarchy Admin UI to show usage information
    before performing rename/reparent/delete operations.

    Args:
        material_id: ID of material to check
        session: Optional SQLAlchemy session

    Returns:
        {"product_count": int}
    """
    from src.models.material_product import MaterialProduct

    def _impl(session):
        product_count = (
            session.query(MaterialProduct).filter(MaterialProduct.material_id == material_id).count()
        )

        return {"product_count": product_count}

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def add_material(
    subcategory_id: int,
    name: str,
    base_unit_type: str = "each",
    session=None,
) -> Dict:
    """
    Create new material under subcategory.

    Feature 052: Admin operation to add new material.

    Args:
        subcategory_id: ID of parent subcategory
        name: Display name for new material
        base_unit_type: Unit type ('each', 'linear_inches', 'square_inches')
        session: Optional SQLAlchemy session

    Returns:
        Dictionary representation of created Material

    Raises:
        ValueError: If subcategory not found, invalid unit type, name empty, or name not unique
    """
    from src.services import hierarchy_admin_service

    VALID_UNIT_TYPES = ("each", "linear_inches", "square_inches")

    def _impl(session):
        # Validate name not empty
        if not hierarchy_admin_service.validate_name_not_empty(name):
            raise ValueError("Material name cannot be empty")

        # Trim name
        trimmed_name = hierarchy_admin_service.trim_name(name)

        # Validate unit type
        if base_unit_type not in VALID_UNIT_TYPES:
            raise ValueError(
                f"Invalid unit type '{base_unit_type}'. Must be one of: {VALID_UNIT_TYPES}"
            )

        # Validate subcategory exists
        subcategory = (
            session.query(MaterialSubcategory)
            .filter(MaterialSubcategory.id == subcategory_id)
            .first()
        )

        if not subcategory:
            raise ValueError(f"Subcategory {subcategory_id} not found")

        # Get siblings for uniqueness check
        siblings = (
            session.query(Material)
            .filter(Material.subcategory_id == subcategory_id)
            .all()
        )

        # Validate unique name
        if not hierarchy_admin_service.validate_unique_sibling_name(siblings, trimmed_name):
            raise ValueError(
                f"A material named '{trimmed_name}' already exists in this subcategory"
            )

        # Generate slug
        slug = hierarchy_admin_service.generate_slug(trimmed_name)

        # Check slug uniqueness globally
        existing_slug = session.query(Material).filter(Material.slug == slug).first()
        if existing_slug:
            # Append subcategory slug for uniqueness
            slug = f"{subcategory.slug}-{slug}"

        # Create material
        material = Material(
            name=trimmed_name,
            slug=slug,
            subcategory_id=subcategory_id,
            base_unit_type=base_unit_type,
        )

        session.add(material)
        session.flush()  # Get ID

        return material.to_dict()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        result = _impl(session)
        session.commit()
        return result
