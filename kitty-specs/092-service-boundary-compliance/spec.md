# F092: Service Boundary Compliance - Purchase Service

**Feature ID**: 092-service-boundary-compliance
**Version**: 1.0
**Priority**: HIGH
**Type**: Architecture Compliance + Code Quality

---

## Overview

The `purchase_service.record_purchase()` function currently violates service boundary principles by directly querying models and creating entities inline instead of delegating to the appropriate services. This feature refactors the purchase service to implement proper service delegation, ensuring compliance with the documented transaction boundary patterns (F091).

## Problem Statement

**Current Violations:**
- Direct `Product` model queries (bypasses `product_catalog_service`)
- Inline `Supplier` creation (bypasses `supplier_service`)
- No service delegation for entity lookup/creation
- Hardcoded placeholder values scattered in code

**Impact:**
- Cross-cutting concerns bypassed (audit, cache, provisional)
- Validation rules bypassed
- No slug generation for suppliers (when TD-009 implemented)
- Duplicated logic (supplier creation)

## User Scenarios

### Scenario 1: Recording a Purchase with New Supplier
**Actor**: System/API caller
**Flow**:
1. Caller invokes `record_purchase()` with product_id and store name
2. Service delegates product lookup to `product_catalog_service`
3. Service delegates supplier get-or-create to `supplier_service`
4. Purchase record created with proper entity references
5. All operations atomic within single transaction

**Acceptance Criteria**:
- Product lookup uses `product_catalog_service.get_product()`
- Supplier lookup/create uses `supplier_service.get_or_create_supplier()`
- Transaction rollback on any failure
- Behavior matches current functionality (backward compatible)

### Scenario 2: Recording a Purchase with Existing Supplier
**Actor**: System/API caller
**Flow**:
1. Caller invokes `record_purchase()` with known store name
2. Service delegates supplier lookup (finds existing)
3. No new supplier created
4. Purchase uses existing supplier_id

**Acceptance Criteria**:
- Existing supplier reused (not duplicated)
- Same lookup logic as current implementation (name-only match)

### Scenario 3: Invalid Product
**Actor**: System/API caller
**Flow**:
1. Caller invokes `record_purchase()` with invalid product_id
2. `product_catalog_service.get_product()` raises `ProductNotFound`
3. Transaction rolled back
4. Exception propagated to caller

**Acceptance Criteria**:
- `ProductNotFound` exception from delegated service
- No partial records created

---

## Functional Requirements

### FR-1: Delegate Product Lookup to Product Catalog Service
- Replace direct `Product` model query with `product_catalog_service.get_product()`
- Pass session parameter for transaction composition
- Rely on service to raise `ProductNotFound` (no manual check needed)

### FR-2: Create Supplier Service Get-or-Create Function
- Add `get_or_create_supplier()` to `supplier_service`
- Accept optional session parameter for composition
- Centralize default values ("Unknown" city, "XX" state, "00000" zip)
- Support future slug generation (TD-009 comment)

### FR-3: Update Purchase Service to Delegate Supplier Operations
- Replace inline supplier query/creation with `supplier_service.get_or_create_supplier()`
- Pass session parameter for transaction composition
- Remove hardcoded defaults from purchase service

---

## Out of Scope

- **Supplier slug generation** - Deferred to TD-009
- **Enhanced supplier matching** - Current name-only lookup preserved
- **Purchase service transaction optimization** - Only fixing boundaries
- **Product catalog enhancements** - Using service as-is

---

## Success Criteria

### Service Delegation
- `product_catalog_service.get_product()` used (no direct Product query)
- `supplier_service.get_or_create_supplier()` created and used
- No direct model queries in `purchase_service` for Product or Supplier
- Session parameter passed to all service calls

### Transaction Integrity (F091)
- Transaction boundaries documented per F091 pattern
- Docstring explains atomicity guarantee
- All nested service calls receive session parameter
- No nested `session_scope()` calls

### Code Quality
- Hardcoded defaults removed from purchase service
- Supplier creation logic centralized in supplier service
- Service boundaries clear and documented

### Testing
- Tests verify product delegation works
- Tests verify supplier get-or-create works (new and existing)
- Tests verify transaction atomicity
- Integration test for full purchase flow

---

## Key Entities

### Supplier (affected)
- `get_or_create_supplier()` function added to supplier_service
- Default values: name (required), city="Unknown", state="XX", zip_code="00000"

### Purchase (affected)
- No model changes
- Service layer refactored to use proper delegation

### Product (no changes)
- Uses existing `product_catalog_service.get_product()`

---

## Dependencies

- **F091**: Transaction Boundary Documentation - Provides patterns
- **product_catalog_service**: Must have `get_product()` accepting session parameter
- **supplier_service**: Will add `get_or_create_supplier()` function

---

## Assumptions

1. `product_catalog_service.get_product()` exists and accepts session parameter (or can be updated per F091)
2. `supplier_service.py` exists and can be extended
3. Current purchase behavior (defaults, name-only matching) is acceptable to preserve
4. No data migration needed (behavior-preserving refactor)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing purchase flow | Preserve exact behavior (defaults match current values); comprehensive testing |
| get_product() missing session param | Verify before implementation; add if needed (F091 pattern) |
| Supplier matching logic change | Use same name-only logic as current implementation |

---

## Constitutional Compliance

- **Principle VI.C.1: Dependency Injection** - Services passed via delegation
- **Principle VI.C.2: Transaction Boundaries** - Purchase service maintains transaction scope
- **F091: Session Composition Pattern** - All nested calls receive session parameter
- **Layered Architecture** - Services coordinate, owning services handle entities
