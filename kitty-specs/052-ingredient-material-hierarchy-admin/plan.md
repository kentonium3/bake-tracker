# Implementation Plan: Ingredient & Material Hierarchy Admin

**Branch**: `052-ingredient-material-hierarchy-admin` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/052-ingredient-material-hierarchy-admin/spec.md`

## Summary

Implement L2-only display for Ingredients/Materials tabs with parent context columns, plus a reusable Hierarchy Admin UI for add/rename/reparent operations. The admin UI will be a single configurable component that works for both Ingredients (L0/L1/L2) and Materials (Category/Subcategory/Material) hierarchies.

**Parallelization Strategy**: Display changes for Ingredients and Materials tabs can be developed in parallel (separate UI files). Service layer changes can also be parallelized. The shared Hierarchy Admin component is sequential but serves both entity types.

## Technical Context

**Language/Version**: Python 3.10+ (per constitution)
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage (per constitution)
**Target Platform**: Desktop (Windows/macOS)
**Project Type**: Single desktop application
**Performance Goals**: Admin operations complete in <30 seconds (per SC-003, SC-005)
**Constraints**: Single-user desktop app, no concurrent edit handling needed
**Scale/Scope**: ~100 ingredients, ~50 materials in typical catalog

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Solves real user complaint (mixed L1/L2 confusion). UI must be intuitive. |
| II. Data Integrity & FIFO | ✅ PASS | No FIFO impact. Renames propagate to display only; FKs unchanged. Historical snapshots preserved. |
| III. Future-Proof Schema | ✅ PASS | Using existing schema fields (hierarchy_level, parent_ingredient_id). No schema changes needed. |
| IV. Test-Driven Development | ✅ PASS | Service layer methods will have unit tests. >70% coverage required. |
| V. Layered Architecture | ✅ PASS | UI calls services; services call models. No cross-layer violations. |
| VI. Schema Change Strategy | ✅ PASS | No schema changes required. |
| VII. Pragmatic Aspiration | ✅ PASS | Desktop-focused; service layer is API-ready for web phase. |

**No constitution violations. Proceeding to Phase 0.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/052-ingredient-material-hierarchy-admin/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── tasks.md             # Phase 2 output (via /spec-kitty.tasks)
└── tasks/               # Work package prompts
```

### Source Code (repository root)

```
src/
├── models/
│   ├── ingredient.py          # Existing - has hierarchy_level, parent_ingredient_id
│   ├── material.py            # Existing - leaf materials
│   ├── material_category.py   # Existing - L0 equivalent
│   └── material_subcategory.py # Existing - L1 equivalent
├── services/
│   ├── ingredient_hierarchy_service.py  # NEW - hierarchy operations for ingredients
│   ├── material_hierarchy_service.py    # NEW - hierarchy operations for materials
│   └── hierarchy_admin_service.py       # NEW - shared admin logic (usage counts, validation)
├── ui/
│   ├── ingredients_tab.py     # MODIFY - L2-only display with parent columns
│   ├── materials_tab.py       # MODIFY - materials-only display with parent columns
│   └── hierarchy_admin_window.py # NEW - reusable tree admin UI
└── tests/
    └── services/
        ├── test_ingredient_hierarchy_service.py  # NEW
        ├── test_material_hierarchy_service.py    # NEW
        └── test_hierarchy_admin_service.py       # NEW
```

**Structure Decision**: Single desktop project following existing `src/` layout. New services follow existing patterns. Reusable admin UI configurable for both entity types.

## Parallelization Plan

| Stream | Files | Can Parallelize With |
|--------|-------|---------------------|
| Stream A: Ingredient Display | `ingredients_tab.py`, `ingredient_hierarchy_service.py` | Stream B |
| Stream B: Material Display | `materials_tab.py`, `material_hierarchy_service.py` | Stream A |
| Stream C: Admin UI | `hierarchy_admin_window.py`, `hierarchy_admin_service.py` | After A & B complete |

**Rationale**: Streams A and B operate on separate files and can be delegated to parallel agents. Stream C depends on services from A & B being defined but can start interface design early.

## Complexity Tracking

*No constitution violations requiring justification.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
