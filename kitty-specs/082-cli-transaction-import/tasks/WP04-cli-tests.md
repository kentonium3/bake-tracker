---
work_package_id: WP04
title: CLI Tests
lane: "done"
dependencies: []
subtasks:
- T011
- T012
- T013
phase: Phase 3 - Testing
assignee: ''
agent: "claude"
shell_pid: "48820"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-29T04:45:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – CLI Tests

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

**Depends on WP02 and WP03** - must branch from completed CLI work.

---

## Objectives & Success Criteria

**Goal**: Add pytest tests for all three CLI commands.

**Success Criteria**:
- [ ] Tests for import-purchases command (happy path, errors, flags)
- [ ] Tests for import-adjustments command (happy path, errors, flags)
- [ ] Tests for validate-import command (both types, pass/fail)
- [ ] All tests pass
- [ ] Tests use fixtures for JSON files (no hardcoded paths)

## Context & Constraints

**Files to Create**:
- `src/tests/services/test_transaction_import_cli.py` - New test file

**Pattern Reference**: Study existing CLI tests in the codebase.

**Key Approach**: Test the handler functions directly, not through subprocess. This is faster and more reliable.

---

## Subtasks & Detailed Guidance

### Subtask T011 – Tests for import-purchases command

**Purpose**: Verify import-purchases CLI works correctly.

**Steps**:

1. Create test file `src/tests/services/test_transaction_import_cli.py`:
   ```python
   """Tests for CLI transaction import commands (F083)."""

   import json
   import pytest
   from pathlib import Path
   from unittest.mock import patch, MagicMock
   from argparse import Namespace

   from src.utils.import_export_cli import (
       import_purchases_cmd,
       import_adjustments_cmd,
       validate_import_cmd,
       result_to_json,
   )
   from src.services.import_export_service import ImportResult


   # ============================================================================
   # Fixtures
   # ============================================================================

   @pytest.fixture
   def valid_purchases_json(tmp_path):
       """Create valid purchases JSON file."""
       file_path = tmp_path / "purchases.json"
       data = {
           "schema_version": "4.0",
           "import_type": "purchases",
           "created_at": "2026-01-29T00:00:00Z",
           "source": "test",
           "purchases": []
       }
       file_path.write_text(json.dumps(data))
       return str(file_path)


   @pytest.fixture
   def mock_import_result():
       """Create mock ImportResult for testing."""
       result = ImportResult()
       result.successful = 2
       result.skipped = 1
       result.failed = 0
       return result


   # ============================================================================
   # import-purchases Tests
   # ============================================================================

   class TestImportPurchasesCmd:
       """Tests for import_purchases_cmd handler."""

       def test_file_not_found(self, tmp_path, capsys):
           """Test error when file doesn't exist."""
           args = Namespace(
               input_file=str(tmp_path / "nonexistent.json"),
               dry_run=False,
               json_output=False,
               resolve_mode="auto",
           )
           result = import_purchases_cmd(args)
           assert result == 1
           captured = capsys.readouterr()
           assert "not found" in captured.out.lower()

       def test_file_not_found_json_output(self, tmp_path, capsys):
           """Test JSON error output when file doesn't exist."""
           args = Namespace(
               input_file=str(tmp_path / "nonexistent.json"),
               dry_run=False,
               json_output=True,
               resolve_mode="auto",
           )
           result = import_purchases_cmd(args)
           assert result == 1
           captured = capsys.readouterr()
           output = json.loads(captured.out)
           assert output["success"] is False
           assert "not found" in output["error"].lower()

       @patch("src.utils.import_export_cli.import_purchases")
       def test_successful_import(self, mock_import, valid_purchases_json, mock_import_result, capsys):
           """Test successful purchase import."""
           mock_import.return_value = mock_import_result
           args = Namespace(
               input_file=valid_purchases_json,
               dry_run=False,
               json_output=False,
               resolve_mode="auto",
           )
           result = import_purchases_cmd(args)
           assert result == 0
           mock_import.assert_called_once_with(
               file_path=valid_purchases_json,
               dry_run=False,
               strict_mode=False,
           )

       @patch("src.utils.import_export_cli.import_purchases")
       def test_dry_run_flag(self, mock_import, valid_purchases_json, mock_import_result, capsys):
           """Test --dry-run flag is passed correctly."""
           mock_import.return_value = mock_import_result
           args = Namespace(
               input_file=valid_purchases_json,
               dry_run=True,
               json_output=False,
               resolve_mode="auto",
           )
           import_purchases_cmd(args)
           mock_import.assert_called_once_with(
               file_path=valid_purchases_json,
               dry_run=True,
               strict_mode=False,
           )

       @patch("src.utils.import_export_cli.import_purchases")
       def test_strict_mode_flag(self, mock_import, valid_purchases_json, mock_import_result):
           """Test --resolve-mode=strict is passed correctly."""
           mock_import.return_value = mock_import_result
           args = Namespace(
               input_file=valid_purchases_json,
               dry_run=False,
               json_output=False,
               resolve_mode="strict",
           )
           import_purchases_cmd(args)
           mock_import.assert_called_once_with(
               file_path=valid_purchases_json,
               dry_run=False,
               strict_mode=True,
           )

       @patch("src.utils.import_export_cli.import_purchases")
       def test_json_output(self, mock_import, valid_purchases_json, mock_import_result, capsys):
           """Test --json outputs valid JSON."""
           mock_import.return_value = mock_import_result
           args = Namespace(
               input_file=valid_purchases_json,
               dry_run=False,
               json_output=True,
               resolve_mode="auto",
           )
           import_purchases_cmd(args)
           captured = capsys.readouterr()
           output = json.loads(captured.out)
           assert output["success"] is True
           assert output["imported"] == 2
           assert output["skipped"] == 1
   ```

