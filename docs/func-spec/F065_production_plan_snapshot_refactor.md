# F065: ProductionPlanSnapshot Architecture Refactor

**Version**: 1.0  
**Priority**: HIGH (P0 - Architectural Debt)  
**Type**: Architecture Refactoring  
**Status**: Draft  
**Created**: 2025-01-24

---

## Executive Summary

Current architectural problem in ProductionPlanSnapshot:
- ❌ ProductionPlanSnapshot is a calculation cache, NOT true definition/instantiation separation
- ❌ Does NOT capture definition state at planning time
- ❌ Does NOT make definitions immutable for the event
- ❌ References live definitions in calculation results (violates immutability principle)
- ❌ Staleness detection compensates for missing snapshot architecture

This spec refactors ProductionPlanSnapshot from a calculation cache into a true snapshot orchestration container that references immutable definition snapshots (RecipeSnapshot, FinishedGoodSnapshot) created at planning time, completing the definition/instantiation separation for event planning.

---

## Problem Statement

**Current State (BROKEN ARCHITECTURE):**
```
ProductionPlanSnapshot (Calculation Cache - Pattern C)
├─ ❌ Stores calculation_results (JSON blob)
├─ ❌ Tracks staleness (requirements_updated_at, recipes_updated_at)
├─ ❌ References live definitions in results
├─ ❌ Does NOT capture definition state
└─ ❌ Recalculates when definitions change (cache invalidation)

Event Planning Workflow
├─ ✅ Calculate recipe batches from event requirements
├─ ❌ Store calculations in ProductionPlanSnapshot (cache)
├─ ❌ No RecipeSnapshot creation during planning
├─ ❌ No FinishedGoodSnapshot creation during planning
└─ ❌ Plan references live definitions (can change)

Production/Assembly Execution
├─ ✅ RecipeSnapshot created at ProductionRun time
├─ ✅ FinishedGoodSnapshot created at AssemblyRun time (F064 complete)
└─ ❌ Planning snapshots disconnected from execution snapshots
```

