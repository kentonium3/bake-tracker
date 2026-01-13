---
work_package_id: "WP06"
subtasks:
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
title: "Dry-Run, Test Data & Polish"
phase: "Phase 3 - Polish"
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

# Work Package Prompt: WP06 - Dry-Run, Test Data & Polish

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: When addressing feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Add dry-run import preview capability and update test data files with slug field.

**Success Criteria**:
- `dry_run=True` parameter returns preview without DB changes
- Preview includes counts: new, existing, errors
- Test data files include slug field for all suppliers
- Round-trip test validates complete feature

## Context & Constraints

**Dependencies**: WP01-WP04 must be complete (core functionality)

**User Story Reference**: User Story 5 - Dry-Run Import Preview (Priority: P3)

**Test Data Files**:
- `test_data/suppliers.json`
- `test_data/sample_data_all.json` (if contains suppliers)

---

## Subtasks & Detailed Guidance

### Subtask T032 - Add dry_run parameter to supplier import

**Purpose**: Allow users to preview import without committing changes.

**Steps**:
1. Update supplier import function signature:
   ```python
   def import_suppliers(
       suppliers_data: List[dict],
       mode: str = "merge",
       dry_run: bool = False,
       session: Optional[Session] = None
   ) -> dict:
       """Import suppliers with optional dry-run preview.

       Args:
           suppliers_data: List of supplier records
           mode: "merge" or "skip"
           dry_run: If True, return preview without DB changes
           session: Optional database session

       Returns:
           dict with counts and optional preview details
       """
   ```

**Files**: `src/services/enhanced_import_service.py` or `src/services/import_export_service.py`

### Subtask T033 - Return preview stats in dry-run mode

**Purpose**: Provide actionable preview information.

**Steps**:
1. Implement preview logic:
   ```python
   def import_suppliers(..., dry_run: bool = False, ...) -> dict:
       preview = {
           "new": 0,
           "existing": 0,
           "to_update": 0,
           "errors": 0,
           "details": []
       }

       for record in suppliers_data:
           slug = record.get("slug")
           existing = _find_existing_by_slug(record, "supplier", session) if slug else None

           if existing:
               if mode == "merge":
                   preview["to_update"] += 1
                   preview["details"].append({
                       "slug": slug,
                       "action": "update",
                       "fields": list(record.keys())
                   })
               else:  # skip
                   preview["existing"] += 1
                   preview["details"].append({
                       "slug": slug,
                       "action": "skip"
                   })
           else:
               preview["new"] += 1
               preview["details"].append({
                   "slug": record.get("slug") or "(auto-generated)",
                   "action": "create",
                   "name": record.get("name")
               })

       if dry_run:
           return preview

       # Proceed with actual import...
   ```

**Files**: `src/services/enhanced_import_service.py`

### Subtask T034 - Ensure no DB changes in dry-run mode

**Purpose**: Guarantee dry-run is truly read-only.

**Steps**:
1. Two implementation approaches:

   **Option A**: Early return (simpler)
   ```python
   if dry_run:
       # Calculate preview without any DB modifications
       return preview
   ```

   **Option B**: Transaction rollback (more accurate preview)
   ```python
   if dry_run:
       # Use nested transaction that we roll back
       with session.begin_nested() as savepoint:
           result = _do_import(suppliers_data, mode, session)
           savepoint.rollback()
           return result
   ```

2. Recommendation: Use Option A for simplicity
3. Add explicit check that no objects are pending:
   ```python
   if dry_run:
       assert len(session.new) == 0, "Dry run should not create objects"
       assert len(session.dirty) == 0, "Dry run should not modify objects"
       return preview
   ```

**Files**: `src/services/enhanced_import_service.py`

### Subtask T035 - Update test_data/suppliers.json

**Purpose**: Add slug field to all test suppliers.

**Steps**:
1. Read current `test_data/suppliers.json`
2. Add slug field to each supplier using the generation algorithm:
   ```json
   {
     "suppliers": [
       {
         "name": "Costco",
         "slug": "costco_waltham_ma",
         "supplier_type": "physical",
         "city": "Waltham",
         "state": "MA",
         "zip_code": "02451"
       },
       {
         "name": "King Arthur Baking",
         "slug": "king_arthur_baking",
         "supplier_type": "online",
         "website_url": "https://shop.kingarthurbaking.com"
       },
       {
         "name": "Wegmans",
         "slug": "wegmans_burlington_ma",
         "supplier_type": "physical",
         "city": "Burlington",
         "state": "MA"
       }
       // ... etc
     ]
   }
   ```

**Files**: `test_data/suppliers.json`
**Parallel?**: Yes - independent of dry-run implementation

### Subtask T036 - Update sample_data_all.json if needed

**Purpose**: Ensure complete test data set includes slugs.

**Steps**:
1. Check if `test_data/sample_data_all.json` exists and contains suppliers
2. If yes, add slug field to suppliers section
3. Verify products in file have `preferred_supplier_slug` field added

