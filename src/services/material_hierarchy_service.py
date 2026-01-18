"""
Material hierarchy service for Feature 052.

Provides service layer methods for fetching materials with their
Category/Subcategory hierarchy context pre-computed for efficient display.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import joinedload

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


def get_aggregated_usage_counts(
    item_type: str, item_id: int, session=None
) -> Dict[str, int]:
    """
    Get aggregated product counts for a material, subcategory, or category.

    Feature 052: Used in Hierarchy Admin UI to show total usage for non-leaf nodes.
    For materials, returns direct usage only.
    For subcategories, sums usage of all child materials.
    For categories, sums usage of all materials in all subcategories.

    Args:
        item_type: 'material', 'subcategory', or 'category'
        item_id: ID of the item to check
        session: Optional SQLAlchemy session

    Returns:
        {"product_count": int, "material_count": int}
    """
    from src.models.material_product import MaterialProduct

    def _impl(session):
        material_ids = []

        if item_type == "material":
            material_ids = [item_id]

        elif item_type == "subcategory":
            # Get all materials in this subcategory
            materials = (
                session.query(Material)
                .filter(Material.subcategory_id == item_id)
                .all()
            )
            material_ids = [m.id for m in materials]

        elif item_type == "category":
            # Get all subcategories, then all materials
            subcategories = (
                session.query(MaterialSubcategory)
                .filter(MaterialSubcategory.category_id == item_id)
                .all()
            )
            for subcat in subcategories:
                materials = (
                    session.query(Material)
                    .filter(Material.subcategory_id == subcat.id)
                    .all()
                )
                material_ids.extend([m.id for m in materials])

        if not material_ids:
            return {"product_count": 0, "material_count": 0}

        product_count = (
            session.query(MaterialProduct)
            .filter(MaterialProduct.material_id.in_(material_ids))
            .count()
        )

        return {
            "product_count": product_count,
            "material_count": len(material_ids),
        }

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
        base_unit_type: Unit type ('each', 'linear_cm', 'area_sq_cm')
            F058: Changed from imperial to metric base units
        session: Optional SQLAlchemy session

    Returns:
        Dictionary representation of created Material

    Raises:
        ValueError: If subcategory not found, invalid unit type, name empty, or name not unique
    """
    from src.services import hierarchy_admin_service

    # F058: Metric base units (cm for linear, sq cm for area)
    VALID_UNIT_TYPES = ("each", "linear_cm", "area_sq_cm")

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


def rename_item(
    item_type: str, item_id: int, new_name: str, session=None
) -> Dict:
    """
    Rename a category, subcategory, or material.

    Feature 052: Admin operation to rename material hierarchy item.

    Args:
        item_type: "category", "subcategory", or "material"
        item_id: ID of item to rename
        new_name: New name
        session: Optional SQLAlchemy session

    Returns:
        Dictionary representation of updated entity

    Raises:
        ValueError: If item not found, invalid type, name empty, or name not unique
    """
    from src.services import hierarchy_admin_service

    VALID_TYPES = ("category", "subcategory", "material")

    def _impl(session):
        if item_type not in VALID_TYPES:
            raise ValueError(
                f"Invalid item type '{item_type}'. Must be one of: {VALID_TYPES}"
            )

        # Validate name not empty
        if not hierarchy_admin_service.validate_name_not_empty(new_name):
            raise ValueError("Name cannot be empty")

        # Trim name
        new_name_stripped = hierarchy_admin_service.trim_name(new_name)

        # Get entity and siblings based on type
        if item_type == "category":
            entity = (
                session.query(MaterialCategory)
                .filter(MaterialCategory.id == item_id)
                .first()
            )
            if not entity:
                raise ValueError(f"Category {item_id} not found")
            # Categories are unique globally
            siblings = session.query(MaterialCategory).all()

        elif item_type == "subcategory":
            entity = (
                session.query(MaterialSubcategory)
                .filter(MaterialSubcategory.id == item_id)
                .first()
            )
            if not entity:
                raise ValueError(f"Subcategory {item_id} not found")
            # Subcategories unique within category
            siblings = (
                session.query(MaterialSubcategory)
                .filter(MaterialSubcategory.category_id == entity.category_id)
                .all()
            )

        else:  # material
            entity = session.query(Material).filter(Material.id == item_id).first()
            if not entity:
                raise ValueError(f"Material {item_id} not found")
            # Materials unique within subcategory
            siblings = (
                session.query(Material)
                .filter(Material.subcategory_id == entity.subcategory_id)
                .all()
            )

        # Validate unique name (excluding self)
        if not hierarchy_admin_service.validate_unique_sibling_name(
            siblings, new_name_stripped, exclude_id=item_id
        ):
            raise ValueError(
                f"A {item_type} named '{new_name_stripped}' already exists at this level"
            )

        # Update name
        entity.name = new_name_stripped

        # Regenerate slug
        new_slug = hierarchy_admin_service.generate_slug(new_name_stripped)

        # Check slug uniqueness based on type
        if item_type == "category":
            existing = (
                session.query(MaterialCategory)
                .filter(MaterialCategory.slug == new_slug, MaterialCategory.id != item_id)
                .first()
            )
        elif item_type == "subcategory":
            existing = (
                session.query(MaterialSubcategory)
                .filter(
                    MaterialSubcategory.slug == new_slug, MaterialSubcategory.id != item_id
                )
                .first()
            )
        else:
            existing = (
                session.query(Material)
                .filter(Material.slug == new_slug, Material.id != item_id)
                .first()
            )

        if existing:
            # Add prefix for uniqueness
            new_slug = f"{item_type[0]}-{new_slug}"

        entity.slug = new_slug

        session.flush()
        return entity.to_dict()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        result = _impl(session)
        session.commit()
        return result


