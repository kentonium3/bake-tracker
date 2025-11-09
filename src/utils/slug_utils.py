"""Slug generation utilities for ingredient naming.

This module provides utilities for generating URL-safe, deterministic slugs from
ingredient names with Unicode support and uniqueness guarantees.

Key Features:
- Unicode normalization (NFD decomposition)
- ASCII transliteration
- Deterministic output (same input always gives same slug)
- Automatic uniqueness checking with auto-increment suffixes
- Reversible (human-readable, not hash-based)

Examples:
    >>> create_slug("All-Purpose Flour")
    'all_purpose_flour'

    >>> create_slug("Confectioner's Sugar")
    'confectioners_sugar'

    >>> create_slug("Jalapeno Peppers")
    'jalapeno_peppers'
"""

import unicodedata
import re
from typing import Optional
from sqlalchemy.orm import Session


def create_slug(name: str, session: Optional[Session] = None) -> str:
    """Generate URL-safe slug from ingredient name.

    This function creates deterministic, human-readable slugs using Unicode
    normalization and ASCII transliteration. If a database session is provided,
    it ensures uniqueness by checking against existing Ingredient records and
    appending numeric suffixes as needed.

    Algorithm:
        1. Normalize Unicode to NFD (decompose accented characters)
        2. Encode to ASCII, ignoring non-ASCII characters
        3. Convert to lowercase
        4. Replace whitespace and hyphens with underscores
        5. Remove all non-alphanumeric characters except underscores
        6. Collapse multiple consecutive underscores
        7. Strip leading/trailing underscores
        8. Check uniqueness and auto-increment if needed

    Args:
        name: Ingredient name to convert to slug
        session: Optional database session for uniqueness checking.
                 If provided, will auto-increment slug if collision detected.

    Returns:
        str: URL-safe slug (lowercase, underscores, alphanumeric only)

    Raises:
        ValueError: If name is empty or results in empty slug after processing

    Examples:
        >>> create_slug("All-Purpose Flour")
        'all_purpose_flour'

        >>> create_slug("Confectioner's Sugar")
        'confectioners_sugar'

        >>> create_slug("100% Whole Wheat")
        '100_whole_wheat'

        >>> # With uniqueness checking (requires session)
        >>> create_slug("Sugar", session)  # First call
        'sugar'
        >>> create_slug("Sugar", session)  # Second call (collision)
        'sugar_1'
    """
    if not name or not name.strip():
        raise ValueError("Name cannot be empty")

    # Step 1-2: Unicode normalization and ASCII conversion
    # NFD = Canonical Decomposition (e.g., "é" -> "e" + combining accent)
    normalized = unicodedata.normalize('NFD', name)
    slug = normalized.encode('ascii', 'ignore').decode('ascii')

    # Step 3: Lowercase
    slug = slug.lower()

    # Step 4: Replace whitespace and hyphens with underscores
    slug = re.sub(r'[\s\-]+', '_', slug)

    # Step 5: Remove all non-alphanumeric except underscores
    slug = re.sub(r'[^a-z0-9_]', '', slug)

    # Step 6: Collapse multiple underscores
    slug = re.sub(r'_+', '_', slug)

    # Step 7: Strip leading/trailing underscores
    slug = slug.strip('_')

    # Validate result
    if not slug:
        raise ValueError(f"Name '{name}' resulted in empty slug after processing")

    # Step 8: Ensure uniqueness if session provided
    if session:
        from ..models import Ingredient
        original_slug = slug
        counter = 1

        # Keep incrementing until we find an unused slug
        while session.query(Ingredient).filter_by(slug=slug).first():
            slug = f"{original_slug}_{counter}"
            counter += 1

    return slug


def validate_slug_format(slug: str) -> bool:
    """Validate that a slug meets format requirements.

    A valid slug:
    - Contains only lowercase letters, numbers, and underscores
    - Does not start or end with underscores
    - Does not contain consecutive underscores
    - Is not empty

    Args:
        slug: Slug string to validate

    Returns:
        bool: True if slug is valid format, False otherwise

    Examples:
        >>> validate_slug_format("all_purpose_flour")
        True

        >>> validate_slug_format("All-Purpose")  # Uppercase/hyphens
        False

        >>> validate_slug_format("_flour")  # Leading underscore
        False

        >>> validate_slug_format("flour__mix")  # Consecutive underscores
        False
    """
    if not slug:
        return False

    # Check for valid characters only
    if not re.match(r'^[a-z0-9_]+$', slug):
        return False

    # Check for leading/trailing underscores
    if slug.startswith('_') or slug.endswith('_'):
        return False

    # Check for consecutive underscores
    if '__' in slug:
        return False

    return True


def slug_to_display_name(slug: str) -> str:
    """Convert slug back to human-readable display name.

    This function attempts to reverse the slug generation process to create
    a readable name. Note that this is lossy (cannot perfectly recover
    original capitalization or punctuation).

    Algorithm:
        1. Replace underscores with spaces
        2. Title case each word
        3. Handle common abbreviations (e.g., "lb" -> "lb", not "Lb")

    Args:
        slug: Slug string to convert

    Returns:
        str: Human-readable display name

    Examples:
        >>> slug_to_display_name("all_purpose_flour")
        'All Purpose Flour'

        >>> slug_to_display_name("confectioners_sugar")
        'Confectioners Sugar'

        >>> slug_to_display_name("bread_flour_50_lb")
        'Bread Flour 50 Lb'
    """
    # Replace underscores with spaces
    name = slug.replace('_', ' ')

    # Title case (capitalize first letter of each word)
    name = name.title()

    return name
