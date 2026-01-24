# F064: FinishedGoods Snapshot Implementation

**Version**: 1.0  
**Priority**: HIGH (P0 - Blocking)  
**Type**: Service Layer + Data Model  
**Status**: Draft  
**Created**: 2025-01-24

---

## Executive Summary

Current gaps in FinishedGoods implementation:
- ❌ No snapshot models for FinishedUnit or FinishedGood definitions
- ❌ Planning service cannot create immutable snapshots of event requirements
- ❌ Assembly operations reference live definitions (violates definition/instantiation separation)
- ❌ Changes to FinishedGood definitions affect planned/historical assemblies
- ❌ No recursive snapshot support for nested FinishedGoods

This spec implements the universal Pattern A snapshot architecture (Catalog Service Ownership + Mirrored Tables) for FinishedGoods, enabling immutable definition capture at planning/assembly time and completing the definition/instantiation separation principle across the entire application.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
FinishedGoods System
├─ ✅ FinishedUnit model (catalog definitions)
├─ ✅ FinishedGood model (catalog definitions)
├─ ✅ Composition model (component relationships)
├─ ❌ No FinishedUnitSnapshot model
├─ ❌ No FinishedGoodSnapshot model
└─ ❌ AssemblyRun references live definitions (not snapshots)

FinishedUnit Service
├─ ✅ CRUD operations for definitions
├─ ❌ No create_finished_unit_snapshot() primitive
└─ ❌ No snapshot retrieval methods

FinishedGood Service
├─ ✅ CRUD operations for definitions
├─ ✅ Component management
├─ ❌ No create_finished_good_snapshot() primitive
├─ ❌ No recursive snapshot support
└─ ❌ No circular reference detection

Planning Service
├─ ✅ Event planning calculations
├─ ❌ No snapshot orchestration
└─ ❌ References live definitions (not snapshots)

Assembly Service
├─ ✅ AssemblyRun creation
├─ ❌ References live FinishedGood definitions
└─ ❌ No finished_good_snapshot_id FK
```

**Target State (COMPLETE):**
```
FinishedGoods System
├─ ✅ FinishedUnit model (catalog definitions)
├─ ✅ FinishedGood model (catalog definitions)
├─ ✅ FinishedUnitSnapshot model (immutable snapshots)
├─ ✅ FinishedGoodSnapshot model (immutable snapshots)
└─ ✅ AssemblyRun references finished_good_snapshot_id

FinishedUnit Service
├─ ✅ CRUD operations for definitions
├─ ✅ create_finished_unit_snapshot() primitive
└─ ✅ get_snapshot_by_id() retrieval

FinishedGood Service
├─ ✅ CRUD operations for definitions
├─ ✅ create_finished_good_snapshot() primitive (recursive)
├─ ✅ Circular reference detection (max depth 10)
└─ ✅ Component snapshot orchestration

Planning Service
├─ ✅ Event planning calculations
├─ ✅ Snapshot orchestration (calls catalog primitives)
└─ ✅ Creates planning snapshot container

Assembly Service
├─ ✅ AssemblyRun creation with snapshot reference
└─ ✅ Component consumption from snapshot data
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **RecipeSnapshot Implementation (Reference Pattern)**
   - Find `/src/models/recipe_snapshot.py`
   - Study mirrored table pattern (JSON + structured fields)
   - Note snapshot_date, is_backfilled, FK relationships
   - Understand JSON structure for recipe_data and ingredients_data

2. **RecipeSnapshot Service (Reference Implementation)**
   - Find `/src/services/recipe_snapshot_service.py`
   - Study `create_recipe_snapshot()` signature and session management
   - Note wrapper/impl pattern for session handling
   - Understand eager loading of relationships before snapshot

3. **Batch Production Service (Orchestration Pattern)**
   - Find `/src/services/batch_production_service.py`
   - Study how it calls `recipe_snapshot_service.create_recipe_snapshot()`
   - Note snapshot creation before inventory consumption
   - Understand production_run_id FK linkage

4. **FinishedUnit Model**
   - Find `/src/models/finished_unit.py`
   - Study all fields: slug, display_name, recipe_id, yield_mode, items_per_batch, item_unit
   - Note recipe relationship and cascade behavior

5. **FinishedGood Model and Composition**
   - Find `/src/models/finished_good.py`
   - Find `/src/models/composition.py`
   - Study component structure (finished_unit_id, finished_good_id, material_unit_id)
   - Note self-referential nested FinishedGood support

