# Cursor Code Review Prompt - Feature 030: Enhanced Export/Import System

## Role

You are a senior software engineer performing an independent code review of Feature 030 (enhanced-export-import). This feature provides AI-augmented export/import capabilities with denormalized views, manifest-based exports, FK resolution during import, and interactive UI wizards.

## Feature Summary

**Core Changes:**
1. Coordinated export service with manifest files and checksums (WP01)
2. Denormalized view exports for products, inventory, and purchases (WP02)
3. Export CLI commands: `export-complete`, `export-view`, `validate-export` (WP03)
4. FK resolver service with CREATE/MAP/SKIP resolution choices (WP04)
5. Enhanced import service with merge/skip_existing modes, dry-run, skip-on-error (WP05)
6. Import CLI commands: `import-view` with --interactive, --dry-run, --skip-on-error (WP06)
7. FK Resolution Dialog with entity-specific creation forms (WP07)
8. UI integration with Import View menu item and wizard flow (WP08)

**Scope:**
- Services layer: `coordinated_export_service.py`, `denormalized_export_service.py`, `fk_resolver_service.py`, `enhanced_import_service.py`
- Utils layer: `import_export_cli.py` (extended)
- UI layer: `fk_resolution_dialog.py`, `import_export_dialog.py`, `main_window.py`
- Tests: Unit tests for all new services and CLI commands

## Files to Review

### Service Layer - Coordinated Export (WP01)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/services/coordinated_export_service.py`
  - `ExportManifest` dataclass with export metadata
  - `ExportedFile` dataclass with filename, checksum, record_count
  - `export_complete(output_dir, create_zip)` function
  - `validate_export(export_dir)` function
  - SHA-256 checksum generation and validation
  - Entity dependency ordering for import

### Service Layer - Denormalized Export (WP02)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/services/denormalized_export_service.py`
  - `ExportResult` dataclass with view_type, record_count, output_path
  - `export_products_view(output_path)` - products with context fields
  - `export_inventory_view(output_path)` - inventory with supplier/ingredient context
  - `export_purchases_view(output_path)` - purchases with product/supplier context
  - `_meta` section with editable_fields list
  - Context fields (supplier_name, ingredient_category, etc.) for AI augmentation

### Service Layer - FK Resolver (WP04)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/services/fk_resolver_service.py`
  - `ResolutionChoice` enum (CREATE, MAP, SKIP)
  - `MissingFK` dataclass with entity_type, missing_value, affected_record_count
  - `Resolution` dataclass with choice, created_entity, mapped_id
  - `FKResolverCallback` protocol for pluggable resolution
  - `resolve_missing_fks(missing_fks, resolver, session)` function
  - `find_similar_entities(entity_type, search_term, limit)` for fuzzy matching
  - `create_entity(entity_type, entity_data, session)` for creating new entities
  - Follows `session=None` pattern per CLAUDE.md

### Service Layer - Enhanced Import (WP05)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/services/enhanced_import_service.py`
  - `EnhancedImportResult` dataclass extending ImportResult
  - `import_view(file_path, mode, dry_run, skip_on_error, resolver, session)` function
  - Merge mode: updates existing records, adds new ones
  - Skip_existing mode: only adds new records
  - Dry_run mode: previews changes without committing
  - Skip_on_error mode: imports valid records, logs failures
  - FK resolution via slug/name (not ID)
  - Follows `session=None` pattern per CLAUDE.md

### CLI Layer - Import/Export CLI (WP03, WP06)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/utils/import_export_cli.py`
  - `export_complete_cmd(output_dir, create_zip)` function
  - `export_view_cmd(view_type, output_path)` function
  - `validate_export_cmd(export_dir)` function
  - `import_view_cmd(file_path, mode, interactive, skip_on_error, dry_run)` function
  - `CLIFKResolver` class implementing FKResolverCallback
  - argparse subparsers for all new commands
  - Fail-fast default (error on missing FK without --interactive)

### UI Layer - FK Resolution Dialog (WP07)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/ui/fk_resolution_dialog.py`
  - `FKResolutionDialog` class with create/map/skip options
  - `MapEntityDialog` class with fuzzy search dropdown
  - `CreateEntityDialog` class with entity-specific forms
  - `UIFKResolver` class implementing FKResolverCallback for UI use
  - Modal behavior with transient() and grab_set()
  - Cancel handling with keep/rollback options

### UI Layer - Import View Dialog (WP08)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/ui/import_export_dialog.py`
  - `ImportViewDialog` class added
  - File selection via file browser
  - Mode selection (merge/skip_existing)
  - Modal dialog pattern

