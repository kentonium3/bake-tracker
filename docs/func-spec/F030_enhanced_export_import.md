# Feature 031: Enhanced Export/Import System

**Created:** 2025-12-24  
**Status:** DESIGN  
**Priority:** HIGH  
**Complexity:** HIGH

---

## Important Note on Specification Approach

**This document contains detailed technical illustrations** including code samples, schema definitions, service method signatures, and UI mockups. These are provided as **examples and guidance**, not as prescriptive implementations.

**When using spec-kitty to implement this feature:**
- The code samples are **illustrative** - they show one possible approach
- Spec-kitty should **validate and rationalize** the technical approach during its planning phase
- Spec-kitty may **modify or replace** these examples based on:
  - Current codebase patterns and conventions
  - Better architectural approaches discovered during analysis
  - Constitution compliance verification
  - Test-driven development requirements

**The requirements and business logic are the source of truth** - the technical implementation details should be determined by spec-kitty's specification and planning phases.

---

## Problem Statement

Current export/import system has critical gaps blocking AI-assisted data augmentation and efficient test data management:

**Current State Issues:**

1. **Monolithic exports:** Single `sample_data.json` file with all entities - difficult to process, no FK resolution strategy
2. **No AI-friendly formats:** Cannot export products with ingredient context for UPC enrichment
3. **No partial import:** Cannot import just price updates without full entity records
4. **No FK resolution:** Import fails if IDs don't match (no slug/name-based matching)
5. **Manual entity creation:** Missing suppliers/products force exit, manual creation, re-import cycle
6. **No validation:** Import proceeds blindly, FK errors discovered at database level

**User Impact:**

- **AI augmentation workflow blocked:** Cannot export → AI enrich → import cycle
  - Example: Export products without UPCs → AI researches codes → Import fails (FK mismatches)
- **Test data management painful:** Cannot coordinate multi-file imports (suppliers before products before purchases)
- **Manual data entry friction:** AI generates `purchases.json` from barcode scan → Import fails on missing supplier → User must manually create supplier → Re-import
- **No validation feedback:** Import errors are cryptic database constraint violations

**Real-World Example:**
> User shops at Costco, Wegmans, Penzeys, and Wilson's Farm (new supplier). AI tool generates `purchases.json` file. Import fails: "Supplier 'Wilson's Farm' not found". User must exit import, manually create supplier via UI, re-import file. If file also references new products, cycle repeats multiple times.

---

## Solution Overview

Implement coordinated export/import system with denormalized views for AI augmentation and interactive FK resolution for missing entities.

**Core Architecture:**

```
Export System:
  ├── Normalized Exports (DB rebuild)
  │   ├── Manifest-coordinated file set
  │   ├── Individual entity files (suppliers, ingredients, products, etc.)
  │   ├── FK resolution fields (ID + slug/name)
  │   └── ZIP archive option
  │
  └── Denormalized Views (AI augmentation)
      ├── view_products.json (products with ingredient/supplier context)
      ├── view_inventory.json (inventory with product/purchase context)
      └── view_purchases.json (purchases with product/supplier context)

Import System:
  ├── Validation Phase (pre-import)
  │   ├── Manifest verification (checksums, dependencies)
  │   ├── FK reference checking (ID or slug/name matching)
  │   └── Referential integrity validation
  │
  ├── Resolution Phase (if FK errors)
  │   ├── CLI: Fail with error report (default) or --interactive mode
  │   ├── UI: Interactive resolution wizard (default)
  │   └── Options: Create entity, map to existing, skip record
  │
  └── Import Phase (apply changes)
      ├── Mode: merge (update existing, add new)
      ├── Mode: skip_existing (only add new)
      └── Dry-run option (preview changes)
```

**Key Design Principles:**

1. **Standard filenames for denormalized views:** `view_products.json`, `view_inventory.json`, `view_purchases.json` (persistent working files for export → edit → import cycle)
2. **Timestamped normalized exports:** `2025-12-24_120000_abc123/` (snapshots/backups)
3. **FK resolution via slug/name:** IDs don't have to match between export and import environments
4. **Interactive resolution:** Prompt user to create/map missing entities during import (UI default, CLI opt-in)
5. **Validation before import:** Catch FK errors before database operations
6. **Skip-on-error mode:** Import valid records, log skipped records for later resolution

---

## Scope

### In Scope

**Export Capabilities:**

1. **Coordinated Normalized Exports:**
   - Export manifest with metadata, checksums, dependencies, import order
   - Individual entity files: `01_suppliers.json`, `02_ingredients.json`, `03_products.json`, `04_purchases.json`, `05_inventory_items.json`, etc.
   - FK resolution fields: Both `id` and `slug`/`name` for portable references
   - ZIP archive option: `backup_2025-12-24.zip`
   - Configurable output directory (default: `docs/exports/`)

2. **Denormalized View Exports:**
   - `view_products.json` - Products with ingredient name, category, supplier name, last purchase price
   - `view_inventory.json` - Inventory items with product name, ingredient name, purchase details
   - `view_purchases.json` - Purchases with product name, ingredient name, supplier details
   - Standard persistent filenames (not timestamped - working files)
   - Clearly marked read-only context fields vs editable fields (via documentation)

**Import Capabilities:**

1. **Import Normalized Files:**
   - Manifest validation: Verify checksums, dependencies, version compatibility
   - FK resolution: Match via `id` first, fall back to `slug`/`name` matching
   - Import modes: `merge` (update existing, add new) or `skip_existing` (only add new)
   - Dry-run mode: Report what would change without applying (CLI only)

2. **Import Denormalized Views:**
   - Auto-detect file type (normalized vs denormalized view)
   - Extract normalized updates from denormalized context (e.g., `view_products.json` → Product table updates)
   - Ignore read-only context fields during import
   - Preserve referential integrity

3. **Interactive FK Resolution:**
   - **CLI default:** Fail-fast with error report, require `--interactive` flag for resolution
   - **UI default:** Interactive resolution wizard (prompt for each missing FK)
   - Resolution options per missing FK:
     - Create new entity (prompt for required fields)
     - Map to existing entity (fuzzy search)
     - Skip records referencing this FK
   - Entity types supported: Suppliers, Ingredients, Products
   - Dependency chain handling: Product requires Ingredient (resolve Ingredient first)
   - Referential integrity validation during entity creation

4. **Skip-on-Error Mode:**
   - CLI flag: `--skip-on-error`
   - Skip records with unresolved FK errors, import remaining valid records
   - Log skipped records to `import_skipped_{timestamp}.json`
   - Report: X imported, Y skipped
   - Skipped records file can be edited and re-imported

**File Organization:**

```
docs/exports/
├── 2025-12-24_120000_abc123/         # Normalized export (timestamped)
│   ├── manifest.json
│   ├── 01_suppliers.json
│   ├── 02_ingredients.json
│   ├── 03_products.json
│   ├── 04_purchases.json
│   └── ...
│
├── ai_augmentation/                   # Denormalized views (persistent names)
│   ├── view_products.json
│   ├── view_inventory.json
│   └── view_purchases.json
│
├── archives/
│   └── backup_2025-12-24.zip         # ZIP archive option
│
└── import_skipped_2025-12-24_143022.json  # Skipped records log
```

**CLI Interface:**

```bash
# Export coordinated normalized set
python -m src.cli.main export_complete \
    --output docs/exports/backup_2025-12-24 \
    --zip

# Export denormalized view
python -m src.cli.main export_view products \
    --output docs/exports/ai_augmentation/view_products.json

# Import with validation and interactive resolution
python -m src.cli.main import_view \
    --input docs/exports/ai_augmentation/view_products.json \
    --mode merge \
    --interactive

# Import with skip-on-error
python -m src.cli.main import_view \
    --input messy_data.json \
    --mode merge \
    --skip-on-error

# Validate export set
python -m src.cli.main validate_export \
    --manifest docs/exports/backup_2025-12-24/manifest.json
```

**UI Integration:**

- File → Import → Import View (new menu item)
- Interactive resolution wizard (default behavior)
- Progress dialog with status updates
- Results summary dialog

