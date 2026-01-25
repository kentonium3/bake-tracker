# Variant Yield Implementation - Gap Analysis

**Date:** 2025-01-24  
**Status:** Critical Issues Identified  
**Reviewed:** F063 Spec vs Current Implementation

---

## Executive Summary

The variant recipe implementation has **significant gaps** between the specification (F063) and actual implementation. The current approach creates FinishedUnits with NULL yield fields, which violates the core requirements and creates a confusing user experience.

### Critical Issues

1. **❌ NULL Yield Fields**: Variant FinishedUnits created with `items_per_batch=None, item_unit=None`
2. **❌ Missing Primitives**: `get_base_yield_structure()` and `get_finished_units()` not implemented
3. **❌ No Yield Inheritance UI**: Variant form shows full yield editing instead of inherited structure
4. **❌ Confusing Terminology**: "Yield Type" vs "Finished Unit" used interchangeably
5. **❌ Incomplete Edit Flow**: Editing variant doesn't show yield structure from base

---

## Specification vs Implementation

### What F063 Requires

**Core Principle (REQ-RCP-031 to REQ-RCP-040):**
> Variants SHALL define their own FinishedUnit records with **complete yield data** (items_per_batch, item_unit) that **matches** the base recipe's yield structure.

**Key Requirements:**
- Variant FinishedUnits have **same** items_per_batch as base
- Variant FinishedUnits have **same** item_unit as base
- Variant FinishedUnits have **distinct** display_name from base
- Services use `get_finished_units(recipe_id)` primitive (works for base or variant)
- UI shows base yield structure as **reference** during variant creation
- Yield validation ensures variant/base consistency

### What Was Actually Implemented

**Current Implementation (Lines 2224-2238 of recipe_service.py):**
```python
# Create variant FinishedUnit with NULL yield fields
variant_fu = FinishedUnit(
    recipe_id=variant.id,
    slug=_generate_variant_fu_slug(variant.name, new_display_name, variant.id),
    display_name=new_display_name,
    # Yield fields NULL for variants (inherited via primitives)
    items_per_batch=None,  # ❌ WRONG: Should copy from base
    item_unit=None,         # ❌ WRONG: Should copy from base
    # Copy non-yield fields from base
    yield_mode=base_fu.yield_mode,
    category=base_fu.category,
    batch_percentage=None,  # Clear for variants
    portion_description=base_fu.portion_description,
    production_notes=base_fu.production_notes,
)
```

**Problems:**
1. Violates REQ-RCP-034: "Variant FinishedUnit items_per_batch SHALL equal base recipe FinishedUnit items_per_batch"
2. Violates REQ-RCP-035: "Variant FinishedUnit item_unit SHALL match base recipe FinishedUnit item_unit"
3. Comment says "inherited via primitives" but primitives don't exist
4. Creates incomplete FinishedUnit records that fail validation

---

## Gap Analysis by Functional Requirement

### FR-1: Base Recipe Yield Structure Primitive ❌ NOT IMPLEMENTED

**Spec:** `get_base_yield_structure(recipe_id)` in recipe_service

**Current State:** Does not exist

**Impact:**
- UI cannot display base yield structure during variant creation/editing
- Services cannot reference base yields for validation
- No way to detect base yield changes

**Required Actions:**
1. Implement `get_base_yield_structure(recipe_id)` in recipe_service
2. Return list of dicts with items_per_batch, item_unit, display_name
3. Handle variant (return base's yields) vs base recipe (return own yields)

---

### FR-2: Universal Finished Units Primitive ❌ NOT IMPLEMENTED

**Spec:** `get_finished_units(recipe_id)` in recipe_service

**Current State:** Does not exist (services use `finished_unit_service.get_units_by_recipe()`)

**Impact:**
- Services must know if recipe is variant or base
- No abstraction layer for variant yield access
- Batch calculations may use wrong yields

**Required Actions:**
1. Implement `get_finished_units(recipe_id)` in recipe_service
2. Return recipe's own FinishedUnits (never base's)
3. Services should always use this primitive

---

### FR-3: Variant Yield Consistency Validation ❌ PARTIALLY IMPLEMENTED

**Spec:** Validate variant yields match base structure

**Current State:** 
- ✅ Validates display_name differs from base (line 2219)
- ❌ Does NOT validate items_per_batch matches base (not copied)
- ❌ Does NOT validate item_unit matches base (not copied)
- ❌ Does NOT validate count of FinishedUnits matches

**Impact:**
- Variant FinishedUnits created with NULL yields
- No enforcement of yield structure consistency
- Services cannot rely on variant yields

