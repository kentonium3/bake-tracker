# Cursor Code Review Prompt - Feature 026: Deferred Packaging Decisions

## Role

You are a senior software engineer performing an independent code review of Feature 026 (deferred-packaging-decisions). This feature enables bakers to plan events with generic packaging requirements (e.g., "Cellophane Bags 6x10") without committing to specific designs upfront, deferring specific material selection until assembly time.

## Feature Summary

**Core Changes:**
1. New `is_generic` boolean column on `compositions` table
2. New `composition_assignments` junction table linking compositions to inventory items
3. New `packaging_service.py` with functions for generic packaging management
4. Updated `event_service.py` for generic packaging in shopping lists
5. Updated `assembly_service.py` to support `packaging_bypassed` flag
6. UI updates for planning, assignment, dashboard indicators, and bypass dialogs
7. Import/export support for `is_generic` and assignments

**Scope:**
- Model layer: `composition.py`, `composition_assignment.py`, `assembly_run.py`
- Service layer: `packaging_service.py`, `composition_service.py`, `event_service.py`, `assembly_service.py`, `import_export_service.py`
- UI layer: `event_detail_window.py`, `record_assembly_dialog.py`, `event_card.py`
- Tests: `test_packaging_service.py`, `test_deferred_packaging.py`, `test_packaging_flow.py`

## Files to Review

### Model Layer (WP01)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/models/composition.py`
  - `is_generic` column (Boolean, default False)
  - `assignments` relationship to CompositionAssignment

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/models/composition_assignment.py`
  - New model with `composition_id`, `inventory_item_id`, `quantity_assigned`, `assigned_at`
  - Foreign key constraints with proper ON DELETE behavior

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/models/assembly_run.py`
  - `packaging_bypassed` column (Boolean)
  - `packaging_bypass_notes` column (String)

### Service Layer (WP02-WP03)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/services/packaging_service.py`
  - `get_generic_products()` - list distinct product_name values
  - `get_generic_inventory_summary(product_name)` - aggregate inventory by product name
  - `get_estimated_cost(product_name, quantity)` - weighted average cost calculation
  - `assign_materials(composition_id, assignments)` - create assignment records
  - `clear_assignments(composition_id)` - remove existing assignments
  - `get_assignments(composition_id)` - list current assignments
  - `is_fully_assigned(composition_id)` - check if requirements met
  - `get_pending_requirements(assembly_id)` - find unassigned generic compositions
  - `get_assignment_summary(composition_id)` - aggregated status
  - `get_actual_cost(composition_id)` - calculate cost from assignments
  - `get_available_inventory_items(product_name)` - list matching inventory

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/services/composition_service.py`
  - `add_packaging_to_assembly()` - updated to accept `is_generic` parameter
  - `add_packaging_to_package()` - updated to accept `is_generic` parameter

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/services/event_service.py`
  - `get_event_packaging_needs()` - updated to aggregate generic packaging
  - `PackagingNeed` dataclass - added `is_generic`, `generic_product_name`, `estimated_cost` fields

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/services/assembly_service.py`
  - `record_assembly()` - accepts `packaging_bypassed` and `packaging_bypass_notes`
  - Skip packaging consumption when `packaging_bypassed=True` (~line 376-378)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/services/import_export_service.py`
  - `export_compositions_to_json()` - exports `is_generic` and `assignments`
  - `import_compositions_from_json()` - imports `is_generic` and creates assignments

### UI Layer (WP04-WP08)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/ui/event_detail_window.py`
  - Shopping list display with generic items and estimated costs

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/ui/forms/record_assembly_dialog.py`
  - Bypass prompt for unassigned packaging
  - Options: "Quick Assign", "Assembly Details", "Record Anyway"

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/ui/widgets/event_card.py`
  - Pending packaging indicator on event cards

### Test Files
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/tests/services/test_packaging_service.py`
  - Unit tests for all packaging_service functions (88% coverage target)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/tests/integration/test_deferred_packaging.py`
  - 8 integration tests for full workflow

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/src/tests/integration/test_packaging_flow.py`
  - Updated tests for generic packaging export/import

### Specification Documents
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/kitty-specs/026-deferred-packaging-decisions/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/kitty-specs/026-deferred-packaging-decisions/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/kitty-specs/026-deferred-packaging-decisions/data-model.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions/kitty-specs/026-deferred-packaging-decisions/quickstart.md`

## Review Checklist

