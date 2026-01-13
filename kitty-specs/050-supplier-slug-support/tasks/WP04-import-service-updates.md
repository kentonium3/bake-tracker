---
work_package_id: "WP04"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
title: "Import Service Updates"
phase: "Phase 1 - Core Functionality"
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

# Work Package Prompt: WP04 - Import Service Updates

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: When addressing feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Update import to match suppliers by slug and resolve product supplier references by slug.

**Success Criteria**:
- Suppliers matched/created by slug during import
- Merge mode: update only explicitly provided fields for existing suppliers
- Skip mode: add new suppliers only
- Product import resolves `preferred_supplier_slug` to `preferred_supplier_id`
- Backward compatibility: legacy files with only `preferred_supplier_id` still work
- Warning logged for unresolved supplier slugs (import continues)
- All import tests pass

## Context & Constraints

**Dependencies**: WP01 (model), WP03 (export format finalized)

**Key Files**:
- `src/services/enhanced_import_service.py` - Main import logic
- `src/services/fk_resolver_service.py` - FK resolution helpers

**Clarification Applied**: Merge mode uses "sparse update" - only fields explicitly present in import record are updated.

**Session Management**: CRITICAL - Read CLAUDE.md on session management. This work package has high risk of session detachment issues.

---

## Subtasks & Detailed Guidance

### Subtask T018 - Update _find_existing_by_slug() for suppliers

**Purpose**: Enable finding existing suppliers by slug during import.

**Steps**:
1. Open `src/services/enhanced_import_service.py`
2. Locate `_find_existing_by_slug()` function
3. Add supplier handling:
   ```python
   def _find_existing_by_slug(
       record: Dict[str, Any],
       entity_type: str,
       session: Session
   ) -> Optional[Any]:
       if entity_type == "supplier":
           slug = record.get("slug")
           if slug:
               return session.query(Supplier).filter(
                   Supplier.slug == slug
               ).first()
           return None

       # Existing logic for other entity types...
   ```

**Files**: `src/services/enhanced_import_service.py`

### Subtask T019 - Update _resolve_fk_by_slug() for suppliers

**Purpose**: Resolve supplier references in product import.

**Steps**:
1. Locate `_resolve_fk_by_slug()` function
2. Update supplier resolution:
   ```python
   def _resolve_fk_by_slug(
       entity_type: str,
       slug_value: str,
       session: Session
   ) -> Optional[int]:
       if entity_type == "supplier":
           supplier = session.query(Supplier).filter(
               Supplier.slug == slug_value
           ).first()
           return supplier.id if supplier else None

       # Existing logic...
   ```

**Files**: `src/services/enhanced_import_service.py`

### Subtask T020 - Update fk_resolver_service.py for supplier slugs

**Purpose**: Collect supplier slugs instead of names for validation.

**Steps**:
1. Open `src/services/fk_resolver_service.py`
2. Find where existing entities are collected (likely in `_collect_existing_values()`)
3. Update supplier collection:
   ```python
   # Before (uses names):
   existing["supplier"] = {
       s.name
       for s in session.query(Supplier.name)
       .filter(Supplier.is_active == True)
       .all()
   }

   # After (uses slugs):
   existing["supplier"] = {
       s.slug
       for s in session.query(Supplier.slug)
       .filter(Supplier.is_active == True)
       .all()
   }
   ```

**Files**: `src/services/fk_resolver_service.py`

### Subtask T021 - Implement merge mode for existing suppliers

**Purpose**: Update only explicitly provided fields when supplier exists.

**Steps**:
1. In import logic for suppliers, implement sparse update:
   ```python
   def _import_supplier(record: dict, session: Session, mode: str) -> ImportResult:
       existing = _find_existing_by_slug(record, "supplier", session)

       if existing:
           if mode == "skip":
               return ImportResult(status="skipped", message="Supplier exists")

           if mode == "merge":
               # Sparse update: only update fields present in record
               for field in ["name", "supplier_type", "website_url", "city",
                             "state", "zip_code", "street_address", "notes"]:
                   if field in record:
                       setattr(existing, field, record[field])

               # NEVER update slug (immutability)
               return ImportResult(status="updated", entity=existing)

       # Create new supplier
       return _create_new_supplier(record, session)
   ```

