# F070: Finished Goods Filtering

**Version**: 1.0  
**Priority**: HIGH  
**Type**: Service Layer + UI Enhancement

---

## Executive Summary

Baker cannot see which finished goods are makeable until recipes are selected, and system doesn't prevent invalid selections:
- ❌ No dynamic filtering of finished goods based on recipe selections
- ❌ User can attempt to select FGs requiring unselected recipes
- ❌ No clear feedback about why FG is unavailable
- ❌ Nested FGs (bundles) not validated for ALL atomic recipe requirements

This spec implements dynamic FG filtering that shows only makeable finished goods, prevents invalid selections, and provides clear feedback about dependencies.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Recipe Selection
└─ ✅ User can select recipes (F069)

Finished Goods Display
└─ ❌ Shows all FGs regardless of recipe selection

FG Availability Validation
└─ ❌ No check if FG's recipe is selected

Bundle Validation
└─ ❌ No check if ALL bundle components' recipes selected

User Feedback
└─ ❌ No indication why FG unavailable
```

**Target State (COMPLETE):**
```
Dynamic FG Filtering
├─ ✅ Shows only FGs where recipe is selected
├─ ✅ Hides FGs where recipe not selected
└─ ✅ Real-time updates when recipe selection changes

Bundle Validation (Nested FGs)
├─ ✅ Decompose bundles to atomic FGs
├─ ✅ Check ALL atomic recipes selected
└─ ✅ Show/hide bundle based on complete availability

User Feedback
├─ ✅ Clear indication which FGs available
├─ ✅ Clear indication which FGs unavailable (if shown)
└─ ✅ Explanation of missing recipe dependency

Selection Protection
└─ ✅ Clear invalid FG selections when recipe deselected
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Finished Goods service and model**
   - Find FinishedGoodsService methods
   - Understand FG model structure (atomic vs bundle, recipe relationships)
   - Note how to query all FGs
   - Understand bundle contents structure (BundleContent model)

2. **Recipe-FG relationship**
   - Find how FG links to recipe (finished_good.recipe_id or produced_by_recipe)
   - Understand base recipe vs variant recipe linkage
   - Note how bundles store component FGs

3. **Recipe selection state (F069)**
   - Find how to get currently selected recipes for event
   - Understand when selection changes (triggers for filtering)
   - Note how selection state maintained

4. **Decomposition algorithm patterns**
   - Find existing recursive algorithms in codebase
   - Study tree traversal patterns
   - Note how nested structures flattened

---

## Requirements Reference

This specification implements:
- **REQ-PLAN-013**: System shall filter finished goods list based on selected recipes
- **REQ-PLAN-014**: A finished good shall be selectable ONLY if ALL its atomic recipe components are in the selected recipe list
- **REQ-PLAN-015**: For nested finished goods (bundles), system shall decompose to atomic recipes for filtering
- **REQ-PLAN-016**: System shall update finished goods list immediately when recipe selection changes
- **REQ-PLAN-017**: System shall clearly indicate why a finished good is not available (missing recipe dependency)

From: `docs/requirements/req_planning.md` (v0.4) - Mental Model Section 2.2.1

---

## Functional Requirements

### FR-1: Implement FG Availability Checking Service

**What it must do:**
- Given a list of selected recipe IDs and a finished good, determine if FG is available
- For atomic FG: check if FG's recipe is in selected list
- For bundle FG: recursively decompose to atomic FGs, check ALL atomic recipes in selected list
- Return boolean: is_available
- Return list of missing recipe IDs (for feedback)

**Service interface needed:**
```
check_fg_availability(fg_id, selected_recipe_ids) → {
    is_available: bool,
    missing_recipe_ids: List[int],
    atomic_recipe_ids_required: List[int]
}
```

**Pattern reference:** Create new method in PlanningService or FinishedGoodsService, study existing service patterns

**Business rules:**
- Atomic FG available if its recipe in selected list
- Bundle available if ALL component atomic recipes in selected list
- Empty selected list → no FGs available

**Success criteria:**
- [ ] Method correctly identifies atomic FG availability
- [ ] Method recursively decomposes bundles
- [ ] Method returns missing recipe IDs
- [ ] Method handles multi-level nesting

