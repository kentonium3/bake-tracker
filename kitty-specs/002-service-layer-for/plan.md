# Implementation Plan: Service Layer for Ingredient/Variant Architecture

**Branch**: `002-service-layer-for` | **Date**: 2025-11-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/002-service-layer-for/spec.md`

**Note**: Planning questions answered: Functional service pattern confirmed to match existing codebase (`recipe_service.py`, `event_service.py`). Using `session_scope()` context manager for transaction management.

## Summary

Implement four interconnected service modules to complete Phase 4 of the Ingredient/Variant refactor. Services provide business logic layer between UI and database models, enforcing data integrity, FIFO inventory consumption, dependency checking, and price tracking. All services follow established functional pattern using module-level functions with `session_scope()` for transaction management.

**Technical Approach**: Extend existing service layer architecture with four new modules (`ingredient_service.py`, `variant_service.py`, `pantry_service.py`, `purchase_service.py`) plus supporting validators and custom exceptions. FIFO consumption implemented as pure function that queries pantry items by purchase date, calculates partial lot consumption, and updates quantities transactionally.

## Technical Context

**Language/Version**: Python 3.10+ (type hints, match statements, structural pattern matching)
**Primary Dependencies**:
- SQLAlchemy 2.x (ORM, session management, relationships)
- Python Decimal (precise quantity/cost calculations)
- pytest (unit and integration testing)
- pytest-cov (test coverage measurement)

**Storage**: SQLite with WAL mode (desktop), SQLAlchemy ORM abstracts database for future PostgreSQL migration

**Testing**:
- pytest with in-memory SQLite for speed
- Unit tests for each service function
- Integration tests for database operations
- Fixtures for test data setup
- Coverage target: >70% for services layer

**Target Platform**: Windows 10+ desktop (64-bit)

**Project Type**: Single desktop application (src/ structure)

**Performance Goals**:
- CRUD operations <100ms for datasets up to 1000 ingredients, 5000 pantry items
- FIFO consumption calculation <200ms for 50+ lot scenario
- Search operations <50ms for partial name matching across 1000 ingredients

**Constraints**:
- FIFO consumption MUST be transactionally atomic (all-or-nothing pantry updates)
- Decimal precision MUST be maintained (no float rounding errors in costs/quantities)
- Slug generation MUST be deterministic and reversible (no hash-based slugs)
- Services MUST NOT import from `src/ui/` (layered architecture discipline)
- All database operations MUST use `session_scope()` context manager (no raw sessions)

**Scale/Scope**:
- Single user desktop application
- Expected ingredient catalog: 50-200 ingredients
- Expected pantry items: 100-500 active items
- Expected variants: 100-300 brand/package combinations
- Expected purchases (historical): 1000-5000 records over multiple years

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Principles Review

**I. User-Centric Design**
- [x] Does this feature solve a real user problem? **YES** - Enables multi-brand tracking, accurate FIFO costing, price trend analysis for budget planning
- [x] Will the primary user understand how to use it? **YES** - Services are backend layer; UI integration (separate feature) will present user-friendly interface
- [x] Does it match natural baking planning workflows? **YES** - Supports workflow of buying ingredients from various stores/brands, tracking what's in pantry, calculating costs
- [x] Can it be validated with user testing? **YES** - After UI integration, user can test ingredient catalog, variant selection, pantry tracking

**II. Data Integrity & FIFO Accuracy**
- [x] Are cost calculations accurate and trustworthy? **YES** - FIFO consumption uses Decimal for precision, consumes oldest lots first matching physical reality
- [x] Is FIFO consumption enforced where applicable? **YES** - PantryService.consume_fifo() orders by purchase_date ASC, consumes chronologically
- [x] Are unit conversions ingredient-specific? **YES** - Builds on existing UnitConversion model (already ingredient-specific per Phase 4 Items 1-6)
- [x] Will data migration preserve all existing data? **N/A** - This feature adds services, doesn't migrate data (migration scripts exist from Phase 4 Items 1-6)

**III. Future-Proof Schema, Present-Simple Implementation**
- [x] Does schema support future enhancements (nullable industry fields)? **YES** - Models already have FoodOn, GTIN, etc. (Phase 4 Items 1-6 complete)
- [x] Are only required fields populated initially? **YES** - Services validate only required fields (name, slug, category for ingredients; brand, package for variants)
- [x] Can features be added without breaking changes? **YES** - Adding new service methods doesn't break existing functionality
- [x] Is user not burdened with unnecessary data entry? **YES** - Optional fields (UPC, FoodOn ID, allergens) remain nullable

**IV. Test-Driven Development**
- [x] Are unit tests planned for all service layer methods? **YES** - Spec SC-002 requires >70% coverage; each service function will have unit tests
- [x] Do tests cover happy path, edge cases, and errors? **YES** - Spec lists 8 edge cases; all documented in acceptance scenarios
- [x] Is test coverage goal >70% for services? **YES** - Spec SC-002 explicitly requires this
- [x] Will failing tests block feature completion? **YES** - CI/CD not in place, but local test runs required before merge per development workflow

**V. Layered Architecture Discipline**
- [x] Is UI layer free of business logic? **N/A** - This feature doesn't touch UI (UI integration is separate feature)
- [x] Do services avoid importing UI components? **YES** - Services only import from models, utils, and service exceptions
- [x] Do models only define schema and relationships? **YES** - Models already exist (Phase 4 Items 1-6); services use them without modification
- [x] Do dependencies flow downward only (UI → Services → Models)? **YES** - Services import Models; UI (future) will import Services

**VI. Migration Safety & Validation**
- [x] Does migration support dry-run mode? **N/A** - No migration in this feature; models already exist
- [x] Is rollback plan documented? **N/A** - No schema changes
- [x] Is data preservation validated? **N/A** - No data migration
- [x] Are schema changes backward-compatible? **N/A** - No schema changes

**VII. Pragmatic Aspiration**

*Desktop Phase (Current):*
- [x] Does this design block web deployment? **NO** - Functional services can be wrapped in API endpoints; service layer is already UI-independent
- [x] Is the service layer UI-independent? **YES** - Services use explicit parameters, return data objects, no UI imports
- [x] Are business rules in services, not UI? **YES** - All FIFO logic, dependency checking, slug generation in services
- [x] What's the web migration cost? **LOW** - Services are stateless functions; can be called from FastAPI endpoints with minimal refactoring. Will document in `/docs/web_migration_notes.md` after implementation.

*Web Phase Readiness (6-18 months):*
- [x] Does this assume single-tenant database? **YES, acceptable** - Desktop phase; will add `user_id` parameter to service functions during web migration (documented in web_migration_notes.md)
- [x] Could this expose user data to other users? **NO** - Single-user desktop app; no multi-user concerns yet
- [x] Can this scale to 50 users? **YES** - Service logic is stateless; adding `user_id` filtering + PostgreSQL will support 50 users
- [x] What security vulnerabilities exist? **NONE** - Offline app, no network exposure, input validation prevents SQL injection (SQLAlchemy parameterization)

*Platform Readiness (1-3+ years):*
- [x] Does this assume baking domain only? **YES, acceptable** - Core logic (FIFO, catalog management) is domain-agnostic; only entity names (Ingredient, Variant) are baking-specific. Can generalize to "Item/Product" in platform phase.
- [x] Does this assume English only? **YES, acceptable** - No i18n in service layer; slug generation uses ASCII. Platform phase would need Unicode slug support.
- [x] Does this assume manual data entry? **YES, acceptable** - Services support programmatic calls; future supplier APIs can call same service functions

**Decision**: ✅ **Passes all checks** - No violations, no complexity tracking needed

## Project Structure

### Documentation (this feature)

```
kitty-specs/002-service-layer-for/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 output (research findings)
├── data-model.md        # Phase 1 output (entity definitions, FIFO algorithm)
├── quickstart.md        # Phase 1 output (developer onboarding)
├── contracts/           # Phase 1 output (service function signatures)
│   ├── ingredient_service.md
│   ├── variant_service.md
│   ├── pantry_service.md
│   └── purchase_service.md
├── checklists/
│   └── requirements.md  # Specification quality checklist (complete)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created yet)
```

### Source Code (repository root)

```
src/
├── models/              # Database models (already exist from Phase 4 Items 1-6)
│   ├── ingredient.py
│   ├── variant.py
│   ├── pantry_item.py
│   ├── purchase.py
│   └── unit_conversion.py
├── services/            # Service layer (NEW: 4 modules)
│   ├── __init__.py
│   ├── database.py      # Existing: session_scope() context manager
│   ├── exceptions.py    # EXTEND: Add new exception types
│   ├── ingredient_service.py   # NEW
│   ├── variant_service.py      # NEW
│   ├── pantry_service.py       # NEW
│   ├── purchase_service.py     # NEW
│   ├── recipe_service.py       # Existing: may need updates to use IngredientService
│   ├── event_service.py        # Existing: may need updates to use PantryService
│   └── unit_converter.py       # Existing: used by services for conversions
├── utils/               # Utilities
│   ├── validators.py    # EXTEND: Add ingredient/variant validators
│   └── slug_utils.py    # NEW: Slug generation/validation utilities
└── ui/                  # UI layer (not modified in this feature)

