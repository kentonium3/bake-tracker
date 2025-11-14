"""
Migration Wizard UI for v0.3.0 → v0.4.0 schema migration.

Provides interface for:
- Viewing migration explanation
- Running dry-run preview
- Executing actual migration
- Viewing migration results and validation
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Dict
import threading

from src.services.database import session_scope
from src.utils.migrate_to_ingredient_variant import (
    populate_uuids,
    migrate_all_ingredients,
    update_recipe_ingredient_references,
)


class MigrationWizardDialog(ctk.CTkToplevel):
    """
    Migration wizard for v0.3.0 → v0.4.0 schema migration.

    Features:
    - Welcome screen with migration explanation
    - Dry-run preview showing what will change
    - Migration execution with progress tracking
    - Results display with validation
    - Error handling with rollback advice
    """

    def __init__(self, parent):
        """
        Initialize the migration wizard.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.title("Migration Wizard - v0.3.0 → v0.4.0")
        self.geometry("800x700")
        self.resizable(True, True)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # State
        self.dry_run_results = None
        self.migration_running = False
        self.migration_executed = False

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Create UI
        self._create_header()
        self._create_content()
        self._create_buttons()

        # Show welcome screen
        self._show_welcome_screen()

    def _create_header(self):
        """Create header with title."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="Migration Wizard",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Migrate from v0.3.0 (legacy) to v0.4.0 (Ingredient/Variant/Pantry architecture)",
            font=ctk.CTkFont(size=12),
        )
        subtitle.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

    def _create_content(self):
        """Create scrollable content area."""
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # Scrollable textbox for content
        self.content_text = ctk.CTkTextbox(content_frame, wrap="word")
        self.content_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

    def _create_buttons(self):
        """Create action buttons."""
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=0)
        button_frame.grid_columnconfigure(2, weight=0)
        button_frame.grid_columnconfigure(3, weight=0)

        # Close button
        self.close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            width=100,
        )
        self.close_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Dry Run button
        self.dry_run_btn = ctk.CTkButton(
            button_frame,
            text="Run Dry Run",
            command=self._run_dry_run,
            width=120,
        )
        self.dry_run_btn.grid(row=0, column=1, padx=5, pady=5)

        # Execute button (disabled initially)
        self.execute_btn = ctk.CTkButton(
            button_frame,
            text="Execute Migration",
            command=self._execute_migration,
            width=150,
            fg_color="darkred",
            hover_color="red",
        )
        self.execute_btn.grid(row=0, column=2, padx=5, pady=5)
        self.execute_btn.configure(state="disabled")

        # Back button
        self.back_btn = ctk.CTkButton(
            button_frame,
            text="← Back to Welcome",
            command=self._show_welcome_screen,
            width=150,
        )
        self.back_btn.grid(row=0, column=3, padx=5, pady=5)

    def _show_welcome_screen(self):
        """Display welcome screen with migration explanation."""
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")

        welcome_text = """
WELCOME TO THE MIGRATION WIZARD

This wizard will help you migrate your database from the v0.3.0 schema to the new v0.4.0 architecture.

═══════════════════════════════════════════════════════════════════

WHAT'S CHANGING:

The v0.4.0 release introduces a new data model separating:

1. Ingredients (Generic)
   - Generic ingredient definitions (e.g., "All-Purpose Flour")
   - No brand or quantity information
   - Category, recipe unit, density metadata

2. Variants (Brand-Specific)
   - Brand and package-specific information
   - Purchase unit and quantity (e.g., "King Arthur - 25 lb")
   - UPC/GTIN, supplier information
   - One variant can be marked as "preferred"

3. Pantry Items (Inventory Lots)
   - Individual purchase lots with tracking
   - Purchase date, expiration date, location
   - FIFO (First In, First Out) consumption

═══════════════════════════════════════════════════════════════════

MIGRATION PROCESS:

1. UUID Population
   - Populate UUID columns for all existing records

2. Ingredient Migration
   - Each legacy ingredient becomes a generic ingredient
   - A variant is created with brand/package information
   - If quantity > 0, a pantry item is created
   - Unit conversions are preserved
   - Purchase history (unit_cost) becomes Purchase records

3. Recipe Updates
   - RecipeIngredient foreign keys are updated to new ingredient IDs

4. Validation
   - Data integrity checks
   - Cost calculation comparison

═══════════════════════════════════════════════════════════════════

BEFORE YOU BEGIN:

⚠️  BACKUP YOUR DATABASE FIRST!

This migration modifies your database structure. While it has been tested,
you should always backup your data before running any migration.

📋  RECOMMENDED STEPS:

1. Run a DRY RUN first to preview changes
2. Review the dry run report carefully
3. Backup your database file (baking_tracker.db)
4. Execute the migration
5. Verify data integrity in the new UI

═══════════════════════════════════════════════════════════════════

READY TO START?

