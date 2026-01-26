# F069: Recipe Selection UI

**Version**: 1.0  
**Priority**: HIGH  
**Type**: UI Enhancement (Service Integration)

---

## Executive Summary

Planning workflow requires recipe selection before finished goods selection, but no UI exists:
- ❌ No way to select which recipes user wants to make for an event
- ❌ No distinction between base recipes and variants in selection
- ❌ No prevention of auto-inclusion (user must explicitly choose each recipe)
- ❌ Recipe selections not persisted with event

This spec implements recipe selection UI following the baker's natural mental model: select recipes (what foods to make) before selecting finished goods (how many of each).

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Event Management
└─ ✅ Events can be created (F068)

Recipe Selection
└─ ❌ No UI to select recipes for event

Event-Recipe Associations
└─ ❌ No way to persist selections (data model exists but unused)
```

**Target State (COMPLETE):**
```
Recipe Selection UI
├─ ✅ Flat list of all recipes (bases + variants)
├─ ✅ Visual distinction between bases and variants
├─ ✅ Explicit selection via checkboxes (no auto-inclusion)
├─ ✅ Selection count display
└─ ✅ Selections persist with event

Event-Recipe Associations
└─ ✅ Selections stored in event_recipes table
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Recipe catalog access**
   - Find RecipeService (how to get all recipes)
   - Understand recipe model structure (base vs variant identification)
   - Note recipe naming and display conventions

2. **Event management patterns (F068)**
   - Find how event context maintained in planning UI
   - Study how to access current event
   - Note session management for planning operations

3. **Existing selection UI patterns**
   - Find checkbox list implementations in app
   - Study how selections tracked and persisted
   - Note visual hierarchy patterns

4. **Event-recipe associations (F068)**
   - Find event_recipes table model (defined in F068)
   - Understand how to create/delete associations
   - Note PlanningService methods for recipe management

---

## Requirements Reference

This specification implements:
- **REQ-PLAN-006**: System shall present flat list of all recipes (bases and variants) for selection
- **REQ-PLAN-007**: User shall explicitly select each base recipe AND each variant they want to make
- **REQ-PLAN-008**: System shall NOT auto-include variant recipes when base is selected
- **REQ-PLAN-009**: System shall NOT auto-include base recipes when variant is selected
- **REQ-PLAN-010**: System shall allow user to select any combination of bases and variants
- **REQ-PLAN-011**: Recipe selection shall persist with event
- **REQ-PLAN-012**: System shall support modifying recipe selection after initial definition

From: `docs/requirements/req_planning.md` (v0.4) - Mental Model Section 2.2.1 and 2.2.2

---

## Functional Requirements

### FR-1: Display Flat Recipe List with Visual Distinction

**What it must do:**
- Display all recipes (both base recipes and variants) in single flat list
- Visually distinguish base recipes from variants (indentation, icon, label, etc.)
- Show recipe name clearly
- Enable checkbox selection per recipe
- Display selection count (e.g., "5 of 23 recipes selected")

**UI Requirements:**
- Recipe list must be scrollable for large catalogs
- Base recipes visually distinct from variants
- Each recipe has checkbox for explicit selection
- Selection state visible at a glance

**Pattern reference:** Study existing list views with checkboxes, note visual hierarchy patterns for parent/child items

**Success criteria:**
- [ ] All recipes displayed in flat list
- [ ] Base recipes distinguishable from variants
- [ ] Each recipe has selectable checkbox
- [ ] Selection count displays correctly
- [ ] List scrollable for large catalogs

---

### FR-2: Explicit Selection (No Auto-Inclusion)

**What it must do:**
- Each recipe checkbox operates independently
- Selecting base recipe does NOT auto-select its variants
- Selecting variant recipe does NOT auto-select its base
- User explicitly checks each recipe they want to make
- Selection state persists during session

**Business rules:**
- No automatic inclusions based on relationships
- User has complete control over which recipes selected
- Empty selection allowed (but validation at higher level prevents saving event without recipes)

**Pattern reference:** Standard checkbox behavior - each independent

**Success criteria:**
- [ ] Checking base doesn't auto-check variants
- [ ] Checking variant doesn't auto-check base
- [ ] Each checkbox independent
- [ ] Selection state maintained during session
- [ ] User can select any combination

---

### FR-3: Persist Recipe Selections with Event

**What it must do:**
- When user confirms selections, persist to event_recipes table
- Clear old selections before saving new ones (replace, not append)
- Load existing selections when viewing event
- Pre-check recipes that are already selected for event

**Service operations needed:**
- Add recipes to event (batch create event_recipes records)
- Remove recipes from event (delete event_recipes records)
- Get selected recipes for event (query event_recipes)

**Pattern reference:** Study how PlanningService (F068) works, add recipe management methods

