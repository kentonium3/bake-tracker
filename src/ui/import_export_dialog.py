"""
Import and Export dialogs for the Seasonal Baking Tracker.

Provides modal dialogs for data import/export operations with mode selection.
"""

import logging
import os
import time
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Dict, List, Optional

import customtkinter as ctk

from src.services import import_export_service
from src.services import coordinated_export_service
from src.services import denormalized_export_service
from src.services import preferences_service
from src.services import schema_validation_service
from src.utils.constants import APP_NAME, APP_VERSION


# Import log format version
IMPORT_LOG_VERSION = "2.0"

# Maximum errors/warnings to show in log before truncating
MAX_LOG_ENTRIES = 20

logger = logging.getLogger(__name__)


def _get_logs_dir() -> Path:
    """Get the logs directory from preferences, creating it if needed."""
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


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes:,} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:,.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):,.2f} MB"


def _write_import_log(
    file_path: str,
    result,
    summary_text: str,
    *,
    purpose: str = None,
    mode: str = None,
    detected_format: Any = None,
    validation_result: Any = None,
    preprocessing_result: Dict = None,
    start_time: float = None,
) -> str:
    """Write comprehensive import results to a log file.

    Creates a structured log file with multiple sections for troubleshooting
    and audit purposes.

    Args:
        file_path: Source file that was imported
        result: ImportResult, CatalogImportResult, or similar result object
        summary_text: Formatted summary text (legacy, for compatibility)
        purpose: Import purpose (backup, catalog, purchases, adjustments, context_rich)
        mode: Import mode if applicable (add, augment)
        detected_format: FormatDetectionResult with format details
        validation_result: Schema ValidationResult (optional)
        preprocessing_result: Context-Rich preprocessing info (optional)
        start_time: Start time from time.time() for duration calculation

    Returns:
        Path to the created log file (for display in UI).
    """
    logs_dir = _get_logs_dir()
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
    lines.append(f"Size: {_format_file_size(file_size)}")
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
                warning_type = warn.get("warning_type", "")

                if warning_type:
                    lines.append(f"- [{entity}] {name}: {message} ({warning_type})")
                else:
                    lines.append(f"- [{entity}] {name}: {message}")
            else:
                # Handle ValidationWarning dataclass or string
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
    lines.append("=" * 80)
    lines.append("SUMMARY")
    lines.append("=" * 80)
    # Handle CatalogImportResult (has total_processed, total_added, etc.)
    # vs other result types (have total_records, successful, etc.)
    if hasattr(result, "total_processed"):
        # CatalogImportResult
        total_records = result.total_processed
        successful = getattr(result, "total_added", 0)
        augmented = getattr(result, "total_augmented", 0)
        skipped = getattr(result, "total_skipped", 0)
        failed = getattr(result, "total_failed", 0)
        lines.append(f"Total Records: {total_records}")
        lines.append(f"Added: {successful}")
        if augmented:
            lines.append(f"Augmented: {augmented}")
        lines.append(f"Skipped: {skipped}")
        lines.append(f"Failed: {failed}")
    else:
        # Other result types (ImportResult, etc.)
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
        except Exception:
            return "(log file could not be written)"

    # Return path for display
    try:
        return str(log_file.relative_to(Path.cwd()))
    except ValueError:
        return str(log_file)


class ImportResultsDialog(ctk.CTkToplevel):
    """Dialog for displaying import results with scrolling, copy, and logging."""

    def __init__(self, parent, title: str, summary_text: str, log_path: str = None):
        """Initialize the import results dialog.

        Args:
            parent: Parent window
            title: Dialog title
            summary_text: Full text of import results
            log_path: Path to log file (optional)
        """
        super().__init__(parent)

        self.title(title)
        self.summary_text = summary_text
        self.log_path = log_path

        # Set size and make resizable
        self.geometry("600x500")
        self.minsize(400, 300)

        self._setup_ui()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Focus the dialog
        self.focus_force()

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Configure grid weights for resizing
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Import Results",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.grid(row=0, column=0, pady=(15, 10), padx=20, sticky="w")

        # Scrollable text area
        text_frame = ctk.CTkFrame(self)
        text_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)

        self.text_widget = ctk.CTkTextbox(
            text_frame,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12),
        )
        self.text_widget.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Insert the summary text
        self.text_widget.insert("1.0", self.summary_text)
        self.text_widget.configure(state="disabled")  # Make read-only

        # Log file path label
        if self.log_path:
            log_frame = ctk.CTkFrame(self, fg_color="transparent")
            log_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

            log_label = ctk.CTkLabel(
                log_frame,
                text=f"Log saved to: {self.log_path}",
                font=ctk.CTkFont(size=11),
                text_color="gray",
                wraplength=550,
            )
            log_label.pack(anchor="w")

        # Button frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")

        # Copy to Clipboard button
        copy_btn = ctk.CTkButton(
            btn_frame,
            text="Copy to Clipboard",
            width=140,
            command=self._copy_to_clipboard,
        )
        copy_btn.pack(side="left")

        # Close button
        close_btn = ctk.CTkButton(
            btn_frame,
            text="Close",
            width=100,
            command=self.destroy,
        )
        close_btn.pack(side="right")

        # Bind Escape key to close
        self.bind("<Escape>", lambda e: self.destroy())

    def _copy_to_clipboard(self):
        """Copy the summary text to clipboard."""
        self.clipboard_clear()
        self.clipboard_append(self.summary_text)

        # Brief visual feedback (could show a tooltip, but keeping it simple)
        self.update()