**Required Actions:**
1. Copy items_per_batch from base_fu to variant_fu
2. Copy item_unit from base_fu to variant_fu
3. Add validation: variant FU count == base FU count
4. Add validation: items_per_batch matches (after copying)
5. Add validation: item_unit matches (after copying)

---

### FR-4: Variant Creation with Yield Setup ⚠️ PARTIALLY IMPLEMENTED

**Spec:** Variant creation workflow includes yield setup with base reference

**Current State:**
- ✅ VariantCreationDialog shows base FinishedUnits (line 142)
- ✅ User enters variant display_name (line 174-187)
- ❌ Does NOT show items_per_batch from base (hidden)
- ❌ Does NOT show item_unit from base (hidden)
- ❌ Creates FinishedUnits with NULL yield fields

**Impact:**
- User doesn't see what yield structure they're inheriting
- Confusing what "Yield Type Names" means
- Variant FinishedUnits incomplete

**Required Actions:**
1. Show base items_per_batch and item_unit (read-only) in dialog
2. Label clearly: "Base Yield Structure" (not "Yield Type Names")
3. Copy items_per_batch and item_unit to variant FinishedUnits
4. Update dialog to show: "Base: Plain Cookie (32 cookies/batch)"

---

### FR-5: Base Yield Change Flagging ❌ NOT IMPLEMENTED

**Spec:** Flag variants when base FinishedUnit changes

**Current State:** Does not exist

**Impact:**
- Variants can become out of sync with base
- No notification when base yields change
- User unaware of potential inconsistencies

**Required Actions:**
1. Add `needs_yield_review` field to Recipe model
2. Detect base FinishedUnit modifications
3. Flag all variants
4. Display warning in variant edit UI
5. Provide "Mark as Reviewed" action

---

### FR-6: Service Integration for Batch Calculations ❌ NOT VERIFIED

**Spec:** Services use `get_finished_units(recipe_id)` for calculations

