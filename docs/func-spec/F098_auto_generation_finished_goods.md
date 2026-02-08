# F098: Auto-Generation of FinishedGoods from FinishedUnits

**Version**: 1.0  
**Priority**: HIGH  
**Type**: Service Layer + Database Logic  

**Created**: 2026-02-08  
**Status**: Draft  

---

## Executive Summary

Current gaps:
- ❌ Bare FinishedGoods manually created via builder (unnecessary steps)
- ❌ No automatic FinishedGood creation when FinishedUnit created
- ❌ 1:1 relationship between FinishedUnit and bare FinishedGood not enforced
- ❌ Changes to recipe/FinishedUnit don't propagate to corresponding FinishedGood
- ❌ User must remember to create FinishedGood for every recipe that yields EA

This spec implements automatic FinishedGood generation from FinishedUnits, establishing FinishedUnits as atomic building blocks and FinishedGoods as the event-selection layer, aligning code with baker's mental model.

---

## Problem Statement

**Current State (MANUAL CREATION):**
```
Recipe with EA Yield
├─ ✅ Creates FinishedUnit automatically
└─ ❌ User must manually create FinishedGood via builder
    ├─ ❌ Unnecessary multi-step workflow
    ├─ ❌ Prone to forgetting
    └─ ❌ Creates data inconsistency

FinishedUnit ↔ FinishedGood Relationship
├─ ❌ Not enforced (can have FU without FG)
├─ ❌ Not maintained (recipe changes don't propagate)
└─ ❌ Manual sync burden on user

Mental Model Misalignment
├─ ❌ "Bare" treated same as "assembled" in UI
├─ ❌ Builder shows all FGs together (atomic + composite)
└─ ❌ No clear distinction between building blocks vs assemblies
```

**Target State (AUTO-GENERATION):**
```
Recipe with EA Yield
├─ ✅ Creates FinishedUnit automatically
└─ ✅ Creates corresponding FinishedGood automatically
    ├─ ✅ Marked as is_assembled=False (atomic)
    ├─ ✅ Single component linking to FinishedUnit
    └─ ✅ Metadata inherited from recipe/FinishedUnit

FinishedUnit ↔ FinishedGood Relationship
├─ ✅ 1:1 enforced (every FU has exactly one FG)
├─ ✅ Maintained automatically (changes propagate)
└─ ✅ Lifecycle coupled (delete FU → delete FG)

Mental Model Alignment
├─ ✅ FinishedUnits = atomic building blocks (auto-managed)
├─ ✅ FinishedGoods (is_assembled=False) = event-selectable units
├─ ✅ FinishedGoods (is_assembled=True) = user-built bundles
└─ ✅ Clear separation in data model and UI

Event Selection Layer
├─ ✅ All event planning works with FinishedGoods only
├─ ✅ Batch calculations use FinishedUnits
├─ ✅ Reporting uses FinishedGoods
└─ ✅ Clean architectural boundary
```

---

## User Testing Validation

**Discovery from Applied Testing (2026-02-08):**

**Finding 1:** Bare FinishedGoods are functionally different from assembled FinishedGoods
- Atomic units (recipes → finished units → bare finished goods) have direct lineage
- These are reusable building blocks, not compositions
- Manual creation via builder is overkill and doesn't match mental model

**Finding 2:** Editing bare FinishedGood via builder doesn't make sense
- Bare FGs are atomic - no assembly steps needed
- Multi-select component selection irrelevant for atomic items
- User wants to edit recipe, not FinishedGood

**Finding 3:** FinishedUnits and bare FinishedGoods have 1:1 relationship
- Every FinishedUnit should automatically become selectable for events
- This requires corresponding FinishedGood record
- Relationship should be maintained automatically, not manually

**Conclusion:** Auto-generation aligns code architecture with baker's mental model where FinishedUnits are atomic building blocks and FinishedGoods represent the event-selection layer.

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **FinishedUnit Model and Lifecycle**
   - `src/models/finished_unit.py` - FinishedUnit model structure
   - Study: When/how FinishedUnits created (recipe save triggers)
   - Note: FinishedUnit fields (name, category, recipe relationship)
   - Understand: FinishedUnit update/delete patterns

2. **FinishedGood Model and Component Structure**
   - `src/models/finished_good.py` - FinishedGood model with is_assembled field
   - `src/models/finished_good_component.py` - Component junction table
   - Study: How components link to FinishedUnits vs Materials
   - Note: is_assembled boolean (False = atomic, True = user-built bundle)

3. **Recipe Save Workflow**
   - Find where FinishedUnits created during recipe save
   - Study trigger points for auto-generation
   - Note transaction boundaries (atomic save requirements)
   - Understand rollback scenarios

