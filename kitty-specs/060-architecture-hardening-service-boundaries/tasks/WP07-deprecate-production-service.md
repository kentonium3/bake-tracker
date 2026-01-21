---
work_package_id: "WP07"
subtasks:
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
title: "Deprecate Production Service"
phase: "Phase 2 - Parallel Track"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "29946"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-20T20:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2026-01-21T04:53:30Z"
    lane: "done"
    agent: "claude-opus"
    shell_pid: "29946"
    action: "Review passed - Production service deprecated"
---

# Work Package Prompt: WP07 – Deprecate Production Service

## Implementation Command

```bash
spec-kitty implement WP07 --base WP01
```

Depends on WP01 (session pattern established).

**Codex Parallelizable**: YES - This WP can be assigned to Codex for parallel execution with WP04, WP05, WP06 after WP01 completes.

---

## Objectives & Success Criteria

**Primary Objective**: Remove the old `production_service.record_production` method and migrate all callers to `batch_production_service`.

**Success Criteria**:
1. `production_tab.py` deleted (already marked DEPRECATED)
2. `record_production()` removed from production_service.py
3. All tests migrated to use batch_production_service
4. No remaining references to old service in codebase
5. Single production pattern throughout codebase

**Key Acceptance Checkpoints**:
- [ ] `production_tab.py` file deleted
- [ ] `record_production()` method removed
- [ ] Tests pass with batch_production_service
- [ ] `grep -r "production_service.record_production"` returns no results

---

## Context & Constraints

### Supporting Documents
- **Research**: `kitty-specs/060-architecture-hardening-service-boundaries/research.md` - Section 3 (Production Service Caller Analysis)
- **Plan**: `kitty-specs/060-architecture-hardening-service-boundaries/plan.md` - WP07 section

### Current State (from research)

**Active Callers**:
| File | Line | Status |
|------|------|--------|
| `src/ui/production_tab.py` | 337 | File DEPRECATED |

**Already Migrated**:
| File | Uses |
|------|------|
| `src/ui/forms/record_production_dialog.py` | `batch_production_service` |

**Tests to Migrate**:
| File | References |
|------|------------|
| `src/tests/services/test_production_service.py` | 14+ |

### Migration Risk Assessment
**RISK: LOW**
- Only 1 active UI caller (in deprecated file)
- Modern UI already uses batch_production_service
- Tests are the main migration work

### Comparison: Old vs New

| Aspect | production_service | batch_production_service |
|--------|-------------------|-------------------------|
| Session param | NO | YES |
| Recipe snapshot | NO | YES |
| Loss tracking | NO | YES |
| FIFO with session | NO | YES |
| Cost variance | NO | YES |

---

## Subtasks & Detailed Guidance

### Subtask T033 – Delete deprecated production_tab.py file

**Purpose**: Remove the deprecated UI file that is the only active caller of old production service.

**Steps**:

1. Verify production_tab.py is marked DEPRECATED:
   ```bash
   head -20 src/ui/production_tab.py
   ```
   Should show deprecation notice (lines 1-15)

2. Verify no other files import production_tab:
   ```bash
   grep -r "production_tab\|ProductionTab" src/ --include="*.py" | grep -v production_tab.py
   ```

3. Check if production_tab is registered in app navigation:
   - Look in main app file for tab registration
   - Remove any registration if present

4. Delete the file:
   ```bash
   rm src/ui/production_tab.py
   ```

5. If there's a corresponding test file, delete it too:
   ```bash
   rm src/tests/ui/test_production_tab.py 2>/dev/null || true
   ```

6. Run tests to verify no import errors:
   ```bash
   ./run-tests.sh -v
   ```

**Files**:
- `src/ui/production_tab.py` (DELETE)
- `src/tests/ui/test_production_tab.py` (DELETE if exists)
- Main app file (remove registration if needed)

**Parallel?**: Yes - can proceed alongside T034

**Notes**:
- File is already marked for removal
- This is a clean delete, not a migration
- Verify no hidden dependencies first

---

### Subtask T034 – Remove record_production() from production_service.py

**Purpose**: Remove the deprecated method to enforce single production pattern.

**Steps**:

