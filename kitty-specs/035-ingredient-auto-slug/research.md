# Research: Ingredient Auto-Slug & Deletion Protection

**Feature**: 035-ingredient-auto-slug
**Date**: 2026-01-02
**Status**: Complete

## Executive Summary

Research revealed significant existing infrastructure that changes the implementation scope:

| Component | Expected | Actual Finding | Impact |
|-----------|----------|----------------|--------|
| Slug Generation | Build new | **Already exists** in `src/utils/slug_utils.py` | Reduced scope |
| Slug in Service | Need to add | **Already integrated** in `ingredient_service.create_ingredient()` | Reduced scope |
| Clear Filters | Need to add | **Already exists** from F034 | Remove from scope |
| Deletion Protection | Need to add | Partial - only checks recipes, not products | As expected |
| Historical Denormalization | Need to add | Not implemented | As expected |

## Research Findings

### 1. Slug Generation Utility - ALREADY EXISTS

**Location**: `src/utils/slug_utils.py`

**Key Function**: `create_slug(name: str, session: Optional[Session] = None) -> str`

**Features**:
- Unicode normalization (NFD decomposition)
- ASCII transliteration (handles accented characters like "Creme Brulee")
- Lowercase with underscores (not hyphens)
- Auto-increment suffixes for uniqueness: `flour`, `flour_1`, `flour_2`, etc.
- Session-based uniqueness checking against Ingredient table

**Decision**: Reuse existing utility. No new slug generation code needed.

### 2. Slug Integration in Service - PARTIALLY EXISTS

**Location**: `src/services/ingredient_service.py:188`

```python
slug = create_slug(ingredient_data["display_name"], session)
```

**Issue Found**: Field name mismatch
- UI form (`ingredients_tab.py:1341`) sends `result["name"]`
- Service expects `ingredient_data["display_name"]`
- Validator (`validators.py:261`) checks `data.get("display_name")`

**Decision**: Fix field mapping to ensure consistent use of "display_name" or add normalization layer.

**Alternatives Considered**:
1. Fix UI to send "display_name" - requires UI changes
2. Fix service to accept both - adds complexity
3. Add normalization in service - cleanest solution

**Rationale**: Option 3 (normalization) is safest - backward compatible and doesn't break existing code.

### 3. Deletion Protection - INCOMPLETE

**Current Implementation**: `src/services/ingredient_crud_service.py:215`

```python
def delete_ingredient(ingredient_id: int, force: bool = False) -> bool:
    # Only checks RecipeIngredient - MISSING Product check!
    recipe_count = session.query(RecipeIngredient).filter_by(ingredient_id=ingredient_id).count()
```

**Also in**: `src/services/ingredient_service.py:465` - `delete_ingredient(slug: str)`

**Missing Checks**:
- Product references (`Product.ingredient_id`)
- SnapshotIngredient references (`SnapshotIngredient.ingredient_id`)
- Child ingredients (hierarchy validation)

**FK Constraints Found**:
- `SnapshotIngredient.ingredient_id` has `ondelete="RESTRICT"` - will block deletion at DB level
- Need to handle this gracefully with denormalization before deletion

**Decision**: Create new comprehensive deletion service that:
1. Checks Product count (block if > 0)
2. Checks RecipeIngredient count (block if > 0)
3. Checks child count (block if > 0) - already exists from F033
4. For SnapshotIngredient: denormalize names, nullify FK, then allow deletion

### 4. SnapshotIngredient Model - NEEDS SCHEMA UPDATE

**Current Schema** (`src/models/inventory_snapshot.py`):

```python
class SnapshotIngredient(BaseModel):
    snapshot_id = Column(Integer, ForeignKey("inventory_snapshots.id", ondelete="CASCADE"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"))
    quantity = Column(Float, nullable=False, default=0.0)
```

**Required Changes**:
- Add `ingredient_name_snapshot` (String, nullable)
- Add `parent_l1_name_snapshot` (String, nullable)
- Add `parent_l0_name_snapshot` (String, nullable)
- Change `ingredient_id` FK to `ondelete="SET NULL"` (allow nullification after denormalization)

### 5. Clear Filters - ALREADY IMPLEMENTED

**Finding**: F034 already implemented Clear Filters buttons!

**Products Tab** (`src/ui/products_tab.py:194-198`):
```python
# Feature 034: Clear Filters button
self.clear_filters_button = ctk.CTkButton(
    filter_frame, text="Clear", width=60,
    command=self._clear_filters,
)
```

**Inventory Tab** (`src/ui/inventory_tab.py:189-193`):
```python
# Feature 034: Clear Filters button
self.clear_filters_button = ctk.CTkButton(
    filter_frame, text="Clear", width=60,
    command=self._clear_hierarchy_filters,
)
```

**Decision**: Remove Clear Filters from F035 scope - already done.

### 6. Cascade Delete Configuration

**Entities that should CASCADE delete**:
- `IngredientAlias` - check current config
- `IngredientCrosswalk` - check current config

**Verification Complete** (2026-01-02):

| Model | FK Column | Configuration | Status |
|-------|-----------|---------------|--------|
| IngredientAlias | `ingredient_id` | `ForeignKey("ingredients.id", ondelete="CASCADE")` | PRESENT |
| IngredientCrosswalk | `ingredient_id` | `ForeignKey("ingredients.id", ondelete="CASCADE")` | PRESENT |

**Findings**:
- Both models already have `ondelete="CASCADE"` configured on their `ingredient_id` foreign keys
- No changes required - cascade deletes will work automatically when parent ingredient is deleted
- Verified in `src/models/ingredient_alias.py` (lines 32-34) and `src/models/ingredient_crosswalk.py` (lines 34-36)

## Updated Scope

Based on research, the revised feature scope is:

### In Scope (Revised)

1. **Fix slug field mapping** - Ensure UI "name" field maps to service "display_name"
2. **Enhance deletion protection** - Add Product reference check to deletion service
3. **Implement historical denormalization** - Add 3 snapshot fields, denormalize before delete
4. **Configure cascade deletes** - Ensure Alias and Crosswalk cascade properly

### Out of Scope (Removed)

- **Slug generation utility** - Already exists
- **Clear Filters buttons** - Already implemented in F034

## Open Questions

1. Should the existing `ingredient_crud_service.delete_ingredient()` be enhanced or replaced by `ingredient_service.delete_ingredient()`?
   - **Recommendation**: Enhance `ingredient_service.delete_ingredient()` as the authoritative implementation

2. Is there test data with SnapshotIngredient records to validate the denormalization flow?
   - **Action**: Check during implementation, may need to create test fixtures

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Schema change breaks existing data | Low | High | Export/import cycle per constitution |
| Field mapping fix breaks other callers | Medium | Medium | Add normalization layer, don't remove "name" support |
| Cascade delete misconfigured | Low | High | Verify with tests before merge |

## Files to Modify

### Service Layer
- `src/services/ingredient_service.py` - Add deletion protection, field normalization

### Model Layer
- `src/models/inventory_snapshot.py` - Add 3 denormalization fields, change FK constraint
- `src/models/ingredient_alias.py` - Verify cascade delete config
- `src/models/ingredient_crosswalk.py` - Verify cascade delete config

### Test Layer
- `src/tests/services/test_ingredient_service.py` - Add deletion protection tests
- New: `src/tests/services/test_ingredient_deletion.py` - Comprehensive deletion tests
