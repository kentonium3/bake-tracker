# F0XX: Finished Goods Inventory Service Layer

**Version**: 2.0
**Priority**: MEDIUM
**Type**: Service Layer

---

## Executive Summary

Finished goods inventory tracking exists in the data model (`inventory_count` fields on FinishedUnit and FinishedGood), but lacks service layer support for validation, queries, and integration with production/assembly workflows. Production runs add inventory without service coordination, assembly runs may fail due to insufficient components, and there's no way to query current stock levels.

Current gaps:
- ❌ No service layer for inventory queries (current stock, low stock alerts)
- ❌ No consumption validation (can consume more than available)
- ❌ Production runs don't coordinate inventory updates through services
- ❌ Assembly runs don't have inventory primitives available
- ❌ No inventory value calculations

This spec adds finished goods inventory service to enable validated inventory operations and queries, preparing for Phase 3 UI implementation.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Data Model (Phase 1)
├─ ✅ FinishedUnit.inventory_count field exists
├─ ✅ FinishedGood.inventory_count field exists
├─ ✅ Model methods: is_available(), update_inventory(), can_assemble()
└─ ✅ Database constraints: CHECK (inventory_count >= 0)

Service Layer
├─ ❌ No inventory query service
├─ ❌ No consumption validation service
├─ ❌ No inventory adjustment tracking
├─ ❌ No assembly feasibility checks
└─ ❌ No inventory value calculations

Production Integration
├─ ✅ Production runs create finished units
└─ ❌ No service-coordinated inventory updates

Assembly Integration
├─ ✅ Assembly runs consume components, create goods
├─ ❌ No pre-validation of component availability
└─ ❌ Direct model updates without service coordination

UI Layer
└─ ❌ No inventory visibility (deferred to Phase 3)
```

**Target State (COMPLETE - Phase 2 Service Layer Only):**
```
Service Layer
├─ ✅ finished_goods_inventory_service.py
├─ ✅ get_inventory_status() - query current stock
├─ ✅ check_availability() - validate sufficient inventory
├─ ✅ validate_consumption() - prevent overconsumption
├─ ✅ adjust_inventory() - tracked inventory changes
├─ ✅ get_low_stock_items() - identify shortages
└─ ✅ get_total_inventory_value() - cost tracking

Production Integration
├─ ✅ adjust_inventory() primitive available for production service
└─ ✅ Production service decides when to call it

Assembly Integration
├─ ✅ check_availability() primitive available for assembly service
├─ ✅ adjust_inventory() primitive available for assembly service
└─ ✅ Assembly service owns feasibility logic, calls inventory primitives

UI Layer
└─ ⏳ Deferred to Phase 3 (service layer prepares for it)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Existing Models**
   - Find `src/models/finished_unit.py`
   - Find `src/models/finished_good.py`
   - Study `inventory_count` field usage
   - Note existing methods: is_available(), update_inventory(), can_assemble()
   - **IMPORTANT**: Existing model methods should be deprecated or made minimal (property accessors only)
   - Business logic should move to finished_goods_inventory_service
   - Understand database constraints (non-negative inventory)

2. **Production Run Service**
   - Find `src/services/production_run_service.py`
   - Study production completion workflow
   - Note how actual_yield is recorded
   - Understand where inventory should be updated

3. **Assembly Run Service**
   - Find `src/services/assembly_run_service.py`
   - Study assembly creation workflow
   - Note component consumption patterns
   - Understand FinishedGood.can_assemble() usage

4. **Related Service Patterns**
   - Study `src/services/inventory_service.py` (raw ingredients)
   - Note FIFO pattern (not needed for finished goods)
   - Study validation patterns
   - Note service method naming conventions

5. **Recipe Service (Optional)**
   - Study costing calculations if implementing inventory value
   - Note how costs are propagated to finished units

---

## Requirements Reference

This specification implements service layer support for finished goods inventory. No formal requirements document exists yet for this subsystem, but key principles:
- Non-negative inventory constraint (already enforced at model level)
- Consumption validation before inventory decrease
- Tracked inventory adjustments with reasons
- Assembly feasibility pre-checks
- Simple inventory counting (FIFO not required for finished goods)

---

## Functional Requirements

### FR-1: Inventory Status Queries

**What it must do:**
- Query current inventory levels for finished units and/or finished goods
- Filter by specific item or return all items
- Option to include/exclude zero-stock items
- Return inventory with display names, slugs, counts
- Calculate inventory values based on unit/good costs