**Target State (CORRECT ARCHITECTURE):**
```
ProductionPlanSnapshot (Snapshot Container - Pattern A)
├─ ✅ event_id reference
├─ ✅ created_at timestamp
├─ ✅ References to RecipeSnapshots (via production targets)
├─ ✅ References to FinishedGoodSnapshots (via assembly targets)
├─ ❌ NO calculation_results (removed)
├─ ❌ NO staleness tracking (removed)
└─ ✅ Immutable - definitions captured at planning time

Event Planning Workflow
├─ ✅ Calculate recipe batches from event requirements
├─ ✅ Create RecipeSnapshot for each production target
├─ ✅ Create FinishedGoodSnapshot for each assembly target (F064)
├─ ✅ Store snapshot IDs in targets
├─ ✅ Create ProductionPlanSnapshot container
├─ ✅ Plan references snapshots (immutable)
└─ ✅ Definition changes don't affect planned events

Production/Assembly Execution
├─ ✅ Use RecipeSnapshot from planning (same snapshot)
├─ ✅ Use FinishedGoodSnapshot from planning (same snapshot)
├─ ✅ ProductionRun references recipe_snapshot_id
├─ ✅ AssemblyRun references finished_good_snapshot_id
├─ ✅ Planning and execution use same immutable snapshots
└─ ✅ Complete definition/instantiation separation
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **ProductionPlanSnapshot Model (Current - To Refactor)**
   - Find `/src/models/production_plan_snapshot.py`
   - Study calculation_results structure (JSON blob to remove)
   - Note staleness tracking fields (to remove)
   - Understand current event_id relationship

2. **Planning Service (Current - To Refactor)**
   - Find `/src/services/planning/planning_service.py`
   - Study calculation workflow and snapshot creation
   - Note how calculation_results are stored
   - Understand staleness detection logic

3. **RecipeSnapshot Pattern (Reference)**
   - Find `/src/models/recipe_snapshot.py`
   - Study snapshot creation at production time
   - Note recipe_snapshot_id FK on ProductionRun
   - Understand immutability pattern

4. **FinishedGoodSnapshot Pattern (Reference - F064 Complete)**
   - Find `/src/models/finished_good_snapshot.py`
   - Study snapshot creation at assembly time (F064)
   - Note finished_good_snapshot_id FK on AssemblyRun
   - Understand recursive snapshot pattern

5. **Recipe Snapshot Service (Reference)**
   - Find `/src/services/recipe_snapshot_service.py`
   - Study create_recipe_snapshot() signature
   - Note session management pattern
   - Understand snapshot data capture

6. **FinishedGood Snapshot Service (Reference - F064 Complete)**
   - Find `/src/services/finished_good_service.py`
   - Study create_finished_good_snapshot() implementation (F064)
   - Note recursive snapshot creation
   - Understand component snapshot orchestration

7. **Batch Production Service (Orchestration Pattern)**
   - Find `/src/services/batch_production_service.py`
   - Study how RecipeSnapshot is created BEFORE production
   - Note snapshot_id storage on ProductionRun
   - Understand snapshot timing (before inventory consumption)

8. **Instantiation Pattern Research**
   - Find `/docs/research/instantiation_pattern_findings.md`
   - Study Section 1.4 (ProductionPlanSnapshot architectural problem)
   - Review Pattern A recommendation (Catalog Service Ownership)
   - Note planning snapshot container pattern

9. **Event and Target Models**
   - Find `/src/models/event.py`
   - Find `/src/models/production_target.py` (or equivalent)
   - Study event → targets relationship
   - Note where snapshot_id references should be added

10. **Constitution Principles**
    - Find `/.kittify/memory/constitution.md`
    - Study Principle II: Definition vs Instantiation Separation
    - Understand immutability requirements

---

## Requirements Reference

This specification addresses architectural issues identified in:
- **instantiation_pattern_findings.md** Section 1.4: ProductionPlanSnapshot architectural problem
- **Constitutional Principle II**: Definition vs Instantiation Separation
- **F064 Complete**: FinishedGoodSnapshot now available for assembly targets

---

## Functional Requirements

### FR-1: Remove Calculation Cache from ProductionPlanSnapshot

**What it must do:**
- Remove calculation_results JSON field from ProductionPlanSnapshot model
- Remove staleness tracking fields (requirements_updated_at, recipes_updated_at, bundles_updated_at, is_stale, stale_reason)
- Keep event_id FK and created_at timestamp
- ProductionPlanSnapshot becomes a lightweight container, not a cache
- Database migration removes obsolete fields

**Pattern reference:** Study RecipeSnapshot - it stores snapshot_id references, not calculation results

**Fields to REMOVE:**
```python
# DELETE these fields
calculation_results = JSON(nullable=False)  # DELETE
requirements_updated_at = DateTime(nullable=False)  # DELETE
recipes_updated_at = DateTime(nullable=False)  # DELETE
bundles_updated_at = DateTime(nullable=False)  # DELETE
is_stale = Boolean(default=False, nullable=False)  # DELETE
stale_reason = String(200, nullable=True)  # DELETE
```

**Fields to KEEP:**
```python
# KEEP these fields
id = PrimaryKey
event_id = ForeignKey("events.id", ondelete="CASCADE")
created_at = DateTime(nullable=False)
```

**Success criteria:**
- [ ] calculation_results field removed from model
- [ ] Staleness tracking fields removed
- [ ] Database migration successful
- [ ] ProductionPlanSnapshot is now a simple container

---

### FR-2: Add RecipeSnapshot References to Production Targets

**What it must do:**
- Add recipe_snapshot_id FK to ProductionTarget model (or equivalent event target entity)
- FK references recipe_snapshots table
- FK nullable=True initially for backward compatibility
- Production target stores reference to RecipeSnapshot created during planning
- Planning service populates recipe_snapshot_id when creating snapshots

**Pattern reference:** Study how ProductionRun stores recipe_snapshot_id, apply to ProductionTarget

**Model update:**
```python
class ProductionTarget(BaseModel):
    event_id = ForeignKey("events.id")
    recipe_id = ForeignKey("recipes.id")  # Definition reference (existing)
    quantity_needed = Integer  # (existing)
    
    # NEW: Snapshot reference created at planning time
    recipe_snapshot_id = ForeignKey(
        "recipe_snapshots.id",
        nullable=True,  # Backward compatibility
        ondelete="RESTRICT"  # Keep snapshot if target deleted
    )
