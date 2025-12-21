# Cursor Code Review Prompt - Feature 025: Production Loss Tracking

## Role

You are a senior software engineer performing an independent code review of Feature 025 (production-loss-tracking). This feature enables tracking of production losses when actual yield is less than expected yield, including categorization, notes, cost calculations, and historical reporting.

## Feature Summary

**Core Changes:**
1. New `ProductionLoss` model with FK relationships to ProductionRun and FinishedUnit
2. New enums: `ProductionStatus` (COMPLETE, PARTIAL_LOSS, TOTAL_LOSS) and `LossCategory` (BURNT, BROKEN, etc.)
3. Updated `ProductionRun` model with `production_status` and `loss_quantity` fields
4. Updated `record_batch_production()` with loss recording logic
5. Yield validation: actual_yield cannot exceed expected_yield
6. Updated `get_production_history()` to include loss data
7. Updated export/import to v1.1 schema with loss tracking fields
8. UI: Expandable loss details section in Record Production dialog
9. UI: Loss and Status columns in production history table
10. Migration script and documentation for v1.0 to v1.1 data transform

**Scope:**
- Models: `production_loss.py`, `production_run.py`, `enums.py`, `__init__.py`
- Services: `batch_production_service.py` (loss recording, history, export/import)
- UI: `record_production_dialog.py`, `production_history_table.py`
- Tests: `test_batch_production_service.py`
- Migration: `scripts/migrate_v1_0_to_v1_1.py`
- Documentation: `docs/migrations/v0.6_to_v0.7_production_loss.md`

## Files to Review

### Models Layer (WP01)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/src/models/enums.py`
  - `ProductionStatus` enum with COMPLETE, PARTIAL_LOSS, TOTAL_LOSS values
  - `LossCategory` enum with BURNT, BROKEN, CONTAMINATED, DROPPED, WRONG_INGREDIENTS, OTHER values

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/src/models/production_loss.py`
  - `ProductionLoss` model inherits from BaseModel
  - FK to `production_runs` with `ondelete="SET NULL"` (preserves audit trail)
  - FK to `finished_units` with `ondelete="RESTRICT"` (prevents orphaned losses)
  - Columns: loss_category, loss_quantity, per_unit_cost, total_loss_cost, notes

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/src/models/production_run.py`
  - New column: `production_status = Column(String(20), nullable=False, default="complete")`
  - New column: `loss_quantity = Column(Integer, nullable=False, default=0)`
  - New relationship: `losses = relationship("ProductionLoss", ...)`
  - Index on production_status for efficient queries
  - Check constraint: `loss_quantity >= 0`

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/src/models/__init__.py`
  - Exports for ProductionLoss, ProductionStatus, LossCategory

### Service Layer - Loss Recording (WP02)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/src/services/batch_production_service.py`
  - `ActualYieldExceedsExpectedError` exception class (~line 94-106)
  - `record_batch_production()` updated with:
    - `loss_category` and `loss_notes` parameters
    - Yield validation: raises `ActualYieldExceedsExpectedError` if actual > expected (~line 294-296)
    - Loss quantity calculation: `expected_yield - actual_yield` (~line 299)
    - Production status determination (~line 301-306)
    - `ProductionLoss` record creation when `loss_quantity > 0` (~line 379-395)
    - Return dict includes: production_status, loss_quantity, loss_record_id, total_loss_cost
  - `get_production_history()` updated with `include_losses` parameter (~line 455-456)
  - `_production_run_to_dict()` includes production_status and loss_quantity fields (~line 570-571)

### Service Layer - Export/Import (WP05)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/src/services/batch_production_service.py`
  - `export_production_history()` updated to v1.1:
    - Version bumped to "1.1" (~line 702)
    - Calls `get_production_history()` with `include_losses=True` (~line 656)
    - Exports production_status, loss_quantity fields (~line 673-675)
    - Exports losses array (~line 686-698)
  - `import_production_history()` updated:
    - Version detection at start (~line 735)
    - v1.0 transform adds defaults (~line 736-741)
    - Creates ProductionLoss records from losses array (~line 808-820)
    - Sets production_status and loss_quantity on ProductionRun (~line 789-791)

### UI Layer - Record Production Dialog (WP03)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/src/ui/forms/record_production_dialog.py`
  - Import: `LossCategory` from src.models
  - Loss tracking state variables
  - `_create_loss_details_frame()` with category dropdown and notes textbox
  - `_toggle_loss_details(show: bool)` for auto-expand/collapse
  - `_calculate_loss_quantity()` returns `max(0, expected - actual)`
  - `_update_loss_quantity_display()` updates label and triggers auto-expand
  - Yield validation in `_validate()`: actual_yield <= expected_yield
  - `_on_confirm()` includes loss info in confirmation and service call