**Success criteria:**
- [ ] Selections saved to database
- [ ] Selections loaded when event opened
- [ ] Selections pre-checked in UI
- [ ] Replace (not append) on save
- [ ] Service methods work correctly

---

### FR-4: Recipe Selection Count and Feedback

**What it must do:**
- Display "X of Y recipes selected" count
- Update count immediately as user checks/unchecks
- Provide visual feedback for selection changes
- Clear indication when no recipes selected

**UI Requirements:**
- Count updates in real-time
- Count visible without scrolling
- Visual confirmation on selection change

**Pattern reference:** Simple counter pattern, study how other UIs display counts

**Success criteria:**
- [ ] Count displays correctly
- [ ] Count updates immediately
- [ ] Count visible at all times
- [ ] Visual feedback on selection changes

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Finished goods filtering (F070 - needs recipe selections first)
- ❌ Quantity specification (F071)
- ❌ Batch calculations (F073)
- ❌ Recipe search/filtering (future enhancement)
- ❌ Recipe details display (separate feature)
- ❌ Recipe reordering or grouping (use natural DB order)

---

## Success Criteria

**Complete when:**

### Recipe List Display
- [ ] All recipes display in flat list
- [ ] Base recipes visually distinct from variants
- [ ] List scrollable for large catalogs
- [ ] Recipe names clear and readable

### Selection Mechanism
- [ ] Each recipe has checkbox
- [ ] Checkboxes work independently (no auto-inclusion)
- [ ] User can select any combination
- [ ] Selection state persists during session

### Persistence
- [ ] Selections save to event_recipes table
- [ ] Selections load when event opened
- [ ] Pre-checking works correctly
- [ ] Replace (not append) behavior works

### User Feedback
- [ ] Selection count displays correctly
- [ ] Count updates in real-time
- [ ] Visual confirmation on changes
- [ ] Empty selection warning (if appropriate)

### Quality
- [ ] Code follows established UI patterns
- [ ] Service operations follow F068 patterns
- [ ] Error handling consistent
- [ ] Performance acceptable for large catalogs

---

## Architecture Principles

### Mental Model Alignment

**Recipe-First Ordering:**
- Recipe selection must happen before finished goods selection
- This mirrors baker's thinking: "What do I want to make?" before "How many?"
- UI flow must enforce this order

### Explicit Selection Principle

**No Auto-Inclusion:**
- Each recipe selection is explicit user choice
- System never assumes user wants related recipes
- User has complete control

**Why this matters:**
- Baker may want base recipe without variants
- Baker may want specific variants only
- Auto-inclusion would violate user intent

### Data Integrity

**Replace Not Append:**
- Saving selections replaces all prior selections
- Prevents duplicate associations
- Ensures UI state matches database state

---

## Constitutional Compliance

✅ **Principle I: User Intent Respected**
- Explicit selection honors user's choices
- No system assumptions about what user wants

✅ **Principle II: Layered Architecture**
- UI calls PlanningService methods
- Service handles database operations
- Clear separation maintained

✅ **Principle III: Service Primitives**
- Recipe selection operations are atomic
- Add/remove/get operations independent
- Composable for higher-level operations

✅ **Principle IV: Session Consistency**
- Selection operations use provided session
- Multiple operations in same session for atomicity

✅ **Principle V: Pattern Matching**
- Recipe selection UI matches existing checkbox list patterns
- Service methods match F068 PlanningService patterns

---

## Risk Considerations

**Risk: Performance with large recipe catalogs**
- **Context:** If user has 100+ recipes, list could be slow to render
- **Mitigation:** Planning phase should consider virtualization if needed, test with realistic data size

**Risk: Visual distinction between base and variant unclear**
- **Context:** User might not understand difference
- **Mitigation:** Use clear visual cues (indentation + label/icon), consider tooltip explaining difference

**Risk: Selection state lost on error**
- **Context:** If save fails, user loses selection work
- **Mitigation:** Maintain selection state in UI until explicitly cleared, show error without losing selections

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study RecipeService → understand how to get all recipes with variant relationships
- Study checkbox list UIs → apply pattern to recipe selection
- Study PlanningService (F068) → add recipe management methods using same patterns
- Study event_recipes model (F068) → understand association structure

**Key Patterns to Copy:**
- Checkbox list UI → Recipe selection list
- Service CRUD methods (F068) → Recipe association methods
- Session management (F068) → Recipe selection persistence

**Focus Areas:**
- **Visual distinction:** Base vs variant must be immediately clear
- **Independence:** No auto-inclusion, each checkbox operates alone
- **Persistence:** Selections saved correctly to event_recipes
- **Load behavior:** Pre-checking existing selections works correctly

**UI Design Freedom:**
- Exact visual approach (indentation, icons, labels) determined in planning
- Checkbox style determined in planning
- Layout (single column, multi-column) determined in planning
- Focus on WHAT must be accomplished, let planning determine HOW

---

**END OF SPECIFICATION**
