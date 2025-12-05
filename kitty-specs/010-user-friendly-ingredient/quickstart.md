# Quickstart: User-Friendly Ingredient Density Input

**Feature**: 010-user-friendly-ingredient
**Date**: 2025-12-04

## Code Examples

### 1. Ingredient Model with Density Method

```python
# src/models/ingredient.py

from typing import Optional
from sqlalchemy import Column, String, Float

class Ingredient(BaseModel):
    # ... existing fields ...

    # User-friendly density specification (replaces density_g_per_ml)
    density_volume_value = Column(Float, nullable=True)
    density_volume_unit = Column(String(20), nullable=True)
    density_weight_value = Column(Float, nullable=True)
    density_weight_unit = Column(String(20), nullable=True)

    def get_density_g_per_ml(self) -> Optional[float]:
        """
        Calculate density in g/ml from the 4-field specification.

        Example: If density is "1 cup = 4.25 oz":
        - 1 cup = 236.588 ml
        - 4.25 oz = 120.49 g
        - Density = 120.49 / 236.588 = 0.509 g/ml

        Returns:
            Density in grams per milliliter, or None if not specified.
        """
        if not all([
            self.density_volume_value,
            self.density_volume_unit,
            self.density_weight_value,
            self.density_weight_unit
        ]):
            return None

        from src.services.unit_converter import convert_standard_units

        # Convert volume to ml
        success, ml, _ = convert_standard_units(
            self.density_volume_value,
            self.density_volume_unit,
            "ml"
        )
        if not success or ml <= 0:
            return None

        # Convert weight to grams
        success, grams, _ = convert_standard_units(
            self.density_weight_value,
            self.density_weight_unit,
            "g"
        )
        if not success or grams <= 0:
            return None

        return grams / ml

    def format_density_display(self) -> str:
        """Format density for UI display."""
        if not self.get_density_g_per_ml():
            return "Not set"
        return (
            f"{self.density_volume_value:g} {self.density_volume_unit} = "
            f"{self.density_weight_value:g} {self.density_weight_unit}"
        )
```

### 2. Updated Unit Converter Functions

```python
# src/services/unit_converter.py

from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.ingredient import Ingredient


def convert_volume_to_weight(
    volume_value: float,
    volume_unit: str,
    weight_unit: str,
    ingredient: "Ingredient" = None,
    density_g_per_ml: float = None,
) -> Tuple[bool, float, str]:
    """
    Convert a volume measurement to weight using ingredient density.

    Args:
        volume_value: Quantity in volume units
        volume_unit: Volume unit (e.g., "cup", "tbsp")
        weight_unit: Target weight unit (e.g., "g", "oz")
        ingredient: Ingredient object with density specification
        density_g_per_ml: Direct density override (for testing)

    Returns:
        Tuple of (success, weight_value, error_message)
    """
    # Get density from ingredient or override
    density = density_g_per_ml
    if density is None and ingredient is not None:
        density = ingredient.get_density_g_per_ml()

    if density is None or density <= 0:
        ingredient_name = ingredient.name if ingredient else "unknown"
        return (
            False,
            0.0,
            f"Density required for conversion. Edit ingredient '{ingredient_name}' to set density.",
        )

    # Convert volume to ml
    success, ml, error = convert_standard_units(volume_value, volume_unit, "ml")
    if not success:
        return False, 0.0, error

    # Calculate weight in grams
    grams = ml * density

    # Convert to target weight unit
    success, weight, error = convert_standard_units(grams, "g", weight_unit)
    if not success:
        return False, 0.0, error

    return True, weight, ""


def convert_weight_to_volume(
    weight_value: float,
    weight_unit: str,
    volume_unit: str,
    ingredient: "Ingredient" = None,
    density_g_per_ml: float = None,
) -> Tuple[bool, float, str]:
    """
    Convert a weight measurement to volume using ingredient density.

    Args:
        weight_value: Quantity in weight units
        weight_unit: Weight unit (e.g., "g", "oz")
        volume_unit: Target volume unit (e.g., "cup", "tbsp")
        ingredient: Ingredient object with density specification
        density_g_per_ml: Direct density override (for testing)

    Returns:
        Tuple of (success, volume_value, error_message)
    """
    # Get density from ingredient or override
    density = density_g_per_ml
    if density is None and ingredient is not None:
        density = ingredient.get_density_g_per_ml()

    if density is None or density <= 0:
        ingredient_name = ingredient.name if ingredient else "unknown"
        return (
            False,
            0.0,
            f"Density required for conversion. Edit ingredient '{ingredient_name}' to set density.",
        )

    # Convert weight to grams
    success, grams, error = convert_standard_units(weight_value, weight_unit, "g")
    if not success:
        return False, 0.0, error

    # Calculate volume in ml
    ml = grams / density

    # Convert to target volume unit
    success, volume, error = convert_standard_units(ml, "ml", volume_unit)
    if not success:
        return False, 0.0, error

    return True, volume, ""
```

