"""
Database backup and validation utilities for FinishedUnit Model Refactoring.

This module provides safe backup and restore functionality for SQLite database
migration operations, ensuring zero data loss during model transformation.
"""

import shutil
import hashlib
import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def create_database_backup(db_path: str, backup_dir: str = "backups") -> Tuple[bool, str]:
    """
    Create a timestamped backup of the SQLite database.

    Args:
        db_path: Path to the source database file
        backup_dir: Directory to store backup files (default: "backups")

    Returns:
        Tuple of (success: bool, backup_path: str)
    """
    try:
        # Ensure backup directory exists
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)

        # Generate timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_name = Path(db_path).stem
        backup_filename = f"{db_name}_backup_{timestamp}.sqlite"
        full_backup_path = backup_path / backup_filename

        # Handle SQLite WAL mode properly by checkpoint
        if os.path.exists(db_path):
            # Checkpoint WAL file to main database before backup
            try:
                with sqlite3.connect(db_path) as conn:
                    conn.execute("PRAGMA wal_checkpoint(FULL)")
                    conn.commit()
                logger.info(f"WAL checkpoint completed for {db_path}")
            except sqlite3.Error as e:
                logger.warning(f"Could not checkpoint WAL: {e}")

        # Copy database file
        shutil.copy2(db_path, full_backup_path)

        # Verify backup was created successfully
        if full_backup_path.exists() and full_backup_path.stat().st_size > 0:
            logger.info(f"Database backup created successfully: {full_backup_path}")
            return True, str(full_backup_path)
        else:
            logger.error("Backup file was not created or is empty")
            return False, ""

    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return False, ""


def validate_backup_integrity(backup_path: str) -> Dict[str, any]:
    """
    Validate the integrity of a database backup file.

    Args:
        backup_path: Path to the backup file to validate

    Returns:
        Dictionary with validation results including:
        - is_valid: bool
        - file_exists: bool
        - file_size: int
        - checksum: str
        - sqlite_valid: bool
        - table_count: int
        - error_message: Optional[str]
    """
    result = {
        "is_valid": False,
        "file_exists": False,
        "file_size": 0,
        "checksum": "",
        "sqlite_valid": False,
        "table_count": 0,
        "error_message": None,
    }

    try:
        backup_file = Path(backup_path)

        # Check if file exists
        if not backup_file.exists():
            result["error_message"] = f"Backup file does not exist: {backup_path}"
            return result

        result["file_exists"] = True
        result["file_size"] = backup_file.stat().st_size

        # Calculate file checksum
        with open(backup_path, "rb") as f:
            file_hash = hashlib.sha256()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        result["checksum"] = file_hash.hexdigest()

        # Validate SQLite database structure
        try:
            with sqlite3.connect(backup_path) as conn:
                # Check database integrity
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()

                if integrity_result and integrity_result[0] == "ok":
                    result["sqlite_valid"] = True

                    # Count tables
                    cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    result["table_count"] = cursor.fetchone()[0]

                    result["is_valid"] = True
                    logger.info(f"Backup validation successful: {backup_path}")
                else:
                    result["error_message"] = f"SQLite integrity check failed: {integrity_result}"

        except sqlite3.Error as e:
            result["error_message"] = f"SQLite validation error: {e}"

    except Exception as e:
        result["error_message"] = f"Validation error: {e}"
        logger.error(f"Backup validation failed: {e}")

    return result


def restore_database_from_backup(
    backup_path: str, target_path: str, safety_backup: bool = True
) -> Tuple[bool, str]:
    """
    Restore database from backup file with safety checks.

    Args:
        backup_path: Path to the backup file to restore from
        target_path: Path where to restore the database
        safety_backup: Whether to create a backup of existing target before restore

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Validate backup before restoration
        validation = validate_backup_integrity(backup_path)
        if not validation["is_valid"]:
            error_msg = f"Backup validation failed: {validation['error_message']}"
            logger.error(error_msg)
            return False, error_msg

        # Create safety backup of existing target if requested
        safety_backup_path = ""
        if safety_backup and os.path.exists(target_path):
            success, safety_backup_path = create_database_backup(target_path, "safety_backups")
            if not success:
                return False, "Failed to create safety backup before restore"

        # Perform restoration
        shutil.copy2(backup_path, target_path)

        # Verify restoration
        if os.path.exists(target_path):
            restore_validation = validate_backup_integrity(target_path)
            if restore_validation["is_valid"]:
                success_msg = f"Database restored successfully from {backup_path}"
                if safety_backup_path:
                    success_msg += f" (safety backup: {safety_backup_path})"
                logger.info(success_msg)
                return True, success_msg
            else:
                error_msg = (
                    f"Restored database validation failed: {restore_validation['error_message']}"
                )
                logger.error(error_msg)
                return False, error_msg
        else:
            return False, "Restored database file does not exist"

    except Exception as e:
        error_msg = f"Database restoration failed: {e}"
        logger.error(error_msg)
        return False, error_msg


def list_available_backups(backup_dir: str = "backups") -> list:
    """
    List all available backup files in the backup directory.

    Args:
        backup_dir: Directory to scan for backup files

    Returns:
        List of dictionaries with backup file information
    """
    backups = []
    backup_path = Path(backup_dir)

    if not backup_path.exists():
        return backups

    try:
        for backup_file in backup_path.glob("*_backup_*.sqlite"):
            validation = validate_backup_integrity(str(backup_file))

            backups.append(
                {
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size": validation["file_size"],
                    "created": datetime.fromtimestamp(backup_file.stat().st_mtime),
                    "valid": validation["is_valid"],
                    "checksum": validation["checksum"][:16] + "...",  # Truncated for display
                    "table_count": validation["table_count"],
                }
            )

        # Sort by creation time, newest first
        backups.sort(key=lambda x: x["created"], reverse=True)

    except Exception as e:
        logger.error(f"Failed to list backups: {e}")

    return backups


def cleanup_old_backups(backup_dir: str = "backups", keep_count: int = 10) -> int:
    """
    Clean up old backup files, keeping only the most recent ones.

    Args:
        backup_dir: Directory containing backup files
        keep_count: Number of recent backups to keep

    Returns:
        Number of backup files deleted
    """
    deleted_count = 0

    try:
        backups = list_available_backups(backup_dir)

        if len(backups) > keep_count:
            backups_to_delete = backups[keep_count:]

            for backup in backups_to_delete:
                try:
                    os.remove(backup["path"])
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {backup['filename']}")
                except Exception as e:
                    logger.error(f"Failed to delete backup {backup['filename']}: {e}")

    except Exception as e:
        logger.error(f"Backup cleanup failed: {e}")

    return deleted_count
