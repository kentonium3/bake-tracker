---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Model & Slug Generation Foundation"
phase: "Phase 0 - Foundation"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "59105"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2026-01-12T23:45:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Model & Slug Generation Foundation

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Add slug field to Supplier model and create the slug generation function that will be used throughout the feature.

**Success Criteria**:
- Supplier model has `slug` field (String(100), unique, indexed, non-nullable)
- `generate_supplier_slug()` function creates slugs following the pattern:
  - Physical suppliers: `{name}_{city}_{state}` normalized
  - Online suppliers: `{name}` only
- Slug generation uses Unicode normalization (NFD) from existing `slug_utils.py`
- Conflict resolution appends `_1`, `_2`, `_3` suffixes
- All unit tests pass

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md` (Section VII endorses slug-based FKs)
- Plan: `kitty-specs/050-supplier-slug-support/plan.md`
- Research: `kitty-specs/050-supplier-slug-support/research.md` (existing slug patterns)
- Data Model: `kitty-specs/050-supplier-slug-support/data-model.md` (schema details)

**Architectural Constraints**:
- Follow existing `create_slug()` pattern from `src/utils/slug_utils.py`
- Session management: pass session parameter for uniqueness checking
- Avoid circular imports when generalizing slug utility

**Key Code References**:
- `src/utils/slug_utils.py:30-143` - Existing slug generation
- `src/models/supplier.py` - Current Supplier model
- `src/models/ingredient.py` - Example of model with slug field

---

## Subtasks & Detailed Guidance

### Subtask T001 - Add slug field to Supplier model

**Purpose**: Add the slug column to the Supplier database table.

**Steps**:
1. Open `src/models/supplier.py`
2. Add the slug field after the `name` field:
   ```python
   slug = Column(String(100), nullable=False, unique=True, index=True)
   ```
3. The field must be:
   - `String(100)` - sufficient for `name_city_state` + conflict suffix
   - `nullable=False` - all suppliers must have slugs
   - `unique=True` - slugs are identifiers
   - `index=True` - fast lookups during import

**Files**: `src/models/supplier.py`
**Parallel?**: No - must complete before T003

### Subtask T002 - Add unique index to __table_args__

**Purpose**: Ensure slug uniqueness is enforced at database level.

**Steps**:
1. In `src/models/supplier.py`, locate `__table_args__` tuple
2. Add the index:
   ```python
   Index("idx_supplier_slug", "slug", unique=True),
   ```
3. Place it alongside existing indexes

**Files**: `src/models/supplier.py`
**Parallel?**: No - part of model changes

### Subtask T003 - Create generate_supplier_slug() function

**Purpose**: Generate slugs based on supplier type (physical vs online).

**Steps**:
1. In `src/services/supplier_service.py`, add function:
   ```python
   def generate_supplier_slug(
       name: str,
       supplier_type: str,
       city: Optional[str] = None,
       state: Optional[str] = None,
       session: Optional[Session] = None
   ) -> str:
       """Generate slug for supplier based on type.

       Physical suppliers: {name}_{city}_{state}
       Online suppliers: {name} only

       Uses Unicode normalization and conflict resolution.
       """
       if supplier_type == "online":
           input_string = name
       else:
           # Physical supplier: include location
           parts = [name]
           if city:
               parts.append(city)
           if state:
               parts.append(state)
           input_string = " ".join(parts)

       return create_slug_for_model(input_string, Supplier, session)
   ```
2. Import the generalized slug utility (see T004)

**Files**: `src/services/supplier_service.py`
**Parallel?**: No - depends on T001, T002, T004
**Notes**: Must handle None city/state gracefully for online suppliers

### Subtask T004 - Generalize create_slug() in slug_utils.py

**Purpose**: Make the slug utility work with any model, not just Ingredient.

**Steps**:
1. Open `src/utils/slug_utils.py`
2. Add a new function that accepts model class:
   ```python
   def create_slug_for_model(
       name: str,
       model_class: type,
       session: Optional[Session] = None
   ) -> str:
       """Generate unique slug for any model.

       Args:
           name: String to convert to slug
           model_class: SQLAlchemy model class with 'slug' attribute
           session: Optional session for uniqueness checking

       Returns:
           Unique slug string
       """
       # Same algorithm as create_slug()
       normalized = unicodedata.normalize("NFD", name)
       slug = normalized.encode("ascii", "ignore").decode("ascii")
       slug = slug.lower()
       slug = re.sub(r"[\s\-]+", "_", slug)
       slug = re.sub(r"[^a-z0-9_]", "", slug)
       slug = re.sub(r"_+", "_", slug)
       slug = slug.strip("_")

       if session is None:
           return slug

       # Uniqueness check with model_class
       existing = session.query(model_class).filter(
           model_class.slug == slug
       ).first()

       if not existing:
           return slug

       # Conflict resolution
       original_slug = slug
       counter = 1
       while True:
           candidate_slug = f"{original_slug}_{counter}"
           existing = session.query(model_class).filter(
               model_class.slug == candidate_slug
           ).first()
           if not existing:
               return candidate_slug
           counter += 1
           if counter > 10000:
               raise ValueError(f"Unable to generate unique slug after 10000 attempts")
   ```
3. Keep the original `create_slug()` function for backward compatibility (it can call `create_slug_for_model` internally)

**Files**: `src/utils/slug_utils.py`
**Parallel?**: Yes - can proceed while T001/T002 are in progress
**Notes**: This approach avoids circular imports by accepting model class as parameter

### Subtask T005 - Write unit tests for slug generation

**Purpose**: Validate slug generation covers all cases.

**Steps**:
1. Create or update `src/tests/test_supplier_service.py`
2. Add test cases:
   ```python
   class TestSupplierSlugGeneration:
       def test_physical_supplier_slug(self):
           """Physical supplier: name + city + state"""
           slug = generate_supplier_slug(
               name="Wegmans",
               supplier_type="physical",
               city="Burlington",
               state="MA"
           )
           assert slug == "wegmans_burlington_ma"

       def test_online_supplier_slug(self):
           """Online supplier: name only"""
           slug = generate_supplier_slug(
               name="King Arthur Baking",
               supplier_type="online"
           )
           assert slug == "king_arthur_baking"

       def test_slug_unicode_normalization(self):
           """Accented characters removed"""
           slug = generate_supplier_slug(
               name="Cafe Crme",
               supplier_type="online"
           )
           assert slug == "cafe_creme"

       def test_slug_special_characters_removed(self):
           """Special chars removed, spaces to underscores"""
           slug = generate_supplier_slug(
               name="Bob's Market & Deli",
               supplier_type="physical",
               city="New York",
               state="NY"
           )
           assert slug == "bobs_market_deli_new_york_ny"

       def test_slug_conflict_resolution(self, session):
           """Duplicate slugs get numeric suffix"""
           # Create first supplier
           # Create second with same details
           # Verify suffix _1 added
   ```

**Files**: `src/tests/test_supplier_service.py`
**Parallel?**: Yes - can proceed alongside T004

### Subtask T006 - Update to_dict() method

**Purpose**: Include slug in model serialization.

**Steps**:
1. In `src/models/supplier.py`, the `to_dict()` method calls `super().to_dict()`
2. Verify that `slug` is included in serialization (should be automatic from base class)
3. If not automatic, explicitly add:
   ```python
   result["slug"] = self.slug
   ```

**Files**: `src/models/supplier.py`
**Parallel?**: No - depends on T001

---

## Test Strategy

**Required Tests** (per TDD principle):
1. Unit tests for `generate_supplier_slug()` - physical vs online
2. Unit tests for Unicode normalization edge cases
3. Unit tests for conflict resolution with session
4. Unit tests for `create_slug_for_model()` utility

**Test Location**: `src/tests/test_supplier_service.py`

**Run Tests**:
```bash
./run-tests.sh src/tests/test_supplier_service.py -v
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular import when importing Supplier in slug_utils | Build failure | Accept model class as parameter instead of importing |
| Existing slug_utils tests break | Test failure | Keep original `create_slug()` for backward compatibility |
| Slug conflict counter differs from spec | Confusion | Clarified: use existing `_1` pattern per research.md |

