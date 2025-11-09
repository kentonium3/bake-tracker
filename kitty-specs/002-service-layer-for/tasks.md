---
description: "Work package task list for Feature 002: Service Layer Implementation"
---

# Work Packages: Service Layer for Ingredient/Variant Architecture

**Inputs**: Design documents from `/kitty-specs/002-service-layer-for/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/

**Tests**: TDD approach with pytest - tests written before implementation for all service functions.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `/tasks/planned/`. Keep this file as the high-level checklist; implementation details live in the prompt files.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Includes precise file paths or modules.

## Path Conventions
- Services: `src/services/`
- Tests: `src/tests/`
- Utilities: `src/utils/`
- Models: `src/models.py`

---

## Work Package WP01: Foundational Infrastructure (Priority: P0)

**Goal**: Establish shared utilities, exceptions, and database infrastructure required by all services.
**Independent Test**: Infrastructure modules importable; session_scope() can execute basic queries; slug generation produces correct output.
**Prompt**: `/tasks/planned/WP01-foundational-infrastructure.md`

### Included Subtasks
- [x] T001 Create service exceptions module in `src/services/exceptions.py`
- [x] T002 [P] Create database session_scope() context manager in `src/services/database.py`
- [x] T003 [P] Create slug generation utility in `src/utils/slug_utils.py`
- [x] T004 [P] Create validation utilities in `src/utils/validators.py`
- [x] T005 Setup service layer package structure with `src/services/__init__.py`

### Implementation Notes
- Exception hierarchy: `ServiceError` base → specific errors (IngredientNotFoundBySlug, VariantNotFound, etc.)
- session_scope() must handle commit/rollback automatically
- Slug generation: Unicode normalization → ASCII transliteration → regex cleanup → uniqueness check
- Validators: ingredient_data, variant_data, unit validation

### Parallel Opportunities
- T002, T003, T004 can proceed in parallel after T001 completes

### Dependencies
- None (starting package)

### Risks & Mitigations
- Decimal precision errors → Use Python Decimal throughout, no floats
- Unicode slug collisions → Implement auto-increment suffix (slug, slug_1, slug_2)

---

## Work Package WP02: IngredientService Implementation (Priority: P1) 🎯 MVP

**Goal**: Deliver complete IngredientService with 7 functions for managing ingredient catalog.
**Independent Test**: All IngredientService functions pass unit tests; CRUD operations work end-to-end.
**Prompt**: `/tasks/planned/WP02-ingredient-service.md`

### Included Subtasks
- [x] T006 [P] Write tests for create_ingredient() in `src/tests/test_ingredient_service.py`
- [x] T007 Implement create_ingredient() in `src/services/ingredient_service.py`
- [x] T008 [P] Write tests for get_ingredient()
- [x] T009 Implement get_ingredient()
- [x] T010 [P] Write tests for search_ingredients()
- [x] T011 Implement search_ingredients()
- [x] T012 [P] Write tests for update_ingredient()
- [x] T013 Implement update_ingredient()
- [x] T014 [P] Write tests for delete_ingredient()
- [x] T015 Implement delete_ingredient()
- [x] T016 [P] Write tests for check_ingredient_dependencies()
- [x] T017 Implement check_ingredient_dependencies()
- [x] T018 [P] Write tests for list_ingredients()
- [x] T019 Implement list_ingredients()

### Implementation Notes
- TDD: Write tests first, then implementation
- All functions use session_scope() context manager
- Slug generation via slug_utils.create_slug()
- Dependency checking: COUNT queries on recipes, variants, pantry_items, unit_conversions

### Parallel Opportunities
- Test writing tasks (T006, T008, T010, T012, T014, T016, T018) can proceed in parallel
- Implementation follows after corresponding tests complete

### Dependencies
- Depends on WP01 (infrastructure)

### Risks & Mitigations
- Slug collision during concurrent ingredient creation → Use database UNIQUE constraint + auto-increment
- Orphaned references during deletion → Enforce dependency checking before delete

---

## Work Package WP03: VariantService Implementation (Priority: P1) 🎯 MVP

**Goal**: Deliver complete VariantService with 9 functions for managing product variants.
**Independent Test**: All VariantService functions pass unit tests; preferred variant toggle works atomically.
**Prompt**: `/tasks/planned/WP03-variant-service.md`

### Included Subtasks
- [x] T020 [P] Write tests for create_variant() in `src/tests/test_variant_service.py`
- [x] T021 Implement create_variant() in `src/services/variant_service.py`
- [x] T022 [P] Write tests for get_variant()
- [x] T023 Implement get_variant()
- [x] T024 [P] Write tests for get_variants_for_ingredient()
- [x] T025 Implement get_variants_for_ingredient()
- [x] T026 [P] Write tests for set_preferred_variant()
- [x] T027 Implement set_preferred_variant()
- [x] T028 [P] Write tests for update_variant()
- [x] T029 Implement update_variant()
- [x] T030 [P] Write tests for delete_variant()
- [x] T031 Implement delete_variant()
- [x] T032 [P] Write tests for check_variant_dependencies()
- [x] T033 Implement check_variant_dependencies()
- [x] T034 [P] Write tests for search_variants_by_upc()
- [x] T035 Implement search_variants_by_upc()
- [x] T036 [P] Write tests for get_preferred_variant()
- [x] T037 Implement get_preferred_variant()

### Implementation Notes
- Display name auto-calculated as property: `f"{brand} - {package_size}"`
- Preferred variant toggle: UPDATE all to False, then SET one to True (atomic in session_scope)
- Dependency checking: COUNT queries on pantry_items, purchases

### Parallel Opportunities
- Test writing tasks (T020, T022, T024, T026, T028, T030, T032, T034, T036) can proceed in parallel
- Implementation follows after corresponding tests complete

### Dependencies
- Depends on WP01 (infrastructure) and WP02 (IngredientService for foreign keys)

### Risks & Mitigations
- Race condition in preferred toggle → Transaction isolation via session_scope()
- Display name inconsistency → Enforce as @property, not stored column

---

## Work Package WP04: PantryService Implementation (Priority: P1) 🎯 MVP

**Goal**: Deliver complete PantryService with 8 functions including critical FIFO consumption algorithm.
**Independent Test**: All PantryService functions pass unit tests; FIFO correctly consumes oldest lots first.
**Prompt**: `/tasks/planned/WP04-pantry-service.md`

### Included Subtasks
- [x] T038 [P] Write tests for add_to_pantry() in `src/tests/test_pantry_service.py`
- [x] T039 Implement add_to_pantry() in `src/services/pantry_service.py`
- [x] T040 [P] Write tests for get_pantry_items()
- [x] T041 Implement get_pantry_items()
- [x] T042 [P] Write tests for get_total_quantity()
- [x] T043 Implement get_total_quantity()
- [x] T044 [P] Write tests for consume_fifo() (extensive edge cases)
- [x] T045 Implement consume_fifo() with FIFO algorithm
- [x] T046 [P] Write tests for get_expiring_soon()
- [x] T047 Implement get_expiring_soon()
- [x] T048 [P] Write tests for update_pantry_item()
- [x] T049 Implement update_pantry_item()
- [x] T050 [P] Write tests for delete_pantry_item()
- [x] T051 Implement delete_pantry_item()
- [x] T052 [P] Write tests for get_pantry_value()
- [x] T053 Implement get_pantry_value()

### Implementation Notes
- FIFO algorithm: Query ordered by purchase_date ASC, iterate in Python, consume oldest first
- Unit conversion: Use existing unit_converter.py for quantity normalization
- Transaction safety: All lot updates within single session_scope()
- Shortfall handling: Consume all available if insufficient, return {consumed, shortfall, satisfied}

### Parallel Opportunities
- Test writing tasks (T038, T040, T042, T044, T046, T048, T050, T052) can proceed in parallel
- Implementation follows after corresponding tests complete

### Dependencies
- Depends on WP01 (infrastructure), WP02 (IngredientService), WP03 (VariantService)

### Risks & Mitigations
- FIFO ordering incorrect → Index on purchase_date, extensive test coverage
- Partial lot consumption bugs → session.flush() after each update, rollback on error
- Unit conversion errors → Validate all units against unit_converter.py

---

## Work Package WP05: PurchaseService Implementation (Priority: P1)

**Goal**: Deliver complete PurchaseService with 8 functions including price trend analysis.
**Independent Test**: All PurchaseService functions pass unit tests; price alerts trigger correctly.
**Prompt**: `/tasks/planned/WP05-purchase-service.md`

### Included Subtasks
- [x] T054 [P] Write tests for record_purchase() in `src/tests/test_purchase_service.py`
- [x] T055 Implement record_purchase() in `src/services/purchase_service.py`
- [x] T056 [P] Write tests for get_purchase()
- [x] T057 Implement get_purchase()
- [x] T058 [P] Write tests for get_purchase_history()
- [x] T059 Implement get_purchase_history()
- [x] T060 [P] Write tests for get_most_recent_purchase()
- [x] T061 Implement get_most_recent_purchase()
- [x] T062 [P] Write tests for calculate_average_price()
- [x] T063 Implement calculate_average_price()
- [x] T064 [P] Write tests for detect_price_change()
- [x] T065 Implement detect_price_change()
- [x] T066 [P] Write tests for get_price_trend()
- [x] T067 Implement get_price_trend() with statistics.linear_regression
- [x] T068 [P] Write tests for delete_purchase()
- [x] T069 Implement delete_purchase()

### Implementation Notes
- Total cost auto-calculation: If None, compute as quantity * unit_cost
- Price trend: Use statistics.linear_regression for slope calculation
- Alert thresholds: Warning (20-40%), Critical (>40%) from 60-day average
- All monetary values use Decimal, round only at display

### Parallel Opportunities
- Test writing tasks (T054, T056, T058, T060, T062, T064, T066, T068) can proceed in parallel
- Implementation follows after corresponding tests complete

### Dependencies
- Depends on WP01 (infrastructure) and WP03 (VariantService)

### Risks & Mitigations
- Linear regression on insufficient data → Return "insufficient_data" for < 3 purchases
- Float precision in statistics module → Convert to Decimal immediately after calculation
- Price volatility false alarms → Configurable threshold_percent parameter

---

## Work Package WP06: Integration Testing & Documentation (Priority: P2)

**Goal**: Validate cross-service workflows and ensure comprehensive documentation.
**Independent Test**: Integration tests pass; all spec.md success criteria validated; documentation complete.
**Prompt**: `/tasks/planned/WP06-integration-testing.md`

### Included Subtasks
- [x] T070 [P] Write integration test: ingredient → variant → pantry flow in `src/tests/integration/test_inventory_flow.py`
- [x] T071 [P] Write integration test: purchase → price analysis flow in `src/tests/integration/test_purchase_flow.py`
- [x] T072 [P] Write integration test: FIFO consumption scenarios in `src/tests/integration/test_fifo_scenarios.py`
- [x] T073 [P] Update service layer documentation in `docs/services/README.md`
- [x] T074 [P] Create usage examples for each service in `docs/services/examples.md`
- [x] T075 Validate all success criteria from spec.md

### Implementation Notes
- Integration tests use real database (not mocks), test multi-service interactions
- FIFO scenarios: single lot, multiple lots, insufficient inventory, expiration ordering
- Documentation: API reference, usage examples, common patterns, error handling

### Parallel Opportunities
- All subtasks can proceed in parallel

### Dependencies
- Depends on WP02, WP03, WP04, WP05 (all services implemented)

### Risks & Mitigations
- Integration test failures due to service bugs → Fix services, not tests
- Documentation drift → Auto-generate API docs from docstrings where possible

---

## Dependency & Execution Summary

- **Sequence**: WP01 → {WP02, WP03 start} → {WP03 complete, WP04, WP05} → WP06
- **Parallelization**:
  - WP02 and WP03 can start after WP01
  - WP04 needs WP02 and WP03 complete
  - WP05 needs WP01 and WP03
  - WP06 needs all services complete
- **MVP Scope**: WP01 + WP02 + WP03 + WP04 (covers ingredient, variant, pantry management)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create service exceptions | WP01 | P0 | No |
| T002 | Create session_scope() | WP01 | P0 | Yes |
| T003 | Create slug generation | WP01 | P0 | Yes |
| T004 | Create validators | WP01 | P0 | Yes |
| T005 | Setup service package | WP01 | P0 | No |
| T006-T019 | IngredientService (tests + impl) | WP02 | P1 | Tests: Yes |
| T020-T037 | VariantService (tests + impl) | WP03 | P1 | Tests: Yes |
| T038-T053 | PantryService (tests + impl) | WP04 | P1 | Tests: Yes |
| T054-T069 | PurchaseService (tests + impl) | WP05 | P1 | Tests: Yes |
| T070-T075 | Integration & docs | WP06 | P2 | Yes |

**Total**: 75 subtasks across 6 work packages
