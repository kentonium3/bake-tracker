---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Production Run Models"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T17:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Production Run Models

## Objectives & Success Criteria

Create the foundational SQLAlchemy models for batch production tracking:
- **ProductionRun**: Records batch production events with recipe, yield, and cost data
- **ProductionConsumption**: Ingredient-level consumption ledger for production runs

**Success Criteria**:
- [ ] Both models inherit from BaseModel correctly
- [ ] All columns, constraints, and indexes match data-model.md exactly
- [ ] Foreign key relationships properly configured
- [ ] Models can be imported from `src/models/__init__.py`
- [ ] Recipe model has `production_runs` back-reference relationship

## Context & Constraints

**Reference Documents**:
- `kitty-specs/013-production-inventory-tracking/data-model.md` - Entity definitions
- `kitty-specs/013-production-inventory-tracking/plan.md` - Technical context
- `src/models/base.py` - BaseModel pattern to follow
- `src/models/production_record.py` - Existing model for reference pattern

**Constraints**:
- Follow existing model patterns exactly (Column definitions, __table_args__, relationships)
- Use Decimal for all monetary values (Numeric(10,4))
- Include CheckConstraints for data integrity
- ProductionConsumption stores ingredient_slug (String), NOT ingredient_id FK

## Subtasks & Detailed Guidance

### Subtask T001 - Create ProductionRun model
- **Purpose**: Record batch production events linking recipes to FinishedUnits with cost tracking
- **File**: `src/models/production_run.py`
- **Parallel?**: Yes (can develop alongside T002)

**Steps**:
1. Create new file with module docstring
2. Import required SQLAlchemy components and BaseModel
3. Define ProductionRun class with columns:
   - `recipe_id` (Integer FK to recipes.id, ondelete="RESTRICT", nullable=False)
   - `finished_unit_id` (Integer FK to finished_units.id, ondelete="RESTRICT", nullable=False)
   - `num_batches` (Integer, nullable=False)
   - `expected_yield` (Integer, nullable=False)
   - `actual_yield` (Integer, nullable=False)
   - `produced_at` (DateTime, nullable=False, default=datetime.utcnow)
   - `notes` (Text, nullable=True)
   - `total_ingredient_cost` (Numeric(10,4), nullable=False, default=Decimal("0.0000"))
   - `per_unit_cost` (Numeric(10,4), nullable=False, default=Decimal("0.0000"))
4. Add relationships:
   - `recipe` -> Recipe (back_populates="production_runs")
   - `finished_unit` -> FinishedUnit
   - `consumptions` -> ProductionConsumption (back_populates="production_run", cascade="all, delete-orphan")
5. Add __table_args__ with:
   - Indexes: idx_production_run_recipe, idx_production_run_finished_unit, idx_production_run_produced_at
   - CheckConstraints: num_batches > 0, expected_yield >= 0, actual_yield >= 0, costs >= 0
6. Add `__repr__` and `to_dict` methods following BaseModel pattern

**Reference Pattern** (from production_record.py):
```python
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Index, Numeric, CheckConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel

class ProductionRun(BaseModel):
    __tablename__ = "production_runs"
    # ... columns and relationships
```

### Subtask T002 - Create ProductionConsumption model
- **Purpose**: Store ingredient-level consumption ledger entries for each production run
- **File**: `src/models/production_consumption.py`
- **Parallel?**: Yes (can develop alongside T001)

**Steps**:
1. Create new file with module docstring
2. Import required components
3. Define ProductionConsumption class with columns:
   - `production_run_id` (Integer FK to production_runs.id, ondelete="CASCADE", nullable=False)
   - `ingredient_slug` (String(100), nullable=False) - NOT a foreign key
   - `quantity_consumed` (Numeric(10,3), nullable=False)
   - `unit` (String(50), nullable=False)
   - `total_cost` (Numeric(10,4), nullable=False)
4. Add relationships:
   - `production_run` -> ProductionRun (back_populates="consumptions")
5. Add __table_args__ with:
   - Indexes: idx_prod_consumption_run, idx_prod_consumption_ingredient
   - CheckConstraints: quantity_consumed > 0, total_cost >= 0
6. Add `__repr__` and `to_dict` methods

**Note**: We store `ingredient_slug` as String, not FK, because:
- Allows flexibility for ingredient renames
- Matches design decision in research.md
- Consumption ledger is an immutable snapshot

### Subtask T003 - Update models __init__.py
- **Purpose**: Export new models so they can be imported from `src.models`
- **File**: `src/models/__init__.py`
- **Parallel?**: No (depends on T001, T002)

**Steps**:
1. Add imports for ProductionRun and ProductionConsumption
2. Add to __all__ list if one exists
3. Verify import works: `from src.models import ProductionRun, ProductionConsumption`

### Subtask T004 - Add Recipe.production_runs relationship
- **Purpose**: Enable navigation from Recipe to its ProductionRuns
- **File**: `src/models/recipe.py`
- **Parallel?**: No (depends on T001)

**Steps**:
1. Add relationship to Recipe class:
   ```python
   production_runs = relationship("ProductionRun", back_populates="recipe")
   ```
2. Verify bidirectional navigation works

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Schema mismatch with data-model.md | Validate every column against data-model.md before commit |
| Circular import with Recipe relationship | Use string references for relationship targets |
| Missing constraint or index | Cross-check __table_args__ against data-model.md spec |

## Definition of Done Checklist

- [ ] T001: ProductionRun model created with all columns, constraints, indexes
- [ ] T002: ProductionConsumption model created with all columns, constraints, indexes
- [ ] T003: Both models exported from src/models/__init__.py
- [ ] T004: Recipe.production_runs relationship added
- [ ] Models can be instantiated without errors
- [ ] Database tables can be created (run alembic or direct create_all)
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewer Checklist**:
- [ ] All column types match data-model.md exactly
- [ ] All CheckConstraints present and correctly named
- [ ] All indexes present and correctly named
- [ ] Foreign key ondelete behavior correct (RESTRICT for references, CASCADE for children)
- [ ] Relationships have correct back_populates configuration
- [ ] No circular import issues

## Activity Log

- 2025-12-09T17:30:00Z - system - lane=planned - Prompt created.
