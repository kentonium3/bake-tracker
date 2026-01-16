---
work_package_id: "WP03"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
title: "Catalog Commands"
phase: "Phase 3 - Catalog Commands (P2)"
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

# Work Package Prompt: WP03 - Catalog Commands

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

Implement 3 catalog import/export CLI commands for selective entity operations:

1. `catalog-export` - Export catalog entities (7 types) selectively
2. `catalog-import` - Import catalog with mode selection
3. `catalog-validate` - Validate catalog schema before import

**Success Criteria**:
- All 3 commands registered with correct arguments
- `catalog-export --entities ingredients,products` exports only those types
- `catalog-export` without `--entities` exports all 7 types
- `catalog-import --mode augment` updates existing + adds new
- `catalog-validate` reports schema validation results
- Catalog entity types: ingredients, products, recipes, finished-goods, materials, material-products, suppliers

## Context & Constraints

**Reference Documents**:
- `kitty-specs/054-cli-import-export-parity/plan.md` - Phase 3 details
- `kitty-specs/054-cli-import-export-parity/research.md` - Service function signatures

**Service Functions** (from research.md):
```python
from src.services.catalog_import_service import import_catalog
# Note: No catalog_export service function exists - must aggregate individual exports
```

**Key Difference**: Unlike backup (16 entities), catalog operations focus on 7 catalog-specific entities.

## Subtasks & Detailed Guidance

### T019 - Add `catalog-export` subparser

**Purpose**: Register the `catalog-export` command.

**Steps**:
1. Add subparser after aug commands
2. Define arguments:
   - `-o, --output`: Output directory (default: `./catalog_export/`)
   - `--entities`: Comma-separated entity list (optional, default: all)

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
# Catalog export command
catalog_export_parser = subparsers.add_parser(
    "catalog-export",
    help="Export catalog data (7 entity types)"
)
catalog_export_parser.add_argument(
    "-o", "--output",
    dest="output_dir",
    default="./catalog_export/",
    help="Output directory (default: ./catalog_export/)"
)
catalog_export_parser.add_argument(
    "--entities",
    dest="entities",
    help="Comma-separated entity types to export (default: all)"
)
```

### T020 - Implement `catalog_export_cmd()` function

**Purpose**: Export catalog entities by aggregating individual export functions.

**Steps**:
1. Define list of catalog entity types
2. Parse `--entities` argument if provided
3. For each entity type, call appropriate export function
4. Write files to output directory
5. Print summary

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
def catalog_export_cmd(output_dir: str, entities_str: str = None) -> int:
    """Export catalog data."""
    from src.services.import_export_service import (
        export_ingredients_to_json,
        export_recipes_to_json,
        export_finished_goods_to_json,
    )
    # Import additional export functions as needed

    # Define all catalog entity types
    all_catalog_entities = [
        "ingredients", "products", "recipes", "finished-goods",
        "materials", "material-products", "suppliers"
    ]

    # Parse entities to export
    if entities_str:
        entities = [e.strip() for e in entities_str.split(",")]
        invalid = set(entities) - set(all_catalog_entities)
        if invalid:
            print(f"ERROR: Unknown entity types: {', '.join(invalid)}")
            print(f"Valid types: {', '.join(all_catalog_entities)}")
            return 1
    else:
        entities = all_catalog_entities

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Exporting catalog to {output_dir}...")

    # Map entity types to export functions
    exporters = {
        "ingredients": ("ingredients.json", export_ingredients_to_json),
        "products": ("products.json", export_products_to_json),
        "recipes": ("recipes.json", export_recipes_to_json),
        "finished-goods": ("finished_goods.json", export_finished_goods_to_json),
        "materials": ("materials.json", export_materials_to_json),
        "material-products": ("material_products.json", export_material_products_to_json),
        "suppliers": ("suppliers.json", export_suppliers_to_json),
    }

    results = []
    try:
        for entity in entities:
            filename, exporter = exporters[entity]
            file_path = str(output_path / filename)
            result = exporter(file_path)
            results.append((entity, result))
            print(f"  {entity}: {result.record_count} records")

        print(f"\nCatalog Export Complete")
        print(f"-----------------------")
        print(f"Output directory: {output_dir}")
        print(f"Entities exported: {len(results)}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1
```

### T021 - Define catalog entity type list

**Purpose**: Establish the 7 catalog entity types.

**Steps**: Incorporated into T020 - the list is defined in `catalog_export_cmd()`.

**Catalog Entities** (7 types):
1. ingredients
2. products
3. recipes
4. finished-goods
5. materials
6. material-products
7. suppliers

### T022 - Add `catalog-import` subparser

**Purpose**: Register the `catalog-import` command.

