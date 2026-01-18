# Tasks: F057 Purchase Management with Provisional Products

**Feature Branch**: `057-purchase-management-provisional-products`
**Created**: 2026-01-17
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Summary

Enable purchase recording regardless of product catalog state by introducing provisional product creation. When a user searches for a product during purchase entry and it doesn't exist, the form expands inline to allow creating a provisional product. Provisional products are flagged with `is_provisional=True` and appear in a review queue in the Products tab.

## Work Package Overview

| WP | Title | Subtasks | Priority | Est. Lines | Dependencies |
|----|-------|----------|----------|------------|--------------|
| WP01 | Model & Service Foundation | 6 | P0 | ~350 | None |
| WP02 | Add Purchase Dialog Enhancement | 6 | P1 | ~450 | WP01 |
| WP03 | Products Tab Review Queue | 5 | P2 | ~350 | WP01 |
| WP04 | Export/Import Integration | 5 | P3 | ~400 | WP01 |

**Total**: 22 subtasks across 4 work packages

---

## Phase 0: Foundation

### WP01: Model & Service Foundation

**Goal**: Add `is_provisional` field to Product model and extend services with provisional product support.

**Priority**: P0 (Foundation - blocks all other work)
**Prompt File**: [WP01-model-service-foundation.md](./tasks/WP01-model-service-foundation.md)
**Dependencies**: None

**Subtasks**:
- [x] T001: Add `is_provisional` field to Product model
- [x] T002: Add `create_provisional_product()` to product_service
- [x] T003: Add `get_provisional_products()` to product_catalog_service
- [x] T004: Add `get_provisional_count()` to product_catalog_service
- [x] T005: Add `mark_product_reviewed()` to product_catalog_service
- [x] T006: Write unit tests for all new service methods

**Implementation Notes**:
- Schema change requires app restart with database reset/re-import per constitution VI
- New field defaults to `False` - existing products unaffected
- All new methods follow `session: Optional[Session] = None` pattern per CLAUDE.md

**Risks**:
- Schema migration disrupts existing data (mitigate: document export/import steps)

---

## Phase 1: User Story 1 - Record Purchase for Unknown Product

### WP02: Add Purchase Dialog Enhancement

**Goal**: Enhance Add Purchase dialog with inline provisional product creation when product not found.

**Priority**: P1 (Core value proposition)
**Prompt File**: [WP02-add-purchase-dialog.md](./tasks/WP02-add-purchase-dialog.md)
**Dependencies**: WP01

**Subtasks**:
- [x] T007: Add "Product not found" detection and inline expansion trigger
- [ ] T008: Create provisional product form section with ingredient selector
- [ ] T009: Implement brand/product name prepopulation from search context
- [ ] T010: Add validation for provisional product minimum fields
- [ ] T011: Wire form to `create_provisional_product()` service method
- [ ] T012: Update dialog to continue purchase flow with newly created product

**Implementation Notes**:
- Use existing `ctk.CTkFrame` for collapsible section
- Ingredient selector follows existing cascading dropdown pattern from `_create_filters()` in products_tab.py
- Prepopulate brand if search text contains recognizable brand pattern

**Risks**:
- Dialog height may exceed screen on small displays (mitigate: make scrollable)

---

## Phase 2: User Story 2 - Review Provisional Products

### WP03: Products Tab Review Queue

**Goal**: Add review queue capabilities to Products tab with badge indicator and filter.

**Priority**: P2 (Data quality improvement)
**Prompt File**: [WP03-products-tab-review.md](./tasks/WP03-products-tab-review.md)
**Dependencies**: WP01

**Subtasks**:
- [ ] T013: Add "Needs Review" filter option to Products tab filters
- [ ] T014: Add provisional count badge to filter area
- [ ] T015: Add visual indicator for incomplete fields in product rows
- [ ] T016: Add "Mark as Reviewed" action to product context menu
- [ ] T017: Wire "Mark as Reviewed" to `mark_product_reviewed()` service

**Implementation Notes**:
- Badge shows count when provisional products exist (e.g., "Needs Review (3)")
- Use existing tag styling pattern (`self.tree.tag_configure`) for provisional indicator
- Missing field highlighting: orange border or icon in row

**Risks**:
- Badge may not update after provisional product creation (mitigate: refresh callback)