def reparent_material(
    material_id: int,
    new_subcategory_id: int,
    session=None,
) -> Dict:
    """
    Move material to new subcategory.

    Feature 052: Admin operation to move material between subcategories.

    Args:
        material_id: ID of material to move
        new_subcategory_id: ID of new subcategory
        session: Optional SQLAlchemy session

    Returns:
        Dictionary representation of updated Material

    Raises:
        ValueError: If material/subcategory not found, same parent, or duplicate name
    """
    from src.services import hierarchy_admin_service

    def _impl(session):
        # Find material
        material = session.query(Material).filter(Material.id == material_id).first()

        if not material:
            raise ValueError(f"Material {material_id} not found")

        # Find new subcategory
        new_subcategory = (
            session.query(MaterialSubcategory)
            .filter(MaterialSubcategory.id == new_subcategory_id)
            .first()
        )

        if not new_subcategory:
            raise ValueError(f"Subcategory {new_subcategory_id} not found")

        # Check if already under this subcategory
        if material.subcategory_id == new_subcategory_id:
            raise ValueError("Material is already under this subcategory")

        # Validate unique name in new location
        siblings = (
            session.query(Material)
            .filter(Material.subcategory_id == new_subcategory_id)
            .all()
        )

        if not hierarchy_admin_service.validate_unique_sibling_name(
            siblings, material.name, exclude_id=material_id
        ):
            raise ValueError(
                f"A material named '{material.name}' already exists in the new subcategory"
            )

        # Perform move
        material.subcategory_id = new_subcategory_id

        session.flush()
        return material.to_dict()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        result = _impl(session)
        session.commit()
        return result


def reparent_subcategory(
    subcategory_id: int,
    new_category_id: int,
    session=None,
) -> Dict:
    """
    Move subcategory to new category.

    Feature 052: Admin operation to move subcategory between categories.

    Args:
        subcategory_id: ID of subcategory to move
        new_category_id: ID of new category
        session: Optional SQLAlchemy session

    Returns:
        Dictionary representation of updated MaterialSubcategory

    Raises:
        ValueError: If subcategory/category not found, same parent, or duplicate name
    """
    from src.services import hierarchy_admin_service

    def _impl(session):
        # Find subcategory
        subcategory = (
            session.query(MaterialSubcategory)
            .filter(MaterialSubcategory.id == subcategory_id)
            .first()
        )

        if not subcategory:
            raise ValueError(f"Subcategory {subcategory_id} not found")

        # Find new category
        new_category = (
            session.query(MaterialCategory)
            .filter(MaterialCategory.id == new_category_id)
            .first()
        )

        if not new_category:
            raise ValueError(f"Category {new_category_id} not found")

        # Check if already under this category
        if subcategory.category_id == new_category_id:
            raise ValueError("Subcategory is already under this category")

        # Validate unique name in new location
        siblings = (
            session.query(MaterialSubcategory)
            .filter(MaterialSubcategory.category_id == new_category_id)
            .all()
        )

        if not hierarchy_admin_service.validate_unique_sibling_name(
            siblings, subcategory.name, exclude_id=subcategory_id
        ):
            raise ValueError(
                f"A subcategory named '{subcategory.name}' already exists in the new category"
            )

        # Perform move
        subcategory.category_id = new_category_id

        session.flush()
        return subcategory.to_dict()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        result = _impl(session)
        session.commit()
        return result
