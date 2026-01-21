# F060: Architecture Hardening - Service Boundaries & Session Management

**Version**: 1.0
**Priority**: HIGH
**Type**: Service Layer Architecture

---

## Executive Summary

Cursor's independent architecture review (2026-01-20) identified critical gaps in service boundary discipline and session management that create atomicity risks and prevent clean feature expansion:
- ❌ Session boundary violations (services open sessions inside transactions)
- ❌ Planning snapshots incomplete (missing ingredient aggregation, costs)
- ❌ Assembly cost/ledger gaps for nested finished goods
- ❌ Production service paths inconsistent (old vs batch production patterns)
- ❌ Planning orchestration (progress/shopping/feasibility) uses detached sessions
- ❌ Staleness checks miss key mutations (yield changes, composition updates)

This spec hardens the foundational architecture to "must fix" standards before continuing with feature development, ensuring session ownership discipline, planning snapshot completeness, and assembly/production path consistency.

---

## Problem Statement

**Current State (FRAGILE):**
```
Session Management
├─ ✅ Batch production service (proper session threading)
├─ ❌ Planning services (progress/shopping open own sessions)
├─ ❌ Production service (doesn't pass session to FIFO consumption)
└─ ❌ Event service helpers (self-manage sessions, break atomicity)

Planning Snapshots
├─ ✅ Batch calculation results stored
├─ ❌ Missing aggregated ingredients (TODO placeholder)
├─ ❌ Missing cost baselines (can't audit variance)
└─ ❌ Staleness ignores FinishedUnit/Composition updates

Assembly Service
├─ ✅ Ledger for packaging/materials consumption
├─ ❌ NO ledger for nested FinishedGood consumption
├─ ❌ Costs inferred, not snapshotted per component
└─ ❌ Export missing nested consumption records

Production Paths
├─ ✅ Batch production (snapshot + loss + session aware)
├─ ❌ Production service (older pattern, no snapshot, session unsafe)
└─ ❌ Two competing paths with different invariants

Planning Orchestration
├─ ❌ Progress uses detached event service reads
├─ ❌ Shopping commits inside helpers (breaks caller transaction)
└─ ❌ Feasibility lacks material/packaging cost awareness
```

