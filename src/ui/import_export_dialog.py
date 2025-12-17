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
from src.services.import_export_service import ImportVersionError


def _get_logs_dir() -> Path:
    """Get the logs directory, creating it if needed."""
    # Use the app's data directory (same location as database)
    app_data_dir = Path.home() / "Documents" / "BakeTracker"
    logs_dir = app_data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _write_import_log(file_path: str, result, summary_text: str) -> str:
    """Write import results to a log file.

    Returns:
        Path to the created log file.
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
    """Dialog for importing data from a JSON file."""

    def __init__(self, parent):
        """Initialize the import dialog."""
        super().__init__(parent)
        self.title("Import Data")
        self.geometry("500x450")
        self.resizable(False, False)

        self.result = None
        self.file_path = None

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
        title_label.pack(pady=(20, 10))

        # Instructions
        instructions = ctk.CTkLabel(
            self,
            text="Select a JSON backup file to import into the application.",
            font=ctk.CTkFont(size=12),
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
            text="Merge (add new records, skip duplicates)",
            variable=self.mode_var,
            value="merge",
        ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkRadioButton(
            mode_frame,
            text="Replace (clear ALL existing data first)",
            variable=self.mode_var,
            value="replace",
        ).pack(anchor="w", padx=20, pady=(2, 10))

        # Status label (for progress indication)
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.status_label.pack(pady=5)

        # Button frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        self.import_btn = ctk.CTkButton(
            btn_frame,
            text="Import",
            width=100,
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

    def _browse_file(self):
        """Open file browser to select import file."""
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

    def _do_import(self):
        """Execute the import operation."""
        if not self.file_path:
            messagebox.showwarning(
                "No File Selected",
                "Please select a file to import.",
                parent=self,
            )
            return

        # Confirm Replace mode
        if self.mode_var.get() == "replace":
            if not messagebox.askyesno(
                "Confirm Replace",
                "This will DELETE all existing data before importing.\n\n"
                "Are you sure you want to continue?",
                icon="warning",
                parent=self,
            ):
                return

        # Show progress
        self.status_label.configure(text="Importing data... Please wait.")
        self.import_btn.configure(state="disabled")
        self.config(cursor="wait")
        self.update()

        try:
            result = import_export_service.import_all_from_json_v3(
                self.file_path,
                mode=self.mode_var.get(),
            )

            # Get summary text and write to log file
            summary_text = result.get_summary()
            log_path = _write_import_log(self.file_path, result, summary_text)

            # Show results in custom dialog with scrolling, copy, and log path
            self.result = result
            results_dialog = ImportResultsDialog(
                self.master,  # Use main window as parent, not this dialog
                title="Import Complete",
                summary_text=summary_text,
                log_path=log_path,
            )
            results_dialog.wait_window()
            self.destroy()

        except ImportVersionError as e:
            # User-friendly version error
            messagebox.showerror(
                "Unsupported File Version",
                str(e),
                parent=self,
            )
        except FileNotFoundError:
            messagebox.showerror(
                "File Not Found",
                "The selected file could not be found.\n"
                "Please check the file path and try again.",
                parent=self,
            )
        except Exception as e:
            messagebox.showerror(
                "Import Failed",
                self._format_error(e),
                parent=self,
            )
        finally:
            # Only update widgets if dialog still exists (not destroyed after success)
            if self.winfo_exists():
                self.status_label.configure(text="")
                self.import_btn.configure(state="normal")
                self.config(cursor="")

    def _format_error(self, e: Exception) -> str:
        """Convert exception to user-friendly message."""
        error_str = str(e)

        # Handle common errors with friendly messages
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

        # Generic fallback
        return f"An error occurred during import:\n{error_str}"


class ExportDialog(ctk.CTkToplevel):
    """Dialog for exporting data to a JSON file."""

    def __init__(self, parent):
        """Initialize the export dialog."""
        super().__init__(parent)
        self.title("Export Data")
        self.geometry("450x250")
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
        """Set up the dialog UI."""
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Export Data",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.pack(pady=(20, 10))

        # Instructions
        instructions = ctk.CTkLabel(
            self,
            text="Export all application data to a JSON backup file.\n"
            "This creates a complete backup of your ingredients,\n"
            "recipes, pantry items, events, and more.",
            font=ctk.CTkFont(size=12),
            justify="center",
        )
        instructions.pack(pady=(0, 20))

        # Status label (for progress indication)
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.status_label.pack(pady=5)

        # Button frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        self.export_btn = ctk.CTkButton(
            btn_frame,
            text="Choose Location & Export...",
            width=200,
            command=self._do_export,
        )
        self.export_btn.pack(side="right", padx=(10, 0))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self.destroy,
        )
        cancel_btn.pack(side="right")

    def _do_export(self):
        """Execute the export operation."""
        # Default filename with date
        default_name = f"bake-tracker-backup-{date.today().isoformat()}.json"

        file_path = filedialog.asksaveasfilename(
            title="Export Data",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self,
        )

        if not file_path:
            return  # User cancelled

        # Show progress
        self.status_label.configure(text="Exporting data... Please wait.")
        self.export_btn.configure(state="disabled")
        self.config(cursor="wait")
        self.update()

        try:
            result = import_export_service.export_all_to_json(file_path)

            # Build success message with entity counts
            summary_lines = [f"Successfully exported {result.record_count} records."]
            if result.entity_counts:
                summary_lines.append("")
                summary_lines.append("Records by type:")
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

        except PermissionError:
            messagebox.showerror(
                "Export Failed",
                "Unable to write to the selected location.\n"
                "Please check that you have write permission and try again.",
                parent=self,
            )
        except Exception as e:
            messagebox.showerror(
                "Export Failed",
                self._format_error(e),
                parent=self,
            )
        finally:
            # Only update widgets if dialog still exists (not destroyed after success)
            if self.winfo_exists():
                self.status_label.configure(text="")
                self.export_btn.configure(state="normal")
                self.config(cursor="")

    def _format_error(self, e: Exception) -> str:
        """Convert exception to user-friendly message."""
        error_str = str(e)

        # Handle common errors with friendly messages
        if "permission" in error_str.lower():
            return (
                "Unable to write to the selected location.\n"
                "Please check that you have write permission."
            )
        if "database" in error_str.lower() or "sqlite" in error_str.lower():
            return "A database error occurred while reading data for export."

        # Generic fallback
        return f"An error occurred during export:\n{error_str}"
