---
work_package_id: "WP05"
subtasks:
  - "T028"
  - "T029"
  - "T030"
  - "T031"
title: "Slug Immutability & Validation"
phase: "Phase 2 - Data Integrity"
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

# Work Package Prompt: WP05 - Slug Immutability & Validation

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: When addressing feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Prevent slug modification after creation to preserve data integrity and ensure existing exports remain valid.

**Success Criteria**:
- Attempting to modify slug via service layer raises error
- Updating supplier name/location does NOT change slug
- Clear error message explains why slug cannot be changed
- Tests verify immutability enforcement

## Context & Constraints

**Dependencies**: WP02 must be complete (supplier service integration)

**User Story Reference**: User Story 4 - Slug Immutability Prevents Reference Breakage (Priority: P2)

**Rationale**: Once a slug is assigned, it may be referenced in export files. If the slug changes, those references become invalid. Immutability ensures data portability over time.

---

## Subtasks & Detailed Guidance

### Subtask T028 - Reject slug changes in update_supplier()

**Purpose**: Prevent modification of slug field through service layer.

**Steps**:
1. Open `src/services/supplier_service.py`
2. Locate `update_supplier()` function (or equivalent)
3. Add slug immutability check:
   ```python
   def update_supplier(
       supplier_id: int,
       update_data: dict,
       session: Optional[Session] = None
   ) -> Supplier:
       """Update supplier. Slug is immutable and cannot be changed.

       Args:
           supplier_id: ID of supplier to update
           update_data: Fields to update (slug changes rejected)
           session: Optional database session

       Returns:
           Updated Supplier object

       Raises:
           ValueError: If attempting to modify slug
       """
       def _update(sid: int, data: dict, sess: Session) -> Supplier:
           supplier = sess.query(Supplier).get(sid)
           if not supplier:
               raise ValueError(f"Supplier not found: {sid}")

           # Check for slug modification attempt
           if "slug" in data:
               new_slug = data["slug"]
               if new_slug != supplier.slug:
                   raise ValueError(
                       f"Slug cannot be modified after creation. "
                       f"Current: '{supplier.slug}', Attempted: '{new_slug}'. "
                       f"Slugs are immutable to preserve data portability."
                   )
               # Remove slug from update data (even if same value)
               data = {k: v for k, v in data.items() if k != "slug"}

           # Apply other updates
           for field, value in data.items():
               if hasattr(supplier, field):
                   setattr(supplier, field, value)

           return supplier

       if session is not None:
           return _update(supplier_id, update_data, session)

       with session_scope() as sess:
           return _update(supplier_id, update_data, sess)
   ```

**Files**: `src/services/supplier_service.py`

### Subtask T029 - Ensure slug preserved on name/location change

**Purpose**: Verify that changing supplier details doesn't regenerate slug.

**Steps**:
1. The implementation in T028 already handles this by:
   - Not regenerating slug during updates
   - Only allowing other fields to be modified
2. Add explicit documentation in service:
   ```python
   # Note: Slug is generated once at creation and NEVER regenerated,
   # even if name/city/state changes. This preserves data portability.
   ```
3. Ensure update path does NOT call `generate_supplier_slug()`

**Files**: `src/services/supplier_service.py`
**Notes**: This is implicit in T028 but worth explicit verification

### Subtask T030 - Add appropriate error message

**Purpose**: Provide clear guidance when slug modification is attempted.

**Steps**:
1. Already implemented in T028 with message:
   ```
   "Slug cannot be modified after creation. Current: 'X', Attempted: 'Y'.
   Slugs are immutable to preserve data portability."
   ```
2. Consider adding to validation layer as well:
   ```python
   def validate_supplier_update(existing: Supplier, update_data: dict) -> list:
       errors = []

       if "slug" in update_data and update_data["slug"] != existing.slug:
           errors.append(
               "slug: Cannot be modified. Slugs are immutable identifiers."
           )

       return errors
   ```

**Files**: `src/services/supplier_service.py`