---

## Definition of Done Checklist

- [ ] Supplier model has slug field (String(100), unique, indexed, non-nullable)
- [ ] `generate_supplier_slug()` function implemented in supplier_service.py
- [ ] `create_slug_for_model()` utility added to slug_utils.py
- [ ] Unit tests written and passing for all slug generation cases
- [ ] `to_dict()` includes slug field
- [ ] No circular import issues
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

**Key Checkpoints**:
1. Verify slug field definition matches data-model.md spec
2. Verify slug generation algorithm matches research.md findings
3. Confirm conflict resolution uses `_1`, `_2` pattern (not `_2`, `_3`)
4. Check session is properly passed for uniqueness checking
5. Run tests: `./run-tests.sh src/tests/test_supplier_service.py -v`

---

## Activity Log

- 2026-01-12T23:45:00Z - system - lane=planned - Prompt created.
- 2026-01-13T04:46:49Z – claude – lane=doing – Started implementation
- 2026-01-13T05:01:23Z – claude – lane=for_review – All subtasks complete. Core slug generation implemented: model field, unique index, generate_supplier_slug(), create_slug_for_model(), unit tests passing.
- 2026-01-13T06:19:00Z – claude – shell_pid=59105 – lane=done – APPROVED. All DoD items verified: slug field correct (String(100), unique, indexed, non-nullable), generate_supplier_slug() and create_slug_for_model() implemented, 13 unit tests passing, to_dict() includes slug automatically via base class.
