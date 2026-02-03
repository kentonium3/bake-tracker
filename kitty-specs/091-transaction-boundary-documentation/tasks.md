# Work Packages: Transaction Boundary Documentation

**Inputs**: Design documents from `/kitty-specs/091-transaction-boundary-documentation/`
**Prerequisites**: plan.md (required), spec.md (user stories), func-spec F091

**Tests**: Not required (documentation feature).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

**Parallelization Strategy**: WP02-WP08 can run in parallel once WP01 completes. Assign to Gemini/Codex for maximum throughput.

---

## Work Package WP01: Service Inventory & Templates (Priority: P0)

**Goal**: Create comprehensive service function inventory and establish documentation templates.
**Independent Test**: Inventory document exists with all ~107 functions classified.
**Prompt**: `/tasks/WP01-service-inventory-templates.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [x] T001 Create service function inventory spreadsheet in kitty-specs/091/research/
- [x] T002 Classify all functions as READ/SINGLE/MULTI
- [x] T003 Document existing "Transaction boundary:" sections (7 functions already done)
- [x] T004 Create docstring template examples file with Pattern A/B/C

### Implementation Notes
- Grep for `def ` in all service files
- Check for existing "Transaction boundary:" strings
- Output: `research/service_inventory.md`

### Parallel Opportunities
- None (foundation work)

### Dependencies
- None (starting package)

### Risks & Mitigations
- Missing functions: Use both `grep` for `def ` and AST parsing for accuracy

---

## Work Package WP02: Core CRUD Services - Ingredient & Recipe (Priority: P1) [P]

**Goal**: Add transaction boundary documentation to ingredient_service.py, ingredient_crud_service.py, and recipe_service.py.
**Independent Test**: All public functions have "Transaction boundary:" section in docstrings.
**Prompt**: `/tasks/WP02-crud-ingredient-recipe.md`
**Estimated Size**: ~450 lines
**Agent**: Gemini (parallel-safe)

### Included Subtasks
- [x] T005 [P] Document ingredient_service.py (~14 functions)
- [x] T006 [P] Document ingredient_crud_service.py (~13 functions)
- [x] T007 [P] Document recipe_service.py (~20+ functions)

### Implementation Notes
- Use Pattern A for get_*, list_*, search_* functions
- Use Pattern B for create_*, update_*, delete_* (single-step)
- Use Pattern C for functions calling other services

### Parallel Opportunities
- All three files independent, can split among agents

### Dependencies
- Depends on WP01 (templates)

### Risks & Mitigations
- recipe_service.py is large (1700+ lines): Focus on public functions only

---

## Work Package WP03: Core CRUD Services - Product & Supplier (Priority: P1) [P]

**Goal**: Add transaction boundary documentation to product_service.py, product_catalog_service.py, supplier_service.py.
**Independent Test**: All public functions have "Transaction boundary:" section in docstrings.
**Prompt**: `/tasks/WP03-crud-product-supplier.md`
**Estimated Size**: ~400 lines
**Agent**: Codex (parallel-safe)

### Included Subtasks
- [ ] T008 [P] Document product_service.py (~16 functions)
- [ ] T009 [P] Document product_catalog_service.py
- [ ] T010 [P] Document supplier_service.py

### Implementation Notes
- product_service has 7 MULTI functions - use Pattern C
- Check session parameter passing for all MULTI functions

### Parallel Opportunities
- All files independent

### Dependencies
- Depends on WP01 (templates)

### Risks & Mitigations
- None significant

---

## Work Package WP04: Inventory & Purchasing Services (Priority: P1) [P]

**Goal**: Add transaction boundary documentation to inventory_item_service.py and purchase_service.py.
**Independent Test**: All public functions have "Transaction boundary:" section in docstrings.
**Prompt**: `/tasks/WP04-inventory-purchasing.md`
**Estimated Size**: ~500 lines
**Agent**: Claude (complex multi-step operations)

### Included Subtasks
- [x] T011 [P] Document inventory_item_service.py (~19 functions, 9 MULTI)
- [x] T012 [P] Document purchase_service.py (~26 functions, 12 MULTI)
- [x] T013 Verify consume_fifo documentation is complete (already has partial docs)
- [x] T014 Verify record_purchase documentation is complete (already has partial docs)

### Implementation Notes
- These services have most MULTI functions
- consume_fifo and record_purchase already have docs - verify and enhance
- Many _impl functions - document transaction inheritance

### Parallel Opportunities
- Two files can be done in parallel by same agent

### Dependencies
- Depends on WP01 (templates)

### Risks & Mitigations
- High complexity: Audit session passing carefully

---

## Work Package WP05: Production & Assembly Services (Priority: P1) [P]

**Goal**: Add transaction boundary documentation to batch_production_service.py and assembly_service.py.
**Independent Test**: All public functions have "Transaction boundary:" section in docstrings.
**Prompt**: `/tasks/WP05-production-assembly.md`
**Estimated Size**: ~450 lines
**Agent**: Gemini (parallel-safe)

### Included Subtasks
- [ ] T015 [P] Document batch_production_service.py (~8 functions, 6 MULTI)
- [ ] T016 [P] Document assembly_service.py (~11 functions, 8 MULTI)
- [ ] T017 Verify record_batch_production docs (already documented)
- [ ] T018 Verify record_assembly docs (already documented)

### Implementation Notes
- These are critical multi-step atomic operations
- Already have good documentation - verify completeness and consistency
- Verify session passing to nested service calls

### Parallel Opportunities
- Two files independent

### Dependencies
- Depends on WP01 (templates)

### Risks & Mitigations
- None - these are well-documented already

---

## Work Package WP06: Planning & Event Services (Priority: P1) [P]

**Goal**: Add transaction boundary documentation to planning services and event_service.py.
**Independent Test**: All public functions have "Transaction boundary:" section in docstrings.
**Prompt**: `/tasks/WP06-planning-event.md`
**Estimated Size**: ~450 lines
**Agent**: Codex (parallel-safe)

### Included Subtasks
- [ ] T019 [P] Document planning/planning_service.py
- [ ] T020 [P] Document plan_state_service.py
- [ ] T021 [P] Document plan_snapshot_service.py
- [ ] T022 [P] Document event_service.py
- [ ] T023 [P] Document planning/feasibility.py, progress.py, shopping_list.py

### Implementation Notes
- Planning services have complex multi-step operations
- Focus on transaction scope clarity

### Parallel Opportunities
- All files independent

### Dependencies
- Depends on WP01 (templates)

### Risks & Mitigations
- Complex service interactions: Document which services share sessions

---

## Work Package WP07: Material & Finished Good Services (Priority: P1) [P]

**Goal**: Add transaction boundary documentation to material and finished good services.
**Independent Test**: All public functions have "Transaction boundary:" section in docstrings.
**Prompt**: `/tasks/WP07-material-finished-good.md`
**Estimated Size**: ~450 lines
**Agent**: Gemini (parallel-safe)

### Included Subtasks
- [ ] T024 [P] Document finished_good_service.py
- [ ] T025 [P] Document material_consumption_service.py
- [ ] T026 [P] Document material_purchase_service.py
- [ ] T027 [P] Document material_inventory_service.py
- [ ] T028 [P] Document finished_goods_inventory_service.py

### Implementation Notes
- finished_good_service.py uses class-based pattern
- Material services support new material abstraction layer

### Parallel Opportunities
- All files independent

### Dependencies
- Depends on WP01 (templates)

### Risks & Mitigations
- Class-based services: Document instance method patterns

---

## Work Package WP08: Import/Export & Support Services (Priority: P1) [P]

**Goal**: Add transaction boundary documentation to remaining support services.
**Independent Test**: All public functions have "Transaction boundary:" section in docstrings.
**Prompt**: `/tasks/WP08-import-export-support.md`
**Estimated Size**: ~400 lines
**Agent**: Codex (parallel-safe)

### Included Subtasks
- [ ] T029 [P] Document import_export_service.py
- [ ] T030 [P] Document enhanced_import_service.py
- [ ] T031 [P] Document transaction_import_service.py
- [ ] T032 [P] Document catalog_import_service.py
- [ ] T033 [P] Document coordinated_export_service.py
- [ ] T034 [P] Document denormalized_export_service.py

### Implementation Notes
- Import services are complex multi-step operations
- Export services are typically read-only

### Parallel Opportunities
- All files independent

### Dependencies
- Depends on WP01 (templates)

### Risks & Mitigations
- Large files: Focus on public API functions

---

## Work Package WP09: Multi-Step Operation Audit (Priority: P2)

**Goal**: Audit all MULTI functions for correct session passing and atomicity guarantees.
**Independent Test**: All nested service calls pass session parameter; no broken atomicity patterns.
**Prompt**: `/tasks/WP09-multi-step-audit.md`
**Estimated Size**: ~500 lines

### Included Subtasks
- [ ] T035 Audit inventory_item_service.py multi-step functions (9 MULTI)
- [ ] T036 Audit purchase_service.py multi-step functions (12 MULTI)
- [ ] T037 Audit product_service.py multi-step functions (7 MULTI)
- [ ] T038 Audit assembly_service.py and batch_production_service.py
- [ ] T039 Fix any broken atomicity patterns (add session parameter)
- [ ] T040 Document audit results in research/atomicity_audit.md

### Implementation Notes
- Verify every nested service call receives `session=session`
- Check for multiple `session_scope()` calls in same function (anti-pattern)
- Document any fixes required

### Parallel Opportunities
- None (sequential audit required)

### Dependencies
- Depends on WP02-WP08 (documentation complete)

### Risks & Mitigations
- May find code bugs: Create fix tickets if > minor changes needed

---

## Work Package WP10: Transaction Patterns Guide (Priority: P2)

**Goal**: Create comprehensive transaction patterns guide in docs/design/.
**Independent Test**: Guide exists with all three patterns, examples, and pitfalls documented.
**Prompt**: `/tasks/WP10-transaction-patterns-guide.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [ ] T041 Create docs/design/transaction_patterns_guide.md
- [ ] T042 Document Pattern A (Read-Only) with code examples
- [ ] T043 Document Pattern B (Single-Step Write) with code examples
- [ ] T044 Document Pattern C (Multi-Step Atomic) with code examples
- [ ] T045 Document common pitfalls (at least 3 anti-patterns with fixes)
- [ ] T046 Document session parameter pattern and when to use it

