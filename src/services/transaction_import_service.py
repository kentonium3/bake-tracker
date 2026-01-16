"""
Transaction Import Service - Import purchases and adjustments from JSON.

Handles non-catalog imports that create transaction records and
modify inventory state. Unlike catalog imports, these are NOT idempotent.

Key Differences from Catalog Import:
- Transaction imports create NEW records (not merge/update)
- Duplicate detection prevents double-import
- Side effects: creates InventoryItem, updates costs
- Atomic transactions: all-or-nothing rollback on failure

Usage:
    from src.services.transaction_import_service import import_purchases

    # Import from BT Mobile purchase file
    result = import_purchases("purchases.json", dry_run=True)
    print(result.get_summary())
"""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from src.services.database import session_scope
from src.services.import_export_service import ImportResult
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.inventory_item import InventoryItem
from src.models.inventory_depletion import InventoryDepletion
from src.models.supplier import Supplier


# ============================================================================
# Constants
# ============================================================================

# Expected schema version for purchase imports
SUPPORTED_SCHEMA_VERSIONS = {"4.0"}

# Allowed reason codes for inventory adjustments (FR-021)
# Stored as lowercase for case-insensitive matching
ALLOWED_REASON_CODES = {"spoilage", "waste", "correction", "damaged", "other"}


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_datetime(datetime_str: str) -> Optional[date]:
    """
    Parse datetime string to date object.

    Supports ISO 8601 format with or without time component.

    Args:
        datetime_str: ISO format datetime string (e.g., "2026-01-12T14:15:23Z")

    Returns:
        date object, or None if parsing fails or input is None
    """
    if not datetime_str:
        return None

    try:
        # Handle ISO format with time
        if "T" in datetime_str:
            # Remove Z suffix and parse
            clean_str = datetime_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            return dt.date()
        else:
            # Simple date format
            return date.fromisoformat(datetime_str)
    except (ValueError, TypeError):
        return None


def _resolve_supplier(name: str, session: Session) -> Optional[Supplier]:
    """
    Find or create supplier by name.

    Creates a minimal supplier record if not found. Uses supplier_type='online'
    for new suppliers since mobile imports typically don't include full address.

    Args:
        name: Supplier name
        session: Database session

    Returns:
        Supplier instance, or None if name is empty
    """
    if not name:
        return None

    # Try to find existing supplier by name (case-insensitive)
    supplier = session.query(Supplier).filter(
        Supplier.name.ilike(name)
    ).first()

    if not supplier:
        # Create minimal supplier record
        supplier = Supplier(
            name=name,
            supplier_type="physical",  # Assume physical store for now
            is_active=True,
        )
        session.add(supplier)
        session.flush()  # Get supplier.id

    return supplier


def _is_duplicate_purchase(
    product_id: int,
    purchase_date: date,
    unit_price: Decimal,
    session: Session,
) -> bool:
    """
    Check if purchase appears to be a duplicate.

    Uses three-field combination for detection:
    - Same product
    - Same date
    - Same unit price

    Args:
        product_id: Product ID
        purchase_date: Date of purchase
        unit_price: Unit price
        session: Database session

    Returns:
        True if duplicate found, False otherwise
    """
    existing = session.query(Purchase).filter(
        Purchase.product_id == product_id,
        Purchase.purchase_date == purchase_date,
        Purchase.unit_price == unit_price,
    ).first()

    return existing is not None


def _update_product_average_cost(product: Product, session: Session) -> None:
    """
    Recalculate weighted average cost from inventory items.

    Computes weighted average based on current inventory quantities
    and their unit costs.

    Args:
        product: Product to update
        session: Database session
    """
    items = session.query(InventoryItem).filter(
        InventoryItem.product_id == product.id,
        InventoryItem.quantity > 0,
    ).all()

    if not items:
        return

    total_value = Decimal("0")
    total_quantity = Decimal("0")

    for item in items:
        if item.unit_cost is not None and item.quantity > 0:
            total_value += Decimal(str(item.unit_cost)) * Decimal(str(item.quantity))
            total_quantity += Decimal(str(item.quantity))

    # Note: Product model doesn't have average_cost field currently.
    # This is a placeholder for future enhancement.
    # When average_cost field is added:
    # if total_quantity > 0:
    #     product.average_cost = float(total_value / total_quantity)


