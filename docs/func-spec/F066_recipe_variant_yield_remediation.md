# F066: Recipe Variant Yield Remediation

**Version**: 1.0  
**Priority**: HIGH (P0 - Fixes F063 Gaps)  
**Type**: Service Layer + UI Polish  
**Status**: Draft  
**Created**: 2025-01-24

---

## Executive Summary

F063 (Recipe Variant Yield Inheritance) implementation has gaps preventing proper variant usage:
- ❌ **Phase 1 (CRITICAL - Bug Fix):** NULL yield fields on variant FinishedUnits - BEING FIXED BY CLAUDE CODE
- ❌ **Phase 2 (HIGH):** Missing service primitives cause tight coupling between services
- ❌ **Phase 3 (HIGH):** UI confusion with terminology, edit flow, and missing base recipe references
- ✅ **Phase 4 (MEDIUM):** Yield change detection - DEFERRED to future feature

This spec addresses **Phase 2 (Service Primitives)** and **Phase 3 (UI Polish)** to complete F063 implementation.

Phase 1 is being fixed as a direct bug fix by Claude Code (NULL yield fields → copy from base).

---

## Problem Statement

**Current State (POST-PHASE-1-FIX):**
```
Service Layer
├─ ✅ Variant FinishedUnits have correct yield values (Phase 1 fix)
├─ ❌ No get_finished_units(recipe_id) universal primitive
├─ ❌ No get_base_yield_structure(recipe_id) for variants
├─ ❌ Services use recipe.finished_units directly (tight coupling)
├─ ❌ Planning/Production/Cost services coupled to Recipe model
└─ ❌ No abstraction between base and variant yield access

UI Layer
├─ ✅ Can create variants
├─ ❌ Confusing terminology ("finished unit" vs "yield" vs "output")
├─ ❌ Edit flow unclear (can users edit variant yields?)
├─ ❌ No visual reference to base recipe yields
└─ ❌ RecipeFormDialog doesn't handle variants properly
```

**Target State (COMPLETE):**
```
Service Layer
├─ ✅ get_finished_units(recipe_id) returns yields for ANY recipe
├─ ✅ get_base_yield_structure(recipe_id) returns base recipe yields
├─ ✅ Planning/Production/Cost services use primitives (decoupled)
├─ ✅ No direct access to recipe.finished_units in services
└─ ✅ Consistent abstraction across all recipe types

UI Layer
├─ ✅ Clear terminology (consistent "yields" language)
├─ ✅ Variant creation shows base recipe yields as reference
├─ ✅ Edit flow clarified (variants inherit, don't override)
├─ ✅ RecipeFormDialog handles variants correctly
└─ ✅ Visual distinction between base and variant recipes
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **F063 Specification (Original Variant Spec)**
   - Find `/docs/func-spec/F063_recipe_variant_yield_inheritance.md`
   - Study original requirements (REQ-RCP-031 through REQ-RCP-044)
   - Note what was intended vs what gaps exist

2. **Recipe Service (Current Implementation)**
   - Find `/src/services/recipe_service.py`
   - Study create_variant() implementation (Phase 1 bug location)
   - Note how base recipe relationship works
   - Understand current yield access patterns

3. **FinishedUnit Service (Yield Management)**
   - Find `/src/services/finished_unit_service.py`
   - Study CRUD operations for FinishedUnits
   - Note relationship to recipes
   - Understand yield validation

4. **Planning Service (Yield Consumer)**
   - Find `/src/services/planning/planning_service.py`
   - Study how it accesses recipe yields
   - Note batch calculations using yields
   - Understand coupling to Recipe model

5. **Production Service (Yield Consumer)**
   - Find `/src/services/batch_production_service.py`
   - Study how production uses recipe yields
   - Note any direct recipe.finished_units access

6. **Cost Service (Yield Consumer)**
   - Find `/src/services/cost_service.py` (if exists)
   - Study how costs are calculated per yield
   - Note yield assumptions

7. **Recipe Form Dialog (UI)**
   - Find `/src/ui/dialogs/recipe_form_dialog.py`
   - Study current recipe editing UI
   - Note how variants are (or aren't) handled

8. **Variant Creation Dialog (UI)**
   - Find `/src/ui/dialogs/variant_creation_dialog.py`
   - Study terminology used
   - Note how base recipe yields are displayed
   - Understand user flow

9. **Requirements Specification**
   - Find `/docs/requirements/req_recipes.md`
   - Study Section 5.6: Variant Yield Inheritance
   - Note REQ-RCP-041 through REQ-RCP-044 (service primitives)

10. **Code Review Findings**
    - Review Claude Code's assessment (pasted in issue)
    - Note specific service coupling issues identified
    - Understand UI confusion points

---

## Requirements Reference

This specification completes F063 implementation by addressing:
- **REQ-RCP-041** through **REQ-RCP-044**: Service primitives for yield access
- **UI/UX gaps** identified in post-F063 review
- **Service coupling** preventing clean abstraction

From: `docs/requirements/req_recipes.md` Section 5.6a

---

## Functional Requirements

### FR-1: Universal get_finished_units() Primitive

**What it must do:**
- Add `get_finished_units(recipe_id, session=None)` to recipe_service
- Works for BOTH base recipes and variants
- For base recipes: returns recipe.finished_units
- For variants: returns variant's own finished_units (inherited from base)
- Returns list of FinishedUnit objects with complete yield data
- Accept optional session parameter for transaction consistency
- No caller needs to know if recipe is base or variant

**Pattern reference:** Study existing recipe_service CRUD patterns for session management

**Implementation:**
```python
def get_finished_units(recipe_id: int, session: Session = None) -> list:
    """
    Get all FinishedUnits (yields) for a recipe.
    
    Works for both base recipes and variants. Variants return their own
    FinishedUnits which inherit yield structure from base recipe.
    
    Args:
        recipe_id: Recipe ID (base or variant)
        session: Optional session for transaction consistency
    
    Returns:
        List of FinishedUnit objects for this recipe
    
    Raises:
        RecipeNotFoundError: If recipe doesn't exist
    """
    if session is not None:
        return _get_finished_units_impl(recipe_id, session)
    
    with session_scope() as session:
        return _get_finished_units_impl(recipe_id, session)

