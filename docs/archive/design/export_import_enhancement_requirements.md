# Technical Requirements: Enhanced Export/Import Mechanism

## Overview

This document specifies requirements for a robust export/import system that:
1. Exports data as a coordinated set of files that can fully rebuild the database
2. Supports AI-assisted augmentation workflows (price enrichment, purchase record creation)
3. Provides denormalized views optimized for external AI processing

## Current State Analysis

### Existing Export Capabilities

| Export Function | Format | Notes |
|-----------------|--------|-------|
| `export_all_to_json()` | v3.5 monolithic | Single file with all entities |
| `export_ingredients_to_json()` | v1.0 | Standalone catalog |
| `export_recipes_to_json()` | v1.0 | Includes embedded ingredients |
| Individual entity exports | v3.0+ | Return List[Dict], not files |

### Current File Landscape

| File | Purpose | Can Rebuild DB? |
|------|---------|-----------------|
| `sample_data.json` | Complete v3.5 export | Yes, but monolithic |
| `ingredients_catalog.json` | Ingredient definitions | Partial - no FKs |
| `products_catalog.json` | Product definitions | Partial - needs ingredients |
| `recipes_catalog.json` | Recipe definitions | Partial - needs ingredients |
| `inventory.json` | Purchases + inventory | Partial - needs products |

### Gap Analysis

1. **No coordinated export set** - Files exported independently, may have version drift
2. **No manifest file** - No way to verify set completeness or import order
3. **No validation checksums** - Can't detect corruption or partial exports
4. **No AI-friendly denormalized views** - FKs require multi-file lookups
5. **Missing entity exports** - No standalone exports for suppliers, events, finished_goods, etc.

---

## Requirement 1: Coordinated Export Set for DB Rebuild

### 1.1 Export Manifest

Create a manifest file that coordinates the export set:

```json
{
  "manifest_version": "1.0",
  "export_id": "uuid-v4",
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
    }
    // ... etc
  ],
  "import_modes_supported": ["replace", "merge"],
  "export_options": {
    "include_transactional": true,
    "include_events": true,
    "date_range": null
  }
}
```

### 1.2 Entity Export Files

Export each entity type to a separate file with consistent structure:

| File | Entity | Dependencies | Import Order |
|------|--------|--------------|--------------|
| `01_suppliers.json` | Supplier | None | 1 |
| `02_ingredients.json` | Ingredient | None | 2 |
| `03_products.json` | Product | ingredients, suppliers | 3 |
| `04_purchases.json` | Purchase | products, suppliers | 4 |
| `05_inventory_items.json` | InventoryItem | products, purchases | 5 |
| `06_recipes.json` | Recipe + RecipeIngredient + RecipeComponent | ingredients | 6 |
| `07_finished_units.json` | FinishedUnit | recipes | 7 |
| `08_finished_goods.json` | FinishedGood | None | 8 |
| `09_compositions.json` | Composition + CompositionAssignment | finished_goods, finished_units, packages, products | 9 |
| `10_packages.json` | Package + PackageFinishedGood | finished_goods | 10 |
| `11_recipients.json` | Recipient | None | 11 |
| `12_events.json` | Event + EventRecipientPackage + Targets | recipients, packages | 12 |
| `13_production_runs.json` | ProductionRun + Consumptions + Losses | events, recipes, inventory_items | 13 |
| `14_assembly_runs.json` | AssemblyRun + Consumptions | events, finished_goods | 14 |

### 1.3 File Format Requirements

Each entity file must include:

```json
{
  "file_version": "1.0",
  "entity_type": "products",
  "export_id": "uuid-matching-manifest",
  "exported_at": "2025-12-24T12:00:00Z",
  "record_count": 152,
  "schema": {
    "primary_key": "id",
    "slug_field": "slug",
    "foreign_keys": {
      "ingredient_id": {"references": "ingredients.id", "lookup_field": "ingredient_slug"},
      "preferred_supplier_id": {"references": "suppliers.id", "lookup_field": "supplier_name"}
    }
  },
  "records": [
    // ... entity records with both ID and slug/name for FK resolution
  ]
}
```

