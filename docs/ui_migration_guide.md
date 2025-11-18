# UI Migration Guide: FinishedGood → FinishedUnit

**Migration Period**: November 15, 2025 - December 15, 2025
**Status**: In Progress
**Version**: v0.4.0 → v0.5.0

## Overview

The Seasonal Baking Tracker is migrating from a single-tier `FinishedGood` model to a two-tier hierarchical system that better supports both individual items and package assemblies.

## Changes Summary

### New Two-Tier System

1. **FinishedUnit** - Individual consumable items (cookies, brownies, cakes, etc.)
2. **FinishedGood** - Package assemblies (gift boxes, variety packs, holiday sets, etc.)

### UI Components Migration

| Old Component | New Component | Purpose | Status |
|---------------|---------------|---------|--------|
| `FinishedGoodsTab` | `FinishedUnitsTab` | Individual items management | ✅ Migrated |
| `FinishedGoodFormDialog` | `FinishedUnitFormDialog` | Individual item editing | ✅ Migrated |
| `FinishedGoodsTab` | Enhanced `FinishedGoodsTab` | Assembly management | 🔄 Planned |

### Service Layer Changes

| Old Service | New Service | Purpose |
|-------------|-------------|---------|
| `finished_good_service` (for items) | `finished_unit_service` | Individual item operations |
| `finished_good_service` (for assemblies) | `finished_good_service` | Assembly operations |

## Migration Timeline

- **Phase 1** (Nov 15 - Nov 22): Core service migration ✅
- **Phase 2** (Nov 22 - Nov 29): UI component migration ✅
- **Phase 3** (Nov 29 - Dec 6): Assembly UI enhancement 🔄
- **Phase 4** (Dec 6 - Dec 13): Testing and validation 📋
- **Phase 5** (Dec 13 - Dec 15): Legacy cleanup 📋

## User Impact

### What Users Will See

1. **"Finished Goods" tab renamed to "Finished Units"**
   - Purpose: Manage individual consumable items
   - Functionality: Same CRUD operations, better performance
   - Data: All existing data preserved

2. **Enhanced "Bundles" tab** (Future)
   - Purpose: Manage package assemblies
   - Functionality: Create gift boxes, variety packs, etc.
   - New Features: Nested assemblies, component tracking

### What Stays the Same

- All existing data is preserved
- Core workflows remain identical
- Performance improvements are transparent
- No data entry format changes

## Developer Migration Guide

### For Custom Integrations

#### UI Components

**Old Pattern (Deprecated):**
```python
from src.ui.finished_goods_tab import FinishedGoodsTab

# This will show deprecation warnings
tab = FinishedGoodsTab(parent)
```

**New Pattern:**
```python
from src.ui.finished_units_tab import FinishedUnitsTab

# For individual items (cookies, brownies, etc.)
tab = FinishedUnitsTab(parent)
```

#### Service Calls

**Old Pattern (Deprecated):**
```python
from src.services import finished_good_service

# For individual items - NOW DEPRECATED
item = finished_good_service.create_finished_good({
    "name": "Chocolate Chip Cookie",
    "recipe_id": recipe.id,
    "items_per_batch": 24
})
```

**New Pattern:**
```python
from src.services import finished_unit_service

# For individual items - NEW APPROACH
unit = finished_unit_service.create_finished_unit(
    display_name="Chocolate Chip Cookie",
    recipe_id=recipe.id,
    items_per_batch=24,
    item_unit="cookie"
)
```

#### Assembly Operations

**New Pattern:**
```python
from src.services import finished_good_service

# For assemblies (gift boxes, etc.)
assembly = finished_good_service.create_finished_good(
    display_name="Holiday Cookie Gift Box",
    assembly_type=AssemblyType.GIFT_BOX,
    components=[
        {"component_type": "finished_unit", "component_id": unit1.id, "quantity": 6},
        {"component_type": "finished_unit", "component_id": unit2.id, "quantity": 4}
    ]
)
```

### Model Usage

**Old Pattern:**
```python
from src.models.finished_good import FinishedGood

# Individual items - NOW DEPRECATED for this use case
item = FinishedGood(name="Cookie", yield_mode="discrete_count")
```

**New Pattern:**
```python
from src.models.finished_unit import FinishedUnit
from src.models.finished_good import FinishedGood

# Individual items
unit = FinishedUnit(display_name="Cookie", yield_mode=YieldMode.DISCRETE_COUNT)

# Assemblies
assembly = FinishedGood(display_name="Gift Box", assembly_type=AssemblyType.GIFT_BOX)
```

## Deprecation Warnings

### Current Warnings

Starting in v0.4.0, the following components show deprecation warnings:

- `FinishedGoodsTab` (when used for individual items)
- `FinishedGoodFormDialog` (when used for individual items)
- Service calls using old patterns

### Warning Example

```
UserWarning: UI component 'FinishedGoodsTab' is deprecated and will be removed in v0.5.0.
Please migrate to 'FinishedUnitsTab'. This change supports the new two-tier
FinishedUnit/FinishedGood system. See migration guide for details.
```

## Migration Support

### Automatic Compatibility

- Legacy API calls continue to work with warnings
- Data migration is handled automatically
- UI falls back gracefully if components fail

### Rollback Plan

If issues arise:
1. Legacy components remain available until v0.5.0
2. Data can be restored from automatic backups
3. Service layer maintains compatibility mode

### Getting Help

1. **Check logs**: Deprecation warnings are logged with guidance
2. **Review examples**: See `tests/integration/test_ui_migration.py`
3. **Migration utility**: Use `python -m src.utils.migration_checker` to scan for deprecated usage

## Testing Your Migration

### Checklist

- [ ] Update imports to new components
- [ ] Test individual item workflows (create, edit, delete)
- [ ] Test search and filtering functionality
- [ ] Verify performance with your data volumes
- [ ] Check that deprecation warnings are resolved

### Validation Commands

```bash
# Check for deprecated usage patterns
python -m src.utils.migration_checker scan

# Run UI integration tests
pytest tests/integration/test_ui_migration.py

# Test performance with your data
python -m src.utils.performance_validator
```

## FAQ

### Q: Will my existing data be lost?
A: No. All data is preserved and automatically migrated to the new system.

### Q: Do I need to change how I create individual items?
A: The UI workflow remains identical. The underlying implementation is improved.

### Q: When will the old components stop working?
A: Legacy components will be removed in v0.5.0 (planned for December 15, 2025).

### Q: Can I still create assemblies/packages?
A: Yes, assembly functionality is enhanced in the new system with better hierarchy support.

### Q: What if I have custom code that uses the old APIs?
A: Follow the migration patterns in this guide. Old APIs work with warnings until v0.5.0.

## Support

For migration support or questions:
- Review deprecation warnings in your logs
- Check this guide for migration patterns
- Test changes in a development environment first
- Monitor the migration status dashboard (if available)

---

**Last Updated**: November 15, 2025
**Next Review**: November 22, 2025