def _get_finished_units_impl(recipe_id: int, session: Session) -> list:
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise RecipeNotFoundError(f"Recipe {recipe_id} not found")
    
    # Works for both base and variant - they all have finished_units
    return list(recipe.finished_units)
```

**Success criteria:**
- [ ] get_finished_units() exists in recipe_service
- [ ] Works for base recipes
- [ ] Works for variant recipes
- [ ] Returns complete FinishedUnit list
- [ ] Session parameter pattern followed
- [ ] Raises RecipeNotFoundError if recipe missing

---

### FR-2: Variant get_base_yield_structure() Primitive

**What it must do:**
- Add `get_base_yield_structure(recipe_id, session=None)` to recipe_service
- Returns base recipe's yield specifications for a variant
- For base recipes: raises ValidationError (no base recipe)
- For variants: returns base_recipe.finished_units yield data
- Returns list of dicts with yield specifications (not full FinishedUnit objects)
- Used during variant creation to show reference yields
- Accept optional session parameter

**Pattern reference:** Similar to get_finished_units but returns structured data for display

**Implementation:**
```python
def get_base_yield_structure(recipe_id: int, session: Session = None) -> list[dict]:
    """
    Get base recipe yield structure for a variant recipe.
    
    Returns yield specifications from the variant's base recipe.
    Used during variant creation to display reference yields.
    
    Args:
        recipe_id: Variant recipe ID
        session: Optional session for transaction consistency
    
    Returns:
        List of yield spec dicts:
        [
            {
                "display_name": "Chocolate Chip Cookie",
                "items_per_batch": 32,
                "item_unit": "cookie",
                "yield_mode": "DISCRETE_COUNT",
                "batch_percentage": None,
                "portion_description": None
            }
        ]
    
    Raises:
        RecipeNotFoundError: If recipe doesn't exist
        ValidationError: If recipe is not a variant (has no base_recipe_id)
    """
    if session is not None:
        return _get_base_yield_structure_impl(recipe_id, session)
    
    with session_scope() as session:
        return _get_base_yield_structure_impl(recipe_id, session)

