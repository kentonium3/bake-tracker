"""Enhanced import service for denormalized views with FK resolution.

This module provides import functionality for denormalized view exports,
with support for FK resolution, merge/skip modes, dry-run, and skip-on-error.

Key Features:
- FK resolution via slug/name (not ID)
- Merge mode: update existing + add new
- Skip_existing mode: add new only
- Dry_run mode: preview changes without DB modification
- Skip-on-error mode: import valid records, log failures
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from sqlalchemy.orm import Session

from src.models.ingredient import Ingredient
from src.models.inventory_item import InventoryItem
from src.models.material import Material
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.recipe import Recipe
from src.models.supplier import Supplier
from src.services.fk_resolver_service import (
    FKResolverCallback,
    MissingFK,
    Resolution,
    ResolutionChoice,
    collect_missing_fks,
    resolve_missing_fks,
)
from src.services.import_export_service import ImportResult
from src.services.database import session_scope


# ============================================================================
# Result Classes
# ============================================================================


@dataclass
class EnhancedImportResult:
    """Extended import result with FK resolution tracking.

    Extends ImportResult functionality with:
    - Resolution tracking (created, mapped, skipped entities)
    - Dry-run indicator
    - Skipped records log path
    """

    # Delegate to ImportResult for base counts
    base_result: ImportResult = field(default_factory=ImportResult)

    # Resolution tracking
    resolutions: List[Resolution] = field(default_factory=list)
    created_entities: Dict[str, int] = field(
        default_factory=dict
    )  # {entity_type: count}
    mapped_entities: Dict[str, int] = field(default_factory=dict)
    skipped_due_to_fk: int = 0

    # Mode indicators
    dry_run: bool = False
    skipped_records_path: Optional[str] = None

    # Convenience properties delegating to base_result
    @property
    def total_records(self) -> int:
        return self.base_result.total_records

    @property
    def successful(self) -> int:
        return self.base_result.successful

    @property
    def skipped(self) -> int:
        return self.base_result.skipped

    @property
    def failed(self) -> int:
        return self.base_result.failed

    @property
    def errors(self) -> List[Dict]:
        return self.base_result.errors

    @property
    def warnings(self) -> List[Dict]:
        return self.base_result.warnings

    @property
    def entity_counts(self) -> Dict[str, Dict[str, int]]:
        return self.base_result.entity_counts

    def add_success(self, entity_type: str = None):
        """Record a successful import."""
        self.base_result.add_success(entity_type)

    def add_skip(
        self,
        record_type: str,
        record_name: str,
        reason: str,
        suggestion: str = None,
    ):
        """Record a skipped record."""
        self.base_result.add_skip(record_type, record_name, reason, suggestion)

    def add_error(
        self,
        record_type: str,
        record_name: str,
        error: str,
        suggestion: str = None,
    ):
        """Record a failed import."""
        self.base_result.add_error(record_type, record_name, error, suggestion)

    def add_warning(
        self,
        record_type: str,
        record_name: str,
        message: str,
        suggestion: str = None,
    ):
        """Record a warning."""
        self.base_result.add_warning(record_type, record_name, message, suggestion)

    def add_created_entity(self, entity_type: str):
        """Track a created entity during FK resolution."""
        self.created_entities[entity_type] = (
            self.created_entities.get(entity_type, 0) + 1
        )

    def add_mapped_entity(self, entity_type: str):
        """Track a mapped entity during FK resolution."""
        self.mapped_entities[entity_type] = self.mapped_entities.get(entity_type, 0) + 1

    def get_summary(self) -> str:
        """Get a user-friendly summary including FK resolution info."""
        lines = []

        # Add dry-run notice if applicable
        if self.dry_run:
            lines.extend(
                [
                    "=" * 60,
                    "DRY RUN - No changes were made to the database",
                    "=" * 60,
                    "",
                ]
            )

        # Get base summary
        base_summary = self.base_result.get_summary()
        lines.append(base_summary)

        # Add FK resolution summary if any resolutions were made
        if self.resolutions:
            lines.append("")
            lines.append("FK Resolutions:")
            total_created = sum(self.created_entities.values())
            total_mapped = sum(self.mapped_entities.values())
            lines.append(f"  Created: {total_created}")
            if self.created_entities:
                for entity_type, count in sorted(self.created_entities.items()):
                    lines.append(f"    - {entity_type}: {count}")
            lines.append(f"  Mapped: {total_mapped}")
            if self.mapped_entities:
                for entity_type, count in sorted(self.mapped_entities.items()):
                    lines.append(f"    - {entity_type}: {count}")
            lines.append(f"  Skipped (FK): {self.skipped_due_to_fk}")

        # Add skipped records log path if applicable
        if self.skipped_records_path:
            lines.append("")
            lines.append(f"Skipped records log: {self.skipped_records_path}")

        return "\n".join(lines)


# ============================================================================
# Format Detection Types
# ============================================================================

FormatType = Literal["context_rich", "normalized", "purchases", "adjustments", "unknown"]


@dataclass
class FormatDetectionResult:
    """Result of format auto-detection for UI confirmation.

    Attributes:
        format_type: Detected format type
        view_type: For context-rich formats, the entity type (e.g., "ingredients")
        entity_count: Number of records in the file
        editable_fields: List of editable fields (for context-rich)
        readonly_fields: List of readonly fields (for context-rich)
        version: Schema version (for normalized)
        import_type: Import type (for purchases/adjustments)
        source: Source system if specified
        raw_data: The parsed JSON data for subsequent import
    """

    format_type: FormatType
    view_type: Optional[str] = None
    entity_count: int = 0
    editable_fields: Optional[List[str]] = None
    readonly_fields: Optional[List[str]] = None
    version: Optional[str] = None
    import_type: Optional[str] = None
    source: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

    @property
    def display_name(self) -> str:
        """Human-readable format name for UI display."""
        if self.format_type == "context_rich":
            view_name = (self.view_type or "unknown").replace("_", " ").title()
            return f"Context-Rich View ({view_name})"
        elif self.format_type == "normalized":
            return f"Normalized Backup (v{self.version or 'unknown'})"
        elif self.format_type == "purchases":
            return "Purchase Transactions"
        elif self.format_type == "adjustments":
            return "Inventory Adjustments"
        else:
            return "Unknown Format"

    @property
    def summary(self) -> str:
        """Get a summary string for display."""
        lines = [f"Format: {self.display_name}"]
        lines.append(f"Records: {self.entity_count}")

        if self.editable_fields:
            lines.append(f"Editable fields: {', '.join(self.editable_fields)}")
        if self.readonly_fields:
            lines.append(f"Readonly fields: {', '.join(self.readonly_fields)}")
        if self.source:
            lines.append(f"Source: {self.source}")

        return "\n".join(lines)


# ============================================================================
# Format Detection Functions
# ============================================================================


def detect_format(file_path: str) -> FormatDetectionResult:
    """Detect the format of an import file.

    Args:
        file_path: Path to JSON file to analyze

    Returns:
        FormatDetectionResult with detected format and metadata

    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return _detect_format_from_data(data)