### 1.4 FK Resolution Strategy

For portability, include both ID-based and slug/name-based FK references:

```json
{
  "id": 42,
  "ingredient_id": 15,
  "ingredient_slug": "all_purpose_flour",  // For slug-based resolution
  "preferred_supplier_id": 3,
  "supplier_name": "Costco"  // For name-based resolution
}
```

### 1.5 Import Service Requirements

- **Validation phase**: Verify manifest, checksums, and dependency order before importing
- **Dry-run mode**: Report what would be imported without modifying DB
- **Transaction safety**: All-or-nothing import within manifest scope
- **Conflict resolution**: Support `replace`, `merge`, `skip_existing` modes
- **Progress reporting**: Emit progress events for UI feedback
- **Rollback capability**: Ability to restore from pre-import backup

---

## Requirement 2: AI-Assisted Augmentation Support

### 2.1 Use Cases

| Use Case | Input | AI Task | Output |
|----------|-------|---------|--------|
| Price enrichment | Products without prices | Look up current prices | Products with `suggested_price`, `price_source`, `price_date` |
| Purchase creation | Inventory items without purchases | Generate purchase records | New purchase records linked to existing products |
| Ingredient matching | Raw product list | Match to canonical ingredients | Product records with `ingredient_slug` |
| Recipe costing | Recipe with ingredients | Calculate costs from inventory | Recipe with `estimated_cost_per_batch` |

### 2.2 AI-Friendly Export Format

Create denormalized views that eliminate FK lookups for AI processing:

#### 2.2.1 Products Augmentation View

File: `ai_products_for_pricing.json`

```json
{
  "purpose": "AI price enrichment",
  "instructions": "For each product, research current retail price and add suggested_unit_price, price_source, and price_confidence fields",
  "products": [
    {
      "product_id": 42,
      "ingredient_name": "All-Purpose Flour",
      "ingredient_category": "Flours & Starches",
      "brand": "King Arthur",
      "product_name": "Unbleached All-Purpose Flour",
      "package_size": "5 lb",
      "package_unit": "lb",
      "package_unit_quantity": 5.0,
      "upc_code": "071012010103",
      "current_unit_price": null,
      "last_purchase_price": 6.99,
      "last_purchase_date": "2024-11-15",
      "supplier_name": "Costco",

      // AI should populate these:
      "suggested_unit_price": null,
      "price_source": null,
      "price_confidence": null,
      "price_notes": null
    }
  ]
}
```

#### 2.2.2 Inventory Augmentation View

File: `ai_inventory_for_purchase_creation.json`

```json
{
  "purpose": "AI purchase record generation",
  "instructions": "For inventory items without purchase_id, create purchase records with estimated prices based on similar products",
  "context": {
    "known_suppliers": ["Costco", "Amazon", "Walmart", "King Arthur Baking"],
    "default_supplier": "Unknown"
  },
  "inventory_items_needing_purchases": [
    {
      "inventory_item_id": 101,
      "product_id": 42,
      "product_display": "King Arthur Unbleached All-Purpose Flour (5 lb)",
      "ingredient_name": "All-Purpose Flour",
      "quantity": 2.5,
      "unit_cost": null,
      "purchase_date": "2024-12-01",
      "location": "Pantry Shelf 2",

      "similar_products_with_prices": [
        {"product": "Gold Medal All-Purpose Flour (5 lb)", "last_price": 5.49},
        {"product": "King Arthur AP Flour (10 lb)", "last_price": 12.99}
      ],

      // AI should populate these for new purchase record:
      "suggested_unit_price": null,
      "suggested_supplier": null,
      "purchase_notes": null
    }
  ]
}
```

#### 2.2.3 Shopping List View

File: `ai_shopping_list.json`