def _get_base_yield_structure_impl(recipe_id: int, session: Session) -> list[dict]:
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise RecipeNotFoundError(f"Recipe {recipe_id} not found")
    
    if not recipe.base_recipe_id:
        raise ValidationError(
            "Recipe is not a variant - no base recipe available"
        )
    
    base_recipe = session.get(Recipe, recipe.base_recipe_id)
    
    return [
        {
            "display_name": fu.display_name,
            "items_per_batch": fu.items_per_batch,
            "item_unit": fu.item_unit,
            "yield_mode": fu.yield_mode.value,
            "batch_percentage": float(fu.batch_percentage) if fu.batch_percentage else None,
            "portion_description": fu.portion_description
        }
        for fu in base_recipe.finished_units
    ]
```

**Success criteria:**
- [ ] get_base_yield_structure() exists in recipe_service
- [ ] Returns yield specs from base recipe
- [ ] Raises ValidationError for base recipes
- [ ] Raises RecipeNotFoundError if recipe missing
- [ ] Returns structured dict data (not objects)
- [ ] Session parameter pattern followed

---

### FR-3: Audit and Update Service Yield Access

**What it must do:**
- Audit all services that access recipe yields
- Replace direct `recipe.finished_units` with `get_finished_units(recipe_id)`
- Services to update: planning_service, batch_production_service, cost_service, assembly_service
- Ensure all yield access goes through primitive
- No service directly accesses Recipe.finished_units relationship
- Services don't need to know if recipe is base or variant

**Pattern reference:** Service decoupling - use primitives not direct model access

**Services requiring updates:**

**Planning Service:**
```python
# BEFORE (tightly coupled):
recipe = session.get(Recipe, recipe_id)
for finished_unit in recipe.finished_units:
    # Calculate batches needed

# AFTER (decoupled):
finished_units = recipe_service.get_finished_units(recipe_id, session=session)
for finished_unit in finished_units:
    # Calculate batches needed
```

**Production Service:**
```python
# BEFORE:
recipe = session.get(Recipe, recipe_id)
finished_units = recipe.finished_units

# AFTER:
finished_units = recipe_service.get_finished_units(recipe_id, session=session)
```

**Cost Service (if exists):**
```python
# BEFORE:
for finished_unit in recipe.finished_units:
    cost_per_unit = calculate_cost(...)

# AFTER:
finished_units = recipe_service.get_finished_units(recipe_id, session=session)
for finished_unit in finished_units:
    cost_per_unit = calculate_cost(...)
```

**Success criteria:**
- [ ] Planning service uses get_finished_units()
- [ ] Production service uses get_finished_units()
- [ ] Cost service uses get_finished_units() (if exists)
- [ ] Assembly service uses get_finished_units() (if relevant)
- [ ] No direct recipe.finished_units access in services
- [ ] All services pass session to primitive

---

### FR-4: Fix VariantCreationDialog Terminology

**What it must do:**
- Update VariantCreationDialog to use consistent "yield" terminology
- Replace confusing "finished unit" references with "yield" or "output"
- Show base recipe yields as read-only reference during variant creation
- Display yield specifications clearly (items_per_batch, item_unit, yield_mode)
- Use get_base_yield_structure() to fetch base yields
- Make it clear that variant inherits yields from base (cannot override)

**Pattern reference:** Study existing dialogs for terminology consistency

**UI updates:**
```python
# VariantCreationDialog layout
┌─────────────────────────────────────────────┐
│ Create Recipe Variant                        │
├─────────────────────────────────────────────┤
│ Base Recipe: Chocolate Chip Cookies          │
│                                              │
│ Variant Name: [________________]             │
│                                              │
│ Base Recipe Yields (Reference):              │
│ ┌───────────────────────────────────────┐   │
│ │ • Chocolate Chip Cookie               │   │
│ │   32 cookies per batch                │   │
│ │   (Discrete count yield)              │   │
│ └───────────────────────────────────────┘   │
│                                              │
│ Note: Variant will inherit these yields.    │
│ Edit display names after creation if needed. │
│                                              │
│ [Cancel]                        [Create]     │
└─────────────────────────────────────────────┘
```

**Success criteria:**
- [ ] Uses "yield" terminology consistently
- [ ] Shows base recipe yields as read-only reference
- [ ] Uses get_base_yield_structure() to fetch yields
- [ ] Clear message that variant inherits yields
- [ ] Display shows items_per_batch, item_unit, yield_mode
- [ ] No confusing "finished unit" references

---

### FR-5: Fix RecipeFormDialog Variant Handling

**What it must do:**
- RecipeFormDialog must detect when recipe is a variant
- For variants: disable yield editing (inherited from base)
- For variants: show "Base Recipe: [name]" reference
- For variants: allow editing display_name of inherited yields
- For base recipes: allow full yield editing as before
- Prevent users from trying to edit variant yield structure

**Pattern reference:** Conditional UI based on recipe type (base vs variant)

**UI changes:**
```python
# RecipeFormDialog for VARIANT
┌─────────────────────────────────────────────┐
│ Edit Recipe: Gluten-Free Chocolate Chip     │
├─────────────────────────────────────────────┤
│ Base Recipe: Chocolate Chip Cookies          │
│ (This is a variant - yields inherited)       │
│                                              │
│ Recipe Name: [Gluten-Free Chocolate Chip]    │
│ Category: [Cookies ▼]                        │
│                                              │
│ Yields (Inherited from Base):                │
│ ┌───────────────────────────────────────┐   │
│ │ Display Name: [GF Chocolate Chip     ]│   │
│ │ 32 cookies per batch                  │   │
│ │ (Yield structure cannot be edited)    │   │
│ └───────────────────────────────────────┘   │
│                                              │
│ Ingredients: [Edit]                          │
│ (Variant uses different ingredients)         │
└─────────────────────────────────────────────┘

