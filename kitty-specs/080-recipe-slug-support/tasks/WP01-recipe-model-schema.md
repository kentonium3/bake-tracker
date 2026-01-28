---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Recipe Model Schema Changes"
phase: "Phase 0 - Foundation"
lane: "doing"
assignee: ""
agent: "claude-code"
shell_pid: "56589"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-28T07:45:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Recipe Model Schema Changes

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# No dependencies - start from main
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

**Objective**: Add `slug` and `previous_slug` columns to the Recipe model with proper indexing and auto-generation on insert.

**Success Criteria**:
- [ ] Recipe model has `slug` column (String(200), unique, indexed, non-nullable)
- [ ] Recipe model has `previous_slug` column (String(200), nullable, indexed)
- [ ] Unique index exists on `slug` column
- [ ] Event listener auto-generates slug on insert when not provided
- [ ] Slug format validated (lowercase, hyphens, alphanumeric only)
- [ ] Existing tests pass after schema changes

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/080-recipe-slug-support/spec.md`
- Plan: `kitty-specs/080-recipe-slug-support/plan.md`
- Research: `kitty-specs/080-recipe-slug-support/research.md`
- Data Model: `kitty-specs/080-recipe-slug-support/data-model.md`

**Pattern Sources (COPY EXACTLY)**:
- Slug column: `src/models/supplier.py:82-83`
- Event listener: `src/models/supplier.py:183-189`
- Slug generation: `src/services/finished_unit_service.py:629-652`

**Constraints**:
- Schema uses reset/re-import cycle (no migration scripts per Constitution VI)
- Slug format: lowercase, hyphens for spaces, alphanumeric-and-hyphens only
- Max length: 200 characters
- Must not break existing Recipe functionality

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add `slug` Column to Recipe Model

**Purpose**: Create the primary portable identifier field for recipes.

**Steps**:
1. Open `src/models/recipe.py`
2. Add the slug column after existing columns (near `name` field):
   ```python
   slug = Column(
       String(200),
       nullable=False,
       unique=True,
       index=True,
       comment="Unique human-readable identifier for export/import portability"
   )
   ```
3. Ensure import of `String` from SQLAlchemy is present

**Files**:
- `src/models/recipe.py` (modify)

**Pattern Reference**: Copy from `src/models/supplier.py:82-83`:
```python
slug = Column(String(100), nullable=False, unique=True, index=True)
```

**Notes**:
- Use 200 chars (not 100 like Supplier) to match Product/Ingredient
- nullable=False enforces data integrity
- unique=True prevents collision at DB level
- index=True enables fast lookups

---

### Subtask T002 – Add `previous_slug` Column to Recipe Model

**Purpose**: Enable one-rename grace period for import compatibility.

**Steps**:
1. In `src/models/recipe.py`, add after the `slug` column:
   ```python
   previous_slug = Column(
       String(200),
       nullable=True,
       index=True,
       comment="Previous slug retained after rename for import compatibility"
   )
   ```

**Files**:
- `src/models/recipe.py` (modify)

**Notes**:
- nullable=True because not all recipes have been renamed
- index=True for fast fallback resolution during import
- No unique constraint (old slugs may match across renames)

---

### Subtask T003 – Add Unique Index for Slug Column

**Purpose**: Ensure database-level enforcement of slug uniqueness.

**Steps**:
1. In `src/models/recipe.py`, locate the `__table_args__` tuple (or create if missing)
2. Add index definition:
   ```python
   __table_args__ = (
       # Existing indexes...
       Index("idx_recipe_slug", "slug", unique=True),
       Index("idx_recipe_previous_slug", "previous_slug"),
   )
   ```

**Files**:
- `src/models/recipe.py` (modify)

**Pattern Reference**: Check existing index patterns in `src/models/supplier.py`

**Notes**:
- The unique constraint on the column already creates an index, but explicit naming helps debugging
- previous_slug index is NOT unique (same old slug could exist if recipe renamed multiple times, though we only keep most recent)

---

### Subtask T004 – Add Event Listener for Slug Auto-Generation

**Purpose**: Automatically generate slug when recipe is created without one provided.

**Steps**:
1. At the top of `src/models/recipe.py`, add import:
   ```python
   from sqlalchemy import event
   ```

2. At module level (after the Recipe class definition), add:
   ```python
   @event.listens_for(Recipe, "before_insert")
   def generate_recipe_slug_on_insert(mapper, connection, target):
       """Auto-generate slug before insert if not provided."""
       if not target.slug:
           # Import here to avoid circular dependency
           from src.services.recipe_service import RecipeService
           target.slug = RecipeService._generate_slug(target.name)
   ```

**Files**:
- `src/models/recipe.py` (modify)

**Pattern Reference**: `src/models/supplier.py:183-189`

**Notes**:
- Use lazy import inside function to avoid circular dependency
- Only generates if slug is None/empty (allows explicit slug setting)
- This handles basic auto-generation; unique collision handling done in service layer

**Edge Cases**:
- If RecipeService not yet implemented (WP02), temporarily use a simple inline slug generator:
  ```python
  import re
  if not target.slug:
      slug = re.sub(r'[^\w\s-]', '', target.name.lower())
      slug = re.sub(r'[\s_]+', '-', slug).strip('-')
      target.slug = slug or 'recipe'
  ```
  Replace with RecipeService call after WP02.

---

### Subtask T005 – Add Model-Level Validation for Slug Format

**Purpose**: Ensure slugs conform to expected format before database save.

**Steps**:
1. Add a validation method to the Recipe class:
   ```python
   from sqlalchemy.orm import validates

   class Recipe(BaseModel):
       # ... columns ...

       @validates('slug')
       def validate_slug(self, key, value):
           """Validate slug format."""
           if value is None:
               return value  # Allow None during construction, event listener will populate

           # Check format: lowercase, alphanumeric, hyphens only
           import re
           if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', value):
               # Auto-normalize if invalid
               normalized = re.sub(r'[^\w\s-]', '', value.lower())
               normalized = re.sub(r'[\s_]+', '-', normalized).strip('-')
               return normalized or 'recipe'

           # Check length
           if len(value) > 200:
               return value[:200].rstrip('-')

           return value
   ```

**Files**:
- `src/models/recipe.py` (modify)

**Notes**:
- Use SQLAlchemy's `@validates` decorator for attribute validation
- Auto-normalize invalid slugs rather than raising errors (defensive approach)
- Truncate to 200 chars if too long

---

## Test Strategy

**Tests to verify** (run after implementation):
```bash
# Run existing recipe tests to ensure no regression
./run-tests.sh src/tests/test_recipe*.py -v

