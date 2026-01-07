# Work Packages: Manual Inventory Adjustments (F041)

**Inputs**: Design documents from `/kitty-specs/041-manual-inventory-adjustments/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Unit tests included per Constitution Principle IV (Test-Driven Development).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

**Parallel Development**: This feature uses parallel agent development:
- **Claude** owns: `src/models/`, `src/services/`, `src/tests/` (WP01, WP02, WP03)
- **Gemini** owns: `src/ui/` (WP04, WP05)

**Prompt Files**: Each work package references a matching prompt file in `tasks/planned/`.

---

## Work Package WP01: Service Layer Foundation (Priority: P0) MVP

**Goal**: Create DepletionReason enum and InventoryDepletion model as foundation for service layer.
**Agent**: Claude
**Independent Test**: Model can be imported and instantiated; enum values accessible.
**Prompt**: `tasks/planned/WP01-service-layer-foundation.md`

### Included Subtasks
- [x] T001 [P] Add DepletionReason enum to `src/models/enums.py`
- [x] T002 Create InventoryDepletion model in `src/models/inventory_depletion.py`
- [x] T003 Export InventoryDepletion from `src/models/__init__.py`
- [x] T004 Add relationship to InventoryItem model (back_populates)

### Implementation Notes
1. Add DepletionReason enum following existing pattern (ProductionStatus, LossCategory)
2. Create InventoryDepletion model with all attributes from data-model.md
3. Add foreign key relationship to InventoryItem
4. Export from __init__.py for clean imports

### Parallel Opportunities
- T001 (enum) can be developed independently of T002-T004 (model)

### Dependencies
- None (starting package)

### Risks & Mitigations
- Schema change requires export/import cycle per Constitution Principle VI
- Mitigation: Document in tasks.md that schema reset is needed before testing

---

## Work Package WP02: Service Methods Implementation (Priority: P1) MVP

**Goal**: Implement manual_adjustment() and get_depletion_history() service methods.
**Agent**: Claude
**Independent Test**: Service methods can be called and return expected results with test data.
**Prompt**: `tasks/planned/WP02-service-methods.md`

### Included Subtasks
- [x] T005 Implement manual_adjustment() in `src/services/inventory_item_service.py`
- [x] T006 Implement validation logic (quantity > 0, <= current, notes for OTHER)
- [x] T007 Implement cost calculation (quantity * unit_cost)
- [x] T008 Implement get_depletion_history() in `src/services/inventory_item_service.py`
- [x] T009 Add session parameter support following CLAUDE.md pattern

### Implementation Notes
1. Follow contract in `contracts/inventory_adjustment_service.py`
2. Use session=None pattern per CLAUDE.md Session Management section
3. Hardcode created_by as "desktop-user"
4. Atomically update InventoryItem.quantity and create depletion record

### Parallel Opportunities
- None within this package; T005-T009 are sequential

### Dependencies
- Depends on WP01 (model and enum must exist)

### Risks & Mitigations
- Session management anti-pattern risk
- Mitigation: Follow established pattern from CLAUDE.md

---

## Work Package WP03: Service Layer Tests (Priority: P1)

**Goal**: Write unit tests for service layer per Constitution Principle IV.
**Agent**: Claude
**Independent Test**: `pytest src/tests/test_inventory_adjustment.py -v` passes.
**Prompt**: `tasks/planned/WP03-service-layer-tests.md`

### Included Subtasks
- [x] T010 [P] Create test file `src/tests/test_inventory_adjustment.py`
- [x] T011 [P] Test manual_adjustment() happy path (valid depletion)
- [x] T012 [P] Test manual_adjustment() validation (quantity > current fails)
- [x] T013 [P] Test manual_adjustment() validation (quantity <= 0 fails)
- [x] T014 [P] Test manual_adjustment() notes required for OTHER reason
- [x] T015 [P] Test manual_adjustment() cost calculation accuracy
- [x] T016 [P] Test get_depletion_history() returns records DESC by date

### Implementation Notes
1. Use pytest fixtures for test data setup
2. Follow existing test patterns in src/tests/
3. Cover all acceptance scenarios from spec.md

### Parallel Opportunities
- All test cases (T011-T016) can be written in parallel after T010

### Dependencies
- Depends on WP02 (service methods must exist)

### Risks & Mitigations
- Test isolation risk with shared database
- Mitigation: Use session rollback in fixtures

---

## Work Package WP04: UI Adjustment Dialog (Priority: P1)

**Goal**: Create the manual adjustment dialog with live preview.
**Agent**: Gemini
**Independent Test**: Dialog opens, displays current inventory info, and shows live preview as user types.
**Prompt**: `tasks/planned/WP04-ui-adjustment-dialog.md`

### Included Subtasks
- [x] T017 Create dialog class in `src/ui/dialogs/adjustment_dialog.py`
- [x] T018 Implement dialog layout (product info, current quantity, unit cost)
- [x] T019 Add quantity input field with validation (positive numbers only)
- [x] T020 Add reason dropdown (Spoilage, Gift, Correction, Ad Hoc Usage, Other)
- [x] T021 Add notes text field (conditionally required for OTHER)
- [x] T022 Implement live preview (new quantity, cost impact) updating on input
- [x] T023 Add Apply and Cancel buttons

### Implementation Notes
1. Use CustomTkinter widgets for modern appearance
2. Live preview updates on KeyRelease event
3. Preview shows: "New Quantity: X.X cups (Y.Y - Z.Z)" and "Cost Impact: $A.AA"
4. Reason dropdown labels per quickstart.md DepletionReason Values table

### Parallel Opportunities
- T017-T023 are sequential within dialog creation

### Dependencies
- Depends on WP01 (needs DepletionReason enum for dropdown values)
- Can start after WP01 completes, parallel with WP02/WP03

### Risks & Mitigations
- Live preview performance risk
- Mitigation: Debounce input if needed; target <100ms update per SC-003

---

## Work Package WP05: UI Integration & Wiring (Priority: P2)

**Goal**: Wire dialog to inventory tab and connect to service layer.
**Agent**: Gemini
**Independent Test**: Full workflow: click Adjust -> enter data -> Apply -> inventory updates.
**Prompt**: `tasks/planned/WP05-ui-integration.md`

### Included Subtasks
- [x] T024 Add [Adjust] button to inventory item rows in `src/ui/inventory_tab.py`
- [x] T025 Wire button click to open adjustment dialog
- [x] T026 Wire dialog Apply button to call manual_adjustment() service
- [x] T027 Handle ValidationError from service and display to user
- [x] T028 Refresh inventory list after successful adjustment
- [x] T029 Update/enhance depletion history view to show manual adjustments with reason/notes

### Implementation Notes
1. Import manual_adjustment from src.services.inventory_item_service
2. Catch ValidationError and InventoryItemNotFound, display in error dialog
3. Refresh inventory tab data after successful adjustment
4. History view shows reason enum display name and truncated notes

### Parallel Opportunities
- T024-T025 (button) can be done parallel with T029 (history view)

### Dependencies
- Depends on WP02 (service methods must exist for wiring)
- Depends on WP04 (dialog must exist)

### Risks & Mitigations
- Import path issues between UI and service layers
- Mitigation: Use absolute imports from src root

---

## Dependency & Execution Summary

```
WP01 (Foundation) ─────────────────────────────────────────┐
     │                                                      │
     ├──► WP02 (Service Methods) ──► WP03 (Tests) ─────────┤
     │                                   │                  │
     └──► WP04 (UI Dialog) ────────────────────────────────┤
                              │                             │
                              └──► WP05 (UI Integration) ──┘
