# Tasks: CLI Transaction Import Commands

**Feature**: 082-cli-transaction-import
**Created**: 2026-01-28
**Status**: Planning Complete

## Overview

Add CLI commands for transaction import (purchases, adjustments) with validation and FK resolution modes.

**Total Subtasks**: 13
**Work Packages**: 4

## Work Package Summary

| WP | Title | Subtasks | Priority | Dependencies | Est. Lines |
|----|-------|----------|----------|--------------|------------|
| WP01 | Service Layer Extension | T001-T003 | P1 | None | ~300 |
| WP02 | Purchase Import CLI | T004-T006 | P1 | WP01 | ~350 |
| WP03 | Adjustment & Validate CLI | T007-T010 | P1 | WP01 | ~400 |
| WP04 | CLI Tests | T011-T013 | P2 | WP02, WP03 | ~350 |

## Parallelization

- WP02 and WP03 can run in parallel after WP01 completes
- WP04 requires both WP02 and WP03

```
WP01 (foundation)
  ├── WP02 (purchase CLI) ──┐
  └── WP03 (adjust/validate)├── WP04 (tests)
```

---

## Phase 1: Foundation

### WP01 – Service Layer Extension

**Goal**: Add strict_mode parameter to transaction import services and create JSON output helper.

**Priority**: P1 (foundation for all CLI commands)

**Prompt**: [WP01-service-layer-extension.md](tasks/WP01-service-layer-extension.md)

**Subtasks**:
- [ ] T001: Add `strict_mode` parameter to `import_purchases()` [P]
- [ ] T002: Add `strict_mode` parameter to `import_adjustments()` [P]
- [ ] T003: Add `result_to_json()` helper function

**Implementation Notes**:
- Modify transaction_import_service.py to accept strict_mode parameter
- In strict mode, return early on first FK resolution failure
- JSON helper converts ImportResult to structured dict for --json output

**Dependencies**: None

**Risks**: Changes to existing service signatures require careful backward compatibility

---

## Phase 2: CLI Commands

### WP02 – Purchase Import CLI

**Goal**: Add `import-purchases` command to CLI with full flag support.

**Priority**: P1 (User Story 1 - core capability)

**Prompt**: [WP02-purchase-import-cli.md](tasks/WP02-purchase-import-cli.md)

**Subtasks**:
- [ ] T004: Add `import-purchases` CLI parser
- [ ] T005: Implement `import_purchases_cmd()` handler
- [ ] T006: Wire into main dispatch

**Implementation Notes**:
- Follow catalog-import pattern exactly
- Support --dry-run, --json, --resolve-mode flags
- Call transaction_import_service.import_purchases()

**Dependencies**: WP01

**Risks**: None - straightforward wrapper

---

### WP03 – Adjustment & Validate CLI

**Goal**: Add `import-adjustments` and `validate-import` commands to CLI.

**Priority**: P1 (User Stories 2 & 3)

**Prompt**: [WP03-adjustment-validate-cli.md](tasks/WP03-adjustment-validate-cli.md)

**Subtasks**:
- [ ] T007: Add `import-adjustments` CLI parser
- [ ] T008: Implement `import_adjustments_cmd()` handler
- [ ] T009: Add `validate-import` CLI parser
- [ ] T010: Implement `validate_import_cmd()` handler

**Implementation Notes**:
- validate-import uses dry_run=True to validate without changes
- Support --type flag for validate-import (purchase or adjustment)

**Dependencies**: WP01

**Risks**: None - straightforward wrappers

---

## Phase 3: Testing

### WP04 – CLI Tests

**Goal**: Add pytest tests for all three CLI commands.

**Priority**: P2 (quality assurance)

**Prompt**: [WP04-cli-tests.md](tasks/WP04-cli-tests.md)

**Subtasks**:
- [ ] T011: Add tests for import-purchases command
- [ ] T012: Add tests for import-adjustments command
- [ ] T013: Add tests for validate-import command

**Implementation Notes**:
- Test happy path, error cases, flag combinations
- Use test fixtures for JSON input files
- Mock database to avoid side effects

**Dependencies**: WP02, WP03

**Risks**: Test setup complexity for CLI testing

---

## Subtask Reference

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Add strict_mode to import_purchases() | WP01 | [P] |
| T002 | Add strict_mode to import_adjustments() | WP01 | [P] |
| T003 | Add result_to_json() helper | WP01 | |
| T004 | Add import-purchases parser | WP02 | |
| T005 | Implement import_purchases_cmd() | WP02 | |
| T006 | Wire import-purchases to dispatch | WP02 | |
| T007 | Add import-adjustments parser | WP03 | |
| T008 | Implement import_adjustments_cmd() | WP03 | |
| T009 | Add validate-import parser | WP03 | |
| T010 | Implement validate_import_cmd() | WP03 | |
| T011 | Tests for import-purchases | WP04 | [P] |
| T012 | Tests for import-adjustments | WP04 | [P] |
| T013 | Tests for validate-import | WP04 | [P] |

---

## Next Steps

1. Run `/spec-kitty.implement WP01` to start service layer extension
2. After WP01, run WP02 and WP03 in parallel (different agents)
3. After WP02+WP03, run WP04 for tests
