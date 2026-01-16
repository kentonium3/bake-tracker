---
work_package_id: "WP02"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "Context-Rich Aug Commands"
phase: "Phase 2 - Context-Rich Aug Commands (P1)"
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

# Work Package Prompt: WP02 - Context-Rich Aug Commands

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

Implement 3 context-rich "aug" CLI commands for AI-assisted workflows:

1. `aug-export` - Export with human-readable context (resolved FKs)
2. `aug-import` - Import with automatic FK resolution
3. `aug-validate` - Validate aug file format

**Success Criteria**:
- All 3 commands registered with correct arguments
- `aug-export -t products` creates `aug_products.json` with `aug_` prefix
- `aug-export -t all` exports all 7 entity types
- `aug-import` resolves FKs automatically or prompts in interactive mode
- `aug-validate` reports format/schema violations
- Entity types: ingredients, products, recipes, materials, material-products, finished-units, finished-goods

## Context & Constraints

**Reference Documents**:
- `kitty-specs/054-cli-import-export-parity/plan.md` - Phase 2 details
- `kitty-specs/054-cli-import-export-parity/research.md` - Service function signatures

**Service Functions** (from research.md):
```python
from src.services.denormalized_export_service import (
    export_products_context_rich,
    export_ingredients_context_rich,
    export_materials_context_rich,
    export_recipes_context_rich,
    export_material_products_context_rich,
    export_finished_units_context_rich,
    export_finished_goods_context_rich,
    export_all_context_rich,
)
from src.services.enhanced_import_service import (
    import_context_rich_export,
    detect_format,
)
```

**Existing Pattern**: Reuse `CLIFKResolver` class at lines 344-537 for interactive FK resolution.

## Subtasks & Detailed Guidance

### T010 - Add `aug-export` subparser

**Purpose**: Register the `aug-export` command.

**Steps**:
1. Add subparser after backup commands
2. Define arguments:
   - `-t, --type`: Entity type (required), choices include 7 types + "all"
   - `-o, --output`: Output path (default: `aug_{type}.json`)

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
# Aug export command
aug_export_parser = subparsers.add_parser(
    "aug-export",
    help="Export context-rich data for AI workflows (aug_ prefix)"
)
aug_export_parser.add_argument(
    "-t", "--type",
    dest="entity_type",
    choices=["ingredients", "products", "recipes", "materials",
             "material-products", "finished-units", "finished-goods", "all"],
    required=True,
    help="Entity type to export"
)
aug_export_parser.add_argument(
    "-o", "--output",
    dest="output_path",
    help="Output file path (default: aug_{type}.json)"
)
```

### T011 - Implement `aug_export_cmd()` function

**Purpose**: Execute context-rich export for specified entity type.

**Steps**:
1. Create mapping from entity type names to export functions
2. Handle "all" type using `export_all_context_rich()`
3. Generate default output path with `aug_` prefix
4. Call appropriate export function
5. Print summary and return exit code

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
def aug_export_cmd(entity_type: str, output_path: str = None) -> int:
    """Export context-rich data for AI workflows."""
    from src.services.denormalized_export_service import (
        export_products_context_rich,
        export_ingredients_context_rich,
        export_materials_context_rich,
        export_recipes_context_rich,
        export_material_products_context_rich,
        export_finished_units_context_rich,
        export_finished_goods_context_rich,
        export_all_context_rich,
    )

    # Map entity types to export functions
    exporters = {
        "products": export_products_context_rich,
        "ingredients": export_ingredients_context_rich,
        "recipes": export_recipes_context_rich,
        "materials": export_materials_context_rich,
        "material-products": export_material_products_context_rich,
        "finished-units": export_finished_units_context_rich,
        "finished-goods": export_finished_goods_context_rich,
    }

    try:
        if entity_type == "all":
            # Export all types to directory
            output_dir = output_path or "."
            print(f"Exporting all context-rich types to {output_dir}...")
            results = export_all_context_rich(output_dir)
            print(f"\nExport Complete")
            print(f"---------------")
            for etype, result in results.items():
                print(f"  {etype}: {result.record_count} records")
            return 0
        else:
            # Single entity type
            if output_path is None:
                output_path = f"aug_{entity_type.replace('-', '_')}.json"

            print(f"Exporting {entity_type} to {output_path}...")
            result = exporters[entity_type](output_path)

            print(f"\nExport Complete")
            print(f"---------------")
            print(f"Output file: {output_path}")
            print(f"Records exported: {result.record_count}")
            return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1
```

### T012 - Add entity type mapping

**Purpose**: Define the 7 supported entity types + "all" convenience option.

**Steps**: This is incorporated into T011 - the mapping is part of `aug_export_cmd()`.

**Notes**: Entity types use kebab-case in CLI (`material-products`) but underscore in filenames (`aug_material_products.json`).

### T013 - Add `aug-import` subparser

**Purpose**: Register the `aug-import` command.

