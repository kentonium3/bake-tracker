---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
title: "Models & Enums"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "73162"
history:
  - timestamp: "2025-12-21T16:55:08Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Models & Enums

## Objectives & Success Criteria

- Create `ProductionStatus` enum with COMPLETE, PARTIAL_LOSS, TOTAL_LOSS values
- Create `LossCategory` enum with BURNT, BROKEN, CONTAMINATED, DROPPED, WRONG_INGREDIENTS, OTHER values
- Add `production_status` and `loss_quantity` columns to ProductionRun model
- Create new `ProductionLoss` model with all fields per data-model.md
- Establish bidirectional relationship between ProductionRun and ProductionLoss
- All new models importable from `src/models/__init__.py`
- Database creates new tables/columns without errors

## Context & Constraints

- **Spec**: `kitty-specs/025-production-loss-tracking/spec.md`
- **Plan**: `kitty-specs/025-production-loss-tracking/plan.md`
- **Data Model**: `kitty-specs/025-production-loss-tracking/data-model.md`
- **Constitution**: `.kittify/memory/constitution.md`

**Key Constraints**:
- Follow existing model patterns (BaseModel inheritance, UUID support)
- Use String columns for enum storage (not SQLAlchemy Enum type) per research decision
- Add defaults for backward compatibility: production_status="complete", loss_quantity=0
- FK to ProductionRun uses `ondelete="SET NULL"` to preserve audit trail
- Follow session management patterns per CLAUDE.md

## Subtasks & Detailed Guidance

### Subtask T001 - Create ProductionStatus enum
- **Purpose**: Classify production run outcomes for filtering and display
- **File**: `src/models/enums.py` (create if not exists)
- **Steps**:
  1. Create or open `src/models/enums.py`
  2. Add `ProductionStatus(str, Enum)` class with values:
     - `COMPLETE = "complete"`
     - `PARTIAL_LOSS = "partial_loss"`
     - `TOTAL_LOSS = "total_loss"`
  3. Include docstring explaining each value
- **Parallel?**: Yes, with T002
- **Notes**: Inherit from both `str` and `Enum` for JSON serialization

### Subtask T002 - Create LossCategory enum
- **Purpose**: Classify loss reasons for categorization and reporting
- **File**: `src/models/enums.py`
- **Steps**:
  1. Add `LossCategory(str, Enum)` class with values:
     - `BURNT = "burnt"`
     - `BROKEN = "broken"`
     - `CONTAMINATED = "contaminated"`
     - `DROPPED = "dropped"`
     - `WRONG_INGREDIENTS = "wrong_ingredients"`
     - `OTHER = "other"`
  2. Include docstring with descriptions for each category
- **Parallel?**: Yes, with T001
- **Notes**: OTHER is the fallback; notes field captures specifics

### Subtask T003 - Add production_status column to ProductionRun
- **Purpose**: Quick access to production outcome without querying losses
- **File**: `src/models/production_run.py`
- **Steps**:
  1. Import String from sqlalchemy if not present
  2. Add column: `production_status = Column(String(20), nullable=False, default="complete")`
  3. Place after existing notes column
- **Parallel?**: No, T003-T005 are sequential edits to same file
- **Notes**: Default ensures existing records have valid value

### Subtask T004 - Add loss_quantity column to ProductionRun
- **Purpose**: Store calculated loss count for quick queries
- **File**: `src/models/production_run.py`
- **Steps**:
  1. Add column: `loss_quantity = Column(Integer, nullable=False, default=0)`
  2. Place after production_status column
- **Parallel?**: No
- **Notes**: Always equals expected_yield - actual_yield

### Subtask T005 - Add constraints and index for loss tracking
- **Purpose**: Data integrity and query performance
- **File**: `src/models/production_run.py`
- **Steps**:
  1. Add to `__table_args__`:
     - `CheckConstraint("loss_quantity >= 0", name="ck_production_run_loss_non_negative")`
  2. Add index:
     - `Index("idx_production_run_status", "production_status")`
  3. Update `to_dict()` method to include new fields
- **Parallel?**: No
- **Notes**: Index supports filtering by status