Click "Run Dry Run" to see a preview of what will change without actually
modifying your database.
"""

        self.content_text.insert("1.0", welcome_text)
        self.content_text.configure(state="disabled")

        # Update button states
        self.dry_run_btn.configure(state="normal")
        self.execute_btn.configure(state="disabled")
        self.dry_run_results = None

    def _run_dry_run(self):
        """Run dry-run migration preview."""
        self.dry_run_btn.configure(state="disabled", text="Running Dry Run...")
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", "Running dry run...\n\nPlease wait...")
        self.content_text.configure(state="disabled")

        # Run in thread to avoid blocking UI
        thread = threading.Thread(target=self._execute_dry_run_thread)
        thread.daemon = True
        thread.start()

    def _execute_dry_run_thread(self):
        """Execute dry run in background thread."""
        try:
            results = {}

            with session_scope() as session:
                # Step 1: Populate UUIDs (dry run)
                uuid_counts = populate_uuids(session, dry_run=True)
                results['uuid_counts'] = uuid_counts

                # Step 2: Migrate ingredients (dry run)
                migration_stats = migrate_all_ingredients(session, dry_run=True)
                results['migration_stats'] = migration_stats

                # Step 3: Update recipe references (dry run)
                updated_count = update_recipe_ingredient_references(session, dry_run=True)
                results['recipe_updates'] = updated_count

            self.dry_run_results = results

            # Update UI on main thread
            self.after(0, self._display_dry_run_results, results)

        except Exception as e:
            error_msg = f"Dry run failed: {str(e)}"
            self.after(0, self._display_error, error_msg)

    def _display_dry_run_results(self, results: Dict):
        """Display dry run results."""
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")

        report = """
DRY RUN REPORT
═══════════════════════════════════════════════════════════════════

This is a PREVIEW of what will happen when you execute the migration.
No changes have been made to your database.

═══════════════════════════════════════════════════════════════════

STEP 1: UUID POPULATION
"""

        uuid_counts = results.get('uuid_counts', {})
        total_uuids = sum(uuid_counts.values())
        if total_uuids > 0:
            report += f"\nWill populate UUIDs for {total_uuids} records:\n"
            for model, count in uuid_counts.items():
                if count > 0:
                    report += f"  • {model}: {count} records\n"
        else:
            report += "\n✓ All records already have UUIDs\n"

        report += "\n" + "═" * 67 + "\n\n"
        report += "STEP 2: INGREDIENT MIGRATION\n"

        migration_stats = results.get('migration_stats', {})
        report += f"\nTotal legacy ingredients: {migration_stats.get('total_legacy', 0)}\n"
        report += f"\nWill create:\n"
        report += f"  • {migration_stats.get('migrated_ingredients', 0)} new generic ingredients\n"
        report += f"  • {migration_stats.get('created_variants', 0)} variants (brand/package)\n"
        report += f"  • {migration_stats.get('created_pantry_items', 0)} pantry items (inventory)\n"
        report += f"  • {migration_stats.get('created_conversions', 0)} unit conversions\n"
        report += f"  • {migration_stats.get('created_purchases', 0)} purchase records\n"

        if migration_stats.get('errors', 0) > 0:
            report += f"\n⚠️  Errors encountered: {migration_stats['errors']}\n"

        report += "\n" + "═" * 67 + "\n\n"
        report += "STEP 3: RECIPE UPDATES\n"

        recipe_updates = results.get('recipe_updates', 0)
        report += f"\nWill update {recipe_updates} recipe ingredient references\n"

        report += "\n" + "═" * 67 + "\n\n"
        report += "SUMMARY\n\n"

        if migration_stats.get('errors', 0) > 0:
            report += "⚠️  DRY RUN COMPLETED WITH ERRORS\n\n"
            report += "Please review the errors above before proceeding.\n"
        else:
            report += "✓ DRY RUN COMPLETED SUCCESSFULLY\n\n"
            report += "The migration appears ready to execute.\n\n"
            report += "⚠️  IMPORTANT: Backup your database before executing!\n\n"
            report += "Click 'Execute Migration' to proceed with the actual migration.\n"

        self.content_text.insert("1.0", report)
        self.content_text.configure(state="disabled")

        # Update button states
        self.dry_run_btn.configure(state="normal", text="Run Dry Run")
        if migration_stats.get('errors', 0) == 0:
            self.execute_btn.configure(state="normal")

    def _execute_migration(self):
        """Execute actual migration after confirmation."""
        # Confirmation dialog
        confirm_msg = "⚠️  FINAL WARNING ⚠️\n\n"
        confirm_msg += "This will MODIFY YOUR DATABASE.\n\n"
        confirm_msg += "Have you backed up your database file (baking_tracker.db)?\n\n"
        confirm_msg += "Proceed with migration?"

        result = messagebox.askyesno(
            "Confirm Migration",
            confirm_msg,
            parent=self,
            icon="warning",
        )

        if not result:
            return

        # Disable buttons during migration
        self.dry_run_btn.configure(state="disabled")
        self.execute_btn.configure(state="disabled")
        self.back_btn.configure(state="disabled")
        self.close_btn.configure(state="disabled")

        self.migration_running = True

        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", "Executing migration...\n\nPlease wait, do not close this window...\n")
        self.content_text.configure(state="disabled")

        # Run in thread
        thread = threading.Thread(target=self._execute_migration_thread)
        thread.daemon = True
        thread.start()

    def _execute_migration_thread(self):
        """Execute migration in background thread."""
        try:
            results = {}

            with session_scope() as session:
                # Step 1: Populate UUIDs (LIVE)
                uuid_counts = populate_uuids(session, dry_run=False)
                results['uuid_counts'] = uuid_counts
                self.after(0, self._update_progress, "UUIDs populated")

                # Step 2: Migrate ingredients (LIVE)
                migration_stats = migrate_all_ingredients(session, dry_run=False)
                results['migration_stats'] = migration_stats
                self.after(0, self._update_progress, "Ingredients migrated")

                # Step 3: Update recipe references (LIVE)
                updated_count = update_recipe_ingredient_references(session, dry_run=False)
                results['recipe_updates'] = updated_count
                self.after(0, self._update_progress, "Recipe references updated")

            # Update UI on main thread
            self.after(0, self._display_migration_results, results)

        except Exception as e:
            error_msg = f"Migration failed: {str(e)}\n\n"
            error_msg += "⚠️  THE DATABASE MAY BE IN AN INCONSISTENT STATE!\n\n"
            error_msg += "Please restore from your backup."
            self.after(0, self._display_error, error_msg, critical=True)

    def _update_progress(self, message: str):
        """Update progress message."""
        self.content_text.configure(state="normal")
        self.content_text.insert("end", f"\n✓ {message}")
        self.content_text.see("end")
        self.content_text.configure(state="disabled")

    def _display_migration_results(self, results: Dict):
        """Display migration results."""
        self.migration_running = False
        self.migration_executed = True

        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")

        report = """
