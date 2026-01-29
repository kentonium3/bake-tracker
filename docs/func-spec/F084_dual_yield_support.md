# F084: Dual-Yield Support for Recipe Outputs

**Version**: 1.1 (Post-Implementation Clarification)
**Priority**: HIGH
**Type**: Service Layer + Schema Enhancement

---

## Executive Summary

Current gaps:
- ❌ Recipes can only define one finished unit (e.g., "1 cake" OR "16 slices" but not both)
- ❌ Planning calculations can't distinguish between whole-unit delivery (EA) and serving-based planning (SERVING)
- ❌ Unit field is free text, preventing deterministic yield selection logic

This spec adds dual-yield capability by separating user-facing descriptions from system calculation types, enabling recipes like cakes to define both whole-unit (EA) and serving-based (SERVING) yields for flexible planning workflows.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Recipe: Wedding Cake
├── ✅ Can define ingredients
├── ✅ Can define instructions
└── ❌ finished_unit: ONE yield only
    ├── unit: "cake" (free text, no calculation semantics)
    ├── quantity: 1.0
    └── ❌ Cannot express: "1 cake = 16 slices"

Planning Service
├── ✅ Calculates batches needed
└── ❌ Cannot choose between:
    ├── Plan by whole cakes (catering delivery)
    └── Plan by servings (consumption planning)

UI: Recipe Definition
├── ✅ User can add finished unit
└── ❌ User cannot express dual yield (EA + SERVING)
```

**Target State (COMPLETE):**
```
Recipe: Wedding Cake
├── ✅ Can define ingredients
├── ✅ Can define instructions
└── ✅ finished_unit: MULTIPLE yields possible
    ├── Yield 1: yield_type='EA', unit_description='3-tier cake', quantity=1.0
    └── Yield 2: yield_type='SERVING', unit_description='slice', quantity=100.0

Planning Service
├── ✅ Calculates batches needed
└── ✅ Selects appropriate yield:
    ├── get_yield(prefer_servings=True) → 100 slices
    └── get_yield(prefer_servings=False) → 1 cake

UI: Recipe Definition
├── ✅ User adds primary yield (required)
└── ✅ User optionally adds alternate yield
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Recipe Data Model**
   - Find `src/models/recipe.py` - Recipe and FinishedUnit models
   - Study current `finished_unit` table structure
   - Note relationship: Recipe → FinishedUnit (one-to-many)

2. **Recipe Service**
   - Find `src/services/recipe_service.py`
   - Study how finished_units are created/validated
   - Note validation patterns for recipe data

3. **Export/Import Patterns**
   - Find `src/services/export_service.py` - how finished_units export
   - Find `src/services/import_service.py` - how finished_units import
   - Study slug-based identification patterns

4. **Recipe UI**
   - Find `src/ui/tabs/recipes_tab.py`
   - Study how recipe details are displayed
   - Note edit workflow patterns

5. **Planning Service (Future Integration)**
   - Find `src/services/planning_service.py`
   - Note where yield quantities are used for calculations
   - Understand batch calculation logic

---

## Requirements Reference

This specification implements:
- **FR-REC-03**: Recipe must define finished unit(s) produced
- **FR-PLAN-02**: Planning must calculate batches based on yield
- **NFR-DATA-01**: Data model must support future extensibility

From: `docs/requirements/req_recipes.md` (v1.0) and `docs/requirements/req_planning.md` (v1.0)

---

## Functional Requirements

### FR-1: Split Unit Field into Description and Type

**What it must do:**
- Replace `finished_unit.unit` (TEXT) with two fields:
  - `unit_description` (TEXT) - user-facing name ("slice", "square", "cookie", "cake")
  - `yield_type` (TEXT) - calculation semantic ('EA' or 'SERVING')
- Maintain all existing finished_unit data through migration
- Preserve slug-based identification for portability

**Pattern reference:** Study how `material.unit_code` uses controlled vocabulary while `material.display_name` allows free text

**Success criteria:**
- [ ] Schema has `unit_description` and `yield_type` fields
- [ ] `yield_type` constrained to 'EA' or 'SERVING' via CHECK constraint
- [ ] All existing recipes migrated to new schema
- [ ] Export format includes both fields
- [ ] Import validates yield_type values

---

### FR-2: Enable Multiple Finished Units per Recipe