### Implementation Notes
- Use real code examples from batch_production_service and assembly_service
- Include anti-patterns discovered during audit (WP09)

### Parallel Opportunities
- Can start once WP01 templates are done

### Dependencies
- Depends on WP09 (audit findings inform pitfalls section)

### Risks & Mitigations
- None significant

---

## Work Package WP11: Code Review Checklist Update (Priority: P2)

**Goal**: Update code review checklist with transaction boundary verification.
**Independent Test**: Constitution and review checklists include transaction documentation checks.
**Prompt**: `/tasks/WP11-code-review-checklist.md`
**Estimated Size**: ~250 lines

### Included Subtasks
- [ ] T047 Add "Transaction boundary matches implementation?" to Code Review Checklist in constitution
- [ ] T048 Update New Service Function Checklist to include transaction docs
- [ ] T049 Add transaction verification to PR template if one exists
- [ ] T050 Update CLAUDE.md session management section to reference guide

### Implementation Notes
- Constitution already has Code Review Checklist (Appendix)
- Add after "All public functions have docstrings and type hints"

### Parallel Opportunities
- None

### Dependencies
- Depends on WP10 (guide created to reference)

### Risks & Mitigations
- Constitution version bump needed: Follow amendment process

---

## Work Package WP12: Verification & Consistency Check (Priority: P3)

