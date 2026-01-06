---
work_package_id: "WP06"
subtasks:
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
title: "Planning Service Facade"
phase: "Phase 2 - Services"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T03:09:20Z"
    lane: "planned"
    agent: "claude"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Planning Service Facade

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create PlanningService facade that orchestrates all modules
- Implement calculate_plan that persists to ProductionPlanSnapshot
- Implement staleness detection using timestamp comparison
- Provide unified API matching the contract

**Success Metrics (from spec):**
- SC-001: Users can calculate a complete production plan within 3 clicks
- SC-002: Plan calculation completes in under 500ms for 10+ recipes
- FR-037-041: Plan persistence and staleness detection

---

## Context & Constraints

### Reference Documents
- **Contract**: `kitty-specs/039-planning-workspace/contracts/planning_service.py` - Full API definition
- **Quickstart**: `kitty-specs/039-planning-workspace/quickstart.md` - Staleness check algorithm
- **Data Model**: `kitty-specs/039-planning-workspace/data-model.md` - ProductionPlanSnapshot schema

### Key Constraints
- MUST follow contract signatures exactly
- MUST use session parameter pattern throughout
- Depends on WP02, WP03, WP04, WP05 (all modules)
- NOT parallelizable (integrates all modules)

### Architectural Notes
- Facade pattern: PlanningService delegates to focused modules
- All methods accept optional `session` parameter
- Exceptions defined: PlanningError, StalePlanError, IncompleteRequirementsError

---

## Subtasks & Detailed Guidance

### Subtask T031 - Create planning_service.py facade

- **Purpose**: Initialize facade with public API
- **Steps**:
  1. Create `src/services/planning/planning_service.py`
  2. Add imports from all modules:
     ```python
     from typing import Any, Dict, List, Optional
     from datetime import datetime
     from sqlalchemy.orm import Session
     from src.services.database import session_scope
     from src.models import Event, ProductionPlanSnapshot
     from .batch_calculation import (calculate_batches, explode_bundle_requirements,
                                     aggregate_by_recipe, RecipeBatchResult)
     from .shopping_list import get_shopping_list, mark_shopping_complete, ShoppingListItem
     from .feasibility import (check_assembly_feasibility, check_production_feasibility,
                              FeasibilityResult)
     from .progress import (get_production_progress, get_assembly_progress,
                           get_overall_progress, ProductionProgress, AssemblyProgress)
     ```
  3. Define class or module-level functions (per contract pattern)
- **Files**: `src/services/planning/planning_service.py`
- **Notes**: Follow contract structure exactly

### Subtask T032 - Implement calculate_plan

- **Purpose**: Orchestrate full plan calculation (FR-037)
- **Steps**:
  1. Add function matching contract:
     ```python
     def calculate_plan(
         event_id: int,
         *,
         force_recalculate: bool = False,
         session: Optional[Session] = None,
     ) -> Dict[str, Any]:
         """Calculate production plan for an event."""
     ```
  2. Implementation flow:
     a. Get Event, validate output_mode is set
     b. If not force_recalculate, check for existing non-stale plan
     c. Get requirements (EventAssemblyTarget or EventProductionTarget based on mode)
     d. Call explode_bundle_requirements if BUNDLED mode
     e. Call aggregate_by_recipe to get batch counts
     f. Call get_shopping_list for ingredient needs
     g. Call check_assembly_feasibility
     h. Persist to ProductionPlanSnapshot:
        - calculation_results JSON
        - requirements_updated_at, recipes_updated_at, bundles_updated_at
        - calculated_at = now
     i. Return dict with plan_id, calculated_at, recipe_batches, shopping_list, feasibility
- **Files**: `src/services/planning/planning_service.py`
- **Notes**: This is the core orchestration function

### Subtask T033 - Implement get_plan_summary

- **Purpose**: Get summary with phase statuses
- **Steps**:
  1. Add function:
     ```python
     def get_plan_summary(
         event_id: int,
         *,
         session: Optional[Session] = None,
     ) -> PlanSummary:
         """Get summary of current plan status."""
     ```
  2. Implementation:
     - Query latest ProductionPlanSnapshot for event
     - Calculate phase_statuses for each PlanPhase
     - Determine overall_status based on progress
     - Return PlanSummary DTO
  3. Define PlanSummary dataclass per contract
- **Files**: `src/services/planning/planning_service.py`

### Subtask T034 - Implement check_staleness

- **Purpose**: Detect when plan needs recalculation (FR-039-040)
- **Steps**:
  1. Add function:
     ```python
     def check_staleness(
         event_id: int,
         *,
         session: Optional[Session] = None,
     ) -> tuple[bool, Optional[str]]:
         """Check if plan is stale."""
     ```
  2. Implementation (per data-model.md):
     ```python
     # Compare calculated_at vs:
     # - Event.last_modified
     # - EventAssemblyTarget.updated_at (each)
     # - EventProductionTarget.updated_at (each)
     # - Recipe.last_modified (each in plan)
     # - FinishedGood.updated_at (each)
     # - Composition.created_at (bundle contents)
     # Return (True, reason) if any is newer than calculated_at
     ```
- **Files**: `src/services/planning/planning_service.py`
- **Notes**: Handle both timestamp field patterns (last_modified vs updated_at)