---

### FR-2: Implement Bundle Decomposition to Atomic Recipes

**What it must do:**
- Given a finished good (potentially bundle), return list of ALL atomic recipe IDs required
- Recursively traverse bundle structure (bundle can contain bundles)
- Collect unique recipe IDs from atomic FGs
- Handle circular references gracefully (error or detection)

**Decomposition logic:**
- If FG is atomic: return [FG.recipe_id]
- If FG is bundle: for each component FG, recursively decompose and collect recipe IDs
- Flatten nested lists, return unique recipe IDs

**Pattern reference:** Recursive tree traversal, study similar algorithms in codebase

**Success criteria:**
- [ ] Atomic FG returns single recipe ID
- [ ] Bundle returns all component recipe IDs
- [ ] Multi-level bundles fully decomposed
- [ ] Duplicate recipe IDs removed (unique list)
- [ ] Handles circular references

---

### FR-3: Dynamic FG List Filtering

**What it must do:**
- Display finished goods list filtered by availability
- Show only available FGs (where all recipes selected)
- Update list immediately when recipe selection changes
- Optionally show unavailable FGs with visual indication (grayed out, disabled)

**UI Requirements:**
- FG list updates automatically when recipes selected/deselected
- Available FGs clearly selectable
- Unavailable FGs either hidden OR shown but disabled with explanation
- Performance acceptable (filter should be fast)

**Filtering behavior decision (planning phase determines):**
- Option A: Hide unavailable FGs completely (simpler UX)
- Option B: Show but disable unavailable FGs (more informative)

**Pattern reference:** Study filtered list implementations, reactive UI patterns

**Success criteria:**
- [ ] List shows only available FGs
- [ ] List updates when recipe selection changes
- [ ] Update is immediate (no lag)
- [ ] Visual distinction for availability clear
- [ ] Performance acceptable for large catalogs

---

### FR-4: Missing Recipe Dependency Feedback

**What it must do:**
- If FG unavailable, show user which recipe(s) missing
- Feedback should be clear and actionable
- For bundles, explain which component requires missing recipe

**UI Requirements:**
- Tooltip, label, or message shows missing recipes
- User understands what to do (select missing recipe)
- Feedback specific (not generic "unavailable")

**Feedback format examples:**
- "Requires: Chocolate Chip Cookie (variant) - not selected"
- "Bundle requires 2 recipes: Cookie Base, Brownie - select both to enable"

**Pattern reference:** Study tooltip patterns, validation message patterns

**Success criteria:**
- [ ] Missing recipes identified correctly
- [ ] User receives clear feedback
- [ ] Feedback actionable (tells user what to do)
- [ ] Works for atomic FGs and bundles

---

### FR-5: Clear Invalid FG Selections When Recipe Deselected

**What it must do:**
- When user deselects a recipe, check if any selected FGs depend on it
- Remove those FG selections automatically
- Notify user of automatic removal
- Update quantity specifications accordingly

**Protection logic:**
- Monitor recipe deselection events
- Query which FGs depend on deselected recipe
- If any selected FGs affected, remove from event_finished_goods
- Show notification to user

**Pattern reference:** Cascade deletion patterns, UI notification patterns

**Success criteria:**
- [ ] Deselecting recipe removes dependent FGs
- [ ] User notified of automatic removal
- [ ] Database updated correctly
- [ ] Quantities cleared for removed FGs

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Quantity specification for FGs (F071)
- ❌ Recipe search/filtering (future enhancement)
- ❌ FG search/filtering (future enhancement)
- ❌ Sorting FGs by category (use default order)
- ❌ Favoriting or recently used FGs (future enhancement)

---

## Success Criteria

**Complete when:**

### Service Layer
- [ ] FG availability checking works
- [ ] Bundle decomposition recursive algorithm works
- [ ] Multi-level nesting handled
- [ ] Missing recipe identification works
- [ ] Service methods performant

### FG List Filtering
- [ ] Only available FGs displayed
- [ ] List updates when recipe selection changes
- [ ] Real-time updates work
- [ ] No performance lag

