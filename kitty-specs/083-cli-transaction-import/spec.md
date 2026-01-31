# Feature Specification: CLI Transaction Import Commands

**Feature Branch**: `083-cli-transaction-import`
**Created**: 2026-01-28
**Status**: Draft
**Input**: F083 CLI Transaction Import Parity - Add CLI commands for transaction import (purchases, adjustments) with schema validation and FK resolution modes to enable mobile AI workflows.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import Purchase Transactions (Priority: P1)

As an AI workflow system, I need to import purchase transaction data from JSON files so that receipt scanning results can be added to the database without UI interaction.

**Why this priority**: Core capability that enables mobile AI receipt scanning workflow. Without this, AI-generated purchase data cannot enter the system.

**Independent Test**: Can be tested by creating a valid purchases JSON file and running `app import-purchases purchases.json`. Success means purchase records appear in database.

**Acceptance Scenarios**:

1. **Given** a valid purchases JSON file, **When** user runs `app import-purchases purchases.json`, **Then** purchase records are created in database with success message
2. **Given** a purchases JSON file with FK references, **When** user runs with `--resolve-mode=auto`, **Then** FK conflicts are automatically resolved using best-match
3. **Given** any purchases JSON file, **When** user runs with `--dry-run`, **Then** validation occurs but no database changes are made
4. **Given** a valid file and `--json` flag, **When** import completes, **Then** structured JSON output shows import counts and resolution log

---

### User Story 2 - Import Inventory Adjustments (Priority: P1)

As an AI workflow system, I need to import inventory adjustment data from JSON files so that AI-assisted inventory counts can update the database without UI interaction.

**Why this priority**: Core capability that enables mobile AI inventory counting workflow. Equal priority to purchases as both are essential for mobile AI.

**Independent Test**: Can be tested by creating a valid adjustments JSON file and running `app import-adjustments adjustments.json`. Success means inventory adjustments are applied.

**Acceptance Scenarios**:

1. **Given** a valid adjustments JSON file, **When** user runs `app import-adjustments adjustments.json`, **Then** inventory adjustments are applied with success message
2. **Given** adjustments with valid reason codes (RECOUNT, WASTE, CORRECTION), **When** import runs, **Then** adjustments are accepted
3. **Given** adjustments with invalid reason codes, **When** import runs, **Then** clear error message identifies invalid codes
4. **Given** any adjustments JSON file, **When** user runs with `--dry-run`, **Then** validation occurs but no database changes are made

---

### User Story 3 - Pre-Validate Import Files (Priority: P2)

As an AI workflow system, I need to validate JSON files before import so that errors can be caught and corrected before committing data.

**Why this priority**: Prevents failed imports and enables AI to self-correct. Important but not blocking core functionality.

**Independent Test**: Can be tested by running `app validate-import file.json --type=purchase` on valid and invalid files. Success means accurate validation without database changes.

**Acceptance Scenarios**:

1. **Given** a valid purchases JSON file, **When** user runs `app validate-import file.json --type=purchase`, **Then** validation passes with success message
2. **Given** an invalid JSON file, **When** user runs validate-import, **Then** error messages include field paths and error types
3. **Given** any file, **When** validate-import runs, **Then** no database operations occur (validation only)
4. **Given** `--json` flag, **When** validation completes, **Then** structured JSON output is machine-parseable

---

### User Story 4 - FK Resolution Mode Selection (Priority: P2)

As a user or AI system, I need to choose how FK conflicts are resolved so that I can balance automation vs manual control.

**Why this priority**: Enables flexible workflows - human interactive mode vs AI automatic mode. Important for AI integration.

**Independent Test**: Can be tested by importing a file with unresolved FKs using each mode (interactive, auto, strict). Success means each mode behaves differently as expected.

**Acceptance Scenarios**:

1. **Given** FK conflicts and `--resolve-mode=interactive`, **When** import runs, **Then** user is prompted for each conflict (existing behavior)
2. **Given** FK conflicts and `--resolve-mode=auto`, **When** import runs, **Then** best-match is used without prompting
3. **Given** FK conflicts and `--resolve-mode=strict`, **When** import runs, **Then** import fails on first unresolvable FK
4. **Given** any resolution mode, **When** import completes, **Then** resolution log shows all FK decisions made

---

### Edge Cases

- What happens when JSON file is empty or malformed? Clear error message with parse failure details.
- What happens when all FKs fail resolution in strict mode? Import stops with list of unresolvable FKs.
- What happens when product_slug references non-existent product? FK resolver attempts match or reports error.
- What happens when adjustment reason code is missing? Validation error with field path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide `app import-purchases <file>` CLI command that uses existing transaction_import_service.import_purchases()
- **FR-002**: System MUST provide `app import-adjustments <file>` CLI command that uses existing transaction_import_service.import_adjustments()
- **FR-003**: System MUST provide `app validate-import <file> --type={purchase|adjustment}` command that validates without database changes
- **FR-004**: All transaction import commands MUST support `--dry-run` flag for validation without database changes
- **FR-005**: All transaction import commands MUST support `--resolve-mode={interactive|auto|strict}` flag for FK resolution
- **FR-006**: All transaction import commands MUST support `--json` flag for machine-parseable output
- **FR-007**: JSON output MUST include import counts (success, skipped, errors), FK resolution log, and validation errors with field paths
- **FR-008**: CLI commands MUST reuse existing service layer implementations (no duplicate business logic)
- **FR-009**: CLI command patterns MUST match existing catalog import commands for consistency

### Key Entities

- **Purchase Transaction**: Purchase record with supplier, product references, quantities, costs
- **Inventory Adjustment**: Adjustment record with product reference, quantity change, reason code (RECOUNT, WASTE, CORRECTION)
- **FK Resolution Log**: Record of field name, input value, resolved value, resolution mode used

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 3 new CLI commands (import-purchases, import-adjustments, validate-import) are functional and documented
- **SC-002**: CLI import behavior matches UI import behavior exactly (same service layer)
- **SC-003**: JSON output format enables AI systems to parse results and provide user feedback
- **SC-004**: Dry-run mode performs zero database writes while providing accurate validation
- **SC-005**: All 3 FK resolution modes (interactive, auto, strict) behave correctly per specification
- **SC-006**: CLI help text documents all flags, modes, and expected JSON format

## Assumptions

- Existing transaction_import_service.py provides import_purchases() and import_adjustments() methods
- Existing FKResolverCallback pattern can be extended for auto and strict modes
- JSON input format follows existing export format patterns
- CLI entry point is `app` (via import_export_cli.py)

## Dependencies

- transaction_import_service.py (existing)
- schema_validation_service.py (existing, if available)
- import_export_cli.py (existing CLI infrastructure)
- FKResolverCallback (existing FK resolution mechanism)

## Out of Scope

- Batch import of multiple files
- UI changes
- New import service logic (reuse existing)
- Receipt OCR/scanning (AI generates JSON externally)
- Import history tracking
- Rollback/undo commands
