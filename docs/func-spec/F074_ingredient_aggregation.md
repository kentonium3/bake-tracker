# F074: Ingredient Aggregation

**Version**: 1.0  
**Priority**: HIGH  
**Type**: Service Layer (Pure Calculation)

---

## Executive Summary

Cannot generate shopping list without aggregating ingredients across all recipe batches:
- ❌ No variant proportion calculation
- ❌ No base ingredient scaling by batches
- ❌ No variant ingredient scaling by proportion
- ❌ No cross-recipe ingredient aggregation

This spec implements ingredient calculation algorithms that convert batch decisions into total ingredient quantities, prerequisite for shopping list (F075).

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Batch Decisions
└─ ✅ User selected batches per recipe (F073)

Ingredient Totals
└─ ❌ No calculation of total ingredients needed
```

**Target State (COMPLETE):**
```
Variant Proportion Calculation
└─ ✅ Calculate how batches split across variants

Ingredient Scaling
├─ ✅ Base ingredients × batches × batch_multiplier
└─ ✅ Variant ingredients × batches × multiplier × proportion

Cross-Recipe Aggregation
└─ ✅ Sum same ingredient from different recipes

Ingredient Totals Output
└─ ✅ {(Ingredient, Unit) → total_quantity}
```

---

## CRITICAL: Study These Files FIRST

1. **Recipe ingredients structure**
   - Find recipe_ingredients model (base ingredients)
   - Find variant_ingredient_changes model
   - Understand quantity, unit, action fields

2. **Batch decisions (F073)**
   - Find how to get batch decisions per event
   - Understand yield_option relationship
   - Note batch_multiplier usage

3. **Recipe decomposition (F072)**
   - Study how recipe requirements calculated
   - Understand FG → Recipe mapping
   - Note quantity aggregation approach

---

## Requirements Reference

Implements:
- **REQ-PLAN-035** through **REQ-PLAN-046**: Variant allocation and ingredient aggregation
- Section 7.4 and 7.5 from req_planning.md (v0.4)

---

## Functional Requirements

### FR-1: Calculate Variant Proportions

**What it must do:**
- For recipes producing multiple FG variants, calculate proportion of each
- Proportion = variant_quantity_needed / total_recipe_yield
- Validate proportions sum to ~100%

**Success criteria:**
- [ ] Proportions calculated correctly
- [ ] Sum validation works
- [ ] Handles base + variant combinations

---

### FR-2: Scale Base Ingredients

**What it must do:**
- Base ingredient quantity × batches × batch_multiplier
- Maintain precision to 3 decimal places

**Success criteria:**
- [ ] Scaling math correct
- [ ] Precision maintained
- [ ] All base ingredients processed

---

### FR-3: Scale Variant Ingredients

**What it must do:**
- Variant ingredient quantity × batches × batch_multiplier × variant_proportion
- Only process "add" actions

**Success criteria:**
- [ ] Scaling includes proportion
- [ ] Only additions processed
- [ ] Math correct

---

### FR-4: Aggregate Across Recipes

**What it must do:**
- Sum same (ingredient, unit) pairs from different recipes
- Keep different forms separate
- Return aggregated totals

**Success criteria:**
- [ ] Cross-recipe aggregation works
- [ ] Different forms separate
- [ ] Output structure correct

---

## Out of Scope

- ❌ Inventory gap analysis (F075)
- ❌ Unit conversion
- ❌ Substitution suggestions

---

## Success Criteria

### Calculations
- [ ] Variant proportions correct
- [ ] Base ingredient scaling works
- [ ] Variant ingredient scaling works
- [ ] Cross-recipe aggregation works
- [ ] Precision maintained

### Quality
- [ ] Algorithm handles edge cases
- [ ] Performance acceptable
- [ ] Code follows patterns
- [ ] Unit tests comprehensive

---

## Architecture Principles

**Pure Calculation:**
- No side effects
- Deterministic
- Testable independently

---

## Constitutional Compliance

✅ **Deterministic Calculations**
✅ **Separation of Concerns**
✅ **Pattern Matching**

---

## Notes for Implementation

Study F072 decomposition patterns, apply to ingredient aggregation.

---

**END OF SPECIFICATION**
