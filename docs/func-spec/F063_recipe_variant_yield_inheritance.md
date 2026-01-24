# F063: Recipe Variant Yield Inheritance

**Version**: 1.0  
**Priority**: HIGH  
**Type**: Service Layer + UI Enhancement  
**Status**: Draft  
**Created**: 2025-01-24

---

## Executive Summary

Current gaps in variant recipe implementation:
- ❌ Variants don't automatically define FinishedUnits matching base recipe yield structure
- ❌ No validation ensuring variant yields match base (items_per_batch, item_unit)
- ❌ Services can't reliably get FinishedUnits for variants (no universal primitive)
- ❌ Batch calculations fail for variants (may use base recipe yields incorrectly)
- ❌ No mechanism to flag variants when base recipe yields change

This spec implements variant yield inheritance: variants define their own FinishedUnits that reference the base recipe's yield structure, with validation ensuring consistency and service primitives enabling transparent access for batch/cost calculations.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Recipe System
├─ ✅ Recipe model supports variants (base_recipe_id, variant_name)
├─ ✅ FinishedUnit model exists with yield specifications
├─ ❌ No automatic FinishedUnit creation for variants
├─ ❌ No yield structure inheritance/validation
└─ ❌ No service primitives for transparent yield access

Recipe Service
├─ ✅ Variant creation copies ingredients from base
├─ ❌ No get_base_yield_structure() primitive
├─ ❌ No get_finished_units() universal primitive
└─ ❌ No variant yield validation

FinishedUnit Service
├─ ✅ CRUD operations for FinishedUnits
├─ ❌ No yield consistency validation for variants
└─ ❌ No flagging mechanism for base yield changes

Planning/Production/Cost Services
└─ ❌ No reliable way to get yields for variants
```

**Target State (COMPLETE):**
```
Recipe System
├─ ✅ Variants have own FinishedUnits matching base yield structure
├─ ✅ Yield validation ensures variant/base consistency
└─ ✅ Services access yields transparently via primitives

Recipe Service
├─ ✅ get_base_yield_structure(recipe_id) primitive
├─ ✅ get_finished_units(recipe_id) universal primitive
└─ ✅ Variant creation includes yield setup

FinishedUnit Service  
├─ ✅ Validates variant yield consistency with base
└─ ✅ Flags variants when base yields change

Planning/Production/Cost Services
└─ ✅ Use get_finished_units() for all batch/cost calculations
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Recipe Model and Variants**
   - Find `/src/models/recipe.py`
   - Study variant relationships (base_recipe_id, variant_name, base_recipe relationship)
   - Note self-referential pattern and constraints

2. **FinishedUnit Model**
   - Find `/src/models/finished_unit.py`
   - Study yield modes (DISCRETE_COUNT, BATCH_PORTION)
   - Note fields: items_per_batch, item_unit, display_name, slug
   - Understand recipe relationship

3. **Recipe Service**
   - Find `/src/services/recipe_service.py`
   - Study variant creation workflow
   - Note ingredient copying pattern
   - Understand session management patterns

4. **FinishedUnit Service**
   - Find `/src/services/finished_unit_service.py`
   - Study CRUD operations
   - Note validation patterns
   - Understand how FinishedUnits link to recipes

5. **Constitution Principles**
   - Find `/.kittify/memory/constitution.md`
   - Study Definition vs Instantiation separation (Principle II)
   - Note Service Boundary discipline (Principle V)
   - Understand Session Management patterns

---

## Requirements Reference

This specification implements:
- **REQ-RCP-031** through **REQ-RCP-044**: Variant Yield Inheritance and Service Primitives
- **REQ-RCP-054** through **REQ-RCP-057**: Yield Primitives for Services (renumbered to REQ-RCP-041-044)
- **VAL-RCP-020**, **VAL-RCP-021**: Variant yield validation rules

From: `docs/requirements/req_recipes.md` (v0.3)

---

## Functional Requirements

### FR-1: Base Recipe Yield Structure Primitive

**What it must do:**
- Provide primitive `get_base_yield_structure(recipe_id)` in recipe_service
- Return yield specifications from base recipe when given a variant recipe_id
- Return yield specifications from the recipe itself when given a base recipe_id
- Return list of FinishedUnit yield data (items_per_batch, item_unit, display_name for each)
- Handle case where recipe has no base (return own yields)
- Handle case where base recipe has no FinishedUnits (return empty list)

**Pattern reference:** Study how recipe_service accesses related entities via relationships, copy for base_recipe access