### UI Layer - Production History Table (WP04)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/src/ui/widgets/production_history_table.py`
  - `STATUS_DISPLAY` mapping with accessibility prefixes (!, !!)
  - `STATUS_COLORS` for visual indicators (green, amber, red)
  - `COLUMNS` updated to include Loss (width 60) and Status (width 110)
  - `_format_loss()` returns quantity or "-" for no loss
  - `_format_status()` returns human-readable status with prefix
  - `_get_status_color()` returns hex color for status
  - `_create_row()` override applies color styling to Status column

### Unit Tests (WP06)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/src/tests/test_batch_production_service.py`
  - Imports: `ProductionLoss`, `LossCategory`, `ActualYieldExceedsExpectedError`
  - `TestProductionLossTracking` class with tests for:
    - Complete production (no loss)
    - Partial loss recording
    - Total loss recording
    - Yield validation (rejects actual > expected)
    - All loss categories (parametrized)
    - Loss notes
    - Cost calculations
    - ProductionLoss model and relationships
  - `TestExportImportV11` class with tests for:
    - Export includes loss fields
    - Import v1.0 data adds defaults
    - Import v1.1 data creates ProductionLoss records
    - Roundtrip preserves loss data

### Migration Script (WP07)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/scripts/migrate_v1_0_to_v1_1.py`
  - `transform_v1_0_to_v1_1()` function
  - Idempotent: detects v1.1 data and skips transform
  - Adds defaults: production_status="complete", loss_quantity=0, losses=[]
  - `validate_input()` function for input validation
  - CLI interface with usage documentation

