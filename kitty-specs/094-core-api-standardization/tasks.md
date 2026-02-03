# Work Packages: Core API Standardization

**Inputs**: Design documents from `/kitty-specs/094-core-api-standardization/`
**Prerequisites**: plan.md (required), spec.md (user stories)

**Tests**: Update existing tests to expect exceptions instead of None checks.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

---

## Work Package WP01: Exception Infrastructure (Priority: P0)

**Goal**: Add all missing exception types needed for FR-1 and FR-2.
**Independent Test**: Import all new exception types and verify inheritance hierarchy.
**Prompt**: `/tasks/WP01-exception-infrastructure.md`

### Included Subtasks
- [x] T001 Add recipe-related exceptions (RecipeNotFoundBySlug, RecipeNotFoundByName)
- [x] T002 Add event-related exceptions (EventNotFoundById, EventNotFoundByName)
- [x] T003 Add finished goods exceptions (FinishedGoodNotFoundById/BySlug, FinishedUnitNotFoundById/BySlug)
- [x] T004 Add package exceptions (PackageNotFoundById, PackageNotFoundByName)
- [x] T005 Add composition/unit exceptions (CompositionNotFoundById, UnitNotFoundByCode)
- [x] T006 Add material catalog exceptions (MaterialCategoryNotFound, etc.)
- [x] T007 Add ConversionError exception for unit converters
- [x] T008 Update exceptions.py docstring with new hierarchy

### Implementation Notes
- Follow existing exception patterns in `src/services/exceptions.py`
- Each exception inherits from `ServiceError` with `http_status_code = 404`
- Include `correlation_id` parameter for future tracing

### Dependencies
- None (starting package)

### Risks & Mitigations
- Too many exception types → Group logically, use clear naming

---

## Work Package WP02: Recipe & Ingredient Service Updates (Priority: P1)

**Goal**: Update recipe_service.py and related functions to raise exceptions.
**Independent Test**: Call `get_recipe_by_slug("nonexistent")` and verify it raises `RecipeNotFoundBySlug`.
**Prompt**: `/tasks/WP02-recipe-ingredient-exceptions.md`

### Included Subtasks
- [x] T009 Update `get_recipe_by_slug()` to raise RecipeNotFoundBySlug
- [x] T010 Update `get_recipe_by_name()` to raise RecipeNotFoundByName
- [x] T011 Update calling code for recipe functions
- [x] T012 Update recipe tests to expect exceptions
- [x] T013 [P] Review ingredient_service.py (already uses exceptions - verify consistency)

### Implementation Notes
- recipe_service.py functions return Optional[Recipe] currently
- Update return type annotations to remove Optional
- Find all call sites with grep before changing

### Dependencies
- Depends on WP01 (exception types)

### Risks & Mitigations
- Breaking UI → Test UI flows after each change

---

## Work Package WP03: Event & Package Service Updates (Priority: P1)

**Goal**: Update event_service.py and package_service.py to raise exceptions.
**Independent Test**: Call `get_event_by_id(999)` and verify it raises `EventNotFoundById`.
**Prompt**: `/tasks/WP03-event-package-exceptions.md`

### Included Subtasks
- [x] T014 Update `get_event_by_id()` to raise EventNotFoundById
- [x] T015 Update `get_event_by_name()` to raise EventNotFoundByName
- [x] T016 Update `get_package_by_id()` to raise PackageNotFoundById
- [x] T017 Update `get_package_by_name()` to raise PackageNotFoundByName
- [x] T018 Update calling code for event/package functions
- [x] T019 Update event and package tests

### Implementation Notes
- Event service has many functions - focus on core get functions
- Package service is simpler - fewer call sites

### Dependencies
- Depends on WP01 (exception types)

### Risks & Mitigations
- Event service is heavily used → Test thoroughly

---

## Work Package WP04: Finished Goods Service Updates (Priority: P1)

**Goal**: Update finished_good_service.py and finished_unit_service.py to raise exceptions.
**Independent Test**: Call `get_finished_good_by_id(999)` and verify it raises `FinishedGoodNotFoundById`.
**Prompt**: `/tasks/WP04-finished-goods-exceptions.md`

### Included Subtasks
- [x] T020 Update `get_finished_good_by_id()` to raise FinishedGoodNotFoundById
- [x] T021 Update `get_finished_good_by_slug()` to raise FinishedGoodNotFoundBySlug
- [x] T022 Update `get_finished_unit_by_id()` to raise FinishedUnitNotFoundById
- [x] T023 Update `get_finished_unit_by_slug()` to raise FinishedUnitNotFoundBySlug
- [x] T024 Update calling code for finished goods functions
- [x] T025 Update finished goods tests

### Implementation Notes
- Both services have class-based and module-level wrapper functions
- Update both the class method and the wrapper

### Dependencies
- Depends on WP01 (exception types)

### Risks & Mitigations
- Class wrapper pattern → Ensure both levels are updated

---

## Work Package WP05: Secondary Service Updates (Priority: P2)

**Goal**: Update remaining services (composition, supplier, recipient, unit, material catalog).
**Independent Test**: Call `get_composition_by_id(999)` and verify it raises exception.
**Prompt**: `/tasks/WP05-secondary-service-exceptions.md`