```

**Success criteria:**
- [ ] recipe_snapshot_id FK added to ProductionTarget
- [ ] FK properly indexed
- [ ] Migration successful
- [ ] Nullable for backward compatibility

---

### FR-3: Add FinishedGoodSnapshot References to Assembly Targets

**What it must do:**
- Add finished_good_snapshot_id FK to AssemblyTarget model (or equivalent)
- FK references finished_good_snapshots table (F064 complete)
- FK nullable=True initially for backward compatibility
- Assembly target stores reference to FinishedGoodSnapshot created during planning
- Planning service populates finished_good_snapshot_id when creating snapshots

**Pattern reference:** Study how AssemblyRun stores finished_good_snapshot_id (F064), apply to AssemblyTarget

**Model update:**
```python
class AssemblyTarget(BaseModel):
    event_id = ForeignKey("events.id")
    finished_good_id = ForeignKey("finished_goods.id")  # Definition reference
    quantity_needed = Integer
    
    # NEW: Snapshot reference created at planning time (F064 complete)
    finished_good_snapshot_id = ForeignKey(
        "finished_good_snapshots.id",
        nullable=True,  # Backward compatibility
        ondelete="RESTRICT"
    )
```

**Success criteria:**
- [ ] finished_good_snapshot_id FK added to AssemblyTarget
- [ ] FK properly indexed
- [ ] Migration successful
- [ ] Nullable for backward compatibility

---

### FR-4: Planning Service Creates Definition Snapshots

**What it must do:**
- Planning service creates RecipeSnapshot for each production target during event planning
- Planning service creates FinishedGoodSnapshot for each assembly target (F064)
- Call recipe_snapshot_service.create_recipe_snapshot() for each recipe
- Call finished_good_service.create_finished_good_snapshot() for each finished good
- Pass planning_snapshot_id to link snapshots to plan (if supported by snapshot models)
- Store snapshot IDs on targets (recipe_snapshot_id, finished_good_snapshot_id)
- All snapshots created in single transaction
- Snapshot creation happens BEFORE calculation (captures state before changes)

**Pattern reference:** Study batch_production_service snapshot creation, apply to planning phase

**Planning workflow update:**
```python
def create_event_plan(event_id, session):
    event = session.get(Event, event_id)
    
    # Create planning snapshot container
    planning_snapshot = ProductionPlanSnapshot(
        event_id=event_id,
        created_at=utc_now()
    )
    session.add(planning_snapshot)
    session.flush()
    
    # Create RecipeSnapshot for each production target
    for target in event.production_targets:
        recipe_snapshot = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=target.recipe_id,
            scale_factor=1.0,  # Base scale, targets have quantity_needed
            production_run_id=None,  # Planning snapshot, not production
            session=session
        )
        target.recipe_snapshot_id = recipe_snapshot["id"]
    
    # Create FinishedGoodSnapshot for each assembly target (F064)
    for target in event.assembly_targets:
        fg_snapshot = finished_good_service.create_finished_good_snapshot(
            finished_good_id=target.finished_good_id,
            recursive=True,
            assembly_run_id=None,  # Planning snapshot, not assembly
            session=session
        )
        target.finished_good_snapshot_id = fg_snapshot["id"]
    
    # Calculate requirements (still needed for display/shopping list)
    # But calculations NOT stored in ProductionPlanSnapshot
    calculations = calculate_batch_requirements(event, session)
    
    return {
        "planning_snapshot_id": planning_snapshot.id,
        "recipe_snapshots_created": len(event.production_targets),
        "finished_good_snapshots_created": len(event.assembly_targets),
        "calculations": calculations  # Returned, not stored
    }
