# Implementation Plan: Enhanced Export/Import System

**Branch**: `030-enhanced-export-import` | **Date**: 2025-12-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/030-enhanced-export-import/spec.md`

## Summary

Implement a coordinated export/import system with:
1. **Normalized exports** - Individual entity files with manifest, checksums, and dependency ordering
2. **Denormalized views** - AI-friendly exports (view_products.json, etc.) for external augmentation
3. **Interactive FK resolution** - When importing data with missing FKs, prompt user to create/map/skip
4. **Skip-on-error mode** - Import valid records, log skipped records for later

Architecture derived from codebase analysis (not design doc). Parallel work split: Export services (Gemini) / Import services (Claude).

## Technical Context

**Language/Version**: Python 3.10+ (per constitution)
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter, pytest
**Storage**: SQLite with WAL mode (existing)
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (macOS/Windows)
**Project Type**: Single desktop application
**Performance Goals**: <10 seconds for 1,000 record import (SC-005)
**Constraints**: Single-user, local database, no network dependencies
**Scale/Scope**: ~1,000 records typical, 10,000 max target

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Feature solves real user pain (manual entity creation cycle) |
| II. Data Integrity & FIFO | PASS | No changes to FIFO logic; import validates FK integrity |
| III. Future-Proof Schema | PASS | No schema changes; uses slug-based resolution |
| IV. Test-Driven Development | PASS | Services will have tests; UI tested via user flows |
| V. Layered Architecture | PASS | UI → Services → Models; FK resolver is pure service |
| VI. Schema Change Strategy | N/A | No schema changes |
| VII. Pragmatic Aspiration | PASS | Slug-based FKs support web migration |

**Re-check after Phase 1**: All principles still satisfied.

## Project Structure

### Documentation (this feature)

```
kitty-specs/030-enhanced-export-import/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Codebase research findings
├── data-model.md        # File formats and interfaces
├── research/
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks.md             # Task breakdown (Phase 2)
```

### Source Code (repository root)

```
src/
├── services/
│   ├── coordinated_export_service.py   # NEW: Gemini
│   ├── denormalized_export_service.py  # NEW: Gemini
│   ├── enhanced_import_service.py      # NEW: Claude
│   ├── fk_resolver_service.py          # NEW: Claude
│   ├── import_export_service.py        # EXISTING: reference only
│   └── catalog_import_service.py       # EXISTING: pattern source
├── ui/
│   ├── fk_resolution_dialog.py         # NEW: Claude
│   ├── import_export_dialog.py         # MODIFY: add view import
│   └── main_window.py                  # MODIFY: add menu item
├── utils/
│   └── import_export_cli.py            # MODIFY: add new commands
└── tests/
    └── services/
        ├── test_coordinated_export.py  # NEW: Gemini
        ├── test_denormalized_export.py # NEW: Gemini
        ├── test_enhanced_import.py     # NEW: Claude
        └── test_fk_resolver.py         # NEW: Claude
```

**Structure Decision**: Follows existing single-project layout. New services added to `src/services/`, new UI to `src/ui/`, CLI extended in `src/utils/`.

## Parallel Work Strategy

| Work Package | Owner | Dependencies | Files |
|--------------|-------|--------------|-------|
| WP1: Coordinated Export Service | Gemini | None | `coordinated_export_service.py`, tests |
| WP2: Denormalized Export Service | Gemini | None | `denormalized_export_service.py`, tests |
| WP3: Export CLI Commands | Gemini | WP1, WP2 | `import_export_cli.py` (export parts) |
| WP4: FK Resolver Service | Claude | None | `fk_resolver_service.py`, tests |
| WP5: Enhanced Import Service | Claude | WP4 | `enhanced_import_service.py`, tests |
| WP6: Import CLI Commands | Claude | WP5 | `import_export_cli.py` (import parts) |
| WP7: FK Resolution Dialog | Claude | WP4 | `fk_resolution_dialog.py` |
| WP8: UI Integration | Claude | WP5, WP7 | `import_export_dialog.py`, `main_window.py` |

**Parallel Tracks**:
- Track A (Gemini): WP1 → WP2 → WP3
- Track B (Claude): WP4 → WP5 → WP6 → WP7 → WP8

WP1-WP3 and WP4-WP5 can run in parallel. WP6-WP8 depend on import service completion.

## Implementation Phases

### Phase 0: Research (COMPLETE)

See [research.md](research.md) for detailed findings.

**Key Decisions**:
1. Use `catalog_import_service.py` patterns (session=None, structured errors)
2. Extend existing CLI rather than create new
3. FK resolution via slug/name, not ID
4. Composite key for Product matching

### Phase 1: Design & Contracts

**Core Interfaces** (see [data-model.md](data-model.md)):

1. **ExportManifest** dataclass:
   - files: List[FileEntry] with checksums, counts, dependencies
   - version, export_date, source

2. **FKResolver Protocol**:
   - `resolve(missing: MissingFK) -> Resolution`
   - ResolutionChoice: CREATE, MAP, SKIP

3. **EnhancedImportResult**:
   - Extends existing ImportResult
   - Adds resolution tracking, created/mapped counts

**File Formats**:
- `manifest.json` - Export set metadata
- `{entity}.json` - Normalized entity files with FK resolution fields
- `view_{entity}.json` - Denormalized views with editable/readonly metadata
- `import_skipped_{timestamp}.json` - Skipped records log

### Phase 2: Task Breakdown

*Generated by `/spec-kitty.tasks` command*

See [tasks.md](tasks.md) after running task generation.

## Complexity Tracking

No Constitution violations. No complexity justifications needed.

## Testing Strategy

| Layer | Coverage Target | Focus |
|-------|-----------------|-------|
| Services | >70% | FK resolution, mode handling, edge cases |
| CLI | Smoke tests | Command parsing, flag combinations |
| UI | Manual | Dialog flows, error states |
| Integration | Round-trip | Export → Import produces identical data |

**Key Test Scenarios**:
1. Export/import round-trip with all entities
2. Import with missing FK - each resolution type
3. Import with duplicate slugs
4. Checksum mismatch handling
5. User cancellation mid-resolution
6. Unknown fields in import file
7. Dry-run mode (no DB changes)
8. Skip-on-error with partial success

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Product ambiguity | Medium | Medium | Warn on multiple matches, skip |
| Large file performance | Low | Medium | Defer optimization post-MVP |
| Session detachment | High | High | Follow session=None pattern strictly |
| UI complexity | Medium | Medium | Reuse existing dialog patterns |

## Success Criteria Mapping

| Spec Criterion | Implementation | Verification |
|----------------|----------------|--------------|
| SC-001: <5 min cycle | CLI export + import | Manual timing |
| SC-002: <2 sec FK prompt | UI responsiveness | Manual testing |
| SC-003: 95% resolution coverage | Create/Map/Skip options | Code review |
| SC-004: Round-trip identical | Integration test | Automated test |
| SC-005: <10 sec for 1k records | Performance test | Automated benchmark |
| SC-006: 20% FK error tolerance | Skip-on-error test | Automated test |
| SC-007: Actionable skip log | Log format review | Code review |

## Next Steps

1. Run `/spec-kitty.tasks` to generate work packages
2. Delegate export work packages (WP1-WP3) to Gemini
3. Begin import work packages (WP4-WP8) sequentially
4. Integration testing after both tracks complete
