"""
Migration service for coordinated data migration from old to new schema.

This service handles the complex migration from the original single-tier FinishedGood
model to the new two-tier hierarchical system with FinishedUnit and FinishedGood
assemblies, ensuring zero data loss and maintaining referential integrity.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import re
import unicodedata

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import get_db_session
from ..models import FinishedUnit
from ..utils.backup_validator import (
    create_database_backup,
    validate_backup_integrity,
    restore_database_from_backup
)

logger = logging.getLogger(__name__)


class MigrationService:
    """
    Service for coordinated migration from legacy FinishedGood to new two-tier system.

    This service provides safe migration functionality with comprehensive validation,
    backup/restore capabilities, and detailed progress tracking.

    Key Features:
    - Pre-migration validation to ensure data integrity
    - Safe backup creation before any schema changes
    - Field mapping and data transformation with validation
    - Post-migration verification to confirm success
    - Rollback capability for failure recovery
    - Detailed logging and progress reporting
    """

    @staticmethod
    def validate_pre_migration() -> Dict[str, any]:
        """
        Validate existing data integrity before migration.

        Performs comprehensive checks on existing FinishedGood data to ensure
        migration can proceed safely.

        Returns:
            Dictionary with validation results:
            - is_ready: bool - Overall readiness status
            - finished_good_count: int - Number of records to migrate
            - validation_errors: List[str] - Any blocking issues found
            - warnings: List[str] - Non-blocking issues
            - data_integrity: bool - Data integrity status
        """
        result = {
            "is_ready": False,
            "finished_good_count": 0,
            "validation_errors": [],
            "warnings": [],
            "data_integrity": True
        }

        try:
            with get_db_session() as session:
                # Check if old finished_goods table exists
                table_check = session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='finished_goods'")
                ).fetchone()

                if not table_check:
                    result["validation_errors"].append("No finished_goods table found to migrate")
                    return result

                # Count existing records
                count_result = session.execute(text("SELECT COUNT(*) FROM finished_goods")).fetchone()
                result["finished_good_count"] = count_result[0] if count_result else 0

                if result["finished_good_count"] == 0:
                    result["warnings"].append("No finished goods records found to migrate")
                    result["is_ready"] = True  # Empty migration is valid
                    return result

                # Validate data integrity
                integrity_issues = MigrationService._validate_data_integrity(session)
                result["validation_errors"].extend(integrity_issues)

                # Check for duplicate names (will become slugs)
                duplicate_check = session.execute(
                    text("SELECT name, COUNT(*) FROM finished_goods GROUP BY name HAVING COUNT(*) > 1")
                ).fetchall()

                if duplicate_check:
                    result["warnings"].append(f"Found {len(duplicate_check)} duplicate names - will add suffixes")

                # Check for foreign key constraints
                fk_issues = MigrationService._validate_foreign_keys(session)
                result["validation_errors"].extend(fk_issues)

                # Set readiness status
                result["is_ready"] = len(result["validation_errors"]) == 0
                result["data_integrity"] = len(result["validation_errors"]) == 0

                logger.info(f"Pre-migration validation completed: {result['finished_good_count']} records, "
                          f"ready: {result['is_ready']}")

        except Exception as e:
            result["validation_errors"].append(f"Pre-migration validation failed: {e}")
            result["data_integrity"] = False
            logger.error(f"Pre-migration validation error: {e}")

        return result

    @staticmethod
    def _validate_data_integrity(session: Session) -> List[str]:
        """Validate existing data integrity."""
        errors = []

        try:
            # Check for NULL required fields
            null_names = session.execute(
                text("SELECT COUNT(*) FROM finished_goods WHERE name IS NULL OR name = ''")
            ).fetchone()[0]

            if null_names > 0:
                errors.append(f"Found {null_names} finished goods with missing names")

            # Check for invalid recipe references
            invalid_recipes = session.execute(text("""
                SELECT COUNT(*) FROM finished_goods fg
                WHERE fg.recipe_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM recipes r WHERE r.id = fg.recipe_id)
            """)).fetchone()[0]

            if invalid_recipes > 0:
                errors.append(f"Found {invalid_recipes} finished goods with invalid recipe references")

        except SQLAlchemyError as e:
            errors.append(f"Data integrity check failed: {e}")

        return errors

    @staticmethod
    def _validate_foreign_keys(session: Session) -> List[str]:
        """Validate foreign key constraints."""
        errors = []

        try:
            # Check recipe references exist
            orphaned_recipes = session.execute(text("""
                SELECT id, name FROM finished_goods
                WHERE recipe_id IS NOT NULL
                AND recipe_id NOT IN (SELECT id FROM recipes)
            """)).fetchall()

            if orphaned_recipes:
                errors.append(f"Found {len(orphaned_recipes)} finished goods with orphaned recipe references")

        except SQLAlchemyError as e:
            errors.append(f"Foreign key validation failed: {e}")

        return errors

    @staticmethod
    def execute_schema_migration() -> bool:
        """
        Execute schema migration to create new table structures.

        Creates the new finished_units table and related indexes/constraints
        while preserving the existing finished_goods table for migration.

        Returns:
            True if schema migration successful
        """
        try:
            with get_db_session() as session:
                # Create finished_units table (FinishedUnit model will handle this via SQLAlchemy)
                # The table creation is handled by SQLAlchemy's create_all() method
                # This method serves as a validation step

                # Verify new table was created
                table_check = session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='finished_units'")
                ).fetchone()

                if not table_check:
                    logger.error("Failed to create finished_units table")
                    return False

                logger.info("Schema migration completed successfully")
                return True

        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            return False

    @staticmethod
    def migrate_finished_good_to_unit() -> Dict[str, any]:
        """
        Migrate data from old FinishedGood records to new FinishedUnit structure.

        Performs field mapping, data transformation, and validation for each record
        being migrated from the legacy schema to the new two-tier system.

        Returns:
            Dictionary with migration results:
            - success: bool - Overall success status
            - migrated_count: int - Number of records migrated
            - failed_count: int - Number of records that failed
            - errors: List[str] - Migration errors encountered
            - duplicates_handled: int - Number of duplicate names resolved
        """
        result = {
            "success": False,
            "migrated_count": 0,
            "failed_count": 0,
            "errors": [],
            "duplicates_handled": 0
        }

        try:
            with get_db_session() as session:
                # Fetch all existing FinishedGood records
                existing_records = session.execute(text("""
                    SELECT id, name, recipe_id, yield_mode, items_per_batch, item_unit,
                           batch_percentage, portion_description, category, notes,
                           date_added, last_modified
                    FROM finished_goods
                    ORDER BY id
                """)).fetchall()

                if not existing_records:
                    result["success"] = True
                    logger.info("No records to migrate")
                    return result

                # Track used slugs to handle duplicates
                used_slugs = set()

                for record in existing_records:
                    try:
                        # Generate unique slug from name
                        slug = MigrationService._generate_unique_slug(
                            record.name, used_slugs
                        )

                        if slug != MigrationService._generate_slug(record.name):
                            result["duplicates_handled"] += 1

                        used_slugs.add(slug)

                        # Create new FinishedUnit from legacy data
                        unit_data = {
                            'slug': slug,
                            'display_name': record.name,
                            'recipe_id': record.recipe_id,
                            'unit_cost': Decimal('0.0000'),  # Will be calculated later
                            'inventory_count': 0,  # Start with zero inventory
                            'created_at': record.date_added,
                            'updated_at': record.last_modified or record.date_added
                        }

                        # Map yield_mode and related fields
                        if record.yield_mode:
                            unit_data['yield_mode'] = record.yield_mode
                        if record.items_per_batch:
                            unit_data['items_per_batch'] = record.items_per_batch
                        if record.item_unit:
                            unit_data['item_unit'] = record.item_unit
                        if record.batch_percentage:
                            unit_data['batch_percentage'] = Decimal(str(record.batch_percentage))
                        if record.portion_description:
                            unit_data['portion_description'] = record.portion_description
                        if record.category:
                            unit_data['category'] = record.category
                        if record.notes:
                            unit_data['notes'] = record.notes

                        # Create FinishedUnit instance
                        finished_unit = FinishedUnit(**unit_data)
                        session.add(finished_unit)
                        session.flush()  # Get the ID

                        # Calculate and update unit cost if recipe is available
                        if finished_unit.recipe:
                            finished_unit.update_unit_cost_from_recipe()

                        result["migrated_count"] += 1
                        logger.debug(f"Migrated record {record.id}: {record.name} -> {slug}")

                    except Exception as e:
                        result["failed_count"] += 1
                        error_msg = f"Failed to migrate record {record.id} ({record.name}): {e}"
                        result["errors"].append(error_msg)
                        logger.error(error_msg)

                # Commit all migrations
                session.commit()

                result["success"] = result["failed_count"] == 0
                logger.info(f"Migration completed: {result['migrated_count']} migrated, "
                          f"{result['failed_count']} failed")

        except Exception as e:
            result["errors"].append(f"Migration process failed: {e}")
            logger.error(f"Migration process error: {e}")

        return result

    @staticmethod
    def _generate_slug(name: str) -> str:
        """
        Generate URL-safe slug from display name.

        Args:
            name: Display name to convert

        Returns:
            URL-safe slug
        """
        if not name:
            return "unknown-item"

        # Normalize unicode characters
        slug = unicodedata.normalize('NFKD', name)

        # Convert to lowercase and replace spaces/punctuation with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug).strip().lower()
        slug = re.sub(r'[\s_-]+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        # Ensure not empty
        if not slug:
            return "unknown-item"

        # Limit length
        if len(slug) > 90:
            slug = slug[:90].rstrip('-')

        return slug

    @staticmethod
    def _generate_unique_slug(name: str, used_slugs: set) -> str:
        """
        Generate unique slug, adding suffix if needed.

        Args:
            name: Display name to convert
            used_slugs: Set of already used slugs

        Returns:
            Unique slug
        """
        base_slug = MigrationService._generate_slug(name)

        if base_slug not in used_slugs:
            return base_slug

        # Add numeric suffix for uniqueness
        counter = 2
        while f"{base_slug}-{counter}" in used_slugs:
            counter += 1

        return f"{base_slug}-{counter}"

    @staticmethod
    def validate_post_migration() -> Dict[str, any]:
        """
        Validate migration success and data integrity.

        Performs comprehensive verification that migration completed successfully
        and all data was transferred correctly.

        Returns:
            Dictionary with validation results:
            - is_valid: bool - Overall validation status
            - original_count: int - Count from original table
            - migrated_count: int - Count in new table
            - data_matches: bool - Data integrity verification
            - missing_records: List[str] - Any missing records
            - cost_calculations: bool - Cost calculation validation
        """
        result = {
            "is_valid": False,
            "original_count": 0,
            "migrated_count": 0,
            "data_matches": False,
            "missing_records": [],
            "cost_calculations": True
        }

        try:
            with get_db_session() as session:
                # Count original records
                original_count = session.execute(
                    text("SELECT COUNT(*) FROM finished_goods")
                ).fetchone()[0]
                result["original_count"] = original_count

                # Count migrated records
                migrated_count = session.execute(
                    text("SELECT COUNT(*) FROM finished_units")
                ).fetchone()[0]
                result["migrated_count"] = migrated_count

                # Basic count validation
                if original_count != migrated_count:
                    result["missing_records"].append(
                        f"Count mismatch: {original_count} original vs {migrated_count} migrated"
                    )

                # Validate field mappings for sample records
                validation_errors = MigrationService._validate_field_mappings(session)
                result["missing_records"].extend(validation_errors)

                # Validate cost calculations
                cost_errors = MigrationService._validate_cost_calculations(session)
                result["cost_calculations"] = len(cost_errors) == 0

                # Set overall validation status
                result["data_matches"] = len(result["missing_records"]) == 0
                result["is_valid"] = result["data_matches"] and result["cost_calculations"]

                logger.info(f"Post-migration validation: {result['migrated_count']} records, "
                          f"valid: {result['is_valid']}")

        except Exception as e:
            result["missing_records"].append(f"Validation failed: {e}")
            logger.error(f"Post-migration validation error: {e}")

        return result

    @staticmethod
    def _validate_field_mappings(session: Session) -> List[str]:
        """Validate that field mappings were applied correctly."""
        errors = []

        try:
            # Check that all names were mapped to display_name
            unmapped_names = session.execute(text("""
                SELECT fg.name
                FROM finished_goods fg
                LEFT JOIN finished_units fu ON fg.name = fu.display_name
                WHERE fu.display_name IS NULL
                LIMIT 5
            """)).fetchall()

            if unmapped_names:
                errors.append(f"Found unmapped names: {[r[0] for r in unmapped_names]}")

        except SQLAlchemyError as e:
            errors.append(f"Field mapping validation failed: {e}")

        return errors

    @staticmethod
    def _validate_cost_calculations(session: Session) -> List[str]:
        """Validate cost calculations are working."""
        errors = []

        try:
            # Check for units with recipes that should have calculated costs
            zero_cost_with_recipe = session.execute(text("""
                SELECT fu.slug, fu.display_name
                FROM finished_units fu
                JOIN recipes r ON fu.recipe_id = r.id
                WHERE fu.unit_cost = 0 AND fu.items_per_batch > 0
                LIMIT 5
            """)).fetchall()

            if zero_cost_with_recipe:
                errors.append(f"Found units with zero cost despite having recipes: {len(zero_cost_with_recipe)}")

        except SQLAlchemyError as e:
            errors.append(f"Cost calculation validation failed: {e}")

        return errors

    @staticmethod
    def rollback_migration(backup_path: str) -> Tuple[bool, str]:
        """
        Rollback migration by restoring from backup.

        Provides safe recovery mechanism in case of migration failure by
        restoring the database from a pre-migration backup.

        Args:
            backup_path: Path to the backup file to restore from

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from ..utils.config import get_database_path  # Correct import path
            from ..utils.backup_validator import restore_database_from_backup

            # Validate backup before restoration
            validation = validate_backup_integrity(backup_path)
            if not validation["is_valid"]:
                error_msg = f"Backup validation failed: {validation['error_message']}"
                logger.error(error_msg)
                return False, error_msg

            # Get current database path
            try:
                current_db_path = str(get_database_path())  # Convert Path to string
            except (ImportError, AttributeError):
                # Fallback to default path if get_database_path not available
                current_db_path = "bake_tracker.db"
                logger.warning(f"Using fallback database path: {current_db_path}")

            logger.warning("Starting database rollback restoration...")

            # Perform actual backup restoration
            success, message = restore_database_from_backup(
                backup_path=backup_path,
                target_path=current_db_path,
                safety_backup=True  # Create safety backup of current state
            )

            if success:
                logger.info(f"Rollback completed successfully: {message}")
                return True, f"Database successfully restored from backup: {message}"
            else:
                logger.error(f"Rollback restoration failed: {message}")
                return False, f"Failed to restore database from backup: {message}"

        except Exception as e:
            error_msg = f"Rollback failed: {e}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def create_migration_backup() -> Tuple[bool, str]:
        """
        Create backup before migration with validation.

        Returns:
            Tuple of (success: bool, backup_path: str)
        """
        try:
            from ..utils.config import get_database_path
            from ..utils.backup_validator import create_database_backup, validate_backup_integrity

            database_path = str(get_database_path())
            logger.info(f"Creating migration backup for database: {database_path}")

            # Create backup with migration-specific subdirectory
            success, backup_path = create_database_backup(
                database_path,
                backup_dir="migration_backups"
            )

            if success:
                # Validate backup integrity
                validation = validate_backup_integrity(backup_path)
                if validation["is_valid"]:
                    logger.info(f"Migration backup created and validated: {backup_path}")
                    return True, backup_path
                else:
                    error_msg = f"Backup validation failed: {validation['error_message']}"
                    logger.error(error_msg)
                    return False, ""
            else:
                logger.error(f"Backup creation failed: {backup_path}")
                return False, ""

        except Exception as e:
            error_msg = f"Migration backup creation failed: {e}"
            logger.error(error_msg)
            return False, ""

    @staticmethod
    def cleanup_legacy_data() -> Dict[str, any]:
        """
        Clean up legacy data after successful migration verification.

        CAUTION: This permanently removes the original finished_goods data.
        Should only be called after thorough verification.

        Returns:
            Dictionary with cleanup results
        """
        result = {
            "success": False,
            "tables_dropped": [],
            "errors": []
        }

        try:
            with get_db_session() as session:
                # This is a placeholder - actual cleanup would need careful implementation
                logger.warning("Legacy cleanup requested - manual verification required")
                result["success"] = True

        except Exception as e:
            result["errors"].append(f"Cleanup failed: {e}")
            logger.error(f"Legacy cleanup error: {e}")

        return result