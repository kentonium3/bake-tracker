# Data Model: Enhanced Catalog Import

**Feature**: 020-enhanced-catalog-import
**Date**: 2025-12-14

## Overview

This document defines the data structures, contracts, and interfaces for the catalog import feature. It builds on existing models (Ingredient, Product, Recipe) without schema changes.

---

## New Data Structures

### CatalogImportResult

Result object for catalog import operations. Follows pattern of existing `ImportResult`.

```python
@dataclass
class EntityImportCounts:
    """Per-entity import statistics."""
    added: int = 0
    skipped: int = 0
    failed: int = 0
    augmented: int = 0  # New: tracks AUGMENT mode updates


@dataclass
class ImportError:
    """Structured error for import failures."""
    entity_type: str      # "ingredients", "products", "recipes"
    identifier: str       # slug, name, or composite key
    error_type: str       # "validation", "fk_missing", "duplicate", "format"
    message: str          # Human-readable error
    suggestion: str       # Actionable fix suggestion


class CatalogImportResult:
    """Result of a catalog import operation."""

    def __init__(self):
        self.entity_counts: Dict[str, EntityImportCounts] = {
            "ingredients": EntityImportCounts(),
            "products": EntityImportCounts(),
            "recipes": EntityImportCounts(),
        }
        self.errors: List[ImportError] = []
        self.warnings: List[str] = []
        self.dry_run: bool = False
        self.mode: str = "add"

    @property
    def total_added(self) -> int

    @property
    def total_skipped(self) -> int

    @property
    def total_failed(self) -> int

    @property
    def total_augmented(self) -> int

    @property
    def has_errors(self) -> bool

    def add_success(self, entity_type: str) -> None

    def add_skip(self, entity_type: str, identifier: str, reason: str) -> None

    def add_error(self, entity_type: str, identifier: str,
                  error_type: str, message: str, suggestion: str) -> None

    def add_augment(self, entity_type: str, identifier: str,
                    fields_updated: List[str]) -> None

    def get_summary(self) -> str
        """Generate user-friendly summary for CLI/UI display."""

    def get_detailed_report(self) -> str
        """Generate detailed report with all errors and warnings."""
```

### ImportMode Enum

```python
from enum import Enum

class ImportMode(str, Enum):
    """Import mode selection."""
    ADD_ONLY = "add"      # Create new, skip existing
    AUGMENT = "augment"   # Update null fields on existing, add new
```

---

## Catalog File Format (v1.0)

### Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["catalog_version"],
  "properties": {
    "catalog_version": {
      "type": "string",
      "const": "1.0"
    },
    "generated_at": {
      "type": "string",
      "format": "date-time"
    },
    "ingredients": {
      "type": "array",
      "items": { "$ref": "#/definitions/ingredient" }
    },
    "products": {
      "type": "array",
      "items": { "$ref": "#/definitions/product" }
    },
    "recipes": {
      "type": "array",
      "items": { "$ref": "#/definitions/recipe" }
    }
  },
  "definitions": {
    "ingredient": {
      "type": "object",
      "required": ["slug", "display_name", "category"],
      "properties": {
        "slug": { "type": "string" },
        "display_name": { "type": "string" },
        "category": { "type": "string" },
        "description": { "type": ["string", "null"] },
        "is_packaging": { "type": "boolean", "default": false },
        "density_volume_value": { "type": ["number", "null"] },
        "density_volume_unit": { "type": ["string", "null"] },
        "density_weight_value": { "type": ["number", "null"] },
        "density_weight_unit": { "type": ["string", "null"] },
        "allergens": { "type": ["array", "null"], "items": { "type": "string" } },
        "foodon_id": { "type": ["string", "null"] },
        "fdc_ids": { "type": ["array", "null"], "items": { "type": "string" } },
        "foodex2_code": { "type": ["string", "null"] },
        "langual_terms": { "type": ["array", "null"], "items": { "type": "string" } }
      }
    },
    "product": {
      "type": "object",
      "required": ["ingredient_slug", "brand", "purchase_unit", "purchase_quantity"],
      "properties": {
        "ingredient_slug": { "type": "string" },
        "brand": { "type": ["string", "null"] },
        "package_size": { "type": ["string", "null"] },
        "package_type": { "type": ["string", "null"] },
        "purchase_unit": { "type": "string" },
        "purchase_quantity": { "type": "number" },
        "upc_code": { "type": ["string", "null"] },
        "preferred": { "type": ["boolean", "null"] }
      }
    },
    "recipe": {
      "type": "object",
      "required": ["name", "category", "yield_quantity", "yield_unit"],
      "properties": {
        "name": { "type": "string" },
        "category": { "type": "string" },
        "source": { "type": ["string", "null"] },
        "yield_quantity": { "type": "number" },
        "yield_unit": { "type": "string" },
        "yield_description": { "type": ["string", "null"] },
        "estimated_time_minutes": { "type": ["integer", "null"] },
        "notes": { "type": ["string", "null"] },
        "ingredients": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["ingredient_slug", "quantity", "unit"],
            "properties": {
              "ingredient_slug": { "type": "string" },
              "quantity": { "type": "number" },
              "unit": { "type": "string" },
              "notes": { "type": ["string", "null"] }
            }
          }
        },
        "components": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["recipe_name", "quantity"],
            "properties": {
              "recipe_name": { "type": "string" },
              "quantity": { "type": "number", "default": 1.0 },
              "notes": { "type": ["string", "null"] }
            }
          }
        }
      }
    }
  }
}
```

---

## Service Contracts

### catalog_import_service.py

```python
"""Catalog Import Service - Entity-specific import with ADD_ONLY and AUGMENT modes."""

