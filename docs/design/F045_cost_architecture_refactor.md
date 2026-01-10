# Cost Architecture Refactor - Feature Specification

**Feature ID**: F045
**Feature Name**: Cost Architecture Refactor (Definitions vs Instances)
**Priority**: P0 - FOUNDATIONAL ARCHITECTURE (blocks F046-F048)
**Status**: Design Specification
**Created**: 2026-01-09
**Dependencies**: F044 (Finished Units Functionality & UI ✅)
**Blocks**: F046 (Finished Goods), F047 (Shopping Lists), F048 (Assembly), Event Planning
**Constitutional References**: Principle III (Data Integrity), Principle V (Layered Architecture)

---

## Important Note on Specification Approach

**This document contains detailed technical illustrations** including code samples, migration scripts, and implementation patterns. These are provided as **examples and guidance**, not as prescriptive implementations.

**When using spec-kitty to implement this feature:**
- The code samples are **illustrative** - they show one possible approach
- Spec-kitty should **validate and rationalize** the technical approach during its planning phase
- Spec-kitty may **modify or replace** these examples based on:
  - Current codebase patterns and conventions
  - Better architectural approaches discovered during analysis
  - Constitution compliance verification

**The requirements are the source of truth** - the technical implementation details should be determined by spec-kitty's specification and planning phases.

---

## Executive Summary

**Problem**: Current architecture stores costs as fields in definition models (FinishedUnit, FinishedGood), creating cascading staleness when ingredient prices change. Stored costs become outdated but remain in database, causing data integrity issues and user confusion.

**Root Cause**: 
- FinishedUnit has `unit_cost` field (stored, becomes stale)
- FinishedGood has `total_cost` field (stored, becomes stale)
- No automatic synchronization when upstream costs change (purchases, recipe edits)
- Stored costs displayed in UI, confusing users when values don't match reality

**Solution**: Remove stored costs from definition models. Calculate costs dynamically on-demand from current inventory (FIFO basis). Store costs only on instance models (events, production runs, assembly runs) as point-in-time snapshots.

**Philosophy**: **"Costs on Instances, Not Definitions"**
- Definitions (recipes, finished units, finished goods) have no inherent cost
- Costs only exist when instantiated for actual production/assembly
- Current costs calculated fresh from FIFO inventory whenever needed
- Historical costs captured as immutable snapshots on production/assembly records

**Impact**:
- Eliminates data integrity issues (no stale costs)
- Simplifies maintenance (no synchronization burden)
- Provides foundation for accurate event planning, cost reports
- Breaking change: Requires database migration, UI updates, import/export updates

**Scope**:
- Remove `unit_cost` from FinishedUnit model
- Remove `total_cost` from FinishedGood model
- Add dynamic cost calculation methods
- Remove cost columns from catalog UI views
- Update import/export services (remove cost fields from JSON)
- Update sample data files (remove cost fields)
- Database migration (drop columns, no data loss)
- **NO backward compatibility**: Old exports must be externally refactored

---

## Import/Export Philosophy

**Clean Break Approach**: We are NOT maintaining backward compatibility with old export formats. 

**Rationale**:
- Application is changing rapidly during development
- Maintaining multiple import versions adds complexity
- Old exports can be externally refactored to match current spec
- Simpler codebase = fewer bugs, easier maintenance

**User Impact**:
- Users with old exports must manually update JSON files before importing
- Clear error messages guide users to fix format issues
- Documentation explains version 4.1 changes

**Implementation Strategy**:
- Import service validates structure strictly
- Import service REJECTS files with deprecated fields
- Clear error messages: "Field 'unit_cost' no longer supported in version 4.1"
- No warning logs, no silent ignoring - fail fast with helpful message

---