### 1. Model Layer - Schema Changes
- [ ] `Composition.is_generic` column exists with Boolean type, default False
- [ ] `Composition.assignments` relationship defined with proper backref
- [ ] `CompositionAssignment` model has all required columns (id, uuid, composition_id, inventory_item_id, quantity_assigned, assigned_at, created_at, updated_at)
- [ ] `CompositionAssignment.composition_id` has ON DELETE CASCADE
- [ ] `CompositionAssignment.inventory_item_id` has ON DELETE RESTRICT
- [ ] `AssemblyRun.packaging_bypassed` column exists (Boolean, nullable)
- [ ] `AssemblyRun.packaging_bypass_notes` column exists (String, nullable)

### 2. Packaging Service - Core Functions
- [ ] `get_generic_products()` returns list of product_name strings for packaging products
- [ ] `get_generic_inventory_summary()` returns dict with 'total' and 'breakdown'
- [ ] `get_estimated_cost()` calculates weighted average from inventory costs
- [ ] `assign_materials()` validates total assigned equals required quantity
- [ ] `assign_materials()` clears existing assignments before creating new ones
- [ ] `assign_materials()` raises `InvalidAssignmentError` for invalid assignments
- [ ] `clear_assignments()` removes all CompositionAssignment records for composition
- [ ] `get_assignments()` returns list of dicts with inventory_item_id, quantity_assigned
- [ ] `is_fully_assigned()` returns True only when total equals required
- [ ] `get_pending_requirements()` returns compositions where is_generic=True and not fully assigned
- [ ] `get_actual_cost()` calculates cost from actual assigned inventory items
- [ ] All functions accept optional `session=None` parameter (per CLAUDE.md)

### 3. Composition Service Updates
- [ ] `add_packaging_to_assembly()` accepts `is_generic` parameter
- [ ] `add_packaging_to_package()` accepts `is_generic` parameter
- [ ] Default value for `is_generic` is False (backward compatible)

### 4. Event Service - Shopping List
- [ ] `get_event_packaging_needs()` groups generic packaging by product_name
- [ ] Generic items use key format `generic_{product_name}`
- [ ] Specific items use key format `specific_{product_id}`
- [ ] `PackagingNeed.is_generic` field populated correctly
- [ ] `PackagingNeed.estimated_cost` calculated for generic items

### 5. Assembly Service - Bypass Support
- [ ] `record_assembly()` accepts `packaging_bypassed` parameter
- [ ] `record_assembly()` accepts `packaging_bypass_notes` parameter
- [ ] When `packaging_bypassed=True`, packaging consumption is SKIPPED (line ~376-378)
- [ ] `AssemblyRun` record stores bypass flag and notes

### 6. Import/Export - New Fields
- [ ] `export_compositions_to_json()` includes `is_generic` field
- [ ] `export_compositions_to_json()` includes `assignments` array for generic compositions
- [ ] `import_compositions_from_json()` handles `is_generic` field
- [ ] `import_compositions_from_json()` creates CompositionAssignment records from `assignments`
- [ ] Import warns but doesn't fail when inventory_item_id not found

### 7. UI - Planning & Assignment
- [ ] Event detail shows pending packaging indicators
- [ ] Shopping list shows generic items with "(any)" suffix
- [ ] Shopping list shows estimated costs for generic items
- [ ] Record assembly dialog prompts for unassigned packaging
- [ ] Bypass option records flag on AssemblyRun

### 8. Test Coverage
- [ ] Unit tests cover all packaging_service functions
- [ ] Integration tests cover full workflow (plan -> assign -> assemble)
- [ ] Edge cases tested: partial assignment, reassignment, bypass
- [ ] Import/export round-trip tested for is_generic and assignments
- [ ] All tests pass (70 packaging-related tests expected)

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/026-deferred-packaging-decisions

# Verify modules import correctly
python3 -c "
from src.models.composition import Composition
from src.models.composition_assignment import CompositionAssignment
from src.models.assembly_run import AssemblyRun
from src.services.packaging_service import (
    get_generic_products, get_generic_inventory_summary, get_estimated_cost,
    assign_materials, clear_assignments, get_assignments, is_fully_assigned,
    get_pending_requirements, get_assignment_summary, get_actual_cost,
    get_available_inventory_items, InvalidAssignmentError
)
print('All modules import successfully')
"

# Verify Composition.is_generic column
grep -n "is_generic" src/models/composition.py

# Verify CompositionAssignment model
grep -n "class CompositionAssignment" src/models/composition_assignment.py

# Verify AssemblyRun bypass columns
grep -n "packaging_bypassed\|packaging_bypass_notes" src/models/assembly_run.py

# Verify packaging service functions exist
grep -n "^def " src/services/packaging_service.py | head -20

# Verify session parameter pattern
grep -n "session=None" src/services/packaging_service.py | head -5

# Verify bypass skip logic in assembly_service
grep -A 3 "if packaging_bypassed:" src/services/assembly_service.py