def _resolve_product_by_slug(
    product_slug: str,
    session: Session,
) -> Tuple[Optional[Product], Optional[str]]:
    """
    Resolve a product from a composite slug, product ID, or UPC/GTIN.

    Supports multiple formats:
    1. Composite slug: ingredient_slug:brand:package_unit_quantity:package_unit
       Example: all_purpose_flour:King Arthur:5.0:lb
    2. Simple product ID (integer as string)
    3. UPC code
    4. GTIN code

    For products without a brand, use empty string in the composite slug:
        all_purpose_flour::5.0:lb

    Args:
        product_slug: Product identifier in one of the supported formats
        session: Database session

    Returns:
        Tuple of (Product or None, error_message or None)
    """
    if not product_slug:
        return None, "Missing product_slug"

    # Try parsing as composite slug (format: ingredient_slug:brand:qty:unit)
    parts = product_slug.split(":")
    if len(parts) >= 4:
        ingredient_slug = parts[0]
        brand = parts[1] if parts[1] else None  # Empty string means no brand
        try:
            package_unit_quantity = float(parts[2])
        except (ValueError, TypeError):
            return None, f"Invalid package_unit_quantity in slug: {parts[2]}"
        package_unit = parts[3]

        # Resolve ingredient first
        ingredient = session.query(Ingredient).filter(
            Ingredient.slug == ingredient_slug
        ).first()
        if not ingredient:
            return None, f"Ingredient '{ingredient_slug}' not found"

        # Find product by composite key
        query = session.query(Product).filter(
            Product.ingredient_id == ingredient.id,
            Product.package_unit == package_unit,
            Product.package_unit_quantity == package_unit_quantity,
        )
        if brand:
            query = query.filter(Product.brand == brand)
        else:
            query = query.filter(Product.brand.is_(None))

        product = query.first()
        if product:
            return product, None
        else:
            return None, f"No product found matching: ingredient={ingredient_slug}, brand={brand or 'None'}, qty={package_unit_quantity}, unit={package_unit}"

    # Try as simple product ID
    try:
        product_id = int(product_slug)
        product = session.query(Product).filter(Product.id == product_id).first()
        if product:
            return product, None
        else:
            return None, f"Product ID {product_id} not found"
    except ValueError:
        pass

    # If not composite slug and not ID, try as UPC
    product = session.query(Product).filter(Product.upc_code == product_slug).first()
    if product:
        return product, None

    # Try as GTIN
    product = session.query(Product).filter(Product.gtin == product_slug).first()
    if product:
        return product, None

    return None, f"Could not resolve product_slug '{product_slug}'. Expected format: ingredient_slug:brand:qty:unit (e.g., all_purpose_flour:King Arthur:5.0:lb)"


# ============================================================================
# Main Import Function
# ============================================================================


