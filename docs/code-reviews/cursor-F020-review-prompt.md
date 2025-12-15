# Code Review Prompt: Feature 020 - Enhanced Catalog Import

**Reviewer**: Cursor (acting as Senior Software Engineer)
**Feature**: 020-enhanced-catalog-import
**Worktree**: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/020-enhanced-catalog-import/`

---

## Your Role

You are a senior software engineer performing an independent code review of Feature 020 (Enhanced Catalog Import). This feature adds the ability to import ingredient catalogs, products, and recipes from external JSON files, separate from the existing unified import/export system.

Your review should be thorough, objective, and actionable. Evaluate whether the implementation correctly fulfills the specification, follows project architectural constraints, and is production-ready.

---

## Reference Documents (Read These First)

These documents define the intent, design, and acceptance criteria for this feature. Read them to understand what was supposed to be built:

| Document | Path | Purpose |
|----------|------|---------|
| **Specification** | `kitty-specs/020-enhanced-catalog-import/spec.md` | User stories, success criteria (SC-001 through SC-010), acceptance criteria |
| **Implementation Plan** | `kitty-specs/020-enhanced-catalog-import/plan.md` | Technical approach, design decisions, architecture |
| **Data Model** | `kitty-specs/020-enhanced-catalog-import/data-model.md` | Catalog file schema, field mappings, validation rules |
| **Research** | `kitty-specs/020-enhanced-catalog-import/research.md` | Background research on existing codebase patterns |
| **Quickstart** | `kitty-specs/020-enhanced-catalog-import/quickstart.md` | User documentation for CLI and UI usage |
| **Tasks** | `kitty-specs/020-enhanced-catalog-import/tasks.md` | Work packages and subtasks breakdown |

---

## Project Architectural Constraints

Read these files to understand non-negotiable project requirements:

| Document | Path | Key Constraints |
|----------|------|-----------------|
| **Project CLAUDE.md** | `CLAUDE.md` | Layered architecture (UI -> Services -> Models), session management patterns, test coverage requirements (>70% on service layer) |
| **Constitution** | `.kittify/constitution.md` | Project principles including TDD, FIFO accuracy, user-centric design |

**Critical Pattern**: The `session=None` pattern for transactional composition (documented in CLAUDE.md under "Session Management"). Service functions that may be called from other services MUST accept `session=None` and correctly propagate sessions.

---

## Implementation Files to Review

### Core Service (Primary Focus)

| File | Path | Lines | Description |
|------|------|-------|-------------|
| **Catalog Import Service** | `src/services/catalog_import_service.py` | ~1167 | Main service implementing all catalog import logic |

Key components to verify:
- `CatalogImportResult` class with per-entity tracking
- `ImportMode` enum (ADD_ONLY, AUGMENT)
- `import_ingredients()` - ingredient import with validation
- `import_products()` - product import with FK validation
- `import_recipes()` - recipe import with FK validation, collision detection, circular reference detection
- `validate_catalog_file()` - format detection and validation
- `import_catalog()` - coordinator function with dependency ordering
- Protected vs augmentable field classifications

### CLI Entry Point

| File | Path | Description |
|------|------|-------------|
| **CLI** | `src/utils/import_catalog.py` | CLI with argparse, exit codes (0/1/2/3), --mode, --entity, --dry-run, --verbose flags |

### UI Components

| File | Path | Description |
|------|------|-------------|
| **Dialog** | `src/ui/catalog_import_dialog.py` | CustomTkinter dialog with file picker, mode selection, entity checkboxes |
| **Main Window** | `src/ui/main_window.py` | Modified to add "Import Catalog..." menu item (look for `_show_catalog_import_dialog`) |

### Tests

| File | Path | Description |
|------|------|-------------|
| **Test Suite** | `src/tests/test_catalog_import_service.py` | 66 tests covering all service functions |

### Test Data

| File | Path | Description |
|------|------|-------------|
| **Sample Catalog** | `test_data/sample_catalog.json` | E2E test catalog with 5 ingredients, 2 products, 1 recipe |
| **160-Ingredient Catalog** | `test_data/baking_ingredients_v33.json` | Large catalog for performance testing |

---

## Review Checklist

### 1. Specification Compliance

Verify each success criterion from `spec.md`:

- [ ] **SC-001**: CLI import of ingredient catalog creates new Ingredient records
- [ ] **SC-002**: CLI import skips existing ingredients (matched by slug)
- [ ] **SC-003**: CLI import reports summary (added, skipped, failed counts)
- [ ] **SC-004**: AUGMENT mode fills null fields without overwriting existing values
- [ ] **SC-005**: Products and recipes can be imported with FK validation
- [ ] **SC-006**: Existing unified import/export functionality unchanged
- [ ] **SC-007**: Invalid catalog files produce actionable error messages
- [ ] **SC-008**: UI provides "Import Catalog..." menu option
- [ ] **SC-009**: Dry-run mode previews changes without committing
- [ ] **SC-010**: Import completes in under 30 seconds for 160 ingredients

### 2. Architecture Compliance

- [ ] Service layer contains no UI imports
- [ ] UI layer delegates all business logic to services
- [ ] `session=None` pattern correctly implemented in all public service functions
- [ ] No nested `session_scope()` calls that could cause detachment

### 3. Code Quality

- [ ] Error messages are user-friendly and actionable (no raw exceptions or jargon)
- [ ] FK validation provides clear guidance ("Product X references missing ingredient Y")
- [ ] Collision errors include enough detail to resolve (existing vs incoming)
- [ ] Circular reference detection works correctly

### 4. Test Coverage

- [ ] Test coverage >70% on `src/services/catalog_import_service.py`
- [ ] Tests cover happy path, edge cases, and error conditions
- [ ] Tests verify session parameter propagation
- [ ] E2E tests verify CLI and UI workflows

### 5. Data Integrity

- [ ] Import is transactional (all-or-nothing per session)
- [ ] Dry-run mode uses rollback (no database changes)
- [ ] Dependency order enforced: ingredients -> products -> recipes
- [ ] Protected fields cannot be overwritten in AUGMENT mode

### 6. Regression Safety

- [ ] Existing import_export_service.py unchanged
- [ ] Existing tests still pass (run full test suite)
- [ ] Catalog format detection correctly rejects unified import files

---

## Commands to Run

Execute these from the worktree root:

```bash
# Navigate to worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/020-enhanced-catalog-import/

