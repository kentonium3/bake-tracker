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