def _detect_format_from_data(data: Dict[str, Any]) -> FormatDetectionResult:
    """Detect format from parsed JSON data.

    Detection rules (in order of priority):
    1. Context-Rich: Has _meta.editable_fields
    2. Purchases: import_type == "purchases"
    3. Adjustments: import_type in ("adjustments", "inventory_updates")
    4. Normalized: Has version and application == "bake-tracker"
    5. Unknown: None of the above

    Args:
        data: Parsed JSON data

    Returns:
        FormatDetectionResult with detected format
    """
    result = FormatDetectionResult(format_type="unknown", raw_data=data)

    # Check for context-rich view format (has _meta.editable_fields)
    meta = data.get("_meta", {})
    if isinstance(meta, dict) and "editable_fields" in meta:
        result.format_type = "context_rich"
        result.view_type = data.get("view_type")
        result.editable_fields = meta.get("editable_fields", [])
        result.readonly_fields = meta.get("readonly_fields", [])
        result.entity_count = len(data.get("records", []))
        return result

    # Check for transaction imports (purchases, adjustments)
    import_type = data.get("import_type")
    if import_type == "purchases":
        result.format_type = "purchases"
        result.import_type = import_type
        result.version = data.get("schema_version")
        result.source = data.get("source")
        result.entity_count = len(data.get("purchases", []))
        return result

    if import_type in ("adjustments", "inventory_updates"):
        result.format_type = "adjustments"
        result.import_type = import_type
        result.version = data.get("schema_version")
        result.source = data.get("source")
        # Check both possible array names
        adjustments = data.get("adjustments", []) or data.get("inventory_updates", [])
        result.entity_count = len(adjustments)
        return result

    # Check for normalized backup/catalog format
    if "version" in data and data.get("application") == "bake-tracker":
        result.format_type = "normalized"
        result.version = data.get("version")
        result.source = data.get("application")
        # Count total records across all entity arrays
        entity_count = 0
        for key, value in data.items():
            if isinstance(value, list) and key not in ("_meta", "files"):
                entity_count += len(value)
        result.entity_count = entity_count
        return result

    # Unknown format - try to provide some info
    result.format_type = "unknown"
    # Try to count records if there's any array
    for key, value in data.items():
        if isinstance(value, list):
            result.entity_count = len(value)
            result.view_type = key  # Best guess at what the data represents
            break

    return result


