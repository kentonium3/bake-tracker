# Feature Specification: Assembly Feasibility & Single-Screen Planning

**Feature Number**: F076
**Version**: 1.0
**Status**: Draft
**Priority**: HIGH

---

## Problem Statement

All Phase 2 planning calculations exist (F068-F075) but are not integrated into a cohesive user experience:
- No assembly feasibility validation exists to check if batch production meets finished goods requirements
- Planning UI sections are scattered, requiring users to navigate between different views
- Changes in one section don't automatically update dependent sections
- Users cannot see the complete planning workflow on a single screen

This creates cognitive burden and risks planning errors when users cannot see the full picture.

---

## User Stories

### US-1: Event Planner Validates Assembly Feasibility
**As an** event planner
**I want to** see whether my batch decisions produce enough to meet finished goods requirements
**So that** I can identify and resolve production shortfalls before the event

**Acceptance Criteria**:
- System calculates expected production from batch decisions
- Production is compared against FG quantity requirements
- For bundles, all component availability is validated recursively
- Clear status indicators show feasibility (met, warning, failed)

### US-2: Event Planner Uses Single-Screen Planning
**As an** event planner
**I want to** see all planning sections on one screen
**So that** I can understand the complete plan without navigating between views

**Acceptance Criteria**:
- Event header, recipe selection, FG selection, batch decisions, shopping summary, and assembly status visible simultaneously
- Logical flow from top to bottom: Event → Recipes → FGs → Batches → Shopping → Assembly
- Layout fits standard desktop resolution without horizontal scrolling
- All sections are readable and interactive without excessive scrolling

### US-3: Event Planner Sees Real-Time Updates
**As an** event planner
**I want** changes in one section to automatically update dependent sections
**So that** I always see accurate, current information

**Acceptance Criteria**:
- Recipe selection change → FG list refreshes
- FG quantity change → Batch options recalculate
- Batch decision change → Shopping list updates AND assembly status updates
- Updates occur immediately without manual refresh
- No stale data displayed

### US-4: Event Planner Understands Plan Status at a Glance
**As an** event planner
**I want** clear visual indicators showing the status of my plan
**So that** I know what actions are needed

**Acceptance Criteria**:
- Assembly feasibility shows prominent status (all met / issues / failed)
- Batch decisions section shows complete/incomplete indicator
- Shopping list section shows whether purchases are required
- Overall plan completeness is visible

---

## Functional Requirements

### FR-1: Assembly Feasibility Service
The system shall provide a service that:
- Calculates expected production quantities from saved batch decisions
- Compares production against finished goods requirements
- For bundles, validates all component availability recursively
- Returns a structured result with overall feasibility and per-FG details

**Input**: Event ID with saved batch decisions
**Output**: Feasibility result with:
- Overall feasibility flag (boolean)
- Per-finished-good status:
  - FG identity (name, ID)
  - Quantity needed
  - Can assemble (boolean)
  - Component details for bundles

### FR-2: Single-Screen Layout Integration
The planning tab shall display all sections on one screen:
1. Event metadata header (name, date, attendees)
2. Recipe selection section
3. Finished goods selection with quantities
4. Batch decision options
5. Shopping list summary (purchase required count, sufficient count)
6. Assembly feasibility status panel

Layout shall be compact but readable, with logical vertical flow.

### FR-3: Real-Time Update Propagation
The UI shall automatically propagate changes:
- Recipe change → Refresh available FGs → Clear invalid FG selections
- FG quantity change → Recalculate batch options → Update shopping list
- Batch decision change → Update shopping list → Update assembly status

Updates shall be immediate (no manual refresh button required for cascading updates).

### FR-4: Visual Status Indicators
The UI shall display clear status indicators:
- **Assembly Status**: All FGs can be assembled / Partial / Cannot assemble
- **Batch Decisions**: "X of Y decided" progress indicator
- **Shopping List**: "X items to purchase" summary
- **Overall**: Visual cue when plan is complete vs needs attention

---

## Out of Scope

- Plan locking (F077 - Phase 3)
- Plan amendments (F078 - Phase 3)
- Production awareness/tracking (F079 - Phase 3)
- Multi-event comparison views
- Print/export of single-screen view
- Mobile responsive layout

---

## Dependencies

- **F068**: Event Management & Planning Data Model (Event, EventRecipe, EventFinishedGood)
- **F069**: Recipe Selection for Event Planning
- **F070**: Finished Goods Filtering for Event Planning
- **F071**: Finished Goods Quantity Specification
- **F072**: Recipe Decomposition & Aggregation (bundle decomposition)
- **F073**: Batch Calculation & User Decisions
- **F074**: Ingredient Aggregation for Batch Decisions
- **F075**: Inventory Gap Analysis

---

## Assumptions

1. Batch decisions exist for all FUs before assembly feasibility can be calculated
2. Bundle decomposition (F072) correctly handles nested bundles to 3 levels
3. The planning_tab.py UI structure can accommodate additional sections
4. Real-time updates can be achieved via callback mechanisms already in place

---

## Success Criteria

1. **Assembly Calculation**: Service correctly calculates production vs requirements with 100% accuracy
2. **Bundle Validation**: Nested bundle components validated recursively
3. **UI Integration**: All 6 planning sections visible on single screen without tab navigation
4. **Update Propagation**: Changes cascade to dependent sections within 500ms
5. **Status Clarity**: Users can determine plan status at a glance in under 3 seconds
6. **Stability**: No UI freezes or errors during rapid input changes

---

## Key Entities

### AssemblyFeasibilityResult
- overall_feasible: boolean
- finished_goods: list of FGFeasibilityStatus

### FGFeasibilityStatus
- finished_good_id: integer
- finished_good_name: string
- quantity_needed: integer
- can_assemble: boolean
- shortfall: integer (0 if can_assemble)
- components: list of ComponentStatus (for bundles only)

### ComponentStatus
- component_type: "finished_unit" or "nested_bundle"
- component_id: integer
- component_name: string
- quantity_needed: integer
- quantity_available: integer
- is_sufficient: boolean
