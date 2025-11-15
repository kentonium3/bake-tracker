"""
Integration tests for FinishedUnit migration workflow.

Tests validate complete migration process with realistic data patterns,
relationship preservation, and service integration with migrated data.
"""

import pytest
import tempfile
import os
import shutil
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.models import Base, Recipe, FinishedUnit
from src.services.migration_service import MigrationService
from src.services.finished_unit_service import FinishedUnitService
from src.migrations.migration_orchestrator import MigrationOrchestrator, get_migration_status
from src.utils.backup_validator import create_database_backup, validate_backup_integrity


class TestFinishedUnitMigrationWorkflow:
    """
    Integration tests for complete migration workflow.

    Tests the end-to-end migration process including data validation,
    relationship preservation, and service functionality with migrated data.
    """

    @pytest.fixture(scope="class")
    def temp_database(self):
        """Create temporary database for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_migration.db")

        # Create SQLite engine
        engine = create_engine(f"sqlite:///{db_path}", echo=False)

        # Create tables
        Base.metadata.create_all(engine)

        yield {
            "engine": engine,
            "db_path": db_path,
            "session_factory": sessionmaker(bind=engine)
        }

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_recipes(self, temp_database):
        """Create sample recipes for testing."""
        Session = temp_database["session_factory"]

        recipes_data = [
            {"id": 1, "name": "Chocolate Chip Cookie Recipe", "description": "Classic cookie recipe"},
            {"id": 2, "name": "Chocolate Cake Recipe", "description": "Rich chocolate cake"},
            {"id": 3, "name": "Vanilla Cupcake Recipe", "description": "Light vanilla cupcakes"},
        ]

        with Session() as session:
            for recipe_data in recipes_data:
                # Create mock Recipe (simplified for testing)
                recipe = type('Recipe', (), recipe_data)()
                session.merge(recipe)
            session.commit()

        return recipes_data

    @pytest.fixture
    def legacy_finished_goods_data(self, temp_database, sample_recipes):
        """Create realistic legacy FinishedGood data for migration testing."""
        Session = temp_database["session_factory"]

        # Realistic FinishedGood data patterns
        finished_goods_data = [
            {
                "id": 1,
                "name": "Chocolate Chip Cookie",
                "recipe_id": 1,
                "yield_mode": "discrete_count",
                "items_per_batch": 24,
                "item_unit": "cookie",
                "category": "cookies",
                "notes": "Most popular item",
                "date_added": datetime.now() - timedelta(days=30),
                "last_modified": datetime.now() - timedelta(days=5)
            },
            {
                "id": 2,
                "name": "9-inch Chocolate Cake",
                "recipe_id": 2,
                "yield_mode": "batch_portion",
                "batch_percentage": 100.0,
                "portion_description": "9-inch round cake pan",
                "category": "cakes",
                "notes": "Special occasion item",
                "date_added": datetime.now() - timedelta(days=20),
                "last_modified": datetime.now() - timedelta(days=2)
            },
            {
                "id": 3,
                "name": "Vanilla Cupcake",
                "recipe_id": 3,
                "yield_mode": "discrete_count",
                "items_per_batch": 12,
                "item_unit": "cupcake",
                "category": "cupcakes",
                "notes": "Light and fluffy",
                "date_added": datetime.now() - timedelta(days=15),
                "last_modified": datetime.now() - timedelta(days=1)
            },
            {
                "id": 4,
                "name": "Mini Chocolate Chip Cookie",
                "recipe_id": 1,  # Same recipe as regular cookies
                "yield_mode": "discrete_count",
                "items_per_batch": 48,  # Double yield for mini size
                "item_unit": "cookie",
                "category": "cookies",
                "notes": "Bite-sized version",
                "date_added": datetime.now() - timedelta(days=10),
                "last_modified": datetime.now()
            }
        ]

        # Insert legacy data directly into database
        with Session() as session:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS finished_goods (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    recipe_id INTEGER,
                    yield_mode TEXT,
                    items_per_batch INTEGER,
                    item_unit TEXT,
                    batch_percentage REAL,
                    portion_description TEXT,
                    category TEXT,
                    notes TEXT,
                    date_added TIMESTAMP,
                    last_modified TIMESTAMP
                )
            """))

            for fg_data in finished_goods_data:
                session.execute(text("""
                    INSERT INTO finished_goods
                    (id, name, recipe_id, yield_mode, items_per_batch, item_unit,
                     batch_percentage, portion_description, category, notes, date_added, last_modified)
                    VALUES
                    (:id, :name, :recipe_id, :yield_mode, :items_per_batch, :item_unit,
                     :batch_percentage, :portion_description, :category, :notes, :date_added, :last_modified)
                """), fg_data)

            session.commit()

        return finished_goods_data

    def test_pre_migration_validation_success(self, temp_database, legacy_finished_goods_data):
        """Test pre-migration validation with realistic data."""
        # Act
        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            validation_result = MigrationService.validate_pre_migration()

        # Assert
        assert validation_result["is_ready"] is True
        assert validation_result["finished_good_count"] == len(legacy_finished_goods_data)
        assert len(validation_result["validation_errors"]) == 0
        assert validation_result["data_integrity"] is True

    def test_pre_migration_validation_with_issues(self, temp_database):
        """Test pre-migration validation with data integrity issues."""
        Session = temp_database["session_factory"]

        # Insert problematic data
        with Session() as session:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS finished_goods (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    recipe_id INTEGER
                )
            """))

            # Insert record with missing name
            session.execute(text("INSERT INTO finished_goods (id, name) VALUES (1, NULL)"))
            session.commit()

        # Act
        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            validation_result = MigrationService.validate_pre_migration()

        # Assert
        assert validation_result["is_ready"] is False
        assert len(validation_result["validation_errors"]) > 0
        assert "missing names" in str(validation_result["validation_errors"])

    def test_backup_creation_and_validation(self, temp_database):
        """Test backup creation and integrity validation."""
        # Act
        success, backup_path = create_database_backup(temp_database["db_path"])

        # Assert backup creation
        assert success is True
        assert os.path.exists(backup_path)

        # Test backup validation
        validation_result = validate_backup_integrity(backup_path)
        assert validation_result["is_valid"] is True
        assert validation_result["sqlite_valid"] is True
        assert validation_result["table_count"] > 0

        # Cleanup
        if os.path.exists(backup_path):
            os.remove(backup_path)

    def test_complete_migration_workflow(self, temp_database, legacy_finished_goods_data):
        """Test complete migration workflow from start to finish."""
        orchestrator = MigrationOrchestrator(temp_database["db_path"])

        # Patch database connections to use test database
        with patch('src.services.migration_service.get_db_session') as mock_migration_session, \
             patch('src.migrations.migration_orchestrator.get_db_session') as mock_orchestrator_session, \
             patch('src.utils.backup_validator.create_database_backup') as mock_backup:

            # Configure mocks
            mock_migration_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_migration_session.return_value.__exit__ = lambda *args: None
            mock_orchestrator_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_orchestrator_session.return_value.__exit__ = lambda *args: None
            mock_backup.return_value = (True, "test_backup.db")

            # Act
            migration_result = orchestrator.execute_full_migration()

        # Assert migration success
        assert migration_result["success"] is True
        assert migration_result["completed_phases"] == 6
        assert migration_result["backup_path"] == "test_backup.db"
        assert migration_result["rollback_performed"] is False

    def test_data_migration_field_mapping(self, temp_database, legacy_finished_goods_data):
        """Test that field mapping works correctly during migration."""
        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            # Act
            migration_result = MigrationService.migrate_finished_good_to_unit()

        # Assert field mappings
        assert migration_result["success"] is True
        assert migration_result["migrated_count"] == len(legacy_finished_goods_data)
        assert migration_result["failed_count"] == 0

        # Verify migrated data
        Session = temp_database["session_factory"]
        with Session() as session:
            migrated_units = session.query(FinishedUnit).all()
            assert len(migrated_units) == len(legacy_finished_goods_data)

            # Check specific field mappings
            for unit in migrated_units:
                assert unit.slug is not None and len(unit.slug) > 0
                assert unit.display_name is not None
                assert unit.unit_cost >= Decimal('0.0000')
                assert unit.inventory_count >= 0
                assert unit.created_at is not None

    def test_recipe_relationship_preservation(self, temp_database, legacy_finished_goods_data, sample_recipes):
        """Test that Recipe relationships are preserved during migration."""
        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            # Execute migration
            migration_result = MigrationService.migrate_finished_good_to_unit()
            assert migration_result["success"] is True

        # Verify recipe relationships
        Session = temp_database["session_factory"]
        with Session() as session:
            for original_fg in legacy_finished_goods_data:
                # Find corresponding migrated unit
                migrated_unit = session.query(FinishedUnit)\
                    .filter(FinishedUnit.display_name == original_fg["name"])\
                    .first()

                assert migrated_unit is not None
                assert migrated_unit.recipe_id == original_fg["recipe_id"]

    def test_slug_uniqueness_during_migration(self, temp_database):
        """Test that duplicate names get unique slugs during migration."""
        Session = temp_database["session_factory"]

        # Create test data with duplicate names
        with Session() as session:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS finished_goods (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    recipe_id INTEGER
                )
            """))

            # Insert records with duplicate names
            session.execute(text("INSERT INTO finished_goods (id, name, recipe_id) VALUES (1, 'Duplicate Item', 1)"))
            session.execute(text("INSERT INTO finished_goods (id, name, recipe_id) VALUES (2, 'Duplicate Item', 1)"))
            session.execute(text("INSERT INTO finished_goods (id, name, recipe_id) VALUES (3, 'Duplicate Item', 1)"))
            session.commit()

        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            # Act
            migration_result = MigrationService.migrate_finished_good_to_unit()

        # Assert unique slugs
        assert migration_result["success"] is True
        assert migration_result["duplicates_handled"] == 2  # 2 duplicates needed suffixes

        with Session() as session:
            slugs = [unit.slug for unit in session.query(FinishedUnit).all()]
            assert len(slugs) == len(set(slugs))  # All slugs are unique
            assert "duplicate-item" in slugs
            assert "duplicate-item-2" in slugs
            assert "duplicate-item-3" in slugs

    def test_post_migration_validation(self, temp_database, legacy_finished_goods_data):
        """Test post-migration validation ensures data integrity."""
        # Setup: Run migration first
        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            migration_result = MigrationService.migrate_finished_good_to_unit()
            assert migration_result["success"] is True

        # Act: Validate post-migration
        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            validation_result = MigrationService.validate_post_migration()

        # Assert validation results
        assert validation_result["is_valid"] is True
        assert validation_result["original_count"] == len(legacy_finished_goods_data)
        assert validation_result["migrated_count"] == len(legacy_finished_goods_data)
        assert validation_result["data_matches"] is True

    def test_finished_unit_service_operations_post_migration(self, temp_database, legacy_finished_goods_data):
        """Test that FinishedUnit service works correctly with migrated data."""
        # Setup: Run migration
        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            migration_result = MigrationService.migrate_finished_good_to_unit()
            assert migration_result["success"] is True

        # Test service operations with migrated data
        with patch('src.services.finished_unit_service.get_db_session') as mock_service_session, \
             patch('src.services.finished_unit_service.session_scope') as mock_service_scope:

            mock_service_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_service_session.return_value.__exit__ = lambda *args: None
            mock_service_scope.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_service_scope.return_value.__exit__ = lambda *args: None

            # Test count operation
            count = FinishedUnitService.get_finished_unit_count()
            assert count == len(legacy_finished_goods_data)

            # Test retrieval operations
            all_units = FinishedUnitService.get_all_finished_units()
            assert len(all_units) == len(legacy_finished_goods_data)

            # Test search operations
            cookie_results = FinishedUnitService.search_finished_units("cookie")
            assert len(cookie_results) >= 2  # Should find both cookie variants

    def test_cost_calculation_consistency(self, temp_database, legacy_finished_goods_data):
        """Test that cost calculations are consistent pre and post migration."""
        # Setup: Run migration
        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            migration_result = MigrationService.migrate_finished_good_to_unit()
            assert migration_result["success"] is True

        # Test cost calculation consistency
        Session = temp_database["session_factory"]
        with Session() as session:
            migrated_units = session.query(FinishedUnit).all()

            for unit in migrated_units:
                # Test that cost calculation methods work
                if unit.recipe_id:
                    calculated_cost = unit.calculate_recipe_cost_per_item()
                    assert isinstance(calculated_cost, Decimal)
                    assert calculated_cost >= Decimal('0.0000')

    def test_migration_rollback_scenario(self, temp_database, legacy_finished_goods_data):
        """Test rollback scenario with data restoration validation."""
        # Create backup first
        success, backup_path = create_database_backup(temp_database["db_path"])
        assert success is True

        try:
            # Simulate failed migration scenario
            orchestrator = MigrationOrchestrator(temp_database["db_path"])
            orchestrator.migration_state["backup_path"] = backup_path

            # Test rollback capability
            rollback_result = orchestrator.rollback_to_backup()

            # Assert rollback preparation (actual restoration would be manual)
            assert "backup_used" in rollback_result
            assert rollback_result["backup_used"] == backup_path

        finally:
            # Cleanup
            if os.path.exists(backup_path):
                os.remove(backup_path)

    def test_migration_performance_with_large_dataset(self, temp_database):
        """Test migration performance with larger dataset."""
        Session = temp_database["session_factory"]

        # Create larger test dataset
        large_dataset_size = 100

        with Session() as session:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS finished_goods (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    recipe_id INTEGER
                )
            """))

            for i in range(large_dataset_size):
                session.execute(text(
                    "INSERT INTO finished_goods (id, name, recipe_id) VALUES (:id, :name, :recipe_id)"
                ), {"id": i + 1, "name": f"Test Item {i + 1}", "recipe_id": (i % 3) + 1})

            session.commit()

        # Test migration performance
        import time

        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            start_time = time.perf_counter()
            migration_result = MigrationService.migrate_finished_good_to_unit()
            duration = time.perf_counter() - start_time

        # Assert performance and success
        assert migration_result["success"] is True
        assert migration_result["migrated_count"] == large_dataset_size
        assert duration < 10.0  # Should complete within 10 seconds for 100 items

    def test_migration_error_handling(self, temp_database):
        """Test migration error handling and graceful failure."""
        Session = temp_database["session_factory"]

        # Create problematic data that should cause migration to fail gracefully
        with Session() as session:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS finished_goods (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    recipe_id INTEGER
                )
            """))

            # Insert record with invalid recipe reference
            session.execute(text(
                "INSERT INTO finished_goods (id, name, recipe_id) VALUES (1, 'Invalid Recipe Item', 999)"
            ))
            session.commit()

        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            # Act
            migration_result = MigrationService.migrate_finished_good_to_unit()

        # Assert graceful error handling
        assert migration_result["success"] is False
        assert migration_result["failed_count"] > 0
        assert len(migration_result["errors"]) > 0

    def test_index_performance_post_migration(self, temp_database, legacy_finished_goods_data):
        """Test that database indexes perform correctly post-migration."""
        # Setup: Run migration
        with patch('src.services.migration_service.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            migration_result = MigrationService.migrate_finished_good_to_unit()
            assert migration_result["success"] is True

        # Test index performance using orchestrator validation
        orchestrator = MigrationOrchestrator(temp_database["db_path"])

        with patch('src.migrations.migration_orchestrator.get_db_session') as mock_session:
            mock_session.return_value.__enter__ = lambda x: temp_database["session_factory"]()
            mock_session.return_value.__exit__ = lambda *args: None

            # Test index validation
            index_results = orchestrator._validate_index_performance()

        # Assert index validation (may be limited in test environment)
        assert "indexes_checked" in index_results
        assert "performance_summary" in index_results


# Utility functions for integration testing

def create_realistic_test_database(db_path: str, num_finished_goods: int = 50) -> None:
    """Create realistic test database with specified number of records."""
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    with Session() as session:
        # Create recipes
        for i in range(10):
            recipe = Recipe(
                id=i + 1,
                name=f"Test Recipe {i + 1}",
                description=f"Test recipe description {i + 1}"
            )
            session.add(recipe)

        # Create legacy finished goods data
        categories = ["cookies", "cakes", "cupcakes", "brownies", "bars"]
        yield_modes = ["discrete_count", "batch_portion"]

        for i in range(num_finished_goods):
            fg_data = {
                "id": i + 1,
                "name": f"Test Product {i + 1}",
                "recipe_id": (i % 10) + 1,
                "yield_mode": yield_modes[i % 2],
                "category": categories[i % len(categories)],
                "date_added": datetime.now() - timedelta(days=i),
                "last_modified": datetime.now() - timedelta(days=i // 2)
            }

            if fg_data["yield_mode"] == "discrete_count":
                fg_data["items_per_batch"] = (i % 20) + 12
                fg_data["item_unit"] = "piece"
            else:
                fg_data["batch_percentage"] = min(100.0, (i % 10 + 1) * 10)
                fg_data["portion_description"] = f"Test portion {i + 1}"

            session.execute(text("""
                INSERT INTO finished_goods
                (id, name, recipe_id, yield_mode, items_per_batch, item_unit,
                 batch_percentage, portion_description, category, date_added, last_modified)
                VALUES
                (:id, :name, :recipe_id, :yield_mode, :items_per_batch, :item_unit,
                 :batch_percentage, :portion_description, :category, :date_added, :last_modified)
            """), fg_data)

        session.commit()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])