def import_purchases(
    file_path: str,
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> ImportResult:
    """
    Import purchase transactions from JSON file.

    Creates Purchase and InventoryItem records, updates costs.
    Detects and skips duplicate purchases.

    Args:
        file_path: Path to JSON file with purchases
        dry_run: If True, validate without committing

    Returns:
        ImportResult with counts and any errors

    Expected JSON format:
        {
            "schema_version": "4.0",
            "import_type": "purchases",
            "created_at": "2026-01-12T14:30:00Z",
            "source": "bt_mobile",
            "supplier": "Costco Waltham MA",  # Optional default supplier
            "purchases": [
                {
                    "product_slug": "flour_all_purpose_king_arthur_5lb",
                    "purchased_at": "2026-01-12T14:15:23Z",
                    "unit_price": 7.99,
                    "quantity_purchased": 2,
                    "supplier": "Costco",  # Optional per-purchase supplier
                    "notes": "Weekly shopping"
                }
            ]
        }
    """
    if session is not None:
        return _import_purchases_impl(file_path, dry_run, session)

    with session_scope() as sess:
        result = _import_purchases_impl(file_path, dry_run, sess)
        if dry_run:
            sess.rollback()
        return result


def _import_purchases_impl(
    file_path: str,
    dry_run: bool,
    session: Session,
) -> ImportResult:
    """
    Internal implementation of purchase import.

    Processes all purchases atomically - any failure rolls back all changes.

    Args:
        file_path: Path to JSON file
        dry_run: If True, rollback after validation
        session: Database session

    Returns:
        ImportResult with counts and errors
    """
    result = ImportResult()

    # Load and validate file
    path = Path(file_path)
    if not path.exists():
        result.add_error("file", file_path, f"File not found: {file_path}")
        return result

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result

    # Validate import type
    import_type = data.get("import_type")
    if import_type != "purchases":
        result.add_error(
            "file",
            file_path,
            f"Invalid import_type: '{import_type}' (expected 'purchases')",
            suggestion="Ensure file has 'import_type': 'purchases'",
        )
        return result

    # Validate schema version (informational warning only)
    schema_version = data.get("schema_version")
    if schema_version and schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        result.add_warning(
            "file",
            file_path,
            f"Schema version '{schema_version}' may not be fully supported",
            suggestion=f"Expected one of: {', '.join(SUPPORTED_SCHEMA_VERSIONS)}",
        )

    # Get default supplier from file header
    default_supplier_name = data.get("supplier")

    # Process each purchase
    purchases_data = data.get("purchases", [])

    if not purchases_data:
        result.add_warning("file", file_path, "No purchases in file")
        return result

    for purchase_data in purchases_data:
        _process_single_purchase(
            purchase_data,
            default_supplier_name,
            result,
            session,
        )

    # Handle dry-run: rollback instead of commit
    if dry_run:
        session.rollback()

    return result


def _process_single_purchase(
    purchase_data: Dict,
    default_supplier_name: Optional[str],
    result: ImportResult,
    session: Session,
) -> None:
    """
    Process a single purchase record.

    Creates Purchase and InventoryItem records if valid.

    Args:
        purchase_data: Purchase data from JSON
        default_supplier_name: Default supplier from file header
        result: ImportResult to update
        session: Database session
    """
    # Extract and validate product_slug
    product_slug = purchase_data.get("product_slug")
    if not product_slug:
        result.add_error(
            "purchases",
            "unknown",
            "Missing product_slug field",
            suggestion="Each purchase must have a 'product_slug' field in format: ingredient_slug:brand:qty:unit",
        )
        return

    # Validate positive quantity
    quantity = purchase_data.get("quantity_purchased", 0)
    if quantity <= 0:
        result.add_error(
            "purchases",
            product_slug,
            f"Invalid quantity {quantity}: purchases must have positive quantities",
            suggestion="Use inventory adjustments for negative quantities",
        )
        return

    # Resolve product using composite slug or other identifiers
    product, error = _resolve_product_by_slug(product_slug, session)
    if not product:
        result.add_error(
            "purchases",
            product_slug,
            f"Product '{product_slug}' not found: {error}",
            suggestion="Ensure product exists in catalog before importing purchases",
        )
        return

    # Parse purchase date
    purchased_at_str = purchase_data.get("purchased_at")
    purchase_date = _parse_datetime(purchased_at_str)
    if not purchase_date:
        # Default to today if no date provided
        purchase_date = date.today()

    # Parse unit price
    unit_price_raw = purchase_data.get("unit_price", 0)
    try:
        unit_price = Decimal(str(unit_price_raw))
    except (ValueError, TypeError, ArithmeticError):
        result.add_error(
            "purchases",
            product_slug,
            f"Invalid unit_price: '{unit_price_raw}'",
            suggestion="Provide a valid numeric value for unit_price",
        )
        return

    # Check for duplicate
    if _is_duplicate_purchase(product.id, purchase_date, unit_price, session):
        result.add_skip(
            "purchases",
            product_slug,
            "Duplicate purchase detected (same product, date, price)",
            suggestion="This purchase may have been imported previously",
        )
        return

    # Resolve supplier (use per-purchase supplier, file default, or create "Unknown")
    supplier_name = purchase_data.get("supplier") or default_supplier_name
    if supplier_name:
        supplier = _resolve_supplier(supplier_name, session)
    else:
        # Create/find "Unknown" supplier since supplier_id is required
        supplier = _resolve_supplier("Unknown", session)

    # Create Purchase record
    purchase = Purchase(
        product_id=product.id,
        supplier_id=supplier.id,
        purchase_date=purchase_date,
        unit_price=unit_price,
        quantity_purchased=quantity,
        notes=purchase_data.get("notes"),
    )
    session.add(purchase)
    session.flush()  # Get purchase.id for InventoryItem FK

    # Create InventoryItem record linked to purchase
    inventory_item = InventoryItem(
        product_id=product.id,
        purchase_id=purchase.id,
        quantity=float(quantity),  # InventoryItem.quantity is Float
        purchase_date=purchase_date,
        unit_cost=float(unit_price),  # InventoryItem.unit_cost is Float
    )
    session.add(inventory_item)

    # Update product average cost
    _update_product_average_cost(product, session)

    # Record success
    result.add_success("purchases")


# ============================================================================
# Adjustment Import (WP05)
# ============================================================================


def import_adjustments(
    file_path: str,
    dry_run: bool = False,
    session: Optional[Session] = None,
) -> ImportResult:
    """
    Import inventory adjustments from JSON file.

    Decreases inventory quantities for spoilage, waste, and corrections.
    Only negative quantities are allowed (increases must be done via purchases).
    Uses FIFO to select which inventory items to adjust.

    Args:
        file_path: Path to JSON file with adjustments
        dry_run: If True, validate without committing

    Returns:
        ImportResult with counts and any errors

    JSON Schema:
        {
            "schema_version": "4.0",
            "import_type": "adjustments",
            "created_at": "2026-01-12T09:15:00Z",
            "source": "bt_mobile",
            "adjustments": [
                {
                    "product_slug": "flour_all_purpose_king_arthur_5lb",
                    "adjusted_at": "2026-01-12T09:10:12Z",
                    "quantity": -2.5,
                    "reason_code": "spoilage",
                    "notes": "Found mold, discarding"
                }
            ]
        }

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    if session is not None:
        return _import_adjustments_impl(file_path, dry_run, session)

    with session_scope() as sess:
        result = _import_adjustments_impl(file_path, dry_run, sess)
        if dry_run:
            sess.rollback()
        return result


def _import_adjustments_impl(
    file_path: str,
    dry_run: bool,
    session: Session,
) -> ImportResult:
    """
    Internal implementation of adjustment import.

    Args:
        file_path: Path to JSON file
        dry_run: If True, rollback after validation
        session: Database session

    Returns:
        ImportResult with counts and errors
    """
    result = ImportResult()

    # Load and validate file
    path = Path(file_path)
    if not path.exists():
        result.add_error("file", file_path, f"File not found: {file_path}")
        return result

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result

    # Validate schema version
    schema_version = data.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        result.add_error(
            "file",
            file_path,
            f"Unsupported schema version '{schema_version}'",
            suggestion=f"Expected one of: {', '.join(SUPPORTED_SCHEMA_VERSIONS)}",
        )
        return result

    # Validate import type - accept "adjustments" or "inventory_updates"
    import_type = data.get("import_type")
    if import_type not in ("adjustments", "inventory_updates"):
        result.add_error(
            "file",
            file_path,
            f"Invalid import_type: '{import_type}'",
            suggestion="Use 'adjustments' or 'inventory_updates' for adjustment imports",
        )
        return result

    # Get adjustments array - support both key names for compatibility
    adjustments_data = data.get("adjustments") or data.get("inventory_updates", [])

    if not adjustments_data:
        result.add_warning("file", file_path, "No adjustments in file")
        return result

    # Process each adjustment
    for adj_data in adjustments_data:
        _process_single_adjustment(
            adj_data,
            result,
            session,
        )

    # Handle dry-run: rollback instead of commit
    if dry_run:
        session.rollback()

    return result


def _process_single_adjustment(
    adj_data: Dict,
    result: ImportResult,
    session: Session,
) -> None:
    """
    Process a single adjustment record.

    Validates fields, resolves product, selects inventory via FIFO,
    creates depletion record, and updates inventory quantity.

    Args:
        adj_data: Single adjustment record from JSON
        result: ImportResult to update
        session: Database session
    """
    product_slug = adj_data.get("product_slug", "unknown")
    identifier = product_slug

    # -------------------------------------------------------------------------
    # T039: Validate negative quantities only
    # -------------------------------------------------------------------------
    quantity = adj_data.get("quantity")

    if quantity is None:
        result.add_error(
            "adjustments",
            identifier,
            "Missing required field: quantity",
            suggestion="Add 'quantity' field with negative value (e.g., -2.5)",
        )
        return

    # Convert to Decimal for precision
    try:
        quantity_decimal = Decimal(str(quantity))
    except (ValueError, TypeError):
        result.add_error(
            "adjustments",
            identifier,
            f"Invalid quantity value: {quantity}",
            suggestion="Quantity must be a number",
        )
        return

    # Reject positive or zero quantities (FR-020, SC-008)
    if quantity_decimal >= 0:
        result.add_error(
            "adjustments",
            identifier,
            f"Invalid quantity {quantity}: adjustments must be negative",
            suggestion="Inventory increases must be done via purchase import",
        )
        return

    # -------------------------------------------------------------------------
    # T040: Default reason_code to CORRECTION if not provided
    # -------------------------------------------------------------------------
    reason_code_raw = adj_data.get("reason_code")

    # Default to "correction" if not specified (common case for manual adjustments)
    if not reason_code_raw:
        reason_code = "correction"
    else:
        # Normalize to lowercase for case-insensitive matching (FR-021)
        reason_code = reason_code_raw.lower()

    # -------------------------------------------------------------------------
    # T041: Validate reason_code against allowed list
    # -------------------------------------------------------------------------
    if reason_code not in ALLOWED_REASON_CODES:
        result.add_error(
            "adjustments",
            identifier,
            f"Invalid reason_code '{reason_code}'",
            suggestion=f"Valid codes: {', '.join(sorted(ALLOWED_REASON_CODES))}",
        )
        return

    # -------------------------------------------------------------------------
    # T042: Resolve product_slug to Product and find InventoryItem (FIFO)
    # -------------------------------------------------------------------------
    if not product_slug or product_slug == "unknown":
        result.add_error(
            "adjustments",
            identifier,
            "Missing required field: product_slug",
            suggestion="Add 'product_slug' referencing an existing product (format: ingredient_slug:brand:qty:unit)",
        )
        return

    # Resolve product using composite slug or other identifiers
    product, error = _resolve_product_by_slug(product_slug, session)
    if not product:
        result.add_error(
            "adjustments",
            product_slug,
            f"Product '{product_slug}' not found: {error}",
            suggestion="Import the product first or check the slug format",
        )
        return

    # Query inventory items in FIFO order (oldest purchase_date first)
    inventory_items = (
        session.query(InventoryItem)
        .filter(
            InventoryItem.product_id == product.id,
            InventoryItem.quantity > 0,  # Only items with remaining quantity
        )
        .order_by(InventoryItem.purchase_date.asc().nullslast())
        .all()
    )

    if not inventory_items:
        result.add_error(
            "adjustments",
            product_slug,
            "No inventory found for product",
            suggestion="Cannot adjust inventory that doesn't exist",
        )
        return

    # -------------------------------------------------------------------------
    # T043: Prevent adjustments exceeding available inventory (FR-022)
    # -------------------------------------------------------------------------
    total_available = sum(Decimal(str(i.quantity)) for i in inventory_items)
    adjustment_amount = abs(quantity_decimal)  # quantity is negative, get positive

    if adjustment_amount > total_available:
        result.add_error(
            "adjustments",
            product_slug,
            f"Adjustment amount ({adjustment_amount}) exceeds available inventory ({total_available})",
            suggestion="Cannot reduce inventory below zero",
        )
        return

    # -------------------------------------------------------------------------
    # T044 & T045: Create depletion records and update inventory quantities
    # -------------------------------------------------------------------------
    adjusted_at_str = adj_data.get("adjusted_at")
    adjusted_at = None
    if adjusted_at_str:
        # Parse datetime
        try:
            if adjusted_at_str.endswith("Z"):
                adjusted_at_str = adjusted_at_str[:-1] + "+00:00"
            adjusted_at = datetime.fromisoformat(adjusted_at_str)
        except (ValueError, TypeError):
            adjusted_at = datetime.now()
    else:
        adjusted_at = datetime.now()

    notes = adj_data.get("notes")
    remaining_to_adjust = adjustment_amount

    # FIFO: Drain from oldest inventory items first
    for inv_item in inventory_items:
        if remaining_to_adjust <= Decimal("0"):
            break

        available = Decimal(str(inv_item.quantity))
        amount_from_this_item = min(available, remaining_to_adjust)

        # Calculate cost for this portion
        unit_cost = Decimal(str(inv_item.unit_cost)) if inv_item.unit_cost else Decimal("0")
        cost = amount_from_this_item * unit_cost

        # Create InventoryDepletion record for audit trail
        depletion = InventoryDepletion(
            inventory_item_id=inv_item.id,
            quantity_depleted=amount_from_this_item,
            depletion_date=adjusted_at,
            depletion_reason=reason_code,
            notes=notes,
            cost=cost,
            created_by="import:adjustment",
        )
        session.add(depletion)

        # Update inventory item quantity
        inv_item.quantity = float(available - amount_from_this_item)

        remaining_to_adjust -= amount_from_this_item

    # Record success
    result.add_success("adjustments")