**Files**: `src/tests/services/test_transaction_import_cli.py`

**Parallel?**: Yes - T011, T012, T013 can be written in parallel

---

### Subtask T012 – Tests for import-adjustments command

**Purpose**: Verify import-adjustments CLI works correctly.

**Steps**:

1. Add to same test file:
   ```python
   @pytest.fixture
   def valid_adjustments_json(tmp_path):
       """Create valid adjustments JSON file."""
       file_path = tmp_path / "adjustments.json"
       data = {
           "schema_version": "4.0",
           "import_type": "adjustments",
           "created_at": "2026-01-29T00:00:00Z",
           "source": "test",
           "adjustments": []
       }
       file_path.write_text(json.dumps(data))
       return str(file_path)


   class TestImportAdjustmentsCmd:
       """Tests for import_adjustments_cmd handler."""

       def test_file_not_found(self, tmp_path, capsys):
           """Test error when file doesn't exist."""
           args = Namespace(
               input_file=str(tmp_path / "nonexistent.json"),
               dry_run=False,
               json_output=False,
               resolve_mode="auto",
           )
           result = import_adjustments_cmd(args)
           assert result == 1

       @patch("src.utils.import_export_cli.import_adjustments")
       def test_successful_import(self, mock_import, valid_adjustments_json, mock_import_result):
           """Test successful adjustment import."""
           mock_import.return_value = mock_import_result
           args = Namespace(
               input_file=valid_adjustments_json,
               dry_run=False,
               json_output=False,
               resolve_mode="auto",
           )
           result = import_adjustments_cmd(args)
           assert result == 0
           mock_import.assert_called_once()

       @patch("src.utils.import_export_cli.import_adjustments")
       def test_strict_mode(self, mock_import, valid_adjustments_json, mock_import_result):
           """Test --resolve-mode=strict."""
           mock_import.return_value = mock_import_result
           args = Namespace(
               input_file=valid_adjustments_json,
               dry_run=False,
               json_output=False,
               resolve_mode="strict",
           )
           import_adjustments_cmd(args)
           mock_import.assert_called_once_with(
               file_path=valid_adjustments_json,
               dry_run=False,
               strict_mode=True,
           )
   ```

**Files**: `src/tests/services/test_transaction_import_cli.py`

---

### Subtask T013 – Tests for validate-import command

**Purpose**: Verify validate-import CLI works correctly.

**Steps**:

