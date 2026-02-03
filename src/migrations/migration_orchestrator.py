"""
Migration orchestrator for coordinated multi-step migration process.

This module coordinates the complete migration workflow from the legacy single-tier
FinishedGood model to the new two-tier hierarchical system, ensuring proper
sequencing, comprehensive validation, and safe rollback capabilities.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import os

from ..services.migration_service import MigrationService
from ..services.exceptions import ServiceError
from ..utils.backup_validator import (
    create_database_backup,
    validate_backup_integrity,
    restore_database_from_backup,
)

logger = logging.getLogger(__name__)


class MigrationPhase(Enum):
    """Enum for migration phases."""

    NOT_STARTED = "not_started"
    VALIDATION = "validation"
    BACKUP = "backup"
    SCHEMA = "schema"
    DATA = "data"
    INDEXES = "indexes"
    POST_VALIDATION = "post_validation"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationOrchestrator:
    """
    Orchestrator for coordinated multi-step migration workflow.

    This class manages the complete migration process with proper phase sequencing,
    detailed progress tracking, comprehensive error handling, and rollback
    capabilities at each phase.

    Migration Phases:
    1. Validation - Pre-migration data integrity checks
    2. Backup - Create and validate database backup
    3. Schema - Create new table structures
    4. Data - Transform and migrate data
    5. Indexes - Create indexes and constraints
    6. Post-Validation - Verify migration success
    7. Completed - Migration finished successfully

    Key Features:
    - Phase-by-phase execution with checkpoint validation
    - Comprehensive error handling and recovery
    - Detailed progress tracking and logging
    - Rollback capability at each phase
    - Migration state persistence
    - Performance monitoring
    """

    def __init__(self, database_path: str = None):
        """
        Initialize migration orchestrator.

        Args:
            database_path: Path to database file (for backup/restore operations)
        """
        self.database_path = database_path or "bake_tracker.db"
        self.migration_state = {
            "current_phase": MigrationPhase.NOT_STARTED,
            "started_at": None,
            "completed_at": None,
            "backup_path": None,
            "phases": {},
            "errors": [],
            "warnings": [],
        }

    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get current migration status and progress.

        Returns:
            Dictionary with comprehensive migration status:
            - current_phase: Current migration phase
            - migration_completed: Whether migration is completed
            - migration_started: Whether migration has started
            - phases_completed: Number of phases completed
            - total_phases: Total number of migration phases
            - errors: List of errors encountered
            - warnings: List of warnings
            - backup_available: Whether backup is available
            - rollback_available: Whether rollback is possible
        """
        status = {
            "current_phase": self.migration_state["current_phase"].value,
            "migration_completed": self.migration_state["current_phase"]
            == MigrationPhase.COMPLETED,
            "migration_started": self.migration_state["current_phase"]
            != MigrationPhase.NOT_STARTED,
            "phases_completed": len(
                [p for p in self.migration_state["phases"].values() if p.get("completed", False)]
            ),
            "total_phases": 6,  # validation, backup, schema, data, indexes, post_validation
            "errors": self.migration_state["errors"],
            "warnings": self.migration_state["warnings"],
            "backup_available": bool(self.migration_state.get("backup_path")),
            "rollback_available": self._is_rollback_available(),
            "started_at": self.migration_state.get("started_at"),
            "completed_at": self.migration_state.get("completed_at"),
            "phases": self.migration_state["phases"],
        }

        # Add phase-specific progress
        if status["migration_started"]:
            status["progress_percentage"] = self._calculate_progress_percentage()

        return status

    def execute_full_migration(self) -> Dict[str, Any]:
        """
        Execute complete migration workflow with all phases.

        Runs the complete migration process from start to finish, with proper
        error handling and rollback capabilities at each phase.

        Returns:
            Dictionary with migration results:
            - success: Overall migration success
            - completed_phases: Number of phases completed
            - failed_phase: Phase that failed (if any)
            - backup_path: Path to backup file
            - errors: List of errors encountered
            - rollback_performed: Whether rollback was performed
        """
        result = {
            "success": False,
            "completed_phases": 0,
            "failed_phase": None,
            "backup_path": None,
            "errors": [],
            "rollback_performed": False,
        }

        try:
            logger.info("Starting full migration workflow")
            self._start_migration()

            # Phase 1: Validation
            if not self._execute_validation_phase():
                result["failed_phase"] = "validation"
                return result

            # Phase 2: Backup
            if not self._execute_backup_phase():
                result["failed_phase"] = "backup"
                return result

            result["backup_path"] = self.migration_state["backup_path"]

            # Phase 3: Schema
            if not self._execute_schema_phase():
                result["failed_phase"] = "schema"
                self._attempt_rollback()
                result["rollback_performed"] = True
                return result

            # Phase 4: Data Migration
            if not self._execute_data_phase():
                result["failed_phase"] = "data"
                self._attempt_rollback()
                result["rollback_performed"] = True
                return result

            # Phase 5: Indexes and Constraints
            if not self._execute_indexes_phase():
                result["failed_phase"] = "indexes"
                self._attempt_rollback()
                result["rollback_performed"] = True
                return result

            # Phase 6: Post-Migration Validation
            if not self._execute_post_validation_phase():
                result["failed_phase"] = "post_validation"
                self._attempt_rollback()
                result["rollback_performed"] = True
                return result

            # Migration completed successfully
            self._complete_migration()
            result["success"] = True
            result["completed_phases"] = 6

            logger.info("Full migration workflow completed successfully")

        except (ServiceError, Exception) as e:
            error_msg = f"Migration workflow failed: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            self.migration_state["errors"].append(error_msg)
            self.migration_state["current_phase"] = MigrationPhase.FAILED

            # Attempt rollback
            self._attempt_rollback()
            result["rollback_performed"] = True

        # Copy errors from state
        result["errors"].extend(self.migration_state["errors"])

        return result

    def _start_migration(self) -> None:
        """Initialize migration state and logging."""
        self.migration_state["started_at"] = datetime.now().isoformat()
        self.migration_state["current_phase"] = MigrationPhase.VALIDATION
        logger.info("Migration started")

    def _complete_migration(self) -> None:
        """Mark migration as completed."""
        self.migration_state["completed_at"] = datetime.now().isoformat()
        self.migration_state["current_phase"] = MigrationPhase.COMPLETED
        logger.info("Migration completed successfully")

    def _execute_validation_phase(self) -> bool:
        """Execute pre-migration validation phase."""
        phase_name = "validation"
        logger.info(f"Starting {phase_name} phase")

        try:
            self.migration_state["current_phase"] = MigrationPhase.VALIDATION
            phase_start = datetime.now()

            validation_result = MigrationService.validate_pre_migration()

            phase_info = {
                "started_at": phase_start.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "completed": validation_result["is_ready"],
                "result": validation_result,
            }

            self.migration_state["phases"][phase_name] = phase_info

            if validation_result["is_ready"]:
                logger.info(f"{phase_name} phase completed successfully")
                if validation_result["warnings"]:
                    self.migration_state["warnings"].extend(validation_result["warnings"])
                return True
            else:
                error_msg = f"Validation failed: {validation_result['validation_errors']}"
                logger.error(error_msg)
                self.migration_state["errors"].append(error_msg)
                return False

        except (ServiceError, Exception) as e:
            error_msg = f"Validation phase failed: {e}"
            logger.error(error_msg)
            self.migration_state["errors"].append(error_msg)
            return False

    def _execute_backup_phase(self) -> bool:
        """Execute database backup phase."""
        phase_name = "backup"
        logger.info(f"Starting {phase_name} phase")

        try:
            self.migration_state["current_phase"] = MigrationPhase.BACKUP
            phase_start = datetime.now()

            # Create backup
            success, backup_path = create_database_backup(self.database_path)

            if success:
                # Validate backup
                validation = validate_backup_integrity(backup_path)
                if validation["is_valid"]:
                    self.migration_state["backup_path"] = backup_path

                    phase_info = {
                        "started_at": phase_start.isoformat(),
                        "completed_at": datetime.now().isoformat(),
                        "completed": True,
                        "backup_path": backup_path,
                        "validation": validation,
                    }

                    self.migration_state["phases"][phase_name] = phase_info
                    logger.info(f"{phase_name} phase completed: {backup_path}")
                    return True
                else:
                    error_msg = f"Backup validation failed: {validation['error_message']}"
                    logger.error(error_msg)
                    self.migration_state["errors"].append(error_msg)
                    return False
            else:
                error_msg = f"Backup creation failed: {backup_path}"
                logger.error(error_msg)
                self.migration_state["errors"].append(error_msg)
                return False

        except (ServiceError, Exception) as e:
            error_msg = f"Backup phase failed: {e}"
            logger.error(error_msg)
            self.migration_state["errors"].append(error_msg)
            return False

    def _execute_schema_phase(self) -> bool:
        """Execute schema creation phase."""
        phase_name = "schema"
        logger.info(f"Starting {phase_name} phase")

        try:
            self.migration_state["current_phase"] = MigrationPhase.SCHEMA
            phase_start = datetime.now()

            success = MigrationService.execute_schema_migration()

            phase_info = {
                "started_at": phase_start.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "completed": success,
            }

            self.migration_state["phases"][phase_name] = phase_info

            if success:
                logger.info(f"{phase_name} phase completed successfully")
                return True
            else:
                error_msg = "Schema migration failed"
                logger.error(error_msg)
                self.migration_state["errors"].append(error_msg)
                return False

        except (ServiceError, Exception) as e:
            error_msg = f"Schema phase failed: {e}"
            logger.error(error_msg)
            self.migration_state["errors"].append(error_msg)
            return False

    def _execute_data_phase(self) -> bool:
        """Execute data migration phase."""
        phase_name = "data"
        logger.info(f"Starting {phase_name} phase")

        try:
            self.migration_state["current_phase"] = MigrationPhase.DATA
            phase_start = datetime.now()

            migration_result = MigrationService.migrate_finished_good_to_unit()

            phase_info = {
                "started_at": phase_start.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "completed": migration_result["success"],
                "result": migration_result,
            }

            self.migration_state["phases"][phase_name] = phase_info

            if migration_result["success"]:
                logger.info(
                    f"{phase_name} phase completed: {migration_result['migrated_count']} records migrated"
                )
                return True
            else:
                error_msg = f"Data migration failed: {migration_result['errors']}"
                logger.error(error_msg)
                self.migration_state["errors"].append(error_msg)
                return False

        except (ServiceError, Exception) as e:
            error_msg = f"Data phase failed: {e}"
            logger.error(error_msg)
            self.migration_state["errors"].append(error_msg)
            return False

    def _execute_indexes_phase(self) -> bool:
        """Execute index and constraint creation phase."""
        phase_name = "indexes"
        logger.info(f"Starting {phase_name} phase")

        try:
            self.migration_state["current_phase"] = MigrationPhase.INDEXES
            phase_start = datetime.now()

            # Create indexes if they don't exist
            index_creation_result = self._create_missing_indexes()

            # Validate index creation and performance
            index_results = self._validate_index_performance()

            phase_info = {
                "started_at": phase_start.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "completed": index_results["all_indexes_valid"],
                "index_creation": index_creation_result,
                "index_validation": index_results,
            }

            self.migration_state["phases"][phase_name] = phase_info

            if index_results["all_indexes_valid"]:
                logger.info(f"{phase_name} phase completed successfully")
                logger.info(f"Index performance results: {index_results['performance_summary']}")
                return True
            else:
                error_msg = f"Index validation failed: {index_results['errors']}"
                logger.error(error_msg)
                self.migration_state["errors"].append(error_msg)
                return False

        except (ServiceError, Exception) as e:
            error_msg = f"Indexes phase failed: {e}"
            logger.error(error_msg)
            self.migration_state["errors"].append(error_msg)
            return False

    def _create_missing_indexes(self) -> dict:
        """Create indexes that don't exist."""
        from ..database import get_db_session
        from sqlalchemy import text

        result = {"indexes_created": [], "indexes_existed": [], "errors": []}

        try:
            with get_db_session() as session:
                # Index definitions from FinishedUnit model
                index_definitions = [
                    {
                        "name": "idx_finished_unit_slug",
                        "sql": "CREATE INDEX IF NOT EXISTS idx_finished_unit_slug ON finished_units(slug)",
                    },
                    {
                        "name": "idx_finished_unit_display_name",
                        "sql": "CREATE INDEX IF NOT EXISTS idx_finished_unit_display_name ON finished_units(display_name)",
                    },
                    {
                        "name": "idx_finished_unit_recipe",
                        "sql": "CREATE INDEX IF NOT EXISTS idx_finished_unit_recipe ON finished_units(recipe_id)",
                    },
                    {
                        "name": "idx_finished_unit_category",
                        "sql": "CREATE INDEX IF NOT EXISTS idx_finished_unit_category ON finished_units(category)",
                    },
                    {
                        "name": "idx_finished_unit_inventory",
                        "sql": "CREATE INDEX IF NOT EXISTS idx_finished_unit_inventory ON finished_units(inventory_count)",
                    },
                    {
                        "name": "idx_finished_unit_created_at",
                        "sql": "CREATE INDEX IF NOT EXISTS idx_finished_unit_created_at ON finished_units(created_at)",
                    },
                    {
                        "name": "idx_finished_unit_recipe_inventory",
                        "sql": "CREATE INDEX IF NOT EXISTS idx_finished_unit_recipe_inventory ON finished_units(recipe_id, inventory_count)",
                    },
                ]

                for index_def in index_definitions:
                    try:
                        # Check if index exists
                        existing = session.execute(
                            text(
                                "SELECT name FROM sqlite_master WHERE type='index' AND name = :name"
                            ),
                            {"name": index_def["name"]},
                        ).fetchone()

                        if existing:
                            result["indexes_existed"].append(index_def["name"])
                            logger.debug(f"Index {index_def['name']} already exists")
                        else:
                            # Create index
                            session.execute(text(index_def["sql"]))
                            result["indexes_created"].append(index_def["name"])
                            logger.info(f"Created index {index_def['name']}")
                    except (ServiceError, Exception) as e:
                        error_msg = f"Failed to create index {index_def['name']}: {e}"
                        result["errors"].append(error_msg)
                        logger.error(error_msg)

                session.commit()

        except (ServiceError, Exception) as e:
            result["errors"].append(f"Index creation error: {e}")
            logger.error(f"Index creation failed: {e}")

        return result

    def _validate_index_performance(self) -> dict:
        """Validate that indexes exist and meet performance targets."""
        from ..database import get_db_session
        from sqlalchemy import text
        import time

        result = {
            "all_indexes_valid": True,
            "indexes_checked": [],
            "performance_summary": {},
            "errors": [],
        }

        try:
            with get_db_session() as session:
                # Expected indexes for FinishedUnit
                expected_indexes = [
                    "idx_finished_unit_slug",
                    "idx_finished_unit_display_name",
                    "idx_finished_unit_recipe",
                    "idx_finished_unit_inventory",
                    "idx_finished_unit_created_at",
                    "idx_finished_unit_recipe_inventory",
                    "uq_finished_unit_slug",
                ]

                # Check if indexes exist
                for index_name in expected_indexes:
                    index_exists = session.execute(
                        text(
                            """
                        SELECT name FROM sqlite_master
                        WHERE type='index' AND name = :index_name
                    """
                        ),
                        {"index_name": index_name},
                    ).fetchone()

                    if index_exists:
                        result["indexes_checked"].append(
                            {"name": index_name, "exists": True, "status": "OK"}
                        )
                    else:
                        result["indexes_checked"].append(
                            {"name": index_name, "exists": False, "status": "MISSING"}
                        )
                        result["errors"].append(f"Index {index_name} not found")
                        result["all_indexes_valid"] = False

                # Performance validation queries with timing
                performance_tests = [
                    {
                        "name": "slug_lookup",
                        "query": "SELECT COUNT(*) FROM finished_units WHERE slug = 'test-slug'",
                        "target_ms": 50,
                        "description": "Fast slug lookup",
                    },
                    {
                        "name": "display_name_search",
                        "query": "SELECT COUNT(*) FROM finished_units WHERE display_name LIKE '%test%'",
                        "target_ms": 200,
                        "description": "Display name search",
                    },
                    {
                        "name": "recipe_inventory_query",
                        "query": "SELECT COUNT(*) FROM finished_units WHERE recipe_id = 1 AND inventory_count > 0",
                        "target_ms": 200,
                        "description": "Recipe-inventory composite query",
                    },
                    {
                        "name": "temporal_query",
                        "query": "SELECT COUNT(*) FROM finished_units WHERE created_at > datetime('now', '-30 days')",
                        "target_ms": 300,
                        "description": "Recent items temporal query",
                    },
                ]

                for test in performance_tests:
                    start_time = time.perf_counter()
                    try:
                        session.execute(text(test["query"]))
                        end_time = time.perf_counter()
                        duration_ms = (end_time - start_time) * 1000

                        result["performance_summary"][test["name"]] = {
                            "duration_ms": round(duration_ms, 2),
                            "target_ms": test["target_ms"],
                            "meets_target": duration_ms <= test["target_ms"],
                            "description": test["description"],
                        }

                        if duration_ms > test["target_ms"]:
                            logger.warning(
                                f"Performance test '{test['name']}' took {duration_ms:.2f}ms, "
                                f"exceeds target {test['target_ms']}ms"
                            )

                    except (ServiceError, Exception) as e:
                        result["errors"].append(f"Performance test '{test['name']}' failed: {e}")
                        result["all_indexes_valid"] = False

                logger.info(
                    f"Index validation completed: {len(result['indexes_checked'])} indexes checked"
                )

        except (ServiceError, Exception) as e:
            result["errors"].append(f"Index validation error: {e}")
            result["all_indexes_valid"] = False
            logger.error(f"Index validation failed: {e}")

        return result

    def _execute_post_validation_phase(self) -> bool:
        """Execute post-migration validation phase."""
        phase_name = "post_validation"
        logger.info(f"Starting {phase_name} phase")

        try:
            self.migration_state["current_phase"] = MigrationPhase.POST_VALIDATION
            phase_start = datetime.now()

            validation_result = MigrationService.validate_post_migration()

            phase_info = {
                "started_at": phase_start.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "completed": validation_result["is_valid"],
                "result": validation_result,
            }

            self.migration_state["phases"][phase_name] = phase_info

            if validation_result["is_valid"]:
                logger.info(f"{phase_name} phase completed successfully")
                return True
            else:
                error_msg = f"Post-validation failed: {validation_result['missing_records']}"
                logger.error(error_msg)
                self.migration_state["errors"].append(error_msg)
                return False

        except (ServiceError, Exception) as e:
            error_msg = f"Post-validation phase failed: {e}"
            logger.error(error_msg)
            self.migration_state["errors"].append(error_msg)
            return False

    def _attempt_rollback(self) -> bool:
        """Attempt to rollback migration using backup."""
        if not self.migration_state.get("backup_path"):
            logger.error("No backup available for rollback")
            return False

        try:
            logger.warning("Attempting migration rollback")
            success, message = MigrationService.rollback_migration(
                self.migration_state["backup_path"]
            )

            if success:
                self.migration_state["current_phase"] = MigrationPhase.ROLLED_BACK
                logger.info(f"Rollback successful: {message}")
                return True
            else:
                self.migration_state["current_phase"] = MigrationPhase.FAILED
                logger.error(f"Rollback failed: {message}")
                return False

        except (ServiceError, Exception) as e:
            logger.error(f"Rollback attempt failed: {e}")
            self.migration_state["current_phase"] = MigrationPhase.FAILED
            return False

    def _is_rollback_available(self) -> bool:
        """Check if rollback is available."""
        return bool(self.migration_state.get("backup_path")) and self.migration_state[
            "current_phase"
        ] not in [MigrationPhase.NOT_STARTED, MigrationPhase.COMPLETED, MigrationPhase.ROLLED_BACK]

    def _calculate_progress_percentage(self) -> int:
        """Calculate migration progress percentage."""
        phase_weights = {
            MigrationPhase.VALIDATION: 10,
            MigrationPhase.BACKUP: 15,
            MigrationPhase.SCHEMA: 20,
            MigrationPhase.DATA: 30,
            MigrationPhase.INDEXES: 15,
            MigrationPhase.POST_VALIDATION: 10,
        }

        total_weight = sum(phase_weights.values())
        completed_weight = 0

        for phase_name, phase_info in self.migration_state["phases"].items():
            if phase_info.get("completed", False):
                # Map phase name to enum
                for phase_enum in MigrationPhase:
                    if phase_enum.value == phase_name:
                        completed_weight += phase_weights.get(phase_enum, 0)
                        break

        return int((completed_weight / total_weight) * 100)

    def rollback_to_backup(self) -> Dict[str, Any]:
        """
        Manual rollback to backup (can be called independently).

        Returns:
            Dictionary with rollback results
        """
        result = {"success": False, "message": "", "backup_used": None}

        try:
            if not self._is_rollback_available():
                result["message"] = "Rollback not available - no backup or invalid state"
                return result

            success = self._attempt_rollback()
            result["success"] = success
            result["backup_used"] = self.migration_state.get("backup_path")

            if success:
                result["message"] = "Rollback completed successfully"
            else:
                result["message"] = "Rollback failed - check logs for details"

        except (ServiceError, Exception) as e:
            result["message"] = f"Rollback error: {e}"
            logger.error(f"Manual rollback failed: {e}")

        return result


# Module-level convenience functions
def get_migration_status() -> Dict[str, Any]:
    """
    Get current migration status.

    Returns:
        Dictionary with migration status
    """
    orchestrator = MigrationOrchestrator()
    return orchestrator.get_migration_status()


def execute_full_migration(database_path: str = None) -> Dict[str, Any]:
    """
    Execute complete migration workflow.

    Args:
        database_path: Optional database path

    Returns:
        Dictionary with migration results
    """
    orchestrator = MigrationOrchestrator(database_path)
    return orchestrator.execute_full_migration()
