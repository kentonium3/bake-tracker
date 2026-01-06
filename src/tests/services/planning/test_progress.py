"""
Unit tests for progress tracking service (Feature 039).

Tests cover:
- get_production_progress() with various progress states
- get_assembly_progress() with various progress states
- get_overall_progress() status calculation
- Edge cases: zero targets, division by zero handling

Per WP05 specification:
- SC-006: Users can track production progress in real-time with visual feedback
- FR-030-033: Progress tracking and overall status
"""

import pytest
from unittest.mock import patch, MagicMock

from src.services.planning.progress import (
    ProductionProgress,
    AssemblyProgress,
    get_production_progress,
    get_assembly_progress,
    get_overall_progress,
)


class TestProductionProgressDataclass:
    """Tests for ProductionProgress dataclass."""

    def test_dataclass_fields(self):
        """Test that ProductionProgress has all required fields."""
        progress = ProductionProgress(
            recipe_id=1,
            recipe_name="Chocolate Chip Cookies",
            target_batches=7,
            completed_batches=4,
            progress_percent=57.14,
            is_complete=False,
        )

        assert progress.recipe_id == 1
        assert progress.recipe_name == "Chocolate Chip Cookies"
        assert progress.target_batches == 7
        assert progress.completed_batches == 4
        assert progress.progress_percent == 57.14
        assert progress.is_complete is False

    def test_dataclass_equality(self):
        """Test dataclass equality comparison."""
        p1 = ProductionProgress(1, "Cookies", 7, 4, 57.14, False)
        p2 = ProductionProgress(1, "Cookies", 7, 4, 57.14, False)
        assert p1 == p2

    def test_complete_progress(self):
        """Test that 100% progress is represented correctly."""
        progress = ProductionProgress(
            recipe_id=1,
            recipe_name="Cookies",
            target_batches=5,
            completed_batches=5,
            progress_percent=100.0,
            is_complete=True,
        )
        assert progress.is_complete is True
        assert progress.progress_percent == 100.0


class TestAssemblyProgressDataclass:
    """Tests for AssemblyProgress dataclass."""

    def test_dataclass_fields(self):
        """Test that AssemblyProgress has all required fields."""
        progress = AssemblyProgress(
            finished_good_id=1,
            finished_good_name="Holiday Gift Box",
            target_quantity=50,
            assembled_quantity=25,
            available_to_assemble=10,
            progress_percent=50.0,
            is_complete=False,
        )

        assert progress.finished_good_id == 1
        assert progress.finished_good_name == "Holiday Gift Box"
        assert progress.target_quantity == 50
        assert progress.assembled_quantity == 25
        assert progress.available_to_assemble == 10
        assert progress.progress_percent == 50.0
        assert progress.is_complete is False

    def test_dataclass_equality(self):
        """Test dataclass equality comparison."""
        a1 = AssemblyProgress(1, "Gift Box", 50, 25, 10, 50.0, False)
        a2 = AssemblyProgress(1, "Gift Box", 50, 25, 10, 50.0, False)
        assert a1 == a2


