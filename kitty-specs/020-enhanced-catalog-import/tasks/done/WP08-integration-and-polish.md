---
work_package_id: "WP08"
subtasks:
  - "T062"
  - "T063"
  - "T064"
  - "T065"
  - "T066"
  - "T067"
  - "T068"
title: "Integration and Polish"
phase: "Phase 3 - Interface"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "63528"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - Integration and Polish

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: Update `review_status: acknowledged` when addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: End-to-end validation, error message refinement, documentation updates, and verification of all success criteria.

**Success Criteria**:
- 160-ingredient catalog imports successfully via CLI
- 160-ingredient catalog imports successfully via UI
- Import completes in under 30 seconds (SC-010)
- All error messages are user-friendly and actionable
- Existing unified import/export functionality unchanged (SC-006)
- Service layer test coverage >70%
- Documentation reflects final verified implementation

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/020-enhanced-catalog-import/spec.md` - Success criteria SC-001 through SC-010
- `kitty-specs/020-enhanced-catalog-import/quickstart.md` - User documentation
- `test_data/baking_ingredients_v33.json` - 160-ingredient catalog file

**Prerequisites**:
- WP01-WP07 all complete (full implementation exists)

**Performance Target**:
- Import 160 ingredients in under 30 seconds
- If exceeded, consider batch commits (every 50 records)

---

## Subtasks & Detailed Guidance

### T062 - E2E Test: Import 160-ingredient catalog via CLI

**Purpose**: Verify real-world catalog import works end-to-end.

**Steps**:
1. Ensure clean database state (or note existing ingredient count)
2. Run CLI import:
   ```bash
   python -m src.utils.import_catalog test_data/baking_ingredients_v33.json --verbose
   ```
3. Verify:
   - Exit code 0
   - Output shows expected counts
   - Query database, verify ingredients created
4. Run again to verify skip behavior:
   ```bash
   python -m src.utils.import_catalog test_data/baking_ingredients_v33.json
   ```
5. Verify all 160 skipped (already exist)

**Files**: Manual test, document results in this file's Activity Log

---

### T063 - E2E Test: Import via UI

**Purpose**: Verify UI workflow end-to-end.

**Steps**:
1. Start application: `python src/main.py`
2. Navigate: File > Import Catalog...
3. Test workflow:
   - Select `test_data/baking_ingredients_v33.json`
   - Select "Add Only" mode
   - Check "Ingredients" (uncheck others if possible)
   - Click "Preview..." (dry-run)
   - Verify preview shows expected counts
   - Click "Import" (actual import)
   - Verify results dialog shows success
4. Verify Ingredients tab refreshes and shows new ingredients
5. Close dialog, verify application stable

**Files**: Manual test, document results in this file's Activity Log

---

### T064 - Verify SC-010: Import completes in under 30 seconds

**Purpose**: Confirm performance requirement met.

**Steps**:
1. Time the CLI import:
   ```bash
   time python -m src.utils.import_catalog test_data/baking_ingredients_v33.json
   ```
2. Record elapsed time
3. If under 30 seconds, mark as PASS
4. If over 30 seconds:
   - Profile to identify bottleneck
   - Consider batch commits (every 50 records)
   - Re-test after optimization

**Expected**: ~2-5 seconds for 160 records (well under limit)

**Files**: Document timing in Activity Log

---

### T065 - Review and refine error message wording

**Purpose**: Ensure all error messages are user-friendly and actionable.

**Steps**:
1. Review error messages in `catalog_import_service.py`
2. Test each error scenario:
   - File not found
   - Invalid JSON
   - Wrong format (unified import file)
   - Missing FK reference
   - Name collision (recipe)
   - Circular reference
3. For each error, verify message includes:
   - What went wrong
   - Which record/entity caused it
   - What the user should do to fix it
4. Refine wording if needed (no jargon, clear action)

**Example improvements**:
- BAD: "FK constraint violation: ingredient_id"
- GOOD: "Product 'Organic Flour 5lb' references ingredient 'organic_flour' which doesn't exist. Import the ingredient first or correct the ingredient_slug."

**Files**: `src/services/catalog_import_service.py`

---

### T066 - Verify existing unified import/export unchanged (SC-006)

**Purpose**: Regression test to ensure existing functionality not broken.

**Steps**:
1. Run existing import/export tests:
   ```bash
   pytest src/tests/test_import_export_service.py -v
   ```
2. Verify all existing tests pass
3. Manual verification:
   - Export current database via UI (File > Export Data...)
   - Note file contents
   - Import same file via UI (File > Import Data...)
   - Verify no errors, data unchanged
4. Confirm unified import correctly rejects catalog files:
   - Attempt to import catalog file via unified import
   - Verify appropriate error message

**Files**: `src/tests/test_import_export_service.py`

---

### T067 - Update quickstart.md with final verified commands

**Purpose**: Ensure documentation matches actual implementation.

**Steps**:
1. Read current `quickstart.md`
2. Verify each command works as documented:
   ```bash
   python -m src.utils.import_catalog --help
   python -m src.utils.import_catalog catalog.json
   python -m src.utils.import_catalog catalog.json --mode=augment
   python -m src.utils.import_catalog catalog.json --entity=ingredients
   python -m src.utils.import_catalog catalog.json --dry-run --verbose
   ```
3. Update any commands that don't match implementation
4. Add any missing flags or options
5. Verify file format example matches schema

**Files**: `kitty-specs/020-enhanced-catalog-import/quickstart.md`

---

### T068 - Run test coverage report, ensure >70% on service layer

**Purpose**: Verify test coverage meets Constitution requirement.

**Steps**:
1. Run coverage report:
   ```bash
   pytest src/tests/test_catalog_import_service.py -v --cov=src/services/catalog_import_service --cov-report=term-missing
   ```
2. Review coverage:
   - Target: >70% coverage
   - Identify any uncovered critical paths
3. If under 70%:
   - Add tests for uncovered paths
   - Focus on error handling paths
4. Run full service layer coverage:
   ```bash
   pytest src/tests -v --cov=src/services --cov-report=term-missing
   ```
5. Document coverage percentage in Activity Log

**Files**: `src/tests/test_catalog_import_service.py`

---

## Test Strategy

**Required Verification**:
- T062: CLI E2E with 160 ingredients
- T063: UI E2E manual test
- T064: Performance timing
- T066: Regression tests pass
- T068: Coverage >70%

**Commands**:
```bash
# Full test suite
pytest src/tests -v

