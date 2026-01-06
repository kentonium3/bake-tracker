---
work_package_id: "WP04"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Feasibility Service"
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

# Work Package Prompt: WP04 - Feasibility Service

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Check assembly feasibility: can all bundles be assembled given production?
- Check production feasibility: are ingredients available for recipes?
- Support partial assembly when some components are available
- Return structured results with missing component details

**Success Metrics (from spec):**
- SC-005: Assembly feasibility status is accurate - if system shows "can assemble", production yields are mathematically sufficient
- FR-022-026: Visual status indicators for feasibility

---

## Context & Constraints

### Reference Documents
- **Contract**: `kitty-specs/039-planning-workspace/contracts/planning_service.py` - FeasibilityResult, FeasibilityStatus
- **Research**: `kitty-specs/039-planning-workspace/research.md` - Existing assembly_service, batch_production_service

### Key Constraints
- MUST wrap existing `assembly_service.check_can_assemble()`
- MUST wrap existing `batch_production_service.check_can_produce()`
- Session management: all functions accept optional `session` parameter
- Parallelizable with WP02, WP03, WP05

### Architectural Notes
- Located in `src/services/planning/feasibility.py`
- No inventory transactions - read-only checks
- Return structured DTOs for UI consumption

---

## Subtasks & Detailed Guidance

### Subtask T019 - Create feasibility.py

- **Purpose**: Initialize feasibility module
- **Steps**:
  1. Create `src/services/planning/feasibility.py`
  2. Add imports:
     ```python
     from dataclasses import dataclass
     from enum import Enum
     from typing import Any, Dict, List, Optional
     from sqlalchemy.orm import Session
     from src.services.database import session_scope
     from src.services import assembly_service, batch_production_service
     ```
- **Files**: `src/services/planning/feasibility.py`
- **Parallel?**: Yes

### Subtask T020 - Implement check_assembly_feasibility

- **Purpose**: Check if bundles can be assembled (FR-022-026)
- **Steps**:
  1. Add function:
     ```python
     def check_assembly_feasibility(
         event_id: int,
         *,
         session: Optional[Session] = None,
     ) -> List[FeasibilityResult]:
         """Check assembly feasibility for all targets.

         Args:
             event_id: Event to check
             session: Optional database session

         Returns:
             List of FeasibilityResult for each assembly target
         """
     ```
  2. Implement `_check_assembly_feasibility_impl()`:
     - Query EventAssemblyTarget for event
     - For each target:
       - Call `assembly_service.check_can_assemble(finished_good_id, target_quantity, session=session)`
       - Determine FeasibilityStatus based on result
       - Build FeasibilityResult with missing_components detail
- **Files**: `src/services/planning/feasibility.py`
- **Parallel?**: Yes
- **Notes**: Pass session to assembly_service

### Subtask T021 - Implement check_production_feasibility

- **Purpose**: Check if recipes can be produced (ingredient availability)
- **Steps**:
  1. Add function:
     ```python
     def check_production_feasibility(
         event_id: int,
         *,
         session: Optional[Session] = None,
     ) -> List[Dict[str, Any]]:
         """Check production feasibility (ingredient availability).

         Args:
             event_id: Event to check
             session: Optional database session

         Returns:
             List of dicts with recipe_id, can_produce, missing ingredients
         """
     ```
  2. Implement `_check_production_feasibility_impl()`:
     - Query EventProductionTarget for event
     - For each target:
       - Call `batch_production_service.check_can_produce(recipe_id, target_batches, session=session)`
       - Return structured result with any missing ingredients
- **Files**: `src/services/planning/feasibility.py`
- **Parallel?**: Yes

### Subtask T022 - Implement Feasibility DTOs

- **Purpose**: Define data structures per contract
- **Steps**:
  1. Add enums and dataclasses:
     ```python
     class FeasibilityStatus(Enum):
         CAN_ASSEMBLE = "can_assemble"
         PARTIAL = "partial"  # Can assemble some but not all
         CANNOT_ASSEMBLE = "cannot_assemble"
         AWAITING_PRODUCTION = "awaiting_production"

     @dataclass
     class FeasibilityResult:
         finished_good_id: int
         finished_good_name: str
         target_quantity: int
         can_assemble: int  # How many CAN be assembled now
         status: FeasibilityStatus
         missing_components: List[Dict[str, Any]]  # What's short
     ```
  2. Ensure these match contract exactly
- **Files**: `src/services/planning/feasibility.py`
- **Parallel?**: Yes

### Subtask T023 - Handle partial assembly feasibility

- **Purpose**: Support assembling what's available (FR-028, FR-036)
- **Steps**:
  1. Modify `check_assembly_feasibility` to calculate partial assembly:
     - Determine how many complete sets of components are available
     - Example: need 50 bags, have 300 cookies (need 6 each) and 120 brownies (need 3 each)
       - Cookies: 300/6 = 50 bags worth
       - Brownies: 120/3 = 40 bags worth
       - Can assemble: min(50, 40) = 40 bags
     - Return `can_assemble = 40`, status = PARTIAL
  2. Set status logic:
     - `can_assemble >= target` -> CAN_ASSEMBLE
     - `can_assemble > 0 && < target` -> PARTIAL
     - `can_assemble == 0 && production_incomplete` -> AWAITING_PRODUCTION
     - `can_assemble == 0 && production_complete` -> CANNOT_ASSEMBLE
- **Files**: `src/services/planning/feasibility.py`
- **Parallel?**: Yes
- **Notes**: This enables flexible workflow (assemble while producing)

### Subtask T024 - Write unit tests

- **Purpose**: Verify feasibility functions
- **Steps**:
  1. Create `src/tests/services/planning/test_feasibility.py`
  2. Test cases for `check_assembly_feasibility()`:
     - All components available -> CAN_ASSEMBLE
     - Some components available -> PARTIAL with correct can_assemble count
     - Zero components -> AWAITING_PRODUCTION or CANNOT_ASSEMBLE
     - Multiple bundles with different statuses
  3. Test cases for `check_production_feasibility()`:
     - All ingredients available
     - Some ingredients missing
     - Multiple recipes
  4. Test partial assembly calculation:
     - Minimum of all component availability
- **Files**: `src/tests/services/planning/test_feasibility.py`
- **Parallel?**: Yes

---

## Test Strategy

**Unit Tests Required:**
- `src/tests/services/planning/test_feasibility.py`

**Run with:**
```bash
pytest src/tests/services/planning/test_feasibility.py -v
```

**Critical Test Cases:**
- Partial assembly calculates minimum correctly
- Status enum values are accurate
- Missing components list is populated correctly

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Complex nested queries | Use eager loading; test with realistic data |
| Division by zero | Guard against zero component_quantity |
| Session detachment | Pass session through all nested calls |

---

## Definition of Done Checklist

- [ ] feasibility.py created with all functions
- [ ] FeasibilityResult and FeasibilityStatus match contract
- [ ] check_assembly_feasibility wraps assembly_service
- [ ] check_production_feasibility wraps batch_production_service
- [ ] Partial assembly correctly calculates can_assemble
- [ ] Status values are accurate
- [ ] All unit tests pass
- [ ] >70% test coverage on module
- [ ] `tasks.md` updated with status change

---

## Review Guidance

- Verify partial assembly calculation (minimum across components)
- Check status enum values match spec
- Validate missing_components structure
- Ensure session parameter pattern followed

---

## Activity Log

- 2026-01-06T03:09:20Z - claude - lane=planned - Prompt created.
- 2026-01-06T13:05:45Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-06T13:13:24Z – system – shell_pid= – lane=for_review – Moved to for_review
