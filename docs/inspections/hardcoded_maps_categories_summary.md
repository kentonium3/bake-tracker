# Hardcoded Maps & Categories Inspection - Executive Summary

**Date:** February 5, 2026  
**Full Report:** `docs/inspections/hardcoded_maps_categories_dropdowns_inspection.md`

---

## Quick Findings

### Issues Found: 3 Total

1. **AssemblyType Enum Maps** (2 files, F095)
   - `finished_goods_tab.py:367-372` - hardcoded display map
   - `finished_good_form.py:214-219` - hardcoded display map
   - **Fix:** Use `assembly_type.get_display_name()` method

2. **Recipe Categories** (1 location, F096)
   - `finished_unit_form.py:155` - hardcoded list
   - **Fix:** Create `RecipeCategory` table, admin UI, and service layer

### Quality Metrics

- **Total Dropdowns Analyzed:** 60+
- **Correct Implementations:** 57+ (95%)
- **Issues to Fix:** 3 (5%)

---

## F095 Scope: Enum Display Patterns

**Effort:** 1-2 hours  
**Files to Update:** 2  
**Pattern:** Replace hardcoded maps with `enum.get_display_name()`

**Changes:**
```python
# BEFORE
type_map = {AssemblyType.BARE: "Bare", ...}
return type_map.get(assembly_type)

# AFTER
return assembly_type.get_display_name()
```

**Deliverables:**
- Fix 2 AssemblyType map violations
- Document correct enum pattern in CLAUDE.md
- Add tests for enum display methods

---

## F096 Scope: Recipe Category Management

**Effort:** 4-6 hours  
**Pattern:** Follow MaterialCategory exemplar (database + admin UI)

**Implementation:**
1. Create `recipe_categories` table (name, slug, sort_order, description)
2. Create `recipe_category_service.py` with CRUD operations
3. Create admin UI: Catalog menu → "Recipe Categories..."
4. Update `finished_unit_form.py` to query database
5. Update validators to check against database
6. Add import/export support

**Migration Strategy:**
- Populate from `SELECT DISTINCT category FROM recipes`
- Keep `Recipe.category` as string (validate on save, not FK)
- No data migration needed

---

## Already Correct (No Action)

✅ **Ingredient Categories** - Derived from data via `query(Ingredient.category).distinct()`  
✅ **Material Categories** - Database-driven with 3-level hierarchy and admin UI  
✅ **LossCategory Enum** - Correctly builds dropdown dynamically from enum  
✅ **DepletionReason Enum** - Correctly uses centralized display labels  
✅ **Recipe Readiness** - Boolean field, not a category  
✅ **Event Status** - Workflow constants, not customizable  
✅ **Unit Types** - UN/CEFACT international standards  
✅ **Package Types** - Industry standard container classifications

---

## Pattern Decision Matrix

| Scenario | Pattern | Example |
|----------|---------|---------|
| International standard | `constants.py` | UN/CEFACT units |
| Fixed business logic | Enum with `get_display_name()` | AssemblyType, LossCategory |
| User-defined taxonomy | Database table + admin UI | RecipeCategory, MaterialCategory |
| Emergent from data | Derived via query | Ingredient categories |
| Boolean flag | Model field + filter | `is_production_ready` |

---

## Priority Order

**Phase 1: F095 (Quick Win)** - 1-2 hours
- Fix AssemblyType violations
- Document enum pattern
- Low risk, high value

**Phase 2: F096 (Major Feature)** - 4-6 hours
- Create RecipeCategory system
- Enable user customization
- Medium risk, high value

**Phase 3: Optional Enhancements** - Future
- Add display methods to other enums
- Consolidate category management UI

---

## Key Insights

1. **Code Quality is High:** 95% of dropdowns follow correct patterns
2. **Clear Patterns Exist:** MaterialCategory is exemplar for database-driven categories
3. **Limited Scope:** Only 3 issues across entire codebase
4. **Easy Fixes:** Both F095 and F096 have clear implementation paths
5. **Good Architecture:** Layered approach (UI → Services → Models) mostly enforced

**Recommendation:** Proceed with both F095 and F096. Low risk, high value improvements that set standards for future development.