def extract_editable_fields(record: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only editable fields from a context-rich record.

    This filters out computed and readonly fields, returning only the
    fields that should be imported/merged with existing records.

    Args:
        record: Full record with all fields
        meta: _meta section containing editable_fields list

    Returns:
        Dict containing only editable fields from the record
    """
    editable_fields = set(meta.get("editable_fields", []))
    return {k: v for k, v in record.items() if k in editable_fields}


def merge_fields(entity: Any, editable_data: Dict[str, Any]) -> bool:
    """Update entity with editable field values.

    Only updates fields that are present in editable_data.
    Does not clear fields not present in the update.

    Args:
        entity: The SQLAlchemy entity to update
        editable_data: Dict of field names to new values

    Returns:
        True if any fields were updated, False otherwise
    """
    updated = False
    for field_name, value in editable_data.items():
        if hasattr(entity, field_name):
            current_value = getattr(entity, field_name, None)
            if current_value != value:
                setattr(entity, field_name, value)
                updated = True
    return updated


def _find_entity_by_slug(
    view_type: str, slug: str, session: Session
) -> Optional[Any]:
    """Find an entity by its slug for context-rich import.

    Args:
        view_type: The view type (e.g., "ingredients", "materials", "recipes")
        slug: The entity's slug identifier
        session: Database session

    Returns:
        The entity if found, None otherwise
    """
    entity_type = _view_type_to_entity_type(view_type)

    if entity_type == "ingredient":
        return session.query(Ingredient).filter(Ingredient.slug == slug).first()
    elif entity_type == "material":
        return session.query(Material).filter(Material.slug == slug).first()
    elif entity_type == "recipe":
        return session.query(Recipe).filter(Recipe.slug == slug).first()
    elif entity_type == "product":
        return session.query(Product).filter(Product.slug == slug).first()
    elif entity_type == "supplier":
        return session.query(Supplier).filter(Supplier.name == slug).first()

    return None


# ============================================================================
# Context-Rich Import
# ============================================================================


@dataclass
class ContextRichImportResult:
    """Result of context-rich import operation.

    Tracks which records were merged, skipped, or had errors.
    """

    total_records: int = 0
    merged: int = 0
    skipped: int = 0
    not_found: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    dry_run: bool = False

    def add_merged(self):
        """Record a successful merge."""
        self.merged += 1

    def add_skipped(self, slug: str, reason: str):
        """Record a skipped record."""
        self.skipped += 1
        self.errors.append({"slug": slug, "reason": reason, "type": "skip"})

    def add_not_found(self, slug: str):
        """Record a record that wasn't found in the database."""
        self.not_found += 1
        self.errors.append({"slug": slug, "reason": "Record not found for merge", "type": "not_found"})

    def add_error(self, slug: str, error: str):
        """Record an error."""
        self.errors.append({"slug": slug, "reason": error, "type": "error"})

    def get_summary(self) -> str:
        """Get a summary of the import operation."""
        lines = []
        if self.dry_run:
            lines.append("=" * 50)
            lines.append("DRY RUN - No changes were made")
            lines.append("=" * 50)
            lines.append("")

        lines.append(f"Total records: {self.total_records}")
        lines.append(f"Merged: {self.merged}")
        lines.append(f"Skipped (no changes): {self.skipped}")
        lines.append(f"Not found: {self.not_found}")

        if self.errors:
            lines.append("")
            lines.append("Issues:")
            for err in self.errors[:10]:  # Show first 10
                lines.append(f"  - [{err['type']}] {err['slug']}: {err['reason']}")
            if len(self.errors) > 10:
                lines.append(f"  ... and {len(self.errors) - 10} more")

        return "\n".join(lines)


def import_context_rich_view(
    file_path: str,
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> ContextRichImportResult:
    """Import a context-rich view file, merging editable fields with existing records.

    Context-rich imports are merge-only operations - they update existing
    records with AI-augmented editable fields. Records not found in the
    database are skipped (not created).

    Args:
        file_path: Path to the context-rich JSON file
        dry_run: If True, preview changes without modifying database
        session: Optional database session

    Returns:
        ContextRichImportResult with import statistics
    """
    if session is not None:
        return _import_context_rich_impl(file_path, dry_run, session)

    with session_scope() as session:
        result = _import_context_rich_impl(file_path, dry_run, session)
        if dry_run:
            session.rollback()
        return result


def _import_context_rich_impl(
    file_path: str,
    dry_run: bool,
    session: Session,
) -> ContextRichImportResult:
    """Implementation of context-rich import.

    Args:
        file_path: Path to the JSON file
        dry_run: Preview mode flag
        session: Database session

    Returns:
        ContextRichImportResult
    """
    result = ContextRichImportResult(dry_run=dry_run)

    # First detect the format to ensure it's context-rich
    detection = detect_format(file_path)
    if detection.format_type != "context_rich":
        result.add_error("file", f"Expected context-rich format, got {detection.format_type}")
        return result

    data = detection.raw_data
    meta = data.get("_meta", {})
    view_type = data.get("view_type")
    records = data.get("records", [])

    result.total_records = len(records)

    if not view_type:
        result.add_error("file", "Missing view_type in context-rich file")
        return result

    # Process each record
    for record in records:
        # Get the slug identifier (always in readonly fields but needed for lookup)
        slug = record.get("slug")
        if not slug:
            result.add_error("unknown", "Record missing slug identifier")
            continue

        # Find existing entity
        existing = _find_entity_by_slug(view_type, slug, session)
        if not existing:
            result.add_not_found(slug)
            continue

        # Extract only editable fields
        editable_data = extract_editable_fields(record, meta)

        if not editable_data:
            result.add_skipped(slug, "No editable fields to update")
            continue

        # Merge editable fields
        updated = merge_fields(existing, editable_data)

        if updated:
            result.add_merged()
        else:
            result.add_skipped(slug, "No changes needed")

    return result


# ============================================================================
# FK Resolution Helpers
# ============================================================================


def _resolve_fk_by_slug(
    entity_type: str, slug_value: str, session: Session
) -> Optional[int]:
    """Resolve a foreign key reference by slug/name.

    Args:
        entity_type: Type of entity ("ingredient", "supplier", "product")
        slug_value: The slug or name to look up
        session: Database session

    Returns:
        The entity ID if found, None otherwise
    """
    if not slug_value:
        return None

    if entity_type == "ingredient":
        ing = session.query(Ingredient).filter(Ingredient.slug == slug_value).first()
        return ing.id if ing else None

    elif entity_type == "supplier":
        sup = session.query(Supplier).filter(Supplier.name == slug_value).first()
        return sup.id if sup else None

    elif entity_type == "product":
        # Product lookup by product_slug (format: ingredient_slug:brand:qty:unit)
        # Parse the slug and look up by composite key
        parts = slug_value.split(":")
        if len(parts) >= 4:
            ingredient_slug = parts[0]
            brand = parts[1]
            try:
                package_unit_quantity = float(parts[2])
            except (ValueError, TypeError):
                return None
            package_unit = parts[3]

            # First resolve ingredient
            ingredient = session.query(Ingredient).filter(
                Ingredient.slug == ingredient_slug
            ).first()
            if not ingredient:
                return None

            # Then find product by composite key
            prod = session.query(Product).filter(
                Product.ingredient_id == ingredient.id,
                Product.brand == brand,
                Product.package_unit == package_unit,
                Product.package_unit_quantity == package_unit_quantity,
            ).first()
            return prod.id if prod else None
        return None

    return None


def _find_existing_by_slug(
    record: Dict[str, Any], entity_type: str, session: Session
) -> Optional[Any]:
    """Find an existing entity by its unique identifier (slug/name/uuid).

    Args:
        record: The record containing identifier fields
        entity_type: Type of entity to find
        session: Database session

    Returns:
        The existing entity if found, None otherwise
    """
    if entity_type == "ingredient":
        slug = record.get("ingredient_slug") or record.get("slug")
        if slug:
            return session.query(Ingredient).filter(Ingredient.slug == slug).first()

    elif entity_type == "supplier":
        name = record.get("supplier_name") or record.get("name")
        if name:
            return session.query(Supplier).filter(Supplier.name == name).first()

    elif entity_type == "product":
        # Product uses composite key
        ingredient_slug = record.get("ingredient_slug")
        brand = record.get("brand")
        package_unit = record.get("package_unit")
        package_unit_quantity = record.get("package_unit_quantity")

        if ingredient_slug and brand and package_unit and package_unit_quantity:
            # First resolve ingredient
            ingredient = (
                session.query(Ingredient)
                .filter(Ingredient.slug == ingredient_slug)
                .first()
            )
            if ingredient:
                return (
                    session.query(Product)
                    .filter(
                        Product.ingredient_id == ingredient.id,
                        Product.brand == brand,
                        Product.package_unit == package_unit,
                        Product.package_unit_quantity == package_unit_quantity,
                    )
                    .first()
                )

    elif entity_type == "inventory_item":
        # Inventory items are identified by UUID
        uuid_val = record.get("uuid")
        if uuid_val:
            return session.query(InventoryItem).filter(InventoryItem.uuid == uuid_val).first()

    elif entity_type == "purchase":
        # Purchases are identified by UUID
        uuid_val = record.get("uuid")
        if uuid_val:
            return session.query(Purchase).filter(Purchase.uuid == uuid_val).first()

    return None


# ============================================================================
# Import Mode Handlers
# ============================================================================


def _import_record_merge(
    record: Dict[str, Any],
    entity_type: str,
    editable_fields: List[str],
    fk_mapping: Dict[str, Dict[str, int]],
    session: Session,
) -> Tuple[str, Optional[str]]:
    """Import a record in merge mode (update existing, add new).

    Args:
        record: The record to import
        entity_type: Type of entity
        editable_fields: List of fields that can be updated
        fk_mapping: FK resolution mapping {entity_type: {missing_value: resolved_id}}
        session: Database session

    Returns:
        Tuple of (status, error_message)
        status is one of: "added", "updated", "skipped", "failed"
    """
    existing = _find_existing_by_slug(record, entity_type, session)

    if existing:
        # Build list of fields to update
        # IMPORTANT: Honor _meta.editable_fields strictly (FR-014)
        # Never update readonly/computed fields like unit_cost, unit_price, quantity_purchased
        fields_to_update = list(editable_fields)

        # Update fields
        updated = False
        for field_name in fields_to_update:
            if field_name in record and record[field_name] is not None:
                current_value = getattr(existing, field_name, None)
                new_value = record[field_name]
                if current_value != new_value:
                    setattr(existing, field_name, new_value)
                    updated = True
        return ("updated" if updated else "skipped", None)
    else:
        # Create new record
        return _create_new_record(record, entity_type, fk_mapping, session)


def _import_record_skip_existing(
    record: Dict[str, Any],
    entity_type: str,
    fk_mapping: Dict[str, Dict[str, int]],
    session: Session,
) -> Tuple[str, Optional[str]]:
    """Import a record in skip_existing mode (add new only).

    Args:
        record: The record to import
        entity_type: Type of entity
        fk_mapping: FK resolution mapping
        session: Database session

    Returns:
        Tuple of (status, error_message)
        status is one of: "added", "skipped", "failed"
    """
    existing = _find_existing_by_slug(record, entity_type, session)

    if existing:
        return ("skipped", None)
    else:
        return _create_new_record(record, entity_type, fk_mapping, session)


def _create_new_record(
    record: Dict[str, Any],
    entity_type: str,
    fk_mapping: Dict[str, Dict[str, int]],
    session: Session,
) -> Tuple[str, Optional[str]]:
    """Create a new entity from the record.

    Args:
        record: The record data
        entity_type: Type of entity to create
        fk_mapping: FK resolution mapping for resolving references
        session: Database session

    Returns:
        Tuple of (status, error_message)
        status is one of: "added", "failed"
    """
    try:
        if entity_type == "ingredient":
            slug = record.get("ingredient_slug") or record.get("slug")
            display_name = (
                record.get("ingredient_name")
                or record.get("display_name")
                or record.get("name")
            )
            category = record.get("ingredient_category") or record.get("category")

            if not slug:
                return ("failed", "Missing required field: slug")
            if not display_name:
                return ("failed", "Missing required field: display_name")
            if not category:
                return ("failed", "Missing required field: category")

            ingredient = Ingredient(
                slug=slug,
                display_name=display_name,
                category=category,
            )
            session.add(ingredient)
            return ("added", None)

        elif entity_type == "supplier":
            name = record.get("supplier_name") or record.get("name")
            city = record.get("city")
            state = record.get("state")
            zip_code = record.get("zip_code") or record.get("zip")

            if not name:
                return ("failed", "Missing required field: name")
            if not city:
                return ("failed", "Missing required field: city")
            if not state:
                return ("failed", "Missing required field: state")
            if not zip_code:
                return ("failed", "Missing required field: zip_code")

            supplier = Supplier(
                name=name,
                city=city,
                state=state,
                zip_code=zip_code,
            )
            session.add(supplier)
            return ("added", None)

        elif entity_type == "product":
            # Resolve ingredient FK
            ingredient_slug = record.get("ingredient_slug")
            ingredient_id = None

            if ingredient_slug:
                # Check FK mapping first
                if "ingredient" in fk_mapping and ingredient_slug in fk_mapping.get(
                    "ingredient", {}
                ):
                    ingredient_id = fk_mapping["ingredient"][ingredient_slug]
                else:
                    # Try direct lookup
                    ingredient_id = _resolve_fk_by_slug(
                        "ingredient", ingredient_slug, session
                    )

            if not ingredient_id:
                return ("failed", f"Cannot resolve ingredient: {ingredient_slug}")

            brand = record.get("brand")
            package_unit = record.get("package_unit")
            package_unit_quantity = record.get("package_unit_quantity")

            if not brand:
                return ("failed", "Missing required field: brand")
            if not package_unit:
                return ("failed", "Missing required field: package_unit")
            if package_unit_quantity is None:
                return ("failed", "Missing required field: package_unit_quantity")

            product = Product(
                ingredient_id=ingredient_id,
                brand=brand,
                package_unit=package_unit,
                package_unit_quantity=package_unit_quantity,
                product_name=record.get("product_name"),
                package_size=record.get("package_size"),
                upc_code=record.get("upc_code"),
            )
            session.add(product)
            return ("added", None)

        elif entity_type == "inventory_item":
            # Resolve product FK
            product_slug = record.get("product_slug")
            product_id = None

            if product_slug:
                # Check FK mapping first
                if "product" in fk_mapping and product_slug in fk_mapping.get("product", {}):
                    product_id = fk_mapping["product"][product_slug]
                else:
                    # Try direct lookup
                    product_id = _resolve_fk_by_slug("product", product_slug, session)

            if not product_id:
                return ("failed", f"Cannot resolve product: {product_slug}")

            # Parse date fields
            purchase_date = record.get("purchase_date")
            expiration_date = record.get("expiration_date")
            opened_date = record.get("opened_date")

            inventory_item = InventoryItem(
                product_id=product_id,
                quantity=record.get("quantity", 0.0),
                unit_cost=record.get("unit_cost"),
                purchase_date=purchase_date,
                expiration_date=expiration_date,
                opened_date=opened_date,
                location=record.get("location"),
                lot_or_batch=record.get("lot_or_batch"),
                notes=record.get("notes"),
            )
            session.add(inventory_item)
            return ("added", None)

        elif entity_type == "purchase":
            # Resolve product FK
            product_slug = record.get("product_slug")
            product_id = None

            if product_slug:
                # Check FK mapping first
                if "product" in fk_mapping and product_slug in fk_mapping.get("product", {}):
                    product_id = fk_mapping["product"][product_slug]
                else:
                    # Try direct lookup
                    product_id = _resolve_fk_by_slug("product", product_slug, session)

            if not product_id:
                return ("failed", f"Cannot resolve product: {product_slug}")

            # Resolve supplier FK
            supplier_name = record.get("supplier_name")
            supplier_id = None

            if supplier_name:
                # Check FK mapping first
                if "supplier" in fk_mapping and supplier_name in fk_mapping.get("supplier", {}):
                    supplier_id = fk_mapping["supplier"][supplier_name]
                else:
                    # Try direct lookup
                    supplier_id = _resolve_fk_by_slug("supplier", supplier_name, session)

            if not supplier_id:
                return ("failed", f"Cannot resolve supplier: {supplier_name}")

            # Parse purchase date
            purchase_date = record.get("purchase_date")

            purchase = Purchase(
                product_id=product_id,
                supplier_id=supplier_id,
                purchase_date=purchase_date,
                unit_price=record.get("unit_price"),
                quantity_purchased=record.get("quantity_purchased", 1),
                notes=record.get("notes"),
            )
            session.add(purchase)
            return ("added", None)

        else:
            return ("failed", f"Unsupported entity type: {entity_type}")

    except Exception as e:
        return ("failed", str(e))


# ============================================================================
# Skipped Records Logging
# ============================================================================


def _write_skipped_records_log(
    import_file: str,
    skipped_records: List[Dict[str, Any]],
    mode: str,
    output_dir: Optional[str] = None,
) -> str:
    """Write skipped records to a log file.

    Args:
        import_file: Path to the original import file
        skipped_records: List of skipped record entries
        mode: Import mode used
        output_dir: Optional output directory (defaults to same as import file)

    Returns:
        Path to the created log file
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    import_path = Path(import_file)

    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = import_path.parent

    log_filename = f"import_skipped_{timestamp}.json"
    log_path = output_path / log_filename

    log_data = {
        "import_file": str(import_path.name),
        "import_date": datetime.now().isoformat(),
        "mode": mode,
        "skipped_records": skipped_records,
    }

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    return str(log_path)


# ============================================================================
# Main Import Function
# ============================================================================


def import_view(
    file_path: str,
    mode: str = "merge",
    dry_run: bool = False,
    skip_on_error: bool = False,
    resolver: Optional[FKResolverCallback] = None,
    session: Session = None,
) -> EnhancedImportResult:
    """Import a denormalized view file with FK resolution.

    Args:
        file_path: Path to the view JSON file
        mode: Import mode - "merge" (default) or "skip_existing"
        dry_run: If True, preview changes without modifying database
        skip_on_error: If True, skip records with errors and continue
        resolver: Optional FK resolver callback for missing references
        session: Optional database session for transactional composition

    Returns:
        EnhancedImportResult with import statistics and resolution tracking
    """
    if session is not None:
        return _import_view_impl(
            file_path, mode, dry_run, skip_on_error, resolver, session
        )

    with session_scope() as session:
        result = _import_view_impl(
            file_path, mode, dry_run, skip_on_error, resolver, session
        )
        if dry_run:
            session.rollback()
        return result


def _import_view_impl(
    file_path: str,
    mode: str,
    dry_run: bool,
    skip_on_error: bool,
    resolver: Optional[FKResolverCallback],
    session: Session,
) -> EnhancedImportResult:
    """Implementation of view import with FK resolution.

    Args:
        file_path: Path to the view JSON file
        mode: Import mode - "merge" or "skip_existing"
        dry_run: If True, preview changes without modifying database
        skip_on_error: If True, skip records with errors and continue
        resolver: Optional FK resolver callback
        session: Database session

    Returns:
        EnhancedImportResult with import statistics
    """
    result = EnhancedImportResult()
    result.dry_run = dry_run
    skipped_records: List[Dict[str, Any]] = []

    # Load the view file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            view_data = json.load(f)
    except FileNotFoundError:
        result.add_error("file", file_path, f"File not found: {file_path}")
        return result
    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result

    # Extract view metadata
    view_type = view_data.get("view_type")
    if not view_type:
        result.add_error("file", file_path, "Missing view_type in file")
        return result

    records = view_data.get("records", [])
    if not records:
        result.add_warning("file", file_path, "No records in file")
        return result

    meta = view_data.get("_meta", {})
    editable_fields = meta.get("editable_fields", [])

    # Determine entity type from view_type
    entity_type = _view_type_to_entity_type(view_type)
    if not entity_type:
        result.add_error("file", file_path, f"Unknown view type: {view_type}")
        return result

    # Collect missing FKs
    missing_fks = _collect_missing_fks_for_view(records, entity_type, session)

    # Resolve missing FKs if any
    fk_mapping: Dict[str, Dict[str, int]] = {}
    if missing_fks:
        if resolver:
            # Use the resolver callback
            fk_mapping, resolutions = resolve_missing_fks(
                missing_fks, resolver, session
            )
            result.resolutions = resolutions

            # Track resolution stats
            for resolution in resolutions:
                if resolution.choice == ResolutionChoice.CREATE:
                    result.add_created_entity(resolution.entity_type)
                elif resolution.choice == ResolutionChoice.MAP:
                    result.add_mapped_entity(resolution.entity_type)
                elif resolution.choice == ResolutionChoice.SKIP:
                    # Records with skipped FKs will be counted per-record below
                    pass
        elif skip_on_error:
            # No resolver and skip_on_error - we'll skip records with missing FKs
            pass
        else:
            # No resolver and not skip_on_error - fail with error
            missing_list = ", ".join(
                f"{mfk.entity_type}:{mfk.missing_value}" for mfk in missing_fks
            )
            result.add_error(
                "fk_resolution",
                file_path,
                f"Missing foreign key references: {missing_list}",
                "Provide a resolver callback or use skip_on_error=True",
            )
            return result

    # Build set of skipped FK values for quick lookup
    skipped_fk_values: set = set()
    for resolution in result.resolutions:
        if resolution.choice == ResolutionChoice.SKIP:
            skipped_fk_values.add((resolution.entity_type, resolution.missing_value))

    # Process each record
    for idx, record in enumerate(records):
        record_id = _get_record_identifier(record, entity_type)

        # Check if this record has a skipped FK
        if _record_has_skipped_fk(record, entity_type, skipped_fk_values):
            result.skipped_due_to_fk += 1
            if skip_on_error:
                skipped_records.append(
                    {
                        "record_index": idx,
                        "skip_reason": "fk_skipped",
                        "original_record": record,
                    }
                )
            result.add_skip(
                entity_type,
                record_id,
                "Foreign key was skipped during resolution",
            )
            continue

        # Check for missing FK that wasn't resolved
        missing_fk = _check_record_fk(record, entity_type, fk_mapping, session)
        if missing_fk:
            if skip_on_error:
                skipped_records.append(
                    {
                        "record_index": idx,
                        "skip_reason": "fk_missing",
                        "fk_entity": missing_fk[0],
                        "fk_value": missing_fk[1],
                        "original_record": record,
                    }
                )
                result.skipped_due_to_fk += 1
                result.add_skip(
                    entity_type,
                    record_id,
                    f"Missing {missing_fk[0]}: {missing_fk[1]}",
                )
                continue
            else:
                result.add_error(
                    entity_type,
                    record_id,
                    f"Missing {missing_fk[0]}: {missing_fk[1]}",
                )
                continue

        # Import the record based on mode
        if mode == "merge":
            status, error = _import_record_merge(
                record, entity_type, editable_fields, fk_mapping, session
            )
        elif mode == "skip_existing":
            status, error = _import_record_skip_existing(
                record, entity_type, fk_mapping, session
            )
        else:
            result.add_error(entity_type, record_id, f"Unknown mode: {mode}")
            continue

        # Record the result
        if status == "added":
            result.add_success(entity_type)
        elif status == "updated":
            result.add_success(entity_type)
            result.add_warning(entity_type, record_id, "Record updated")
        elif status == "skipped":
            result.add_skip(entity_type, record_id, "No changes needed")
        elif status == "failed":
            if skip_on_error:
                skipped_records.append(
                    {
                        "record_index": idx,
                        "skip_reason": "validation_error",
                        "error": error,
                        "original_record": record,
                    }
                )
                result.add_skip(entity_type, record_id, error or "Unknown error")
            else:
                result.add_error(entity_type, record_id, error or "Unknown error")

    # Write skipped records log if any
    if skipped_records:
        result.skipped_records_path = _write_skipped_records_log(
            file_path, skipped_records, mode
        )

    return result


# ============================================================================
# Helper Functions
# ============================================================================


def _view_type_to_entity_type(view_type: str) -> Optional[str]:
    """Convert view type to entity type."""
    mapping = {
        "products": "product",
        "product": "product",
        "ingredients": "ingredient",
        "ingredient": "ingredient",
        "suppliers": "supplier",
        "supplier": "supplier",
        "inventory": "inventory_item",
        "inventory_item": "inventory_item",
        "purchases": "purchase",
        "purchase": "purchase",
        "materials": "material",
        "material": "material",
        "recipes": "recipe",
        "recipe": "recipe",
    }
    return mapping.get(view_type.lower())


def _get_record_identifier(record: Dict[str, Any], entity_type: str) -> str:
    """Get a human-readable identifier for a record."""
    if entity_type == "ingredient":
        return record.get("ingredient_slug") or record.get("slug") or str(record.get("id", "unknown"))
    elif entity_type == "supplier":
        return record.get("supplier_name") or record.get("name") or str(record.get("id", "unknown"))
    elif entity_type == "product":
        brand = record.get("brand", "")
        name = record.get("product_name", "")
        return f"{brand} {name}".strip() or str(record.get("id", "unknown"))
    elif entity_type == "inventory_item":
        product_slug = record.get("product_slug", "")
        uuid = record.get("uuid", "")
        return f"{product_slug} ({uuid[:8]})" if uuid else product_slug or str(record.get("id", "unknown"))
    elif entity_type == "purchase":
        product_slug = record.get("product_slug", "")
        purchase_date = record.get("purchase_date", "")
        return f"{product_slug} @ {purchase_date}" or str(record.get("id", "unknown"))
    return str(record.get("id", "unknown"))


def _collect_missing_fks_for_view(
    records: List[Dict[str, Any]],
    entity_type: str,
    session: Session,
) -> List[MissingFK]:
    """Collect missing FK references from view records.

    Args:
        records: List of records from the view
        entity_type: Type of entity being imported
        session: Database session

    Returns:
        List of MissingFK instances for unresolved references
    """
    missing_fks: Dict[Tuple[str, str, str], MissingFK] = {}

    for record in records:
        # Check for missing FKs based on entity type
        if entity_type == "product":
            # Products have FK to ingredient
            ingredient_slug = record.get("ingredient_slug")
            if ingredient_slug:
                ingredient_id = _resolve_fk_by_slug("ingredient", ingredient_slug, session)
                if ingredient_id is None:
                    key = ("ingredient", ingredient_slug, "ingredient_slug")
                    if key not in missing_fks:
                        missing_fks[key] = MissingFK(
                            entity_type="ingredient",
                            missing_value=ingredient_slug,
                            field_name="ingredient_slug",
                            affected_record_count=0,
                            sample_records=[],
                        )
                    missing_fks[key].affected_record_count += 1
                    if len(missing_fks[key].sample_records) < 3:
                        missing_fks[key].sample_records.append(record)

            # Products may also reference supplier
            supplier_name = record.get("supplier_name")
            if supplier_name:
                supplier_id = _resolve_fk_by_slug("supplier", supplier_name, session)
                if supplier_id is None:
                    key = ("supplier", supplier_name, "supplier_name")
                    if key not in missing_fks:
                        missing_fks[key] = MissingFK(
                            entity_type="supplier",
                            missing_value=supplier_name,
                            field_name="supplier_name",
                            affected_record_count=0,
                            sample_records=[],
                        )
                    missing_fks[key].affected_record_count += 1
                    if len(missing_fks[key].sample_records) < 3:
                        missing_fks[key].sample_records.append(record)

        elif entity_type == "inventory_item":
            # Inventory items have FK to product
            product_slug = record.get("product_slug")
            if product_slug:
                product_id = _resolve_fk_by_slug("product", product_slug, session)
                if product_id is None:
                    key = ("product", product_slug, "product_slug")
                    if key not in missing_fks:
                        missing_fks[key] = MissingFK(
                            entity_type="product",
                            missing_value=product_slug,
                            field_name="product_slug",
                            affected_record_count=0,
                            sample_records=[],
                        )
                    missing_fks[key].affected_record_count += 1
                    if len(missing_fks[key].sample_records) < 3:
                        missing_fks[key].sample_records.append(record)

        elif entity_type == "purchase":
            # Purchases have FK to product and supplier
            product_slug = record.get("product_slug")
            if product_slug:
                product_id = _resolve_fk_by_slug("product", product_slug, session)
                if product_id is None:
                    key = ("product", product_slug, "product_slug")
                    if key not in missing_fks:
                        missing_fks[key] = MissingFK(
                            entity_type="product",
                            missing_value=product_slug,
                            field_name="product_slug",
                            affected_record_count=0,
                            sample_records=[],
                        )
                    missing_fks[key].affected_record_count += 1
                    if len(missing_fks[key].sample_records) < 3:
                        missing_fks[key].sample_records.append(record)

            supplier_name = record.get("supplier_name")
            if supplier_name:
                supplier_id = _resolve_fk_by_slug("supplier", supplier_name, session)
                if supplier_id is None:
                    key = ("supplier", supplier_name, "supplier_name")
                    if key not in missing_fks:
                        missing_fks[key] = MissingFK(
                            entity_type="supplier",
                            missing_value=supplier_name,
                            field_name="supplier_name",
                            affected_record_count=0,
                            sample_records=[],
                        )
                    missing_fks[key].affected_record_count += 1
                    if len(missing_fks[key].sample_records) < 3:
                        missing_fks[key].sample_records.append(record)

    return list(missing_fks.values())


def _check_record_fk(
    record: Dict[str, Any],
    entity_type: str,
    fk_mapping: Dict[str, Dict[str, int]],
    session: Session,
) -> Optional[Tuple[str, str]]:
    """Check if a record has unresolved FK references.

    Args:
        record: The record to check
        entity_type: Type of entity
        fk_mapping: FK resolution mapping
        session: Database session

    Returns:
        Tuple of (fk_entity_type, missing_value) if unresolved, None otherwise
    """
    if entity_type == "product":
        ingredient_slug = record.get("ingredient_slug")
        if ingredient_slug:
            # Check mapping first
            if "ingredient" in fk_mapping and ingredient_slug in fk_mapping.get("ingredient", {}):
                pass  # Resolved via mapping
            elif _resolve_fk_by_slug("ingredient", ingredient_slug, session) is None:
                return ("ingredient", ingredient_slug)

    elif entity_type == "inventory_item":
        product_slug = record.get("product_slug")
        if product_slug:
            # Check mapping first
            if "product" in fk_mapping and product_slug in fk_mapping.get("product", {}):
                pass  # Resolved via mapping
            elif _resolve_fk_by_slug("product", product_slug, session) is None:
                return ("product", product_slug)

    elif entity_type == "purchase":
        product_slug = record.get("product_slug")
        if product_slug:
            # Check mapping first
            if "product" in fk_mapping and product_slug in fk_mapping.get("product", {}):
                pass  # Resolved via mapping
            elif _resolve_fk_by_slug("product", product_slug, session) is None:
                return ("product", product_slug)

        # Supplier is also required for purchases
        supplier_name = record.get("supplier_name")
        if supplier_name:
            if "supplier" in fk_mapping and supplier_name in fk_mapping.get("supplier", {}):
                pass  # Resolved via mapping
            elif _resolve_fk_by_slug("supplier", supplier_name, session) is None:
                return ("supplier", supplier_name)

    return None


def _record_has_skipped_fk(
    record: Dict[str, Any],
    entity_type: str,
    skipped_fk_values: set,
) -> bool:
    """Check if a record references a skipped FK value.

    Args:
        record: The record to check
        entity_type: Type of entity
        skipped_fk_values: Set of (entity_type, value) tuples for skipped FKs

    Returns:
        True if the record references a skipped FK
    """
    if entity_type == "product":
        ingredient_slug = record.get("ingredient_slug")
        if ingredient_slug and ("ingredient", ingredient_slug) in skipped_fk_values:
            return True

        supplier_name = record.get("supplier_name")
        if supplier_name and ("supplier", supplier_name) in skipped_fk_values:
            return True

    elif entity_type == "inventory_item":
        product_slug = record.get("product_slug")
        if product_slug and ("product", product_slug) in skipped_fk_values:
            return True

    elif entity_type == "purchase":
        product_slug = record.get("product_slug")
        if product_slug and ("product", product_slug) in skipped_fk_values:
            return True

        supplier_name = record.get("supplier_name")
        if supplier_name and ("supplier", supplier_name) in skipped_fk_values:
            return True

    return False