### 3. Density Input UI Component

```python
# In src/ui/ingredients_tab.py - density input section

def _create_density_frame(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
    """Create the 4-field density input section."""
    from src.utils.constants import VOLUME_UNITS, WEIGHT_UNITS

    density_frame = ctk.CTkFrame(parent, fg_color="transparent")

    # Label
    label = ctk.CTkLabel(
        density_frame,
        text="Density (optional):",
        font=ctk.CTkFont(size=14),
    )
    label.grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 5))

    # Volume value entry
    self.density_volume_value_entry = ctk.CTkEntry(
        density_frame,
        width=80,
        placeholder_text="1.0",
    )
    self.density_volume_value_entry.grid(row=1, column=0, padx=(0, 5))

    # Volume unit dropdown
    self.density_volume_unit_var = ctk.StringVar(value="cup")
    self.density_volume_unit_dropdown = ctk.CTkComboBox(
        density_frame,
        values=VOLUME_UNITS,
        variable=self.density_volume_unit_var,
        width=100,
    )
    self.density_volume_unit_dropdown.grid(row=1, column=1, padx=(0, 10))

    # Equals label
    equals_label = ctk.CTkLabel(
        density_frame,
        text="=",
        font=ctk.CTkFont(size=16, weight="bold"),
    )
    equals_label.grid(row=1, column=2, padx=10)

    # Weight value entry
    self.density_weight_value_entry = ctk.CTkEntry(
        density_frame,
        width=80,
        placeholder_text="4.25",
    )
    self.density_weight_value_entry.grid(row=1, column=3, padx=(10, 5))

    # Weight unit dropdown
    self.density_weight_unit_var = ctk.StringVar(value="oz")
    self.density_weight_unit_dropdown = ctk.CTkComboBox(
        density_frame,
        values=WEIGHT_UNITS,
        variable=self.density_weight_unit_var,
        width=100,
    )
    self.density_weight_unit_dropdown.grid(row=1, column=4)

    # Help text
    help_label = ctk.CTkLabel(
        density_frame,
        text="Example: 1 cup = 4.25 oz for flour",
        font=ctk.CTkFont(size=11),
        text_color="gray",
    )
    help_label.grid(row=2, column=0, columnspan=5, sticky="w", pady=(5, 0))

    return density_frame
```

### 4. Density Validation

```python
# In src/services/ingredient_service.py

def validate_density_fields(
    volume_value: Optional[float],
    volume_unit: Optional[str],
    weight_value: Optional[float],
    weight_unit: Optional[str],
) -> Tuple[bool, str]:
    """
    Validate density field group (all or nothing).

    Args:
        volume_value: Volume amount
        volume_unit: Volume unit string
        weight_value: Weight amount
        weight_unit: Weight unit string

    Returns:
        Tuple of (is_valid, error_message)
    """
    from src.utils.constants import VOLUME_UNITS, WEIGHT_UNITS

    # Normalize empty strings to None
    fields = [
        volume_value if volume_value not in (None, "", 0) else None,
        volume_unit if volume_unit not in (None, "") else None,
        weight_value if weight_value not in (None, "", 0) else None,
        weight_unit if weight_unit not in (None, "") else None,
    ]

    filled_count = sum(1 for f in fields if f is not None)

    # All empty is valid (no density)
    if filled_count == 0:
        return True, ""

    # Partially filled is invalid
    if filled_count < 4:
        return False, "All density fields must be provided together"

    # Validate positive values
    if volume_value <= 0:
        return False, "Volume value must be greater than zero"

    if weight_value <= 0:
        return False, "Weight value must be greater than zero"

    # Validate unit types
    if volume_unit.lower() not in [u.lower() for u in VOLUME_UNITS]:
        return False, f"Invalid volume unit: {volume_unit}"

    if weight_unit.lower() not in [u.lower() for u in WEIGHT_UNITS]:
        return False, f"Invalid weight unit: {weight_unit}"

    return True, ""
```