src/tests/               # Test suite (NEW: test files for services)
├── conftest.py          # Existing: pytest fixtures
├── test_ingredient_service.py   # NEW
├── test_variant_service.py      # NEW
├── test_pantry_service.py       # NEW
├── test_purchase_service.py     # NEW
└── integration/         # Integration tests (NEW)
    └── test_fifo_integration.py # NEW: End-to-end FIFO scenario tests
```

**Structure Decision**: Using Option 1 (Single project) as this is a desktop Python application. All new code goes in `src/services/` following existing pattern. Tests in `src/tests/` with separate unit and integration directories. No frontend/backend split needed (desktop app, not web).

## Complexity Tracking

*No violations - Constitution Check passed all gates. No complexity justification needed.*

## Phase 0: Outline & Research

### Research Questions

The following unknowns require research before design phase:

1. **FIFO Algorithm Implementation**
   - **Question**: What's the optimal SQL query pattern for FIFO consumption across multiple pantry lots?
   - **Why it matters**: Need efficient query that orders by purchase_date, handles partial lot consumption, updates quantities atomically
   - **Research task**: Review SQLAlchemy query patterns for ordered SELECT with row locking and UPDATE in single transaction

2. **Slug Generation Strategy**
   - **Question**: How to generate unique, URL-safe slugs from ingredient names with special characters (e.g., "Confectioner's Sugar")?
   - **Why it matters**: Slugs are primary keys for ingredients; must be deterministic, reversible, unique
   - **Research task**: Research slug generation libraries (python-slugify, django.utils.text.slugify) and uniqueness enforcement strategies

3. **Decimal Precision for Costs**
   - **Question**: What precision is needed for cost calculations? How to handle rounding in FIFO breakdown?
   - **Why it matters**: User relies on accurate costs for budgeting; rounding errors accumulate
   - **Research task**: Review Python Decimal best practices, precision settings for currency (2 decimal places) vs. quantities (3 decimal places)

4. **Dependency Checking Pattern**
   - **Question**: How to efficiently check if ingredient/variant is referenced by other entities before deletion?
   - **Why it matters**: Must prevent orphaned recipe references, corrupted pantry data
   - **Research task**: Review SQLAlchemy relationship query patterns, EXISTS queries, COUNT queries for performance comparison

5. **Preferred Variant Toggle Logic**
   - **Question**: How to ensure only one preferred variant per ingredient without race conditions?
   - **Why it matters**: Business rule enforcement; UI should display one "preferred" option
   - **Research task**: Review transaction isolation patterns, optimistic locking, database constraints (CHECK, UNIQUE partial index)

### Research Findings

*(To be populated during Phase 0 execution)*

Research findings will be documented in `research.md` with decisions, rationale, and alternatives considered for each question above.

## Phase 1: Design & Contracts

### Data Model

*(To be populated during Phase 1 execution)*

Entity definitions, field specifications, validation rules, and FIFO algorithm pseudocode will be documented in `data-model.md`.

### API Contracts

*(To be populated during Phase 1 execution)*

Service function signatures with parameter types, return types, exception specifications will be documented in `contracts/` directory.

### Developer Quickstart

*(To be populated during Phase 1 execution)*

Setup instructions, usage examples, testing guide will be documented in `quickstart.md`.

## Implementation Notes

### Service Dependencies

```
IngredientService (no dependencies on other services)
    ├─ Uses: slug_utils (create_slug), validators (validate_ingredient_data)

