"""
Contract: Recipe Costing Methods

This file defines the interface contracts for recipe cost calculation methods
to be added to RecipeService. These are NOT production code - they define
the expected signatures, return types, and behavior contracts.

Feature: 005-recipe-fifo-cost
Date: 2025-12-02
"""

from decimal import Decimal
from typing import Protocol


class RecipeCostingProtocol(Protocol):
    """
    Protocol defining the costing methods to be added to RecipeService.

    These methods extend the existing RecipeService with FIFO-based
    cost calculations.
    """

    def calculate_actual_cost(self, recipe_id: int) -> Decimal:
        """
        Calculate the actual cost of a recipe using FIFO pantry inventory.

        Determines what the recipe would cost to make using ingredients
        currently in the pantry, consuming oldest inventory first (FIFO).
        When pantry inventory is insufficient, falls back to preferred
        variant pricing for the shortfall.

        Args:
            recipe_id: The ID of the recipe to cost

        Returns:
            Decimal: Total cost of the recipe

        Raises:
            RecipeNotFound: If recipe_id does not exist
            IngredientNotFound: If a recipe ingredient has no variants
            ValidationError: If an ingredient cannot be costed (no pricing data,
                           missing density for unit conversion, etc.)

        Behavior:
            - Uses FIFO ordering (oldest pantry items first)
            - Does NOT modify pantry quantities (read-only)
            - Converts units using INGREDIENT_DENSITIES constants
            - Fails fast on any uncostable ingredient
            - Returns Decimal for precision in monetary calculations
        """
        ...

    def calculate_estimated_cost(self, recipe_id: int) -> Decimal:
        """
        Calculate the estimated cost of a recipe using preferred variant pricing.

        Determines what the recipe would cost based on current market prices,
        ignoring pantry inventory. Useful for planning and shopping decisions.

        Args:
            recipe_id: The ID of the recipe to cost

        Returns:
            Decimal: Estimated total cost of the recipe

        Raises:
            RecipeNotFound: If recipe_id does not exist
            IngredientNotFound: If a recipe ingredient has no variants
            ValidationError: If an ingredient cannot be costed (no purchase
                           history, missing density for unit conversion, etc.)

        Behavior:
            - Uses preferred variant for each ingredient
            - Falls back to any available variant if no preferred set
            - Uses most recent purchase price for pricing
            - Converts units using INGREDIENT_DENSITIES constants
            - Fails fast on any uncostable ingredient
            - Returns Decimal for precision in monetary calculations
        """
        ...
