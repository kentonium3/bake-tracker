# F103: Production-Aware Planning Calculations

**Version**: 1.0
**Priority**: HIGH
**Type**: Full Stack (Service Layer + UI Integration)

**Created**: 2026-02-28
**Status**: Draft

---

## Executive Summary

The planning module's service layer includes production progress tracking and remaining-needs calculations (F079), but these are not surfaced in the Planning UI during the IN_PRODUCTION state. The user has no way to see how production progress affects their plan, whether assembly is feasible given current output, or what ingredients are still needed for remaining batches.

Current gaps:
- ❌ Planning UI does not reflect production progress against plan targets
- ❌ Ingredient gap analysis shows total needs, not remaining needs adjusted for completed production
- ❌ Assembly feasibility does not project output from remaining planned batches
- ❌ No guards preventing batch decision modifications for recipes with completed production runs
- ❌ Planning screen does not refresh when production records are added

This spec wires the existing production-aware service layer into the Planning UI, adds projected assembly feasibility, and enforces amendment guards — completing Phase 3 dynamic planning.

---

## Problem Statement

**Current State (STATIC PLANNING VIEW DURING PRODUCTION):**
```
Planning UI (IN_PRODUCTION state)
├─ ✅ Plan state shown (IN_PRODUCTION label)
├─ ✅ Lock/transition buttons work
├─ ❌ Shopping summary shows TOTAL ingredient needs (not remaining)
├─ ❌ Assembly feasibility uses TOTAL requirements (ignores completed batches)
├─ ❌ No production progress display in planning context
├─ ❌ Batch decisions editable even after production started for that recipe
└─ ❌ No refresh when production records added elsewhere in app

Service Layer (ALREADY EXISTS)
├─ ✅ progress.get_production_progress() → per-recipe progress
├─ ✅ progress.get_remaining_production_needs() → remaining batches
├─ ✅ progress.get_assembly_progress() → per-FG assembly progress
├─ ✅ progress.get_overall_progress() → aggregated status
├─ ✅ shopping_list.get_shopping_list(production_aware=True) → adjusted gaps
├─ ✅ feasibility.check_production_feasibility() → ingredient checks
├─ ✅ feasibility.check_assembly_feasibility() → component checks
└─ ❌ No projected assembly feasibility (accounting for pending production)
```

