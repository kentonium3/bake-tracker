# Ingredient Hierarchy Implementation Gap Analysis

**Date:** 2025-12-30  
**Updated:** 2026-01-02  
**Status:** IN PROGRESS - Phase 1 complete, Phases 2-4 pending  
**Reference:** `/docs/requirements/req_ingredients.md`

---

## Implementation Status

**Phase 1: COMPLETE ✅** (2026-01-02) → Merged as part of F033
- Fixed ingredient edit form mental model
- Fixed ingredients tab hierarchy display  
- Implemented core validation services

**Phase 2: PENDING** → Will be F034 (Cascading Filters & Integration)  
**Phase 3: PENDING** → Will be F035 (Auto-Update & Polish)  
**Phase 4: PENDING** → Will be F036 (Comprehensive Testing)

---

## Executive Summary

The ingredient hierarchy implementation has **fundamental gaps** across all layers (schema, service, UI, validation). While backend infrastructure exists, the implementation is incomplete and inconsistent. This analysis maps each requirement to implementation status.

**Overall Completion: ~55%** (updated 2026-01-02 after Phase 1)

| Layer | Status | Completeness | Phase 1 Status |
|-------|--------|--------------|----------------|
| **Schema** | ✅ Complete | 100% | No changes |
| **Service Layer** | ⚠️ Partial | 70% (+10%) | Validation services added |
| **UI Layer** | ⚠️ Partial | 50% (+20%) | Edit form & tab fixed |
| **Validation** | ⚠️ Partial | 40% (+30%) | Core validation added |
| **Integration** | ⚠️ Partial | 40% | Unchanged (Phase 2) |

---

## Gap Analysis by Requirement

### Section 5.1: Data Management

| Req ID | Requirement | Status | Gap Description |
|--------|-------------|--------|-----------------|
| REQ-ING-001 | Store hierarchy using parent_ingredient_id FK | ✅ DONE | Schema exists |
| REQ-ING-002 | Compute hierarchy_level based on parent | ✅ DONE | Computation logic exists |
| REQ-ING-003 | Generate unique slugs from display_name | ⚠️ PARTIAL | Auto-generation missing in UI create workflow |
| REQ-ING-004 | Prevent cycles in hierarchy | ❌ MISSING | No cycle detection in edit workflow |

**Critical Gaps:**
- **REQ-ING-003:** Slug auto-generation not called from ingredient create dialog
- **REQ-ING-004:** No validation prevents user from creating circular references

---

### Section 5.2: Ingredient Creation

| Req ID | Requirement | Status | Gap Description |
|--------|-------------|--------|-----------------|
| REQ-ING-005 | Allow creation of L2 ingredients via UI | ⚠️ PARTIAL | UI exists but uses wrong mental model (level dropdown vs parent selection) |
| REQ-ING-006 | Require L0/L1 parent selection for L2 | ❌ MISSING | Current UI has "level" dropdown instead of parent selectors |
| REQ-ING-007 | Auto-generate slug on creation | ❌ MISSING | Not implemented in create workflow |
| REQ-ING-008 | Validate slug uniqueness | ⚠️ PARTIAL | Database constraint exists but no UI-level validation |

**Critical Gaps:**
- **REQ-ING-005/006:** Edit form conceptually wrong - has "set ingredient level" dropdown instead of parent selection
- **REQ-ING-007:** No slug generation hooked up in create dialog
- **REQ-ING-008:** No pre-save validation in UI to check slug conflicts

---

### Section 5.3: Ingredient Editing

| Req ID | Requirement | Status | Gap Description |
|--------|-------------|--------|-----------------|
| REQ-ING-009 | Allow editing L2 ingredient names | ✅ DONE | Name field editable |
| REQ-ING-010 | Allow changing L0/L1 parentage | ⚠️ PARTIAL | Wrong UI (level dropdown) but parentage change technically possible |
| REQ-ING-011 | Prevent hierarchy changes orphaning products | ❌ MISSING | No validation |
| REQ-ING-012 | Prevent hierarchy changes orphaning recipes | ❌ MISSING | No validation |
| REQ-ING-013 | Auto-update Product records on hierarchy change | ❌ MISSING | No cascading update logic |
| REQ-ING-014 | Auto-update Recipe records on attribute change | ❌ MISSING | No cascading update logic |