# RecipeFormDialog for BASE
┌─────────────────────────────────────────────┐
│ Edit Recipe: Chocolate Chip Cookies          │
├─────────────────────────────────────────────┤
│ Recipe Name: [Chocolate Chip Cookies]        │
│ Category: [Cookies ▼]                        │
│                                              │
│ Yields:                                      │
│ ┌───────────────────────────────────────┐   │
│ │ Display Name: [Chocolate Chip Cookie]│   │
│ │ Items/Batch: [32]                     │   │
│ │ Unit: [cookie]                        │   │
│ │ Yield Mode: [Discrete Count ▼]       │   │
│ │ [Add Yield] [Remove]                  │   │
│ └───────────────────────────────────────┘   │
│                                              │
│ Ingredients: [Edit]                          │
└─────────────────────────────────────────────┘
```

**Success criteria:**
- [ ] Detects if recipe is variant (base_recipe_id not null)
- [ ] For variants: shows base recipe name
- [ ] For variants: disables yield structure editing
- [ ] For variants: allows display_name editing only
- [ ] For base recipes: full yield editing as before
- [ ] Clear messaging about inheritance

---

### FR-6: Add Tests for Service Primitives

**What it must do:**
- Unit tests for get_finished_units(recipe_id)
- Unit tests for get_base_yield_structure(recipe_id)
- Test both base and variant recipes
- Test error cases (recipe not found, not a variant)
- Integration tests for service updates
- Verify planning/production/cost use primitives correctly

**Pattern reference:** Study existing recipe_service tests

**Test coverage:**
```python
# test_recipe_service.py
def test_get_finished_units_base_recipe():
    # Returns base recipe's FinishedUnits
    
def test_get_finished_units_variant_recipe():
    # Returns variant's inherited FinishedUnits
    
def test_get_finished_units_recipe_not_found():
    # Raises RecipeNotFoundError

def test_get_base_yield_structure_variant():
    # Returns base recipe yield specs
    
def test_get_base_yield_structure_base_recipe():
    # Raises ValidationError (not a variant)
    
def test_get_base_yield_structure_recipe_not_found():
    # Raises RecipeNotFoundError

# test_planning_service.py
def test_planning_uses_get_finished_units():
    # Verify planning service calls primitive
    
# test_batch_production_service.py  
def test_production_uses_get_finished_units():
    # Verify production service calls primitive