```

**Success criteria:**
- [ ] Planning service creates RecipeSnapshot for each production target
- [ ] Planning service creates FinishedGoodSnapshot for each assembly target
- [ ] recipe_snapshot_id stored on ProductionTarget
- [ ] finished_good_snapshot_id stored on AssemblyTarget
- [ ] All snapshots created in single transaction
- [ ] Calculation results returned but NOT stored in ProductionPlanSnapshot

---

### FR-5: Remove Staleness Detection Logic

**What it must do:**
- Remove all staleness detection code from planning service
- Remove methods that check if snapshots are stale
- Remove methods that update staleness flags
- Snapshots are immutable - no staleness concept needed
- If user changes definitions, they create a NEW plan (new snapshots)

**Pattern reference:** RecipeSnapshot and FinishedGoodSnapshot have no staleness tracking - they're immutable

**Code to REMOVE:**
```python
# DELETE these methods/logic
def check_snapshot_staleness(planning_snapshot_id)  # DELETE
def mark_snapshot_stale(planning_snapshot_id, reason)  # DELETE
def get_stale_snapshots()  # DELETE
# Any code checking is_stale field  # DELETE
```

**Success criteria:**
- [ ] Staleness detection methods removed
- [ ] No code references is_stale field
- [ ] Planning service simplified
- [ ] Immutability principle enforced

---

### FR-6: Production/Assembly Services Use Planning Snapshots

**What it must do:**
- When ProductionRun is created from a planned event, use the RecipeSnapshot already created during planning
- When AssemblyRun is created from a planned event, use the FinishedGoodSnapshot already created during planning (F064)
- Check if target has snapshot_id
- If yes: reference that snapshot (don't create new one)
- If no: create snapshot at production/assembly time (backward compatibility)
- Eventually all ProductionRuns/AssemblyRuns reference snapshots created at planning time

**Pattern reference:** Planning and production/assembly share same snapshots (immutability)

**Production workflow update:**
```python
def record_batch_production(recipe_id, quantity, event_id, session):
    # Check if this production is for a planned event target
    snapshot_id = None
    if event_id:
        target = get_production_target(event_id, recipe_id, session)
        if target and target.recipe_snapshot_id:
            # Use snapshot created during planning
            snapshot_id = target.recipe_snapshot_id
    
    # If no planning snapshot, create one now (backward compatibility)
    if not snapshot_id:
        production_run = ProductionRun(...)
        session.add(production_run)
        session.flush()
        
        recipe_snapshot = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=recipe_id,
            scale_factor=1.0,
            production_run_id=production_run.id,
            session=session
        )
        snapshot_id = recipe_snapshot["id"]
    
    # Production uses snapshot (whether from planning or created now)
    production_run.recipe_snapshot_id = snapshot_id
    # ... rest of production logic
```

**Assembly workflow update:**
```python
def record_assembly(finished_good_id, quantity, event_id, session):
    # Check if this assembly is for a planned event target
    snapshot_id = None
    if event_id:
        target = get_assembly_target(event_id, finished_good_id, session)
        if target and target.finished_good_snapshot_id:
            # Use snapshot created during planning
            snapshot_id = target.finished_good_snapshot_id
    
    # If no planning snapshot, create one now (F064 pattern)
    if not snapshot_id:
        assembly_run = AssemblyRun(...)
        session.add(assembly_run)
        session.flush()
        
        fg_snapshot = finished_good_service.create_finished_good_snapshot(
            finished_good_id=finished_good_id,
            recursive=True,
            assembly_run_id=assembly_run.id,
            session=session
        )
        snapshot_id = fg_snapshot["id"]
    
    # Assembly uses snapshot (whether from planning or created now)
    assembly_run.finished_good_snapshot_id = snapshot_id
    # ... rest of assembly logic
```

**Success criteria:**
- [ ] Production checks for planning snapshot first
- [ ] Assembly checks for planning snapshot first
- [ ] Planning snapshots reused if available
- [ ] Backward compatibility maintained (create snapshot if missing)
- [ ] Planning and production/assembly share same immutable snapshots

---

### FR-7: Update RecipeSnapshot and FinishedGoodSnapshot Models for Planning Context

**What it must do:**
- RecipeSnapshot currently requires production_run_id
- Make production_run_id nullable to support planning snapshots
- Add optional planning_snapshot_id FK to ProductionPlanSnapshot
- FinishedGoodSnapshot (F064) may already support planning_snapshot_id
- Snapshot can be linked to production/assembly run OR planning snapshot OR both

**Pattern reference:** Study FinishedGoodSnapshot (F064) for multiple context FKs

**RecipeSnapshot model update:**
```python
class RecipeSnapshot(BaseModel):
    recipe_id = ForeignKey("recipes.id", ondelete="RESTRICT")
    
    # Context FKs - at least one must be set
    production_run_id = ForeignKey(
        "production_runs.id",
        ondelete="CASCADE",
        nullable=True  # Changed from False
    )
    planning_snapshot_id = ForeignKey(
        "production_plan_snapshots.id",
        ondelete="CASCADE",
        nullable=True  # NEW
    )
    
    # ... rest of model unchanged
