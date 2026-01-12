---
work_package_id: "WP02"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
title: "Materials Catalog Import"
phase: "Phase 2 - Wave 1"
lane: "done"
assignee: "gemini"
agent: "gemini"
shell_pid: "13882"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2026-01-12T16:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Materials Catalog Import

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Extend `catalog_import_service.py` to import materials and material_products, matching the ingredient import pattern exactly.

**Success Criteria**:
- SC-004: Materials import creates records visible in Materials tab within 5 seconds
- SC-005: Material products slug resolution achieves 100% accuracy
- SC-013: Materials import pattern matches ingredients import exactly
- FR-009: System MUST support materials and material_products in catalog import
- FR-010: System MUST resolve material_slug references during import
- FR-011: System MUST support ADD_ONLY and AUGMENT modes
- FR-012: System MUST report created/updated/skipped/error counts

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/049-import-export-phase1/spec.md` (User Story 2)
- Plan: `kitty-specs/049-import-export-phase1/plan.md`
- Existing code: `src/services/catalog_import_service.py`

**CRITICAL: Pattern Matching (SC-013)**:
The materials import MUST follow the exact same pattern as ingredients import. Study `import_ingredients()` carefully and replicate:
- Function signature
- Mode handling (ADD_ONLY vs AUGMENT)
- Error handling
- Result reporting
- Protected vs augmentable fields

**Import Modes**:
- **ADD_ONLY**: Create new records, skip if slug exists
- **AUGMENT**: Create new records, update NULL fields on existing

**Protected Fields** (never modified):
- slug, display_name, id, date_added, category

**Augmentable Fields** (updated only if NULL):
- description, notes, other nullable fields

---

## Subtasks & Detailed Guidance

### Subtask T013 - Add `import_materials()` function

**Purpose**: Import Material records from JSON following ingredient pattern.

**Steps**:
1. Open `src/services/catalog_import_service.py`
2. Study `import_ingredients()` function thoroughly
3. Create `import_materials()` with identical structure:
```python
def import_materials(
    file_path: str,
    mode: str = "add",  # "add" or "augment"
    dry_run: bool = False
) -> ImportResult:
    """
    Import materials from JSON file.

    Args:
        file_path: Path to JSON file with materials array
        mode: "add" (ADD_ONLY) or "augment" (AUGMENT)
        dry_run: If True, validate without committing

    Returns:
        ImportResult with counts
    """
```
4. Handle JSON structure:
```json
{
  "version": "4.0",
  "materials": [
    {
      "slug": "kraft_boxes",
      "display_name": "Kraft Boxes",
      "category": "Packaging",
      "description": "...",
      "notes": "..."
    }
  ]
}
```

**Files**: `src/services/catalog_import_service.py`

### Subtask T014 - Add `import_material_products()` with slug resolution

**Purpose**: Import MaterialProduct records, resolving material_slug to parent.

**Steps**:
1. Create `import_material_products()` function
2. Resolve `material_slug` field to Material.id:
```python
def import_material_products(
    file_path: str,
    mode: str = "add",
    dry_run: bool = False
) -> ImportResult:
    # ...
    for mp_data in data.get("material_products", []):
        material_slug = mp_data.get("material_slug")
        material = session.query(Material).filter_by(slug=material_slug).first()
        if not material:
            result.add_error(
                "material_products",
                mp_data.get("brand", "unknown"),
                f"Material '{material_slug}' not found"
            )
            continue
        # Create MaterialProduct with material_id=material.id
```
3. Handle same unique constraint as products: (material_slug, brand, product_name, package_unit_quantity, package_unit)

**Files**: `src/services/catalog_import_service.py`

### Subtask T015 - Support ADD_ONLY mode for materials

**Purpose**: In ADD_ONLY mode, skip materials that already exist.

**Steps**:
1. Check if material with slug exists:
```python
existing = session.query(Material).filter_by(slug=material_data["slug"]).first()
if existing and mode == "add":
    result.add_skip("materials", material_data["slug"], "Already exists")
    continue
