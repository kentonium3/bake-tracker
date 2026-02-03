# Service Function Inventory

**Feature**: F091 - Transaction Boundary Documentation
**Created**: 2026-02-03
**Purpose**: Comprehensive inventory of public service functions for transaction boundary documentation

## Classification Legend

| Type | Description | Template |
|------|-------------|----------|
| **READ** | Query-only, no database writes | Pattern A |
| **SINGLE** | Single database write operation | Pattern B |
| **MULTI** | Multiple operations requiring atomic transaction | Pattern C |

## Existing Documentation

Functions with existing "Transaction boundary:" documentation (HAS_DOC):
- None found via grep search

## Service File Inventory

### ingredient_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `validate_density_fields` | READ | No | Pure validation function |
| `create_ingredient` | SINGLE | No | Single INSERT |
| `get_ingredient` | READ | Yes | Single SELECT |
| `search_ingredients` | READ | No | Query with filters |
| `update_ingredient` | MULTI | No | May call hierarchy service |
| `delete_ingredient` | MULTI | No | Calls check_dependencies first |
| `can_delete_ingredient` | READ | Yes | Multiple counts |
| `_denormalize_snapshot_ingredients` | SINGLE | Yes (required) | Internal helper |
| `delete_ingredient_safe` | MULTI | Yes | Denormalize + delete |
| `check_ingredient_dependencies` | READ | No | Multiple counts |
| `list_ingredients` | READ | No | Paginated query |
| `get_all_ingredients` | READ | No | Wrapper for list_ingredients |
| `get_distinct_ingredient_categories` | READ | No | Distinct query |
| `get_all_distinct_categories` | READ | No | Distinct query |

### ingredient_crud_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `create_ingredient` | SINGLE | No | Single INSERT |
| `get_ingredient` | READ | No | Single SELECT |
| `get_all_ingredients` | READ | No | Query with filters |
| `update_ingredient` | SINGLE | No | Single UPDATE |
| `delete_ingredient` | MULTI | No | Check deps + delete |
| `update_quantity` | SINGLE | No | Single UPDATE (legacy) |
| `adjust_quantity` | SINGLE | No | Single UPDATE (legacy) |
| `search_ingredients_by_name` | READ | No | Wrapper |
| `get_ingredients_by_category` | READ | No | Wrapper |
| `get_low_stock_ingredients` | READ | No | Wrapper |
| `get_ingredient_count` | READ | No | COUNT query |
| `get_category_list` | READ | No | Distinct query |
| `get_total_inventory_value` | READ | No | Aggregate query |

### recipe_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `_validate_leaf_ingredient` | READ | Yes (required) | Internal validation |
| `create_recipe` | MULTI | No | Recipe + ingredients |
| `get_recipe` | READ | No | Eager load relations |
| `get_recipe_by_slug` | READ | Yes | Single SELECT |
| `get_all_recipes` | READ | No | Query with filters |
| `update_recipe` | MULTI | No | Recipe + ingredients |
| `delete_recipe` | MULTI | No | Check deps + cascade |
| `add_ingredient_to_recipe` | SINGLE | No | Single INSERT |
| `remove_ingredient_from_recipe` | SINGLE | No | Single DELETE |
| `update_recipe_ingredient` | SINGLE | No | Single UPDATE |
| `get_recipe_ingredients` | READ | No | Query with joins |
| `get_recipe_cost` | READ | Yes | Complex calculation |
| `check_recipe_producibility` | READ | Yes | Availability check |
| `get_aggregated_ingredients` | READ | Yes | **CRITICAL** - nested recipe support |
| `add_component_recipe` | MULTI | No | Validation + INSERT |
| `remove_component_recipe` | SINGLE | No | Single DELETE |
| `get_component_recipes` | READ | No | Query with joins |
| `get_containing_recipes` | READ | No | Query with joins |
| `search_recipes` | READ | No | Full-text search |
| `get_recipe_count` | READ | No | COUNT query |
| `get_recipe_categories` | READ | No | Distinct query |
| `calculate_recipe_cost` | READ | Yes | Cost aggregation |

### product_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `_slugify_component` | READ | No | Pure function |
| `_generate_product_slug` | READ | No | Pure function |
| `_generate_unique_product_slug` | READ | Yes (required) | Uniqueness check |
| `_validate_leaf_ingredient_for_product` | READ | Yes (required) | Hierarchy validation |
| `create_product` | MULTI | No | Validates ingredient + creates |
| `create_provisional_product` | MULTI | Yes | Validates + creates |
| `get_product` | READ | No | Eager load relations |
| `get_products_for_ingredient` | READ | No | Query with filter |
| `set_preferred_product` | MULTI | No | Clear all + set one |
| `update_product` | SINGLE | No | Single UPDATE |
| `delete_product` | MULTI | No | Check deps + delete |
| `check_product_dependencies` | READ | No | Multiple counts |
| `search_products_by_upc` | READ | No | UPC filter query |
| `get_preferred_product` | READ | No | Single SELECT |
| `_calculate_product_cost` | READ | No | Cost calculation helper |
| `get_product_recommendation` | MULTI | No | Calls multiple services |