class TestGetProductionProgress:
    """Tests for get_production_progress() function."""

    @patch("src.services.planning.progress.event_service")
    def test_zero_progress(self, mock_event_service):
        """Test 0/7 batches = 0%."""
        mock_event_service.get_production_progress.return_value = [
            {
                "recipe_id": 1,
                "recipe_name": "Cookies",
                "target_batches": 7,
                "produced_batches": 0,
                "produced_yield": 0,
                "progress_pct": 0.0,
                "is_complete": False,
            }
        ]

        result = get_production_progress(event_id=1)

        assert len(result) == 1
        assert result[0].recipe_id == 1
        assert result[0].target_batches == 7
        assert result[0].completed_batches == 0
        assert result[0].progress_percent == 0.0
        assert result[0].is_complete is False

    @patch("src.services.planning.progress.event_service")
    def test_partial_progress(self, mock_event_service):
        """Test 4/7 batches = 57.14%."""
        mock_event_service.get_production_progress.return_value = [
            {
                "recipe_id": 1,
                "recipe_name": "Cookies",
                "target_batches": 7,
                "produced_batches": 4,
                "produced_yield": 192,
                "progress_pct": 57.14,
                "is_complete": False,
            }
        ]

        result = get_production_progress(event_id=1)

        assert len(result) == 1
        assert result[0].completed_batches == 4
        assert result[0].progress_percent == 57.14
        assert result[0].is_complete is False

    @patch("src.services.planning.progress.event_service")
    def test_complete_progress(self, mock_event_service):
        """Test 7/7 batches = 100%, is_complete=True."""
        mock_event_service.get_production_progress.return_value = [
            {
                "recipe_id": 1,
                "recipe_name": "Cookies",
                "target_batches": 7,
                "produced_batches": 7,
                "produced_yield": 336,
                "progress_pct": 100.0,
                "is_complete": True,
            }
        ]

        result = get_production_progress(event_id=1)

        assert len(result) == 1
        assert result[0].completed_batches == 7
        assert result[0].progress_percent == 100.0
        assert result[0].is_complete is True

    @patch("src.services.planning.progress.event_service")
    def test_over_production(self, mock_event_service):
        """Test over-production: 10/7 batches = 142.86%."""
        mock_event_service.get_production_progress.return_value = [
            {
                "recipe_id": 1,
                "recipe_name": "Cookies",
                "target_batches": 7,
                "produced_batches": 10,
                "produced_yield": 480,
                "progress_pct": 142.86,
                "is_complete": True,
            }
        ]

        result = get_production_progress(event_id=1)

        assert len(result) == 1
        assert result[0].completed_batches == 10
        assert result[0].progress_percent == 142.86
        assert result[0].is_complete is True

    @patch("src.services.planning.progress.event_service")
    def test_multiple_recipes(self, mock_event_service):
        """Test progress across multiple recipes."""
        mock_event_service.get_production_progress.return_value = [
            {
                "recipe_id": 1,
                "recipe_name": "Cookies",
                "target_batches": 5,
                "produced_batches": 5,
                "produced_yield": 240,
                "progress_pct": 100.0,
                "is_complete": True,
            },
            {
                "recipe_id": 2,
                "recipe_name": "Brownies",
                "target_batches": 3,
                "produced_batches": 1,
                "produced_yield": 24,
                "progress_pct": 33.33,
                "is_complete": False,
            },
        ]

        result = get_production_progress(event_id=1)

        assert len(result) == 2
        assert result[0].recipe_name == "Cookies"
        assert result[0].is_complete is True
        assert result[1].recipe_name == "Brownies"
        assert result[1].is_complete is False

    @patch("src.services.planning.progress.event_service")
    def test_no_targets(self, mock_event_service):
        """Test empty result when no production targets."""
        mock_event_service.get_production_progress.return_value = []

        result = get_production_progress(event_id=1)

        assert result == []


class TestGetAssemblyProgress:
    """Tests for get_assembly_progress() function."""

    @patch("src.services.planning.progress.event_service")
    def test_zero_assembled(self, mock_event_service):
        """Test 0/50 assembled = 0%."""
        mock_event_service.get_assembly_progress.return_value = [
            {
                "finished_good_id": 1,
                "finished_good_name": "Gift Box",
                "target_quantity": 50,
                "assembled_quantity": 0,
                "progress_pct": 0.0,
                "is_complete": False,
            }
        ]

        result = get_assembly_progress(event_id=1)

        assert len(result) == 1
        assert result[0].finished_good_id == 1
        assert result[0].target_quantity == 50
        assert result[0].assembled_quantity == 0
        assert result[0].progress_percent == 0.0
        assert result[0].is_complete is False

    @patch("src.services.planning.progress.event_service")
    def test_partial_assembled(self, mock_event_service):
        """Test 25/50 assembled = 50%."""
        mock_event_service.get_assembly_progress.return_value = [
            {
                "finished_good_id": 1,
                "finished_good_name": "Gift Box",
                "target_quantity": 50,
                "assembled_quantity": 25,
                "progress_pct": 50.0,
                "is_complete": False,
            }
        ]

        result = get_assembly_progress(event_id=1)

        assert len(result) == 1
        assert result[0].assembled_quantity == 25
        assert result[0].progress_percent == 50.0
        assert result[0].is_complete is False

    @patch("src.services.planning.progress.event_service")
    def test_complete_assembled(self, mock_event_service):
        """Test 50/50 assembled = 100%, is_complete=True."""
        mock_event_service.get_assembly_progress.return_value = [
            {
                "finished_good_id": 1,
                "finished_good_name": "Gift Box",
                "target_quantity": 50,
                "assembled_quantity": 50,
                "progress_pct": 100.0,
                "is_complete": True,
            }
        ]

        result = get_assembly_progress(event_id=1)

        assert len(result) == 1
        assert result[0].assembled_quantity == 50
        assert result[0].progress_percent == 100.0
        assert result[0].is_complete is True

    @patch("src.services.planning.progress.event_service")
    def test_no_assembly_targets(self, mock_event_service):
        """Test empty result when no assembly targets."""
        mock_event_service.get_assembly_progress.return_value = []

        result = get_assembly_progress(event_id=1)

        assert result == []

    @patch("src.services.planning.progress.event_service")
    def test_available_to_assemble_defaults_to_zero(self, mock_event_service):
        """Test that available_to_assemble defaults to 0."""
        mock_event_service.get_assembly_progress.return_value = [
            {
                "finished_good_id": 1,
                "finished_good_name": "Gift Box",
                "target_quantity": 50,
                "assembled_quantity": 25,
                "progress_pct": 50.0,
                "is_complete": False,
            }
        ]

        result = get_assembly_progress(event_id=1)

        # available_to_assemble is not provided by event_service
        # so it should default to 0
        assert result[0].available_to_assemble == 0