**Files**: `test_data/sample_data_all.json`
**Parallel?**: Yes

### Subtask T037 - Write tests for dry-run mode

**Purpose**: Verify dry-run returns accurate preview without changes.

**Steps**:
1. Add dry-run tests:
   ```python
   def test_dry_run_returns_preview_counts(self, session):
       """Dry run returns accurate counts."""
       existing = create_supplier({...}, session=session)

       result = import_suppliers([
           {"slug": existing.slug, "name": "Updated"},  # Existing
           {"name": "New Store", "supplier_type": "physical", "city": "X", "state": "MA"}  # New
       ], mode="merge", dry_run=True, session=session)

       assert result["new"] == 1
       assert result["to_update"] == 1

   def test_dry_run_no_db_changes(self, session):
       """Dry run doesn't modify database."""
       initial_count = session.query(Supplier).count()

       import_suppliers([
           {"name": "New Store", "supplier_type": "online"}
       ], dry_run=True, session=session)

       assert session.query(Supplier).count() == initial_count

   def test_dry_run_skip_mode_counts(self, session):
       """Dry run with skip mode shows skipped count."""
       existing = create_supplier({...}, session=session)

       result = import_suppliers([
           {"slug": existing.slug, "name": "Updated"}
       ], mode="skip", dry_run=True, session=session)

       assert result["existing"] == 1
       assert result["to_update"] == 0
   ```

**Files**: `src/tests/test_import_export.py`
**Parallel?**: Yes

### Subtask T038 - Round-trip integration test

**Purpose**: Validate complete feature end-to-end.

**Steps**:
1. Add comprehensive round-trip test:
   ```python
   def test_full_round_trip_with_slugs(self, session, tmp_path):
       """Export -> fresh DB -> import -> verify associations."""
       # Setup: create suppliers and products with associations
       supplier = create_supplier({
           "name": "Test Store",
           "supplier_type": "physical",
           "city": "Boston",
           "state": "MA"
       }, session=session)

       product = create_product({
           "sku": "TEST-001",
           "display_name": "Test Product",
           "preferred_supplier_id": supplier.id
       }, session=session)

       # Export all data
       export_data = export_all_data(session)

       # Verify export has slugs
       supplier_export = export_data["suppliers"][0]
       assert supplier_export["slug"] == "test_store_boston_ma"

       product_export = export_data["products"][0]
       assert product_export["preferred_supplier_slug"] == "test_store_boston_ma"

       # Clear database (simulate fresh environment)
       session.query(Product).delete()
       session.query(Supplier).delete()
       session.commit()

       # Import back
       import_all_data(export_data, session)

       # Verify associations restored
       imported_supplier = session.query(Supplier).filter_by(
           slug="test_store_boston_ma"
       ).first()
       assert imported_supplier is not None

       imported_product = session.query(Product).filter_by(
           sku="TEST-001"
       ).first()
       assert imported_product.preferred_supplier_id == imported_supplier.id
   ```

**Files**: `src/tests/test_import_export.py`
**Parallel?**: Yes

---

## Test Strategy

**Required Tests**:
1. Dry-run returns accurate preview counts
2. Dry-run makes no database changes
3. Dry-run works with both merge and skip modes
4. Test data files load successfully
5. Round-trip maintains all associations

**Run Tests**:
```bash
./run-tests.sh src/tests/test_import_export.py -v
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Dry-run complexity | Implementation bugs | Use simple early-return approach |
| Test data out of sync | Test failures | Generate slugs using same algorithm |
| Round-trip timing | Flaky tests | Use explicit session management |

---

## Definition of Done Checklist

- [ ] Dry-run parameter added to import function
- [ ] Preview returns new/existing/error counts
- [ ] No DB changes occur in dry-run mode
- [ ] `test_data/suppliers.json` has slug field
- [ ] `test_data/sample_data_all.json` updated (if applicable)
- [ ] Dry-run tests pass
- [ ] Round-trip integration test passes
- [ ] `tasks.md` updated

---

## Review Guidance

**Key Checkpoints**:
1. Verify dry-run truly makes no DB changes
2. Check preview counts are accurate
3. Verify test data slugs match generation algorithm
4. Run full test suite: `./run-tests.sh -v`

---

## Activity Log

- 2026-01-12T23:45:00Z - system - lane=planned - Prompt created.
- 2026-01-13T05:31:23Z – claude – lane=doing – Starting dry-run, test data, and polish implementation
- 2026-01-13T05:37:09Z – claude – lane=for_review – All subtasks complete: T032-T038 implemented dry-run import preview and updated test data files. 29/29 integration tests pass.
- 2026-01-13T06:25:00Z – claude – shell_pid=59105 – lane=done – APPROVED. All 4 tests pass (3 dry-run, 1 round-trip). FR-014 dry-run preview, test data updates, round-trip slug preservation verified.
