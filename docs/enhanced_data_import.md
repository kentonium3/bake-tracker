# Feature Proposal: Enhanced Data Import

**Status:** In Progress (Feature 020)
**Created:** 2025-12-13
**Updated:** 2025-12-14
**Author:** Kent Gale
**Priority:** HIGH

---

## Problem Statement

The current unified import/export system (v3.3) conflates two fundamentally different data types:

1. **Reference/Catalog Data** - Ingredients, Products, Recipes
   - Slowly changing, potentially shared across users
   - Candidates for pre-populated libraries
   - Large metadata sets that are burdensome to enter manually

2. **Transactional Data** - Purchases, Inventory Items, Event Assignments, Production Records
   - User-specific, frequently changing
   - Represents actual user activity and inventory state

This conflation creates several issues:
- No safe way to expand ingredient/product catalogs without risking user data
- AI-generated recipe collections cannot be imported incrementally
- Future commercial web version requires separation for shared catalog management
- Manual data entry burden for large reference datasets (160+ ingredients in pending catalog)

---

## Proposed Solution

### Separate Import Pathways

**Catalog Import** (new)
- Handles: Ingredients, Products, Recipes
- Modes: ADD_ONLY (default), AUGMENT (ingredients/products only)
- Purpose: Safely expand reference data catalogs

**Data Import** (existing, refined)
- Handles: Purchases, Inventory Items, Finished Units, Finished Goods, Compositions, Packages, Recipients, Events, Production Records
- Mode: ADD_ONLY
- Requires: Valid FK references to existing catalog entities
- Purpose: Import/export user-specific transactional data

### Import Mode Definitions

| Mode | Behavior | Use Case |
|------|----------|----------|
| `ADD_ONLY` | Create new records, skip existing (by unique key) | Safe catalog expansion |
| `AUGMENT` | Update NULL fields on existing records, add new | Metadata enrichment |

**Prohibited Operations (all modes):**
- Delete existing records
- Modify primary/foreign key fields
- Overwrite non-null user data (in AUGMENT mode)

---

## Development Workflow Preservation (CRITICAL)

### Original Use Case

The unified import/export system was created to support a critical development workflow:

```
Development Round-Trip Cycle:
1. Manually enter test data via UI (ingredients, recipes, events, etc.)
2. Export ALL data to single JSON file (complete snapshot)
3. Schema change required → delete DB, update models, recreate empty DB
4. Programmatically transform exported JSON to match new schema
5. Import entire dataset back → full restoration with schema compliance
```

**This workflow MUST remain fully functional.** The catalog import separation is an **additive capability**, not a replacement for the unified export/import.

### Preserved Capabilities

The following capabilities remain unchanged:

| Capability | Status | Tool |
|------------|--------|------|
| Export complete database to single JSON file | ✅ Unchanged | `import_export export` |
| Import complete JSON to empty database | ✅ Unchanged | `import_export import --mode=replace` |
| Programmatic JSON transformation between schema versions | ✅ Unchanged | External scripts on v3.3 JSON |
| Merge external data into existing database | ✅ Unchanged | `import_export import --mode=merge` |

### Development Workflow Commands

```bash
# === DEVELOPMENT ROUND-TRIP (unchanged) ===

# Step 1: Export current state before schema change
python -m src.utils.import_export export checkpoint_before_v0.7.json

# Step 2: Reset database after model changes
# (delete bake_tracker.db, run app to recreate empty DB)

# Step 3: Transform JSON if schema changed (external script)
python scripts/migrate_v0.6_to_v0.7.py checkpoint_before_v0.7.json checkpoint_v0.7.json

# Step 4: Restore all data
python -m src.utils.import_export import checkpoint_v0.7.json --mode=replace


# === NEW: CATALOG EXPANSION (additive) ===

# Add AI-generated ingredients without touching existing data
python -m src.utils.import_catalog new_ingredients.json --mode=add

# Enrich existing ingredients with density values
python -m src.utils.import_catalog density_data.json --entity=ingredients --mode=augment
```