**Files**: `src/services/enhanced_import_service.py`
**Notes**: Slug is NEVER updated even in merge mode

### Subtask T022 - Implement skip mode for supplier import

**Purpose**: Only add new suppliers, skip existing.

**Steps**:
1. Already handled in T021 logic
2. Verify skip mode returns appropriate status:
   ```python
   if existing and mode == "skip":
       return ImportResult(status="skipped", id=existing.id)
   ```

**Files**: `src/services/enhanced_import_service.py`

### Subtask T023 - Add backward compatibility for legacy files

**Purpose**: Support import files that only have `preferred_supplier_id`.

**Steps**:
1. In product import, check for slug first, then fall back to ID:
   ```python
   def _resolve_preferred_supplier(
       record: dict,
       session: Session
   ) -> Optional[int]:
       # Primary: resolve by slug
       supplier_slug = record.get("preferred_supplier_slug")
       if supplier_slug:
           supplier = session.query(Supplier).filter(
               Supplier.slug == supplier_slug
           ).first()
           if supplier:
               return supplier.id
           # Log warning - slug not found
           logger.warning(f"Supplier slug not found: {supplier_slug}")

       # Fallback: use ID directly (legacy support)
       supplier_id = record.get("preferred_supplier_id")
       if supplier_id:
           supplier = session.query(Supplier).get(supplier_id)
           if supplier:
               logger.info(f"Using legacy supplier_id fallback: {supplier_id}")
               return supplier.id
           logger.warning(f"Legacy supplier_id not found: {supplier_id}")

       return None
   ```

**Files**: `src/services/enhanced_import_service.py`

### Subtask T024 - Add warning logging for unresolved slugs

**Purpose**: Log warnings but don't fail import when supplier not found.

