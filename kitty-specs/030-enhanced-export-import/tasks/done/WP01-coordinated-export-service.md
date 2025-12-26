---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Coordinated Export Service"
phase: "Phase 1 - Export Services"
lane: "done"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-25T14:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Coordinated Export Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Export complete database to individual entity files with manifest, checksums, and dependency ordering.

**Success Criteria**:
1. Each entity type exports to its own JSON file (suppliers.json, ingredients.json, etc.)
2. Manifest.json contains SHA256 checksums for all files
3. Manifest includes import_order field respecting FK dependencies
4. FK fields include both ID and slug/name for portable resolution
5. ZIP archive option creates compressed export
6. Unit tests achieve >70% coverage

## Context & Constraints

**Owner**: Gemini (Track A - Export)

**References**:
- `kitty-specs/030-enhanced-export-import/spec.md`: FR-001 through FR-005
- `kitty-specs/030-enhanced-export-import/data-model.md`: Manifest and entity file schemas
- `kitty-specs/030-enhanced-export-import/research.md`: Session patterns and existing service analysis
- `src/services/catalog_import_service.py`: Pattern source for session=None

**Constraints**:
- MUST use session=None pattern with _impl functions
- MUST follow existing service patterns in codebase
- Entity order: suppliers → ingredients → products → recipes → purchases → inventory

## Subtasks & Detailed Guidance

### Subtask T001 - Create ExportManifest and FileEntry dataclasses

**Purpose**: Define data structures for manifest metadata.

**Steps**:
1. Create `src/services/coordinated_export_service.py`
2. Add imports: `dataclasses`, `datetime`, `hashlib`, `json`, `pathlib`, `typing`, `zipfile`
3. Define `FileEntry` dataclass:
   ```python
   @dataclass
   class FileEntry:
       filename: str
       entity_type: str
       record_count: int
       sha256: str
       dependencies: List[str]
       import_order: int
   ```
4. Define `ExportManifest` dataclass:
   ```python
   @dataclass
   class ExportManifest:
       version: str = "1.0"
       export_date: str = ""
       source: str = ""
       files: List[FileEntry] = field(default_factory=list)
   ```

**Files**: `src/services/coordinated_export_service.py`
**Parallel?**: No (foundation for other subtasks)

### Subtask T002 - Implement per-entity export functions with FK resolution fields

**Purpose**: Export each entity type with both ID and slug/name for FK fields.

**Steps**:
1. Implement `_export_suppliers(output_dir, session)` - returns FileEntry
2. Implement `_export_ingredients(output_dir, session)` - returns FileEntry
3. Implement `_export_products(output_dir, session)` - include ingredient_id AND ingredient_slug
4. Implement `_export_recipes(output_dir, session)` - returns FileEntry
5. Implement `_export_purchases(output_dir, session)` - include product_id/product_slug, supplier_id/supplier_name
6. Implement `_export_inventory_items(output_dir, session)` - include product_id/product_slug

**Example Product Export**:
```python
def _export_products(output_dir: Path, session: Session) -> FileEntry:
    products = session.query(Product).options(joinedload(Product.ingredient)).all()
    records = []
    for p in products:
        records.append({
            "id": p.id,
            "ingredient_id": p.ingredient_id,
            "ingredient_slug": p.ingredient.slug if p.ingredient else None,
            "brand": p.brand,
            # ... other fields
        })
    # Write to file, calculate checksum
    ...
```

**Files**: `src/services/coordinated_export_service.py`
**Parallel?**: Yes (each entity export is independent once dataclasses exist)

### Subtask T003 - Implement manifest generation with SHA256 checksums

**Purpose**: Generate manifest.json with checksums for validation.

**Steps**:
1. After exporting each entity file, calculate SHA256:
   ```python
   def _calculate_checksum(file_path: Path) -> str:
       with open(file_path, 'rb') as f:
           return hashlib.sha256(f.read()).hexdigest()
   ```
2. Populate FileEntry with checksum
3. Generate manifest.json with all FileEntry objects
4. Include version, export_date, source (APP_NAME + APP_VERSION)

**Files**: `src/services/coordinated_export_service.py`
**Parallel?**: No (depends on T002)

### Subtask T004 - Implement dependency ordering logic

**Purpose**: Ensure import_order respects FK dependencies.

**Steps**:
1. Define DEPENDENCY_ORDER constant:
   ```python
   DEPENDENCY_ORDER = {
       "suppliers": (1, []),
       "ingredients": (2, []),
       "products": (3, ["ingredients"]),
       "recipes": (4, ["ingredients"]),
       "purchases": (5, ["products", "suppliers"]),
       "inventory_items": (6, ["products"]),
   }
   ```
2. Set import_order and dependencies fields in each FileEntry
3. Sort manifest.files by import_order before writing

**Files**: `src/services/coordinated_export_service.py`
**Parallel?**: No (logic integration)

### Subtask T005 - Implement ZIP archive creation

**Purpose**: Support --zip flag for compressed exports.

**Steps**:
1. Add `create_zip` parameter to main export function
2. Use `zipfile.ZipFile` to compress output directory:
   ```python
   if create_zip:
       zip_path = output_dir.with_suffix('.zip')
       with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
           for file in output_dir.iterdir():
               zf.write(file, file.name)
       return zip_path
   ```
3. Return path to created ZIP or directory

**Files**: `src/services/coordinated_export_service.py`
**Parallel?**: No (final step)

### Subtask T006 - Write unit tests

**Purpose**: Verify export functionality with >70% coverage.

**Steps**:
1. Create `src/tests/services/test_coordinated_export.py`
2. Test cases:
   - Export empty database (should create files with 0 records)
   - Export with sample data (verify record counts)
   - Verify checksums match file contents
   - Verify import_order is correct
   - Verify FK resolution fields present
   - Test ZIP creation
3. Use fixtures from existing test patterns

**Files**: `src/tests/services/test_coordinated_export.py`
**Parallel?**: No (after implementation)

## Test Strategy

- Unit tests for each export function
- Integration test: export → verify manifest → verify checksums
- Fixture: Use test database with known data counts

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large exports OOM | Defer streaming to post-MVP; test with 1k records |
| Session patterns | Follow catalog_import_service.py patterns exactly |

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] `export_complete()` function creates directory with entity files and manifest
- [ ] Checksums verified via automated test
- [ ] Dependency order verified via automated test
- [ ] ZIP option tested
- [ ] >70% test coverage on service
- [ ] tasks.md updated with status change

## Review Guidance

- Verify session=None pattern used throughout
- Verify FK fields include both ID and slug/name
- Verify checksums are SHA256 hex strings
- Verify import_order respects dependencies

## Activity Log

- 2025-12-25T14:00:00Z - system - lane=planned - Prompt created.
- 2025-12-26T03:47:50Z – system – shell_pid= – lane=done – Implementation complete by Gemini CLI, reviewed and tests pass (commit 2ccc5d1)
