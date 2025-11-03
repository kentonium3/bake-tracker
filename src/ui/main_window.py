"""
Main application window for the Seasonal Baking Tracker.

Provides the main window with tabbed navigation and menu bar.
"""

import customtkinter as ctk
from tkinter import messagebox

from src.utils.constants import APP_NAME, APP_VERSION
from src.ui.dashboard_tab import DashboardTab
from src.ui.inventory_tab import InventoryTab


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
        self.geometry("1200x800")
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
        """Create the menu bar."""
        # Create menu frame
        menu_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        menu_frame.grid(row=0, column=0, sticky="ew")
        menu_frame.grid_columnconfigure(0, weight=1)

        # File menu button
        file_button = ctk.CTkButton(
            menu_frame,
            text="File",
            width=80,
            command=self._show_file_menu,
        )
        file_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Help menu button
        help_button = ctk.CTkButton(
            menu_frame,
            text="Help",
            width=80,
            command=self._show_help_menu,
        )
        help_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    def _create_tabs(self):
        """Create the tabbed interface."""
        # Create tab view
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # Add tabs
        self.tabview.add("Dashboard")
        self.tabview.add("Inventory")
        self.tabview.add("Recipes")
        self.tabview.add("Bundles")
        self.tabview.add("Packages")
        self.tabview.add("Recipients")
        self.tabview.add("Events")
        self.tabview.add("Reports")

        # Initialize Dashboard tab
        dashboard_frame = self.tabview.tab("Dashboard")
        self.dashboard_tab = DashboardTab(dashboard_frame)

        # Initialize Inventory tab
        inventory_frame = self.tabview.tab("Inventory")
        self.inventory_tab = InventoryTab(inventory_frame)

        # Add placeholders for other tabs
        self._add_placeholder_tab("Recipes", "Phase 1: Available")
        self._add_placeholder_tab("Bundles", "Phase 2: Coming Soon")
        self._add_placeholder_tab("Packages", "Phase 2: Coming Soon")
        self._add_placeholder_tab("Recipients", "Phase 3: Coming Soon")
        self._add_placeholder_tab("Events", "Phase 3: Coming Soon")
        self._add_placeholder_tab("Reports", "Phase 4: Coming Soon")

        # Set default tab
        self.tabview.set("Dashboard")

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

    def _show_file_menu(self):
        """Show the File menu."""
        # Create a simple menu using messagebox for now
        # In a production app, you might use a custom dropdown menu
        result = messagebox.askyesno(
            "Exit",
            "Are you sure you want to exit the application?",
            parent=self,
        )
        if result:
            self.quit()

    def _show_help_menu(self):
        """Show the Help menu."""
        messagebox.showinfo(
            "About",
            f"{APP_NAME}\nVersion {APP_VERSION}\n\n"
            f"A tool for tracking seasonal baking inventory,\n"
            f"recipes, and event planning.",
            parent=self,
        )

    def refresh_dashboard(self):
        """Refresh the dashboard tab with current data."""
        self.dashboard_tab.refresh()

    def refresh_inventory(self):
        """Refresh the inventory tab with current data."""
        self.inventory_tab.refresh()

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