6. **Instantiation Pattern Research**
   - Find `/docs/research/instantiation_pattern_findings.md`
   - Study Pattern A architecture (Catalog Service Ownership)
   - Review recursive snapshot creation guidance
   - Note circular reference prevention strategies

7. **FinishedGoods Requirements**
   - Find `/docs/requirements/req_finished_goods.md` (v2.1)
   - Study REQ-FG-037 through REQ-FG-046 (Planning Snapshots)
   - Note three-layer model: Catalog/Planning/Production

8. **Constitution Principles**
   - Find `/.kittify/memory/constitution.md`
   - Study Principle II: Definition vs Instantiation Separation
   - Study Principle V: Service Boundaries (catalog owns snapshots)
   - Study Principle VIII: Session Management patterns

---

## Requirements Reference

This specification implements:
- **REQ-FG-037** through **REQ-FG-046**: Planning Snapshots (Definition/Instantiation Separation)
- Universal Pattern A architecture from instantiation pattern research
- Service boundary discipline (catalog services own snapshot creation)

From: `docs/requirements/req_finished_goods.md` (v2.1)

---

## Functional Requirements

### FR-1: FinishedUnit Snapshot Model and Service

**What it must do:**
- Create `FinishedUnitSnapshot` model following RecipeSnapshot mirrored table pattern
- Store snapshot data in JSON field for flexibility
- Include metadata: snapshot_date, snapshot_type ('planning' or 'assembly'), is_backfilled
- Support optional FK references to planning_snapshot_id and assembly_run_id
- Provide `create_finished_unit_snapshot()` primitive in finished_unit_service
- Accept optional session parameter for transactional consistency
- Return snapshot data dictionary with id and all captured fields

**Pattern reference:** Study RecipeSnapshot model structure, copy for FinishedUnit

**Data to capture in snapshot:**
```python
{
    "slug": "chocolate-chip-cookie",
    "display_name": "Chocolate Chip Cookie",
    "description": "Classic chocolate chip cookie",
    "recipe_id": 123,
    "recipe_name": "Chocolate Chip Cookie Recipe",
    "yield_mode": "DISCRETE_COUNT",
    "items_per_batch": 32,
    "item_unit": "cookie",
    "batch_percentage": null,
    "portion_description": null,
    "category": "Cookies",
    "production_notes": "Cool on rack",
    "notes": "Best served warm"
}
```

**Success criteria:**
- [ ] FinishedUnitSnapshot model exists with JSON definition_data field
- [ ] create_finished_unit_snapshot() primitive exists in finished_unit_service
- [ ] Snapshot captures all FinishedUnit fields including recipe name (denormalized)
- [ ] Session parameter follows existing pattern (session=None, wrapper/impl)
- [ ] FK to planning_snapshot_id and assembly_run_id (nullable)
- [ ] Snapshot immutable once created

---

### FR-2: FinishedGood Snapshot Model and Service

**What it must do:**
- Create `FinishedGoodSnapshot` model following RecipeSnapshot mirrored table pattern
- Store snapshot data in JSON field including full component structure
- Include metadata: snapshot_date, snapshot_type ('planning' or 'assembly'), is_backfilled
- Support optional FK references to planning_snapshot_id and assembly_run_id
- Provide `create_finished_good_snapshot()` primitive in finished_good_service
- Support recursive snapshot creation for nested FinishedGoods
- Accept optional session parameter for transactional consistency
- Return snapshot data dictionary with id and all captured fields

**Pattern reference:** Study RecipeSnapshot model, extend with component snapshot orchestration

**Data to capture in snapshot:**
```python
{
    "slug": "cookie-gift-box",
    "display_name": "Holiday Cookie Gift Box",
    "assembly_type": "gift_box",
    "packaging_instructions": "Use snowflake cellophane bag",
    "notes": "Include ribbon",
    "components": [
        {
            "component_type": "finished_unit",
            "finished_unit_snapshot_id": 456,
            "component_slug": "chocolate-chip-cookie",
            "component_name": "Chocolate Chip Cookie",
            "component_quantity": 6,
            "component_notes": "Arrange in rows",
            "sort_order": 1,
            "is_generic": false
        },
        {
            "component_type": "finished_unit",
            "finished_unit_snapshot_id": 789,
            "component_slug": "sugar-cookie",
            "component_name": "Sugar Cookie",
            "component_quantity": 6,
            "component_notes": null,
            "sort_order": 2,
            "is_generic": false
        },
        {
            "component_type": "material_unit",
            "material_unit_snapshot_id": 321,
            "component_slug": "6x6-gift-box",
            "component_name": "6x6 Gift Box",
            "component_quantity": 1,
            "component_notes": null,
            "sort_order": 3,
            "is_generic": false
        }
    ]
}
```

