"""Tests for CLI transaction import commands (F083).

Tests for import-purchases, import-adjustments, and validate-import CLI commands.
These commands wrap the transaction_import_service for AI workflow integration.
"""

import json
import pytest
from argparse import Namespace
from unittest.mock import patch

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
        "purchases": [],
    }
    file_path.write_text(json.dumps(data))
    return str(file_path)


@pytest.fixture
def valid_adjustments_json(tmp_path):
    """Create valid adjustments JSON file."""
    file_path = tmp_path / "adjustments.json"
    data = {
        "schema_version": "4.0",
        "import_type": "adjustments",
        "created_at": "2026-01-29T00:00:00Z",
        "source": "test",
        "adjustments": [],
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


@pytest.fixture
def mock_failed_import_result():
    """Create mock ImportResult with failures for testing."""
    result = ImportResult()
    result.successful = 1
    result.skipped = 0
    result.failed = 2
    result.errors = [
        {
            "record_type": "purchase",
            "record_name": "test_product",
            "error_type": "not_found",
            "message": "Product not found",
        }
    ]
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

    @patch("src.services.transaction_import_service.import_purchases")
    def test_successful_import(
        self, mock_import, valid_purchases_json, mock_import_result, capsys
    ):
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

    @patch("src.services.transaction_import_service.import_purchases")
    def test_dry_run_flag(
        self, mock_import, valid_purchases_json, mock_import_result, capsys
    ):
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
        # Verify dry run message in output
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    @patch("src.services.transaction_import_service.import_purchases")
    def test_strict_mode_flag(
        self, mock_import, valid_purchases_json, mock_import_result
    ):
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

    @patch("src.services.transaction_import_service.import_purchases")
    def test_json_output(
        self, mock_import, valid_purchases_json, mock_import_result, capsys
    ):
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
        assert output["dry_run"] is False
        assert output["resolve_mode"] == "auto"

    @patch("src.services.transaction_import_service.import_purchases")
    def test_json_output_with_dry_run(
        self, mock_import, valid_purchases_json, mock_import_result, capsys
    ):
        """Test --json with --dry-run includes dry_run field."""
        mock_import.return_value = mock_import_result
        args = Namespace(
            input_file=valid_purchases_json,
            dry_run=True,
            json_output=True,
            resolve_mode="strict",
        )
        import_purchases_cmd(args)
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["dry_run"] is True
        assert output["resolve_mode"] == "strict"

    @patch("src.services.transaction_import_service.import_purchases")
    def test_returns_1_on_failures(
        self, mock_import, valid_purchases_json, mock_failed_import_result
    ):
        """Test returns exit code 1 when there are import failures."""
        mock_import.return_value = mock_failed_import_result
        args = Namespace(
            input_file=valid_purchases_json,
            dry_run=False,
            json_output=False,
            resolve_mode="auto",
        )
        result = import_purchases_cmd(args)
        assert result == 1

    @patch("src.services.transaction_import_service.import_purchases")
    def test_exception_handling(self, mock_import, valid_purchases_json, capsys):
        """Test exception is caught and returns error."""
        mock_import.side_effect = Exception("Database error")
        args = Namespace(
            input_file=valid_purchases_json,
            dry_run=False,
            json_output=False,
            resolve_mode="auto",
        )
        result = import_purchases_cmd(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Database error" in captured.out

    @patch("src.services.transaction_import_service.import_purchases")
    def test_exception_handling_json(self, mock_import, valid_purchases_json, capsys):
        """Test exception returns JSON error."""
        mock_import.side_effect = Exception("Database error")
        args = Namespace(
            input_file=valid_purchases_json,
            dry_run=False,
            json_output=True,
            resolve_mode="auto",
        )
        result = import_purchases_cmd(args)
        assert result == 1
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False
        assert "Database error" in output["error"]


# ============================================================================
# import-adjustments Tests
# ============================================================================


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
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_file_not_found_json_output(self, tmp_path, capsys):
        """Test JSON error when file doesn't exist."""
        args = Namespace(
            input_file=str(tmp_path / "nonexistent.json"),
            dry_run=False,
            json_output=True,
            resolve_mode="auto",
        )
        result = import_adjustments_cmd(args)
        assert result == 1
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False

    @patch("src.services.transaction_import_service.import_adjustments")
    def test_successful_import(
        self, mock_import, valid_adjustments_json, mock_import_result
    ):
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
        mock_import.assert_called_once_with(
            file_path=valid_adjustments_json,
            dry_run=False,
            strict_mode=False,
        )

    @patch("src.services.transaction_import_service.import_adjustments")
    def test_dry_run_flag(
        self, mock_import, valid_adjustments_json, mock_import_result, capsys
    ):
        """Test --dry-run flag is passed correctly."""
        mock_import.return_value = mock_import_result
        args = Namespace(
            input_file=valid_adjustments_json,
            dry_run=True,
            json_output=False,
            resolve_mode="auto",
        )
        import_adjustments_cmd(args)
        mock_import.assert_called_once_with(
            file_path=valid_adjustments_json,
            dry_run=True,
            strict_mode=False,
        )
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    @patch("src.services.transaction_import_service.import_adjustments")
    def test_strict_mode(
        self, mock_import, valid_adjustments_json, mock_import_result
    ):
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

    @patch("src.services.transaction_import_service.import_adjustments")
    def test_json_output(
        self, mock_import, valid_adjustments_json, mock_import_result, capsys
    ):
        """Test --json outputs valid JSON."""
        mock_import.return_value = mock_import_result
        args = Namespace(
            input_file=valid_adjustments_json,
            dry_run=False,
            json_output=True,
            resolve_mode="auto",
        )
        import_adjustments_cmd(args)
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is True
        assert output["imported"] == 2

    @patch("src.services.transaction_import_service.import_adjustments")
    def test_returns_1_on_failures(
        self, mock_import, valid_adjustments_json, mock_failed_import_result
    ):
        """Test returns exit code 1 when there are import failures."""
        mock_import.return_value = mock_failed_import_result
        args = Namespace(
            input_file=valid_adjustments_json,
            dry_run=False,
            json_output=False,
            resolve_mode="auto",
        )
        result = import_adjustments_cmd(args)
        assert result == 1


# ============================================================================
# validate-import Tests
# ============================================================================


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
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_file_not_found_json_output(self, tmp_path, capsys):
        """Test JSON error when file doesn't exist."""
        args = Namespace(
            input_file=str(tmp_path / "nonexistent.json"),
            import_type="purchase",
            json_output=True,
            resolve_mode="auto",
        )
        result = validate_import_cmd(args)
        assert result == 1
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False

    @patch("src.services.transaction_import_service.import_purchases")
    def test_validate_purchase_type(
        self, mock_import, valid_purchases_json, mock_import_result
    ):
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

    @patch("src.services.transaction_import_service.import_adjustments")
    def test_validate_adjustment_type(
        self, mock_import, valid_adjustments_json, mock_import_result
    ):
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

    @patch("src.services.transaction_import_service.import_purchases")
    def test_strict_mode_passed(
        self, mock_import, valid_purchases_json, mock_import_result
    ):
        """Test --resolve-mode=strict is passed to import."""
        mock_import.return_value = mock_import_result
        args = Namespace(
            input_file=valid_purchases_json,
            import_type="purchase",
            json_output=False,
            resolve_mode="strict",
        )
        validate_import_cmd(args)
        mock_import.assert_called_once_with(
            file_path=valid_purchases_json,
            dry_run=True,
            strict_mode=True,
        )

    @patch("src.services.transaction_import_service.import_purchases")
    def test_json_output_includes_validation_only(
        self, mock_import, valid_purchases_json, mock_import_result, capsys
    ):
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

    @patch("src.services.transaction_import_service.import_purchases")
    def test_validation_passed_message(
        self, mock_import, valid_purchases_json, mock_import_result, capsys
    ):
        """Test validation passed message is shown."""
        mock_import.return_value = mock_import_result
        args = Namespace(
            input_file=valid_purchases_json,
            import_type="purchase",
            json_output=False,
            resolve_mode="auto",
        )
        result = validate_import_cmd(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "validation passed" in captured.out.lower()

    @patch("src.services.transaction_import_service.import_purchases")
    def test_validation_failed_message(
        self, mock_import, valid_purchases_json, mock_failed_import_result, capsys
    ):
        """Test validation failed message is shown."""
        mock_import.return_value = mock_failed_import_result
        args = Namespace(
            input_file=valid_purchases_json,
            import_type="purchase",
            json_output=False,
            resolve_mode="auto",
        )
        result = validate_import_cmd(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "validation failed" in captured.out.lower()


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

    def test_includes_errors(self, mock_failed_import_result):
        """Test errors are included in output."""
        output = result_to_json(mock_failed_import_result)
        assert output["success"] is False
        assert len(output["errors"]) == 1
        assert output["errors"][0]["record_type"] == "purchase"

    def test_default_values(self):
        """Test default values for new ImportResult."""
        result = ImportResult()
        output = result_to_json(result)
        assert output["success"] is True  # No failures
        assert output["imported"] == 0
        assert output["skipped"] == 0
        assert output["failed"] == 0
        assert output["errors"] == []
        assert output["warnings"] == []
        assert output["entity_counts"] == {}