VariantService (depends on IngredientService)
    ├─ Uses: IngredientService (verify ingredient exists), validators (validate_variant_data)

PantryService (depends on VariantService, IngredientService)
    ├─ Uses: VariantService (verify variant exists), IngredientService (get total by ingredient)
    ├─ Implements: FIFO consumption algorithm

PurchaseService (depends on VariantService)
    ├─ Uses: VariantService (verify variant exists), Python statistics (mean, stdev for trends)
```

### Testing Strategy

**Unit Tests** (one file per service):
- Test each function in isolation using mocked database
- Use pytest fixtures for common test data (ingredients, variants, pantry items)
- Test happy path, edge cases (partial consumption, no inventory), error conditions (not found, validation failures)

**Integration Tests**:
- Use in-memory SQLite database
- Test end-to-end workflows (create ingredient → create variants → add to pantry → consume FIFO)
- Verify transaction atomicity (partial failure should rollback)
- Test FIFO accuracy with complex multi-lot scenarios

**Coverage Measurement**:
- Run `pytest --cov=src/services --cov-report=html` to generate coverage report
- Target: >70% coverage for all service modules
- Focus on critical paths: FIFO logic, dependency checking, validation

### Validation Approach

New validators in `src/utils/validators.py`:

```python
def validate_ingredient_data(data: Dict) -> Tuple[bool, List[str]]:
    """Validate ingredient creation/update data."""
    # Check required fields: name, category, recipe_unit
    # Validate recipe_unit is known unit
    # Validate optional fields: density_g_per_ml (positive float)

