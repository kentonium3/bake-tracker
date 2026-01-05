# Implementation Plan: Recipe Template & Snapshot System

**Branch**: `037-recipe-template-snapshot` | **Date**: 2026-01-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/037-recipe-template-snapshot/spec.md`

## Summary

Implement a Template/Snapshot architecture to preserve historical recipe state at production time. This solves four critical issues: (1) recipe versioning for historical accuracy, (2) base/variant relationships for recipe families, (3) two-parameter batch scaling (num_batches × scale_factor), and (4) production readiness filtering.

**Key Decisions**:
- Full denormalization: Snapshots are self-contained with all recipe data as JSON
- Migration: Backfill existing production runs with is_backfilled flag
- Variant UI: Indented list consistent with ingredient hierarchy patterns

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (macOS/Windows)
**Project Type**: Single desktop application
**Performance Goals**: Recipe history loads within 2 seconds for 100+ snapshots
**Constraints**: Single-user desktop app, offline-capable
**Scale/Scope**: ~100 recipes, ~500 production runs expected

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Snapshots are transparent; user doesn't manage versions manually |
| II. Data Integrity & FIFO | PASS | Snapshots preserve historical accuracy; FIFO unchanged |
| III. Future-Proof Schema | PASS | JSON storage allows evolution; variant FK enables family tracking |
| IV. Test-Driven Development | PASS | New service functions require unit tests |
| V. Layered Architecture | PASS | Snapshot logic in services; UI only displays |
| VI. Schema Change Strategy | PASS | Migration via backfill; export/import available |
| VII. Pragmatic Aspiration | PASS | No web-blocking changes; service layer remains UI-independent |

## Project Structure

### Documentation (this feature)

```
kitty-specs/037-recipe-template-snapshot/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output (complete)
├── data-model.md        # Phase 1 output (complete)
├── quickstart.md        # Phase 1 output (complete)
├── research/
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks.md             # Phase 2 output (from /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── recipe.py           # MODIFY: Add base_recipe_id, variant_name, is_production_ready
│   ├── recipe_snapshot.py  # NEW: RecipeSnapshot model
│   ├── production_run.py   # MODIFY: Add recipe_snapshot_id FK
│   └── __init__.py         # MODIFY: Export RecipeSnapshot
├── services/
│   ├── recipe_service.py   # MODIFY: Add snapshot functions, variant queries
│   ├── recipe_snapshot_service.py  # NEW: Snapshot CRUD
│   └── batch_production_service.py # MODIFY: Create snapshot before production
├── ui/
│   ├── recipes_tab.py      # MODIFY: Variant indentation, readiness filter
│   ├── forms/
│   │   ├── recipe_form.py           # MODIFY: Add variant fields, readiness checkbox
│   │   └── record_production_dialog.py  # MODIFY: Add scale_factor input
│   └── views/
│       └── recipe_history_view.py   # NEW: Snapshot history display
└── tests/
    ├── services/
    │   ├── test_recipe_service.py        # EXTEND: Variant, readiness tests
    │   ├── test_recipe_snapshot_service.py  # NEW: Snapshot tests
    │   └── test_batch_production_service.py # EXTEND: Snapshot integration tests
    └── models/
        └── test_recipe_snapshot_model.py # NEW: Model tests
