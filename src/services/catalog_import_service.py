"""
Catalog Import Service - Entity-specific import for ingredients, products, and recipes.

Provides ADD_ONLY and AUGMENT modes for safe catalog expansion without
affecting transactional user data. This is separate from the unified
import/export service to support catalog-specific workflows.

Usage:
    from src.services.catalog_import_service import import_ingredients

    # Import ingredients from parsed catalog data
    result = import_ingredients(ingredient_data, mode="add")
    print(result.get_summary())
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session

from src.services.database import session_scope
from src.models.ingredient import Ingredient
from src.models.product import Product


# ============================================================================
# Enums and Data Classes
# ============================================================================


class ImportMode(str, Enum):
    """Import mode selection."""

    ADD_ONLY = "add"  # Create new, skip existing
    AUGMENT = "augment"  # Update null fields on existing, add new


@dataclass
class ImportError:
    """Structured error for import failures."""

    entity_type: str  # "ingredients", "products", "recipes"
    identifier: str  # slug, name, or composite key
    error_type: str  # "validation", "fk_missing", "duplicate", "format"
    message: str  # Human-readable error
    suggestion: str  # Actionable fix suggestion


@dataclass
class EntityImportCounts:
    """Per-entity import statistics."""

    added: int = 0
    skipped: int = 0
    failed: int = 0
    augmented: int = 0  # Tracks AUGMENT mode updates


# ============================================================================
# Result Class
# ============================================================================


class CatalogImportResult:
    """
    Result of a catalog import operation with per-entity tracking.

    Follows the pattern of ImportResult from import_export_service.py
    but adds catalog-specific tracking (augmented count, structured errors).
    """

    def __init__(self):
        self.entity_counts: Dict[str, EntityImportCounts] = {
            "ingredients": EntityImportCounts(),
            "products": EntityImportCounts(),
            "recipes": EntityImportCounts(),
        }
        self.errors: List[ImportError] = []
        self.warnings: List[str] = []
        self.dry_run: bool = False
        self.mode: str = "add"
        self._augment_details: List[Dict] = []  # Track which fields were augmented

    # -------------------------------------------------------------------------
    # Properties for aggregate counts
    # -------------------------------------------------------------------------

    @property
    def total_added(self) -> int:
        """Total records added across all entity types."""
        return sum(counts.added for counts in self.entity_counts.values())

    @property
    def total_skipped(self) -> int:
        """Total records skipped across all entity types."""
        return sum(counts.skipped for counts in self.entity_counts.values())

    @property
    def total_failed(self) -> int:
        """Total records failed across all entity types."""
        return sum(counts.failed for counts in self.entity_counts.values())

    @property
    def total_augmented(self) -> int:
        """Total records augmented across all entity types."""
        return sum(counts.augmented for counts in self.entity_counts.values())

    @property
    def total_processed(self) -> int:
        """Total records processed (added + skipped + failed + augmented)."""
        return self.total_added + self.total_skipped + self.total_failed + self.total_augmented

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred during import."""
        return len(self.errors) > 0

    # -------------------------------------------------------------------------
    # Mutation methods
    # -------------------------------------------------------------------------

    def add_success(self, entity_type: str) -> None:
        """Record a successful import (new record created)."""
        if entity_type in self.entity_counts:
            self.entity_counts[entity_type].added += 1

    def add_skip(self, entity_type: str, identifier: str, reason: str) -> None:
        """Record a skipped record (already exists in ADD_ONLY mode)."""
        if entity_type in self.entity_counts:
            self.entity_counts[entity_type].skipped += 1
        self.warnings.append(f"{entity_type.capitalize()} '{identifier}' skipped: {reason}")

    def add_error(
        self,
        entity_type: str,
        identifier: str,
        error_type: str,
        message: str,
        suggestion: str,
    ) -> None:
        """Record a failed import with structured error details."""
        if entity_type in self.entity_counts:
            self.entity_counts[entity_type].failed += 1
        self.errors.append(
            ImportError(
                entity_type=entity_type,
                identifier=identifier,
                error_type=error_type,
                message=message,
                suggestion=suggestion,
            )
        )

    def add_augment(
        self, entity_type: str, identifier: str, fields_updated: List[str]
    ) -> None:
        """Record an augmented record (existing record updated with null fields)."""
        if entity_type in self.entity_counts:
            self.entity_counts[entity_type].augmented += 1
        self._augment_details.append(
            {
                "entity_type": entity_type,
                "identifier": identifier,
                "fields_updated": fields_updated,
            }
        )

    def merge(self, other: "CatalogImportResult") -> None:
        """Merge another CatalogImportResult into this one."""
        for entity_type, counts in other.entity_counts.items():
            if entity_type in self.entity_counts:
                self.entity_counts[entity_type].added += counts.added
                self.entity_counts[entity_type].skipped += counts.skipped
                self.entity_counts[entity_type].failed += counts.failed
                self.entity_counts[entity_type].augmented += counts.augmented
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self._augment_details.extend(other._augment_details)

    # -------------------------------------------------------------------------
    # Reporting methods
    # -------------------------------------------------------------------------

    def get_summary(self) -> str:
        """Generate user-friendly summary for CLI/UI display."""
        lines = [
            "=" * 60,
            f"Catalog Import Summary (mode: {self.mode})",
        ]
        if self.dry_run:
            lines.append("*** DRY RUN - No changes committed ***")
        lines.append("=" * 60)

        # Per-entity breakdown
        for entity_type, counts in self.entity_counts.items():
            parts = []
            if counts.added > 0:
                parts.append(f"{counts.added} added")
            if counts.augmented > 0:
                parts.append(f"{counts.augmented} augmented")
            if counts.skipped > 0:
                parts.append(f"{counts.skipped} skipped")
            if counts.failed > 0:
                parts.append(f"{counts.failed} failed")
            if parts:
                lines.append(f"  {entity_type.capitalize()}: {', '.join(parts)}")

        lines.append("")
        lines.append(f"Total Processed: {self.total_processed}")
        lines.append(f"  Added:     {self.total_added}")
        lines.append(f"  Augmented: {self.total_augmented}")
        lines.append(f"  Skipped:   {self.total_skipped}")
        lines.append(f"  Failed:    {self.total_failed}")

        # Show errors
        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors[:10]:  # Limit to first 10
                lines.append(f"  - {error.entity_type}: {error.identifier}")
                lines.append(f"    {error.message}")
                lines.append(f"    Suggestion: {error.suggestion}")
            if len(self.errors) > 10:
                lines.append(f"  ... and {len(self.errors) - 10} more errors")

        # Show warnings (limited)
        if self.warnings and len(self.warnings) <= 10:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        elif self.warnings:
            lines.append(
                f"\n{len(self.warnings)} warnings (use detailed report for full list)"
            )

        lines.append("=" * 60)
        return "\n".join(lines)

    def get_detailed_report(self) -> str:
        """Generate detailed report with all errors and warnings."""
        lines = [self.get_summary()]

        # Full error list
        if len(self.errors) > 10:
            lines.append("\nAll Errors:")
            for error in self.errors:
                lines.append(f"  - [{error.error_type}] {error.entity_type}: {error.identifier}")
                lines.append(f"    Message: {error.message}")
                lines.append(f"    Suggestion: {error.suggestion}")

        # Full warning list
        if len(self.warnings) > 10:
            lines.append("\nAll Warnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        # Augment details
        if self._augment_details:
            lines.append("\nAugmented Records:")
            for detail in self._augment_details:
                fields = ", ".join(detail["fields_updated"])
                lines.append(
                    f"  - {detail['entity_type']}: {detail['identifier']} ({fields})"
                )

        return "\n".join(lines)


# ============================================================================
# Ingredient Import Functions
# ============================================================================


def import_ingredients(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult:
    """
    Import ingredients from parsed data.

    Independently callable for future integrations (USDA FDC, FoodOn).
    Uses the session=None pattern for transactional composition.

    Args:
        data: List of ingredient dictionaries from catalog file
        mode: "add" (ADD_ONLY) or "augment" (AUGMENT mode)
        dry_run: If True, validate and preview without committing
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        CatalogImportResult with counts and any errors
    """
    if session is not None:
        return _import_ingredients_impl(data, mode, dry_run, session)
    with session_scope() as sess:
        return _import_ingredients_impl(data, mode, dry_run, sess)


def _import_ingredients_impl(
    data: List[Dict],
    mode: str,
    dry_run: bool,
    session: Session,
) -> CatalogImportResult:
    """Internal implementation of ingredient import."""
    result = CatalogImportResult()
    result.dry_run = dry_run
    result.mode = mode

    # Query existing slugs for duplicate detection
    existing_slugs = {
        row[0] for row in session.query(Ingredient.slug).filter(Ingredient.slug.isnot(None)).all()
    }

    for item in data:
        # Extract identifier for error reporting
        slug = item.get("slug", "")
        identifier = slug or item.get("display_name", "unknown")

        # Validate required fields
        validation_error = _validate_ingredient_data(item)
        if validation_error:
            result.add_error(
                "ingredients",
                identifier,
                "validation",
                validation_error["message"],
                validation_error["suggestion"],
            )
            continue

        # Check for existing slug
        if slug in existing_slugs:
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("ingredients", slug, "Already exists")
                continue
            # AUGMENT mode will be implemented in WP04
            # For now, skip in add mode only
            result.add_skip("ingredients", slug, "Already exists (augment mode pending WP04)")
            continue

        # Create new ingredient
        ingredient = Ingredient(
            slug=slug,
            display_name=item.get("display_name"),
            category=item.get("category"),
            description=item.get("description"),
            is_packaging=item.get("is_packaging", False),
            # Density fields (4-field model)
            density_volume_value=item.get("density_volume_value"),
            density_volume_unit=item.get("density_volume_unit"),
            density_weight_value=item.get("density_weight_value"),
            density_weight_unit=item.get("density_weight_unit"),
            # Industry standard identifiers
            allergens=item.get("allergens"),
            foodon_id=item.get("foodon_id"),
            fdc_ids=item.get("fdc_ids"),
            foodex2_code=item.get("foodex2_code"),
            langual_terms=item.get("langual_terms"),
        )
        session.add(ingredient)
        result.add_success("ingredients")

        # Track slug to prevent duplicates within same import
        existing_slugs.add(slug)

    # Handle dry-run: rollback instead of commit
    if dry_run:
        session.rollback()
    # Note: session_scope handles commit automatically on success

    return result


def _validate_ingredient_data(item: Dict) -> Optional[Dict]:
    """
    Validate ingredient data before creation.

    Args:
        item: Ingredient dictionary from catalog file

    Returns:
        None if valid, or dict with 'message' and 'suggestion' keys if invalid
    """
    # Check required fields
    if not item.get("slug"):
        return {
            "message": "Missing required field: slug",
            "suggestion": "Add 'slug' field to ingredient data (e.g., 'all_purpose_flour')",
        }

    if not item.get("display_name"):
        return {
            "message": "Missing required field: display_name",
            "suggestion": "Add 'display_name' field to ingredient data (e.g., 'All-Purpose Flour')",
        }

    if not item.get("category"):
        return {
            "message": "Missing required field: category",
            "suggestion": "Add 'category' field to ingredient data (e.g., 'Flour', 'Sugar', 'Dairy')",
        }

    # Validate slug format (non-empty string, no spaces preferred)
    slug = item.get("slug", "")
    if not isinstance(slug, str) or len(slug.strip()) == 0:
        return {
            "message": "Invalid slug: must be non-empty string",
            "suggestion": "Provide a valid slug identifier (e.g., 'brown_sugar')",
        }

    return None


# ============================================================================
# Product Import Functions
# ============================================================================


def import_products(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult:
    """
    Import products from parsed data.

    Validates ingredient_slug FK references before creating products.
    Independently callable for future integrations (UPC databases).
    Uses the session=None pattern for transactional composition.

    Args:
        data: List of product dictionaries from catalog file
        mode: "add" (ADD_ONLY) or "augment" (AUGMENT mode)
        dry_run: If True, validate and preview without committing
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        CatalogImportResult with counts and any errors
    """
    if session is not None:
        return _import_products_impl(data, mode, dry_run, session)
    with session_scope() as sess:
        return _import_products_impl(data, mode, dry_run, sess)


def _import_products_impl(
    data: List[Dict],
    mode: str,
    dry_run: bool,
    session: Session,
) -> CatalogImportResult:
    """Internal implementation of product import."""
    result = CatalogImportResult()
    result.dry_run = dry_run
    result.mode = mode

    # Build ingredient slug -> id lookup for FK validation
    slug_to_id = {
        row.slug: row.id
        for row in session.query(Ingredient.slug, Ingredient.id).filter(
            Ingredient.slug.isnot(None)
        ).all()
    }

    # Build existing products lookup for uniqueness check
    # Unique key is (ingredient_id, brand) where brand can be None
    existing_products = {
        (row.ingredient_id, row.brand)
        for row in session.query(Product.ingredient_id, Product.brand).all()
    }

    for item in data:
        # Extract fields for identification and validation
        ingredient_slug = item.get("ingredient_slug", "")
        brand = item.get("brand")  # Can be None
        identifier = f"{brand or 'Generic'} ({ingredient_slug})"

        # Validate required fields
        validation_error = _validate_product_data(item)
        if validation_error:
            result.add_error(
                "products",
                identifier,
                "validation",
                validation_error["message"],
                validation_error["suggestion"],
            )
            continue

        # FK validation: check ingredient exists
        ingredient_id = slug_to_id.get(ingredient_slug)
        if ingredient_id is None:
            result.add_error(
                "products",
                identifier,
                "fk_missing",
                f"Ingredient '{ingredient_slug}' not found",
                "Import the ingredient first or check the slug spelling",
            )
            continue

        # Check for existing product with same (ingredient_id, brand)
        if (ingredient_id, brand) in existing_products:
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("products", identifier, "Already exists")
                continue
            # AUGMENT mode will be implemented in WP04
            result.add_skip("products", identifier, "Already exists (augment mode pending WP04)")
            continue

        # Create new product
        product = Product(
            ingredient_id=ingredient_id,
            brand=brand,
            package_size=item.get("package_size"),
            package_type=item.get("package_type"),
            purchase_unit=item.get("purchase_unit"),
            purchase_quantity=item.get("purchase_quantity"),
            upc_code=item.get("upc_code"),
            preferred=item.get("preferred", False),
        )
        session.add(product)
        result.add_success("products")

        # Track to prevent duplicates within same import
        existing_products.add((ingredient_id, brand))

    # Handle dry-run: rollback instead of commit
    if dry_run:
        session.rollback()

    return result


def _validate_product_data(item: Dict) -> Optional[Dict]:
    """
    Validate product data before creation.

    Args:
        item: Product dictionary from catalog file

    Returns:
        None if valid, or dict with 'message' and 'suggestion' keys if invalid
    """
    # Check required fields
    if not item.get("ingredient_slug"):
        return {
            "message": "Missing required field: ingredient_slug",
            "suggestion": "Add 'ingredient_slug' field referencing an existing ingredient",
        }

    if not item.get("purchase_unit"):
        return {
            "message": "Missing required field: purchase_unit",
            "suggestion": "Add 'purchase_unit' field (e.g., 'bag', 'lb', 'oz')",
        }

    if item.get("purchase_quantity") is None:
        return {
            "message": "Missing required field: purchase_quantity",
            "suggestion": "Add 'purchase_quantity' field (e.g., 25, 5.0)",
        }

    return None
