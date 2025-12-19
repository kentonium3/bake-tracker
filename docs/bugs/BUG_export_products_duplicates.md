# BUG: Export Products Generates Duplicate Rows

## Context

Refer to `.kittify/memory/constitution.md` for project principles.

## Bug Report

When exporting products, the export function generates duplicate product rows if multiple inventory items exist for the same product.

### Observed Behavior

- User has 2 inventory items for "Domino sugar_granulated 4 lb"
- Export generates 2 identical rows for this product
- This causes confusion when reviewing/editing exported data

### Expected Behavior

- Export should generate unique product rows only
- Product export should not be influenced by inventory item count
- One row per unique product (brand + ingredient_slug + package_unit + package_unit_quantity + product_name)

### Root Cause Investigation

Check `src/services/import_export_service.py` export functions:
1. Look for product export logic
2. Check if it's iterating over inventory items instead of distinct products
3. May need to add DISTINCT or GROUP BY to the query

### Suggested Fix

- Query products directly rather than through inventory items
- Or add deduplication logic before writing rows
- Ensure product export uses unique constraint fields for deduplication

## Priority

Low - Data integrity not affected, just export convenience

## Discovered

2025-12-19 during product data cleanup