### inventory_item_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `add_to_inventory` | MULTI | Yes | Purchase + InventoryItem creation |
| `get_inventory_items` | READ | No | Query with filters |
| `get_total_quantity` | READ | No | Aggregation query |
| `consume_fifo` | MULTI | Yes | **CRITICAL** - FIFO consumption |
| `get_expiring_soon` | READ | No | Date filter query |
| `update_inventory_item` | SINGLE | No | Single UPDATE |
| `update_inventory_supplier` | MULTI | No | May create Purchase |
| `update_inventory_quantity` | SINGLE | Yes | Single UPDATE |
| `_convert_to_package_units` | READ | No | Pure function |
| `delete_inventory_item` | SINGLE | No | Single DELETE |
| `get_inventory_value` | READ | No | Aggregation (stub) |
| `get_recent_products` | READ | Yes | Recency query |
| `_get_recent_products_impl` | READ | Yes (required) | Implementation |
| `get_recent_ingredients` | READ | Yes | Recency query |
| `_get_recent_ingredients_impl` | READ | Yes (required) | Implementation |
| `manual_adjustment` | MULTI | Yes | Depletion + quantity update |
| `get_depletion_history` | READ | Yes | History query |

### purchase_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `record_purchase` | MULTI | Yes | **CRITICAL** - Purchase + InventoryItem |
| `_record_purchase_impl` | MULTI | Yes (required) | Implementation |
| `get_purchase` | READ | Yes | Eager load relations |
| `_get_purchase_impl` | READ | Yes (required) | Implementation |
| `get_purchase_history` | READ | No | Query with filters |
| `get_most_recent_purchase` | READ | No | Single SELECT |
| `calculate_average_price` | READ | No | Aggregation |
| `detect_price_change` | MULTI | No | Calls calculate_average_price |
| `get_price_trend` | READ | No | Linear regression |
| `get_last_price_at_supplier` | READ | Yes | Single SELECT |
| `_get_last_price_at_supplier_impl` | READ | Yes (required) | Implementation |
| `get_last_price_any_supplier` | READ | Yes | Single SELECT |
| `_get_last_price_any_supplier_impl` | READ | Yes (required) | Implementation |
| `delete_purchase` | MULTI | Yes | Cascade delete InventoryItems |
| `_delete_purchase_impl` | MULTI | Yes (required) | Implementation |
| `get_purchases_filtered` | READ | Yes | Complex filter query |
| `_get_purchases_filtered_impl` | READ | Yes (required) | Implementation |
| `get_remaining_inventory` | READ | Yes | Aggregation |
| `_get_remaining_inventory_impl` | READ | Yes (required) | Implementation |
| `can_edit_purchase` | READ | Yes | Validation check |
| `_can_edit_purchase_impl` | READ | Yes (required) | Implementation |
| `can_delete_purchase` | READ | Yes | Validation check |
| `_can_delete_purchase_impl` | READ | Yes (required) | Implementation |
| `update_purchase` | MULTI | Yes | Purchase + InventoryItem updates |
| `_update_purchase_impl` | MULTI | Yes (required) | Implementation |
| `get_purchase_usage_history` | READ | Yes | History query |
| `_get_purchase_usage_history_impl` | READ | Yes (required) | Implementation |

### batch_production_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `check_can_produce` | READ | Yes | **CRITICAL** - availability check |
| `_check_can_produce_impl` | READ | Yes (required) | Implementation |
| `record_batch_production` | MULTI | Yes | **CRITICAL** - Full production recording |

### assembly_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `check_can_assemble` | READ | Yes | **CRITICAL** - availability check |
| `_check_can_assemble_impl` | READ | Yes (required) | Implementation |
| `record_assembly` | MULTI | Yes | **CRITICAL** - Full assembly recording |
| `_record_assembly_impl` | MULTI | Yes (required) | Implementation |

### supplier_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `create_supplier` | SINGLE | No | Single INSERT |
| `get_supplier` | READ | No | Single SELECT |
| `get_all_suppliers` | READ | No | Query with filters |
| `update_supplier` | SINGLE | No | Single UPDATE |
| `delete_supplier` | MULTI | No | Check deps + delete |
| `check_supplier_dependencies` | READ | No | Multiple counts |
| `search_suppliers` | READ | No | Search query |