```

**FinishedGoodSnapshot verification (F064):**
- Check if planning_snapshot_id already exists from F064
- If not, add planning_snapshot_id FK
- Ensure assembly_run_id is nullable for planning context

**Success criteria:**
- [ ] production_run_id now nullable on RecipeSnapshot
- [ ] planning_snapshot_id FK added to RecipeSnapshot
- [ ] FinishedGoodSnapshot supports planning_snapshot_id (verify F064)
- [ ] Migration successful
- [ ] Snapshots can be created for planning OR production/assembly

---

### FR-8: Deprecate Calculation Storage in UI

**What it must do:**
- UI currently expects calculation_results from ProductionPlanSnapshot
- Update UI to recalculate on-demand from snapshots
- Planning view calculates requirements from snapshot_id references
- Remove UI code that displays staleness warnings
- Shopping list generated from current calculation (not cached)

**Pattern reference:** UI queries snapshots and calculates, doesn't retrieve cached calculations

**UI update:**
```python
def display_event_plan(event_id):
    event = get_event(event_id)
    
    # Recalculate from snapshots (not from cache)
    calculations = calculate_requirements_from_snapshots(event)
    
    # Display calculations (freshly computed)
    display_batch_requirements(calculations)
    display_shopping_list(calculations)
    
    # No staleness warnings (snapshots are immutable)
