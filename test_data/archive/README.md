# Archived Test Data

This directory contains archived test data files that use older (deprecated) formats.

## Files

- **test_data.json** - v1.0/v2.0 format test data
- **test_data_v2.json** - v2.0 format with 20 recipes from scanned sources
- **test_data_v2_original.json** - Original v1.0 format (deprecated)
- **ai_generated_sample.json** - AI-generated sample data (old format)

## Why Archived?

These files use the old v1.0/v2.0 import format which:
- Combined ingredients and products into a single entity
- Used `ingredient_name` instead of `ingredient_slug` in recipes
- Had different field names and structure

The current application uses **v3.4 format** which properly separates:
- Ingredients (generic types)
- Products (brand-specific items)
- Inventory items (actual stock)
- Purchases (transaction history)

## Can I Use These Files?

These files will **not import** into the current application. They are kept for:
- Historical reference
- Recipe data that could be manually converted
- Understanding the evolution of the data model

## Converting Old Data

If you need to use data from these files:
1. Review the v3.4 specification in `docs/design/import_export_specification.md`
2. Manually convert the structure to separate ingredients from products
3. Update recipe ingredients to use `ingredient_slug` references
