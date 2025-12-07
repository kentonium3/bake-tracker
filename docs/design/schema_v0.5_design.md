# Schema v0.5 Design - Product and Inventory Foundation

**Purpose:** Replace the out-of-date `schema_v0.4_design.md` with a concise, current view of the data model after TD-001 and outline the schema targets for the next feature set (011-013).

**Status:** Drafted 2025-12-07. TD-001 refactor is merged and live. This document is the active design reference going into Feature 011.

**Sources:**
- `docs/TD-001-schema-cleanup-prompt.md`
- `docs/feature_roadmap.md`
- `docs/workflow-refactoring-spec.md`
- Current models under `src/models/`

---

## 1) Terminology (updated)
- **Ingredient**: Catalog entry for the generic concept (display name, category, recipe unit, density, identifiers).
- **Product** (formerly Variant): Brand/package-specific purchasable option for an Ingredient.
- **InventoryItem** (formerly PantryItem): FIFO-tracked on-hand quantity for a Product.
- **Purchase**: Price history entry for a Product.
- **UnitConversion**: Ingredient-scoped conversions and density-based cross-unit support.
- **RecipeIngredient**: Brand-agnostic ingredient requirement for a recipe.
- **FinishedUnit / FinishedGood / Composition**: Produced items and assemblies (Phase 4, already in code).
- **ProductPackaging**: Packaging hierarchy metadata for a Product (each/inner/case/pallet).
- **InventorySnapshot**: Periodic point-in-time inventory capture.

All user-facing strings now use "product" and "inventory"; legacy "variant" and "pantry" remain only in historical notes.

---

## 2) Completed changes (TD-001 recap)
- Renamed Variant → Product across models, services, UI, import/export keys, and tests.
- Renamed PantryItem → InventoryItem; renamed PantryService → InventoryItemService; renamed InventoryService → IngredientCrudService.
- RecipeIngredient now uses `ingredient_id` only (legacy dual FK removed).
- Ingredient naming aligned to `display_name` (replacing `name`), and display_name is required and indexed.
- Import/export JSON keys use `products` instead of `variants`; sample data updated.
- ProductPackaging, FinishedUnit, FinishedGood, Composition retained and aligned to Product/Inventory terminology.
- Database recreation guidance captured in TD-001 (backup, rebuild, reimport).

---

## 3) Current schema overview (post TD-001)

```
Ingredient 1--* Product 1--* Purchase
    |              |
    |              *--* ProductPackaging
    |
    *--* UnitConversion
    *--* RecipeIngredient *-- Recipe

Product 1--* InventoryItem

FinishedUnit 1--* Composition (component)
FinishedGood 1--* Composition (assembly)

InventorySnapshot (captures InventoryItem state)
```

### Catalog layer
- **Ingredient (`src/models/ingredient.py`)**
  - Required: `display_name`, `category`.
  - Optional: `slug`, `recipe_unit`, description/notes, density fields, identifiers (foodon_id, foodex2_code, langual_terms, fdc_ids), moisture/allergens.
  - Relationships: products, conversions, recipe_ingredients.
- **Product (`src/models/product.py`)**
  - FK: `ingredient_id`.
  - Brand/package: `brand`, `package_size`, `package_type`.
  - Purchase definition: `purchase_unit`, `purchase_quantity`.
  - Identifiers: `upc_code`, `gtin`, `brand_owner`, `gpc_brick_code`, `net_content_value`, `net_content_uom`, `country_of_sale`, `off_id`.
  - Flags/notes: `preferred`, `notes`, timestamps.
  - Relationships: purchases, inventory_items, packaging_levels.
- **ProductPackaging (`src/models/product_packaging.py`)**
  - FK: `product_id`.
  - Fields: `packaging_level` (each/inner/case/pallet), GS1 codes, `qty_of_next_lower_level`, dimensions, weight.
- **Purchase (`src/models/purchase.py`)**
  - FK: `product_id`.
  - Fields: `purchase_date`, `unit_cost`, `quantity_purchased`, `total_cost`, supplier, receipt_number, notes.
- **UnitConversion (`src/models/unit_conversion.py`)**
  - FK: `ingredient_id`.
  - Fields: from_unit, to_unit, factor; supports density-aware conversions via services.

### Inventory layer
- **InventoryItem (`src/models/inventory_item.py`)**
  - FK: `product_id`.
  - Fields: `quantity`, `unit_cost`, `purchase_date`, `expiration_date`, `opened_date`, `location`, `lot_or_batch`, notes, `last_updated`.
  - FIFO helpers: `get_inventory_items_fifo`, `consume_fifo`, `get_expiring_soon`, `get_total_quantity_for_ingredient`.
- **InventorySnapshot (`src/models/inventory_snapshot.py`)**
  - Captures snapshot metadata and itemized quantities (used for audits and UI summaries).