```

**Structure Decision**: Single desktop project with layered architecture (Models → Services → UI)

## Implementation Phases

*Note: Work packages consolidated during `/spec-kitty.tasks` for optimal grouping and parallelization.*

### Phase 1: Core Snapshot System (P1 User Stories 1-2)

**Goal**: Historical production costs remain accurate when recipes change.

**Work Packages**:

1. **WP01: Models Layer** (Foundational)
   - Create `src/models/recipe_snapshot.py` with RecipeSnapshot model
   - Fields: recipe_id, production_run_id, scale_factor, snapshot_date, recipe_data (JSON), ingredients_data (JSON), is_backfilled
   - Constraints: RESTRICT on recipe delete, UNIQUE on production_run_id
   - Add to Recipe: base_recipe_id (nullable FK), variant_name, is_production_ready
   - CHECK constraint: base_recipe_id != id, ON DELETE SET NULL for base_recipe_id
   - Add recipe_snapshot_id FK to ProductionRun
   - Tests: Model creation, JSON serialization, constraint enforcement

2. **WP02: Snapshot Service** [Depends on WP01]
   - Create `src/services/recipe_snapshot_service.py`
   - `create_recipe_snapshot(recipe_id, scale_factor, production_run_id, session=None)`
   - `get_recipe_snapshots(recipe_id)` - history list
   - `get_snapshot_by_production_run(production_run_id)`
   - Follow session=None pattern from CLAUDE.md
   - Tests: Snapshot creation, retrieval, immutability verification

3. **WP03: Production Integration** [Depends on WP02]
   - Modify `record_batch_production()` to create snapshot FIRST
   - Add scale_factor parameter to production flow
   - Update ProductionRun to reference recipe_snapshot_id
   - Tests: Integration with FIFO consumption, snapshot linkage

4. **WP04: Migration Script** [Depends on WP03]
   - Create `scripts/migrate_production_snapshots.py`
   - Backfill snapshots for existing ProductionRuns
   - Set is_backfilled=True for migrated data
   - Support --dry-run for validation
   - Tests: Migration with sample data, idempotency

### Phase 2: Scaling & Variants (P2 User Stories 3-4)

**Goal**: Support batch scaling and recipe variant relationships.

**Work Packages**:

5. **WP05: Scale Factor UI** [Depends on WP03, PARALLEL with WP04]
   - Add scale_factor input to RecordProductionDialog
   - Calculate: expected_yield = base × scale_factor × num_batches
   - Display ingredient requirements scaled
   - Validation: scale_factor > 0
   - Tests: UI validation, calculation accuracy

6. **WP06: Variant Service & UI** [Depends on WP01, PARALLEL with WP02]
   - `get_recipe_variants(base_recipe_id)`
   - `create_recipe_variant(base_recipe_id, variant_name, copy_ingredients=True)`
   - Extend `get_all_recipes()` to group variants under base
   - Recipe form: base_recipe dropdown, variant_name field
   - Recipe list: Indent variants under base with "└─" prefix
   - Tests: Variant queries, orphaning on base delete, UI display

### Phase 3: Production Readiness & History (P3 User Stories 5-6)

**Goal**: Filter experimental recipes and view recipe history.

**Work Packages**:

7. **WP07: Production Readiness** [Depends on WP01, PARALLEL with WP02, WP06]
   - Add is_production_ready checkbox to recipe form (default: unchecked)
   - Add filter dropdown to recipes_tab: "All" | "Production Ready" | "Experimental"
   - New recipes default to experimental (not production ready)
   - Tests: Toggle persistence, filter accuracy

8. **WP08: Recipe History View** [Depends on WP02]
   - Create `src/ui/views/recipe_history_view.py`
   - Display snapshot list: date, scale_factor, "(approximated)" badge for backfilled
   - "View Details" shows denormalized ingredient data
   - "Restore as New Recipe" creates new recipe from snapshot
   - Add `create_recipe_from_snapshot()` service function
   - Tests: History display, restoration accuracy

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| JSON columns in SQLite | Schema flexibility for denormalized snapshot data | Fixed columns would require schema changes when recipe structure evolves |
| New RecipeSnapshot table | Historical accuracy requires immutable records | Versioning Recipe rows would complicate queries and allow mutation |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Migration fails for existing data | Low | High | Dry-run mode, backup before migration |
| Session management bugs | Medium | High | Follow CLAUDE.md patterns, thorough testing |
| JSON parsing errors | Low | Medium | Schema validation, error handling |
| UI complexity with variants | Medium | Low | Indented list simpler than tree widget |

## Dependencies

- **Requires Complete**: F031-F036 Ingredient Hierarchy (for leaf-only validation)
- **Blocks**: F039 Planning Workspace (requires recipe scaling and variants)

## Success Metrics

- SC-001: Historical costs unchanged after recipe modification (100%)
- SC-002: Production run creation under 30 seconds
- SC-003: Variants correctly grouped in UI
- SC-004: Production readiness filter accurate (no false positives)
- SC-005: Recipe history loads within 2 seconds
- SC-006: Zero errors on existing production data post-migration
- SC-007: 100% service tests passing
