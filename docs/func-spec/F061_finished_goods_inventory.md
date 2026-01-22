# F0XX: Finished Goods Inventory Service Layer

**Version**: 3.0
**Priority**: MEDIUM
**Type**: Service Layer

---

## Executive Summary

Finished goods inventory tracking exists in the data model (`inventory_count` fields on FinishedUnit and FinishedGood), but lacks service layer support for validation, queries, and integration with production/assembly workflows. Production runs add inventory without service coordination, assembly runs may fail due to insufficient components, and there's no way to query current stock levels.

Current gaps:
- ❌ No service layer for inventory queries (current stock, low stock alerts)
- ❌ No consumption validation (can consume more than available)
- ❌ No session-aware inventory operations (violates F060 session ownership)
- ❌ Model methods contain business logic (should be in service layer)
- ❌ Production/assembly lack inventory primitives
- ❌ No inventory value calculations
- ❌ No export/import coordination for inventory state

This spec adds finished goods inventory service with session-aware primitives, enabling validated inventory operations and preparing for Phase 3 UI implementation.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Data Model (Phase 1)
├─ ✅ FinishedUnit.inventory_count field exists
├─ ✅ FinishedGood.inventory_count field exists
├─ ⚠️ Model methods contain business logic (should be in service)
│   ├─ is_available() - should be service method
│   ├─ update_inventory() - should be service method
│   └─ can_assemble() - should be service method
└─ ✅ Database constraints: CHECK (inventory_count >= 0)

Service Layer
├─ ❌ No inventory query service
├─ ❌ No consumption validation service
├─ ❌ No session-aware inventory operations
├─ ❌ No inventory adjustment tracking
├─ ❌ No assembly feasibility primitives
└─ ❌ No inventory value calculations

Production Integration
├─ ✅ Production runs create finished units
└─ ❌ No service-coordinated inventory updates

Assembly Integration
├─ ✅ Assembly runs consume components, create goods
├─ ❌ No pre-validation of component availability
└─ ❌ Direct model updates without service coordination

Export/Import
└─ ❌ No inventory state export/import coordination

UI Layer
└─ ❌ No inventory visibility (deferred to Phase 3)
```

**Target State (COMPLETE - Phase 2 Service Layer Only):**
```
Data Model
├─ ✅ inventory_count fields (unchanged)
├─ ✅ Database constraints (unchanged)
└─ ✅ Models as data containers only (business logic moved to service)

Service Layer
├─ ✅ finished_goods_inventory_service.py
├─ ✅ Session-aware operations (F060 compliant)
├─ ✅ get_inventory_status() - query current stock
├─ ✅ check_availability() - validate sufficient inventory
├─ ✅ validate_consumption() - prevent overconsumption
├─ ✅ adjust_inventory() - tracked inventory changes with session
├─ ✅ get_low_stock_items() - identify shortages
└─ ✅ get_total_inventory_value() - cost tracking

Production Integration
├─ ✅ adjust_inventory() primitive available (session-aware)
└─ ✅ Production service orchestrates, inventory service provides primitive

Assembly Integration
├─ ✅ check_availability() primitive available (session-aware)
├─ ✅ adjust_inventory() primitive available (session-aware)
└─ ✅ Assembly service orchestrates transaction, inventory participates

Export/Import
└─ ✅ Inventory state coordinated with export/import system

UI Layer
└─ ⏳ Deferred to Phase 3 (service layer prepares for it)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **F060 Architecture Hardening (Session Ownership Pattern)**
   - Read `docs/func-spec/F060_architecture_hardening_service_boundaries.md`
   - Study session ownership principle ("caller owns session")
   - Understand optional session parameter pattern
   - Note: ALL services must accept session, use provided session exclusively
   - This is the PRIMARY pattern to follow for all service methods

2. **Batch Production Service (Mature Session Pattern)**
   - Find `src/services/batch_production_service.py`
   - Study how session is threaded through all calls
   - Note dry-run vs commit pattern
   - Observe how FIFO consumption receives session
   - **This is the reference implementation for session discipline**

3. **Assembly Service (Session Threading)**
   - Find `src/services/assembly_service.py`
   - Study session handling in `record_assembly`
   - Note how downstream services receive session
   - Understand multi-service atomic operations

