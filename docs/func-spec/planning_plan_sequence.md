# Planning Module - Functional Specification Sequence

**Document Version:** 1.0  
**Date:** 2025-01-26  
**Author:** Kent Gale  
**Status:** Planning

---

## Purpose

This document defines the sequence and scope of functional specifications to be developed for the Planning module using the spec-kitty workflow. Each feature represents a discrete, implementable unit that builds upon the requirements defined in `req_planning.md`.

**Source Requirements:** `/docs/requirements/req_planning.md` (v0.4)

**Target Workflow:** Spec-kitty feature development (specify → plan → tasks → implement → review → merge)

---

## Phase 2: Static Planning (9 Features)

### F-PLAN-001: Event Management & Planning Data Model

**Scope:**
- CRUD operations for events (create, read, update, delete)
- Event metadata: name, date, expected attendees
- Basic validation (required fields, valid dates)
- **Complete planning data model schema definition**
  - Events table
  - EventRecipeSelection (event-recipe associations)
  - EventFinishedGood (event-FG associations with quantities)
  - BatchDecision (user's batch choices per recipe)
  - Plan state and metadata
- Event persistence in database
- Database migration scripts

**Why First:**
- Foundation for all other planning features
- No dependencies on other planning features
- Enables basic data entry and testing
- **Critical: Establishes complete data model upfront to prevent schema churn**

**Requirements Coverage:**
- REQ-PLAN-001 through REQ-PLAN-005
- Event planning validation rules (VAL-PLAN-001 through VAL-PLAN-003)

**Key Design Questions:**
- Complete planning database schema (all tables for Phase 2 + Phase 3 preparation)
- Service layer interface for event operations
- UI components for event CRUD
- Foreign key relationships and constraints
- Index strategy for query performance

---

### F-PLAN-002: Recipe Selection UI

**Scope:**
- Flat list presentation of all recipes (bases + variants)
- Explicit selection via checkboxes (no auto-inclusion)
- Visual distinction between base recipes and variants
- Selection count display
- Selection persistence with event

**Why Second:**
- Enables recipe selection before FG filtering
- Independent of other planning features (just reads recipe catalog)
- Critical for establishing natural workflow order

**Requirements Coverage:**
- REQ-PLAN-006 through REQ-PLAN-012
- Mental model Section 2.2.1 and 2.2.2 (recipe-first ordering, explicit variant selection)

**Key Design Questions:**
- UI layout and visual hierarchy
- Recipe catalog service interface
- Selection state management

**Dependencies:**
- F-PLAN-001 (needs events to associate recipes with)

---

### F-PLAN-003: Finished Goods Filtering

**Scope:**
- Dynamic filtering of FG list based on selected recipes
- "ALL atomic recipes selected" check for nested FGs (bundles)
- Clear indicators for unavailable FGs (which recipe missing)
- Real-time updates when recipe selection changes
- Automatic clearing of invalid FG selections

**Why Third:**
- Implements core UX principle (recipe selection drives FG availability)
- Depends on recipe selection being established
- Prerequisite for quantity specification

**Requirements Coverage:**
- REQ-PLAN-013 through REQ-PLAN-017
- Mental model Section 2.2.1 (pre-filtering prevents invalid selections)

**Key Design Questions:**
- Decomposition algorithm for nested FGs
- Filtering performance for large FG catalogs
- UI feedback for unavailable items

**Dependencies:**
- F-PLAN-001 (needs events)
- F-PLAN-002 (needs recipe selections)

---

### F-PLAN-004: Quantity Specification

**Scope:**
- Quantity input per selected finished good
- Validation (positive integers only)
- Modification support
- Input persistence

**Why Fourth:**
- Completes basic event definition
- Simple feature, low risk
- Enables next phase (decomposition)

**Requirements Coverage:**
- REQ-PLAN-018 through REQ-PLAN-021
- Validation rules VAL-PLAN-005

**Key Design Questions:**
- Input component design
- Validation feedback
- Bulk entry patterns (if needed)

**Dependencies:**
- F-PLAN-001 (needs events)
- F-PLAN-003 (needs filtered FG list)

---

### F-PLAN-005: Recipe Decomposition & Aggregation

**Scope:**
- Decompose nested finished goods to atomic recipe components (recursive)
- Map each atomic FG to the recipe that produces it (base or variant)
- Aggregate quantities by unique recipe
- Handle multi-level nesting
- Sum quantities when multiple FGs use same recipe

**Why Fifth:**
- Core calculation logic
- Prerequisite for all downstream calculations
- No UI component (pure service layer)

**Requirements Coverage:**
- REQ-PLAN-022 through REQ-PLAN-027
- Section 7.2 (Recipe Decomposition Requirements)
- Mental model Section 2.2.4 (nested FG handling)

**Key Design Questions:**
- Recursive decomposition algorithm
- Performance for deeply nested structures
- Caching strategy for decomposition results

**Dependencies:**
- F-PLAN-001 (needs events)
- F-PLAN-002 (needs recipe selections)
- F-PLAN-003 (needs FG selections)
- F-PLAN-004 (needs quantities)

---

### F-PLAN-006: Batch Calculation & User Decisions

**Scope:**
- Calculate batch options for each recipe (floor and ceil)
- Present options with actual numbers (batches, yield, shortfall/excess)
- Identify exact matches
- User selection per recipe (radio buttons or similar)
- Shortfall confirmation flow
- Batch decision persistence

**Why Sixth:**
- Core value proposition (solving manual batch calculation errors)
- Depends on recipe aggregation being complete
- Critical user decision point

**Requirements Coverage:**
- REQ-PLAN-028 through REQ-PLAN-034
- Section 7.3 (Batch Calculation Requirements)
- Mental model Section 2.2.3 (batch rounding decisions)
- Validation rules VAL-PLAN-009 through VAL-PLAN-011

**Key Design Questions:**
- Batch option presentation UI
- Decision state management
- Shortfall warning UX
- Multiple yield options handling

**Dependencies:**
- F-PLAN-001 through F-PLAN-005 (full pipeline to recipe requirements)

---

### F-PLAN-007a: Ingredient Aggregation

**Scope:**
- Calculate variant proportions (variant_quantity / total_recipe_quantity)
- Scale base ingredients (batches × batch_multiplier)
- Scale variant ingredients (base_quantity × variant_proportion)
- Aggregate same ingredients across recipes
- Keep different ingredient forms separate
- Maintain precision to 3 decimal places

**Why Seventh:**
- Requires batch decisions to be finalized
- Complex calculation logic deserves focused implementation
- Testable independently from inventory system

**Requirements Coverage:**
- REQ-PLAN-035 through REQ-PLAN-046
- Section 7.4 (Variant Allocation Requirements)
- Section 7.5 (Ingredient Aggregation Requirements)

**Key Design Questions:**
- Variant proportion calculation algorithm
- Ingredient aggregation data structures
- Rounding and precision handling
- Same ingredient identification (form separation)

**Dependencies:**
- F-PLAN-006 (needs batch decisions)

---

### F-PLAN-007b: Inventory Gap Analysis

**Scope:**
- Query current inventory for all needed ingredients
- Compare aggregated ingredients against inventory
- Calculate gaps (need - have) for each ingredient
- Flag ingredients requiring purchase
- Generate shopping list with quantities
- Display sufficient ingredients separately

**Why Eighth:**
- Depends on ingredient aggregation being complete
- Integrates with InventoryService
- Delivers key user output (shopping list)

**Requirements Coverage:**
- REQ-PLAN-047 through REQ-PLAN-052
- Section 7.6 (Inventory Gap Requirements)

**Key Design Questions:**
- InventoryService interface contract
- Gap calculation for missing inventory (treat as zero)
- Purchase list formatting and presentation
- Unit handling and conversion

**Dependencies:**
- F-PLAN-007a (needs aggregated ingredients)

---

### F-PLAN-008: Assembly Feasibility & Single-Screen UI

**Scope:**
- **Service Layer (testable independently):**
  - Calculate production from batch decisions
  - Compare production vs finished goods requirements
  - Validate component availability for bundles
  - Return feasibility data structure
- **UI Integration:**
  - Single-screen layout integrating all planning sections
  - Display overall feasibility status
  - Show component-level detail for bundles
  - Real-time updates across all sections
  - Visual status indicators (✓/⚠️/✗)
  - Section organization and flow

**Why Ninth (Capstone):**
- Brings all planning features together
- Final validation before production
- Completes Phase 2 user experience
- Inherently larger as integration feature - this is expected and acceptable

**Requirements Coverage:**
- REQ-PLAN-053 through REQ-PLAN-061
- Section 7.7 (Assembly Feasibility Requirements)
- Section 10 (UI/UX Specifications)
- Non-functional requirements (performance, usability)

**Key Design Questions:**
- **Service layer:** Assembly calculation algorithm, component decomposition logic
- **UI layer:** Single-screen layout design, update propagation mechanism, component breakdown presentation
- Clear separation between calculation services and UI presentation

**Dependencies:**
- F-PLAN-001 through F-PLAN-007b (all Phase 2 features)

---

## Phase 3: Dynamic Planning (3 Features)

### F-PLAN-009: Plan State Management

**Scope:**
- State transitions (DRAFT → LOCKED → IN_PRODUCTION → COMPLETED)
- Plan locking when production starts
- State validation (prevent invalid transitions)
- State persistence
- UI indicators for current state

**Why First (Phase 3):**
- Foundation for dynamic planning
- Required before amendments can be tracked
- Simple state machine implementation

**Requirements Coverage:**
- Section 3.2 (Deferred to Phase 3)
- Section 14.2 (Phase 3 Candidates)
- Dynamic planning design from requirements refinement session

**Key Design Questions:**
- State transition rules
- Lock/unlock authorization
- State change events

**Dependencies:**
- All Phase 2 features (F-PLAN-001 through F-PLAN-008)

---

### F-PLAN-010: Plan Snapshots & Amendments

**Scope:**
- Capture original plan snapshot when production starts
- Amendment types: drop FG, add FG, modify batch decision
- Amendment logging (timestamp, reason, amendment data)
- Amendment history view
- Current plan vs original plan comparison
- Prevent amendments to in-progress batches

**Why Second (Phase 3):**
- Enables mid-production plan changes
- Requires state management foundation
- Core Phase 3 functionality

**Requirements Coverage:**
- Section 14.2 (Phase 3 enhancements)
- Dynamic planning design (amendments, audit trail)
- Mental model refinement notes (between-batch modifications)

**Key Design Questions:**
- Snapshot data structure
- Amendment data model
- Version comparison UI
- Reason/justification capture

**Dependencies:**
- F-PLAN-009 (needs state management)

---

### F-PLAN-011: Production-Aware Calculations

**Scope:**
- Query ProductionService for batch completion status
- Calculate remaining needs (forward-looking, not total)
- Real-time assembly feasibility with production status
- Validate modification allowed (batch not in-progress)
- Update ingredient gaps based on remaining needs
- Show production progress in planning UI

**Why Third (Phase 3):**
- Most complex Phase 3 feature
- Depends on amendments being tracked
- Integrates with ProductionService (external dependency)
- Completes dynamic planning capability

**Requirements Coverage:**
- Section 3.2 (Phase 3 scope)
- Section 14.2 (real-time plan adjustments)
- Dynamic planning design (production-aware calculations, remaining needs)

**Key Design Questions:**
- ProductionService interface contract
- Recalculation triggers
- UI presentation of production vs planned
- Performance of real-time queries

**Dependencies:**
- F-PLAN-009 (needs state management)
- F-PLAN-010 (needs amendment tracking)
- ProductionService (external - must be available)

---

## Feature Dependency Graph

```
Phase 2:
F-001 (Event Management + Data Model)
  ├─→ F-002 (Recipe Selection)
  │     ├─→ F-003 (FG Filtering)
  │     │     ├─→ F-004 (Quantity Spec)
  │     │     │     └─→ F-005 (Decomposition)
  │     │     │           └─→ F-006 (Batch Calc)
  │     │     │                 ├─→ F-007a (Ingredient Aggregation)
  │     │     │                 │     └─→ F-007b (Inventory Gaps)
  │     │     │                 │           └─→ F-008 (Assembly & UI)
  │     │     └─────────────────────────────────┘

Phase 3:
[All Phase 2 Features]
  └─→ F-009 (Plan States)
        └─→ F-010 (Amendments)
              └─→ F-011 (Production-Aware)
```

---

## Implementation Considerations

### F-PLAN-001: Complete Data Model First

**Critical:** F-PLAN-001 must define the complete planning data model schema, not just the Event table. This prevents schema churn as features are implemented.

**Tables to define in F-PLAN-001:**
- `events` - Event metadata
- `event_recipes` - Many-to-many: events ↔ recipes
- `event_finished_goods` - Event FG selections with quantities
- `batch_decisions` - User's batch choices per recipe per event
- Phase 3 preparation: `plan_snapshots`, `plan_amendments` (structure defined, not necessarily implemented)

**Why this matters:** Each subsequent feature (F-002 through F-008) will add service layer operations and UI, but the database schema should be stable from the start.

---

### F-PLAN-007: Split for Manageable Scope

**F-PLAN-007a (Ingredient Aggregation)** focuses on calculation logic:
- Pure calculation feature
- Complex algorithms (variant proportions, scaling, aggregation)
- Testable independently without external dependencies
- Output: Complete ingredient totals data structure

**F-PLAN-007b (Inventory Gap Analysis)** focuses on external integration:
- Integrates with InventoryService
- Simpler logic (comparison and gap calculation)
- Delivers user-facing output (shopping list)
- Input: Ingredient totals from F-PLAN-007a

**Decision point:** If during F-PLAN-007a specification, the scope still feels manageable, the features MAY be recombined. However, default to keeping them split to prevent overwhelming implementation cycles.

---

### F-PLAN-008: Accept as Integration Feature

**This feature is intentionally larger** as the capstone of Phase 2. It brings together all previous features into a cohesive user experience.

**Mitigation strategy in spec:**
- **Clear separation:** Service-layer assembly calculations vs UI integration work
- **Service layer first:** Assembly feasibility calculations fully testable before UI work begins
- **UI integration second:** Layout, updates, visual indicators
- **Acceptance criteria:** Explicitly separate service tests from UI tests

**This is expected and acceptable** for an integration feature. The key is ensuring the spec maintains clear boundaries.

---

## Implementation Sequence

### Recommended Order

**Sprint 1-2 (Foundation):**
1. F-PLAN-001: Event Management
2. F-PLAN-002: Recipe Selection UI

**Sprint 3-4 (Event Definition):**
3. F-PLAN-003: Finished Goods Filtering
4. F-PLAN-004: Quantity Specification

**Sprint 5-6 (Core Calculations):**
5. F-PLAN-005: Recipe Decomposition & Aggregation
6. F-PLAN-006: Batch Calculation & User Decisions

**Sprint 7-8 (Final Calculations):**
7. F-PLAN-007a: Ingredient Aggregation
8. F-PLAN-007b: Inventory Gap Analysis

**Sprint 9 (Integration):**
9. F-PLAN-008: Assembly Feasibility & Single-Screen UI

**Sprint 10-12 (Phase 3):**
10. F-PLAN-009: Plan State Management
11. F-PLAN-010: Plan Snapshots & Amendments
12. F-PLAN-011: Production-Aware Calculations

---

## Success Criteria

**Phase 2 Complete When:**
- User can create event, select recipes, specify FG quantities
- System calculates batch options, user makes decisions
- System generates shopping list (ingredient gaps)
- System validates assembly feasibility
- All features integrated on single screen
- Real-time updates work across all sections

**Phase 3 Complete When:**
- Plans can be locked when production starts
- Original plan preserved as snapshot
- User can amend plans between batches (drop/add FGs, modify batches)
- System tracks amendments with reasons
- Calculations update based on production progress
- Real-time assembly feasibility reflects actual production

---

## Notes

**Spec-Kitty Workflow:**
Each feature follows: specify → plan → tasks → implement → review → merge

**Requirements Traceability:**
Each feature spec will explicitly map to requirements in `req_planning.md` (v0.4)

**Constitutional Alignment:**
All features must follow architectural patterns defined in Section 15 (service primitives, session consistency, separation of concerns, immutability, catalog vs operational data)

**Testing Strategy:**
Each feature includes unit tests, integration tests, and user acceptance criteria

---

**Document Status:** ✅ APPROVED FOR SPEC-KITTY WORKFLOW

**Next Step:** Begin F-PLAN-001 specification development
