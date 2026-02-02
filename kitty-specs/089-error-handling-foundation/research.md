# Research: Error Handling Foundation

**Feature**: 089-error-handling-foundation
**Date**: 2026-02-02
**Status**: Complete

## Research Questions

### Q1: Current Exception Hierarchy State

**Finding**: Two parallel base classes exist:
- `ServiceException(Exception)` - Legacy base (7 subclasses)
- `ServiceError(Exception)` - New base (12 subclasses in exceptions.py)

**Legacy exceptions (inheriting ServiceException)**:
- `IngredientNotFound`
- `RecipeNotFound`
- `IngredientInUse`
- `ValidationError`
- `InsufficientStock`
- `DatabaseError`
- `HierarchyValidationError` (and its subclasses)

**New exceptions (inheriting ServiceError)**:
- `IngredientNotFoundBySlug`
- `ProductNotFound`
- `InventoryItemNotFound`
- `MaterialInventoryItemNotFoundError` (DUPLICATE - defined twice!)
- `PurchaseNotFound`
- `SlugAlreadyExists`
- `ProductInUse`
- `SupplierNotFoundError`
- `PlanStateError`

**Decision**: Migrate all `ServiceException` subclasses to `ServiceError`. Remove `ServiceException` after migration.

### Q2: Service-Local Exception Inventory

**Finding**: 60+ exception classes defined in service modules, most inherit from `Exception` directly.

| Service Module | Exception Classes | Current Base |
|----------------|-------------------|--------------|
| `batch_production_service.py` | RecipeNotFoundError, FinishedUnitNotFoundError, FinishedUnitRecipeMismatchError, InsufficientInventoryError, EventNotFoundError, ActualYieldExceedsExpectedError, ProductionRunNotFoundError | `Exception` |
| `assembly_service.py` | FinishedGoodNotFoundError, InsufficientFinishedUnitError, InsufficientFinishedGoodError, InsufficientPackagingError, EventNotFoundError, AssemblyRunNotFoundError, UnassignedPackagingError | `Exception` |
| `production_service.py` | InsufficientInventoryError, RecipeNotFoundError, ProductionExceedsPlannedError, InvalidStatusTransitionError, IncompleteProductionError, AssignmentNotFoundError | `Exception` |
| `event_service.py` | EventNotFoundError, EventHasAssignmentsError, AssignmentNotFoundError, RecipientNotFoundError, DuplicateAssignmentError, CircularReferenceError, MaxDepthExceededError | `Exception` |
| `finished_good_service.py` | FinishedGoodNotFoundError, CircularReferenceError, InsufficientInventoryError, InvalidComponentError, AssemblyIntegrityError, SnapshotCreationError, SnapshotCircularReferenceError, MaxDepthExceededError | `ServiceError` |
| `finished_unit_service.py` | FinishedUnitNotFoundError, InvalidInventoryError, DuplicateSlugError, ReferencedUnitError, SnapshotCreationError | `ServiceError` |
| `composition_service.py` | CompositionNotFoundError, InvalidComponentTypeError, CircularReferenceError, DuplicateCompositionError, IntegrityViolationError | `ServiceError` |
| `package_service.py` | PackageNotFoundError, PackageInUseError, InvalidFinishedGoodError, DuplicatePackageNameError, PackageFinishedGoodNotFoundError | `Exception` |
| `packaging_service.py` | PackagingServiceError, GenericProductNotFoundError, CompositionNotFoundError, NotGenericCompositionError, InvalidAssignmentError, InsufficientInventoryError, ProductMismatchError | `PackagingServiceError` (local) |
| `material_consumption_service.py` | MaterialConsumptionError, InsufficientMaterialError, MaterialAssignmentRequiredError | `MaterialConsumptionError` (local) |
| `planning/planning_service.py` | PlanningError, StalePlanError, IncompleteRequirementsError, EventNotConfiguredError, EventNotFoundError | `PlanningError` (local) |
| Other services | Various | Mixed |

**Decision**: Keep service-local exceptions in their modules (per planning discussion). Update inheritance to `ServiceError` for all.

### Q3: Duplicate Exception Classes

