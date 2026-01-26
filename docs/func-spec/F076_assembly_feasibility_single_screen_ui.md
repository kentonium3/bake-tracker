# F076: Assembly Feasibility & Single-Screen UI

**Version**: 1.0  
**Priority**: HIGH  
**Type**: Service Layer + UI Integration (Phase 2 Capstone)

---

## Executive Summary

All planning calculations exist but not integrated into cohesive UX:
- ❌ No assembly feasibility validation
- ❌ Planning UI scattered across multiple views
- ❌ No real-time updates across sections
- ❌ No single-screen workflow

This spec completes Phase 2 by integrating all features into cohesive single-screen planning experience with final validation.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Planning Features (F068-F075)
├─ ✅ Events, recipes, FGs, quantities
├─ ✅ Batch calculations
├─ ✅ Ingredient aggregation
└─ ✅ Shopping list

Assembly Validation
└─ ❌ No check if production meets assembly needs

UI Integration
└─ ❌ Features not integrated into single workflow
```

**Target State (COMPLETE):**
```
Assembly Feasibility Service
├─ ✅ Calculate production from batch decisions
├─ ✅ Compare vs FG requirements
└─ ✅ Validate bundle component availability

Single-Screen Planning UI
├─ ✅ All sections visible on one screen
├─ ✅ Event → Recipes → FGs → Batches → Shopping → Assembly
├─ ✅ Real-time updates across sections
└─ ✅ Visual status indicators
```

---

## CRITICAL: Study These Files FIRST

1. **All previous planning features (F068-F075)**
   - Understand complete workflow
   - Note data flow between features
   - Identify integration points

2. **Assembly patterns**
   - Find bundle decomposition (F070, F072)
   - Study component validation patterns
   - Note success/failure indicators

3. **Single-screen UI patterns**
   - Find existing integrated workflows
   - Study layout strategies
   - Note update propagation patterns

---

## Requirements Reference

Implements:
- **REQ-PLAN-053** through **REQ-PLAN-061**: Assembly feasibility and single-screen UI
- Sections 7.7 and 10 from req_planning.md (v0.4)

---

## Functional Requirements

### FR-1: Assembly Feasibility Service

**What it must do:**
- Calculate what will be produced from batch decisions
- Compare production vs FG requirements
- For bundles, validate ALL component availability
- Return feasibility data structure

**Service interface:**
```
calculate_assembly_feasibility(event_id) → {
  overall_feasible: bool,
  finished_goods: [
    {
      fg: FinishedGood,
      quantity_needed: int,
      can_assemble: bool,
      components: [ComponentStatus]
    }
  ]
}
```

**Success criteria:**
- [ ] Production calculation correct
- [ ] Comparison logic works
- [ ] Bundle validation recursive
- [ ] Output structure complete

---

### FR-2: Single-Screen Layout Integration

**What it must do:**
- Integrate all planning sections on one screen
- Logical flow: Event → Recipes → FGs → Quantities → Batches → Shopping → Assembly
- All sections visible without navigation
- Compact but readable layout

**UI sections:**
1. Event metadata (header)
2. Recipe selection
3. FG selection with quantities
4. Batch decisions
5. Shopping list summary
6. Assembly feasibility status

**Success criteria:**
- [ ] All sections present
- [ ] Flow logical and clear
- [ ] No tab navigation required
- [ ] Fits standard desktop resolution

---

### FR-3: Real-Time Update Propagation

**What it must do:**
- Recipe selection change → FG list updates
- FG quantity change → Batch options recalculate
- Batch decision change → Shopping list updates, Assembly status updates
- Updates immediate and automatic

**Success criteria:**
- [ ] Updates propagate correctly
- [ ] No manual refresh needed
- [ ] Performance acceptable
- [ ] State consistency maintained

---

### FR-4: Visual Status Indicators

**What it must do:**
- Assembly feasibility: ✓ (all met) or ⚠️ (issues) or ✗ (failed)
- Batch decisions: Complete/Incomplete indicator
- Shopping list: Purchase required indicator
- Overall plan status

**Success criteria:**
- [ ] Indicators clear and visible
- [ ] Status accurate
- [ ] Updates in real-time

---

## Out of Scope

- ❌ Plan locking (F077 - Phase 3)
- ❌ Amendments (F078 - Phase 3)
- ❌ Production awareness (F079 - Phase 3)
- ❌ Multiple events (future)

---

## Success Criteria

### Assembly Feasibility Service
- [ ] Service calculates correctly
- [ ] Bundle validation works
- [ ] Component details accurate
- [ ] Output structure complete

### Single-Screen UI
- [ ] All sections integrated
- [ ] Layout clear and usable
- [ ] Fits on screen
- [ ] Navigation not required

### Real-Time Updates
- [ ] Changes propagate correctly
- [ ] Updates immediate
- [ ] No lag or jank
- [ ] State consistent

### Visual Feedback
- [ ] Status indicators clear
- [ ] Assembly status prominent
- [ ] Completeness visible
- [ ] User understands state

### Quality
- [ ] Integration stable
- [ ] Performance acceptable
- [ ] Error handling robust
- [ ] Code follows patterns

---

## Architecture Principles

**Service Layer First:**
- Assembly calculations separate from UI
- Testable independently
- UI consumes service data

**Update Strategy:**
- Reactive updates (not polling)
- Cascading recalculations
- Efficient re-rendering

**Single-Screen Philosophy:**
- All context visible at once
- No hidden state
- Complete mental model

---

## Constitutional Compliance

✅ **Layered Architecture**
✅ **User Experience Priority**
✅ **Service Primitives**
✅ **Pattern Matching**
✅ **Integration Excellence**

---

## Notes for Implementation

**Pattern Discovery:**
Study integrated workflows, apply to planning. Service layer separate from UI integration.

**Mitigation Strategy:**
- Service layer fully tested before UI work
- UI integration incremental (section by section)
- Acceptance criteria separate service from UI

This is expected as integration feature - maintain clear boundaries.

---

**END OF SPECIFICATION**