# Verify is_generic in composition_service
grep -n "is_generic" src/services/composition_service.py

# Verify import/export handles is_generic
grep -n "is_generic" src/services/import_export_service.py

# Run all packaging tests
python3 -m pytest src/tests/services/test_packaging_service.py src/tests/integration/test_deferred_packaging.py src/tests/integration/test_packaging_flow.py -v

# Check test coverage for packaging_service
python3 -m pytest src/tests/services/test_packaging_service.py -v --cov=src.services.packaging_service --cov-report=term-missing
```

## Key Implementation Patterns

### Session Management Pattern (per CLAUDE.md)
```python
def some_function(..., session=None):
    """Accept optional session parameter."""
    if session is not None:
        return _impl(..., session)
    with session_scope() as session:
        return _impl(..., session)
```

### Assignment Validation Pattern
```python
if total_assigned != required:
    raise InvalidAssignmentError(
        f"Total assigned ({total_assigned}) must equal required quantity ({required})"
    )
```

### Bypass Skip Pattern
```python
elif comp.packaging_product_id:
    # Skip packaging consumption if bypass flag is set (Feature 026)
    if packaging_bypassed:
        continue
    # ... normal packaging consumption
```

### Generic Product Key Pattern
```python
key = f"generic_{product_name}"  # For generic packaging
key = f"specific_{product_id}"   # For specific packaging
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F026-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 026 - Deferred Packaging Decisions

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 026-deferred-packaging-decisions
**Branch:** 026-deferred-packaging-decisions

## Summary

[Brief overview of findings]

## Verification Results

### Module Import Validation
- composition.py: [PASS/FAIL]
- composition_assignment.py: [PASS/FAIL]
- assembly_run.py: [PASS/FAIL]
- packaging_service.py: [PASS/FAIL]
- composition_service.py: [PASS/FAIL]
- event_service.py: [PASS/FAIL]
- assembly_service.py: [PASS/FAIL]
- import_export_service.py: [PASS/FAIL]

### Test Results
- pytest result: [PASS/FAIL - X passed, Y skipped, Z failed]
- packaging_service coverage: [XX%]

### Code Pattern Validation
- Session parameter pattern: [present/missing]
- Assignment validation: [present/missing]
- Bypass skip logic: [present/missing]
- Generic product key format: [present/missing]
- Import/export is_generic: [present/missing]

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
| src/models/composition.py | [status] | [notes] |
| src/models/composition_assignment.py | [status] | [notes] |
| src/models/assembly_run.py | [status] | [notes] |
| src/services/packaging_service.py | [status] | [notes] |
| src/services/composition_service.py | [status] | [notes] |
| src/services/event_service.py | [status] | [notes] |
| src/services/assembly_service.py | [status] | [notes] |
| src/services/import_export_service.py | [status] | [notes] |
| src/ui/event_detail_window.py | [status] | [notes] |
| src/ui/forms/record_assembly_dialog.py | [status] | [notes] |
| src/ui/widgets/event_card.py | [status] | [notes] |

## Architecture Assessment

### Layered Architecture
[Assessment of UI -> Services -> Models dependency flow]

### Session Management
[Assessment of session=None parameter pattern per CLAUDE.md]

### Error Handling
[Assessment of InvalidAssignmentError and validation patterns]

### Backward Compatibility
[Assessment of default is_generic=False and existing functionality]

## User Story Verification

| User Story | Status | Evidence |
|------------|--------|----------|
| US-1: Plan with generic packaging | [PASS/FAIL] | [evidence] |
| US-2: Assign materials at assembly | [PASS/FAIL] | [evidence] |
| US-3: Dashboard indicators | [PASS/FAIL] | [evidence] |
| US-4: Shopping list with generic items | [PASS/FAIL] | [evidence] |
| US-5: Assembly bypass option | [PASS/FAIL] | [evidence] |
| US-6: Modify packaging during assembly | [PASS/FAIL] | [evidence] |

## Test Coverage Assessment

| Test File | Tests | Coverage | Notes |
|-----------|-------|----------|-------|
| test_packaging_service.py | [count] | [%] | [notes] |
| test_deferred_packaging.py | [count] | N/A | [notes] |
| test_packaging_flow.py | [count] | N/A | [notes] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing with pytest-cov for coverage
- The worktree is isolated from main branch
- Layered architecture: UI -> Services -> Models -> Database
- Session management pattern: functions accept `session=None` per CLAUDE.md
- This feature adds a new model (CompositionAssignment) and new columns
- Migration strategy: export-delete-import (per Constitution VI)
- 70 packaging-related tests expected to pass
- 88% coverage target for packaging_service.py
