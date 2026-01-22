# Implementation Plan: Service Session Consistency Hardening

**Branch**: `062-service-session-consistency-hardening` | **Date**: 2026-01-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/062-service-session-consistency-hardening/spec.md`

## Summary

Complete session discipline across ALL service layer functions to prevent silent data loss and enable reliable multi-service transactions. This feature:

1. Adds **required** `session` parameter to all ~40+ event_service functions
2. Fixes ignored session parameters in batch_production_service and assembly_service history queries
3. Adds session parameter to production_service.get_production_progress
4. Threads session through get_events_with_progress
5. Standardizes DTO cost format to 2-decimal strings
6. Adds structured logging for production/assembly operations
7. Updates all UI callers to pass session via context managers

**Implementation Approach**: Foundation-first - create session context managers in UI layer before updating services to require sessions. This ensures caller infrastructure is ready before services start requiring session parameters.

## Technical Context

**Language/Version**: Python 3.10+ (per constitution)
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter (per constitution)
**Storage**: SQLite with WAL mode (per constitution)
**Testing**: pytest (per constitution)
**Target Platform**: Desktop (Windows/macOS/Linux)
**Project Type**: Single project (desktop application)
**Performance Goals**: N/A (correctness over performance for this feature)
**Constraints**: Single-user desktop app; we control all callers
**Scale/Scope**: ~40+ event_service functions, 4 batch/assembly history functions, all UI callers

## Constitution Check

*GATE: Must pass before Phase 0 research.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Prevents silent data loss (documented pain point) |
| II. Data Integrity & FIFO | ✅ PASS | Required sessions ensure transactional consistency |
| III. Future-Proof Schema | ✅ PASS | No schema changes; patterns support web migration |
| IV. Test-Driven Development | ✅ PASS | Transaction rollback tests required |
| V. Layered Architecture | ✅ PASS | Reinforces service layer discipline |
| VI. Schema Change Strategy | ✅ PASS | No database changes |
| VII. Pragmatic Aspiration | ✅ PASS | Medium web migration cost (API-ready services) |

**Phase-Specific Gates (Desktop Phase)**:
- Does this design block web deployment? → **NO** (improves web readiness)
- Is the service layer UI-independent? → **YES** (reinforces separation)
- What's the web migration cost? → **MEDIUM** (services become API-ready)

## Project Structure

### Documentation (this feature)

```
kitty-specs/062-service-session-consistency-hardening/
├── spec.md              # Feature specification
├── plan.md              # This file
├── meta.json            # Feature metadata
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec quality validation
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── services/                    # PRIMARY TARGET
│   ├── event_service.py         # ~40+ functions need session param
│   ├── batch_production_service.py  # Fix ignored session in history queries
│   ├── assembly_service.py      # Fix ignored session in history queries
│   ├── production_service.py    # Add session to get_production_progress
│   └── database.py              # session_scope context manager (reference)
├── ui/                          # CALLER UPDATES
│   ├── frames/                  # UI frames that call services
│   └── dialogs/                 # UI dialogs that call services
└── tests/
    └── services/                # Test updates for session params
```

**Structure Decision**: Existing single-project structure. Changes are refactoring within `src/services/` and `src/ui/` directories.

## Implementation Strategy

### Foundation-First Approach (User Choice: Option C)

The implementation follows a foundation-first strategy:

1. **Wave 0: UI Session Infrastructure** (Foundation)
   - Create session context manager utilities in UI layer
   - Establish pattern for UI frames/dialogs to manage session lifecycle
   - This provides the infrastructure for callers before services require sessions

2. **Wave 1: Service Layer Hardening** (Core Work)
   - Update services to require session parameter
   - Fix ignored session parameters
   - Remove internal session_scope() calls
   - Update tests

3. **Wave 2: DTO Consistency & Observability** (Polish)
   - Standardize cost format to 2-decimal strings
   - Add structured logging

### Dependency Graph

```
Wave 0: UI Foundation (must complete first)
    └─► UI session context manager utilities