### Migration Documentation (WP07)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/docs/migrations/v0.6_to_v0.7_production_loss.md`
  - Step-by-step migration instructions
  - Rollback procedure documented
  - Verification checklist

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/kitty-specs/025-production-loss-tracking/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/kitty-specs/025-production-loss-tracking/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking/kitty-specs/025-production-loss-tracking/data-model.md`

## Review Checklist

### 1. Models Layer (WP01)

- [ ] `ProductionStatus` enum has COMPLETE, PARTIAL_LOSS, TOTAL_LOSS values
- [ ] `LossCategory` enum has all 6 category values
- [ ] Both enums inherit from `(str, Enum)` for JSON serialization
- [ ] `ProductionLoss` model inherits from BaseModel (gets id, uuid, timestamps)
- [ ] `ProductionLoss.production_run_id` FK uses `ondelete="SET NULL"`
- [ ] `ProductionLoss.finished_unit_id` FK uses `ondelete="RESTRICT"`
- [ ] `ProductionRun.production_status` is String(20), default="complete"
- [ ] `ProductionRun.loss_quantity` is Integer, default=0
- [ ] `ProductionRun.losses` relationship has cascade="all, delete-orphan"
- [ ] Check constraint on loss_quantity >= 0
- [ ] Index on production_status column
- [ ] `__init__.py` exports ProductionLoss, ProductionStatus, LossCategory

### 2. Service Layer - Loss Recording (WP02)

- [ ] `ActualYieldExceedsExpectedError` has actual_yield and expected_yield attributes
- [ ] `record_batch_production()` accepts `loss_category` and `loss_notes` parameters
- [ ] Yield validation occurs BEFORE FIFO consumption (fail-fast)
- [ ] Loss quantity = expected_yield - actual_yield
- [ ] Status logic: 0 loss = COMPLETE, 0 actual = TOTAL_LOSS, else PARTIAL_LOSS
- [ ] ProductionLoss created only when loss_quantity > 0
- [ ] ProductionLoss.per_unit_cost matches ProductionRun.per_unit_cost
- [ ] ProductionLoss.total_loss_cost = loss_quantity * per_unit_cost
- [ ] Default category is OTHER when not specified but loss exists
- [ ] Return dict includes production_status, loss_quantity, loss_record_id, total_loss_cost
- [ ] `get_production_history()` has `include_losses=False` parameter
- [ ] Eager loading for losses when include_losses=True
- [ ] `_production_run_to_dict()` includes loss fields

### 3. Service Layer - Export/Import (WP05)

- [ ] Export version is "1.1"
- [ ] Export calls get_production_history with include_losses=True
- [ ] Exported run includes production_status, loss_quantity, losses array
- [ ] Losses array includes: uuid, loss_category, loss_quantity, per_unit_cost, total_loss_cost, notes
- [ ] Import detects version at start
- [ ] v1.0 data gets defaults added: production_status="complete", loss_quantity=0, losses=[]
- [ ] Import creates ProductionRun with production_status and loss_quantity
- [ ] Import creates ProductionLoss records from losses array
- [ ] ProductionLoss.finished_unit_id set correctly during import

### 4. UI Layer - Record Production Dialog (WP03)

- [ ] LossCategory imported from src.models
- [ ] Loss details frame created with grid layout
- [ ] Category dropdown has all LossCategory values (human-readable labels)
- [ ] Notes textbox for optional loss notes
- [ ] Cost breakdown displays good units, lost units, total with $ amounts
- [ ] `_toggle_loss_details()` uses grid/grid_remove for show/hide
- [ ] Auto-expand when loss_quantity > 0
- [ ] Auto-collapse when loss_quantity == 0
- [ ] Yield validation: actual_yield <= expected_yield
- [ ] Error shown if actual > expected
- [ ] Confirmation dialog includes loss info when loss exists
- [ ] Service called with loss_category and loss_notes when loss exists
- [ ] Service called without loss params when no loss

### 5. UI Layer - Production History Table (WP04)

- [ ] Loss column width is 60, center-aligned
- [ ] Status column width is 110, center-aligned
- [ ] Loss shows quantity if > 0, "-" otherwise
- [ ] Status shows human-readable label with accessibility prefix
- [ ] Status uses color coding: green (complete), amber (partial), red (total)
- [ ] Text prefixes for accessibility: !, !!
- [ ] `_create_row()` overrides base to apply color styling

### 6. Unit Tests (WP06)

- [ ] Test for complete production (no loss, loss_record_id is None)
- [ ] Test for partial loss (status=partial_loss, loss_record created)
- [ ] Test for total loss (actual_yield=0, status=total_loss)
- [ ] Test for yield validation (ActualYieldExceedsExpectedError raised)
- [ ] Parametrized test covers all LossCategory values
- [ ] Test for default category (OTHER when not specified)
- [ ] Test for loss notes storage
- [ ] Test for cost calculation (total_loss_cost = qty * per_unit_cost)
- [ ] Test for ProductionLoss model creation and relationships
- [ ] Test for export includes loss fields
- [ ] Test for import v1.0 adds defaults
- [ ] Test for import v1.1 creates ProductionLoss records
- [ ] Test for roundtrip preserves loss data

### 7. Migration (WP07)

- [ ] Script is executable (chmod +x)
- [ ] Script has docstring with usage
- [ ] `transform_v1_0_to_v1_1()` is idempotent (skips v1.1 data)
- [ ] Transform adds production_status, loss_quantity, losses defaults
- [ ] Input validation checks for required keys
- [ ] Error handling for invalid JSON, missing files
- [ ] Documentation has step-by-step instructions
- [ ] Documentation has rollback procedure
- [ ] Documentation has verification checklist

### 8. Architecture Compliance

- [ ] No business logic in UI layer (calculations in service)
- [ ] No UI imports in service layer
- [ ] No service imports in model layer
- [ ] Layered architecture preserved (UI -> Services -> Models)
- [ ] Session management follows established patterns
- [ ] No new nested session_scope() issues

### 9. Session Management

- [ ] `record_batch_production()` uses single session for atomic transaction
- [ ] ProductionLoss created within same session as ProductionRun
- [ ] session.flush() called after ProductionRun to get ID before creating ProductionLoss
- [ ] No detached object issues in loss creation

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/025-production-loss-tracking

# Verify modules import correctly
python3 -c "
from src.models import ProductionLoss, ProductionStatus, LossCategory
from src.services.batch_production_service import ActualYieldExceedsExpectedError
print('ProductionStatus values:', [s.value for s in ProductionStatus])
print('LossCategory values:', [c.value for c in LossCategory])
print('All modules import successfully')
"

# Verify ProductionLoss model structure
python3 -c "
from src.models.production_loss import ProductionLoss
from sqlalchemy import inspect
mapper = inspect(ProductionLoss)
print('ProductionLoss columns:', [c.name for c in mapper.columns])
print('ProductionLoss relationships:', list(mapper.relationships.keys()))
"

# Verify ProductionRun has loss fields
python3 -c "
from src.models.production_run import ProductionRun
from sqlalchemy import inspect
mapper = inspect(ProductionRun)
cols = [c.name for c in mapper.columns]
assert 'production_status' in cols, 'Missing production_status'
assert 'loss_quantity' in cols, 'Missing loss_quantity'
print('ProductionRun has loss fields:', 'production_status', 'loss_quantity')
print('ProductionRun relationships:', list(mapper.relationships.keys()))
"

# Verify service function signatures
python3 -c "
import inspect
from src.services.batch_production_service import record_batch_production, get_production_history
sig = inspect.signature(record_batch_production)
params = list(sig.parameters.keys())
assert 'loss_category' in params, 'Missing loss_category parameter'
assert 'loss_notes' in params, 'Missing loss_notes parameter'
print('record_batch_production params:', params)

sig2 = inspect.signature(get_production_history)
params2 = list(sig2.parameters.keys())
assert 'include_losses' in params2, 'Missing include_losses parameter'
print('get_production_history params:', params2)
"

# Verify export version
python3 -c "
from src.services.batch_production_service import export_production_history
result = export_production_history()
assert result['version'] == '1.1', f'Expected v1.1, got {result[\"version\"]}'
print('Export version:', result['version'])
"

# Verify migration script
python scripts/migrate_v1_0_to_v1_1.py 2>&1 | head -5

# Test migration script with sample data
cat > /tmp/test_v10.json << 'EOF'
{"version":"1.0","production_runs":[{"uuid":"test","recipe_name":"Test","finished_unit_slug":"test","num_batches":1,"expected_yield":10,"actual_yield":10,"produced_at":"2024-01-01T00:00:00","notes":null,"total_ingredient_cost":"1.00","per_unit_cost":"0.10","consumptions":[]}]}
EOF
python scripts/migrate_v1_0_to_v1_1.py /tmp/test_v10.json /tmp/test_v11.json
python3 -c "
import json
with open('/tmp/test_v11.json') as f:
    data = json.load(f)
run = data['production_runs'][0]
assert data['version'] == '1.1', 'Version not updated'
assert run['production_status'] == 'complete', 'Status not set'
assert run['loss_quantity'] == 0, 'Loss quantity not set'
assert run['losses'] == [], 'Losses not set'
print('Migration transform: PASS')
"

# Run all tests
python3 -m pytest src/tests/test_batch_production_service.py -v

# Run Feature 025 specific tests
python3 -m pytest src/tests/test_batch_production_service.py -v -k "TestProductionLossTracking or TestExportImportV11"

# Check test count
python3 -m pytest src/tests/test_batch_production_service.py --collect-only -q | tail -5
```

