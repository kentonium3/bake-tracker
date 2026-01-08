---
work_package_id: WP05
title: Enhanced Import Service
lane: done
history:
- timestamp: '2025-12-25T14:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 2 - Import Services
review_status: ''
reviewed_by: ''
shell_pid: reviewed
subtasks:
- T022
- T023
- T024
- T025
- T026
- T027
- T028
- T029
---

# Work Package Prompt: WP05 - Enhanced Import Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Import denormalized views with FK resolution, merge/skip modes, dry-run, and skip-on-error.

**Success Criteria**:
1. EnhancedImportResult tracks resolutions, created/mapped counts
2. FK resolution via slug/name matching (not ID)
3. Merge mode updates existing and adds new records
4. Skip_existing mode only adds new records
5. Dry_run mode previews changes without modifying database
6. Skip-on-error mode imports valid records, logs failures
7. Unit tests achieve >70% coverage

## Context & Constraints

**Owner**: Claude (Track B - Import)

**References**:
- `kitty-specs/030-enhanced-export-import/spec.md`: FR-011 through FR-026, User Stories 2, 3, 5
- `kitty-specs/030-enhanced-export-import/data-model.md`: Import result extensions
- `src/services/catalog_import_service.py`: Pattern source
- `CLAUDE.md`: Session management warnings

**Constraints**:
- MUST use session=None pattern for transactional composition
- MUST only update editable fields from view metadata
- MUST log all errors, warnings, and resolutions per FR-026
- Duplicate slugs: first occurrence wins for entities

**Dependencies**: WP04 (FK Resolver Service)

## Subtasks & Detailed Guidance

### Subtask T022 - Create EnhancedImportResult

**Purpose**: Extend ImportResult with resolution tracking.

**Steps**:
1. Create `src/services/enhanced_import_service.py`
2. Import and extend ImportResult from import_export_service:
   ```python
   from src.services.import_export_service import ImportResult

   @dataclass
   class EnhancedImportResult:
       # Delegate to ImportResult for counts
       base_result: ImportResult = field(default_factory=ImportResult)

       # Resolution tracking
       resolutions: List[Resolution] = field(default_factory=list)
       created_entities: Dict[str, int] = field(default_factory=dict)  # {type: count}
       mapped_entities: Dict[str, int] = field(default_factory=dict)
       skipped_due_to_fk: int = 0

       # Convenience properties
       @property
       def total_records(self): return self.base_result.total_records
       # ... delegate other properties

       def get_summary(self) -> str:
           summary = self.base_result.get_summary()
           if self.resolutions:
               summary += f"\n\nFK Resolutions:"
               summary += f"\n  Created: {sum(self.created_entities.values())}"
               summary += f"\n  Mapped: {sum(self.mapped_entities.values())}"
               summary += f"\n  Skipped (FK): {self.skipped_due_to_fk}"
           return summary
   ```

**Files**: `src/services/enhanced_import_service.py`
**Parallel?**: No (foundation)

### Subtask T023 - Implement FK resolution via slug/name

**Purpose**: Resolve FK references using slug/name instead of ID.

**Steps**:
1. Implement `_resolve_fk_by_slug(entity_type: str, slug_value: str, session: Session) -> Optional[int]`:
   ```python
   def _resolve_fk_by_slug(entity_type: str, slug_value: str, session: Session) -> Optional[int]:
       if entity_type == "ingredient":
           ing = session.query(Ingredient).filter(Ingredient.slug == slug_value).first()
           return ing.id if ing else None
       elif entity_type == "supplier":
           sup = session.query(Supplier).filter(Supplier.name == slug_value).first()
           return sup.id if sup else None
       elif entity_type == "product":
           # Product uses composite key - needs ingredient_slug + brand + package info
           # This is called after ingredient resolution
           ...
   ```
2. Call this during import before attempting to use ID field
3. If slug resolution fails, add to missing_fks list for FK resolver

**Files**: `src/services/enhanced_import_service.py`
**Parallel?**: No (core logic)

### Subtask T024 - Implement merge mode

**Purpose**: Update existing records and add new ones.

**Steps**:
1. Implement merge logic in main import function:
   ```python
   def _import_record_merge(record: Dict, entity_type: str, session: Session, editable_fields: List[str]) -> str:
       """Returns: 'added', 'updated', 'skipped', or 'failed'"""
       # Find existing by slug
       existing = _find_existing_by_slug(record, entity_type, session)
       if existing:
           # Update only editable fields
           updated = False
           for field in editable_fields:
               if field in record and record[field] is not None:
                   if getattr(existing, field, None) != record[field]:
                       setattr(existing, field, record[field])
                       updated = True
           return 'updated' if updated else 'skipped'
       else:
           # Create new record
           return _create_new_record(record, entity_type, session)
   ```