**Finding**: Multiple exception classes with same name defined in different files:

| Class Name | Files | Resolution |
|------------|-------|------------|
| `MaterialInventoryItemNotFoundError` | exceptions.py (lines 176 & 261) | Remove duplicate definition |
| `CircularReferenceError` | exceptions.py, composition_service.py, event_service.py, finished_good_service.py | Keep in exceptions.py, import elsewhere |
| `MaxDepthExceededError` | exceptions.py, event_service.py, finished_good_service.py | Keep in exceptions.py, import elsewhere |
| `InsufficientInventoryError` | batch_production_service.py, production_service.py, finished_good_service.py, packaging_service.py | Keep service-specific versions (different context) |
| `EventNotFoundError` | batch_production_service.py, assembly_service.py, event_service.py, planning_service.py | Consolidate to single definition |
| `SnapshotCreationError` | finished_unit_service.py, finished_good_service.py, material_unit_service.py, recipe_snapshot_service.py | Keep service-specific (different contexts) |
| `RecipeNotFoundError` | batch_production_service.py, production_service.py | Consolidate |
| `FinishedGoodNotFoundError` | assembly_service.py, finished_good_service.py | Consolidate |

**Decision**:
- Remove exact duplicates (same file)
- For cross-file duplicates with identical semantics: consolidate to exceptions.py
- For cross-file duplicates with different context: keep separate, ensure `ServiceError` inheritance

### Q4: UI Error Display Patterns

**Finding**: 461 `except Exception` occurrences across 88 files.

**Current patterns observed**:

1. **Direct messagebox** (most common):
   ```python
   except Exception as e:
       messagebox.showerror("Error", str(e))
   ```

2. **Helper functions** (src/ui/widgets/dialogs.py):
   ```python
   show_error(title, message, parent=None)  # Uses messagebox.showerror
   ```

3. **Silent failures**:
   ```python
   except Exception:
       return []  # Silently returns empty
   ```

4. **Specific + generic**:
   ```python
   except ValidationError as e:
       messagebox.showerror("Validation Error", str(e))
   except Exception as e:
       messagebox.showerror("Error", f"Failed: {str(e)}")
   ```

**Decision**: Create centralized error handler that:
- Maps exception types to user-friendly messages
- Logs technical details (exception type, message, context, stack trace)
- Supports optional correlation ID
- Returns structured result for UI display

### Q5: HTTP Status Code Mapping

**Finding**: Constitution requires exception hierarchy to map to HTTP status codes for web migration.

**Proposed mapping**:

| Exception Pattern | HTTP Status | User Message Pattern |
|-------------------|-------------|---------------------|
| `*NotFound*` | 404 | "[Entity] not found" |
| `ValidationError`, `Invalid*` | 400 | "Validation failed: [details]" |
| `*InUse*`, `*HasAssignments*` | 409 | "Cannot delete: [entity] is in use" |
| `Insufficient*` | 422 | "Not enough [resource]" |
| `CircularReference*` | 422 | "Operation would create circular reference" |
| `Duplicate*`, `*AlreadyExists` | 409 | "[Entity] already exists" |
| `*StateError`, `InvalidTransition*` | 409 | "Invalid state for operation" |
| `DatabaseError` | 500 | "Database error occurred" |
| Generic `ServiceError` | 500 | "Operation failed" |
| Unexpected `Exception` | 500 | "An unexpected error occurred" |

**Decision**: Add `http_status_code` class attribute to `ServiceError` and subclasses.

## Research Artifacts

- Exception hierarchy documented in `data-model.md`
- File inventory for UI updates in `tasks.md` (generated by /spec-kitty.tasks)

## Alternatives Considered

### Full Centralization vs Partial Centralization

**Option A**: Move ALL exceptions to `exceptions.py`
- Pro: Single source of truth
- Con: Large file, tight coupling, circular import risks

**Option B (Selected)**: Keep service-local exceptions, ensure `ServiceError` inheritance
- Pro: Maintains cohesion, avoids circular imports
- Con: Must ensure consistent inheritance

**Rationale**: Option B balances organization with practical concerns. Service-local exceptions are domain-specific and tightly coupled to their service logic.