class TestGetOverallProgress:
    """Tests for get_overall_progress() function."""

    @patch("src.services.planning.progress.get_assembly_progress")
    @patch("src.services.planning.progress.get_production_progress")
    def test_not_started_status(self, mock_prod, mock_asm):
        """Test 'not_started' status when production_percent == 0."""
        mock_prod.return_value = [
            ProductionProgress(1, "Cookies", 7, 0, 0.0, False),
        ]
        mock_asm.return_value = [
            AssemblyProgress(1, "Gift Box", 50, 0, 0, 0.0, False),
        ]

        result = get_overall_progress(event_id=1)

        assert result["status"] == "not_started"
        assert result["production_percent"] == 0.0
        assert result["assembly_percent"] == 0.0
        assert result["overall_percent"] == 0.0

    @patch("src.services.planning.progress.get_assembly_progress")
    @patch("src.services.planning.progress.get_production_progress")
    def test_in_progress_status(self, mock_prod, mock_asm):
        """Test 'in_progress' status when partially complete."""
        mock_prod.return_value = [
            ProductionProgress(1, "Cookies", 7, 4, 57.14, False),
        ]
        mock_asm.return_value = [
            AssemblyProgress(1, "Gift Box", 50, 25, 0, 50.0, False),
        ]

        result = get_overall_progress(event_id=1)

        assert result["status"] == "in_progress"
        assert result["production_percent"] == 57.14
        assert result["assembly_percent"] == 50.0
        # (57.14 + 50.0) / 2 = 53.57
        assert result["overall_percent"] == 53.57

    @patch("src.services.planning.progress.get_assembly_progress")
    @patch("src.services.planning.progress.get_production_progress")
    def test_complete_status(self, mock_prod, mock_asm):
        """Test 'complete' status when production_percent == 100 && assembly_percent == 100."""
        mock_prod.return_value = [
            ProductionProgress(1, "Cookies", 7, 7, 100.0, True),
        ]
        mock_asm.return_value = [
            AssemblyProgress(1, "Gift Box", 50, 50, 0, 100.0, True),
        ]

        result = get_overall_progress(event_id=1)

        assert result["status"] == "complete"
        assert result["production_percent"] == 100.0
        assert result["assembly_percent"] == 100.0
        assert result["overall_percent"] == 100.0
        assert result["production_targets"] == 1
        assert result["production_complete"] == 1
        assert result["assembly_targets"] == 1
        assert result["assembly_complete"] == 1

    @patch("src.services.planning.progress.get_assembly_progress")
    @patch("src.services.planning.progress.get_production_progress")
    def test_zero_targets_handled_gracefully(self, mock_prod, mock_asm):
        """Test edge case: zero targets returns not_started."""
        mock_prod.return_value = []
        mock_asm.return_value = []

        result = get_overall_progress(event_id=1)

        assert result["status"] == "not_started"
        assert result["production_percent"] == 0.0
        assert result["assembly_percent"] == 0.0
        assert result["overall_percent"] == 0.0
        assert result["production_targets"] == 0
        assert result["assembly_targets"] == 0

    @patch("src.services.planning.progress.get_assembly_progress")
    @patch("src.services.planning.progress.get_production_progress")
    def test_production_only(self, mock_prod, mock_asm):
        """Test with production targets but no assembly targets."""
        mock_prod.return_value = [
            ProductionProgress(1, "Cookies", 7, 7, 100.0, True),
        ]
        mock_asm.return_value = []

        result = get_overall_progress(event_id=1)

        # With only production, overall should match production
        assert result["status"] == "complete"
        assert result["production_percent"] == 100.0
        assert result["assembly_percent"] == 0.0
        assert result["overall_percent"] == 100.0

    @patch("src.services.planning.progress.get_assembly_progress")
    @patch("src.services.planning.progress.get_production_progress")
    def test_assembly_only(self, mock_prod, mock_asm):
        """Test with assembly targets but no production targets."""
        mock_prod.return_value = []
        mock_asm.return_value = [
            AssemblyProgress(1, "Gift Box", 50, 50, 0, 100.0, True),
        ]

        result = get_overall_progress(event_id=1)

        # With only assembly, overall should match assembly
        assert result["status"] == "complete"
        assert result["production_percent"] == 0.0
        assert result["assembly_percent"] == 100.0
        assert result["overall_percent"] == 100.0

    @patch("src.services.planning.progress.get_assembly_progress")
    @patch("src.services.planning.progress.get_production_progress")
    def test_multiple_targets_averaging(self, mock_prod, mock_asm):
        """Test averaging across multiple targets."""
        mock_prod.return_value = [
            ProductionProgress(1, "Cookies", 10, 10, 100.0, True),
            ProductionProgress(2, "Brownies", 5, 2, 40.0, False),
        ]
        mock_asm.return_value = [
            AssemblyProgress(1, "Gift Box A", 50, 50, 0, 100.0, True),
            AssemblyProgress(2, "Gift Box B", 30, 0, 0, 0.0, False),
        ]

        result = get_overall_progress(event_id=1)

        # Production: (100 + 40) / 2 = 70
        assert result["production_percent"] == 70.0
        # Assembly: (100 + 0) / 2 = 50
        assert result["assembly_percent"] == 50.0
        # Overall: (70 + 50) / 2 = 60
        assert result["overall_percent"] == 60.0
        assert result["status"] == "in_progress"
        assert result["production_targets"] == 2
        assert result["production_complete"] == 1
        assert result["assembly_targets"] == 2
        assert result["assembly_complete"] == 1

    @patch("src.services.planning.progress.get_assembly_progress")
    @patch("src.services.planning.progress.get_production_progress")
    def test_over_production_capped_in_average(self, mock_prod, mock_asm):
        """Test that over-production is capped at 100% for averaging."""
        mock_prod.return_value = [
            ProductionProgress(1, "Cookies", 5, 10, 200.0, True),  # 200% progress
        ]
        mock_asm.return_value = [
            AssemblyProgress(1, "Gift Box", 50, 25, 0, 50.0, False),
        ]

        result = get_overall_progress(event_id=1)

        # Production should be capped at 100% for averaging
        assert result["production_percent"] == 100.0
        assert result["assembly_percent"] == 50.0
        # (100 + 50) / 2 = 75
        assert result["overall_percent"] == 75.0


