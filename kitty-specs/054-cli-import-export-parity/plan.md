# Implementation Plan: CLI Import/Export Parity

**Branch**: `054-cli-import-export-parity` | **Date**: 2026-01-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/054-cli-import-export-parity/spec.md`

## Summary

Bring CLI import/export functionality to full parity with UI capabilities by adding ~16 new commands that wrap existing service layer functions. This feature enables AI-assisted workflows and mobile JSON ingestion through a first-class CLI interface.

**Technical Approach**: Extend existing `src/utils/import_export_cli.py` with new argparse subparsers that call existing service functions. No new business logic - CLI is a thin wrapper over services.

## Technical Context

**Language/Version**: Python 3.10+ (existing project requirement)
**Primary Dependencies**: argparse (stdlib), existing service layer
**Storage**: SQLite via SQLAlchemy (existing)
**Testing**: pytest with integration tests for CLI commands
**Target Platform**: Desktop CLI (Windows, macOS, Linux)
**Project Type**: Single project (extending existing CLI module)
**Performance Goals**: N/A - synchronous CLI operations
**Constraints**: CLI output must match UI export formats exactly
**Scale/Scope**: ~16 new commands, ~400 lines of code addition

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Layered Architecture**: CLI wraps services only - no business logic in CLI
- [x] **Service Layer Reuse**: All commands call existing service functions
- [x] **Backward Compatibility**: Legacy commands preserved unchanged
- [x] **DRY Principle**: No duplication of service logic in CLI
- [x] **User-Centric Design**: Command names match user mental model from UI

## Project Structure

### Documentation (this feature)

```
kitty-specs/054-cli-import-export-parity/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Service layer research findings
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── utils/
│   └── import_export_cli.py    # EXTEND: Add new subparsers
├── services/
│   ├── coordinated_export_service.py  # EXISTS: backup/restore functions
│   ├── denormalized_export_service.py # EXISTS: aug export functions
│   ├── catalog_import_service.py      # EXISTS: catalog import functions
│   ├── enhanced_import_service.py     # EXISTS: aug import functions
│   └── import_export_service.py       # EXISTS: entity export functions
└── tests/
    └── test_import_export_cli.py      # ADD: CLI integration tests
