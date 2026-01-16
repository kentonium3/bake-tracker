"""
Catalog Import Service - Entity-specific import for ingredients, products, and recipes.

Provides ADD_ONLY and AUGMENT modes for safe catalog expansion without
affecting transactional user data. This is separate from the unified
import/export service to support catalog-specific workflows.

Usage:
    from src.services.catalog_import_service import import_catalog, validate_catalog_file

    # Validate and import from catalog file
    result = import_catalog("catalog.json", mode="add", dry_run=True)
    print(result.get_summary())

    # Or import specific entities
    result = import_catalog("catalog.json", entities=["ingredients", "products"])
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session

from src.services.database import session_scope
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.recipe import Recipe, RecipeIngredient, RecipeComponent
from src.models.supplier import Supplier
from src.models.material_category import MaterialCategory
from src.models.material_subcategory import MaterialSubcategory
from src.models.material import Material
from src.models.material_product import MaterialProduct
from src.models.material_unit import MaterialUnit
from src.models.supplier import Supplier
from src.services.material_catalog_service import slugify


# ============================================================================
# Exceptions
# ============================================================================


class CatalogImportError(Exception):
    """Raised when catalog import fails due to file/format issues."""

    pass


# ============================================================================
# Constants
# ============================================================================

# Valid entity types for import
VALID_ENTITIES = {
    # Feature 051: Suppliers must be first (products reference suppliers)
    "suppliers",
    "ingredients", "products", "recipes",
    # Feature 047: Materials Management System
    "material_categories", "material_subcategories", "materials",
    "material_products", "material_units",
}


# ============================================================================
# Enums and Data Classes
# ============================================================================


class ImportMode(str, Enum):
    """Import mode selection."""

    ADD_ONLY = "add"  # Create new, skip existing
    AUGMENT = "augment"  # Update null fields on existing, add new


# ============================================================================
# Field Classification Constants for AUGMENT Mode
# ============================================================================

# Ingredient fields: Protected = never modified; Augmentable = updated only if current value is NULL
INGREDIENT_PROTECTED_FIELDS = {"slug", "display_name", "id", "date_added", "category"}
INGREDIENT_AUGMENTABLE_FIELDS = {
    "density_volume_value",
    "density_volume_unit",
    "density_weight_value",
    "density_weight_unit",
    "foodon_id",
    "fdc_ids",
    "foodex2_code",
    "langual_terms",
    "allergens",
    "description",
    "hierarchy_level",  # Feature 031: Ingredient hierarchy
}

# Product fields: Protected = never modified; Augmentable = updated only if current value is NULL
PRODUCT_PROTECTED_FIELDS = {"ingredient_id", "brand", "id", "date_added"}
PRODUCT_AUGMENTABLE_FIELDS = {
    "product_name",
    "upc_code",
    "package_size",
    "package_type",
    "package_unit",
    "package_unit_quantity",
    "preferred",
    "supplier",
    "supplier_sku",
    "notes",
    "gtin",
    "brand_owner",
    "gpc_brick_code",
    "net_content_value",
    "net_content_uom",
    "country_of_sale",
    "off_id",
}

# Feature 051: Supplier fields for AUGMENT mode
SUPPLIER_PROTECTED_FIELDS = {"slug", "name", "id", "created_at"}
SUPPLIER_AUGMENTABLE_FIELDS = {
    "supplier_type",
    "city",
    "state",
    "zip_code",
    "street_address",
    "website_url",
    "notes",
    "is_active",
}


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
            # Feature 051: Suppliers must be first (products reference suppliers)
            "suppliers": EntityImportCounts(),
            "ingredients": EntityImportCounts(),
            "products": EntityImportCounts(),
            "recipes": EntityImportCounts(),
            # Feature 047: Materials Management System
            "material_categories": EntityImportCounts(),
            "material_subcategories": EntityImportCounts(),
            "materials": EntityImportCounts(),
            "material_products": EntityImportCounts(),
            "material_units": EntityImportCounts(),
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
                if error.suggestion:  # Only show suggestion if non-empty
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
                if error.suggestion:  # Only show suggestion if non-empty
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
# Supplier Import Functions (Feature 051)
# ============================================================================


def import_suppliers(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult:
    """
    Import suppliers from parsed data.

    Independently callable for catalog imports. Uses the session=None pattern
    for transactional composition.

    Args:
        data: List of supplier dictionaries from catalog file
        mode: "add" (ADD_ONLY) or "augment" (AUGMENT mode)
        dry_run: If True, validate and preview without committing
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        CatalogImportResult with counts and any errors
    """
    if session is not None:
        return _import_suppliers_impl(data, mode, dry_run, session)
    with session_scope() as sess:
        return _import_suppliers_impl(data, mode, dry_run, sess)


def _import_suppliers_impl(
    data: List[Dict],
    mode: str,
    dry_run: bool,
    session: Session,
) -> CatalogImportResult:
    """Internal implementation of supplier import."""
    from src.services.supplier_service import generate_supplier_slug

    result = CatalogImportResult()
    result.dry_run = dry_run
    result.mode = mode

    # Query existing suppliers for duplicate detection and AUGMENT mode
    existing_suppliers = {
        row.slug: row
        for row in session.query(Supplier).filter(Supplier.slug.isnot(None)).all()
    }
    existing_slugs = set(existing_suppliers.keys())

    # Also track names for slug collision detection
    existing_names = {
        row.name: row.slug
        for row in session.query(Supplier).all()
    }

    for item in data:
        name = item.get("name", "")
        slug = item.get("slug", "")

        # Generate slug if not provided
        if not slug and name:
            slug = generate_supplier_slug(name)

        identifier = slug or name or "unknown"

        # Validate required fields
        if not name:
            result.add_error(
                "suppliers",
                identifier,
                "validation",
                "Missing required field: name",
                "Ensure each supplier has a 'name' field",
            )
            continue

        # Check for slug collision with different name
        if slug in existing_slugs:
            existing_supplier = existing_suppliers[slug]
            if existing_supplier.name != name:
                result.add_error(
                    "suppliers",
                    identifier,
                    "duplicate",
                    f"Slug '{slug}' already exists for different supplier '{existing_supplier.name}'",
                    f"Change the slug or use a unique identifier",
                )
                continue

            # Same slug and matching name - handle based on mode
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("suppliers", slug, "Already exists")
                continue

            # AUGMENT mode: update only null fields
            updated_fields = []
            for field in SUPPLIER_AUGMENTABLE_FIELDS:
                if field in item and item[field] is not None:
                    current_value = getattr(existing_supplier, field, None)
                    if current_value is None:
                        setattr(existing_supplier, field, item[field])
                        updated_fields.append(field)

            if updated_fields:
                result.add_augment("suppliers", slug, updated_fields)
            else:
                result.add_skip("suppliers", slug, "No null fields to update")
            continue

        # Check if name exists but with different slug (name collision)
        if name in existing_names and existing_names[name] != slug:
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("suppliers", name, "Supplier with this name already exists")
                continue

        # Create new supplier
        supplier = Supplier(
            slug=slug,
            name=name,
            supplier_type=item.get("supplier_type", "physical"),
            city=item.get("city"),
            state=item.get("state"),
            zip_code=item.get("zip_code"),
            street_address=item.get("street_address"),
            website_url=item.get("website_url"),
            notes=item.get("notes"),
            is_active=item.get("is_active", True),
        )

        if not dry_run:
            session.add(supplier)
            session.flush()  # Get ID for FK references

        result.add_success("suppliers")

        # Track for subsequent imports in same transaction
        existing_suppliers[slug] = supplier
        existing_slugs.add(slug)
        existing_names[name] = slug

    return result


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

    # Query existing ingredients for duplicate detection and AUGMENT mode
    existing_ingredients = {
        row.slug: row
        for row in session.query(Ingredient).filter(Ingredient.slug.isnot(None)).all()
    }
    existing_slugs = set(existing_ingredients.keys())

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
            # AUGMENT mode: update only null fields
            existing_ingredient = existing_ingredients[slug]
            updated_fields = []
            for field in INGREDIENT_AUGMENTABLE_FIELDS:
                if field in item and item[field] is not None:
                    current_value = getattr(existing_ingredient, field, None)
                    if current_value is None:
                        setattr(existing_ingredient, field, item[field])
                        updated_fields.append(field)
            if updated_fields:
                result.add_augment("ingredients", slug, updated_fields)
            else:
                result.add_skip("ingredients", slug, "No null fields to update")
            continue

        # Create new ingredient
        # Feature 031: hierarchy_level defaults to 2 (leaf) if not specified
        hierarchy_level = item.get("hierarchy_level", 2)

        ingredient = Ingredient(
            slug=slug,
            display_name=item.get("display_name"),
            category=item.get("category"),
            description=item.get("description"),
            hierarchy_level=hierarchy_level,
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

        # Track for duplicate detection within same import
        existing_slugs.add(slug)
        existing_ingredients[slug] = ingredient

    # Feature 031: Second pass to resolve parent_slug references
    # Flush first to ensure all ingredients have IDs
    session.flush()

    for item in data:
        parent_slug = item.get("parent_slug")
        if parent_slug:
            slug = item.get("slug", "")
            ingredient = existing_ingredients.get(slug)
            if not ingredient:
                # Try to find in DB (may have been skipped as existing)
                ingredient = session.query(Ingredient).filter_by(slug=slug).first()

            parent = existing_ingredients.get(parent_slug)
            if not parent:
                # Try to find in DB
                parent = session.query(Ingredient).filter_by(slug=parent_slug).first()

            if ingredient and parent:
                ingredient.parent_ingredient_id = parent.id
            elif ingredient and not parent:
                result.add_warning(
                    "ingredients",
                    slug,
                    f"Parent '{parent_slug}' not found - hierarchy not set",
                )

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
    supplier_id_to_slug: Optional[Dict[int, str]] = None,
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
        supplier_id_to_slug: Mapping of old supplier IDs to slugs for FK resolution

    Returns:
        CatalogImportResult with counts and any errors
    """
    if session is not None:
        return _import_products_impl(data, mode, dry_run, session, supplier_id_to_slug)
    with session_scope() as sess:
        return _import_products_impl(data, mode, dry_run, sess, supplier_id_to_slug)