class ImportDialog(ctk.CTkToplevel):
    """Dialog for importing data with 4 purpose options and auto-detection.

    Redesigned for Feature 049 to clearly distinguish:
    - Backup Restore: Full restore, replace mode
    - Catalog Import: Add/augment entities
    - Purchases Import: Transaction import from BT Mobile
    - Adjustments Import: Inventory adjustments (spoilage, waste)
    """

    def __init__(self, parent):
        """Initialize the import dialog."""
        super().__init__(parent)
        self.title("Import Data")
        self.geometry("550x650")
        self.minsize(550, 600)

        self.result = None
        self.file_path = None
        self.detected_format = None

        self._setup_ui()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Button frame - pack at bottom FIRST so it's always visible
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=15)

        self.import_btn = ctk.CTkButton(
            btn_frame,
            text="Import",
            width=120,
            command=self._do_import,
        )
        self.import_btn.pack(side="right", padx=(10, 0))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self.destroy,
        )
        cancel_btn.pack(side="right")

        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Import Data",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.pack(pady=(15, 5))

        # File selection frame (at top for workflow)
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            file_frame,
            text="1. Select file to import:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        file_inner = ctk.CTkFrame(file_frame, fg_color="transparent")
        file_inner.pack(fill="x", padx=10, pady=(0, 5))

        self.file_entry = ctk.CTkEntry(file_inner, width=350, state="readonly")
        self.file_entry.pack(side="left", padx=(0, 10))

        browse_btn = ctk.CTkButton(
            file_inner,
            text="Browse...",
            width=80,
            command=self._browse_file,
        )
        browse_btn.pack(side="left")

        # Detection result label
        self.detection_label = ctk.CTkLabel(
            file_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.detection_label.pack(anchor="w", padx=10, pady=(0, 10))

        # Purpose selection frame
        purpose_frame = ctk.CTkFrame(self)
        purpose_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            purpose_frame,
            text="2. What are you importing?",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.purpose_var = ctk.StringVar(value="catalog")
        purposes = [
            ("backup", "Backup Restore", "Restore complete system from backup (replaces all data)"),
            ("catalog", "Catalog Data", "Add or update ingredients, products, recipes, materials"),
            ("purchases", "Purchases", "Import purchase transactions (from BT Mobile or spreadsheet)"),
            ("adjustments", "Adjustments", "Import inventory adjustments (spoilage, waste, corrections)"),
            ("context_rich", "Context-Rich", "Import AI-augmented files (aug_*.json) with preprocessing"),
        ]

        for value, label, desc in purposes:
            frame = ctk.CTkFrame(purpose_frame, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=3)

            rb = ctk.CTkRadioButton(
                frame,
                text=label,
                variable=self.purpose_var,
                value=value,
                command=self._on_purpose_changed,
            )
            rb.pack(side="left")

            desc_label = ctk.CTkLabel(
                frame,
                text=f"- {desc}",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            )
            desc_label.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(purpose_frame, text="").pack(pady=3)

        # Options frame (changes based on purpose)
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(fill="x", padx=20, pady=10)

        self._setup_catalog_options()  # Default

        # Progress bar
        self.progress = ctk.CTkProgressBar(self)
        self.progress.set(0)

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.status_label.pack(pady=5)

    def _setup_catalog_options(self):
        """Set up options for catalog import."""
        # Clear existing options
        for widget in self.options_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.options_frame,
            text="3. Import mode:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.mode_var = ctk.StringVar(value="add")

        modes = [
            ("add", "Add Only", "Create new records, skip existing"),
            ("augment", "Augment", "Create new + fill empty fields on existing"),
        ]

        for value, label, desc in modes:
            frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=2)

            rb = ctk.CTkRadioButton(frame, text=label, variable=self.mode_var, value=value)
            rb.pack(side="left")

            desc_label = ctk.CTkLabel(
                frame,
                text=f"- {desc}",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            )
            desc_label.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(self.options_frame, text="").pack(pady=3)

    def _setup_backup_options(self):
        """Set up options for backup restore."""
        for widget in self.options_frame.winfo_children():
            widget.destroy()

        warning = ctk.CTkLabel(
            self.options_frame,
            text="WARNING: This will replace ALL existing data!",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="red",
        )
        warning.pack(pady=15)

        info = ctk.CTkLabel(
            self.options_frame,
            text="All current data will be deleted and replaced\n"
                 "with the contents of the backup file.",
            font=ctk.CTkFont(size=12),
        )
        info.pack(pady=5)

    def _setup_transaction_options(self, transaction_type: str):
        """Set up options for purchase/adjustment import."""
        for widget in self.options_frame.winfo_children():
            widget.destroy()

        if transaction_type == "purchases":
            info_text = (
                "Import purchase records with product, price, and quantity.\n"
                "Inventory will be increased for each purchase."
            )
        else:
            info_text = (
                "Import inventory adjustments (negative quantities only).\n"
                "Requires reason code: SPOILAGE, WASTE, DAMAGED, CORRECTION, OTHER."
            )

        info = ctk.CTkLabel(
            self.options_frame,
            text=info_text,
            font=ctk.CTkFont(size=12),
            justify="left",
        )
        info.pack(anchor="w", padx=10, pady=15)

    def _setup_context_rich_options(self):
        """Set up options for context-rich import."""
        # Clear existing options
        for widget in self.options_frame.winfo_children():
            widget.destroy()

        # Context-rich imports are merge-only (update existing records)
        # No mode selection needed

        ctk.CTkLabel(
            self.options_frame,
            text="3. Import behavior:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        info_label = ctk.CTkLabel(
            self.options_frame,
            text="Context-rich imports update existing records with\n"
                 "AI-augmented editable fields. Records not found\n"
                 "in the database will be skipped (not created).",
            font=ctk.CTkFont(size=12),
            justify="left",
        )
        info_label.pack(anchor="w", padx=20, pady=(5, 10))

        # Additional info about aug_*.json files
        format_label = ctk.CTkLabel(
            self.options_frame,
            text="Context-rich files (aug_*.json) include metadata\n"
                 "indicating which fields are editable vs. computed.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        format_label.pack(anchor="w", padx=10, pady=(5, 10))

    def _on_purpose_changed(self):
        """Handle purpose selection change."""
        purpose = self.purpose_var.get()

        if purpose == "backup":
            self._setup_backup_options()
        elif purpose == "catalog":
            self._setup_catalog_options()
        elif purpose == "context_rich":
            self._setup_context_rich_options()
        elif purpose == "purchases":
            self._setup_transaction_options("purchases")
        elif purpose == "adjustments":
            self._setup_transaction_options("adjustments")

    def _browse_file(self):
        """Open file browser and auto-detect format."""
        # FR-015: Use configured import directory as initial location
        initial_dir = str(preferences_service.get_import_directory())
        file_path = filedialog.askopenfilename(
            title="Select Import File",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self,
        )
        if file_path:
            self.file_path = file_path
            self.file_entry.configure(state="normal")
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, file_path)
            self.file_entry.configure(state="readonly")

            # Auto-detect format
            self._detect_format()

    def _detect_format(self):
        """Detect file format and update UI."""
        try:
            from src.services.enhanced_import_service import detect_format

            result = detect_format(self.file_path)
            self.detected_format = result

            # Check for aug_*.json filename pattern (overrides format detection)
            filename = Path(self.file_path).name
            is_aug_file = filename.startswith("aug_") and filename.endswith(".json")

            # Display detection result
            format_name = result.format_type.replace("_", " ").title()
            record_count = result.entity_count or "unknown"
            self.detection_label.configure(
                text=f"Detected: {format_name} format ({record_count} records)",
                text_color="green",
            )

            # Auto-select matching purpose
            if result.format_type == "purchases":
                self.purpose_var.set("purchases")
                self._on_purpose_changed()
            elif result.format_type in ("adjustments", "inventory_updates"):
                self.purpose_var.set("adjustments")
                self._on_purpose_changed()
            elif result.format_type == "context_rich" or is_aug_file:
                # Auto-select context_rich for context-rich files or aug_*.json
                self.purpose_var.set("context_rich")
                self._on_purpose_changed()
                if is_aug_file:
                    self.detection_label.configure(
                        text=f"Detected: Context-Rich format (aug_*.json, {record_count} records)",
                        text_color="green",
                    )
            elif result.format_type == "normalized":
                # Could be backup or catalog - show per-entity breakdown
                entity_parts = []
                if result.raw_data:
                    # Build per-entity counts
                    entity_order = ["suppliers", "ingredients", "products", "recipes",
                                    "materials", "material_products", "finished_goods",
                                    "packages", "recipients", "events"]
                    for entity in entity_order:
                        if entity in result.raw_data and isinstance(result.raw_data[entity], list):
                            count = len(result.raw_data[entity])
                            if count > 0:
                                entity_name = entity.replace("_", " ").title()
                                entity_parts.append(f"{entity_name} ({count})")

                if entity_parts:
                    entity_summary = ", ".join(entity_parts[:4])  # Show first 4
                    if len(entity_parts) > 4:
                        entity_summary += f", +{len(entity_parts) - 4} more"
                    self.detection_label.configure(
                        text=f"Multiple entities: {entity_summary} - select purpose below",
                        text_color="orange",
                    )
                else:
                    self.detection_label.configure(
                        text=f"Detected: Normalized format ({record_count} records) - select purpose below",
                        text_color="orange",
                    )

        except Exception as e:
            self.detection_label.configure(
                text=f"Could not detect format: {str(e)[:50]}",
                text_color="red",
            )
            self.detected_format = None

    def _do_import(self):
        """Execute the import operation based on selected purpose."""
        if not self.file_path:
            messagebox.showwarning(
                "No File Selected",
                "Please select a file to import.",
                parent=self,
            )
            return

        purpose = self.purpose_var.get()

        if purpose == "backup":
            self._do_backup_restore()
        elif purpose == "catalog":
            self._do_catalog_import()
        elif purpose == "context_rich":
            self._do_context_rich_import()
        elif purpose == "purchases":
            self._do_purchases_import()
        elif purpose == "adjustments":
            self._do_adjustments_import()

    def _do_backup_restore(self):
        """Execute full backup restore (replace mode)."""
        if not messagebox.askyesno(
            "Confirm Backup Restore",
            "This will DELETE all existing data and replace it with\n"
            "the contents of the backup file.\n\n"
            "This action cannot be undone.\n\n"
            "Are you sure you want to continue?",
            icon="warning",
            parent=self,
        ):
            return

        self._show_progress("Restoring backup...")

        try:
            # Check if this is a coordinated backup (manifest.json)
            file_path = Path(self.file_path)
            is_coordinated = (
                file_path.name == "manifest.json" or
                (file_path.is_dir() and (file_path / "manifest.json").exists())
            )

            if is_coordinated:
                # Use coordinated import for manifest-based backups
                result = coordinated_export_service.import_complete(str(file_path))

                summary_lines = [
                    f"Restored {result['successful']} records",
                    f"from {result['files_imported']} entity files.",
                    "",
                ]
                if result['entity_counts']:
                    summary_lines.append("Records by entity:")
                    for entity, count in result['entity_counts'].items():
                        summary_lines.append(f"  {entity}: {count}")

                if result['errors']:
                    summary_lines.append("")
                    summary_lines.append("Errors:")
                    for err in result['errors'][:5]:
                        summary_lines.append(f"  - {err}")

                summary_text = "\n".join(summary_lines)
            else:
                # FR-012: Run schema validation before single-file backup restore
                import json
                with open(self.file_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

                validation_result = schema_validation_service.validate_import_file(raw_data)

                if not validation_result.valid:
                    # Write validation failure log before showing dialog
                    from dataclasses import dataclass

                    @dataclass
                    class ValidationFailureResult:
                        total_records: int = 0
                        successful: int = 0
                        failed: int = 0
                        errors: list = None
                        warnings: list = None

                        def __post_init__(self):
                            if self.errors is None:
                                self.errors = []
                            if self.warnings is None:
                                self.warnings = []

                    failure_result = ValidationFailureResult(
                        failed=len(validation_result.errors),
                        errors=validation_result.errors,
                        warnings=validation_result.warnings or [],
                    )
                    log_path = _write_import_log(
                        self.file_path,
                        failure_result,
                        f"Schema validation failed with {len(validation_result.errors)} error(s)",
                        purpose="backup",
                        validation_result=validation_result,
                    )

                    # Show validation error dialog and abort
                    self._hide_progress()
                    self._show_validation_errors(validation_result, log_path=log_path)
                    return

                # Use standard single-file import
                result = import_export_service.import_all_from_json_v4(
                    self.file_path,
                    mode="replace",
                )
                summary_text = result.get_summary()

            log_path = _write_import_log(self.file_path, result, summary_text)

            self.result = result
            results_dialog = ImportResultsDialog(
                self.master,
                title="Backup Restored",
                summary_text=summary_text,
                log_path=log_path,
            )
            results_dialog.wait_window()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Restore Failed", self._format_error(e), parent=self)
        finally:
            self._hide_progress()

    def _do_catalog_import(self):
        """Execute catalog import with selected mode."""
        self._show_progress("Importing catalog data...")

        try:
            mode = self.mode_var.get()

            # FR-012: Run schema validation before import
            import json
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            validation_result = schema_validation_service.validate_import_file(raw_data)

            if not validation_result.valid:
                # Write validation failure log before showing dialog
                from dataclasses import dataclass

                @dataclass
                class ValidationFailureResult:
                    total_records: int = 0
                    successful: int = 0
                    failed: int = 0
                    errors: list = None
                    warnings: list = None

                    def __post_init__(self):
                        if self.errors is None:
                            self.errors = []
                        if self.warnings is None:
                            self.warnings = []

                failure_result = ValidationFailureResult(
                    failed=len(validation_result.errors),
                    errors=validation_result.errors,
                    warnings=validation_result.warnings or [],
                )
                log_path = _write_import_log(
                    self.file_path,
                    failure_result,
                    f"Schema validation failed with {len(validation_result.errors)} error(s)",
                    purpose="catalog",
                    mode=mode,
                    validation_result=validation_result,
                )

                # Show validation error dialog and abort
                self._hide_progress()
                self._show_validation_errors(validation_result, log_path=log_path)
                return

            # Check if it's a context-rich file
            if self.detected_format and self.detected_format.format_type == "context_rich":
                from src.services.enhanced_import_service import import_context_rich_view

                result = import_context_rich_view(self.file_path)
                summary_text = result.get_summary()
            else:
                # Standard catalog import - use catalog_import_service which supports
                # both "add" (ADD_ONLY) and "augment" (AUGMENT) modes properly
                from src.services.catalog_import_service import import_catalog

                result = import_catalog(self.file_path, mode=mode)
                summary_text = result.get_summary()

            log_path = _write_import_log(
                self.file_path, result, summary_text,
                purpose="catalog", mode=mode,
            )

            self.result = result
            results_dialog = ImportResultsDialog(
                self.master,
                title="Import Complete",
                summary_text=summary_text,
                log_path=log_path,
            )
            results_dialog.wait_window()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Import Failed", self._format_error(e), parent=self)
        finally:
            self._hide_progress()

    def _do_context_rich_import(self):
        """Execute context-rich import with preprocessing and schema validation."""
        start_time = time.time()
        self._show_progress("Importing context-rich data...")

        try:
            mode = self.mode_var.get()

            # Load the context-rich file
            import json
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # Track preprocessing info for logging
            preprocessing_result = {}

            # FR-010: Preprocess context-rich files
            # Context-rich format has _meta, view_type, records structure
            view_type = raw_data.get("view_type")
            meta = raw_data.get("_meta", {})
            records = raw_data.get("records", [])

            preprocessing_result["view_type"] = view_type or "unknown"
            preprocessing_result["record_count"] = len(records)

            if not view_type:
                messagebox.showerror(
                    "Invalid Format",
                    "Context-rich file missing 'view_type' field.\n\n"
                    "Expected format: {\"view_type\": \"ingredients\", \"records\": [...]}",
                    parent=self,
                )
                return

            # FR-010a/FR-010b: Extract editable fields and convert to normalized format
            # for schema validation (strip read-only context fields)
            editable_fields = set(meta.get("editable_fields", []))
            normalized_records = []

            for record in records:
                # Extract only editable fields plus identifier (slug)
                normalized = {"slug": record.get("slug")}
                for field in editable_fields:
                    if field in record:
                        normalized[field] = record[field]
                # Always include display_name/name if present (for identification)
                if "display_name" in record:
                    normalized["display_name"] = record["display_name"]
                if "name" in record:
                    normalized["name"] = record["name"]
                normalized_records.append(normalized)

            # Build normalized data structure for schema validation
            normalized_data = {view_type: normalized_records}
            preprocessing_result["normalized_fields"] = list(editable_fields)

            # FR-010b: Run schema validation on preprocessed/normalized output
            validation_result = schema_validation_service.validate_import_file(normalized_data)

            if not validation_result.valid:
                # Write validation failure log before showing dialog
                from dataclasses import dataclass

                @dataclass
                class ValidationFailureResult:
                    total_records: int = 0
                    successful: int = 0
                    failed: int = 0
                    errors: list = None
                    warnings: list = None

                    def __post_init__(self):
                        if self.errors is None:
                            self.errors = []
                        if self.warnings is None:
                            self.warnings = []

                failure_result = ValidationFailureResult(
                    failed=len(validation_result.errors),
                    errors=validation_result.errors,
                    warnings=validation_result.warnings or [],
                )
                log_path = _write_import_log(
                    self.file_path,
                    failure_result,
                    f"Schema validation failed with {len(validation_result.errors)} error(s)",
                    purpose="context_rich",
                    mode=mode,
                    validation_result=validation_result,
                    preprocessing_result=preprocessing_result,
                    start_time=start_time,
                )

                # Show validation error dialog
                self._hide_progress()
                self._show_validation_errors(validation_result, log_path=log_path)
                return

            # Log any warnings but continue
            if validation_result.warnings:
                preprocessing_result["validation_warnings"] = len(validation_result.warnings)

            # FR-011: Validate FK references exist before import
            # Context-rich imports update EXISTING records - check all slugs exist
            from src.services.database import session_scope
            from src.services.enhanced_import_service import _find_entity_by_slug

            missing_refs = []
            with session_scope() as session:
                for record in records:
                    slug = record.get("slug")
                    if slug:
                        existing = _find_entity_by_slug(view_type, slug, session)
                        if not existing:
                            missing_refs.append(slug)

            if missing_refs:
                # FR-011: Block with actionable error dialog
                self._hide_progress()
                error_msg = (
                    f"Cannot import: {len(missing_refs)} record(s) reference "
                    f"{view_type} that don't exist in the database.\n\n"
                    f"Missing {view_type}:\n"
                )
                for slug in missing_refs[:10]:
                    error_msg += f"  - {slug}\n"
                if len(missing_refs) > 10:
                    error_msg += f"  ... and {len(missing_refs) - 10} more\n"
                error_msg += (
                    "\nTo fix: Import the missing records first using Catalog import, "
                    "then retry the Context-Rich import."
                )
                messagebox.showerror("Missing References", error_msg, parent=self)
                return

            preprocessing_result["fk_validated"] = True

            # Execute the import using enhanced_import_service
            # Note: Context-rich imports are merge-only (updates existing records)
            from src.services.enhanced_import_service import import_context_rich_view

            result = import_context_rich_view(self.file_path)

            # Build summary with per-entity counts
            summary_lines = self._build_import_summary(result)
            summary_text = "\n".join(summary_lines)

            # Write enhanced log
            log_path = _write_import_log(
                self.file_path,
                result,
                summary_text,
                purpose="context_rich",
                mode=mode,
                detected_format=self.detected_format,
                validation_result=validation_result,
                preprocessing_result=preprocessing_result,
                start_time=start_time,
            )

            self.result = result
            results_dialog = ImportResultsDialog(
                self.master,
                title="Context-Rich Import Complete",
                summary_text=summary_text,
                log_path=log_path,
            )
            results_dialog.wait_window()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Import Failed", self._format_error(e), parent=self)
        finally:
            self._hide_progress()

    def _show_validation_errors(self, validation_result, log_path: str = None):
        """Show dialog with validation errors and field paths."""
        errors = validation_result.errors
        error_count = len(errors)

        # Build error message
        lines = [
            f"Schema validation found {error_count} error(s).",
            "",
            "Please fix these issues in the source file before importing:",
            "",
        ]

        # Show first 10 errors with details
        for i, err in enumerate(errors[:10]):
            record_num = getattr(err, "record_number", 0)
            field = getattr(err, "field", "")
            message = getattr(err, "message", str(err))
            expected = getattr(err, "expected", "")
            actual = getattr(err, "actual", "")

            if record_num > 0:
                lines.append(f"Record {record_num}, {field}:")
            else:
                lines.append(f"{field}:")
            lines.append(f"  {message}")
            if expected and actual:
                lines.append(f"  Expected: {expected}")
                lines.append(f"  Actual: {actual}")
            lines.append("")

        if error_count > 10:
            lines.append(f"... and {error_count - 10} more error(s)")
            lines.append("")

        lines.append("Import aborted. No changes were made.")

        error_text = "\n".join(lines)

        # Show in a scrollable dialog
        error_dialog = ImportResultsDialog(
            self,
            title="Validation Failed",
            summary_text=error_text,
            log_path=log_path,
        )
        error_dialog.wait_window()

    def _build_import_summary(self, result) -> List[str]:
        """Build formatted summary lines with per-entity counts."""
        lines = []

        # Header
        total = getattr(result, "total_records", 0)
        successful = getattr(result, "successful", 0)
        lines.append(f"Import completed: {successful} of {total} records processed.")
        lines.append("")

        # Per-entity breakdown
        entity_counts = getattr(result, "entity_counts", None)
        if entity_counts:
            lines.append("Results by entity:")
            for entity, counts in entity_counts.items():
                if isinstance(counts, dict):
                    imported = counts.get("imported", counts.get("added", 0))
                    skipped = counts.get("skipped", 0)
                    updated = counts.get("updated", counts.get("augmented", 0))
                    failed = counts.get("failed", counts.get("errors", 0))

                    parts = []
                    if imported:
                        parts.append(f"{imported} imported")
                    if updated:
                        parts.append(f"{updated} updated")
                    if skipped:
                        parts.append(f"{skipped} skipped")
                    if failed:
                        parts.append(f"{failed} failed")

                    if parts:
                        lines.append(f"  {entity}: {', '.join(parts)}")
                else:
                    lines.append(f"  {entity}: {counts}")
            lines.append("")

        # Errors summary
        errors = getattr(result, "errors", [])
        if errors:
            lines.append(f"Errors ({len(errors)}):")
            for err in errors[:5]:
                if isinstance(err, dict):
                    msg = err.get("message", str(err))
                else:
                    msg = getattr(err, "message", str(err))
                lines.append(f"  - {msg}")
            if len(errors) > 5:
                lines.append(f"  ... and {len(errors) - 5} more")
            lines.append("")

        # Warnings summary
        warnings = getattr(result, "warnings", [])
        if warnings:
            lines.append(f"Warnings ({len(warnings)}):")
            for warn in warnings[:5]:
                if isinstance(warn, dict):
                    msg = warn.get("message", str(warn))
                else:
                    msg = getattr(warn, "message", str(warn))
                lines.append(f"  - {msg}")
            if len(warnings) > 5:
                lines.append(f"  ... and {len(warnings) - 5} more")

        return lines

    def _do_purchases_import(self):
        """Execute purchase transaction import."""
        self._show_progress("Importing purchases...")

        try:
            from src.services.transaction_import_service import import_purchases

            result = import_purchases(self.file_path)

            summary_lines = [
                f"Successfully imported {result.created} purchase(s).",
                f"Skipped: {result.skipped} (duplicates or errors)",
            ]
            if result.errors:
                summary_lines.append("")
                summary_lines.append("Errors:")
                for err in result.errors[:5]:
                    summary_lines.append(f"  - {err}")
                if len(result.errors) > 5:
                    summary_lines.append(f"  ... and {len(result.errors) - 5} more")

            summary_text = "\n".join(summary_lines)
            log_path = _write_import_log(self.file_path, result, summary_text)

            self.result = result
            results_dialog = ImportResultsDialog(
                self.master,
                title="Purchases Imported",
                summary_text=summary_text,
                log_path=log_path,
            )
            results_dialog.wait_window()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Import Failed", self._format_error(e), parent=self)
        finally:
            self._hide_progress()

    def _do_adjustments_import(self):
        """Execute inventory adjustment import."""
        self._show_progress("Importing adjustments...")

        try:
            from src.services.transaction_import_service import import_adjustments

            result = import_adjustments(self.file_path)

            summary_lines = [
                f"Successfully imported {result.created} adjustment(s).",
                f"Skipped: {result.skipped}",
            ]
            if result.errors:
                summary_lines.append("")
                summary_lines.append("Errors:")
                for err in result.errors[:5]:
                    summary_lines.append(f"  - {err}")
                if len(result.errors) > 5:
                    summary_lines.append(f"  ... and {len(result.errors) - 5} more")

            summary_text = "\n".join(summary_lines)
            log_path = _write_import_log(self.file_path, result, summary_text)

            self.result = result
            results_dialog = ImportResultsDialog(
                self.master,
                title="Adjustments Imported",
                summary_text=summary_text,
                log_path=log_path,
            )
            results_dialog.wait_window()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Import Failed", self._format_error(e), parent=self)
        finally:
            self._hide_progress()

    def _show_progress(self, message: str):
        """Show progress indication."""
        self.status_label.configure(text=message)
        self.progress.pack(fill="x", padx=20, pady=(0, 5))
        self.progress.start()
        self.import_btn.configure(state="disabled")
        self.config(cursor="wait")
        self.update()

    def _hide_progress(self):
        """Hide progress indication."""
        if self.winfo_exists():
            self.progress.stop()
            self.progress.pack_forget()
            self.status_label.configure(text="")
            self.import_btn.configure(state="normal")
            self.config(cursor="")

    def _format_error(self, e: Exception) -> str:
        """Convert exception to user-friendly message."""
        error_str = str(e)

        if "JSON" in error_str or "json" in error_str:
            return (
                "The file does not appear to be a valid JSON file.\n"
                "Please check that you selected the correct file."
            )
        if "permission" in error_str.lower():
            return (
                "Unable to read the file due to permission issues.\n"
                "Please check the file permissions and try again."
            )
        if "database" in error_str.lower() or "sqlite" in error_str.lower():
            return (
                "A database error occurred during import.\n"
                "The import has been rolled back. No data was changed."
            )

        return f"An error occurred during import:\n{error_str}"


class ExportDialog(ctk.CTkToplevel):
    """Dialog for exporting data with tabbed interface for 3 export types.

    Redesigned for Feature 049 to provide clear separation:
    - Full Backup: Complete system backup (all 16 entities)
    - Catalog: Selective entity export
    - Context-Rich: AI-augmentation views with hierarchy paths
    """

    def __init__(self, parent):
        """Initialize the export dialog."""
        super().__init__(parent)
        self.title("Export Data")
        self.geometry("550x480")
        self.resizable(False, False)

        self.result = None

        self._setup_ui()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        """Set up the tabbed dialog UI."""
        # Create tab view
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Add tabs
        self.tabview.add("Full Backup")
        self.tabview.add("Catalog")
        self.tabview.add("Context-Rich")

        # Populate each tab
        self._setup_full_backup_tab()
        self._setup_catalog_tab()
        self._setup_context_rich_tab()

        # Status label (shared across tabs)
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.status_label.pack(pady=5)

        # Progress bar
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=20, pady=(0, 10))
        self.progress.set(0)
        self.progress.pack_forget()  # Hidden initially

    def _setup_full_backup_tab(self):
        """Set up Full Backup tab - exports everything, no selection needed."""
        tab = self.tabview.tab("Full Backup")

        # Purpose explanation
        purpose = ctk.CTkLabel(
            tab,
            text="Create a complete backup of all data for disaster recovery\n"
                 "or migration to another system.",
            font=ctk.CTkFont(size=13),
            wraplength=450,
            justify="center",
        )
        purpose.pack(pady=(20, 15))

        # Info about what's included
        info_frame = ctk.CTkFrame(tab)
        info_frame.pack(fill="x", padx=20, pady=10)

        info_title = ctk.CTkLabel(
            info_frame,
            text="Includes:",
            font=ctk.CTkFont(weight="bold"),
        )
        info_title.pack(anchor="w", padx=10, pady=(10, 5))

        entities = (
            "All 16 entity types: ingredients, products, recipes,\n"
            "materials, suppliers, inventory, purchases, events,\n"
            "finished goods, packages, recipients, and more."
        )
        info_label = ctk.CTkLabel(
            info_frame,
            text=entities,
            font=ctk.CTkFont(size=12),
            justify="left",
        )
        info_label.pack(anchor="w", padx=20, pady=(0, 10))

        output_label = ctk.CTkLabel(
            info_frame,
            text="Output: Folder with individual JSON files + manifest",
            font=ctk.CTkFont(size=12),
        )
        output_label.pack(anchor="w", padx=20, pady=(0, 10))

        # Export button
        export_btn = ctk.CTkButton(
            tab,
            text="Export Full Backup...",
            width=200,
            command=self._export_full_backup,
        )
        export_btn.pack(pady=20)

    def _setup_catalog_tab(self):
        """Set up Catalog tab - selective entity export."""
        tab = self.tabview.tab("Catalog")

        purpose = ctk.CTkLabel(
            tab,
            text="Export catalog data for sharing or partial backup.",
            font=ctk.CTkFont(size=13),
            wraplength=450,
        )
        purpose.pack(pady=(15, 10))

        # Entity selection frame
        entity_frame = ctk.CTkFrame(tab)
        entity_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            entity_frame,
            text="Select entities to export:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.entity_vars = {}
        # FR-003: Entities sorted alphabetically with Suppliers in correct position
        entities = [
            ("ingredients", "Ingredients"),
            ("material_products", "Material Products"),
            ("materials", "Materials"),
            ("products", "Products"),
            ("recipes", "Recipes"),
            ("suppliers", "Suppliers"),
        ]
        for key, label in entities:
            var = ctk.BooleanVar(value=True)
            self.entity_vars[key] = var
            cb = ctk.CTkCheckBox(entity_frame, text=label, variable=var)
            cb.pack(anchor="w", padx=20, pady=2)

        # Spacer
        ctk.CTkLabel(entity_frame, text="").pack(pady=5)

        # Export button
        export_btn = ctk.CTkButton(
            tab,
            text="Export Catalog...",
            width=200,
            command=self._export_catalog,
        )
        export_btn.pack(pady=15)

    def _setup_context_rich_tab(self):
        """Set up Context-Rich tab - AI augmentation views."""
        tab = self.tabview.tab("Context-Rich")

        purpose = ctk.CTkLabel(
            tab,
            text="Export data with full context (hierarchy paths, computed values)\n"
                 "for AI tools to augment and return.",
            font=ctk.CTkFont(size=13),
            wraplength=450,
            justify="center",
        )
        purpose.pack(pady=(15, 10))

        # View type selection
        view_frame = ctk.CTkFrame(tab)
        view_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            view_frame,
            text="Select view to export:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.view_var = ctk.StringVar(value="ingredients")
        views = [
            ("ingredients", "Ingredients (with products, inventory totals, costs)"),
            ("materials", "Materials (with hierarchy paths, products)"),
            ("recipes", "Recipes (with ingredients, computed costs)"),
        ]
        for value, label in views:
            rb = ctk.CTkRadioButton(
                view_frame,
                text=label,
                variable=self.view_var,
                value=value,
            )
            rb.pack(anchor="w", padx=20, pady=3)

        ctk.CTkLabel(view_frame, text="").pack(pady=5)

        # Info about editable fields
        info_label = ctk.CTkLabel(
            tab,
            text="Exported files include _meta section indicating which\n"
                 "fields are editable vs. computed (readonly).",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        info_label.pack(pady=5)

        # Export button
        export_btn = ctk.CTkButton(
            tab,
            text="Export Context-Rich View...",
            width=200,
            command=self._export_context_rich,
        )
        export_btn.pack(pady=15)

    def _export_full_backup(self):
        """Execute full backup export."""
        # FR-015: Use configured export directory as initial location
        initial_dir = str(preferences_service.get_export_directory())
        dir_path = filedialog.askdirectory(
            title="Select Export Directory for Full Backup",
            initialdir=initial_dir,
            parent=self,
        )

        if not dir_path:
            return

        # Create timestamped subdirectory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        export_dir = Path(dir_path) / f"backup_{timestamp}"

        self._show_progress("Exporting full backup...")

        try:
            manifest = coordinated_export_service.export_complete(str(export_dir))

            file_count = len(manifest.files)
            total_records = sum(f.record_count for f in manifest.files)

            summary_lines = [
                f"Successfully exported {total_records} records",
                f"across {file_count} files.",
                "",
                f"Export directory:\n{export_dir}",
            ]

            messagebox.showinfo(
                "Export Complete",
                "\n".join(summary_lines),
                parent=self,
            )
            self.result = manifest
            self.destroy()

        except Exception as e:
            self._show_error("Export Failed", e)
        finally:
            self._hide_progress()

    def _export_catalog(self):
        """Execute catalog export with selected entities."""
        # Get selected entities
        selected = [k for k, v in self.entity_vars.items() if v.get()]

        if not selected:
            messagebox.showwarning(
                "No Entities Selected",
                "Please select at least one entity type to export.",
                parent=self,
            )
            return

        default_name = f"catalog-export-{date.today().isoformat()}.json"

        # FR-015: Use configured export directory as initial location
        initial_dir = str(preferences_service.get_export_directory())
        file_path = filedialog.asksaveasfilename(
            title="Export Catalog",
            initialdir=initial_dir,
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self,
        )

        if not file_path:
            return

        self._show_progress("Exporting catalog...")

        try:
            result = import_export_service.export_all_to_json(
                file_path,
                entities=selected,
            )

            summary_lines = [f"Successfully exported {result.record_count} records."]
            if result.entity_counts:
                summary_lines.append("")
                for entity, count in result.entity_counts.items():
                    if count > 0:
                        summary_lines.append(f"  {entity}: {count}")

            summary_lines.append("")
            summary_lines.append(f"Saved to:\n{file_path}")

            messagebox.showinfo(
                "Export Complete",
                "\n".join(summary_lines),
                parent=self,
            )
            self.result = result
            self.destroy()

        except Exception as e:
            self._show_error("Export Failed", e)
        finally:
            self._hide_progress()

    def _export_context_rich(self):
        """Execute context-rich view export."""
        view_type = self.view_var.get()

        # FR-015: Use configured export directory as initial location
        initial_dir = str(preferences_service.get_export_directory())
        dir_path = filedialog.askdirectory(
            title=f"Select Export Directory for {view_type.title()} View",
            initialdir=initial_dir,
            parent=self,
        )

        if not dir_path:
            return

        self._show_progress(f"Exporting {view_type} view...")

        try:
            # Export the selected view type
            if view_type == "ingredients":
                result = denormalized_export_service.export_ingredients_view(
                    str(Path(dir_path) / "view_ingredients.json")
                )
            elif view_type == "materials":
                result = denormalized_export_service.export_materials_view(
                    str(Path(dir_path) / "view_materials.json")
                )
            elif view_type == "recipes":
                result = denormalized_export_service.export_recipes_view(
                    str(Path(dir_path) / "view_recipes.json")
                )

            summary_lines = [
                f"Successfully exported {view_type} view.",
                "",
                f"Export directory:\n{dir_path}",
                "",
                "This file can be edited (e.g., by AI tools)",
                "and re-imported to update the database.",
            ]

            messagebox.showinfo(
                "Export Complete",
                "\n".join(summary_lines),
                parent=self,
            )
            self.result = result
            self.destroy()

        except Exception as e:
            self._show_error("Export Failed", e)
        finally:
            self._hide_progress()

    def _show_progress(self, message: str):
        """Show progress indication."""
        self.status_label.configure(text=message)
        self.progress.pack(fill="x", padx=20, pady=(0, 10))
        self.progress.set(0)
        self.progress.start()
        self.config(cursor="wait")
        self.update()

    def _hide_progress(self):
        """Hide progress indication."""
        if self.winfo_exists():
            self.progress.stop()
            self.progress.pack_forget()
            self.status_label.configure(text="")
            self.config(cursor="")

    def _show_error(self, title: str, e: Exception):
        """Show error message."""
        messagebox.showerror(
            title,
            self._format_error(e),
            parent=self,
        )

    def _format_error(self, e: Exception) -> str:
        """Convert exception to user-friendly message."""
        error_str = str(e)

        if "permission" in error_str.lower():
            return (
                "Unable to write to the selected location.\n"
                "Please check that you have write permission."
            )
        if "database" in error_str.lower() or "sqlite" in error_str.lower():
            return "A database error occurred while reading data for export."

        return f"An error occurred during export:\n{error_str}"


class ImportViewDialog(ctk.CTkToplevel):
    """Dialog for importing a denormalized view file (F030).

    Provides file selection and mode selection before import.
    Interactive FK resolution is enabled by default for UI.
    """

    def __init__(self, parent):
        """Initialize the import view dialog.

        Args:
            parent: Parent window
        """
        super().__init__(parent)
        self.title("Import View")
        self.geometry("500x350")
        self.resizable(False, False)

        self.file_path: str = None
        self.mode: str = "merge"
        self.confirmed: bool = False

        self._setup_ui()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Bind Escape key
        self.bind("<Escape>", lambda e: self.destroy())

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Import View",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.pack(pady=(20, 10))

        # Instructions
        instructions = ctk.CTkLabel(
            self,
            text="Import a denormalized view file (JSON format).\n"
            "Missing references will be resolved interactively.",
            font=ctk.CTkFont(size=12),
            justify="center",
        )
        instructions.pack(pady=(0, 15))

        # File selection frame
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(file_frame, text="File:").pack(anchor="w", padx=10, pady=(10, 5))

        file_inner = ctk.CTkFrame(file_frame, fg_color="transparent")
        file_inner.pack(fill="x", padx=10, pady=(0, 10))

        self.file_entry = ctk.CTkEntry(file_inner, width=320, state="readonly")
        self.file_entry.pack(side="left", padx=(0, 10))

        browse_btn = ctk.CTkButton(
            file_inner,
            text="Browse...",
            width=80,
            command=self._browse_file,
        )
        browse_btn.pack(side="left")

        # Mode selection frame
        mode_frame = ctk.CTkFrame(self)
        mode_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            mode_frame,
            text="Import Mode:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.mode_var = ctk.StringVar(value="merge")

        ctk.CTkRadioButton(
            mode_frame,
            text="Merge (update existing, add new)",
            variable=self.mode_var,
            value="merge",
        ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkRadioButton(
            mode_frame,
            text="Skip Existing (add new only)",
            variable=self.mode_var,
            value="skip_existing",
        ).pack(anchor="w", padx=20, pady=(2, 10))

        # Button frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        self.import_btn = ctk.CTkButton(
            btn_frame,
            text="Import",
            width=100,
            command=self._on_import,
        )
        self.import_btn.pack(side="right", padx=(10, 0))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self.destroy,
        )
        cancel_btn.pack(side="right")

    def _browse_file(self):
        """Open file browser to select view file."""
        # FR-015: Use configured import directory as initial location
        initial_dir = str(preferences_service.get_import_directory())
        file_path = filedialog.askopenfilename(
            title="Select View File",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self,
        )
        if file_path:
            self.file_path = file_path
            self.file_entry.configure(state="normal")
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, file_path)
            self.file_entry.configure(state="readonly")

    def _on_import(self):
        """Handle import button click."""
        if not self.file_path:
            messagebox.showwarning(
                "No File Selected",
                "Please select a file to import.",
                parent=self,
            )
            return

        self.confirmed = True
        self.mode = self.mode_var.get()
        self.destroy()