**Critical Gaps:**
- **REQ-ING-011/012:** CRITICAL - No validation prevents orphaning products/recipes when changing hierarchy
- **REQ-ING-013/014:** CRITICAL - No auto-update logic when ingredient hierarchy changes
- **REQ-ING-010:** UI is conceptually wrong (documented in BUG_F032)

---

### Section 5.4: Product Assignment

| Req ID | Requirement | Status | Gap Description |
|--------|-------------|--------|-----------------|
| REQ-ING-015 | Allow product assignment only to L2 | ⚠️ PARTIAL | Backend validation exists but UI doesn't enforce |
| REQ-ING-016 | Prevent product assignment to L0/L1 | ⚠️ PARTIAL | Backend validation exists but UI doesn't guide user |
| REQ-ING-017 | Product edit form uses cascading selectors | ✅ DONE | Implemented and working |

**Critical Gaps:**
- **REQ-ING-015/016:** UI doesn't prevent selection of L0/L1, relies on backend error (poor UX)

---

### Section 5.5: Recipe Integration

| Req ID | Requirement | Status | Gap Description |
|--------|-------------|--------|-----------------|
| REQ-ING-018 | Allow recipe ingredient selection only for L2 | ❌ UNKNOWN | Recipe creation UI not verified |
| REQ-ING-019 | Prevent recipe use of L0/L1 | ❌ UNKNOWN | Validation not verified |
| REQ-ING-020 | Recipe form uses cascading selectors | ❌ UNKNOWN | Not verified - likely missing based on other tabs |

**Critical Gaps:**
- **REQ-ING-018/019/020:** Recipe integration COMPLETELY UNVERIFIED - likely missing based on pattern

---

### Section 5.6: List Filtering

| Req ID | Requirement | Status | Gap Description |
|--------|-------------|--------|-----------------|
| REQ-ING-021 | Product tab supports hierarchy filtering | ⚠️ PARTIAL | Implemented but behavior issues reported |
| REQ-ING-022 | Inventory tab supports hierarchy filtering | ⚠️ PARTIAL | Implemented but behavior issues reported |
| REQ-ING-023 | Filters cascade properly | ❌ BROKEN | L1 doesn't filter based on L0 selection |

**Critical Gaps:**
- **REQ-ING-023:** CRITICAL - Cascading filters don't work properly (L1 dropdown doesn't update when L0 changes)

---

### Section 9: UI Requirements

#### 9.1 Ingredients Tab

| Requirement | Status | Gap Description |
|-------------|--------|-----------------|
| Default view shows L2 only | ❌ MISSING | Shows all levels with dashes |
| Columns: Name \| L1 \| L0 \| Products | ❌ WRONG | Shows deprecated "Category" column |
| Filter dropdown for levels | ❌ MISSING | No level filter exists |

**Critical Gaps:**
- Entire Ingredients tab UI is WRONG - doesn't match requirements at all
- Shows flat list with deprecated fields instead of hierarchical view

#### 9.2 Ingredient Edit Form

| Requirement | Status | Gap Description |
|-------------|--------|-----------------|
| Name field editable | ✅ DONE | Works correctly |
| Parent selection (L0 dropdown) | ❌ WRONG | Has "level" dropdown instead |
| Parent selection (L1 dropdown) | ❌ WRONG | Has "level" dropdown instead |
| Level computed and displayed | ❌ WRONG | Level is user-selectable dropdown |
| "Can have products" indicator | ❌ MISSING | Not displayed |

**Critical Gaps:**
- FUNDAMENTAL CONCEPTUAL ERROR: Form treats level as assignable property instead of computed value
- No parent selection mechanism at all
- Documented in BUG_F032_hierarchy_conceptual_errors.md

#### 9.3 Cascading Selector Component

| Requirement | Status | Gap Description |
|-------------|--------|-----------------|
| Used in Product edit form | ✅ DONE | Working |
| Used in Recipe creation | ❌ UNKNOWN | Not verified |
| Used in Product tab filter | ⚠️ PARTIAL | Exists but broken cascading |
| Used in Inventory tab filter | ⚠️ PARTIAL | Exists but broken cascading |
| L0 → L1 → L2 cascading behavior | ❌ BROKEN | L1 doesn't update when L0 changes |
| Clear button resets all levels | ❌ MISSING | No clear functionality |