```json
{
  "purpose": "AI-assisted shopping list with price estimates",
  "generated_for_event": "Christmas 2025",
  "items_needed": [
    {
      "ingredient_name": "Butter, Unsalted",
      "ingredient_slug": "butter_unsalted",
      "category": "Dairy & Eggs",
      "quantity_needed": 8.0,
      "unit": "lb",
      "current_inventory": 2.0,
      "shortage": 6.0,

      "preferred_products": [
        {
          "product_id": 55,
          "brand": "Kerrygold",
          "product_name": "Pure Irish Butter",
          "package_size": "8 oz",
          "packages_needed": 12,
          "last_price": 4.99,
          "supplier": "Costco"
        }
      ],

      // AI should populate:
      "estimated_total_cost": null,
      "alternative_products": null,
      "bulk_buying_recommendation": null
    }
  ]
}
```

### 2.3 AI Response Import Format

Define structure for importing AI-augmented data back:

```json
{
  "augmentation_type": "price_enrichment",
  "source_file": "ai_products_for_pricing.json",
  "processed_at": "2025-12-24T14:00:00Z",
  "ai_model": "claude-3-opus",
  "updates": [
    {
      "product_id": 42,
      "updates": {
        "suggested_unit_price": 7.49,
        "price_source": "costco.com",
        "price_confidence": "high",
        "price_notes": "Verified 2025-12-24"
      }
    }
  ],
  "new_records": {
    "purchases": [
      {
        "product_id": 42,
        "supplier_name": "Costco",
        "purchase_date": "2024-12-01",
        "unit_price": 6.99,
        "quantity_purchased": 2,
        "notes": "AI-generated from inventory data"
      }
    ]
  }
}
```

---

## Requirement 3: Recommended Denormalized Export Files

### 3.1 Core Denormalized Views

| File | Purpose | Contents |
|------|---------|----------|
| `view_products_complete.json` | Product catalog with all context | Product + Ingredient details + Last purchase + Inventory status |
| `view_inventory_status.json` | Current inventory state | InventoryItem + Product + Ingredient + Purchase details |
| `view_recipes_costed.json` | Recipes with cost calculations | Recipe + Ingredients with quantities + Current costs |
| `view_shopping_needs.json` | What needs to be purchased | Shortage analysis + Preferred products + Price history |

### 3.2 AI Workflow Files

| File | Workflow | AI Task |
|------|----------|---------|
| `ai_products_for_pricing.json` | Price enrichment | Add/update prices from web research |
| `ai_inventory_for_purchase_creation.json` | Purchase record creation | Create missing purchase records |
| `ai_ingredients_for_categorization.json` | Category cleanup | Suggest category corrections |
| `ai_recipes_for_scaling.json` | Recipe optimization | Suggest batch size adjustments |

### 3.3 View Schema

Each denormalized view should include:

```json
{
  "view_name": "products_complete",
  "view_version": "1.0",
  "generated_at": "2025-12-24T12:00:00Z",
  "purpose": "Complete product information with denormalized relationships",
  "source_entities": ["products", "ingredients", "suppliers", "purchases", "inventory_items"],
  "record_count": 152,
  "schema_description": {
    "product_id": "Primary key from products table",
    "ingredient_name": "Denormalized from ingredients.display_name",
    "last_purchase_price": "Most recent purchase.unit_price",
    "current_inventory_qty": "SUM of inventory_items.quantity"
  },
  "records": [...]
}
```

---

## Requirement 4: Export Service API

### 4.1 New Service Functions

```python
# Coordinated export
def export_complete_set(
    output_dir: Path,
    include_transactional: bool = True,
    include_events: bool = True,
    date_range: Optional[Tuple[date, date]] = None
) -> ExportManifest:
    """Export complete dataset as coordinated file set with manifest."""

# Individual entity exports (enhanced)
def export_entity(
    entity_type: str,
    output_path: Path,
    include_fk_lookups: bool = True
) -> ExportResult:
    """Export single entity type with FK resolution fields."""

# Denormalized view exports
def export_view(
    view_name: str,
    output_path: Path,
    filters: Optional[Dict] = None
) -> ExportResult:
    """Export denormalized view for AI processing."""

# AI workflow exports
def export_for_ai_augmentation(
    workflow: str,  # "price_enrichment", "purchase_creation", etc.
    output_path: Path,
    scope: Optional[Dict] = None
) -> ExportResult:
    """Export AI-ready format for specific augmentation workflow."""
```

