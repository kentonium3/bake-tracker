"""
Hierarchy admin service for Feature 052.

Provides shared utility functions for hierarchy admin operations
including validation, slug generation, and cycle detection.
"""

import re
from typing import List, Any, Optional


def validate_unique_sibling_name(
    siblings: List[Any], new_name: str, exclude_id: Optional[int] = None
) -> bool:
    """
    Check if name is unique among siblings.

    Feature 052: Used during add/rename operations to ensure no duplicate
    names exist at the same hierarchy level under the same parent.

    Args:
        siblings: List of sibling entities with 'name' or 'display_name' attribute
        new_name: Proposed new name
        exclude_id: ID to exclude from check (for rename operations)

    Returns:
        True if name is unique, False if duplicate exists
    """
    new_name_lower = new_name.strip().lower()

    for sibling in siblings:
        # Skip the item being renamed
        sibling_id = getattr(sibling, "id", None)
        if exclude_id is not None and sibling_id == exclude_id:
            continue

        # Get the sibling's name (ingredients use display_name, materials use name)
        sibling_name = getattr(sibling, "display_name", None) or getattr(sibling, "name", "")
        if sibling_name.strip().lower() == new_name_lower:
            return False

    return True


def generate_slug(name: str) -> str:
    """
    Generate URL-friendly slug from name.

    Feature 052: Used when creating new items to generate a unique slug
    from the display name.

    Args:
        name: Display name to slugify

    Returns:
        Lowercase slug with hyphens (e.g., "All-Purpose Flour" -> "all-purpose-flour")
    """
    if not name:
        return ""

    slug = name.strip().lower()
    # Remove special characters except spaces and hyphens
    slug = re.sub(r"[^\w\s-]", "", slug)
    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    # Remove leading/trailing hyphens
    return slug.strip("-")


def validate_no_cycle(item_descendants: List[Any], proposed_parent: Any) -> bool:
    """
    Ensure reparenting won't create a cycle.

    Feature 052: Used during reparent operations to prevent an item
    from being moved under one of its own descendants.

    Args:
        item_descendants: List of descendant entities of the item being moved
        proposed_parent: The proposed new parent entity

    Returns:
        True if safe (no cycle), False if cycle would be created
    """
    if proposed_parent is None:
        return True

    # Check if proposed parent is in the descendants list
    proposed_id = getattr(proposed_parent, "id", None)
    for desc in item_descendants:
        desc_id = getattr(desc, "id", None)
        if desc_id == proposed_id:
            return False

    return True


def validate_name_not_empty(name: str) -> bool:
    """
    Validate that name is not empty or whitespace-only.

    Feature 052: Edge case validation per spec.md.

    Args:
        name: Name to validate

    Returns:
        True if name is valid (not empty after trimming), False otherwise
    """
    return bool(name and name.strip())


def trim_name(name: str) -> str:
    """
    Trim leading/trailing whitespace from name.

    Feature 052: Edge case handling per spec.md - whitespace should be
    trimmed automatically.

    Args:
        name: Name to trim

    Returns:
        Trimmed name
    """
    return name.strip() if name else ""