### Import Pathway Decision Matrix

| Scenario | Use This Tool | Mode | Rationale |
|----------|---------------|------|-----------|
| DB reset during development | `import_export` | replace | Complete restoration needed |
| Backup before risky change | `import_export export` | — | Capture full state |
| Schema migration checkpoint | `import_export` | replace | Transformed JSON replaces all |
| Adding recipes from AI/external source | `import_catalog` | add | Preserve existing, add new |
| Enriching ingredient metadata | `import_catalog` | augment | Update nulls only |
| Merging user data from another instance | `import_export` | merge | Combine datasets |
| Pre-populating new installation | `import_export` | replace | Start with known dataset |

### Unified vs Catalog Import: When to Use Each

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    UNIFIED IMPORT/EXPORT (v3.3)                         │
│                                                                         │
│  Use when you need:                                                     │
│  • Complete database backup/restore                                     │
│  • Development DB reset recovery                                        │
│  • Schema migration with data transformation                            │
│  • Full state transfer between installations                            │
│                                                                         │
│  Format: Single JSON with ALL entity types                              │
│  Modes: merge (default), replace                                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    CATALOG IMPORT (new)                                 │
│                                                                         │
│  Use when you need:                                                     │
│  • Add new ingredients/products without affecting existing              │
│  • Import AI-generated recipe collections                               │
│  • Enrich metadata (densities, UPCs, allergens) on existing records     │
│  • Incremental catalog expansion from external sources                  │
│                                                                         │
│  Format: Catalog-specific JSON (ingredients, products, recipes only)    │
│  Modes: add (default), augment                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Entity-Specific Behavior

### Ingredients

**Unique Key:** `slug`

| Mode | Supported | Behavior |
|------|-----------|----------|
| ADD_ONLY | ✅ Yes | Create new ingredients, skip existing slugs |
| AUGMENT | ✅ Yes | Update null metadata fields (density, allergens, FoodOn IDs) |

**Protected Fields (never modified via import):**
- `slug` (primary reference key)
- `display_name` (user may have customized)

**Augmentable Fields:**
- `density_volume_value`, `density_volume_unit`
- `density_weight_value`, `density_weight_unit`
- `foodon_id`, `fdc_ids`, `foodex2_code`, `langual_terms`
- `allergens`
- `description` (only if currently null)

**Rationale:** Ingredients are reference data that will be pre-populated in commercial version. Metadata enrichment (industry standard IDs, allergen data, density values) should be additive without disrupting existing user configurations.

---

### Products

**Unique Key:** `(ingredient_slug, brand)`

| Mode | Supported | Behavior |
|------|-----------|----------|
| ADD_ONLY | ✅ Yes | Create new products, skip existing ingredient+brand combinations |
| AUGMENT | ✅ Yes | Update null fields (UPC, supplier, package details) |

**Protected Fields (never modified via import):**
- `ingredient_slug` (FK reference)
- `brand` (part of composite key)
- `is_preferred` (user preference - consider separate handling)

**Augmentable Fields:**
- `upc_code`
- `package_size`, `package_type`
- `package_unit`, `package_unit_quantity` (only if currently null)

**Rationale:** Products link ingredients to purchasable items. Reference integrity to Purchases and InventoryItems must be preserved. UPC data is valuable for future barcode scanning and API integrations.

---

### Recipes

**Unique Key:** `slug`

| Mode | Supported | Behavior |
|------|-----------|----------|
| ADD_ONLY | ✅ Yes | Create new recipes, skip existing slugs |
| AUGMENT | ❌ No | Not supported - recipes are user-authored content |

**Rationale:** Recipes represent user-authored content with personal customizations (timing, notes, yield adjustments). Bulk modification via import risks overwriting intentional user changes. The "import adds, UI edits" model is intuitive and safe.

