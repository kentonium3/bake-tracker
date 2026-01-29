# F083: CLI Transaction Import Parity

**Version**: 1.0
**Priority**: HIGH
**Type**: CLI Enhancement

---

## Executive Summary

CLI import/export tools lack parity with UI transaction import services, blocking mobile AI-assisted input prototyping.

Current gaps:
- ❌ Can't import AI-scanned receipts via CLI (purchase import missing)
- ❌ Can't import AI-assisted inventory counts via CLI (adjustment import missing)
- ❌ Can't pre-validate JSON before commit (schema validation missing)
- ❌ Can't guide AI through FK conflicts (interactive resolution modes missing)

This spec adds CLI commands for transaction import (purchases, adjustments) with schema validation and enhanced FK resolution modes to enable mobile AI workflows.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
CLI Import/Export (src/utils/import_export_cli.py)
├─ ✅ Full backup/restore (16 entities)
├─ ✅ Catalog import (ingredients, products, recipes, etc.)
├─ ✅ Context-rich exports with _meta.editable_fields
├─ ✅ Dry-run validation for catalog
└─ ❌ Transaction import
    ├─ ❌ Purchase import (UI service exists, no CLI)
    ├─ ❌ Adjustment import (UI service exists, no CLI)
    ├─ ❌ Schema validation (UI service exists, no CLI)
    └─ ❌ FK resolution modes (only basic interactive, no auto/strict)

Mobile AI Workflow (BLOCKED)
├─ ❌ Can't import scanned receipt JSON
├─ ❌ Can't import inventory count JSON
├─ ❌ Can't pre-validate before import
└─ ❌ Can't automate FK resolution for AI
```

**Target State (COMPLETE):**
```
CLI Import/Export
├─ ✅ Full backup/restore
├─ ✅ Catalog import
├─ ✅ Context-rich exports
└─ ✅ Transaction import
    ├─ ✅ Purchase import with dry-run
    ├─ ✅ Adjustment import with dry-run
    ├─ ✅ Schema validation command
    └─ ✅ FK resolution modes (interactive/auto/strict)

Mobile AI Workflow (ENABLED)
├─ ✅ Photo receipt → AI JSON → validate → import
├─ ✅ Inventory count → AI JSON → validate → import
├─ ✅ Pre-validation without database changes
└─ ✅ AI-guided FK resolution
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **UI Transaction Import Service**
   - Find `src/services/transaction_import_service.py`
   - Study `import_purchases()` method - this is the implementation to reuse
   - Study `import_adjustments()` method - this is the implementation to reuse
   - Note FK resolution callback mechanism (`FKResolverCallback`)

2. **UI Schema Validation Service**
   - Find `src/services/schema_validation_service.py`
   - Study validation methods - these determine import vs validation modes
   - Note error message structure for AI parsing

3. **Existing CLI Import/Export**
   - Find `src/utils/import_export_cli.py`
   - Study command structure and argument patterns
   - Study existing dry-run implementation
   - Note output formatting (human vs JSON)

4. **FK Resolver Implementation**
   - Find `FKResolverCallback` class (likely in transaction_import_service.py)
   - Study interactive prompt mechanism
   - Note how best-match suggestions work
   - Understand conflict resolution flow

---

## Requirements Reference

This specification enables:
- **Mobile AI Vision**: Voice/visual recipe entry use cases (Phase 2)
- **CLI/UI Parity**: Constitutional principle of AI configurability through CLI access
- **Data Portability**: AI-generated data must be importable via CLI

From: `docs/.kittify/memory/constitution.md` (AI configurability principle)

---

## Functional Requirements

### FR-1: Purchase Import Command

**What it must do:**
- Add `app import-purchases <file>` CLI command
- Use existing `transaction_import_service.import_purchases()` (DO NOT reimplement)
- Support `--dry-run` flag for validation without database changes
- Support `--resolve-mode` flag for FK conflict handling
- Return structured errors for AI parsing when `--json` flag present

**Pattern reference:** Study how `app import-catalog` command works in `import_export_cli.py`, copy structure for transaction import

**Success criteria:**
- [ ] Command `app import-purchases receipt.json` imports purchase data
- [ ] `--dry-run` validates without database changes
- [ ] `--resolve-mode` supports interactive/auto/strict modes
- [ ] `--json` outputs machine-parseable results
- [ ] Reuses existing transaction_import_service (no duplicate logic)