4. **Existing Auto-Creation Patterns**
   - Find similar auto-creation logic in codebase
   - Study cascade delete patterns
   - Note propagation update patterns (source changes → derived changes)
   - Understand session management during creation

5. **Service Layer Patterns**
   - `src/services/finished_unit_service.py` - FinishedUnit CRUD
   - `src/services/finished_good_service.py` - FinishedGood CRUD  
   - Study service method signatures and session handling
   - Note validation patterns and error handling

---

## Requirements Reference

This specification implements:
- **Constitution Principle I**: User-Centric Design & Workflow Validation
  - Features MUST solve actual user problems (eliminate manual FG creation)
  - UI MUST be intuitive (distinguish building blocks from assemblies)
  - Workflows MUST match natural baking planning (recipes → units → goods → events)
  - User testing MUST validate major features (✓ completed 2026-02-08)

- **Constitution Principle II**: Data Integrity & Future-Proof Schema
  - Schema changes MUST maintain referential integrity (1:1 relationship enforced)
  - Automated processes MUST be transactional (atomic creation/updates)
  - Lifecycle coupling MUST prevent orphaned records (cascade deletes)

From: `.kittify/memory/constitution.md` (v1.4.0)

---

## Functional Requirements

### FR-1: Automatic FinishedGood Creation from FinishedUnit

**What it must do:**
- When FinishedUnit created, automatically create corresponding FinishedGood
- Mark created FinishedGood with is_assembled=False (atomic unit)
- Create single FinishedGoodComponent linking FG to FU
- Inherit metadata from source FinishedUnit (name, category, notes)
- Operate within same transaction as FinishedUnit creation (atomic operation)
- Prevent creation if FinishedGood already exists for this FinishedUnit

**Metadata inheritance rules:**
- Name: Copy from FinishedUnit.name
- Category: Copy from FinishedUnit product category
- Tags: Auto-generate from recipe name + category (e.g., "chocolate", "cake")
- Notes: Optional - copy from recipe notes or leave blank
- is_assembled: Always False
- nesting_level: Always 0 (atomic)

**Component creation requirements:**
- Create one FinishedGoodComponent record
- component_type: "finished_unit"
- finished_unit_id: Links to source FinishedUnit
- quantity: 1 (always one unit per finished good)

**Transaction requirements:**
- FinishedGood + FinishedGoodComponent creation must be atomic
- If FG creation fails, FinishedUnit creation must rollback
- If component creation fails, both FG and FU must rollback
- No partial states allowed (FU without FG, or FG without component)

**Validation rules:**
- Only create for FinishedUnits (not for weight-based yields)
- Check for existing FinishedGood before creating
- Validate FinishedUnit has valid name and category
- Prevent duplicate FinishedGoods for same FinishedUnit

**Success criteria:**
- [ ] FinishedGood auto-created when FinishedUnit created
- [ ] is_assembled=False set correctly
- [ ] Single component links to FinishedUnit
- [ ] Metadata populated from source
- [ ] Transaction atomic (all or nothing)
- [ ] No duplicates created

---

### FR-2: Propagate Updates from FinishedUnit to FinishedGood

**What it must do:**
- When FinishedUnit updated, propagate relevant changes to corresponding FinishedGood
- Update FinishedGood name if FinishedUnit name changes
- Update FinishedGood category if FinishedUnit category changes
- Regenerate tags if recipe name or category changes
- Maintain synchronization automatically without user intervention

**Fields to propagate:**
- Name changes (FinishedUnit.name → FinishedGood.name)
- Category changes (FinishedUnit.category → FinishedGood.category)
- Tag regeneration (based on updated name/category)

**Fields NOT propagated:**
- User-added notes (preserve user customizations)
- User-added tags (preserve on top of auto-generated)
- Manual overrides (if user explicitly changed name, respect it)

**Propagation timing:**
- Immediate during FinishedUnit update transaction
- Same transaction boundary (update both or neither)

**Edge cases:**
- If FinishedGood manually modified, decide: overwrite or preserve manual changes?
- If multiple FinishedUnits share same name, ensure no conflicts
- If category deleted, handle gracefully (null or default category)

**Success criteria:**
- [ ] Name changes propagate to FinishedGood
- [ ] Category changes propagate to FinishedGood
- [ ] Tags regenerate on relevant changes
- [ ] Propagation within same transaction
- [ ] User customizations preserved appropriately
- [ ] Edge cases handled without errors

---

### FR-3: Cascade Delete FinishedGood When FinishedUnit Deleted

