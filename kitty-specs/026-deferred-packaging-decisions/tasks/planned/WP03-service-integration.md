---
work_package_id: "WP03"
subtasks:
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "Service Integration"
phase: "Phase 2 - Service Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
gemini_candidate: true
history:
  - timestamp: "2025-12-21T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Service Integration

**GEMINI DELEGATION CANDIDATE**: This work package updates independent service files and is suitable for parallel development.

## Objectives & Success Criteria

- Update composition_service to support `is_generic` flag
- Update assembly_service with packaging assignment validation
- Update shopping_list_service to group generic packaging by `product_name`
- Add bypass flag support for assembly completion
- All existing service tests continue to pass
- New functionality tested

## Context & Constraints

**References**:
- `kitty-specs/026-deferred-packaging-decisions/plan.md` - Phase 2 service updates
- `kitty-specs/026-deferred-packaging-decisions/research.md` - Service integration notes
- `CLAUDE.md` - Session Management section (CRITICAL)
- Existing service files for patterns

**Constraints**:
- Must not break existing service behavior
- Default values must preserve backward compatibility
- Follow session management pattern per CLAUDE.md

**Parallel Opportunities**:
- T014, T015, T016 update different service files - can proceed in parallel
- **SUITABLE FOR GEMINI DELEGATION**

## Subtasks & Detailed Guidance

### Subtask T014 - Update composition_service.py

- **Purpose**: Support `is_generic` flag in composition creation and updates
- **Steps**:
  1. Open `src/services/composition_service.py`
  2. Add `is_generic: bool = False` parameter to create/update methods
  3. Persist `is_generic` flag when creating compositions
  4. Add method to retrieve compositions with their assignment status
  5. Update any serialization to include `is_generic` field
- **Files**: `src/services/composition_service.py`
- **Parallel?**: Yes - independent of other service files
- **Notes**:
  - Default `is_generic=False` preserves existing behavior
  - May need to add relationship loading for assignments

### Subtask T015 - Update assembly_service.py

- **Purpose**: Add validation for unassigned packaging at assembly completion
- **Steps**:
  1. Open `src/services/assembly_service.py`
  2. Add `check_packaging_assigned(assembly_id, session=None)` method:
     - Query compositions for the assembly where `is_generic=True`
     - Check if each has complete assignments
     - Return list of unassigned packaging requirements
  3. Update `record_assembly()` to optionally validate packaging
  4. Add `bypass_packaging_check: bool = False` parameter
  5. When bypass used, set flag on AssemblyRun for reconciliation
- **Files**: `src/services/assembly_service.py`
- **Parallel?**: Yes - independent of other service files
- **Notes**:
  - Validation is opt-in to preserve existing behavior
  - Bypass flag should be recorded for later reconciliation

### Subtask T016 - Update shopping_list_service.py

- **Purpose**: Group generic packaging by `product_name` instead of specific product
- **Steps**:
  1. Open `src/services/shopping_list_service.py`
  2. When aggregating packaging needs, check `is_generic` flag
  3. For generic compositions:
     - Group by `product_name` instead of specific product
     - Sum quantities across all compositions with same `product_name`
     - Use estimated cost from `packaging_service.get_estimated_cost()`
  4. For specific compositions: preserve existing behavior
  5. Add "Estimated" flag to cost data for generic items
- **Files**: `src/services/shopping_list_service.py`
- **Parallel?**: Yes - independent of other service files
- **Notes**:
  - Output format: "Cellophane Bags 6x10: 50 needed (Estimated: $25.00)"
  - Import `packaging_service` for cost estimation

### Subtask T017 - Add bypass flag support

- **Purpose**: Enable assembly completion without full packaging assignment
- **Steps**:
  1. Define bypass flag on AssemblyRun model (if not exists)
  2. Set flag when `bypass_packaging_check=True` in `record_assembly()`
  3. Add query method to find assemblies needing reconciliation
  4. Document reconciliation workflow
- **Files**: `src/services/assembly_service.py`, `src/models/assembly_run.py`
- **Parallel?**: No - depends on T015
- **Notes**:
  - Flag enables later reconciliation workflow
  - May need model changes for bypass tracking

## Test Strategy

```bash
# Run affected service tests
pytest src/tests/services/test_composition_service.py -v
pytest src/tests/services/test_assembly_service.py -v
pytest src/tests/services/test_shopping_list_service.py -v
```

New tests to add:
- `test_create_composition_with_is_generic`
- `test_check_packaging_assigned_finds_unassigned`
- `test_record_assembly_with_bypass`
- `test_shopping_list_groups_generic_packaging`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing behavior | Default values preserve current behavior |
| Missing test coverage | Run full test suite after changes |
| Session management issues | Follow CLAUDE.md pattern strictly |

## Definition of Done Checklist

- [ ] composition_service updated with `is_generic` support
- [ ] assembly_service updated with packaging validation
- [ ] shopping_list_service updated with generic grouping
- [ ] Bypass flag implemented
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] No lint errors

## Review Guidance

- Verify default values preserve backward compatibility
- Check session management pattern followed
- Confirm existing tests still pass
- Validate shopping list output format

## Activity Log

- 2025-12-21T12:00:00Z - system - lane=planned - Prompt created.
