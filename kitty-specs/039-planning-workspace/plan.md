# Implementation Plan: Planning Workspace

**Branch**: `039-planning-workspace` | **Date**: 2026-01-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/039-planning-workspace/spec.md`
**Dependencies**: F037 (Recipe Redesign), F038 (UI Mode Restructure) - both merged to main

## Summary

Automatic batch calculation system to prevent underproduction during holiday baking. The system explodes bundle requirements to unit quantities, calculates optimal batches (never short, minimize waste under 15% threshold), aggregates ingredients with inventory gap analysis, validates assembly feasibility, and tracks progress through shopping/production/assembly phases.

**Technical Approach**: Hybrid service architecture with `PlanningService` facade delegating to focused modules. Wizard-style UI with sidebar showing phase status. Timestamp-based staleness detection for persisted plan snapshots.

## Technical Context

**Language/Version**: Python 3.10+ (type hints, match statements)
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode (local desktop database)
**Testing**: pytest with >70% service layer coverage requirement
**Target Platform**: Desktop (Windows/macOS/Linux via PyInstaller)
**Project Type**: Single desktop application
**Performance Goals**: Plan calculation <500ms for 10+ recipes (SC-002)
**Constraints**: Single-user, offline-capable, intuitive for non-technical user
**Scale/Scope**: Single event at a time, ~10-20 recipes, ~50-100 bundles per event

## Engineering Decisions (from Planning Interrogation)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Staleness Detection** | Timestamp-based | Compare `plan.calculated_at` vs `updated_at` on recipes/bundles/requirements |
| **Service Architecture** | Hybrid facade | `PlanningService` delegates to focused modules (batch calc, shopping, feasibility, progress) |
| **UI Structure** | Wizard-style sidebar | Phase status indicators + main content area; guided-but-flexible navigation |
| **Workflow Model** | Flexible with warnings | Free navigation between phases; contextual warnings for incomplete prerequisites |
| **Plan Persistence** | Persisted snapshot | Store calculation results; show "stale" warning when inputs change |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Wizard UI matches natural planning workflow; solves real underproduction problem |
| II. Data Integrity & FIFO | PASS | Feature reads inventory but doesn't modify FIFO logic; uses existing services |
| III. Future-Proof Schema | PASS | ProductionPlanSnapshot uses nullable fields; timestamp staleness is web-compatible |
| IV. Test-Driven Development | PASS | Each service module independently testable; >70% coverage required |
| V. Layered Architecture | PASS | UI -> PlanningService facade -> Modules -> Models; no cross-layer violations |
| VI. Schema Change Strategy | PASS | New model added; export/reset/import cycle handles schema change |
| VII. Pragmatic Aspiration | PASS | Desktop-first; service layer enables future API wrapper for web |

**Constitution Check Result: PASS** - No violations requiring justification.

## Project Structure

### Documentation (this feature)

```
kitty-specs/039-planning-workspace/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal service contracts)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── production_plan_snapshot.py   # NEW: Persisted plan entity
│   ├── event.py                      # MODIFY: Add output_mode, updated_at
│   ├── event_assembly_target.py      # EXISTS: Bundle requirements
│   ├── event_production_target.py    # EXISTS: Unit requirements (BULK_COUNT)
│   ├── finished_good.py              # EXISTS: Bundle definitions
│   ├── composition.py                # EXISTS: Bundle contents
│   ├── finished_unit.py              # EXISTS: Product variants
│   └── recipe.py                     # EXISTS: Production templates (single yield per recipe)
├── services/
│   ├── planning/                     # NEW: Planning subsystem
│   │   ├── __init__.py               # Exports PlanningService facade
│   │   ├── planning_service.py       # Facade orchestrating modules
│   │   ├── batch_calculation.py      # Batch optimization logic
│   │   ├── shopping_list.py          # Ingredient aggregation
│   │   ├── feasibility.py            # Assembly feasibility checks
│   │   └── progress.py               # Progress tracking
│   └── [existing services]
├── ui/
│   └── planning/                     # NEW: Planning UI components
│       ├── __init__.py
│       ├── planning_workspace.py     # Main wizard container
│       ├── phase_sidebar.py          # Phase navigation sidebar
│       ├── calculate_view.py         # Calculate phase UI
│       ├── shop_view.py              # Shopping phase UI
│       ├── produce_view.py           # Production phase UI
│       └── assemble_view.py          # Assembly phase UI
└── tests/
    ├── services/
    │   └── planning/                 # NEW: Planning service tests
    │       ├── test_batch_calculation.py
    │       ├── test_shopping_list.py
    │       ├── test_feasibility.py
    │       └── test_progress.py
    └── ui/
        └── planning/                 # NEW: Planning UI tests (if needed)
```

**Structure Decision**: Single desktop application with existing layered structure. New `planning/` subdirectories under `services/` and `ui/` to contain feature-specific code. Hybrid service architecture with facade pattern.

## Complexity Tracking

*No violations requiring justification - Constitution Check passed.*

---

## Phase 0: Research Summary

### Critical Finding: Spec Adjustment Required

**Issue**: Spec assumes `RecipeYieldOption` model with multiple yield options per recipe (FR-011). Actual codebase has single `yield_quantity` per Recipe.

**Resolution**: Simplify batch calculation to use single yield per recipe. Defer yield option optimization to Phase 3+. Update spec FR-011 accordingly.

### Existing Service Reuse

Many required functions already exist in `event_service`:
- `get_shopping_list(event_id)` - Shopping list with inventory comparison
- `get_production_progress(event_id)` - Production progress tracking
- `get_assembly_progress(event_id)` - Assembly progress tracking
- `set_production_target()` / `set_assembly_target()` - Target management

PlanningService will wrap/extend these rather than reimplementing.

### Model Changes Required

1. **Add `Event.output_mode`** - Enum field (BUNDLED, BULK_COUNT)
2. **Create `ProductionPlanSnapshot`** - Persisted plan with staleness detection

See [research.md](./research.md) and [data-model.md](./data-model.md) for details.

---

## Phase 1: Design Artifacts

| Artifact | Status | Path |
|----------|--------|------|
| research.md | Complete | `kitty-specs/039-planning-workspace/research.md` |
| data-model.md | Complete | `kitty-specs/039-planning-workspace/data-model.md` |
| quickstart.md | Complete | `kitty-specs/039-planning-workspace/quickstart.md` |
| contracts/planning_service.py | Complete | `kitty-specs/039-planning-workspace/contracts/planning_service.py` |
| evidence-log.csv | Complete | `kitty-specs/039-planning-workspace/research/evidence-log.csv` |
| source-register.csv | Complete | `kitty-specs/039-planning-workspace/research/source-register.csv` |

---

## Parallelization Strategy (for Gemini)

After models are defined, these work packages can be parallelized:

**Safe to parallelize:**
- `batch_calculation.py` (no shared state)
- `shopping_list.py` (wraps existing service)
- `feasibility.py` (read-only checks)
- `progress.py` (wraps existing service)

**Safe to parallelize (after services):**
- `calculate_view.py`, `shop_view.py`, `produce_view.py`, `assemble_view.py`

**Must be sequential:**
- Model definitions (foundation)
- `planning_service.py` facade (imports modules)
- `planning_workspace.py` container (integrates views)

---

## Next Steps

1. Run `/spec-kitty.tasks` to generate work packages
2. Implement in order: Models -> Services -> UI
3. Use Gemini for parallelizable service modules after models complete