[Sections 1-10 from original spec remain here - I'll include the key ones below]

---

## 11. Import/Export Impact

### 11.1 Affected Data Files

**Sample Data Files (Remove Cost Fields):**
- `test_data/sample_data_min.json`
- `test_data/sample_data_all.json`

**Catalog Files (No Changes - recipes already don't store costs):**
- `test_data/recipes_catalog.json` - No changes needed (recipes calculate costs)
- `test_data/products_catalog.json` - No changes needed
- `test_data/ingredients_catalog.json` - No changes needed

**View Files (No Cost Fields):**
- `test_data/view_inventory.json` - No changes needed
- `test_data/view_products.json` - No changes needed
- `test_data/view_purchases.json` - No changes needed

### 11.2 Export Service Changes

**File**: `src/services/export_service.py` (or similar)

**BEFORE (exports stored costs):**
```python
def export_finished_units(session) -> List[Dict]:
    """Export finished units to JSON."""
    finished_units = session.query(FinishedUnit).all()
    return [
        {
            "slug": fu.slug,
            "display_name": fu.display_name,
            "items_per_batch": fu.items_per_batch,
            "recipe_slug": fu.recipe.slug if fu.recipe else None,
            "unit_cost": float(fu.unit_cost),  # REMOVE THIS
        }
        for fu in finished_units
    ]

def export_finished_goods(session) -> List[Dict]:
    """Export finished goods to JSON."""
    finished_goods = session.query(FinishedGood).all()
    return [
        {
            "slug": fg.slug,
            "display_name": fg.display_name,
            "assembly_type": fg.assembly_type.value,
            "total_cost": float(fg.total_cost),  # REMOVE THIS
            "components": [...]
        }
        for fg in finished_goods
    ]
```

**AFTER (no cost fields exported):**
```python
def export_finished_units(session) -> List[Dict]:
    """Export finished units to JSON (version 4.1+)."""
    finished_units = session.query(FinishedUnit).all()
    return [
        {
            "slug": fu.slug,
            "display_name": fu.display_name,
            "items_per_batch": fu.items_per_batch,
            "recipe_slug": fu.recipe.slug if fu.recipe else None,
            # NO unit_cost field
        }
        for fu in finished_units
    ]

def export_finished_goods(session) -> List[Dict]:
    """Export finished goods to JSON (version 4.1+)."""
    finished_goods = session.query(FinishedGood).all()
    return [
        {
            "slug": fg.slug,
            "display_name": fg.display_name,
            "assembly_type": fg.assembly_type.value,
            # NO total_cost field
            "components": [...]
        }
        for fg in finished_goods
    ]
```

### 11.3 Import Service Changes (Strict Validation)

**File**: `src/services/import_service.py` (or similar)

**BEFORE (accepts stored costs):**
```python
def import_finished_unit(session, data: Dict) -> FinishedUnit:
    """Import finished unit from JSON."""
    fu = FinishedUnit(
        slug=data["slug"],
        display_name=data["display_name"],
        items_per_batch=data["items_per_batch"],
        recipe_id=get_recipe_id_by_slug(session, data.get("recipe_slug")),
        unit_cost=Decimal(str(data.get("unit_cost", 0.0))),  # REMOVE THIS
    )
    return fu
```

**AFTER (rejects files with cost fields):**
```python
def import_finished_unit(session, data: Dict) -> FinishedUnit:
    """Import finished unit from JSON (version 4.1+)."""
    
    # STRICT VALIDATION: Reject deprecated fields
    if "unit_cost" in data:
        raise ImportError(
            f"FinishedUnit '{data.get('slug', 'unknown')}' contains deprecated field 'unit_cost'. "
            f"This field is no longer supported in version 4.1. "
            f"Costs are now calculated dynamically from recipes. "
            f"Please remove 'unit_cost' from your import file."
        )
    
    fu = FinishedUnit(
        slug=data["slug"],
        display_name=data["display_name"],
        items_per_batch=data["items_per_batch"],
        recipe_id=get_recipe_id_by_slug(session, data.get("recipe_slug")),
        # NO unit_cost field
    )
    return fu

def import_finished_good(session, data: Dict) -> FinishedGood:
    """Import finished good from JSON (version 4.1+)."""
    
    # STRICT VALIDATION: Reject deprecated fields
    if "total_cost" in data:
        raise ImportError(
            f"FinishedGood '{data.get('slug', 'unknown')}' contains deprecated field 'total_cost'. "
            f"This field is no longer supported in version 4.1. "
            f"Costs are now calculated dynamically from components. "
            f"Please remove 'total_cost' from your import file."
        )
    
    fg = FinishedGood(
        slug=data["slug"],
        display_name=data["display_name"],
        assembly_type=AssemblyType(data["assembly_type"]),
        # NO total_cost field
    )
    return fg
```

**Key Points**:
- Import service **rejects** files with deprecated cost fields
- Clear error messages explain what's wrong and how to fix it
- Users must update their export files before importing
- No silent ignoring, no backward compatibility complexity

### 11.4 Sample Data File Updates

**File**: `test_data/sample_data_min.json`

**BEFORE (if costs exist in finished_units array):**
```json
{
  "finished_units": [
    {
      "slug": "large-cookie-cookie-dough",
      "display_name": "Large Cookie",
      "items_per_batch": 30,
      "recipe_slug": "cookie-dough",
      "unit_cost": 0.42
    }
  ]
}
```

**AFTER (remove unit_cost):**
```json
{
  "finished_units": [
    {
      "slug": "large-cookie-cookie-dough",
      "display_name": "Large Cookie",
      "items_per_batch": 30,
      "recipe_slug": "cookie-dough"
    }
  ]
}
```

**File**: `test_data/sample_data_all.json`

Same changes - remove `unit_cost` from all finished_units entries, remove `total_cost` from all finished_goods entries (if present).

### 11.5 Export Format Version Bump

**Update export format version to indicate breaking change:**

```python
def export_data(session) -> Dict:
    """Export all data with version."""
    return {
        "version": "4.1",  # Bump from 4.0 → 4.1 (BREAKING CHANGE)
        "exported_at": datetime.now().isoformat(),
        "application": "bake-tracker",
        "products": export_products(session),
        "recipes": export_recipes(session),
        "finished_units": export_finished_units(session),  # No cost fields
        "finished_goods": export_finished_goods(session),  # No cost fields
        # ... other data
    }
```

**Version 4.1 Changes (BREAKING):**
- Removed `finished_units[].unit_cost` field
- Removed `finished_goods[].total_cost` field
- Costs now calculated dynamically on-demand
- Old exports (v4.0) will be rejected with clear error messages

### 11.6 Import Validation

**Validate version and reject old formats:**

```python
def import_data(data: Dict) -> None:
    """Import data with strict version checking."""
    version = data.get("version", "unknown")
    
    # Check version compatibility
    if version == "4.0":
        raise ImportError(
            f"Import file is version {version}, but application requires version 4.1+. "
            f"Version 4.1 removed stored cost fields (unit_cost, total_cost). "
            f"Please update your export file:\n"
            f"  1. Remove 'unit_cost' from all finished_units entries\n"
            f"  2. Remove 'total_cost' from all finished_goods entries\n"
            f"  3. Update 'version' field to '4.1'"
        )
    
    if version < "4.1":
        raise ImportError(
            f"Import file version {version} is not supported. "
            f"Application requires version 4.1 or higher."
        )
    
    # Proceed with import...
```

---

## 12. Testing Import/Export

### 12.1 Export Tests

**Test: Export Does Not Include Cost Fields**
```python
def test_export_finished_units_excludes_unit_cost():
    """Verify exported finished units don't have unit_cost field."""
    with session_scope() as session:
        fu = create_test_finished_unit(session)
        exported = export_finished_units(session)
        fu_data = next(item for item in exported if item["slug"] == fu.slug)
        assert "unit_cost" not in fu_data, "Exported data should not include unit_cost"

def test_export_finished_goods_excludes_total_cost():
    """Verify exported finished goods don't have total_cost field."""
    with session_scope() as session:
        fg = create_test_finished_good(session)
        exported = export_finished_goods(session)
        fg_data = next(item for item in exported if item["slug"] == fg.slug)
        assert "total_cost" not in fg_data, "Exported data should not include total_cost"

def test_export_version_is_4_1():
    """Verify export version bumped to 4.1."""
    with session_scope() as session:
        exported = export_data(session)
        assert exported["version"] == "4.1", "Export version should be 4.1"
```

### 12.2 Import Tests (Strict Rejection)

**Test: Import Rejects Files With Cost Fields**
```python
def test_import_finished_unit_rejects_unit_cost():
    """Verify import rejects finished_units with unit_cost field."""
    with session_scope() as session:
        # Old format data (with unit_cost)
        old_data = {
            "slug": "test-cookie",
            "display_name": "Test Cookie",
            "items_per_batch": 30,
            "recipe_slug": "test-recipe",
            "unit_cost": 0.42  # DEPRECATED - should be rejected
        }
        
        # Import should raise error
        with pytest.raises(ImportError) as exc_info:
            import_finished_unit(session, old_data)
        
        # Verify error message is helpful
        assert "unit_cost" in str(exc_info.value).lower()
        assert "4.1" in str(exc_info.value)
        assert "remove" in str(exc_info.value).lower()

def test_import_finished_good_rejects_total_cost():
    """Verify import rejects finished_goods with total_cost field."""
    with session_scope() as session:
        # Old format data (with total_cost)
        old_data = {
            "slug": "test-box",
            "display_name": "Test Box",
            "assembly_type": "gift_box",
            "total_cost": 8.50  # DEPRECATED - should be rejected
        }
        
        # Import should raise error
        with pytest.raises(ImportError) as exc_info:
            import_finished_good(session, old_data)
        
        # Verify error message is helpful
        assert "total_cost" in str(exc_info.value).lower()
        assert "4.1" in str(exc_info.value)
        assert "remove" in str(exc_info.value).lower()

def test_import_rejects_version_4_0():
    """Verify import rejects version 4.0 files."""
    old_export = {
        "version": "4.0",
        "exported_at": "2026-01-01T00:00:00Z",
        "finished_units": [...]
    }
    
    with pytest.raises(ImportError) as exc_info:
        import_data(old_export)
    
    assert "4.0" in str(exc_info.value)
    assert "4.1" in str(exc_info.value)
    assert "remove" in str(exc_info.value).lower()
```

**Test: Import Accepts Clean 4.1 Format**
```python
def test_import_finished_unit_accepts_clean_format():
    """Verify import accepts finished_units without cost fields."""
    with session_scope() as session:
        # Version 4.1 format (no cost fields)
        clean_data = {
            "slug": "test-cookie",
            "display_name": "Test Cookie",
            "items_per_batch": 30,
            "recipe_slug": "test-recipe"
            # NO unit_cost field
        }
        
        # Import should succeed
        fu = import_finished_unit(session, clean_data)
        
        # Verify
        assert fu.display_name == "Test Cookie"
        assert fu.items_per_batch == 30
        assert not hasattr(fu, "unit_cost")
```

### 12.3 Sample Data Validation

**Test: Sample Data Files Are Clean**
```python
def test_sample_data_min_has_no_cost_fields():
    """Verify sample_data_min.json is version 4.1 format."""
    import json
    
    with open("test_data/sample_data_min.json") as f:
        data = json.load(f)
    
    # Check version
    assert data.get("version") == "4.1", "Sample data should be version 4.1"
    
    # Check finished_units
    if "finished_units" in data:
        for fu in data["finished_units"]:
            assert "unit_cost" not in fu, \
                f"FinishedUnit '{fu.get('slug')}' should not have unit_cost"
    
    # Check finished_goods
    if "finished_goods" in data:
        for fg in data["finished_goods"]:
            assert "total_cost" not in fg, \
                f"FinishedGood '{fg.get('slug')}' should not have total_cost"

def test_sample_data_all_has_no_cost_fields():
    """Verify sample_data_all.json is version 4.1 format."""
    import json
    
    with open("test_data/sample_data_all.json") as f:
        data = json.load(f)
    
    assert data.get("version") == "4.1"
    
    if "finished_units" in data:
        for fu in data["finished_units"]:
            assert "unit_cost" not in fu
    
    if "finished_goods" in data:
        for fg in data["finished_goods"]:
            assert "total_cost" not in fg
```

---

## 13. Implementation Plan (Updated)

### Phase 1: Model & Database Changes (2-3 hours)

**Tasks:**
1. Update FinishedUnit model
2. Update FinishedGood model
3. Create migration script
4. Run migration on dev database

**Deliverables:**
- ✓ Models updated
- ✓ Migration script created
- ✓ Migration tested

### Phase 2: Import/Export Changes (2-3 hours)

**Tasks:**
1. Update export_service.py:
   - Remove unit_cost from finished_units export
   - Remove total_cost from finished_goods export
   - Bump export version to 4.1

2. Update import_service.py:
   - Add strict validation (reject cost fields)
   - Add version check (reject v4.0)
   - Add helpful error messages

3. Update sample data files:
   - Update version to 4.1 in all files
   - Remove unit_cost from sample_data_min.json
   - Remove unit_cost from sample_data_all.json
   - Remove total_cost if present in any files

4. Test import/export:
   - Verify exports don't include cost fields
   - Verify imports reject old formats
   - Verify imports accept clean formats
   - Verify sample data loads without errors

**Deliverables:**
- ✓ Import/export services updated (strict validation)
- ✓ Sample data files cleaned (version 4.1)
- ✓ Clear error messages for old formats

### Phase 3: UI Updates (2-3 hours)

**Tasks:**
1. Update Recipes tab
2. Update FinishedUnits tab
3. Search for other UI references

**Deliverables:**
- ✓ UI updated
- ✓ No cost columns in catalog views
- ✓ Info messages added

### Phase 4: Testing & Validation (2 hours)

**Tasks:**
1. Write/update unit tests
2. Write/update integration tests
3. Manual testing

**Deliverables:**
- ✓ All tests pass
- ✓ Manual testing complete
- ✓ No regressions

### Phase 5: Documentation (1 hour)

**Tasks:**
1. Update model documentation
2. Update import/export format docs (version 4.1 changes)
3. Add migration notes to changelog
4. Document migration path for old exports

**Deliverables:**
- ✓ Documentation updated

**Total Effort: 9-12 hours**

---

## 14. Files to Modify Summary

### Models
- ✅ `src/models/finished_unit.py`
- ✅ `src/models/finished_good.py`

### Services
- ✅ `src/services/export_service.py` - Remove cost fields, bump version
- ✅ `src/services/import_service.py` - Add strict validation, reject old formats

### UI
- ✅ `src/ui/tabs/recipes_tab.py`
- ✅ `src/ui/tabs/finished_units_tab.py`

### Sample Data
- ✅ `test_data/sample_data_min.json` - Update to v4.1, remove costs
- ✅ `test_data/sample_data_all.json` - Update to v4.1, remove costs

### Database
- ✅ Migration script to drop columns

### Tests
- ✅ Update existing tests for model changes
- ✅ Add new tests for import/export strict validation
- ✅ Add sample data validation tests

---

## 15. Success Criteria (Updated)

**Must Have:**
- [ ] `finished_units.unit_cost` column dropped from database
- [ ] `finished_goods.total_cost` column dropped from database
- [ ] `FinishedUnit.calculate_current_cost_per_item()` method works correctly
- [ ] `FinishedGood.calculate_current_cost()` method works correctly
- [ ] No cost columns in Recipes catalog view
- [ ] No cost columns in FinishedUnits catalog view
- [ ] Export service excludes cost fields
- [ ] Export version bumped to 4.1
- [ ] Import service REJECTS files with cost fields
- [ ] Import service REJECTS version 4.0 files
- [ ] Error messages are clear and helpful
- [ ] Sample data files are version 4.1 with no cost fields
- [ ] All existing tests pass (with updates)
- [ ] Migration script runs successfully

**Should Have:**
- [ ] Cost changes propagate immediately (no stale data)
- [ ] Detail views optionally show "current estimate" costs
- [ ] Info messages explain where to see costs
- [ ] Documentation updated (models, API, import/export v4.1 format)

**Nice to Have:**
- [ ] Performance metrics (cost calculation speed)
- [ ] Migration validation script
- [ ] Automated tests for cost propagation

---

## 16. Migration Guide for Users

### For Users With Old Exports (v4.0)

**If you have exported data files from version 4.0:**

1. **Update version field:**
   ```json
   "version": "4.1"  // Change from "4.0"
   ```

2. **Remove cost fields from finished_units:**
   ```json
   // BEFORE (v4.0)
   "finished_units": [
     {
       "slug": "large-cookie",
       "display_name": "Large Cookie",
       "items_per_batch": 30,
       "unit_cost": 0.42  // ← REMOVE THIS LINE
     }
   ]
   
   // AFTER (v4.1)
   "finished_units": [
     {
       "slug": "large-cookie",
       "display_name": "Large Cookie",
       "items_per_batch": 30
     }
   ]
   ```

3. **Remove cost fields from finished_goods:**
   ```json
   // BEFORE (v4.0)
   "finished_goods": [
     {
       "slug": "gift-box",
       "display_name": "Holiday Gift Box",
       "total_cost": 8.50  // ← REMOVE THIS LINE
     }
   ]
   
   // AFTER (v4.1)
   "finished_goods": [
     {
       "slug": "gift-box",
       "display_name": "Holiday Gift Box"
     }
   ]
   ```

**Why?** Costs are now calculated dynamically from current ingredient prices. Stored costs were becoming stale and causing data integrity issues.

**Automated Tool** (optional, out of scope for F045):
```bash
# Future: Tool to upgrade v4.0 → v4.1
python scripts/upgrade_export_to_4_1.py old_export.json new_export.json
```

---

## 17. Related Documents

- **Analysis:** `F045_COST_ANALYSIS.md` (detailed cost architecture analysis)
- **Requirements:** `docs/requirements/req_finished_goods.md` Section 5.1, 5.2
- **Constitution:** `.kittify/memory/constitution.md` (Principles III, V, VII)
- **Dependencies:** F044 (Finished Units Functionality & UI ✅)
- **Blocks:** F046 (Finished Goods), F047 (Shopping Lists), F048 (Assembly)

---

**END OF SPECIFICATION**
