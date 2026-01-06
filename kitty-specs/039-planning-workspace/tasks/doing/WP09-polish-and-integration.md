---
work_package_id: "WP09"
subtasks:
  - "T058"
  - "T059"
  - "T060"
  - "T061"
  - "T062"
  - "T063"
  - "T064"
  - "T065"
title: "Polish & Integration"
phase: "Phase 4 - Validation"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "71115"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T03:09:20Z"
    lane: "planned"
    agent: "claude"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 - Polish & Integration

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Validate full workflow end-to-end
- Test all edge cases from spec
- Verify performance requirements
- Ensure test coverage meets threshold
- Final validation before feature acceptance

**Success Metrics (from spec):**
- SC-002: Plan calculation <500ms for 10+ recipes
- SC-003: Batch calculations NEVER produce shortfall
- SC-008: Shopping list gap calculation 100% accurate
- Constitution: >70% service layer test coverage

---

## Context & Constraints

### Reference Documents
- **Spec**: `kitty-specs/039-planning-workspace/spec.md` - Edge cases, acceptance scenarios
- **Quickstart**: `kitty-specs/039-planning-workspace/quickstart.md` - Verification checklist
- **Constitution**: `.kittify/memory/constitution.md` - Test coverage requirements

### Key Constraints
- NOT parallelizable (final validation phase)
- Depends on WP08 (all components complete)
- Must pass all acceptance scenarios before feature acceptance

---

## Subtasks & Detailed Guidance

### Subtask T058 - Validate full workflow

- **Purpose**: End-to-end workflow test
- **Steps**:
  1. Create integration test or manual test script:
     ```
     1. Create new Event with BUNDLED output_mode
     2. Add assembly targets (e.g., 50 Holiday Gift Bags)
     3. Navigate to PLAN mode
     4. Click "Calculate Plan" - verify results display
     5. Navigate to Shop - verify shopping list
     6. Mark shopping complete
     7. Navigate to Produce - verify progress bars
     8. (Simulate batch completion)
     9. Navigate to Assemble - verify checklist enables
     10. Complete assembly checklist
     11. Verify overall progress shows 100%
     ```
  2. Document any issues found
  3. Test with realistic data volume (10+ recipes, 5+ bundles)
- **Files**: Integration test or manual test script
- **Notes**: This validates the entire feature flow

### Subtask T059 - Test edge cases

- **Purpose**: Verify edge case handling from spec
- **Steps**:
  1. Test each edge case from spec:
     - [ ] Bundle with no composition -> "Bundle has no components defined"
     - [ ] FinishedUnit with no recipe -> "No recipe found for [unit name]"
     - [ ] Recipe with no yield -> Handle gracefully (use 1?)
     - [ ] Zero requirements -> Validation error prevents calculation
     - [ ] Inventory check failure -> "Unable to check inventory" fallback
     - [ ] Single yield option -> Works without optimization
     - [ ] Waste threshold cannot be met -> Warning displayed
  2. Create test cases for each:
     ```python
     def test_bundle_with_no_composition():
         # Create bundle with no components
         # Attempt calculate_plan
         # Assert appropriate error raised/displayed
     ```
- **Files**: `src/tests/services/planning/test_edge_cases.py`

### Subtask T060 - Verify staleness detection

- **Purpose**: Ensure plan outdated detection works (FR-039-040)
- **Steps**:
  1. Test staleness scenarios:
     - [ ] Fresh plan (no changes) -> Not stale
     - [ ] Event modified after calculation -> Stale
     - [ ] Recipe modified after calculation -> Stale
     - [ ] Bundle composition added -> Stale
     - [ ] Target quantity changed -> Stale
  2. Test UI integration:
     - [ ] Stale banner appears when plan is stale
     - [ ] Recalculate button updates plan
     - [ ] Banner disappears after recalculation
- **Files**: Test files + manual verification

### Subtask T061 - Verify shortfall prevention

- **Purpose**: Confirm SC-003 (never short)
- **Steps**:
  1. Create comprehensive batch calculation tests:
     ```python
     @pytest.mark.parametrize("needed,yield_per,expected_batches,expected_yield", [
         (48, 48, 1, 48),   # Exact fit
         (49, 48, 2, 96),   # 1 over
         (1, 48, 1, 48),    # Minimum
         (300, 48, 7, 336), # Large
         (1000, 48, 21, 1008), # Very large
     ])
     def test_batch_never_short(needed, yield_per, expected_batches, expected_yield):
         result = calculate_batches(needed, yield_per)
         assert result == expected_batches
         assert result * yield_per >= needed  # CRITICAL: never short
     ```
  2. Run with various quantities and yield values
  3. Assert `total_yield >= units_needed` in ALL cases