**What it must do:**
- Allow recipes to have 0-2 finished_unit records
- Enforce constraint: maximum ONE yield_type='EA' per recipe
- Enforce constraint: maximum ONE yield_type='SERVING' per recipe
- Require at least ONE finished_unit per recipe (either EA or SERVING)

**Pattern reference:** Study how `material_product` allows multiple records per material while enforcing uniqueness constraints

**Business rules:**
- Recipes MUST have at least one finished_unit
- Recipes MAY have both EA and SERVING yields (dual-yield)
- Recipes with only SERVING yield are valid (cookies, brownies)
- Recipes with only EA yield are valid (rare, but allowed)

**Success criteria:**
- [ ] UNIQUE constraint on (recipe_id, yield_type)
- [ ] Validation prevents duplicate yield_types per recipe
- [ ] Validation requires at least one finished_unit per recipe
- [ ] Service layer enforces business rules

---

### FR-3: Update Recipe Service for Dual-Yield

**What it must do:**
- Support creating/updating recipes with multiple finished_units
- Validate yield_type values ('EA' or 'SERVING' only)
- Validate uniqueness constraints (one EA, one SERVING max)
- Validate at least one finished_unit exists
- Handle deletion of finished_units with validation

**Pattern reference:** Study how `recipe_service.py` validates ingredients list, copy validation pattern for finished_units

**Success criteria:**
- [ ] `create_recipe()` accepts multiple finished_units
- [ ] `update_recipe()` handles finished_unit changes
- [ ] Validation prevents invalid yield_type values
- [ ] Validation prevents duplicate yield_types
- [ ] Error messages are clear and actionable

---

### FR-4: Extend Export/Import for Dual-Yield

**What it must do:**
- Export finished_units array (supports 0-2 items)
- Include `unit_description` and `yield_type` in export
- Import validates yield_type values during load
- Import enforces uniqueness constraints
- Maintain backward compatibility with single-yield exports

**Pattern reference:** Study how ingredients export as array in recipes.json, copy exact pattern for finished_units

**Export format:**
```json
{
  "recipe_slug": "wedding-cake",
  "finished_units": [
    {
      "unit_description": "3-tier cake",
      "yield_type": "EA",
      "quantity": 1.0
    },
    {
      "unit_description": "slice",
      "yield_type": "SERVING",
      "quantity": 100.0
    }
  ]
}
```

**Success criteria:**
- [ ] Export includes all finished_units as array
- [ ] Export includes both unit_description and yield_type
- [ ] Import validates yield_type is 'EA' or 'SERVING'
- [ ] Import enforces one EA, one SERVING max per recipe
- [ ] Single-yield recipes export/import correctly

---

### FR-5: Update Recipe UI for Dual-Yield

**What it must do:**
- Display all finished_units for a recipe (up to 2)
- Show unit_description and yield_type clearly
- Allow user to edit/delete finished_units
- Prevent deletion if it would leave zero finished_units
- Show validation errors for duplicate yield_types

**UI Requirements:**
- User must see which yield is EA vs SERVING
- User must be able to add/edit/delete yields
- UI must prevent saving invalid state (no finished_units)
- UI must prevent duplicate yield_types

**Note:** Exact UI design (list vs stacked forms, add button placement, etc.) determined during planning phase. Focus on WHAT the UI needs to accomplish.

**Success criteria:**
- [ ] Recipe detail view shows all finished_units
- [ ] User can distinguish EA from SERVING yields
- [ ] User can edit yield details (description, type, quantity)
- [ ] User cannot save recipe without finished_units
- [ ] Validation errors display clearly

---

### FR-6: Add Planning Service Yield Selection

**What it must do:**
- Provide method to get appropriate yield for planning context
- Support preference for SERVING yield when both exist
- Fallback to EA yield if SERVING not available
- Return consistent results for single-yield recipes

**Pattern reference:** Study how `material_service.get_material_by_slug()` handles lookup with fallback logic

**Yield selection logic:**
```
get_yield_for_planning(recipe_id, prefer_servings=True):
  if prefer_servings:
    try SERVING yield first
    fallback to EA yield if not found
  else:
    try EA yield first
    fallback to SERVING yield if not found
  
  if no yields exist:
    raise validation error
```