def _import_products_impl(
    data: List[Dict],
    mode: str,
    dry_run: bool,
    session: Session,
    supplier_id_to_slug: Optional[Dict[int, str]] = None,
) -> CatalogImportResult:
    """Internal implementation of product import.

    Product matching uses (ingredient_id, brand, package_unit_quantity, package_unit)
    to identify existing products. If multiple products match (ambiguous), the import
    skips that item to avoid updating the wrong record.
    """
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

    # Build supplier lookups for resolving preferred_supplier
    # Support: preferred_supplier_id (int), supplier_slug, supplier_name
    from src.models.supplier import Supplier
    supplier_by_id = {
        row.id: row.id
        for row in session.query(Supplier.id).all()
    }
    supplier_slug_to_id = {
        row.slug.lower(): row.id
        for row in session.query(Supplier.slug, Supplier.id).filter(
            Supplier.slug.isnot(None)
        ).all()
    }
    supplier_name_to_id = {
        row.name.lower(): row.id
        for row in session.query(Supplier.name, Supplier.id).all()
    }

    # Build existing products lookup for uniqueness check and AUGMENT mode
    # Key: (ingredient_id, brand, package_unit_quantity, package_unit)
    # Value: List of matching products (to detect ambiguity)
    from collections import defaultdict
    existing_products_map = defaultdict(list)
    for row in session.query(Product).all():
        key = (row.ingredient_id, row.brand, row.package_unit_quantity, row.package_unit)
        existing_products_map[key].append(row)

    for item in data:
        # Extract fields for identification and validation
        ingredient_slug = item.get("ingredient_slug", "")
        brand = item.get("brand")  # Can be None
        package_unit_quantity = item.get("package_unit_quantity")
        package_unit = item.get("package_unit")
        identifier = f"{brand or 'Generic'} ({ingredient_slug}) {package_unit_quantity} {package_unit}"

        # Validate required fields (relaxed for AUGMENT mode on existing records)
        if mode == ImportMode.ADD_ONLY.value:
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
        else:
            # For AUGMENT mode, need ingredient_slug plus package info for matching
            if not ingredient_slug:
                result.add_error(
                    "products",
                    identifier,
                    "validation",
                    "Missing required field: ingredient_slug",
                    "Add 'ingredient_slug' field referencing an existing ingredient",
                )
                continue
            if package_unit_quantity is None or not package_unit:
                result.add_error(
                    "products",
                    identifier,
                    "validation",
                    "Missing package_unit_quantity or package_unit for matching",
                    "Add package_unit_quantity and package_unit to identify the product",
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

        # Resolve preferred supplier (support: supplier_slug, supplier_name, preferred_supplier_id)
        resolved_supplier_id = None
        supplier_slug = item.get("supplier_slug") or item.get("preferred_supplier_slug")
        supplier_name = item.get("supplier_name") or item.get("preferred_supplier_name")
        supplier_id_from_import = item.get("preferred_supplier_id")

        if supplier_slug:
            resolved_supplier_id = supplier_slug_to_id.get(supplier_slug.lower())
        elif supplier_name:
            resolved_supplier_id = supplier_name_to_id.get(supplier_name.lower())
        elif supplier_id_from_import and supplier_id_to_slug:
            # Use the ID->slug mapping from the same import file, then resolve slug
            mapped_slug = supplier_id_to_slug.get(supplier_id_from_import)
            if mapped_slug:
                resolved_supplier_id = supplier_slug_to_id.get(mapped_slug.lower())
        elif supplier_id_from_import:
            # Fallback: try to match by ID directly if it exists in database
            if supplier_id_from_import in supplier_by_id:
                resolved_supplier_id = supplier_id_from_import

        # Build matching key
        product_key = (ingredient_id, brand, package_unit_quantity, package_unit)
        matching_products = existing_products_map.get(product_key, [])

        if len(matching_products) > 1:
            # Ambiguous: multiple products match the key - skip to avoid wrong update
            result.add_skip(
                "products",
                identifier,
                f"Ambiguous: {len(matching_products)} products match this key"
            )
            continue

        if len(matching_products) == 1:
            # Exactly one match
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("products", identifier, "Already exists")
                continue
            # AUGMENT mode: update only null fields
            existing_product = matching_products[0]
            updated_fields = []
            for field in PRODUCT_AUGMENTABLE_FIELDS:
                if field in item and item[field] is not None:
                    current_value = getattr(existing_product, field, None)
                    if current_value is None:
                        setattr(existing_product, field, item[field])
                        updated_fields.append(field)
            # Also augment preferred_supplier_id if resolved and currently null
            if resolved_supplier_id and existing_product.preferred_supplier_id is None:
                existing_product.preferred_supplier_id = resolved_supplier_id
                updated_fields.append("preferred_supplier_id")
            if updated_fields:
                result.add_augment("products", identifier, updated_fields)
            else:
                result.add_skip("products", identifier, "No null fields to update")
            continue

        # No match found - create new product
        # For new products, require full validation
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

        # Create new product
        product = Product(
            ingredient_id=ingredient_id,
            brand=brand,
            product_name=item.get("product_name"),
            package_size=item.get("package_size"),
            package_type=item.get("package_type"),
            package_unit=package_unit,
            package_unit_quantity=package_unit_quantity,
            upc_code=item.get("upc_code"),
            gtin=item.get("gtin"),
            preferred=item.get("preferred", False),
            preferred_supplier_id=resolved_supplier_id,
        )
        session.add(product)
        result.add_success("products")

        # Track to prevent duplicates within same import
        existing_products_map[product_key].append(product)

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

    if not item.get("package_unit"):
        return {
            "message": "Missing required field: package_unit",
            "suggestion": "Add 'package_unit' field (e.g., 'bag', 'lb', 'oz')",
        }

    if item.get("package_unit_quantity") is None:
        return {
            "message": "Missing required field: package_unit_quantity",
            "suggestion": "Add 'package_unit_quantity' field (e.g., 25, 5.0)",
        }

    return None


# ============================================================================
# Recipe Import Functions
# ============================================================================


def import_recipes(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult:
    """
    Import recipes from parsed data.

    Validates ingredient_slug and recipe_name FK references.
    Detects circular recipe references.
    AUGMENT mode is not supported for recipes - raises error if requested.

    Args:
        data: List of recipe dictionaries from catalog file
        mode: Must be "add" (AUGMENT not supported for recipes)
        dry_run: If True, validate and preview without committing
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        CatalogImportResult with counts and any errors
    """
    if session is not None:
        return _import_recipes_impl(data, mode, dry_run, session)
    with session_scope() as sess:
        return _import_recipes_impl(data, mode, dry_run, sess)


def _import_recipes_impl(
    data: List[Dict],
    mode: str,
    dry_run: bool,
    session: Session,
) -> CatalogImportResult:
    """Internal implementation of recipe import."""
    result = CatalogImportResult()
    result.dry_run = dry_run
    result.mode = mode

    # AUGMENT mode not supported for recipes
    if mode == ImportMode.AUGMENT.value:
        result.add_error(
            "recipes",
            "all",
            "mode_not_supported",
            "AUGMENT mode is not supported for recipes",
            "Use ADD_ONLY (--mode=add) for recipe import",
        )
        return result

    # Early exit if no data
    if not data:
        return result

    # Check for circular references before any imports
    cycle = _detect_cycles(data)
    if cycle:
        result.add_error(
            "recipes",
            cycle[0],
            "circular_reference",
            f"Circular reference detected: {' -> '.join(cycle)}",
            "Remove circular dependency to import",
        )
        return result

    # Build ingredient slug -> id lookup for FK validation
    slug_to_id = {
        row.slug: row.id
        for row in session.query(Ingredient.slug, Ingredient.id).filter(
            Ingredient.slug.isnot(None)
        ).all()
    }

    # Build recipe name -> (id, yield_quantity, yield_unit) lookup for collision detection and FK
    existing_recipes = {
        row.name: {"id": row.id, "yield_quantity": row.yield_quantity, "yield_unit": row.yield_unit}
        for row in session.query(
            Recipe.name, Recipe.id, Recipe.yield_quantity, Recipe.yield_unit
        ).all()
    }

    # Track newly created recipes for component FK resolution within the same import
    new_recipe_ids = {}  # name -> id

    for item in data:
        recipe_name = item.get("name", "")
        identifier = recipe_name or "unknown"

        # Validate required fields
        validation_error = _validate_recipe_data(item)
        if validation_error:
            result.add_error(
                "recipes",
                identifier,
                "validation",
                validation_error["message"],
                validation_error["suggestion"],
            )
            continue

        # Check for name collision with existing recipe
        if recipe_name in existing_recipes:
            existing = existing_recipes[recipe_name]
            import_yield_qty = item.get("yield_quantity", 0)
            import_yield_unit = item.get("yield_unit", "")
            result.add_error(
                "recipes",
                recipe_name,
                "collision",
                f"Recipe '{recipe_name}' already exists. "
                f"Existing: yields {existing['yield_quantity']} {existing['yield_unit']}. "
                f"Import: yields {import_yield_qty} {import_yield_unit}.",
                "Delete existing recipe or rename import",
            )
            continue

        # Validate ingredient FKs
        recipe_ingredients_data = item.get("ingredients", [])
        missing_ingredients = []
        for ri in recipe_ingredients_data:
            ing_slug = ri.get("ingredient_slug", "")
            if ing_slug not in slug_to_id:
                missing_ingredients.append(ing_slug)

        if missing_ingredients:
            result.add_error(
                "recipes",
                recipe_name,
                "fk_missing",
                f"Missing ingredients: {', '.join(missing_ingredients)}",
                "Import these ingredients first or remove from recipe",
            )
            continue

        # Validate component recipe FKs
        recipe_components_data = item.get("components", [])
        missing_components = []
        for rc in recipe_components_data:
            component_name = rc.get("recipe_name", "")
            # Component must exist in DB or have been created earlier in this import
            if component_name not in existing_recipes and component_name not in new_recipe_ids:
                missing_components.append(component_name)

        if missing_components:
            result.add_error(
                "recipes",
                recipe_name,
                "fk_missing",
                f"Missing component recipes: {', '.join(missing_components)}",
                "Import component recipes first or remove from components",
            )
            continue

        # Create the recipe
        # Default is_production_ready to True for imports (backward compatibility)
        recipe = Recipe(
            name=recipe_name,
            category=item.get("category"),
            source=item.get("source"),
            yield_quantity=item.get("yield_quantity"),
            yield_unit=item.get("yield_unit"),
            yield_description=item.get("yield_description"),
            estimated_time_minutes=item.get("estimated_time_minutes"),
            notes=item.get("notes"),
            is_production_ready=item.get("is_production_ready", True),
        )
        session.add(recipe)
        session.flush()  # Get the recipe ID for FK references

        # Create RecipeIngredients
        for ri in recipe_ingredients_data:
            ing_slug = ri.get("ingredient_slug", "")
            ingredient_id = slug_to_id.get(ing_slug)
            recipe_ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient_id,
                quantity=ri.get("quantity"),
                unit=ri.get("unit"),
                notes=ri.get("notes"),
            )
            session.add(recipe_ingredient)

        # Create RecipeComponents
        for idx, rc in enumerate(recipe_components_data):
            component_name = rc.get("recipe_name", "")
            # Resolve component recipe ID
            if component_name in existing_recipes:
                component_recipe_id = existing_recipes[component_name]["id"]
            else:
                component_recipe_id = new_recipe_ids.get(component_name)

            recipe_component = RecipeComponent(
                recipe_id=recipe.id,
                component_recipe_id=component_recipe_id,
                quantity=rc.get("quantity", 1.0),
                notes=rc.get("notes"),
                sort_order=idx,
            )
            session.add(recipe_component)

        result.add_success("recipes")

        # Track new recipe for component FK resolution
        new_recipe_ids[recipe_name] = recipe.id
        existing_recipes[recipe_name] = {
            "id": recipe.id,
            "yield_quantity": recipe.yield_quantity,
            "yield_unit": recipe.yield_unit,
        }

    # Handle dry-run: rollback instead of commit
    if dry_run:
        session.rollback()

    return result


def _detect_cycles(recipes_data: List[Dict]) -> Optional[List[str]]:
    """
    Detect circular recipe references.

    Args:
        recipes_data: List of recipe dictionaries to analyze

    Returns:
        List of recipe names forming a cycle, or None if no cycle
    """
    # Build directed graph of recipe -> component relationships
    graph = {}
    for r in recipes_data:
        name = r.get("name", "")
        components = [c.get("recipe_name", "") for c in r.get("components", [])]
        graph[name] = components

    visited = set()
    rec_stack = set()  # Current recursion stack
    path = []

    def dfs(node):
        if node in rec_stack:
            # Found a cycle, reconstruct path
            cycle_start = path.index(node)
            return path[cycle_start:] + [node]
        if node in visited:
            return None

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor in graph:  # Only follow edges to recipes in import
                cycle = dfs(neighbor)
                if cycle:
                    return cycle

        path.pop()
        rec_stack.remove(node)
        return None

    for recipe_name in graph:
        if recipe_name not in visited:
            cycle = dfs(recipe_name)
            if cycle:
                return cycle

    return None


def _validate_recipe_data(item: Dict) -> Optional[Dict]:
    """
    Validate recipe data before creation.

    Args:
        item: Recipe dictionary from catalog file

    Returns:
        None if valid, or dict with 'message' and 'suggestion' keys if invalid
    """
    # Check required fields
    if not item.get("name"):
        return {
            "message": "Missing required field: name",
            "suggestion": "Add 'name' field to recipe data (e.g., 'Chocolate Chip Cookies')",
        }

    if not item.get("category"):
        return {
            "message": "Missing required field: category",
            "suggestion": "Add 'category' field to recipe data (e.g., 'Cookies', 'Cakes')",
        }

    if item.get("yield_quantity") is None:
        return {
            "message": "Missing required field: yield_quantity",
            "suggestion": "Add 'yield_quantity' field (e.g., 24, 12)",
        }

    if not item.get("yield_unit"):
        return {
            "message": "Missing required field: yield_unit",
            "suggestion": "Add 'yield_unit' field (e.g., 'cookies', 'servings')",
        }

    # Validate ingredients have required fields
    for idx, ing in enumerate(item.get("ingredients", [])):
        if not ing.get("ingredient_slug"):
            return {
                "message": f"Ingredient {idx + 1}: Missing 'ingredient_slug'",
                "suggestion": "Each ingredient must have an 'ingredient_slug' field",
            }
        if ing.get("quantity") is None:
            return {
                "message": f"Ingredient {idx + 1}: Missing 'quantity'",
                "suggestion": "Each ingredient must have a 'quantity' field",
            }
        if not ing.get("unit"):
            return {
                "message": f"Ingredient {idx + 1}: Missing 'unit'",
                "suggestion": "Each ingredient must have a 'unit' field",
            }

    # Validate components have required fields
    for idx, comp in enumerate(item.get("components", [])):
        if not comp.get("recipe_name"):
            return {
                "message": f"Component {idx + 1}: Missing 'recipe_name'",
                "suggestion": "Each component must have a 'recipe_name' field",
            }

    return None


# ============================================================================
# Material Import Functions (Feature 047)
# ============================================================================


def import_material_categories(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult:
    """
    Import material categories from parsed data.

    Args:
        data: List of category dictionaries
        mode: "add" (ADD_ONLY) or "augment" (AUGMENT mode)
        dry_run: If True, validate and preview without committing
        session: Optional SQLAlchemy session

    Returns:
        CatalogImportResult with counts and any errors
    """
    if session is not None:
        return _import_material_categories_impl(data, mode, dry_run, session)
    with session_scope() as sess:
        return _import_material_categories_impl(data, mode, dry_run, sess)


def _import_material_categories_impl(
    data: List[Dict],
    mode: str,
    dry_run: bool,
    session: Session,
) -> CatalogImportResult:
    """Internal implementation of material category import."""
    result = CatalogImportResult()
    result.dry_run = dry_run
    result.mode = mode

    existing_slugs = {
        row.slug: row
        for row in session.query(MaterialCategory).all()
    }

    for item in data:
        slug = item.get("slug", "")
        name = item.get("name", "")
        identifier = slug or name or "unknown"

        if not name:
            result.add_error(
                "material_categories", identifier, "validation",
                "Missing required field: name",
                "Add 'name' field to category data",
            )
            continue

        if not slug:
            # Auto-generate slug from name
            slug = name.lower().replace(" ", "-").replace("_", "-")
            slug = "".join(c for c in slug if c.isalnum() or c == "-")

        if slug in existing_slugs:
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("material_categories", slug, "Already exists")
                continue
            # AUGMENT mode: update description only if null
            existing = existing_slugs[slug]
            updated_fields = []
            if item.get("description") and not existing.description:
                existing.description = item["description"]
                updated_fields.append("description")
            if updated_fields:
                result.add_augment("material_categories", slug, updated_fields)
            else:
                result.add_skip("material_categories", slug, "No null fields to update")
            continue

        category = MaterialCategory(
            name=name,
            slug=slug,
            description=item.get("description"),
            sort_order=item.get("sort_order", 0),
        )
        session.add(category)
        result.add_success("material_categories")
        existing_slugs[slug] = category

    if dry_run:
        session.rollback()

    return result


def import_material_subcategories(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult:
    """Import material subcategories from parsed data."""
    if session is not None:
        return _import_material_subcategories_impl(data, mode, dry_run, session)
    with session_scope() as sess:
        return _import_material_subcategories_impl(data, mode, dry_run, sess)


def _import_material_subcategories_impl(
    data: List[Dict],
    mode: str,
    dry_run: bool,
    session: Session,
) -> CatalogImportResult:
    """Internal implementation of material subcategory import."""
    result = CatalogImportResult()
    result.dry_run = dry_run
    result.mode = mode

    # Build category slug -> id lookup
    category_lookup = {
        row.slug: row.id
        for row in session.query(MaterialCategory).all()
    }

    existing_slugs = {
        row.slug: row
        for row in session.query(MaterialSubcategory).all()
    }

    for item in data:
        slug = item.get("slug", "")
        name = item.get("name", "")
        category_slug = item.get("category_slug", "")
        identifier = slug or name or "unknown"

        if not name:
            result.add_error(
                "material_subcategories", identifier, "validation",
                "Missing required field: name",
                "Add 'name' field to subcategory data",
            )
            continue

        if not category_slug:
            result.add_error(
                "material_subcategories", identifier, "validation",
                "Missing required field: category_slug",
                "Add 'category_slug' referencing an existing category",
            )
            continue

        category_id = category_lookup.get(category_slug)
        if category_id is None:
            result.add_error(
                "material_subcategories", identifier, "fk_missing",
                f"Category '{category_slug}' not found",
                "Import the category first or check the slug spelling",
            )
            continue

        if not slug:
            slug = name.lower().replace(" ", "-").replace("_", "-")
            slug = "".join(c for c in slug if c.isalnum() or c == "-")

        if slug in existing_slugs:
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("material_subcategories", slug, "Already exists")
                continue
            existing = existing_slugs[slug]
            updated_fields = []
            if item.get("description") and not existing.description:
                existing.description = item["description"]
                updated_fields.append("description")
            if updated_fields:
                result.add_augment("material_subcategories", slug, updated_fields)
            else:
                result.add_skip("material_subcategories", slug, "No null fields to update")
            continue

        subcategory = MaterialSubcategory(
            category_id=category_id,
            name=name,
            slug=slug,
            description=item.get("description"),
            sort_order=item.get("sort_order", 0),
        )
        session.add(subcategory)
        result.add_success("material_subcategories")
        existing_slugs[slug] = subcategory

    if dry_run:
        session.rollback()

    return result


def import_materials(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult:
    """Import materials from parsed data."""
    if session is not None:
        return _import_materials_impl(data, mode, dry_run, session)
    with session_scope() as sess:
        return _import_materials_impl(data, mode, dry_run, sess)


def _generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name."""
    slug = name.lower().replace(" ", "_").replace("-", "_")
    return "".join(c for c in slug if c.isalnum() or c == "_")


def _import_materials_impl(
    data: List[Dict],
    mode: str,
    dry_run: bool,
    session: Session,
) -> CatalogImportResult:
    """Internal implementation of material import."""
    result = CatalogImportResult()
    result.dry_run = dry_run
    result.mode = mode

    # Build category lookups
    categories = session.query(MaterialCategory).all()
    category_by_name = {row.name: row for row in categories}
    category_by_slug = {row.slug: row for row in categories}
    category_by_id = {row.id: row for row in categories}

    # Build subcategory lookups
    subcategories = session.query(MaterialSubcategory).all()
    # Key is (category_name, subcategory_name) -> subcategory object (for name-based creation)
    subcategory_lookup = {}
    for row in subcategories:
        if row.category:
            key = (row.category.name, row.name)
            subcategory_lookup[key] = row
    subcategory_by_slug = {row.slug: row for row in subcategories}
    subcategory_by_id = {row.id: row for row in subcategories}

    existing_slugs = {row.slug: row for row in session.query(Material).all()}

    valid_base_units = {"linear_inches", "square_inches", "each"}

    for item in data:
        slug = item.get("slug", "")
        # Accept both 'name' and 'display_name' (prefer name, fallback to display_name)
        name = item.get("name") or item.get("display_name", "")
        # Default base_unit_type to "each" if not provided
        base_unit_type = item.get("base_unit_type", "each")
        identifier = slug or name or "unknown"

        if not name:
            result.add_error(
                "materials", identifier, "validation",
                "Missing required field: name or display_name",
                "Add 'name' or 'display_name' field to material data",
            )
            continue

        # Resolve subcategory / category from slug/id or legacy "Category: Subcategory" string
        subcategory = None
        category = None

        subcategory_id = item.get("subcategory_id")
        if subcategory_id:
            subcategory = subcategory_by_id.get(subcategory_id)

        if subcategory is None:
            sub_slug = item.get("subcategory_slug")
            if sub_slug:
                subcategory = subcategory_by_slug.get(sub_slug)
                if subcategory:
                    subcategory_id = subcategory.id

        if subcategory is None:
            # Legacy path: category string "Category: Subcategory"
            category_str = item.get("category", "")
            if not category_str:
                result.add_error(
                    "materials",
                    identifier,
                    "validation",
                    "Missing required field: category or subcategory_slug",
                    "Provide 'subcategory_slug' or 'category' in format 'Category: Subcategory'",
                )
                continue

            if ": " not in category_str:
                result.add_error(
                    "materials",
                    identifier,
                    "validation",
                    f"Invalid category format: '{category_str}'",
                    "Use format 'Category: Subcategory' (e.g., 'Boxes: Window Boxes')",
                )
                continue

            category_name, subcategory_name = category_str.split(": ", 1)

            # Get or create category
            if category_name not in category_by_name:
                new_category = MaterialCategory(
                    name=category_name,
                    slug=_generate_slug(category_name),
                )
                session.add(new_category)
                session.flush()  # Get the ID
                category_by_name[category_name] = new_category
                category_by_slug[new_category.slug] = new_category
                category_by_id[new_category.id] = new_category

            category = category_by_name[category_name]

            # Get or create subcategory
            subcat_key = (category_name, subcategory_name)
            if subcat_key not in subcategory_lookup:
                new_subcategory = MaterialSubcategory(
                    category_id=category.id,
                    name=subcategory_name,
                    slug=_generate_slug(subcategory_name),
                )
                session.add(new_subcategory)
                session.flush()  # Get the ID
                subcategory_lookup[subcat_key] = new_subcategory
                subcategory_by_slug[new_subcategory.slug] = new_subcategory
                subcategory_by_id[new_subcategory.id] = new_subcategory

            subcategory = subcategory_lookup[subcat_key]
            subcategory_id = subcategory.id
        else:
            # If we resolved a subcategory, resolve its category as well
            category = subcategory.category or category_by_id.get(subcategory.category_id)

        # If category was provided separately by slug/id, prefer it when missing
        if category is None:
            cat_slug = item.get("category_slug")
            cat_id = item.get("category_id")
            if cat_slug and cat_slug in category_by_slug:
                category = category_by_slug[cat_slug]
            elif cat_id and cat_id in category_by_id:
                category = category_by_id[cat_id]

        if subcategory is None or category is None:
            result.add_error(
                "materials",
                identifier,
                "validation",
                "Could not resolve material category/subcategory",
                "Provide valid 'subcategory_slug' or 'category' in format 'Category: Subcategory'",
            )
            continue

        if base_unit_type not in valid_base_units:
            result.add_error(
                "materials", identifier, "validation",
                f"Invalid base_unit_type: {base_unit_type}",
                f"Use one of: {', '.join(valid_base_units)}",
            )
            continue

        if not slug:
            slug = name.lower().replace(" ", "-").replace("_", "-")
            slug = "".join(c for c in slug if c.isalnum() or c == "-")

        if slug in existing_slugs:
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("materials", slug, "Already exists")
                continue
            existing = existing_slugs[slug]
            updated_fields = []
            if item.get("description") and not existing.description:
                existing.description = item["description"]
                updated_fields.append("description")
            if updated_fields:
                result.add_augment("materials", slug, updated_fields)
            else:
                result.add_skip("materials", slug, "No null fields to update")
            continue

        material = Material(
            subcategory_id=subcategory_id,
            name=name,
            slug=slug,
            base_unit_type=base_unit_type,
            description=item.get("description"),
        )
        session.add(material)
        result.add_success("materials")
        existing_slugs[slug] = material

    if dry_run:
        session.rollback()

    return result


def import_material_products(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult:
    """Import material products from parsed data."""
    if session is not None:
        return _import_material_products_impl(data, mode, dry_run, session)
    with session_scope() as sess:
        return _import_material_products_impl(data, mode, dry_run, sess)


def _import_material_products_impl(
    data: List[Dict],
    mode: str,
    dry_run: bool,
    session: Session,
) -> CatalogImportResult:
    """Internal implementation of material product import."""
    result = CatalogImportResult()
    result.dry_run = dry_run
    result.mode = mode

    # Build material lookups (by slug and by name for flexible matching)
    all_materials = session.query(Material).all()
    material_by_slug = {row.slug: row.id for row in all_materials}
    material_by_name = {row.name: row.id for row in all_materials}

    supplier_lookup = {
        row.name.lower(): row.id
        for row in session.query(Supplier).all()
    }

    # Build existing product lookups by (material_id, name) and slug
    existing_products = {}
    existing_slugs = {}
    for row in session.query(MaterialProduct).all():
        key = (row.material_id, row.name)
        existing_products[key] = row
        if row.slug:
            existing_slugs[row.slug] = row

    for item in data:
        # Accept material_slug or material (by display name)
        material_slug = item.get("material_slug", "")
        material_name = item.get("material", "")
        # Accept both 'name' and 'display_name' (prefer name, fallback to display_name)
        name = item.get("name") or item.get("display_name", "")
        product_slug = item.get("slug", "")
        identifier = name or "unknown"

        if not name:
            result.add_error(
                "material_products", identifier, "validation",
                "Missing required field: name or display_name",
                "Add 'name' or 'display_name' field to product data",
            )
            continue

        # Resolve material from slug or name
        material_id = None
        if material_slug:
            material_id = material_by_slug.get(material_slug)
        if material_id is None and material_name:
            material_id = material_by_name.get(material_name)

        if material_id is None:
            mat_info = material_slug or material_name or "not specified"
            result.add_error(
                "material_products", identifier, "fk_missing",
                f"Material not found: '{mat_info}'",
                "Import the material first or check the name/slug",
            )
            continue

        # Resolve optional supplier (accept supplier, supplier_name, or supplier_slug)
        supplier_id = None
        supplier_value = (
            item.get("supplier_slug")
            or item.get("supplier_name")
            or item.get("supplier", "")
        )
        if supplier_value:
            supplier_id = supplier_lookup.get(supplier_value.lower())

        # Check for existing product by slug first, then by (material_id, name)
        existing = None
        if product_slug and product_slug in existing_slugs:
            existing = existing_slugs[product_slug]
        else:
            product_key = (material_id, name)
            if product_key in existing_products:
                existing = existing_products[product_key]

        if existing:
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("material_products", identifier, "Already exists")
                continue
            updated_fields = []
            if item.get("brand") and not existing.brand:
                existing.brand = item["brand"]
                updated_fields.append("brand")
            if supplier_id and not existing.supplier_id:
                existing.supplier_id = supplier_id
                updated_fields.append("supplier_id")
            # Backfill slug if missing
            if product_slug and not existing.slug:
                existing.slug = product_slug
                updated_fields.append("slug")
            if updated_fields:
                result.add_augment("material_products", identifier, updated_fields)
            else:
                result.add_skip("material_products", identifier, "No null fields to update")
            continue

        # Required fields for new product
        # Accept default_unit as fallback for package_unit, default package_quantity to 1
        package_quantity = item.get("package_quantity", 1)
        package_unit = item.get("package_unit") or item.get("default_unit", "")
        quantity_in_base_units = item.get("quantity_in_base_units", package_quantity)
        if not package_unit:
            result.add_error(
                "material_products", identifier, "validation",
                "Missing package_unit or default_unit",
                "Add 'package_unit' or 'default_unit' field (e.g., 'each', 'linear_inches')",
            )
            continue

        # Generate slug if not provided
        final_slug = product_slug or slugify(name)
        # Ensure uniqueness
        if final_slug in existing_slugs:
            counter = 1
            while f"{final_slug}_{counter}" in existing_slugs:
                counter += 1
            final_slug = f"{final_slug}_{counter}"

        product = MaterialProduct(
            material_id=material_id,
            name=name,
            slug=final_slug,
            brand=item.get("brand"),
            package_quantity=package_quantity,
            package_unit=package_unit,
            quantity_in_base_units=quantity_in_base_units,
            supplier_id=supplier_id,
            sku=item.get("sku"),
            notes=item.get("notes"),
        )
        session.add(product)
        result.add_success("material_products")
        existing_products[(material_id, name)] = product
        existing_slugs[final_slug] = product

    if dry_run:
        session.rollback()

    return result


def import_material_units(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult:
    """Import material units from parsed data."""
    if session is not None:
        return _import_material_units_impl(data, mode, dry_run, session)
    with session_scope() as sess:
        return _import_material_units_impl(data, mode, dry_run, sess)


def _import_material_units_impl(
    data: List[Dict],
    mode: str,
    dry_run: bool,
    session: Session,
) -> CatalogImportResult:
    """Internal implementation of material unit import."""
    result = CatalogImportResult()
    result.dry_run = dry_run
    result.mode = mode

    material_lookup = {
        row.slug: row.id
        for row in session.query(Material).all()
    }

    existing_slugs = {
        row.slug: row
        for row in session.query(MaterialUnit).all()
    }

    for item in data:
        slug = item.get("slug", "")
        name = item.get("name", "")
        material_slug = item.get("material_slug", "")
        identifier = slug or name or "unknown"

        if not name:
            result.add_error(
                "material_units", identifier, "validation",
                "Missing required field: name",
                "Add 'name' field to unit data",
            )
            continue

        if not material_slug:
            result.add_error(
                "material_units", identifier, "validation",
                "Missing required field: material_slug",
                "Add 'material_slug' referencing an existing material",
            )
            continue

        quantity_per_unit = item.get("quantity_per_unit")
        if quantity_per_unit is None or quantity_per_unit <= 0:
            result.add_error(
                "material_units", identifier, "validation",
                "Invalid quantity_per_unit: must be > 0",
                "Add 'quantity_per_unit' field with positive value",
            )
            continue

        material_id = material_lookup.get(material_slug)
        if material_id is None:
            result.add_error(
                "material_units", identifier, "fk_missing",
                f"Material '{material_slug}' not found",
                "Import the material first or check the slug spelling",
            )
            continue

        if not slug:
            slug = name.lower().replace(" ", "-").replace("_", "-")
            slug = "".join(c for c in slug if c.isalnum() or c == "-")

        if slug in existing_slugs:
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("material_units", slug, "Already exists")
                continue
            existing = existing_slugs[slug]
            updated_fields = []
            if item.get("description") and not existing.description:
                existing.description = item["description"]
                updated_fields.append("description")
            if updated_fields:
                result.add_augment("material_units", slug, updated_fields)
            else:
                result.add_skip("material_units", slug, "No null fields to update")
            continue

        unit = MaterialUnit(
            material_id=material_id,
            name=name,
            slug=slug,
            quantity_per_unit=quantity_per_unit,
            description=item.get("description"),
        )
        session.add(unit)
        result.add_success("material_units")
        existing_slugs[slug] = unit

    if dry_run:
        session.rollback()

    return result


# ============================================================================
# File Validation and Coordinator Functions
# ============================================================================


def validate_catalog_file(file_path: str) -> Dict:
    """
    Load and validate a catalog file.

    Detects file format and ensures it's valid JSON for catalog import.

    Args:
        file_path: Path to the JSON catalog file

    Returns:
        Parsed catalog data dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        CatalogImportError: If JSON is invalid

    Note:
        The 'version' field is optional and informational only. Import validation
        relies on required field presence, FK resolution, and SQLAlchemy model
        validation. This allows imports to work across minor format changes.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise CatalogImportError(f"Invalid JSON: {e}")

    # Version field is informational only - no validation
    # Actual compatibility is determined by field presence and FK resolution

    return data


def import_catalog(
    file_path: str,
    mode: str = "add",
    entities: Optional[List[str]] = None,
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> CatalogImportResult:
    """
    Import catalog from file.

    Main entry point for catalog import. Validates file format, then
    imports entities in dependency order (ingredients -> products -> recipes).

    Args:
        file_path: Path to the JSON catalog file
        mode: "add" (ADD_ONLY) or "augment" (AUGMENT mode)
        entities: Optional list of entity types to import (default: all)
        dry_run: If True, validate and preview without committing
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        CatalogImportResult with combined counts from all entity types

    Raises:
        FileNotFoundError: If file doesn't exist
        CatalogImportError: If format invalid or entity list invalid
    """
    # Validate entity list if provided
    if entities:
        invalid = set(entities) - VALID_ENTITIES
        if invalid:
            raise CatalogImportError(f"Invalid entity types: {invalid}")

    # Load and validate file format
    data = validate_catalog_file(file_path)

    if session is not None:
        return _import_catalog_impl(data, mode, entities, dry_run, session)
    with session_scope() as sess:
        result = _import_catalog_impl(data, mode, entities, dry_run, sess)
        if dry_run:
            sess.rollback()
        return result


def _import_catalog_impl(
    data: Dict,
    mode: str,
    entities: Optional[List[str]],
    dry_run: bool,
    session: Session,
) -> CatalogImportResult:
    """
    Internal implementation of catalog import.

    Processes entities in dependency order to ensure FK references exist.
    """
    result = CatalogImportResult()
    result.dry_run = dry_run
    result.mode = mode

    # Dependency order: suppliers -> ingredients -> products -> recipes
    # This ensures FK references exist when needed
    # (Products may reference suppliers via supplier_slug FK)

    # Feature 051: Import suppliers first (products reference suppliers)
    if entities is None or "suppliers" in entities:
        if "suppliers" in data:
            sup_result = import_suppliers(
                data["suppliers"], mode, dry_run=False, session=session
            )
            result.merge(sup_result)
            # Flush to make new suppliers visible to products import queries
            session.flush()

    # Import ingredients
    if entities is None or "ingredients" in entities:
        if "ingredients" in data:
            ing_result = import_ingredients(
                data["ingredients"], mode, dry_run=False, session=session
            )
            result.merge(ing_result)
            # Flush to make new ingredients visible to products/recipes import queries
            session.flush()

    # Import products (depends on ingredients and suppliers)
    if entities is None or "products" in entities:
        if "products" in data:
            # Build supplier ID -> slug mapping from import file for FK resolution
            # This handles the case where preferred_supplier_id references an ID
            # from the same import file (which may have a different ID in the database)
            supplier_id_to_slug = {}
            if "suppliers" in data:
                for sup in data["suppliers"]:
                    if sup.get("id") and sup.get("slug"):
                        supplier_id_to_slug[sup["id"]] = sup["slug"]

            prod_result = import_products(
                data["products"], mode, dry_run=False, session=session,
                supplier_id_to_slug=supplier_id_to_slug,
            )
            result.merge(prod_result)

    # Import recipes (depends on ingredients)
    if entities is None or "recipes" in entities:
        if "recipes" in data:
            recipe_result = import_recipes(
                data["recipes"], mode, dry_run=False, session=session
            )
            result.merge(recipe_result)

    # =========================================================================
    # Feature 047: Materials Management System
    # Import order: categories -> subcategories -> materials -> products -> units
    # =========================================================================

    # Import material categories
    if entities is None or "material_categories" in entities:
        if "material_categories" in data:
            cat_result = import_material_categories(
                data["material_categories"], mode, dry_run=False, session=session
            )
            result.merge(cat_result)
            # Flush to make new categories visible to subcategory import queries
            session.flush()

    # Import material subcategories (depends on categories)
    if entities is None or "material_subcategories" in entities:
        if "material_subcategories" in data:
            subcat_result = import_material_subcategories(
                data["material_subcategories"], mode, dry_run=False, session=session
            )
            result.merge(subcat_result)
            # Flush to make new subcategories visible to materials import queries
            session.flush()

    # Import materials (depends on subcategories)
    if entities is None or "materials" in entities:
        if "materials" in data:
            mat_result = import_materials(
                data["materials"], mode, dry_run=False, session=session
            )
            result.merge(mat_result)
            # Flush to make new materials visible to products/units import queries
            session.flush()

    # Import material products (depends on materials, suppliers)
    if entities is None or "material_products" in entities:
        if "material_products" in data:
            prod_result = import_material_products(
                data["material_products"], mode, dry_run=False, session=session
            )
            result.merge(prod_result)

    # Import material units (depends on materials)
    if entities is None or "material_units" in entities:
        if "material_units" in data:
            unit_result = import_material_units(
                data["material_units"], mode, dry_run=False, session=session
            )
            result.merge(unit_result)

    return result
