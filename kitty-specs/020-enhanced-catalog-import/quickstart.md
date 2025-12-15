# Quickstart: Enhanced Catalog Import

**Feature**: 020-enhanced-catalog-import
**Date**: 2025-12-14

## Quick Reference

### CLI Usage

```bash
# Import full catalog (add mode - default)
python -m src.utils.import_catalog catalog.json

# Import specific entity types
python -m src.utils.import_catalog catalog.json --entity=ingredients
python -m src.utils.import_catalog catalog.json --entity=products
python -m src.utils.import_catalog catalog.json --entity=recipes

# Augment existing records (fill null fields)
python -m src.utils.import_catalog catalog.json --entity=ingredients --mode=augment

# Preview changes without committing
python -m src.utils.import_catalog catalog.json --dry-run

# Verbose output
python -m src.utils.import_catalog catalog.json --verbose
```

### UI Access

1. Open application
2. File menu > Import Catalog...
3. Select catalog JSON file
4. Choose mode (Add Only / Augment)
5. Optionally check "Preview changes"
6. Click Import (or Preview)

---

## File Structure

```
src/
  services/
    catalog_import_service.py    # NEW: Service logic
  utils/
    import_catalog.py            # NEW: CLI entry point
  ui/
    catalog_import_dialog.py     # NEW: UI dialog
    main_window.py               # MODIFIED: Add menu item
```

---

## Catalog File Format

Minimal example:

```json
{
  "catalog_version": "1.0",
  "ingredients": [
    {
      "slug": "all_purpose_flour",
      "display_name": "All-Purpose Flour",
      "category": "Flour"
    }
  ]
}
```

Full example with all entity types:

```json
{
  "catalog_version": "1.0",
  "generated_at": "2025-12-14T10:00:00Z",
  "ingredients": [
    {
      "slug": "all_purpose_flour",
      "display_name": "All-Purpose Flour",
      "category": "Flour",
      "density_volume_value": 1.0,
      "density_volume_unit": "cup",
      "density_weight_value": 4.25,
      "density_weight_unit": "oz"
    }
  ],
  "products": [
    {
      "ingredient_slug": "all_purpose_flour",
      "brand": "King Arthur",
      "package_size": "5 lb",
      "purchase_unit": "bag",
      "purchase_quantity": 1.0
    }
  ],
  "recipes": [
    {
      "name": "Simple Cookies",
      "category": "Cookies",
      "yield_quantity": 24,
      "yield_unit": "cookies",
      "ingredients": [
        {"ingredient_slug": "all_purpose_flour", "quantity": 2.0, "unit": "cup"}
      ]
    }
  ]
}
```

---

## Import Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `add` (default) | Create new, skip existing | Expanding catalog |
| `augment` | Update null fields, add new | Enriching metadata |

**Note**: `augment` mode is NOT supported for recipes.

---

## Common Tasks

### Import sample catalog

```bash
python -m src.utils.import_catalog test_data/sample_catalog.json --verbose
```

### Add density data to existing ingredients

```bash
python -m src.utils.import_catalog density_enrichment.json \
    --entity=ingredients \
    --mode=augment
```

### Preview recipe import before committing

```bash
python -m src.utils.import_catalog ai_recipes.json \
    --entity=recipes \
    --dry-run
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (all processed) |
| 1 | Partial success (some failed) |
| 2 | Complete failure |
| 3 | Invalid arguments/file |

---

## Error Handling

Import continues after individual record failures (partial success). Check the summary report for:
- **Added**: New records created
- **Skipped**: Existing records (unchanged)
- **Augmented**: Existing records updated (AUGMENT mode only)
- **Failed**: Records with validation errors

Each failure includes:
- Entity type and identifier
- Specific error description
- Suggested fix action