### Out of Scope

**Deferred to Future Features:**
- Auto-create modes (e.g., `--auto-create suppliers`)
- Additional denormalized views (recipes, events, finished goods)
- Schema transformation utilities (convert old exports to new format)
- Voice interaction files / barcode scan files (use denormalized views for now)
- Replace mode (not needed - can delete DB and import fresh)
- Backward compatibility with old export formats

---

## Technical Design

### Export Manifest Schema

```json
{
  "manifest_version": "1.0",
  "export_id": "550e8400-e29b-41d4-a716-446655440000",
  "exported_at": "2025-12-24T12:00:00Z",
  "application": "bake-tracker",
  "app_version": "0.6.0",
  "schema_version": "3.5",
  
  "files": [
    {
      "filename": "01_suppliers.json",
      "entity_type": "suppliers",
      "record_count": 5,
      "checksum_sha256": "abc123...",
      "import_order": 1,
      "dependencies": []
    },
    {
      "filename": "02_ingredients.json",
      "entity_type": "ingredients",
      "record_count": 343,
      "checksum_sha256": "def456...",
      "import_order": 2,
      "dependencies": []
    },
    {
      "filename": "03_products.json",
      "entity_type": "products",
      "record_count": 152,
      "checksum_sha256": "ghi789...",
      "import_order": 3,
      "dependencies": ["ingredients", "suppliers"]
    },
    {
      "filename": "04_purchases.json",
      "entity_type": "purchases",
      "record_count": 423,
      "checksum_sha256": "jkl012...",
      "import_order": 4,
      "dependencies": ["products", "suppliers"]
    }
    // ... etc
  ],
  
  "export_options": {
    "include_transactional": true,
    "include_events": true,
    "date_range": null
  }
}
```

---

### Entity File Format (Normalized Export)

**Example: `03_products.json`**

```json
{
  "file_version": "1.0",
  "entity_type": "products",
  "export_id": "550e8400-e29b-41d4-a716-446655440000",
  "exported_at": "2025-12-24T12:00:00Z",
  "record_count": 152,
  
  "schema": {
    "primary_key": "id",
    "slug_field": "slug",
    "foreign_keys": {
      "ingredient_id": {
        "references": "ingredients.id",
        "lookup_field": "ingredient_slug"
      },
      "preferred_supplier_id": {
        "references": "suppliers.id",
        "lookup_field": "supplier_name"
      }
    }
  },
  
  "records": [
    {
      "id": 42,
      "slug": "king_arthur_ap_flour_5lb",
      "ingredient_id": 15,
      "ingredient_slug": "all_purpose_flour",  // For FK resolution
      "brand": "King Arthur",
      "product_name": "Unbleached All-Purpose Flour",
      "package_size": 5.0,
      "package_unit": "lb",
      "package_unit_quantity": 5.0,
      "upc_code": "071012010103",
      "preferred_supplier_id": 3,
      "supplier_name": "Costco Waltham MA",  // For FK resolution
      "is_hidden": false,
      "notes": null,
      "created_at": "2024-01-15T10:00:00Z"
    }
    // ... more records
  ]
}
```

**Key Features:**
- Both `id` and `slug` for flexible matching
- FK fields include both `id` and lookup field (e.g., `ingredient_slug`, `supplier_name`)
- Schema metadata for import validation

---

### Denormalized View Format

**Example: `view_products.json`**

```json
{
  "export_type": "denormalized_view",
  "view_name": "products_complete",
  "view_version": "1.0",
  "exported_at": "2025-12-24T12:00:00Z",
  "record_count": 152,
  
  "documentation": {
    "purpose": "AI-assisted product augmentation (UPC codes, product names)",
    "editable_fields": ["brand", "product_name", "package_size", "package_unit", "package_unit_quantity", "upc_code", "notes"],
    "readonly_fields": ["product_id", "product_slug", "ingredient_name", "ingredient_slug", "ingredient_category", "preferred_supplier_name", "last_purchase_price", "last_purchase_date", "current_inventory_qty"],
    "import_instructions": "On import, only editable_fields are applied to Product table. Readonly fields provide context and are ignored during import."
  },
  
  "records": [
    {
      // Identity (match keys - DO NOT EDIT)
      "product_id": 42,
      "product_slug": "king_arthur_ap_flour_5lb",
      
      // Context (read-only - provides information for AI)
      "ingredient_name": "All-Purpose Flour",
      "ingredient_slug": "all_purpose_flour",
      "ingredient_category": "Flours & Starches",
      "preferred_supplier_name": "Costco Waltham MA",
      "last_purchase_price": 6.99,
      "last_purchase_date": "2024-11-15",
      "current_inventory_qty": 2.5,
      
      // Product fields (editable - AI can update these)
      "brand": "King Arthur",
      "product_name": "Unbleached All-Purpose Flour",
      "package_size": 5.0,
      "package_unit": "lb",
      "package_unit_quantity": 5.0,
      "upc_code": "071012010103",
      "notes": null
    }
    // ... more records
  ]
}
```

**Example: `view_inventory.json`**

```json
{
  "export_type": "denormalized_view",
  "view_name": "inventory_complete",
  "view_version": "1.0",
  "exported_at": "2025-12-24T12:00:00Z",
  "record_count": 87,
  
  "documentation": {
    "purpose": "Inventory quantity updates and price adjustments",
    "editable_fields": ["quantity", "addition_date", "location", "notes"],
    "readonly_fields": ["inventory_id", "product_id", "product_slug", "product_name", "ingredient_name", "ingredient_category", "purchase_date", "purchase_unit_price", "supplier_name"]
  },
  
  "records": [
    {
      // Identity
      "inventory_id": 101,
      
      // Context (read-only)
      "product_id": 42,
      "product_slug": "king_arthur_ap_flour_5lb",
      "product_name": "King Arthur Unbleached All-Purpose Flour",
      "ingredient_name": "All-Purpose Flour",
      "ingredient_category": "Flours & Starches",
      "purchase_date": "2024-12-01",
      "purchase_unit_price": 6.99,
      "supplier_name": "Costco Waltham MA",
      
      // Inventory fields (editable)
      "quantity": 2.5,
      "addition_date": "2024-12-01",
      "location": "Pantry Shelf 2",
      "notes": null
    }
  ]
}
```

**Example: `view_purchases.json`**

```json
{
  "export_type": "denormalized_view",
  "view_name": "purchases_complete",
  "view_version": "1.0",
  "exported_at": "2025-12-24T12:00:00Z",
  "record_count": 423,
  
  "documentation": {
    "purpose": "Purchase data augmentation (supplier info, dates, prices)",
    "editable_fields": ["supplier_name", "purchase_date", "unit_price", "quantity_purchased", "notes"],
    "readonly_fields": ["purchase_id", "product_id", "product_slug", "product_name", "ingredient_name", "inventory_quantity"]
  },
  
  "records": [
    {
      // Identity
      "purchase_id": 201,
      
      // Context (read-only)
      "product_id": 42,
      "product_slug": "king_arthur_ap_flour_5lb",
      "product_name": "King Arthur Unbleached All-Purpose Flour",
      "ingredient_name": "All-Purpose Flour",
      "inventory_quantity": 2.5,
      
      // Purchase fields (editable)
      "supplier_name": "Costco Waltham MA",
      "purchase_date": "2024-12-01",
      "unit_price": 6.99,
      "quantity_purchased": 2,
      "notes": null
    }
  ]
}
```

---

### Service Layer Architecture

#### New Services

