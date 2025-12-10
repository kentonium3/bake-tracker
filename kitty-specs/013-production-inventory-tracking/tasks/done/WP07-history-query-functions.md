---
work_package_id: "WP07"
subtasks:
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
title: "History & Query Functions"
phase: "Phase 4 - History"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "17214"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T17:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - History & Query Functions

## Objectives & Success Criteria

Implement history query functions for production and assembly tracking:
- `get_production_history()` - Query production runs with filters
- `get_production_run()` - Get single production run with consumption details
- `get_assembly_history()` - Query assembly runs with filters
- `get_assembly_run()` - Get single assembly run with consumption details

**Success Criteria**:
- [ ] Can query production history with recipe_id, date range, pagination
- [ ] Can query assembly history with finished_good_id, date range, pagination
- [ ] Single-run queries include full consumption ledger details
- [ ] Eager loading prevents N+1 queries

## Context & Constraints

**Reference Documents**:
- `kitty-specs/013-production-inventory-tracking/contracts/batch_production_service.py` - History function signatures
- `kitty-specs/013-production-inventory-tracking/contracts/assembly_service.py` - History function signatures
- `kitty-specs/013-production-inventory-tracking/spec.md` - User Story 5

**Query Requirements**:
- Filter by recipe_id, finished_unit_id, finished_good_id
- Filter by date range (start_date, end_date)
- Pagination with limit/offset
- Include consumption details optionally

## Subtasks & Detailed Guidance

### Subtask T036 - Implement get_production_history()
- **Purpose**: Query production runs with optional filters
- **File**: `src/services/batch_production_service.py`
- **Parallel?**: Yes

**Function Signature**:
```python
def get_production_history(
    *,
    recipe_id: Optional[int] = None,
    finished_unit_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    include_consumptions: bool = False,
    session=None
) -> List[Dict[str, Any]]:
```

**Implementation**:
```python
def get_production_history(...):
    with session_scope() as session:
        query = session.query(ProductionRun)

        # Apply filters
        if recipe_id:
            query = query.filter(ProductionRun.recipe_id == recipe_id)
        if finished_unit_id:
            query = query.filter(ProductionRun.finished_unit_id == finished_unit_id)
        if start_date:
            query = query.filter(ProductionRun.produced_at >= start_date)
        if end_date:
            query = query.filter(ProductionRun.produced_at <= end_date)

        # Eager load relationships to avoid N+1
        query = query.options(
            joinedload(ProductionRun.recipe),
            joinedload(ProductionRun.finished_unit)
        )
        if include_consumptions:
            query = query.options(joinedload(ProductionRun.consumptions))

        # Order and paginate
        query = query.order_by(ProductionRun.produced_at.desc())
        query = query.offset(offset).limit(limit)

        runs = query.all()
        return [run.to_dict(include_relationships=include_consumptions) for run in runs]
```

### Subtask T037 - Implement get_production_run()
- **Purpose**: Get single production run with full details
- **File**: `src/services/batch_production_service.py`
- **Parallel?**: Yes

**Function Signature**:
```python
def get_production_run(
    production_run_id: int,
    *,
    include_consumptions: bool = True,
    session=None
) -> Dict[str, Any]:
```

**Implementation**:
```python
def get_production_run(production_run_id, *, include_consumptions=True, session=None):
    with session_scope() as session:
        query = session.query(ProductionRun).filter(ProductionRun.id == production_run_id)

        query = query.options(
            joinedload(ProductionRun.recipe),
            joinedload(ProductionRun.finished_unit)
        )
        if include_consumptions:
            query = query.options(joinedload(ProductionRun.consumptions))

        run = query.first()
        if not run:
            raise ProductionRunNotFoundError(production_run_id)

        result = run.to_dict(include_relationships=True)

        # Add recipe and finished_unit names for convenience
        result["recipe_name"] = run.recipe.name
        result["finished_unit_name"] = run.finished_unit.display_name

        if include_consumptions:
            result["consumptions"] = [c.to_dict() for c in run.consumptions]

        return result
```

### Subtask T038 - Implement get_assembly_history()
- **Purpose**: Query assembly runs with optional filters
- **File**: `src/services/assembly_service.py`
- **Parallel?**: Yes

