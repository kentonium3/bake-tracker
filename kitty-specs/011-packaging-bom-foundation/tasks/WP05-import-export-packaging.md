---
work_package_id: WP05
title: Import/Export Service Updates
lane: done
history:
- timestamp: '2025-12-08T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-opus-4-5
assignee: claude
phase: Phase 2 - User Stories
review_status: approved without changes
reviewed_by: claude-opus-4-5
shell_pid: review
subtasks:
- T039
- T040
- T041
- T042
- T043
- T044
- T045
- T046
---

# Work Package Prompt: WP05 - Import/Export Service Updates

## Objectives & Success Criteria

**Goal**: Update import/export to preserve all packaging data through export/import cycle.

**Success Criteria**:
- [ ] Export includes `is_packaging` field for ingredients
- [ ] Export includes `package_id` and `packaging_product_id` for compositions
- [ ] Export uses Float for `component_quantity`
- [ ] Import handles new fields with backward compatibility defaults
- [ ] Full export/import cycle preserves all packaging data
- [ ] Format version incremented to "2.0"
- [ ] Integration test passes

## Context & Constraints

**Reference Documents**:
- Contract: `kitty-specs/011-packaging-bom-foundation/contracts/import_export_service.md`
- Spec: FR-014, FR-015, FR-016, FR-017

**Dependencies**:
- WP01, WP02, WP03 must be complete

**Backward Compatibility**:
- Import: Handle missing fields with defaults (is_packaging=False, package_id=None, etc.)
- Export: No backward compatibility required per FR-017

## Subtasks & Detailed Guidance

### Subtask T039 - Update ingredient export
- **Purpose**: Include `is_packaging` field in exported ingredients
- **File**: `src/services/import_export_service.py`
- **Steps**:
  1. Find ingredient export function (e.g., `export_ingredients_to_json` or `_serialize_ingredient`)
  2. Add `is_packaging` to exported dict:
     ```python
     ingredient_data = {
         "id": ingredient.id,
         "display_name": ingredient.display_name,
         "category": ingredient.category,
         "is_packaging": ingredient.is_packaging,  # NEW
         # ... other fields
     }
     ```
- **Parallel?**: Yes - independent of composition changes

### Subtask T040 - Update ingredient import
- **Purpose**: Handle `is_packaging` field during import
- **File**: `src/services/import_export_service.py`
- **Steps**:
  1. Find ingredient import function
  2. Read `is_packaging` with default:
     ```python
     is_packaging = data.get("is_packaging", False)
     ```
  3. Pass to create_ingredient or set on model
- **Parallel?**: Yes - independent of composition changes

### Subtask T041 - Update composition export
- **Purpose**: Include `package_id` and `packaging_product_id` in exported compositions
- **File**: `src/services/import_export_service.py`
- **Steps**:
  1. Find composition export (may be part of full export or separate)
  2. Add new fields:
     ```python
     composition_data = {
         "id": comp.id,
         "assembly_id": comp.assembly_id,
         "package_id": comp.package_id,  # NEW
         "finished_unit_id": comp.finished_unit_id,
         "finished_good_id": comp.finished_good_id,
         "packaging_product_id": comp.packaging_product_id,  # NEW
         "component_quantity": float(comp.component_quantity),  # Ensure float
         "component_notes": comp.component_notes,
         "sort_order": comp.sort_order,
     }
     ```
- **Parallel?**: Yes - independent of ingredient changes

### Subtask T042 - Update composition import
- **Purpose**: Handle new fields during composition import
- **File**: `src/services/import_export_service.py`
- **Steps**:
  1. Find composition import function
  2. Read new fields with defaults:
     ```python
     package_id = data.get("package_id")  # None if missing
     packaging_product_id = data.get("packaging_product_id")  # None if missing
     ```
  3. Pass to create_composition or set on model
- **Parallel?**: Yes - independent of ingredient changes

### Subtask T043 - Handle Float quantity import
- **Purpose**: Ensure `component_quantity` converted to float
- **File**: `src/services/import_export_service.py`
- **Steps**:
  1. In composition import:
     ```python
     quantity = float(data.get("component_quantity", 1.0))
     ```
  2. Handle both int and float input values
- **Parallel?**: No - part of T042