**Pattern reference:** Study how inventory_service.py queries raw ingredient inventory, adapt pattern for finished goods

**Success criteria:**
- [ ] Can query all finished units inventory
- [ ] Can query all finished goods inventory
- [ ] Can query specific item by ID
- [ ] Can filter out zero-stock items
- [ ] Returns structured data with counts and values

---

### FR-2: Availability Checking

**What it must do:**
- Check if sufficient inventory exists for required quantity
- Return availability status (bool) plus current inventory
- Calculate shortage amount if insufficient
- Support both finished units and finished goods

**Pattern reference:** Wraps existing model method is_available(), adds service-layer structure

**Success criteria:**
- [ ] Returns true when inventory sufficient
- [ ] Returns false with shortage amount when insufficient
- [ ] Works for both FinishedUnit and FinishedGood
- [ ] Provides actionable data for callers

---

### FR-3: Consumption Validation

**What it must do:**
- Validate consumption request before allowing operation
- Prevent consumption exceeding available inventory
- Return validation result (bool) and error message if invalid
- Support validation without actually consuming

**Pattern reference:** Similar to inventory_service consumption validation for raw ingredients

**Business rules:**
- Cannot consume more than current inventory_count
- Validation must occur before any database updates
- Error messages must clearly state shortage amounts

**Success criteria:**
- [ ] Validates before consumption allowed
- [ ] Blocks overconsumption attempts
- [ ] Provides clear error messages
- [ ] Separates validation from actual consumption

---

### FR-4: Tracked Inventory Adjustments

**What it must do:**
- Adjust inventory_count with reason tracking
- Support positive changes (production, assembly completion)
- Support negative changes (assembly consumption, spoilage, gifts)
- Validate adjustments won't create negative inventory
- Record reason and optional notes

**Pattern reference:** Study inventory_service.adjust_inventory() for raw ingredients, adapt pattern

**Business rules:**
- Reason must be specified: "production", "assembly", "consumption", "spoilage", "gift", "adjustment"
- Notes optional but recommended for manual adjustments
- Must validate final inventory_count >= 0
- Return previous count, new count, change amount

**Success criteria:**
- [ ] Adjusts inventory with validation
- [ ] Tracks reason for adjustment
- [ ] Prevents negative inventory
- [ ] Returns adjustment summary
- [ ] Supports both increase and decrease

---

### FR-5: Low Stock Identification

**What it must do:**
- Identify items with inventory below threshold
- Default threshold configurable (e.g., 5 units)
- Filter by item type (units vs goods) or show all
- Return items with current counts

**Pattern reference:** Simple query pattern filtering inventory_count < threshold

**Success criteria:**
- [ ] Returns items below threshold
- [ ] Threshold configurable via parameter
- [ ] Can filter by item type
- [ ] Useful for production planning

---

### FR-6: Low Stock Identification

**What it must do:**
- Identify items with inventory below threshold
- Default threshold configurable (e.g., 5 units)
- Filter by item type (units vs goods) or show all
- Return items with current counts

**Pattern reference:** Simple query pattern filtering inventory_count < threshold

**Success criteria:**
- [ ] Returns items below threshold
- [ ] Threshold configurable via parameter
- [ ] Can filter by item type
- [ ] Useful for production planning

---

### FR-7: Inventory Value Calculation

**What it must do:**
- Calculate total value of finished goods inventory
- Aggregate finished units value (count × unit_cost)
- Aggregate finished goods value (count × total_cost)
- Return grand total inventory value

**Pattern reference:** Simple aggregation query across inventory_count and cost fields

**Note:** If costing logic is complex (weighted average, cost layers), planning phase should verify whether a separate costing_service is needed. Simple multiplication (count × cost) can stay in inventory service.

**Success criteria:**
- [ ] Calculates finished units total value
- [ ] Calculates finished goods total value
- [ ] Returns grand total
- [ ] Handles items with zero inventory

---

### FR-8: Service Primitives for Production Integration

**What it must do:**
- Provide adjust_inventory() method that production_run_service CAN call
- Accept reason="production" for production-related adjustments
- Support positive quantity changes (adding produced items)
- Record production run context in notes if provided

**Pattern reference:** Study how inventory_service supports purchase integration

**Note:** This spec does NOT dictate when or how production_run_service calls this method. Production service owns its own workflow. This spec only ensures the primitive operation is available.