### Recipe and production layer
- **Recipe / RecipeIngredient (`src/models/recipe.py`)**
  - RecipeIngredient uses `ingredient_id` (brand-agnostic), `quantity`, `unit`, `notes`.
- **FinishedUnit (`src/models/finished_unit.py`)**
  - Fields: `slug`, `display_name`, `recipe_id`, `yield_mode`, items_per_batch/batch_percentage, `unit_cost`, `inventory_count`, production_notes, notes.
- **FinishedGood (`src/models/finished_good.py`)**
  - Assembly-level artifact; works with Composition for nested structures.
- **Composition (`src/models/composition.py`)**
  - FK: `assembly_id` (FinishedGood), component as FinishedUnit or FinishedGood, quantity, notes, sort order with integrity constraints.
- **ProductionRecord (`src/models/production_record.py`)**
  - Tracks production runs and quantities (basis for future batch/BOM work).

### Services (aligned with schema)
- Catalog: IngredientService, IngredientCrudService, ProductService, UnitConverter.
- Inventory: InventoryItemService, ImportExportService (products key), InventorySnapshot via services.
- Production: FinishedUnitService, FinishedGoodService, CompositionService, ProductionService.
- UI: Product and Inventory wording throughout; legacy wording removed.

---

## 4) Planned changes (next features)

### Feature 011 - Packaging and BOM Foundation (HIGH)
- Introduce packaging materials without a new entity by flagging Ingredients as packaging-capable (add `is_packaging` boolean plus optional packaging attributes). Products for packaging follow the same Product table.
- Add BOM tables to support assemblies:
  - **fg_bom_lines**: FinishedGood requires FinishedUnit components and packaging Products (consumes inventory).
  - **pkg_bom_lines**: Package assembly requires FinishedGoods and packaging Products.
- Extend ProductPackaging where needed for BOM-friendly packaging specs.
- Service updates: BOM management service, validation of packaging Products, unit conversion hooks for packaging.

### Feature 012 - Production and Inventory Tracking (HIGH, depends on 011)
- Introduce explicit batch tracking entity (BATCH) tied to recipes and FinishedUnits; record inputs consumed and outputs produced.
- Separate inventory ledgers:
  - `inventory_items` (raw and packaging Products) — already present.
  - `finished_item_stock` (atomic outputs from batches).
  - `finished_good_stock` (assembled goods ready for packaging).
- Consumption flows:
  - Batch consumes InventoryItems (raw/packaging) according to RecipeIngredient and BOM definitions.
  - FinishedGood assembly consumes FinishedUnit stock and packaging Products via fg_bom_lines.
  - Package assembly consumes FinishedGood stock and packaging Products via pkg_bom_lines.
- Service work: production execution service with FIFO-aware consumption, cost rollups, and stock adjustments; reporting hooks for UI.

### Feature 013 - Production UI (HIGH, depends on 012)
- UI screens for:
  - Batch runs (inputs, outputs, waste).
  - BOM authoring for FinishedGoods and Packages.
  - Inventory movements: consume, produce, adjust, snapshot review.
- Ensure UI uses product/inventory wording and pulls data via services (no direct DB coupling).

### Later (014/015)
- Reporting and distribution enhancements; follow once inventory separation is stable.

---

## 5) Open design questions and decisions
- **Packaging flag location:** Add `is_packaging` on Ingredient (preferred per roadmap). Derive UI grouping from this field and category.
- **BOM storage:** Use dedicated tables for BOM lines (fg_bom_lines, pkg_bom_lines) rather than overloading Composition; keep Composition for FinishedGood component nesting only.
- **Inventory normalization:** Keep InventoryItem as raw/packaging stock; add separate tables for finished_item_stock and finished_good_stock to avoid mixed semantics.
- **Costing:** Use FIFO from InventoryItem for raw/packaging; roll costs into FinishedUnit and FinishedGood via production records; persist computed unit_cost for performance.
- **Unit conversion:** Require density for cross-unit conversions when consuming inventory; fail fast when missing data.
- **Migration:** Full DB rebuild still recommended after schema changes; import/export formats stay product/inventory centric.

---

## 6) Implementation checklist (snapshot)
- Add `is_packaging` to Ingredient and update services/UI/import-export.
- Create BOM tables (fg_bom_lines, pkg_bom_lines) and services with validation.
- Add finished_item_stock and finished_good_stock tables with services and UI hooks.
- Extend ProductionRecord (or add Batch) to record inputs/outputs and cost rollups.
- Update tests and sample data to use products/inventory terminology and new BOM structures.
- Update diagrams in `docs/workflow-refactoring-spec.md` once schemas land.

---

## 7) How to use this document
- Treat this as the authoritative schema reference until superseded.
- When implementing features 011-013, update this file and link PRs to relevant sections.
- Keep `schema_v0.4_design.md` for historical context only; do not modify it further.