### Subtask T044 - Add import validation
- **Purpose**: Reject invalid compositions during import
- **File**: `src/services/import_export_service.py`
- **Steps**:
  1. Add validation for parent XOR:
     ```python
     if data.get("assembly_id") and data.get("package_id"):
         raise ValidationError("Composition must have exactly one parent (assembly_id or package_id)")
     if not data.get("assembly_id") and not data.get("package_id"):
         raise ValidationError("Composition must have exactly one parent")
     ```
  2. Add validation for component XOR:
     ```python
     component_ids = [
         data.get("finished_unit_id"),
         data.get("finished_good_id"),
         data.get("packaging_product_id")
     ]
     non_null = [x for x in component_ids if x is not None]
     if len(non_null) != 1:
         raise ValidationError("Composition must have exactly one component type")
     ```
  3. Validate quantity > 0:
     ```python
     if quantity <= 0:
         raise ValidationError("Composition quantity must be greater than 0")
     ```
- **Parallel?**: No - part of T042

### Subtask T045 - Increment format_version
- **Purpose**: Indicate new export format with packaging support
- **File**: `src/services/import_export_service.py`
- **Steps**:
  1. Find metadata section of export
  2. Update format_version:
     ```python
     metadata = {
         "app_name": APP_NAME,
         "app_version": APP_VERSION,
         "export_date": datetime.utcnow().isoformat(),
         "format_version": "2.0"  # Incremented for packaging support
     }
     ```
- **Parallel?**: No - simple change

### Subtask T046 - Add integration test
- **Purpose**: Verify full export/import cycle preserves packaging data
- **File**: `src/tests/integration/test_import_export.py` or `src/tests/integration/test_packaging_flow.py`
- **Steps**:
  1. Create test data:
     - Packaging ingredient with is_packaging=True
     - Product for packaging ingredient
     - Inventory for product
     - FinishedGood with packaging composition
     - Package with packaging composition
  2. Export all data to temp file
  3. Delete database
  4. Import from temp file
  5. Verify:
     - Ingredient has is_packaging=True
     - Compositions have correct packaging_product_id
     - Compositions have correct package_id
     - Float quantities preserved
- **Example**:
  ```python
  def test_export_import_preserves_packaging():
      # Setup
      ingredient = create_ingredient("Bags", "Bags", is_packaging=True)
      product = create_product(ingredient.id, ...)
      composition = add_packaging_to_assembly(fg.id, product.id, quantity=2.5)

      # Export
      result = export_all_data("test_export.json")
      assert result.success

      # Clear and reimport
      clear_database()
      import_result = import_all_data("test_export.json")

      # Verify
      imported_ingredient = get_ingredient_by_name("Bags")
      assert imported_ingredient.is_packaging == True

      imported_compositions = get_assembly_packaging(fg.id)
      assert len(imported_compositions) == 1
      assert imported_compositions[0].component_quantity == 2.5
  ```
- **Parallel?**: No - depends on all other subtasks

## Test Strategy

**Test Commands**:
```bash
# Run import/export tests
pytest src/tests -v -k "import" -k "export"

# Run integration test
pytest src/tests/integration -v -k "packaging"
```

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data loss during format migration | Low | High | Clear error for old format; user backs up first |
| Import order issues (FKs) | Medium | Medium | Import in dependency order: ingredients -> products -> compositions |

## Definition of Done Checklist

- [ ] All 8 subtasks completed
- [ ] Ingredient export includes is_packaging
- [ ] Ingredient import handles is_packaging (default False)
- [ ] Composition export includes package_id, packaging_product_id
- [ ] Composition import handles new fields (default None)
- [ ] Float quantities handled correctly
- [ ] Import validation rejects invalid compositions
- [ ] Format version is "2.0"
- [ ] Integration test passes
- [ ] tasks.md updated

## Review Guidance

**Key Checkpoints**:
1. Export with packaging data, inspect JSON manually
2. Import into fresh database, verify data integrity
3. Try importing old format - verify graceful handling

## Activity Log

- 2025-12-08T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-08T17:28:12Z – claude – shell_pid=37652 – lane=doing – Started implementation
- 2025-12-08T17:34:19Z – claude – shell_pid=38916 – lane=for_review – All subtasks completed, 478 tests pass
- 2025-12-09T11:24:00Z – claude-opus-4-5 – shell_pid=review – lane=done – Code review: Approved. All 46 import/export tests pass. is_packaging field, packaging compositions, and float quantities preserved through export/import cycle.
- 2025-12-09T11:22:03Z – claude-opus-4-5 – shell_pid=review – lane=done – Code review: Approved - All tests pass