MIGRATION COMPLETE!
═══════════════════════════════════════════════════════════════════

✓ The migration has been executed successfully.
✓ Your database has been updated to v0.4.0 architecture.

═══════════════════════════════════════════════════════════════════

RESULTS:

STEP 1: UUID POPULATION
"""

        uuid_counts = results.get('uuid_counts', {})
        total_uuids = sum(uuid_counts.values())
        if total_uuids > 0:
            report += f"\nPopulated UUIDs for {total_uuids} records:\n"
            for model, count in uuid_counts.items():
                if count > 0:
                    report += f"  • {model}: {count} records\n"
        else:
            report += "\n✓ All records already had UUIDs\n"

        report += "\n" + "═" * 67 + "\n\n"
        report += "STEP 2: INGREDIENT MIGRATION\n"

        migration_stats = results.get('migration_stats', {})
        report += f"\nTotal legacy ingredients: {migration_stats.get('total_legacy', 0)}\n"
        report += f"\nCreated:\n"
        report += f"  • {migration_stats.get('migrated_ingredients', 0)} new generic ingredients\n"
        report += f"  • {migration_stats.get('created_variants', 0)} variants (brand/package)\n"
        report += f"  • {migration_stats.get('created_pantry_items', 0)} pantry items (inventory)\n"
        report += f"  • {migration_stats.get('created_conversions', 0)} unit conversions\n"
        report += f"  • {migration_stats.get('created_purchases', 0)} purchase records\n"

        report += "\n" + "═" * 67 + "\n\n"
        report += "STEP 3: RECIPE UPDATES\n"

        recipe_updates = results.get('recipe_updates', 0)
        report += f"\nUpdated {recipe_updates} recipe ingredient references\n"

        report += "\n" + "═" * 67 + "\n\n"
        report += "NEXT STEPS:\n\n"
        report += "1. Close this wizard\n"
        report += "2. Navigate to the 'My Ingredients' tab\n"
        report += "3. Verify your ingredients and variants\n"
        report += "4. Check the 'My Pantry' tab for your inventory\n"
        report += "5. Review your recipes to ensure ingredient references are correct\n"
        report += "\n"
        report += "Your legacy data has been preserved in the IngredientLegacy table\n"
        report += "for reference and rollback purposes.\n"

        self.content_text.insert("1.0", report)
        self.content_text.configure(state="disabled")

        # Re-enable close button
        self.close_btn.configure(state="normal")

        # Show success message
        messagebox.showinfo(
            "Migration Complete",
            "Migration completed successfully!\n\nYou can now close this wizard and explore the new UI.",
            parent=self,
        )

    def _display_error(self, error_msg: str, critical: bool = False):
        """Display error message."""
        self.migration_running = False
        self.migration_executed = False

        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")

        report = "ERROR\n"
        report += "═" * 67 + "\n\n"

        if critical:
            report += "⚠️  CRITICAL ERROR ⚠️\n\n"

        report += error_msg

        self.content_text.insert("1.0", report)
        self.content_text.configure(state="disabled")

        # Re-enable buttons
        self.dry_run_btn.configure(state="normal", text="Run Dry Run")
        self.back_btn.configure(state="normal")
        self.close_btn.configure(state="normal")

        if not critical:
            self.execute_btn.configure(state="disabled")

        # Show error dialog
        messagebox.showerror(
            "Migration Error",
            error_msg,
            parent=self,
        )