from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from src.services.database import session_scope


def import_catalog(
    file_path: str,
    mode: str = "add",
    entities: Optional[List[str]] = None,
    dry_run: bool = False,
    session: Optional[Session] = None
) -> CatalogImportResult:
    """
    Import a catalog file (ingredients, products, recipes).

    Coordinator function that dispatches to entity-specific importers
    in dependency order: ingredients -> products -> recipes.

    Args:
        file_path: Path to catalog JSON file
        mode: "add" (ADD_ONLY) or "augment" (AUGMENT)
        entities: List of entity types to import, or None for all
        dry_run: If True, validate and preview without committing
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        CatalogImportResult with counts and any errors

    Raises:
        FileNotFoundError: If file doesn't exist
        CatalogImportError: If file format is invalid
    """


def import_ingredients(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None
) -> CatalogImportResult:
    """
    Import ingredients from parsed data.

    Independently callable for future integrations (USDA FDC, FoodOn).

    Args:
        data: List of ingredient dictionaries
        mode: "add" or "augment"
        dry_run: Preview mode
        session: Optional session

    Returns:
        CatalogImportResult for ingredients only
    """


def import_products(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None
) -> CatalogImportResult:
    """
    Import products from parsed data.

    Validates ingredient_slug FK references before creating.
    Independently callable for future integrations (UPC databases).

    Args:
        data: List of product dictionaries
        mode: "add" or "augment"
        dry_run: Preview mode
        session: Optional session

    Returns:
        CatalogImportResult for products only
    """


def import_recipes(
    data: List[Dict],
    mode: str = "add",
    dry_run: bool = False,
    session: Optional[Session] = None
) -> CatalogImportResult:
    """
    Import recipes from parsed data.

    Validates ingredient_slug and recipe_name FK references.
    Detects circular recipe references.
    AUGMENT mode not supported - raises error if requested.

    Args:
        data: List of recipe dictionaries
        mode: Must be "add" (AUGMENT not supported for recipes)
        dry_run: Preview mode
        session: Optional session

    Returns:
        CatalogImportResult for recipes only

    Raises:
        CatalogImportError: If mode is "augment"
    """


def validate_catalog_file(file_path: str) -> Dict:
    """
    Load and validate a catalog file.

    Detects format (catalog vs unified) and validates structure.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed catalog data dict

    Raises:
        CatalogImportError: If format invalid or not a catalog file
    """
```

### CLI Contract (import_catalog.py)

```python
"""CLI for catalog import operations."""

import argparse
import sys


def main():
    """
    Entry point for: python -m src.utils.import_catalog

    Usage:
        python -m src.utils.import_catalog catalog.json
        python -m src.utils.import_catalog catalog.json --mode=augment
        python -m src.utils.import_catalog catalog.json --entity=ingredients
        python -m src.utils.import_catalog catalog.json --dry-run
        python -m src.utils.import_catalog catalog.json --verbose

    Arguments:
        file_path       Path to catalog JSON file

    Options:
        --mode          Import mode: add (default) or augment
        --entity        Entity to import: ingredients, products, recipes (can repeat)
        --dry-run       Preview changes without committing
        --verbose       Show detailed output for each record

    Exit Codes:
        0   Success (all records processed, may have skips)
        1   Partial success (some records failed)
        2   Complete failure (no records imported)
        3   Invalid arguments or file not found
    """