1. Add to same test file:
   ```python
   class TestValidateImportCmd:
       """Tests for validate_import_cmd handler."""

       def test_file_not_found(self, tmp_path, capsys):
           """Test error when file doesn't exist."""
           args = Namespace(
               input_file=str(tmp_path / "nonexistent.json"),
               import_type="purchase",
               json_output=False,
               resolve_mode="auto",
           )
           result = validate_import_cmd(args)
           assert result == 1

       @patch("src.utils.import_export_cli.import_purchases")
       def test_validate_purchase_type(self, mock_import, valid_purchases_json, mock_import_result):
           """Test --type=purchase routes to import_purchases."""
           mock_import.return_value = mock_import_result
           args = Namespace(
               input_file=valid_purchases_json,
               import_type="purchase",
               json_output=False,
               resolve_mode="auto",
           )
           validate_import_cmd(args)
           mock_import.assert_called_once_with(
               file_path=valid_purchases_json,
               dry_run=True,  # validate always uses dry_run
               strict_mode=False,
           )

       @patch("src.utils.import_export_cli.import_adjustments")
       def test_validate_adjustment_type(self, mock_import, valid_adjustments_json, mock_import_result):
           """Test --type=adjustment routes to import_adjustments."""
           mock_import.return_value = mock_import_result
           args = Namespace(
               input_file=valid_adjustments_json,
               import_type="adjustment",
               json_output=False,
               resolve_mode="auto",
           )
           validate_import_cmd(args)
           mock_import.assert_called_once_with(
               file_path=valid_adjustments_json,
               dry_run=True,  # validate always uses dry_run
               strict_mode=False,
           )

       @patch("src.utils.import_export_cli.import_purchases")
       def test_json_output_includes_validation_only(self, mock_import, valid_purchases_json, mock_import_result, capsys):
           """Test JSON output has validation_only field."""
           mock_import.return_value = mock_import_result
           args = Namespace(
               input_file=valid_purchases_json,
               import_type="purchase",
               json_output=True,
               resolve_mode="auto",
           )
           validate_import_cmd(args)
           captured = capsys.readouterr()
           output = json.loads(captured.out)
           assert output["validation_only"] is True
           assert output["import_type"] == "purchase"


   # ============================================================================
   # result_to_json Tests
   # ============================================================================

   class TestResultToJson:
       """Tests for result_to_json helper."""

       def test_converts_import_result(self, mock_import_result):
           """Test conversion of ImportResult to dict."""
           output = result_to_json(mock_import_result)
           assert output["success"] is True
           assert output["imported"] == 2
           assert output["skipped"] == 1
           assert output["failed"] == 0
           assert "errors" in output
           assert "warnings" in output
           assert "entity_counts" in output

       def test_failed_result(self):
           """Test that failed > 0 sets success=False."""
           result = ImportResult()
           result.failed = 1
           output = result_to_json(result)
           assert output["success"] is False
   ```

**Files**: `src/tests/services/test_transaction_import_cli.py`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Mocking imports incorrectly | Use full path in @patch decorator |
| Fixture paths not working | Use tmp_path fixture for file creation |

---

## Definition of Done Checklist

- [ ] T011: Tests for import-purchases command
- [ ] T012: Tests for import-adjustments command
- [ ] T013: Tests for validate-import command
- [ ] All tests pass (`pytest src/tests/services/test_transaction_import_cli.py -v`)
- [ ] No import errors in test file
- [ ] Tests cover happy path, error cases, and flag variations

---

## Review Guidance

**Reviewers should verify**:
1. Tests use mocking correctly (service layer mocked, not bypassed)
2. Fixtures create valid JSON files
3. All flag combinations tested (dry-run, json, resolve-mode)
4. validate-import always passes dry_run=True to services
5. Test assertions match expected behavior from spec

---

## Activity Log

- 2026-01-29T04:45:00Z – system – lane=planned – Prompt created.
- 2026-01-29T05:24:06Z – claude – shell_pid=31301 – lane=doing – Started implementation via workflow command
- 2026-01-29T13:31:52Z – claude – shell_pid=31301 – lane=for_review – Ready for review: Added 29 tests for CLI transaction import commands
- 2026-01-29T13:31:59Z – claude – shell_pid=48820 – lane=doing – Started review via workflow command
- 2026-01-29T13:32:24Z – claude – shell_pid=48820 – lane=done – Review passed: 29 tests covering all CLI commands, flags, and error handling.