### Included Subtasks
- [x] T026 Update composition_service.py get functions
- [x] T027 Update supplier_service.py get functions
- [x] T028 Update recipient_service.py `get_recipient_by_name()`
- [x] T029 Update unit_service.py `get_unit_by_code()`
- [x] T030 Update material_catalog_service.py get functions
- [x] T031 Update calling code for all secondary services
- [x] T032 Update tests for secondary services

### Implementation Notes
- These services have fewer call sites
- Material catalog is internal - less risk
- Supplier service already has `get_supplier_or_raise()` pattern

### Dependencies
- Depends on WP01 (exception types)

### Risks & Mitigations
- Some services are internal-only → Lower risk, can be more aggressive

---

## Work Package WP06: Tuple Return Elimination (Priority: P2)

**Goal**: Convert all tuple-returning validation functions to use exceptions.
**Independent Test**: Call `validate_ingredient_data({})` and verify it raises `ValidationError`.
**Prompt**: `/tasks/WP06-tuple-elimination.md`

### Included Subtasks
- [x] T033 Update `utils/validators.py` validation functions (9 functions)
- [x] T034 Update calling code for validators
- [x] T035 Update `ingredient_service.py` tuple-returning functions
- [x] T036 Update `purchase_service.py` tuple-returning functions
- [x] T037 Update tests for all converted functions

### Implementation Notes
- ValidationError already exists and accepts list of errors
- Replace `return (False, errors)` with `raise ValidationError(errors)`
- Replace `return (True, "")` with `return None` (no exception)

### Dependencies
- None (uses existing ValidationError)

### Risks & Mitigations
- Many call sites use tuple unpacking → Must update all

---

## Work Package WP07: Unit Converter Updates (Priority: P2)

**Goal**: Convert unit converter tuple returns to use exceptions.
**Independent Test**: Call `convert_standard_units(1, "invalid", "kg")` and verify it raises `ConversionError`.
**Prompt**: `/tasks/WP07-unit-converter-updates.md`

### Included Subtasks
- [x] T038 Update `unit_converter.py` functions (5 functions)
- [x] T039 Update `material_unit_converter.py` functions (4 functions)
- [x] T040 Update calling code for converters
- [x] T041 Update converter tests

### Implementation Notes
- Converters return `Tuple[bool, float, str]` pattern
- Need to decide: raise exception on invalid input, or return converted value
- ConversionError should include from_unit, to_unit, value context

### Dependencies
- Depends on WP01 (ConversionError exception)

### Risks & Mitigations
- Converters used in many places → Test thoroughly

---

## Work Package WP08: Type Hints Completion (Priority: P3)

**Goal**: Add complete type hints to all service functions.
**Independent Test**: Run `mypy src/services/` and verify no type hint errors.
**Prompt**: `/tasks/WP08-type-hints.md`

### Included Subtasks
- [x] T042 Add type hints to functions missing them
- [x] T043 Fix `session=None` parameters to use `Optional[Session]`
- [x] T044 Update return types to remove Optional where exceptions raised
- [x] T045 Run mypy and fix errors
- [x] T046 Verify IDE autocomplete works

### Implementation Notes
- Many functions already have type hints
- Focus on `session` parameters and complex return types
- Use `Dict[str, Any]` for dynamic dict returns

### Dependencies
- Should be done after WP02-WP07 (return types change)

### Risks & Mitigations
- mypy errors cascade → Fix incrementally

---

## Work Package WP09: Documentation Update (Priority: P3)

**Goal**: Update CLAUDE.md with exception and type hint patterns.
**Independent Test**: Review CLAUDE.md for completeness.
**Prompt**: `/tasks/WP09-documentation.md`

### Included Subtasks
- [ ] T047 Add "Exception Pattern" section to CLAUDE.md
- [ ] T048 Add "Validation Pattern" section to CLAUDE.md
- [ ] T049 Update existing "Key Design Decisions" with new patterns
- [ ] T050 Document which services have been updated

### Implementation Notes
- Follow existing CLAUDE.md structure
- Include code examples for patterns

### Dependencies
- Depends on WP02-WP08 (patterns established)

### Risks & Mitigations
- None

---

## Dependency & Execution Summary

```
WP01 (Foundation)
 ├── WP02 (Recipe/Ingredient) ─┐
 ├── WP03 (Event/Package)     ─┼── WP08 (Type Hints) ─── WP09 (Docs)
 ├── WP04 (Finished Goods)    ─┤
 └── WP05 (Secondary)         ─┘

WP06 (Tuple Elimination) ─────────┘
WP07 (Unit Converters) ───────────┘
```

**Parallelization**:
- WP02, WP03, WP04, WP05 can run in parallel after WP01
- WP06, WP07 can run in parallel (no dependencies on WP02-WP05)
- WP08 should wait for WP02-WP07 completion
- WP09 should be last

**MVP Scope**: WP01 + WP02 (recipe exceptions) establishes the pattern and delivers immediate value.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001-T008 | Exception types | WP01 | P0 | No |
| T009-T013 | Recipe/Ingredient | WP02 | P1 | Partial |
| T014-T019 | Event/Package | WP03 | P1 | No |
| T020-T025 | Finished Goods | WP04 | P1 | No |
| T026-T032 | Secondary Services | WP05 | P2 | Partial |
| T033-T037 | Validators | WP06 | P2 | No |
| T038-T041 | Converters | WP07 | P2 | No |
| T042-T046 | Type Hints | WP08 | P3 | Yes |
| T047-T050 | Documentation | WP09 | P3 | No |