**Target State (DYNAMIC PRODUCTION-AWARE PLANNING):**
```
Planning UI (IN_PRODUCTION state)
├─ ✅ Production progress per recipe (completed/target batches, %)
├─ ✅ Assembly progress per FG (assembled/target, %)
├─ ✅ Overall progress summary (production %, assembly %, overall %)
├─ ✅ Shopping summary shows REMAINING ingredient needs only
├─ ✅ Assembly feasibility projects output from remaining batches
├─ ✅ Batch decisions locked for recipes with completed production
├─ ✅ Planning view refreshes when returning from production/assembly screens
└─ ✅ Visual indicators distinguish complete vs in-progress vs not-started

Service Layer
├─ ✅ All existing functions (unchanged)
├─ ✅ Projected assembly feasibility (current stock + expected remaining output)
└─ ✅ Amendment guard (reject batch changes for recipes with production runs)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Planning Service Modules**
   - Find: `src/services/planning/progress.py`
   - Study: `get_production_progress()`, `get_remaining_production_needs()`, `get_assembly_progress()`, `get_overall_progress()`
   - Note: These return dataclasses (`ProductionProgress`, `AssemblyProgress`) with computed fields
   - Understand: How remaining_batches and overage_batches are calculated

2. **Shopping List with Production Awareness (F079)**
   - Find: `src/services/planning/shopping_list.py`
   - Study: `get_shopping_list(production_aware=True)` parameter
   - Note: Already calls `get_remaining_production_needs()` internally
   - Understand: How remaining needs reduce the ingredient gap

3. **Assembly Feasibility Service**
   - Find: `src/services/planning/feasibility.py`
   - Study: `check_assembly_feasibility()` — returns `FeasibilityResult` with `Blocker` details
   - Study: `FeasibilityStatus` enum (CAN_ASSEMBLE, PARTIAL, CANNOT_ASSEMBLE, AWAITING_PRODUCTION)
   - Note: Currently checks actual inventory only, does not project future production output

4. **Planning Tab UI**
   - Find: `src/ui/planning_tab.py`
   - Study: How shopping summary, assembly status, and production progress frames are integrated
   - Note: Current refresh patterns and data flow
   - Understand: Plan state controls and button visibility by state

5. **Production Progress UI Component**
   - Find: `src/ui/components/production_progress_frame.py`
   - Study: Current summary-level display
   - Note: What data it receives and how it renders

6. **Batch Decision Service**
   - Find: `src/services/batch_decision_service.py`
   - Study: Save/update/delete operations
   - Note: No guards currently prevent modification after production starts

7. **Production and Assembly Tracking**
   - Find: `src/services/batch_production_service.py` and `src/services/assembly_service.py`
   - Study: `record_batch_production()` and `record_assembly()` — how production records link to events
   - Note: `ProductionRun.event_id` and `AssemblyRun.event_id` link to planning targets

---

## Requirements Reference

This specification implements:
- **F-PLAN-011**: Production-Aware Calculations (from `docs/func-spec/planning_plan_sequence.md`)
- **REQ-PLAN (Section 3.2)**: Phase 3 dynamic planning scope
- **REQ-PLAN (Section 14.2)**: Real-time plan adjustments during production

From: `docs/requirements/req_planning.md` (v0.1), `docs/func-spec/planning_plan_sequence.md` (v1.0)

---

## Functional Requirements

### FR-1: Production Progress Display in Planning UI

**What it must do:**
- Display per-recipe production progress when plan is in IN_PRODUCTION or COMPLETED state
- Show for each recipe: target batches, completed batches, remaining batches, progress percentage
- Show overall production progress (aggregate across all recipes)
- Visually distinguish recipes that are complete, in-progress, and not-started
- Display overage when production exceeds target (e.g., "5/4 batches — 1 extra")

**UI Requirements:**
- Progress information must be visible in the planning workspace without navigating away
- Each recipe row shows target vs actual with progress indicator
- Overall progress summary visible at a glance (e.g., "Production: 60% complete")
- Color or icon coding: complete (green/check), in-progress (yellow/spinner), not-started (gray/dash)

**Pattern reference:** Study `progress.get_production_progress()` return values — the data is already computed, this is about surfacing it in the planning UI context

**Success criteria:**
- [ ] Per-recipe progress displayed when plan is IN_PRODUCTION
- [ ] Target, completed, and remaining batch counts shown per recipe
- [ ] Overall production progress percentage displayed
- [ ] Visual indicators distinguish complete/in-progress/not-started
- [ ] Overage batches displayed when production exceeds target
- [ ] Progress hidden or N/A when plan is in DRAFT or LOCKED state

---

### FR-2: Assembly Progress Display in Planning UI

**What it must do:**
- Display per-finished-good assembly progress when plan is in IN_PRODUCTION or COMPLETED state
- Show for each FG: target quantity, assembled quantity, remaining quantity, progress percentage
- Show overall assembly progress (aggregate)
- Indicate which FGs are ready to assemble (components available) vs blocked

**UI Requirements:**
- Assembly progress section in planning workspace
- Each FG row shows target vs assembled with progress indicator
- Overall assembly progress visible at a glance
- FGs that cannot yet be assembled show reason (awaiting production of component X)

**Pattern reference:** Study `progress.get_assembly_progress()` and `feasibility.check_assembly_feasibility()` for data sources

**Success criteria:**
- [ ] Per-FG assembly progress displayed when plan is IN_PRODUCTION
- [ ] Target, assembled, and remaining quantities shown per FG
- [ ] Overall assembly progress percentage displayed
- [ ] FGs blocked from assembly show blocker reason
- [ ] Progress hidden or N/A when plan is in DRAFT or LOCKED state

---

### FR-3: Production-Aware Ingredient Gap Analysis

**What it must do:**
- When plan is IN_PRODUCTION, shopping summary must show ingredient needs for REMAINING batches only
- Ingredients fully consumed by completed production must not appear in shopping list
- Partially completed recipes show reduced ingredient needs (remaining batches × per-batch quantities)
- User must clearly understand they are seeing remaining needs, not total plan needs
- Provide toggle or label to clarify: "Showing needs for X remaining batches" vs "Showing total plan needs"

**Business rules:**
- DRAFT and LOCKED states show total plan ingredient needs (current behavior, unchanged)
- IN_PRODUCTION state defaults to showing remaining needs
- Ingredient quantities = (remaining_batches × ingredients_per_batch) aggregated across all recipes
- If all production is complete, ingredient gap shows zero (or "Production complete" message)

**Pattern reference:** Study `shopping_list.get_shopping_list(production_aware=True)` — the calculation already exists, this wires it into the planning UI

**Success criteria:**
- [ ] IN_PRODUCTION state shows remaining ingredient needs by default
- [ ] Shopping summary correctly reduces needs for completed production
- [ ] User can distinguish remaining needs from total plan needs
- [ ] DRAFT/LOCKED states show total needs (unchanged behavior)
- [ ] Fully completed production shows zero remaining ingredient needs

---

### FR-4: Projected Assembly Feasibility

**What it must do:**
- Calculate assembly feasibility considering both current inventory AND expected output from remaining planned production
- Answer the question: "If we complete all remaining planned production, will we have enough components to assemble all target FGs?"
- Distinguish between three states:
  1. **Ready now**: Components already available in inventory for assembly
  2. **Ready after production**: Components will be available once remaining production completes
  3. **Blocked**: Even after all planned production, components will be insufficient
- Show per-FG projected feasibility status alongside current feasibility

**Business rules:**
- Current feasibility = what can be assembled with inventory right now
- Projected feasibility = current inventory + (remaining batches × yield per batch) for each recipe
- A FG is "ready after production" only if ALL required components will be met after remaining production
- A FG is "blocked" if any component will still be insufficient even after completing all planned production
- Overage from one recipe does not substitute for shortfall in another (recipes produce specific finished units)

**Pattern reference:** Study `feasibility.check_assembly_feasibility()` for current checks, extend with projected output from `progress.get_remaining_production_needs()`

**Success criteria:**
- [ ] Projected feasibility calculated considering expected production output
- [ ] Three-state display: ready now / ready after production / blocked
- [ ] Each FG shows both current and projected feasibility
- [ ] "Ready after production" indicates which production must complete
- [ ] "Blocked" shows which components remain insufficient and by how much

---

### FR-5: Batch Decision Amendment Guards

**What it must do:**
- Prevent modification of batch decisions for recipes that have completed production runs
- When user attempts to change batch count for a recipe with production: show informational message explaining why
- Allow batch decision changes for recipes with NO production runs yet
- Allow INCREASING batch count for recipes with partial production (adding more batches is safe)
- Prevent DECREASING batch count below already-produced batches

**Business rules:**
- Recipe with 0 production runs: batch decision fully editable
- Recipe with production runs (completed < target): can increase target, cannot decrease below completed
- Recipe with production runs (completed >= target): batch decision locked (display-only)
- Guard applies only in IN_PRODUCTION state (DRAFT and LOCKED allow free editing)
- Message: "X batches already produced for this recipe. Target cannot be reduced below X."

**Pattern reference:** Study `batch_decision_service.py` for current save/update operations; study `progress.get_production_progress()` for completed batch counts

**Success criteria:**
- [ ] Batch decisions editable when no production runs exist for recipe
- [ ] Batch count cannot be decreased below completed production count
- [ ] Batch count can be increased even after partial production
- [ ] Fully produced recipes show batch decision as read-only
- [ ] Clear message explains why changes are restricted
- [ ] DRAFT/LOCKED states allow free batch editing (unchanged)

---

### FR-6: Planning View Refresh on State Change

**What it must do:**
- Refresh all production-aware calculations when user navigates to planning tab
- Refresh when plan state transitions (LOCKED → IN_PRODUCTION, etc.)
- Ensure data is current when user switches between production/assembly screens and planning
- Avoid unnecessary recalculation when data hasn't changed

**UI Requirements:**
- Refresh must be fast enough to feel instantaneous (target: <500ms for typical event)
- Show brief loading indicator if refresh takes longer
- No stale data displayed — user always sees current production state

**Pattern reference:** Study existing tab refresh patterns in the planning UI; study how production_progress_frame currently refreshes

**Success criteria:**
- [ ] Planning data refreshes when tab becomes visible
- [ ] Data refreshes on plan state transitions
- [ ] Refresh completes in <500ms for typical event (10-20 recipes)
- [ ] Loading indicator shown if refresh exceeds threshold
- [ ] No stale production data displayed after recording production elsewhere

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Cross-event inventory awareness (sharing ingredients between concurrent events — future enhancement)
- ❌ Automatic substitution suggestions (suggesting alternative ingredients — future enhancement)
- ❌ Cost optimization (calculating cheapest production plan — future enhancement)
- ❌ Schedule optimization (suggesting production order/timing — future enhancement)
- ❌ Real-time push notifications (production completed elsewhere triggers instant UI update — future; tab refresh is sufficient)
- ❌ Amendment history UI (displaying amendment log — separate feature, F-PLAN-010 completion)
- ❌ Plan snapshot comparison (original vs current plan side-by-side — separate feature, F-PLAN-010 completion)

---

## Success Criteria

**Complete when:**

### Production Progress
- [ ] Per-recipe production progress visible in planning UI during IN_PRODUCTION
- [ ] Overall production progress percentage displayed
- [ ] Visual indicators for complete/in-progress/not-started recipes
- [ ] Overage batches shown when exceeding target

### Assembly Progress
- [ ] Per-FG assembly progress visible in planning UI during IN_PRODUCTION
- [ ] Overall assembly progress percentage displayed
- [ ] Blocked FGs show reason (missing components)

### Production-Aware Calculations
- [ ] Shopping summary shows remaining needs (not total) during IN_PRODUCTION
- [ ] Projected assembly feasibility accounts for expected production output
- [ ] Three feasibility states displayed: ready now / ready after production / blocked
- [ ] Batch amendment guards prevent invalid modifications

### UI Integration
- [ ] Planning view refreshes on tab navigation and state transitions
- [ ] Refresh performance acceptable (<500ms typical)
- [ ] State-appropriate display (DRAFT/LOCKED vs IN_PRODUCTION vs COMPLETED)
- [ ] No stale data after production/assembly activity

### Quality
- [ ] All new service functions accept `session: Optional[Session] = None`
- [ ] Exception-based error handling (no None returns for not-found)
- [ ] Tests cover happy path, edge cases (no production, partial, complete, overage)
- [ ] UI follows layered architecture (no business logic in UI layer)

---

## Architecture Principles

### Leverage Existing Service Layer

**Build on what exists — don't duplicate:**
- The `planning/progress.py`, `planning/shopping_list.py`, and `planning/feasibility.py` modules already contain the core calculation logic
- This feature primarily WIRES existing services into the planning UI
- New service code is limited to projected assembly feasibility and amendment guards
- Avoid creating parallel calculation paths

### State-Conditional Display

**Planning UI behavior varies by plan state:**
- **DRAFT**: Full editing, no production data (current behavior, unchanged)
- **LOCKED**: Read-only plan review, no production data (current behavior, unchanged)
- **IN_PRODUCTION**: Production-aware display with amendment guards (this feature)
- **COMPLETED**: Final summary with all production data (read-only)

### Refresh-on-Navigate Pattern

**Recalculate when user enters planning context:**
- Planning data recalculated each time the planning tab becomes active
- Avoids complexity of real-time event listeners or push notifications
- Acceptable latency for desktop app (user explicitly navigates to planning)
- Simpler than maintaining WebSocket-style update channels

### Session Parameter Compliance

**All new service functions must follow session pattern:**
- Accept `session: Optional[Session] = None` parameter
- Support both standalone and transactional composition
- Follow Pattern A/B/C from `docs/design/transaction_patterns_guide.md`

---

## Constitutional Compliance

✅ **Principle I: User-Centric Design & Workflow Validation**
- Surfaces production progress directly in planning context (user doesn't need to cross-reference screens)
- Shows remaining needs (what's actionable) not total needs (already partially fulfilled)
- Amendment guards prevent confusing situations where plan says one thing, production says another

✅ **Principle II: Data Integrity & FIFO Accuracy**
- Production-aware calculations use actual production records (not estimates)
- Ingredient gap based on real remaining needs after FIFO consumption
- Amendment guards preserve consistency between plan and production history

✅ **Principle IV: Test-Driven Development**
- Service layer calculations independently testable
- Edge cases (no production, partial, complete, overage) must be covered
- Integration tests validate UI receives correct data

✅ **Principle V: Layered Architecture Discipline**
- Service layer computes all production-aware data
- UI layer only displays what services provide
- No production queries in UI code

✅ **Principle VI.C: Dependency & State Management**
- All new functions follow session parameter pattern
- Transaction boundaries documented in docstrings
- No nested session_scope() anti-patterns

✅ **Principle VI.D: API Consistency & Contracts**
- New functions return typed dataclasses (not dicts)
- Exceptions raised for not-found, not None returns
- Consistent with existing planning service patterns

---

## Risk Considerations

**Risk: Performance of production-aware calculations**
- Context: Multiple queries (progress, shopping, feasibility) on each tab refresh could be slow
- Mitigation: Planning phase should profile calculation time; consider caching within a single refresh cycle (compute once, display in multiple sections). Target <500ms for typical event.

**Risk: Stale data between tabs**
- Context: User records production in production tab, switches to planning tab — must see updated progress
- Mitigation: Refresh-on-navigate pattern ensures data is current. Planning phase should verify the tab activation callback mechanism in CustomTkinter.

**Risk: Projected feasibility accuracy**
- Context: Projected output assumes remaining batches will yield expected quantities; actual yield may vary (losses, partial batches)
- Mitigation: Show projected feasibility clearly labeled as "projected" (not guaranteed). Use target yield for projections. Actual feasibility updates as production completes.

**Risk: Amendment guard edge cases**
- Context: User may have legitimate need to reduce batch target below completed count (e.g., batch was defective)
- Mitigation: Planning phase should determine whether to support override with confirmation dialog or require plan amendment workflow (F-PLAN-010). For this feature, block with informational message; override capability can be added later.

**Risk: UI complexity during IN_PRODUCTION**
- Context: Planning screen already dense; adding progress, projected feasibility, and amendment status increases cognitive load
- Mitigation: Planning phase should consider progressive disclosure (collapse/expand sections) or tabs within the planning workspace. Production-aware sections only visible in IN_PRODUCTION state.

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `progress.py` dataclasses → understand what's already computed
- Study `shopping_list.py` `production_aware` parameter → understand how remaining needs work
- Study `feasibility.py` `FeasibilityResult` → understand current blocker categorization
- Study `planning_tab.py` tab refresh mechanism → understand when/how to trigger recalculation
- Study `batch_decision_service.py` → understand save flow for adding guards

**Key Patterns to Copy:**
- `progress.ProductionProgress` dataclass → extend or compose for UI display model
- `shopping_list.get_shopping_list(production_aware=True)` → call from planning UI in IN_PRODUCTION state
- `feasibility.check_assembly_feasibility()` → extend with projected output calculation
- Plan state conditional rendering → existing pattern in planning_tab.py for button visibility

**Focus Areas:**
- **Minimize new service code**: Most calculations already exist; focus on wiring and UI
- **Projected feasibility**: The primary new service logic — computing expected output from remaining production
- **Amendment guards**: Simple guard logic in batch decision save path
- **State-conditional UI**: Planning tab must show different content based on plan state
- **Refresh mechanism**: Ensure production data is fresh when planning tab is viewed

**Integration Points:**
- Production progress data feeds shopping summary recalculation
- Assembly feasibility consumes both current inventory and projected production output
- Batch decision guards consume production progress per recipe
- All data refreshes when planning tab becomes active

---

**END OF SPECIFICATION**