```python
# src/services/coordinated_export_service.py

from pathlib import Path
from typing import Optional, List, Dict
import json
import hashlib
import zipfile
from datetime import datetime
from uuid import uuid4

from src.database import session_scope
from src.models import Supplier, Ingredient, Product, Purchase, InventoryItem
# ... other models


class ExportManifest:
    """Manifest for coordinated export set."""
    
    def __init__(self, export_id: str, output_dir: Path):
        self.export_id = export_id
        self.output_dir = output_dir
        self.files: List[Dict] = []
        self.exported_at = datetime.utcnow().isoformat() + "Z"
    
    def add_file(self, filename: str, entity_type: str, record_count: int, 
                 checksum: str, import_order: int, dependencies: List[str]):
        """Add file to manifest."""
        self.files.append({
            "filename": filename,
            "entity_type": entity_type,
            "record_count": record_count,
            "checksum_sha256": checksum,
            "import_order": import_order,
            "dependencies": dependencies
        })
    
    def save(self):
        """Write manifest to disk."""
        manifest_data = {
            "manifest_version": "1.0",
            "export_id": self.export_id,
            "exported_at": self.exported_at,
            "application": "bake-tracker",
            "app_version": "0.6.0",  # Get from config
            "schema_version": "3.5",  # Get from config
            "files": sorted(self.files, key=lambda f: f["import_order"]),
            "export_options": {
                "include_transactional": True,
                "include_events": True,
                "date_range": None
            }
        }
        
        manifest_path = self.output_dir / "manifest.json"
        with manifest_path.open('w') as f:
            json.dump(manifest_data, f, indent=2)


def export_complete_set(
    output_dir: Path,
    create_zip: bool = False,
    include_transactional: bool = True,
    include_events: bool = True
) -> ExportManifest:
    """
    Export complete database to coordinated file set.
    
    Args:
        output_dir: Directory for export files (will be created)
        create_zip: Create ZIP archive after export
        include_transactional: Include purchases, inventory, production runs
        include_events: Include events and related entities
        
    Returns:
        ExportManifest object with metadata
        
    File structure:
        output_dir/
        ├── manifest.json
        ├── 01_suppliers.json
        ├── 02_ingredients.json
        └── ...
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate export ID
    export_id = str(uuid4())
    manifest = ExportManifest(export_id, output_dir)
    
    with session_scope() as session:
        # Level 0: No dependencies
        _export_entity(session, Supplier, output_dir, manifest, 
                      import_order=1, dependencies=[])
        _export_entity(session, Ingredient, output_dir, manifest,
                      import_order=2, dependencies=[])
        
        # Level 1: Single dependency
        _export_entity(session, Product, output_dir, manifest,
                      import_order=3, dependencies=["ingredients", "suppliers"])
        
        # Level 2: Multiple dependencies
        if include_transactional:
            _export_entity(session, Purchase, output_dir, manifest,
                          import_order=4, dependencies=["products", "suppliers"])
            _export_entity(session, InventoryItem, output_dir, manifest,
                          import_order=5, dependencies=["products", "purchases"])
        
        # ... export other entities based on dependency order
    
    # Save manifest
    manifest.save()
    
    # Create ZIP if requested
    if create_zip:
        _create_zip_archive(output_dir)
    
    return manifest


def _export_entity(
    session, 
    model_class, 
    output_dir: Path, 
    manifest: ExportManifest,
    import_order: int,
    dependencies: List[str]
):
    """Export single entity type to JSON file."""
    
    # Determine filename
    entity_type = model_class.__tablename__
    filename = f"{import_order:02d}_{entity_type}.json"
    filepath = output_dir / filename
    
    # Query all records
    records = session.query(model_class).all()
    
    # Convert to dict with FK resolution fields
    records_data = []
    for record in records:
        record_dict = _model_to_dict_with_fk_lookups(record, session)
        records_data.append(record_dict)
    
    # Build file content
    file_content = {
        "file_version": "1.0",
        "entity_type": entity_type,
        "export_id": manifest.export_id,
        "exported_at": manifest.exported_at,
        "record_count": len(records_data),
        "schema": _get_schema_metadata(model_class),
        "records": records_data
    }
    
    # Write to file
    with filepath.open('w') as f:
        json.dump(file_content, f, indent=2)
    
    # Calculate checksum
    checksum = _calculate_file_checksum(filepath)
    
    # Add to manifest
    manifest.add_file(
        filename=filename,
        entity_type=entity_type,
        record_count=len(records_data),
        checksum=checksum,
        import_order=import_order,
        dependencies=dependencies
    )


def _model_to_dict_with_fk_lookups(record, session) -> Dict:
    """
    Convert SQLAlchemy model to dict with FK resolution fields.
    
    Example for Product:
        {
            "id": 42,
            "slug": "king_arthur_ap_flour_5lb",
            "ingredient_id": 15,
            "ingredient_slug": "all_purpose_flour",  # ← Added for FK resolution
            "preferred_supplier_id": 3,
            "supplier_name": "Costco Waltham MA",  # ← Added for FK resolution
            ...
        }
    """
    # Start with base fields
    result = {}
    for column in record.__table__.columns:
        value = getattr(record, column.name)
        # Handle datetime serialization
        if isinstance(value, datetime):
            value = value.isoformat() + "Z"
        result[column.name] = value
    
    # Add FK lookup fields
    # This is model-specific - could use reflection or explicit mapping
    if hasattr(record, 'ingredient_id') and record.ingredient_id:
        ingredient = session.query(Ingredient).get(record.ingredient_id)
        if ingredient:
            result['ingredient_slug'] = ingredient.slug
    
    if hasattr(record, 'preferred_supplier_id') and record.preferred_supplier_id:
        supplier = session.query(Supplier).get(record.preferred_supplier_id)
        if supplier:
            result['supplier_name'] = supplier.name
    
    # ... handle other FK relationships
    
    return result


def _get_schema_metadata(model_class) -> Dict:
    """Extract schema metadata for validation."""
    fk_metadata = {}
    
    # Inspect foreign keys
    for fk in model_class.__table__.foreign_keys:
        column_name = fk.parent.name
        target_table = fk.column.table.name
        
        # Determine lookup field (slug or name)
        lookup_field = None
        if target_table == "ingredients":
            lookup_field = "ingredient_slug"
        elif target_table == "suppliers":
            lookup_field = "supplier_name"
        # ... handle other FK relationships
        
        if lookup_field:
            fk_metadata[column_name] = {
                "references": f"{target_table}.id",
                "lookup_field": lookup_field
            }
    
    return {
        "primary_key": "id",
        "slug_field": "slug" if hasattr(model_class, 'slug') else None,
        "foreign_keys": fk_metadata
    }


def _calculate_file_checksum(filepath: Path) -> str:
    """Calculate SHA256 checksum of file."""
    sha256 = hashlib.sha256()
    with filepath.open('rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _create_zip_archive(export_dir: Path):
    """Create ZIP archive of export directory."""
    archive_name = f"{export_dir.name}.zip"
    archive_path = export_dir.parent / "archives" / archive_name
    archive_path.parent.mkdir(exist_ok=True)
    
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in export_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(export_dir.parent)
                zipf.write(file, arcname)
    
    print(f"✓ ZIP archive created: {archive_path}")
```

---

#### Denormalized View Export