---

### FR-2: Adjustment Import Command

**What it must do:**
- Add `app import-adjustments <file>` CLI command
- Use existing `transaction_import_service.import_adjustments()` (DO NOT reimplement)
- Support `--dry-run` flag for validation
- Support `--resolve-mode` flag for FK conflict handling
- Validate reason codes match system defaults (RECOUNT, WASTE, CORRECTION)

**Pattern reference:** Copy FR-1 purchase import pattern exactly, replace with adjustment service calls

**Success criteria:**
- [ ] Command `app import-adjustments count.json` imports adjustment data
- [ ] `--dry-run` validates without database changes
- [ ] Reason code validation works correctly
- [ ] FK resolution modes work for adjustments
- [ ] Reuses existing transaction_import_service

---

### FR-3: Schema Validation Command

**What it must do:**
- Add `app validate-import <file> --type={catalog|purchase|adjustment}` command
- Use existing `schema_validation_service` for validation
- Perform NO database operations (validation only)
- Return structured error messages for AI parsing
- Support `--json` flag for machine-readable output

**Pattern reference:** Study how schema_validation_service is used, expose via CLI wrapper

**Business rules:**
- Validation must match UI service validation exactly
- Validation errors must include field paths for AI guidance
- Must detect missing required fields, type errors, FK references

**Success criteria:**
- [ ] Command validates JSON structure without database changes
- [ ] Error messages include field paths and error types
- [ ] `--json` output is machine-parseable
- [ ] Validation matches UI service behavior exactly

---

### FR-4: Enhanced FK Resolution Modes

**What it must do:**
- Extend FK resolution to support three modes:
  - `interactive`: Prompt user for choices (existing behavior, default)
  - `auto`: Use best-match suggestions without prompting (new)
  - `strict`: Fail on any FK conflict without resolution (new)
- Add `--resolve-mode` flag to import commands
- Output structured resolution log showing what was resolved and how

**Pattern reference:** Study existing `FKResolverCallback` interactive prompts, extend with auto and strict modes

**Business rules:**
- `interactive` mode is default (backward compatible)
- `auto` mode uses best-match algorithm from existing resolver
- `strict` mode stops on first unresolvable FK
- Resolution log must show: field name, input value, resolved value (or error)

**Success criteria:**
- [ ] `--resolve-mode=interactive` prompts user (existing behavior)
- [ ] `--resolve-mode=auto` uses best-match without prompting
- [ ] `--resolve-mode=strict` fails on FK conflicts
- [ ] Resolution log shows all FK resolution decisions
- [ ] `--json` output includes resolution log

---

### FR-5: Structured JSON Output

**What it must do:**
- Add `--json` flag to all transaction import commands
- Output machine-parseable JSON result structure
- Include import counts (success, skipped, errors)
- Include FK resolution log
- Include validation errors with field paths

**Pattern reference:** Study existing CLI JSON output patterns if any, or design minimal structure for AI consumption

**JSON Output Structure:**
```json
{
  "success": true,
  "imported": 3,
  "skipped": 1,
  "errors": [
    {"field": "items[0].material_slug", "error": "Material not found: 'unknown'"}
  ],
  "resolutions": [
    {"field": "supplier_id", "input": "Costco", "resolved": "SUP-001", "mode": "auto"}
  ]
}
```

**Success criteria:**
- [ ] `--json` flag outputs structured results
- [ ] JSON includes all import statistics
- [ ] JSON includes FK resolution log
- [ ] JSON includes validation errors with field paths
- [ ] JSON output is valid and parseable

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Batch import of multiple files - single file import only
- ❌ UI changes - CLI only enhancement
- ❌ New transaction import service logic - reuse existing
- ❌ Receipt OCR/scanning - AI generates JSON externally
- ❌ Import history tracking - future enhancement
- ❌ Rollback/undo commands - future enhancement

---

## Success Criteria

**Complete when:**

### Purchase Import
- [ ] `app import-purchases receipt.json` imports purchase data using transaction_import_service
- [ ] `app import-purchases receipt.json --dry-run` validates without database changes
- [ ] `app import-purchases receipt.json --resolve-mode=auto --json` outputs structured results
- [ ] Purchase import matches UI service behavior exactly