**Function Signature**:
```python
def get_assembly_history(
    *,
    finished_good_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    include_consumptions: bool = False,
    session=None
) -> List[Dict[str, Any]]:
```

**Implementation**: Similar pattern to get_production_history()

### Subtask T039 - Implement get_assembly_run()
- **Purpose**: Get single assembly run with full details
- **File**: `src/services/assembly_service.py`
- **Parallel?**: Yes

**Function Signature**:
```python
def get_assembly_run(
    assembly_run_id: int,
    *,
    include_consumptions: bool = True,
    session=None
) -> Dict[str, Any]:
```

**Implementation**:
```python
def get_assembly_run(assembly_run_id, *, include_consumptions=True, session=None):
    with session_scope() as session:
        query = session.query(AssemblyRun).filter(AssemblyRun.id == assembly_run_id)

        query = query.options(joinedload(AssemblyRun.finished_good))
        if include_consumptions:
            query = query.options(
                joinedload(AssemblyRun.finished_unit_consumptions).joinedload(
                    AssemblyFinishedUnitConsumption.finished_unit
                ),
                joinedload(AssemblyRun.packaging_consumptions).joinedload(
                    AssemblyPackagingConsumption.product
                )
            )

        run = query.first()
        if not run:
            raise AssemblyRunNotFoundError(assembly_run_id)

        result = run.to_dict(include_relationships=True)
        result["finished_good_name"] = run.finished_good.name

        if include_consumptions:
            result["finished_unit_consumptions"] = [
                {
                    **c.to_dict(),
                    "finished_unit_name": c.finished_unit.display_name
                }
                for c in run.finished_unit_consumptions
            ]
            result["packaging_consumptions"] = [
                {
                    **c.to_dict(),
                    "product_name": c.product.name
                }
                for c in run.packaging_consumptions
            ]

        return result
```

### Subtask T040 - Add tests for history query functions
- **Purpose**: Verify history queries work correctly
- **File**: Add to existing test files
- **Parallel?**: No (depends on T036-T039)

**Tests to Add**:
```python
# In test_batch_production_service.py
def test_get_production_history_filters(multiple_production_runs):
    """History query respects filters."""
    # Test recipe_id filter
    # Test date range filter
    # Test pagination

def test_get_production_run_with_consumptions(production_run_with_consumptions):
    """Single run includes consumption details."""
    result = batch_production_service.get_production_run(production_run_id, include_consumptions=True)
    assert "consumptions" in result
    assert len(result["consumptions"]) > 0

# In test_assembly_service.py
def test_get_assembly_history_filters(multiple_assembly_runs):
    """Assembly history query respects filters."""

def test_get_assembly_run_with_consumptions(assembly_run_with_consumptions):
    """Single assembly run includes both consumption types."""
    result = assembly_service.get_assembly_run(assembly_run_id)
    assert "finished_unit_consumptions" in result
    assert "packaging_consumptions" in result
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| N+1 query performance | Use eager loading with joinedload() |
| Large result sets | Enforce pagination with reasonable defaults |
| Missing NotFoundError | Add ProductionRunNotFoundError, AssemblyRunNotFoundError |

## Definition of Done Checklist

- [ ] T036: get_production_history() with filters and pagination
- [ ] T037: get_production_run() with consumption details
- [ ] T038: get_assembly_history() with filters and pagination
- [ ] T039: get_assembly_run() with consumption details
- [ ] T040: Tests for all history functions
- [ ] No N+1 queries (verify with query logging)
- [ ] `tasks.md` updated

## Review Guidance

**Reviewer Checklist**:
- [ ] All filters work correctly
- [ ] Pagination with limit/offset works
- [ ] Eager loading prevents N+1 queries
- [ ] to_dict() includes all necessary fields
- [ ] NotFoundError exceptions added

## Activity Log

- 2025-12-09T17:30:00Z - system - lane=planned - Prompt created.
- 2025-12-10T03:49:08Z – claude – shell_pid=15592 – lane=doing – Implementation complete - get_production_history, get_assembly_history and related query functions
- 2025-12-10T03:49:08Z – claude – shell_pid=15592 – lane=for_review – Ready for review - history queries with filtering, pagination, eager loading
- 2025-12-10T03:54:06Z – claude-reviewer – shell_pid=17214 – lane=done – Review approved: get_production_history, get_assembly_history with filters and pagination
