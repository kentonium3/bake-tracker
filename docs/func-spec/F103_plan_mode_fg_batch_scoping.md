# F103: Plan Mode FG and Batch Scoping Fix

**Version**: 1.0
**Priority**: HIGH
**Type**: Service Layer + UI Fix

**Created**: 2026-03-15
**Status**: Complete

---

## Executive Summary

In Plan mode, the Finished Goods selection section only shows FGs when ALL component recipes of a composition are selected -- a model designed for assembly availability, not recipe-level planning. Additionally, Batch Options shows stale data from recipes that were previously selected but later deselected, and FG filter dropdowns start blank instead of defaulting to "All".

Current gaps:
- ❌ FG selection uses assembly-oriented availability check requiring ALL component recipes
- ❌ Batch Options includes stale EventFinishedGood records from deselected recipes
- ❌ FG filter dropdowns start blank instead of showing "All Categories" / "All Types" / "All Yields"
- ❌ FG category filter derives categories from existing FG inventory instead of canonical recipe_categories table
- ❌ Import service creates FinishedUnits without corresponding bare FinishedGood + Composition links

This spec fixes the planning data flow so FG selection and Batch Options are correctly scoped to the event's current recipe selections.

---

## Problem Statement

**Current State (INCORRECT SCOPING):**
```
Plan Mode -- Event with 8 selected recipes
├─ Recipe Selection
│  └─ ✅ All 8 recipes visible and selectable
│
├─ FG Selection
│  ├─ ❌ Only 2-3 FGs appear (requires ALL component recipes for assembly availability)
│  ├─ ❌ Category filter derives from FG inventory, not recipe_categories table
│  ├─ ❌ Filter dropdowns start blank
│  └─ ❌ Imported recipes missing bare FG + Composition links
│
├─ Batch Options
│  ├─ ❌ Shows batches for deselected recipes (stale EventFinishedGood records)
│  └─ ❌ No recipe-scoping filter on batch decomposition
│
└─ Stale Data
   ├─ ❌ EventFinishedGood records persist after recipe deselection
   └─ ❌ Cleanup uses same assembly-oriented availability check
```