**Success criteria:**
- [ ] FinishedGoodSnapshot model exists with JSON definition_data field
- [ ] create_finished_good_snapshot() primitive exists in finished_good_service
- [ ] Snapshot captures all FinishedGood fields including components
- [ ] Component snapshots include references to nested snapshot IDs
- [ ] Session parameter follows existing pattern
- [ ] FK to planning_snapshot_id and assembly_run_id (nullable)
- [ ] Snapshot immutable once created

---

### FR-3: Recursive Snapshot Creation for Nested FinishedGoods

**What it must do:**
- When creating FinishedGood snapshot, automatically create snapshots for all components
- For FinishedUnit components: call finished_unit_service.create_finished_unit_snapshot()
- For nested FinishedGood components: recursively call create_finished_good_snapshot()
- For MaterialUnit components: call material_service.create_material_unit_snapshot() (when available)
- Track visited FinishedGood IDs to prevent circular references
- Enforce maximum nesting depth of 10 levels
- All component snapshots created in same transaction (all-or-nothing)
- Return complete snapshot tree structure with all nested snapshot IDs

**Pattern reference:** Study instantiation_pattern_findings.md recursive snapshot examples

**Business rules:**
- Circular references MUST be detected and prevented
- Maximum depth prevents infinite recursion
- Generic material placeholders (is_generic=true) captured without MaterialUnit snapshot
- All snapshots share same transaction for atomicity

**Success criteria:**
- [ ] Nested FinishedGood components trigger recursive snapshot creation
- [ ] Circular reference detection prevents infinite loops
- [ ] Maximum depth of 10 enforced (raises error if exceeded)
- [ ] All component snapshots created in single transaction
- [ ] Visited set passed through recursion to track hierarchy
- [ ] Error messages indicate which component caused circular reference

---

### FR-4: Circular Reference Detection and Prevention

**What it must do:**
- Maintain visited set of FinishedGood IDs during recursive snapshot traversal
- Before creating snapshot for nested FinishedGood, check if ID already in visited set
- Raise CircularReferenceError if circular dependency detected
- Include component path in error message (e.g., "A → B → C → A")
- Track nesting depth and raise MaxDepthExceededError if depth > 10
- Visited set scoped to single snapshot creation call (not global)

**Pattern reference:** Study recipe component circular reference validation, apply to snapshots

**Error handling:**
```python
# Example error messages
raise CircularReferenceError(
    f"Circular reference detected: FinishedGood {fg_id} already in snapshot tree"
)

raise MaxDepthExceededError(
    f"Snapshot nesting depth exceeds maximum of 10 levels"
)
```

