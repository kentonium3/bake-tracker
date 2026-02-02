---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "Service-Local Exception Fixes"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-02-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Service-Local Exception Fixes

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address feedback items first.

---

## Review Feedback

*[Empty initially. Reviewers populate if work needs changes.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

**Depends on**: WP01 (ServiceError base must be updated first)

---

## Objectives & Success Criteria

**Objective**: Update 60+ service-local exception classes to inherit from `ServiceError` instead of bare `Exception`.

**Success Criteria**:
- [ ] All exceptions in `batch_production_service.py` inherit from `ServiceError`
- [ ] All exceptions in `assembly_service.py` inherit from `ServiceError`
- [ ] All exceptions in `production_service.py` inherit from `ServiceError`
- [ ] All exceptions in `event_service.py` inherit from `ServiceError`
- [ ] All exceptions in `planning/planning_service.py` inherit from `ServiceError`
- [ ] All exceptions in `package_service.py` and `packaging_service.py` inherit from `ServiceError`
- [ ] All remaining service exceptions inherit from `ServiceError`
- [ ] Each exception has appropriate `http_status_code`

---

## Context & Constraints

**Reference Documents**:
- Research: `kitty-specs/089-error-handling-foundation/research.md` (Q2: Service-Local Exception Inventory)
- Data Model: `kitty-specs/089-error-handling-foundation/data-model.md`

**Pattern to Apply**:
```python
# Before
class RecipeNotFoundError(Exception):
    def __init__(self, recipe_id: int):
        self.recipe_id = recipe_id
        super().__init__(f"Recipe with ID {recipe_id} not found")

# After
from src.services.exceptions import ServiceError

class RecipeNotFoundError(ServiceError):
    """Raised when recipe cannot be found by ID."""
    http_status_code = 404

    def __init__(self, recipe_id: int, correlation_id: Optional[str] = None):
        self.recipe_id = recipe_id
        super().__init__(
            f"Recipe with ID {recipe_id} not found",
            correlation_id=correlation_id,
            recipe_id=recipe_id
        )
```

**HTTP Status Code Guide**:
- `*NotFound*` → 404
- `*Validation*`, `Invalid*` → 400
- `*InUse*`, `*Conflict*`, `Duplicate*` → 409
- `Insufficient*`, `*Exceeds*` → 422
- Generic errors → 500

**Constraints**:
- Do NOT move exceptions to `exceptions.py` - keep them in their service modules
- Preserve ALL existing attributes and behavior
- Add `correlation_id` parameter but make it optional with default `None`

---

## Subtasks & Detailed Guidance

### Subtask T007 – Update batch_production_service.py Exceptions

**Purpose**: Fix inheritance for 7 exception classes in batch production service.

**Steps**:
1. Open `src/services/batch_production_service.py`
2. Add import at top: `from src.services.exceptions import ServiceError`
3. Add `from typing import Optional` if not present
4. Update each exception class:

| Class | HTTP Code | Key Attributes |
|-------|-----------|----------------|
| `RecipeNotFoundError` | 404 | `recipe_id` |
| `FinishedUnitNotFoundError` | 404 | `finished_unit_id` |
| `FinishedUnitRecipeMismatchError` | 400 | `finished_unit_id`, `recipe_id` |
| `InsufficientInventoryError` | 422 | `ingredient_slug`, `needed`, `available`, `unit` |
| `EventNotFoundError` | 404 | `event_id` |
| `ActualYieldExceedsExpectedError` | 422 | `actual_yield`, `expected_yield` |
| `ProductionRunNotFoundError` | 404 | `production_run_id` |

**Example for InsufficientInventoryError** (most complex):
```python
class InsufficientInventoryError(ServiceError):
    """Raised when there is insufficient inventory for production."""
    http_status_code = 422

    def __init__(
        self,
        ingredient_slug: str,
        needed: float,
        available: float,
        unit: str,
        correlation_id: Optional[str] = None
    ):
        self.ingredient_slug = ingredient_slug
        self.needed = needed
        self.available = available
        self.unit = unit
        super().__init__(
            f"Insufficient inventory for '{ingredient_slug}': need {needed} {unit}, have {available} {unit}",
            correlation_id=correlation_id,
            ingredient_slug=ingredient_slug,
            needed=needed,
            available=available,
            unit=unit
        )
```

**Files**: `src/services/batch_production_service.py`
**Parallel?**: Yes

---

### Subtask T008 – Update assembly_service.py Exceptions

**Purpose**: Fix inheritance for 7 exception classes in assembly service.

**Steps**:
1. Open `src/services/assembly_service.py`
2. Add imports: `from src.services.exceptions import ServiceError` and `from typing import Optional`
3. Update each exception:

| Class | HTTP Code | Key Attributes |
|-------|-----------|----------------|
| `FinishedGoodNotFoundError` | 404 | `finished_good_id` |
| `InsufficientFinishedUnitError` | 422 | `finished_unit_id`, `needed`, `available` |
| `InsufficientFinishedGoodError` | 422 | `finished_good_id`, `needed`, `available` |
| `InsufficientPackagingError` | 422 | `product_id`, `needed`, `available` |
| `EventNotFoundError` | 404 | `event_id` |
| `AssemblyRunNotFoundError` | 404 | `assembly_run_id` |
| `UnassignedPackagingError` | 400 | varies |

**Files**: `src/services/assembly_service.py`
**Parallel?**: Yes

---

### Subtask T009 – Update production_service.py Exceptions

**Purpose**: Fix inheritance for 6 exception classes.

**Steps**:
1. Open `src/services/production_service.py`
2. Add imports
3. Update each exception:

| Class | HTTP Code | Key Attributes |
|-------|-----------|----------------|
| `InsufficientInventoryError` | 422 | (check existing attrs) |
| `RecipeNotFoundError` | 404 | `recipe_id` |
| `ProductionExceedsPlannedError` | 422 | (check existing attrs) |
| `InvalidStatusTransitionError` | 409 | (check existing attrs) |
| `IncompleteProductionError` | 400 | (check existing attrs) |
| `AssignmentNotFoundError` | 404 | (check existing attrs) |

**Files**: `src/services/production_service.py`
**Parallel?**: Yes

---

### Subtask T010 – Update event_service.py Exceptions

**Purpose**: Fix inheritance for 7 exception classes.

**Steps**:
1. Open `src/services/event_service.py`
2. Add imports
3. Update each exception:

| Class | HTTP Code |
|-------|-----------|
| `EventNotFoundError` | 404 |
| `EventHasAssignmentsError` | 409 |
| `AssignmentNotFoundError` | 404 |
| `RecipientNotFoundError` | 404 |
| `DuplicateAssignmentError` | 409 |
| `CircularReferenceError` | 422 |
| `MaxDepthExceededError` | 422 |

**Files**: `src/services/event_service.py`
**Parallel?**: Yes

---

### Subtask T011 – Update planning/planning_service.py Exceptions

**Purpose**: Fix inheritance for 5 exception classes in planning service.

**Steps**:
1. Open `src/services/planning/planning_service.py`
2. Add imports
3. Update the base `PlanningError` and its subclasses:

```python
class PlanningError(ServiceError):
    """Base for planning-related errors."""
    http_status_code = 400

class StalePlanError(PlanningError):
    """Raised when plan data is stale."""
    http_status_code = 409
    # ... preserve existing __init__

class IncompleteRequirementsError(PlanningError):
    http_status_code = 400

class EventNotConfiguredError(PlanningError):
    http_status_code = 400

class EventNotFoundError(PlanningError):
    http_status_code = 404
```

**Files**: `src/services/planning/planning_service.py`
**Parallel?**: Yes

---

### Subtask T012 – Update package_service.py and packaging_service.py Exceptions

**Purpose**: Fix inheritance for 12 exception classes across both files.

**Steps**:
1. **package_service.py** exceptions:
   - `PackageNotFoundError` → 404
   - `PackageInUseError` → 409
   - `InvalidFinishedGoodError` → 400
   - `DuplicatePackageNameError` → 409
   - `PackageFinishedGoodNotFoundError` → 404

2. **packaging_service.py** exceptions:
   - First update base: `PackagingServiceError(ServiceError)`
   - Then update subclasses (they already inherit from PackagingServiceError):
   - `GenericProductNotFoundError` → 404
   - `CompositionNotFoundError` → 404
   - `NotGenericCompositionError` → 400
   - `InvalidAssignmentError` → 400
   - `InsufficientInventoryError` → 422
   - `ProductMismatchError` → 400

**Files**: `src/services/package_service.py`, `src/services/packaging_service.py`
**Parallel?**: Yes

---

### Subtask T013 – Update Remaining Service Exceptions

**Purpose**: Fix inheritance for exceptions in remaining services.

**Services to update**:
1. **material_consumption_service.py**:
   - `MaterialConsumptionError(ServiceError)` - base
   - `InsufficientMaterialError` → 422
   - `MaterialAssignmentRequiredError` → 400

2. **fk_resolver_service.py**:
   - `FKResolutionError(ServiceError)` → 400
   - `EntityCreationError` → 400

3. **recipient_service.py**:
   - `RecipientHasAssignmentsError` → 409

4. **catalog_import_service.py**:
   - `CatalogImportError` → 400

5. **material_unit_service.py**:
   - `MaterialUnitNotFoundError` → 404
   - `MaterialProductNotFoundError` → 404
   - `MaterialUnitInUseError` → 409
   - `SnapshotCreationError` → 500

6. **material_purchase_service.py**:
   - `MaterialProductNotFoundError` → 404
   - `SupplierNotFoundError` → 404

7. **recipe_snapshot_service.py**:
   - `SnapshotCreationError` → 500

8. **import_export_service.py**:
   - `ImportVersionError` → 400

**Note**: Some services like `finished_good_service.py`, `finished_unit_service.py`, `composition_service.py` already inherit from `ServiceError` - verify and add `http_status_code` if missing.

**Files**: Multiple service files
**Parallel?**: Yes

---

## Test Strategy

**Verification Script**:
```python
# Run from project root
import importlib
import inspect
from src.services.exceptions import ServiceError

services = [
    'src.services.batch_production_service',
    'src.services.assembly_service',
    'src.services.production_service',
    'src.services.event_service',
    'src.services.planning.planning_service',
    'src.services.package_service',
    'src.services.packaging_service',
]

for service_path in services:
    module = importlib.import_module(service_path)
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if name.endswith('Error') and obj.__module__ == module.__name__:
            assert issubclass(obj, ServiceError), f"{name} does not inherit from ServiceError"
            assert hasattr(obj, 'http_status_code'), f"{name} missing http_status_code"
            print(f"✓ {name}: http_status_code={obj.http_status_code}")
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Import `ServiceError` at module level, not locally |
| Missing exception classes | Use grep to find all `class.*Error.*Exception` |
| Breaking existing code | Preserve all existing attributes and signatures |

---

## Definition of Done Checklist

- [ ] All exceptions in listed services inherit from `ServiceError`
- [ ] All exceptions have `http_status_code` class attribute
- [ ] All exceptions accept optional `correlation_id` parameter
- [ ] Verification script passes
- [ ] No import errors when running application

---

## Review Guidance

**Key Checkpoints**:
1. Verify imports are at module level (no circular import issues)
2. Verify `http_status_code` matches exception semantics
3. Verify existing attributes preserved
4. Run verification script

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