## Key Implementation Patterns

### Enum Pattern (str, Enum for JSON serialization)
```python
class ProductionStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL_LOSS = "partial_loss"
    TOTAL_LOSS = "total_loss"
```

### Fail-Fast Yield Validation Pattern
```python
# Validate BEFORE consuming inventory
if actual_yield > expected_yield:
    raise ActualYieldExceedsExpectedError(actual_yield, expected_yield)

# Only then proceed with FIFO consumption
```

### Production Status Determination Pattern
```python
loss_quantity = expected_yield - actual_yield

if loss_quantity == 0:
    production_status = ProductionStatus.COMPLETE
elif actual_yield == 0:
    production_status = ProductionStatus.TOTAL_LOSS
else:
    production_status = ProductionStatus.PARTIAL_LOSS
```

### ProductionLoss Creation Pattern
```python
# Only create when loss exists
if loss_quantity > 0:
    loss_record = ProductionLoss(
        production_run_id=production_run.id,
        finished_unit_id=finished_unit_id,
        loss_category=(loss_category or LossCategory.OTHER).value,
        loss_quantity=loss_quantity,
        per_unit_cost=per_unit_cost,
        total_loss_cost=loss_quantity * per_unit_cost,
        notes=loss_notes,
    )
    session.add(loss_record)
```

### Auto-Expand UI Pattern
```python
def _update_loss_quantity_display(self):
    loss_qty = self._calculate_loss_quantity()
    self.loss_quantity_label.configure(text=str(loss_qty))
    # Auto-expand when loss detected, collapse when no loss
    self._toggle_loss_details(loss_qty > 0)
```