**Target State (CORRECTLY SCOPED):**
```
Plan Mode -- Event with 8 selected recipes
├─ Recipe Selection
│  └─ ✅ All 8 recipes visible and selectable
│
├─ FG Selection
│  ├─ ✅ All FGs for selected recipes appear (simple recipe membership check)
│  ├─ ✅ Category filter from canonical recipe_categories table
│  ├─ ✅ Filter dropdowns default to "All Categories" / "All Types" / "All Yields"
│  └─ ✅ All FUs have bare FG + Composition links
│
├─ Batch Options
│  ├─ ✅ Only shows batches for currently selected recipes
│  └─ ✅ Defense-in-depth recipe filter on batch decomposition
│
└─ Clean Data
   ├─ ✅ EventFinishedGood records eagerly deleted on recipe deselection
   └─ ✅ Cleanup uses direct recipe_id membership check
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **FG Availability Logic**
   - Find: `src/services/event_service.py`
   - Study: `get_available_finished_goods()` -- requires ALL component recipes selected
   - Study: `get_filtered_available_fgs()` -- adds filter layer on top
   - Study: `check_fg_availability()` -- recursive decomposition for assembly availability
   - Note: These functions are designed for assembly/bundle availability, not recipe-level planning

2. **Stale Record Cleanup**
   - Find: `src/services/event_service.py`
   - Study: `remove_invalid_fg_selections()` -- called by `set_event_recipes()` on recipe changes
   - Study: `set_event_recipes()` -- replaces all EventRecipe records, then calls cleanup
   - Note: Cleanup delegates to `check_fg_availability()` -- same assembly-oriented logic

3. **Batch Decomposition**
   - Find: `src/services/planning_service.py`
   - Study: `decompose_event_to_fu_requirements()` -- queries ALL EventFinishedGood records
   - Study: `_decompose_fg_to_fus()` -- recursive FG-to-FU decomposition
   - Note: No filtering by current recipe selections

4. **FG Selection UI**
   - Find: `src/ui/components/fg_selection_frame.py`
   - Study: `_on_filter_change()` -- calls `get_filtered_available_fgs()` to populate list
   - Study: Filter dropdown initialization -- uses empty string defaults
   - Note: Category filter populated from `event_service.get_available_recipe_categories_for_event()`

5. **Data Model: FinishedGood ↔ FinishedUnit Relationship**
   - Find: `src/models/composition.py`
   - Study: `Composition` junction model -- links FinishedGood to FinishedUnit via `assembly_id` + `finished_unit_id`
   - Note: Bare FGs have exactly one Composition with one FinishedUnit

---

## Requirements Reference

This specification addresses:
- **User feedback**: Plan mode FG selection only showing 2-3 items for 8 selected recipes
- **User feedback**: Batch Options showing "Pecan Shortbread Christmas Tree" for Easter 2026 event
- **Data integrity**: Stale EventFinishedGood records polluting downstream calculations

From: User testing feedback (2026-03-15)

---

## Functional Requirements

### FR-1: Recipe-Scoped FG Selection

**What it must do:**
- Show all finished units/goods whose parent recipe is among the event's selected recipes
- Use simple recipe membership check (recipe_id in EventRecipe), not recursive assembly decomposition
- Support filtering by recipe category, item type (bare/bundle), and yield type (EA/SERVING)
- At this planning stage, only simple recipe-to-finished-unit relationships are relevant; assemblies are planned after component production

**Pattern reference:** Study how EventRecipe joins to Recipe; query FinishedUnit through this join, then map back to FinishedGood via Composition

**Success criteria:**
- [ ] All FGs for selected recipes appear in the FG selection list
- [ ] Deselecting a recipe removes its FGs from the list
- [ ] Category filter works correctly with new query
- [ ] Item type and yield type filters work correctly
- [ ] Existing `get_available_finished_goods()` preserved for future assembly use

---

### FR-2: Eager Cleanup of Stale EventFinishedGood Records

**What it must do:**
- When a recipe is deselected from an event, immediately delete EventFinishedGood records for that recipe's finished units
- Use direct recipe_id membership check instead of recursive `check_fg_availability()`
- Return RemovedFGInfo with missing recipe names for user notification
- Re-selecting a recipe shows FGs fresh (without previously saved quantities)

**Pattern reference:** Study `remove_invalid_fg_selections()` -- replace `check_fg_availability()` call with direct FU recipe_id check against EventRecipe

**Success criteria:**
- [ ] Deselecting a recipe immediately removes its EventFinishedGood records
- [ ] RemovedFGInfo correctly populated with removed FG names
- [ ] Re-selected recipes show FGs without previously saved quantities
- [ ] Existing `check_fg_availability()` preserved for future assembly use

---

### FR-3: Recipe-Scoped Batch Decomposition

**What it must do:**
- Batch decomposition must only include FU requirements for recipes currently selected for the event
- Defense-in-depth: filter FURequirements after decomposition, even if eager cleanup should have removed stale records
- Only filter when EventRecipes exist (backward compat for events without explicit recipe selection)

**Pattern reference:** Study `decompose_event_to_fu_requirements()` -- add post-decomposition filter using `get_event_recipe_ids()`

**Success criteria:**
- [ ] Batch Options shows zero batches for deselected recipes
- [ ] Valid batches for selected recipes still appear correctly
- [ ] Events without EventRecipe records still decompose correctly (backward compat)

---

### FR-4: FG Filter Dropdown Defaults and Category Source

**What it must do:**
- Filter dropdowns must default to "All Categories" / "All Types" / "All Yields" instead of blank
- Recipe Category filter must populate from canonical `recipe_categories` table, not from FG inventory

**Pattern reference:** Study how `recipe_selection_frame.py` uses `recipe_category_service.list_categories()` for its category dropdown

**Success criteria:**
- [ ] Filter dropdowns show "All" defaults on load and reset
- [ ] Category dropdown shows all defined recipe categories
- [ ] Categories not represented in current FG inventory still appear in dropdown

---

### FR-5: Import Service Creates Complete FG Data

**What it must do:**
- When importing recipes, the import service must create bare FinishedGood + Composition links for every FinishedUnit created
- Applies to both default FU creation (no finished_units in JSON) and explicit FU creation (finished_units array provided)
- Slug deduplication for both FU and FG slugs

**Pattern reference:** Study how existing recipes in the database have FinishedGood → Composition → FinishedUnit chains; replicate this for imported recipes

**Success criteria:**
- [ ] Every imported FinishedUnit has a corresponding bare FinishedGood + Composition link
- [ ] Imported recipes appear in FG selection without manual data fixes
- [ ] Slug collisions handled gracefully

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Assembly/composition planning -- assemblies are planned after component production (separate workflow)
- ❌ Plan state guards (LOCKED/IN_PRODUCTION) -- F104 covers this
- ❌ Shopping list scoping -- follows from batch decomposition fix automatically
- ❌ New filter UI patterns or progressive disclosure -- F100 already covers this
- ❌ Batch calculation display changes -- already working correctly

---

## Success Criteria

**Complete when:**

### FG Selection
- [ ] All FGs for selected recipes visible in FG selection list
- [ ] Deselecting a recipe removes its FGs from the list
- [ ] Filter dropdowns default to "All" values
- [ ] Category dropdown sourced from canonical recipe_categories table

### Batch Options
- [ ] Only batches for currently selected recipes appear
- [ ] No stale batches from deselected recipes

### Data Integrity
- [ ] Stale EventFinishedGood records cleaned up on recipe deselection
- [ ] Import service creates complete FG data chains

### Quality
- [ ] Service layer changes covered by tests
- [ ] Existing planning tests pass without regression
- [ ] No business logic in UI layer

---

## Architecture Principles

### Additive Over Destructive

**Preserve existing functions:**
- `get_available_finished_goods()` and `check_fg_availability()` remain for future assembly planning
- New `get_fgs_for_selected_recipes()` is additive, not a replacement
- Cleanup simplification is internal to `remove_invalid_fg_selections()` only

### Defense in Depth

**Multiple layers of correctness:**
- Eager cleanup: delete stale records on recipe deselection
- Query filter: batch decomposition excludes deselected recipes even if stale records survive
- Conditional filter: only apply when EventRecipes exist (backward compat)

### Pattern Matching

**New FG query must match existing UI contract:**
- Return `List[FinishedGood]` objects (not FinishedUnit)
- Map FinishedUnits back to FinishedGoods via Composition
- Accept same filter parameters as existing function

---

## Constitutional Compliance

✅ **Principle I: User-Centric Design**
- Fixes broken planning workflow reported by primary user during testing

✅ **Principle IV: Test-Driven Development**
- All service layer changes covered by unit/integration tests

✅ **Principle V: Layered Architecture**
- Service layer changes only; UI layer swaps one service call

✅ **Principle VI-C: Session Parameter Pattern**
- All new functions accept `session: Session` parameter

---

## Risk Considerations

**Risk: Breaking existing assembly/bundle logic**
- Assembly availability functions (`get_available_finished_goods`, `check_fg_availability`) are preserved
- New function is additive; no existing callers modified (except the one UI call site)

**Risk: FinishedUnits without Composition links**
- Discovered during testing: imported recipes lacked bare FG + Composition entries
- Fixed in both import service (future imports) and production data (existing records)

**Risk: Backward compatibility for events without recipe selection**
- Batch decomposition filter is conditional: only filters when EventRecipes exist
- Events created before recipe selection feature still work correctly

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `get_available_finished_goods()` → understand why it's wrong for recipe planning
- Study `Composition` model → understand FG ↔ FU mapping via `assembly_id` + `finished_unit_id`
- Study `recipe_selection_frame.py` → copy category dropdown pattern for FG frame

**Key Patterns to Copy:**
- `recipe_category_service.list_categories()` → canonical category source (already used by recipe frame)
- `EventRecipe` join → recipe membership check (simple, not recursive)

**Focus Areas:**
- The FG ↔ FU mapping through Composition is the critical data path
- Eager cleanup must use the same simple recipe_id check, not recursive decomposition
- Import service must create complete data chains (FU + FG + Composition)

---

**END OF SPECIFICATION**