4. **Existing Models (Data Layer Only)**
   - Find `src/models/finished_unit.py`
   - Find `src/models/finished_good.py`
   - Study `inventory_count` field usage
   - Note existing methods: `is_available()`, `update_inventory()`, `can_assemble()`
   - **CRITICAL**: These model methods will be DEPRECATED in favor of service methods
   - Understand database constraints (non-negative inventory)

5. **Production Run Service (Integration Point)**
   - Find `src/services/production_run_service.py` OR `src/services/batch_production_service.py`
   - Study production completion workflow
   - Note how actual_yield is recorded
   - Understand where inventory should be updated
   - **Post-F060**: May use batch_production_service exclusively

6. **Assembly Run Service (Integration Point)**
   - Find `src/services/assembly_run_service.py`
   - Study assembly creation workflow
   - Note component consumption patterns
   - Understand where feasibility checks occur

7. **Related Service Patterns**
   - Study `src/services/inventory_service.py` (raw ingredients)
   - Note validation patterns (NOT FIFO - finished goods don't need it)
   - Study service method naming conventions
   - Note how services coordinate with export/import

8. **Export/Import Coordination**
   - Find `src/services/export_service.py`
   - Find `src/services/import_service.py`
   - Study how inventory state is exported (if at all currently)
   - Understand full backup export structure

---

## Requirements Reference

This specification implements service layer support for finished goods inventory, building on:
- **F060**: Architecture Hardening - Session ownership pattern (MUST follow)
- **F049**: Import/Export System - Export/import coordination
- **Constitution Principle I**: User-Centric Design & Workflow Validation
- **Constitution Principle II**: Data Integrity & FIFO Accuracy (finished goods: simple counting, NOT FIFO)
- **Constitution Principle V**: Layered Architecture Discipline

Key principles:
- Session ownership: Caller owns session, services accept and use it
- Non-negative inventory constraint (enforced at model and service layers)
- Consumption validation before inventory decrease
- Service provides primitives only; other services orchestrate workflows
- Simple inventory counting (FIFO not required for finished goods)

---

## Functional Requirements

### FR-0: Session-Aware Service Architecture (F060 Compliance)

**What it must do:**
- ALL service methods accept optional `session` parameter
- When session provided, use it exclusively (no internal session_scope)
- When session NOT provided, open own session (backward compatibility)
- Thread session through ALL downstream service calls
- NO internal commits when session provided (caller controls transaction)

**Pattern reference:** Study `batch_production_service.record_production` for session threading discipline

**Rationale:** Post-F060, ALL services must follow session ownership pattern. This enables atomic multi-service operations and prevents partial writes.

**Success criteria:**
- [ ] All service methods accept optional `session` parameter
- [ ] When session provided, no internal session_scope used
- [ ] When session NOT provided, service opens own session
- [ ] No internal commits when session provided
- [ ] Backward compatible with callers not passing session

---

### FR-1: Inventory Status Queries

**What it must do:**
- Query current inventory levels for finished units and/or finished goods
- Filter by specific item or return all items
- Option to include/exclude zero-stock items
- Return inventory with display names, slugs, counts
- Calculate inventory values based on unit/good costs
- Accept optional session parameter for transactional queries

**Pattern reference:** Study how inventory_service.py queries raw ingredient inventory, adapt pattern for finished goods with session awareness

**Success criteria:**
- [ ] Can query all finished units inventory
- [ ] Can query all finished goods inventory
- [ ] Can query specific item by ID
- [ ] Can filter out zero-stock items
- [ ] Returns structured data with counts and values
- [ ] Accepts optional session parameter

---

### FR-2: Availability Checking

**What it must do:**
- Check if sufficient inventory exists for required quantity
- Return availability status (bool) plus current inventory
- Calculate shortage amount if insufficient
- Support both finished units and finished goods
- Accept optional session parameter for transactional checks

**Pattern reference:** Service method wraps model-level inventory_count check, adds session support and structured response

**Business rules:**
- Returns true when `inventory_count >= required_quantity`
- Returns false with shortage amount when insufficient
- Works within caller's transaction if session provided

**Success criteria:**
- [ ] Returns true when inventory sufficient
- [ ] Returns false with shortage amount when insufficient
- [ ] Works for both FinishedUnit and FinishedGood
- [ ] Provides actionable data for callers
- [ ] Accepts optional session parameter

---

### FR-3: Consumption Validation

**What it must do:**
- Validate consumption request before allowing operation
- Prevent consumption exceeding available inventory
- Return validation result (bool) and error message if invalid
- Support validation without actually consuming
- Accept optional session parameter for transactional validation

**Pattern reference:** Similar to inventory_service consumption validation for raw ingredients, with session support

**Business rules:**
- Cannot consume more than current inventory_count
- Validation must occur before any database updates
- Error messages must clearly state shortage amounts
- Validation reads current inventory_count within provided session

**Success criteria:**
- [ ] Validates before consumption allowed
- [ ] Blocks overconsumption attempts
- [ ] Provides clear error messages
- [ ] Separates validation from actual consumption
- [ ] Accepts optional session parameter

---

### FR-4: Tracked Inventory Adjustments

**What it must do:**
- Adjust inventory_count with reason tracking
- Support positive changes (production, assembly completion)
- Support negative changes (assembly consumption, spoilage, gifts)
- Validate adjustments won't create negative inventory
- Record reason and optional notes
- Accept optional session parameter (CRITICAL for atomic operations)
- Use provided session exclusively when present

**Pattern reference:** Study inventory_service.adjust_inventory() for raw ingredients; adapt with session awareness and reason tracking

**Business rules:**
- Reason must be specified: "production", "assembly", "consumption", "spoilage", "gift", "adjustment"
- Notes optional but recommended for manual adjustments
- Must validate final inventory_count >= 0
- Return previous count, new count, change amount
- When session provided, participate in caller's transaction

**Success criteria:**
- [ ] Adjusts inventory with validation
- [ ] Tracks reason for adjustment
- [ ] Prevents negative inventory
- [ ] Returns adjustment summary
- [ ] Supports both increase and decrease
- [ ] Accepts optional session parameter
- [ ] Uses provided session exclusively (no internal commits)

---

### FR-5: Low Stock Identification

**What it must do:**
- Identify items with inventory below threshold
- Default threshold configurable (e.g., 5 units)
- Filter by item type (units vs goods) or show all
- Return items with current counts
- Accept optional session parameter for transactional queries

**Pattern reference:** Simple query pattern filtering `inventory_count < threshold`, with session support

**Success criteria:**
- [ ] Returns items below threshold
- [ ] Threshold configurable via parameter
- [ ] Can filter by item type
- [ ] Useful for production planning
- [ ] Accepts optional session parameter

---

### FR-6: Inventory Value Calculation

**What it must do:**
- Calculate total value of finished goods inventory
- Aggregate finished units value (count × unit_cost)
- Aggregate finished goods value (count × total_cost)
- Return grand total inventory value
- Accept optional session parameter for transactional queries

**Pattern reference:** Simple aggregation query across inventory_count and cost fields, with session support

**Note:** If costing logic is complex (weighted average, cost layers), planning phase should verify whether a separate costing_service is needed. Simple multiplication (count × cost) can stay in inventory service.

**Success criteria:**
- [ ] Calculates finished units total value
- [ ] Calculates finished goods total value
- [ ] Returns grand total
- [ ] Handles items with zero inventory
- [ ] Accepts optional session parameter

---

### FR-7: Deprecate Model Business Logic Methods

**What it must do:**
- Identify existing model methods with business logic
- Move business logic to finished_goods_inventory_service
- Keep model methods as minimal property accessors ONLY (if kept at all)
- Update all callers to use service methods instead

**Methods to deprecate or minimize:**
- `FinishedUnit.is_available()` → `finished_goods_inventory_service.check_availability()`
- `FinishedUnit.update_inventory()` → `finished_goods_inventory_service.adjust_inventory()`
- `FinishedGood.is_available()` → `finished_goods_inventory_service.check_availability()`
- `FinishedGood.can_assemble()` → `finished_goods_inventory_service.check_availability()` (for components)

**Pattern reference:** Study F060 service layer discipline - models are data containers, services contain business logic

**Approach options (planning phase decides):**
1. Keep methods as thin wrappers calling service (backward compat)
2. Deprecate methods entirely, update all callers
3. Keep methods as simple property checks only (no service calls)

**Success criteria:**
- [ ] Business logic moved to service layer
- [ ] Model methods are minimal or removed
- [ ] All callers updated to use service methods
- [ ] No direct `inventory_count` manipulation outside service

---

### FR-8: Service Primitives for Production Integration

**What it must do:**
- Provide `adjust_inventory(session=None, ...)` primitive that production service CAN call
- Accept reason="production" for production-related adjustments
- Support positive quantity changes (adding produced items)
- Record production run context in notes if provided
- Participate in production service's transaction via session parameter

**Pattern reference:** Study how inventory_service supports purchase integration with session threading

**Service Boundary Clarity:**
- **Inventory service provides**: `adjust_inventory()` primitive
- **Production service owns**: When/how to call it, orchestrating workflow
- **Inventory service does NOT**: Dictate production workflow or timing
- **Transaction ownership**: Production service owns session, passes to inventory

**Success criteria:**
- [ ] `adjust_inventory()` supports reason="production"
- [ ] Positive quantity changes work correctly
- [ ] Notes field can store production run ID
- [ ] Method available for production service to use
- [ ] Accepts session parameter from production service

---

### FR-9: Service Primitives for Assembly Integration

**What it must do:**
- Provide `check_availability(session=None, ...)` to verify components exist
- Provide `adjust_inventory(session=None, ...)` for component consumption (negative) and good creation (positive)
- Accept session parameter for atomic multi-item adjustments
- Accept reason="assembly" for assembly-related adjustments
- Participate in assembly service's transaction

**Pattern reference:** Study assembly_run_service to understand what primitives it needs, then study batch_production session threading

**Service Boundary Clarity:**
- **Inventory service provides**: `check_availability()`, `adjust_inventory()` primitives
- **Assembly service owns**: Feasibility logic, orchestrating multi-step workflow, transaction coordination
- **Inventory service does NOT**: Implement assembly feasibility logic or orchestrate assembly steps
- **Transaction ownership**: Assembly service owns session, passes to inventory for each operation

**Business rules:**
- Multiple `adjust_inventory()` calls can be wrapped in single transaction (assembly owns session)
- Component consumption and good creation should be atomic (same transaction)

**Success criteria:**
- [ ] `check_availability()` works for finished units and goods
- [ ] `adjust_inventory()` supports reason="assembly"
- [ ] Both methods accept session parameter
- [ ] Multiple adjustments can be atomic (via shared session)
- [ ] Methods available for assembly service to use

---

### FR-10: Export/Import Coordination

**What it must do:**
- Coordinate with export service for full backup exports
- Include finished goods inventory state in exports
- Support import of inventory state during restore
- Maintain inventory counts during export/import cycle

**Pattern reference:** Study how `export_service.py` handles inventory_items export; apply to finished goods

**Export requirements:**
- Include FinishedUnit inventory counts in export
- Include FinishedGood inventory counts in export
- Use slug-based references (not IDs)
- Include in manifest with entity counts

**Import requirements:**
- Restore inventory counts during import
- Validate inventory_count >= 0
- Skip inventory adjustment tracking (imports are state restoration, not adjustments)

**Success criteria:**
- [ ] Finished goods inventory included in full backup export
- [ ] Inventory state restored during import
- [ ] Export/import round-trip preserves inventory counts
- [ ] Slug-based references work correctly

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ UI implementation (deferred to Phase 3)
- ❌ Historical inventory tracking (current state only)
- ❌ Full inventory audit trail (reason tracking is minimal)
- ❌ FIFO inventory management (not needed for finished goods)
- ❌ Consumption ledger records (unlike materials/ingredients - finished goods use simple counting)
- ❌ Manual inventory adjustment UI (service layer only)
- ❌ Low stock alerts/notifications (query only, no alerts)
- ❌ Event fulfillment allocation (future feature)
- ❌ Inventory forecasting/planning (future analytics)

**Rationale:** 
- Phase 2 focuses on service layer primitives. UI, notifications, and advanced analytics deferred to Phase 3+.
- FIFO not required because finished goods costs determined by production time, not purchase time (unlike raw ingredients).
- Consumption ledger not needed because finished goods don't track lot-level consumption history (simple count sufficient).

---

## Success Criteria

**Complete when:**

### Service Layer Methods
- [ ] finished_goods_inventory_service.py created
- [ ] All methods accept optional session parameter (F060 compliant)
- [ ] get_inventory_status() implemented and tested
- [ ] check_availability() implemented and tested
- [ ] validate_consumption() implemented and tested
- [ ] adjust_inventory() implemented and tested
- [ ] get_low_stock_items() implemented and tested
- [ ] get_total_inventory_value() implemented and tested

### Model Cleanup
- [ ] Business logic moved from models to service
- [ ] Model methods deprecated or minimized
- [ ] All callers updated to use service methods

### Production Integration
- [ ] adjust_inventory() supports reason="production"
- [ ] Method accepts session from production service
- [ ] Method works with positive quantity changes
- [ ] Notes field supports production run IDs

### Assembly Integration
- [ ] check_availability() works for units and goods
- [ ] adjust_inventory() supports reason="assembly"
- [ ] Both methods accept session from assembly service
- [ ] Multiple adjustments atomic via shared session

### Export/Import Integration
- [ ] Finished goods inventory included in full backup export
- [ ] Inventory state restored during import
- [ ] Export/import round-trip preserves counts

### Validation and Data Integrity
- [ ] Cannot consume more inventory than available
- [ ] Cannot create negative inventory
- [ ] Validation provides clear error messages
- [ ] All adjustments tracked with reasons

### Session Discipline (F060 Compliance)
- [ ] All methods accept optional session parameter
- [ ] When session provided, no internal session_scope
- [ ] When session provided, no internal commits
- [ ] Session threaded through downstream calls
- [ ] Backward compatible with callers not passing session

### Quality
- [ ] Service methods follow project patterns
- [ ] Service layer tests comprehensive
- [ ] Integration tests cover production workflow
- [ ] Integration tests cover assembly workflow
- [ ] Integration tests cover export/import round-trip
- [ ] No direct model.inventory_count updates bypass service

---

## Architecture Principles

### Session Ownership (F060 Compliance)

**Caller Owns Session:**
- Service methods accept optional `session` parameter
- When provided, service MUST use it exclusively
- When not provided, service opens own session (backward compat)
- No internal commits when session provided
- Thread session through ALL downstream calls

**Rationale:** Ensures atomic multi-service operations, prevents partial writes, enables clean transaction boundaries for future multi-user/API scenarios. This is a core principle established in F060 and must be followed by ALL services.

---

### No FIFO Required

**Design Decision:**
- Raw ingredients: FIFO required (different purchase prices/times)
- Finished goods: Cost based on production time, not purchase time
- All units of same FinishedUnit from same batch have same cost
- Consumption order irrelevant to cost accuracy

**Implication:** Simple inventory_count decrement sufficient, no need for complex FIFO tracking like raw ingredients. No consumption ledger records needed.

---

### Service Layer Coordination

**Responsibility Separation:**
- **Models**: Store inventory_count, enforce constraints (CHECK >= 0), provide data access
- **Services**: Validate changes, coordinate updates, track reasons, enforce business rules
- **UI**: Display status, initiate adjustments (Phase 3)

**Business Logic Location:**
- Model methods like `is_available()`, `update_inventory()`, `can_assemble()` should be DEPRECATED
- Business logic moves to `finished_goods_inventory_service`
- Models become pure data containers

**Rationale:** Models enforce invariants (non-negative), services implement business logic (validation, reason tracking), UI provides interface. Clean separation enables testing and future evolution. Aligns with F060 service layer discipline.

---

### Reason Tracking

**Minimal Audit Trail:**
- Adjustments require reason: "production", "assembly", "consumption", "spoilage", "gift", "adjustment"
- Optional notes field for context
- Not full audit trail (no historical table in Phase 2)
- No consumption ledger (unlike materials/ingredients)

**Rationale:** Sufficient for understanding inventory changes without complex historical tracking. Full audit trail can be added in Phase 3 without breaking Phase 2 service interface.

---

### Atomic Assembly Operations

**Transaction Boundary:**
- Assembly feasibility check
- Component consumption (multiple items)
- Finished good creation
- All succeed together or all fail

**Session Ownership:**
- Assembly service owns session
- Passes session to inventory service for each operation
- Inventory service participates in transaction via provided session
- Assembly service commits or rolls back at end

**Rationale:** Prevents partial assemblies, maintains inventory consistency, enables rollback on errors. Aligns with F060 session ownership pattern.

---

### Service Boundary Discipline

**Inventory Service Responsibilities (Primitives ONLY):**
- Query inventory status (`get_inventory_status()`, `get_low_stock_items()`, `get_total_inventory_value()`)
- Validate availability (`check_availability()`, `validate_consumption()`)
- Adjust inventory counts (`adjust_inventory()`)
- Track reasons for adjustments
- Participate in caller's transactions via session parameter

**NOT Inventory Service Responsibilities (Orchestration):**
- Assembly feasibility logic (belongs in assembly_run_service)
- Production workflow coordination (belongs in production_run_service)
- Dictating when other services call inventory methods
- Managing transactions (caller owns session)

**Other Services:**
- Production service: Owns production workflow, decides when to call `adjust_inventory()`, owns transaction
- Assembly service: Owns assembly workflow and feasibility logic, decides when to call `check_availability()` and `adjust_inventory()`, owns transaction

**Rationale:** Each service owns its domain. Inventory service provides primitives (check, adjust). Other services own their workflows and decide when to use inventory primitives. This prevents service coupling and maintains clear boundaries. Aligns with F060 service layer discipline.

---

## Constitutional Compliance

✅ **Principle I: User-Centric Design & Workflow Validation**
- Service primitives enable validated workflows
- Prevents user errors (overconsumption)
- Prepares for Phase 3 UI with solid foundation

✅ **Principle II: Data Integrity & FIFO Accuracy**
- Non-negative constraints enforced at model and service layers
- Validation prevents overconsumption
- Atomic transactions maintain consistency
- FIFO not required for finished goods (different costing model than raw ingredients)
- Session ownership (F060) prevents partial writes

✅ **Principle III: Future-Proof Schema, Present-Simple Implementation**
- Simple inventory_count field extensible to historical tracking later
- Service layer interface stable for Phase 3 UI
- No schema changes needed
- Export/import preserves inventory state

✅ **Principle IV: Test-Driven Development**
- Service layer methods must be tested before completion
- Integration tests cover production/assembly workflows
- Export/import round-trip tests verify data preservation

✅ **Principle V: Layered Architecture Discipline**
- Models: Storage and constraints (data layer)
- Services: Business logic and coordination (service layer)
- UI: Deferred to Phase 3 (presentation layer)
- Clear delegation patterns with session ownership
- Business logic moved from models to services

✅ **F060: Architecture Hardening**
- Session ownership pattern followed throughout
- Service provides primitives, doesn't orchestrate
- Clear transaction boundaries
- Atomic multi-service operations enabled

---

## Risk Considerations

**Risk: Production/assembly services may directly update inventory_count**
- Context: Existing code may bypass service layer
- Mitigation: Planning phase discovers current implementation; refactor to use service coordination with session threading; add tests to prevent regression

**Risk: Model method deprecation may break existing callers**
- Context: Unknown how many places call model methods directly
- Mitigation: Planning phase finds all callers; update to use service methods; consider keeping model methods as thin wrappers for backward compat initially

**Risk: Session parameter adoption requires updating all callers**
- Context: All service methods gain session parameter
- Mitigation: Session parameter is optional (backward compatible); callers can migrate incrementally; non-session callers continue working

**Risk: FinishedGood.can_assemble() may have different interface than assumed**
- Context: Spec assumes specific return structure
- Mitigation: Planning phase verifies actual model method signature; adapt service wrapper to match

**Risk: Transaction boundary scope unclear across production and assembly**
- Context: Multiple database updates must succeed/fail together
- Mitigation: Planning phase identifies transaction boundaries; follow F060 session ownership pattern; assembly/production services own session, inventory participates

**Risk: Cost calculations for inventory value may not exist**
- Context: FinishedUnit/FinishedGood may not have cost fields
- Mitigation: Planning phase verifies cost fields exist; if missing, defer `get_total_inventory_value()` to when costing implemented

**Risk: Export/import coordination may require format changes**
- Context: Current export may not include finished goods inventory
- Mitigation: Planning phase reviews current export format; extend following F049 patterns; ensure backward compatibility with manifests

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study F060 specification FIRST → understand session ownership pattern deeply
- Study `batch_production_service` → apply session pattern to all inventory methods
- Study `assembly_service` → understand transaction coordination pattern
- Study `inventory_service.py` for raw ingredients → adapt patterns for finished goods (but note: NO FIFO, NO consumption ledger)
- Study `production_run_service.py` OR `batch_production_service.py` → find completion workflow, add inventory update with session
- Study `assembly_run_service.py` → find creation workflow, add feasibility check and consumption with session
- Study `export_service.py` and `import_service.py` → understand how to coordinate inventory state

**Key Patterns to Copy:**
- `batch_production_service` session threading → ALL inventory service methods
- inventory_service query patterns → finished_goods_inventory_service queries (add session parameter)
- inventory_service validation → finished goods consumption validation (add session parameter)
- Service method naming conventions → maintain consistency
- F049 export/import coordination → finished goods inventory export

**Focus Areas:**
- Session parameter on EVERY service method (F060 compliance)
- Validation before consumption (prevent negative inventory)
- Reason tracking for all adjustments
- Assembly feasibility pre-checks (fail fast)
- Atomic transactions for assembly (session owned by assembly service)
- Integration with existing production/assembly services (minimal disruption)
- Model method deprecation (business logic moves to service)
- Export/import coordination (preserve inventory state)

**Service Interface Design:**
```python
finished_goods_inventory_service
  # All methods accept optional session parameter
  ├─ Queries: 
  │   ├─ get_inventory_status(session=None, ...)
  │   ├─ get_low_stock_items(session=None, threshold=5, ...)
  │   └─ get_total_inventory_value(session=None)
  ├─ Validation: 
  │   ├─ check_availability(session=None, item_id, quantity, ...)
  │   └─ validate_consumption(session=None, item_id, quantity, ...)
  └─ Updates: 
      └─ adjust_inventory(session=None, item_id, quantity, reason, notes=None)
```

**Service Boundary Principle:** 
- Inventory service provides primitives (check, adjust) with session support
- Production/Assembly services own their workflows and decide when to use primitives
- Production/Assembly services own session, pass to inventory service
- Inventory service participates in caller's transaction via provided session

**Integration Points:**
```python
# Production service (owns production workflow and session)
with session_scope() as session:
    # ... production workflow steps ...
    finished_goods_inventory_service.adjust_inventory(
        session=session,  # Thread session through
        item_id=finished_unit_id,
        quantity=+actual_yield,
        reason="production",
        notes=f"Production run {run_id}"
    )
    session.commit()  # Production service commits

# Assembly service (owns assembly workflow, feasibility logic, and session)
with session_scope() as session:
    # Check components (assembly owns feasibility logic)
    for component in components:
        available = finished_goods_inventory_service.check_availability(
            session=session,  # Thread session through
            item_id=component.id,
            quantity=component.required
        )
        if not available:
            session.rollback()
            raise InsufficientInventoryError(...)
    
    # Consume components
    for component in components:
        finished_goods_inventory_service.adjust_inventory(
            session=session,  # Same session
            item_id=component.id,
            quantity=-component.required,
            reason="assembly"
        )
    
    # Create finished good
    finished_goods_inventory_service.adjust_inventory(
        session=session,  # Same session
        item_id=finished_good_id,
        quantity=+1,
        reason="assembly"
    )
    
    session.commit()  # Assembly service commits
```

**Model Cleanup:**
```python
# BEFORE (business logic in model)
class FinishedUnit:
    def is_available(self, quantity):
        return self.inventory_count >= quantity
    
    def update_inventory(self, quantity, reason):
        self.inventory_count += quantity
        # ... validation, tracking, etc ...

# AFTER (models as data containers)
class FinishedUnit:
    # inventory_count is just a field
    # Business logic removed, handled by service
    pass

# Business logic moves to service
finished_goods_inventory_service.check_availability(session, unit_id, quantity)
finished_goods_inventory_service.adjust_inventory(session, unit_id, quantity, reason)
```

**Critical Implementation Considerations:**
- Session parameter MUST be first consideration for every method
- Test atomicity by forcing rollbacks mid-operation
- Verify no internal commits when session provided
- Verify no internal session_scope when session provided
- Ensure backward compatibility (callers without session still work)
- Document session ownership pattern for future developers
- Model method deprecation must not break existing code
- Export/import must preserve inventory_count values

**Verification Approach:**
- Code review focusing on session parameter usage
- Transaction rollback testing
- Multi-service operation atomicity tests
- Export/import round-trip with inventory state
- Test coverage for all reason types
- Test coverage for validation edge cases

---

## Future Integration Points

**Phase 3 UI (Not Implemented):**
- Inventory status dashboard (calls `get_inventory_status()`)
- Low stock alerts display (calls `get_low_stock_items()`)
- Manual adjustment workflows (calls `adjust_inventory()`)
- Historical tracking views (requires new feature)

**Phase 4+ Features (Informational):**
- Event fulfillment allocation
- Production planning based on inventory levels
- Inventory forecasting
- Full audit trail with historical table
- Consumption ledger (if needed - currently not planned)

These are examples of how Phase 3+ might use the service layer. This spec does NOT implement these features or dictate how they should work.

---

**END OF SPECIFICATION**