**Goal**: Final verification that all documentation is complete and consistent.
**Independent Test**: 100% of service functions have Transaction boundary docs; all use consistent templates.
**Prompt**: `/tasks/WP12-verification-consistency.md`
**Estimated Size**: ~300 lines

### Included Subtasks
- [ ] T051 Grep all services for "Transaction boundary:" to verify coverage
- [ ] T052 Check documentation consistency (same phrasing across services)
- [ ] T053 Verify all success criteria from spec.md are met
- [ ] T054 Update service inventory with final counts

### Implementation Notes
- Create verification script or grep commands
- Check SC-001 through SC-006 from spec

### Parallel Opportunities
- None (final verification)

### Dependencies
- Depends on WP02-WP11 (all documentation complete)

### Risks & Mitigations
- May find gaps: Budget time for touch-ups

---

## Dependency & Execution Summary

```
WP01 (Foundation)
  │
  ├──────┬──────┬──────┬──────┬──────┬──────┐
  ▼      ▼      ▼      ▼      ▼      ▼      ▼
WP02   WP03   WP04   WP05   WP06   WP07   WP08   (PARALLEL - Gemini/Codex)
  │      │      │      │      │      │      │
  └──────┴──────┴──────┴──────┴──────┴──────┘
                       │
                       ▼
                     WP09 (Audit)
                       │
                       ▼
                     WP10 (Guide)
                       │
                       ▼
                     WP11 (Checklist)
                       │
                       ▼
                     WP12 (Verification)
```

