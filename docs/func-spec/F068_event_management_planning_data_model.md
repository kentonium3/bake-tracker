# F068: Event Management & Planning Data Model

**Version**: 1.0  
**Priority**: HIGH  
**Type**: Full Stack (Service Layer + Database Schema + UI)

---

## Executive Summary

Planning module cannot function without event management and a complete data model foundation:
- ❌ No event CRUD operations (can't create events to plan for)
- ❌ Planning data model undefined (schema will churn as features added)
- ❌ No event-recipe associations (can't track which recipes selected)
- ❌ No event-finished goods associations (can't track quantities)
- ❌ No batch decision storage (user choices lost)

This spec establishes the complete planning data model and implements basic event management as the foundation for all subsequent planning features (F069-F079).

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Planning Module
└─ ❌ DOESN'T EXIST

Events
└─ ❌ No event table

Event-Recipe Associations
└─ ❌ No way to track recipe selections

Event-Finished Goods Associations
└─ ❌ No way to track FG selections with quantities

Batch Decisions
└─ ❌ No storage for user's batch choices

Plan State
└─ ❌ No state tracking (DRAFT/LOCKED/IN_PRODUCTION/COMPLETED)
```

**Target State (COMPLETE):**
```
Planning Data Model (Phase 2 + Phase 3 Prepared)
├─ ✅ events table
├─ ✅ event_recipes (many-to-many: events ↔ recipes)
├─ ✅ event_finished_goods (FG selections with quantities)
├─ ✅ batch_decisions (user's batch choices per recipe)
├─ ✅ plan_snapshots (Phase 3 structure defined)
└─ ✅ plan_amendments (Phase 3 structure defined)

Event Management
├─ ✅ Create events (name, date, attendees)
├─ ✅ Read events (list, detail)
├─ ✅ Update events (edit metadata)
└─ ✅ Delete events (with cascade rules)

Event Service
├─ ✅ CRUD operations
├─ ✅ Validation (required fields, valid dates)
└─ ✅ Database session management

Event UI (Basic)
├─ ✅ Event list view
├─ ✅ Create event dialog
├─ ✅ Edit event dialog
└─ ✅ Delete confirmation
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Database schema patterns**
   - Find existing models in `src/models/`
   - Study SQLAlchemy model patterns (relationships, constraints, timestamps)
   - Note naming conventions (table names, foreign keys)
   - Understand how relationships defined (e.g., ingredient_id references ingredients.id)

2. **Service layer patterns**
   - Find existing services like `IngredientService`, `ProductService`, `RecipeService`
   - Study CRUD operation patterns
   - Note session management approach (session passed to __init__)
   - Understand validation patterns
   - Note error handling approach

3. **UI patterns for CRUD operations**
   - Find existing CRUD UIs (ingredients, products, recipes management)
   - Study dialog patterns (create, edit, delete confirmation)
   - Note list view patterns (display, selection, actions)
   - Understand how services called from UI

4. **Migration script patterns**
   - Find existing migrations in `migrations/`
   - Study manual Python migration approach (no Alembic)
   - Note how schema changes managed
   - Understand rollback patterns

---

## Requirements Reference

This specification implements:
- **REQ-PLAN-001**: System shall support event creation with name, date, and expected attendees
- **REQ-PLAN-002**: Expected attendees shall be stored as metadata but NOT used in any calculations
- **REQ-PLAN-003**: System shall support viewing past events as reference during planning
- **REQ-PLAN-004**: System shall validate event dates are valid dates
- **REQ-PLAN-005**: System shall support event editing (name, date, attendees)
- **VAL-PLAN-001**: Event name required
- **VAL-PLAN-002**: Event date must be valid date
- **VAL-PLAN-003**: At least one recipe must be selected (enforced in later features)

From: `docs/requirements/req_planning.md` (v0.4)

---

## Functional Requirements

### FR-1: Define Complete Planning Data Model

**What it must do:**
- Define complete database schema for all planning tables (Phase 2 + Phase 3 preparation)
- Create migration script to establish tables
- Establish foreign key relationships
- Add appropriate indexes for query performance
- Include created_at/updated_at timestamps on all tables

**Schema requirements:**

**events table:**
- id (primary key)
- name (text, required)
- event_date (date, required)
- expected_attendees (integer, nullable) 
- plan_state (text, default 'DRAFT') - values: DRAFT, LOCKED, IN_PRODUCTION, COMPLETED
- created_at, updated_at (timestamps)

**event_recipes table (many-to-many):**
- event_id (foreign key → events.id)
- recipe_id (foreign key → recipes.id)
- Primary key: (event_id, recipe_id)
- created_at timestamp

**event_finished_goods table:**
- event_id (foreign key → events.id)
- finished_good_id (foreign key → finished_goods.id)
- quantity (integer, required, positive)
- Primary key: (event_id, finished_good_id)
- created_at, updated_at timestamps

**batch_decisions table:**
- event_id (foreign key → events.id)
- recipe_id (foreign key → recipes.id)
- batches (integer, required, positive)
- yield_option_id (foreign key → recipe_yield_options.id)
- Primary key: (event_id, recipe_id)
- created_at, updated_at timestamps

**plan_snapshots table (Phase 3 preparation):**
- id (primary key)
- event_id (foreign key → events.id)
- snapshot_type (text) - values: ORIGINAL, CURRENT
- snapshot_data (JSON, complete plan state)
- created_at timestamp

**plan_amendments table (Phase 3 preparation):**
- id (primary key)
- event_id (foreign key → events.id)
- amendment_type (text) - values: DROP_FG, ADD_FG, MODIFY_BATCH
- amendment_data (JSON, type-specific details)
- reason (text, nullable)
- created_at timestamp

**Pattern reference:** Study existing model files (ingredients.py, products.py, recipes.py), copy SQLAlchemy patterns

**Success criteria:**
- [ ] All 6 tables defined in models
- [ ] Migration script creates all tables
- [ ] Foreign key constraints work correctly
- [ ] Cascade delete rules defined (deleting event deletes associations)
- [ ] Timestamps auto-populate on create/update

---

### FR-2: Implement Event Service CRUD Operations

**What it must do:**
- Create PlanningService with event CRUD methods
- Accept database session in __init__ (session management pattern)
- Implement create_event(name, date, expected_attendees) → Event
- Implement get_event(event_id) → Event
- Implement get_all_events() → List[Event]
- Implement update_event(event_id, **updates) → Event
- Implement delete_event(event_id) → bool
- Validate required fields (name, date)
- Validate date format
- Return appropriate errors for not found, validation failures

**Pattern reference:** Study IngredientService, ProductService patterns, copy service structure exactly

**Business rules:**
- Event name cannot be empty
- Event date must be valid date object
- Expected attendees must be positive integer or None
- Deleting event cascades to event_recipes, event_finished_goods, batch_decisions

**Success criteria:**
- [ ] PlanningService class exists with session management
- [ ] create_event creates record and returns Event
- [ ] get_event retrieves by ID
- [ ] get_all_events returns list
- [ ] update_event modifies and returns Event
- [ ] delete_event removes event and cascades
- [ ] Validation errors raised for invalid inputs
- [ ] Service follows established patterns exactly

---

### FR-3: Implement Event Management UI

**What it must do:**
- Add Events section to Planning workspace (new workspace or existing)
- Display list of existing events (name, date, attendees count)
- Provide "Create Event" button
- Provide edit/delete actions per event
- Create Event dialog: name, date picker, attendees input
- Edit Event dialog: same fields, pre-populated
- Delete confirmation dialog
- Refresh list after create/update/delete

**UI Requirements:**
- Events list shows: name, date (formatted), expected attendees, actions
- Create/Edit dialogs validate before saving
- Date picker for event date (not free text)
- Expected attendees accepts integers only
- Error messages display for validation failures
- Success feedback after operations

**Pattern reference:** Study existing CRUD UIs (Ingredients, Products management), copy dialog and list patterns

**Note:** Exact UI layout (table vs cards, button placement, etc.) determined during planning phase. Focus on WHAT the UI must accomplish, not HOW to implement it.

**Success criteria:**
- [ ] User can view list of events
- [ ] User can create new event
- [ ] User can edit existing event
- [ ] User can delete event (with confirmation)
- [ ] Validation messages clear and helpful
- [ ] UI follows existing patterns

---

### FR-4: Event Lifecycle Support

**What it must do:**
- Support plan_state field (DRAFT, LOCKED, IN_PRODUCTION, COMPLETED)
- Default new events to DRAFT state
- Display plan state in event list
- Allow filtering events by state (optional enhancement)

**Pattern reference:** State is stored but state transitions implemented in F077 (Plan State Management)

**Success criteria:**
- [ ] plan_state field exists and defaults to DRAFT
- [ ] State displays in event list
- [ ] State persists correctly

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Recipe selection UI (F069)
- ❌ Finished goods selection UI (F070-F071)
- ❌ Batch calculation logic (F073)
- ❌ Ingredient aggregation (F074a)
- ❌ Inventory gap analysis (F074b)
- ❌ Assembly feasibility (F075)
- ❌ Plan state transitions (F077 - just define field structure here)
- ❌ Plan snapshots/amendments implementation (F078-F079 - just define table structure here)

---

## Success Criteria

**Complete when:**

### Database Schema
- [ ] All 6 tables created via migration
- [ ] Foreign keys work correctly
- [ ] Cascade deletes work (event deletion removes associations)
- [ ] Timestamps auto-populate
- [ ] Tables match requirements exactly

### Event Service
- [ ] PlanningService class implements CRUD
- [ ] create_event works
- [ ] get_event works
- [ ] get_all_events works
- [ ] update_event works
- [ ] delete_event works with cascade
- [ ] Validation catches invalid inputs
- [ ] Error messages clear

### Event UI
- [ ] Events display in list
- [ ] Create event dialog works
- [ ] Edit event dialog works
- [ ] Delete confirmation works
- [ ] Date picker functional
- [ ] Validation feedback works
- [ ] List refreshes after operations

### Quality
- [ ] Code follows established service patterns
- [ ] UI follows established dialog patterns
- [ ] Error handling consistent with project
- [ ] Session management correct
- [ ] No code duplication

---

## Architecture Principles

### Data Model Foundation

**Complete Schema Definition:**
- Define ALL planning tables in this feature (even if not fully used until later features)
- Prevents schema churn as features F069-F079 are implemented
- Each subsequent feature adds service operations and UI, not schema changes

**Why this matters:**
- Database schema should be stable from the start
- Migration scripts easier to manage if schema defined once
- Prevents foreign key issues from evolving schema

### Service Layer Structure

**Session Management:**
- Service accepts session in __init__
- All operations use provided session
- No session commits within service methods (caller controls transaction)

**CRUD Pattern:**
- create_x() → returns created object
- get_x(id) → returns object or None
- get_all_x() → returns list
- update_x(id, **updates) → returns updated object
- delete_x(id) → returns bool

### UI Pattern Consistency

**Dialog Pattern:**
- Create/Edit use same dialog structure
- Validation before save
- Error feedback inline
- Success feedback after save

**List Pattern:**
- Display key fields
- Action buttons per row
- Refresh after mutations

---

## Constitutional Compliance

✅ **Principle I: Data Integrity and Immutability**
- Timestamps track all changes (created_at, updated_at)
- Foreign key constraints maintain referential integrity
- Cascade deletes prevent orphaned records

✅ **Principle II: Layered Architecture**
- Service layer separate from UI
- Database operations in service only
- UI calls service methods, never direct DB access

✅ **Principle III: Service Primitives**
- Each CRUD operation is atomic
- Service methods composable
- No hidden side effects

✅ **Principle IV: Session Consistency**
- Service uses provided session
- Caller controls transaction boundaries
- Multiple service calls in same session for consistency

✅ **Principle V: Pattern Matching**
- Event service matches IngredientService pattern exactly
- Event UI matches existing CRUD UI patterns
- Database models match existing model patterns

---

## Risk Considerations

**Risk: Schema churn if tables incomplete**
- **Context:** If we only define tables needed for F068, later features will require new migrations
- **Mitigation:** Define complete planning schema (Phase 2 + Phase 3 structure) in this feature, even if some tables not fully used until later

**Risk: Service pattern deviation**
- **Context:** New developers might deviate from established service patterns
- **Mitigation:** Planning phase must study existing services (IngredientService, ProductService) and copy patterns exactly

**Risk: Foreign key constraint failures**
- **Context:** If cascade rules not defined, deleting events could fail or leave orphaned records
- **Mitigation:** Define explicit cascade rules in schema, test delete operations

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `src/models/ingredient.py` → apply to Event model
- Study `src/services/ingredient_catalog_service.py` → apply to PlanningService
- Study existing CRUD dialogs → apply to Event dialogs
- Study migration scripts in `migrations/` → apply to planning schema migration

**Key Patterns to Copy:**
- SQLAlchemy model structure → Event model (exact parallel)
- Service __init__ with session → PlanningService (exact parallel)
- CRUD method signatures → PlanningService methods (exact parallel)
- Dialog validation patterns → Event dialogs (exact parallel)

**Focus Areas:**
- **Schema completeness:** All 6 tables defined even if not fully used yet
- **Foreign key relationships:** Correct references to recipes, finished_goods, recipe_yield_options
- **Cascade rules:** DELETE event cascades to associations
- **Service patterns:** Follow existing patterns exactly (no improvisation)
- **UI patterns:** Follow existing CRUD UI patterns exactly

**Migration Strategy:**
- Single migration script creates all 6 tables
- Include indexes on foreign keys for query performance
- Test cascade deletes work correctly

---

**END OF SPECIFICATION**
