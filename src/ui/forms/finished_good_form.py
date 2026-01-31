"""
FinishedGood form dialog for creating and editing assembled packages.

This dialog provides a modal form for managing FinishedGood records, which
represent assembled packages containing multiple FinishedUnits and/or other
FinishedGoods (e.g., gift boxes, variety packs, seasonal collections).

Feature 088: Finished Goods Catalog UI - WP04, WP05, WP06
"""

import customtkinter as ctk
from typing import Optional, Dict, List, Callable

from src.models.finished_good import FinishedGood
from src.models.assembly_type import AssemblyType
from src.services import finished_unit_service
from src.services import material_unit_service
from src.services import finished_good_service


class ComponentSelectionPopup(ctk.CTkToplevel):
    """
    Popup dialog for selecting a component with category filter and search.

    Used by FinishedGoodFormDialog to select FinishedUnits to add as
    components of a FinishedGood (gift box, variety pack, etc.).
    """

    def __init__(
        self,
        parent,
        title: str,
        items: List[tuple],  # [(id, display_name, category), ...]
        categories: List[str],
        on_select: Callable[[int, str], None],
    ):
        """
        Initialize the component selection popup.

        Args:
            parent: Parent window
            title: Dialog title
            items: List of tuples (id, display_name, category)
            categories: List of category names for filter dropdown
            on_select: Callback function when item is selected (id, display_name)
        """
        super().__init__(parent)

        self.items = items
        self.categories = categories
        self.on_select = on_select
        self.filtered_items = items.copy()

        # Window configuration
        self.title(title)
        self.geometry("400x500")
        self.resizable(True, True)
        self.minsize(350, 400)

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._center_on_parent(parent)

    def _center_on_parent(self, parent):
        """Center the dialog on its parent window."""
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create all popup widgets."""
        # Filter frame
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=10, pady=10)

        # Category filter
        ctk.CTkLabel(filter_frame, text="Category:").pack(side="left", padx=5)
        self.category_dropdown = ctk.CTkComboBox(
            filter_frame,
            values=["All"] + self.categories,
            command=self._on_filter_changed,
            state="readonly",
            width=120,
        )
        self.category_dropdown.set("All")
        self.category_dropdown.pack(side="left", padx=5)

        # Search entry
        self.search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Search...",
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)

        # Items list
        self.items_frame = ctk.CTkScrollableFrame(self)
        self.items_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self._refresh_items_list()

        # Cancel button
        cancel_btn = ctk.CTkButton(
            self,
            text="Cancel",
            command=self.destroy,
            fg_color="gray",
        )
        cancel_btn.pack(pady=10)

    def _on_filter_changed(self, category: str):
        """Handle category filter change."""
        self._apply_filters()

    def _on_search_changed(self, event):
        """Handle search text change."""
        self._apply_filters()

    def _apply_filters(self):
        """Apply category and search filters to items list."""
        category = self.category_dropdown.get()
        search = self.search_entry.get().lower().strip()

        self.filtered_items = []
        for item_id, display_name, item_category in self.items:
            # Category filter
            if category != "All" and item_category != category:
                continue
            # Search filter
            if search and search not in display_name.lower():
                continue
            self.filtered_items.append((item_id, display_name, item_category))

        self._refresh_items_list()

    def _refresh_items_list(self):
        """Refresh the items list display."""
        # Clear existing items
        for widget in self.items_frame.winfo_children():
            widget.destroy()

        if not self.filtered_items:
            no_items = ctk.CTkLabel(
                self.items_frame,
                text="No items match your search",
                text_color="gray",
            )
            no_items.pack(pady=20)
            return

        for item_id, display_name, category in self.filtered_items:
            item_frame = ctk.CTkFrame(self.items_frame)
            item_frame.pack(fill="x", pady=2)

            # Display name with category in parentheses if available
            label_text = f"{display_name} ({category})" if category else display_name
            label = ctk.CTkLabel(
                item_frame,
                text=label_text,
                anchor="w",
            )
            label.pack(side="left", padx=5, fill="x", expand=True)

            select_btn = ctk.CTkButton(
                item_frame,
                text="Select",
                width=60,
                command=lambda id=item_id, name=display_name: self._select_item(id, name),
            )
            select_btn.pack(side="right", padx=5)

    def _select_item(self, item_id: int, display_name: str):
        """Handle item selection."""
        self.on_select(item_id, display_name)
        self.destroy()


class FinishedGoodFormDialog(ctk.CTkToplevel):
    """
    Modal dialog for creating/editing FinishedGoods.

    Provides form fields for:
    - Name (required)
    - Assembly Type (required, defaults to Custom Order)
    - Packaging Instructions (optional)
    - Notes (optional)

    The dialog returns a result dictionary on save, or None on cancel.
    Component management is handled in WP05/WP06.
    """

    # Mapping from display names to enum values
    _type_to_enum: Dict[str, AssemblyType] = {
        "Custom Order": AssemblyType.CUSTOM_ORDER,
        "Gift Box": AssemblyType.GIFT_BOX,
        "Variety Pack": AssemblyType.VARIETY_PACK,
        "Holiday Set": AssemblyType.HOLIDAY_SET,
        "Bulk Pack": AssemblyType.BULK_PACK,
    }

    # Reverse mapping from enum values to display names
    _enum_to_type: Dict[AssemblyType, str] = {
        AssemblyType.CUSTOM_ORDER: "Custom Order",
        AssemblyType.GIFT_BOX: "Gift Box",
        AssemblyType.VARIETY_PACK: "Variety Pack",
        AssemblyType.HOLIDAY_SET: "Holiday Set",
        AssemblyType.BULK_PACK: "Bulk Pack",
    }

    def __init__(
        self,
        parent,
        finished_good: Optional[FinishedGood] = None,
        title: str = "Create Finished Good",
    ):
        """
        Initialize the FinishedGood form dialog.

        Args:
            parent: Parent window
            finished_good: Existing FinishedGood to edit (None for new)
            title: Dialog title (overridden in edit mode)
        """
        super().__init__(parent)

        self.finished_good = finished_good
        self.result: Optional[Dict] = None

        # Foods components list storage (WP05)
        self._foods_components: List[Dict] = []

        # Materials components list storage (WP06)
        self._materials_components: List[Dict] = []

        # Nested FinishedGoods components list storage (WP06)
        self._nested_components: List[Dict] = []

        # Window configuration
        if finished_good:
            self.title(f"Edit: {finished_good.display_name}")
        else:
            self.title(title)
        self.geometry("600x700")
        self.resizable(True, True)
        self.minsize(500, 500)

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Build UI
        self._create_widgets()
        self._populate_form()

        # Center on parent
        self._center_on_parent(parent)

    def _center_on_parent(self, parent):
        """Center the dialog on its parent window."""
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create all form widgets."""
        # Main container
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Scrollable form area
        self.form_scroll = ctk.CTkScrollableFrame(
            self.main_frame,
            label_text="",
            label_anchor="nw",
        )
        self.form_scroll.pack(fill="both", expand=True, pady=(0, 10))

        # Configure scroll frame grid for consistent widget sizing
        self.form_scroll.grid_columnconfigure(0, weight=0)  # Labels
        self.form_scroll.grid_columnconfigure(1, weight=1)  # Inputs

        # Create form sections
        self._create_basic_info_section()
        self._create_packaging_section()
        self._create_notes_section()
        self._create_foods_section()  # WP05: Foods (FinishedUnits) section
        self._create_materials_section()  # WP06: Materials (MaterialUnits) section
        self._create_components_section()  # WP06: Components (nested FinishedGoods) section

        # Button frame at bottom (not scrollable)
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x", pady=(10, 0))

        # Create buttons
        self._create_buttons()

    def _create_basic_info_section(self):
        """Create the Basic Information section with Name and Assembly Type."""
        # Section header
        header = ctk.CTkLabel(
            self.form_scroll,
            text="Basic Information",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(10, 5))

        # Name label
        name_label = ctk.CTkLabel(self.form_scroll, text="Name *")
        name_label.grid(row=1, column=0, sticky="w", pady=5, padx=(0, 10))

        # Name entry
        self.name_entry = ctk.CTkEntry(
            self.form_scroll,
            placeholder_text="Enter name (e.g., Holiday Gift Box)",
        )
        self.name_entry.grid(row=1, column=1, sticky="ew", pady=5)

        # Assembly Type label
        type_label = ctk.CTkLabel(self.form_scroll, text="Assembly Type *")
        type_label.grid(row=2, column=0, sticky="w", pady=5, padx=(0, 10))

        # Assembly Type dropdown
        type_values = list(self._type_to_enum.keys())
        self.type_dropdown = ctk.CTkComboBox(
            self.form_scroll,
            values=type_values,
            state="readonly",
        )
        self.type_dropdown.set("Custom Order")  # Default
        self.type_dropdown.grid(row=2, column=1, sticky="ew", pady=5)

    def _create_packaging_section(self):
        """Create the Packaging Instructions section."""
        # Section header
        header = ctk.CTkLabel(
            self.form_scroll,
            text="Packaging Instructions",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        header.grid(row=3, column=0, columnspan=2, sticky="w", pady=(15, 5))

        # Textarea
        self.packaging_text = ctk.CTkTextbox(
            self.form_scroll,
            height=100,
            wrap="word",
        )
        self.packaging_text.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

    def _create_notes_section(self):
        """Create the Notes section."""
        # Section header
        header = ctk.CTkLabel(
            self.form_scroll,
            text="Notes",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        header.grid(row=5, column=0, columnspan=2, sticky="w", pady=(15, 5))

        # Textarea
        self.notes_text = ctk.CTkTextbox(
            self.form_scroll,
            height=80,
            wrap="word",
        )
        self.notes_text.grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)

    def _create_foods_section(self):
        """Create the Foods (FinishedUnits) section (WP05)."""
        # Section header with Add button
        self.foods_header_frame = ctk.CTkFrame(
            self.form_scroll,
            fg_color="transparent",
        )
        self.foods_header_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(15, 5))

        foods_label = ctk.CTkLabel(
            self.foods_header_frame,
            text="Foods (Finished Units)",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        foods_label.pack(side="left")

        self.add_food_btn = ctk.CTkButton(
            self.foods_header_frame,
            text="+ Add Food",
            width=100,
            command=self._on_add_food,
        )
        self.add_food_btn.pack(side="right")

        # Foods list container
        self.foods_list_frame = ctk.CTkScrollableFrame(
            self.form_scroll,
            height=150,
        )
        self.foods_list_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=5)

        # Initial display
        self._refresh_foods_list()

    def _get_food_categories(self) -> List[str]:
        """Get unique categories from FinishedUnits."""
        units = finished_unit_service.get_all_finished_units()
        categories = set()
        for unit in units:
            if unit.category:
                categories.add(unit.category)
        return sorted(list(categories))

    def _on_add_food(self):
        """Open food selection popup (WP05: T032)."""
        units = finished_unit_service.get_all_finished_units()

        # Build items list: (id, display_name, category)
        items = [(u.id, u.display_name, u.category or "") for u in units]
        categories = self._get_food_categories()

        ComponentSelectionPopup(
            self,
            title="Select Food",
            items=items,
            categories=categories,
            on_select=self._show_quantity_dialog,
        )

    def _show_quantity_dialog(self, item_id: int, display_name: str):
        """Show quantity input dialog after selecting food (WP05: T032)."""
        dialog = ctk.CTkInputDialog(
            text=f"Quantity for {display_name}:",
            title="Enter Quantity",
        )
        quantity_str = dialog.get_input()

        if quantity_str:
            try:
                quantity = int(quantity_str)
                if quantity <= 0:
                    raise ValueError("Must be positive")
                self._add_food_component(item_id, display_name, quantity)
            except ValueError:
                # Invalid input - silently ignore
                pass

    def _add_food_component(self, food_id: int, display_name: str, quantity: int):
        """Add a food component and update display (WP05: T033)."""
        # Check for duplicates - if found, add to quantity
        for comp in self._foods_components:
            if comp["id"] == food_id:
                # Update quantity instead of adding duplicate
                comp["quantity"] += quantity
                self._refresh_foods_list()
                return

        # Add new component
        self._foods_components.append({
            "type": "finished_unit",
            "id": food_id,
            "quantity": quantity,
            "display_name": display_name,
            "sort_order": len(self._foods_components),
        })
        self._refresh_foods_list()

    def _refresh_foods_list(self):
        """Refresh the foods list display (WP05: T033)."""
        # Clear existing
        for widget in self.foods_list_frame.winfo_children():
            widget.destroy()

        if not self._foods_components:
            empty_label = ctk.CTkLabel(
                self.foods_list_frame,
                text="No foods added yet",
                text_color="gray",
            )
            empty_label.pack(pady=10)
            return

        for i, comp in enumerate(self._foods_components):
            row_frame = ctk.CTkFrame(self.foods_list_frame)
            row_frame.pack(fill="x", pady=2)

            # Name and quantity
            name_label = ctk.CTkLabel(
                row_frame,
                text=f"{comp['display_name']} x {comp['quantity']}",
                anchor="w",
            )
            name_label.pack(side="left", padx=5, fill="x", expand=True)

            # Remove button (WP05: T034)
            remove_btn = ctk.CTkButton(
                row_frame,
                text="Remove",
                width=70,
                fg_color="red",
                hover_color="darkred",
                command=lambda idx=i: self._remove_food_component(idx),
            )
            remove_btn.pack(side="right", padx=5)

    def _remove_food_component(self, index: int):
        """Remove a food component by index (WP05: T034)."""
        if 0 <= index < len(self._foods_components):
            del self._foods_components[index]
            # Update sort_order for remaining items
            for i, comp in enumerate(self._foods_components):
                comp["sort_order"] = i
            self._refresh_foods_list()

    # ==========================================================================
    # WP06: Materials (MaterialUnits) Section
    # ==========================================================================

    def _create_materials_section(self):
        """Create the Materials (MaterialUnits) section (WP06: T035)."""
        # Section header with Add button
        self.materials_header_frame = ctk.CTkFrame(
            self.form_scroll,
            fg_color="transparent",
        )
        self.materials_header_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(15, 5))

        materials_label = ctk.CTkLabel(
            self.materials_header_frame,
            text="Materials",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        materials_label.pack(side="left")

        self.add_material_btn = ctk.CTkButton(
            self.materials_header_frame,
            text="+ Add Material",
            width=120,
            command=self._on_add_material,
        )
        self.add_material_btn.pack(side="right")

        # Materials list container
        self.materials_list_frame = ctk.CTkScrollableFrame(
            self.form_scroll,
            height=120,
        )
        self.materials_list_frame.grid(row=10, column=0, columnspan=2, sticky="ew", pady=5)

        # Initial display
        self._refresh_materials_list()

    def _get_material_categories(self) -> List[str]:
        """Get unique categories from MaterialUnits (WP06: T036)."""
        units = material_unit_service.list_units(include_relationships=True)
        categories = set()
        for unit in units:
            if unit.material_product and unit.material_product.material:
                material = unit.material_product.material
                if material.subcategory and material.subcategory.category:
                    categories.add(material.subcategory.category.name)
        return sorted(list(categories))

    def _on_add_material(self):
        """Open material selection popup (WP06: T036)."""
        units = material_unit_service.list_units(include_relationships=True)

        # Build items list: (id, display_name, category)
        items = []
        for u in units:
            product_name = u.material_product.name if u.material_product else ""
            display = f"{u.name} ({product_name})" if product_name else u.name
            # Get category from material hierarchy
            category = ""
            if u.material_product and u.material_product.material:
                material = u.material_product.material
                if material.subcategory and material.subcategory.category:
                    category = material.subcategory.category.name
            items.append((u.id, display, category))

        categories = self._get_material_categories()

        ComponentSelectionPopup(
            self,
            title="Select Material",
            items=items,
            categories=categories,
            on_select=self._show_material_quantity_dialog,
        )

    def _show_material_quantity_dialog(self, item_id: int, display_name: str):
        """Show quantity input dialog for material (accepts decimals) (WP06: T038)."""
        dialog = ctk.CTkInputDialog(
            text=f"Quantity for {display_name}:",
            title="Enter Quantity",
        )
        quantity_str = dialog.get_input()

        if quantity_str:
            try:
                quantity = float(quantity_str)
                if quantity <= 0:
                    raise ValueError("Must be positive")
                self._add_material_component(item_id, display_name, quantity)
            except ValueError:
                # Invalid input - silently ignore
                pass

    def _add_material_component(self, material_id: int, display_name: str, quantity: float):
        """Add a material component and update display (WP06: T038)."""
        # Check for duplicates - if found, add to quantity
        for comp in self._materials_components:
            if comp["id"] == material_id:
                # Update quantity instead of adding duplicate
                comp["quantity"] += quantity
                self._refresh_materials_list()
                return

        # Add new component
        self._materials_components.append({
            "type": "material_unit",
            "id": material_id,
            "quantity": quantity,
            "display_name": display_name,
            "sort_order": len(self._materials_components),
        })
        self._refresh_materials_list()

    def _refresh_materials_list(self):
        """Refresh the materials list display (WP06: T039)."""
        # Clear existing
        for widget in self.materials_list_frame.winfo_children():
            widget.destroy()

        if not self._materials_components:
            empty_label = ctk.CTkLabel(
                self.materials_list_frame,
                text="No materials added yet",
                text_color="gray",
            )
            empty_label.pack(pady=10)
            return

        for i, comp in enumerate(self._materials_components):
            row_frame = ctk.CTkFrame(self.materials_list_frame)
            row_frame.pack(fill="x", pady=2)

            # Format quantity nicely (show decimal only if needed)
            qty = comp["quantity"]
            qty_str = f"{qty:.1f}" if qty % 1 else str(int(qty))

            # Name and quantity
            name_label = ctk.CTkLabel(
                row_frame,
                text=f"{comp['display_name']} x {qty_str}",
                anchor="w",
            )
            name_label.pack(side="left", padx=5, fill="x", expand=True)

            # Remove button
            remove_btn = ctk.CTkButton(
                row_frame,
                text="Remove",
                width=70,
                fg_color="red",
                hover_color="darkred",
                command=lambda idx=i: self._remove_material_component(idx),
            )
            remove_btn.pack(side="right", padx=5)

    def _remove_material_component(self, index: int):
        """Remove a material component by index (WP06: T039)."""
        if 0 <= index < len(self._materials_components):
            del self._materials_components[index]
            # Update sort_order for remaining items
            for i, comp in enumerate(self._materials_components):
                comp["sort_order"] = i
            self._refresh_materials_list()

    # ==========================================================================
    # WP06: Components (Nested FinishedGoods) Section
    # ==========================================================================

    def _create_components_section(self):
        """Create the Components (nested FinishedGoods) section (WP06: T040)."""
        # Section header with Add button
        self.components_header_frame = ctk.CTkFrame(
            self.form_scroll,
            fg_color="transparent",
        )
        self.components_header_frame.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(15, 5))

        components_label = ctk.CTkLabel(
            self.components_header_frame,
            text="Components (Finished Goods)",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        components_label.pack(side="left")

        self.add_component_btn = ctk.CTkButton(
            self.components_header_frame,
            text="+ Add Component",
            width=130,
            command=self._on_add_component,
        )
        self.add_component_btn.pack(side="right")

        # Components list container
        self.components_list_frame = ctk.CTkScrollableFrame(
            self.form_scroll,
            height=120,
        )
        self.components_list_frame.grid(row=12, column=0, columnspan=2, sticky="ew", pady=5)

        # Initial display
        self._refresh_components_list()

    def _get_assembly_type_options(self) -> List[str]:
        """Get assembly type options for filtering (WP06: T041)."""
        return list(self._type_to_enum.keys())

    def _on_add_component(self):
        """Open component selection popup (WP06: T041)."""
        goods = finished_good_service.get_all_finished_goods()

        # Filter out self if editing (can't add self as component)
        current_id = self.finished_good.id if self.finished_good else None

        # Build items list, filtering out invalid options
        items = []
        for fg in goods:
            if fg.id == current_id:
                continue  # Can't add self as component

            # Check for circular reference in edit mode (WP06: T042)
            if current_id is not None:
                if not finished_good_service.FinishedGoodService.validate_no_circular_references(
                    current_id, fg.id
                ):
                    continue  # Skip items that would create circular reference

            type_display = self._enum_to_type.get(fg.assembly_type, "Custom Order")
            items.append((fg.id, fg.display_name, type_display))

        assembly_types = self._get_assembly_type_options()

        ComponentSelectionPopup(
            self,
            title="Select Component",
            items=items,
            categories=assembly_types,
            on_select=self._on_component_selected,
        )

    def _on_component_selected(self, item_id: int, display_name: str):
        """Handle component selection (WP06: T042)."""
        # In create mode, no additional validation needed (already filtered in popup)
        # In edit mode, validation was done during popup item filtering
        # Show quantity dialog
        self._show_component_quantity_dialog(item_id, display_name)

    def _show_component_quantity_dialog(self, item_id: int, display_name: str):
        """Show quantity input dialog for component (WP06: T042)."""
        dialog = ctk.CTkInputDialog(
            text=f"Quantity for {display_name}:",
            title="Enter Quantity",
        )
        quantity_str = dialog.get_input()

        if quantity_str:
            try:
                quantity = int(quantity_str)
                if quantity <= 0:
                    raise ValueError("Must be positive")
                self._add_nested_component(item_id, display_name, quantity)
            except ValueError:
                # Invalid input - silently ignore
                pass

    def _add_nested_component(self, component_id: int, display_name: str, quantity: int):
        """Add a nested FinishedGood component (WP06: T042)."""
        # Check for duplicates - if found, add to quantity
        for comp in self._nested_components:
            if comp["id"] == component_id:
                # Update quantity instead of adding duplicate
                comp["quantity"] += quantity
                self._refresh_components_list()
                return

        # Add new component
        self._nested_components.append({
            "type": "finished_good",
            "id": component_id,
            "quantity": quantity,
            "display_name": display_name,
            "sort_order": len(self._nested_components),
        })
        self._refresh_components_list()

    def _refresh_components_list(self):
        """Refresh the components list display (WP06: T042)."""
        # Clear existing
        for widget in self.components_list_frame.winfo_children():
            widget.destroy()

        if not self._nested_components:
            empty_label = ctk.CTkLabel(
                self.components_list_frame,
                text="No components added yet",
                text_color="gray",
            )
            empty_label.pack(pady=10)
            return

        for i, comp in enumerate(self._nested_components):
            row_frame = ctk.CTkFrame(self.components_list_frame)
            row_frame.pack(fill="x", pady=2)

            # Name and quantity
            name_label = ctk.CTkLabel(
                row_frame,
                text=f"{comp['display_name']} x {comp['quantity']}",
                anchor="w",
            )
            name_label.pack(side="left", padx=5, fill="x", expand=True)

            # Remove button
            remove_btn = ctk.CTkButton(
                row_frame,
                text="Remove",
                width=70,
                fg_color="red",
                hover_color="darkred",
                command=lambda idx=i: self._remove_nested_component(idx),
            )
            remove_btn.pack(side="right", padx=5)

    def _remove_nested_component(self, index: int):
        """Remove a nested FinishedGood component by index (WP06: T042)."""
        if 0 <= index < len(self._nested_components):
            del self._nested_components[index]
            # Update sort_order for remaining items
            for i, comp in enumerate(self._nested_components):
                comp["sort_order"] = i
            self._refresh_components_list()

    def _create_buttons(self):
        """Create Save and Cancel buttons."""
        # Cancel button
        self.cancel_btn = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self._on_cancel,
            fg_color="gray",
        )
        self.cancel_btn.pack(side="right", padx=5)

        # Save button
        self.save_btn = ctk.CTkButton(
            self.button_frame,
            text="Save",
            command=self._on_save,
        )
        self.save_btn.pack(side="right", padx=5)

    def _populate_form(self):
        """Populate form fields from existing FinishedGood."""
        if not self.finished_good:
            return

        # Name
        self.name_entry.insert(0, self.finished_good.display_name)

        # Assembly Type
        type_display = self._enum_to_type.get(
            self.finished_good.assembly_type,
            "Custom Order",
        )
        self.type_dropdown.set(type_display)

        # Packaging Instructions
        if self.finished_good.packaging_instructions:
            self.packaging_text.insert("1.0", self.finished_good.packaging_instructions)

        # Notes
        if self.finished_good.notes:
            self.notes_text.insert("1.0", self.finished_good.notes)

        # Populate all component types from existing components (WP05/WP06: Edit mode integration)
        if self.finished_good.components:
            for comp in self.finished_good.components:
                if comp.finished_unit_id is not None:
                    # FinishedUnit component (Foods)
                    display_name = (
                        comp.finished_unit_component.display_name
                        if comp.finished_unit_component
                        else f"Food #{comp.finished_unit_id}"
                    )
                    self._foods_components.append({
                        "type": "finished_unit",
                        "id": comp.finished_unit_id,
                        "quantity": comp.component_quantity,
                        "display_name": display_name,
                        "sort_order": comp.sort_order or len(self._foods_components),
                    })
                elif comp.material_unit_id is not None:
                    # MaterialUnit component (Materials) - WP06
                    mu = comp.material_unit_component
                    if mu:
                        product_name = mu.material_product.name if mu.material_product else ""
                        display_name = f"{mu.name} ({product_name})" if product_name else mu.name
                    else:
                        display_name = f"Material #{comp.material_unit_id}"
                    self._materials_components.append({
                        "type": "material_unit",
                        "id": comp.material_unit_id,
                        "quantity": comp.component_quantity,
                        "display_name": display_name,
                        "sort_order": comp.sort_order or len(self._materials_components),
                    })
                elif comp.finished_good_id is not None:
                    # Nested FinishedGood component (Components) - WP06
                    fg = comp.finished_good_component
                    display_name = fg.display_name if fg else f"Component #{comp.finished_good_id}"
                    self._nested_components.append({
                        "type": "finished_good",
                        "id": comp.finished_good_id,
                        "quantity": comp.component_quantity,
                        "display_name": display_name,
                        "sort_order": comp.sort_order or len(self._nested_components),
                    })

            # Refresh all lists
            self._refresh_foods_list()
            self._refresh_materials_list()
            self._refresh_components_list()

    def _show_error(self, message: str):
        """Show error indication on the name field."""
        # Highlight the name field with red border
        self.name_entry.configure(border_color="red")

    def _clear_error(self):
        """Clear error indication on the name field."""
        # Reset to default border color
        self.name_entry.configure(border_color=("gray50", "gray30"))

    def _get_assembly_type(self) -> str:
        """Get the selected assembly type as enum value string."""
        selected = self.type_dropdown.get()
        enum_value = self._type_to_enum.get(selected, AssemblyType.CUSTOM_ORDER)
        return enum_value.value

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()

    def _on_save(self):
        """Handle save button click with validation."""
        # Clear any previous error
        self._clear_error()

        # Validate required fields
        name = self.name_entry.get().strip()
        if not name:
            self._show_error("Name is required")
            return

        # Combine all component types (WP06)
        all_components = (
            self._foods_components.copy()
            + self._materials_components.copy()
            + self._nested_components.copy()
        )

        # Re-assign sort_order across all types
        for i, comp in enumerate(all_components):
            comp["sort_order"] = i

        # Build result with all components (WP05/WP06)
        self.result = {
            "display_name": name,
            "assembly_type": self._get_assembly_type(),
            "packaging_instructions": self.packaging_text.get("1.0", "end-1c").strip(),
            "notes": self.notes_text.get("1.0", "end-1c").strip(),
            "components": all_components,
        }
        self.destroy()

    def get_result(self) -> Optional[Dict]:
        """
        Wait for dialog to close and return result.

        Returns:
            Dictionary with form data if saved, None if cancelled
        """
        self.wait_window()
        return self.result
