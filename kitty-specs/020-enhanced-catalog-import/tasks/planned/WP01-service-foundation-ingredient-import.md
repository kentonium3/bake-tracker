---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Service Foundation - Result Class & Ingredient Import"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Service Foundation - Result Class & Ingredient Import

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Create the foundation for catalog import - the `CatalogImportResult` class and `import_ingredients()` function with ADD_ONLY mode.

**Success Criteria**:
- `src/services/catalog_import_service.py` exists with proper structure
- `CatalogImportResult` class tracks counts per entity type (added/skipped/failed)
- `import_ingredients()` creates new ingredients and skips existing slugs
- Unit tests pass with >70% coverage on new code
- Pattern matches existing `import_export_service.py` conventions

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/020-enhanced-catalog-import/spec.md` - FR-001, FR-003, FR-009
- `kitty-specs/020-enhanced-catalog-import/research.md` - Result class pattern
- `kitty-specs/020-enhanced-catalog-import/data-model.md` - CatalogImportResult spec
- `src/services/import_export_service.py` - ImportResult pattern to follow
- `CLAUDE.md` - Session management rules (CRITICAL)

**Architectural Constraints**:
1. Module-level functions (not class-based service)
2. Optional `session=None` parameter for transactional composition
3. Ingredient unique key: `slug`
4. Follow existing `ImportResult` pattern for consistency

---

## Subtasks & Detailed Guidance

### T001 - Create catalog_import_service.py with module structure

**Purpose**: Establish the service file with proper imports and docstring.

**Steps**:
1. Create `src/services/catalog_import_service.py`
2. Add module docstring explaining purpose
3. Add imports:
   - `json`, `typing` (Dict, List, Optional)
   - `datetime`
   - `sqlalchemy.orm` (Session)
   - `src.services.database` (session_scope)
   - `src.models.ingredient` (Ingredient)

**Files**: `src/services/catalog_import_service.py`

**Template**:
```python
"""
Catalog Import Service - Entity-specific import for ingredients, products, and recipes.

Provides ADD_ONLY and AUGMENT modes for safe catalog expansion without
affecting transactional user data.
"""

