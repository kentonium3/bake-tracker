---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
title: "Supplier Service Slug Integration"
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

# Work Package Prompt: WP02 - Supplier Service Slug Integration

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: When addressing feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Integrate slug generation into supplier CRUD operations and create migration function for existing data.

**Success Criteria**:
- `create_supplier()` automatically generates slug on creation
- `migrate_supplier_slugs()` assigns slugs to all existing suppliers
- Migration regenerates ALL slugs to enforce consistency (per clarification)
- Validation rejects suppliers without slugs
- All tests pass

## Context & Constraints

**Dependencies**: WP01 must be complete (model and slug generation function exist)

**Clarification Applied**: Per session 2026-01-12, migration REGENERATES all slugs to match standard pattern, even if a supplier already has a slug.

**Session Management**: Critical - review CLAUDE.md section on session management. Pass session to all nested function calls.

---

## Subtasks & Detailed Guidance

### Subtask T007 - Update create_supplier() to generate slug

**Purpose**: Auto-generate slug when creating new suppliers.

**Steps**:
1. Open `src/services/supplier_service.py`
2. Locate `create_supplier()` function
3. Before creating the supplier object, generate the slug:
   ```python
   def create_supplier(supplier_data: dict, session: Optional[Session] = None) -> Supplier:
       """Create a new supplier with auto-generated slug."""
       def _create(data: dict, sess: Session) -> Supplier:
           # Generate slug from supplier data
           slug = generate_supplier_slug(
               name=data["name"],
               supplier_type=data.get("supplier_type", "physical"),
               city=data.get("city"),
               state=data.get("state"),
               session=sess  # Pass session for uniqueness check
           )

           supplier = Supplier(
               slug=slug,
               name=data["name"],
               supplier_type=data.get("supplier_type", "physical"),
               # ... other fields
           )
           sess.add(supplier)
           sess.flush()  # Get ID assigned
           return supplier

       if session is not None:
           return _create(supplier_data, session)

       with session_scope() as sess:
           return _create(supplier_data, sess)
   ```

**Files**: `src/services/supplier_service.py`
**Notes**: Follow existing session management pattern in the codebase

### Subtask T008 - Create migrate_supplier_slugs() function

**Purpose**: Generate slugs for all existing suppliers in the database.

**Steps**:
1. Add migration function:
   ```python
   def migrate_supplier_slugs(session: Optional[Session] = None) -> dict:
       """Generate slugs for all existing suppliers.

       Per clarification: ALL slugs are regenerated to enforce consistency,
       even if a supplier already has a slug.

       Returns:
           dict with counts: {"migrated": N, "conflicts": N}
       """
       def _migrate(sess: Session) -> dict:
           suppliers = sess.query(Supplier).all()
           migrated = 0
           conflicts = 0
           slugs_used = set()

           for supplier in suppliers:
               new_slug = generate_supplier_slug(
                   name=supplier.name,
                   supplier_type=supplier.supplier_type,
                   city=supplier.city,
                   state=supplier.state,
                   session=sess
               )

               # Track if conflict resolution was needed
               base_slug = generate_supplier_slug(
                   name=supplier.name,
                   supplier_type=supplier.supplier_type,
                   city=supplier.city,
                   state=supplier.state,
                   session=None  # No session = no uniqueness check
               )
               if new_slug != base_slug:
                   conflicts += 1

               supplier.slug = new_slug
               slugs_used.add(new_slug)
               migrated += 1

           return {"migrated": migrated, "conflicts": conflicts}

       if session is not None:
           return _migrate(session)

       with session_scope() as sess:
           return _migrate(sess)
   ```

**Files**: `src/services/supplier_service.py`
**Notes**: Regenerates ALL slugs per clarification - does NOT preserve existing

### Subtask T009 - Add validation for slug required

**Purpose**: Prevent creation of suppliers without slugs.

**Steps**:
1. In supplier service, add validation:
   ```python
   def validate_supplier(supplier_data: dict) -> list:
       """Validate supplier data before creation."""
       errors = []

       if not supplier_data.get("name"):
           errors.append("Supplier name is required")

       # Slug will be auto-generated, but if provided, validate format
       if "slug" in supplier_data:
           from ..utils.slug_utils import validate_slug_format
           if not validate_slug_format(supplier_data["slug"]):
               errors.append("Invalid slug format")

       return errors
   ```

