---
work_package_id: WP06
title: Export/Import Updates
lane: "for_review"
dependencies: [WP03]
base_branch: 084-material-unit-schema-refactor-WP03
base_commit: 8175cc9090e816bdaae4a24c51e036817c6199a0
created_at: '2026-01-30T18:02:17.872122+00:00'
subtasks:
- T027
- T028
- T029
- T030
- T031
phase: Wave 3 - Export/Import & UI
assignee: ''
agent: ''
shell_pid: "34519"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-30T17:11:03Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – Export/Import Updates

## Implementation Command

```bash
spec-kitty implement WP06 --base WP03
```

Depends on WP03 (MaterialUnit service must handle material_product_id).

---

## Objectives & Success Criteria

**Goal**: Update export/import to use material_product_slug for MaterialUnits.

**Success Criteria**:
- [ ] MaterialUnit export includes material_product_slug (not material_slug)
- [ ] MaterialUnit import resolves material_product_slug to material_product_id
- [ ] Composition export does not include material_id
- [ ] Composition import skips records with material_id (logs skipped)
- [ ] Export→Import round-trip preserves 100% of MaterialUnit relationships
- [ ] Service tests pass

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/084-material-unit-schema-refactor/spec.md` (FR-015 to FR-017)
- Plan: `kitty-specs/084-material-unit-schema-refactor/plan.md`
- Research: `kitty-specs/084-material-unit-schema-refactor/research.md`

**Key Pattern** (from research.md):
```python
# Export: Use slug string
export_data["material_units"].append({
    "material_product_slug": unit.material_product.slug,  # FK via slug
    "name": unit.name,
    "slug": unit.slug,
    ...
})

# Import: Resolve slug to ID
product_lookup = {row.slug: row.id for row in session.query(MaterialProduct).all()}
material_product_id = product_lookup.get(item["material_product_slug"])
if material_product_id is None:
    result.add_error(..., f"MaterialProduct '{item['material_product_slug']}' not found")