---

## Phase 3: User Story 3 - Import Integration

### WP04: Export/Import Integration

**Goal**: Extend coordinated_export_service to handle `is_provisional` field and create provisional products for unknown items during import.

**Priority**: P3 (Bulk workflow)
**Prompt File**: [WP04-export-import-integration.md](./tasks/WP04-export-import-integration.md)
**Dependencies**: WP01

**Subtasks**:
- [ ] T018: Update export to include `is_provisional` field in product records
- [ ] T019: Update import to handle missing `is_provisional` field (default False)
- [ ] T020: Add unknown product detection during transaction import
- [ ] T021: Create provisional products for unknown items with minimal required fields
- [ ] T022: Return import results with provisional products count

**Implementation Notes**:
- Import compatibility: missing field defaults to `False` for existing backups
- Unknown product creation requires: ingredient_id (lookup by name), brand, package_unit, package_unit_quantity
- Log provisional products created during import for user visibility

**Risks**:
- Ingredient lookup may fail for unknown names (mitigate: create placeholder or skip with warning)

---

## Subtask Reference

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Add is_provisional field to Product model | WP01 | - |
| T002 | Add create_provisional_product() to product_service | WP01 | [P] |
| T003 | Add get_provisional_products() to product_catalog_service | WP01 | [P] |
| T004 | Add get_provisional_count() to product_catalog_service | WP01 | [P] |
| T005 | Add mark_product_reviewed() to product_catalog_service | WP01 | [P] |
| T006 | Write unit tests for new service methods | WP01 | - |
| T007 | Add "Product not found" detection and expansion | WP02 | - |
| T008 | Create provisional product form section | WP02 | - |
| T009 | Implement brand/name prepopulation | WP02 | [P] |
| T010 | Add provisional product validation | WP02 | [P] |
| T011 | Wire form to create_provisional_product() | WP02 | - |
| T012 | Update dialog to continue with new product | WP02 | - |
| T013 | Add "Needs Review" filter option | WP03 | - |
| T014 | Add provisional count badge | WP03 | [P] |
| T015 | Add visual indicator for incomplete fields | WP03 | [P] |
| T016 | Add "Mark as Reviewed" context menu action | WP03 | - |
| T017 | Wire "Mark as Reviewed" to service | WP03 | - |
| T018 | Update export to include is_provisional | WP04 | - |
| T019 | Update import to handle missing is_provisional | WP04 | [P] |
| T020 | Add unknown product detection in import | WP04 | - |
| T021 | Create provisional products for unknowns | WP04 | - |
| T022 | Return import results with provisional count | WP04 | - |

`[P]` = Safe to parallelize with other `[P]` tasks in same WP

---

## Testing Strategy

### Unit Tests (WP01)
- `test_create_provisional_product`: Verify is_provisional=True
- `test_create_regular_product`: Verify is_provisional=False (default)
- `test_get_provisional_products`: Verify filter returns only provisional
- `test_get_provisional_count`: Verify count accuracy
- `test_mark_product_reviewed`: Verify is_provisional changes to False

### Integration Tests (WP04)
- Import with provisional field present: Verify preserved
- Import with provisional field missing: Verify defaults to False
- Import with unknown products: Verify provisional products created

### UI Tests (Manual - WP02, WP03)
- Search for non-existent product: Form should expand
- Create provisional product: Should succeed with minimal fields
- Products tab badge: Should show count when provisional exist
- Mark as reviewed: Product should leave review queue

---

## Definition of Done

A work package is complete when:
1. All subtasks checked off
2. Tests pass (unit tests for services, manual verification for UI)
3. Code follows existing patterns in codebase
4. Session management pattern followed for all service methods
5. No regressions in existing functionality

## Acceptance Criteria (from spec.md)

- [ ] **SC-001**: Purchase for unknown product < 2 minutes
- [ ] **SC-002**: 100% of purchases result in inventory updates
- [ ] **SC-003**: Access provisional products within 3 clicks
- [ ] **SC-004**: JSON import of 50+ purchases < 30 seconds
- [ ] **SC-005**: Purchase workflow never blocked by missing products
- [ ] **SC-006**: All provisional products visible in review queue
- [ ] **SC-007**: Service boundaries enforced