def validate_variant_data(data: Dict, ingredient_slug: str) -> Tuple[bool, List[str]]:
    """Validate variant creation/update data."""
    # Check required fields: brand, purchase_unit, purchase_quantity
    # Validate purchase_quantity > 0
    # Validate purchase_unit is known unit
    # Validate UPC format if provided (12-14 digits)
```

### Exception Hierarchy

Extend `src/services/exceptions.py`:

```python
# Existing base
class ServiceException(Exception): pass

# NEW exceptions
class IngredientNotFoundBySlug(ServiceException):
    """Raised when ingredient cannot be found by slug."""
    def __init__(self, slug: str): ...

class VariantNotFound(ServiceException):
    """Raised when variant cannot be found by ID."""
    def __init__(self, variant_id: int): ...

class PantryItemNotFound(ServiceException):
    """Raised when pantry item cannot be found by ID."""
    def __init__(self, pantry_item_id: int): ...

class PurchaseNotFound(ServiceException):
    """Raised when purchase record cannot be found by ID."""
    def __init__(self, purchase_id: int): ...

class VariantInUse(ServiceException):
    """Raised when attempting to delete variant referenced by pantry items."""
    def __init__(self, variant_id: int, pantry_item_count: int): ...

class SlugAlreadyExists(ServiceException):
    """Raised when attempting to create ingredient with duplicate slug."""
    def __init__(self, slug: str): ...
```

## Success Criteria Validation

From spec.md Success Criteria section:

- **SC-001**: All four service modules implement specified methods ✅ Contracts will define signatures
- **SC-002**: Service layer test coverage exceeds 70% ✅ pytest-cov will measure
- **SC-003**: CRUD operations <100ms for 1000 ingredients, 5000 pantry items ✅ Integration tests will time operations
- **SC-004**: FIFO consumption correctly orders by purchase date in 100% of test cases ✅ Unit tests will verify chronological consumption
- **SC-005**: Dependency checking prevents orphaned data in 100% of deletion attempts ✅ Unit tests will verify prevention
- **SC-006**: Services enforce all business rules ✅ Validators will check; unit tests will verify enforcement
- **SC-007**: Services use database sessions correctly ✅ All functions use `session_scope()` context manager
- **SC-008**: Services return clear error messages ✅ Custom exceptions provide field-specific error details
- **SC-009**: Average price calculation accuracy within 0.01 ✅ Unit tests will verify using Decimal arithmetic
- **SC-010**: Pantry consumption shortfall calculations accurate to 0.001 ✅ Unit tests will verify precision
- **SC-011**: All service methods stateless and UI-independent ✅ No UI imports; functions accept explicit parameters
- **SC-012**: Services use explicit parameters not global state ✅ Functional pattern enforces this
- **SC-013**: All queries use SQLAlchemy ORM (no raw SQL) ✅ Code review will verify
- **SC-014**: Services log errors with sufficient context ✅ Exception messages include entity IDs, quantities, etc.
- **SC-015**: Comprehensive unit tests cover happy path, edge cases, errors ✅ Test plan documents all scenarios

## Next Steps

1. **Phase 0**: Run `spec-kitty research` (or `/spec-kitty.research`) to scaffold research.md
2. **Phase 0**: Complete research questions above, document findings in research.md
3. **Phase 1**: Generate data-model.md with entity definitions and FIFO algorithm
4. **Phase 1**: Generate contracts/ with service function signatures
5. **Phase 1**: Generate quickstart.md with setup and usage examples
6. **Phase 1**: Update agent context with technology stack
7. **Re-evaluate Constitution Check** after Phase 1 design (verify no new violations)
8. **Phase 2**: Run `/spec-kitty.tasks` to generate atomic task prompts from design artifacts

---

**Plan Status**: Phase 0 & 1 Ready - Research questions identified, constitution check passed, project structure defined. Ready to proceed with research scaffolding and design artifact generation.
