# Research: Production-Aware Planning Calculations

**Feature**: F079 | **Date**: 2026-01-28

## Research Summary

Minimal research required - the codebase exploration during planning discovery resolved all unknowns.

## Findings

### 1. Progress Tracking Architecture

**Current State**: `planning/progress.py` already provides `ProductionProgress` DTO with:
- `target_batches` (from EventProductionTarget)
- `completed_batches` (from ProductionRun aggregation via event_service)

**Decision**: Extend existing DTO rather than create new module.

**Rationale**: Single source of truth for progress data; avoids duplication.

### 2. Feasibility Check Integration Point

**Current State**: `planning/feasibility.py` line 254-256:
```python
check_result = batch_production_service.check_can_produce(
    target.recipe_id,
    target.target_batches,  # <-- Uses total, not remaining
    session=session,
)
```

**Decision**: Add `production_aware` flag to use remaining instead of total.

**Rationale**: Backward-compatible; existing callers get production-aware behavior by default.

### 3. Shopping List Integration Point

**Current State**: `planning/shopping_list.py` wraps `event_service.get_shopping_list()` which calculates needs based on total batch targets.

**Decision**: Either modify event_service or add wrapper that filters to remaining needs.

**Rationale**: Shopping list during production should only show what's still needed.

### 4. Amendment Validation Integration Point

**Current State**: `plan_amendment_service.py` has `_validate_amendment_allowed()` that checks plan state but not production status.

**Decision**: Add production status check in the specific amendment functions (`modify_batch_decision`, `drop_finished_good`).

**Rationale**: Validation is amendment-type-specific; batch modifications need recipe check, FG drops need FG-recipes check.

## Alternatives Considered

| Decision | Alternative | Why Rejected |
|----------|-------------|--------------|
| Extend ProductionProgress DTO | New RemainingNeeds DTO | Over-engineering; progress already has the data |
| Add production_aware flag | Always use remaining | Would break existing callers expecting total |
| Check production in amendment functions | Global production check | Not all amendments need production check (ADD_FG is fine) |

## Dependencies Identified

- `event_service.get_production_progress()` - provides completed batch counts
- `batch_production_service.check_can_produce()` - feasibility check engine
- `event_service.get_shopping_list()` - shopping list calculation engine

## No Blocking Issues

All integration points are clear and follow existing patterns.
