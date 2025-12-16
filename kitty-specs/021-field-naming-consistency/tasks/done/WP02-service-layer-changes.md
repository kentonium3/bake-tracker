---
work_package_id: "WP02"
subtasks:
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
title: "Service Layer Changes"
phase: "Phase 2 - Core Logic"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "83880"
review_status: "approved without changes"
reviewed_by: "claude-reviewer"
history:
  - timestamp: "2025-12-15T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: "automated"
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Service Layer Changes

## Objectives & Success Criteria

- Update all service files to use `package_unit` and `package_unit_quantity` instead of `purchase_unit` and `purchase_quantity`
- **Success**: `grep -rn "purchase_unit\|purchase_quantity" src/services/` returns zero matches

## Context & Constraints

### Prerequisites
- WP01 (Model Layer Changes) must be completed first.

### Related Documents
- Spec: `kitty-specs/021-field-naming-consistency/spec.md` (FR-004, FR-017, FR-018)
- Research: `kitty-specs/021-field-naming-consistency/research.md` (lines affected in import_export_service.py)

### Constraints
- Update field references only; do not change business logic.
- In import_export_service.py, ensure JSON field names match model attributes exactly (no aliasing).

## Subtasks & Detailed Guidance

### Subtask T004 - Update product_service.py

**Purpose**: Update field references in the product service.

**Steps**:
1. Open `src/services/product_service.py`
2. Find all occurrences of `purchase_unit` and `purchase_quantity`
3. Replace with `package_unit` and `package_unit_quantity`
4. Update any variable names that were named after these fields

**Files**: `src/services/product_service.py`

**Parallel?**: Yes - can be done alongside other service updates.

### Subtask T005 - Update import_export_service.py (export logic)

**Purpose**: Update export field mappings to use new names.

**Steps**:
1. Open `src/services/import_export_service.py`
2. Find lines ~233-234 (export product legacy fields):
   ```python
   "purchase_quantity": ingredient.purchase_quantity,
   "purchase_unit": ingredient.purchase_unit,
   ```
3. Update to:
   ```python
   "package_unit_quantity": ingredient.package_unit_quantity,
   "package_unit": ingredient.package_unit,
   ```
4. Find lines ~1084-1085 (export product current fields):
   ```python
   "purchase_unit": product.purchase_unit,
   "purchase_quantity": product.purchase_quantity,
   ```
5. Update to:
   ```python
   "package_unit": product.package_unit,
   "package_unit_quantity": product.package_unit_quantity,
   ```

**Files**: `src/services/import_export_service.py`

**Parallel?**: Yes - can be done alongside T006.

### Subtask T006 - Update import_export_service.py (import logic)

**Purpose**: Update import field mappings to use new names.

**Steps**:
1. In `src/services/import_export_service.py`
2. Find lines ~2298-2299 (import product fields):
   ```python
   purchase_unit=prod_data.get("purchase_unit"),
   purchase_quantity=prod_data.get("purchase_quantity"),
   ```
3. Update to:
   ```python
   package_unit=prod_data.get("package_unit"),
   package_unit_quantity=prod_data.get("package_unit_quantity"),
   ```
4. Search for any other references in the file and update them

**Files**: `src/services/import_export_service.py`

**Parallel?**: Yes - can be done alongside T005.

### Subtask T007 - Update recipe_service.py

**Purpose**: Update any field references in recipe service.

**Steps**:
1. Open `src/services/recipe_service.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace with `package_unit` and `package_unit_quantity`

**Files**: `src/services/recipe_service.py`

**Parallel?**: Yes.

### Subtask T008 - Update inventory_item_service.py

**Purpose**: Update any field references in inventory item service.

**Steps**:
1. Open `src/services/inventory_item_service.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace with `package_unit` and `package_unit_quantity`

**Files**: `src/services/inventory_item_service.py`

**Parallel?**: Yes.

### Subtask T009 - Update finished_unit_service.py

**Purpose**: Update any field references in finished unit service.

**Steps**:
1. Open `src/services/finished_unit_service.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace with `package_unit` and `package_unit_quantity`

**Files**: `src/services/finished_unit_service.py`

**Parallel?**: Yes.

### Subtask T010 - Update event_service.py

**Purpose**: Update any field references in event service.

**Steps**:
1. Open `src/services/event_service.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace with `package_unit` and `package_unit_quantity`

**Files**: `src/services/event_service.py`

**Parallel?**: Yes.

### Subtask T011 - Update catalog_import_service.py

**Purpose**: Update any field references in catalog import service.

**Steps**:
1. Open `src/services/catalog_import_service.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace with `package_unit` and `package_unit_quantity`

**Files**: `src/services/catalog_import_service.py`

**Parallel?**: Yes.

### Subtask T012 - Update assembly_service.py

**Purpose**: Update any field references in assembly service.

**Steps**:
1. Open `src/services/assembly_service.py`
2. Search for `purchase_unit` and `purchase_quantity`
3. Replace with `package_unit` and `package_unit_quantity`

**Files**: `src/services/assembly_service.py`

**Parallel?**: Yes.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Aliasing logic broken in import/export | Verify JSON keys match model attributes exactly |
| Missed references | Run grep after changes to verify zero matches |

## Definition of Done Checklist

- [ ] All service files updated
- [ ] `grep -rn "purchase_unit\|purchase_quantity" src/services/` returns zero matches
- [ ] No syntax errors in any service file
- [ ] Import/export field mappings use exact model attribute names
- [ ] `tasks.md` updated with status change

## Review Guidance

- Run grep to confirm zero matches for old field names
- Spot-check import_export_service.py to verify JSON key names match model attributes
- Verify no business logic was changed (only field references)

## Activity Log

- 2025-12-15T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-15T17:09:27Z – claude – shell_pid=83880 – lane=doing – Started implementation
- 2025-12-15T17:20:00Z – claude – shell_pid=83880 – lane=doing – Completed: Updated all 9 service files (T004-T012). grep returns zero matches.
- 2025-12-15T17:15:37Z – claude – shell_pid=83880 – lane=for_review – Ready for review
- 2025-12-15T21:51:48Z – claude – shell_pid=83880 – lane=done – Code review approved: Service layer correctly updated
