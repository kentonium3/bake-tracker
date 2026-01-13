# Implementation Plan: Supplier Slug Support

**Branch**: `050-supplier-slug-support` | **Date**: 2026-01-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/050-supplier-slug-support/spec.md`

## Summary

Add a portable `slug` field to the Supplier model to enable cross-environment data portability via import/export. The slug serves as a stable, human-readable identifier that survives database migrations and environment changes, replacing fragile auto-increment ID references in foreign key relationships.

**Technical Approach**: Replicate the existing slug generation patterns from Ingredient and Material models exactly, ensuring consistency across the codebase. Slug generation uses Unicode normalization (NFD → ASCII → lowercase → underscores) with numeric suffix conflict resolution (`_2`, `_3`, etc.).

## Technical Context

**Language/Version**: Python 3.10+ (minimum for type hints)
**Primary Dependencies**: SQLAlchemy 2.x (ORM), CustomTkinter (UI)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (macOS, Windows, Linux)
**Project Type**: Single desktop application
**Performance Goals**: N/A (single-user desktop)
**Constraints**: Must preserve FIFO accuracy; slug generation must be idempotent
**Scale/Scope**: Single-user, ~6 existing suppliers, ~50 products with supplier refs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Solves real data portability problem; no UI complexity added |
| II. Data Integrity & FIFO | ✅ PASS | Slug field adds data integrity; no FIFO impact |
| III. Future-Proof Schema | ✅ PASS | Slug enables portable references for web migration |
| IV. Test-Driven Development | ✅ PASS | Service layer changes require >70% coverage |
| V. Layered Architecture | ✅ PASS | Changes follow UI→Services→Models flow |
| VI. Schema Change Strategy | ✅ PASS | Uses export/reset/import for migration |
| VII. Pragmatic Aspiration | ✅ PASS | **Explicitly endorsed**: "Slug-based foreign keys instead of display names" listed as Good Opportunistic Choice |

**Constitution v1.4.0 Alignment**: This feature directly implements a pattern explicitly endorsed in Section VII (Pragmatic Aspiration) as a "Good Opportunistic Choice" that benefits desktop, web, and platform phases.

## Project Structure

### Documentation (this feature)

```
kitty-specs/050-supplier-slug-support/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.research command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── supplier.py          # Add slug field to Supplier model
│   └── base.py              # Existing base model (reference for patterns)
├── services/
│   ├── supplier_service.py  # Add slug generation logic
│   └── import_export_service.py  # Update export/import for slug support
├── ui/                      # No changes expected
└── utils/
    └── slug_utils.py        # Shared slug generation utilities (if not already present)

src/tests/
├── test_supplier_service.py     # Unit tests for slug generation
├── test_import_export.py        # Integration tests for slug-based import/export
└── fixtures/                    # Test data fixtures

test_data/
└── suppliers.json               # Update with slug field
```

**Structure Decision**: Single desktop application following existing bake-tracker structure. Changes are localized to models, services, and import/export layers. No UI changes required.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

No violations. All constitution principles pass without exception.

## Planning Questions

**Q1: How should slug generation be implemented?**
- **Answer**: Research existing slug patterns in Ingredient and Material models, then replicate exactly for consistency (User selected option A).

**Q2: Parallelization strategy for implementation?**
- **Answer**: Use Gemini for parallelization where safely practical for speed (per user request). Safe parallelization candidates:
  - Model changes + service tests (different files)
  - Export changes + import changes (after model is stable)
  - Test data updates + documentation (independent)