```

**Success criteria:**
- [ ] UI recalculates requirements on-demand
- [ ] No UI code reads calculation_results field
- [ ] Staleness warning UI removed
- [ ] Shopping list generated from fresh calculation

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ InventorySnapshot improvements (eliminated - F066 not needed)
- ❌ Material snapshots (handled by consumption records)
- ❌ Changing event planning calculation logic (just where results are stored)
- ❌ UI redesign (just remove calculation cache dependencies)
- ❌ Performance optimization of recalculation (acceptable to recalculate on-demand)

---

## Success Criteria

**Complete when:**

### Data Model
- [ ] calculation_results field removed from ProductionPlanSnapshot
- [ ] Staleness fields removed (requirements_updated_at, recipes_updated_at, etc.)
- [ ] recipe_snapshot_id FK added to ProductionTarget
- [ ] finished_good_snapshot_id FK added to AssemblyTarget
- [ ] production_run_id nullable on RecipeSnapshot
- [ ] planning_snapshot_id FK added to RecipeSnapshot
- [ ] FinishedGoodSnapshot supports planning_snapshot_id (verify F064)
- [ ] Database migrations successful

### Service Layer - Planning
- [ ] Planning service creates RecipeSnapshot for each production target
- [ ] Planning service creates FinishedGoodSnapshot for each assembly target
- [ ] recipe_snapshot_id stored on ProductionTarget
- [ ] finished_good_snapshot_id stored on AssemblyTarget
- [ ] Staleness detection code removed
- [ ] Calculation results returned but not stored
- [ ] All snapshots created in single transaction

### Service Layer - Production/Assembly
- [ ] Production checks for planning snapshot before creating new one
- [ ] Assembly checks for planning snapshot before creating new one
- [ ] Planning snapshots reused when available
- [ ] Backward compatibility maintained (create if missing)
- [ ] ProductionRun/AssemblyRun reference correct snapshot (planning or new)

### UI Layer
- [ ] UI recalculates requirements on-demand from snapshots
- [ ] calculation_results field no longer referenced
- [ ] Staleness warnings removed
- [ ] Shopping list generated from fresh calculation

### Quality
- [ ] Unit tests for snapshot creation during planning
- [ ] Integration tests for planning → production/assembly snapshot reuse
- [ ] Migration tested (forward and backward)
- [ ] Performance acceptable for on-demand recalculation
- [ ] Pattern consistency with RecipeSnapshot and FinishedGoodSnapshot verified

---

## Architecture Principles

### ProductionPlanSnapshot as Container (Not Cache)

**Lightweight container:**
- Stores event_id and created_at
- References RecipeSnapshots via ProductionTargets
- References FinishedGoodSnapshots via AssemblyTargets (F064)
- NO calculation results stored
- NO staleness tracking needed

**Immutability:**
- Snapshots created at planning time are immutable
- Definition changes require NEW plan with NEW snapshots
- No concept of "stale" snapshots - they're historical records

### Planning and Production/Assembly Share Snapshots

**Single source of truth:**
- RecipeSnapshot created during planning
- FinishedGoodSnapshot created during planning (F064)
- Same snapshots referenced by ProductionRun/AssemblyRun
- Definitions captured once, used by both planning and execution
- Complete definition/instantiation separation

### Pattern A Architecture

**Catalog Service Ownership:**
- recipe_snapshot_service owns RecipeSnapshot creation
- finished_good_service owns FinishedGoodSnapshot creation (F064)
- Planning service orchestrates (calls primitives)
- Production/Assembly services orchestrate (calls primitives or reuses existing)

---

## Constitutional Compliance

✅ **Principle II: Definition vs Instantiation Separation**
- Recipes and FinishedGoods are catalog definitions (mutable)
- RecipeSnapshots and FinishedGoodSnapshots capture state at planning time (immutable)
- Planning references snapshots, not live definitions
- Production/Assembly reference same snapshots from planning
- Definition changes don't affect planned events

✅ **Principle V: Service Boundaries**
- recipe_snapshot_service owns RecipeSnapshot creation
- finished_good_service owns FinishedGoodSnapshot creation (F064)
- Planning service orchestrates snapshot creation
- Production/Assembly services consume snapshots (planning or creates new)
- No service dictates another service's implementation

✅ **Principle VIII: Session Management**
- All snapshot creation in single transaction
- Session passed through planning workflow
- Atomic snapshot creation for entire event plan

---

## Risk Considerations

**Risk: Existing events have calculation_results cached**
- Removing field loses cached calculations
- Mitigation: UI recalculates on-demand from definitions/snapshots
- Data migration exports calculations if users need historical data

**Risk: Performance impact of on-demand recalculation**
- Current caching avoids recalculation
- Mitigation: Calculation is fast (<100ms for typical event), acceptable to recalculate on view
- Future optimization: client-side caching if needed

**Risk: Backward compatibility for events without snapshots**
- Old events have no snapshot_id on targets
- Mitigation: Production/Assembly service creates snapshot at execution time if missing
- Graceful degradation - old events still work

**Risk: RecipeSnapshot and FinishedGoodSnapshot model changes affect existing code**
- Making production_run_id/assembly_run_id nullable changes assumptions
- Mitigation: Planning phase audits all snapshot usage
- Validation ensures at least one context FK is set

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study RecipeSnapshot model → understand immutability pattern
- Study FinishedGoodSnapshot model (F064) → understand recursive pattern
- Study recipe_snapshot_service → understand creation primitive
- Study finished_good_service (F064) → understand snapshot orchestration
- Study batch_production_service → understand snapshot timing
- Study planning service current calculation logic → preserve calculation, change storage

**Key Patterns to Copy:**
- RecipeSnapshot immutability → apply to ProductionPlanSnapshot refactor
- FinishedGoodSnapshot immutability (F064) → planning integration
- batch_production_service snapshot timing → apply to planning phase
- ProductionRun.recipe_snapshot_id → apply to ProductionTarget.recipe_snapshot_id
- AssemblyRun.finished_good_snapshot_id (F064) → apply to AssemblyTarget.finished_good_snapshot_id

**Focus Areas:**
- Data migration: Remove calculation_results safely
- Backward compatibility: Old events without snapshots still work
- UI updates: Recalculate instead of read cache
- Transaction boundaries: All planning snapshots in one transaction
- F064 integration: Leverage completed FinishedGoodSnapshot implementation

**Migration Strategy:**
1. Add recipe_snapshot_id to ProductionTarget (nullable)
2. Add finished_good_snapshot_id to AssemblyTarget (nullable)
3. Make production_run_id nullable on RecipeSnapshot
4. Add planning_snapshot_id to RecipeSnapshot
5. Verify FinishedGoodSnapshot supports planning_snapshot_id (F064)
6. Deploy code that creates snapshots during planning
7. Remove calculation_results field (data loss acceptable - recalculate)
8. Remove staleness tracking fields
9. Remove staleness detection code

**Testing Strategy:**
- Unit test planning service snapshot creation
- Integration test planning → production/assembly snapshot reuse
- Test backward compatibility (events without snapshots)
- Test on-demand calculation performance
- Test migration (forward only, data loss acceptable)

**UI Migration:**
- Identify all uses of calculation_results
- Replace with on-demand calculation calls
- Remove staleness warning components
- Test shopping list generation

---

**END OF SPECIFICATION**