### Adjustment Import
- [ ] `app import-adjustments count.json` imports adjustment data using transaction_import_service
- [ ] `app import-adjustments count.json --dry-run` validates without database changes
- [ ] Reason code validation works correctly
- [ ] Adjustment import matches UI service behavior exactly

### Schema Validation
- [ ] `app validate-import data.json --type=purchase` validates structure only
- [ ] Validation errors include field paths
- [ ] No database operations occur during validation
- [ ] Validation matches UI service validation exactly

### FK Resolution
- [ ] `--resolve-mode=interactive` prompts user (default, backward compatible)
- [ ] `--resolve-mode=auto` uses best-match without prompting
- [ ] `--resolve-mode=strict` fails on FK conflicts
- [ ] Resolution log shows all FK decisions

### JSON Output
- [ ] `--json` flag outputs machine-parseable results
- [ ] JSON includes import counts, errors, resolutions
- [ ] JSON structure supports AI parsing

### Quality
- [ ] All commands reuse existing service layer (no duplicate logic)
- [ ] Error messages are clear and actionable
- [ ] CLI help text documents all flags and modes
- [ ] Pattern consistency with existing CLI commands

---

## Architecture Principles

### Service Layer Reuse

**Principle: CLI as Thin Wrapper**
- CLI commands MUST reuse existing transaction_import_service methods
- CLI commands MUST NOT reimplement import logic
- CLI provides argument parsing and output formatting only

**Rationale:** Maintains single source of truth for business logic, ensures CLI/UI parity

### FK Resolution Architecture

**Principle: Mode-Based Resolution Strategy**
- Three modes: interactive (user-driven), auto (AI-friendly), strict (fail-fast)
- Modes share same FK resolver implementation, differ only in decision logic
- Resolution log captures all decisions for auditability

**Rationale:** Supports both human workflows (interactive) and AI workflows (auto) without duplicate code

### Pattern Matching

**Transaction Import CLI must match Catalog Import CLI exactly:**
- Same argument structure (file path as positional argument)
- Same flag naming (`--dry-run`, `--json`)
- Same error handling approach
- Same output formatting conventions

---

## Constitutional Compliance

✅ **Principle: AI Configurability**
- CLI provides programmatic access to all import functionality
- Enables mobile AI workflows (voice/visual input)
- Supports automation and scripting

✅ **Principle: CLI/UI Feature Parity**
- All UI transaction import capabilities available via CLI
- Same validation rules and business logic
- Same service layer implementation

✅ **Principle: Service Layer Discipline**
- CLI reuses existing transaction_import_service
- No duplicate business logic in CLI layer
- Clear separation: CLI = presentation, Service = business logic

---

## Risk Considerations

**Risk: FK Resolution Mode Complexity**
- Three resolution modes increase testing surface
- Mitigation: Modes share same resolver implementation, differ only in decision strategy; extensive testing of mode switching

**Risk: JSON Output Breaking Changes**
- Future schema changes could break AI parsers
- Mitigation: Version JSON output structure if schema changes needed; document structure clearly

**Risk: Import Service Dependency**
- CLI depends on transaction_import_service stability
- Mitigation: Service layer is stable and well-tested; CLI reuse ensures any service fixes benefit both CLI and UI

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `import_export_cli.py` → understand CLI command structure
- Study `transaction_import_service.py` → understand import methods to wrap
- Study `FKResolverCallback` → understand how to extend with auto/strict modes
- Study `schema_validation_service.py` → understand validation to expose

**Key Patterns to Copy:**
- Catalog import CLI pattern → Transaction import CLI pattern (exact parallel)
- Existing dry-run implementation → Apply to transaction import
- Existing JSON output (if any) → Apply to transaction import results

**Focus Areas:**
- FK resolver mode implementation (interactive/auto/strict)
- JSON output structure for AI consumption
- Error message clarity for AI parsing
- CLI argument consistency with existing commands

**Mobile AI Workflow Integration:**
This CLI enables future mobile AI workflows:
1. User photographs receipt
2. External AI service extracts data → generates purchase JSON
3. CLI validates: `app validate-import receipt.json --type=purchase`
4. CLI imports: `app import-purchases receipt.json --resolve-mode=auto --json`
5. AI parses JSON results → provides user feedback

Similar workflow for inventory counting with adjustment import.

---

**END OF SPECIFICATION**
