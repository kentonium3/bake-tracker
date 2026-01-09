# Implementation Plan: Finished Units Yield Type Management

**Branch**: `044-finished-units-yield-type-management`
**Date**: 2026-01-09
**Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/044-finished-units-yield-type-management/spec.md`

## Summary

Enable bakers to define yield types (finished products) for recipes inline within the Recipe Edit form. The existing FinishedUnit infrastructure will be leveraged with modifications. A read-only catalog tab provides system-wide overview with navigation to parent recipes.

**Key Design Decision**: Inline row entry in Recipe Edit form (not modal dialogs), per user preference.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (macOS, Windows, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Tab load <1 second, form operations <500ms
**Constraints**: Single-user application, local database

## Constitution Check

*GATE: Verified against CLAUDE.md principles*

| Principle | Status | Notes |
|-----------|--------|-------|
| Layered Architecture (UI → Services → Models) | ✅ Pass | Changes respect layer boundaries |
| User-Centric Design | ✅ Pass | Inline entry is simpler than modals |
| Test-Driven Development | ✅ Pass | Service tests planned |
| Session Management | ✅ Pass | Will follow existing session patterns |

## Project Structure

### Documentation (this feature)

```
kitty-specs/044-finished-units-yield-type-management/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output - infrastructure analysis
├── data-model.md        # Phase 1 output - entity documentation
├── quickstart.md        # Phase 1 output - implementation guide
├── contracts/           # (empty - no new APIs)
├── checklists/
│   └── requirements.md  # Requirements traceability
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   └── finished_unit.py     # MODIFY: Change FK ondelete to CASCADE
├── services/
│   └── finished_unit_service.py  # MODIFY: Add name uniqueness validation
├── ui/
│   ├── forms/
│   │   └── recipe_form.py   # MODIFY: Add Yield Types section
│   └── finished_units_tab.py  # MODIFY: Convert to read-only catalog
└── tests/
    └── test_finished_unit_recipe_integration.py  # NEW: Integration tests
```

**Structure Decision**: Single project structure - all changes within existing `src/` hierarchy.

## Work Package Overview

### WP1: Model Layer - Cascade Delete (Gemini)

**Files**: `src/models/finished_unit.py`
**Scope**: Change FK constraint from RESTRICT to CASCADE
**Dependencies**: None
**Parallelizable**: Yes

### WP2: Service Layer - Name Validation (Gemini)

**Files**: `src/services/finished_unit_service.py`
**Scope**: Add name uniqueness validation per recipe
**Dependencies**: None
**Parallelizable**: Yes (with WP1, WP4)

### WP3: Recipe Edit Form - Yield Types Section (Claude - Lead)

**Files**: `src/ui/forms/recipe_form.py`
**Scope**: Add Yield Types section below ingredients
**Dependencies**: WP2 (service validation)
**Parallelizable**: Partial - UI structure can start immediately

### WP4: Finished Units Tab - Read-Only Conversion (Gemini)

**Files**: `src/ui/finished_units_tab.py`
**Scope**: Convert to read-only catalog with navigation
**Dependencies**: None
**Parallelizable**: Yes (with WP1, WP2)

### WP5: Integration Tests (Gemini)

**Files**: `src/tests/test_finished_unit_recipe_integration.py`
**Scope**: Tests for cascade delete, uniqueness, UI integration
**Dependencies**: WP1-WP4
**Parallelizable**: After implementation complete

### WP6: Manual Acceptance Testing (Claude - Lead)

**Scope**: Run application, verify all acceptance scenarios
**Dependencies**: WP1-WP5

## Parallelization Strategy

```
Timeline (conceptual, not time-estimated):
═══════════════════════════════════════════════════════════════

Phase 1 - Parallel Foundation:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ WP1: Model      │  │ WP2: Service    │  │ WP4: Tab        │
│ (Gemini)        │  │ (Gemini)        │  │ (Gemini)        │
│ CASCADE FK      │  │ Validation      │  │ Read-only       │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
═══════════════════════════════════════════════════════════════

Phase 2 - Sequential (depends on Phase 1):
                    ┌─────────────────────┐
                    │ WP3: Recipe Form    │
                    │ (Claude - Lead)     │
                    │ Yield Types Section │
                    └──────────┬──────────┘
                               │
                               ▼
═══════════════════════════════════════════════════════════════

Phase 3 - Testing:
                    ┌─────────────────────┐
                    │ WP5: Integration    │
                    │ Tests (Gemini)      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ WP6: Acceptance     │
                    │ (Claude - Lead)     │
                    └─────────────────────┘
```

## Key Implementation Details

### Yield Types Section in Recipe Form

Insert after Recipe Ingredients section (around line 660 of recipe_form.py):

1. Section header: "Yield Types"
2. List frame for existing yield types
3. Inline entry row with Name + Items Per Batch + Add button
4. Each row has Edit (inline) and Delete buttons
5. Save validates at least 1 yield type (warning, not blocking)

### Read-Only Catalog Tab

Modifications to finished_units_tab.py:

1. Remove Add, Edit, Delete buttons
2. Add info label: "Yield types are managed in Recipe Edit"
3. Add Recipe column to data table
4. Double-click opens parent Recipe Edit form (not detail dialog)

### Validation Flow

```
User enters yield type in Recipe Edit
           │
           ▼
┌─────────────────────────────────┐
│ Client-side validation          │
│ - Name not empty                │
│ - Items per batch > 0           │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Service-side validation         │
│ - Name unique within recipe     │
│ - Recipe exists                 │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Database constraints            │
│ - items_per_batch CHECK > 0     │
│ - slug UNIQUE                   │
└─────────────────────────────────┘
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing recipes | CASCADE change is behavioral only - no migration needed |
| Complex form layout | Follow existing RecipeIngredientRow pattern exactly |
| Navigation not working | Test double-click with mock recipe data first |

## Phase 1 Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| research.md | `./research.md` | ✅ Complete |
| data-model.md | `./data-model.md` | ✅ Complete |
| quickstart.md | `./quickstart.md` | ✅ Complete |
| contracts/ | `./contracts/` | N/A (no new APIs) |

## Next Steps

**This plan is complete. Do NOT proceed to task generation.**

User must explicitly run `/spec-kitty.tasks` to generate work packages.