**Success criteria:**
- [ ] Primitive exists in recipe_service
- [ ] Returns base recipe yields when given variant recipe_id  
- [ ] Returns own yields when given base recipe_id
- [ ] Returns empty list when no FinishedUnits exist
- [ ] Works correctly for non-variant recipes

---

### FR-2: Universal Finished Units Primitive

**What it must do:**
- Provide primitive `get_finished_units(recipe_id)` in recipe_service
- Return all FinishedUnit records for the given recipe (base or variant)
- Return recipe's OWN FinishedUnits, never base recipe FinishedUnits
- Return same structure for base recipes and variant recipes
- No special case handling required by callers
- Return empty list if recipe has no FinishedUnits

**Pattern reference:** Study how ingredient_service.get_ingredients_for_recipe() works, copy for FinishedUnits

**Success criteria:**
- [ ] Primitive exists in recipe_service
- [ ] Returns variant's own FinishedUnits (not base's) for variant recipes
- [ ] Returns base's FinishedUnits for base recipes
- [ ] Structure identical regardless of variant status
- [ ] Planning/Production/Cost services can use without variant checks

---

### FR-3: Variant Yield Consistency Validation

**What it must do:**
- Validate variant FinishedUnits match base recipe yield structure
- Check number of FinishedUnits matches between variant and base
- Check each FinishedUnit's items_per_batch matches corresponding base FinishedUnit
- Check each FinishedUnit's item_unit matches corresponding base FinishedUnit  
- Allow variant FinishedUnit to have different display_name from base
- Allow variant FinishedUnit to have different slug from base
- Raise validation error with clear message on mismatch

**Pattern reference:** Study how recipe_service validates circular references in recipe components, copy validation pattern

**Business rules:**
- Variant must have same number of FinishedUnits as base recipe
- Each variant FinishedUnit must have same items_per_batch as corresponding base FinishedUnit
- Each variant FinishedUnit must have same item_unit as corresponding base FinishedUnit
- display_name MUST differ between variant and base (e.g., "Raspberry Cookie" vs "Plain Cookie")
- slug MAY differ between variant and base

**Success criteria:**
- [ ] Validation triggers when creating variant recipe
- [ ] Validation triggers when modifying variant FinishedUnits
- [ ] Error raised if FinishedUnit count doesn't match
- [ ] Error raised if items_per_batch doesn't match
- [ ] Error raised if item_unit doesn't match
- [ ] Validation passes when display_name differs
- [ ] Clear error messages indicate which field mismatches

---

### FR-4: Variant Creation with Yield Setup

**What it must do:**
- Extend variant creation workflow to handle FinishedUnit setup
- After copying ingredients, prompt user for yield specification
- Auto-detect base recipe FinishedUnits
- Pre-fill variant FinishedUnit form with inherited yield structure (items_per_batch, item_unit)
- Require user to provide distinct display_name for variant FinishedUnits
- Create variant FinishedUnits with validated yield structure
- Mark variant FinishedUnits as linked to variant recipe (not base)

**Pattern reference:** Study how variant creation currently copies ingredients, extend for FinishedUnits