```
2. Only create new records
3. Report skip count in result

**Files**: `src/services/catalog_import_service.py`
**Parallel?**: Yes, with T016

### Subtask T016 - Support AUGMENT mode for materials

**Purpose**: In AUGMENT mode, update NULL fields on existing materials.

**Steps**:
1. When material exists and mode == "augment":
```python
if existing and mode == "augment":
    updated = False
    # Only update NULL fields
    if existing.description is None and material_data.get("description"):
        existing.description = material_data["description"]
        updated = True
    if existing.notes is None and material_data.get("notes"):
        existing.notes = material_data["notes"]
        updated = True
    # ... other augmentable fields

    if updated:
        result.add_success("materials")  # as updated
    else:
        result.add_skip("materials", slug, "No null fields to augment")
```
2. Never modify protected fields (slug, display_name, category, id, date_added)

**Files**: `src/services/catalog_import_service.py`
**Parallel?**: Yes, with T015

### Subtask T017 - Add validation for circular category references

**Purpose**: Prevent materials with invalid category hierarchies.

**Steps**:
1. If materials have parent/child category relationships, validate no cycles
2. Build category tree and detect cycles before committing:
```python
def validate_category_hierarchy(materials: List[dict]) -> List[str]:
    """Return list of error messages for any circular references."""
    errors = []
    # Build parent->children map
    # DFS to detect cycles
    return errors
```
3. Add errors to result if cycles detected

**Files**: `src/services/catalog_import_service.py`

### Subtask T018 - Add unit tests

**Purpose**: Comprehensive tests for materials import.

**Steps**:
1. Open `src/tests/services/test_catalog_import_service.py`
2. Add tests:
   - `test_import_materials_add_only_creates_new()`
   - `test_import_materials_add_only_skips_existing()`
   - `test_import_materials_augment_updates_null_fields()`
   - `test_import_materials_augment_preserves_protected_fields()`
   - `test_import_material_products_resolves_slug()`
   - `test_import_material_products_error_invalid_slug()`
   - `test_import_materials_circular_reference_rejected()`

**Files**: `src/tests/services/test_catalog_import_service.py`

### Subtask T019 - Verify import result counts

**Purpose**: Ensure result reports created/updated/skipped/error counts accurately.

**Steps**:
1. Test that ImportResult contains:
   - `successful` - count of created/updated records
   - `skipped` - count of skipped records
   - `failed` - count of errors
   - `entity_counts` - per-entity breakdown
2. Verify logs/warnings contain actionable information

**Files**: `src/tests/services/test_catalog_import_service.py`

---

## Test Strategy

**Unit Tests** (required):
- Test ADD_ONLY creates new, skips existing
- Test AUGMENT updates NULL fields only
- Test slug resolution for material_products
- Test error handling for invalid slugs
- Test circular reference detection

**Run Tests**:
```bash
./run-tests.sh src/tests/services/test_catalog_import_service.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Pattern mismatch with ingredients | Directly compare code structure |
| Slug resolution performance | Use bulk query for material lookup |
| Category validation complexity | Start simple, add if needed |

---

## Definition of Done Checklist

- [ ] `import_materials()` implemented matching ingredient pattern
- [ ] `import_material_products()` with slug resolution
- [ ] ADD_ONLY mode skips existing
- [ ] AUGMENT mode updates only NULL fields
- [ ] Circular reference validation (if applicable)
- [ ] All unit tests pass
- [ ] Import result counts accurate

## Review Guidance

**Reviewers should verify**:
1. Code structure mirrors `import_ingredients()` exactly
2. Protected fields are never modified in AUGMENT mode
3. Slug resolution handles missing materials gracefully
4. Error messages are actionable

---

## Activity Log

- 2026-01-12T16:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-12T17:22:55Z – gemini – lane=doing – Writing unit tests for materials import
- 2026-01-12T17:25:26Z – gemini – lane=for_review – All 26 unit tests passing for materials import
- 2026-01-12T21:50:00Z – claude – shell_pid=13882 – lane=done – Approved: All 26 tests pass. import_materials() and import_material_products() implemented. ADD/AUGMENT modes working.