### UI Layer - Main Window Integration (WP08)

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/ui/main_window.py`
  - "Import View..." menu item added to File menu
  - `_show_import_view_dialog()` method
  - Integration with UIFKResolver and enhanced_import_service
  - Results display via ImportResultsDialog

### Test Files

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/tests/services/test_coordinated_export.py`
  - Tests for manifest generation
  - Tests for checksum validation
  - Tests for ZIP archive creation

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/tests/services/test_denormalized_export.py`
  - Tests for products view export
  - Tests for inventory view export
  - Tests for purchases view export
  - Tests for context field inclusion

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/tests/services/test_fk_resolver.py`
  - Tests for MissingFK and Resolution dataclasses
  - Tests for CREATE/MAP/SKIP resolution choices
  - Tests for find_similar_entities fuzzy matching
  - Tests for create_entity for each entity type
  - Tests for FKResolverCallback protocol

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/tests/services/test_enhanced_import.py`
  - Tests for EnhancedImportResult
  - Tests for merge mode
  - Tests for skip_existing mode
  - Tests for dry_run mode
  - Tests for skip_on_error mode
  - Tests for FK resolution via slug

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/src/tests/utils/test_import_export_cli.py`
  - Tests for export_complete_cmd
  - Tests for export_view_cmd
  - Tests for validate_export_cmd
  - Tests for import_view_cmd with all flags
  - Tests for CLIFKResolver

### Specification Documents

- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/kitty-specs/030-enhanced-export-import/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/kitty-specs/030-enhanced-export-import/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/kitty-specs/030-enhanced-export-import/data-model.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import/kitty-specs/030-enhanced-export-import/tasks.md`

## Review Checklist

### 1. Coordinated Export Service (WP01)

- [ ] `ExportManifest` dataclass exists with export_date, format_version, files list
- [ ] `ExportedFile` dataclass exists with filename, checksum, record_count, import_order
- [ ] `export_complete(output_dir, create_zip)` creates directory with entity JSON files
- [ ] Manifest includes SHA-256 checksums for each file
- [ ] `validate_export(export_dir)` verifies checksums match
- [ ] Entity dependency order: suppliers -> ingredients -> products -> recipes -> ...
- [ ] ZIP archive creation works when create_zip=True
- [ ] Unit tests cover manifest generation, validation, ZIP creation

### 2. Denormalized Export Service (WP02)

- [ ] `ExportResult` dataclass exists with view_type, record_count, output_path, export_date
- [ ] `export_products_view(output_path)` exports products with context
- [ ] `export_inventory_view(output_path)` exports inventory with context
- [ ] `export_purchases_view(output_path)` exports purchases with context
- [ ] Context fields included: supplier_name, ingredient_slug, category, etc.
- [ ] `_meta` section includes editable_fields list
- [ ] Version field included for future compatibility
- [ ] Unit tests cover each view type

### 3. FK Resolver Service (WP04)

- [ ] `ResolutionChoice` enum has CREATE, MAP, SKIP values
- [ ] `MissingFK` dataclass has entity_type, missing_value, field_name, affected_record_count
- [ ] `Resolution` dataclass has choice, entity_type, missing_value, created_entity, mapped_id
- [ ] `FKResolverCallback` protocol defines resolve(missing) -> Resolution
- [ ] `resolve_missing_fks(missing_fks, resolver, session)` processes all missing FKs
- [ ] `find_similar_entities(entity_type, search_term, limit)` returns fuzzy matches
- [ ] `create_entity(entity_type, entity_data, session)` creates entities correctly
- [ ] Supports supplier, ingredient, product entity types
- [ ] Follows `session=None` pattern per CLAUDE.md
- [ ] Unit tests cover all resolution choices

### 4. Enhanced Import Service (WP05)

- [ ] `EnhancedImportResult` extends ImportResult with resolution tracking
- [ ] `import_view(file_path, mode, ...)` function exists
- [ ] Merge mode updates existing and adds new records
- [ ] Skip_existing mode only adds new records
- [ ] Dry_run mode rolls back changes
- [ ] Skip_on_error mode logs failures to JSON file
- [ ] FK resolution via slug/name, not ID
- [ ] Follows `session=None` pattern per CLAUDE.md
- [ ] Unit tests cover all modes and resolution scenarios

### 5. Export CLI Commands (WP03)

- [ ] `export-complete` subparser exists with -o/--output and -z/--zip flags
- [ ] `export-view` subparser exists with -t/--type and -o/--output flags
- [ ] `validate-export` subparser exists with export_dir argument
- [ ] Commands route correctly in main()
- [ ] Unit tests verify command execution

### 6. Import CLI Commands (WP06)

- [ ] `import-view` subparser exists with file argument
- [ ] Supports -m/--mode flag (merge, skip_existing)
- [ ] Supports -i/--interactive flag
- [ ] Supports -s/--skip-on-error flag
- [ ] Supports -d/--dry-run flag
- [ ] `CLIFKResolver` class implements FKResolverCallback
- [ ] CREATE option prompts for entity-specific fields
- [ ] MAP option shows fuzzy search results
- [ ] SKIP option returns skip resolution
- [ ] Fail-fast default (error without --interactive)
- [ ] Unit tests cover all flag combinations

### 7. FK Resolution Dialog (WP07)

- [ ] `FKResolutionDialog` class exists in fk_resolution_dialog.py
- [ ] Shows missing FK info (entity_type, value, affected count)
- [ ] "Create New" button opens CreateEntityDialog
- [ ] "Map to Existing" button opens MapEntityDialog
- [ ] "Skip Records" button returns skip resolution
- [ ] "Cancel Import" button with keep/rollback options
- [ ] Modal behavior (transient, grab_set)
- [ ] `MapEntityDialog` shows fuzzy search results
- [ ] `CreateEntityDialog` has forms for supplier, ingredient, product

### 8. UI Integration (WP08)

- [ ] "Import View..." menu item in File menu
- [ ] `ImportViewDialog` class in import_export_dialog.py
- [ ] File browser for selecting view file
- [ ] Mode selection (merge/skip_existing)
- [ ] `_show_import_view_dialog()` in main_window.py
- [ ] Integrates UIFKResolver for interactive FK resolution
- [ ] Shows ImportResultsDialog after import
- [ ] Refreshes data tabs after successful import

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/030-enhanced-export-import

# Activate virtual environment
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify modules import correctly
python3 -c "
from src.services.coordinated_export_service import (
    export_complete, validate_export, ExportManifest, ExportedFile
)
from src.services.denormalized_export_service import (
    export_products_view, export_inventory_view, export_purchases_view, ExportResult
)
from src.services.fk_resolver_service import (
    ResolutionChoice, MissingFK, Resolution, FKResolverCallback,
    resolve_missing_fks, find_similar_entities, create_entity
)
from src.services.enhanced_import_service import (
    EnhancedImportResult, import_view
)
from src.utils.import_export_cli import (
    export_complete_cmd, export_view_cmd, validate_export_cmd,
    import_view_cmd, CLIFKResolver
)
from src.ui.fk_resolution_dialog import (
    FKResolutionDialog, MapEntityDialog, CreateEntityDialog, UIFKResolver
)
from src.ui.import_export_dialog import ImportViewDialog
print('All modules import successfully')
"

# Verify FK resolver enums and dataclasses
python3 -c "
from src.services.fk_resolver_service import ResolutionChoice, MissingFK, Resolution
print(f'ResolutionChoice values: {[e.value for e in ResolutionChoice]}')
missing = MissingFK('supplier', 'Test Supplier', 'supplier_name', 5, [])
print(f'MissingFK: {missing}')
resolution = Resolution(ResolutionChoice.SKIP, 'supplier', 'Test Supplier')
print(f'Resolution: {resolution}')
"

# Verify session parameter pattern
grep -n "session.*=.*None" src/services/fk_resolver_service.py
grep -n "session.*=.*None" src/services/enhanced_import_service.py

# Verify CLI subparsers
grep -n "add_parser.*export-complete\|add_parser.*export-view\|add_parser.*validate-export\|add_parser.*import-view" src/utils/import_export_cli.py

# Verify menu item addition
grep -n "Import View" src/ui/main_window.py

# Run ALL tests to verify no regressions
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -40

# Run F030-specific tests
PYTHONPATH=. python3 -m pytest src/tests/services/test_coordinated_export.py -v --tb=short
PYTHONPATH=. python3 -m pytest src/tests/services/test_denormalized_export.py -v --tb=short
PYTHONPATH=. python3 -m pytest src/tests/services/test_fk_resolver.py -v --tb=short
PYTHONPATH=. python3 -m pytest src/tests/services/test_enhanced_import.py -v --tb=short
PYTHONPATH=. python3 -m pytest src/tests/utils/test_import_export_cli.py -v --tb=short

# Check test coverage for new services
PYTHONPATH=. python3 -m pytest src/tests/services/test_fk_resolver.py -v --cov=src.services.fk_resolver_service --cov-report=term-missing
PYTHONPATH=. python3 -m pytest src/tests/services/test_enhanced_import.py -v --cov=src.services.enhanced_import_service --cov-report=term-missing
```

