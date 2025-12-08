# Service Contract: Import/Export Service (Packaging Extensions)

**Service**: `src/services/import_export_service.py`
**Feature**: 011-packaging-bom-foundation

## Export Changes

### export_ingredients_to_json

Include `is_packaging` field in ingredient export.

```python
# Exported ingredient structure:
{
    "id": 1,
    "display_name": "Cellophane Cookie Bags",
    "slug": "cellophane_cookie_bags",
    "category": "Bags",
    "recipe_unit": null,
    "is_packaging": true,  # NEW FIELD
    "description": "Clear bags for cookie dozens",
    "notes": null,
    # ... other fields ...
}
```

### export_compositions

Include `package_id` and `packaging_product_id` fields.

```python
# Exported composition structure:
{
    "id": 1,
    "assembly_id": 5,
    "package_id": null,  # NEW FIELD
    "finished_unit_id": 12,
    "finished_good_id": null,
    "packaging_product_id": null,  # NEW FIELD
    "component_quantity": 12.0,  # Now float
    "component_notes": null,
    "sort_order": 0
}

# Packaging composition example:
{
    "id": 2,
    "assembly_id": 5,
    "package_id": null,
    "finished_unit_id": null,
    "finished_good_id": null,
    "packaging_product_id": 23,  # References packaging product
    "component_quantity": 1.0,
    "component_notes": "One bag per dozen",
    "sort_order": 1
}
```

## Import Changes

### import_ingredients

Handle `is_packaging` field, defaulting to False for backward compatibility.

```python
def _import_ingredient(data: dict) -> Ingredient:
    """
    Import single ingredient.

    Handles:
    - is_packaging field (defaults to False if missing)
    """
    is_packaging = data.get("is_packaging", False)
    # ... rest of import logic ...
```

### import_compositions

Handle `package_id` and `packaging_product_id` fields.

```python
def _import_composition(data: dict) -> Composition:
    """
    Import single composition.

    Handles:
    - package_id field (null if missing)
    - packaging_product_id field (null if missing)
    - component_quantity as float (converts int to float)
    """
    package_id = data.get("package_id")
    packaging_product_id = data.get("packaging_product_id")
    quantity = float(data.get("component_quantity", 1.0))
    # ... rest of import logic ...
```

## Backward Compatibility

### Import from Old Format

| Field | Old Format | New Handling |
|-------|------------|--------------|
| `is_packaging` | Not present | Default to `False` |
| `package_id` | Not present | Default to `null` |
| `packaging_product_id` | Not present | Default to `null` |
| `component_quantity` | Integer | Convert to Float |

### Export Format (Current)

All exports use the new format. No backward compatibility mode for export (per spec FR-017: "backward compatibility with previous export versions is NOT required").

## Full Export Structure

```json
{
    "metadata": {
        "app_name": "Bake Tracker",
        "app_version": "0.6.0",
        "export_date": "2025-12-08T10:30:00Z",
        "format_version": "2.0"  # Increment for packaging support
    },
    "ingredients": [
        {
            "display_name": "All-Purpose Flour",
            "is_packaging": false,
            ...
        },
        {
            "display_name": "Cellophane Cookie Bags",
            "is_packaging": true,
            ...
        }
    ],
    "products": [...],
    "inventory_items": [...],
    "recipes": [...],
    "finished_units": [...],
    "finished_goods": [...],
    "compositions": [
        {
            "assembly_id": 1,
            "package_id": null,
            "finished_unit_id": 5,
            "finished_good_id": null,
            "packaging_product_id": null,
            "component_quantity": 12.0,
            ...
        },
        {
            "assembly_id": 1,
            "package_id": null,
            "finished_unit_id": null,
            "finished_good_id": null,
            "packaging_product_id": 23,
            "component_quantity": 1.0,
            ...
        }
    ],
    "packages": [...]
}
```

## Validation During Import

| Check | Action |
|-------|--------|
| `is_packaging` not boolean | Coerce to boolean, log warning |
| `packaging_product_id` references non-packaging product | Import anyway, log warning |
| `component_quantity` <= 0 | Reject record, log error |
| Both `assembly_id` and `package_id` set | Reject record, log error |
| Multiple component IDs set | Reject record, log error |

## Error Messages

| Error | Message |
|-------|---------|
| Invalid composition parent | "Composition must have exactly one parent (assembly_id or package_id)" |
| Invalid composition component | "Composition must have exactly one component type" |
| Invalid quantity | "Composition quantity must be greater than 0" |
| Product not packaging | "Warning: Product {id} is not marked as packaging but used in packaging composition" |
