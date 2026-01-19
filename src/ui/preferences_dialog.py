"""
Preferences Dialog for the Seasonal Baking Tracker.

Provides a modal dialog for configuring application directory preferences
(import, export, logs directories).
"""

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.services import preferences_service


class PreferencesDialog(ctk.CTkToplevel):
    """Dialog for configuring application preferences.

    Allows users to configure:
    - Import directory (where to look for import files)
    - Export directory (where to save exported files)
    - Logs directory (where to write import/export logs)
    """

    def __init__(self, parent):
        """Initialize the preferences dialog.

        Args:
            parent: Parent window
        """
        super().__init__(parent)
        self.title("Preferences")
        self.geometry("550x620")
        self.resizable(False, False)

        # Store original values for cancel
        self._import_dir = None
        self._export_dir = None
        self._logs_dir = None
        self._backup_dir = None

        self._setup_ui()
        self._load_current_preferences()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Bind Escape key to cancel
        self.bind("<Escape>", lambda e: self._on_cancel())

        # Focus the dialog
        self.focus_force()

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Button frame - pack at bottom FIRST so it's always visible
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=(20, 15))

        # Restore Defaults button (left side)
        restore_btn = ctk.CTkButton(
            btn_frame,
            text="Restore Defaults",
            width=130,
            fg_color="gray",
            command=self._on_restore_defaults,
        )
        restore_btn.pack(side="left")

        # Cancel button (right side)
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self._on_cancel,
        )
        cancel_btn.pack(side="right", padx=(10, 0))

        # Save button (right side)
        save_btn = ctk.CTkButton(
            btn_frame,
            text="Save",
            width=100,
            command=self._on_save,
        )
        save_btn.pack(side="right")

        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Preferences",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.pack(pady=(15, 10))

        # Description
        desc_label = ctk.CTkLabel(
            self,
            text="Configure default directories for import, export, and log files.",
            font=ctk.CTkFont(size=12),
        )
        desc_label.pack(pady=(0, 15))

        # Directory pickers frame
        dirs_frame = ctk.CTkFrame(self)
        dirs_frame.pack(fill="x", padx=20, pady=10)

        # Import Directory
        self._create_directory_picker(
            dirs_frame,
            "Import Directory",
            "Default location for import file browser",
            "import",
        )

        # Export Directory
        self._create_directory_picker(
            dirs_frame,
            "Export Directory",
            "Default location for export file browser",
            "export",
        )

        # Logs Directory
        self._create_directory_picker(
            dirs_frame,
            "Logs Directory",
            "Where import/export logs are saved (requires write permission)",
            "logs",
        )

        # Backup Directory
        self._create_directory_picker(
            dirs_frame,
            "Backup Directory",
            "Default location for backup restore file browser",
            "backup",
        )

    def _create_directory_picker(self, parent, label: str, description: str, dir_type: str):
        """Create a directory picker widget.

        Args:
            parent: Parent frame
            label: Label text
            description: Description text
            dir_type: Type of directory ('import', 'export', 'logs')
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=8)

        # Label
        lbl = ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(weight="bold"),
        )
        lbl.pack(anchor="w")

        # Description
        desc = ctk.CTkLabel(
            frame,
            text=description,
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        desc.pack(anchor="w")

        # Entry and button row
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(5, 0))

        entry = ctk.CTkEntry(row, width=380, state="readonly")
        entry.pack(side="left", padx=(0, 10))

        browse_btn = ctk.CTkButton(
            row,
            text="Browse...",
            width=80,
            command=lambda: self._browse_directory(dir_type),
        )
        browse_btn.pack(side="left")

        # Store entry reference
        setattr(self, f"_{dir_type}_entry", entry)

    def _load_current_preferences(self):
        """Load current preferences into the UI."""
        # Import directory
        self._import_dir = preferences_service.get_import_directory()
        self._update_entry("import", self._import_dir)

        # Export directory
        self._export_dir = preferences_service.get_export_directory()
        self._update_entry("export", self._export_dir)

        # Logs directory
        self._logs_dir = preferences_service.get_logs_directory()
        self._update_entry("logs", self._logs_dir)

        # Backup directory
        self._backup_dir = preferences_service.get_backup_directory()
        self._update_entry("backup", self._backup_dir)

    def _update_entry(self, dir_type: str, path: Path):
        """Update an entry field with a path.

        Args:
            dir_type: Type of directory ('import', 'export', 'logs')
            path: Path to display
        """
        entry = getattr(self, f"_{dir_type}_entry")
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, str(path))
        entry.configure(state="readonly")

    def _browse_directory(self, dir_type: str):
        """Open directory browser and update the entry.

        Args:
            dir_type: Type of directory ('import', 'export', 'logs')
        """
        # Get current value as initial directory
        current = getattr(self, f"_{dir_type}_dir")
        initial_dir = str(current) if current and current.exists() else str(Path.home())

        # Open directory picker
        selected = filedialog.askdirectory(
            title=f"Select {dir_type.title()} Directory",
            initialdir=initial_dir,
            parent=self,
        )

        if selected:
            path = Path(selected)
            setattr(self, f"_{dir_type}_dir", path)
            self._update_entry(dir_type, path)

    def _on_restore_defaults(self):
        """Handle Restore Defaults button click."""
        if not messagebox.askyesno(
            "Restore Defaults",
            "This will reset all directory preferences to their default values.\n\n"
            "Are you sure you want to continue?",
            parent=self,
        ):
            return

        # Reset preferences
        preferences_service.reset_all_preferences()

        # Reload into UI
        self._load_current_preferences()

        messagebox.showinfo(
            "Defaults Restored",
            "All directory preferences have been reset to defaults.",
            parent=self,
        )

    def _on_save(self):
        """Handle Save button click."""
        errors = []

        # Validate import directory
        if not self._import_dir or not self._import_dir.exists():
            errors.append(f"Import directory does not exist: {self._import_dir}")
        elif not self._import_dir.is_dir():
            errors.append(f"Import path is not a directory: {self._import_dir}")

        # Validate export directory
        if not self._export_dir or not self._export_dir.exists():
            errors.append(f"Export directory does not exist: {self._export_dir}")
        elif not self._export_dir.is_dir():
            errors.append(f"Export path is not a directory: {self._export_dir}")

        # Validate logs directory (also check write permission)
        if not self._logs_dir or not self._logs_dir.exists():
            errors.append(f"Logs directory does not exist: {self._logs_dir}")
        elif not self._logs_dir.is_dir():
            errors.append(f"Logs path is not a directory: {self._logs_dir}")

        # Validate backup directory
        if not self._backup_dir or not self._backup_dir.exists():
            errors.append(f"Backup directory does not exist: {self._backup_dir}")
        elif not self._backup_dir.is_dir():
            errors.append(f"Backup path is not a directory: {self._backup_dir}")

        if errors:
            messagebox.showerror(
                "Validation Error",
                "Please fix the following issues:\n\n" + "\n".join(errors),
                parent=self,
            )
            return

        # Save preferences
        try:
            preferences_service.set_import_directory(str(self._import_dir))
            preferences_service.set_export_directory(str(self._export_dir))
            preferences_service.set_logs_directory(str(self._logs_dir))
            preferences_service.set_backup_directory(str(self._backup_dir))

            self.destroy()

        except ValueError as e:
            messagebox.showerror(
                "Save Failed",
                f"Failed to save preferences:\n\n{str(e)}",
                parent=self,
            )

    def _on_cancel(self):
        """Handle Cancel button click."""
        self.destroy()