**Validation Requirements:**
- All `ingredient_slug` references in recipe ingredients must exist
- All `recipe_name` references in recipe components must exist (for nested recipes)
- Fail-fast with clear error listing missing references
- Optional: `--create-stubs` flag to auto-create minimal ingredient records

---

## Reference Integrity Validation

### Catalog Import Validation

Before creating any records, validate FK references exist:

```
Products → Ingredients (ingredient_slug must exist)
Recipes → Ingredients (all ingredient_slugs in recipe must exist)
Recipes → Recipes (all component recipe_names must exist, no cycles)
```

**Failure Behavior:**
- Collect all missing references
- Report complete list in error output
- Fail entire import (no partial imports)
- Suggest: "Run ingredient catalog import first"

### Data Import Validation

Before creating transactional records, validate catalog references:

```
Purchases → Products (ingredient_slug + brand must exist)
InventoryItems → Products (ingredient_slug + brand must exist)
FinishedUnits → Recipes (recipe_slug must exist)
Compositions → FinishedUnits/FinishedGoods (component_slug must exist)
PackageFinishedGoods → Packages, FinishedGoods (slugs must exist)
EventRecipientPackages → Events, Recipients, Packages (refs must exist)
ProductionRecords → Events, Recipes (refs must exist)
```

---

## Proposed CLI Interface

### Unified Import/Export Commands (existing, unchanged)

```bash
# Complete database export (all entities)
python -m src.utils.import_export export backup.json

# Complete database restore (replaces all data)
python -m src.utils.import_export import backup.json --mode=replace

# Merge external data into existing database
python -m src.utils.import_export import additional_data.json --mode=merge
```

### Catalog Import Commands (new)

```bash
# Import full catalog bundle (ingredients, products, recipes)
python -m src.utils.import_catalog catalog.json

# Import specific entity type
python -m src.utils.import_catalog ingredients.json --entity=ingredients
python -m src.utils.import_catalog products.json --entity=products
python -m src.utils.import_catalog recipes.json --entity=recipes

# Augment mode for metadata enrichment
python -m src.utils.import_catalog enrichment.json --entity=ingredients --mode=augment
python -m src.utils.import_catalog product_upcs.json --entity=products --mode=augment

# Dry-run to preview changes
python -m src.utils.import_catalog catalog.json --dry-run

# Verbose output showing all decisions
python -m src.utils.import_catalog catalog.json --verbose
```

---

## UI Integration

Extend the existing File menu (Feature 009) to support catalog import.

### Menu Structure

```
File
├── Import Data...              (existing - unified import)
├── Export Data...              (existing - unified export)
├── ──────────────────────
├── Import Catalog...           (NEW - catalog import)
│   ├── Opens file picker
│   └── Shows CatalogImportDialog
└── ──────────────────────
```

### CatalogImportDialog

Modal dialog with the following elements:

```
┌───────────────────────────────────────────────────────────┐
│  Import Catalog                                          │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  File: [/path/to/catalog.json            ] [Browse...]   │
│                                                           │
│  Import Mode:                                             │
│    ◉ Add Only (skip existing records)                     │
│    ○ Augment (update null fields on existing)             │
│                                                           │
│  Entity Filter (optional):                                │
│    ☑ Ingredients                                          │
│    ☑ Products                                              │
│    ☑ Recipes                                               │
│                                                           │
│  ☐ Preview changes before importing (dry-run)             │
│                                                           │
├───────────────────────────────────────────────────────────┤
│                                    [Cancel]  [Import...]  │
└───────────────────────────────────────────────────────────┘
```

### Import Results Dialog

After import completes, show results summary:

```
┌───────────────────────────────────────────────────────────┐
│  Catalog Import Complete                                  │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Ingredients:  12 added, 3 skipped, 0 failed              │
│  Products:      8 added, 5 skipped, 1 failed              │
│  Recipes:       6 added, 2 skipped, 0 failed              │
│                                                           │
│  ⚠ 1 error (click Details to view)                        │
│                                                           │
├───────────────────────────────────────────────────────────┤
│                              [Details...]  [OK]           │
└───────────────────────────────────────────────────────────┘
```