import json
from typing import Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.services.database import session_scope
from src.models.ingredient import Ingredient
```

---

### T002 - Implement CatalogImportResult class

**Purpose**: Create result tracking class matching ImportResult pattern.

**Steps**:
1. Define `CatalogImportResult` class with attributes:
   - `entity_counts: Dict[str, Dict[str, int]]` - {"ingredients": {"added": 0, "skipped": 0, "failed": 0, "augmented": 0}}
   - `errors: List[Dict]` - Structured error records
   - `warnings: List[str]` - Warning messages
   - `dry_run: bool` - Whether this was a preview
   - `mode: str` - "add" or "augment"
2. Add methods:
   - `add_success(entity_type: str)` - Increment added count
   - `add_skip(entity_type: str, identifier: str, reason: str)` - Increment skipped, add warning
   - `add_error(entity_type: str, identifier: str, error_type: str, message: str, suggestion: str)` - Increment failed, add error
   - `add_augment(entity_type: str, identifier: str, fields: List[str])` - Increment augmented
   - `get_summary() -> str` - User-friendly summary for CLI/UI
   - `has_errors -> bool` - Property to check if any failures
3. Initialize entity_counts for all types in `__init__`

**Files**: `src/services/catalog_import_service.py`

**Reference**: See `ImportResult` in `src/services/import_export_service.py` lines 41-166

---

### T003 - Implement import_ingredients() with ADD_ONLY mode

**Purpose**: Create the ingredient import function that creates new and skips existing.

**Steps**:
1. Define function signature:
   ```python
   def import_ingredients(
       data: List[Dict],
       mode: str = "add",
       dry_run: bool = False,
       session: Optional[Session] = None
   ) -> CatalogImportResult:
   ```
2. Implement session handling pattern:
   ```python
   if session is not None:
       return _import_ingredients_impl(data, mode, dry_run, session)
   with session_scope() as session:
       return _import_ingredients_impl(data, mode, dry_run, session)
   ```
3. In `_import_ingredients_impl`:
   - Create `CatalogImportResult`
   - Query existing slugs: `existing_slugs = {i.slug for i in session.query(Ingredient.slug).all()}`
   - For each ingredient in data:
     - Extract required fields: slug, display_name, category
     - If slug exists: `result.add_skip("ingredients", slug, "Already exists")`
     - Else: Create `Ingredient`, add to session, `result.add_success("ingredients")`
   - If not dry_run: commit implicitly (session_scope handles)
   - If dry_run: session.rollback() before return

**Files**: `src/services/catalog_import_service.py`

**Field Mapping** (from data-model.md):
- Required: `slug`, `display_name`, `category`
- Optional: `description`, `is_packaging`, all density_* fields, allergens, foodon_id, etc.

---

### T004 - Implement inline validation for ingredients

**Purpose**: Validate ingredient data before creation.

**Steps**:
1. Add validation in `_import_ingredients_impl`:
   - Check required fields present: `slug`, `display_name`, `category`
   - Validate slug format (non-empty string)
   - Validate category non-empty
2. On validation failure:
   ```python
   result.add_error(
       "ingredients",
       slug or "unknown",
       "validation",
       "Missing required field: category",
       "Add 'category' field to ingredient data"
   )
   ```
3. Continue processing other ingredients (partial success)

**Files**: `src/services/catalog_import_service.py`

---

### T005 - Create test file structure

**Purpose**: Establish test file with fixtures for ingredient import testing.

**Steps**:
1. Create `src/tests/test_catalog_import_service.py`
2. Add imports and fixtures:
   ```python
   import pytest
   from src.services import catalog_import_service
   from src.services.database import session_scope
   from src.models.ingredient import Ingredient
   ```
3. Create helper fixture for test ingredient data
4. Create fixture to clean up test data after each test

**Files**: `src/tests/test_catalog_import_service.py`

---

### T006 - Test: test_import_ingredients_add_mode [P]

**Purpose**: Verify new ingredients are created correctly.

**Steps**:
1. Create test data with 3 new ingredients
2. Call `import_ingredients(data)`
3. Assert result.entity_counts["ingredients"]["added"] == 3
4. Query database to verify ingredients exist with correct fields

**Files**: `src/tests/test_catalog_import_service.py`

**Parallel**: Yes - independent test case

---

### T007 - Test: test_import_ingredients_skip_existing [P]

**Purpose**: Verify existing slugs are skipped.

**Steps**:
1. Pre-create an ingredient with slug "existing_flour"
2. Create test data including "existing_flour" and 2 new ingredients
3. Call `import_ingredients(data)`
4. Assert added == 2, skipped == 1
5. Verify "existing_flour" unchanged in database

**Files**: `src/tests/test_catalog_import_service.py`

**Parallel**: Yes - independent test case

---

## Test Strategy

**Required Tests**:
- `test_import_ingredients_add_mode` - Happy path, all new ingredients
- `test_import_ingredients_skip_existing` - Skip existing slugs
- Both tests must pass before WP01 is complete

**Test Commands**:
```bash
pytest src/tests/test_catalog_import_service.py -v
pytest src/tests/test_catalog_import_service.py -v --cov=src/services/catalog_import_service
```

**Coverage Target**: >70% on `catalog_import_service.py`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Follow `session=None` pattern exactly as in CLAUDE.md |
| Field mapping errors | Use explicit field assignment, not **kwargs |
| Dry-run commits data | Verify session.rollback() called before return |

---

## Definition of Done Checklist

- [ ] T001: `catalog_import_service.py` created with imports
- [ ] T002: `CatalogImportResult` class implemented with all methods
- [ ] T003: `import_ingredients()` function with ADD_ONLY mode
- [ ] T004: Validation logic for required fields
- [ ] T005: Test file created with fixtures
- [ ] T006: `test_import_ingredients_add_mode` passes
- [ ] T007: `test_import_ingredients_skip_existing` passes
- [ ] All tests pass: `pytest src/tests/test_catalog_import_service.py -v`
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

**Reviewer Checkpoints**:
1. Verify `CatalogImportResult` matches pattern from `ImportResult`
2. Verify session handling uses `session=None` pattern correctly
3. Verify dry_run calls rollback, not commit
4. Verify test coverage meets 70% threshold
5. Verify ingredient fields map correctly per data-model.md

---

## Activity Log

- 2025-12-14T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
