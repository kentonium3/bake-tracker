# Implementation Plan: Recipe Slug Support

**Branch**: `080-recipe-slug-support` | **Date**: 2026-01-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/080-recipe-slug-support/spec.md`

## Summary

Add unique `slug` and `previous_slug` fields to the Recipe model for data portability. Update all recipe FK exports to include `recipe_slug` alongside `recipe_name`, and update imports to resolve via slug first with name fallback. Follows established patterns from Supplier, Product, and Ingredient slug implementations.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode
**Testing**: pytest
**Target Platform**: macOS/Windows desktop
**Project Type**: Single desktop application
**Performance Goals**: <100ms per slug generation (per F080 spec)
**Constraints**: No migration scripts - uses reset/re-import cycle per Constitution Principle VI
**Scale/Scope**: Single user, ~50-100 recipes typical

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Slug is internal identifier - no UI changes required |
| II. Data Integrity (NON-NEGOTIABLE) | PASS | Unique constraint prevents collision; slug-based FK resolution ensures correct references |
| III. Future-Proof Schema | PASS | Slug field supports future multi-tenant migration; current implementation simple |
| IV. Test-Driven Development | PASS | Service layer tests required for slug generation and collision handling |
| V. Layered Architecture | PASS | Changes confined to Models and Services layers; no UI modifications |
| VI. Schema Change Strategy | PASS | Using reset/re-import cycle, not migration scripts |
| VII. Pragmatic Aspiration | PASS | Slug-based FKs explicitly mentioned as "Good Opportunistic Choice" in constitution |

**Desktop Phase Gates (from Constitution VII):**
- Does this design block web deployment? **NO** - slug pattern is web-ready
- Is the service layer UI-independent? **YES** - all changes in models/services
- Does this support AI-assisted JSON import? **YES** - slug provides reliable entity resolution
- What's the web migration cost? **LOW** - slug pattern already multi-tenant ready

## Project Structure

### Documentation (this feature)

```
kitty-specs/080-recipe-slug-support/
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Schema changes
├── spec.md              # Feature specification
├── checklists/          # Quality checklists
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (files to modify)

```
src/
├── models/
│   └── recipe.py                    # Add slug, previous_slug columns + event listener
├── services/
│   ├── recipe_service.py            # Add generate_slug(), _generate_unique_slug()
│   ├── coordinated_export_service.py # Add recipe_slug to all exports
│   └── catalog_import_service.py    # Update recipe import with slug resolution
└── tests/
    ├── test_recipe_service.py       # Slug generation tests
    └── test_import_export.py        # Round-trip tests with slugs
```

**Structure Decision**: Standard single project structure. All changes within existing `src/models/`, `src/services/`, and `src/tests/` directories.

## Complexity Tracking

*No constitution violations - table not needed.*

## Parallel Work Analysis

### Dependency Graph

```
WP01: Schema (Foundation)
  └─> WP02: Service Layer (depends on WP01)
        └─> WP03: Export Updates (depends on WP02)
              └─> WP04: Import Updates (depends on WP02, can parallel with WP03)
                    └─> WP05: Integration Tests (depends on WP03, WP04)
```

### Work Distribution

**Sequential work (must be done first):**
- WP01: Recipe model schema changes (slug, previous_slug columns)
- WP02: RecipeService slug generation methods

**Parallel streams (after WP02 complete):**
- WP03: Export service updates (recipe_slug in all exports)
- WP04: Import service updates (slug resolution with fallback)

**Final integration:**
- WP05: End-to-end tests with real export/import cycles

### Coordination Points

- **After WP01**: Schema must be verified before service work begins
- **After WP02**: generate_slug() must be tested before export/import work
- **After WP03+WP04**: Integration tests verify round-trip data integrity

## Implementation Approach

### Pattern Sources (Copy Exactly)

| Pattern | Source File | Copy To |
|---------|-------------|---------|
| Slug column definition | `src/models/supplier.py:82-83` | `src/models/recipe.py` |
| Slug event listener | `src/models/supplier.py:183-189` | `src/models/recipe.py` |
| `_generate_slug()` | `src/services/finished_unit_service.py:629-652` | `src/services/recipe_service.py` |
| `_generate_unique_slug()` | `src/services/finished_unit_service.py:655-679` | `src/services/recipe_service.py` |
| Dual-field export | `src/services/coordinated_export_service.py:675-677` | All recipe FK exports |
| Slug-first import | `src/services/coordinated_export_service.py:1354-1361` | All recipe FK imports |

### Key Design Decisions

1. **Slug format**: Hyphens (not underscores) - matches FinishedUnit/FinishedGood pattern
2. **Max length**: 200 characters - matches Product/Ingredient
3. **Event listener**: Auto-generate on insert - like Supplier pattern
4. **previous_slug**: Nullable, indexed - enables one-rename grace period
5. **Resolution order**: slug -> previous_slug -> name (with logging)

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `src/models/recipe.py` | ADD COLUMNS | `slug`, `previous_slug` columns + index + event listener |
| `src/services/recipe_service.py` | ADD METHODS | `generate_slug()`, `_generate_unique_slug()`, update `create_recipe()`, `update_recipe()` |
| `src/services/coordinated_export_service.py` | MODIFY | Add `recipe_slug` to: `_export_recipes()`, `_export_finished_units()`, `_export_event_production_targets()`, `_export_production_runs()`, add `component_recipe_slug` to recipe components |
| `src/services/catalog_import_service.py` | MODIFY | Update `_import_recipes()` to generate/use slug; update FK resolution in all recipe-referencing imports |
| `src/tests/test_recipe_service.py` | ADD TESTS | Slug generation, collision handling, rename behavior |
| `src/tests/test_import_export.py` | ADD TESTS | Round-trip with slugs, legacy fallback |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Slug collision during import | Collision handling with -2, -3 suffixes (copy from FinishedUnitService) |
| Breaking existing exports | Maintain `recipe_name` in all exports for backward compatibility |
| Performance of slug uniqueness check | Use indexed column; batch generation for large imports |
| Recipe rename invalidates references | `previous_slug` field provides one-rename grace period |

## Success Metrics

From spec.md Success Criteria:
- SC-001: All recipes have unique slugs after data re-import
- SC-002: Recipe export includes slug and previous_slug fields
- SC-003: Round-trip export→import preserves all associations
- SC-004: Legacy imports (no slug) work via name fallback
- SC-005: FK associations resolve correctly by slug
- SC-006: Slug generation matches existing patterns
- SC-007: Recipe rename preserves previous_slug
- SC-008: previous_slug fallback resolves correctly
