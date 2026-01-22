# F062: Service Session Consistency Hardening

**Version**: 2.0
**Priority**: HIGH
**Type**: Service Layer Architecture

---

## Executive Summary

Post-F060/F061 architectural reviews reveal remaining session discipline gaps across event, production, and assembly services that create atomicity risks and inconsistent patterns. While F060/F061 hardened core workflows, several services still have functions that don't accept session parameters, ignore provided sessions, or return inconsistent DTO types.

Current gaps:
- ❌ 40+ event_service functions missing session parameters
- ❌ batch_production_service ignores session in history/run queries
- ❌ assembly_service ignores session in history/run queries
- ❌ production_service.get_production_progress doesn't accept session
- ❌ get_events_with_progress doesn't thread session
- ❌ DTO inconsistency (Decimal vs string for costs)
- ❌ Session parameters optional instead of required

This spec completes session discipline across ALL services with REQUIRED session parameters, establishing universal patterns before planning/production feature development. Per CLAUDE.md documentation, session management bugs have caused silent data loss before - this work prevents recurrence.

---

## Problem Statement

**Current State (INCONSISTENT):**
```
Session Pattern Inconsistency
├─ ⚠️ Some services accept session (optional)
├─ ⚠️ Some services ignore session parameter
├─ ⚠️ Some services don't accept session at all
└─ ❌ Optional session creates ambiguity about ownership

Event Service (40+ functions)
├─ ❌ Most functions missing session parameter
├─ ❌ Each opens own session_scope internally
└─ ❌ Cannot participate in caller transactions

Batch Production Service
├─ ✅ record_production accepts and uses session
├─ ❌ get_production_history ignores session parameter
└─ ❌ get_production_run ignores session parameter

Assembly Service
├─ ✅ record_assembly accepts and uses session
├─ ❌ get_assembly_history ignores session parameter
└─ ❌ get_assembly_run ignores session parameter

Production Service
├─ ⚠️ Some methods accept session
└─ ❌ get_production_progress doesn't accept session

Progress Queries
└─ ❌ get_events_with_progress doesn't accept/thread session

DTO Consistency
└─ ❌ Costs returned as Decimal in some services, str in others
```

