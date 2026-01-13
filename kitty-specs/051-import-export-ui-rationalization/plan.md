# Implementation Plan: Import/Export UI Rationalization

**Branch**: `051-import-export-ui-rationalization` | **Date**: 2026-01-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/051-import-export-ui-rationalization/spec.md`

## Summary

Consolidate three separate import menu options (Import Data, Import Catalog, Import Context-Rich) into a single unified Import Data dialog with 5 purpose types (Backup, Catalog, Purchases, Adjustments, Context-Rich). Add supplier import/export support, pre-import schema validation, comprehensive logging, and configurable directory preferences. The dialog follows a file-first flow where users select a file, the system auto-detects the appropriate purpose, and users can override if needed.

## Technical Context

**Language/Version**: Python 3.10+ (minimum for type hints)
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM), pytest (testing)
**Storage**: SQLite with WAL mode (local database)
**Testing**: pytest with >70% service layer coverage required
**Target Platform**: Desktop (macOS, Windows, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Import operations complete within reasonable time for typical file sizes (<10MB)
**Constraints**: Must not break existing import/export workflows; layered architecture (UI -> Services -> Models)
**Scale/Scope**: Single user, local database, files typically contain 10-1000 records

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Unified dialog reduces confusion; file-first flow intuitive |
| II. Data Integrity & FIFO | PASS | No changes to FIFO logic; validation prevents corrupt imports |
| III. Future-Proof Schema | PASS | app_config uses existing pattern; no schema changes needed |
| IV. Test-Driven Development | PASS | New schema_validation_service requires unit tests |
| V. Layered Architecture | PASS | UI orchestrates, services handle logic, no cross-layer violations |
| VI. Schema Change Strategy | PASS | No migration required; app_config survives DB reset by design |
| VII. Pragmatic Aspiration | PASS | Supports AI-assisted JSON import; service layer UI-independent |

**Phase-Specific Checks (Desktop Phase):**
- Does this design block web deployment? NO - Service layer remains UI-independent
- Is the service layer UI-independent? YES - All business logic in services
- Does this support AI-assisted JSON import? YES - Enhanced validation helps AI-generated files
- What's the web migration cost? LOW - Services become API endpoints with minimal refactoring

## Project Structure

### Documentation (this feature)

```
kitty-specs/051-import-export-ui-rationalization/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── tasks.md             # Phase 2 output (via /spec-kitty.tasks)
└── tasks/               # Individual work packages
```

### Source Code (repository root)

```
src/
├── models/
│   └── (no changes - app_config already exists)
├── services/
│   ├── schema_validation_service.py    # NEW: JSON schema validation
│   ├── import_export_service.py        # MODIFY: Enhanced logging, supplier export
│   ├── catalog_import_service.py       # MODIFY: Add suppliers to VALID_ENTITIES
│   ├── enhanced_import_service.py      # MODIFY: Context-Rich improvements
│   └── preferences_service.py          # NEW: Directory preferences management
├── ui/
│   ├── import_export_dialog.py         # MODIFY: Unified import dialog with 5 purposes
│   └── preferences_dialog.py           # NEW: Preferences dialog for directories
└── tests/
    ├── test_schema_validation_service.py  # NEW
    ├── test_preferences_service.py        # NEW
    └── (existing import tests updated)
```

**Structure Decision**: Single project structure. Feature extends existing services and UI components following established patterns.

## Complexity Tracking

*No constitution violations requiring justification.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | N/A        | N/A                                 |

## Implementation Approach

### Service Layer Changes

1. **schema_validation_service.py** (NEW)
   - Reusable JSON structure validation
   - Validates required fields, field types, array structure
   - Returns structured validation results with record numbers and expected vs actual
   - Used by all import purposes (after preprocessing for Context-Rich)

2. **preferences_service.py** (NEW)
   - CRUD for app_config directory preferences
   - Keys: `import_directory`, `export_directory`, `logs_directory`
   - Handles missing directories gracefully (fall back to system default)

3. **import_export_service.py** (MODIFY)
   - Add `export_suppliers()` function
   - Enhance `_write_import_log()` with comprehensive sections:
     - SOURCE, OPERATION, PREPROCESSING, SCHEMA VALIDATION
     - IMPORT RESULTS, ERRORS, WARNINGS, SUMMARY, METADATA
   - Include resolution suggestions in error entries

4. **catalog_import_service.py** (MODIFY)
   - Add `suppliers` to `VALID_ENTITIES`
   - Add `import_suppliers()` function following existing patterns
   - Include supplier in dependency order (before products)

5. **enhanced_import_service.py** (MODIFY)
   - Update `detect_format()` to recognize supplier files
   - Ensure Context-Rich preprocessing ignores read-only context fields
   - Schema validation runs after preprocessing using Catalog schemas

### UI Layer Changes

1. **import_export_dialog.py** (MODIFY)
   - ImportDialog: Add 5th purpose option "Context-Rich"
   - ImportDialog: Update auto-detection to suggest Context-Rich for aug_*.json
   - ExportDialog: Add "Suppliers" checkbox to Catalog tab (alphabetically ordered)
   - ImportResultsDialog: Display modal summary with counts per entity
   - Remove: Import Catalog menu item handling
   - Remove: Import Context-Rich menu item handling

2. **preferences_dialog.py** (NEW)
   - File > Preferences menu opens this dialog
   - Directory pickers for Import, Export, Logs
   - "Restore Defaults" button
   - Persists to app_config table

3. **Menu updates** (main_window.py or equivalent)
   - Remove "Import Catalog" menu item
   - Remove "Import Context-Rich" menu item
   - Add "Preferences..." menu item under File

### Validation Sequence

For standard imports (Backup, Catalog, Purchases, Adjustments):
1. Load JSON file
2. Run schema validation
3. Execute import

For Context-Rich imports:
1. Load JSON file
2. Run preprocessing (convert to normalized, validate FK references)
3. Run schema validation on preprocessed output (same schemas as Catalog)
4. Execute import

### Import Dialog Flow

1. User opens Import Data dialog (single menu item)
2. User clicks Browse, selects file
3. System auto-detects format, suggests purpose
4. User can override purpose selection
5. For Catalog/Context-Rich: mode selection appears (Update Existing / Add New Only)
6. User clicks Import
7. Validation runs (schema validation, FK validation for Context-Rich)
8. If validation fails: Error dialog with actionable messages
9. If validation passes: Import executes
10. Modal summary dialog shows counts (imported/skipped/failed per entity)
11. Log file written to configured directory

## Risk Mitigation

1. **Regression Risk**: Existing import tests must pass; add integration tests for unified dialog
2. **Context-Rich Complexity**: Single-entity only simplifies implementation
3. **Log Directory Access**: Service handles permission errors gracefully with user feedback

## Dependencies Between Work Packages

```
WP01: schema_validation_service.py (independent)
WP02: preferences_service.py (independent)
WP03: preferences_dialog.py (depends on WP02)
WP04: Enhanced logging (depends on WP02 for log directory)
WP05: Supplier export (independent)
WP06: Supplier import (depends on WP05 for testing)
WP07: Unified import dialog (depends on WP01, WP04)
WP08: Context-Rich as 5th purpose (depends on WP07)
WP09: Menu cleanup (depends on WP07, WP08)
WP10: Integration tests (depends on all above)
```