**Success criteria:**
- [ ] adjust_inventory() supports reason="production"
- [ ] Positive quantity changes work correctly
- [ ] Notes field can store production run ID
- [ ] Method available for production service to use

---

### FR-9: Service Primitives for Assembly Integration

**What it must do:**
- Provide check_availability() to verify components exist
- Provide adjust_inventory() for component consumption (negative) and good creation (positive)
- Support atomic transactions for multi-item adjustments
- Accept reason="assembly" for assembly-related adjustments

**Pattern reference:** Study assembly_run_service to understand what primitives it needs

**Business rules:**
- Multiple adjust_inventory() calls can be wrapped in transaction
- Component consumption and good creation should be atomic

**Note:** This spec does NOT dictate assembly_run_service workflow. Assembly service owns feasibility checking logic and decides when to call inventory primitives. This spec only ensures primitives are available.

**Success criteria:**
- [ ] check_availability() works for finished units and goods
- [ ] adjust_inventory() supports reason="assembly"
- [ ] Multiple adjustments can be atomic
- [ ] Methods available for assembly service to use

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ UI implementation (deferred to Phase 3)
- ❌ Historical inventory tracking (current state only)
- ❌ Inventory audit trail (reason tracking is minimal)
- ❌ FIFO inventory management (not needed for finished goods)
- ❌ Manual inventory adjustment UI (service layer only)
- ❌ Low stock alerts/notifications (query only, no alerts)
- ❌ Event fulfillment allocation (future feature)
- ❌ Inventory forecasting/planning (future analytics)

**Rationale:** Phase 2 focuses on service layer primitives. UI, notifications, and advanced analytics deferred to Phase 3+. FIFO not required because finished goods costs determined by production time, not purchase time.

---

## Success Criteria

**Complete when:**

### Service Layer Methods
- [ ] finished_goods_inventory_service.py created
- [ ] get_inventory_status() implemented and tested
- [ ] check_availability() implemented and tested
- [ ] validate_consumption() implemented and tested
- [ ] adjust_inventory() implemented and tested
- [ ] get_low_stock_items() implemented and tested
- [ ] get_total_inventory_value() implemented and tested

### Production Integration
- [ ] adjust_inventory() supports reason="production"
- [ ] Method works with positive quantity changes
- [ ] Notes field supports production run IDs

### Assembly Integration
- [ ] check_availability() works for units and goods
- [ ] adjust_inventory() supports reason="assembly"
- [ ] Multiple adjustments can be atomic (transaction support)

### Validation and Data Integrity
- [ ] Cannot consume more inventory than available
- [ ] Cannot create negative inventory
- [ ] Validation provides clear error messages
- [ ] All adjustments tracked with reasons

### Quality
- [ ] Service methods follow project patterns
- [ ] Service layer tests comprehensive
- [ ] Integration tests cover production workflow
- [ ] Integration tests cover assembly workflow
- [ ] No direct model.inventory_count updates bypass service

---

## Architecture Principles

### No FIFO Required

**Design Decision:**
- Raw ingredients: FIFO required (different purchase prices/times)
- Finished goods: Cost based on production time, not purchase time
- All units of same FinishedUnit from same batch have same cost
- Consumption order irrelevant to cost accuracy

**Implication:** Simple inventory_count decrement sufficient, no need for complex FIFO tracking like raw ingredients.

---

### Service Layer Coordination

**Responsibility Separation:**
- **Models**: Store inventory_count, enforce constraints
- **Services**: Validate changes, coordinate updates, track reasons
- **UI**: Display status, initiate adjustments (Phase 3)

**Rationale:** Models enforce invariants (non-negative), services implement business logic (validation, reason tracking), UI provides interface. Clean separation enables testing and future evolution.

---

### Reason Tracking

**Minimal Audit Trail:**
- Adjustments require reason: "production", "assembly", "consumption", "spoilage", "gift", "adjustment"
- Optional notes field for context
- Not full audit trail (no historical table in Phase 2)

**Rationale:** Sufficient for understanding inventory changes without complex historical tracking. Full audit trail can be added in Phase 3 without breaking Phase 2 service interface.

---

### Atomic Assembly Operations

**Transaction Boundary:**
- Assembly feasibility check
- Component consumption (multiple items)
- Finished good creation
- All succeed together or all fail

**Rationale:** Prevents partial assemblies, maintains inventory consistency, enables rollback on errors.

---

### Service Boundary Discipline

