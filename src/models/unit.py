"""
Unit reference model for the Seasonal Baking Tracker.

This model stores valid measurement units with metadata for UI dropdowns.
Units are seeded on database initialization and should not be modified by users.
"""

from sqlalchemy import Column, String, Integer

from .base import BaseModel


class Unit(BaseModel):
    """
    Reference table for valid measurement units.

    Stores all valid units with metadata for:
    - UI dropdown population
    - Category-based filtering
    - Future UN/CEFACT standard compliance

    Attributes:
        code: Unique unit code stored in other tables (e.g., "oz", "cup")
        display_name: Human-readable name (e.g., "ounce", "cup")
        symbol: Display symbol in UI (typically same as code)
        category: Unit category for filtering: "weight", "volume", "count", "package"
        un_cefact_code: Optional UN/CEFACT standard code for future use
        sort_order: Display order within category for dropdowns
    """

    __tablename__ = "units"

    code = Column(String(20), unique=True, nullable=False, index=True)
    display_name = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    category = Column(String(20), nullable=False, index=True)
    un_cefact_code = Column(String(10), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        """Return string representation of Unit."""
        return f"Unit(code='{self.code}', category='{self.category}')"