**What it must do:**
- When FinishedUnit deleted, automatically delete corresponding FinishedGood
- Delete FinishedGoodComponents linking to this FinishedUnit
- Validate no assembled FinishedGoods reference this atomic FinishedGood before deletion
- Operate within same transaction as FinishedUnit deletion
- Prevent orphaned FinishedGood records

**Deletion validation:**
- Check if any assembled FinishedGoods contain this atomic FG as component
- If referenced by assemblies, prevent deletion and return error
- Error message: "Cannot delete - this item is used in X assembled products"
- List affected assemblies for user reference

**Cascade order:**
- First: Check for assembly references (abort if found)
- Second: Delete FinishedGoodComponents
- Third: Delete FinishedGood
- Fourth: Delete FinishedUnit
- All within single transaction

**Success criteria:**
- [ ] FinishedGood deleted when FinishedUnit deleted
- [ ] Components cleaned up (no orphans)
- [ ] Validation prevents deletion if used in assemblies
- [ ] Error message clear and actionable
- [ ] Transaction atomic (delete all or none)

---

### FR-4: Identify and Mark Atomic vs Assembled FinishedGoods

**What it must do:**
- Add is_assembled boolean field to FinishedGood model (if not exists)
- Auto-created FinishedGoods marked is_assembled=False
- User-built FinishedGoods (via builder) marked is_assembled=True
- Provide query methods to filter by type
- Support UI distinction between atomic and assembled goods

**Field requirements:**
- is_assembled: Boolean, NOT NULL, default False
- Index on is_assembled for query performance
- Migration required for existing FinishedGoods (backfill logic)

**Query methods needed:**
- list_atomic_finished_goods(category_slug=None) → List[FinishedGood]
- list_assembled_finished_goods(category_slug=None) → List[FinishedGood]
- get_component_finished_units(fg_id) → List[FinishedUnit] (for atomic FGs)

**Backfill logic for existing data:**
- FinishedGoods with single component (type=finished_unit) → is_assembled=False
- FinishedGoods with multiple components → is_assembled=True
- FinishedGoods with material components → is_assembled=True
- Manual review flagged if ambiguous

**Success criteria:**
- [ ] is_assembled field added to model
- [ ] Auto-created FGs marked False
- [ ] Builder-created FGs marked True
- [ ] Query methods return correct subsets
- [ ] Existing data backfilled correctly
- [ ] Index improves query performance

---

### FR-5: Migration Path for Existing Bare FinishedGoods

**What it must do:**
- Identify existing manually-created bare FinishedGoods
- Convert to auto-managed atomic FinishedGoods
- Link to corresponding FinishedUnits (establish 1:1 relationship)
- Mark with is_assembled=False
- Preserve user-added metadata (notes, custom tags)

**Identification logic:**
- Find FinishedGoods with single component where component references FinishedUnit
- Verify component quantity = 1
- Check no material components exist
- These are manually-created bare FGs that should be auto-managed

**Conversion process:**
- Set is_assembled=False
- Verify FinishedGoodComponent links to correct FinishedUnit
- Preserve any user-added notes or tags
- Update metadata to match current FinishedUnit state
- Mark as auto-managed (prevent manual editing going forward)

**Validation requirements:**
- Ensure no duplicates (one FinishedUnit → one atomic FinishedGood)
- Check for name conflicts (multiple FGs same name)
- Verify component relationships valid
- Log conversions for audit trail

**Success criteria:**
- [ ] Existing bare FGs identified correctly
- [ ] Converted to auto-managed atomic FGs
- [ ] 1:1 relationships established
- [ ] User metadata preserved
- [ ] No duplicates or conflicts
- [ ] Conversion logged for audit

---

## Edge Cases

### Edge Case 1: FinishedUnit Name Conflicts
**Scenario:** Two recipes produce FinishedUnits with same name
**Behavior:** Auto-generated FinishedGood names must be unique (append recipe variant or ID)
**Validation:** Check uniqueness before creation, handle conflicts gracefully

### Edge Case 2: Recipe Deleted with Dependent FinishedUnit
**Scenario:** Recipe deleted that produced FinishedUnit
**Behavior:** Cascade delete FinishedUnit → FinishedGood if not used in assemblies
**Validation:** Block deletion if atomic FG used in any assembled FGs

### Edge Case 3: Category Deleted with FinishedUnits
**Scenario:** ProductCategory deleted that FinishedUnits belong to
**Behavior:** Reassign to default category or null, propagate to FinishedGoods
**Validation:** Ensure FinishedGoods remain queryable after category changes

