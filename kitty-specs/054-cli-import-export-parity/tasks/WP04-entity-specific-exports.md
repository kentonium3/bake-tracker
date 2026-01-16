---
work_package_id: "WP04"
subtasks:
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
title: "Entity-Specific Export Commands"
phase: "Phase 4 - Entity-Specific Export Commands (P2-P3)"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-15T18:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Entity-Specific Export Commands

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

Add 6 new entity-specific export commands following the existing `export-ingredients` pattern:

1. `export-materials` (P2)
2. `export-material-products` (P2)
3. `export-material-categories` (P2)
4. `export-material-subcategories` (P2)
5. `export-suppliers` (P3)
6. `export-purchases` (P3)

**Success Criteria**:
- All 6 commands registered as subparsers
- Each command accepts `file` positional argument
- Output JSON matches UI export format exactly
- Follow existing `export_ingredients()` pattern

## Context & Constraints

**Reference Documents**:
- `kitty-specs/054-cli-import-export-parity/plan.md` - Phase 4 details
- `src/utils/import_export_cli.py` - Lines 81-92 for existing pattern

**Existing Pattern** (export_ingredients at line 81):
```python
def export_ingredients(output_file: str):
    """Export ingredients only."""
    print(f"Exporting ingredients to {output_file}...")
    result = export_ingredients_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1
```

**Service Functions Required** (verify in import_export_service.py):
- `export_materials_to_json`
- `export_material_products_to_json`
- `export_material_categories_to_json`
- `export_material_subcategories_to_json`
- `export_suppliers_to_json`
- `export_purchases_to_json`

## Subtasks & Detailed Guidance

### T027 - Add `export-materials` subparser and handler

**Purpose**: Export materials to JSON file.

**Steps**:
1. Add subparser in entity export section (around line 642)
2. Add handler function following `export_ingredients` pattern
3. Import `export_materials_to_json` from import_export_service

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes - all 6 entity exports are independent

**Code Pattern**:
```python
# Subparser
materials_parser = subparsers.add_parser(
    "export-materials",
    help="Export materials only"
)
materials_parser.add_argument("file", help="JSON file path")

# Handler function
def export_materials(output_file: str):
    """Export materials only."""
    print(f"Exporting materials to {output_file}...")
    from src.services.import_export_service import export_materials_to_json
    result = export_materials_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1
```

### T028 - Add `export-material-products` subparser and handler

**Purpose**: Export material products to JSON file.

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
# Subparser
material_products_parser = subparsers.add_parser(
    "export-material-products",
    help="Export material products only"
)
material_products_parser.add_argument("file", help="JSON file path")

# Handler function
def export_material_products(output_file: str):
    """Export material products only."""
    print(f"Exporting material products to {output_file}...")
    from src.services.import_export_service import export_material_products_to_json
    result = export_material_products_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1
```

### T029 - Add `export-material-categories` subparser and handler

**Purpose**: Export material categories to JSON file.

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
# Subparser
material_categories_parser = subparsers.add_parser(
    "export-material-categories",
    help="Export material categories only"
)
material_categories_parser.add_argument("file", help="JSON file path")

# Handler function
def export_material_categories(output_file: str):
    """Export material categories only."""
    print(f"Exporting material categories to {output_file}...")
    from src.services.import_export_service import export_material_categories_to_json
    result = export_material_categories_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1
```

### T030 - Add `export-material-subcategories` subparser and handler

**Purpose**: Export material subcategories to JSON file.

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
# Subparser
material_subcategories_parser = subparsers.add_parser(
    "export-material-subcategories",
    help="Export material subcategories only"
)
material_subcategories_parser.add_argument("file", help="JSON file path")

# Handler function
def export_material_subcategories(output_file: str):
    """Export material subcategories only."""
    print(f"Exporting material subcategories to {output_file}...")
    from src.services.import_export_service import export_material_subcategories_to_json
    result = export_material_subcategories_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1
```

### T031 - Add `export-suppliers` subparser and handler

**Purpose**: Export suppliers to JSON file.

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
# Subparser
suppliers_parser = subparsers.add_parser(
    "export-suppliers",
    help="Export suppliers only"
)
suppliers_parser.add_argument("file", help="JSON file path")

# Handler function
def export_suppliers(output_file: str):
    """Export suppliers only."""
    print(f"Exporting suppliers to {output_file}...")
    from src.services.import_export_service import export_suppliers_to_json
    result = export_suppliers_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1
```

### T032 - Add `export-purchases` subparser and handler

**Purpose**: Export purchases to JSON file.

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
# Subparser
purchases_parser = subparsers.add_parser(
    "export-purchases",
    help="Export purchases only"
)
purchases_parser.add_argument("file", help="JSON file path")

# Handler function
def export_purchases(output_file: str):
    """Export purchases only."""
    print(f"Exporting purchases to {output_file}...")
    from src.services.import_export_service import export_purchases_to_json
    result = export_purchases_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1
```

### T033 - Import required service functions

**Purpose**: Verify and import all required export functions.

**Steps**:
1. Check `import_export_service.py` for available export functions
2. If functions don't exist, they may need to be added (out of scope - document as limitation)
3. Add imports at top of file or use inline imports in handlers

**Files**:
- `src/services/import_export_service.py` (read only - verify)
- `src/utils/import_export_cli.py` (modify imports if needed)

**Notes**: If some export functions don't exist, document which ones are missing and skip those commands or raise error with helpful message.

### T034 - Wire all 6 commands in `main()` dispatch logic

**Purpose**: Connect entity export subparsers to handler functions.

**Steps**:
1. Add elif branches in `main()` for each new export command
2. Follow existing pattern from lines 751-764

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
elif args.command == "export-materials":
    return export_materials(args.file)
elif args.command == "export-material-products":
    return export_material_products(args.file)
elif args.command == "export-material-categories":
    return export_material_categories(args.file)
elif args.command == "export-material-subcategories":
    return export_material_subcategories(args.file)
elif args.command == "export-suppliers":
    return export_suppliers(args.file)
elif args.command == "export-purchases":
    return export_purchases(args.file)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Export functions don't exist in import_export_service | Check service; may need to add functions or skip commands |
| Function signatures differ from expected | Verify return type is ExportResult with .success and .get_summary() |

## Definition of Done Checklist

- [ ] All 6 subparsers registered
- [ ] All 6 handler functions implemented
- [ ] Commands wired in main() dispatch
- [ ] Each command exports correct entity type
- [ ] Output JSON matches UI export format
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify service functions exist before reviewing CLI code
- Check that export output matches existing entity export patterns
- Test with empty entities (should create empty array, not fail)

## Activity Log

- 2026-01-15T18:00:00Z - system - lane=planned - Prompt created.
- 2026-01-15T23:47:15Z – unknown – lane=doing – Starting implementation
- 2026-01-15T23:50:56Z – unknown – lane=for_review – All 6 entity export commands implemented and tested
- 2026-01-16T00:40:05Z – agent – lane=doing – Started review via workflow command
- 2026-01-16T00:40:29Z – unknown – lane=done – Review passed: All 6 entity-specific export commands implemented and wired
