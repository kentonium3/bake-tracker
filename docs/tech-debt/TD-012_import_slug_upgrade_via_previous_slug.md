# TD-012: Import Does Not Upgrade Slugs via previous_slug

**Created**: 2026-01-28
**Priority**: High
**Effort**: Small
**Area**: src/services/enhanced_import_service.py
**Deferred Until**: Multi-tenant migration preparations

---

## Summary

The import service's `_find_existing_by_slug()` function only checks the CURRENT `slug` field, ignoring `previous_slug`. This prevents slug upgrades during import and will cause duplicate records when importing renamed entities, blocking proper multi-tenant data migration.

## Current State

```python
# src/services/enhanced_import_service.py:409
def _find_existing_by_slug(record, export_type, session):
    if entity_type == "recipe":
        return session.query(Recipe).filter(Recipe.slug == slug).first()
```

**Problem**: Only searches by current slug, doesn't check previous_slug fallback.

**Impact**:
```
Database State: Recipe(slug="old-name", previous_slug=NULL)
Import File:    {"slug": "new-name", "previous_slug": "old-name"}
Result:         Creates DUPLICATE recipe instead of finding via previous_slug
```

## Root Cause

The import service was implemented before F080 (Recipe slug support) and F082 (Product slug support) added the `previous_slug` migration pattern. The service layer functions `recipe_service.get_by_slug_or_previous_slug()` and similar already implement the correct fallback logic, but the import service doesn't use them.

The import service has its own entity lookup logic that predates the service layer's slug resolution functions.

## Proposed Solution

**Option 1: Use Service Layer Functions (Recommended)**

Update `_find_existing_by_slug()` to delegate to service layer:

```python
# src/services/enhanced_import_service.py
from src.services import recipe_service, product_service

def _find_existing_by_slug(record, export_type, session):
    slug = record.get("slug")
    if not slug:
        return None

    entity_type = _export_type_to_entity_type(export_type)

    if entity_type == "recipe":
        return recipe_service.get_by_slug_or_previous_slug(slug, session)
    elif entity_type == "product":
        # May need to implement if doesn't exist
        return product_service.get_by_slug_or_previous_slug(slug, session)
    # ... etc for all entities with previous_slug
```

**Option 2: Add Inline Fallback**

Add previous_slug fallback directly in `_find_existing_by_slug()`:

```python
# Try current slug first
existing = session.query(Recipe).filter(Recipe.slug == slug).first()
if not existing:
    # Fallback to previous_slug
    existing = session.query(Recipe).filter(Recipe.previous_slug == slug).first()
return existing
```

**Recommendation**: Option 1 (reuse service layer) maintains single source of truth and follows architectural patterns.

**Enhancement**: When found via previous_slug, optionally upgrade the slug:

```python
if existing and existing.slug != new_slug:
    # Upgrade slug if found via previous_slug
    existing.previous_slug = existing.slug
    existing.slug = new_slug
```

## Files to Modify

**Primary**:
- `src/services/enhanced_import_service.py` - Update `_find_existing_by_slug()` function

**Possibly Required**:
- `src/services/product_service.py` - Implement `get_by_slug_or_previous_slug()` if missing
- `src/services/finished_good_service.py` - Implement `get_by_slug_or_previous_slug()` if missing
- `src/services/finished_unit_service.py` - Implement `get_by_slug_or_previous_slug()` if missing

**Testing**:
- Add test: `test_import_finds_recipe_by_previous_slug()`
- Add test: `test_import_upgrades_slug_from_previous()`
- Add test: `test_export_import_roundtrip_with_rename()`

## Acceptance Criteria

- [ ] Import finds entities by current slug OR previous_slug
- [ ] No duplicate records created when importing renamed entities
- [ ] Export → Rename → Import → Export cycle preserves data
- [ ] Slug upgrade happens when found via previous_slug (optional enhancement)
- [ ] All affected entities support previous_slug resolution (Recipe, Product, etc.)
- [ ] Unit tests cover previous_slug fallback scenarios
- [ ] Integration test validates full export/import cycle with renames

## Multi-Tenant Migration Impact

**Current Risk**: Without this fix, desktop-to-cloud migration will:
1. Fail to match renamed entities (slug changed between exports)
2. Create duplicate records for renamed recipes/products
3. Break FK references that rely on slug resolution
4. Propagate stale slugs instead of upgrading to current values

**With Fix**: Clean migration path where renamed entities are properly matched and slugs are upgraded during import.

## Related Items

- F080: Recipe Slug Support - Added slug + previous_slug fields
- F082: Product Slug Implementation - Added slug + previous_slug fields
- Data Portability Review (2026-01-28) - Identified multi-tenant migration requirements
- Data Portability Follow-up (2026-01-28) - Verified F080-F083 implementation

## Notes

This is deferred until multi-tenant migration preparations begin because:
1. Current desktop app doesn't experience the duplicate issue (single-user, no cross-export imports)
2. F080/F082 implementation is complete and working for normal use cases
3. Bug only manifests during import of exports with renamed entities
4. Multi-tenant migration is the primary use case that requires robust slug upgrade logic

**Timeline**: Address during multi-tenant POC preparation (estimated Q2 2026)
**Estimated Effort**: 4-6 hours (implementation + testing)
**Risk if Deferred**: Medium - doesn't affect current desktop app, but will cause migration issues