```python
# src/services/denormalized_export_service.py

def export_view_products(output_path: Path, session: Optional[Session] = None):
    """
    Export denormalized products view.
    
    Includes product fields + ingredient context + supplier context + purchase history.
    """
    if session is not None:
        return _export_view_products_impl(output_path, session)
    
    with session_scope() as session:
        return _export_view_products_impl(output_path, session)


def _export_view_products_impl(output_path: Path, session: Session):
    """Implementation using provided session."""
    
    # Query products with joins
    products = session.query(Product).options(
        joinedload(Product.ingredient),
        joinedload(Product.preferred_supplier)
    ).all()
    
    records = []
    for product in products:
        # Get last purchase info
        last_purchase = session.query(Purchase).filter_by(
            product_id=product.id
        ).order_by(Purchase.purchase_date.desc()).first()
        
        # Get current inventory
        inventory_qty = session.query(func.sum(InventoryItem.quantity)).filter_by(
            product_id=product.id
        ).scalar() or 0
        
        record = {
            # Identity (match keys)
            "product_id": product.id,
            "product_slug": product.slug,
            
            # Context (read-only)
            "ingredient_name": product.ingredient.display_name,
            "ingredient_slug": product.ingredient.slug,
            "ingredient_category": product.ingredient.category,
            "preferred_supplier_name": product.preferred_supplier.name if product.preferred_supplier else None,
            "last_purchase_price": float(last_purchase.unit_price) if last_purchase else None,
            "last_purchase_date": last_purchase.purchase_date.isoformat() if last_purchase else None,
            "current_inventory_qty": float(inventory_qty),
            
            # Product fields (editable)
            "brand": product.brand,
            "product_name": product.product_name,
            "package_size": float(product.package_size),
            "package_unit": product.package_unit,
            "package_unit_quantity": float(product.package_unit_quantity),
            "upc_code": product.upc_code,
            "notes": product.notes
        }
        
        records.append(record)
    
    # Build view file
    view_data = {
        "export_type": "denormalized_view",
        "view_name": "products_complete",
        "view_version": "1.0",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "record_count": len(records),
        
        "documentation": {
            "purpose": "AI-assisted product augmentation (UPC codes, product names)",
            "editable_fields": ["brand", "product_name", "package_size", "package_unit", 
                               "package_unit_quantity", "upc_code", "notes"],
            "readonly_fields": ["product_id", "product_slug", "ingredient_name", 
                               "ingredient_slug", "ingredient_category", 
                               "preferred_supplier_name", "last_purchase_price", 
                               "last_purchase_date", "current_inventory_qty"]
        },
        
        "records": records
    }
    
    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w') as f:
        json.dump(view_data, f, indent=2)
    
    print(f"✓ Exported {len(records)} products to {output_path}")


def export_view_inventory(output_path: Path, session: Optional[Session] = None):
    """Export denormalized inventory view."""
    # Similar structure to export_view_products
    pass


def export_view_purchases(output_path: Path, session: Optional[Session] = None):
    """Export denormalized purchases view."""
    # Similar structure to export_view_products
    pass
```

---

#### Import Service with FK Resolution

```python
# src/services/coordinated_import_service.py

from enum import Enum
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import json

from src.database import session_scope
from src.models import Supplier, Ingredient, Product


class ImportMode(Enum):
    """Import modes for handling existing records."""
    MERGE = "merge"  # Update existing, add new
    SKIP_EXISTING = "skip_existing"  # Only add new, skip existing


class ImportResult:
    """Result of import operation."""
    
    def __init__(self):
        self.total_processed = 0
        self.imported = 0
        self.updated = 0
        self.skipped = 0
        self.errors: List[Dict] = []
        self.created_entities: Dict[str, List] = {
            "suppliers": [],
            "ingredients": [],
            "products": []
        }
    
    def __str__(self):
        lines = [
            f"Import complete:",
            f"  {self.total_processed} records processed",
            f"  {self.imported} imported",
            f"  {self.updated} updated",
            f"  {self.skipped} skipped"
        ]
        
        if self.created_entities["suppliers"]:
            lines.append(f"  {len(self.created_entities['suppliers'])} suppliers created")
        if self.created_entities["ingredients"]:
            lines.append(f"  {len(self.created_entities['ingredients'])} ingredients created")
        if self.created_entities["products"]:
            lines.append(f"  {len(self.created_entities['products'])} products created")
        
        if self.errors:
            lines.append(f"  {len(self.errors)} errors")
        
        return "\n".join(lines)


class FKResolutionError(Exception):
    """Raised when FK cannot be resolved."""
    
    def __init__(self, field: str, value: str, message: str):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(f"{field}='{value}': {message}")


def import_denormalized_view(
    input_path: Path,
    mode: ImportMode = ImportMode.MERGE,
    interactive: bool = False,
    skip_on_error: bool = False,
    dry_run: bool = False,
    session: Optional[Session] = None
) -> ImportResult:
    """
    Import denormalized view file.
    
    Args:
        input_path: Path to view file (e.g., view_products.json)
        mode: Import mode (merge or skip_existing)
        interactive: Prompt user to resolve FK errors (CLI only)
        skip_on_error: Skip records with FK errors instead of failing
        dry_run: Report changes without applying
        session: Optional database session
        
    Returns:
        ImportResult with statistics
    """
    # Load file
    with input_path.open() as f:
        data = json.load(f)
    
    # Validate file type
    if data.get("export_type") != "denormalized_view":
        raise ValueError(f"Expected denormalized_view, got {data.get('export_type')}")
    
    view_name = data.get("view_name")
    
    # Delegate to view-specific importer
    if view_name == "products_complete":
        return _import_products_view(data, mode, interactive, skip_on_error, dry_run, session)
    elif view_name == "inventory_complete":
        return _import_inventory_view(data, mode, interactive, skip_on_error, dry_run, session)
    elif view_name == "purchases_complete":
        return _import_purchases_view(data, mode, interactive, skip_on_error, dry_run, session)
    else:
        raise ValueError(f"Unknown view type: {view_name}")


def _import_products_view(
    data: Dict,
    mode: ImportMode,
    interactive: bool,
    skip_on_error: bool,
    dry_run: bool,
    session: Optional[Session]
) -> ImportResult:
    """Import products from denormalized view."""
    
    if session is not None:
        return _import_products_view_impl(data, mode, interactive, skip_on_error, dry_run, session)
    
    with session_scope() as session:
        return _import_products_view_impl(data, mode, interactive, skip_on_error, dry_run, session)


def _import_products_view_impl(
    data: Dict,
    mode: ImportMode,
    interactive: bool,
    skip_on_error: bool,
    dry_run: bool,
    session: Session
) -> ImportResult:
    """Implementation using provided session."""
    
    result = ImportResult()
    resolver = InteractiveFKResolver(session, interactive) if interactive else None
    skipped_records = []
    
    editable_fields = data["documentation"]["editable_fields"]
    
    for record in data["records"]:
        result.total_processed += 1
        
        try:
            # Find existing product by slug or ID
            product = None
            if "product_slug" in record:
                product = session.query(Product).filter_by(slug=record["product_slug"]).first()
            if not product and "product_id" in record:
                product = session.query(Product).get(record["product_id"])
            
            if product:
                # Existing product
                if mode == ImportMode.SKIP_EXISTING:
                    result.skipped += 1
                    continue
                
                # Merge mode: update editable fields
                if not dry_run:
                    for field in editable_fields:
                        if field in record and record[field] is not None:
                            setattr(product, field, record[field])
                
                result.updated += 1
            
            else:
                # New product - need to resolve FKs
                
                # Resolve ingredient_id
                ingredient_id = _resolve_ingredient_fk(
                    record, session, resolver, skip_on_error
                )
                
                if not ingredient_id:
                    # FK resolution failed
                    if skip_on_error:
                        skipped_records.append({
                            "record_index": result.total_processed,
                            "skip_reason": "Ingredient FK not resolved",
                            "record_data": record
                        })
                        result.skipped += 1
                        continue
                    else:
                        raise FKResolutionError(
                            "ingredient_slug",
                            record.get("ingredient_slug", "unknown"),
                            "Ingredient not found and could not be resolved"
                        )
                
                # Resolve supplier_id (optional)
                supplier_id = None
                if "preferred_supplier_name" in record and record["preferred_supplier_name"]:
                    supplier_id = _resolve_supplier_fk(
                        record, session, resolver, skip_on_error
                    )
                
                # Create new product
                if not dry_run:
                    new_product = Product(
                        ingredient_id=ingredient_id,
                        brand=record["brand"],
                        product_name=record.get("product_name"),
                        package_size=record["package_size"],
                        package_unit=record["package_unit"],
                        package_unit_quantity=record["package_unit_quantity"],
                        upc_code=record.get("upc_code"),
                        preferred_supplier_id=supplier_id,
                        notes=record.get("notes")
                    )
                    session.add(new_product)
                    session.flush()
                    
                    result.created_entities["products"].append(new_product.id)
                
                result.imported += 1
        
        except FKResolutionError as e:
            if skip_on_error:
                skipped_records.append({
                    "record_index": result.total_processed,
                    "skip_reason": str(e),
                    "fk_errors": [{
                        "field": e.field,
                        "value": e.value,
                        "error": e.message
                    }],
                    "record_data": record
                })
                result.skipped += 1
            else:
                raise
        
        except Exception as e:
            result.errors.append({
                "record_index": result.total_processed,
                "error": str(e),
                "record_data": record
            })
    
    # Log skipped records
    if skipped_records:
        _log_skipped_records(skipped_records, data)
    
    return result


def _resolve_ingredient_fk(
    record: Dict,
    session: Session,
    resolver: Optional['InteractiveFKResolver'],
    skip_on_error: bool
) -> Optional[int]:
    """
    Resolve ingredient FK from record.
    
    Returns:
        ingredient_id if resolved, None if failed
    """
    # Try slug-based lookup
    if "ingredient_slug" in record:
        ingredient = session.query(Ingredient).filter_by(
            slug=record["ingredient_slug"]
        ).first()
        
        if ingredient:
            return ingredient.id
    
    # FK not found - interactive resolution?
    if resolver:
        return resolver.resolve_ingredient(record["ingredient_slug"])
    
    return None


def _resolve_supplier_fk(
    record: Dict,
    session: Session,
    resolver: Optional['InteractiveFKResolver'],
    skip_on_error: bool
) -> Optional[int]:
    """Resolve supplier FK from record."""
    
    # Try name-based lookup
    if "preferred_supplier_name" in record:
        supplier = session.query(Supplier).filter_by(
            name=record["preferred_supplier_name"]
        ).first()
        
        if supplier:
            return supplier.id
    
    # FK not found - interactive resolution?
    if resolver:
        return resolver.resolve_supplier(record["preferred_supplier_name"])
    
    return None


def _log_skipped_records(skipped_records: List[Dict], original_data: Dict):
    """Write skipped records to log file."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_path = Path("docs/exports") / f"import_skipped_{timestamp}.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    log_data = {
        "skipped_at": datetime.utcnow().isoformat() + "Z",
        "source_file": original_data.get("view_name", "unknown"),
        "total_skipped": len(skipped_records),
        "records": skipped_records,
        "resolution_instructions": (
            "To retry these records:\n"
            "1. Edit this file or the original import file\n"
            "2. Fix FK references (create missing entities or update field values)\n"
            "3. Re-import with --mode merge"
        )
    }
    
    with log_path.open('w') as f:
        json.dump(log_data, f, indent=2)
    
    print(f"Skipped records logged to: {log_path}")
```