### Import Version Transform Pattern
```python
version = data.get("version", "1.0")
if version == "1.0":
    for run_data in data.get("production_runs", []):
        run_data.setdefault("production_status", "complete")
        run_data.setdefault("loss_quantity", 0)
        run_data.setdefault("losses", [])
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F025-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 025 - Production Loss Tracking

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 025-production-loss-tracking
**Branch:** 025-production-loss-tracking

## Summary

[Brief overview of findings]

## Verification Results

### Module Import Validation
- ProductionLoss model: [PASS/FAIL]
- ProductionStatus enum: [PASS/FAIL]
- LossCategory enum: [PASS/FAIL]
- ActualYieldExceedsExpectedError: [PASS/FAIL]

### Test Results
- pytest result: [PASS/FAIL - X passed, Y skipped, Z failed]
- Feature 025 tests: [X tests passed]

### Code Pattern Validation
- Fail-fast yield validation: [present/missing]
- Production status logic: [correct/incorrect]
- ProductionLoss creation: [correct/incorrect]
- Auto-expand UI: [present/missing]
- Import version transform: [correct/incorrect]

## Findings

### Critical Issues
[Any blocking issues that must be fixed]

### Warnings
[Non-blocking concerns]

### Observations
[General observations about code quality]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/models/enums.py | [status] | [notes] |
| src/models/production_loss.py | [status] | [notes] |
| src/models/production_run.py | [status] | [notes] |
| src/models/__init__.py | [status] | [notes] |
| src/services/batch_production_service.py | [status] | [notes] |
| src/ui/forms/record_production_dialog.py | [status] | [notes] |
| src/ui/widgets/production_history_table.py | [status] | [notes] |
| src/tests/test_batch_production_service.py | [status] | [notes] |
| scripts/migrate_v1_0_to_v1_1.py | [status] | [notes] |
| docs/migrations/v0.6_to_v0.7_production_loss.md | [status] | [notes] |

## Architecture Assessment

### Layered Architecture
[Assessment of UI -> Services -> Models dependency flow]

### Session Management
[Assessment of session handling in record_batch_production - must be atomic]

### FK Cascade Behavior
[Assessment of ondelete="SET NULL" for production_run_id and ondelete="RESTRICT" for finished_unit_id]

### Error Handling
[Assessment of fail-fast validation and exception handling]

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: Loss quantity auto-calculated | [PASS/FAIL] | [evidence] |
| FR-002: actual_yield <= expected_yield enforced | [PASS/FAIL] | [evidence] |
| FR-003: Fail-fast validation before FIFO | [PASS/FAIL] | [evidence] |
| FR-004: Production status derived correctly | [PASS/FAIL] | [evidence] |
| FR-005: ProductionLoss created on loss | [PASS/FAIL] | [evidence] |
| FR-006: No ProductionLoss when no loss | [PASS/FAIL] | [evidence] |
| FR-007: Loss category dropdown in UI | [PASS/FAIL] | [evidence] |
| FR-008: Loss notes optional | [PASS/FAIL] | [evidence] |
| FR-009: Default category is OTHER | [PASS/FAIL] | [evidence] |
| FR-010: Per-unit cost snapshot on loss | [PASS/FAIL] | [evidence] |
| FR-011: Total loss cost calculated | [PASS/FAIL] | [evidence] |
| FR-012: Cost breakdown in UI | [PASS/FAIL] | [evidence] |
| FR-013: History shows Loss and Status columns | [PASS/FAIL] | [evidence] |
| FR-014: Visual indicators for status | [PASS/FAIL] | [evidence] |
| FR-015: Export includes loss data | [PASS/FAIL] | [evidence] |
| FR-016: Import handles v1.0 and v1.1 | [PASS/FAIL] | [evidence] |

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| SC-001: Loss recording adds <30s to workflow | [PASS/FAIL] | [evidence] |
| SC-002: All LossCategory values available | [PASS/FAIL] | [evidence] |
| SC-003: Historical runs show COMPLETE status | [PASS/FAIL] | [evidence] |
| SC-004: Loss details auto-expand on detection | [PASS/FAIL] | [evidence] |
| SC-005: Confirmation shows loss info | [PASS/FAIL] | [evidence] |
| SC-006: Export v1.1 with loss fields | [PASS/FAIL] | [evidence] |
| SC-007: Import v1.0 backward compatible | [PASS/FAIL] | [evidence] |
| SC-008: Migration script idempotent | [PASS/FAIL] | [evidence] |
| SC-009: 22+ unit tests pass | [PASS/FAIL] | [evidence] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing
- The worktree is isolated from main branch at `.worktrees/025-production-loss-tracking`
- Layered architecture: UI -> Services -> Models -> Database
- Per Constitution Principle VI, uses export/reset/import cycle (no Alembic)
- Session management is critical - nested session_scope() can cause detached object issues
- FK cascade behavior is intentional: SET NULL for production_run (audit trail) and RESTRICT for finished_unit (data integrity)
- The `(str, Enum)` pattern is required for JSON serialization in export/import
- Fail-fast validation ensures FIFO consumption only happens for valid inputs
- The UI auto-expand pattern keeps default view clean while guiding users to loss details