```

**Import Modes**:
- ADD_ONLY: Skip existing records
- AUGMENT: Update null fields in existing records

---

## Subtasks & Detailed Guidance

### Subtask T027 – Update MaterialUnit Export

**Purpose**: Export MaterialUnits with material_product_slug reference.

**Files**: `src/services/import_export_service.py`

**Steps**:
1. Locate MaterialUnit export section (search for "material_units" in export function)

2. Update the export mapping:
   ```python
   # Find and update the MaterialUnit export
   material_units = session.query(MaterialUnit).options(
       joinedload(MaterialUnit.material_product)  # Changed from material
   ).all()

   for unit in material_units:
       export_data["material_units"].append({
           "uuid": str(unit.uuid) if unit.uuid else None,
           "material_product_slug": unit.material_product.slug if unit.material_product else None,  # Changed
           "name": unit.name,
           "slug": unit.slug,
           "quantity_per_unit": unit.quantity_per_unit,
           "description": unit.description,
       })
   ```

3. Remove any material_slug export:
   ```python
   # REMOVE:
   # "material_slug": unit.material.slug if unit.material else None,
   ```

4. Update joinedload to use new relationship

**Validation**:
- [ ] Export includes material_product_slug
- [ ] Export does NOT include material_slug
- [ ] Joinedload uses material_product relationship

---

### Subtask T028 – Update MaterialUnit Import

**Purpose**: Import MaterialUnits by resolving material_product_slug.

**Files**: `src/services/catalog_import_service.py`

**Steps**:
1. Locate MaterialUnit import function (_import_material_units_impl or similar)

2. Update the lookup to use MaterialProduct:
   ```python
   def _import_material_units_impl(
       data: List[Dict],
       mode: str,
       dry_run: bool,
       session: Session,
   ) -> CatalogImportResult:
       result = CatalogImportResult()
       result.dry_run = dry_run
       result.mode = mode

       # Build lookups - CHANGED to MaterialProduct
       product_lookup = {
           row.slug: row.id
           for row in session.query(MaterialProduct).all()
       }
       existing_slugs = {row.slug: row for row in session.query(MaterialUnit).all()}

       for item in data:
           # ... validation code ...

           # Changed: Use material_product_slug instead of material_slug
           material_product_slug = item.get("material_product_slug", "")
           if not material_product_slug:
               result.add_error(
                   "material_units", identifier, "validation",
                   "Missing required field: material_product_slug",
                   item,
               )
               continue

           # Resolve FK
           material_product_id = product_lookup.get(material_product_slug)
           if material_product_id is None:
               result.add_error(
                   "material_units", identifier, "fk_missing",
                   f"MaterialProduct '{material_product_slug}' not found",
                   item,
               )
               continue

           # Create unit with new FK
           unit = MaterialUnit(
               material_product_id=material_product_id,  # Changed
               name=name,
               slug=slug,
               quantity_per_unit=quantity_per_unit,
               description=item.get("description"),
           )
           ...
   ```

3. Handle backward compatibility for old exports (optional):
   ```python
   # If material_product_slug not present, check for material_slug
   material_product_slug = item.get("material_product_slug")
   if not material_product_slug:
       # Old format - skip with warning
       old_slug = item.get("material_slug", "")
       if old_slug:
           result.add_error(
               "material_units", identifier, "migration_required",
               f"Old format detected (material_slug='{old_slug}'). "
               f"Run migration script to convert to material_product_slug.",
               item,
           )
           continue
   ```

**Validation**:
- [ ] Import uses material_product_slug field
- [ ] Lookup resolves MaterialProduct slugs
- [ ] Creates MaterialUnit with material_product_id
- [ ] Clear error for missing material_product_slug

---

### Subtask T029 – Update Composition Export

**Purpose**: Remove material_id from Composition export.

**Files**: `src/services/import_export_service.py`

**Steps**:
1. Locate Composition export section

2. Remove material_id/material_slug from export:
   ```python
   for comp in compositions:
       export_data["compositions"].append({
           "assembly_slug": comp.assembly.slug if comp.assembly else None,
           "finished_unit_slug": comp.finished_unit.slug if comp.finished_unit else None,
           "finished_good_slug": comp.finished_good.slug if comp.finished_good else None,
           "packaging_product_slug": comp.packaging_product.slug if comp.packaging_product else None,
           "material_unit_slug": comp.material_unit.slug if comp.material_unit else None,
           # REMOVE: "material_slug": comp.material_component.slug if comp.material_component else None,
           "quantity": comp.quantity,
           "notes": comp.notes,
           "sort_order": comp.sort_order,
       })
   ```

3. Remove any joinedload for material_component:
   ```python
   # Update query options if needed
   compositions = session.query(Composition).options(
       joinedload(Composition.assembly),
       joinedload(Composition.finished_unit),
       joinedload(Composition.finished_good),
       joinedload(Composition.packaging_product),
       joinedload(Composition.material_unit),
       # REMOVE: joinedload(Composition.material_component),
   ).all()
   ```

**Validation**:
- [ ] Export does NOT include material_slug or material_id
- [ ] material_unit_slug still exported correctly
- [ ] No joinedload for material_component

---

### Subtask T030 – Update Composition Import to Skip material_id Records

**Purpose**: Skip Compositions with material_id and log for manual fix.

**Files**: `src/services/catalog_import_service.py`

**Steps**:
1. Locate Composition import function

2. Add check to skip material_slug records:
   ```python
   def _import_compositions_impl(
       data: List[Dict],
       mode: str,
       dry_run: bool,
       session: Session,
   ) -> CatalogImportResult:
       ...
       for item in data:
           # Check for deprecated material_slug
           material_slug = item.get("material_slug")
           if material_slug:
               result.add_skip(
                   "compositions",
                   identifier,
                   f"Skipped: material_slug='{material_slug}' is deprecated. "
                   f"User must manually convert to material_unit_slug.",
               )
               continue

           # Proceed with normal import for valid compositions
           ...
   ```

3. Ensure skip is logged clearly:
   ```python
   # Log format should be clear for user:
   # SKIPPED: Composition in 'Holiday Box A' with material_slug='red-ribbon'
   #   Reason: material_slug is deprecated
   #   Action: Edit export file to use material_unit_slug instead
   ```

4. Count skipped records in result summary

**Validation**:
- [ ] Records with material_slug are skipped (not error)
- [ ] Skip message is clear and actionable
- [ ] Skipped count included in result summary
- [ ] Records without material_slug import normally

---

### Subtask T031 – Add Export/Import Tests

**Purpose**: Test round-trip with new FK references.

**Files**: `src/tests/test_import_export_service.py`

**Steps**:
1. Add test for MaterialUnit export:
   ```python
   def test_export_material_units_includes_product_slug(session, material_unit, material_product):
       """Export should include material_product_slug."""
       material_unit.material_product_id = material_product.id
       session.flush()

       data = export_all_data(session=session)

       assert "material_units" in data
       unit_data = data["material_units"][0]
       assert "material_product_slug" in unit_data
       assert unit_data["material_product_slug"] == material_product.slug
       assert "material_slug" not in unit_data
   ```

2. Add test for MaterialUnit import:
   ```python
   def test_import_material_units_resolves_product_slug(session, material_product):
       """Import should resolve material_product_slug to ID."""
       data = {
           "material_units": [{
               "material_product_slug": material_product.slug,
               "name": "Test Unit",
               "slug": "test-unit",
               "quantity_per_unit": 1.0,
           }]
       }

       result = import_catalog_data(data, mode="add_only", session=session)

       assert result.success_count("material_units") == 1
       unit = session.query(MaterialUnit).filter_by(slug="test-unit").first()
       assert unit.material_product_id == material_product.id
   ```

3. Add test for invalid product slug:
   ```python
   def test_import_material_unit_invalid_product_slug(session):
       """Import should error for invalid material_product_slug."""
       data = {
           "material_units": [{
               "material_product_slug": "nonexistent-product",
               "name": "Test Unit",
               "slug": "test-unit",
               "quantity_per_unit": 1.0,
           }]
       }

       result = import_catalog_data(data, mode="add_only", session=session)

       assert result.error_count("material_units") == 1
       assert "not found" in result.errors[0]["message"]
   ```

4. Add test for Composition with material_slug skip:
   ```python
   def test_import_composition_skips_material_slug(session, assembly):
       """Import should skip compositions with deprecated material_slug."""
       data = {
           "compositions": [{
               "assembly_slug": assembly.slug,
               "material_slug": "some-material",  # Deprecated
               "quantity": 1,
           }]
       }

       result = import_catalog_data(data, mode="add_only", session=session)

       assert result.skip_count("compositions") == 1
       assert "deprecated" in result.skips[0]["reason"].lower()
   ```

5. Add round-trip test:
   ```python
   def test_material_unit_roundtrip(session, material_unit):
       """Export→Import should preserve MaterialUnit relationships."""
       # Export
       data = export_all_data(session=session)

       # Clear and re-import
       session.query(MaterialUnit).delete()
       session.flush()

       result = import_catalog_data(data, mode="add_only", session=session)

       assert result.success_count("material_units") >= 1
       reimported = session.query(MaterialUnit).filter_by(slug=material_unit.slug).first()
       assert reimported.material_product_id == material_unit.material_product_id
   ```

6. Run tests:
   ```bash
   ./run-tests.sh src/tests/test_import_export_service.py -v
   ```

**Validation**:
- [ ] Export test verifies material_product_slug presence
- [ ] Import test verifies slug resolution
- [ ] Error test verifies missing slug handling
- [ ] Skip test verifies material_slug handling
- [ ] Round-trip test verifies data integrity

---

## Test Strategy

**Required Tests**:
1. MaterialUnit export includes material_product_slug
2. MaterialUnit import resolves material_product_slug
3. Invalid material_product_slug produces clear error
4. Composition with material_slug is skipped with log
5. Round-trip preserves all relationships

**Test Commands**:
```bash
./run-tests.sh src/tests/test_import_export_service.py -v --cov=src/services
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing exports | Migration script (WP09) transforms old format |
| User confusion about skipped records | Clear, actionable skip messages |
| Missing FK references | Clear error messages with slug that failed |

---

## Definition of Done Checklist

- [ ] MaterialUnit export uses material_product_slug
- [ ] MaterialUnit import resolves material_product_slug
- [ ] Composition export excludes material_id/material_slug
- [ ] Composition import skips material_slug records with log
- [ ] Round-trip test passes
- [ ] All tests pass
- [ ] No linting errors

---

## Review Guidance

**Key Checkpoints**:
1. Verify no remaining material_slug references in export
2. Verify clear error messages for import failures
3. Verify skip messages are actionable
4. Run round-trip test to confirm data integrity

---

## Activity Log

- 2026-01-30T17:11:03Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-30T18:14:45Z – unknown – shell_pid=34519 – lane=for_review – All subtasks complete, 10 tests added, 143 tests passing
