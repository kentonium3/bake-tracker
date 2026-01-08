---
work_package_id: WP09
title: Testing & Polish
lane: done
history:
- timestamp: '2025-12-21T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
gemini_candidate: true
phase: Phase 9 - Testing & Polish
review_status: ''
reviewed_by: ''
shell_pid: '94728'
subtasks:
- T045
- T046
- T047
- T048
- T049
- T050
- T051
---

# Work Package Prompt: WP09 - Testing & Polish

**GEMINI DELEGATION CANDIDATE (Partial)**: Test writing (T045-T047) is independent work that can be delegated.

## Objectives & Success Criteria

- Achieve >80% unit test coverage for packaging_service
- Create integration tests for full workflow
- Test edge cases (shortage, re-assignment, bypass)
- Update import/export for new fields
- Complete user acceptance testing
- Update documentation as needed
- Validate quickstart scenario end-to-end

## Context & Constraints

**References**:
- `kitty-specs/026-deferred-packaging-decisions/plan.md` - Phase 9 details
- `kitty-specs/026-deferred-packaging-decisions/spec.md` - Acceptance criteria
- `kitty-specs/026-deferred-packaging-decisions/quickstart.md` - Test scenario
- Existing test patterns in `src/tests/`

**Constraints**:
- Test coverage must be >70% for new code
- No regressions in existing functionality
- Primary user acceptance required

**Parallel Opportunities**:
- T045, T046, T047 (test writing) can proceed in parallel
- **SUITABLE FOR GEMINI DELEGATION** - Test writing is independent

## Subtasks & Detailed Guidance

### Subtask T045 - Unit test coverage

- **Purpose**: Ensure packaging_service is well-tested
- **Steps**:
  1. Review existing tests in `test_packaging_service.py`
  2. Identify gaps in coverage
  3. Add tests for uncovered paths:
     - Edge cases (empty inventory, zero quantity)
     - Error paths (validation failures)
     - Boundary conditions
  4. Run coverage report; target >80%
- **Files**: `src/tests/services/test_packaging_service.py`
- **Parallel?**: Yes
- **Notes**:
  ```bash
  pytest src/tests/services/test_packaging_service.py -v --cov=src/services/packaging_service --cov-report=term-missing
  ```

### Subtask T046 - Integration tests

- **Purpose**: Validate complete workflows
- **Steps**:
  1. Create `src/tests/integration/test_deferred_packaging.py`
  2. Test full workflow:
     - Plan with generic packaging
     - Check pending requirements
     - Assign materials
     - Verify costs update
     - Complete assembly
  3. Test cost transition from estimated to actual
  4. Test shopping list with generic items
- **Files**: `src/tests/integration/test_deferred_packaging.py` (new)
- **Parallel?**: Yes
- **Notes**: Use fixtures that set up complete test scenarios

### Subtask T047 - Edge case testing

- **Purpose**: Validate behavior in unusual situations
- **Steps**:
  1. Test shortage scenario:
     - Generic requirement > available inventory
     - Partial assignment allowed
  2. Test re-assignment:
     - Clear existing assignments
     - Assign different products
  3. Test bypass reconciliation:
     - Complete without assignment
     - Later assign materials
     - Verify reconciliation clears flag
- **Files**: Integration tests
- **Parallel?**: Yes
- **Notes**: Document expected behavior for each case

### Subtask T048 - Update import/export

- **Purpose**: Support new fields in data exchange
- **Steps**:
  1. Update `import_export_service.py`:
     - Export `is_generic` field with compositions
     - Export `composition_assignments` table
  2. Update import logic:
     - Import `is_generic` flag
     - Import assignments (match by characteristics)
  3. Test round-trip: export -> delete -> import -> verify
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: No
- **Notes**:
  - See data-model.md for export format
  - Assignment import may need fuzzy matching

### Subtask T049 - User acceptance testing

- **Purpose**: Validate with primary user
- **Steps**:
  1. Prepare test environment with sample data
  2. Walk through each user story with Marianne
  3. Document any issues or feedback
  4. Address critical issues before acceptance
  5. Get sign-off on acceptance criteria
- **Files**: N/A (manual testing)
- **Parallel?**: No
- **Notes**:
  - Use quickstart.md scenario as guide
  - Focus on intuitive workflow

### Subtask T050 - Update CLAUDE.md

- **Purpose**: Document new patterns if needed
- **Steps**:
  1. Review changes for documentation-worthy patterns
  2. If packaging_service introduces new session patterns, document
  3. If CompositionAssignment relationship needs notes, add
  4. Keep documentation minimal and relevant
- **Files**: `CLAUDE.md`
- **Parallel?**: No
- **Notes**: Only add if truly valuable for future development

### Subtask T051 - Validate quickstart.md

- **Purpose**: Ensure quickstart scenario works end-to-end
- **Steps**:
  1. Follow quickstart.md instructions exactly
  2. Verify all commands work
  3. Verify all described behaviors occur
  4. Update quickstart if any steps changed
- **Files**: `kitty-specs/026-deferred-packaging-decisions/quickstart.md`
- **Parallel?**: No
- **Notes**: Final validation before feature acceptance

## Test Strategy

```bash
# Run all feature tests
pytest src/tests/services/test_packaging_service.py -v
pytest src/tests/integration/test_deferred_packaging.py -v

# Full test suite to check for regressions
pytest src/tests -v

# Coverage report
pytest src/tests -v --cov=src --cov-report=html
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Regression in existing tests | Run full suite before acceptance |
| Import/export compatibility | Test with sample_data.json |
| User acceptance blockers | Address critical issues immediately |

## Definition of Done Checklist

- [ ] Unit test coverage >80% for packaging_service
- [ ] Integration tests pass
- [ ] Edge cases tested
- [ ] Import/export works with new fields
- [ ] User acceptance testing completed
- [ ] Documentation updated (if needed)
- [ ] Quickstart scenario validated
- [ ] Full test suite passes
- [ ] No regressions

## Review Guidance

- Verify test coverage meets threshold
- Check that integration tests cover all user stories
- Confirm import/export round-trip works
- Validate user feedback incorporated

## Activity Log

- 2025-12-21T12:00:00Z - system - lane=planned - Prompt created.
- 2025-12-21T22:43:07Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-22T02:23:37Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-22T02:28:12Z – system – shell_pid= – lane=done – Approved