**Success criteria:**
- [ ] Planning service can request SERVING-preferred yield
- [ ] Planning service can request EA-preferred yield
- [ ] Single-yield recipes return their one yield regardless of preference
- [ ] Error raised if recipe has no finished_units (shouldn't happen due to validation)

---

### FR-7: Migrate Existing Data

**What it must do:**
- Classify existing finished_unit records as yield_type='SERVING' (safe default)
- Preserve unit text as unit_description
- Maintain all quantity values unchanged
- Enable constitutional export → schema change → import workflow

**Migration strategy:**
- All existing single-yield recipes become SERVING type
- User can manually add EA yield later if needed
- No data loss during migration

**Pattern reference:** Study how schema changes follow constitutional principle: export → modify schema → import

**Success criteria:**
- [ ] All existing finished_units migrated to new schema
- [ ] unit_description preserves original unit text
- [ ] yield_type set to 'SERVING' for all existing records
- [ ] Quantities unchanged
- [ ] Export before migration succeeds
- [ ] Import after migration succeeds

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Category-driven smart defaults (requires user feedback on real recipes) - **Future Phase 2**
- ❌ Output Mode UI in event planning (planning module not yet complete) - **Separate feature**
- ❌ Learning user's preferred unit descriptions - **Future enhancement**
- ❌ Automatic serving calculation from EA yield - **Requires domain knowledge**
- ❌ UI for choosing yield during event recipe selection - **Part of planning workflow, not recipe definition**

---

## Success Criteria

**Complete when:**

### Schema & Data Model
- [ ] `finished_unit` table has `unit_description` and `yield_type` fields
- [ ] CHECK constraint enforces yield_type IN ('EA', 'SERVING')
- [ ] UNIQUE constraint on (recipe_id, yield_type)
- [ ] All existing data migrated successfully
- [ ] Export/import format updated and documented

### Service Layer
- [ ] Recipe service validates yield_type values
- [ ] Recipe service enforces uniqueness constraints
- [ ] Recipe service enforces "at least one finished_unit" rule
- [ ] Planning service can select appropriate yield
- [ ] Yield selection logic handles all cases (dual-yield, single EA, single SERVING)

### UI
- [ ] Recipe detail shows all finished_units with clear EA/SERVING labels
- [ ] User can add/edit/delete finished_units
- [ ] Validation prevents saving invalid states
- [ ] Error messages are clear and actionable

### Export/Import
- [ ] finished_units export as array with unit_description and yield_type
- [ ] Import validates yield_type values
- [ ] Import enforces uniqueness constraints
- [ ] Single-yield recipes export/import correctly
- [ ] Dual-yield recipes export/import correctly

### Quality
- [ ] Pattern matches existing service validation approaches
- [ ] Error handling follows project standards
- [ ] Code reuses existing patterns (no unnecessary divergence)
- [ ] Constitutional export → import workflow works end-to-end

---

## Architecture Principles

### Yield Type Semantics

**EA (Each) - Whole deliverable unit:**
- Represents complete item produced by recipe (1 cake, 1 pie, 1 loaf)
- Used for delivery manifest, inventory tracking of whole items
- Typical for recipes where finished good is indivisible for delivery

**SERVING - Individual consumption unit:**
- Represents portions/servings produced by recipe (16 slices, 24 cookies)
- Used for consumption planning, serving counts
- May be same as EA (cookies) or different (cake slices)

### Recipe Variants and Multiple Yields

**IMPORTANT CLARIFICATION (Post-Implementation):**

The original spec suggested constraints that are too restrictive for real-world use cases. The actual implementation supports **multiple finished_units with the same yield_type** to accommodate recipe variants (e.g., different cake sizes from the same recipe).

**Example: Single Cake Recipe with Multiple Size Options**

A recipe can define multiple finished_units that represent different variants:

| Description | Unit | Type | Qty/Batch |
|------------|------|------|--------|
| Large cake | cake | EA | 1 |
| Large cake | slice | SERVING | 16 |
| Medium cake | cake | EA | 1 |
| Medium cake | slice | SERVING | 8 |
| Small cake | cake | EA | 1 |
| Small cake | slice | SERVING | 4 |

**What This Enables:**
- User can select which size variant to use when planning
- Each variant has both EA (whole unit) and SERVING (portions) defined
- Planning service can choose appropriate yield based on variant selection
- Same base recipe → different output configurations

**Constraints That DO Apply:**
- Each finished_unit must have valid yield_type ('EA' or 'SERVING')
- Recipe must have at least ONE finished_unit
- unit_description differentiates variants (e.g., "Large cake", "Medium cake")

**Constraints That DO NOT Apply:**
- ❌ "Maximum one EA per recipe" - FALSE, can have multiple EA definitions for variants
- ❌ "Maximum one SERVING per recipe" - FALSE, can have multiple SERVING definitions for variants
- ❌ "UNIQUE(recipe_id, yield_type)" - FALSE, uniqueness is on (recipe_id, unit_description, yield_type)

This flexibility supports the baker's mental model where one recipe can be executed at different scales or configurations.

### Data Model Separation

**unit_description (user-facing):**
- Free text field
- Allows baker's vocabulary ("slice", "square", "piece", "portion")
- Used for display, labels, communication

**yield_type (calculation logic):**
- Controlled enum: 'EA' or 'SERVING'
- Used by planning service for deterministic logic
- Enables future extensibility (output modes, smart defaults)

### Pattern Matching

**finished_units must match ingredients pattern exactly:**
- Both are one-to-many relationships to recipe
- Both export as arrays in JSON
- Both use service layer validation
- Both support empty arrays in export (though finished_units requires at least one)

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- Validation enforces business rules at service layer
- Database constraints prevent invalid states
- Migration preserves all existing data

✅ **Principle II: Immutability of Historical Records**
- Schema changes follow export → modify → import workflow
- No in-place database migrations
- Export format preserves data integrity

✅ **Principle III: Layered Architecture**
- Service layer handles business logic (validation)
- Models layer defines constraints (CHECK, UNIQUE)
- UI layer enforces user interaction rules

✅ **Principle IV: Slug-Based Portability**
- finished_unit references recipe by recipe_id (internal) and recipe_slug (export)
- Export format uses recipe_slug for cross-environment portability
- Import resolves slug → id mapping

✅ **Principle V: Explicit Over Implicit**
- Dual-yield is explicit: user adds second finished_unit
- yield_type makes calculation semantics explicit
- No hidden assumptions about unit types

---

## Risk Considerations

**Risk: User confusion about when to add second yield**
- Context: Some recipes clearly need dual-yield (cakes), others don't (cookies)
- Mitigation approach: Make second yield optional, provide clear labeling in UI
- Future enhancement: Category-driven suggestions after real-world usage data collected

**Risk: Planning service selects wrong yield for context**
- Context: Some planning scenarios need EA, others need SERVING
- Mitigation approach: Provide explicit prefer_servings parameter, sensible defaults
- Future enhancement: Output mode selection in event planning UI

**Risk: Migration assigns wrong yield_type**
- Context: Existing recipes default to SERVING, but some might be EA
- Mitigation approach: Conservative default (SERVING), small dataset allows manual review
- Note: User can add EA yield after migration if needed

**Risk: Export format breaking change**
- Context: finished_unit structure changes from object to possible array
- Mitigation approach: Single-yield recipes export as 1-item array (backward compatible behavior)
- Note: Import must handle both old (object) and new (array) formats during transition

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `recipe.ingredients` relationship → apply to `recipe.finished_units` (both one-to-many)
- Study `ingredient` export in recipes.json → apply to `finished_units` export
- Study `recipe_service.validate_recipe()` → apply validation pattern to finished_units
- Study `material.unit_code` + `material.display_name` → same split for finished_unit

**Key Patterns to Copy:**
- `ingredients` export as array → `finished_units` export as array
- `material` unit split → `finished_unit` unit split
- `recipe_ingredient` validation → `finished_unit` validation

**Focus Areas:**
- Service layer validation must enforce all business rules before database
- Export must handle both single-yield (1 item array) and dual-yield (2 item array)
- Import must validate yield_type values and uniqueness constraints
- UI must make EA vs SERVING distinction clear without overwhelming user
- Planning service yield selection must have sensible defaults

**Migration Approach:**
1. Export all recipes with current schema
2. Modify schema (add fields, constraints)
3. Transform export data (split unit → unit_description + yield_type)
4. Import transformed data
5. Validate all recipes still present and correct

---

## Revision History

**Version 1.1 (2026-01-29)**: Post-implementation clarification
- Added "Recipe Variants and Multiple Yields" section to Architecture Principles
- Clarified that multiple finished_units with same yield_type ARE allowed
- Corrected constraint documentation: uniqueness is on (recipe_id, unit_description, yield_type), not (recipe_id, yield_type)
- Added real-world example showing Large/Medium/Small cake variants
- Original spec was too restrictive; actual implementation correctly supports recipe variants

**Version 1.0 (2026-01-XX)**: Initial specification
- Defined dual-yield capability
- Split unit field into unit_description + yield_type
- Established EA vs SERVING semantics

---

**END OF SPECIFICATION**