### Edge Case 4: Manual Edit of Auto-Generated FinishedGood
**Scenario:** User manually changes name/tags of auto-created FinishedGood
**Behavior:** Decision needed - allow manual overrides OR prevent editing atomic FGs entirely
**Validation:** If allowing overrides, mark field as "manually overridden" to skip propagation

### Edge Case 5: FinishedUnit Without Recipe
**Scenario:** Orphaned FinishedUnit (recipe deleted but FU remains)
**Behavior:** Auto-create FinishedGood anyway, or require valid recipe?
**Validation:** Decide whether to enforce recipe relationship or handle gracefully

### Edge Case 6: Bulk Recipe Import
**Scenario:** 100 recipes imported at once, each creates FinishedUnit + FinishedGood
**Behavior:** Auto-generation must handle bulk operations efficiently
**Validation:** Performance acceptable, no duplicate FGs created, transactions batched appropriately

### Edge Case 7: FinishedGood Already Exists
**Scenario:** Auto-creation triggered but FinishedGood already exists for this FinishedUnit
**Behavior:** Skip creation, log warning, verify existing FG is marked is_assembled=False
**Validation:** Prevent duplicates, ensure data consistency

---

## Success Criteria

### Measurable Outcomes

**SC-001: Elimination of Manual Creation**
- Zero bare FinishedGoods created via builder after F098 implementation
- All atomic FinishedGoods auto-generated from FinishedUnits
- User never needs to manually create FG for EA-yield recipes

**SC-002: 1:1 Relationship Integrity**
- Every FinishedUnit has exactly one corresponding FinishedGood (is_assembled=False)
- No orphaned FinishedGoods (FG without FU)
- No missing FinishedGoods (FU without FG)
- Relationship maintained automatically through all updates/deletes

**SC-003: Propagation Accuracy**
- FinishedUnit name change → FinishedGood name updated within same transaction
- FinishedUnit category change → FinishedGood category updated
- Tags regenerated when recipe/category changes
- 100% propagation success rate (no missed updates)

**SC-004: Data Consistency**
- is_assembled=False for all auto-generated FinishedGoods
- is_assembled=True for all builder-created FinishedGoods
- Query methods return correct subsets (no false positives/negatives)

**SC-005: User Experience Validation**
- Primary user (Marianne) confirms: "I don't need to create FinishedGoods for recipes anymore"
- Zero confusion about which items are building blocks vs assemblies
- Builder workflow simplified (only shows assembled FGs for editing)

---

## User Scenarios & Testing

### User Story 1 - Recipe Creation Automatically Creates Selectable Item (Priority: P1)

**Scenario:** Baker creates recipe with EA yield and immediately wants to include it in event planning.

**Why this priority:** Core value proposition - eliminates manual step and ensures all recipes immediately available for event selection.

**Independent Test:** Can be fully tested by creating recipe, verifying FinishedUnit created, verifying corresponding FinishedGood exists with is_assembled=False.

**Acceptance Scenarios:**

1. **Given** new recipe created with EA yield type, **When** recipe saved, **Then** FinishedUnit created AND FinishedGood auto-created with is_assembled=False

2. **Given** auto-created FinishedGood exists, **When** querying atomic finished goods, **Then** new item appears in list

3. **Given** recipe variant created from base recipe, **When** variant saved, **Then** separate FinishedUnit + FinishedGood created for variant

4. **Given** recipe with weight yield type, **When** recipe saved, **Then** FinishedUnit NOT created, no FinishedGood auto-generated

---

### User Story 2 - Recipe Changes Propagate to Finished Good (Priority: P1)

**Scenario:** Baker renames recipe and expects the change to appear everywhere automatically.

**Why this priority:** Maintains data consistency without manual synchronization burden.

**Independent Test:** Can be tested by renaming recipe, verifying FinishedUnit name updated, verifying FinishedGood name also updated.

**Acceptance Scenarios:**

1. **Given** existing recipe with auto-created FinishedGood, **When** recipe name changed from "Chocolate Cake" to "Rich Chocolate Cake", **Then** FinishedUnit name updated AND FinishedGood name updated

2. **Given** recipe category changed from "Cakes" to "Special Cakes", **When** update saved, **Then** FinishedGood category updated and tags regenerated

3. **Given** multiple recipes sharing similar names, **When** one renamed, **Then** only corresponding FinishedGood updated (not others)

---

### User Story 3 - Deletion Protection for Referenced Items (Priority: P1)

**Scenario:** Baker tries to delete recipe that's used as component in assembled bundles.

**Why this priority:** Prevents broken references and data corruption.

**Independent Test:** Can be tested by creating assembled FG using atomic FG, attempting to delete source recipe, verifying deletion blocked with clear error.

