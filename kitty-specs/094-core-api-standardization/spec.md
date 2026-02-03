# Feature Specification: Core API Standardization

**Feature Branch**: `094-core-api-standardization`
**Created**: 2026-02-03
**Status**: Draft
**Input**: docs/func-spec/F094_core_api_standardization.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Exception-Based Error Handling (Priority: P1)

As a developer maintaining the Bake Tracker codebase, I want all `get_*` service functions to raise exceptions instead of returning None when entities are not found, so that I cannot accidentally forget to check for None and introduce AttributeError bugs.

**Why this priority**: This is the highest-impact change. "Forgot to check None" bugs are a common source of runtime errors. By changing ~40 functions to raise exceptions, we eliminate an entire class of bugs and make the code more predictable.

**Independent Test**: Run tests that call `get_ingredient("nonexistent-slug")` and verify it raises `IngredientNotFoundBySlug` instead of returning None. Any service function can be tested independently.

**Acceptance Scenarios**:

1. **Given** a call to `get_ingredient(slug)` with a non-existent slug, **When** the function executes, **Then** it raises `IngredientNotFoundBySlug` with the slug value.
2. **Given** a call to `get_recipe(recipe_id)` with a non-existent ID, **When** the function executes, **Then** it raises `RecipeNotFoundById` with the ID value.
3. **Given** updated service functions, **When** all calling code (UI, other services) is updated, **Then** the application runs without regression.
4. **Given** exception-based returns, **When** type hints are updated, **Then** return types are non-Optional (e.g., `Ingredient` not `Optional[Ingredient]`).

---

### User Story 2 - Eliminate Tuple Return Anti-Pattern (Priority: P2)

As a developer, I want validation functions to raise `ValidationError` exceptions instead of returning `(bool, List[str])` tuples, so that calling code is simpler and more Pythonic.

**Why this priority**: The tuple return pattern creates awkward calling code with tuple unpacking. Exception-based validation is cleaner, consistent with FR-1, and follows Python conventions.

**Independent Test**: Run tests that call `validate_ingredient_data({})` with invalid data and verify it raises `ValidationError` with an errors list instead of returning `(False, ['error'])`.

**Acceptance Scenarios**:

1. **Given** a call to `validate_ingredient_data(data)` with invalid data, **When** the function executes, **Then** it raises `ValidationError` containing the error messages.
2. **Given** valid data passed to a validation function, **When** the function executes, **Then** it returns None (no exception).
3. **Given** updated validation functions, **When** calling code is simplified, **Then** tuple unpacking is removed from all call sites.

---

### User Story 3 - Complete Type Hints (Priority: P3)

As a developer using an IDE, I want all public service functions to have complete type hints (parameters and return types), so that autocomplete works correctly and type errors are caught at development time.

**Why this priority**: Type hints improve developer experience and catch bugs early. While not as critical as preventing runtime errors (FR-1), they significantly improve code quality and maintainability.

**Independent Test**: Run `mypy src/services/` and verify no type hint errors. Open a service file in VS Code and verify autocomplete works for function parameters and return types.

**Acceptance Scenarios**:

1. **Given** all service functions, **When** mypy runs, **Then** no missing type hint errors are reported.
2. **Given** a function with `Optional` parameter, **When** the type hint is added, **Then** it uses `Optional[Type]` syntax.
3. **Given** a function returning a list of ORM objects, **When** the type hint is added, **Then** it uses `List[Model]` syntax.
4. **Given** complete type hints, **When** using IDE autocomplete, **Then** parameter types and return types are suggested correctly.

---

### Edge Cases

- What happens when an exception type doesn't exist yet? Create it following the existing pattern in `src/services/exceptions.py`.
- How does the UI handle new exception types? Desktop UI uses centralized error handling that catches `ServiceError` (base class for all domain exceptions).
- What if a function legitimately can return None (e.g., optional find operations)? Document the decision - prefer explicit "find_or_none" naming if None is valid.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All `get_*` functions MUST raise domain-specific exceptions (e.g., `IngredientNotFoundBySlug`) instead of returning None when an entity is not found (~40 functions).
- **FR-002**: Exception types MUST follow the pattern `{Entity}NotFoundBy{LookupField}` (e.g., `RecipeNotFoundById`, `ProductNotFoundBySlug`).
- **FR-003**: All validation functions returning `(bool, List[str])` tuples MUST be converted to raise `ValidationError` exceptions (~15 functions).
- **FR-004**: `ValidationError` MUST include an `errors` attribute containing the list of validation error messages.
- **FR-005**: All public service functions MUST have complete type hints for parameters and return types (~60 functions).
- **FR-006**: Type hints MUST use proper generic types (`List[T]`, `Optional[T]`, `Dict[K, V]`).
- **FR-007**: All calling code (UI, other services, tests) MUST be updated to handle exceptions instead of checking for None or unpacking tuples.
- **FR-008**: Patterns MUST be documented in CLAUDE.md for future development.

### Key Entities

- **Exception Types**: Domain-specific exceptions for not-found scenarios, inheriting from `ServiceError`.
- **ValidationError**: Exception for validation failures, with `errors` list attribute.
- **Service Functions**: ~40 get functions, ~15 validation functions, ~60 total functions needing type hints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero `get_*` functions return None for not-found scenarios (all ~40 raise exceptions).
- **SC-002**: Zero functions return `(bool, List[str])` tuples (all ~15 use ValidationError).
- **SC-003**: `mypy src/services/` passes with no type hint errors on all ~60 service functions.
- **SC-004**: All existing tests pass after updates (no regressions).
- **SC-005**: Exception pattern and type hint standards documented in CLAUDE.md.
- **SC-006**: IDE autocomplete works correctly for all service function parameters and return types.