1. Open `src/services/production_service.py`

2. Locate `record_production()` function and its helper if any

3. Before deleting, document what it did (for reference):
   ```python
   # REMOVED: record_production()
   # Was: Record batches of a recipe as produced for an event
   # Replaced by: batch_production_service.record_batch_production()
   # Reason: Lacks session param, recipe snapshot, loss tracking
   ```

4. Delete the function (typically ~100 lines based on research)

5. Check for any private helper functions only used by record_production:
   ```bash
   grep -n "def _" src/services/production_service.py
   ```
   Delete any helpers that are now orphaned.

6. Keep other production_service functions if they exist and are still used:
   - May have utility functions for production queries
   - Only remove record_production and its exclusive helpers

7. If the entire file becomes empty/unused, consider keeping it with a note or deleting

**Files**:
- `src/services/production_service.py` (modify/delete ~100 lines)

**Parallel?**: Yes - can proceed alongside T033

**Notes**:
- Don't delete the entire service if other functions are used
- Add comment noting migration to batch_production_service
- Check for imports from this function elsewhere (T036)

---

### Subtask T035 – Migrate tests to use batch_production_service

**Purpose**: Update test_production_service.py to test batch_production_service instead.

**Steps**:

1. Open `src/tests/services/test_production_service.py`

2. Identify test categories:
   - Tests for `record_production()` → Migrate or delete
   - Tests for other production_service functions → Keep if functions kept

3. For each test of record_production:

   **Option A: Migrate test to batch_production_service**
   ```python
   # Before
   def test_record_production_success():
       record = production_service.record_production(
           event_id=event_id, recipe_id=recipe_id, batches=2
       )
       assert record.batches == 2

   # After
   def test_record_batch_production_success():
       result = batch_production_service.record_batch_production(
           recipe_id=recipe_id,
           finished_unit_id=finished_unit_id,  # NEW: Required
           num_batches=2,
           actual_yield=48,  # NEW: Required
           session=session
       )
       assert result["success"] is True
   ```

   **Option B: Delete test if already covered**
   - Check if batch_production_service has equivalent test
   - If yes, delete duplicate

4. Update imports:
   ```python
   # Before
   from src.services import production_service

   # After
   from src.services import batch_production_service
   ```

5. Handle signature differences:
   - `record_production(event_id, recipe_id, batches)`
   - `record_batch_production(recipe_id, finished_unit_id, num_batches, actual_yield, ...)`

6. Note tests that need new fixtures:
   - batch_production requires `finished_unit_id`
   - May need to create finished units in test setup

7. Consider renaming test file if all tests migrated:
   - Could merge into `test_batch_production_service.py`
   - Or keep as `test_production_service.py` for other functions

**Files**:
- `src/tests/services/test_production_service.py` (modify significantly)
- `src/tests/services/test_batch_production_service.py` (may add tests)

**Parallel?**: No - main work of this WP

**Notes**:
- This is the bulk of the work (14+ test references)
- batch_production_service may already have comprehensive tests
- Don't duplicate tests that already exist
- Focus on coverage, not test count

---

### Subtask T036 – Remove unused imports referencing old service

**Purpose**: Clean up any lingering imports of the removed function.

**Steps**:

1. Search for imports:
   ```bash
   grep -r "from src.services.production_service import" src/ --include="*.py"
   grep -r "from src.services import production_service" src/ --include="*.py"
   grep -r "import production_service" src/ --include="*.py"
   ```

2. For each file found:
   - If importing `record_production`: Remove import or update to batch_production
   - If importing other functions: Keep import

3. Check for wildcard imports:
   ```bash
   grep -r "from src.services.production_service import \*" src/
   ```

4. Update __init__.py if production_service is re-exported:
   ```python
   # In src/services/__init__.py
   # Remove if present:
   from .production_service import record_production
   ```

5. Run import verification:
   ```bash
   python -c "from src.services import production_service" 2>&1 | head
   ```
   Should not error if file still exists with other functions.

**Files**:
- Various files with imports (identify via grep)
- `src/services/__init__.py` (if exports production_service)

**Parallel?**: Yes - can proceed alongside T033, T034

