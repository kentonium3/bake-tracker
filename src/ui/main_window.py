"""
Main application window for the Seasonal Baking Tracker.

Provides the main window with tabbed navigation and menu bar.
"""

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from typing import Optional

from src.utils.constants import APP_NAME, APP_VERSION
from src.ui.dashboard_tab import DashboardTab
from src.ui.ingredients_tab import IngredientsTab
from src.ui.pantry_tab import PantryTab
from src.ui.recipes_tab import RecipesTab
from src.ui.finished_units_tab import FinishedUnitsTab

# BundlesTab removed - Bundle concept eliminated in Feature 006
from src.ui.packages_tab import PackagesTab
from src.ui.recipients_tab import RecipientsTab
from src.ui.events_tab import EventsTab
from src.ui.production_tab import ProductionTab
from src.ui.migration_wizard import MigrationWizardDialog
from src.ui.service_integration import check_service_integration_health


class MainWindow(ctk.CTk):
    """
    Main application window.

    Contains tabbed interface for different features and a menu bar.
    """

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        # Window configuration
        self.title(f"{APP_NAME} - v{APP_VERSION}")
        self.geometry("1400x900")
        self.minsize(1000, 600)

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Menu bar
        self.grid_rowconfigure(1, weight=1)  # Tab view
        self.grid_rowconfigure(2, weight=0)  # Status bar

        # Create menu bar
        self._create_menu_bar()

        # Create tabbed interface
        self._create_tabs()

        # Create status bar
        self._create_status_bar()

        # Set initial status
        self.update_status("Ready")

    def _create_menu_bar(self):
        """Create the native tkinter menu bar."""
        # Create native menu bar (better compatibility than CTk buttons)
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Import Data...", command=self._show_import_dialog)
        file_menu.add_command(label="Export Data...", command=self._show_export_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # Tools menu
        tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        tools_menu.add_command(label="Migration Wizard...", command=self._show_migration_wizard)
        tools_menu.add_command(label="Service Health Check...", command=self._show_service_health_check)
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)

        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

    def _create_tabs(self):
        """Create the tabbed interface."""
        # Create tab view
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # Add tabs (v0.4.0 architecture - Inventory tab removed, replaced with My Ingredients + My Pantry)
        self.tabview.add("Dashboard")
        self.tabview.add("My Ingredients")
        self.tabview.add("My Pantry")
        self.tabview.add("Recipes")
        self.tabview.add("Finished Units")
        # Bundles tab removed - Bundle concept eliminated in Feature 006
        self.tabview.add("Packages")
        self.tabview.add("Recipients")
        self.tabview.add("Events")
        self.tabview.add("Production")
        self.tabview.add("Reports")

        # Initialize Dashboard tab
        dashboard_frame = self.tabview.tab("Dashboard")
        self.dashboard_tab = DashboardTab(dashboard_frame)

        # Initialize My Ingredients tab (v0.4.0 architecture)
        ingredients_frame = self.tabview.tab("My Ingredients")
        self.ingredients_tab = IngredientsTab(ingredients_frame)

        # Initialize My Pantry tab (v0.4.0 architecture)
        pantry_frame = self.tabview.tab("My Pantry")
        self.pantry_tab = PantryTab(pantry_frame)

        # Initialize Recipes tab
        recipes_frame = self.tabview.tab("Recipes")
        self.recipes_tab = RecipesTab(recipes_frame)

        # Initialize Finished Units tab
        finished_units_frame = self.tabview.tab("Finished Units")
        self.finished_units_tab = FinishedUnitsTab(finished_units_frame)

        # Bundles tab removed - Bundle concept eliminated in Feature 006

        # Initialize Packages tab
        packages_frame = self.tabview.tab("Packages")
        self.packages_tab = PackagesTab(packages_frame)

        # Initialize Recipients tab
        recipients_frame = self.tabview.tab("Recipients")
        self.recipients_tab = RecipientsTab(recipients_frame)

        # Initialize Events tab
        events_frame = self.tabview.tab("Events")
        self.events_tab = EventsTab(events_frame)

        # Initialize Production tab (Feature 008)
        production_frame = self.tabview.tab("Production")
        self.production_tab = ProductionTab(production_frame)

        # Add placeholders for future tabs
        self._add_placeholder_tab("Reports", "Phase 4: Coming Soon")

        # Set default tab
        self.tabview.set("Dashboard")

        # Add tab change callback to refresh dashboard when selected
        self.tabview.configure(command=self._on_tab_change)

    def _add_placeholder_tab(self, tab_name: str, message: str):
        """
        Add a placeholder message to a tab.

        Args:
            tab_name: Name of the tab
            message: Placeholder message
        """
        tab_frame = self.tabview.tab(tab_name)
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(0, weight=1)

        label = ctk.CTkLabel(
            tab_frame,
            text=f"{tab_name}\n\n{message}",
            font=ctk.CTkFont(size=20),
        )
        label.grid(row=0, column=0, padx=20, pady=20)

    def _create_status_bar(self):
        """Create the status bar at the bottom."""
        # Status bar frame
        status_frame = ctk.CTkFrame(self, height=30, corner_radius=0)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        # Status label
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Ready",
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

    def update_status(self, message: str):
        """
        Update the status bar message.

        Args:
            message: Status message to display
        """
        self.status_label.configure(text=message)

    def _on_exit(self):
        """Handle application exit."""
        result = messagebox.askyesno(
            "Exit",
            "Are you sure you want to exit the application?",
            parent=self,
        )
        if result:
            self.destroy()

    def _show_import_dialog(self):
        """Show the import data dialog."""
        from src.ui.import_export_dialog import ImportDialog

        dialog = ImportDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            # Import was successful - refresh all tabs
            self._refresh_all_tabs()
            self.update_status("Import completed successfully. Data refreshed.")

    def _show_export_dialog(self):
        """Show the export data dialog."""
        from src.ui.import_export_dialog import ExportDialog

        dialog = ExportDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            self.update_status(f"Export completed successfully.")

    def _show_migration_wizard(self):
        """Show the migration wizard dialog."""
        try:
            wizard = MigrationWizardDialog(self)
            self.wait_window(wizard)
        except Exception as exc:
            messagebox.showerror(
                "Migration Wizard Error",
                f"Unable to open the migration wizard:\n\n{exc}",
                parent=self,
            )
            return

        if getattr(wizard, "migration_executed", False):
            try:
                self.refresh_dashboard()
                self.ingredients_tab.refresh()
                self.pantry_tab.refresh()
                self.update_status("Migration completed successfully. Data refreshed.")
            except Exception as exc:
                messagebox.showwarning(
                    "Refresh Warning",
                    f"Migration completed, but refreshing data failed:\n\n{exc}",
                    parent=self,
                )

    def _show_service_health_check(self):
        """Show service integration health status."""
        try:
            health_data = check_service_integration_health()
            status = health_data["status"]
            stats = health_data["statistics"]
            recommendations = health_data["recommendations"]

            # Build health report
            health_report = []
            health_report.append(f"Service Integration Health: {status.upper()}")
            health_report.append("")
            health_report.append("Statistics:")
            health_report.append(f"  Total Operations: {stats['total_operations']}")
            health_report.append(f"  Success Rate: {stats['success_rate']}%")
            health_report.append(f"  Failure Rate: {stats['failure_rate']}%")
            health_report.append(f"  Average Time: {stats['average_operation_time']}s")

            if recommendations:
                health_report.append("")
                health_report.append("Recommendations:")
                for rec in recommendations:
                    health_report.append(f"  • {rec}")

            if stats["total_operations"] == 0:
                health_report.append("")
                health_report.append("No service operations have been performed yet.")
                health_report.append(
                    "Health check will be more informative after using the application."
                )

            messagebox.showinfo("Service Health Check", "\n".join(health_report), parent=self)

        except Exception as exc:
            messagebox.showerror(
                "Health Check Error", f"Failed to check service health:\n\n{exc}", parent=self
            )

    def _show_about(self):
        """Show the About dialog."""
        messagebox.showinfo(
            "About",
            f"{APP_NAME}\nVersion {APP_VERSION}\n\n"
            f"A tool for tracking seasonal baking inventory,\n"
            f"recipes, and event planning.",
            parent=self,
        )

    def _on_tab_change(self):
        """Handle tab change event - refresh certain tabs when selected."""
        current_tab = self.tabview.get()
        if current_tab == "Dashboard":
            self.dashboard_tab.refresh()
        elif current_tab == "Production":
            self.production_tab.refresh()

    def refresh_dashboard(self):
        """Refresh the dashboard tab with current data."""
        self.dashboard_tab.refresh()

    def refresh_pantry(self):
        """Refresh the pantry tab with current data."""
        self.pantry_tab.refresh()

    def refresh_recipes(self):
        """Refresh the recipes tab with current data."""
        self.recipes_tab.refresh()

    def refresh_finished_units(self):
        """Refresh the finished units tab with current data."""
        self.finished_units_tab.refresh()

    # refresh_bundles removed - Bundle concept eliminated in Feature 006

    def refresh_packages(self):
        """Refresh the packages tab with current data."""
        self.packages_tab.refresh()

    def refresh_recipients(self):
        """Refresh the recipients tab with current data."""
        self.recipients_tab.refresh()

    def refresh_events(self):
        """Refresh the events tab with current data."""
        self.events_tab.refresh()

    def refresh_production(self):
        """Refresh the production tab with current data."""
        self.production_tab.refresh()

    def _refresh_all_tabs(self):
        """Refresh all tabs after data import."""
        self.dashboard_tab.refresh()
        self.ingredients_tab.refresh()
        self.pantry_tab.refresh()
        self.recipes_tab.refresh()
        self.finished_units_tab.refresh()
        self.packages_tab.refresh()
        self.recipients_tab.refresh()
        self.events_tab.refresh()
        self.production_tab.refresh()

    def switch_to_tab(self, tab_name: str):
        """
        Switch to a specific tab.

        Args:
            tab_name: Name of the tab to switch to
        """
        try:
            self.tabview.set(tab_name)
        except Exception:
            pass  # Tab doesn't exist or is disabled

    def navigate_to_ingredient(self, ingredient_slug: str, variant_id: Optional[int] = None):
        """
        Navigate to My Ingredients tab with specific ingredient selected.

        This is a cross-tab navigation helper for Recipe and Events tabs.

        Args:
            ingredient_slug: Slug of ingredient to select
            variant_id: Optional variant ID to highlight
        """
        # Switch to My Ingredients tab
        self.switch_to_tab("My Ingredients")

        # Tell ingredients tab to select the ingredient
        if hasattr(self.ingredients_tab, "select_ingredient"):
            self.ingredients_tab.select_ingredient(ingredient_slug, variant_id)

    def navigate_to_pantry(self, ingredient_slug: Optional[str] = None):
        """
        Navigate to My Pantry tab, optionally filtered by ingredient.

        This is a cross-tab navigation helper for Recipe and Events tabs.

        Args:
            ingredient_slug: Optional ingredient slug to filter by
        """
        # Switch to My Pantry tab
        self.switch_to_tab("My Pantry")

        # Tell pantry tab to filter by ingredient
        if ingredient_slug and hasattr(self.pantry_tab, "filter_by_ingredient"):
            self.pantry_tab.filter_by_ingredient(ingredient_slug)