```

---

## Entity Mapping

### Existing Entities (No Changes)

| Entity | Unique Key | Mode Support |
|--------|------------|--------------|
| Ingredient | `slug` | ADD_ONLY, AUGMENT |
| Product | `ingredient_id` + `brand` | ADD_ONLY, AUGMENT |
| Recipe | `name` | ADD_ONLY only |
| RecipeIngredient | `recipe_id` + `ingredient_id` | Created with recipe |
| RecipeComponent | `recipe_id` + `component_recipe_id` | Created with recipe |

### Field Mappings

**Ingredient Import → Ingredient Model**

| Import Field | Model Field | Notes |
|--------------|-------------|-------|
| `slug` | `slug` | Unique key |
| `display_name` | `display_name` | Required |
| `category` | `category` | Required |
| `description` | `description` | Optional |
| `is_packaging` | `is_packaging` | Default: false |
| `density_volume_value` | `density_volume_value` | Augmentable |
| `density_volume_unit` | `density_volume_unit` | Augmentable |
| `density_weight_value` | `density_weight_value` | Augmentable |
| `density_weight_unit` | `density_weight_unit` | Augmentable |
| `allergens` | `allergens` | Augmentable, JSON array |
| `foodon_id` | `foodon_id` | Augmentable |
| `fdc_ids` | `fdc_ids` | Augmentable, JSON array |
| `foodex2_code` | `foodex2_code` | Augmentable |
| `langual_terms` | `langual_terms` | Augmentable, JSON array |

**Product Import → Product Model**

| Import Field | Model Field | Notes |
|--------------|-------------|-------|
| `ingredient_slug` | `ingredient_id` | FK lookup required |
| `brand` | `brand` | Part of unique key |
| `package_size` | `package_size` | Augmentable |
| `package_type` | `package_type` | Augmentable |
| `purchase_unit` | `purchase_unit` | Required, augmentable if null |
| `purchase_quantity` | `purchase_quantity` | Required, augmentable if null |
| `upc_code` | `upc_code` | Augmentable |
| `preferred` | `preferred` | Augmentable if null |

**Recipe Import → Recipe + RecipeIngredient + RecipeComponent**

| Import Field | Target | Notes |
|--------------|--------|-------|
| `name` | `Recipe.name` | Unique key |
| `category` | `Recipe.category` | Required |
| `source` | `Recipe.source` | Optional |
| `yield_quantity` | `Recipe.yield_quantity` | Required |
| `yield_unit` | `Recipe.yield_unit` | Required |
| `yield_description` | `Recipe.yield_description` | Optional |
| `estimated_time_minutes` | `Recipe.estimated_time_minutes` | Optional |
| `notes` | `Recipe.notes` | Optional |
| `ingredients[].ingredient_slug` | `RecipeIngredient.ingredient_id` | FK lookup |
| `ingredients[].quantity` | `RecipeIngredient.quantity` | Required |
| `ingredients[].unit` | `RecipeIngredient.unit` | Required |
| `ingredients[].notes` | `RecipeIngredient.notes` | Optional |
| `components[].recipe_name` | `RecipeComponent.component_recipe_id` | FK lookup |
| `components[].quantity` | `RecipeComponent.quantity` | Default: 1.0 |
| `components[].notes` | `RecipeComponent.notes` | Optional |

---

## Validation Rules

### Pre-Import Validation

1. **File format**: Must have `catalog_version` field (not `version`)
2. **JSON structure**: Must parse as valid JSON
3. **Required fields**: Each entity must have required fields

### Entity-Level Validation

**Ingredients**:
- `slug` must be unique within import file
- `category` must be non-empty string

**Products**:
- `ingredient_slug` must reference existing ingredient OR ingredient in same import
- `brand` + `ingredient_slug` must be unique within import file

**Recipes**:
- `name` must not exist in database (reject with detailed error)
- All `ingredient_slug` references must exist
- All `recipe_name` references in components must exist (or be earlier in import)
- No circular component references (detect cycles)

### Error Message Templates

```python
# Missing FK reference
"Product '{brand}' for ingredient '{ingredient_slug}' failed: "
"Ingredient '{ingredient_slug}' not found. Import the ingredient first."

# Recipe slug collision
"Recipe '{name}' failed: Recipe already exists. "
"Existing: '{existing_name}' (yields {existing_yield} {existing_unit}). "
"Import: '{import_name}' (yields {import_yield} {import_unit}). "
"To import, delete the existing recipe or rename the import."

# Circular reference
"Recipe '{name}' failed: Circular component reference detected. "
"Cycle: {cycle_path}. Remove circular dependency to import."

# AUGMENT mode for recipes
"AUGMENT mode is not supported for recipes. Use ADD_ONLY (--mode=add)."
```
