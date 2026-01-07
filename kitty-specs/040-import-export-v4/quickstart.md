# Quickstart: Import/Export v4.0 Upgrade

**Feature**: 040-import-export-v4
**Date**: 2026-01-06

## TL;DR

Upgrade `import_export_service.py` to v4.0 format supporting F037 recipe variants and F039 event output_mode. Add two new BT Mobile import functions for UPC-based purchases and percentage-based inventory updates.

## Key Files

| File | Purpose |
|------|---------|
| `src/services/import_export_service.py` | All import/export logic |
| `src/ui/dialogs/upc_resolution_dialog.py` | NEW: UPC resolution UI |
| `src/tests/services/test_import_export_service.py` | Tests |
| `test_data/sample_data.json` | Update to v4.0 format |

## Quick Reference

### Recipe Export Changes (WP01)

```python
# Add to recipe dict in export_recipes_to_json():
recipe_dict["base_recipe_slug"] = (
    session.query(Recipe).filter_by(id=recipe.base_recipe_id).first().slug
    if recipe.base_recipe_id else None
)
recipe_dict["variant_name"] = recipe.variant_name
recipe_dict["is_production_ready"] = recipe.is_production_ready
recipe_dict["finished_units"] = [
    {
        "slug": fu.slug,
        "name": fu.name,
        "yield_mode": fu.yield_mode.value if fu.yield_mode else None,
        "unit_yield_quantity": fu.unit_yield_quantity,
        "unit_yield_unit": fu.unit_yield_unit,
    }
    for fu in recipe.finished_units
]
```

### Recipe Import Changes (WP02)

```python
# In import recipe function:
# 1. Import base recipes first (where base_recipe_slug is None)
# 2. Then import variants (resolve base_recipe_slug to base_recipe_id)

if recipe_data.get("base_recipe_slug"):
    base_recipe = session.query(Recipe).filter_by(
        slug=recipe_data["base_recipe_slug"]
    ).first()
    if not base_recipe:
        result.add_error("recipe", recipe_data["name"],
            f"Base recipe not found: {recipe_data['base_recipe_slug']}")
        continue
    recipe.base_recipe_id = base_recipe.id

recipe.variant_name = recipe_data.get("variant_name")
recipe.is_production_ready = recipe_data.get("is_production_ready", False)
```

### Event Export Changes (WP03)

```python
# Add to event dict:
event_dict["output_mode"] = event.output_mode.value if event.output_mode else None
```

### New Function Signatures (WP05, WP07)

```python
def import_purchases_from_bt_mobile(file_path: str) -> ImportResult:
    """
    Import purchases from BT Mobile JSON file.

    Args:
        file_path: Path to JSON file with schema_version="4.0", import_type="purchases"

    Returns:
        ImportResult with matched/unmatched/error counts
    """

def import_inventory_updates_from_bt_mobile(file_path: str) -> ImportResult:
    """
    Import inventory updates from BT Mobile JSON file.

    Args:
        file_path: Path to JSON file with schema_version="4.0", import_type="inventory_updates"

    Returns:
        ImportResult with update/skip/error counts
    """
```

### Percentage Calculation (WP07)

```python
def calculate_percentage_adjustment(
    inventory_item: InventoryItem,
    remaining_percentage: int
) -> Decimal:
    """
    Calculate quantity adjustment from percentage.

    Example:
        original = 25 lbs (from purchase)
        current = 18 lbs
        percentage = 30%
        target = 25 * 0.30 = 7.5 lbs
        adjustment = 7.5 - 18 = -10.5 lbs (depletion)
    """
    purchase = inventory_item.purchase
    original = purchase.quantity_purchased
    target = original * (Decimal(remaining_percentage) / Decimal(100))
    return target - inventory_item.current_quantity
```

## Testing Commands

```bash
# Run all import/export tests
pytest src/tests/services/test_import_export_service.py -v

# Run specific test class
pytest src/tests/services/test_import_export_service.py::TestRecipeExportV4 -v

# Run with coverage
pytest src/tests/services/test_import_export_service.py --cov=src/services/import_export_service
```

## Validation Checklist

- [ ] Version "4.0" in exported files
- [ ] Recipe base_recipe_slug resolves correctly
- [ ] Recipe finished_units include yield_mode
- [ ] Event output_mode exported and validated
- [ ] UPC matching finds products
- [ ] Unknown UPCs collected for resolution
- [ ] Percentage calculation matches manual calculation
- [ ] FIFO ordering for inventory updates
- [ ] Atomic rollback on errors

## Common Gotchas

1. **Import Order**: Base recipes must be imported before variants
2. **Session Management**: Pass session to inner functions (see CLAUDE.md)
3. **Decimal Precision**: Use `Decimal(str(value))` not `Decimal(value)` for floats
4. **FIFO**: Order by `purchase_date.asc()` for oldest first