## Key Implementation Patterns

### FK Resolver Protocol Pattern
```python
class FKResolverCallback(Protocol):
    """Protocol for FK resolution callbacks."""
    def resolve(self, missing: MissingFK) -> Resolution:
        """Resolve a missing FK reference."""
        ...
```

### Enhanced Import Result Pattern
```python
@dataclass
class EnhancedImportResult:
    base_result: ImportResult = field(default_factory=ImportResult)
    resolutions: List[Resolution] = field(default_factory=list)
    created_entities: Dict[str, int] = field(default_factory=dict)
    mapped_entities: Dict[str, int] = field(default_factory=dict)
    skipped_due_to_fk: int = 0
    dry_run: bool = False
    skipped_records_path: Optional[str] = None
```

### Session Parameter Pattern (per CLAUDE.md)
```python
def import_view(
    file_path: str,
    mode: str = "merge",
    dry_run: bool = False,
    skip_on_error: bool = False,
    resolver: Optional[FKResolverCallback] = None,
    session: Session = None,
) -> EnhancedImportResult:
    if session is not None:
        return _import_view_impl(file_path, mode, dry_run, skip_on_error, resolver, session)
    with session_scope() as session:
        return _import_view_impl(file_path, mode, dry_run, skip_on_error, resolver, session)
```

### CLI FK Resolver Pattern
```python
class CLIFKResolver:
    def resolve(self, missing: MissingFK) -> Resolution:
        print(f"\nMissing {missing.entity_type}: '{missing.missing_value}'")
        # Show options: [C] Create, [M] Map, [S] Skip
        choice = input("\nEnter choice (C/M/S): ").strip().upper()
        if choice == "C":
            return self._handle_create(missing)
        elif choice == "M":
            return self._handle_map(missing)
        elif choice == "S":
            return Resolution(choice=ResolutionChoice.SKIP, ...)
```

