---
work_package_id: "WP05"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
title: "Progress Service"
phase: "Phase 2 - Services"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "67266"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T03:09:20Z"
    lane: "planned"
    agent: "claude"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Progress Service

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Track production progress per recipe (batches complete vs target)
- Track assembly progress per bundle (assembled vs target)
- Calculate overall event progress
- Provide structured DTOs for UI consumption

**Success Metrics (from spec):**
- SC-006: Users can track production progress in real-time with visual feedback
- FR-030-033: Progress tracking and overall status

---

## Context & Constraints

### Reference Documents
- **Contract**: `kitty-specs/039-planning-workspace/contracts/planning_service.py` - ProductionProgress, AssemblyProgress
- **Research**: `kitty-specs/039-planning-workspace/research.md` - Existing event_service progress functions

### Key Constraints
- MUST wrap existing `event_service.get_production_progress()`
- MUST wrap existing `event_service.get_assembly_progress()`
- Session management: all functions accept optional `session` parameter
- Parallelizable with WP02, WP03, WP04

### Architectural Notes
- Located in `src/services/planning/progress.py`
- Extend event_service with DTO formatting
- Progress = (completed / target) * 100

---

## Subtasks & Detailed Guidance

### Subtask T025 - Create progress.py

- **Purpose**: Initialize progress tracking module
- **Steps**:
  1. Create `src/services/planning/progress.py`
  2. Add imports:
     ```python
     from dataclasses import dataclass
     from typing import Any, Dict, List, Optional
     from sqlalchemy.orm import Session
     from src.services.database import session_scope
     from src.services import event_service
     ```
- **Files**: `src/services/planning/progress.py`
- **Parallel?**: Yes

### Subtask T026 - Implement get_production_progress

- **Purpose**: Get production progress for all recipes (FR-030-031)
- **Steps**:
  1. Add function:
     ```python
     def get_production_progress(
         event_id: int,
         *,
         session: Optional[Session] = None,
     ) -> List[ProductionProgress]:
         """Get production progress for all recipe targets.

         Args:
             event_id: Event to get progress for
             session: Optional database session

         Returns:
             List of ProductionProgress
         """
     ```
  2. Implement `_get_production_progress_impl()`:
     - Call `event_service.get_production_progress(event_id, session=session)`
     - Transform to ProductionProgress DTOs
     - Calculate progress_percent = (completed / target) * 100
     - Set is_complete = (completed >= target)
- **Files**: `src/services/planning/progress.py`
- **Parallel?**: Yes

### Subtask T027 - Implement get_assembly_progress

- **Purpose**: Get assembly progress for all bundles
- **Steps**:
  1. Add function:
     ```python
     def get_assembly_progress(
         event_id: int,
         *,
         session: Optional[Session] = None,
     ) -> List[AssemblyProgress]:
         """Get assembly progress for all finished good targets.

         Args:
             event_id: Event to get progress for
             session: Optional database session

         Returns:
             List of AssemblyProgress
         """
     ```
  2. Implement `_get_assembly_progress_impl()`:
     - Call `event_service.get_assembly_progress(event_id, session=session)`
     - Transform to AssemblyProgress DTOs
     - Include `available_to_assemble` (from feasibility)
- **Files**: `src/services/planning/progress.py`
- **Parallel?**: Yes

### Subtask T028 - Implement get_overall_progress

- **Purpose**: Get overall event progress summary (FR-033)
- **Steps**:
  1. Add function:
     ```python
     def get_overall_progress(
         event_id: int,
         *,
         session: Optional[Session] = None,
     ) -> Dict[str, Any]:
         """Get overall event progress summary.

         Args:
             event_id: Event to get progress for
             session: Optional database session

         Returns:
             Dict with production_percent, assembly_percent, overall_percent, status
         """
     ```
  2. Implement `_get_overall_progress_impl()`:
     - Get production_progress and assembly_progress
     - Calculate averages:
       - production_percent = average of all recipe progress
       - assembly_percent = average of all bundle progress
       - overall_percent = (production_percent + assembly_percent) / 2
     - Determine status:
       - "not_started" if production_percent == 0
       - "complete" if production_percent == 100 && assembly_percent == 100
       - "in_progress" otherwise
- **Files**: `src/services/planning/progress.py`
- **Parallel?**: Yes

### Subtask T029 - Implement Progress DTOs

- **Purpose**: Define data structures per contract
- **Steps**:
  1. Add dataclasses:
     ```python
     @dataclass
     class ProductionProgress:
         recipe_id: int
         recipe_name: str
         target_batches: int
         completed_batches: int
         progress_percent: float
         is_complete: bool

     @dataclass
     class AssemblyProgress:
         finished_good_id: int
         finished_good_name: str
         target_quantity: int
         assembled_quantity: int
         available_to_assemble: int  # How many more can be assembled
         progress_percent: float
         is_complete: bool
     ```
  2. Ensure these match contract exactly
- **Files**: `src/services/planning/progress.py`
- **Parallel?**: Yes

### Subtask T030 - Write unit tests

- **Purpose**: Verify progress functions
- **Steps**:
  1. Create `src/tests/services/planning/test_progress.py`
  2. Test cases for `get_production_progress()`:
     - Zero progress: 0/7 batches = 0%
     - Partial progress: 4/7 batches = 57.14%
     - Complete: 7/7 batches = 100%, is_complete=True
  3. Test cases for `get_assembly_progress()`:
     - Zero assembled
     - Partial assembled
     - Complete
  4. Test cases for `get_overall_progress()`:
     - Not started status
     - In progress status
     - Complete status
     - Edge case: zero targets (handle gracefully)
- **Files**: `src/tests/services/planning/test_progress.py`
- **Parallel?**: Yes

---

## Test Strategy

**Unit Tests Required:**
- `src/tests/services/planning/test_progress.py`

**Run with:**
```bash
pytest src/tests/services/planning/test_progress.py -v
```

**Critical Test Cases:**
- Progress percentage calculation is accurate
- Division by zero handled (zero targets)
- Status values are correct

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Division by zero | Guard against zero target values |
| Floating point precision | Round to 2 decimal places for display |
| Session detachment | Pass session through all nested calls |

---

## Definition of Done Checklist

- [ ] progress.py created with all functions
- [ ] ProductionProgress and AssemblyProgress match contract
- [ ] get_production_progress wraps event_service
- [ ] get_assembly_progress wraps event_service
- [ ] get_overall_progress calculates correct averages
- [ ] Status values are accurate
- [ ] Zero targets handled gracefully
- [ ] All unit tests pass
- [ ] >70% test coverage on module
- [ ] `tasks.md` updated with status change

---

## Review Guidance

- Verify percentage calculation (completed/target * 100)
- Check is_complete flag logic
- Validate zero target handling
- Ensure session parameter pattern followed

---

## Activity Log

- 2026-01-06T03:09:20Z - claude - lane=planned - Prompt created.
- 2026-01-06T13:05:32Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-06T13:08:24Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2026-01-06T13:58:52Z – claude-reviewer – shell_pid=67266 – lane=done – Code review approved: Progress tracking with ProductionProgress/AssemblyProgress DTOs, percentage calculations, overall status aggregation - 29 tests passing