**Notes**:
- May find no imports if T033/T034 removed all callers
- This is cleanup/verification step
- Run after T033, T034 for best results

---

### Subtask T037 – Verify no remaining references in codebase

**Purpose**: Final verification that migration is complete.

**Steps**:

1. Search for any remaining references:
   ```bash
   # Direct function call
   grep -r "production_service\.record_production" src/ --include="*.py"

   # Import of the function
   grep -r "record_production" src/ --include="*.py"

   # The deprecated tab
   grep -r "production_tab\|ProductionTab" src/ --include="*.py"
   ```

2. Expected results:
   - All searches should return empty
   - Or only return this WP documentation

3. Search in documentation:
   ```bash
   grep -r "record_production\|production_service" docs/ --include="*.md"
   ```
   Update any docs that reference the old function.

4. Search in configuration:
   ```bash
   grep -r "record_production\|production_tab" . --include="*.json" --include="*.yaml" --include="*.toml"
   ```

5. Run full test suite:
   ```bash
   ./run-tests.sh -v
   ```
   All tests should pass.

6. Start the application (if possible) and verify production UI works:
   - Navigate to production recording
   - Should use the new dialog (batch_production_service)
   - Old tab should not be accessible

7. Document completion:
   ```markdown
   ## Deprecation Complete

   - `production_service.record_production` removed
   - `production_tab.py` deleted
   - All tests migrated to batch_production_service
   - Verified no remaining references
   ```

**Files**:
- Various (verification only)
- Update documentation if references found

**Parallel?**: No - final verification

**Notes**:
- This is the "done" gate for the WP
- All searches should return empty
- If references found, go back and fix

---

## Test Strategy

**Required Tests**:
1. Tests previously testing record_production now test batch_production
2. No import errors after deletion
3. Full test suite passes
4. Production UI works (manual verification)

**Test Commands**:
```bash
# Run migrated tests
./run-tests.sh src/tests/services/test_production_service.py -v

# Run batch production tests
./run-tests.sh src/tests/services/test_batch_production_service.py -v

# Run all tests
./run-tests.sh -v

# Verify no import errors
python -c "import src.services; print('OK')"
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Hidden callers of old function | T037 comprehensive search |
| Tests fail after migration | T035 focuses on coverage |
| Import errors | T036 cleans up imports |
| Production UI breaks | Manual verification in T037 |

---

## Definition of Done Checklist

- [ ] T033: production_tab.py deleted
- [ ] T034: record_production() removed from production_service.py
- [ ] T035: Tests migrated to batch_production_service
- [ ] T036: Unused imports removed
- [ ] T037: No remaining references verified
- [ ] Full test suite passes
- [ ] grep for old function returns empty

---

## Review Guidance

**Key Review Checkpoints**:
1. All tests still pass after migration
2. No references to old function remain
3. batch_production_service used consistently
4. Documentation updated if needed

**Verification Commands for Reviewer**:
```bash
# Should return nothing
grep -r "production_service.record_production" src/
grep -r "production_tab" src/
ls src/ui/production_tab.py 2>&1 | grep -v "No such file"

# Should pass
./run-tests.sh -v
```

---

## Activity Log

- 2026-01-20T20:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-21T04:24:37Z – claude-opus – shell_pid=23366 – lane=doing – Started implementation via workflow command
- 2026-01-21T04:25:57Z – claude-opus – shell_pid=23366 – lane=planned – Reverting: worktree created nested inside WP06 worktree
- 2026-01-21T04:29:08Z – claude-opus – shell_pid=24713 – lane=doing – Started implementation via workflow command
- 2026-01-21T04:44:24Z – claude-opus – shell_pid=24713 – lane=for_review – Removed deprecated production_service.record_production() and production_tab.py. Tests migrated to use direct ProductionRecord creation. All 2549 tests pass.
- 2026-01-21T04:46:19Z – claude-opus – shell_pid=29946 – lane=doing – Started review via workflow command
- 2026-01-21T04:53:30Z – claude-opus – shell_pid=29946 – lane=done – Review passed: production_tab.py deleted, record_production() removed, tests migrated with helper function, removal comments added. All 2549 tests pass.