---

#### Interactive FK Resolution

```python
# src/services/interactive_fk_resolver.py

class InteractiveFKResolver:
    """
    Handle interactive FK resolution during import.
    
    Prompts user to create or map missing entities.
    """
    
    def __init__(self, session: Session, enabled: bool = True):
        self.session = session
        self.enabled = enabled
    
    def resolve_supplier(self, supplier_name: str) -> Optional[int]:
        """
        Resolve missing supplier interactively.
        
        Returns:
            supplier_id if resolved, None if skipped
        """
        if not self.enabled:
            return None
        
        print(f"\n[FK Resolution] Supplier not found: '{supplier_name}'")
        print("Options:")
        print("  1. Create new supplier")
        print("  2. Map to existing supplier")
        print("  3. Skip")
        
        choice = input("Choice [1/2/3]: ").strip()
        
        if choice == "1":
            return self._create_supplier_interactive(supplier_name)
        elif choice == "2":
            return self._map_supplier_interactive(supplier_name)
        else:
            print("Skipping...")
            return None
    
    def _create_supplier_interactive(self, name: str) -> int:
        """Prompt for supplier details and create."""
        
        print(f"\nCreating new Supplier: {name}")
        city = input("  City: ").strip() or "Unknown"
        state = input("  State: ").strip() or "XX"
        zip_code = input("  Zip: ").strip() or "00000"
        
        supplier = Supplier(
            name=name,
            city=city,
            state=state,
            zip=zip_code
        )
        
        # Validate unique constraint
        existing = self.session.query(Supplier).filter_by(name=name).first()
        if existing:
            print(f"✗ Supplier '{name}' already exists (id={existing.id})")
            return existing.id
        
        self.session.add(supplier)
        self.session.flush()
        
        print(f"✓ Supplier created (id={supplier.id})")
        return supplier.id
    
    def _map_supplier_interactive(self, name: str) -> Optional[int]:
        """Show existing suppliers and prompt for mapping."""
        
        # Fuzzy search
        suppliers = self.session.query(Supplier).filter(
            Supplier.name.ilike(f"%{name}%")
        ).limit(10).all()
        
        if not suppliers:
            # Fallback to all suppliers
            suppliers = self.session.query(Supplier).limit(20).all()
        
        print(f"\nFound {len(suppliers)} existing suppliers:")
        for i, s in enumerate(suppliers, 1):
            print(f"  {i}. {s.name} ({s.city}, {s.state})")
        print("  0. Create new supplier instead")
        
        choice = input(f"Select supplier [1-{len(suppliers)}/0]: ").strip()
        
        if choice == "0":
            return self._create_supplier_interactive(name)
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(suppliers):
                selected = suppliers[idx]
                print(f"✓ Mapped to supplier_id={selected.id} ({selected.name})")
                return selected.id
        except ValueError:
            pass
        
        print("Invalid selection, skipping...")
        return None
    
    def resolve_ingredient(self, ingredient_slug: str) -> Optional[int]:
        """Resolve missing ingredient interactively."""
        
        if not self.enabled:
            return None
        
        print(f"\n[FK Resolution] Ingredient not found: '{ingredient_slug}'")
        print("Options:")
        print("  1. Create new ingredient")
        print("  2. Map to existing ingredient")
        print("  3. Skip")
        
        choice = input("Choice [1/2/3]: ").strip()
        
        if choice == "1":
            return self._create_ingredient_interactive(ingredient_slug)
        elif choice == "2":
            return self._map_ingredient_interactive(ingredient_slug)
        else:
            print("Skipping...")
            return None
    
    def _create_ingredient_interactive(self, slug: str) -> int:
        """Prompt for ingredient details and create."""
        
        print(f"\nCreating new Ingredient: {slug}")
        display_name = input("  Display Name: ").strip()
        
        # Show category options
        categories = [
            "Flours & Starches", "Sugars & Sweeteners", "Dairy & Eggs",
            "Chocolate & Cocoa", "Nuts & Seeds", "Fruits", "Spices & Extracts",
            "Leavening Agents", "Fats & Oils", "Liquids", "Misc Ingredients", "Packaging"
        ]
        print("\n  Categories:")
        for i, cat in enumerate(categories, 1):
            print(f"    {i}. {cat}")
        
        cat_choice = input(f"  Select category [1-{len(categories)}]: ").strip()
        try:
            cat_idx = int(cat_choice) - 1
            if 0 <= cat_idx < len(categories):
                category = categories[cat_idx]
            else:
                category = "Misc Ingredients"
        except ValueError:
            category = "Misc Ingredients"
        
        ingredient = Ingredient(
            slug=slug,
            display_name=display_name or slug.replace("_", " ").title(),
            category=category
        )
        
        # Validate unique constraint
        existing = self.session.query(Ingredient).filter_by(slug=slug).first()
        if existing:
            print(f"✗ Ingredient '{slug}' already exists (id={existing.id})")
            return existing.id
        
        self.session.add(ingredient)
        self.session.flush()
        
        print(f"✓ Ingredient created (id={ingredient.id})")
        return ingredient.id
    
    def _map_ingredient_interactive(self, slug: str) -> Optional[int]:
        """Show existing ingredients and prompt for mapping."""
        
        # Fuzzy search on slug and display_name
        search_term = slug.replace("_", " ")
        ingredients = self.session.query(Ingredient).filter(
            or_(
                Ingredient.slug.ilike(f"%{slug}%"),
                Ingredient.display_name.ilike(f"%{search_term}%")
            )
        ).limit(10).all()
        
        if not ingredients:
            print("No similar ingredients found.")
            print("  1. Create new ingredient")
            print("  2. Skip")
            choice = input("Choice [1/2]: ").strip()
            if choice == "1":
                return self._create_ingredient_interactive(slug)
            return None
        
        print(f"\nFound {len(ingredients)} similar ingredients:")
        for i, ing in enumerate(ingredients, 1):
            print(f"  {i}. {ing.display_name} ({ing.slug}) - {ing.category}")
        print("  0. Create new ingredient instead")
        
        choice = input(f"Select ingredient [1-{len(ingredients)}/0]: ").strip()
        
        if choice == "0":
            return self._create_ingredient_interactive(slug)
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ingredients):
                selected = ingredients[idx]
                print(f"✓ Mapped to ingredient_id={selected.id} ({selected.display_name})")
                return selected.id
        except ValueError:
            pass
        
        print("Invalid selection, skipping...")
        return None
    
    def resolve_product(self, record: Dict, ingredient_id: int) -> Optional[int]:
        """Resolve missing product interactively."""
        
        if not self.enabled:
            return None
        
        product_info = f"{record.get('brand', 'Unknown')} {record.get('product_name', 'Unknown Product')}"
        print(f"\n[FK Resolution] Product not found: '{product_info}'")
        print("Options:")
        print("  1. Create new product")
        print("  2. Map to existing product")
        print("  3. Skip")
        
        choice = input("Choice [1/2/3]: ").strip()
        
        if choice == "1":
            return self._create_product_interactive(record, ingredient_id)
        elif choice == "2":
            return self._map_product_interactive(record, ingredient_id)
        else:
            print("Skipping...")
            return None
    
    def _create_product_interactive(self, record: Dict, ingredient_id: int) -> int:
        """Create product from record data."""
        
        print(f"\nCreating new Product:")
        print(f"  Ingredient: {ingredient_id}")
        print(f"  Brand: {record.get('brand')}")
        print(f"  Product Name: {record.get('product_name')}")
        print(f"  Package: {record.get('package_size')} {record.get('package_unit')}")
        
        confirm = input("Create this product? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("Skipping...")
            return None
        
        product = Product(
            ingredient_id=ingredient_id,
            brand=record["brand"],
            product_name=record.get("product_name"),
            package_size=record["package_size"],
            package_unit=record["package_unit"],
            package_unit_quantity=record["package_unit_quantity"],
            upc_code=record.get("upc_code"),
            notes=record.get("notes")
        )
        
        self.session.add(product)
        self.session.flush()
        
        print(f"✓ Product created (id={product.id})")
        return product.id
    
    def _map_product_interactive(self, record: Dict, ingredient_id: int) -> Optional[int]:
        """Show existing products for ingredient and prompt for mapping."""
        
        products = self.session.query(Product).filter_by(
            ingredient_id=ingredient_id
        ).limit(20).all()
        
        if not products:
            print("No products found for this ingredient.")
            return self._create_product_interactive(record, ingredient_id)
        
        print(f"\nFound {len(products)} products for this ingredient:")
        for i, p in enumerate(products, 1):
            print(f"  {i}. {p.brand} {p.product_name or ''} ({p.package_size} {p.package_unit})")
        print("  0. Create new product instead")
        
        choice = input(f"Select product [1-{len(products)}/0]: ").strip()
        
        if choice == "0":
            return self._create_product_interactive(record, ingredient_id)
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(products):
                selected = products[idx]
                print(f"✓ Mapped to product_id={selected.id}")
                return selected.id
        except ValueError:
            pass
        
        print("Invalid selection, skipping...")
        return None
```