**Target State (UNIVERSAL DISCIPLINE):**
```
Session Pattern Universality
├─ ✅ ALL service methods REQUIRE session parameter
├─ ✅ Caller owns session lifecycle
├─ ✅ Services participate in caller's transaction
└─ ✅ No ambiguity about transaction ownership

Event Service
├─ ✅ ALL functions require session parameter
├─ ✅ Use provided session exclusively
└─ ✅ Can participate in multi-service transactions

Batch Production Service
├─ ✅ record_production requires session
├─ ✅ get_production_history requires and uses session
└─ ✅ get_production_run requires and uses session

Assembly Service
├─ ✅ record_assembly requires session
├─ ✅ get_assembly_history requires and uses session
└─ ✅ get_assembly_run requires and uses session

Production Service
├─ ✅ ALL methods require session
└─ ✅ get_production_progress requires session

Progress Queries
└─ ✅ get_events_with_progress requires and threads session

DTO Consistency
└─ ✅ Costs consistently formatted (Decimal as string for DTOs)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **F060 & F061 Specifications**
   - Read `docs/func-spec/F060_architecture_hardening_service_boundaries.md`
   - Read `docs/func-spec/F061_*.md` (whatever F061 covered)
   - Understand session ownership principle ("caller owns session")
   - Note: This spec completes what F060/F061 started

2. **Cursor Code Review (Context for This Work)**
   - Read `docs/code-reviews/cursor-service-primitives-review.md`
   - Understand identified gaps in session discipline
   - Note which services still violate patterns

3. **Current Service Patterns**
   - Find `src/services/batch_production_service.py`
   - Study `record_production` - correct session usage
   - Study `get_production_history` - INCORRECT (ignores session)
   - Find `src/services/assembly_service.py`
   - Study `record_assembly` - correct session usage
   - Study `get_assembly_history` - INCORRECT (ignores session)

4. **Event Service (Primary Target)**
   - Find `src/services/event_service.py`
   - Count functions without session parameter (~40+)
   - Identify internal session_scope usage patterns

5. **Database Session Management**
   - Find `src/database.py`
   - Study `session_scope` context manager
   - Understand transaction lifecycle

6. **DTO Patterns Across Services**
   - Survey how costs are returned in DTOs
   - Identify Decimal vs string inconsistencies

---

## Requirements Reference

This specification completes architectural work started in:
- **F060**: Architecture Hardening - Session ownership pattern
- **F061**: [whatever F061 covered]
- **Cursor Review (2026-01-20)**: Service Primitives & Best-Practice Readiness
- **CLAUDE.md Documentation**: Session management bugs have caused silent data loss

Key principles:
- Required session parameters: ALL services, ALL methods
- Caller owns session lifecycle completely
- Services never open sessions, never commit
- No ambiguity about transaction ownership
- DTO consistency for API readiness

---

## Functional Requirements

### FR-1: Event Service Universal Session Requirement

**What it must do:**
- ALL event_service functions (~40+) MUST require `session` parameter
- Use provided session exclusively for all database operations
- Thread session to any downstream service calls
- Never open internal session_scope
- Never commit (caller owns transaction)

**Why this matters:**
- Planning/progress services need atomic event reads
- Cannot guarantee transactional consistency with optional sessions
- Ambiguity about who owns transaction causes bugs
- Per CLAUDE.md, session bugs caused silent data loss before

**Pattern reference:** Study batch_production_service.record_production for session threading discipline

**Success criteria:**
- [ ] ALL event_service functions require session parameter
- [ ] No internal session_scope usage
- [ ] No internal commits
- [ ] Session threaded to all downstream calls

---

### FR-2: Fix Batch Production Service Session Usage

**What it must do:**
- `get_production_history` MUST use provided session (currently ignores it)
- `get_production_run` MUST use provided session (currently ignores it)
- Ensure history queries participate in caller's transaction
- Never open internal session_scope
- Never commit (caller owns transaction)

**Why this matters:**
- History queries need transactional consistency with other operations
- Ignoring session creates stale read risks
- Multi-service queries need single transaction boundary

**Pattern reference:** Study record_production in same service - it correctly uses session; history queries must match

**Success criteria:**
- [ ] `get_production_history` uses provided session
- [ ] `get_production_run` uses provided session
- [ ] No internal session_scope
- [ ] No internal commits

---

### FR-3: Fix Assembly Service Session Usage

**What it must do:**
- `get_assembly_history` MUST use provided session (currently ignores it)
- `get_assembly_run` MUST use provided session (currently ignores it)
- Ensure history queries participate in caller's transaction
- Never open internal session_scope
- Never commit (caller owns transaction)

**Why this matters:**
- History queries need transactional consistency with other operations
- Ignoring session creates stale read risks
- Assembly workflows may span multiple services

**Pattern reference:** Study record_assembly in same service - it correctly uses session; history queries must match

**Success criteria:**
- [ ] `get_assembly_history` uses provided session
- [ ] `get_assembly_run` uses provided session
- [ ] No internal session_scope
- [ ] No internal commits

---

### FR-4: Production Service Session Completeness

**What it must do:**
- ALL production_service functions MUST require session parameter
- `get_production_progress` must accept and use session
- Thread session to all downstream service calls
- Never open internal session_scope
- Never commit (caller owns transaction)

**Why this matters:**
- Progress queries span multiple services (events, production, inventory)
- Atomic reads essential for accurate progress reporting
- Planning features will depend on production service primitives

**Success criteria:**
- [ ] ALL production_service functions require session
- [ ] `get_production_progress` uses session correctly
- [ ] Session threaded to downstream calls
- [ ] No internal session_scope

---

### FR-5: Progress Query Session Threading

**What it must do:**
- `get_events_with_progress` MUST require session parameter
- Thread session through entire call chain
- Use session for event queries and progress calculations
- Ensure atomic reads across multiple services
- Never open internal session_scope
- Never commit (caller owns transaction)

**Why this matters:**
- Progress spans events + production + assembly data
- Inconsistent reads produce incorrect progress percentages
- Planning UI will rely on accurate progress data

**Success criteria:**
- [ ] `get_events_with_progress` requires session
- [ ] Session threaded to event_service calls
- [ ] Session threaded to progress calculation calls
- [ ] Atomic consistency across all reads

---

### FR-6: DTO Type Standardization

**What it must do:**
- ALL service DTOs MUST return costs as strings (not Decimal objects)
- Standardize Decimal formatting for JSON serialization
- Document DTO type conventions
- Apply consistently across all services

**Why this matters:**
- Decimal objects aren't JSON-serializable
- Inconsistent types cause API integration bugs
- Future web/API exposure requires predictable types
- Prevents runtime serialization errors

**Business rules:**
- DTOs (for API/JSON) use string representation of Decimals
- Internal service calculations use Decimal objects
- Conversion happens at DTO boundary

**Success criteria:**
- [ ] All service DTOs return costs as strings
- [ ] Decimal formatting consistent (precision, rounding)
- [ ] DTO type conventions documented
- [ ] JSON serialization reliable

---

### FR-7: Structured Logging for Production/Assembly Operations

**What it must do:**
- Add structured logging to production operations
- Add structured logging to assembly operations
- Include key context: operation type, entity IDs, outcomes
- Enable debugging of multi-service transactions

**Why this matters:**
- Transaction bugs are hard to debug without operation context
- Multi-service workflows need trace of execution path
- Session-related issues require visibility into transaction boundaries

**Logging context must include:**
- Operation name
- Entity IDs (production_run_id, assembly_run_id, event_id)
- Key parameters (quantities, costs)
- Outcome (success, validation failure, error)

**Success criteria:**
- [ ] Production operations have structured logging
- [ ] Assembly operations have structured logging
- [ ] Logs include operation context
- [ ] Log format consistent across services

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ New planning features (depends on this foundation)
- ❌ New production features (depends on this foundation)
- ❌ UI changes (service layer only)
- ❌ Performance optimization (correctness first)
- ❌ Additional DTO fields beyond type standardization
- ❌ Comprehensive audit logging (just structured logs for debugging)
- ❌ Materials service hardening (separate feature)
- ❌ Backward compatibility with optional sessions (required sessions only)

**Rationale:** This spec focuses on completing session discipline and DTO consistency across existing services. New features build on this foundation AFTER it's solid. Required sessions eliminate ambiguity and prevent the bugs that caused silent data loss.

---

## Success Criteria

**Complete when:**

### Session Requirements Universal
- [ ] ALL service methods require session parameter
- [ ] NO service methods accept optional session
- [ ] NO internal session_scope in any service method
- [ ] NO internal commits in any service method
- [ ] Caller owns session lifecycle universally

### Event Service
- [ ] ALL functions (~40+) require session parameter
- [ ] ALL functions use provided session exclusively
- [ ] Session threaded to downstream calls

### Batch Production Service
- [ ] `get_production_history` requires and uses session
- [ ] `get_production_run` requires and uses session
- [ ] No ignored session parameters

### Assembly Service
- [ ] `get_assembly_history` requires and uses session
- [ ] `get_assembly_run` requires and uses session
- [ ] No ignored session parameters

### Production Service
- [ ] ALL functions require session parameter
- [ ] `get_production_progress` uses session correctly
- [ ] Session threaded to downstream calls

### Progress Queries
- [ ] `get_events_with_progress` requires session
- [ ] Atomic multi-service reads work correctly

### DTO Consistency
- [ ] All service DTOs return costs as strings
- [ ] Decimal formatting consistent
- [ ] JSON serialization reliable

### Logging
- [ ] Production operations logged with structure
- [ ] Assembly operations logged with structure
- [ ] Operation context included

### Quality
- [ ] No session boundary violations
- [ ] Pattern consistency across ALL services
- [ ] Test coverage for transaction scenarios
- [ ] All callers updated to pass required session
- [ ] Transaction ownership clear and explicit

---

## Architecture Principles

### Required Session Parameters

**Universal Pattern:**
- ALL service methods require `session` parameter (not optional)
- Caller opens session and passes to all service calls
- Services use provided session exclusively
- Services never open session_scope
- Services never commit (caller controls transaction)

**Why Required, Not Optional:**
- No ambiguity about who owns transaction
- Forces explicit transaction boundaries
- Prevents accidental session bugs
- Type system helps (Session vs Session | None)
- Desktop single-user app = complete control over all callers
- Not a library = no external consumers to worry about

**Rationale:** Optional sessions create ambiguity ("should I pass session?"). Required sessions make transaction ownership explicit at call site. Desktop context means we control all callers and can update them atomically.

---

### Caller Owns Session Lifecycle

**Transaction Boundaries:**
- UI/orchestration layer opens session
- Passes session to all service calls within transaction
- Commits or rolls back at end
- Services participate but don't control lifecycle

**Why This Matters:**
- Atomic multi-service operations need single session
- Planning/production workflows span many services
- Clear responsibility separation (orchestration vs primitives)

**Rationale:** Service layer provides atomic primitives. Orchestration layer (UI, planning facade, production coordinator) owns transaction boundaries and decides commit/rollback points.

---

### DTO Boundary Convention

**Service Layer Responsibilities:**
- Internal calculations use Decimal objects (precision)
- DTO conversion at service boundary (service → caller)
- DTOs use string representation for Decimals (JSON-safe)

**Conversion Pattern:**
```
Internal: Decimal calculations (preserve precision)
DTO: String representation (JSON-serializable)
```

**Rationale:** Decimals preserve precision in calculations but aren't JSON-serializable. Converting at DTO boundary keeps internal math precise while ensuring API safety for future web/API exposure.

---

## Constitutional Compliance

✅ **Principle I: User-Centric Design & Workflow Validation**
- Prevents silent data loss (documented pain point in CLAUDE.md)
- Enables reliable multi-step workflows
- Foundation for planning/production features

✅ **Principle II: Data Integrity & FIFO Accuracy**
- Required session parameters prevent partial writes
- Transaction guarantees maintain consistency
- FIFO operations require transactional context

✅ **Principle III: Future-Proof Schema, Present-Simple Implementation**
- Universal session pattern supports multi-user future
- DTO standardization enables API exposure
- No schema changes needed

✅ **Principle IV: Test-Driven Development**
- Session management is testable
- Transaction rollback scenarios can be verified
- Atomicity guarantees can be proven
- Required parameters caught by type system

✅ **Principle V: Layered Architecture Discipline**
- Service layer provides atomic primitives
- Orchestration layer owns session lifecycle
- DTO boundaries well-defined
- Clear separation of concerns

✅ **F060/F061: Architecture Hardening**
- Completes work started in F060/F061
- Universal application of established patterns
- Eliminates architectural inconsistencies
- Strengthens pattern (required vs optional)

---

## Risk Considerations

**Risk: 40+ event_service functions is large surface area**
- Context: Mechanical changes but many functions
- Impact: Large changeset increases review complexity
- Mitigation: Spec-kitty planning phase will identify systematic approach

**Risk: ALL callers must be updated to pass session**
- Context: Changing from optional to required changes call sites
- Impact: Every service caller needs updating
- Mitigation: Desktop app = complete control over callers; atomic update possible

**Risk: Ignored session parameters easy to miss**
- Context: Functions accept but don't use session (silent bug)
- Impact: Transaction guarantees silently broken
- Mitigation: Spec-kitty review phase will verify session usage patterns

**Risk: DTO changes may affect existing UI code**
- Context: Changing Decimal to string changes response format
- Impact: UI code expecting Decimal objects may break
- Mitigation: Desktop app only (no external API); safe to update UI atomically

**Risk: Regression in transaction behavior**
- Context: Per CLAUDE.md, session bugs caused silent data loss before
- Impact: New session bugs could cause data loss again
- Mitigation: Spec-kitty review phase requires transaction rollback testing

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study F060/F061 specs for session ownership principle
- Study Cursor review for specific gap locations
- Study batch_production_service.record_production for correct session usage
- Study batch_production_service.get_production_history for incorrect session usage (ignores parameter)
- Identify all event_service functions systematically
- Survey DTO return types across services

**Key Decision: Required Session Parameters**
- Desktop single-user app = control all callers
- Not a library = no external API consumers
- Required parameters eliminate ambiguity
- Type system enforces correct usage
- Cleaner pattern for future development

**Focus Areas:**
- Event service: Add required session to ~40+ functions
- Batch/assembly: Fix ignored session in history/run queries
- Production: Add required session to get_production_progress
- Progress queries: Add required session with threading
- DTOs: Standardize Decimal→string conversion
- Logging: Add structured context

**Critical Verification:**
- No internal session_scope when session required
- No internal commits in service methods
- All callers updated to pass session
- Transaction rollback testing comprehensive
- Multi-service atomicity verified

---

**END OF SPECIFICATION**
