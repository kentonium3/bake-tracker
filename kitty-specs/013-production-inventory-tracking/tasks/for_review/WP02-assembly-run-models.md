---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
title: "Assembly Run Models"
phase: "Phase 1 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "15592"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T17:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Assembly Run Models

## Objectives & Success Criteria

Create the SQLAlchemy models for assembly tracking:
- **AssemblyRun**: Records assembly events where FinishedUnits become FinishedGoods
- **AssemblyFinishedUnitConsumption**: Tracks FinishedUnits consumed during assembly
- **AssemblyPackagingConsumption**: Tracks packaging materials consumed during assembly

**Success Criteria**:
- [ ] All three models inherit from BaseModel correctly
- [ ] All columns, constraints, and indexes match data-model.md exactly
- [ ] Foreign key relationships properly configured with correct targets
- [ ] Models can be imported from `src/models/__init__.py`

## Context & Constraints

**Reference Documents**:
- `kitty-specs/013-production-inventory-tracking/data-model.md` - Entity definitions
- `kitty-specs/013-production-inventory-tracking/plan.md` - Technical context
- `src/models/base.py` - BaseModel pattern
- `src/models/finished_good.py` - FinishedGood model (FK target)
- `src/models/finished_unit.py` - FinishedUnit model (FK target)
- `src/models/product.py` - Product model (FK target for packaging)

**Constraints**:
- Two separate consumption tables (not polymorphic) per design decision
- AssemblyFinishedUnitConsumption.quantity_consumed is Integer (whole units)
- AssemblyPackagingConsumption.quantity_consumed is Numeric(10,3) (can be fractional)

## Subtasks & Detailed Guidance

### Subtask T005 - Create AssemblyRun model
- **Purpose**: Record assembly events linking component consumption to FinishedGood creation
- **File**: `src/models/assembly_run.py`
- **Parallel?**: Yes (can develop alongside T006, T007)

**Steps**:
1. Create new file with module docstring
2. Import required SQLAlchemy components and BaseModel
3. Define AssemblyRun class with columns:
   - `finished_good_id` (Integer FK to finished_goods.id, ondelete="RESTRICT", nullable=False)
   - `quantity_assembled` (Integer, nullable=False)
   - `assembled_at` (DateTime, nullable=False, default=datetime.utcnow)
   - `notes` (Text, nullable=True)
   - `total_component_cost` (Numeric(10,4), nullable=False, default=Decimal("0.0000"))
   - `per_unit_cost` (Numeric(10,4), nullable=False, default=Decimal("0.0000"))
4. Add relationships:
   - `finished_good` -> FinishedGood
   - `finished_unit_consumptions` -> AssemblyFinishedUnitConsumption (back_populates="assembly_run", cascade="all, delete-orphan")
   - `packaging_consumptions` -> AssemblyPackagingConsumption (back_populates="assembly_run", cascade="all, delete-orphan")
5. Add __table_args__ with:
   - Indexes: idx_assembly_run_finished_good, idx_assembly_run_assembled_at
   - CheckConstraints: quantity_assembled > 0, costs >= 0

### Subtask T006 - Create AssemblyFinishedUnitConsumption model
- **Purpose**: Track which FinishedUnits were consumed during an assembly
- **File**: `src/models/assembly_finished_unit_consumption.py`
- **Parallel?**: Yes (can develop alongside T005, T007)

**Steps**:
1. Create new file with module docstring
2. Define AssemblyFinishedUnitConsumption class with columns:
   - `assembly_run_id` (Integer FK to assembly_runs.id, ondelete="CASCADE", nullable=False)
   - `finished_unit_id` (Integer FK to finished_units.id, ondelete="RESTRICT", nullable=False)
   - `quantity_consumed` (Integer, nullable=False) - Note: INTEGER not Numeric
   - `unit_cost_at_consumption` (Numeric(10,4), nullable=False)
   - `total_cost` (Numeric(10,4), nullable=False)
3. Add relationships:
   - `assembly_run` -> AssemblyRun (back_populates="finished_unit_consumptions")
   - `finished_unit` -> FinishedUnit
4. Add __table_args__ with:
   - Indexes: idx_asm_fu_consumption_run, idx_asm_fu_consumption_unit
   - CheckConstraints: quantity_consumed > 0, costs >= 0

### Subtask T007 - Create AssemblyPackagingConsumption model
- **Purpose**: Track packaging materials consumed from inventory during assembly
- **File**: `src/models/assembly_packaging_consumption.py`
- **Parallel?**: Yes (can develop alongside T005, T006)

**Steps**:
1. Create new file with module docstring
2. Define AssemblyPackagingConsumption class with columns:
   - `assembly_run_id` (Integer FK to assembly_runs.id, ondelete="CASCADE", nullable=False)
   - `product_id` (Integer FK to products.id, ondelete="RESTRICT", nullable=False)
   - `quantity_consumed` (Numeric(10,3), nullable=False) - Note: Numeric for fractional packaging
   - `unit` (String(50), nullable=False)
   - `total_cost` (Numeric(10,4), nullable=False)
3. Add relationships:
   - `assembly_run` -> AssemblyRun (back_populates="packaging_consumptions")
   - `product` -> Product
4. Add __table_args__ with:
   - Indexes: idx_asm_pkg_consumption_run, idx_asm_pkg_consumption_product
   - CheckConstraints: quantity_consumed > 0, total_cost >= 0

### Subtask T008 - Update models __init__.py
- **Purpose**: Export new assembly models
- **File**: `src/models/__init__.py`
- **Parallel?**: No (depends on T005, T006, T007)

**Steps**:
1. Add imports for all three assembly models
2. Add to __all__ list if one exists
3. Verify imports work correctly

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Confusion between Integer vs Numeric for quantity | T006 uses Integer (whole units), T007 uses Numeric (fractional packaging) |
| Wrong FK target for packaging | Must reference products.id, not ingredients.id |
| Circular import issues | Use string references for relationship targets |

## Definition of Done Checklist

- [ ] T005: AssemblyRun model created with all columns, constraints, indexes
- [ ] T006: AssemblyFinishedUnitConsumption model created
- [ ] T007: AssemblyPackagingConsumption model created
- [ ] T008: All three models exported from src/models/__init__.py
- [ ] Models can be instantiated without errors
- [ ] Database tables can be created
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewer Checklist**:
- [ ] AssemblyFinishedUnitConsumption.quantity_consumed is Integer
- [ ] AssemblyPackagingConsumption.quantity_consumed is Numeric(10,3)
- [ ] All FK targets are correct (finished_goods, finished_units, products)
- [ ] Cascade delete on assembly_run_id FKs
- [ ] All relationships have correct back_populates

## Activity Log

- 2025-12-09T17:30:00Z - system - lane=planned - Prompt created.
- 2025-12-10T03:47:51Z – claude – shell_pid=15592 – lane=doing – Implementation complete - Assembly models created
- 2025-12-10T03:47:52Z – claude – shell_pid=15592 – lane=for_review – Ready for review - AssemblyRun, AssemblyFinishedUnitConsumption, AssemblyPackagingConsumption models