---

## UI Implementation

### Import View Dialog

```python
# src/ui/dialogs/import_view_dialog.py

import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

from src.services.coordinated_import_service import (
    import_denormalized_view,
    ImportMode,
    ImportResult,
    FKResolutionError
)
from src.services.interactive_fk_resolver import InteractiveFKResolver
from src.database import session_scope


class ImportViewDialog(ctk.CTkToplevel):
    """
    Dialog for importing denormalized view files with interactive FK resolution.
    
    UI default: Interactive mode (prompt for missing FKs)
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Import View")
        self.geometry("600x400")
        
        self.selected_file: Optional[Path] = None
        self.import_mode = ImportMode.MERGE
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configure dialog layout."""
        
        # File selection
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(file_frame, text="View File:").pack(side="left", padx=5)
        
        self.file_entry = ctk.CTkEntry(file_frame, width=300)
        self.file_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(
            file_frame,
            text="Browse...",
            command=self._browse_file,
            width=100
        ).pack(side="left", padx=5)
        
        # Import mode
        mode_frame = ctk.CTkFrame(self)
        mode_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(mode_frame, text="Import Mode:").pack(side="left", padx=5)
        
        self.mode_var = ctk.StringVar(value="merge")
        ctk.CTkRadioButton(
            mode_frame,
            text="Merge (update existing, add new)",
            variable=self.mode_var,
            value="merge"
        ).pack(side="left", padx=10)
        
        ctk.CTkRadioButton(
            mode_frame,
            text="Skip Existing (only add new)",
            variable=self.mode_var,
            value="skip_existing"
        ).pack(side="left", padx=10)
        
        # Status area
        self.status_text = ctk.CTkTextbox(self, height=200)
        self.status_text.pack(fill="both", expand=True, padx=20, pady=10)
        self.status_text.insert("1.0", "Select a view file to import...")
        self.status_text.configure(state="disabled")
        
        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Import",
            command=self._start_import
        ).pack(side="right", padx=5)
    
    def _browse_file(self):
        """Open file chooser for view file."""
        
        filename = filedialog.askopenfilename(
            title="Select View File",
            initialdir="docs/exports/ai_augmentation",
            filetypes=[
                ("View Files", "view_*.json"),
                ("JSON Files", "*.json"),
                ("All Files", "*.*")
            ]
        )
        
        if filename:
            self.selected_file = Path(filename)
            self.file_entry.delete(0, 'end')
            self.file_entry.insert(0, str(self.selected_file))
            
            # Validate file
            self._validate_file()
    
    def _validate_file(self):
        """Validate selected file and show preview."""
        
        if not self.selected_file or not self.selected_file.exists():
            self._update_status("Error: File not found", error=True)
            return
        
        try:
            import json
            with self.selected_file.open() as f:
                data = json.load(f)
            
            # Check file type
            if data.get("export_type") != "denormalized_view":
                self._update_status(
                    f"Error: Not a denormalized view file\n"
                    f"Expected export_type='denormalized_view', got '{data.get('export_type')}'",
                    error=True
                )
                return
            
            # Show preview
            view_name = data.get("view_name", "unknown")
            record_count = data.get("record_count", 0)
            exported_at = data.get("exported_at", "unknown")
            
            preview = f"View: {view_name}\n"
            preview += f"Records: {record_count}\n"
            preview += f"Exported: {exported_at}\n\n"
            preview += "Click Import to proceed with FK resolution..."
            
            self._update_status(preview)
        
        except json.JSONDecodeError as e:
            self._update_status(f"Error: Invalid JSON\n{str(e)}", error=True)
        except Exception as e:
            self._update_status(f"Error: {str(e)}", error=True)
    
    def _start_import(self):
        """Start import process with interactive FK resolution."""
        
        if not self.selected_file:
            messagebox.showerror("Error", "Please select a file first")
            return
        
        # Get import mode
        mode = ImportMode.MERGE if self.mode_var.get() == "merge" else ImportMode.SKIP_EXISTING
        
        # Start import in background thread
        self._update_status("Starting import...\n")
        
        try:
            with session_scope() as session:
                # Create UI-based FK resolver
                resolver = UIFKResolver(self, session)
                
                # Import with interactive resolution
                result = import_denormalized_view(
                    input_path=self.selected_file,
                    mode=mode,
                    interactive=True,  # UI always interactive
                    skip_on_error=False,
                    dry_run=False,
                    session=session
                )
                
                # Show results
                self._show_results(result)
        
        except FKResolutionError as e:
            messagebox.showerror("Import Failed", f"FK Resolution Error:\n{str(e)}")
            self._update_status(f"Import failed: {str(e)}\n", error=True)
        
        except Exception as e:
            messagebox.showerror("Import Failed", str(e))
            self._update_status(f"Import failed: {str(e)}\n", error=True)
    
    def _show_results(self, result: ImportResult):
        """Show import results dialog."""
        
        result_text = str(result)
        self._update_status(result_text)
        
        messagebox.showinfo("Import Complete", result_text)
        
        # Close dialog
        self.destroy()
    
    def _update_status(self, text: str, error: bool = False):
        """Update status text area."""
        
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", text)
        
        if error:
            self.status_text.tag_add("error", "1.0", "end")
            self.status_text.tag_config("error", foreground="red")
        
        self.status_text.configure(state="disabled")


class UIFKResolver(InteractiveFKResolver):
    """
    UI-based FK resolver using dialogs instead of CLI prompts.
    
    Subclasses InteractiveFKResolver to provide graphical resolution.
    """
    
    def __init__(self, parent_dialog, session):
        super().__init__(session, enabled=True)
        self.parent = parent_dialog
    
    def resolve_supplier(self, supplier_name: str) -> Optional[int]:
        """Show supplier resolution dialog."""
        
        dialog = SupplierResolutionDialog(self.parent, supplier_name, self.session)
        self.parent.wait_window(dialog)
        
        return dialog.resolved_supplier_id
    
    def resolve_ingredient(self, ingredient_slug: str) -> Optional[int]:
        """Show ingredient resolution dialog."""
        
        dialog = IngredientResolutionDialog(self.parent, ingredient_slug, self.session)
        self.parent.wait_window(dialog)
        
        return dialog.resolved_ingredient_id
    
    def resolve_product(self, record: Dict, ingredient_id: int) -> Optional[int]:
        """Show product resolution dialog."""
        
        dialog = ProductResolutionDialog(self.parent, record, ingredient_id, self.session)
        self.parent.wait_window(dialog)
        
        return dialog.resolved_product_id


class SupplierResolutionDialog(ctk.CTkToplevel):
    """
    Dialog for resolving missing supplier FK.
    
    Options: Create new, map to existing, skip
    """
    
    def __init__(self, parent, supplier_name: str, session):
        super().__init__(parent)
        
        self.supplier_name = supplier_name
        self.session = session
        self.resolved_supplier_id: Optional[int] = None
        
        self.title("Resolve Supplier")
        self.geometry("500x400")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configure dialog layout."""
        
        # Header
        header = ctk.CTkLabel(
            self,
            text=f"Supplier not found: '{self.supplier_name}'",
            font=("", 14, "bold")
        )
        header.pack(pady=10)
        
        # Options frame
        options_frame = ctk.CTkFrame(self)
        options_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.option_var = ctk.StringVar(value="create")
        
        # Option 1: Create new
        create_radio = ctk.CTkRadioButton(
            options_frame,
            text="Create new supplier",
            variable=self.option_var,
            value="create",
            command=self._on_option_changed
        )
        create_radio.pack(anchor="w", pady=5)
        
        self.create_frame = ctk.CTkFrame(options_frame)
        self.create_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(self.create_frame, text="City:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.city_entry = ctk.CTkEntry(self.create_frame, width=200)
        self.city_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ctk.CTkLabel(self.create_frame, text="State:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.state_entry = ctk.CTkEntry(self.create_frame, width=200)
        self.state_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        ctk.CTkLabel(self.create_frame, text="Zip:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.zip_entry = ctk.CTkEntry(self.create_frame, width=200)
        self.zip_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        
        self.create_frame.columnconfigure(1, weight=1)
        
        # Option 2: Map to existing
        map_radio = ctk.CTkRadioButton(
            options_frame,
            text="Map to existing supplier",
            variable=self.option_var,
            value="map",
            command=self._on_option_changed
        )
        map_radio.pack(anchor="w", pady=5)
        
        self.map_frame = ctk.CTkFrame(options_frame)
        self.map_frame.pack(fill="x", padx=20, pady=5)
        
        # Load existing suppliers
        suppliers = self.session.query(Supplier).order_by(Supplier.name).limit(20).all()
        supplier_options = [f"{s.name} ({s.city}, {s.state})" for s in suppliers]
        self.supplier_map = {opt: s.id for opt, s in zip(supplier_options, suppliers)}
        
        self.supplier_combo = ctk.CTkComboBox(
            self.map_frame,
            values=supplier_options,
            width=300
        )
        self.supplier_combo.pack(padx=5, pady=5)
        self.supplier_combo.set("Select supplier...")
        
        # Option 3: Skip
        skip_radio = ctk.CTkRadioButton(
            options_frame,
            text="Skip records with this supplier",
            variable=self.option_var,
            value="skip",
            command=self._on_option_changed
        )
        skip_radio.pack(anchor="w", pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Confirm",
            command=self._on_confirm
        ).pack(side="right", padx=5)
        
        # Initial state
        self._on_option_changed()
    
    def _on_option_changed(self):
        """Enable/disable frames based on selection."""
        
        option = self.option_var.get()
        
        if option == "create":
            self._enable_frame(self.create_frame)
            self._disable_frame(self.map_frame)
        elif option == "map":
            self._disable_frame(self.create_frame)
            self._enable_frame(self.map_frame)
        else:  # skip
            self._disable_frame(self.create_frame)
            self._disable_frame(self.map_frame)
    
    def _enable_frame(self, frame):
        """Enable all widgets in frame."""
        for child in frame.winfo_children():
            child.configure(state="normal")
    
    def _disable_frame(self, frame):
        """Disable all widgets in frame."""
        for child in frame.winfo_children():
            if isinstance(child, (ctk.CTkEntry, ctk.CTkComboBox)):
                child.configure(state="disabled")
    
    def _on_confirm(self):
        """Handle confirm button."""
        
        option = self.option_var.get()
        
        if option == "create":
            # Create new supplier
            city = self.city_entry.get().strip() or "Unknown"
            state = self.state_entry.get().strip() or "XX"
            zip_code = self.zip_entry.get().strip() or "00000"
            
            supplier = Supplier(
                name=self.supplier_name,
                city=city,
                state=state,
                zip=zip_code
            )
            
            self.session.add(supplier)
            self.session.flush()
            
            self.resolved_supplier_id = supplier.id
        
        elif option == "map":
            # Map to existing
            selected = self.supplier_combo.get()
            if selected == "Select supplier...":
                messagebox.showerror("Error", "Please select a supplier")
                return
            
            self.resolved_supplier_id = self.supplier_map.get(selected)
        
        else:  # skip
            self.resolved_supplier_id = None
        
        self.destroy()
    
    def _on_cancel(self):
        """Handle cancel button."""
        self.resolved_supplier_id = None
        self.destroy()


# Similar dialogs for Ingredient and Product resolution...
```