Wave 1: Service Layer (can parallelize after Wave 0)
    ├─► WP: Event service session hardening (largest)
    ├─► WP: Batch production service fixes
    ├─► WP: Assembly service fixes
    └─► WP: Production service fixes

Wave 2: Polish (after Wave 1 complete)
    ├─► WP: DTO cost standardization
    └─► WP: Structured logging
```

### Key Technical Decisions

**D1: Required vs Optional Session Parameters**
- **Decision**: Required (not optional)
- **Rationale**: Desktop app = control all callers; eliminates ambiguity about transaction ownership; type system catches missing args

**D2: Session Context Manager Pattern**
- **Decision**: Create `with session_context() as session:` utility in UI layer
- **Rationale**: Consistent pattern across all UI callers; easy to audit; clear ownership

**D3: Cost Decimal Formatting**
- **Decision**: 2 decimal places, standard rounding
- **Rationale**: User-confirmed during spec phase; standard currency formatting

**D4: Logging Format**
- **Decision**: Python stdlib logging with structured context dict
- **Rationale**: Consistent with existing codebase; no new dependencies

## Complexity Tracking

*No constitution violations identified. No complexity justification needed.*

## Files Requiring Changes

### Services (Primary Targets)

| File | Changes | Scope |
|------|---------|-------|
| `src/services/event_service.py` | Add required session to ~40+ functions, remove internal session_scope | Large |
| `src/services/batch_production_service.py` | Fix get_production_history, get_production_run to use session | Small |
| `src/services/assembly_service.py` | Fix get_assembly_history, get_assembly_run to use session | Small |
| `src/services/production_service.py` | Add session to all functions including get_production_progress | Medium |

### UI Layer (Callers)

| Pattern | Files | Changes |
|---------|-------|---------|
| Event management frames | `src/ui/frames/event_*.py` | Add session context managers |
| Production frames | `src/ui/frames/production_*.py` | Add session context managers |
| Planning frames | `src/ui/frames/planning_*.py` | Add session context managers |
| Dialogs | `src/ui/dialogs/*.py` | Add session context managers |

### Tests

| File Pattern | Changes |
|--------------|---------|
| `src/tests/test_event_service.py` | Update all tests to pass session |
| `src/tests/test_production_*.py` | Update tests, add rollback scenarios |
| `src/tests/test_assembly_*.py` | Update tests, add rollback scenarios |

## Research Assessment

**Phase 0 Research Required**: Minimal

The patterns for this feature are already established:
- Session ownership pattern documented in CLAUDE.md
- F060/F061 established session threading discipline
- `batch_production_service.record_production` demonstrates correct pattern
- `batch_production_service.get_production_history` demonstrates incorrect pattern (bug to fix)

**Research Tasks**:
1. Enumerate all event_service functions requiring changes
2. Identify all UI callers that need session context managers
3. Survey existing DTO cost return types for standardization scope

These are discovery tasks, not research tasks. They will be performed during task decomposition.

## Parallel Work Analysis

### Agent Assignments

Given the scope (40+ functions in event_service alone), this feature benefits from parallel work:

**Lead Agent (Claude Code)**:
- WP01: UI session infrastructure
- WP02: Event service hardening (largest, most critical)
- Integration verification

**Parallel Agent (Gemini)**:
- WP03-05: Smaller service fixes (batch_production, assembly, production)
- WP06-07: DTO standardization and logging

### Coordination Points

- **After WP01**: UI infrastructure must be complete before service changes
- **After WP02-05**: All services updated; integration test point
- **After WP06-07**: Polish complete; final validation

### File Boundaries (Conflict Prevention)

- Lead agent owns: `event_service.py`, `src/ui/`
- Parallel agent owns: `batch_production_service.py`, `assembly_service.py`, `production_service.py`
- Shared: Test files (coordinate via WP dependencies)

---

## Next Steps

**This plan is complete.**

Run `/spec-kitty.tasks` to generate work packages.