**Steps**:
1. Already included in T023 logic
2. Ensure logger is configured:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```
3. Warnings should include:
   - Supplier slug not found
   - Legacy ID not found
   - Product imported without supplier association

**Files**: `src/services/enhanced_import_service.py`

### Subtask T025 - Write tests for slug-based supplier import

**Purpose**: Test new, existing, merge, and skip scenarios.

**Steps**:
1. Add comprehensive import tests:
   ```python
   def test_import_new_supplier_by_slug(self, session):
       """New supplier created with provided slug."""
       result = import_suppliers([{
           "slug": "test_store_boston_ma",
           "name": "Test Store",
           "supplier_type": "physical",
           "city": "Boston",
           "state": "MA"
       }], session=session)

       assert result["created"] == 1
       supplier = session.query(Supplier).filter_by(slug="test_store_boston_ma").first()
       assert supplier is not None

   def test_import_merge_mode_updates_name(self, session):
       """Merge mode updates explicit fields."""
       # Create supplier
       original = create_supplier({...}, session=session)

       # Import with merge mode, only changing name
       result = import_suppliers([{
           "slug": original.slug,
           "name": "Updated Name"
       }], mode="merge", session=session)

       assert result["updated"] == 1
       session.refresh(original)
       assert original.name == "Updated Name"

   def test_import_skip_mode_ignores_existing(self, session):
       """Skip mode doesn't update existing."""
       original = create_supplier({...}, session=session)
       original_name = original.name

       result = import_suppliers([{
           "slug": original.slug,
           "name": "Should Not Change"
       }], mode="skip", session=session)

       assert result["skipped"] == 1
       session.refresh(original)
       assert original.name == original_name
   ```

**Files**: `src/tests/test_import_export.py`
**Parallel?**: Yes

### Subtask T026 - Write tests for product import with supplier slug

**Purpose**: Test product-supplier FK resolution.

**Steps**:
1. Add product import tests:
   ```python
   def test_import_product_resolves_supplier_slug(self, session):
       """Product import resolves supplier by slug."""
       supplier = create_supplier({...}, session=session)

       result = import_products([{
           "sku": "TEST-001",
           "display_name": "Test Product",
           "preferred_supplier_slug": supplier.slug
       }], session=session)

       product = session.query(Product).filter_by(sku="TEST-001").first()
       assert product.preferred_supplier_id == supplier.id

   def test_import_product_missing_supplier_slug_warns(self, session, caplog):
       """Missing supplier slug logs warning, doesn't fail."""
       result = import_products([{
           "sku": "TEST-002",
           "display_name": "Test Product",
           "preferred_supplier_slug": "nonexistent_slug"
       }], session=session)

       assert result["created"] == 1  # Product still created
       product = session.query(Product).filter_by(sku="TEST-002").first()
       assert product.preferred_supplier_id is None
       assert "nonexistent_slug" in caplog.text
   ```

**Files**: `src/tests/test_import_export.py`
**Parallel?**: Yes

### Subtask T027 - Write tests for legacy backward compatibility

**Purpose**: Verify old export files still import correctly.

**Steps**:
1. Add legacy file tests:
   ```python
   def test_import_product_legacy_id_fallback(self, session, caplog):
       """Legacy files with supplier_id still work."""
       supplier = create_supplier({...}, session=session)

       # Legacy format: only has ID, no slug
       result = import_products([{
           "sku": "LEGACY-001",
           "display_name": "Legacy Product",
           "preferred_supplier_id": supplier.id
           # No preferred_supplier_slug field
       }], session=session)

       product = session.query(Product).filter_by(sku="LEGACY-001").first()
       assert product.preferred_supplier_id == supplier.id
       assert "legacy" in caplog.text.lower()  # Info log about fallback
   ```

**Files**: `src/tests/test_import_export.py`
**Parallel?**: Yes

---

## Test Strategy

**Required Tests**:
1. Slug-based supplier matching (new, existing)
2. Merge mode (sparse update semantics)
3. Skip mode (no updates)
4. Product supplier resolution by slug
5. Warning on missing supplier slug
6. Legacy ID fallback

**Run Tests**:
```bash
./run-tests.sh src/tests/test_import_export.py -v -k "import"
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Session detachment in FK resolution | Silent data loss | Pass session explicitly through all calls |
| Legacy ID points to wrong supplier | Data corruption | Log warning, let user verify |
| Merge mode updates wrong fields | Data corruption | Use explicit field list, never update slug |

---

## Definition of Done Checklist

- [ ] Suppliers matched by slug during import
- [ ] Merge mode updates only explicit fields
- [ ] Skip mode doesn't modify existing
- [ ] Product import resolves supplier slug
- [ ] Backward compatibility with legacy files
- [ ] Warnings logged for unresolved slugs
- [ ] All import tests pass
- [ ] `tasks.md` updated

---

## Review Guidance

**Key Checkpoints**:
1. Verify session is passed through all nested FK resolution calls
2. Confirm merge mode uses sparse update (only explicit fields)
3. Check slug is NEVER updated (immutability preserved)
4. Verify warnings logged but import continues
5. Run: `./run-tests.sh src/tests/test_import_export.py -v`

---

## Activity Log

- 2026-01-12T23:45:00Z - system - lane=planned - Prompt created.
- 2026-01-13T05:11:42Z – claude – lane=doing – Starting import service updates
- 2026-01-13T05:22:04Z – claude – lane=for_review – All subtasks complete: T018-T027 implemented slug-based supplier import with backward compatibility for legacy files. 25/25 import tests pass, 60/60 supplier service tests pass.
- 2026-01-13T06:23:00Z – claude – shell_pid=59105 – lane=done – APPROVED. All 11 import tests pass (including Cursor review fixes: online supplier support, merge mode sparse updates). FR-009 merge mode, FR-012 legacy fallback verified.