### UI Behavior Notes

1. **File picker** filters for `.json` files
2. **Mode toggle** disables "Augment" when Recipes checkbox is selected (augment not supported for recipes)
3. **Dry-run checkbox** when checked, Import button label changes to "Preview..."
4. **Preview results** show in scrollable text area before confirming
5. **Refresh** - after successful import, affected tabs (Ingredients, Recipes) should refresh their data

---

## Service Architecture

### Design Principle

The catalog import service MUST be structured as **independent entity-specific functions** with a coordinator. This enables future import pathways (web scraping, API integration, barcode scanning) to call entity-specific functions directly without going through the catalog coordinator.

### Service Structure

```python
# src/services/catalog_import_service.py

class CatalogImportService:
    """
    Coordinator for catalog imports. Routes to entity-specific 
    functions based on file content.
    """
    
    def import_catalog(
        self, 
        file_path: str, 
        mode: ImportMode = ImportMode.ADD_ONLY,
        entities: list[str] | None = None,  # None = all
        dry_run: bool = False
    ) -> CatalogImportResult:
        """
        Import a catalog bundle file. Dispatches to entity-specific
        functions in dependency order.
        """
        pass
    
    def import_ingredients(
        self, 
        data: list[dict], 
        mode: ImportMode = ImportMode.ADD_ONLY,
        dry_run: bool = False
    ) -> EntityImportResult:
        """
        Import ingredients. Independently callable for future 
        integrations (USDA FDC API, FoodOn ontology).
        """
        pass
    
    def import_products(
        self, 
        data: list[dict], 
        mode: ImportMode = ImportMode.ADD_ONLY,
        dry_run: bool = False
    ) -> EntityImportResult:
        """
        Import products. Independently callable for future 
        integrations (UPC databases, barcode scanning, grocery APIs).
        """
        pass
    
    def import_recipes(
        self, 
        data: list[dict], 
        mode: ImportMode = ImportMode.ADD_ONLY,
        dry_run: bool = False
    ) -> EntityImportResult:
        """
        Import recipes. Independently callable for future 
        integrations (web scraping, OCR/scanning, AI from images).
        """
        pass
```

### Why This Architecture

| Concern | Decision | Rationale |
|---------|----------|----------|
| Service layer | **Separated by entity** | Different validation, FK deps, augmentable fields, post-import hooks |
| CLI/UI layer | **Unified coordinator** | Simpler UX for common case (AI-generated bundles) |
| Future extensibility | **Not blocked** | "Import Recipe from Web" calls `import_recipes()` directly after fetch/transform |

### Future Import Pathways (Not In Scope)

This architecture enables but does not implement:

- `File > Import Recipe from Web...` → fetch URL → parse schema.org/Recipe → `import_recipes()`
- Barcode scanning → UPC lookup API → `import_products()`
- USDA FDC search → `import_ingredients()`

Each future pathway would have its own fetch/transform step, then call the appropriate entity-specific function.

---

## File Format

### Unified Format (v3.3)

```json
{
  "version": "3.3",
  "exported_at": "2025-12-14T10:30:00Z",
  "application": "bake-tracker",
  "ingredients": [...],
  "products": [...],
  "purchases": [...],
  "inventory_items": [...],
  "recipes": [...],
  "finished_units": [...],
  "finished_goods": [...],
  "compositions": [...],
  "packages": [...],
  "package_finished_goods": [...],
  "recipients": [...],
  "events": [...],
  "event_recipient_packages": [...],
  "event_production_targets": [...],
  "event_assembly_targets": [...],
  "production_records": [...],
  "production_runs": [...],
  "assembly_runs": [...]
}
```

### Catalog Import Format (new)