### Subtask T031 - Write tests for immutability enforcement

**Purpose**: Verify slug cannot be changed through service layer.

**Steps**:
1. Add immutability tests:
   ```python
   def test_update_supplier_rejects_slug_change(self, session):
       """Attempting to change slug raises error."""
       supplier = create_supplier({
           "name": "Original Store",
           "supplier_type": "physical",
           "city": "Boston",
           "state": "MA"
       }, session=session)

       original_slug = supplier.slug

       with pytest.raises(ValueError) as exc_info:
           update_supplier(
               supplier.id,
               {"slug": "different_slug"},
               session=session
           )

       assert "cannot be modified" in str(exc_info.value).lower()
       session.refresh(supplier)
       assert supplier.slug == original_slug

   def test_update_supplier_name_preserves_slug(self, session):
       """Changing name doesn't change slug."""
       supplier = create_supplier({
           "name": "Original Store",
           "supplier_type": "physical",
           "city": "Boston",
           "state": "MA"
       }, session=session)

       original_slug = supplier.slug

       update_supplier(
           supplier.id,
           {"name": "New Store Name"},
           session=session
       )

       session.refresh(supplier)
       assert supplier.name == "New Store Name"
       assert supplier.slug == original_slug  # Unchanged!

   def test_update_supplier_location_preserves_slug(self, session):
       """Changing location doesn't change slug."""
       supplier = create_supplier({
           "name": "Test Store",
           "supplier_type": "physical",
           "city": "Boston",
           "state": "MA"
       }, session=session)

       original_slug = supplier.slug  # test_store_boston_ma

       update_supplier(
           supplier.id,
           {"city": "Cambridge", "state": "MA"},
           session=session
       )

       session.refresh(supplier)
       assert supplier.city == "Cambridge"
       assert supplier.slug == original_slug  # Still test_store_boston_ma!

   def test_update_supplier_same_slug_allowed(self, session):
       """Passing same slug value is allowed (no-op)."""
       supplier = create_supplier({...}, session=session)

       # This should NOT raise an error
       update_supplier(
           supplier.id,
           {"slug": supplier.slug, "name": "Updated Name"},
           session=session
       )

       session.refresh(supplier)
       assert supplier.name == "Updated Name"
   ```

**Files**: `src/tests/test_supplier_service.py`
**Parallel?**: Yes - can run after T028-T030 complete

---

## Test Strategy

**Required Tests**:
1. Reject slug modification with clear error
2. Name change preserves slug
3. Location change preserves slug
4. Same slug value is allowed (no-op)
5. Error message is descriptive

**Run Tests**:
```bash
./run-tests.sh src/tests/test_supplier_service.py -v -k "immutab"
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Admin needs to fix typo in slug | Data stuck with typo | Out of scope; document as limitation |
| Import merge mode tries to update slug | Silent failure | T021 already excludes slug from updates |

---

## Definition of Done Checklist

- [ ] `update_supplier()` rejects slug changes with ValueError
- [ ] Error message explains immutability rationale
- [ ] Name/location changes preserve original slug
- [ ] Same slug value passes without error
- [ ] Tests verify all immutability scenarios
- [ ] `tasks.md` updated

---

## Review Guidance

**Key Checkpoints**:
1. Verify ValueError raised with descriptive message
2. Confirm slug preserved when name/location changes
3. Check import merge mode (WP04) respects immutability
4. Run: `./run-tests.sh src/tests/test_supplier_service.py -v`

---

## Activity Log

- 2026-01-12T23:45:00Z - system - lane=planned - Prompt created.
- 2026-01-13T05:28:26Z – claude – lane=doing – Starting slug immutability and validation implementation
- 2026-01-13T05:30:28Z – claude – lane=for_review – All subtasks complete: T028-T031 implemented slug immutability with clear error messages. 65/65 supplier service tests pass.
- 2026-01-13T06:24:00Z – claude – shell_pid=59105 – lane=done – APPROVED. All 5 immutability tests pass. FR-005 slug immutability enforcement verified with clear error messages.