```

- **Sequence**: WP01 → (WP02 + WP04 parallel) → (WP03 + WP05 after deps)
- **Parallelization**:
  - After WP01: Claude starts WP02, Gemini starts WP04 (parallel)
  - After WP02: Claude starts WP03, Gemini continues WP05 (parallel)
- **Completed**: WP01-WP05 (all core functionality implemented and tested)

---

## Subtask Index (Reference)

| Subtask | Summary | Work Package | Priority | Parallel? | Agent |
|---------|---------|--------------|----------|-----------|-------|
| T001 | Add DepletionReason enum | WP01 | P0 | Yes | Claude |
| T002 | Create InventoryDepletion model | WP01 | P0 | No | Claude |
| T003 | Export from __init__.py | WP01 | P0 | No | Claude |
| T004 | Add relationship to InventoryItem | WP01 | P0 | No | Claude |
| T005 | Implement manual_adjustment() | WP02 | P1 | No | Claude |
| T006 | Implement validation logic | WP02 | P1 | No | Claude |
| T007 | Implement cost calculation | WP02 | P1 | No | Claude |
| T008 | Implement get_depletion_history() | WP02 | P1 | No | Claude |
| T009 | Add session parameter support | WP02 | P1 | No | Claude |
| T010 | Create test file | WP03 | P1 | Yes | Claude |
| T011 | Test happy path | WP03 | P1 | Yes | Claude |
| T012 | Test quantity > current fails | WP03 | P1 | Yes | Claude |
| T013 | Test quantity <= 0 fails | WP03 | P1 | Yes | Claude |
| T014 | Test notes required for OTHER | WP03 | P1 | Yes | Claude |
| T015 | Test cost calculation | WP03 | P1 | Yes | Claude |
| T016 | Test history DESC order | WP03 | P1 | Yes | Claude |
| T017 | Create dialog class | WP04 | P1 | No | Gemini |
| T018 | Implement dialog layout | WP04 | P1 | No | Gemini |
| T019 | Add quantity input field | WP04 | P1 | No | Gemini |
| T020 | Add reason dropdown | WP04 | P1 | No | Gemini |
| T021 | Add notes text field | WP04 | P1 | No | Gemini |
| T022 | Implement live preview | WP04 | P1 | No | Gemini |
| T023 | Add Apply/Cancel buttons | WP04 | P1 | No | Gemini |
| T024 | Add [Adjust] button to inventory tab | WP05 | P2 | Yes | Gemini |
| T025 | Wire button to dialog | WP05 | P2 | No | Gemini |
| T026 | Wire Apply to service | WP05 | P2 | No | Gemini |
| T027 | Handle ValidationError | WP05 | P2 | No | Gemini |
| T028 | Refresh inventory after adjustment | WP05 | P2 | No | Gemini |
| T029 | Update history view | WP05 | P2 | Yes | Gemini |