### Subtask T035 - Implement batch/shopping facade methods

- **Purpose**: Expose module functions through facade
- **Steps**:
  1. Add `get_recipe_batches()` - delegates to batch_calculation
  2. Add `get_shopping_list()` - delegates to shopping_list module
  3. Add `calculate_batches_for_quantity()` - utility for ad-hoc calculation
  4. Maintain session parameter pattern
- **Files**: `src/services/planning/planning_service.py`

### Subtask T036 - Implement feasibility facade methods

- **Purpose**: Expose feasibility functions through facade
- **Steps**:
  1. Add `check_assembly_feasibility()` - delegates to feasibility module
  2. Add `check_production_feasibility()` - delegates to feasibility module
  3. Maintain session parameter pattern
- **Files**: `src/services/planning/planning_service.py`

### Subtask T037 - Implement progress facade methods

- **Purpose**: Expose progress functions through facade
- **Steps**:
  1. Add `get_production_progress()` - delegates to progress module
  2. Add `get_assembly_progress()` - delegates to progress module
  3. Add `get_overall_progress()` - delegates to progress module
  4. Maintain session parameter pattern
- **Files**: `src/services/planning/planning_service.py`

### Subtask T038 - Implement assembly checklist methods

- **Purpose**: Support assembly workflow (FR-027-029)
- **Steps**:
  1. Add `get_assembly_checklist()`:
     - Query EventAssemblyTarget for event
     - For each: get target, assembled count, available to assemble
     - Return list of dicts
  2. Add `record_assembly_confirmation()`:
     - Status tracking only (no inventory transaction in Phase 2)
     - Update assembled count or progress tracking
     - Return confirmation details
- **Files**: `src/services/planning/planning_service.py`
- **Notes**: Phase 2 is confirmation-only, no inventory consumption

### Subtask T039 - Implement mark_shopping_complete facade

- **Purpose**: Track shopping completion
- **Steps**:
  1. Add `mark_shopping_complete()` - delegates to shopping_list module
  2. Maintain session parameter pattern
- **Files**: `src/services/planning/planning_service.py`

### Subtask T040 - Define exceptions

- **Purpose**: Define domain-specific exceptions
- **Steps**:
  1. Add exception classes (can be in same file or separate exceptions.py):
     ```python
     class PlanningError(Exception):
         """Base exception for planning service errors."""
         pass

     class StalePlanError(PlanningError):
         """Plan is stale and needs recalculation."""
         def __init__(self, reason: str):
             self.reason = reason
             super().__init__(f"Plan is stale: {reason}")

     class IncompleteRequirementsError(PlanningError):
         """Event requirements are incomplete."""
         def __init__(self, missing: List[str]):
             self.missing = missing
             super().__init__(f"Missing requirements: {', '.join(missing)}")

     class EventNotConfiguredError(PlanningError):
         """Event output_mode not set."""
         pass
     ```
- **Files**: `src/services/planning/planning_service.py` or `src/services/planning/exceptions.py`

### Subtask T041 - Write integration tests

- **Purpose**: Test full facade operation
- **Steps**:
  1. Create `src/tests/services/planning/test_planning_service.py`
  2. Test cases for `calculate_plan()`:
     - BUNDLED mode with bundles
     - BULK_COUNT mode with direct units
     - force_recalculate=True
     - EventNotConfiguredError when output_mode is None
  3. Test cases for `check_staleness()`:
     - Fresh plan (not stale)
     - Modified event (stale)
     - Modified recipe (stale)
     - Modified target (stale)
  4. Test cases for `get_plan_summary()`:
     - All phases not started
     - Some phases complete
     - All phases complete
  5. Integration: full workflow test
- **Files**: `src/tests/services/planning/test_planning_service.py`
- **Notes**: Use realistic test data with multiple recipes/bundles

---

## Test Strategy

**Integration Tests Required:**
- `src/tests/services/planning/test_planning_service.py`

**Run with:**
```bash
pytest src/tests/services/planning/test_planning_service.py -v
```

**Critical Test Cases:**
- calculate_plan produces correct results
- Staleness detection is accurate
- Exceptions are raised appropriately
- Session is maintained throughout transaction

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Transaction scope issues | Ensure facade methods maintain session |
| Performance with many recipes | Test with 10+ recipes; optimize if >500ms |
| Complex error handling | Define clear exception hierarchy |

---

## Definition of Done Checklist

- [ ] planning_service.py created with all facade methods
- [ ] calculate_plan orchestrates all modules correctly
- [ ] ProductionPlanSnapshot persisted with correct data
- [ ] check_staleness uses timestamp comparison
- [ ] get_plan_summary returns correct phase statuses
- [ ] All facade methods delegate correctly
- [ ] Exceptions defined and raised appropriately
- [ ] Session parameter pattern followed throughout
- [ ] Integration tests pass
- [ ] >70% coverage on facade
- [ ] `tasks.md` updated with status change

---

## Review Guidance

- Verify contract signatures match exactly
- Check session is passed through all delegations
- Validate staleness detection logic
- Ensure exceptions match contract definitions

---

## Activity Log

- 2026-01-06T03:09:20Z - claude - lane=planned - Prompt created.
- 2026-01-06T13:15:51Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-06T13:22:46Z – system – shell_pid= – lane=for_review – Moved to for_review