**Steps**:
1. Add subparser after `aug-export`
2. Define arguments:
   - `file`: Positional argument for input file
   - `--interactive`: Enable interactive FK resolution
   - `--skip-on-error`: Continue on validation errors

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
# Aug import command
aug_import_parser = subparsers.add_parser(
    "aug-import",
    help="Import context-rich data with FK resolution"
)
aug_import_parser.add_argument(
    "file",
    help="Input aug JSON file"
)
aug_import_parser.add_argument(
    "-i", "--interactive",
    action="store_true",
    help="Enable interactive FK resolution"
)
aug_import_parser.add_argument(
    "-s", "--skip-on-error",
    dest="skip_on_error",
    action="store_true",
    help="Skip records with errors instead of failing"
)
```

### T014 - Implement `aug_import_cmd()` function

**Purpose**: Execute context-rich import with FK resolution.

**Steps**:
1. Import `import_context_rich_export` from enhanced_import_service
2. Set up `CLIFKResolver` if interactive mode
3. Call service function with resolver and skip_on_error options
4. Print import summary
5. Return 0 if no failures, 1 otherwise

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
def aug_import_cmd(
    file_path: str,
    interactive: bool = False,
    skip_on_error: bool = False,
) -> int:
    """Import context-rich data with FK resolution."""
    from src.services.enhanced_import_service import import_context_rich_export

    mode_display = []
    if interactive:
        mode_display.append("interactive")
    if skip_on_error:
        mode_display.append("skip-on-error")
    mode_str = f" ({', '.join(mode_display)})" if mode_display else ""

    print(f"Importing from {file_path}{mode_str}...")

    # Set up resolver if interactive
    resolver = CLIFKResolver() if interactive else None

    try:
        result = import_context_rich_export(
            file_path,
            skip_on_error=skip_on_error,
            resolver=resolver,
        )

        print("\n" + result.get_summary())
        return 0 if result.base_result.failed == 0 else 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1
```

### T015 - Integrate CLIFKResolver for interactive mode

**Purpose**: Ensure existing `CLIFKResolver` class works with new import.

**Steps**:
1. Verify `CLIFKResolver` at lines 344-537 is compatible
2. Test that resolver callbacks work with `import_context_rich_export`
3. No changes expected if service follows same FK resolution pattern

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Notes**: CLIFKResolver already handles ingredient, supplier, product entity types. May need to extend for materials if context-rich imports include them.

### T016 - Add `aug-validate` subparser

**Purpose**: Register the `aug-validate` command.

**Steps**:
1. Add subparser after `aug-import`
2. Define arguments:
   - `file`: Positional argument for file to validate

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

### T017 - Implement `aug_validate_cmd()` function

**Purpose**: Validate aug file format and schema.

**Steps**:
1. Import `detect_format` from enhanced_import_service
2. Call format detection
3. Report detected format or validation errors

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
def aug_validate_cmd(file_path: str) -> int:
    """Validate aug file format."""
    from src.services.enhanced_import_service import detect_format
    import json

    print(f"Validating {file_path}...")

    try:
        # Read and parse file
        with open(file_path) as f:
            data = json.load(f)

        # Detect format
        format_info = detect_format(data)

        print(f"\nValidation Results")
        print(f"------------------")
        print(f"File: {file_path}")
        print(f"Format: {format_info.get('format', 'Unknown')}")
        print(f"Version: {format_info.get('version', 'Unknown')}")
        print(f"Entity type: {format_info.get('entity_type', 'Unknown')}")
        print(f"Record count: {format_info.get('record_count', 0)}")

        if format_info.get('valid', True):
            print("\nStatus: VALID")
            return 0
        else:
            print("\nStatus: INVALID")
            for error in format_info.get('errors', []):
                print(f"  - {error}")
            return 1

    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON - {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
```

### T018 - Wire all 3 commands in `main()` dispatch logic

**Purpose**: Connect aug subparsers to handler functions.

**Steps**:
1. Add elif branches in `main()` for aug commands
2. Pass correct arguments from args namespace

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
elif args.command == "aug-export":
    return aug_export_cmd(args.entity_type, args.output_path)
elif args.command == "aug-import":
    return aug_import_cmd(args.file, args.interactive, args.skip_on_error)
elif args.command == "aug-validate":
    return aug_validate_cmd(args.file)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Export function signatures differ | Verify each function in denormalized_export_service |
| `import_context_rich_export` may have different signature | Check enhanced_import_service for actual parameters |
| `detect_format` may return different structure | Adapt validation display based on actual return value |

## Definition of Done Checklist

- [ ] All 3 subparsers registered with correct arguments
- [ ] All 3 command functions implemented
- [ ] Commands wired in main() dispatch
- [ ] `aug-export -t products` creates `aug_products.json`
- [ ] `aug-export -t all` exports all 7 types
- [ ] `aug-import` works in non-interactive mode
- [ ] `aug-import --interactive` prompts for FK resolution
- [ ] `aug-validate` reports format and validation results
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify `aug_` prefix used in output filenames
- Test with files containing missing FK references
- Verify interactive mode prompts work correctly
- Check export file structure matches expected format

## Activity Log

- 2026-01-15T18:00:00Z - system - lane=planned - Prompt created.
- 2026-01-15T23:41:14Z – unknown – lane=doing – Starting implementation
- 2026-01-15T23:43:37Z – unknown – lane=for_review – All 3 aug commands implemented and tested
- 2026-01-16T00:39:09Z – agent – lane=doing – Started review via workflow command
- 2026-01-16T00:39:31Z – unknown – lane=done – Review passed: All 3 aug commands implemented with correct entity types and options