---

## Testing Strategy

### Unit Tests

**Export Service Tests:**
```python
# tests/services/test_coordinated_export.py

def test_export_complete_set_creates_manifest(session, sample_data):
    """Verify manifest created with correct metadata."""
    
def test_export_entity_includes_fk_lookups(session, products):
    """Verify FK resolution fields included in entity export."""
    
def test_export_calculates_checksums(session, sample_data):
    """Verify SHA256 checksums calculated for each file."""
    
def test_denormalized_view_products_includes_context(session, products):
    """Verify products view includes ingredient/supplier context."""
    
def test_denormalized_view_marks_readonly_fields(session):
    """Verify documentation specifies editable vs readonly fields."""
```

**Import Service Tests:**
```python
# tests/services/test_coordinated_import.py

def test_import_resolves_fk_by_slug(session, export_data):
    """Verify FK resolution via slug when ID doesn't match."""
    
def test_import_merge_updates_existing(session, export_data):
    """Verify merge mode updates existing records."""
    
def test_import_skip_existing_skips(session, export_data):
    """Verify skip_existing mode doesn't update existing records."""
    
def test_import_denormalized_view_extracts_normalized_updates(session):
    """Verify denormalized view import only updates editable fields."""
    
def test_import_skip_on_error_logs_skipped_records(session):
    """Verify skipped records logged to file."""
```