### Export Manifest Pattern
```python
@dataclass
class ExportManifest:
    export_date: str
    format_version: str
    files: List[ExportedFile]
    import_order: List[str]
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F030-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 030 - Enhanced Export/Import System

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 030-enhanced-export-import
**Branch:** 030-enhanced-export-import

## Summary

[Brief overview of findings]

## Verification Results

### Module Import Validation
- coordinated_export_service.py: [PASS/FAIL]
- denormalized_export_service.py: [PASS/FAIL]
- fk_resolver_service.py: [PASS/FAIL]
- enhanced_import_service.py: [PASS/FAIL]
- import_export_cli.py (CLI extensions): [PASS/FAIL]
- fk_resolution_dialog.py: [PASS/FAIL]
- import_export_dialog.py (ImportViewDialog): [PASS/FAIL]
- main_window.py (menu integration): [PASS/FAIL]

### Test Results
- Full test suite: [X passed, Y skipped, Z failed]
- Coordinated export tests: [X passed, Y failed]
- Denormalized export tests: [X passed, Y failed]
- FK resolver tests: [X passed, Y failed]
- Enhanced import tests: [X passed, Y failed]
- CLI tests: [X passed, Y failed]

### Code Pattern Validation
- FKResolverCallback protocol: [correct/issues found]
- Session parameter pattern: [present/missing in which files]
- EnhancedImportResult delegation: [correct/issues found]
- Modal dialog behavior: [correct/issues found]

## Findings

### Critical Issues
[Any blocking issues that must be fixed]

### Warnings
[Non-blocking concerns]

### Observations
[General observations about code quality]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/services/coordinated_export_service.py | [status] | [notes] |
| src/services/denormalized_export_service.py | [status] | [notes] |
| src/services/fk_resolver_service.py | [status] | [notes] |
| src/services/enhanced_import_service.py | [status] | [notes] |
| src/utils/import_export_cli.py | [status] | [notes] |
| src/ui/fk_resolution_dialog.py | [status] | [notes] |
| src/ui/import_export_dialog.py | [status] | [notes] |
| src/ui/main_window.py | [status] | [notes] |
| src/tests/services/test_coordinated_export.py | [status] | [notes] |
| src/tests/services/test_denormalized_export.py | [status] | [notes] |
| src/tests/services/test_fk_resolver.py | [status] | [notes] |
| src/tests/services/test_enhanced_import.py | [status] | [notes] |
| src/tests/utils/test_import_export_cli.py | [status] | [notes] |

## Architecture Assessment

### Layered Architecture
[Assessment of UI -> Services -> Models dependency flow]

### Session Management
[Assessment of session=None parameter pattern per CLAUDE.md]

### Protocol-Based Design
[Assessment of FKResolverCallback protocol and pluggable resolvers]

### Separation of Concerns
[Assessment of service/CLI/UI separation for import/export]

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: Export manifest with checksums | [PASS/FAIL] | [evidence] |
| FR-002: Entity dependency ordering | [PASS/FAIL] | [evidence] |
| FR-003: ZIP archive creation | [PASS/FAIL] | [evidence] |
| FR-004: Checksum validation | [PASS/FAIL] | [evidence] |
| FR-005: Products view export | [PASS/FAIL] | [evidence] |
| FR-006: Inventory view export | [PASS/FAIL] | [evidence] |
| FR-007: Purchases view export | [PASS/FAIL] | [evidence] |
| FR-008: Context fields for AI | [PASS/FAIL] | [evidence] |
| FR-009: Editable fields metadata | [PASS/FAIL] | [evidence] |
| FR-010: export-complete CLI | [PASS/FAIL] | [evidence] |
| FR-011: export-view CLI | [PASS/FAIL] | [evidence] |
| FR-012: validate-export CLI | [PASS/FAIL] | [evidence] |
| FR-013: FK resolution CREATE | [PASS/FAIL] | [evidence] |
| FR-014: FK resolution MAP | [PASS/FAIL] | [evidence] |
| FR-015: FK resolution SKIP | [PASS/FAIL] | [evidence] |
| FR-016: Fuzzy entity matching | [PASS/FAIL] | [evidence] |
| FR-017: import-view CLI | [PASS/FAIL] | [evidence] |
| FR-018: --interactive flag | [PASS/FAIL] | [evidence] |
| FR-019: --dry-run flag | [PASS/FAIL] | [evidence] |
| FR-020: --skip-on-error flag | [PASS/FAIL] | [evidence] |
| FR-021: Merge mode | [PASS/FAIL] | [evidence] |
| FR-022: Skip existing mode | [PASS/FAIL] | [evidence] |
| FR-023: FK resolution dialog | [PASS/FAIL] | [evidence] |
| FR-024: Create entity forms | [PASS/FAIL] | [evidence] |
| FR-025: Map entity search | [PASS/FAIL] | [evidence] |
| FR-026: Import View menu item | [PASS/FAIL] | [evidence] |
| FR-027: Import results dialog | [PASS/FAIL] | [evidence] |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Coordinated Export Service | [PASS/FAIL] | [notes] |
| WP02: Denormalized Export Service | [PASS/FAIL] | [notes] |
| WP03: Export CLI Commands | [PASS/FAIL] | [notes] |
| WP04: FK Resolver Service | [PASS/FAIL] | [notes] |
| WP05: Enhanced Import Service | [PASS/FAIL] | [notes] |
| WP06: Import CLI Commands | [PASS/FAIL] | [notes] |
| WP07: FK Resolution Dialog | [PASS/FAIL] | [notes] |
| WP08: UI Integration | [PASS/FAIL] | [notes] |

## Test Coverage Assessment

| Test File | Tests | Coverage | Notes |
|-----------|-------|----------|-------|
| test_coordinated_export.py | [count] | [%] | [notes] |
| test_denormalized_export.py | [count] | [%] | [notes] |
| test_fk_resolver.py | [count] | [%] | [notes] |
| test_enhanced_import.py | [count] | [%] | [notes] |
| test_import_export_cli.py | [count] | [%] | [notes] |

## Multi-Agent Coordination Assessment

| Agent | Work Packages | Status | Notes |
|-------|---------------|--------|-------|
| Gemini | WP01, WP02, WP03 | [status] | [notes] |
| Claude | WP04, WP05, WP06, WP07, WP08 | [status] | [notes] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing with pytest-cov for coverage
- The worktree is isolated from main branch at `.worktrees/030-enhanced-export-import`
- Layered architecture: UI -> Services -> Models -> Database
- Session management pattern: functions accept `session=None` per CLAUDE.md
- This feature was implemented using multi-agent orchestration:
  - Gemini CLI handled export services (WP01-WP03)
  - Claude Code handled import services and UI (WP04-WP08)
- 70%+ coverage target for service layer
- All existing tests must pass (no regressions) - currently 1329 passed, 12 skipped
- 3 pre-existing test failures in denormalized export tests (decimal formatting)
- Feature adds new CLI commands to existing import_export_cli.py
- Interactive FK resolution is default for UI, fail-fast is default for CLI