**Steps**:
1. Add subparser after `catalog-export`
2. Define arguments:
   - `input_dir`: Positional argument for input directory
   - `--mode`: Import mode (add/augment), default "add"
   - `--interactive`: Enable FK resolution prompts
   - `--dry-run`: Preview mode

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
# Catalog import command
catalog_import_parser = subparsers.add_parser(
    "catalog-import",
    help="Import catalog data with mode selection"
)
catalog_import_parser.add_argument(
    "input_dir",
    help="Input directory with catalog JSON files"
)
catalog_import_parser.add_argument(
    "-m", "--mode",
    dest="import_mode",
    choices=["add", "augment"],
    default="add",
    help="Import mode: 'add' (default) skip existing, 'augment' update nulls"
)
catalog_import_parser.add_argument(
    "-i", "--interactive",
    action="store_true",
    help="Enable interactive FK resolution"
)
catalog_import_parser.add_argument(
    "-d", "--dry-run",
    dest="dry_run",
    action="store_true",
    help="Preview changes without modifying database"
)
```

### T023 - Implement `catalog_import_cmd()` function

**Purpose**: Import catalog data using catalog_import_service.

**Steps**:
1. Import `import_catalog` from catalog_import_service
2. Call service with mode and dry_run options
3. Print import summary
4. Return exit code based on failures

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
def catalog_import_cmd(
    input_dir: str,
    mode: str = "add",
    interactive: bool = False,
    dry_run: bool = False,
) -> int:
    """Import catalog data."""
    from src.services.catalog_import_service import import_catalog

    mode_display = [f"mode: {mode}"]
    if dry_run:
        mode_display.append("DRY RUN")
    if interactive:
        mode_display.append("interactive")

    print(f"Importing catalog from {input_dir} ({', '.join(mode_display)})...")

    try:
        result = import_catalog(
            input_dir,
            mode=mode,
            dry_run=dry_run,
        )

        print("\n" + result.get_summary())

        # Check for failures
        total_failed = sum(
            counts.failed for counts in result.entity_counts.values()
        )
        return 0 if total_failed == 0 else 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1
```

### T024 - Add `catalog-validate` subparser

**Purpose**: Register the `catalog-validate` command.

**Steps**:
1. Add subparser after `catalog-import`
2. Define arguments:
   - `input_dir`: Positional argument for directory to validate

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

### T025 - Implement `catalog_validate_cmd()` function

**Purpose**: Validate catalog files before import.

**Steps**:
1. Scan input directory for expected JSON files
2. Validate JSON structure and required fields
3. Report validation results per entity type

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
def catalog_validate_cmd(input_dir: str) -> int:
    """Validate catalog files."""
    import json

    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"ERROR: Directory not found: {input_dir}")
        return 1

    # Expected catalog files
    expected_files = {
        "ingredients.json": ["slug", "display_name", "category"],
        "products.json": ["ingredient_slug", "package_unit"],
        "recipes.json": ["slug", "display_name"],
        "finished_goods.json": ["recipe_slug"],
        "materials.json": ["slug", "display_name"],
        "material_products.json": ["material_slug"],
        "suppliers.json": ["name", "city", "state", "zip_code"],
    }

    print(f"Validating catalog in {input_dir}...")

    errors = []
    valid_files = 0

    for filename, required_fields in expected_files.items():
        file_path = input_path / filename
        if not file_path.exists():
            continue  # File is optional

        try:
            with open(file_path) as f:
                data = json.load(f)

            if not isinstance(data, list):
                errors.append(f"{filename}: Expected array, got {type(data).__name__}")
                continue

            # Check required fields in first record
            if data:
                first = data[0]
                missing = [f for f in required_fields if f not in first]
                if missing:
                    errors.append(f"{filename}: Missing required fields: {missing}")
                else:
                    valid_files += 1
                    print(f"  {filename}: {len(data)} records - VALID")
            else:
                valid_files += 1
                print(f"  {filename}: 0 records - VALID (empty)")

        except json.JSONDecodeError as e:
            errors.append(f"{filename}: Invalid JSON - {e}")

    print(f"\nValidation Summary")
    print(f"------------------")
    print(f"Valid files: {valid_files}")

    if errors:
        print(f"Errors: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
        return 1
    else:
        print("Status: ALL VALID")
        return 0
```

### T026 - Wire all 3 commands in `main()` dispatch logic

**Purpose**: Connect catalog subparsers to handler functions.

**Steps**:
1. Add elif branches in `main()` for catalog commands
2. Pass correct arguments from args namespace

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
elif args.command == "catalog-export":
    return catalog_export_cmd(args.output_dir, args.entities)
elif args.command == "catalog-import":
    return catalog_import_cmd(
        args.input_dir, args.import_mode, args.interactive, args.dry_run
    )
elif args.command == "catalog-validate":
    return catalog_validate_cmd(args.input_dir)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Export functions don't exist for all entity types | May need to add missing exports to import_export_service |
| `import_catalog` signature differs from expected | Check catalog_import_service for actual parameters |
| Catalog entity list differs from spec | Verify against spec.md catalog entity types |

## Definition of Done Checklist

- [ ] All 3 subparsers registered with correct arguments
- [ ] All 3 command functions implemented
- [ ] Commands wired in main() dispatch
- [ ] `catalog-export` with no args exports all 7 types
- [ ] `catalog-export --entities x,y` exports only specified types
- [ ] `catalog-import --mode augment` updates existing records
- [ ] `catalog-validate` reports per-file validation
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify catalog entity list matches spec (7 types)
- Test selective export with various `--entities` combinations
- Check import mode behavior (add vs augment)
- Verify dry-run doesn't modify database

## Activity Log

- 2026-01-15T18:00:00Z - system - lane=planned - Prompt created.
- 2026-01-15T23:43:52Z – unknown – lane=doing – Starting implementation
- 2026-01-15T23:47:01Z – unknown – lane=for_review – All 3 catalog commands implemented and tested
- 2026-01-16T00:39:37Z – agent – lane=doing – Started review via workflow command
- 2026-01-16T00:40:00Z – unknown – lane=done – Review passed: All 3 catalog commands implemented with combined catalog.json support