- **Phase 1 (Foundation)**: WP01 - Sequential
- **Phase 2 (Documentation)**: WP02-WP08 - PARALLEL (assign to Gemini/Codex)
- **Phase 3 (Audit & Guide)**: WP09, WP10 - Sequential
- **Phase 4 (Finalization)**: WP11, WP12 - Sequential

**MVP Scope**: WP01 + WP02-WP08 delivers core documentation (FR-001 through FR-004)

**Parallelization Plan**:
- Claude: WP01 (foundation), WP04 (complex inventory), WP09 (audit), WP11 (checklist)
- Gemini: WP02 (ingredient/recipe), WP05 (production/assembly), WP07 (material/FG)
- Codex: WP03 (product/supplier), WP06 (planning/event), WP08 (import/export)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create service inventory | WP01 | P0 | No |
| T002 | Classify functions | WP01 | P0 | No |
| T003 | Document existing docs | WP01 | P0 | No |
| T004 | Create template examples | WP01 | P0 | No |
| T005 | Document ingredient_service | WP02 | P1 | Yes |
| T006 | Document ingredient_crud_service | WP02 | P1 | Yes |
| T007 | Document recipe_service | WP02 | P1 | Yes |
| T008 | Document product_service | WP03 | P1 | Yes |
| T009 | Document product_catalog_service | WP03 | P1 | Yes |
| T010 | Document supplier_service | WP03 | P1 | Yes |
| T011 | Document inventory_item_service | WP04 | P1 | Yes |
| T012 | Document purchase_service | WP04 | P1 | Yes |
| T013 | Verify consume_fifo docs | WP04 | P1 | Yes |
| T014 | Verify record_purchase docs | WP04 | P1 | Yes |
| T015 | Document batch_production_service | WP05 | P1 | Yes |
| T016 | Document assembly_service | WP05 | P1 | Yes |
| T017 | Verify record_batch_production | WP05 | P1 | Yes |
| T018 | Verify record_assembly | WP05 | P1 | Yes |
| T019 | Document planning_service | WP06 | P1 | Yes |
| T020 | Document plan_state_service | WP06 | P1 | Yes |
| T021 | Document plan_snapshot_service | WP06 | P1 | Yes |
| T022 | Document event_service | WP06 | P1 | Yes |
| T023 | Document planning submodules | WP06 | P1 | Yes |
| T024 | Document finished_good_service | WP07 | P1 | Yes |
| T025 | Document material_consumption_service | WP07 | P1 | Yes |
| T026 | Document material_purchase_service | WP07 | P1 | Yes |
| T027 | Document material_inventory_service | WP07 | P1 | Yes |
| T028 | Document finished_goods_inventory_service | WP07 | P1 | Yes |
| T029 | Document import_export_service | WP08 | P1 | Yes |
| T030 | Document enhanced_import_service | WP08 | P1 | Yes |
| T031 | Document transaction_import_service | WP08 | P1 | Yes |
| T032 | Document catalog_import_service | WP08 | P1 | Yes |
| T033 | Document coordinated_export_service | WP08 | P1 | Yes |
| T034 | Document denormalized_export_service | WP08 | P1 | Yes |
| T035 | Audit inventory_item_service | WP09 | P2 | No |
| T036 | Audit purchase_service | WP09 | P2 | No |
| T037 | Audit product_service | WP09 | P2 | No |
| T038 | Audit assembly/production | WP09 | P2 | No |
| T039 | Fix broken atomicity | WP09 | P2 | No |
| T040 | Document audit results | WP09 | P2 | No |
| T041 | Create transaction guide | WP10 | P2 | No |
| T042 | Document Pattern A | WP10 | P2 | No |
| T043 | Document Pattern B | WP10 | P2 | No |
| T044 | Document Pattern C | WP10 | P2 | No |
| T045 | Document pitfalls | WP10 | P2 | No |
| T046 | Document session pattern | WP10 | P2 | No |
| T047 | Update code review checklist | WP11 | P2 | No |
| T048 | Update service function checklist | WP11 | P2 | No |
| T049 | Update PR template | WP11 | P2 | No |
| T050 | Update CLAUDE.md | WP11 | P2 | No |
| T051 | Verify doc coverage | WP12 | P3 | No |
| T052 | Check consistency | WP12 | P3 | No |
| T053 | Verify success criteria | WP12 | P3 | No |
| T054 | Final inventory update | WP12 | P3 | No |

---

**Total**: 12 Work Packages, 54 Subtasks
**Parallelization**: WP02-WP08 (7 WPs) can run concurrently
**Estimated Effort**: 2-3 days with parallel execution
