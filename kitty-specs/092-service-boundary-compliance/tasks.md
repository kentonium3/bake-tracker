# F092 Service Boundary Compliance - Task Breakdown

**Feature**: 092-service-boundary-compliance
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Status**: Ready for implementation

---

## Subtask Registry

| ID | Summary | WP | Parallel? | Dependencies |
|----|---------|-----|-----------|--------------|
| T001 | Add session param to product_service.get_product() | WP01 | No | - |
| T002 | Create supplier_service.get_or_create_supplier() | WP01 | No | - |
| T003 | Update purchase_service to delegate to services | WP01 | No | T001, T002 |
| T004 | Add tests for get_or_create_supplier() | WP01 | Yes [P] | T002 |
| T005 | Verify existing purchase_service tests pass | WP01 | No | T003 |
| T006 | Update docstrings with F091 transaction boundaries | WP01 | Yes [P] | T001, T002, T003 |

---

## Work Packages

### WP01: Service Boundary Compliance Implementation

**Summary**: Implement proper service delegation in purchase_service by adding session parameter support to product_service.get_product() and creating a new supplier_service.get_or_create_supplier() function.

**Priority**: HIGH
**Phase**: Implementation
**Estimated Lines**: ~155
**Prompt**: [WP01-service-boundary-compliance.md](tasks/WP01-service-boundary-compliance.md)

**Subtasks**:
- [x] T001: Add session param to product_service.get_product()
- [x] T002: Create supplier_service.get_or_create_supplier()
- [x] T003: Update purchase_service to delegate to services
- [x] T004: Add tests for get_or_create_supplier()
- [ ] T005: Verify existing purchase_service tests pass
- [ ] T006: Update docstrings with F091 transaction boundaries

**Dependencies**: None (foundational WP)

**Risks**:
- Breaking existing get_product() callers → Mitigated: session param is optional
- Breaking purchase flow → Mitigated: exact defaults preserved

---

## Implementation Order

```
WP01: Service Boundary Compliance Implementation
├── T001: product_service.get_product() session param
├── T002: supplier_service.get_or_create_supplier()
├── T003: purchase_service delegation
├── T004: Tests for get_or_create_supplier() [P]
├── T005: Verify existing tests pass
└── T006: Update docstrings [P]
```

Single work package - all subtasks completed sequentially except T004 and T006 which can run in parallel after their dependencies.

---

## Progress Tracking

- **Total WPs**: 1
- **Total Subtasks**: 6
- **Completion**: 0/1 WPs done

---

## Next Command

```bash
spec-kitty implement WP01
```