### 5. Import/Export Handling

```python
# In src/services/import_export_service.py

def export_ingredient_to_dict(ingredient: Ingredient) -> dict:
    """Export ingredient with density fields."""
    return {
        "slug": ingredient.slug,
        "name": ingredient.name,
        "category": ingredient.category,
        "recipe_unit": ingredient.recipe_unit,
        "description": ingredient.description,
        "notes": ingredient.notes,
        # New density fields
        "density_volume_value": ingredient.density_volume_value,
        "density_volume_unit": ingredient.density_volume_unit,
        "density_weight_value": ingredient.density_weight_value,
        "density_weight_unit": ingredient.density_weight_unit,
    }


def import_ingredient_from_dict(data: dict, session) -> Ingredient:
    """Import ingredient with density fields."""
    ingredient = Ingredient(
        slug=data.get("slug"),
        name=data.get("name"),
        category=data.get("category"),
        recipe_unit=data.get("recipe_unit"),
        description=data.get("description"),
        notes=data.get("notes"),
        # New density fields (ignore legacy density_g_per_ml)
        density_volume_value=data.get("density_volume_value"),
        density_volume_unit=data.get("density_volume_unit"),
        density_weight_value=data.get("density_weight_value"),
        density_weight_unit=data.get("density_weight_unit"),
    )
    session.add(ingredient)
    return ingredient
```

### 6. Warning Display for Missing Density

```python
# In recipe ingredient UI when conversion fails

def _show_density_warning(self, ingredient_name: str, ingredient_slug: str):
    """Show inline warning when density is needed but not set."""
    warning_frame = ctk.CTkFrame(self.form_frame, fg_color="#FFF3CD")

    warning_label = ctk.CTkLabel(
        warning_frame,
        text=f"Density required for conversion.",
        text_color="#856404",
    )
    warning_label.pack(side="left", padx=10, pady=5)

    edit_button = ctk.CTkButton(
        warning_frame,
        text="Edit Ingredient",
        width=120,
        height=28,
        command=lambda: self._open_ingredient_editor(ingredient_slug),
    )
    edit_button.pack(side="left", padx=10, pady=5)

    warning_frame.pack(fill="x", pady=5)


def _open_ingredient_editor(self, slug: str):
    """Open ingredient editor without losing current form state."""
    # Store current form state
    self._save_form_state()

    # Open ingredient editor dialog
    from src.ui.ingredient_edit_dialog import IngredientEditDialog
    dialog = IngredientEditDialog(self, slug=slug)
    dialog.wait_window()

    # Restore form state and re-validate
    self._restore_form_state()
    self._validate_conversions()
```

## Testing Examples

```python
# test_density_conversion.py

def test_ingredient_density_calculation():
    """Test that 4-field density calculates correct g/ml."""
    ingredient = Ingredient(
        name="All-Purpose Flour",
        density_volume_value=1.0,
        density_volume_unit="cup",
        density_weight_value=4.25,
        density_weight_unit="oz",
    )

    density = ingredient.get_density_g_per_ml()

    # 1 cup = 236.588 ml, 4.25 oz = 120.49 g
    # Expected: 120.49 / 236.588 = 0.509 g/ml
    assert density is not None
    assert abs(density - 0.509) < 0.01


def test_ingredient_without_density():
    """Test that missing density returns None."""
    ingredient = Ingredient(name="Test Ingredient")

    assert ingredient.get_density_g_per_ml() is None


def test_partial_density_validation():
    """Test that partial density fields fail validation."""
    is_valid, error = validate_density_fields(
        volume_value=1.0,
        volume_unit="cup",
        weight_value=None,  # Missing!
        weight_unit=None,   # Missing!
    )

    assert is_valid is False
    assert "All density fields must be provided together" in error
```
