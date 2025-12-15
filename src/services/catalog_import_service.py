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
VALID_ENTITIES = {"ingredients", "products", "recipes"}


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
    "is_packaging",
}

# Product fields: Protected = never modified; Augmentable = updated only if current value is NULL
PRODUCT_PROTECTED_FIELDS = {"ingredient_id", "brand", "id", "date_added"}
PRODUCT_AUGMENTABLE_FIELDS = {
    "upc_code",
    "package_size",
    "package_type",
    "purchase_unit",
    "purchase_quantity",
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

        # Track for duplicate detection within same import
        existing_slugs.add(slug)
        existing_ingredients[slug] = ingredient

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

    # Build existing products lookup for uniqueness check and AUGMENT mode
    # Unique key is (ingredient_id, brand) where brand can be None
    existing_products_set = set()
    existing_products_map = {}  # (ingredient_id, brand) -> Product
    for row in session.query(Product).all():
        key = (row.ingredient_id, row.brand)
        existing_products_set.add(key)
        existing_products_map[key] = row

    for item in data:
        # Extract fields for identification and validation
        ingredient_slug = item.get("ingredient_slug", "")
        brand = item.get("brand")  # Can be None
        identifier = f"{brand or 'Generic'} ({ingredient_slug})"

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
            # For AUGMENT mode, only ingredient_slug is required
            if not ingredient_slug:
                result.add_error(
                    "products",
                    identifier,
                    "validation",
                    "Missing required field: ingredient_slug",
                    "Add 'ingredient_slug' field referencing an existing ingredient",
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
        product_key = (ingredient_id, brand)
        if product_key in existing_products_set:
            if mode == ImportMode.ADD_ONLY.value:
                result.add_skip("products", identifier, "Already exists")
                continue
            # AUGMENT mode: update only null fields
            existing_product = existing_products_map[product_key]
            updated_fields = []
            for field in PRODUCT_AUGMENTABLE_FIELDS:
                if field in item and item[field] is not None:
                    current_value = getattr(existing_product, field, None)
                    if current_value is None:
                        setattr(existing_product, field, item[field])
                        updated_fields.append(field)
            if updated_fields:
                result.add_augment("products", identifier, updated_fields)
            else:
                result.add_skip("products", identifier, "No null fields to update")
            continue

        # For new products in AUGMENT mode, also require purchase_unit/quantity
        if mode == ImportMode.AUGMENT.value:
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
        existing_products_set.add(product_key)
        existing_products_map[product_key] = product

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
        recipe = Recipe(
            name=recipe_name,
            category=item.get("category"),
            source=item.get("source"),
            yield_quantity=item.get("yield_quantity"),
            yield_unit=item.get("yield_unit"),
            yield_description=item.get("yield_description"),
            estimated_time_minutes=item.get("estimated_time_minutes"),
            notes=item.get("notes"),
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
# File Validation and Coordinator Functions
# ============================================================================


def validate_catalog_file(file_path: str) -> Dict:
    """
    Load and validate a catalog file.

    Detects file format and ensures it's the catalog format (not unified import).

    Args:
        file_path: Path to the JSON catalog file

    Returns:
        Parsed catalog data dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        CatalogImportError: If format invalid or wrong type
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise CatalogImportError(f"Invalid JSON: {e}")

    # Format detection
    if "catalog_version" in data:
        if data["catalog_version"] != "1.0":
            raise CatalogImportError(
                f"Unsupported catalog version: {data['catalog_version']}. Expected 1.0"
            )
        return data
    elif "version" in data:
        # This is a unified import file, not a catalog file
        raise CatalogImportError(
            "This appears to be a unified import file (v3.x format). "
            "Use 'Import Data...' instead of 'Import Catalog...'"
        )
    else:
        raise CatalogImportError(
            "Unrecognized file format. Expected 'catalog_version' field."
        )


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

    # Dependency order: ingredients first, then products, then recipes
    # This ensures FK references exist when needed

    # Import ingredients
    if entities is None or "ingredients" in entities:
        if "ingredients" in data:
            ing_result = import_ingredients(
                data["ingredients"], mode, dry_run=False, session=session
            )
            result.merge(ing_result)

    # Import products (depends on ingredients)
    if entities is None or "products" in entities:
        if "products" in data:
            prod_result = import_products(
                data["products"], mode, dry_run=False, session=session
            )
            result.merge(prod_result)

    # Import recipes (depends on ingredients)
    if entities is None or "recipes" in entities:
        if "recipes" in data:
            recipe_result = import_recipes(
                data["recipes"], mode, dry_run=False, session=session
            )
            result.merge(recipe_result)

    return result