**Current State:** Unknown (primitives don't exist yet)

**Impact:**
- Services may directly access recipe.finished_units
- Variant batch calculations may fail or use wrong yields
- Cost calculations may use base yields instead of variant yields

**Required Actions:**
1. Audit all services accessing FinishedUnits
2. Replace direct access with `get_finished_units(recipe_id)`
3. Ensure no variant-specific checks in services
4. Test batch calculations for variants

---

### FR-7: UI Enhancements for Variant Yield Workflow ⚠️ PARTIALLY IMPLEMENTED

**Spec:** UI shows base yield structure, allows variant FinishedUnit creation

**Current State:**
- ✅ Variant creation dialog exists
- ✅ Shows base display_names
- ❌ Does NOT show base items_per_batch (critical missing info)
- ❌ Does NOT show base item_unit (critical missing info)
- ❌ Uses confusing term "Yield Type Names"
- ❌ Editing variant shows full yield form (should show inherited structure)

**Impact:**
- User doesn't understand yield inheritance
- "Yield Type Names" confusing (should say "FinishedUnit display_name")
- Editing variant allows changing inherited yield structure
- No visual indication that yields are inherited from base

**Required Actions:**
1. Update VariantCreationDialog to show complete base yield structure
2. Change "Yield Type Names:" to "Finished Units (inheriting yield from base):"
3. Show: "Base: Plain Cookie | 32 cookies per batch"
4. RecipeFormDialog should detect variant and show yield structure as read-only reference
5. Add help text: "Yield structure (count, unit) inherited from base recipe"

---

## User Experience Issues

### Issue 1: Terminology Confusion

**Problem:** "Yield Type" used interchangeably with "Finished Unit"

**Where:**
- VariantCreationDialog line 130: "Yield Type Names:"
- RecipeFormDialog uses "Yield Information" and "yield types"
- Requirements doc uses both terms

**Impact:** User doesn't understand the relationship between concepts

**Fix:**
- Use "Finished Unit" consistently in code and UI
- Reserve "yield" for items_per_batch + item_unit
- Label: "Finished Units (Product Names)" or "Product Names"

### Issue 2: Editing Variant Shows Full Yield Form

**Problem:** Opening variant for edit shows complete yield type section with editable fields

**Where:** RecipeFormDialog._populate_form() (lines 1239-1252)

**Impact:**
- User thinks they can change yield structure
- No indication that yield is inherited from base
- Saving changes yield creates inconsistency with base

**Expected Behavior:**
- Variant recipe edit should show: "Yield Structure (inherited from base recipe: [Base Recipe Name])"
- Display base items_per_batch and item_unit as read-only
- Only allow editing variant FinishedUnit display_name
- OR: Hide yield section entirely and show inheritance message

### Issue 3: No Way to Edit Variant FinishedUnit Display Names

**Problem:** After creating variant, no clear path to edit FinishedUnit display_name

**Current State:**
- Edit recipe form shows yield types
- But for variant, should show inherited structure
- No "Edit Product Name" button specific to variants

**Impact:** User cannot correct typos or update variant product names

**Fix:**
- Variant edit form should have special section: "Product Names (inherited yield from base)"
- Show each FinishedUnit with editable display_name only
- Show items_per_batch and item_unit as read-only labels

### Issue 4: Missing Base Recipe Reference in Variant Form

**Problem:** When editing variant, no visual indication of base recipe relationship

**Where:** RecipeFormDialog doesn't show base_recipe_id link

**Impact:** User doesn't know this is a variant or which recipe is the base

**Fix:**
- Add section at top of variant form: "This is a variant of [Base Recipe Name]"
- Show link/button to view base recipe
- Show inherited yield structure reference

---

## Data Model Issues

### Issue 1: NULL Yield Fields on Variant FinishedUnits

**Problem:** Variant FinishedUnits created with items_per_batch=None, item_unit=None

**Database State:**
```sql
-- Base FinishedUnit
id | recipe_id | display_name        | items_per_batch | item_unit
42 | 10        | Plain Cookie        | 32              | cookie

-- Variant FinishedUnit (CURRENT - WRONG)
id | recipe_id | display_name        | items_per_batch | item_unit
43 | 11        | Raspberry Cookie    | NULL            | NULL

-- Variant FinishedUnit (SHOULD BE - CORRECT)
id | recipe_id | display_name        | items_per_batch | item_unit
43 | 11        | Raspberry Cookie    | 32              | cookie
```

**Impact:**
- FinishedUnit validation fails (items_per_batch required for DISCRETE_COUNT)
- Batch calculations fail (cannot divide by NULL)
- Cost calculations fail (no yield for per-unit cost)
- Production planning fails (no target yield)

**Fix:** Copy items_per_batch and item_unit from base to variant (lines 2230-2231)

### Issue 2: Missing Validation Constraints

**Problem:** No database-level enforcement of yield consistency

**Current State:** Application-level validation only (and incomplete)

**Impact:** Data can become inconsistent if validation skipped

**Recommendation:**
- Consider check constraint: variant recipes must have FinishedUnits with non-NULL yields
- Consider trigger: flag variants when base FinishedUnit yields change
- Add migration to fix existing NULL yields

---

## Service Layer Issues

### Issue 1: Missing Abstraction Primitives

**Problem:** No `get_finished_units(recipe_id)` or `get_base_yield_structure(recipe_id)`

**Impact:**
- Services must know variant implementation details
- Code duplication checking if recipe.base_recipe_id exists
- Tight coupling between services and variant logic

**Required Implementation:**
```python
def get_finished_units(recipe_id: int, session=None) -> List[FinishedUnit]:
    """
    Get FinishedUnits for a recipe (base or variant).
    
    Always returns the recipe's OWN FinishedUnits, never base's.
    """
    # Implementation here
    pass

def get_base_yield_structure(recipe_id: int, session=None) -> List[Dict]:
    """
    Get yield structure from base recipe (for variants) or own (for base).
    
    Returns: [{"items_per_batch": 32, "item_unit": "cookie", "display_name": "..."}, ...]
    """
    # Implementation here
    pass
```

### Issue 2: Incomplete Validation in create_recipe_variant

**Problem:** Validation only checks display_name differs, not yield structure match

**Missing Validations:**
- Number of finished_unit_names matches base FinishedUnits count
- After creation, variant items_per_batch matches base
- After creation, variant item_unit matches base

**Fix:**
1. Add count validation before loop
2. Copy items_per_batch and item_unit in loop
3. Add post-creation validation

---

## Recommended Implementation Plan

### Phase 1: Fix Data Creation (Critical)

**Priority:** CRITICAL - Blocks variant usage

**Changes:**
1. Update `_create_recipe_variant_impl` lines 2230-2231:
   ```python
   items_per_batch=base_fu.items_per_batch,  # Copy from base
   item_unit=base_fu.item_unit,              # Copy from base
   ```

2. Add validation before FinishedUnit creation:
   ```python
   if len(finished_unit_names) != len(base_fus):
       raise ValidationError([
           f"Variant must have {len(base_fus)} FinishedUnit(s) to match base recipe"
       ])
   ```

3. Add post-creation validation:
   ```python
   # After session.flush(), validate yield consistency
   for variant_fu, base_fu in zip(variant_fus, base_fus):
       if variant_fu.items_per_batch != base_fu.items_per_batch:
           raise ValidationError([...])
       if variant_fu.item_unit != base_fu.item_unit:
           raise ValidationError([...])
   ```

**Test:** Create variant and verify FinishedUnits have complete yield data

---

### Phase 2: Implement Service Primitives (High Priority)

**Priority:** HIGH - Enables proper service integration

**Changes:**
1. Add `get_finished_units(recipe_id, session=None)` to recipe_service
2. Add `get_base_yield_structure(recipe_id, session=None)` to recipe_service
3. Update all services to use primitives
4. Remove variant-specific checks from services

**Test:** Batch calculations work correctly for variants

---

### Phase 3: Fix UI Experience (High Priority)

**Priority:** HIGH - Confusion blocking users

**Changes:**
1. Update VariantCreationDialog:
   - Change "Yield Type Names:" to "Product Names (inheriting yield from base):"
   - Show base yield structure: "Base: Plain Cookie | 32 cookies per batch"
   - Add help text explaining yield inheritance

2. Update RecipeFormDialog for variants:
   - Detect if recipe.base_recipe_id exists
   - If variant, show: "This is a variant of [Base Recipe Name]"
   - Replace editable yield section with read-only reference
   - Show: "Yield Structure (inherited): 32 cookies per batch"
   - Allow editing only FinishedUnit display_name

3. Add terminology consistency:
   - Use "Finished Unit" or "Product Name" consistently
   - Avoid "Yield Type" (ambiguous)
   - Use "yield" for items_per_batch + item_unit

**Test:** User can create and edit variants without confusion

---

### Phase 4: Add Yield Change Detection (Medium Priority)

**Priority:** MEDIUM - Nice to have but not blocking

**Changes:**
1. Add `needs_yield_review` field to Recipe model
2. Detect base FinishedUnit modifications
3. Flag variants when base yields change
4. Display warning in variant edit UI
5. Provide "Mark as Reviewed" action

**Test:** Base yield changes flag variants, user can review

---

## Specification Updates Needed

### Update F063 Spec

**Section: FR-4 Variant Creation with Yield Setup**

Add clarification:
> **CRITICAL:** Variant FinishedUnits MUST be created with complete yield data (items_per_batch, item_unit) copied from base FinishedUnits. The comment "inherited via primitives" in initial implementation was misleading - variants must have their own complete FinishedUnits that match base structure.

### Update req_recipes.md

**Section 5.6: Variant Yield Inheritance**

REQ-RCP-031 should read:
> Variant recipes SHALL define their own FinishedUnit records **with complete yield data** (items_per_batch, item_unit) matching the base recipe's yield structure.

Add note:
> **Implementation Note:** "Inheritance" means copying yield structure values from base to variant at creation time, NOT leaving fields NULL. Services access variant FinishedUnits directly via `get_finished_units(recipe_id)`.

---

## Testing Checklist

### Critical Tests Needed

- [ ] Create variant with base having FinishedUnits → variant FinishedUnits have items_per_batch, item_unit
- [ ] Variant FinishedUnit items_per_batch equals base
- [ ] Variant FinishedUnit item_unit equals base
- [ ] Variant FinishedUnit display_name differs from base
- [ ] Batch calculation for variant uses variant's FinishedUnits (not base's)
- [ ] Cost calculation for variant uses variant's ingredient costs + yields
- [ ] Edit variant → yields shown as inherited/read-only
- [ ] Create variant with wrong FU count → validation error

### Edge Cases

- [ ] Create variant with base having no FinishedUnits
- [ ] Create variant with base having multiple FinishedUnits
- [ ] Edit base FinishedUnit yields → variants flagged (Phase 4)
- [ ] Delete variant → FinishedUnits cascade delete
- [ ] Variant of variant attempt → blocked by validation

---

## Conclusion

The current variant implementation has **critical architectural flaws**:

1. **Data Layer:** FinishedUnits created with NULL yields (violates spec)
2. **Service Layer:** Missing abstraction primitives
3. **UI Layer:** Confusing terminology and workflow

**Immediate Actions Required:**
1. Fix FinishedUnit creation to copy yield data (Phase 1)
2. Implement service primitives (Phase 2)
3. Update UI to clarify inheritance and terminology (Phase 3)

**Estimated Effort:**
- Phase 1: 2-3 hours (critical fix)
- Phase 2: 4-6 hours (primitives + service updates)
- Phase 3: 6-8 hours (UI updates + testing)
- Phase 4: 4-6 hours (yield change detection)

**Total:** 16-23 hours of focused development + testing

---

**END OF GAP ANALYSIS**