### 4.2 New Import Functions

```python
# Coordinated import
def import_complete_set(
    manifest_path: Path,
    mode: str = "merge",  # "replace", "merge", "skip_existing"
    dry_run: bool = False
) -> ImportResult:
    """Import complete dataset from manifest-coordinated file set."""

# AI augmentation import
def import_ai_augmentation(
    augmentation_file: Path,
    apply_updates: bool = True,
    create_new_records: bool = True
) -> ImportResult:
    """Import AI-generated updates and new records."""

# Validation
def validate_export_set(manifest_path: Path) -> ValidationResult:
    """Validate export set integrity (checksums, dependencies, completeness)."""
```

---

## Requirement 5: Implementation Considerations

### 5.1 Backward Compatibility

- Existing v3.5 monolithic export must continue to work
- New entity files should be importable independently (with warnings about missing deps)
- Legacy import functions should delegate to new system

### 5.2 Performance

- Large exports should use streaming JSON for memory efficiency
- Checksums computed incrementally during export
- Import should batch database operations (100-500 records per transaction)

### 5.3 Error Handling

- Partial export failure should not leave inconsistent state
- Import should report all errors before failing (not fail-fast)
- Clear error messages with actionable suggestions

### 5.4 Testing Requirements

- Unit tests for each export/import function
- Integration tests for full round-trip (export → import → verify identical)
- Validation tests for manifest integrity checking
- AI workflow tests with mock augmentation responses

---

## Appendix A: Entity Dependency Graph

```
Level 0 (No dependencies):
  - Supplier
  - Ingredient
  - Recipient
  - Unit

Level 1 (Single dependency):
  - Product → Ingredient, Supplier
  - Recipe → Ingredient (via RecipeIngredient)
  - FinishedGood (standalone)
  - Package (standalone)

Level 2 (Multiple dependencies):
  - Purchase → Product, Supplier
  - FinishedUnit → Recipe
  - Event (standalone but links many)

Level 3 (Complex dependencies):
  - InventoryItem → Product, Purchase
  - Composition → FinishedGood, FinishedUnit, Package, Product
  - EventRecipientPackage → Event, Recipient, Package
  - EventProductionTarget → Event, Recipe
  - EventAssemblyTarget → Event, FinishedGood

Level 4 (Transactional):
  - ProductionRun → Event, Recipe, FinishedUnit
  - ProductionConsumption → ProductionRun, InventoryItem
  - ProductionLoss → ProductionRun
  - AssemblyRun → Event, FinishedGood
  - AssemblyFinishedUnitConsumption → AssemblyRun, FinishedUnit
  - AssemblyPackagingConsumption → AssemblyRun, Product
```

---

## Appendix B: File Naming Convention

```
exports/
├── manifest.json                      # Coordinated export manifest
├── 01_suppliers.json                  # Entity files (numbered for order)
├── 02_ingredients.json
├── 03_products.json
├── 04_purchases.json
├── 05_inventory_items.json
├── 06_recipes.json
├── 07_finished_units.json
├── 08_finished_goods.json
├── 09_compositions.json
├── 10_packages.json
├── 11_recipients.json
├── 12_events.json
├── 13_production_runs.json
├── 14_assembly_runs.json
└── views/                             # Denormalized views
    ├── products_complete.json
    ├── inventory_status.json
    ├── recipes_costed.json
    └── shopping_needs.json
└── ai/                                # AI workflow files
    ├── products_for_pricing.json
    ├── inventory_for_purchase_creation.json
    └── augmentation_response.json     # AI response (input)
```
