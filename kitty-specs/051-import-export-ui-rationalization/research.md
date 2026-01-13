# Research: Import/Export UI Rationalization

**Feature**: 051-import-export-ui-rationalization
**Date**: 2026-01-13
**Status**: Complete

## Executive Summary

This feature consolidates three separate import menu options into a single unified dialog. Research confirmed that the existing service layer architecture can support this consolidation with minimal new code. Key decisions involve extending existing services rather than creating new orchestration layers.

## Key Decisions

### Decision 1: Service Layer Architecture

**Decision**: Extend existing services rather than create new orchestration layer

**Rationale**:
- Existing `import_export_service.py`, `catalog_import_service.py`, `enhanced_import_service.py`, and `transaction_import_service.py` already handle distinct import types
- Each service follows the same patterns (ImportResult, session handling, error reporting)
- UI layer (`ImportDialog`) can orchestrate between services based on purpose selection
- Lower regression risk than consolidating into new unified service

**Alternatives Considered**:
1. Create `unified_import_service.py` - Rejected: adds indirection, increases maintenance burden
2. Consolidate all into single service - Rejected: high regression risk, complex merge

**Evidence**: Code review of existing services (see `src/services/import_export_service.py:50-247`, `src/services/catalog_import_service.py`, `src/ui/import_export_dialog.py:178-731`)

### Decision 2: Schema Validation Service

**Decision**: Create new `schema_validation_service.py` for reusable JSON validation

**Rationale**:
- Validation logic currently scattered across multiple import functions
- Reusable service allows consistent validation across all import purposes
- Returns structured results enabling actionable error messages
- Service-layer location maintains layered architecture

**Implementation Pattern**:
```python
@dataclass
class ValidationResult:
    valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]

def validate_catalog_schema(data: dict) -> ValidationResult:
    """Validate catalog import JSON structure."""
    ...
```

### Decision 3: Import Dialog Flow (File-First)

**Decision**: File-first flow with auto-detection and override capability

**Rationale**:
- User clarification confirmed file-first is preferred workflow
- Auto-detection provides convenience; override ensures flexibility
- Matches existing `detect_format()` function in `enhanced_import_service.py`

**Flow**:
1. User selects file via Browse button
2. `detect_format()` analyzes JSON structure
3. UI suggests purpose based on detection
4. User can override if detection incorrect
5. Purpose-specific options appear (mode, etc.)

### Decision 4: Context-Rich Validation Sequence

**Decision**: Schema validation runs AFTER preprocessing for Context-Rich files

**Rationale**:
- User clarification: Preprocessing converts aug_*.json to normalized format
- Normalized format uses same schemas as Catalog imports
- Avoids maintaining separate schemas for denormalized aug format
- FK validation happens during preprocessing (existing behavior)

**Sequence**:
1. Load aug_*.json
2. Preprocess: extract editable fields, validate FK references
3. Schema validate preprocessed output using Catalog schemas
4. Execute import

### Decision 5: Import Log Format

**Decision**: Plain text with human-readable header-separated sections

**Rationale**:
- User clarification confirmed plain text preferred
- Headers improve scanability for human review
- No external tooling needs machine-parseable logs currently

**Sections**: SOURCE, OPERATION, PREPROCESSING, SCHEMA VALIDATION, IMPORT RESULTS, ERRORS, WARNINGS, SUMMARY, METADATA

### Decision 6: Preferences Storage

**Decision**: Use existing `app_config` table for directory preferences

**Rationale**:
- `app_config` already exists in schema (Feature 050 added it)
- Key-value pattern suits directory preferences
- Survives DB reset (by design per constitution)
- No schema migration required

**Keys**: `import_directory`, `export_directory`, `logs_directory`

### Decision 7: Supplier Import/Export

**Decision**: Add suppliers to catalog import/export following existing patterns

**Rationale**:
- Suppliers referenced by Products (FK relationship)
- Import order: suppliers before products (dependency order)
- Export: add checkbox to Catalog tab (alphabetical with other entities)

**Implementation**:
- Add `suppliers` to `VALID_ENTITIES` in `catalog_import_service.py`
- Add `export_suppliers()` to `import_export_service.py`
- Update `ExportDialog` Catalog tab checkbox list

## Existing Code Analysis

### Current Import Services

| Service | Responsibility | Import Types |
|---------|---------------|--------------|
| `import_export_service.py` | Core import/export, backup restore | Normalized backup, single-entity |
| `catalog_import_service.py` | Catalog entity import (add/augment) | ingredients, products, recipes, materials, material_products |
| `enhanced_import_service.py` | Context-rich view import, FK resolution | aug_*.json denormalized views |
| `transaction_import_service.py` | Purchase and adjustment transactions | purchases, adjustments |
| `coordinated_export_service.py` | Multi-file backup export/import | manifest-based coordinated |

### Current UI Structure

| Dialog | Location | Purpose |
|--------|----------|---------|
| `ImportDialog` | `import_export_dialog.py:178` | 4-purpose import (Backup, Catalog, Purchases, Adjustments) |
| `ExportDialog` | `import_export_dialog.py:733` | 3-tab export (Full Backup, Catalog, Context-Rich) |
| `ImportResultsDialog` | `import_export_dialog.py:62` | Display import results with summary |
| `ImportViewDialog` | `import_export_dialog.py:1148` | Context-rich import (separate) |

### Format Detection

`enhanced_import_service.py:260-300` contains `detect_format()` function:
- Detects: context_rich, normalized, purchases, adjustments, unknown
- Returns `FormatDetectionResult` with metadata
- Already integrated into `ImportDialog._detect_format()`

## Open Questions (Resolved)

All questions resolved during clarification phase:

1. Dialog sequencing? - File-first with auto-detection
2. Context-Rich multi-entity? - Single-entity only, ignore context fields
3. Log format? - Plain text with headers
4. Validation sequence for Context-Rich? - After preprocessing
5. Success feedback? - Modal dialog with per-entity counts

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Regression in existing imports | Medium | High | Full test coverage, integration tests |
| Context-Rich preprocessing edge cases | Low | Medium | Reuse existing preprocessing, add validation |
| Permission errors on log directory | Low | Low | Graceful fallback to system temp |

## References

- Spec: `kitty-specs/051-import-export-ui-rationalization/spec.md`
- Constitution: `.kittify/memory/constitution.md`
- Existing services: `src/services/import_export_service.py`, `src/services/catalog_import_service.py`, `src/services/enhanced_import_service.py`
- Existing UI: `src/ui/import_export_dialog.py`