**Inventory Service Responsibilities:**
- Query inventory status
- Validate availability
- Adjust inventory counts
- Track reasons for adjustments

**NOT Inventory Service Responsibilities:**
- Assembly feasibility logic (belongs in assembly_run_service)
- Production workflow coordination (belongs in production_run_service)
- Dictating when other services call inventory methods

**Rationale:** Each service owns its domain. Inventory service provides primitives (check, adjust). Other services own their workflows and decide when to use inventory primitives. This prevents service coupling and maintains clear boundaries.

---

## Constitutional Compliance

✅ **Principle II: Data Integrity**
- Non-negative constraints enforced at model and service layers
- Validation prevents overconsumption
- Atomic transactions maintain consistency
- FIFO not required for finished goods (different costing model than raw ingredients)

✅ **Principle III: Future-Proof Schema**
- Simple inventory_count field extensible to historical tracking later
- Service layer interface stable for Phase 3 UI
- No schema changes needed

✅ **Principle V: Layered Architecture Discipline**
- Models: Storage and constraints
- Services: Business logic and coordination
- UI: Deferred to Phase 3
- Clear delegation patterns

✅ **Principle VII: Pragmatic Aspiration**
- Phase 2: Service layer only (no UI complexity)
- Phase 3: Add UI when ready
- Incremental approach prevents over-engineering

---

## Risk Considerations

**Risk: Production/assembly services may directly update inventory_count**
- Context: Existing code may bypass service layer
- Mitigation: Planning phase discovers current implementation; refactor to use service coordination; add tests to prevent regression

**Risk: FinishedGood.can_assemble() may have different interface than assumed**
- Context: Spec assumes specific return structure
- Mitigation: Planning phase verifies actual model method signature; adapt service wrapper to match

**Risk: Atomic transaction scope unclear across production and assembly**
- Context: Multiple database updates must succeed/fail together
- Mitigation: Planning phase identifies transaction boundaries; use database transactions or service-level rollback patterns

**Risk: Cost calculations for inventory value may not exist**
- Context: FinishedUnit/FinishedGood may not have cost fields
- Mitigation: Planning phase verifies cost fields exist; if missing, defer get_total_inventory_value() to when costing implemented

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study inventory_service.py for raw ingredients → adapt patterns for finished goods
- Study production_run_service.py → find completion workflow, add inventory update
- Study assembly_run_service.py → find creation workflow, add feasibility check and consumption
- Study FinishedUnit/FinishedGood models → understand existing methods and constraints
- Study database transaction patterns → ensure atomic assembly operations

**Key Patterns to Copy:**
- inventory_service query patterns → finished_goods_inventory_service queries
- inventory_service validation → finished goods consumption validation
- Service method naming conventions → maintain consistency

**Focus Areas:**
- Validation before consumption (prevent negative inventory)
- Reason tracking for all adjustments
- Assembly feasibility pre-checks (fail fast)
- Atomic transactions for assembly (all or nothing)
- Integration with existing production/assembly services (minimal disruption)

**Service Interface Design:**
```
finished_goods_inventory_service
  ├─ Queries: get_inventory_status(), get_low_stock_items(), get_total_inventory_value()
  ├─ Validation: check_availability(), validate_consumption()
  └─ Updates: adjust_inventory()
```

**Note:** Assembly feasibility logic belongs in assembly_run_service, which calls inventory primitives (check_availability) as needed.

**Integration Points:**
```
production_run_service (owns production workflow)
  └─ Decides when to call: adjust_inventory(+actual_yield, reason="production")

assembly_run_service (owns assembly workflow and feasibility logic)
  ├─ Decides when to check: check_availability() for each component
  ├─ On component consumption: adjust_inventory(-qty, reason="assembly")
  └─ On good creation: adjust_inventory(+qty, reason="assembly")
```

**Boundary Principle:** Inventory service provides primitives (check, adjust). Production/Assembly services own their workflows and decide when to use primitives.

---

## Future Integration Points

**Phase 3 UI (Not Implemented):**
- Inventory status dashboard
- Low stock alerts display
- Manual adjustment workflows
- Historical tracking views

**Phase 4+ Features (Informational):**
- Event fulfillment allocation
- Production planning based on inventory levels
- Inventory forecasting
- Full audit trail with historical table

These are examples of how Phase 3+ might use the service layer. This spec does NOT implement these features or dictate how they should work.

---

**END OF SPECIFICATION**
