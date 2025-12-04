# Implementation Plan: Event Planning Restoration

**Branch**: `006-event-planning-restoration` | **Date**: 2025-12-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/006-event-planning-restoration/spec.md`

## Summary

Reimplement the gift planning subsystem (Package, Event model chain) that was disabled during Phase 4 refactoring. Adapt to the new FinishedGood/FinishedUnit architecture where FinishedGood serves as an assembly container. Integrate with FIFO-based recipe costing from Feature 005.

**Key Architecture Decision**: Eliminate Bundle concept. Package directly references FinishedGood assemblies via new PackageFinishedGood junction table.

## Technical Context

**Language/Version**: Python 3.10+ (minimum for type hints)
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x, SQLite with WAL mode
**Storage**: SQLite local database (existing schema)
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (macOS/Windows/Linux)
**Project Type**: Single desktop application
**Performance Goals**: <2s load time for EventDetailWindow tabs with 50 assignments
**Constraints**: Single-user, offline-capable, FIFO accuracy required
**Scale/Scope**: ~100 events, ~500 recipients, ~50 packages typical usage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | PASS | UI -> Services -> Models -> Database. No cross-layer violations planned. |
| II. Build for Today | PASS | Single-user desktop focus. UUID fields already in BaseModel for future-proofing. |
| III. FIFO Accuracy | PASS | All cost calculations use RecipeService.calculate_actual_cost() (FR-028) |
| IV. User-Centric Design | PASS | Restores core gift planning workflow the primary user needs |
| V. Test-Driven Development | PASS | Service contracts define test requirements; >70% coverage target |
| VI. Migration Safety | PASS | New table (package_finished_goods) only; no data migration needed (clean slate) |

**Gate Status**: PASSED - Ready for implementation planning.

## Project Structure

### Documentation (this feature)

```
kitty-specs/006-event-planning-restoration/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity relationships
├── quickstart.md        # Usage examples
├── contracts/           # Service contracts
│   ├── package_service.md
│   ├── event_service.md
│   └── recipient_service.md
├── research/            # Research artifacts
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks.md             # Phase 2 output (via /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── __init__.py          # Re-enable Event, Package; add PackageFinishedGood
│   ├── event.py             # Event, EventRecipientPackage (re-enable)
│   ├── package.py           # Package (modify), PackageFinishedGood (new)
│   └── recipient.py         # Already enabled
├── services/
│   ├── event_service.py     # Rewrite (remove Bundle references)
│   ├── package_service.py   # Rewrite (use FinishedGood)
│   └── recipient_service.py # Verify functional
└── ui/
    ├── events_tab.py        # Restore/update
    ├── packages_tab.py      # Restore/update
    ├── recipients_tab.py    # Verify functional
    └── event_detail_window.py  # Restore (4 tabs)

tests/
├── unit/
│   ├── test_package_service.py
│   ├── test_event_service.py
│   └── test_recipient_service.py
└── integration/
    └── test_event_planning_workflow.py
```

**Structure Decision**: Standard single project layout per existing codebase structure.

## Research Summary

Phase 0 research (see [research.md](research.md)) revealed:

### Key Findings
- Models exist but are DISABLED in `__init__.py` due to removed Bundle dependency
- Bundle model was completely removed - does not exist
- FinishedGood repurposed as "assembly" (contains FinishedUnits)
- FinishedUnit is the new "individual item" model
- Services (event_service.py, package_service.py) import non-existent Bundle - broken

### Key Decisions
- **D1**: Eliminate Bundle concept - Package references FinishedGood directly
- **D2**: Create PackageFinishedGood junction (replaces PackageBundle)
- **D3**: Use RecipeService.calculate_actual_cost() for FIFO costing
- **D4**: Reimplement services from scratch (not repair broken ones)

## Implementation Phases

### Phase 1: Models Layer
1. Create PackageFinishedGood junction model
2. Update Package model to use PackageFinishedGood relationship
3. Re-enable Event and EventRecipientPackage in __init__.py
4. Verify Recipient model functional (already enabled)

### Phase 2: Services Layer
1. Implement PackageService (contracts/package_service.md)
2. Implement EventService (contracts/event_service.md)
3. Verify/update RecipientService (contracts/recipient_service.md)
4. Write unit tests (>70% coverage)

### Phase 3: Integration
1. Integration tests for cost calculation chain
2. Verify FIFO accuracy (SC-002)
3. Shopping list shortfall calculations (SC-003)

### Phase 4: UI Layer
1. Restore/update Packages tab
2. Restore/update Events tab
3. Verify Recipients tab
4. Restore EventDetailWindow with 4 tabs:
   - Assignments tab
   - Recipe Needs tab
   - Shopping List tab
   - Summary tab

## Database Changes

### New Table: package_finished_goods

```sql
CREATE TABLE package_finished_goods (
    id INTEGER PRIMARY KEY,
    package_id INTEGER NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
    finished_good_id INTEGER NOT NULL REFERENCES finished_goods(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL DEFAULT 1,
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_modified DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_package_fg_package ON package_finished_goods(package_id);
CREATE INDEX idx_package_fg_finished_good ON package_finished_goods(finished_good_id);
```

### No Migration Needed
- Clean slate confirmed - no existing data to preserve
- Tables events, recipients, packages should exist from Phase 3b schema
- Only new table creation required

## Complexity Tracking

*No constitution violations to justify.*

| Aspect | Approach | Rationale |
|--------|----------|-----------|
| Bundle elimination | Replace with FinishedGood | Simpler model, FinishedGood assemblies already serve this purpose |
| Service rewrite | Fresh implementation | Broken imports make repair more complex than rewrite |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| FIFO cost chain not integrated | Test with multi-batch scenarios, verify against RecipeService |
| UI references obsolete patterns | Rewrite UI components following current patterns |
| Performance with 50+ assignments | Eager load relationships, consider pagination if needed |

## Next Steps

Run `/spec-kitty.tasks` to generate work packages for implementation.