### User Feedback
- [ ] Unavailable FGs indicated clearly
- [ ] Missing recipe dependencies shown
- [ ] Feedback is actionable
- [ ] Works for atomic FGs and bundles

### Selection Protection
- [ ] Deselecting recipe removes dependent FGs
- [ ] User notified of removals
- [ ] Database state consistent
- [ ] No orphaned selections

### Quality
- [ ] Recursive algorithm handles edge cases
- [ ] Circular reference detection works
- [ ] Code follows established patterns
- [ ] Error handling robust

---

## Architecture Principles

### Filtering Strategy

**Real-Time Filtering:**
- Filtering happens in UI layer based on service data
- Service provides availability data
- UI renders filtered list

**Why this approach:**
- Keeps UI responsive
- Allows flexible presentation (hide vs show disabled)
- Service layer focused on availability logic, not presentation

### Decomposition Algorithm

**Recursive Tree Traversal:**
- Bundle decomposition is recursive by nature
- Each level returns its required recipes
- Parent aggregates child results

**Termination:**
- Base case: atomic FG returns single recipe ID
- Recursive case: bundle processes components
- Handles arbitrary nesting depth

### Data Integrity

**Cascade Protection:**
- Removing recipe must clean up dependent FG selections
- Prevents invalid state (selected FG with unselected recipe)
- User notified of automatic changes

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- Invalid FG selections automatically removed
- Database state stays consistent
- No orphaned references

✅ **Principle II: Layered Architecture**
- Service layer handles availability logic
- UI layer handles presentation and filtering
- Clear separation maintained

✅ **Principle III: Service Primitives**
- Availability checking is atomic operation
- Decomposition is standalone algorithm
- Composable for higher-level features

✅ **Principle IV: User Intent Respected**
- Automatic removal of invalid selections protects user
- User notified of changes
- Transparent operation

✅ **Principle V: Pattern Matching**
- Recursive algorithms match existing patterns
- Service methods match established structures
- UI filtering matches existing filtered list patterns

---

## Risk Considerations

**Risk: Performance with large FG catalogs and deep nesting**
- **Context:** If bundles are deeply nested and catalog is large, filtering could be slow
- **Mitigation:** Planning phase should implement caching of decomposition results, consider memoization

**Risk: Circular references in bundle structure**
- **Context:** Bundle A contains Bundle B, Bundle B contains Bundle A
- **Mitigation:** Detection algorithm needed, either prevent at bundle creation or detect during decomposition

**Risk: User confused by automatic FG removal**
- **Context:** User deselects recipe, FGs disappear without clear explanation
- **Mitigation:** Clear notification showing what was removed and why, undo option if feasible

**Risk: Race conditions in real-time updates**
- **Context:** User rapidly changes recipe selections, UI updates lag
- **Mitigation:** Debounce updates if needed, ensure state consistency

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study FinishedGoodsService → understand FG and bundle structure
- Study bundle decomposition → understand how to traverse nested FGs
- Study recipe-FG relationships → understand linkage model
- Study reactive UI patterns → understand how to trigger re-filtering

**Key Patterns to Copy:**
- Recursive tree traversal → Bundle decomposition algorithm
- Filtered list rendering → FG list filtering
- Cascade deletion → Invalid selection removal
- Notification patterns → User feedback on changes

**Focus Areas:**
- **Correctness:** Decomposition must handle all nesting levels
- **Performance:** Filtering must be fast enough for real-time feel
- **User feedback:** Clear indication of availability and missing recipes
- **Data consistency:** Removal of invalid selections must be reliable

**Algorithm Design:**
```
Decomposition pseudocode (for reference, not prescription):

get_required_recipes(fg):
  if fg.is_atomic:
    return [fg.recipe_id]
  else:  # is bundle
    recipes = set()
    for component in fg.bundle_contents:
      component_recipes = get_required_recipes(component.finished_good)
      recipes.update(component_recipes)
    return list(recipes)

check_availability(fg, selected_recipe_ids):
  required = get_required_recipes(fg)
  missing = [r for r in required if r not in selected_recipe_ids]
  return {
    'is_available': len(missing) == 0,
    'missing_recipe_ids': missing,
    'required_recipe_ids': required
  }
```

---

**END OF SPECIFICATION**