```

**Structure Decision**: Extend existing single-module CLI (`import_export_cli.py`) rather than creating new modules. All import/export commands in one discoverable location.

## Implementation Phases

### Phase 1: Backup/Restore Commands (P1)

Add 4 commands for 16-entity coordinated backup operations.

**Commands**:
| Command | Service Function | Arguments |
|---------|-----------------|-----------|
| backup | export_complete() | `-o OUTPUT_DIR`, `--zip` |
| restore | import_complete() | `BACKUP_DIR`, `--mode`, `--interactive` |
| backup-list | (directory scan) | `--dir BACKUPS_DIR` |
| backup-validate | validate_export() | `BACKUP_DIR` |

**Service Integration** (from research.md):
```python
from src.services.coordinated_export_service import (
    export_complete,      # Returns ExportManifest
    import_complete,      # Returns Dict with counts
    validate_export,      # Returns Dict with validation results
)
```

### Phase 2: Context-Rich Aug Commands (P1)

Add 3 commands for AI-workflow context-rich exports/imports.

**Commands**:
| Command | Service Function | Arguments |
|---------|-----------------|-----------|
| aug-export | export_*_context_rich() | `-t TYPE`, `-o OUTPUT` |
| aug-import | import_context_rich_export() | `INPUT_FILE`, `--interactive`, `--skip-on-error` |
| aug-validate | detect_format() | `INPUT_FILE` |

**Entity Types** (7 + all):
- ingredients, products, recipes, materials, material-products
- finished-units, finished-goods
- `all` (convenience option)

**Service Integration**:
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

### Phase 3: Catalog Commands (P2)

Add 3 commands for catalog import/export operations.

**Commands**:
| Command | Service Function | Arguments |
|---------|-----------------|-----------|
| catalog-export | (aggregate exports) | `-o OUTPUT_DIR`, `--entities` |
| catalog-import | import_catalog() | `INPUT_DIR`, `--mode`, `--interactive` |
| catalog-validate | (schema validation) | `INPUT_DIR` |

**Catalog Entity Types** (7):
- ingredients, products, recipes, finished-goods
- materials, material-products, suppliers

**Service Integration**:
```python
from src.services.catalog_import_service import import_catalog
# Note: catalog-export aggregates individual entity exports
```

### Phase 4: Entity-Specific Export Commands (P2-P3)

Add 6 commands for materials, suppliers, and purchases.

**Commands**:
| Command | Entity | Priority |
|---------|--------|----------|
| export-materials | Material | P2 |
| export-material-products | MaterialProduct | P2 |
| export-material-categories | MaterialCategory | P2 |
| export-material-subcategories | MaterialSubcategory | P2 |
| export-suppliers | Supplier | P3 |
| export-purchases | Purchase | P3 |

**Pattern**: Follow existing `export-ingredients` command structure.

### Phase 5: Documentation Update (P3)

Update module docstring and help text for all commands.

**Documentation Requirements**:
- Module-level docstring with command reference
- Per-command help text with examples
- AI workflow examples (aug export -> modify -> aug import)
- Mobile JSON ingestion examples

## Key Implementation Patterns

### Command Registration Pattern

```python
# Follow existing subparser pattern
backup_parser = subparsers.add_parser(
    "backup",
    help="Create timestamped 16-entity backup"
)
backup_parser.add_argument(
    "-o", "--output",
    help="Output directory (default: ./backups/)"
)
backup_parser.add_argument(
    "--zip",
    action="store_true",
    help="Create compressed archive"
)
```

### Service Call Pattern

```python
def backup_cmd(output_dir: str = None, create_zip: bool = False) -> int:
    """Execute backup command."""
    from src.services.coordinated_export_service import export_complete

    try:
        manifest = export_complete(output_dir, create_zip=create_zip)
        print(f"Backup created: {manifest.export_date}")
        print(f"Files: {len(manifest.files)}")
        for f in manifest.files:
            print(f"  {f.filename}: {f.record_count} records")
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
```

### FK Resolution Pattern (for imports)

```python
def aug_import_cmd(
    file_path: str,
    interactive: bool = False,
    skip_on_error: bool = False,
) -> int:
    """Execute aug-import command."""
    from src.services.enhanced_import_service import import_context_rich_export

    resolver = CLIFKResolver() if interactive else None

    result = import_context_rich_export(
        file_path,
        skip_on_error=skip_on_error,
        resolver=resolver,
    )
    print(result.get_summary())
    return 0 if result.base_result.failed == 0 else 1
```

## Testing Strategy

### Integration Tests

```python
# test_import_export_cli.py

def test_backup_creates_manifest():
    """Verify backup command creates manifest with all 16 entities."""

def test_restore_validates_manifest():
    """Verify restore fails on invalid manifest."""

def test_aug_export_creates_aug_prefix():
    """Verify aug-export uses aug_ prefix (not view_)."""

def test_catalog_import_modes():
    """Verify add/augment modes work correctly."""
```

### Manual Verification

1. Run each new command with `--help` to verify help text
2. Execute backup -> restore round-trip
3. Execute aug-export -> modify -> aug-import workflow
4. Verify CLI output matches UI export output (byte comparison)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Service function signatures changed | Research completed - signatures verified |
| Context-rich export format unclear | Confirmed aug_ prefix from F053 |
| Materials not in coordinated export | Verified - materials included (order 7-12) |
| CLI testing coverage gaps | Add integration tests per command |

## Dependencies

- F047: Materials entities in services (COMPLETE)
- F049: Coordinated export service (COMPLETE)
- F050/F051: Supplier support (COMPLETE)
- F053: Context-rich export fixes (COMPLETE)

## Artifacts Generated

- [x] plan.md (this file)
- [x] research.md (service layer research)
- [ ] tasks.md (created by /spec-kitty.tasks)