**Acceptance Scenarios:**

1. **Given** recipe's atomic FinishedGood used in 2 assembled bundles, **When** user attempts to delete recipe, **Then** deletion blocked with message: "Cannot delete - this item is used in 2 assembled products: [list names]"

2. **Given** recipe's atomic FinishedGood NOT used anywhere, **When** user deletes recipe, **Then** FinishedUnit deleted, FinishedGood deleted, FinishedGoodComponent deleted (cascade)

3. **Given** assembled bundle references atomic FG that was deleted, **When** user opens assembled bundle for editing, **Then** error displayed: "This bundle contains deleted items and cannot be edited"

---

### User Story 4 - Migration of Existing Bare FinishedGoods (Priority: P2)

**Scenario:** System converts existing manually-created bare FinishedGoods to auto-managed atomic items.

**Why this priority:** Important for data consistency but one-time operation, not daily workflow.

**Independent Test:** Can be tested with snapshot of production data, running migration, verifying all bare FGs converted correctly.

**Acceptance Scenarios:**

1. **Given** 50 manually-created bare FinishedGoods exist, **When** migration runs, **Then** all marked is_assembled=False and linked to corresponding FinishedUnits

2. **Given** manually-created FG has user-added notes, **When** migration runs, **Then** notes preserved after conversion

3. **Given** manually-created FG has no corresponding FinishedUnit, **When** migration runs, **Then** item flagged for manual review (edge case)

---

### User Story 5 - Bulk Import Handles Auto-Generation (Priority: P3)

**Scenario:** Baker imports 100 recipes from backup, each should auto-create FinishedGoods.

**Why this priority:** Nice to have for data portability but less common than daily operations.

**Independent Test:** Can be tested by importing test dataset with many recipes, verifying all FinishedGoods created without errors.

**Acceptance Scenarios:**

1. **Given** 100 recipes in import file with EA yields, **When** import executes, **Then** 100 FinishedUnits + 100 FinishedGoods created

2. **Given** bulk import in progress, **When** one recipe fails validation, **Then** entire import transaction rolls back (no partial imports)

3. **Given** imported recipes have duplicate names, **When** FinishedGoods auto-created, **Then** names disambiguated (append IDs or variants)

---

## Dependencies

**Required Features (Must be Complete):**
- FinishedUnit model and creation logic (existing)
- FinishedGood model with component relationships (existing, F046)
- Recipe save workflow (existing)
- Service layer for FinishedUnit and FinishedGood (existing)

**Blocks These Features:**
- F099: FinishedGoods Builder Refinement (depends on is_assembled field)
- F100: FinishedGoods Management UI Split (depends on atomic vs assembled distinction)

**Related Features (Reference but not blocking):**
- F097: FinishedGoods Builder UI (created manually, now should only create assembled FGs)
- F061: Finished Goods Inventory (reports should use FinishedGoods, not FinishedUnits)

---

## Testing Strategy

### Unit Tests
- Auto-creation when FinishedUnit created
- is_assembled field set correctly (False for atomic)
- Component creation links to FinishedUnit
- Name/category propagation on updates
- Tag regeneration logic
- Cascade delete with validation

### Integration Tests
- Full recipe save → FinishedUnit → FinishedGood workflow
- Transaction rollback on failures
- Bulk import with many recipes
- Migration conversion of existing data
- Deletion validation (check assembly references)

### User Acceptance Tests
With primary user (Marianne):
1. Create new recipe, verify it appears in event planning without manual FG creation
2. Rename recipe, verify name change appears in event planning
3. Delete recipe, verify appropriate error if used in assemblies
4. Verify assembled bundles still work with auto-created atomic FGs as components
5. Confirm no manual bare FinishedGood creation needed anymore

**Success Criteria:** All 5 scenarios completed without errors or confusion

---

## Constitutional Compliance

**Principle I: User-Centric Design & Workflow Validation** ✓
- Eliminates manual creation burden (user testing identified pain point)
- Aligns code with mental model (FinishedUnits as building blocks)
- Validated through applied user testing (2026-02-08)

**Principle II: Data Integrity & Future-Proof Schema** ✓
- 1:1 relationship enforced automatically
- Cascade deletes prevent orphaned records
- Transaction boundaries ensure atomic operations
- Schema supports future expansion (barbecue, non-baked items)

**Principle V: Layered Architecture Discipline** ✓
- Service layer handles auto-generation logic
- Model layer defines relationships and constraints
- UI layer unaware of auto-generation mechanics
- Clear separation of concerns

---

## Version History

- v1.0 (2026-02-08): Initial specification based on user testing insights