class TestProgressWithSession:
    """Tests for session parameter handling."""

    @patch("src.services.planning.progress.event_service")
    @patch("src.services.planning.progress.session_scope")
    def test_production_progress_with_session(self, mock_scope, mock_event_service):
        """Test that passing session skips session_scope."""
        mock_session = MagicMock()
        mock_event_service.get_production_progress.return_value = []

        get_production_progress(event_id=1, session=mock_session)

        # session_scope should not be called when session is provided
        mock_scope.assert_not_called()

    @patch("src.services.planning.progress.event_service")
    @patch("src.services.planning.progress.session_scope")
    def test_production_progress_without_session(self, mock_scope, mock_event_service):
        """Test that session_scope is used when no session provided."""
        mock_context = MagicMock()
        mock_scope.return_value.__enter__ = MagicMock(return_value=mock_context)
        mock_scope.return_value.__exit__ = MagicMock(return_value=False)
        mock_event_service.get_production_progress.return_value = []

        get_production_progress(event_id=1)

        # session_scope should be called
        mock_scope.assert_called_once()

    @patch("src.services.planning.progress.event_service")
    @patch("src.services.planning.progress.session_scope")
    def test_assembly_progress_with_session(self, mock_scope, mock_event_service):
        """Test that passing session skips session_scope for assembly."""
        mock_session = MagicMock()
        mock_event_service.get_assembly_progress.return_value = []

        get_assembly_progress(event_id=1, session=mock_session)

        mock_scope.assert_not_called()


class TestProgressPercentageCalculation:
    """Tests for accurate percentage calculation."""

    @patch("src.services.planning.progress.event_service")
    def test_percentage_rounded_to_two_decimals(self, mock_event_service):
        """Test that percentages are rounded to 2 decimal places."""
        # 3/7 = 0.428571... should be 42.86
        mock_event_service.get_production_progress.return_value = [
            {
                "recipe_id": 1,
                "recipe_name": "Cookies",
                "target_batches": 7,
                "produced_batches": 3,
                "produced_yield": 144,
                "progress_pct": 42.86,
                "is_complete": False,
            }
        ]

        result = get_production_progress(event_id=1)

        assert result[0].progress_percent == 42.86

    @patch("src.services.planning.progress.event_service")
    def test_zero_target_batches_handled(self, mock_event_service):
        """Test that zero target batches doesn't cause division by zero."""
        # This shouldn't happen in practice, but guard against it
        mock_event_service.get_production_progress.return_value = [
            {
                "recipe_id": 1,
                "recipe_name": "Cookies",
                "target_batches": 0,  # Edge case
                "produced_batches": 0,
                "produced_yield": 0,
                "progress_pct": 0.0,
                "is_complete": False,
            }
        ]

        result = get_production_progress(event_id=1)

        # Should handle gracefully without division by zero
        assert result[0].progress_percent == 0.0
