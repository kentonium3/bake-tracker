"""
Catalog Import Dialog for importing ingredients, products, and recipes.

Provides a modal dialog for catalog import operations with mode selection,
entity filtering, and dry-run preview capability.
"""

from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.services.catalog_import_service import (
    import_catalog,
    CatalogImportError,
    CatalogImportResult,
)


class CatalogImportDialog(ctk.CTkToplevel):
    """Dialog for importing catalog data from a JSON file."""

    def __init__(self, parent):
        """Initialize the catalog import dialog."""
        super().__init__(parent)
        self.title("Import Catalog")
        self.geometry("550x620")
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
            text="Import Catalog",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.pack(pady=(20, 10))

        # Instructions
        instructions = ctk.CTkLabel(
            self,
            text="Import catalog data (ingredients, products, recipes) from a JSON file.\n"
            "Catalog import does not affect existing inventory or transactional data.",
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

        self.file_entry = ctk.CTkEntry(file_inner, width=350, state="readonly")
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

        self.mode_var = ctk.StringVar(value="add")

        self.add_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Add Only (create new, skip existing)",
            variable=self.mode_var,
            value="add",
        )
        self.add_radio.pack(anchor="w", padx=20, pady=2)

        self.augment_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Augment (update null fields on existing)",
            variable=self.mode_var,
            value="augment",
        )
        self.augment_radio.pack(anchor="w", padx=20, pady=(2, 10))

        # Entity selection frame
        entity_frame = ctk.CTkFrame(self)
        entity_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            entity_frame,
            text="Entities to Import:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.ingredients_var = ctk.BooleanVar(value=True)
        self.products_var = ctk.BooleanVar(value=True)
        self.recipes_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(
            entity_frame,
            text="Ingredients",
            variable=self.ingredients_var,
        ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkCheckBox(
            entity_frame,
            text="Products",
            variable=self.products_var,
        ).pack(anchor="w", padx=20, pady=2)

        self.recipes_checkbox = ctk.CTkCheckBox(
            entity_frame,
            text="Recipes (Augment mode not supported)",
            variable=self.recipes_var,
            command=self._on_recipe_toggle,
        )
        self.recipes_checkbox.pack(anchor="w", padx=20, pady=(2, 10))

        # Dry-run checkbox
        self.dry_run_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="Preview changes before importing (dry-run)",
            variable=self.dry_run_var,
            command=self._on_dry_run_toggle,
        ).pack(anchor="w", padx=20, pady=10)

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
        """Open file browser to select catalog file."""
        file_path = filedialog.askopenfilename(
            title="Select Catalog File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self,
        )
        if file_path:
            self.file_path = file_path
            self.file_entry.configure(state="normal")
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, file_path)
            self.file_entry.configure(state="readonly")

    def _on_recipe_toggle(self):
        """Handle recipe checkbox toggle - disable Augment when Recipes selected."""
        if self.recipes_var.get():
            # Recipes selected - force Add Only mode
            if self.mode_var.get() == "augment":
                self.mode_var.set("add")
            self.augment_radio.configure(state="disabled")
        else:
            self.augment_radio.configure(state="normal")

    def _on_dry_run_toggle(self):
        """Handle dry-run checkbox toggle - change button label."""
        if self.dry_run_var.get():
            self.import_btn.configure(text="Preview...")
        else:
            self.import_btn.configure(text="Import")

    def _do_import(self):
        """Execute the import operation."""
        if not self.file_path:
            messagebox.showwarning(
                "No File Selected",
                "Please select a catalog file to import.",
                parent=self,
            )
            return

        # Build entity list
        entities = []
        if self.ingredients_var.get():
            entities.append("ingredients")
        if self.products_var.get():
            entities.append("products")
        if self.recipes_var.get():
            entities.append("recipes")

        if not entities:
            messagebox.showwarning(
                "No Entities Selected",
                "Please select at least one entity type to import.",
                parent=self,
            )
            return

        # Show progress
        action = "Previewing" if self.dry_run_var.get() else "Importing"
        self.status_label.configure(text=f"{action}... Please wait.")
        self.import_btn.configure(state="disabled")
        self.config(cursor="wait")
        self.update()

        try:
            result = import_catalog(
                self.file_path,
                mode=self.mode_var.get(),
                entities=entities,
                dry_run=self.dry_run_var.get(),
            )
            self._show_results(result)
        except CatalogImportError as e:
            messagebox.showerror("Catalog Import Error", str(e), parent=self)
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
                f"An unexpected error occurred:\n{str(e)}",
                parent=self,
            )
        finally:
            self.status_label.configure(text="")
            self.import_btn.configure(state="normal")
            self.config(cursor="")

    def _show_results(self, result: CatalogImportResult):
        """Show import results in a message dialog."""
        title = "Preview Complete" if result.dry_run else "Import Complete"

        # Build summary
        lines = []
        for entity_type, counts in result.entity_counts.items():
            parts = []
            if counts.added > 0:
                parts.append(f"{counts.added} added")
            if counts.augmented > 0:
                parts.append(f"{counts.augmented} augmented")
            if counts.skipped > 0:
                parts.append(f"{counts.skipped} skipped")
            if counts.failed > 0:
                parts.append(f"{counts.failed} failed")
            if parts:
                lines.append(f"{entity_type.title()}: {', '.join(parts)}")

        summary = "\n".join(lines) if lines else "No records processed."

        if result.dry_run:
            summary = "DRY RUN - No changes made\n\n" + summary

        # Show main summary
        messagebox.showinfo(title, summary, parent=self)

        # Show errors if any
        if result.errors:
            self._show_errors(result.errors)

        # Close dialog on successful import (not dry-run)
        if not result.dry_run and not result.has_errors:
            self.result = result
            self.destroy()
        elif not result.dry_run and result.total_added > 0:
            # Partial success - still close but set result
            self.result = result
            self.destroy()

    def _show_errors(self, errors):
        """Show error details in a warning dialog."""
        error_lines = []
        for i, err in enumerate(errors[:5]):
            error_lines.append(
                f"- {err.entity_type}: {err.identifier}\n"
                f"  {err.message}"
            )
        if len(errors) > 5:
            error_lines.append(f"\n... and {len(errors) - 5} more errors")

        messagebox.showwarning(
            f"Import Errors ({len(errors)} total)",
            "\n".join(error_lines),
            parent=self,
        )