# Run catalog import tests
pytest src/tests/test_catalog_import_service.py -v

# Run with coverage
pytest src/tests/test_catalog_import_service.py -v --cov=src/services/catalog_import_service --cov-report=term-missing

# Run full test suite (regression check)
pytest src/tests -v

# Test CLI
python -m src.utils.import_catalog --help
python -m src.utils.import_catalog test_data/sample_catalog.json --dry-run --verbose

# Time performance (SC-010)
time python -m src.utils.import_catalog test_data/baking_ingredients_v33.json --dry-run
```

---

## Output Requirements

Create your review report at:

**`docs/code-reviews/cursor-F020-review.md`**

Use this structure (following the pattern from `docs/code-reviews/cursor-F019-review.md`):

```markdown
## Code Review: Feature 020 - Enhanced Catalog Import

**Worktree reviewed**: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/020-enhanced-catalog-import/`

### Feature intent (from spec.md)
[Brief summary of what the feature is supposed to do]

---

## 1) Executive Summary: **[APPROVE/REJECT/APPROVE WITH CONCERNS]**

[Overall assessment and key findings]

---

## 2) Critical Issues (must fix before merge)

### 2.1 [Issue title]
- **File**: [path]
- **Problem**: [description]
- **Impact**: [why this matters]
- **Suggested fix**: [what to do]

[Repeat for each critical issue, or state "None found"]

---

## 3) Specification Compliance

| Success Criterion | Status | Notes |
|-------------------|--------|-------|
| SC-001 | PASS/FAIL | [details] |
| SC-002 | PASS/FAIL | [details] |
| ... | ... | ... |

---

## 4) Architecture Compliance

[Assessment of layered architecture, session management, etc.]

---

## 5) Test Coverage Analysis

- **Coverage percentage**: [X%]
- **Gaps identified**: [list any uncovered critical paths]
- **Test quality**: [assessment]

---

## 6) Code Quality Observations

### Positive
- [Good practices observed]

### Concerns
- [Areas for improvement]

---

## 7) Data Integrity & Safety

[Assessment of transactional safety, FK validation, etc.]

---

## 8) Regression Safety

[Verification that existing functionality is unchanged]

---

## 9) Questions / Clarifications

[Any ambiguities or design questions]

---

## 10) Suggested Improvements (optional, non-blocking)

- [ ] [improvement suggestion]
- [ ] [improvement suggestion]
```

---

## Review Focus Areas

Pay special attention to:

1. **Session Management**: The codebase has had bugs from nested `session_scope()` calls. Verify the `session=None` pattern is used correctly throughout.

2. **Error Messages**: User-friendliness is a core project value. Error messages should tell users what went wrong AND how to fix it.

3. **FK Validation Order**: Products reference ingredients, recipes reference both. Import must handle this dependency correctly.

4. **AUGMENT Mode Safety**: Must NEVER overwrite existing non-null values. This is critical for user data protection.

5. **Format Detection**: Must correctly distinguish catalog files from unified import files and provide clear guidance.

6. **Performance**: 160-ingredient import must complete in under 30 seconds (likely much faster).

---

## Final Notes

- Be objective and thorough
- Cite specific file paths and line numbers when identifying issues
- Distinguish between blocking issues (must fix) and suggestions (nice to have)
- If you find the implementation is solid, say so - don't manufacture issues
- Run the actual tests and commands to verify behavior