**FK Resolution Tests:**
```python
# tests/services/test_fk_resolution.py

def test_resolve_supplier_creates_new(session):
    """Verify interactive resolution creates new supplier."""
    
def test_resolve_ingredient_maps_existing(session):
    """Verify interactive resolution maps to existing ingredient."""
    
def test_resolve_product_validates_referential_integrity(session):
    """Verify product creation validates ingredient_id exists."""
    
def test_resolution_respects_dependency_chain(session):
    """Verify Product requires Ingredient resolved first."""
```

### Integration Tests

**Round-Trip Tests:**
```python
# tests/integration/test_export_import_roundtrip.py

def test_export_import_roundtrip_identical(session, sample_data):
    """
    Verify export → import produces identical database state.
    
    1. Export complete set
    2. Clear database
    3. Import from export
    4. Verify all records identical
    """
    
def test_denormalized_view_roundtrip_preserves_context(session):
    """
    Verify denormalized view export → import preserves data.
    
    1. Export view_products
    2. Modify editable fields
    3. Import view
    4. Verify updates applied, context ignored
    """
```

**AI Workflow Tests:**
```python
# tests/integration/test_ai_augmentation_workflow.py

def test_product_upc_enrichment_workflow(session):
    """
    Simulate AI UPC enrichment workflow.
    
    1. Export view_products (with NULL upc_code)
    2. Fill in upc_code values (simulating AI)
    3. Import with merge mode
    4. Verify upc_code updated, other fields unchanged
    """
    
def test_purchase_creation_with_new_supplier(session):
    """
    Simulate purchase import with new supplier (interactive resolution).
    
    1. Export view_purchases
    2. Add purchase with new supplier "Wilson's Farm"
    3. Import with interactive=True (mock prompts)
    4. Verify supplier created, purchase imported
    """
```

---

## Acceptance Criteria

### Must Have (MVP)

**Export:**
1. ✅ Export complete coordinated set with manifest (checksums, dependencies, import order)
2. ✅ Export individual entity files with FK resolution fields (id + slug/name)
3. ✅ Export denormalized views: view_products, view_inventory, view_purchases
4. ✅ ZIP archive option for coordinated exports
5. ✅ Configurable output directory (default docs/exports/)
6. ✅ Standard persistent filenames for denormalized views

**Import:**
7. ✅ Import coordinated set with manifest validation
8. ✅ FK resolution via slug/name when IDs don't match
9. ✅ Import modes: merge (update existing, add new) and skip_existing (only new)
10. ✅ Import denormalized views with auto-normalization (extract editable fields only)
11. ✅ Dry-run mode (CLI only, report changes without applying)

**Interactive FK Resolution:**
12. ✅ CLI: Fail-fast default, `--interactive` flag for resolution
13. ✅ UI: Interactive resolution default (wizard)
14. ✅ Create new entity during import (Suppliers, Ingredients, Products)
15. ✅ Map to existing entity (fuzzy search)
16. ✅ Skip records with unresolved FKs
17. ✅ Referential integrity validation (e.g., Product requires Ingredient)
18. ✅ Dependency chain handling (resolve Ingredient before Product)

**Skip-on-Error:**
19. ✅ `--skip-on-error` flag skips bad records, imports valid ones
20. ✅ Log skipped records to `import_skipped_{timestamp}.json`
21. ✅ Report: X imported, Y skipped

**CLI Interface:**
22. ✅ `export_complete` command with --output, --zip flags
23. ✅ `export_view` command for denormalized views (products, inventory, purchases)
24. ✅ `import_view` command with --mode, --interactive, --skip-on-error, --dry-run flags
25. ✅ `validate_export` command for manifest verification

**UI Integration:**
26. ✅ File → Import → Import View menu item
27. ✅ Import dialog with file chooser, mode selection
28. ✅ Interactive FK resolution wizard (default UI behavior)
29. ✅ Results summary dialog

**Testing:**
30. ✅ Round-trip test: export → import → verify identical
31. ✅ Denormalized view test: export → edit → import → verify updates
32. ✅ FK resolution test: Import with missing FKs → interactive resolution works
33. ✅ Skip-on-error test: Import with errors → valid records imported, skipped logged

### Should Have (Post-MVP)

1. ⬜ Auto-create modes (e.g., `--auto-create suppliers`)
2. ⬜ Additional denormalized views (recipes, events, finished goods)
3. ⬜ Schema transformation utilities (convert old exports to new format)
4. ⬜ Progress bars for large imports (>1000 records)
5. ⬜ Import preview with change summary before applying

### Could Have (Future)

1. ⬜ Voice interaction file templates
2. ⬜ Barcode scan file templates
3. ⬜ CSV export/import (in addition to JSON)
4. ⬜ Replace mode (delete all + import)
5. ⬜ Partial entity updates (e.g., just quantity changes)

---

## Risks and Mitigation

### Risk: FK Resolution Complexity

**Risk:** Dependency chains (Product → Ingredient → Category) make interactive resolution complex.

**Mitigation:**
- Resolve dependencies in order (Ingredient before Product)
- Clear error messages when dependency missing
- Fallback to skip if resolution fails
- Extensive testing of resolution scenarios

### Risk: Large File Performance

**Risk:** Exporting/importing thousands of records could be slow.

**Mitigation:**
- Streaming JSON write for large exports
- Batch database operations (100-500 records per commit)
- Progress indicators for CLI
- Limit denormalized views to active records (not historical)

### Risk: Data Integrity During Import

**Risk:** Partial import failure could leave database in inconsistent state.

**Mitigation:**
- Validation phase before any database writes
- Transaction-based import (all-or-nothing per file)
- Dry-run mode to preview changes
- Comprehensive testing with edge cases

### Risk: UI Freeze During Import

**Risk:** Long-running imports could freeze UI.

**Mitigation:**
- Background thread for import operations
- Progress dialog with cancel option
- Disable import button during operation
- Timeout for interactive prompts

---

## Migration Strategy

No database schema changes required.

**Deployment:**
1. Add new services: `coordinated_export_service`, `denormalized_export_service`, `coordinated_import_service`, `interactive_fk_resolver`
2. Add CLI commands to `src/cli/main.py`
3. Add UI menu item: File → Import → Import View
4. Add UI dialogs: `ImportViewDialog`, resolution dialogs
5. Update documentation: User guide for AI augmentation workflows

**Testing:**
1. Export existing database to coordinated set
2. Import coordinated set to verify round-trip
3. Export denormalized views
4. Manually edit views (simulate AI)
5. Import views with interactive resolution

**Rollback:**
No schema changes, so rollback is simply reverting code changes.

---

## Future Enhancements

### Feature 032: Additional Denormalized Views
- `view_recipes.json` - Recipes with ingredient details for cost calculation
- `view_events.json` - Events with packages, recipients for planning
- `view_finished_goods.json` - Finished goods with composition details

### Feature 033: Auto-Create Modes
- `--auto-create suppliers` - Automatically create missing suppliers
- `--auto-create products` - Automatically create missing products
- Risk assessment and confirmation prompts

### Feature 034: Schema Transformation
- Utilities to convert old export formats to new coordinated format
- Version migration scripts
- Backward compatibility for legacy exports

---

## References

### Existing Features
- **Feature 020:** Enhanced Data Import (catalog import foundation)
- **Feature 027:** Product Catalog Management (Supplier, Product entities)
- **Feature 028:** Purchase Tracking (Purchase entity, FK relationships)

### Architecture Documents
- **Constitution Principle I:** User-Centric Design (interactive resolution optimizes workflow)
- **Constitution Principle II:** Data Integrity (referential integrity validation)
- **Constitution Principle VI:** Export/Reset/Import (coordinated export supports schema migrations)

### Code References
- `src/cli/main.py` - CLI command structure
- `src/services/import_service.py` - Current import logic (unified import)
- `src/services/export_service.py` - Current export logic (monolithic export)
- `src/database.py` - session_scope context manager

---

**Version:** 1.0  
**Last Updated:** 2025-12-24  
**Dependencies:** Features 027 (Product Catalog), 028 (Purchase Tracking)  
**Next Steps:** Implementation via Spec Kitty workflow