**Files**: `src/services/supplier_service.py`

### Subtask T010 - Write tests for supplier creation with auto-slug

**Purpose**: Verify slug is generated on creation.

**Steps**:
1. Add test cases:
   ```python
   def test_create_supplier_generates_slug(self, session):
       """Creating supplier auto-generates slug."""
       supplier = create_supplier({
           "name": "Test Store",
           "supplier_type": "physical",
           "city": "Boston",
           "state": "MA"
       }, session=session)

       assert supplier.slug == "test_store_boston_ma"

   def test_create_online_supplier_generates_slug(self, session):
       """Online supplier slug uses name only."""
       supplier = create_supplier({
           "name": "Amazon Fresh",
           "supplier_type": "online"
       }, session=session)

       assert supplier.slug == "amazon_fresh"
   ```

**Files**: `src/tests/test_supplier_service.py`
**Parallel?**: Yes - can run after T007 complete

### Subtask T011 - Write tests for migration function

**Purpose**: Verify migration handles all cases correctly.

**Steps**:
1. Add migration tests:
   ```python
   def test_migration_generates_slugs_for_all(self, session):
       """Migration assigns slugs to all suppliers."""
       # Create suppliers without slugs (direct insert)
       # Run migration
       # Verify all have slugs

   def test_migration_regenerates_existing_slugs(self, session):
       """Migration regenerates even existing slugs."""
       # Create supplier with non-standard slug
       supplier = Supplier(name="Test", slug="wrong_format", ...)
       session.add(supplier)
       session.flush()

       migrate_supplier_slugs(session)

       assert supplier.slug == "test"  # Regenerated

   def test_migration_handles_conflicts(self, session):
       """Duplicate names get numeric suffixes."""
       # Create two suppliers that would have same slug
       # Run migration
       # Verify one has _1 suffix
   ```

**Files**: `src/tests/test_supplier_service.py`
**Parallel?**: Yes - can run after T008 complete

### Subtask T012 - Handle malformed slug regeneration

**Purpose**: Ensure consistency by regenerating non-standard slugs.

**Steps**:
1. This is handled by T008 - migration regenerates ALL slugs
2. Add specific test case:
   ```python
   def test_malformed_slug_regenerated(self, session):
       """Malformed slugs are corrected during migration."""
       # Insert supplier with slug "UPPERCASE_SLUG"
       # Run migration
       # Verify slug is now lowercase with proper format
   ```

**Files**: `src/tests/test_supplier_service.py`

---

## Test Strategy

**Required Tests**:
1. Auto-slug generation on create (physical and online)
2. Migration function - all suppliers get slugs
3. Migration regenerates existing slugs
4. Conflict resolution during migration
5. Malformed slug correction

**Run Tests**:
```bash
./run-tests.sh src/tests/test_supplier_service.py -v -k "supplier"
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Session detachment during migration | Silent data loss | Single session for entire migration |
| Slug conflicts create infinite loop | Hang | Counter limit (10000) in slug generation |
| Migration fails mid-way | Partial data | Use transaction - all or nothing |

---

## Definition of Done Checklist

- [ ] `create_supplier()` auto-generates slug
- [ ] `migrate_supplier_slugs()` regenerates all slugs
- [ ] Validation rejects invalid slug formats
- [ ] Tests pass for creation and migration
- [ ] Session management follows CLAUDE.md patterns
- [ ] `tasks.md` updated

---

## Review Guidance

**Key Checkpoints**:
1. Verify session is passed through all nested calls
2. Confirm migration regenerates ALL slugs (per clarification)
3. Check conflict resolution handles edge cases
4. Run full test suite: `./run-tests.sh -v`

---

## Activity Log

- 2026-01-12T23:45:00Z - system - lane=planned - Prompt created.
- 2026-01-13T05:02:48Z – claude – lane=doing – Starting implementation of existing supplier migration
- 2026-01-13T05:06:17Z – claude – lane=for_review – All subtasks complete: auto-slug on create, migration function, validation, tests all passing (60/60)
- 2026-01-13T06:21:00Z – claude – shell_pid=59105 – lane=done – APPROVED. All 10 tests pass (4 creation, 6 migration). Auto-slug generation, migration with regeneration, conflict handling verified.
