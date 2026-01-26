# F072: Recipe Decomposition & Aggregation

**Version**: 1.0  
**Priority**: HIGH  
**Type**: Service Layer (Pure Calculation Logic)

---

## Executive Summary

Cannot calculate batch requirements without aggregating FG quantities by recipe:
- ❌ No decomposition of nested FGs (bundles) to atomic recipes
- ❌ No mapping of FGs to their producing recipes
- ❌ No aggregation of quantities when multiple FGs use same recipe
- ❌ No handling of multi-level bundle nesting

This spec implements core decomposition and aggregation logic that converts "50 Holiday Boxes + 20 Cookie Packs" into "220 Base Buns needed, 150 Variant Scones needed" - the prerequisite for all downstream planning calculations.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Event FG Quantities
└─ ✅ User specified quantities per FG (F071)

Recipe Requirements
└─ ❌ No calculation of how many needed per recipe

Decomposition Logic
└─ ❌ Doesn't exist
```

**Target State (COMPLETE):**
```
Decomposition Algorithm
├─ ✅ Decompose nested FGs recursively
├─ ✅ Map atomic FGs to recipes
└─ ✅ Handle multi-level nesting

Aggregation Algorithm
├─ ✅ Group FGs by recipe
├─ ✅ Sum quantities for same recipe
└─ ✅ Return recipe requirements dict

Recipe Requirements
└─ ✅ {Recipe → total_quantity_needed}
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Bundle decomposition (F070)**
   - Find bundle decomposition to recipes algorithm
   - Study recursive traversal pattern
   - Note how nesting handled

2. **Finished Goods model**
   - Find FG structure (is_bundle flag, recipe relationship)
   - Understand bundle_contents structure
   - Note how atomic FGs link to recipes

3. **Recipe model**
   - Understand base vs variant recipes
   - Note recipe ID structure
   - Understand how FG links to recipe

4. **Existing aggregation patterns**
   - Find any existing summing/grouping algorithms
   - Study how dictionaries used for aggregation
   - Note performance considerations

---

## Requirements Reference

This specification implements:
- **REQ-PLAN-022**: System shall decompose nested finished goods to atomic recipe components
- **REQ-PLAN-023**: System shall group atomic components by the recipe that produces them
- **REQ-PLAN-024**: System shall aggregate quantities for each unique recipe (base or variant)
- **REQ-PLAN-025**: If FG uses base recipe, quantities aggregate to base
- **REQ-PLAN-026**: If FG uses variant recipe, quantities aggregate to that variant
- **REQ-PLAN-027**: System shall sum all quantities for each recipe across all finished goods

From: `docs/requirements/req_planning.md` (v0.4) - Section 7.2 (Recipe Decomposition Requirements)

---

## Functional Requirements

### FR-1: Implement Recursive FG Decomposition

**What it must do:**
- Given FG + quantity, return list of atomic (FG, quantity) pairs
- For atomic FG: return [(FG, quantity)]
- For bundle FG: recursively expand each component, multiply quantities
- Handle multi-level nesting (bundle contains bundle)
- Detect and handle circular references

**Decomposition logic:**
```
decompose(fg, quantity):
  if fg.is_atomic:
    return [(fg, quantity)]
  else:
    results = []
    for component in fg.bundle_contents:
      component_fg = component.finished_good
      component_qty = component.quantity * quantity
      results.extend(decompose(component_fg, component_qty))
    return results
```

**Pattern reference:** Study recursive tree traversal algorithms, copy structure

**Success criteria:**
- [ ] Atomic FGs return correctly
- [ ] Bundles expand recursively
- [ ] Quantity multiplication correct
- [ ] Multi-level nesting works
- [ ] Circular references detected

---

### FR-2: Map Atomic FGs to Producing Recipes

**What it must do:**
- Given atomic FG, determine which recipe produces it
- Handle base recipes
- Handle variant recipes
- Return recipe ID for aggregation

**Mapping logic:**
- FG has recipe_id or produced_by_recipe relationship
- Direct lookup: fg.recipe_id or fg.produced_by_recipe.id

**Pattern reference:** Simple attribute access or relationship traversal

**Success criteria:**
- [ ] Base recipe FGs map correctly
- [ ] Variant recipe FGs map correctly
- [ ] Recipe ID retrieved correctly
- [ ] Handles null recipes (validation error)

---

### FR-3: Aggregate Quantities by Recipe

**What it must do:**
- Given list of (atomic FG, quantity) pairs, group by recipe
- Sum quantities for same recipe
- Return dictionary: {recipe_id → total_quantity}
- Preserve recipe objects (not just IDs) for downstream use

**Aggregation logic:**
```
aggregate(atomic_pairs):
  recipe_totals = {}
  for (fg, qty) in atomic_pairs:
    recipe = fg.produced_by_recipe
    if recipe.id in recipe_totals:
      recipe_totals[recipe.id] += qty
    else:
      recipe_totals[recipe.id] = qty
  return recipe_totals
```

**Pattern reference:** Standard dictionary aggregation pattern

**Success criteria:**
- [ ] Quantities sum correctly
- [ ] Multiple FGs with same recipe aggregate
- [ ] Dictionary structure correct
- [ ] Recipe objects preserved

---

### FR-4: Integrate Decompose + Aggregate Pipeline

**What it must do:**
- Provide single method: calculate_recipe_requirements(event)
- Input: event with FG selections and quantities
- Process: decompose all FGs, map to recipes, aggregate
- Output: {Recipe → total_quantity_needed}

**Service interface:**
```
PlanningService.calculate_recipe_requirements(event_id):
  → Dict[Recipe, int]  # Recipe object → total quantity needed
```