2. Only update fields listed in editable_fields from view metadata
3. Skip if no changes needed

**Files**: `src/services/enhanced_import_service.py`
**Parallel?**: Yes (mode handler)

### Subtask T025 - Implement skip_existing mode

**Purpose**: Only add new records, never update existing.

**Steps**:
1. Implement skip_existing logic:
   ```python
   def _import_record_skip_existing(record: Dict, entity_type: str, session: Session) -> str:
       """Returns: 'added' or 'skipped'"""
       existing = _find_existing_by_slug(record, entity_type, session)
       if existing:
           return 'skipped'
       else:
           return _create_new_record(record, entity_type, session)
   ```
2. Simpler than merge - no field comparison needed

**Files**: `src/services/enhanced_import_service.py`
**Parallel?**: Yes (mode handler)

### Subtask T026 - Implement dry_run mode

**Purpose**: Preview changes without modifying database.

**Steps**:
1. Add dry_run parameter to main import function:
   ```python
   def import_view(file_path: str, mode: str = "merge", dry_run: bool = False, ...) -> EnhancedImportResult:
       with session_scope() as session:
           result = _import_view_impl(file_path, mode, session, ...)
           if dry_run:
               session.rollback()
               result.dry_run = True
           return result
   ```
2. Process all records normally to generate counts
3. Rollback at end instead of commit

**Files**: `src/services/enhanced_import_service.py`
**Parallel?**: Yes (mode handler)

### Subtask T027 - Implement skip-on-error mode

**Purpose**: Import valid records, log failures for later.

**Steps**:
1. Add skip_on_error parameter:
   ```python
   def import_view(file_path: str, mode: str = "merge", skip_on_error: bool = False, ...) -> EnhancedImportResult:
   ```
2. When FK error occurs and skip_on_error=True:
   - Log to skipped_records list
   - Continue with next record
   - At end, write `import_skipped_{timestamp}.json`
3. Log format:
   ```python
   skipped_record = {
       "record_index": idx,
       "skip_reason": "fk_missing",
       "fk_entity": "supplier",
       "fk_value": "Wilson's Farm",
       "original_record": record
   }
   ```

**Files**: `src/services/enhanced_import_service.py`
**Parallel?**: Yes (mode handler)

### Subtask T028 - Integrate FK resolver

**Purpose**: Connect to FK resolver for missing reference handling.

**Steps**:
1. Add resolver parameter to import function:
   ```python
   def import_view(
       file_path: str,
       mode: str = "merge",
       resolver: Optional[FKResolverCallback] = None,
       ...
   ) -> EnhancedImportResult:
   ```
2. Before processing records:
   - Scan for missing FKs
   - If resolver provided and missing_fks found:
     - Call resolve_missing_fks(missing_fks, resolver, session)
     - Apply resolutions to create mapping
   - If no resolver and missing_fks found:
     - Fail with clear error listing all missing references
3. During record processing:
   - Use FK mapping to resolve references

**Files**: `src/services/enhanced_import_service.py`
**Parallel?**: No (integration)

### Subtask T029 - Write unit tests

**Purpose**: Verify enhanced import functionality.

**Steps**:
1. Create `src/tests/services/test_enhanced_import.py`
2. Test cases:
   - Merge mode updates editable fields only
   - Merge mode adds new records
   - Skip_existing mode skips existing records
   - Dry_run mode makes no DB changes
   - Skip-on-error imports valid records, logs failures
   - FK resolution via slug works
   - FK resolver integration with mock callback
   - Duplicate slug handling (first wins)
3. Use test fixtures with known data

**Files**: `src/tests/services/test_enhanced_import.py`
**Parallel?**: No (after implementation)

## Test Strategy

- Unit tests for each mode
- Mock FK resolver callback
- Verify only editable fields updated
- Verify dry_run makes no changes

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Follow session=None pattern strictly |
| Product ambiguity | Warn on multiple matches, skip |
| Partial failures | Atomic transactions per session_scope |

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] EnhancedImportResult tracks all resolution data
- [ ] FK resolution via slug/name works
- [ ] Merge mode updates only editable fields
- [ ] Skip_existing mode works
- [ ] Dry_run mode makes no changes
- [ ] Skip-on-error logs failures correctly
- [ ] FK resolver integration works
- [ ] >70% test coverage on service
- [ ] tasks.md updated with status change

## Review Guidance

- Verify session=None pattern used throughout
- Verify only editable_fields from metadata are updated
- Verify skip-on-error log format per spec
- Verify FK resolution uses slug, not ID

## Activity Log

- 2025-12-25T14:00:00Z - system - lane=planned - Prompt created.
- 2025-12-26T02:37:29Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-26T02:44:18Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-26T03:37:13Z – system – shell_pid= – lane=done – Code review passed: All 46 tests pass, session=None pattern correct, all import modes work
