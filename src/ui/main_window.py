"""
Main application window for the Seasonal Baking Tracker.

Provides the main window with 5-mode workflow navigation (F038):
- CATALOG: Ingredients, Products, Recipes, Finished Units, Finished Goods, Packages
- PLAN: Events, Planning Workspace
- PURCHASE: Shopping Lists, Purchases, Inventory
- MAKE: Production Runs, Assembly, Packaging, Recipients
- OBSERVE: Dashboard, Event Status, Reports
"""

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Dict

from src.utils.constants import APP_NAME, APP_VERSION
from src.ui.mode_manager import ModeManager
from src.ui.modes.catalog_mode import CatalogMode
from src.ui.modes.observe_mode import ObserveMode
from src.ui.modes.plan_mode import PlanMode
from src.ui.modes.purchase_mode import PurchaseMode
from src.ui.modes.make_mode import MakeMode

from src.ui.service_integration import check_service_integration_health
from src.ui.preferences_dialog import PreferencesDialog
# Feature 051: Removed CatalogImportDialog import - now handled by unified ImportDialog


class MainWindow(ctk.CTk):
    """
    Main application window with 5-mode workflow navigation.

    Implements FR-001 through FR-005:
    - FR-001: 5-mode workflow (CATALOG, PLAN, PURCHASE, MAKE, OBSERVE)
    - FR-002: Visual highlighting of active mode
    - FR-003: Keyboard shortcuts Ctrl+1-5
    - FR-004: Tab state preservation per mode
    - FR-005: OBSERVE as default mode on launch
    """

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        # Window configuration
        self.title(f"{APP_NAME} - v{APP_VERSION}")
        self.geometry("1400x900")
        self.minsize(1000, 600)

        # Initialize mode manager
        self.mode_manager = ModeManager()

        # Tab references for backward compatibility
        self._tab_refs: Dict[str, any] = {}

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Menu bar (handled by tk.Menu)
        self.grid_rowconfigure(1, weight=0)  # Mode bar
        self.grid_rowconfigure(2, weight=1)  # Mode content
        self.grid_rowconfigure(3, weight=0)  # Status bar

        # Create menu bar
        self._create_menu_bar()

        # Create mode bar (FR-001, FR-002)
        self._create_mode_bar()

        # Create mode content area
        self._create_mode_content_area()

        # Create modes with their tabs
        self._create_modes()

        # Create status bar
        self._create_status_bar()

        # Set up keyboard shortcuts (FR-003)
        self._setup_keyboard_shortcuts()

        # Initialize default mode (FR-005)
        self.mode_manager.initialize_default_mode()

        # Set initial status
        self.update_status("Ready")

    def _create_menu_bar(self):
        """Create the native tkinter menu bar."""
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        # File menu
        # Feature 051: Unified import entry point - removed separate Import Catalog and Import View
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Import Data...", command=self._show_import_dialog)
        file_menu.add_command(label="Export Data...", command=self._show_export_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Preferences...", command=self._show_preferences_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # Catalog menu (Feature 052: Hierarchy Admin access)
        catalog_menu = tk.Menu(self.menu_bar, tearoff=0)
        catalog_menu.add_command(
            label="Ingredient Hierarchy...", command=self._open_ingredient_admin
        )
        catalog_menu.add_command(
            label="Material Hierarchy...", command=self._open_material_admin
        )
        self.menu_bar.add_cascade(label="Catalog", menu=catalog_menu)

        # Tools menu
        tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        tools_menu.add_command(label="Manage Suppliers...", command=self._show_manage_suppliers)
        tools_menu.add_separator()
        tools_menu.add_command(label="Service Health Check...", command=self._show_service_health_check)
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)

        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

    def _create_mode_bar(self):
        """Create the horizontal mode bar with 5 mode buttons (FR-001)."""
        self.mode_bar = ctk.CTkFrame(self, height=50)
        self.mode_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 5))

        # Configure grid for equal button distribution
        for i in range(5):
            self.mode_bar.grid_columnconfigure(i, weight=1)

        # Create mode buttons with keyboard shortcut hints
        mode_configs = [
            ("CATALOG", "Ctrl+1"),
            ("PLAN", "Ctrl+2"),
            ("PURCHASE", "Ctrl+3"),
            ("MAKE", "Ctrl+4"),
            ("OBSERVE", "Ctrl+5"),
        ]

        for idx, (mode_name, shortcut) in enumerate(mode_configs):
            btn = ctk.CTkButton(
                self.mode_bar,
                text=f"{mode_name}\n({shortcut})",
                font=ctk.CTkFont(size=12),
                height=40,
                command=lambda m=mode_name: self._switch_mode(m)
            )
            btn.grid(row=0, column=idx, padx=5, pady=5, sticky="ew")
            self.mode_manager.register_mode_button(mode_name, btn)

    def _create_mode_content_area(self):
        """Create the content area where mode frames are displayed."""
        self.mode_content = ctk.CTkFrame(self)
        self.mode_content.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 5))

        # Configure content area to fill available space
        self.mode_content.grid_columnconfigure(0, weight=1)
        self.mode_content.grid_rowconfigure(0, weight=1)

        self.mode_manager.set_content_frame(self.mode_content)

    def _create_modes(self):
        """Create all 5 modes with their tabs."""
        # Create CATALOG mode (6 tabs)
        self._create_catalog_mode()

        # Create PLAN mode (2 tabs)
        self._create_plan_mode()

        # Create PURCHASE mode (3 tabs)
        self._create_purchase_mode()

        # Create MAKE mode (4 tabs)
        self._create_make_mode()

        # Create OBSERVE mode (3 tabs)
        self._create_observe_mode()

    def _create_catalog_mode(self):
        """Create CATALOG mode with 6 tabs using CatalogMode class."""
        mode = CatalogMode(self.mode_content)

        # Store tab references for backward compatibility
        self.ingredients_tab = mode.ingredients_tab
        self.products_tab = mode.products_tab
        self.recipes_tab = mode.recipes_tab
        self.finished_units_tab = mode.finished_units_tab
        self.packages_tab = mode.packages_tab
        self.materials_tab = mode.materials_tab  # Feature 052: Added for admin refresh

        self._tab_refs["ingredients"] = self.ingredients_tab
        self._tab_refs["products"] = self.products_tab
        self._tab_refs["recipes"] = self.recipes_tab
        self._tab_refs["finished_units"] = self.finished_units_tab
        self._tab_refs["packages"] = self.packages_tab
        self._tab_refs["materials"] = self.materials_tab  # Feature 052

        self.mode_manager.register_mode("CATALOG", mode)

    def _create_plan_mode(self):
        """Create PLAN mode with 2 tabs using PlanMode class."""
        mode = PlanMode(self.mode_content)

        # Store tab references for backward compatibility
        self.events_tab = mode.events_tab

        self._tab_refs["events"] = self.events_tab

        self.mode_manager.register_mode("PLAN", mode)

    def _create_purchase_mode(self):
        """Create PURCHASE mode with 3 tabs using PurchaseMode class."""
        mode = PurchaseMode(self.mode_content)

        # Store tab references for backward compatibility
        self.inventory_tab = mode.inventory_tab

        self._tab_refs["inventory"] = self.inventory_tab

        self.mode_manager.register_mode("PURCHASE", mode)

    def _create_make_mode(self):
        """Create MAKE mode with 4 tabs using MakeMode class."""
        mode = MakeMode(self.mode_content)

        # Store tab references for backward compatibility
        self.production_tab = mode.production_tab
        self.recipients_tab = mode.recipients_tab

        self._tab_refs["production"] = self.production_tab
        self._tab_refs["recipients"] = self.recipients_tab

        self.mode_manager.register_mode("MAKE", mode)

    def _create_observe_mode(self):
        """Create OBSERVE mode with 3 tabs using ObserveMode class (FR-005 default)."""
        mode = ObserveMode(self.mode_content)

        # Store tab references for backward compatibility
        self.dashboard_tab = mode.dashboard_tab

        self._tab_refs["dashboard"] = self.dashboard_tab

        self.mode_manager.register_mode("OBSERVE", mode)

    def _create_status_bar(self):
        """Create the status bar at the bottom."""
        status_frame = ctk.CTkFrame(self, height=30, corner_radius=0)
        status_frame.grid(row=3, column=0, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Ready",
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

    def _setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts for mode switching (FR-003)."""
        self.bind_all("<Control-Key-1>", lambda e: self._switch_mode("CATALOG"))
        self.bind_all("<Control-Key-2>", lambda e: self._switch_mode("PLAN"))
        self.bind_all("<Control-Key-3>", lambda e: self._switch_mode("PURCHASE"))
        self.bind_all("<Control-Key-4>", lambda e: self._switch_mode("MAKE"))
        self.bind_all("<Control-Key-5>", lambda e: self._switch_mode("OBSERVE"))

    def _switch_mode(self, mode_name: str):
        """Switch to a mode.

        Args:
            mode_name: Name of mode to switch to
        """
        self.mode_manager.switch_mode(mode_name)
        self.update_status(f"Mode: {mode_name}")

    def update_status(self, message: str):
        """Update the status bar message.

        Args:
            message: Status message to display
        """
        self.status_label.configure(text=message)

    # =========================================================================
    # Menu Actions (preserved from original implementation)
    # =========================================================================

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
            self._refresh_all_tabs()
            self.update_status("Import completed successfully. Data refreshed.")

    def _show_export_dialog(self):
        """Show the export data dialog."""
        from src.ui.import_export_dialog import ExportDialog

        dialog = ExportDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            self.update_status("Export completed successfully.")

    def _show_preferences_dialog(self):
        """Show the preferences dialog."""
        dialog = PreferencesDialog(self)
        self.wait_window(dialog)

    def _open_ingredient_admin(self):
        """Open Ingredient Hierarchy Admin window (Feature 052)."""
        from src.ui.hierarchy_admin_window import HierarchyAdminWindow

        # Prevent multiple windows
        if (
            hasattr(self, "_ingredient_admin_window")
            and self._ingredient_admin_window is not None
            and self._ingredient_admin_window.winfo_exists()
        ):
            self._ingredient_admin_window.focus()
            self._ingredient_admin_window.lift()
            return

        def on_close():
            """Handle admin window close."""
            self._ingredient_admin_window = None
            # Refresh ingredients tab if it exists
            if hasattr(self, "ingredients_tab") and self.ingredients_tab:
                self.ingredients_tab.refresh()

        self._ingredient_admin_window = HierarchyAdminWindow(
            self, entity_type="ingredient", on_close=on_close
        )

    def _open_material_admin(self):
        """Open Material Hierarchy Admin window (Feature 052)."""
        from src.ui.hierarchy_admin_window import HierarchyAdminWindow

        # Prevent multiple windows
        if (
            hasattr(self, "_material_admin_window")
            and self._material_admin_window is not None
            and self._material_admin_window.winfo_exists()
        ):
            self._material_admin_window.focus()
            self._material_admin_window.lift()
            return

        def on_close():
            """Handle admin window close."""
            self._material_admin_window = None
            # Refresh materials tab if it exists
            if hasattr(self, "materials_tab") and self.materials_tab:
                self.materials_tab.refresh()

        self._material_admin_window = HierarchyAdminWindow(
            self, entity_type="material", on_close=on_close
        )

    # Feature 051: Removed _show_catalog_import_dialog and _show_import_view_dialog
    # These are now handled by the unified ImportDialog via File > Import Data

    def _show_manage_suppliers(self):
        """Show the manage suppliers dialog."""
        from src.ui.forms.manage_suppliers_dialog import ManageSuppliersDialog

        dialog = ManageSuppliersDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            self.products_tab.refresh()
            self.inventory_tab.refresh()
            self.update_status("Supplier data updated.")

    def _show_service_health_check(self):
        """Show service integration health status."""
        try:
            health_data = check_service_integration_health()
            status = health_data["status"]
            stats = health_data["statistics"]
            recommendations = health_data["recommendations"]

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
                    health_report.append(f"  - {rec}")

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
            f"recipes, and event planning.\n\n"
            f"Modes: CATALOG | PLAN | PURCHASE | MAKE | OBSERVE",
            parent=self,
        )

    # =========================================================================
    # Refresh Methods (preserved for backward compatibility)
    # =========================================================================

    def _refresh_catalog_tabs(self):
        """Refresh tabs that may have been affected by catalog import."""
        self.ingredients_tab.refresh()
        self.products_tab.refresh()
        self.recipes_tab.refresh()
        self.inventory_tab.refresh()

    def _refresh_all_tabs(self):
        """Refresh all tabs after data import."""
        self.dashboard_tab.refresh()
        self.ingredients_tab.refresh()
        self.inventory_tab.refresh()
        self.products_tab.refresh()
        self.recipes_tab.refresh()
        self.finished_units_tab.refresh()
        self.packages_tab.refresh()
        self.recipients_tab.refresh()
        self.events_tab.refresh()
        self.production_tab.refresh()

    def refresh_dashboard(self):
        """Refresh the dashboard tab."""
        self.dashboard_tab.refresh()

    def refresh_inventory(self):
        """Refresh the inventory tab."""
        self.inventory_tab.refresh()

    def refresh_products(self):
        """Refresh the products tab."""
        self.products_tab.refresh()

    def refresh_recipes(self):
        """Refresh the recipes tab."""
        self.recipes_tab.refresh()

    def refresh_finished_units(self):
        """Refresh the finished units tab."""
        self.finished_units_tab.refresh()

    def refresh_packages(self):
        """Refresh the packages tab."""
        self.packages_tab.refresh()

    def refresh_recipients(self):
        """Refresh the recipients tab."""
        self.recipients_tab.refresh()

    def refresh_events(self):
        """Refresh the events tab."""
        self.events_tab.refresh()

    def refresh_production(self):
        """Refresh the production tab."""
        self.production_tab.refresh()

    # =========================================================================
    # Navigation Methods (preserved/updated for mode architecture)
    # =========================================================================

    def switch_to_mode(self, mode_name: str):
        """Switch to a specific mode.

        Args:
            mode_name: Name of the mode to switch to (CATALOG, PLAN, PURCHASE, MAKE, OBSERVE)
        """
        self._switch_mode(mode_name)

    def switch_to_tab(self, tab_name: str):
        """Switch to a specific tab within the current mode.

        Note: For backward compatibility. Consider using switch_to_mode() for new code.

        Args:
            tab_name: Name of the tab to switch to
        """
        current_mode = self.mode_manager.get_current_mode()
        if current_mode and current_mode.tabview:
            try:
                current_mode.tabview.set(tab_name)
            except Exception:
                pass  # Tab doesn't exist in current mode

    def navigate_to_ingredient(self, ingredient_slug: str):
        """Navigate to Ingredients tab with specific ingredient selected.

        Args:
            ingredient_slug: Slug of ingredient to select
        """
        self._switch_mode("CATALOG")
        catalog_mode = self.mode_manager.get_mode("CATALOG")
        if catalog_mode and catalog_mode.tabview:
            catalog_mode.tabview.set("Ingredients")

        if hasattr(self.ingredients_tab, "select_ingredient"):
            self.ingredients_tab.select_ingredient(ingredient_slug)

    def navigate_to_inventory(self, ingredient_slug: Optional[str] = None):
        """Navigate to Inventory tab, optionally filtered by ingredient.

        Args:
            ingredient_slug: Optional ingredient slug to filter by
        """
        self._switch_mode("PURCHASE")
        purchase_mode = self.mode_manager.get_mode("PURCHASE")
        if purchase_mode and purchase_mode.tabview:
            purchase_mode.tabview.set("Inventory")

        if ingredient_slug and hasattr(self.inventory_tab, "filter_by_ingredient"):
            self.inventory_tab.filter_by_ingredient(ingredient_slug)