```

**Success criteria:**
- [ ] Unit tests for get_finished_units()
- [ ] Unit tests for get_base_yield_structure()
- [ ] Error case tests (not found, validation)
- [ ] Integration tests for service updates
- [ ] All tests passing

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ **Phase 1 (NULL yield bug)** - Being fixed by Claude Code separately
- ❌ **Phase 4 (Yield change detection)** - Deferred to future feature (F068+)
- ❌ Yield override capability for variants (intentionally prohibited)
- ❌ Changing yield inheritance design (F063 design is correct)
- ❌ Batch calculation algorithm changes (works correctly with primitives)

---

## Success Criteria

**Complete when:**

### Service Layer
- [ ] get_finished_units(recipe_id) exists in recipe_service
- [ ] get_base_yield_structure(recipe_id) exists in recipe_service
- [ ] Session parameter pattern followed for both primitives
- [ ] Planning service uses get_finished_units()
- [ ] Production service uses get_finished_units()
- [ ] Cost service uses get_finished_units() (if exists)
- [ ] No services directly access recipe.finished_units
- [ ] Error handling correct (RecipeNotFoundError, ValidationError)

### UI Layer
- [ ] VariantCreationDialog uses "yield" terminology
- [ ] VariantCreationDialog shows base recipe yields as reference
- [ ] VariantCreationDialog uses get_base_yield_structure()
- [ ] RecipeFormDialog detects variants
- [ ] RecipeFormDialog disables yield editing for variants
- [ ] RecipeFormDialog shows base recipe reference for variants
- [ ] RecipeFormDialog allows display_name editing for variant yields
- [ ] Clear messaging about yield inheritance

### Testing
- [ ] Unit tests for get_finished_units()
- [ ] Unit tests for get_base_yield_structure()
- [ ] Integration tests for service updates
- [ ] Error case coverage
- [ ] UI behavior validated for both base and variant recipes

---

## Architecture Principles

### Service Decoupling

**Primitives over direct access:**
- Services use recipe_service.get_finished_units() instead of recipe.finished_units
- No service needs to know if recipe is base or variant
- Clear abstraction boundary between catalog and consumers

**Session consistency:**
- All primitives accept session parameter
- Services pass their session to primitives
- Transaction integrity maintained

### UI Clarity

**Consistent terminology:**
- Use "yields" not "finished units" in user-facing text
- Use "output" when describing what recipe produces
- Avoid technical model names in UI

**Visual inheritance cues:**
- Variants show base recipe reference
- Clear distinction between base and variant editing
- Read-only displays for inherited values

---

## Constitutional Compliance

✅ **Service Boundaries**
- recipe_service owns yield access logic
- Other services consume through well-defined primitives
- No service dictates Recipe model implementation

✅ **Session Management**
- All primitives follow session=None pattern
- Wrapper/impl structure for transaction management
- Services can share transactions via session parameter

✅ **Pattern Consistency**
- Primitive naming follows convention (get_X)
- Error handling consistent with existing patterns
- Return types appropriate for consumers

---

## Risk Considerations

**Risk: Services tightly coupled to Recipe model**
- Many services may access recipe.finished_units directly
- Mitigation: Comprehensive audit in planning phase
- Update all services in single feature for consistency

**Risk: UI changes affect user workflows**
- Users may be confused by terminology changes
- Mitigation: Clear messaging, consistent language throughout
- Test with Marianne to validate clarity

**Risk: Variant editing restrictions frustrate users**
- Users may want to edit variant yields
- Mitigation: Clear explanation that yields inherit from base
- Document that display_name can still be customized

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Audit ALL services for recipe.finished_units access
- Study RecipeFormDialog current variant handling
- Review VariantCreationDialog terminology
- Check if cost_service exists and uses yields
- Verify session patterns in existing recipe_service

**Key Patterns to Copy:**
- Recipe service CRUD primitives → get_finished_units/get_base_yield_structure
- Session management wrapper/impl → apply to new primitives
- RecipeFormDialog conditional logic → extend for variant detection
- Error handling patterns → apply to primitive validation

**Focus Areas:**
- Complete service audit (don't miss any recipe.finished_units access)
- UI terminology consistency (global search/replace for "finished unit")
- Clear error messages for validation failures
- Test coverage for all service updates

**Testing Strategy:**
- Unit test both primitives in isolation
- Integration test each service update
- UI test both base and variant recipe editing
- Error case coverage (not found, validation)
- Verify no performance regressions

---

**END OF SPECIFICATION**
