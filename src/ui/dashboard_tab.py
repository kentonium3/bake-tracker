"""
Dashboard tab for the Seasonal Baking Tracker.

Displays welcome message, quick stats, and phase information.
"""

import customtkinter as ctk

from src.services import inventory_service, recipe_service, finished_good_service
from src.utils.constants import APP_NAME


class DashboardTab(ctk.CTkFrame):
    """
    Dashboard tab showing application overview and quick stats.
    """

    def __init__(self, parent):
        """
        Initialize the dashboard tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=0)  # Stats
        self.grid_rowconfigure(2, weight=1)  # Phase info

        # Create header
        self._create_header()

        # Create stats section
        self._create_stats()

        # Create phase info section
        self._create_phase_info()

        # Pack the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _create_header(self):
        """Create the header section."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        # Welcome message
        welcome_label = ctk.CTkLabel(
            header_frame,
            text=f"Welcome to {APP_NAME}",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        welcome_label.grid(row=0, column=0, sticky="w")

        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Track inventory, manage recipes, and plan baking events",
            font=ctk.CTkFont(size=14),
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

    def _create_stats(self):
        """Create the quick stats section."""
        stats_frame = ctk.CTkFrame(self)
        stats_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Stats title
        stats_title = ctk.CTkLabel(
            stats_frame,
            text="Quick Stats",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        stats_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(15, 10))

        # Get stats
        ingredient_count = self._get_ingredient_count()
        recipe_count = self._get_recipe_count()
        inventory_value = self._get_inventory_value()
        finished_good_count = self._get_finished_good_count()
        bundle_count = self._get_bundle_count()

        # Row 1: Ingredients, Recipes, Inventory Value
        # Ingredient count card
        self._create_stat_card(
            stats_frame,
            "Ingredients",
            str(ingredient_count),
            "items in inventory",
            row=1,
            column=0,
        )

        # Recipe count card
        self._create_stat_card(
            stats_frame,
            "Recipes",
            str(recipe_count),
            "recipes available",
            row=1,
            column=1,
        )

        # Inventory value card
        self._create_stat_card(
            stats_frame,
            "Inventory Value",
            f"${inventory_value:.2f}",
            "total value",
            row=1,
            column=2,
        )

        # Row 2: Finished Goods, Bundles (centered across 3 columns)
        # Finished Goods count card
        self._create_stat_card(
            stats_frame,
            "Finished Goods",
            str(finished_good_count),
            "products defined",
            row=2,
            column=0,
        )

        # Bundle count card
        self._create_stat_card(
            stats_frame,
            "Bundles",
            str(bundle_count),
            "bundles configured",
            row=2,
            column=1,
        )

    def _create_stat_card(
        self,
        parent,
        title: str,
        value: str,
        subtitle: str,
        row: int,
        column: int,
    ):
        """
        Create a stat card widget.

        Args:
            parent: Parent widget
            title: Card title
            value: Main value to display
            subtitle: Subtitle text
            row: Grid row
            column: Grid column
        """
        card_frame = ctk.CTkFrame(parent)
        card_frame.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")
        card_frame.grid_columnconfigure(0, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            card_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        title_label.grid(row=0, column=0, padx=15, pady=(15, 5))

        # Value
        value_label = ctk.CTkLabel(
            card_frame,
            text=value,
            font=ctk.CTkFont(size=32, weight="bold"),
        )
        value_label.grid(row=1, column=0, padx=15, pady=5)

        # Subtitle
        subtitle_label = ctk.CTkLabel(
            card_frame,
            text=subtitle,
            font=ctk.CTkFont(size=12),
        )
        subtitle_label.grid(row=2, column=0, padx=15, pady=(5, 15))

    def _create_phase_info(self):
        """Create the phase information section."""
        phase_frame = ctk.CTkFrame(self)
        phase_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        phase_frame.grid_columnconfigure(0, weight=1)

        # Phase title
        phase_title = ctk.CTkLabel(
            phase_frame,
            text="Phase 2: Finished Goods & Bundles",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        phase_title.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))

        # Phase description
        phase_desc = ctk.CTkLabel(
            phase_frame,
            text=(
                "Define finished goods from recipes and create bundles for planning.\n"
                "Support both discrete items (cookies) and batch portions (cakes)."
            ),
            font=ctk.CTkFont(size=14),
            justify="left",
        )
        phase_desc.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 10))

        # Features list
        features_label = ctk.CTkLabel(
            phase_frame,
            text="Available Features:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        features_label.grid(row=2, column=0, sticky="w", padx=15, pady=(10, 5))

        features_text = ctk.CTkLabel(
            phase_frame,
            text=(
                "• Ingredient Management (CRUD operations)\n"
                "• Recipe Management with ingredients\n"
                "• Cost Calculations (ingredient, recipe, and finished good level)\n"
                "• Unit Conversions (weight, volume, count)\n"
                "• Finished Goods (discrete items & batch portions)\n"
                "• Bundles (bags/groups of finished goods)\n"
                "• Batch Planning (calculate batches needed)\n"
                "• Search and Filter capabilities"
            ),
            font=ctk.CTkFont(size=13),
            justify="left",
        )
        features_text.grid(row=3, column=0, sticky="w", padx=30, pady=(0, 15))

        # Coming soon
        coming_label = ctk.CTkLabel(
            phase_frame,
            text="Coming in Future Phases:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        coming_label.grid(row=4, column=0, sticky="w", padx=15, pady=(10, 5))

        coming_text = ctk.CTkLabel(
            phase_frame,
            text=(
                "• Packages (Phase 2 cont.): Complete gift package management\n"
                "• Recipients (Phase 3): Track gift recipients and history\n"
                "• Events (Phase 3): Plan seasonal baking events\n"
                "• Reports (Phase 4): Analytics and export capabilities"
            ),
            font=ctk.CTkFont(size=13),
            justify="left",
        )
        coming_text.grid(row=5, column=0, sticky="w", padx=30, pady=(0, 15))

    def _get_ingredient_count(self) -> int:
        """
        Get the current ingredient count.

        Returns:
            Number of ingredients in inventory
        """
        try:
            return inventory_service.get_ingredient_count()
        except Exception:
            return 0

    def _get_recipe_count(self) -> int:
        """
        Get the current recipe count.

        Returns:
            Number of recipes in system
        """
        try:
            return recipe_service.get_recipe_count()
        except Exception:
            return 0

    def _get_inventory_value(self) -> float:
        """
        Get the total inventory value.

        Returns:
            Total value of all ingredients
        """
        try:
            return inventory_service.get_total_inventory_value()
        except Exception:
            return 0.0

    def _get_finished_good_count(self) -> int:
        """
        Get the current finished good count.

        Returns:
            Number of finished goods in system
        """
        try:
            return finished_good_service.get_finished_good_count()
        except Exception:
            return 0

    def _get_bundle_count(self) -> int:
        """
        Get the current bundle count.

        Returns:
            Number of bundles in system
        """
        try:
            return finished_good_service.get_bundle_count()
        except Exception:
            return 0

    def refresh(self):
        """Refresh the dashboard with current data."""
        # Recreate stats section to update values
        # Clear existing stats
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                widget.destroy()

        # Recreate all sections
        self._create_header()
        self._create_stats()
        self._create_phase_info()