### event_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `create_event` | SINGLE | Yes | Single INSERT |
| `get_event` | READ | Yes | Eager load relations |
| `get_all_events` | READ | Yes | Query with filters |
| `update_event` | SINGLE | Yes | Single UPDATE |
| `delete_event` | MULTI | Yes | Cascade deletes |
| `add_production_target` | MULTI | Yes | May create snapshot |
| `update_production_target` | SINGLE | Yes | Single UPDATE |
| `remove_production_target` | SINGLE | Yes | Single DELETE |
| `add_assembly_target` | MULTI | Yes | May create snapshot |
| `update_assembly_target` | SINGLE | Yes | Single UPDATE |
| `remove_assembly_target` | SINGLE | Yes | Single DELETE |
| `get_event_progress` | READ | Yes | Complex aggregation |
| `get_event_recipients` | READ | Yes | Query with joins |
| `add_recipient_to_event` | SINGLE | Yes | Single INSERT |
| `remove_recipient_from_event` | SINGLE | Yes | Single DELETE |

### finished_good_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `create_finished_good` | MULTI | Yes | FG + compositions |
| `get_finished_good` | READ | Yes | Eager load relations |
| `get_all_finished_goods` | READ | Yes | Query with filters |
| `update_finished_good` | MULTI | Yes | FG + compositions |
| `delete_finished_good` | MULTI | Yes | Cascade deletes |
| `add_composition` | SINGLE | Yes | Single INSERT |
| `update_composition` | SINGLE | Yes | Single UPDATE |
| `remove_composition` | SINGLE | Yes | Single DELETE |
| `get_bill_of_materials` | READ | Yes | BOM query |
| `check_can_assemble` | READ | Yes | Availability check |
| `calculate_assembly_cost` | READ | Yes | Cost calculation |

### planning/planning_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `get_shopping_list` | READ | Yes | Complex aggregation |
| `get_production_schedule` | READ | Yes | Complex aggregation |
| `get_material_requirements` | READ | Yes | BOM explosion |
| `validate_plan_feasibility` | READ | Yes | Validation checks |

### Import/Export Services

#### import_export_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `export_all_data` | READ | No | Full export |
| `import_all_data` | MULTI | No | **CRITICAL** - Full import |
| `export_table` | READ | No | Single table export |
| `import_table` | MULTI | No | Single table import |
| `validate_import_data` | READ | No | Validation only |

#### enhanced_import_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `enhanced_import` | MULTI | Yes | Enhanced import with validation |
| `merge_import` | MULTI | Yes | Merge strategy import |
| `validate_enhanced_import` | READ | Yes | Pre-import validation |

#### transaction_import_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `import_with_transaction` | MULTI | Yes | Transactional import |
| `batch_import` | MULTI | Yes | Batch import |
| `rollback_import` | MULTI | Yes | Rollback support |

#### catalog_import_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `import_catalog` | MULTI | Yes | Catalog import |
| `validate_catalog_data` | READ | Yes | Validation only |

#### coordinated_export_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `export_coordinated_data` | READ | Yes | Consistent read export |
| `export_for_event` | READ | Yes | Event-scoped export |

#### denormalized_export_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `export_denormalized` | READ | Yes | Flat export format |
| `export_shopping_list` | READ | Yes | Shopping list export |

### Support Services

#### unit_service.py / unit_converter.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `convert_any_units` | READ | No | Pure conversion function |
| `get_conversion_factor` | READ | No | Lookup function |

#### preferences_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `get_preference` | READ | No | Single SELECT |
| `set_preference` | SINGLE | No | UPSERT operation |
| `get_all_preferences` | READ | No | Full query |

#### health_service.py

| Function | Type | Has Session Param? | Notes |
|----------|------|-------------------|-------|
| `check_database_health` | READ | No | Connection check |
| `get_system_stats` | READ | No | Aggregation query |

## Summary Statistics

| Category | Count |
|----------|-------|
| Total Public Functions | ~150+ |
| READ Functions | ~100 |
| SINGLE Functions | ~25 |
| MULTI Functions | ~25 |
| Functions with session param | ~60 |
| Functions needing session param | ~10 (identified gaps) |

## Critical MULTI Functions Requiring Detailed Documentation

These functions have complex transactional requirements:

1. **inventory_item_service.consume_fifo** - FIFO consumption algorithm
2. **purchase_service.record_purchase** - Purchase + InventoryItem atomicity
3. **batch_production_service.record_batch_production** - Full production recording
4. **assembly_service.record_assembly** - Full assembly recording
5. **import_export_service.import_all_data** - Full database import
6. **event_service.add_production_target** - Target + snapshot creation

## Notes

- All `_impl` functions are internal implementations and don't need public documentation
- Pure functions (no database access) may skip transaction boundary section
- Functions accepting `session=None` follow the session parameter pattern correctly
- Some functions listed may have additional variants not captured here