# Catalog import tests only
pytest src/tests/test_catalog_import_service.py -v

# Coverage report
pytest src/tests -v --cov=src/services --cov-report=html
open htmlcov/index.html
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance >30s | Profile and add batch commits |
| Regression in unified import | Run full test suite before marking done |
| Documentation drift | Verify each command before updating |

---

## Definition of Done Checklist

- [ ] T062: CLI E2E test passes with 160-ingredient catalog
- [ ] T063: UI E2E test passes
- [ ] T064: Performance under 30 seconds verified
- [ ] T065: All error messages reviewed and user-friendly
- [ ] T066: Existing unified import/export tests pass
- [ ] T067: quickstart.md verified and updated
- [ ] T068: Test coverage >70% on service layer
- [ ] All success criteria (SC-001 through SC-010) verified
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

**Reviewer Checkpoints**:
1. 160-ingredient import succeeds (CLI and UI)
2. Performance timing documented
3. Error messages are actionable (no jargon)
4. Existing tests still pass
5. Coverage report shows >70%

---

## Activity Log

- 2025-12-14T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-15T03:08:47Z – claude – shell_pid=56445 – lane=doing – Started integration testing
- 2025-12-15T03:13:57Z – claude – shell_pid=56445 – lane=for_review – Ready for review
- 2025-12-15T03:25:42Z – claude-reviewer – shell_pid=63528 – lane=done – Code review: APPROVED - Integration verified, 755 tests pass, 90.80% coverage, E2E import under 2s (SC-010: <30s)