### Subtask T006 - Create ProductionLoss model
- **Purpose**: Detailed loss records with category, cost snapshot, and notes
- **File**: `src/models/production_loss.py` (new file)
- **Steps**:
  1. Create new file with imports matching existing model patterns
  2. Define `ProductionLoss(BaseModel)` class with columns:
     - `production_run_id` (FK to production_runs, ondelete="SET NULL", nullable=True)
     - `finished_unit_id` (FK to finished_units, ondelete="RESTRICT", nullable=False)
     - `loss_category` (String(20), default="other")
     - `loss_quantity` (Integer, nullable=False)
     - `per_unit_cost` (Numeric(10,4), nullable=False)
     - `total_loss_cost` (Numeric(10,4), nullable=False)
     - `notes` (Text, nullable=True)
  3. Add constraints:
     - `loss_quantity > 0`
     - `per_unit_cost >= 0`
     - `total_loss_cost >= 0`
  4. Add indexes per data-model.md
  5. Add `__repr__` and `to_dict` methods
- **Parallel?**: No
- **Notes**: Use SET NULL for production_run_id to preserve audit trail if run deleted

### Subtask T007 - Add losses relationship to ProductionRun
- **Purpose**: Enable navigation from ProductionRun to its loss records
- **File**: `src/models/production_run.py`
- **Steps**:
  1. Add relationship: `losses = relationship("ProductionLoss", back_populates="production_run", cascade="all, delete-orphan")`
  2. In ProductionLoss, add: `production_run = relationship("ProductionRun", back_populates="losses")`
  3. Add FinishedUnit relationship to ProductionLoss: `finished_unit = relationship("FinishedUnit")`
- **Parallel?**: No
- **Notes**: Consider cascade behavior - losses orphaned if run deleted (SET NULL FK handles this)

### Subtask T008 - Update models/__init__.py exports
- **Purpose**: Make new models and enums importable from src.models
- **File**: `src/models/__init__.py`
- **Steps**:
  1. Add import: `from .enums import ProductionStatus, LossCategory`
  2. Add import: `from .production_loss import ProductionLoss`
  3. Add to `__all__` list if present
- **Parallel?**: No
- **Notes**: Verify no circular import issues

## Test Strategy

After completing all subtasks:
1. Run `python -c "from src.models import ProductionStatus, LossCategory, ProductionLoss; print('Imports OK')"` to verify imports
2. Run existing tests to ensure no regressions: `pytest src/tests -v --tb=short`
3. Verify database can be created with new schema (existing app startup should work)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular import between models | Use TYPE_CHECKING block for forward references |
| Session detachment | Not applicable for model-only changes |
| Migration complexity | No migration needed - export/reset/import handles schema change |

## Definition of Done Checklist

- [ ] ProductionStatus enum created with 3 values
- [ ] LossCategory enum created with 6 values
- [ ] ProductionRun has production_status column with default
- [ ] ProductionRun has loss_quantity column with default
- [ ] ProductionRun has constraints and index for loss fields
- [ ] ProductionLoss model created with all fields per data-model.md
- [ ] Bidirectional relationship between ProductionRun and ProductionLoss
- [ ] All new symbols exported from src/models/__init__.py
- [ ] Existing tests pass (no regressions)
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify enum values match spec exactly (lowercase with underscores)
- Verify ProductionLoss FK uses SET NULL for audit trail preservation
- Verify constraints match data-model.md
- Check that to_dict() methods include new fields
- Confirm no circular import issues

## Activity Log

- 2025-12-21T16:55:08Z - system - lane=planned - Prompt created.
- 2025-12-21T17:38:20Z – claude – shell_pid=62187 – lane=doing – Started implementation
- 2025-12-21T17:59:29Z – claude – shell_pid=64381 – lane=for_review – T001-T008 complete. All tests pass (excluding pre-existing failures). Ready for review.
- 2025-12-21T19:04:19Z – claude-reviewer – shell_pid=73162 – lane=done – Code review APPROVED: All Definition of Done items verified. Enums, models, relationships, constraints, and exports correct.