**Target State (HARDENED):**
```
Session Management
├─ ✅ All services accept session parameter
├─ ✅ Caller owns session (no internal session_scope when session provided)
├─ ✅ Atomic operations guaranteed
└─ ✅ No internal commits in helpers

Planning Snapshots
├─ ✅ Aggregated ingredients with units/costs
├─ ✅ Cost baselines for variance analysis
└─ ✅ Staleness detects all BOM/yield mutations

Assembly Service
├─ ✅ Ledger for ALL consumption (nested FG + packaging + materials)
├─ ✅ Costs snapshotted at consumption time
└─ ✅ Export includes complete consumption audit trail

Production Paths
├─ ✅ Single production service (aligned to batch production pattern)
└─ ✅ Consistent snapshot + loss + session discipline

Planning Orchestration
├─ ✅ Progress operates in single session with snapshot
├─ ✅ Shopping respects caller transaction
└─ ✅ Feasibility surfaces cost and assignment blockers
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Mature Session Patterns**
   - `src/services/batch_production_service.py`
     - Study how session is threaded through all calls
     - Note dry-run vs commit pattern
     - Observe how FIFO consumption receives session
   - `src/services/assembly_service.py`
     - Study session handling in `record_assembly`
     - Note how downstream services receive session
     - Contrast with areas that don't pass session

2. **Planning Services (Target for Hardening)**
   - `src/services/planning/planning_service.py`
     - Find `calculate_plan` and snapshot creation
     - Note TODO for aggregated_ingredients
     - Study `_check_staleness_impl` mutation detection
   - `src/services/planning/progress.py`
     - Find calls to `event_service` helpers
     - Note detached session pattern
     - Study how progress percentages calculated
   - `src/services/planning/shopping_list.py`
     - Find `mark_shopping_complete` internal commit
     - Study session usage patterns

3. **Production Service Gap**
   - `src/services/production_service.py`
     - Compare `record_production` to batch production
     - Note session handling differences
     - Find inventory consumption calls without session

4. **Assembly Cost/Ledger Patterns**
   - `src/services/assembly_service.py`
     - Study packaging/material consumption ledger creation
     - Note finished unit consumption pattern
     - Find nested FinishedGood consumption (NO ledger currently)
   - `src/models/consumption_record.py`
     - Study consumption types and cost snapshot fields

5. **Event Service Helpers**
   - `src/services/event_service.py`
     - Find methods that open own sessions (get_*, list_*)
     - Note pattern that violates session ownership

6. **Staleness Detection**
   - `src/services/planning/planning_service.py`
     - Study `_check_staleness_impl`
     - Note what triggers staleness (Composition.created_at only)
     - Find what's missing (FinishedUnit updates, yield changes)

---

## Requirements Reference

This specification implements architecture hardening identified in:
- Cursor Architecture Review (2026-01-20)
- `docs/design/architecture.md` - Session ownership principle
- `docs/design/architecture.md` - Service layer discipline
- Constitution - Definition vs Instantiation immutability

**Critical Findings Addressed:**
- Session boundary violations break atomicity
- Planning snapshots omit ingredient aggregation and cost baselines
- Assembly cost and ledger gaps for nested finished goods
- Production service lags feature parity
- Planning progress uses detached data sources
- Staleness checks miss key mutations
- Shopping completion mutates snapshot outside caller transaction

---

## Functional Requirements

### FR-1: Enforce Session Ownership Pattern

**What it must do:**
- ALL service methods must accept optional `session` parameter
- When session provided, use it exclusively (no internal `session_scope`)
- When session NOT provided, open own session (backward compatibility)
- NO internal commits when session provided (caller controls transaction)
- Thread session through ALL downstream service calls

**Current violations:**
- `planning/progress.py` calls event service without passing session
- `planning/shopping_list.py` commits inside `mark_shopping_complete`
- `production_service.record_production` calls FIFO without session
- Event service helpers open own sessions instead of accepting parameter

**Pattern reference:** Study `batch_production_service.record_production` session threading

**Success criteria:**
- [ ] All service methods accept `session` parameter
- [ ] No `session_scope` when session provided
- [ ] No internal commits when session provided
- [ ] All downstream calls receive session
- [ ] Atomicity guaranteed for multi-service operations

---

### FR-2: Complete Planning Snapshot with Ingredient Aggregation

**What it must do:**
- Populate `calculation_results["aggregated_ingredients"]` (currently TODO)
- Include ingredient slug, display name, required quantity, unit
- Store cost per unit at snapshot time (for variance analysis)
- Calculate from recipe composition using post-F056 yield model
- Include in staleness detection (ingredient requirement changes)

**Pattern reference:** Study how batch calculation aggregates recipe requirements

**Business rules:**
- Aggregation must respect recipe yield ratios
- Units must be base units (from ingredient catalog)
- Costs snapshot at plan calculation time (not live lookup)

**Success criteria:**
- [ ] Aggregated ingredients populated in snapshot
- [ ] Includes slug, name, quantity, unit, cost_per_unit
- [ ] Calculated from recipe composition with correct yield
- [ ] Staleness triggers when ingredient requirements change
- [ ] Export/import includes aggregated ingredients

---

### FR-3: Add Assembly Ledger for Nested Finished Goods

**What it must do:**
- Create consumption records when nested FinishedGoods consumed
- Snapshot cost at consumption time (not calculated later)
- Record which assembly consumed which nested finished good
- Include lot tracking for nested finished goods
- Support export/import of nested consumption records

**Current gap:**
- Assembly decrements inventory for nested FG but creates NO ledger entry
- Cost calculated later using `calculate_current_cost` (not snapshotted)
- No audit trail for nested component usage

**Pattern reference:** Study packaging/material consumption ledger creation in `assembly_service.record_assembly`

**Success criteria:**
- [ ] Consumption records created for nested FinishedGoods
- [ ] Cost snapshotted at consumption time
- [ ] Ledger includes lot information
- [ ] Export includes nested FG consumption records
- [ ] Import can restore nested consumption audit trail

---

### FR-4: Deprecate Production Service in Favor of Batch Production

**What it must do:**
- DEPRECATE `production_service.record_production` entirely
- Identify all callers of old production service
- Migrate all callers to `batch_production_service.record_production`
- Remove deprecated service after migration complete
- Ensure UI and other code paths use only batch production service

**Current gaps:**
- No recipe snapshot link (can't audit what was planned)
- No loss tracking (can't analyze waste)
- Calls FIFO without session (atomicity risk)
- Two competing production paths confuse future development

**Rationale for deprecation:**
- Batch production service is more mature and robust
- Better to consolidate now than maintain two patterns
- Planning/production features should build on stronger foundation
- Pattern-matching principle: one way to do production
- Desktop single-user context makes migration low-risk

**Pattern reference:** Study `batch_production_service.record_production` as the single production pattern going forward

**Migration approach:**
- Planning phase identifies all callers of `production_service.record_production`
- Update callers to use `batch_production_service` with appropriate parameters
- Test each migration point
- Remove `production_service.record_production` method
- Update imports and references

**Success criteria:**
- [ ] All callers of old production service identified
- [ ] All callers migrated to batch production service
- [ ] Old production service method removed
- [ ] Single production pattern throughout codebase
- [ ] No references to deprecated service remain

---

### FR-5: Harden Planning Orchestration Session Discipline

**What it must do:**
- `progress.py` operates in single session with snapshot data
- `shopping_list.py` removes internal commits, respects caller session
- `feasibility.py` extended to surface material/packaging cost blockers
- Link progress calculation to plan snapshot (not detached event reads)
- Compute `available_to_assemble` via feasibility service (not hardcoded 0)

**Current problems:**
- Progress calls event service helpers that open own sessions
- Shopping commits inside helper, breaking caller transaction
- Feasibility only checks inventory, ignores cost/assignment gaps
- Progress can be stale vs current transaction state

**Pattern reference:** Study batch production session threading for multi-step orchestration

**Success criteria:**
- [ ] Progress operates in single session
- [ ] Shopping respects caller transaction (no internal commits)
- [ ] Feasibility returns cost and assignment blockers distinctly
- [ ] Progress tied to snapshot + live deltas
- [ ] `available_to_assemble` calculated via feasibility

---

### FR-6: Enhance Staleness Detection for BOM Mutations

**What it must do:**
- Detect Composition updates (not just created_at)
- Detect FinishedUnit yield changes
- Detect packaging assignment changes
- Detect material requirement changes
- Add `updated_at` timestamp to Composition model OR use content hash

**Current gap:**
- Only tracks `Composition.created_at`
- Misses updates, deletes, yield changes, packaging/material changes
- Plans marked fresh while BOM actually changed

**Pattern reference:** Study how other entities track modification (updated_at patterns)

**Business rules:**
- Schema-affecting changes must invalidate plans
- Non-schema changes (e.g., display name) may not invalidate

**Success criteria:**
- [ ] Staleness detects Composition updates
- [ ] Staleness detects FinishedUnit yield changes
- [ ] Staleness detects packaging/material assignment changes
- [ ] Composition has updated_at OR hash mechanism
- [ ] Test coverage for all mutation types

---

### FR-7: Normalize Event Service Helper Session Patterns

**What it must do:**
- Event service methods (get_*, list_*) accept optional session parameter
- Use provided session when available
- Remove internal session_scope when session provided
- Support both standalone usage and transactional usage

**Current violations:**
- Helpers always open own sessions
- Planning services can't include event reads in their transactions
- Progress/shopping forced to use detached reads

**Pattern reference:** Study standard service method session parameter patterns

**Success criteria:**
- [ ] All event service helpers accept session parameter
- [ ] Session used when provided
- [ ] Backward compatible (works without session)
- [ ] Planning orchestration can include event reads in transaction

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Materials UI metric base unit updates (separate feature)
- ❌ Material FIFO consumption type fixes (linear/square/each) (separate feature)
- ❌ New planning features or UI enhancements (foundation only)
- ❌ Export/import format changes beyond ledger completeness (phase 2)
- ❌ Performance optimization (small scale makes this premature)
- ❌ Migration scripts (desktop app uses export/reset/import workflow)

**Deferred to future phases:**
- Composition versioning or hashing (current updated_at sufficient)
- Unified cost model helpers (duplication acceptable for now)
- Export/import of planning snapshots (not needed for current workflows)

---

## Success Criteria

**Complete when:**

### Session Management
- [ ] All services accept optional session parameter
- [ ] No session_scope when session provided
- [ ] No internal commits when session provided
- [ ] All downstream calls thread session through
- [ ] Batch production, assembly, production, planning all consistent

### Planning Snapshots
- [ ] Aggregated ingredients populated with slug/name/quantity/unit/cost
- [ ] Cost baselines enable variance analysis
- [ ] Staleness detects Composition/FinishedUnit/yield mutations
- [ ] Export/import includes complete snapshot data

### Assembly Service
- [ ] Consumption ledger for nested FinishedGoods
- [ ] Costs snapshotted at consumption time
- [ ] Export includes nested consumption records
- [ ] Audit trail complete for all assembly components

### Production Paths
- [ ] Old production_service.record_production deprecated and removed
- [ ] All callers migrated to batch_production_service
- [ ] Single production pattern throughout codebase
- [ ] No competing implementations

### Planning Orchestration
- [ ] Progress operates in single session
- [ ] Shopping respects caller transaction
- [ ] Feasibility surfaces cost/assignment blockers
- [ ] Progress tied to snapshot
- [ ] `available_to_assemble` calculated correctly

### Event Service
- [ ] Helpers accept session parameter
- [ ] Backward compatible standalone usage
- [ ] Transactional usage supported

### Quality
- [ ] Code review confirms session ownership pattern
- [ ] No session boundary violations remain
- [ ] Pattern consistency across all services
- [ ] Test coverage for atomicity guarantees
- [ ] Cursor review "must fix" items resolved

---

## Architecture Principles

### Session Ownership

**Caller Owns Session:**
- Service methods accept optional `session` parameter
- When provided, service MUST use it exclusively
- When not provided, service opens own session (backward compat)
- No internal commits when session provided
- Thread session through ALL downstream calls

**Rationale:** Ensures atomic multi-service operations, prevents partial writes, enables clean transaction boundaries for future multi-user/API scenarios.

### Snapshot Completeness

**Planning Must Capture Full Intent:**
- Snapshots include aggregated ingredient requirements
- Cost baselines stored at snapshot time
- Staleness detects all BOM/yield mutations
- Snapshots enable variance analysis (planned vs actual)

**Rationale:** Planning snapshots represent the complete plan contract. Without ingredients/costs, cannot audit production against plan or detect requirement changes.

### Ledger Completeness

**All Consumption Must Be Ledgered:**
- Every inventory decrement has matching consumption record
- Costs snapshotted at consumption time (not calculated later)
- Applies to: finished units, nested finished goods, packaging, materials
- Enables complete audit trail and export fidelity

**Rationale:** Ledger is source of truth for "what was used when and at what cost." Missing entries break audit chain and prevent variance analysis.

### Pattern Matching

**Production patterns must match batch production exactly:**
- Session threading discipline
- Recipe snapshot linkage
- Loss tracking
- FIFO consumption with session
- Cost variance recording

**Planning orchestration must match batch production session discipline:**
- Single session for multi-step operations
- No internal commits in helpers
- Caller controls transaction boundaries

**Event service must match standard service patterns:**
- Optional session parameter
- Use provided session when available
- Backward compatible standalone usage

---

## Constitutional Compliance

✅ **Principle I: Data Integrity & Immutability**
- Ledger completeness ensures complete audit trail
- Cost snapshots preserve historical values
- Planning snapshots capture plan intent immutably
- Session atomicity prevents partial writes

✅ **Principle II: Future-Proof Schema Design**
- Session parameter pattern supports multi-user future
- Staleness detection supports automated invalidation
- Snapshot completeness enables API contract stability
- No schema migrations needed (export/reset/import)

✅ **Principle III: Definition vs Instantiation**
- Planning snapshots separate plan (definition) from execution (instantiation)
- Cost snapshots preserve instantiation values
- Staleness detects definition changes affecting plans
- Production/assembly record instantiation against definitions

✅ **Principle IV: Service Layer Discipline**
- Clear session ownership boundaries
- Services provide primitives, don't dictate usage
- Each service owns its domain logic
- No scope creep across service boundaries

✅ **Principle V: Pattern Consistency**
- Production paths aligned to single pattern
- Session threading consistent across services
- Ledger creation follows same pattern
- Event service matches standard service structure

---

## Risk Considerations

**Risk: Breaking changes to service signatures**
- All services gain session parameter
- Backward compatible (session optional)
- Callers can migrate incrementally
- Mitigation: Optional parameter maintains compatibility

**Risk: Production service deprecation requires caller migration**
- Must identify all callers of old production service
- Migration work proportional to usage (unknown until planning phase)
- UI workflows may need adjustment for batch production parameters
- Mitigation: Planning phase identifies all callers, tests each migration point thoroughly

**Risk: Staleness detection becoming too sensitive**
- Adding more mutation triggers could over-invalidate plans
- Need to distinguish schema-affecting vs cosmetic changes
- Mitigation: Document which changes should invalidate

**Risk: Snapshot data volume growth**
- Storing aggregated ingredients and costs increases snapshot size
- Current single-user desktop scale makes this negligible
- Mitigation: Desktop context has ample storage, no optimization needed yet

**Risk: Complex multi-service transaction testing**
- Session threading creates more complex test scenarios
- Need to verify atomicity guarantees
- Mitigation: Follow batch production test patterns, add rollback tests

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `batch_production_service` → apply session pattern to all services
- Study packaging/material ledger → apply to nested finished goods
- Study existing snapshot structure → extend for ingredients/costs
- Study staleness detection → extend for all mutations

**Key Patterns to Copy:**
- `batch_production_service.record_production` session threading → all production/planning
- Packaging consumption ledger creation → nested FG consumption
- Recipe snapshot linkage → production service (if aligning)
- Optional session parameter pattern → event service helpers

**Focus Areas:**
- Session parameter threading is mechanical but requires touching many files
- Nested FG ledger creation requires careful cost snapshot timing
- Staleness detection requires analysis of what changes matter
- Production service deprecation requires finding and testing all migration points

**Critical Implementation Considerations:**
- Test atomicity by forcing rollbacks mid-operation
- Verify no internal commits when session provided
- Ensure backward compatibility (callers without session still work)
- Document session ownership pattern for future developers

**Verification Approach:**
- Code review focusing on session_scope usage
- Transaction rollback testing
- Multi-service operation atomicity tests
- Export/import round-trip with ledger completeness

---

**END OF SPECIFICATION**