**Critical Gaps:**
- Cascading logic broken in filters (L1 doesn't update)
- No clear/reset functionality
- Product edit form hangs (separate bug)

---

### Section 10: Validation Rules

#### 10.1 Creation Validation

| Rule ID | Validation | Status | Gap |
|---------|-----------|--------|-----|
| VAL-ING-001 | Name required | ⚠️ PARTIAL | Backend yes, UI no feedback |
| VAL-ING-002 | Slug unique | ⚠️ PARTIAL | Backend yes, UI no check |
| VAL-ING-003 | L2 needs L1 parent | ❌ MISSING | Can't enforce - wrong UI model |
| VAL-ING-004 | L1 needs L0 parent | ❌ MISSING | Can't enforce - wrong UI model |

**Critical Gaps:**
- No validation rules can be enforced because UI uses wrong mental model

#### 10.2 Edit Validation

| Rule ID | Validation | Status | Gap |
|---------|-----------|--------|-----|
| VAL-ING-005 | Can't change parent if has children | ❌ MISSING | No check |
| VAL-ING-006 | Can't change to non-leaf if has products | ❌ MISSING | No check |
| VAL-ING-007 | Can't change to non-leaf if in recipes | ❌ MISSING | No check |
| VAL-ING-008 | Can't create cycles | ❌ MISSING | No check |

**Critical Gaps:**
- ZERO edit validation rules implemented
- Users can break data integrity freely
- Can orphan products and recipes without warning

#### 10.3 Deletion Validation

| Rule ID | Validation | Status | Gap |
|---------|-----------|--------|-----|
| VAL-ING-009 | Can't delete if has products | ❌ UNKNOWN | Not tested |
| VAL-ING-010 | Can't delete if in recipes | ❌ UNKNOWN | Not tested |
| VAL-ING-011 | Can't delete if has children | ❌ UNKNOWN | Not tested |

**Critical Gaps:**
- Deletion validation completely untested
- Likely missing based on pattern

---

## Service Layer Analysis

### Implemented Services

✅ **ingredient_hierarchy_service.py** - Exists with:
- `get_root_ingredients()` - Working
- `get_children(parent_id)` - Working
- `get_ancestors(ingredient_id)` - Working
- `get_hierarchy_path(ingredient_id)` - Working
- `compute_hierarchy_level(parent_id)` - Working
- Basic cycle detection - Working

### Missing Service Methods

❌ **Validation Services** - Critical gaps:

```python
# MISSING: Comprehensive validation
def can_change_parent(ingredient_id, new_parent_id) -> Tuple[bool, str]:
    """
    Validates if hierarchy change is allowed.
    
    Checks:
    - Has children? → Cannot change
    - Has products and new level != L2? → Cannot change
    - Used in recipes and new level != L2? → Cannot change
    - Would create cycle? → Cannot change
    
    Returns: (is_allowed, error_message)
    """
    pass  # NOT IMPLEMENTED

def get_product_count(ingredient_id) -> int:
    """Count products using this ingredient."""
    pass  # NOT IMPLEMENTED

def get_recipe_usage_count(ingredient_id) -> int:
    """Count recipes using this ingredient."""
    pass  # NOT IMPLEMENTED

def get_child_count(ingredient_id) -> int:
    """Count direct children of this ingredient."""
    pass  # NOT IMPLEMENTED
```

❌ **Auto-Update Services** - Missing:

```python
# MISSING: Cascading updates
def update_ingredient_hierarchy(ingredient_id, new_parent_id):
    """
    Update ingredient hierarchy and cascade changes.
    
    Should:
    1. Validate change is allowed
    2. Update parent_ingredient_id
    3. Recompute hierarchy_level
    4. Update all related Product records (denormalized fields if any)
    5. Update all related Recipe records (denormalized fields if any)
    """
    pass  # NOT IMPLEMENTED

def update_related_products(ingredient_id):
    """Update products when ingredient hierarchy changes."""
    pass  # NOT IMPLEMENTED

def update_related_recipes(ingredient_id):
    """Update recipes when ingredient changes."""
    pass  # NOT IMPLEMENTED
```

❌ **Slug Generation Service** - Missing:

```python
# MISSING: Slug utilities
def generate_unique_slug(display_name, session) -> str:
    """Generate unique slug, handling conflicts with -2, -3, etc."""
    pass  # NOT IMPLEMENTED

def validate_slug_unique(slug, exclude_id=None, session) -> bool:
    """Check if slug is unique."""
    pass  # NOT IMPLEMENTED
```

---

## UI Layer Analysis

### What Works

✅ **Product Edit Form:**
- Cascading ingredient selector functional
- Can assign products to L2 ingredients

✅ **Basic Schema:**
- Database supports hierarchy
- Import/export handles hierarchical data

### What's Broken

❌ **Ingredients Tab:**
- Shows all levels mixed together (should show L2 by default)
- Shows deprecated "Category" column instead of L0/L1/L2 columns
- Displays dashes in hierarchy columns
- No filter to switch between L0/L1/L2 views
- No "Products" count column

❌ **Ingredient Edit Form:**
- CONCEPTUALLY WRONG: Treats level as assignable property
- Has "Ingredient Level" dropdown with "Root (L0)", "Subcategory (L1)", "Leaf Ingredient" options
- Shows ingredient name as dialog title (not editable field)
- Missing L0 parent dropdown
- Missing L1 parent dropdown
- Missing computed level display
- Missing "Can have products" indicator

❌ **Product Tab Filter:**
- Cascading selectors exist but don't cascade properly
- L1 dropdown doesn't update when L0 changes
- Can't filter by hierarchy effectively

❌ **Inventory Tab Filter:**
- Same cascading issues as Product tab
- Displays deprecated "Category" column instead of hierarchy

❌ **Product Edit Form (BLOCKER):**
- Hangs when edit button clicked
- Likely infinite loop in cascading dropdown logic

❌ **Recipe Creation (UNKNOWN):**
- Not verified - likely missing cascading selectors based on pattern
- Likely allows selection of L0/L1 (invalid)

---

## Integration Points Analysis

### Product ↔ Ingredient Integration

| Integration Point | Status | Gap |
|-------------------|--------|-----|
| Product edit form ingredient selection | ✅ Works | None |
| Product tab filtering by ingredient | ⚠️ Partial | Cascading broken |
| Product validation (must be L2) | ⚠️ Partial | Backend only, no UI guidance |
| Product update when ingredient changes | ❌ Missing | No auto-update logic |

### Recipe ↔ Ingredient Integration

| Integration Point | Status | Gap |
|-------------------|--------|-----|
| Recipe creation ingredient selection | ❌ Unknown | Not verified |
| Recipe validation (must be L2) | ❌ Unknown | Not verified |
| Recipe update when ingredient changes | ❌ Missing | No auto-update logic |

### Inventory ↔ Ingredient Integration

| Integration Point | Status | Gap |
|-------------------|--------|-----|
| Inventory tab filtering by ingredient | ⚠️ Partial | Cascading broken |
| Inventory read-only hierarchy display | ❌ Wrong | Shows deprecated category |

---

## Critical Blockers (Must Fix Immediately)

### Blocker 1: Ingredient Edit Form Mental Model

**Severity:** CRITICAL  
**Impact:** Users cannot correctly create/edit ingredients  
**Description:** Form treats hierarchy level as assignable property instead of computed value

**Fix Required:**
- Remove "Ingredient Level" dropdown entirely
- Add radio buttons: "No Parent (Root)" vs "Has Parent"
- Add L0 parent dropdown (enabled when "Has Parent" selected)
- Add L1 parent dropdown (cascades from L0 selection)
- Add computed level display (read-only)
- Add "Can have products" indicator (read-only)

**Document:** BUG_F032_hierarchy_conceptual_errors.md

---

### Blocker 2: Ingredients Tab Display

**Severity:** CRITICAL  
**Impact:** Users cannot browse ingredients hierarchically  
**Description:** Tab shows flat list with deprecated fields, missing hierarchy columns

**Fix Required:**
- Default to showing L2 ingredients only
- Replace "Category" column with three columns: "Root (L0)" | "Subcategory (L1)" | "Ingredient (L2)"
- Add "Products" count column
- Add filter dropdown: "Leaf Ingredients (L2)" | "Subcategories (L1)" | "Root Categories (L0)" | "All Levels"
- Use `get_ancestors()` to populate L0/L1 columns for each L2 ingredient

---

### Blocker 3: Cascading Filter Logic

**Severity:** HIGH  
**Impact:** Users cannot filter products/inventory by hierarchy  
**Description:** L1 dropdown doesn't update when L0 selection changes

**Fix Required:**
- Fix cascading logic: L0 change → update L1 options → clear L2 selection
- Add event handler guards to prevent infinite loops
- Add "Clear All" button to reset filters

---

### Blocker 4: Validation Missing

**Severity:** CRITICAL  
**Impact:** Users can break data integrity (orphan products/recipes)  
**Description:** Zero edit validation implemented

**Fix Required:**
- Implement `can_change_parent()` validation service
- Implement `get_product_count()`, `get_recipe_usage_count()`, `get_child_count()` service methods
- Add pre-save validation in edit form
- Display clear error messages when validation fails

---

### Blocker 5: Product Edit Form Hangs

**Severity:** HIGH  
**Impact:** Cannot edit products  
**Description:** Edit button causes hang/freeze

**Fix Required:**
- Debug cascading dropdown logic
- Add re-entry guards to event handlers
- Consider handing to Gemini/Cursor for debugging

---

## Non-Critical Gaps (Can Defer)

### Missing Features

⏳ **Slug Auto-Generation:**
- Service method exists but not called from UI
- Currently users must ensure unique names manually

⏳ **Auto-Update Cascading:**
- No logic to update products/recipes when ingredient hierarchy changes
- Users must manually verify referential integrity

⏳ **Clear/Reset Filters:**
- No easy way to clear all filter selections

⏳ **Hierarchy Visualization:**
- No tree view for browsing full hierarchy
- Users must use dropdowns only

⏳ **Batch Operations:**
- Cannot move multiple ingredients at once
- Each ingredient edited individually

---

## Recommended Implementation Priority

### Phase 1: Critical Fixes ✅ COMPLETE (2026-01-02)

**Goal:** Make ingredient management functional

**Status:** All items completed and merged as part of F033 Phase 1 implementation

1. **Fix Ingredient Edit Form** (Blocker 1) ✅ COMPLETE
   - Replaced level dropdown with parent selection
   - Implemented proper mental model
   - Actual effort: Within estimated 8-10 hours
   - **Delivered:**
     - Removed "Ingredient Level" dropdown
     - Added parent selection dropdowns (L0/L1)
     - Level now computed from parent (read-only display)
     - "Can have products" indicator added

2. **Fix Ingredients Tab Display** (Blocker 2) ✅ COMPLETE
   - Added hierarchy columns
   - Implemented level filtering
   - Actual effort: Within estimated 6-8 hours
   - **Delivered:**
     - Full hierarchy path display (e.g., "Baking > Flour > All-Purpose")
     - Works correctly for L0, L1, and L2 ingredients

3. **Implement Core Validation** (Blocker 4) ✅ COMPLETE
   - Added `can_change_parent()` service
   - Added count services
   - Hooked into edit form
   - Actual effort: Within estimated 6-8 hours
   - **Delivered:**
     - `can_change_parent(ingredient_id, new_parent_id)` validation
     - `get_product_count(ingredient_id)` service
     - `get_child_count(ingredient_id)` service
     - Pre-save validation with warning dialogs
     - Blocks unsafe hierarchy changes

**Phase 1 Total: 20-26 hours estimated → COMPLETED**

---

### Phase 2: Integration Fixes (PENDING → Will be F034)

**Goal:** Make hierarchy work across all tabs

**Status:** NOT STARTED - Will be next feature after F033

1. **Fix Ingredient Edit Form** (Blocker 1)
   - Replace level dropdown with parent selection
   - Implement proper mental model
   - Estimate: 8-10 hours

2. **Fix Ingredients Tab Display** (Blocker 2)
   - Add hierarchy columns
   - Implement level filtering
   - Estimate: 6-8 hours

3. **Implement Core Validation** (Blocker 4)
   - Add `can_change_parent()` service
   - Add count services
   - Hook into edit form
   - Estimate: 6-8 hours

**Phase 1 Total: 20-26 hours (3-4 days)**

---

### Phase 2: Integration Fixes (PENDING → Will be F034)

**Goal:** Make hierarchy work across all tabs

**Status:** NOT STARTED - Planned as F034 feature  
**Estimated Effort:** 12-20 hours (2-3 days)

4. **Fix Cascading Filters** (Blocker 3)
   - Fix Product tab filter
   - Fix Inventory tab filter
   - Estimate: 4-6 hours

5. **Debug Product Edit Hang** (Blocker 5)
   - Add debugging, fix infinite loop
   - Test thoroughly
   - Estimate: 4-8 hours (or hand to Gemini/Cursor)

6. **Verify Recipe Integration**
   - Test recipe creation ingredient selection
   - Implement cascading selector if missing
   - Add validation (L2 only)
   - Estimate: 4-6 hours

**Phase 2 Total: 12-20 hours (2-3 days)**

---

### Phase 3: Polish & Auto-Update (PENDING → Will be F035)

**Goal:** Complete auto-update and quality of life

**Status:** NOT STARTED - Planned as F035 feature  
**Estimated Effort:** 10-14 hours (2 days)

7. **Slug Auto-Generation**
   - Hook up service to create dialog
   - Add conflict handling UI
   - Estimate: 2-3 hours

8. **Auto-Update Cascading**
   - Implement product update service
   - Implement recipe update service
   - Hook into edit workflow
   - Estimate: 6-8 hours

9. **Clear/Reset Functionality**
   - Add clear buttons to filters
   - Improve UX
   - Estimate: 2-3 hours

**Phase 3 Total: 10-14 hours (2 days)**

---

### Phase 4: Comprehensive Testing (PENDING → Will be F036)

**Goal:** Validate all requirements with full test suite

**Status:** NOT STARTED - Planned as F036 feature  
**Estimated Effort:** 8-12 hours (1-2 days)

10. **Full Test Suite**
    - Run all 13 test cases from requirements
    - Fix any discovered issues
    - User testing with Marianne
    - Estimate: 8-12 hours

**Phase 4 Total: 8-12 hours (1-2 days)**

---

## Total Effort Estimate

**Original Total:** 50-72 hours (7-10 working days)

**Phase 1 (COMPLETE):** 20-26 hours ✅  
**Remaining (Phases 2-4):** 30-46 hours (4-6 working days)

**Current Completion: ~55%** (updated 2026-01-02)  
**Remaining Work: ~45%**

**Next Features:**
- F034: Phase 2 (Integration Fixes) - 12-20 hours
- F035: Phase 3 (Auto-Update & Polish) - 10-14 hours
- F036: Phase 4 (Comprehensive Testing) - 8-12 hours

---

## Acceptance Checklist

Use this to track completion against requirements:

### Must Have (Blocking)

**Phase 1 (COMPLETE ✅):**
- [x] REQ-ING-005: Create L2 ingredients with correct UI (parent selection, not level)
- [x] REQ-ING-006: Require L0/L1 parent selection for L2 creation
- [x] REQ-ING-011: Prevent hierarchy changes that orphan products
- [x] REQ-ING-012: Prevent hierarchy changes that orphan recipes
- [x] Section 9.1: Ingredients tab shows hierarchy correctly
- [x] Section 9.2: Edit form uses parent selection (not level dropdown)
- [x] Section 10.2: Core edit validation rules implemented

**Phase 2 (PENDING → F034):**
- [ ] REQ-ING-017: Product edit form cascading selector works (fix hang)
- [ ] REQ-ING-021/022/023: Cascading filters work in Product/Inventory tabs

**Phase 3 (PENDING → F035):**
- [ ] REQ-ING-007: Slug auto-generation on creation
- [ ] REQ-ING-013: Auto-update Product records on hierarchy change
- [ ] REQ-ING-014: Auto-update Recipe records on attribute change
- [ ] Section 10.1: Creation validation with UI feedback

**Phase 4 (PENDING → F036):**
- [ ] REQ-ING-018/019/020: Recipe integration verified and working
- [ ] Section 10.3: Deletion validation implemented

### Should Have (High Priority)

All items moved to appropriate phases above.

### Nice to Have (Can Defer)

- [ ] Inline subcategory creation in edit form
- [ ] Batch operations (move multiple ingredients)
- [ ] Hierarchy visualization (tree view)
- [ ] Clear/reset filter buttons

---

## Conclusion

The ingredient hierarchy implementation is **critically incomplete** (~45% done). While foundational infrastructure exists (schema, basic services), the UI layer is fundamentally broken with wrong mental models, and validation is almost entirely missing.

**Key Issues:**
1. **Conceptual Error:** UI treats level as assignable instead of computed
2. **Missing Validation:** Zero protection against orphaning products/recipes
3. **Broken Cascading:** Filters don't update properly
4. **Integration Gaps:** Recipe integration unverified, Product edit hangs

**Recommendation:** Allocate 50-72 hours (7-10 days) to complete this properly before moving to next features. Ingredient hierarchy is foundational and touches everything - getting it wrong cascades problems throughout the system.

---

**END OF GAP ANALYSIS**