```json
{
  "catalog_version": "1.0",
  "ingredients": [...],
  "products": [...],
  "recipes": [...]
}
```

### Format Detection

Import utilities detect format and route appropriately:
- If `version: "3.3"` present → unified import (existing behavior)
- If `catalog_version` present → catalog import rules

---

## Import Result Reporting

```
============================================================
Catalog Import Summary
============================================================
Mode: ADD_ONLY
Dry Run: No

Ingredients:
  Added:    12
  Skipped:   3 (already exist)
  Failed:    0

Products:
  Added:     8
  Skipped:   5 (already exist)
  Failed:    1 (missing ingredient: organic_vanilla)

Recipes:
  Added:     6
  Skipped:   2 (already exist)
  Failed:    0

Errors:
  - Product "Organic Vanilla Extract" references missing ingredient 'organic_vanilla'

Warnings:
  - Ingredient "all_purpose_flour" already exists, skipped
  - Recipe "Chocolate Chip Cookies" already exists, skipped

============================================================
```

---

## Implementation Considerations

### Module Structure

```
src/utils/
├── import_catalog.py          # New: Catalog import logic
├── import_export.py           # Existing: Full import/export (unchanged interface)
└── import_validators.py       # New: Shared FK validation utilities
```

### Database Considerations

- All imports wrapped in transaction (rollback on failure)
- Dry-run mode queries but does not commit
- Augment mode uses conditional UPDATE (WHERE field IS NULL)

### Logging

- All import operations logged with timestamp
- Augmented fields logged with old (null) → new values
- Provides audit trail for data lineage

---

## Success Criteria

1. **Development Workflow:** Full export → DB reset → transform → import cycle works unchanged
2. **Catalog Expansion:** User can import 160 new ingredients without affecting existing recipes
3. **Metadata Enrichment:** User can augment ingredient density values without data loss
4. **Recipe Collections:** User can import AI-generated recipe sets incrementally
5. **Reference Integrity:** Import fails cleanly with actionable errors when FKs missing
6. **Backward Compatibility:** Existing v3.3 unified import format continues to work exactly as before
7. **Dry-Run Validation:** User can preview all changes before committing
8. **UI Access:** Catalog import available via File menu (not CLI-only)

---

## Pending Ingredient Catalog

A 160-ingredient catalog is ready for import once this feature is complete:
- **File:** `test_data/baking_ingredients_v33.json` (to be converted from v3.2)
- **Categories:** 12 (Alcohol, Chocolate/Candies, Cocoa Powders, Dried Fruits, Extracts, Flour, Misc, Nuts, Oils/Butters, Spices, Sugar, Syrups)
- **All ingredients have 4-field density values**

---

## Future Considerations

### Commercial Web Version

- Shared ingredient/product catalog maintained by system
- User customizations stored in separate layer
- Catalog updates pushed to users without affecting their data

### API Integration

- Ingredient enrichment from FoodOn/USDA FDC APIs
- Product data from UPC databases
- Recipe import from structured recipe formats (Recipe JSON-LD)

### Mobile/Barcode Scanning

- Product lookup by UPC
- Auto-add scanned products to catalog
- Augment mode adds UPCs to existing products

---

## Open Questions

1. **Preferred Flag Handling:** Should `is_preferred` be augmentable, or always require explicit user action?
2. **Name Conflicts:** If imported recipe slug matches existing but content differs, should we suffix "(imported)" or reject?
3. **Partial Success:** Should we support partial imports (commit successful records, report failures)?
4. **Export Separation:** Should export also separate catalog vs data, or always export unified?

---

## References

- [Import/Export Specification v3.3](./import_export_specification.md)
- [Feature 019: Unit Conversion Simplification](./feature_019_unit_simplification.md)
- [Project Constitution v1.2.0](../.kittify/memory/constitution.md)
- [Feature Roadmap](./feature_roadmap.md)

---

**Document Status:** In Progress (Feature 020)