**Success criteria:**
- [ ] Variant creation workflow includes yield setup step
- [ ] System detects base recipe FinishedUnits automatically
- [ ] Form pre-fills with items_per_batch from base
- [ ] Form pre-fills with item_unit from base
- [ ] User must enter distinct display_name
- [ ] Variant FinishedUnits created with correct recipe_id (variant's)
- [ ] Validation ensures yield consistency with base

---

### FR-5: Base Yield Change Flagging

**What it must do:**
- Detect when base recipe FinishedUnit changes (items_per_batch or item_unit modified)
- Flag all variant recipes as requiring yield review
- Store flag on variant recipe record (suggested field: needs_yield_review)
- Provide method to retrieve flagged variants for a base recipe
- Provide method to clear flag after user reviews variant yield
- Display warning in UI when viewing/editing flagged variant

**Pattern reference:** Study how production_ready flag works on Recipe model, copy for needs_yield_review flag

**Success criteria:**
- [ ] Base FinishedUnit changes trigger variant flagging
- [ ] All variants of base recipe get flagged
- [ ] Flag persists until user clears it
- [ ] UI displays warning for flagged variants
- [ ] User can mark variant as reviewed (clear flag)
- [ ] Flag doesn't prevent variant use (warning only)

---

### FR-6: Service Integration for Batch Calculations

**What it must do:**
- Update Planning service to use get_finished_units(recipe_id) for batch calculations
- Update Production service to use get_finished_units(recipe_id) for production planning
- Update Cost service (if exists) to use get_finished_units(recipe_id) for cost calculations
- Ensure no service performs variant-specific checks (primitives handle abstraction)
- Remove any existing code that directly accesses base_recipe.finished_units for variants

**Pattern reference:** Study how services currently access recipe data via recipe_service primitives

**Business rules:**
- Services must ALWAYS use get_finished_units(recipe_id)
- Services must NEVER directly access recipe.base_recipe.finished_units
- Services must NEVER check if recipe.base_recipe_id exists before getting yields
- Batch calculations for "Raspberry Thumbprint Cookies" must use Raspberry variant's FinishedUnits (and ingredient costs)

**Success criteria:**
- [ ] Planning service uses get_finished_units() for batch calculations
- [ ] Production service uses get_finished_units() for production planning
- [ ] No service performs variant-specific logic
- [ ] Batch calculations correct for both base and variant recipes
- [ ] Cost calculations use variant's own ingredient costs

---

### FR-7: UI Enhancements for Variant Yield Workflow

**What it must do:**
- Extend variant creation dialog to include yield setup section
- Display base recipe yield structure (read-only reference)
- Provide form fields for variant FinishedUnit creation
- Pre-populate items_per_batch and item_unit from base
- Require user input for display_name (cannot be same as base)
- Show validation errors clearly if yield structure doesn't match
- Display warning icon/message for flagged variants (needs_yield_review)
- Provide "Mark as Reviewed" action in variant edit view

**UI Requirements:**
- User must understand that yield structure (items_per_batch, item_unit) is inherited from base
- User must provide distinct display_name for variant FinishedUnits
- User must see clear validation feedback when yields don't match
- User must be notified when base recipe yields change (affecting variants)
- User must have clear path to review and acknowledge yield changes

**Note:** Exact UI design (tab layout, dialog structure, etc.) determined during planning phase. Focus on WHAT the UI needs to accomplish for the user.

**Success criteria:**
- [ ] Variant creation includes yield setup step
- [ ] Base yields displayed as reference (read-only)
- [ ] Form fields for variant FinishedUnit creation
- [ ] Validation errors shown clearly
- [ ] Flagged variants show warning
- [ ] User can mark variant as reviewed
- [ ] Workflow is intuitive and prevents errors

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Auto-updating variant yields when base changes (intentional - requires user review)
- ❌ Multi-yield variant types (variant can't have MORE FinishedUnits than base, only matching ones)
- ❌ Variant-of-variant support (variants of variants not supported per requirements)
- ❌ Bulk variant yield updates (single variant workflow only)
- ❌ Historical tracking of yield changes (future enhancement)
- ❌ Yield inheritance for RecipeComponents (sub-recipes) - separate concern

---

## Success Criteria

**Complete when:**

### Service Layer
- [ ] get_base_yield_structure(recipe_id) primitive exists and works correctly
- [ ] get_finished_units(recipe_id) universal primitive exists and works correctly
- [ ] Variant yield validation integrated into variant creation
- [ ] Variant yield validation integrated into FinishedUnit modification
- [ ] Base yield change detection triggers variant flagging
- [ ] Flagged variants retrievable and clearable

### Data Layer
- [ ] needs_yield_review flag added to Recipe model (if needed)
- [ ] Variant FinishedUnits correctly linked to variant recipe_id
- [ ] Database constraints enforce yield consistency

### Service Integration
- [ ] Planning service uses get_finished_units() for batch calculations
- [ ] Production service uses get_finished_units() for production planning
- [ ] Cost service (if exists) uses get_finished_units() for cost calculations
- [ ] No service performs variant-specific checks

### UI Layer
- [ ] Variant creation includes yield setup workflow
- [ ] Base yields displayed as reference
- [ ] Variant FinishedUnit form pre-populated correctly
- [ ] Validation errors displayed clearly
- [ ] Flagged variants show warning
- [ ] User can mark variants as reviewed

### Quality
- [ ] All primitives have unit tests
- [ ] Validation rules have comprehensive test coverage
- [ ] Service integration tested (batch calculations for variants)
- [ ] UI workflow tested end-to-end
- [ ] Error messages are clear and actionable
- [ ] Pattern consistency with existing recipe/variant code

---

## Architecture Principles

### Yield Inheritance Model

**Variants own their FinishedUnits:**
- Variant recipes create their own FinishedUnit records
- Variant FinishedUnits reference variant recipe_id (not base recipe_id)
- Yield structure (items_per_batch, item_unit) matches base via validation
- display_name differs from base (e.g., "Raspberry Cookie" vs "Plain Cookie")

**Rationale:** Maintains separation of definitions while enforcing structural consistency

### Service Abstraction

**get_finished_units() hides variant complexity:**
- Planning/Production/Cost services don't know if recipe is variant or base
- Single primitive works for all recipes
- No special case handling in calling code

**Rationale:** Reduces coupling, prevents variant-specific logic spread across services

### Flagging vs Auto-Update

**Base yield changes flag variants, don't auto-update:**
- System detects base FinishedUnit modifications
- Flags variants as needing review
- User must acknowledge change
- No automatic propagation

**Rationale:** User may have intentionally diverged, auto-update could corrupt data

### Pattern Matching

**Variant Yield validation must match Recipe Component validation exactly:**
- Same validation approach (business rules in service)
- Same error message pattern
- Same session management
- Same testing patterns

---

## Constitutional Compliance

✅ **Principle II: Definition vs Instantiation Separation**
- Variant FinishedUnits are definitions (catalog layer)
- Changes to variant FinishedUnits don't affect production instances
- Snapshots preserve historical yield data

✅ **Principle V: Layered Architecture & Service Boundaries**
- Recipe service owns variant/base relationship logic
- FinishedUnit service owns yield validation logic  
- Planning/Production services consume primitives without crossing boundaries
- No service dictates another service's implementation

✅ **Principle VII: Pragmatic Aspiration**
- Primitives designed to support future multi-user scenarios
- Flagging mechanism extensible for notifications
- Pattern enables future variant-of-variant support if needed

✅ **Principle VIII: Session Management**
- All database operations use shared session
- Validation occurs within transactional boundaries
- Follow established session patterns from recipe_service

---

## Risk Considerations

**Risk: Existing variants break if they have mismatched yields**
- Current database may have variants with FinishedUnits that don't match base
- Validation could prevent editing existing variants
- Mitigation: Include data migration check/fix in planning phase, or grandfather existing variants with warning-only mode initially

**Risk: Performance impact from recursive base recipe lookups**
- get_base_yield_structure() may need to traverse variant → base relationship
- Repeated calls could impact performance
- Mitigation: Planning phase should evaluate if caching needed, leverage existing recipe eager loading patterns

**Risk: UI workflow complexity in variant creation**
- Adding yield setup step increases variant creation complexity
- Users might skip or misunderstand yield requirements
- Mitigation: Clear UI guidance, validation prevents errors, consider wizard-style workflow during planning

**Risk: Services not updated consistently**
- Missing a service that does batch calculations leaves gaps
- Inconsistent primitive usage across services
- Mitigation: Planning phase must audit all services accessing FinishedUnits, comprehensive testing of service integration

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study recipe_service.create_variant() → understand ingredient copy pattern → extend for FinishedUnits
- Study recipe_service circular reference validation → copy for yield consistency validation
- Study FinishedUnit service CRUD → understand validation patterns → add yield consistency checks
- Study Recipe model self-referential relationship → understand base_recipe access → use in get_base_yield_structure()

**Key Patterns to Copy:**
- Ingredient copying in variant creation → FinishedUnit setup in variant creation (parallel workflow)
- RecipeComponent circular reference validation → Variant yield consistency validation (same pattern)
- ProductionRun service accessing Recipe via primitives → Planning service accessing FinishedUnits via primitives

**Focus Areas:**
- Session management: All FinishedUnit creation/validation must use shared session
- Error messaging: Validation errors must clearly indicate which field mismatches (items_per_batch vs item_unit)
- Service boundary discipline: Recipe service owns variant logic, FinishedUnit service owns yield validation
- Pattern consistency: Match existing recipe/variant patterns exactly

**Data Migration Consideration:**
- Planning phase should check if existing variants have FinishedUnits
- If yes, evaluate if they match base recipe yield structure
- Consider migration script to flag non-compliant variants or add validation exemption for pre-existing data

**Testing Strategy:**
- Unit test each primitive in isolation
- Integration test variant creation workflow end-to-end
- Test service integration (Planning/Production using get_finished_units())
- Test edge cases: variant with no FinishedUnits, base with no FinishedUnits, base yield changes
- Test UI workflow: variant creation, yield validation errors, flagged variant review

---

**END OF SPECIFICATION**