**Success criteria:**
- [ ] Circular reference detection prevents infinite recursion
- [ ] Error message includes FinishedGood ID causing circular reference
- [ ] Maximum depth limit enforced (10 levels)
- [ ] Visited set correctly tracks hierarchy during recursion
- [ ] No false positives (siblings at same level don't trigger error)

---

### FR-5: Planning Service Snapshot Orchestration

**What it must do:**
- Planning service orchestrates snapshot creation during event planning
- For each production target: call recipe_service.create_recipe_snapshot() (existing)
- For each assembly target: call finished_good_service.create_finished_good_snapshot()
- Create PlanningSnapshot container record with event_id
- Pass planning_snapshot_id to all snapshot creation calls for linkage
- All snapshots created in single transaction
- Store snapshot IDs in event targets (recipe_snapshot_id, finished_good_snapshot_id)

**Pattern reference:** Study batch_production_service snapshot orchestration, apply to planning

**Orchestration workflow:**
```python
def create_event_plan_snapshots(event_id, session):
    # Create planning snapshot container
    planning_snapshot = PlanningSnapshot(event_id=event_id, created_at=utc_now())
    session.add(planning_snapshot)
    session.flush()
    
    # Snapshot all production targets (recipes)
    for target in event.production_targets:
        recipe_snapshot = recipe_service.create_recipe_snapshot(
            recipe_id=target.recipe_id,
            scale_factor=1.0,
            planning_snapshot_id=planning_snapshot.id,
            session=session
        )
        target.recipe_snapshot_id = recipe_snapshot["id"]
    
    # Snapshot all assembly targets (finished goods)
    for target in event.assembly_targets:
        fg_snapshot = finished_good_service.create_finished_good_snapshot(
            finished_good_id=target.finished_good_id,
            recursive=True,
            planning_snapshot_id=planning_snapshot.id,
            session=session
        )
        target.finished_good_snapshot_id = fg_snapshot["id"]
    
    return planning_snapshot.id
```

**Success criteria:**
- [ ] Planning service calls catalog snapshot primitives
- [ ] PlanningSnapshot container created with event linkage
- [ ] All snapshots reference planning_snapshot_id
- [ ] Event targets store snapshot IDs for later reference
- [ ] All snapshots created in single transaction
- [ ] Rollback if any snapshot creation fails

---

### FR-6: Assembly Service Integration

**What it must do:**
- Update AssemblyRun model to include finished_good_snapshot_id FK (required, non-nullable)
- Assembly service creates FinishedGood snapshot at assembly time
- AssemblyRun references snapshot, not live FinishedGood definition
- Component consumption uses snapshot data (not live definition)
- Snapshot created BEFORE inventory consumption (same pattern as RecipeSnapshot)
- Pass assembly_run_id to snapshot creation for linkage

**Pattern reference:** Study batch_production_service AssemblyRun pattern with RecipeSnapshot

**Assembly workflow:**
```python
def record_assembly(finished_good_id, quantity_assembled, event_id, session):
    # Create AssemblyRun placeholder to get ID
    assembly_run = AssemblyRun(
        finished_good_id=finished_good_id,
        quantity_assembled=quantity_assembled,
        assembled_at=utc_now(),
        event_id=event_id
    )
    session.add(assembly_run)
    session.flush()
    
    # Create snapshot (with nested components)
    fg_snapshot = finished_good_service.create_finished_good_snapshot(
        finished_good_id=finished_good_id,
        recursive=True,
        assembly_run_id=assembly_run.id,
        session=session
    )
    
    # Link snapshot to assembly run
    assembly_run.finished_good_snapshot_id = fg_snapshot["id"]
    
    # Consume components using snapshot data (not live definitions)
    for component in fg_snapshot["definition_data"]["components"]:
        if component["component_type"] == "finished_unit":
            consume_finished_unit_from_snapshot(
                component["finished_unit_snapshot_id"],
                component["component_quantity"] * quantity_assembled,
                session
            )
        # ... handle other component types
    
    return assembly_run.id
```

**Success criteria:**
- [ ] AssemblyRun.finished_good_snapshot_id FK added (non-nullable)
- [ ] Snapshot created before component consumption
- [ ] Component consumption uses snapshot data
- [ ] Live FinishedGood definition changes don't affect assembly
- [ ] Snapshot linked via assembly_run_id

---

### FR-7: MaterialUnit Snapshot Support (Conditional)

**What it must do:**
- If MaterialUnit model exists: create MaterialUnitSnapshot model
- Provide `create_material_unit_snapshot()` primitive in material_service
- Capture material metadata: slug, name, product info, quantity specifications
- Follow same pattern as FinishedUnitSnapshot (mirrored table + JSON)
- FinishedGood snapshot orchestration calls material snapshot primitive

**Pattern reference:** Copy FinishedUnitSnapshot pattern exactly for MaterialUnit

**Note:** If MaterialUnit model doesn't exist yet, store material component data in FinishedGood snapshot as placeholder (material_id reference only, no nested snapshot).

**Success criteria:**
- [ ] MaterialUnitSnapshot model exists (if MaterialUnit exists)
- [ ] create_material_unit_snapshot() primitive in material_service
- [ ] FinishedGood snapshots reference material_unit_snapshot_id when available
- [ ] Graceful handling if MaterialUnit not yet implemented

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Package snapshots (Tier 3 - deferred to future phase)
- ❌ Snapshot backfilling for existing AssemblyRuns (no production data exists)
- ❌ Snapshot versioning or change tracking (snapshots are immutable)
- ❌ Snapshot deletion (CASCADE with assembly_run deletion only)
- ❌ Snapshot comparison or diff functionality
- ❌ UI for viewing snapshot history (future enhancement)
- ❌ Ingredient/Material snapshots (separate feature, lower priority per research)

---

## Success Criteria

**Complete when:**

### Data Models
- [ ] FinishedUnitSnapshot model created with JSON definition_data
- [ ] FinishedGoodSnapshot model created with JSON definition_data
- [ ] MaterialUnitSnapshot model created (if MaterialUnit exists)
- [ ] AssemblyRun.finished_good_snapshot_id FK added (non-nullable)
- [ ] Database migrations successful
- [ ] All FKs use correct cascade behavior

### Service Layer - FinishedUnit
- [ ] finished_unit_service.create_finished_unit_snapshot() exists
- [ ] Session parameter follows pattern (session=None, wrapper/impl)
- [ ] Snapshot captures all FinishedUnit fields
- [ ] Returns snapshot dict with id and definition_data
- [ ] Eager loads recipe relationship before snapshot

### Service Layer - FinishedGood
- [ ] finished_good_service.create_finished_good_snapshot() exists
- [ ] Recursive snapshot creation works for nested FinishedGoods
- [ ] Circular reference detection prevents infinite loops
- [ ] Maximum depth enforcement (10 levels)
- [ ] Component snapshots orchestrated correctly
- [ ] All component types handled (FinishedUnit, FinishedGood, MaterialUnit)

### Service Layer - Planning
- [ ] Planning service orchestrates snapshot creation
- [ ] PlanningSnapshot container created with event linkage
- [ ] Recipe snapshots created for production targets
- [ ] FinishedGood snapshots created for assembly targets
- [ ] All snapshots created in single transaction
- [ ] Event targets store snapshot IDs

### Service Layer - Assembly
- [ ] Assembly service creates snapshot before consumption
- [ ] AssemblyRun references finished_good_snapshot_id
- [ ] Component consumption uses snapshot data
- [ ] Live definition changes don't affect assembly

### Quality
- [ ] All primitives have unit tests
- [ ] Recursive snapshot creation tested (3+ levels deep)
- [ ] Circular reference detection tested
- [ ] Maximum depth limit tested
- [ ] Transaction rollback tested (snapshot creation failure)
- [ ] Pattern consistency with RecipeSnapshot verified
- [ ] Error messages clear and actionable

---

## Architecture Principles

### Pattern A: Catalog Service Ownership + Mirrored Tables

**Catalog services own snapshot creation:**
- finished_unit_service provides create_finished_unit_snapshot()
- finished_good_service provides create_finished_good_snapshot()
- material_service provides create_material_unit_snapshot()
- Planning/Assembly services orchestrate but don't own snapshot logic

**Mirrored table pattern:**
- Each snapshot model mirrors structure of catalog model
- JSON field provides flexibility for schema evolution
- Structured FKs for query performance and referential integrity
- Metadata fields: snapshot_date, snapshot_type, is_backfilled

### Recursive Snapshot Orchestration

**Component snapshot creation:**
- FinishedGood snapshot creates FinishedUnit snapshots for components
- Nested FinishedGood triggers recursive snapshot creation
- MaterialUnit snapshot created if available
- All snapshots share transaction boundary

**Circular reference prevention:**
- Visited set tracks FinishedGood IDs in current hierarchy
- Depth counter enforces 10-level maximum
- Error raised immediately on circular reference detection

### Immutability and Isolation

**Snapshot immutability:**
- Snapshots never modified after creation
- Live definition changes don't affect snapshots
- Snapshots deleted only via CASCADE (AssemblyRun deletion)

**Definition isolation:**
- Planning references snapshots created at plan time
- Assembly references snapshots created at assembly time
- Live catalog changes don't affect planned/historical operations

### Pattern Matching

**FinishedUnit/FinishedGood snapshots MUST match RecipeSnapshot exactly:**
- Same session management pattern (session=None parameter)
- Same wrapper/impl structure
- Same JSON + structured field approach
- Same eager loading before snapshot
- Same error handling patterns
- Same return value structure (dict with id and data)

---

## Constitutional Compliance

✅ **Principle II: Definition vs Instantiation Separation**
- FinishedUnit/FinishedGood are catalog definitions (mutable)
- Snapshots capture definition state at planning/assembly time (immutable)
- AssemblyRun references snapshots, not live definitions
- Historical assemblies preserved even if definitions change/deleted

✅ **Principle V: Layered Architecture & Service Boundaries**
- Catalog services own snapshot creation (finished_unit_service, finished_good_service)
- Planning service orchestrates but doesn't own snapshot logic
- Assembly service consumes snapshots but doesn't create them directly
- No service dictates another service's implementation

✅ **Principle VIII: Session Management**
- All snapshot operations accept session=None parameter
- Wrapper/impl pattern for transaction management
- Recursive snapshots share transaction boundary
- Session passed through all nested snapshot calls

✅ **Pattern Consistency**
- FinishedGoods snapshots match RecipeSnapshot pattern exactly
- Universal Pattern A architecture applied consistently
- Service primitive naming follows convention (create_X_snapshot)
- Error handling patterns consistent across services

---

## Risk Considerations

**Risk: Nested FinishedGood complexity exceeds recursion limits**
- Deep hierarchies (5+ levels) could hit practical limits
- Mitigation: Maximum depth of 10 enforced, error raised if exceeded
- User guidance to avoid excessive nesting in FinishedGood design

**Risk: Transaction size for complex hierarchies**
- Large FinishedGood with many nested components creates many snapshots in one transaction
- Mitigation: Depth limit constrains transaction size, planning phase identifies issues
- Database timeout settings may need review for complex assemblies

**Risk: MaterialUnit model not yet implemented**
- FinishedGood snapshots reference MaterialUnit components
- Mitigation: Conditional handling - create MaterialUnit snapshot if model exists, store placeholder data otherwise
- Planning phase checks MaterialUnit implementation status

**Risk: Existing AssemblyRuns without snapshots**
- Adding non-nullable FK breaks existing records
- Mitigation: User confirmed no production data exists, immature codebase
- If discovered: migration script creates backfilled snapshots with is_backfilled=True

**Risk: Circular reference in existing FinishedGood data**
- Production data may have circular references
- Mitigation: Planning phase audits existing FinishedGood definitions
- Validation added to prevent new circular references in catalog creation

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study RecipeSnapshot model → copy structure for FinishedUnit/FinishedGood snapshots
- Study recipe_snapshot_service.create_recipe_snapshot() → copy session pattern and eager loading
- Study batch_production_service → understand snapshot orchestration timing
- Study recipe component validation → apply circular reference detection to snapshots
- Study instantiation_pattern_findings.md → understand recursive snapshot architecture

**Key Patterns to Copy:**
- RecipeSnapshot model structure → FinishedUnitSnapshot/FinishedGoodSnapshot models (exact match)
- recipe_snapshot_service session management → finished_unit/finished_good snapshot services
- batch_production_service orchestration → planning/assembly snapshot orchestration
- Recipe circular reference validation → FinishedGood snapshot circular reference detection

**Focus Areas:**
- Session management: All snapshots in hierarchy share session for atomicity
- Eager loading: Load all relationships before snapshot creation (avoid lazy load issues)
- Error messaging: Circular reference errors must indicate component causing loop
- Transaction boundaries: Single transaction for entire snapshot tree (all-or-nothing)
- Pattern consistency: Match RecipeSnapshot implementation exactly

**Data Migration Consideration:**
- User confirmed no production data exists (immature codebase)
- AssemblyRun.finished_good_snapshot_id can be non-nullable from start
- No backfill scripts needed
- If production data discovered: add is_backfilled flag and backfill script

**Testing Strategy:**
- Unit test each snapshot service primitive in isolation
- Integration test recursive snapshot creation (3+ levels)
- Test circular reference detection with complex hierarchies
- Test transaction rollback on snapshot creation failure
- Test planning orchestration end-to-end
- Test assembly integration with snapshot consumption
- Performance test: large FinishedGood with 20+ components

**MaterialUnit Integration:**
- Planning phase checks if MaterialUnit model exists
- If yes: implement MaterialUnitSnapshot following same pattern
- If no: store material_id placeholder in FinishedGood snapshot
- Future proof: structure allows adding MaterialUnit snapshots later

**Database Schema Notes:**
- FinishedUnitSnapshot.definition_data: JSON field, NOT TEXT
- FinishedGoodSnapshot.definition_data: JSON field, NOT TEXT
- AssemblyRun.finished_good_snapshot_id: FK with RESTRICT on delete (snapshot keeps assembly)
- Planning/Assembly FK: CASCADE on delete (snapshots deleted with container)

---

**END OF SPECIFICATION**
