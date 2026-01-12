"""
Import and Export dialogs for the Seasonal Baking Tracker.

Provides modal dialogs for data import/export operations with mode selection.
"""

import logging
import os
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.services import import_export_service
from src.services import coordinated_export_service
from src.services import denormalized_export_service


def _get_logs_dir() -> Path:
    """Get the logs directory, creating it if needed."""
    # TEMPORARY: Use project directory for user testing
    # TODO: Make log path configurable. Production path should be relative,
    #   not absolute (Path.home() based). Current test path is relative to project.
    logs_dir = Path(__file__).parent.parent.parent / "docs" / "user_testing"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _write_import_log(file_path: str, result, summary_text: str) -> str:
    """Write import results to a log file.

    Args:
        file_path: Source file that was imported
        result: ImportResult or CatalogImportResult
        summary_text: Formatted summary text

    Returns:
        Relative path to the created log file (for display in UI).
    """
    logs_dir = _get_logs_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_file = logs_dir / f"import_{timestamp}.log"

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Import Log - {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Source file: {file_path}\n")
        f.write(f"Import mode: {getattr(result, 'mode', 'unknown')}\n\n")
        f.write("Results:\n")
        f.write("-" * 40 + "\n")
        f.write(summary_text)
        f.write("\n")

    # Return relative path for display
    try:
        return str(log_file.relative_to(Path.cwd()))
    except ValueError:
        return str(log_file)  # Fallback to absolute if not relative


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
        self.geometry("550x600")
        self.resizable(False, False)

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

        # Button frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

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

    def _on_purpose_changed(self):
        """Handle purpose selection change."""
        purpose = self.purpose_var.get()

        if purpose == "backup":
            self._setup_backup_options()
        elif purpose == "catalog":
            self._setup_catalog_options()
        elif purpose == "purchases":
            self._setup_transaction_options("purchases")
        elif purpose == "adjustments":
            self._setup_transaction_options("adjustments")

    def _browse_file(self):
        """Open file browser and auto-detect format."""
        file_path = filedialog.askopenfilename(
            title="Select Import File",
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
            elif result.format_type == "context_rich":
                self.purpose_var.set("catalog")
                self._on_purpose_changed()
            elif result.format_type == "normalized":
                # Could be backup or catalog
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

            # Check if it's a context-rich file
            if self.detected_format and self.detected_format.format_type == "context_rich":
                from src.services.enhanced_import_service import import_context_rich_view

                result = import_context_rich_view(self.file_path)
                summary_text = result.get_summary()
            else:
                # Standard catalog import
                result = import_export_service.import_all_from_json_v4(
                    self.file_path,
                    mode="merge" if mode == "add" else mode,
                )
                summary_text = result.get_summary()

            log_path = _write_import_log(self.file_path, result, summary_text)

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
        entities = [
            ("ingredients", "Ingredients"),
            ("products", "Products"),
            ("recipes", "Recipes"),
            ("materials", "Materials"),
            ("material_products", "Material Products"),
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
        dir_path = filedialog.askdirectory(
            title="Select Export Directory for Full Backup",
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

        file_path = filedialog.asksaveasfilename(
            title="Export Catalog",
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

        dir_path = filedialog.askdirectory(
            title=f"Select Export Directory for {view_type.title()} View",
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
        file_path = filedialog.askopenfilename(
            title="Select View File",
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
