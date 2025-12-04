"""Slug generation utilities for ingredient naming.

This module provides utilities for generating URL-safe,deterministic slugs from
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
                If None, no uniqueness check is performed.

    Returns:
        URL-safe slug string (lowercase, alphanumeric + underscores only)

    Examples:
        >>> create_slug("All-Purpose Flour")
        'all_purpose_flour'

        >>> create_slug("Confectioner's Sugar")
        'confectioners_sugar'

        >>> create_slug("Jalapeno Peppers")
        'jalapeno_peppers'

        >>> create_slug("    Extra  Spaces   ")
        'extra_spaces'

        >>> create_slug("100% Whole Wheat")
        '100_whole_wheat'

        >>> # With session - auto-increment on conflicts
        >>> create_slug("All-Purpose Flour", session)  # First time
        'all_purpose_flour'
        >>> create_slug("All-Purpose Flour", session)  # Duplicate
        'all_purpose_flour_1'
        >>> create_slug("All-Purpose Flour", session)  # Another duplicate
        'all_purpose_flour_2'

    Note:
        - Slug generation is deterministic: same input always produces same base slug
        - Only numeric suffixes are appended for uniqueness, never random strings
        - Empty or whitespace-only input will result in empty slug (caller should validate)
    """
    # Unicode normalization: decompose accented characters
    # Example: accented "e" (U+00E9) becomes "e" (U+0065) + combining acute accent
    normalized = unicodedata.normalize("NFD", name)

    # Encode to ASCII, ignoring characters that can't be represented
    # This converts "Jalapeno" to "Jalapeno", "Creme" to "Creme", etc.
    slug = normalized.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase
    slug = slug.lower()

    # Replace whitespace and hyphens with underscores
    # "All-Purpose Flour" -> "all_purpose_flour"
    slug = re.sub(r"[\s\-]+", "_", slug)

    # Remove all non-alphanumeric characters except underscores
    # "100% Whole" -> "100_whole"
    slug = re.sub(r"[^a-z0-9_]", "", slug)

    # Collapse multiple consecutive underscores to single underscore
    # "extra___spaces" -> "extra_spaces"
    slug = re.sub(r"_+", "_", slug)

    # Strip leading and trailing underscores
    slug = slug.strip("_")

    # If no session provided, return base slug without uniqueness check
    if session is None:
        return slug

    # Uniqueness checking with auto-increment
    # Check if slug already exists in database
    from ..models import Ingredient  # Import here to avoid circular dependency

    # Try base slug first
    existing = session.query(Ingredient).filter_by(slug=slug).first()
    if not existing:
        return slug

    # Base slug exists, try appending incrementing numbers
    original_slug = slug
    counter = 1

    while True:
        candidate_slug = f"{original_slug}_{counter}"
        existing = session.query(Ingredient).filter_by(slug=candidate_slug).first()

        if not existing:
            return candidate_slug

        counter += 1

        # Safety check: prevent infinite loop (should never happen in practice)
        if counter > 10000:
            raise ValueError(
                f"Unable to generate unique slug for '{name}' after 10000 attempts. "
                "This should never happen - please investigate database state."
            )


def validate_slug_format(slug: str) -> bool:
    """Validate that a slug meets format requirements.

    Args:
        slug: Slug string to validate

    Returns:
        True if slug is valid, False otherwise

    Valid slugs must:
        - Contain only lowercase letters, digits, and underscores
        - Not start or end with underscore
        - Not contain consecutive underscores
        - Not be empty

    Examples:
        >>> validate_slug_format("all_purpose_flour")
        True

        >>> validate_slug_format("AllPurpose")  # Has uppercase
        False

        >>> validate_slug_format("_starts_with_underscore")
        False

        >>> validate_slug_format("ends_with_underscore_")
        False

        >>> validate_slug_format("has__double__underscores")
        False

        >>> validate_slug_format("")
        False
    """
    if not slug:
        return False

    # Check for valid characters (lowercase alphanumeric + underscore)
    if not re.match(r"^[a-z0-9_]+$", slug):
        return False

    # Check doesn't start or end with underscore
    if slug.startswith("_") or slug.endswith("_"):
        return False

    # Check for consecutive underscores
    if "__" in slug:
        return False

    return True


def slug_to_display_name(slug: str) -> str:
    """Convert slug back to approximate display name.

    This function attempts to reverse the slug generation process to create
    a human-readable name. Note that this is lossy - some information like
    original capitalization and punctuation cannot be recovered.

    Args:
        slug: Slug to convert

    Returns:
        Display name with title case and spaces

    Examples:
        >>> slug_to_display_name("all_purpose_flour")
        'All Purpose Flour'

        >>> slug_to_display_name("confectioners_sugar")
        'Confectioners Sugar'

        >>> slug_to_display_name("100_whole_wheat")
        '100 Whole Wheat'

    Note:
        This is a best-effort conversion. Original names should be stored
        separately and not derived from slugs.
    """
    # Replace underscores with spaces
    display = slug.replace("_", " ")

    # Title case (capitalize first letter of each word)
    display = display.title()

    return display