# Quick manual verification
python -c "
from src.models.recipe import Recipe
r = Recipe(name='Test Slug Recipe')
print(f'Slug column exists: {hasattr(Recipe, \"slug\")}')
print(f'Previous slug column exists: {hasattr(Recipe, \"previous_slug\")}')
"
```

**No new test files required for WP01** - unit tests for slug generation added in WP02.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular import with RecipeService | Use lazy import inside event listener function |
| Existing recipes have no slug | Import process will generate slugs (WP04) |
| Breaking existing tests | Run test suite after each change; schema changes are additive |

---

## Definition of Done Checklist

- [ ] T001: `slug` column added to Recipe model
- [ ] T002: `previous_slug` column added to Recipe model
- [ ] T003: Indexes created for both columns
- [ ] T004: Event listener auto-generates slug on insert
- [ ] T005: Slug validation normalizes invalid formats
- [ ] All existing recipe tests pass
- [ ] Code follows project patterns (check with `flake8 src/models/recipe.py`)

---

## Review Guidance

**Reviewers should verify**:
1. Column definitions match specification (types, constraints, indexes)
2. Event listener follows Supplier pattern
3. No circular imports introduced
4. Existing functionality unaffected (run `./run-tests.sh src/tests/ -v`)

---

## Activity Log

- 2026-01-28T07:45:00Z – system – lane=planned – Prompt created.
- 2026-01-28T16:35:52Z – claude-opus – shell_pid=45860 – lane=doing – Started implementation via workflow command
- 2026-01-28T16:50:12Z – claude-opus – shell_pid=45860 – lane=for_review – Ready for review: Added slug and previous_slug columns to Recipe model with auto-generation and validation
- 2026-01-28T17:28:26Z – claude-code – shell_pid=56589 – lane=doing – Started review via workflow command
