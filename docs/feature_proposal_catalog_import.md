# Feature Proposal: Catalog Import Separation

**Status:** Proposal
**Created:** 2025-12-13
**Author:** Kent Gale
**Priority:** TBD
**Complexity:** Medium

---

## Problem Statement

The current unified import/export system (v3.2) conflates two fundamentally different data types:

1. **Reference/Catalog Data** - Ingredients, Products, Unit Conversions, Recipes
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
- Manual data entry burden for large reference datasets (76+ ingredients currently)

---

## Proposed Solution

### Separate Import Pathways

**Catalog Import** (new)
- Handles: Ingredients, Products, Unit Conversions, Recipes
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
| Programmatic JSON transformation between schema versions | ✅ Unchanged | External scripts on v3.2 JSON |
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
│                    UNIFIED IMPORT/EXPORT (v3.2)                         │
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
│  Format: Catalog-specific JSON (ingredients, products, recipes only)   │
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
- `name` (user may have customized)

**Augmentable Fields:**
- `density_g_per_ml`
- `foodon_id`, `fdc_ids`, `foodex2_code`, `langual_terms`
- `allergens`
- `description` (only if currently null)

**Rationale:** Ingredients are reference data that will be pre-populated in commercial version. Metadata enrichment (industry standard IDs, allergen data) should be additive without disrupting existing user configurations.

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

### Unit Conversions

**Unique Key:** `(ingredient_slug, from_unit, to_unit)`

| Mode | Supported | Behavior |
|------|-----------|----------|
| ADD_ONLY | ✅ Yes | Create new conversions, skip existing |
| AUGMENT | ❌ No | Conversion factors are factual, not augmentable |

**Rationale:** Unit conversions are factual reference data. Multiple conversion paths per ingredient are valid (lb→cup, kg→cup). Once established, conversion factors should not change via import.

---

## Reference Integrity Validation

### Catalog Import Validation

Before creating any records, validate FK references exist:

```
Products → Ingredients (ingredient_slug must exist)
Recipes → Ingredients (all ingredient_slugs in recipe must exist)
Recipes → Recipes (all component recipe_names must exist, no cycles)
UnitConversions → Ingredients (ingredient_slug must exist)
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
# Import full catalog bundle (ingredients, products, recipes, conversions)
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

## File Format

### Unified Format (v3.3)

```json
{
  "version": "3.3",
  "exported_at": "2025-12-13T10:30:00Z",
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

Unit Conversions:
  Added:    15
  Skipped:   4 (already exist)
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
2. **Catalog Expansion:** User can import 50+ new ingredients without affecting existing recipes
3. **Metadata Enrichment:** User can augment ingredient density values without data loss
4. **Recipe Collections:** User can import AI-generated recipe sets incrementally
5. **Reference Integrity:** Import fails cleanly with actionable errors when FKs missing
6. **Backward Compatibility:** Existing v3.2 unified import format continues to work exactly as before
7. **Dry-Run Validation:** User can preview all changes before committing

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

- [Import/Export Specification v3.2](./design/import_export_specification.md)
- [Schema v0.6 Design](./design/schema_v0.6_design.md)
- [Architecture Document](./design/architecture.md)
- [Project Constitution](../.kittify/memory/constitution.md)

---

**Document Status:** Proposal - Pending roadmap prioritization