- **Files**: `src/tests/services/planning/test_batch_calculation.py`

### Subtask T062 - Verify gap calculation

- **Purpose**: Confirm SC-008 (accurate shopping gaps)
- **Steps**:
  1. Create gap calculation tests:
     ```python
     @pytest.mark.parametrize("needed,in_stock,expected_gap", [
         (10, 5, 5),    # Need more
         (10, 10, 0),   # Exact
         (10, 15, 0),   # Sufficient (not negative!)
         (100, 0, 100), # Nothing in stock
         (0, 50, 0),    # Don't need any
     ])
     def test_gap_calculation(needed, in_stock, expected_gap):
         gap = calculate_purchase_gap(Decimal(needed), Decimal(in_stock))
         assert gap == Decimal(expected_gap)
         assert gap >= 0  # NEVER negative
     ```
  2. Verify with realistic ingredient data
- **Files**: `src/tests/services/planning/test_shopping_list.py`

### Subtask T063 - Verify performance

- **Purpose**: Confirm SC-002 (<500ms for 10+ recipes)
- **Steps**:
  1. Create performance test:
     ```python
     import time

     def test_calculation_performance():
         # Setup: Create event with 10+ recipes, 5+ bundles
         event_id = create_test_event_with_many_recipes(num_recipes=15)

         start = time.perf_counter()
         result = planning_service.calculate_plan(event_id)
         elapsed = time.perf_counter() - start

         assert elapsed < 0.5, f"Calculation took {elapsed:.2f}s, must be <0.5s"
     ```
  2. Profile if too slow:
     - Check for N+1 queries
     - Add eager loading where needed
     - Consider caching
- **Files**: `src/tests/services/planning/test_performance.py`
- **Notes**: May need optimization if fails

### Subtask T064 - Run coverage verification

- **Purpose**: Ensure >70% service layer coverage
- **Steps**:
  1. Run coverage report:
     ```bash
     pytest src/tests/services/planning/ -v --cov=src/services/planning --cov-report=term-missing
     ```
  2. Verify coverage >= 70% for:
     - batch_calculation.py
     - shopping_list.py
     - feasibility.py
     - progress.py
     - planning_service.py
  3. Add tests for uncovered lines if needed
- **Files**: Coverage output
- **Notes**: Constitution requires >70% service coverage

### Subtask T065 - Update quickstart checklist

- **Purpose**: Document verification results
- **Steps**:
  1. Update `quickstart.md` verification checklist with results:
     ```markdown
     ## Verification Checklist

     - [x] All service tests pass with >70% coverage (actual: XX%)
     - [x] UI displays correctly in all phases
     - [x] Batch calculation never produces shortfall
     - [x] Shopping list aggregates correctly
     - [x] Staleness detection works
     - [x] Progress bars update dynamically
     - [x] Warnings display for incomplete prerequisites
     - [x] Plan persists across sessions
     - [ ] Export/import cycle preserves plan data (if applicable)
     ```
  2. Note any issues or limitations discovered
- **Files**: `kitty-specs/039-planning-workspace/quickstart.md`

---

## Test Strategy

**Run all tests:**
```bash
pytest src/tests/services/planning/ -v --cov=src/services/planning --cov-report=term-missing
```

**Critical Validations:**
- [ ] All edge cases handled
- [ ] No shortfall possible
- [ ] Performance within threshold
- [ ] Coverage meets requirement

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance issues | Profile and optimize queries |
| Coverage gaps | Add targeted tests |
| Edge case failures | Fix and retest |

---

## Definition of Done Checklist

- [ ] Full workflow validated end-to-end
- [ ] All edge cases tested and passing
- [ ] Staleness detection verified
- [ ] Shortfall prevention verified (SC-003)
- [ ] Gap calculation verified (SC-008)
- [ ] Performance verified <500ms (SC-002)
- [ ] Coverage >70% on services/planning
- [ ] quickstart.md checklist updated with results
- [ ] Feature ready for acceptance (`/spec-kitty.accept`)
- [ ] `tasks.md` updated with status change

---

## Review Guidance

- Verify all success criteria from spec are met
- Check coverage report for gaps
- Validate performance on realistic data
- Confirm no regressions in existing functionality

---

## Activity Log

- 2026-01-06T03:09:20Z - claude - lane=planned - Prompt created.
- 2026-01-06T15:19:30Z – claude – shell_pid=71115 – lane=doing – Started implementation - Polish and Integration validation
