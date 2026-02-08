"""
Import Log Service - Write structured import log files for audit and troubleshooting.

Provides service-layer logging for import operations, accessible from both UI and CLI.
Log files are written to the configured logs directory with structured format including
source, operation, validation, results, errors, warnings, and metadata sections.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.services import preferences_service
from src.utils.constants import APP_NAME, APP_VERSION

logger = logging.getLogger(__name__)

# Import log format version
IMPORT_LOG_VERSION = "2.0"

# Maximum errors/warnings to show in log before truncating
MAX_LOG_ENTRIES = 50


def get_logs_directory() -> Path:
    """
    Get the logs directory from preferences, creating it if needed.
    
    Returns:
        Path to logs directory (creates if doesn't exist)
        
    Falls back to temp directory if configured path is not writable.
    """
    logs_dir = preferences_service.get_logs_directory()
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except (IOError, OSError) as e:
        logger.warning(f"Could not create logs directory {logs_dir}: {e}")
        # Fall back to temp directory
        import tempfile
        logs_dir = Path(tempfile.gettempdir()) / "bake_tracker_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes:,} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:,.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):,.2f} MB"


def write_import_log(
    file_path: str,
    result,
    summary_text: str,
    *,
    purpose: Optional[str] = None,
    mode: Optional[str] = None,
    detected_format: Optional[Any] = None,
    validation_result: Optional[Any] = None,
    preprocessing_result: Optional[Dict] = None,
    start_time: Optional[float] = None,
) -> str:
    """
    Write comprehensive import results to a log file.
    
    Creates a structured log file with multiple sections for troubleshooting
    and audit purposes.
    
    Args:
        file_path: Source file that was imported
        result: ImportResult, CatalogImportResult, or similar result object
        summary_text: Formatted summary text (legacy, for compatibility)
        purpose: Import purpose (backup, catalog, purchases, adjustments, context_rich)
        mode: Import mode if applicable (add, augment, replace, merge)
        detected_format: FormatDetectionResult with format details
        validation_result: Schema ValidationResult (optional)
        preprocessing_result: Context-Rich preprocessing info (optional)
        start_time: Start time from time.time() for duration calculation
        
    Returns:
        Path to the created log file (relative if possible, absolute otherwise).
    """
    logs_dir = get_logs_directory()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_file = logs_dir / f"import_{timestamp}.log"
    
    # Calculate duration if start_time provided
    duration = None
    if start_time is not None:
        duration = time.time() - start_time
    
    # Get file size
    file_size = 0
    try:
        file_size = Path(file_path).stat().st_size
    except (IOError, OSError):
        pass
    
    # Build log content
    lines = []
    
    # Header
    lines.append("=" * 80)
    lines.append("IMPORT LOG")
    lines.append("=" * 80)
    lines.append("")
    
    # --- SOURCE section ---
    lines.append("--- SOURCE ---")
    lines.append(f"File: {file_path}")
    lines.append(f"Size: {format_file_size(file_size)}")
    if detected_format:
        format_desc = getattr(detected_format, "format_type", "unknown")
        version = getattr(detected_format, "version", None)
        if version:
            format_desc += f" (v{version})"
        lines.append(f"Format: {format_desc}")
    lines.append("")
    
    # --- OPERATION section ---
    lines.append("--- OPERATION ---")
    purpose_display = purpose or getattr(result, "purpose", None) or "unknown"
    lines.append(f"Purpose: {purpose_display.replace('_', ' ').title()}")
    mode_display = mode or getattr(result, "mode", None)
    if mode_display:
        mode_labels = {
            "add": "Add New Only",
            "merge": "Add New Only",
            "augment": "Update Existing",
            "replace": "Replace All",
        }
        lines.append(f"Mode: {mode_labels.get(mode_display, mode_display)}")
    lines.append(f"Timestamp: {datetime.now().isoformat()}")
    lines.append("")
    
    # --- PREPROCESSING section (only for Context-Rich) ---
    if purpose == "context_rich" and preprocessing_result:
        lines.append("--- PREPROCESSING ---")
        entity_type = preprocessing_result.get("entity_type", "unknown")
        lines.append(f"Entity Type: {entity_type}")
        records = preprocessing_result.get("records_extracted", 0)
        lines.append(f"Records Extracted: {records}")
        fk_passed = preprocessing_result.get("fk_validations_passed", 0)
        fk_failed = preprocessing_result.get("fk_validations_failed", 0)
        lines.append(f"FK Validations: {fk_passed} passed, {fk_failed} failed")
        context_fields = preprocessing_result.get("context_fields_ignored", [])
        if context_fields:
            lines.append(f"Context Fields Ignored: {', '.join(context_fields)}")
        lines.append("")
    
    # --- SCHEMA VALIDATION section ---
    if validation_result is not None:
        lines.append("--- SCHEMA VALIDATION ---")
        status = "PASSED" if getattr(validation_result, "valid", True) else "FAILED"
        lines.append(f"Status: {status}")
        error_count = getattr(validation_result, "error_count", 0)
        warning_count = getattr(validation_result, "warning_count", 0)
        lines.append(f"Errors: {error_count}")
        lines.append(f"Warnings: {warning_count}")
        
        # Show first few validation warnings
        warnings = getattr(validation_result, "warnings", [])
        if warnings:
            for warn in warnings[:10]:
                field = getattr(warn, "field", "")
                message = getattr(warn, "message", str(warn))
                lines.append(f"  - {field}: {message}")
            if len(warnings) > 10:
                lines.append(f"  ... and {len(warnings) - 10} more warnings")
        lines.append("")
    
    # --- IMPORT RESULTS section ---
    lines.append("--- IMPORT RESULTS ---")
    entity_counts = getattr(result, "entity_counts", None)
    if entity_counts:
        for entity, counts in entity_counts.items():
            if isinstance(counts, dict):
                imported = counts.get("imported", counts.get("added", 0))
                skipped = counts.get("skipped", 0)
                updated = counts.get("updated", counts.get("augmented", 0))
                parts = [f"{imported} imported"]
                if skipped:
                    parts.append(f"{skipped} skipped")
                if updated:
                    parts.append(f"{updated} updated")
                lines.append(f"{entity}: {', '.join(parts)}")
            else:
                lines.append(f"{entity}: {counts}")
    else:
        # Fallback to basic counts
        total = getattr(result, "total_records", None)
        successful = getattr(result, "successful", None)
        if total is not None:
            lines.append(f"Total processed: {total}")
        if successful is not None:
            lines.append(f"Successful: {successful}")
    lines.append("")
    
    # --- ERRORS section ---
    lines.append("--- ERRORS ---")
    errors = getattr(result, "errors", [])
    if errors:
        for i, err in enumerate(errors[:MAX_LOG_ENTRIES]):
            if isinstance(err, dict):
                entity = err.get("record_type", err.get("entity_type", ""))
                name = err.get("record_name", err.get("identifier", ""))
                message = err.get("message", str(err))
                suggestion = err.get("suggestion", "")
                expected = err.get("expected", "")
                actual = err.get("actual", "")
                
                error_line = f"- [{entity}] {name}: {message}"
                lines.append(error_line)
                if expected and actual:
                    lines.append(f"    Expected: {expected}")
                    lines.append(f"    Actual: {actual}")
                if suggestion:
                    lines.append(f"    Suggestion: {suggestion}")
            else:
                # Handle ValidationError dataclass or string
                field = getattr(err, "field", "")
                message = getattr(err, "message", str(err))
                suggestion = getattr(err, "suggestion", "")
                expected = getattr(err, "expected", "")
                actual = getattr(err, "actual", "")
                
                if field:
                    lines.append(f"- {field}: {message}")
                else:
                    lines.append(f"- {message}")
                if expected and actual:
                    lines.append(f"    Expected: {expected}")
                    lines.append(f"    Actual: {actual}")
                if suggestion:
                    lines.append(f"    Suggestion: {suggestion}")
        
        if len(errors) > MAX_LOG_ENTRIES:
            lines.append(f"  ... and {len(errors) - MAX_LOG_ENTRIES} more errors")
    else:
        lines.append("(none)")
    lines.append("")
    
    # --- WARNINGS section ---
    lines.append("--- WARNINGS ---")
    warnings = getattr(result, "warnings", [])
    if warnings:
        for i, warn in enumerate(warnings[:MAX_LOG_ENTRIES]):
            if isinstance(warn, dict):
                entity = warn.get("record_type", warn.get("entity_type", ""))
                name = warn.get("record_name", warn.get("identifier", ""))
                message = warn.get("message", str(warn))
                lines.append(f"- [{entity}] {name}: {message}")
            else:
                field = getattr(warn, "field", "")
                message = getattr(warn, "message", str(warn))
                if field:
                    lines.append(f"- {field}: {message}")
                else:
                    lines.append(f"- {message}")
        
        if len(warnings) > MAX_LOG_ENTRIES:
            lines.append(f"  ... and {len(warnings) - MAX_LOG_ENTRIES} more warnings")
    else:
        lines.append("(none)")
    lines.append("")
    
    # --- SUMMARY section ---
    lines.append("--- SUMMARY ---")
    # Use entity_counts for detailed summary if available
    if entity_counts:
        total_imported = sum(
            counts.get("imported", counts.get("added", 0))
            for counts in entity_counts.values()
            if isinstance(counts, dict)
        )
        total_skipped = sum(
            counts.get("skipped", 0)
            for counts in entity_counts.values()
            if isinstance(counts, dict)
        )
        total_updated = sum(
            counts.get("updated", counts.get("augmented", 0))
            for counts in entity_counts.values()
            if isinstance(counts, dict)
        )
        lines.append(f"Total Imported: {total_imported}")
        lines.append(f"Total Skipped: {total_skipped}")
        if total_updated:
            lines.append(f"Total Updated: {total_updated}")
        lines.append(f"Total Errors: {len(errors)}")
        lines.append(f"Total Warnings: {len(warnings)}")
    else:
        # Fallback to basic counts
        total_records = getattr(result, "total_records", 0)
        successful = getattr(result, "successful", 0)
        skipped = getattr(result, "skipped", 0)
        failed = getattr(result, "failed", len(errors))
        lines.append(f"Total Records: {total_records}")
        lines.append(f"Successful: {successful}")
        lines.append(f"Skipped: {skipped}")
        lines.append(f"Failed: {failed}")
    lines.append("")
    
    # --- METADATA section ---
    lines.append("--- METADATA ---")
    lines.append(f"Application: {APP_NAME} v{APP_VERSION}")
    lines.append(f"Log Version: {IMPORT_LOG_VERSION}")
    if duration is not None:
        lines.append(f"Duration: {duration:.2f}s")
    lines.append("=" * 80)
    lines.append("")
    
    # Write to file
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except (IOError, OSError) as e:
        logger.error(f"Failed to write import log to {log_file}: {e}")
        # Try temp directory as fallback
        import tempfile
        fallback_file = Path(tempfile.gettempdir()) / f"import_{timestamp}.log"
        try:
            with open(fallback_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            log_file = fallback_file
        except (IOError, OSError):
            return "(log file could not be written)"
    
    # Return path for display (relative if possible)
    try:
        return str(log_file.relative_to(Path.cwd()))
    except ValueError:
        return str(log_file)