**Pipeline:**
1. Get event FG quantities from event_finished_goods
2. For each (FG, quantity), decompose to atomic pairs
3. For each atomic pair, get producing recipe
4. Aggregate quantities by recipe
5. Return recipe requirements dictionary

**Pattern reference:** Service method pattern from F068

**Success criteria:**
- [ ] Method accepts event ID
- [ ] Pipeline executes correctly
- [ ] Output structure correct
- [ ] Error handling robust

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Batch calculation (F073 - uses output from this feature)
- ❌ Variant allocation (F074 - separate concern)
- ❌ Ingredient aggregation (F074 - separate concern)
- ❌ UI display of recipe requirements (F073 shows batch options instead)
- ❌ Caching of decomposition results (optimization for later)

---

## Success Criteria

**Complete when:**

### Decomposition
- [ ] Recursive decomposition works
- [ ] Atomic FGs handled
- [ ] Bundles expanded correctly
- [ ] Multi-level nesting works
- [ ] Quantity multiplication correct
- [ ] Circular references detected

### Recipe Mapping
- [ ] FG-to-recipe mapping works
- [ ] Base recipes identified
- [ ] Variant recipes identified
- [ ] Null recipe handled (error)

### Aggregation
- [ ] Quantities sum correctly
- [ ] Dictionary structure correct
- [ ] Multiple FGs per recipe aggregate
- [ ] Recipe objects preserved

### Pipeline Integration
- [ ] Service method works end-to-end
- [ ] Input validation works
- [ ] Output structure correct
- [ ] Error handling robust

### Quality
- [ ] Algorithm handles edge cases
- [ ] Performance acceptable
- [ ] Code follows patterns
- [ ] Unit tests comprehensive

---

## Architecture Principles

### Pure Calculation Layer

**No Side Effects:**
- Decomposition is pure calculation
- No database writes
- No state modifications
- Deterministic output

**Why this matters:**
- Testable independently
- Composable with other operations
- Cacheable results
- Predictable behavior

### Recursive Algorithm Design

**Base Case:**
- Atomic FG returns itself with quantity
- Terminates recursion

**Recursive Case:**
- Bundle processes each component
- Recurses on nested bundles
- Aggregates results

**Termination Guarantee:**
- Must reach atomic FGs eventually
- Circular reference detection prevents infinite loops

### Data Structure Choice

**Dictionary for Aggregation:**
- Key: Recipe ID (or Recipe object)
- Value: Total quantity needed
- Efficient lookup and update
- Natural representation for downstream use

---

## Constitutional Compliance

✅ **Principle I: Separation of Concerns**
- Decomposition separate from aggregation
- Each algorithm focused and single-purpose
- Composable components

✅ **Principle II: Deterministic Calculations**
- Same inputs always produce same outputs
- No hidden state
- Pure functions

✅ **Principle III: Pattern Matching**
- Recursive algorithms match existing patterns
- Service methods match F068 patterns
- Dictionary aggregation matches established patterns

✅ **Principle IV: Testability**
- Pure calculation logic easy to test
- No database dependencies for algorithm
- Unit tests can cover edge cases

✅ **Principle V: Performance Considerations**
- Algorithm complexity documented
- No unnecessary iterations
- Efficient data structures

---

## Risk Considerations

**Risk: Circular references in bundle structure**
- **Context:** Bundle A contains Bundle B, Bundle B contains Bundle A
- **Mitigation:** Detection algorithm with visited set, error on circular reference or prevent at bundle creation (separate feature)

**Risk: Performance with deeply nested bundles**
- **Context:** 5+ levels of nesting could be slow
- **Mitigation:** Document complexity, implement memoization if needed in future

**Risk: Recipe link missing for FG**
- **Context:** FG without recipe cannot be decomposed
- **Mitigation:** Validation at FG creation time (separate concern), error handling in decomposition

**Risk: Integer overflow with large quantities**
- **Context:** Quantity multiplication in nested bundles could overflow
- **Mitigation:** Python handles big integers natively, validate reasonable quantity limits at input

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study recursive algorithms in codebase
- Study F070 bundle decomposition (if it decomposed to recipes)
- Study dictionary aggregation patterns
- Study PlanningService structure (F068)

**Key Patterns to Copy:**
- Recursive tree traversal → Decomposition algorithm
- Dictionary aggregation → Recipe quantity summing
- Service methods (F068) → calculate_recipe_requirements

**Focus Areas:**
- **Correctness:** Algorithm must handle all nesting levels
- **Termination:** Must detect circular references
- **Efficiency:** Avoid redundant decompositions
- **Testability:** Write comprehensive unit tests

**Test Cases to Consider:**
- Atomic FG (no nesting)
- Bundle with atomic components
- Bundle with bundle components (2-level nesting)
- Bundle with 3+ level nesting
- Multiple FGs using same recipe
- Circular reference detection
- Large quantities (thousands)
- Empty event (no FGs selected)

**Example Flow:**
```
Event Requirements:
  50 Holiday Boxes (bundle: 2 base buns + 3 variant scones each)
  20 Plain Bun Packs (bundle: 6 base buns each)

Step 1 - Decompose:
  Holiday Box → 2 Base Buns, 3 Variant Scones (per box)
  50 boxes → 100 Base Buns, 150 Variant Scones
  
  Plain Bun Pack → 6 Base Buns (per pack)
  20 packs → 120 Base Buns

Step 2 - Map to Recipes:
  Base Buns → Base Bun Recipe
  Variant Scones → Variant Scone Recipe

Step 3 - Aggregate:
  Base Bun Recipe: 100 + 120 = 220 needed
  Variant Scone Recipe: 150 needed

Output:
  {
    BaseBunRecipe: 220,
    VariantSconeRecipe: 150
  }
```

---

**END OF SPECIFICATION**
