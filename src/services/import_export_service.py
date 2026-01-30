"""
Import/Export Service - JSON-based data import and export for testing.

Provides minimal functionality to export and import ingredients and recipes
for testing purposes. No UI required - designed for programmatic use.
"""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from src.utils.datetime_utils import utc_now
from pathlib import Path

from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

from src.services import ingredient_crud_service
from src.services import recipe_service, finished_good_service
from src.services import package_service, recipient_service, event_service
from src.services import catalog_import_service
from src.services.exceptions import ValidationError
from src.services.supplier_service import generate_supplier_slug
from src.services.database import session_scope
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.inventory_item import InventoryItem
from src.models.purchase import Purchase
from src.models.supplier import Supplier
from src.models.finished_unit import FinishedUnit, YieldMode
from src.models.finished_good import FinishedGood
from src.models.composition import Composition
from src.models.composition_assignment import CompositionAssignment
from src.models.package import Package, PackageFinishedGood
from src.models.production_record import ProductionRecord
from src.models.production_run import ProductionRun
from src.models.assembly_run import AssemblyRun
from src.models.event import (
    Event,
    EventProductionTarget,
    EventAssemblyTarget,
    FulfillmentStatus,
    PlanState,
    OutputMode,
)
from src.models.event_recipe import EventRecipe
from src.models.event_finished_good import EventFinishedGood
from src.models.batch_decision import BatchDecision
from src.models.plan_amendment import PlanAmendment, AmendmentType
from src.models.recipe import Recipe, RecipeComponent, RecipeIngredient
from src.models.material import Material
from src.models.material_product import MaterialProduct
from src.models.material_unit import MaterialUnit  # Feature 084
from src.models.material_category import MaterialCategory
from src.models.material_subcategory import MaterialSubcategory
from src.utils.constants import (
    APP_NAME,
    APP_VERSION,
    ALL_UNITS,
    MEASUREMENT_UNITS,
    WEIGHT_UNITS,
    VOLUME_UNITS,
    COUNT_UNITS,
)


# ============================================================================
# Result Classes
# ============================================================================


class ImportResult:
    """Result of an import operation with per-entity tracking."""

    def __init__(self):
        self.total_records = 0
        self.successful = 0
        self.skipped = 0
        self.failed = 0
        self.errors = []
        self.warnings = []
        self.entity_counts: Dict[str, Dict[str, int]] = {}
        # F057: Track provisional products created during import
        self.provisional_products_created = 0

    def add_success(self, entity_type: str = None):
        """Record a successful import."""
        self.successful += 1
        self.total_records += 1
        if entity_type:
            self._ensure_entity(entity_type)
            self.entity_counts[entity_type]["imported"] += 1

    def add_skip(
        self,
        record_type: str,
        record_name: str,
        reason: str,
        suggestion: str = None,
    ):
        """Record a skipped record.

        Args:
            record_type: Type of record (e.g., "ingredients", "recipes")
            record_name: Identifier for the record
            reason: Why the record was skipped
            suggestion: Optional actionable suggestion
        """
        self.skipped += 1
        self.total_records += 1
        self._ensure_entity(record_type)
        self.entity_counts[record_type]["skipped"] += 1
        warning_entry = {
            "record_type": record_type,
            "record_name": record_name,
            "warning_type": "skipped",
            "message": reason,
        }
        if suggestion:
            warning_entry["suggestion"] = suggestion
        self.warnings.append(warning_entry)

    def add_update(
        self,
        record_type: str,
        record_name: str,
        message: str,
    ):
        """Record an updated record (merge mode).

        Args:
            record_type: Type of record (e.g., "supplier")
            record_name: Identifier for the record
            message: Description of what was updated
        """
        self.successful += 1
        self.total_records += 1
        self._ensure_entity(record_type)
        self.entity_counts[record_type]["updated"] += 1
        self.warnings.append(
            {
                "record_type": record_type,
                "record_name": record_name,
                "warning_type": "updated",
                "message": message,
            }
        )

    def add_error(
        self,
        record_type: str,
        record_name: str,
        error: str,
        suggestion: str = None,
    ):
        """Record a failed import.

        Args:
            record_type: Type of record (e.g., "ingredients", "recipes")
            record_name: Identifier for the record
            error: Error message describing what went wrong
            suggestion: Optional actionable suggestion for fixing the error
        """
        self.failed += 1
        self.total_records += 1
        self._ensure_entity(record_type)
        self.entity_counts[record_type]["errors"] += 1
        error_entry = {
            "record_type": record_type,
            "record_name": record_name,
            "error_type": "import_error",
            "message": error,
        }
        if suggestion:
            error_entry["suggestion"] = suggestion
        self.errors.append(error_entry)

    def add_warning(
        self,
        record_type: str,
        record_name: str,
        message: str,
        suggestion: str = None,
    ):
        """Record a warning (non-fatal issue during import).

        Args:
            record_type: Type of record (e.g., "ingredients", "recipes")
            record_name: Identifier for the record
            message: Warning message
            suggestion: Optional actionable suggestion
        """
        warning_entry = {
            "record_type": record_type,
            "record_name": record_name,
            "warning_type": "warning",
            "message": message,
        }
        if suggestion:
            warning_entry["suggestion"] = suggestion
        self.warnings.append(warning_entry)

    def _ensure_entity(self, entity_type: str):
        """Ensure entity type exists in entity_counts."""
        if entity_type not in self.entity_counts:
            self.entity_counts[entity_type] = {
                "imported": 0,
                "skipped": 0,
                "errors": 0,
                "updated": 0,
            }

    def merge(self, other: "ImportResult"):
        """Merge another ImportResult into this one."""
        self.total_records += other.total_records
        self.successful += other.successful
        self.skipped += other.skipped
        self.failed += other.failed
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        for entity, counts in other.entity_counts.items():
            self._ensure_entity(entity)
            self.entity_counts[entity]["imported"] += counts["imported"]
            self.entity_counts[entity]["skipped"] += counts["skipped"]
            self.entity_counts[entity]["errors"] += counts["errors"]
            self.entity_counts[entity]["updated"] += counts.get("updated", 0)

    def get_summary(self) -> str:
        """Get a user-friendly summary string of the import results."""
        lines = [
            "=" * 60,
            "Import Summary",
            "=" * 60,
        ]

        # Show per-entity breakdown if available
        if self.entity_counts:
            for entity, counts in self.entity_counts.items():
                parts = []
                if counts["imported"] > 0:
                    parts.append(f"{counts['imported']} imported")
                if counts.get("updated", 0) > 0:
                    parts.append(f"{counts['updated']} updated")
                if counts["skipped"] > 0:
                    parts.append(f"{counts['skipped']} skipped")
                if counts["errors"] > 0:
                    parts.append(f"{counts['errors']} errors")
                if parts:
                    lines.append(f"  {entity}: {', '.join(parts)}")
            lines.append("")

        lines.extend(
            [
                f"Total Records: {self.total_records}",
                f"Successful:    {self.successful}",
                f"Skipped:       {self.skipped}",
                f"Failed:        {self.failed}",
            ]
        )

        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors:
                lines.append(f"  - {error['record_type']}: {error['record_name']}")
                lines.append(f"    {error['message']}")
                if error.get("suggestion"):
                    lines.append(f"    Suggestion: {error['suggestion']}")

        if self.warnings and len(self.warnings) <= 10:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning['record_type']}: {warning['record_name']}")
                lines.append(f"    {warning['message']}")
                if warning.get("suggestion"):
                    lines.append(f"    Suggestion: {warning['suggestion']}")
        elif self.warnings:
            lines.append(f"\n{len(self.warnings)} warnings (see log file for full list)")

        lines.append("=" * 60)
        return "\n".join(lines)


class ExportResult:
    """Result of an export operation."""

    def __init__(self, file_path: str, record_count: int):
        self.file_path = file_path
        self.record_count = record_count
        self.success = True
        self.error = None
        self.entity_counts: Dict[str, int] = {}

    def add_entity_count(self, entity_type: str, count: int):
        """Add count for a specific entity type."""
        self.entity_counts[entity_type] = count

    def get_summary(self) -> str:
        """Get a summary string of the export results."""
        if not self.success:
            return f"Export failed: {self.error}"

        lines = [f"Exported {self.record_count} records to {self.file_path}"]

        if self.entity_counts:
            lines.append("")
            for entity, count in self.entity_counts.items():
                lines.append(f"  {entity}: {count}")

        return "\n".join(lines)


# ============================================================================
# Unit Validation Helpers
# ============================================================================


def _validate_unit(unit: str, valid_units: List[str], entity: str, field: str) -> Optional[str]:
    """
    Validate a unit value against a list of valid units.

    Args:
        unit: The unit value to validate
        valid_units: List of valid unit values
        entity: Entity name for error message (e.g., "product", "ingredient")
        field: Field name for error message (e.g., "package_unit")

    Returns:
        Error message string if invalid, None if valid
    """
    if unit is None:
        return None  # Allow None for optional fields

    unit_lower = unit.lower()
    valid_lower = [u.lower() for u in valid_units]

    if unit_lower not in valid_lower:
        valid_list = ", ".join(sorted(valid_units))
        return f"Invalid unit '{unit}' for {entity}.{field}. Valid units: {valid_list}"

    return None


def _validate_package_unit(unit: str, entity_name: str) -> Optional[str]:
    """Validate package_unit field (measurement units only: weight, volume, count)."""
    return _validate_unit(unit, MEASUREMENT_UNITS, entity_name, "package_unit")


def _validate_density_volume_unit(unit: str, entity_name: str) -> Optional[str]:
    """Validate density_volume_unit field (must be volume unit if provided)."""
    if unit is None:
        return None
    return _validate_unit(unit, VOLUME_UNITS, entity_name, "density_volume_unit")


def _validate_density_weight_unit(unit: str, entity_name: str) -> Optional[str]:
    """Validate density_weight_unit field (must be weight unit if provided)."""
    if unit is None:
        return None
    return _validate_unit(unit, WEIGHT_UNITS, entity_name, "density_weight_unit")


def _validate_recipe_ingredient_unit(
    unit: str, recipe_name: str, ingredient_slug: str
) -> Optional[str]:
    """Validate recipe ingredient unit field (weight, volume, or count)."""
    valid_units = WEIGHT_UNITS + VOLUME_UNITS + COUNT_UNITS
    if unit is None:
        return f"Missing unit for recipe '{recipe_name}' ingredient '{ingredient_slug}'"
    return _validate_unit(
        unit, valid_units, f"recipe '{recipe_name}'", f"ingredient '{ingredient_slug}' unit"
    )


# ============================================================================
# Export Functions
# ============================================================================


def export_ingredients_to_json(
    file_path: str, include_all: bool = True, category_filter: Optional[str] = None
) -> ExportResult:
    """
    Export ingredients to JSON file.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all ingredients (default)
        category_filter: Optional category to filter by

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get ingredients
        ingredients = ingredient_crud_service.get_all_ingredients(category=category_filter)

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": utc_now().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "ingredients": [],
        }

        for ingredient in ingredients:
            ingredient_data = {
                "display_name": ingredient.display_name,
                "brand": ingredient.brand,
                "category": ingredient.category,
                "package_unit_quantity": ingredient.package_unit_quantity,
                "package_unit": ingredient.package_unit,
                "quantity": ingredient.quantity,
                "unit_cost": ingredient.unit_cost,
            }

            # Optional fields
            if ingredient.package_type:
                ingredient_data["package_type"] = ingredient.package_type

            # Note: density_g_per_cup removed in Feature 010 (4-field density model)
            # Legacy v1.0 export does not include density; use v3.0 export for density data

            if ingredient.notes:
                ingredient_data["notes"] = ingredient.notes

            export_data["ingredients"].append(ingredient_data)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(file_path, len(ingredients))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


def export_recipes_to_json(
    file_path: str, include_all: bool = True, category_filter: Optional[str] = None
) -> ExportResult:
    """
    Export recipes to JSON file.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all recipes (default)
        category_filter: Optional category to filter by

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get recipes
        recipes = recipe_service.get_all_recipes(category=category_filter)

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": utc_now().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "recipes": [],
        }

        for recipe in recipes:
            # F056: yield_quantity, yield_unit, yield_description removed
            # Yield data is now in FinishedUnit records
            recipe_data = {
                "name": recipe.name,
                "category": recipe.category,
            }

            # Optional fields
            if recipe.source:
                recipe_data["source"] = recipe.source

            if recipe.estimated_time_minutes:
                recipe_data["estimated_time_minutes"] = recipe.estimated_time_minutes

            if recipe.notes:
                recipe_data["notes"] = recipe.notes

            # Recipe ingredients
            recipe_data["ingredients"] = []
            for ri in recipe.recipe_ingredients:
                ingredient_data = {
                    "ingredient_name": ri.ingredient.display_name,
                    "quantity": ri.quantity,
                    "unit": ri.unit,
                }

                # Include brand for disambiguation (brand moved to Product in TD-001)
                if hasattr(ri.ingredient, "brand") and ri.ingredient.brand:
                    ingredient_data["ingredient_brand"] = ri.ingredient.brand

                if ri.notes:
                    ingredient_data["notes"] = ri.notes

                recipe_data["ingredients"].append(ingredient_data)

            # Add recipe components (sub-recipes)
            recipe_data["components"] = []
            for comp in recipe.recipe_components:
                component_data = {
                    "recipe_name": comp.component_recipe.name if comp.component_recipe else None,
                    "quantity": comp.quantity,
                }
                if comp.notes:
                    component_data["notes"] = comp.notes

                recipe_data["components"].append(component_data)

            export_data["recipes"].append(recipe_data)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(file_path, len(recipes))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


def export_finished_goods_to_json(
    file_path: str, include_all: bool = True, category_filter: Optional[str] = None
) -> ExportResult:
    """
    Export finished goods to JSON file.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all finished goods (default)
        category_filter: Optional category to filter by

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get finished goods
        finished_goods = finished_good_service.get_all_finished_goods(category=category_filter)

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": utc_now().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "finished_goods": [],
        }

        for fg in finished_goods:
            fg_data = {
                "name": fg.name,
                "recipe_name": fg.recipe.name,
                "yield_mode": fg.yield_mode.value,
            }

            # Optional fields
            if fg.category:
                fg_data["category"] = fg.category

            if fg.yield_mode.value == "discrete_count":
                fg_data["items_per_batch"] = fg.items_per_batch
                fg_data["item_unit"] = fg.item_unit
            elif fg.yield_mode.value == "batch_portion":
                fg_data["batch_percentage"] = fg.batch_percentage
                if fg.portion_description:
                    fg_data["portion_description"] = fg.portion_description

            if fg.notes:
                fg_data["notes"] = fg.notes

            export_data["finished_goods"].append(fg_data)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(file_path, len(finished_goods))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


def export_bundles_to_json(file_path: str, include_all: bool = True) -> ExportResult:
    """
    Export bundles to JSON file.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all bundles (default)

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get bundles
        bundles = finished_good_service.get_all_bundles()

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": utc_now().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "bundles": [],
        }

        for bundle in bundles:
            bundle_data = {
                "name": bundle.name,
                "finished_good_name": bundle.finished_good.display_name,
                "quantity": bundle.quantity,
            }

            # Optional fields
            if bundle.packaging_notes:
                bundle_data["packaging_notes"] = bundle.packaging_notes

            export_data["bundles"].append(bundle_data)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(file_path, len(bundles))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


def export_packages_to_json(file_path: str, include_all: bool = True) -> ExportResult:
    """
    Export packages to JSON file.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all packages (default)

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get packages
        packages = package_service.get_all_packages()

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": utc_now().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "packages": [],
        }

        for package in packages:
            package_data = {"name": package.name, "is_template": package.is_template, "bundles": []}

            # Optional fields
            if package.description:
                package_data["description"] = package.description

            if package.notes:
                package_data["notes"] = package.notes

            # Package bundles
            for pb in package.package_bundles:
                bundle_item = {
                    "bundle_name": pb.bundle.name,
                    "quantity": pb.quantity,
                }
                package_data["bundles"].append(bundle_item)

            export_data["packages"].append(package_data)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(file_path, len(packages))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


def export_recipients_to_json(file_path: str, include_all: bool = True) -> ExportResult:
    """
    Export recipients to JSON file.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all recipients (default)

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get recipients
        recipients = recipient_service.get_all_recipients()

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": utc_now().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "recipients": [],
        }

        for recipient in recipients:
            recipient_data = {
                "name": recipient.name,
            }

            # Optional fields
            if recipient.household_name:
                recipient_data["household_name"] = recipient.household_name

            if recipient.address:
                recipient_data["address"] = recipient.address

            if recipient.notes:
                recipient_data["notes"] = recipient.notes

            export_data["recipients"].append(recipient_data)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(file_path, len(recipients))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


def export_events_to_json(file_path: str, include_all: bool = True) -> ExportResult:
    """
    Export events to JSON file.

    Includes event details and all recipient-package assignments.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all events (default)

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get events within session scope
        with session_scope() as session:
            events = event_service.get_all_events(session=session)

            # Build export data
            export_data = {
                "version": "1.0",
                "export_date": utc_now().isoformat() + "Z",
                "source": f"{APP_NAME} v{APP_VERSION}",
                "events": [],
            }

            for event in events:
                event_data = {
                    "name": event.name,
                    "event_date": event.event_date.isoformat(),
                    "year": event.year,
                    "assignments": [],
                }

                # Optional fields
                if event.notes:
                    event_data["notes"] = event.notes

                # Event assignments
                for assignment in event.event_recipient_packages:
                    assignment_data = {
                        "recipient_name": assignment.recipient.name,
                        "package_name": assignment.package.name,
                        "quantity": assignment.quantity,
                    }

                    if assignment.notes:
                        assignment_data["notes"] = assignment.notes

                    event_data["assignments"].append(assignment_data)

                export_data["events"].append(event_data)

            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            return ExportResult(file_path, len(events))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


# ============================================================================
# v3.0 Export Functions - New Entities
# ============================================================================


def export_finished_units_to_json() -> List[Dict]:
    """
    Export FinishedUnit records for v3.0 format.

    Returns:
        List of dictionaries containing finished unit data
    """
    result = []
    with session_scope() as session:
        finished_units = session.query(FinishedUnit).options(joinedload(FinishedUnit.recipe)).all()
        for fu in finished_units:
            fu_data = {
                "slug": fu.slug,
                "recipe_name": fu.recipe.name if fu.recipe else None,
                "display_name": fu.display_name,
                "yield_mode": fu.yield_mode.value if fu.yield_mode else None,
            }

            # Conditional fields based on yield mode
            if fu.yield_mode and fu.yield_mode.value == "discrete_count":
                if fu.items_per_batch is not None:
                    fu_data["items_per_batch"] = fu.items_per_batch
                if fu.item_unit:
                    fu_data["item_unit"] = fu.item_unit
            elif fu.yield_mode and fu.yield_mode.value == "batch_portion":
                if fu.batch_percentage is not None:
                    fu_data["batch_percentage"] = float(fu.batch_percentage)
                if fu.portion_description:
                    fu_data["portion_description"] = fu.portion_description

            # Optional fields
            if fu.category:
                fu_data["category"] = fu.category
            if fu.description:
                fu_data["description"] = fu.description
            if fu.production_notes:
                fu_data["production_notes"] = fu.production_notes
            if fu.notes:
                fu_data["notes"] = fu.notes

            result.append(fu_data)
    return result


def export_compositions_to_json() -> List[Dict]:
    """
    Export Composition records for v3.0 format.

    Compositions link finished units/goods to finished good assemblies.
    Feature 011: Also supports package_id and packaging_product_id for packaging compositions.

    Returns:
        List of dictionaries containing composition data
    """
    result = []
    with session_scope() as session:
        compositions = (
            session.query(Composition)
            .options(
                joinedload(Composition.assembly),
                joinedload(Composition.package),  # Feature 011
                joinedload(Composition.finished_unit_component),
                joinedload(Composition.finished_good_component),
                joinedload(Composition.packaging_product),  # Feature 011
                joinedload(Composition.material_unit_component),  # Feature 084
                joinedload(Composition.assignments),  # Feature 026
            )
            .all()
        )
        for comp in compositions:
            comp_data = {
                "component_quantity": float(comp.component_quantity),  # Ensure float
                "sort_order": comp.sort_order,
            }

            # Parent reference - XOR: assembly_id OR package_id (Feature 011)
            if comp.assembly:
                comp_data["finished_good_slug"] = comp.assembly.slug
                comp_data["package_name"] = None
            elif comp.package:
                comp_data["finished_good_slug"] = None
                comp_data["package_name"] = comp.package.name
            else:
                comp_data["finished_good_slug"] = None
                comp_data["package_name"] = None

            # Component reference - XOR: 4-way (Feature 084: material_id removed)
            # finished_unit OR finished_good OR packaging_product OR material_unit
            if comp.finished_unit_component:
                comp_data["finished_unit_slug"] = comp.finished_unit_component.slug
                comp_data["finished_good_component_slug"] = None
                comp_data["packaging_product_id"] = None
                comp_data["material_unit_slug"] = None
            elif comp.finished_good_component:
                comp_data["finished_unit_slug"] = None
                comp_data["finished_good_component_slug"] = comp.finished_good_component.slug
                comp_data["packaging_product_id"] = None
                comp_data["material_unit_slug"] = None
            elif comp.packaging_product:
                comp_data["finished_unit_slug"] = None
                comp_data["finished_good_component_slug"] = None
                # For packaging products, export ingredient_slug + brand for lookup
                comp_data["packaging_product_id"] = comp.packaging_product_id
                comp_data["packaging_ingredient_slug"] = (
                    comp.packaging_product.ingredient.slug
                    if comp.packaging_product.ingredient
                    else None
                )
                comp_data["packaging_product_brand"] = comp.packaging_product.brand
                comp_data["material_unit_slug"] = None
            elif comp.material_unit_component:
                # Feature 084: Export material_unit_slug for material compositions
                comp_data["finished_unit_slug"] = None
                comp_data["finished_good_component_slug"] = None
                comp_data["packaging_product_id"] = None
                comp_data["material_unit_slug"] = comp.material_unit_component.slug
            else:
                comp_data["finished_unit_slug"] = None
                comp_data["finished_good_component_slug"] = None
                comp_data["packaging_product_id"] = None
                comp_data["material_unit_slug"] = None

            # Feature 026: is_generic flag for deferred packaging
            comp_data["is_generic"] = comp.is_generic or False

            # Feature 026: Export assignments for generic compositions
            if comp.is_generic and comp.assignments:
                comp_data["assignments"] = [
                    {
                        "inventory_item_id": a.inventory_item_id,
                        "quantity_assigned": float(a.quantity_assigned),
                    }
                    for a in comp.assignments
                ]

            # Optional fields
            if comp.component_notes:
                comp_data["notes"] = comp.component_notes

            result.append(comp_data)
    return result


def export_package_finished_goods_to_json() -> List[Dict]:
    """
    Export PackageFinishedGood records for v3.0 format.

    Links packages to finished goods with quantities.

    Returns:
        List of dictionaries containing package-finished good links
    """
    result = []
    with session_scope() as session:
        pfgs = (
            session.query(PackageFinishedGood)
            .options(
                joinedload(PackageFinishedGood.package),
                joinedload(PackageFinishedGood.finished_good),
            )
            .all()
        )
        for pfg in pfgs:
            pfg_data = {
                "package_name": pfg.package.name if pfg.package else None,
                "finished_good_slug": pfg.finished_good.slug if pfg.finished_good else None,
                "quantity": pfg.quantity,
            }
            result.append(pfg_data)
    return result


def export_production_records_to_json() -> List[Dict]:
    """
    Export ProductionRecord records for v3.0 format.

    Production records track batch production with FIFO cost capture.

    Returns:
        List of dictionaries containing production record data
    """
    result = []
    with session_scope() as session:
        records = (
            session.query(ProductionRecord)
            .options(
                joinedload(ProductionRecord.event),
                joinedload(ProductionRecord.recipe),
            )
            .all()
        )
        for rec in records:
            rec_data = {
                "event_name": rec.event.name if rec.event else None,
                "recipe_name": rec.recipe.name if rec.recipe else None,
                "batches": rec.batches,
                "produced_at": rec.produced_at.isoformat() + "Z" if rec.produced_at else None,
                "actual_cost": float(rec.actual_cost) if rec.actual_cost else 0.0,
            }

            # Optional fields
            if rec.notes:
                rec_data["notes"] = rec.notes

            result.append(rec_data)
    return result


def export_production_runs_to_json() -> List[Dict]:
    """
    Export ProductionRun records for Feature 016.

    Production runs track batch production with event attribution.

    Returns:
        List of dictionaries containing production run data
    """
    result = []
    with session_scope() as session:
        runs = (
            session.query(ProductionRun)
            .options(
                joinedload(ProductionRun.event),
                joinedload(ProductionRun.recipe),
            )
            .all()
        )
        for run in runs:
            run_data = {
                "event_name": run.event.name if run.event else None,
                "recipe_name": run.recipe.name if run.recipe else None,
                "num_batches": run.num_batches,
                "actual_yield": run.actual_yield,
                "produced_at": run.produced_at.isoformat() + "Z" if run.produced_at else None,
            }

            # Optional fields
            if run.notes:
                run_data["notes"] = run.notes

            result.append(run_data)
    return result


def export_assembly_runs_to_json() -> List[Dict]:
    """
    Export AssemblyRun records for Feature 016.

    Assembly runs track finished good assembly with event attribution.

    Returns:
        List of dictionaries containing assembly run data
    """
    result = []
    with session_scope() as session:
        runs = (
            session.query(AssemblyRun)
            .options(
                joinedload(AssemblyRun.event),
                joinedload(AssemblyRun.finished_good),
            )
            .all()
        )
        for run in runs:
            run_data = {
                "event_name": run.event.name if run.event else None,
                "finished_good_slug": run.finished_good.slug if run.finished_good else None,
                "quantity_assembled": run.quantity_assembled,
                "assembled_at": run.assembled_at.isoformat() + "Z" if run.assembled_at else None,
            }

            # Optional fields
            if run.notes:
                run_data["notes"] = run.notes

            result.append(run_data)
    return result


def export_event_production_targets_to_json() -> List[Dict]:
    """
    Export EventProductionTarget records for Feature 016.

    Production targets track batch production goals per event.

    Returns:
        List of dictionaries containing production target data
    """
    result = []
    with session_scope() as session:
        targets = (
            session.query(EventProductionTarget)
            .options(
                joinedload(EventProductionTarget.event),
                joinedload(EventProductionTarget.recipe),
            )
            .all()
        )
        for target in targets:
            target_data = {
                "event_name": target.event.name if target.event else None,
                "recipe_name": target.recipe.name if target.recipe else None,
                "target_batches": target.target_batches,
            }

            # Optional fields
            if target.notes:
                target_data["notes"] = target.notes

            result.append(target_data)
    return result


def export_event_assembly_targets_to_json() -> List[Dict]:
    """
    Export EventAssemblyTarget records for Feature 016.

    Assembly targets track finished good assembly goals per event.

    Returns:
        List of dictionaries containing assembly target data
    """
    result = []
    with session_scope() as session:
        targets = (
            session.query(EventAssemblyTarget)
            .options(
                joinedload(EventAssemblyTarget.event),
                joinedload(EventAssemblyTarget.finished_good),
            )
            .all()
        )
        for target in targets:
            target_data = {
                "event_name": target.event.name if target.event else None,
                "finished_good_slug": target.finished_good.slug if target.finished_good else None,
                "target_quantity": target.target_quantity,
            }

            # Optional fields
            if target.notes:
                target_data["notes"] = target.notes

            result.append(target_data)
    return result


def export_all_to_json(
    file_path: str,
    entities: Optional[List[str]] = None,
) -> ExportResult:
    """
    Export data to a single JSON file in v4.1 format.

    Exports in dependency order per data-model.md:
    suppliers, ingredients, products, purchases, inventory_items,
    recipes, finished_units, finished_goods, compositions, packages,
    package_finished_goods, recipients, events, event_recipient_packages,
    production_records.

    Args:
        file_path: Path to output JSON file
        entities: Optional list of entity types to export. If None, exports all.
                  Valid values: suppliers, ingredients, products, recipes,
                  materials, material_products, etc.

    Returns:
        ExportResult with export statistics including per-entity counts
    """
    try:
        # Get all data - use session scope to eagerly load products
        with session_scope() as session:
            # Eagerly load products to avoid detached instance errors
            ingredients = session.query(Ingredient).options(joinedload(Ingredient.products)).all()
            # Make objects accessible outside session by accessing all lazy-loaded attributes
            for ing in ingredients:
                _ = ing.products  # Access to ensure loaded

        recipes = recipe_service.get_all_recipes()
        packages = package_service.get_all_packages()
        recipients = recipient_service.get_all_recipients()
        # Events are fetched later in a session scope with their relationships

        # Get v3.0 entity exports
        finished_units_data = export_finished_units_to_json()
        compositions_data = export_compositions_to_json()
        package_finished_goods_data = export_package_finished_goods_to_json()
        production_records_data = export_production_records_to_json()

        # Feature 016: Production and assembly runs with event attribution
        production_runs_data = export_production_runs_to_json()
        assembly_runs_data = export_assembly_runs_to_json()
        event_production_targets_data = export_event_production_targets_to_json()
        event_assembly_targets_data = export_event_assembly_targets_to_json()

        # Build combined export data - v4.0 format (Feature 040: F037 recipe fields, F039 event output_mode)
        export_data = {
            "version": "4.1",  # Feature 045: Cost field removal from definitions
            "exported_at": utc_now().isoformat() + "Z",
            "application": "bake-tracker",
            "suppliers": [],  # Feature 027: Suppliers before products (products reference suppliers)
            "ingredients": [],
            "products": [],
            "purchases": [],
            "inventory_items": [],
            "recipes": [],
            "finished_units": finished_units_data,
            "finished_goods": [],
            "compositions": compositions_data,
            "packages": [],
            "package_finished_goods": package_finished_goods_data,
            "recipients": [],
            "events": [],
            "event_recipient_packages": [],
            "event_production_targets": event_production_targets_data,
            "event_assembly_targets": event_assembly_targets_data,
            "production_records": production_records_data,
            "production_runs": production_runs_data,
            "assembly_runs": assembly_runs_data,
            # Material entities (Feature 047)
            "material_categories": [],
            "material_subcategories": [],
            "materials": [],
            "material_products": [],
            "material_units": [],  # Feature 084
            # Planning entities (Feature 068)
            "event_recipes": [],
            "event_finished_goods": [],
            "batch_decisions": [],
            "plan_amendments": [],
        }

        # Add ingredients (NEW SCHEMA: generic ingredient definitions)
        for ingredient in ingredients:
            ingredient_data = {
                "display_name": ingredient.display_name,
                "slug": ingredient.slug,
                "category": ingredient.category,
                # Feature 031: Hierarchy fields
                "hierarchy_level": ingredient.hierarchy_level,
            }

            # Feature 031: Parent reference uses slug for portability
            if ingredient.parent_ingredient_id is not None:
                # Look up parent's slug for export (more portable than ID)
                parent = next(
                    (i for i in ingredients if i.id == ingredient.parent_ingredient_id), None
                )
                if parent:
                    ingredient_data["parent_slug"] = parent.slug

            # Optional fields
            if ingredient.description:
                ingredient_data["description"] = ingredient.description
            if ingredient.notes:
                ingredient_data["notes"] = ingredient.notes

            # Density fields (4-field model: volume_value, volume_unit, weight_value, weight_unit)
            if ingredient.density_volume_value is not None:
                ingredient_data["density_volume_value"] = ingredient.density_volume_value
            if ingredient.density_volume_unit:
                ingredient_data["density_volume_unit"] = ingredient.density_volume_unit
            if ingredient.density_weight_value is not None:
                ingredient_data["density_weight_value"] = ingredient.density_weight_value
            if ingredient.density_weight_unit:
                ingredient_data["density_weight_unit"] = ingredient.density_weight_unit

            if ingredient.moisture_pct:
                ingredient_data["moisture_pct"] = ingredient.moisture_pct
            if ingredient.allergens:
                ingredient_data["allergens"] = ingredient.allergens
            if ingredient.foodon_id:
                ingredient_data["foodon_id"] = ingredient.foodon_id
            if ingredient.foodex2_code:
                ingredient_data["foodex2_code"] = ingredient.foodex2_code
            if ingredient.langual_terms:
                ingredient_data["langual_terms"] = ingredient.langual_terms
            if ingredient.fdc_ids:
                ingredient_data["fdc_ids"] = ingredient.fdc_ids

            export_data["ingredients"].append(ingredient_data)

        # Feature 027: Add suppliers (before products, which may reference them)
        # Feature 050: Build supplier lookup map for product export
        supplier_lookup = {}  # supplier_id -> {slug, display_name}
        with session_scope() as session:
            suppliers = session.query(Supplier).all()
            for supplier in suppliers:
                supplier_data = {
                    "id": supplier.id,
                    "uuid": supplier.uuid,
                    "slug": supplier.slug,  # Feature 050: Portable identifier
                    "name": supplier.name,
                    "supplier_type": supplier.supplier_type,  # Feature 050
                    "city": supplier.city,
                    "state": supplier.state,
                    "zip_code": supplier.zip_code,
                    "is_active": supplier.is_active,
                }

                # Optional fields
                if supplier.website_url:
                    supplier_data["website_url"] = supplier.website_url
                if supplier.street_address:
                    supplier_data["street_address"] = supplier.street_address
                if supplier.notes:
                    supplier_data["notes"] = supplier.notes

                # Timestamps
                if supplier.created_at:
                    supplier_data["created_at"] = supplier.created_at.isoformat()
                if supplier.updated_at:
                    supplier_data["updated_at"] = supplier.updated_at.isoformat()

                export_data["suppliers"].append(supplier_data)

                # Feature 050: Store for product export lookup
                supplier_lookup[supplier.id] = {
                    "slug": supplier.slug,
                    "display_name": supplier.display_name,
                }

        # Add products (brand/package-specific versions)
        for ingredient in ingredients:
            for product in ingredient.products:
                product_data = {
                    "ingredient_slug": ingredient.slug,
                    "package_unit": product.package_unit,
                    "package_unit_quantity": product.package_unit_quantity,
                }

                # Optional fields
                if product.brand:
                    product_data["brand"] = product.brand
                if product.product_name:
                    product_data["product_name"] = product.product_name
                if product.package_size:
                    product_data["package_size"] = product.package_size
                if product.package_type:
                    product_data["package_type"] = product.package_type
                if product.upc_code:
                    product_data["upc_code"] = product.upc_code
                if product.supplier:
                    product_data["supplier"] = product.supplier
                if product.supplier_sku:
                    product_data["supplier_sku"] = product.supplier_sku
                if product.gtin:
                    product_data["gtin"] = product.gtin
                if product.brand_owner:
                    product_data["brand_owner"] = product.brand_owner
                if product.gpc_brick_code:
                    product_data["gpc_brick_code"] = product.gpc_brick_code
                if product.net_content_value:
                    product_data["net_content_value"] = product.net_content_value
                if product.net_content_uom:
                    product_data["net_content_uom"] = product.net_content_uom
                if product.country_of_sale:
                    product_data["country_of_sale"] = product.country_of_sale
                if product.off_id:
                    product_data["off_id"] = product.off_id
                if product.preferred:
                    product_data["preferred"] = product.preferred
                if product.notes:
                    product_data["notes"] = product.notes

                # Feature 027: New fields
                if product.preferred_supplier_id:
                    product_data["preferred_supplier_id"] = product.preferred_supplier_id
                    # Feature 050: Add slug-based supplier reference
                    supplier_info = supplier_lookup.get(product.preferred_supplier_id)
                    if supplier_info:
                        product_data["preferred_supplier_slug"] = supplier_info["slug"]
                        product_data["preferred_supplier_name"] = supplier_info["display_name"]
                    else:
                        # Supplier was deleted but ID still referenced
                        product_data["preferred_supplier_slug"] = None
                        product_data["preferred_supplier_name"] = None
                else:
                    # Feature 050: Include null fields for products without supplier
                    product_data["preferred_supplier_slug"] = None
                    product_data["preferred_supplier_name"] = None
                # Always include is_hidden for round-trip (defaults to False)
                product_data["is_hidden"] = product.is_hidden

                export_data["products"].append(product_data)

        # Add inventory items (actual inventory lots)
        with session_scope() as session:
            inventory_items = session.query(InventoryItem).join(Product).join(Ingredient).all()
            for item in inventory_items:
                item_data = {
                    "ingredient_slug": item.product.ingredient.slug,
                    "product_brand": item.product.brand or "",
                    "quantity": item.quantity,
                    "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
                }

                # Product identification fields (for unique lookup during import)
                if item.product.product_name:
                    item_data["product_name"] = item.product.product_name
                if item.product.package_size:
                    item_data["package_size"] = item.product.package_size
                if item.product.package_unit:
                    item_data["package_unit"] = item.product.package_unit
                if item.product.package_unit_quantity is not None:
                    item_data["package_unit_quantity"] = item.product.package_unit_quantity

                # Optional fields
                if item.expiration_date:
                    item_data["expiration_date"] = item.expiration_date.isoformat()
                if item.location:
                    item_data["location"] = item.location
                if item.notes:
                    item_data["notes"] = item.notes

                # Feature 027: purchase_id FK (may be None for old data)
                if item.purchase_id:
                    item_data["purchase_id"] = item.purchase_id

                export_data["inventory_items"].append(item_data)

        # Add purchases (price history)
        # Feature 027: Now uses supplier_id FK instead of supplier string
        with session_scope() as session:
            purchases = (
                session.query(Purchase)
                .join(Product)
                .join(Ingredient)
                .options(joinedload(Purchase.supplier))
                .all()
            )
            for purchase in purchases:
                purchase_data = {
                    "id": purchase.id,
                    "uuid": purchase.uuid,
                    "product_id": purchase.product_id,
                    "supplier_id": purchase.supplier_id,
                    "ingredient_slug": purchase.product.ingredient.slug,
                    "product_brand": purchase.product.brand or "",
                    "purchase_date": (
                        purchase.purchase_date.isoformat() if purchase.purchase_date else None
                    ),
                    "quantity_purchased": purchase.quantity_purchased,
                    # Use unit_price per the Purchase model (not unit_cost)
                    "unit_price": str(purchase.unit_price) if purchase.unit_price else None,
                }

                # Product identification fields (for unique lookup during import)
                if purchase.product.product_name:
                    purchase_data["product_name"] = purchase.product.product_name
                if purchase.product.package_size:
                    purchase_data["package_size"] = purchase.product.package_size
                if purchase.product.package_unit:
                    purchase_data["package_unit"] = purchase.product.package_unit

                # Optional fields
                if purchase.notes:
                    purchase_data["notes"] = purchase.notes

                # Timestamps
                if purchase.created_at:
                    purchase_data["created_at"] = purchase.created_at.isoformat()

                export_data["purchases"].append(purchase_data)

        # Add recipes
        for recipe in recipes:
            # F056: yield_quantity, yield_unit, yield_description removed
            # Yield data is now in FinishedUnit records (exported as finished_units)
            recipe_data = {
                "name": recipe.name,
                "category": recipe.category,
            }

            if recipe.source:
                recipe_data["source"] = recipe.source
            if recipe.estimated_time_minutes:
                recipe_data["estimated_time_minutes"] = recipe.estimated_time_minutes
            if recipe.notes:
                recipe_data["notes"] = recipe.notes

            # Feature 040 / F037: Export variant fields
            # T001: Export base_recipe_slug (convert FK to name-based slug for portability)
            # Note: Recipe model doesn't have a slug column, so we use name as identifier
            recipe_data["base_recipe_slug"] = None
            if recipe.base_recipe_id and recipe.base_recipe:
                # Generate slug from recipe name (lowercase, spaces to underscores)
                recipe_data["base_recipe_slug"] = recipe.base_recipe.name.lower().replace(" ", "_")

            # T002: Export variant_name
            recipe_data["variant_name"] = recipe.variant_name

            # T003: Export is_production_ready
            recipe_data["is_production_ready"] = recipe.is_production_ready

            # T004: Export finished_units[] with yield_mode
            recipe_data["finished_units"] = []
            for fu in recipe.finished_units:
                fu_data = {
                    "slug": fu.slug,
                    "name": fu.display_name,
                    "yield_mode": fu.yield_mode.value if fu.yield_mode else None,
                }
                # Include yield quantity fields based on mode
                if fu.yield_mode:
                    if fu.yield_mode.value == "discrete_count":
                        if fu.items_per_batch is not None:
                            fu_data["unit_yield_quantity"] = fu.items_per_batch
                        if fu.item_unit:
                            fu_data["unit_yield_unit"] = fu.item_unit
                    elif fu.yield_mode.value == "batch_portion":
                        if fu.batch_percentage is not None:
                            fu_data["unit_yield_quantity"] = float(fu.batch_percentage)
                        if fu.portion_description:
                            fu_data["unit_yield_unit"] = fu.portion_description
                recipe_data["finished_units"].append(fu_data)

            recipe_data["ingredients"] = []
            for ri in recipe.recipe_ingredients:
                # Get ingredient from the recipe ingredient relationship
                ingredient = ri.ingredient

                ingredient_data = {
                    "ingredient_slug": (
                        ingredient.slug
                        if ingredient.slug
                        else ingredient.display_name.lower().replace(" ", "_")
                    ),
                    "quantity": ri.quantity,
                    "unit": ri.unit,
                }
                if ri.notes:
                    ingredient_data["notes"] = ri.notes

                recipe_data["ingredients"].append(ingredient_data)

            # Add recipe components (sub-recipes)
            recipe_data["components"] = []
            for comp in recipe.recipe_components:
                component_data = {
                    "recipe_name": comp.component_recipe.name if comp.component_recipe else None,
                    "quantity": comp.quantity,
                }
                if comp.notes:
                    component_data["notes"] = comp.notes

                recipe_data["components"].append(component_data)

            export_data["recipes"].append(recipe_data)

        # Add finished goods (v3.0: assembly-focused, slug-based)
        with session_scope() as session:
            finished_goods = (
                session.query(FinishedGood).options(joinedload(FinishedGood.components)).all()
            )
            for fg in finished_goods:
                fg_data = {
                    "slug": fg.slug,
                    "display_name": fg.display_name,
                    "assembly_type": fg.assembly_type.value if fg.assembly_type else None,
                }

                if fg.description:
                    fg_data["description"] = fg.description
                if fg.packaging_instructions:
                    fg_data["packaging_instructions"] = fg.packaging_instructions
                if fg.notes:
                    fg_data["notes"] = fg.notes

                export_data["finished_goods"].append(fg_data)

        # NOTE: bundles removed in v3.0 - replaced by compositions (already populated above)

        # Add packages (v3.0: no embedded bundles - use package_finished_goods)
        for package in packages:
            package_data = {
                "name": package.name,
                "is_template": package.is_template,
            }
            if package.description:
                package_data["description"] = package.description
            if package.notes:
                package_data["notes"] = package.notes

            export_data["packages"].append(package_data)

        # Add recipients
        for recipient in recipients:
            recipient_data = {
                "name": recipient.name,
            }
            if recipient.household_name:
                recipient_data["household_name"] = recipient.household_name
            if recipient.address:
                recipient_data["address"] = recipient.address
            if recipient.notes:
                recipient_data["notes"] = recipient.notes

            export_data["recipients"].append(recipient_data)

        # Add events (v3.0: no embedded assignments - use event_recipient_packages)
        # Fetch events within session scope to support lazy-loaded relationships
        with session_scope() as session:
            events = event_service.get_all_events(session=session)
            for event in events:
                event_data = {
                    "name": event.name,
                    "event_date": event.event_date.isoformat(),
                    "year": event.year,
                }
                if event.notes:
                    event_data["notes"] = event.notes

                # Feature 040 / F039: Export output_mode
                event_data["output_mode"] = event.output_mode.value if event.output_mode else None

                # Feature 068: Export planning fields
                if event.expected_attendees is not None:
                    event_data["expected_attendees"] = event.expected_attendees
                event_data["plan_state"] = event.plan_state.value if event.plan_state else "draft"

                export_data["events"].append(event_data)

                # Populate event_recipient_packages separately (v3.2 format with both status fields)
                for assignment in event.event_recipient_packages:
                    assignment_data = {
                        "event_name": event.name,
                        "recipient_name": assignment.recipient.name,
                        "package_name": assignment.package.name,
                        "quantity": assignment.quantity,
                        "status": assignment.status.value if assignment.status else "pending",
                        "fulfillment_status": assignment.fulfillment_status,  # Feature 016
                    }
                    if assignment.delivered_to:
                        assignment_data["delivered_to"] = assignment.delivered_to
                    if assignment.notes:
                        assignment_data["notes"] = assignment.notes

                    export_data["event_recipient_packages"].append(assignment_data)

        # Add material categories
        with session_scope() as session:
            categories = session.query(MaterialCategory).all()
            for c in categories:
                export_data["material_categories"].append(
                    {
                        "uuid": str(c.uuid) if c.uuid else None,
                        "name": c.name,
                        "slug": c.slug,
                        "description": c.description,
                        "sort_order": c.sort_order,
                    }
                )

        # Add material subcategories
        with session_scope() as session:
            subcategories = (
                session.query(MaterialSubcategory)
                .options(joinedload(MaterialSubcategory.category))
                .all()
            )
            for s in subcategories:
                export_data["material_subcategories"].append(
                    {
                        "uuid": str(s.uuid) if s.uuid else None,
                        "category_slug": s.category.slug if s.category else None,
                        "name": s.name,
                        "slug": s.slug,
                        "description": s.description,
                        "sort_order": s.sort_order,
                    }
                )

        # Add materials
        with session_scope() as session:
            materials = session.query(Material).options(joinedload(Material.subcategory)).all()
            for m in materials:
                export_data["materials"].append(
                    {
                        "uuid": str(m.uuid) if m.uuid else None,
                        "subcategory_slug": m.subcategory.slug if m.subcategory else None,
                        "name": m.name,
                        "slug": m.slug,
                        "base_unit_type": m.base_unit_type,
                        "description": m.description,
                    }
                )

        # Add material products
        with session_scope() as session:
            mat_products = (
                session.query(MaterialProduct)
                .options(
                    joinedload(MaterialProduct.material),
                    joinedload(MaterialProduct.supplier),
                )
                .all()
            )
            for p in mat_products:
                # Feature 058: Removed current_inventory, weighted_avg_cost, inventory_value
                # These are now tracked via MaterialInventoryItem (FIFO)
                export_data["material_products"].append(
                    {
                        "uuid": str(p.uuid) if p.uuid else None,
                        "material_slug": p.material.slug if p.material else None,
                        "name": p.name,
                        "slug": p.slug,
                        "brand": p.brand,
                        "package_quantity": p.package_quantity,
                        "package_unit": p.package_unit,
                        "quantity_in_base_units": p.quantity_in_base_units,
                        "supplier_slug": p.supplier.slug if p.supplier else None,
                        "sku": p.sku,
                        "is_hidden": p.is_hidden,
                        "notes": p.notes,
                    }
                )

        # Add material units (Feature 084)
        with session_scope() as session:
            mat_units = (
                session.query(MaterialUnit)
                .options(joinedload(MaterialUnit.material_product))
                .all()
            )
            for u in mat_units:
                export_data["material_units"].append(
                    {
                        "uuid": str(u.uuid) if u.uuid else None,
                        # Feature 084: Use material_product_slug (not material_slug)
                        "material_product_slug": (
                            u.material_product.slug if u.material_product else None
                        ),
                        "name": u.name,
                        "slug": u.slug,
                        "quantity_per_unit": u.quantity_per_unit,
                        "description": u.description,
                    }
                )

        # Add planning entities (Feature 068)
        with session_scope() as session:
            # Build event name lookup for FK references
            events_list = event_service.get_all_events(session=session)
            event_id_to_name = {e.id: e.name for e in events_list}

            # Build recipe name lookup
            recipes_list = session.query(Recipe).all()
            recipe_id_to_name = {r.id: r.name for r in recipes_list}

            # Build finished_good name lookup
            fgs_list = session.query(FinishedGood).all()
            fg_id_to_name = {fg.id: fg.display_name for fg in fgs_list}

            # Build finished_unit name lookup
            fus_list = session.query(FinishedUnit).all()
            fu_id_to_name = {fu.id: fu.display_name for fu in fus_list}

            # Export event_recipes
            event_recipes = session.query(EventRecipe).all()
            for er in event_recipes:
                export_data["event_recipes"].append({
                    "event_name": event_id_to_name.get(er.event_id),
                    "recipe_name": recipe_id_to_name.get(er.recipe_id),
                    "created_at": er.created_at.isoformat() if er.created_at else None,
                })

            # Export event_finished_goods
            event_fgs = session.query(EventFinishedGood).all()
            for efg in event_fgs:
                export_data["event_finished_goods"].append({
                    "event_name": event_id_to_name.get(efg.event_id),
                    "finished_good_name": fg_id_to_name.get(efg.finished_good_id),
                    "quantity": efg.quantity,
                    "created_at": efg.created_at.isoformat() if efg.created_at else None,
                    "updated_at": efg.updated_at.isoformat() if efg.updated_at else None,
                })

            # Export batch_decisions
            batch_decisions = session.query(BatchDecision).all()
            for bd in batch_decisions:
                bd_data = {
                    "event_name": event_id_to_name.get(bd.event_id),
                    "recipe_name": recipe_id_to_name.get(bd.recipe_id),
                    "batches": bd.batches,
                    "created_at": bd.created_at.isoformat() if bd.created_at else None,
                    "updated_at": bd.updated_at.isoformat() if bd.updated_at else None,
                }
                if bd.finished_unit_id:
                    bd_data["finished_unit_name"] = fu_id_to_name.get(bd.finished_unit_id)
                export_data["batch_decisions"].append(bd_data)

            # Export plan_amendments
            plan_amendments = session.query(PlanAmendment).all()
            for pa in plan_amendments:
                export_data["plan_amendments"].append({
                    "event_name": event_id_to_name.get(pa.event_id),
                    "amendment_type": pa.amendment_type.value if pa.amendment_type else None,
                    "amendment_data": pa.amendment_data,
                    "reason": pa.reason,
                    "created_at": pa.created_at.isoformat() if pa.created_at else None,
                })

        # Filter entities if selective export requested
        if entities is not None:
            # Map UI entity names to export_data keys
            entity_mapping = {
                "suppliers": ["suppliers"],
                "ingredients": ["ingredients"],
                "products": ["products"],
                "recipes": ["recipes", "finished_units", "compositions"],
                "materials": ["material_categories", "material_subcategories", "materials"],
                # Feature 084: Include material_units with material_products
                "material_products": ["material_products", "material_units"],
            }

            # Build set of keys to keep
            keys_to_keep = {"version", "exported_at", "application"}
            for entity in entities:
                if entity in entity_mapping:
                    keys_to_keep.update(entity_mapping[entity])

            # Clear data for unselected entities
            for key in list(export_data.keys()):
                if key not in keys_to_keep and isinstance(export_data[key], list):
                    export_data[key] = []

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        # Calculate total records and build entity counts
        total_records = (
            len(export_data["suppliers"])  # Feature 027
            + len(export_data["ingredients"])
            + len(export_data["products"])
            + len(export_data["purchases"])
            + len(export_data["inventory_items"])
            + len(export_data["recipes"])
            + len(export_data["finished_units"])
            + len(export_data["finished_goods"])
            + len(export_data["compositions"])
            + len(export_data["packages"])
            + len(export_data["package_finished_goods"])
            + len(export_data["recipients"])
            + len(export_data["events"])
            + len(export_data["event_recipient_packages"])
            + len(export_data["event_production_targets"])
            + len(export_data["event_assembly_targets"])
            + len(export_data["production_records"])
            + len(export_data["production_runs"])
            + len(export_data["assembly_runs"])
            # Material entities (Feature 047)
            + len(export_data["material_categories"])
            + len(export_data["material_subcategories"])
            + len(export_data["materials"])
            + len(export_data["material_products"])
            + len(export_data["material_units"])  # Feature 084
            # Planning entities (Feature 068)
            + len(export_data["event_recipes"])
            + len(export_data["event_finished_goods"])
            + len(export_data["batch_decisions"])
            + len(export_data["plan_amendments"])
        )

        result = ExportResult(file_path, total_records)

        # Add per-entity counts
        result.add_entity_count("suppliers", len(export_data["suppliers"]))  # Feature 027
        result.add_entity_count("ingredients", len(export_data["ingredients"]))
        result.add_entity_count("products", len(export_data["products"]))
        result.add_entity_count("purchases", len(export_data["purchases"]))
        result.add_entity_count("inventory_items", len(export_data["inventory_items"]))
        result.add_entity_count("recipes", len(export_data["recipes"]))
        result.add_entity_count("finished_units", len(export_data["finished_units"]))
        result.add_entity_count("finished_goods", len(export_data["finished_goods"]))
        result.add_entity_count("compositions", len(export_data["compositions"]))
        result.add_entity_count("packages", len(export_data["packages"]))
        result.add_entity_count(
            "package_finished_goods", len(export_data["package_finished_goods"])
        )
        result.add_entity_count("recipients", len(export_data["recipients"]))
        result.add_entity_count("events", len(export_data["events"]))
        result.add_entity_count(
            "event_recipient_packages", len(export_data["event_recipient_packages"])
        )
        result.add_entity_count(
            "event_production_targets", len(export_data["event_production_targets"])
        )
        result.add_entity_count(
            "event_assembly_targets", len(export_data["event_assembly_targets"])
        )
        result.add_entity_count("production_records", len(export_data["production_records"]))
        result.add_entity_count("production_runs", len(export_data["production_runs"]))
        result.add_entity_count("assembly_runs", len(export_data["assembly_runs"]))
        # Material entities (Feature 047)
        result.add_entity_count("material_categories", len(export_data["material_categories"]))
        result.add_entity_count(
            "material_subcategories", len(export_data["material_subcategories"])
        )
        result.add_entity_count("materials", len(export_data["materials"]))
        result.add_entity_count("material_products", len(export_data["material_products"]))
        result.add_entity_count("material_units", len(export_data["material_units"]))  # F084
        # Planning entities (Feature 068)
        result.add_entity_count("event_recipes", len(export_data["event_recipes"]))
        result.add_entity_count("event_finished_goods", len(export_data["event_finished_goods"]))
        result.add_entity_count("batch_decisions", len(export_data["batch_decisions"]))
        result.add_entity_count("plan_amendments", len(export_data["plan_amendments"]))

        return result

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


# ============================================================================
# v3.2 Import Functions
# ============================================================================
# Note: Legacy individual entity import functions (import_ingredients_from_json,
# import_recipes_from_json, etc.) have been removed. Use import_all_from_json_v3()
# for all imports - it accepts only v3.2 format files.


# Placeholder to maintain structure - legacy functions removed
def _legacy_import_removed():
    """Legacy individual import functions removed - use import_all_from_json_v3() instead."""
    raise NotImplementedError("Legacy import functions removed. Use import_all_from_json_v3()")


# ============================================================================
# v3.0 Import Functions - New Entities
# ============================================================================


class ImportVersionError(Exception):
    """Raised when import file has incompatible version."""

    pass


def _clear_all_tables(session) -> None:
    """
    Clear all tables in reverse dependency order for Replace mode.

    Must be called within an active session transaction.

    Args:
        session: SQLAlchemy session
    """
    from src.models.recipe import Recipe, RecipeIngredient
    from src.models.event import Event, EventRecipientPackage
    from src.models.recipient import Recipient

    # Tables in REVERSE dependency order to avoid FK violations
    # Order: dependent tables cleared first, base tables cleared last
    # Feature 027: Added Supplier (cleared after Products since Products reference Suppliers)
    # Feature 068: Added planning tables (cleared before Event)
    tables_to_clear = [
        ProductionRecord,
        EventRecipientPackage,
        # Feature 068 planning tables (depend on Event, cleared before Event)
        PlanAmendment,
        BatchDecision,
        EventFinishedGood,
        EventRecipe,
        Event,
        Recipient,
        PackageFinishedGood,
        Package,
        Composition,
        FinishedGood,
        FinishedUnit,
        RecipeIngredient,
        Recipe,
        InventoryItem,
        Purchase,
        Product,
        Supplier,  # Feature 027: Products reference suppliers, purchases reference suppliers
        Ingredient,
    ]

    for table in tables_to_clear:
        session.query(table).delete()


def import_finished_units_from_json(
    data: List[Dict], session, skip_duplicates: bool = True
) -> ImportResult:
    """
    Import FinishedUnit records from v3.0 format data.

    Args:
        data: List of finished unit dictionaries
        session: SQLAlchemy session
        skip_duplicates: If True, skip records that already exist

    Returns:
        ImportResult with import statistics
    """
    from src.models.recipe import Recipe

    result = ImportResult()

    for record in data:
        try:
            slug = record.get("slug", "")
            display_name = record.get("display_name", "")
            recipe_slug = record.get("recipe_slug", "")

            if not slug:
                result.add_error("finished_unit", "unknown", "Missing slug")
                continue

            if not display_name:
                result.add_error("finished_unit", slug, "Missing display_name")
                continue

            if not recipe_slug:
                result.add_error("finished_unit", slug, "Missing recipe_slug")
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = session.query(FinishedUnit).filter_by(slug=slug).first()
                if existing:
                    result.add_skip("finished_unit", slug, "Already exists")
                    continue

            # Resolve recipe reference - Recipe model doesn't have slug field,
            # so convert recipe_slug to name format for lookup
            recipe_name_from_slug = recipe_slug.replace("_", " ").title()
            recipe = session.query(Recipe).filter_by(name=recipe_name_from_slug).first()

            if not recipe:
                result.add_error("finished_unit", slug, f"Recipe not found: {recipe_slug}")
                continue

            # Create finished unit
            from src.models.finished_unit import YieldMode

            yield_mode_str = record.get("yield_mode", "discrete_count")
            yield_mode = YieldMode(yield_mode_str)

            fu = FinishedUnit(
                slug=slug,
                display_name=display_name,
                recipe_id=recipe.id,
                yield_mode=yield_mode,
                items_per_batch=record.get("items_per_batch"),
                item_unit=record.get("item_unit"),
                batch_percentage=record.get("batch_percentage"),
                portion_description=record.get("portion_description"),
                category=record.get("category"),
                description=record.get("description"),
                production_notes=record.get("production_notes"),
                notes=record.get("notes"),
            )

            session.add(fu)
            result.add_success("finished_unit")

        except Exception as e:
            result.add_error("finished_unit", record.get("slug", "unknown"), str(e))

    return result


def import_compositions_from_json(
    data: List[Dict], session, skip_duplicates: bool = True
) -> ImportResult:
    """
    Import Composition records from v3.0/v3.1 format data.

    Feature 011: Supports package_id and packaging_product_id for packaging compositions.
    Feature 084: Supports material_unit_slug for material compositions.
                 Deprecated material_slug is rejected with error and migration guidance.

    Args:
        data: List of composition dictionaries
        session: SQLAlchemy session
        skip_duplicates: If True, skip records that already exist

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    for record in data:
        try:
            finished_good_slug = record.get("finished_good_slug")
            package_name = record.get("package_name")  # Feature 011
            finished_unit_slug = record.get("finished_unit_slug")
            finished_good_component_slug = record.get("finished_good_component_slug")
            packaging_ingredient_slug = record.get("packaging_ingredient_slug")  # Feature 011
            packaging_product_brand = record.get("packaging_product_brand")  # Feature 011
            material_unit_slug = record.get("material_unit_slug")  # Feature 084
            quantity = float(record.get("component_quantity", 1.0))  # Ensure float

            # Feature 084: Check for deprecated material_slug (old format)
            deprecated_material_slug = record.get("material_slug")
            if deprecated_material_slug:
                parent_name = finished_good_slug or package_name or "unknown"
                result.add_skip(
                    "composition",
                    parent_name,
                    f"Skipped: material_slug='{deprecated_material_slug}' is deprecated. "
                    "Convert to material_unit_slug using migration script (WP09).",
                )
                continue

            # Validate quantity
            if quantity <= 0:
                result.add_error("composition", "unknown", "Quantity must be greater than 0")
                continue

            # Parent XOR validation: must have exactly one of assembly_id or package_id
            if finished_good_slug and package_name:
                result.add_error(
                    "composition",
                    "unknown",
                    "Composition must have exactly one parent (finished_good_slug or package_name)",
                )
                continue
            if not finished_good_slug and not package_name:
                result.add_error(
                    "composition",
                    "unknown",
                    "Composition must have exactly one parent (finished_good_slug or package_name)",
                )
                continue

            # Component XOR validation: must have exactly one component type (4-way)
            # Feature 084: Added material_unit_slug, removed material_slug
            component_refs = [
                finished_unit_slug,
                finished_good_component_slug,
                packaging_ingredient_slug,
                material_unit_slug,
            ]
            non_null_components = [x for x in component_refs if x is not None]
            if len(non_null_components) != 1:
                result.add_error(
                    "composition",
                    finished_good_slug or package_name,
                    "Composition must have exactly one component type",
                )
                continue

            # Resolve parent reference
            assembly_id = None
            package_id = None

            if finished_good_slug:
                assembly = session.query(FinishedGood).filter_by(slug=finished_good_slug).first()
                if not assembly:
                    result.add_error(
                        "composition",
                        finished_good_slug,
                        f"Assembly not found: {finished_good_slug}",
                    )
                    continue
                assembly_id = assembly.id
            else:
                package = session.query(Package).filter_by(name=package_name).first()
                if not package:
                    result.add_error(
                        "composition", package_name, f"Package not found: {package_name}"
                    )
                    continue
                package_id = package.id

            # Resolve component reference
            finished_unit_id = None
            finished_good_id = None
            packaging_product_id = None
            material_unit_id = None  # Feature 084

            if finished_unit_slug:
                fu = session.query(FinishedUnit).filter_by(slug=finished_unit_slug).first()
                # Also try lookup via recipe_slug (slug might reference recipe, not finished_unit)
                if not fu:
                    from src.models.recipe import Recipe

                    # Convert slug to recipe name format
                    recipe_name = finished_unit_slug.replace("_", " ").title()
                    recipe = session.query(Recipe).filter_by(name=recipe_name).first()
                    if recipe:
                        fu = session.query(FinishedUnit).filter_by(recipe_id=recipe.id).first()
                if not fu:
                    result.add_error(
                        "composition",
                        finished_good_slug or package_name,
                        f"FinishedUnit not found: {finished_unit_slug}",
                    )
                    continue
                finished_unit_id = fu.id
            elif finished_good_component_slug:
                fg = (
                    session.query(FinishedGood).filter_by(slug=finished_good_component_slug).first()
                )
                if not fg:
                    result.add_error(
                        "composition",
                        finished_good_slug or package_name,
                        f"FinishedGood component not found: {finished_good_component_slug}",
                    )
                    continue
                finished_good_id = fg.id
            elif packaging_ingredient_slug:
                # Feature 011: Resolve packaging product by ingredient slug + brand
                ingredient = (
                    session.query(Ingredient).filter_by(slug=packaging_ingredient_slug).first()
                )
                if not ingredient:
                    result.add_error(
                        "composition",
                        finished_good_slug or package_name,
                        f"Packaging ingredient not found: {packaging_ingredient_slug}",
                    )
                    continue
                # Find product by ingredient and brand
                product_query = session.query(Product).filter_by(ingredient_id=ingredient.id)
                if packaging_product_brand:
                    product_query = product_query.filter_by(brand=packaging_product_brand)
                product = product_query.first()
                if not product:
                    result.add_error(
                        "composition",
                        finished_good_slug or package_name,
                        f"Packaging product not found for ingredient {packaging_ingredient_slug}",
                    )
                    continue
                packaging_product_id = product.id
            elif material_unit_slug:
                # Feature 084: Resolve material unit by slug
                mat_unit = session.query(MaterialUnit).filter_by(slug=material_unit_slug).first()
                if not mat_unit:
                    result.add_error(
                        "composition",
                        finished_good_slug or package_name,
                        f"MaterialUnit not found: {material_unit_slug}",
                    )
                    continue
                material_unit_id = mat_unit.id

            # Check for duplicate
            if skip_duplicates:
                existing = (
                    session.query(Composition)
                    .filter_by(
                        assembly_id=assembly_id,
                        package_id=package_id,
                        finished_unit_id=finished_unit_id,
                        finished_good_id=finished_good_id,
                        packaging_product_id=packaging_product_id,
                        material_unit_id=material_unit_id,  # Feature 084
                    )
                    .first()
                )
                if existing:
                    parent_name = finished_good_slug or package_name
                    component_name = (
                        finished_unit_slug
                        or finished_good_component_slug
                        or packaging_ingredient_slug
                        or material_unit_slug  # Feature 084
                    )
                    result.add_skip(
                        "composition", f"{parent_name}->{component_name}", "Already exists"
                    )
                    continue

            # Create composition
            comp = Composition(
                assembly_id=assembly_id,
                package_id=package_id,  # Feature 011
                finished_unit_id=finished_unit_id,
                finished_good_id=finished_good_id,
                packaging_product_id=packaging_product_id,  # Feature 011
                material_unit_id=material_unit_id,  # Feature 084
                component_quantity=quantity,
                sort_order=record.get("sort_order", 0),
                component_notes=record.get("notes"),
                is_generic=record.get("is_generic", False),  # Feature 026
            )

            session.add(comp)
            session.flush()  # Get composition ID for assignments
            result.add_success("composition")

            # Feature 026: Import assignments for generic compositions
            assignments_data = record.get("assignments", [])
            if assignments_data and record.get("is_generic"):
                for assign_record in assignments_data:
                    inv_item_id = assign_record.get("inventory_item_id")
                    qty = assign_record.get("quantity_assigned", 0)

                    # Check if inventory item exists
                    inv_item = session.query(InventoryItem).filter_by(id=inv_item_id).first()
                    if not inv_item:
                        # Warn but don't fail - inventory items may not exist in target DB
                        result.add_warning(
                            "composition_assignment",
                            f"composition_{comp.id}",
                            f"Inventory item {inv_item_id} not found - assignment skipped",
                        )
                        continue

                    # Create assignment
                    assignment = CompositionAssignment(
                        composition_id=comp.id,
                        inventory_item_id=inv_item_id,
                        quantity_assigned=qty,
                    )
                    session.add(assignment)

        except Exception as e:
            parent_name = (
                record.get("finished_good_slug") or record.get("package_name") or "unknown"
            )
            result.add_error("composition", parent_name, str(e))

    return result


def import_package_finished_goods_from_json(
    data: List[Dict], session, skip_duplicates: bool = True
) -> ImportResult:
    """
    Import PackageFinishedGood records from v3.0 format data.

    Args:
        data: List of package-finished-good link dictionaries
        session: SQLAlchemy session
        skip_duplicates: If True, skip records that already exist

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    for record in data:
        try:
            package_slug = record.get("package_slug", "")
            finished_good_slug = record.get("finished_good_slug", "")
            quantity = record.get("quantity", 1)

            if not package_slug or not finished_good_slug:
                result.add_error(
                    "package_finished_good", "unknown", "Missing package_slug or finished_good_slug"
                )
                continue

            # Resolve package reference - Package model doesn't have slug field,
            # so convert package_slug to name format for lookup
            package_name = package_slug.replace("_", " ").title()
            package = session.query(Package).filter_by(name=package_name).first()
            if not package:
                result.add_error(
                    "package_finished_good", package_slug, f"Package not found: {package_slug}"
                )
                continue

            # Resolve finished good reference
            fg = session.query(FinishedGood).filter_by(slug=finished_good_slug).first()
            if not fg:
                result.add_error(
                    "package_finished_good",
                    package_name,
                    f"FinishedGood not found: {finished_good_slug}",
                )
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = (
                    session.query(PackageFinishedGood)
                    .filter_by(
                        package_id=package.id,
                        finished_good_id=fg.id,
                    )
                    .first()
                )
                if existing:
                    result.add_skip(
                        "package_finished_good",
                        f"{package_name}->{finished_good_slug}",
                        "Already exists",
                    )
                    continue

            # Create link
            pfg = PackageFinishedGood(
                package_id=package.id,
                finished_good_id=fg.id,
                quantity=quantity,
            )

            session.add(pfg)
            result.add_success("package_finished_good")

        except Exception as e:
            result.add_error("package_finished_good", record.get("package_name", "unknown"), str(e))

    return result


def import_production_records_from_json(
    data: List[Dict], session, skip_duplicates: bool = True
) -> ImportResult:
    """
    Import ProductionRecord records from v3.0 format data.

    Args:
        data: List of production record dictionaries
        session: SQLAlchemy session
        skip_duplicates: If True, skip records that already exist

    Returns:
        ImportResult with import statistics
    """
    from src.models.recipe import Recipe
    from src.models.event import Event

    result = ImportResult()

    for record in data:
        try:
            event_name = record.get("event_name", "")
            event_slug = record.get("event_slug", "")
            recipe_name = record.get("recipe_name", "")
            recipe_slug = record.get("recipe_slug", "")
            batches = record.get("batches", 0)
            produced_at_str = record.get("produced_at", "")

            # Support slug products - convert to name format
            if not event_name and event_slug:
                event_name = event_slug.replace("_", " ").title()
            if not recipe_name and recipe_slug:
                recipe_name = recipe_slug.replace("_", " ").title()

            if not event_name or not recipe_name or not produced_at_str:
                result.add_error(
                    "production_record",
                    event_name or "unknown",
                    "Missing event_name/slug, recipe_name/slug, or produced_at",
                )
                continue

            # Parse datetime
            produced_at = datetime.fromisoformat(produced_at_str.replace("Z", "+00:00"))
            # Convert to naive UTC for SQLite compatibility
            produced_at = produced_at.replace(tzinfo=None)

            # Resolve event reference
            event = session.query(Event).filter_by(name=event_name).first()
            if not event:
                result.add_error("production_record", event_name, f"Event not found: {event_name}")
                continue

            # Resolve recipe reference
            recipe = session.query(Recipe).filter_by(name=recipe_name).first()
            if not recipe:
                result.add_error(
                    "production_record", event_name, f"Recipe not found: {recipe_name}"
                )
                continue

            # Check for duplicate (by event + recipe + produced_at)
            if skip_duplicates:
                existing = (
                    session.query(ProductionRecord)
                    .filter_by(
                        event_id=event.id,
                        recipe_id=recipe.id,
                        produced_at=produced_at,
                    )
                    .first()
                )
                if existing:
                    result.add_skip(
                        "production_record", f"{event_name}/{recipe_name}", "Already exists"
                    )
                    continue

            # Create production record
            from decimal import Decimal

            pr = ProductionRecord(
                event_id=event.id,
                recipe_id=recipe.id,
                batches=batches,
                produced_at=produced_at,
                actual_cost=Decimal(str(record.get("actual_cost", 0))),
                notes=record.get("notes"),
            )

            session.add(pr)
            result.add_success("production_record")

        except Exception as e:
            result.add_error("production_record", record.get("event_name", "unknown"), str(e))

    return result


def import_event_recipient_packages_from_json(
    data: List[Dict], session, skip_duplicates: bool = True
) -> ImportResult:
    """
    Import EventRecipientPackage records from v3.0 format data.

    Args:
        data: List of event-recipient-package dictionaries
        session: SQLAlchemy session
        skip_duplicates: If True, skip records that already exist

    Returns:
        ImportResult with import statistics
    """
    from src.models.event import Event, EventRecipientPackage
    from src.models.recipient import Recipient
    from src.models.package_status import PackageStatus

    result = ImportResult()

    for record in data:
        try:
            event_slug = record.get("event_slug", "")
            recipient_name = record.get("recipient_name", "")
            package_slug = record.get("package_slug", "")
            quantity = record.get("quantity", 1)

            if not event_slug or not recipient_name or not package_slug:
                result.add_error(
                    "event_recipient_package",
                    "unknown",
                    "Missing event_slug, recipient_name, or package_slug",
                )
                continue

            # Resolve event reference - Event model doesn't have slug field,
            # so convert event_slug to name format for lookup
            event_name = event_slug.replace("_", " ").title()
            event = session.query(Event).filter_by(name=event_name).first()
            if not event:
                result.add_error(
                    "event_recipient_package", event_slug, f"Event not found: {event_slug}"
                )
                continue

            # Resolve recipient reference (uses name directly)
            recipient = session.query(Recipient).filter_by(name=recipient_name).first()
            if not recipient:
                result.add_error(
                    "event_recipient_package", event_slug, f"Recipient not found: {recipient_name}"
                )
                continue

            # Resolve package reference - Package model doesn't have slug field,
            # so convert package_slug to name format for lookup
            package_name = package_slug.replace("_", " ").title()
            package = session.query(Package).filter_by(name=package_name).first()
            if not package:
                result.add_error(
                    "event_recipient_package", event_slug, f"Package not found: {package_slug}"
                )
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = (
                    session.query(EventRecipientPackage)
                    .filter_by(
                        event_id=event.id,
                        recipient_id=recipient.id,
                        package_id=package.id,
                    )
                    .first()
                )
                if existing:
                    result.add_skip(
                        "event_recipient_package",
                        f"{event_name}/{recipient_name}/{package_name}",
                        "Already exists",
                    )
                    continue

            # Parse status
            status_str = record.get("status", "pending")
            try:
                status = PackageStatus(status_str)
            except ValueError:
                status = PackageStatus.PENDING

            # Feature 016: Parse fulfillment_status
            fulfillment_str = record.get("fulfillment_status", "pending")
            try:
                fulfillment_status = FulfillmentStatus(fulfillment_str)
            except ValueError:
                fulfillment_status = FulfillmentStatus.PENDING

            # Create assignment
            erp = EventRecipientPackage(
                event_id=event.id,
                recipient_id=recipient.id,
                package_id=package.id,
                quantity=quantity,
                status=status,
                fulfillment_status=fulfillment_status.value,  # Feature 016
                delivered_to=record.get("delivered_to"),
                notes=record.get("notes"),
            )

            session.add(erp)
            result.add_success("event_recipient_package")

        except Exception as e:
            result.add_error("event_recipient_package", record.get("event_name", "unknown"), str(e))

    return result


def import_event_production_targets_from_json(
    data: List[Dict], session, skip_duplicates: bool = True
) -> ImportResult:
    """
    Import EventProductionTarget records from v3.2 format data.

    Args:
        data: List of event-production-target dictionaries
        session: SQLAlchemy session
        skip_duplicates: If True, skip records that already exist

    Returns:
        ImportResult with import statistics
    """
    from src.models.event import Event

    result = ImportResult()

    for record in data:
        try:
            event_name = record.get("event_name", "")
            recipe_name = record.get("recipe_name", "")
            target_batches = record.get("target_batches", 0)

            if not event_name or not recipe_name:
                result.add_error(
                    "event_production_target", "unknown", "Missing event_name or recipe_name"
                )
                continue

            # Resolve event reference
            event = session.query(Event).filter_by(name=event_name).first()
            if not event:
                result.add_error(
                    "event_production_target", event_name, f"Event not found: {event_name}"
                )
                continue

            # Resolve recipe reference
            recipe = session.query(Recipe).filter_by(name=recipe_name).first()
            if not recipe:
                result.add_error(
                    "event_production_target", event_name, f"Recipe not found: {recipe_name}"
                )
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = (
                    session.query(EventProductionTarget)
                    .filter_by(
                        event_id=event.id,
                        recipe_id=recipe.id,
                    )
                    .first()
                )
                if existing:
                    result.add_skip(
                        "event_production_target", f"{event_name}/{recipe_name}", "Already exists"
                    )
                    continue

            # Create target
            target = EventProductionTarget(
                event_id=event.id,
                recipe_id=recipe.id,
                target_batches=target_batches,
                notes=record.get("notes"),
            )

            session.add(target)
            result.add_success("event_production_target")

        except Exception as e:
            result.add_error("event_production_target", record.get("event_name", "unknown"), str(e))

    return result


def import_event_assembly_targets_from_json(
    data: List[Dict], session, skip_duplicates: bool = True
) -> ImportResult:
    """
    Import EventAssemblyTarget records from v3.2 format data.

    Args:
        data: List of event-assembly-target dictionaries
        session: SQLAlchemy session
        skip_duplicates: If True, skip records that already exist

    Returns:
        ImportResult with import statistics
    """
    from src.models.event import Event

    result = ImportResult()

    for record in data:
        try:
            event_name = record.get("event_name", "")
            finished_good_slug = record.get("finished_good_slug", "")
            target_quantity = record.get("target_quantity", 0)

            if not event_name or not finished_good_slug:
                result.add_error(
                    "event_assembly_target", "unknown", "Missing event_name or finished_good_slug"
                )
                continue

            # Resolve event reference
            event = session.query(Event).filter_by(name=event_name).first()
            if not event:
                result.add_error(
                    "event_assembly_target", event_name, f"Event not found: {event_name}"
                )
                continue

            # Resolve finished good reference
            finished_good = session.query(FinishedGood).filter_by(slug=finished_good_slug).first()
            if not finished_good:
                result.add_error(
                    "event_assembly_target",
                    event_name,
                    f"Finished good not found: {finished_good_slug}",
                )
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = (
                    session.query(EventAssemblyTarget)
                    .filter_by(
                        event_id=event.id,
                        finished_good_id=finished_good.id,
                    )
                    .first()
                )
                if existing:
                    result.add_skip(
                        "event_assembly_target",
                        f"{event_name}/{finished_good_slug}",
                        "Already exists",
                    )
                    continue

            # Create target
            target = EventAssemblyTarget(
                event_id=event.id,
                finished_good_id=finished_good.id,
                target_quantity=target_quantity,
                notes=record.get("notes"),
            )

            session.add(target)
            result.add_success("event_assembly_target")

        except Exception as e:
            result.add_error("event_assembly_target", record.get("event_name", "unknown"), str(e))

    return result


def import_production_runs_from_json(
    data: List[Dict], session, skip_duplicates: bool = True
) -> ImportResult:
    """
    Import ProductionRun records from v3.2 format data.

    Args:
        data: List of production-run dictionaries
        session: SQLAlchemy session
        skip_duplicates: If True, skip records that already exist

    Returns:
        ImportResult with import statistics
    """
    from src.models.event import Event
    from datetime import datetime

    result = ImportResult()

    for record in data:
        try:
            event_name = record.get("event_name")  # Can be None for standalone
            recipe_name = record.get("recipe_name", "")
            num_batches = record.get("num_batches", 0)
            actual_yield = record.get("actual_yield", 0)
            produced_at_str = record.get("produced_at")

            if not recipe_name:
                result.add_error("production_run", "unknown", "Missing recipe_name")
                continue

            # Resolve event reference (optional - can be None for standalone)
            event_id = None
            if event_name:
                event = session.query(Event).filter_by(name=event_name).first()
                if not event:
                    result.add_error("production_run", event_name, f"Event not found: {event_name}")
                    continue
                event_id = event.id

            # Resolve recipe reference
            recipe = session.query(Recipe).filter_by(name=recipe_name).first()
            if not recipe:
                result.add_error("production_run", recipe_name, f"Recipe not found: {recipe_name}")
                continue

            # Parse produced_at timestamp
            produced_at = None
            if produced_at_str:
                try:
                    produced_at = datetime.fromisoformat(produced_at_str.replace("Z", "+00:00"))
                except ValueError:
                    produced_at = utc_now()

            # Create production run
            run = ProductionRun(
                event_id=event_id,
                recipe_id=recipe.id,
                num_batches=num_batches,
                actual_yield=actual_yield,
                produced_at=produced_at,
                notes=record.get("notes"),
            )

            session.add(run)
            result.add_success("production_run")

        except Exception as e:
            result.add_error("production_run", record.get("recipe_name", "unknown"), str(e))

    return result


def import_assembly_runs_from_json(
    data: List[Dict], session, skip_duplicates: bool = True
) -> ImportResult:
    """
    Import AssemblyRun records from v3.2 format data.

    Args:
        data: List of assembly-run dictionaries
        session: SQLAlchemy session
        skip_duplicates: If True, skip records that already exist

    Returns:
        ImportResult with import statistics
    """
    from src.models.event import Event
    from datetime import datetime

    result = ImportResult()

    for record in data:
        try:
            event_name = record.get("event_name")  # Can be None for standalone
            finished_good_slug = record.get("finished_good_slug", "")
            quantity_assembled = record.get("quantity_assembled", 0)
            assembled_at_str = record.get("assembled_at")

            if not finished_good_slug:
                result.add_error("assembly_run", "unknown", "Missing finished_good_slug")
                continue

            # Resolve event reference (optional - can be None for standalone)
            event_id = None
            if event_name:
                event = session.query(Event).filter_by(name=event_name).first()
                if not event:
                    result.add_error("assembly_run", event_name, f"Event not found: {event_name}")
                    continue
                event_id = event.id

            # Resolve finished good reference
            finished_good = session.query(FinishedGood).filter_by(slug=finished_good_slug).first()
            if not finished_good:
                result.add_error(
                    "assembly_run",
                    finished_good_slug,
                    f"Finished good not found: {finished_good_slug}",
                )
                continue

            # Parse assembled_at timestamp
            assembled_at = None
            if assembled_at_str:
                try:
                    assembled_at = datetime.fromisoformat(assembled_at_str.replace("Z", "+00:00"))
                except ValueError:
                    assembled_at = utc_now()

            # Create assembly run
            run = AssemblyRun(
                event_id=event_id,
                finished_good_id=finished_good.id,
                quantity_assembled=quantity_assembled,
                assembled_at=assembled_at,
                notes=record.get("notes"),
            )

            session.add(run)
            result.add_success("assembly_run")

        except Exception as e:
            result.add_error("assembly_run", record.get("finished_good_slug", "unknown"), str(e))

    return result


def _import_dry_run_preview(data: dict, mode: str, skip_duplicates: bool) -> ImportResult:
    """
    Generate a preview of what an import would do without making changes.

    Feature 050: Dry-run preview for import operations.

    Args:
        data: Parsed JSON data to preview
        mode: Import mode ("merge" or "replace")
        skip_duplicates: Whether to skip existing records

    Returns:
        ImportResult with preview counts (no DB changes made)
    """
    result = ImportResult()
    result.warnings.append("DRY RUN - No changes were made to the database")

    with session_scope() as session:
        # Preview suppliers
        if "suppliers" in data:
            for supplier_data in data["suppliers"]:
                name = supplier_data.get("name", "unknown")
                slug = supplier_data.get("slug")
                city = supplier_data.get("city", "")
                state = supplier_data.get("state", "")

                # Check for existing supplier
                existing = None
                if slug:
                    existing = session.query(Supplier).filter_by(slug=slug).first()
                if not existing and name and city and state:
                    existing = (
                        session.query(Supplier).filter_by(name=name, city=city, state=state).first()
                    )

                if existing:
                    if skip_duplicates:
                        result.add_skip(
                            "supplier", f"{name} ({city}, {state})", "Would skip (exists)"
                        )
                    else:
                        # In replace mode, would update
                        result.add_success("supplier")
                else:
                    result.add_success("supplier")

        # Preview ingredients
        if "ingredients" in data:
            for ing in data["ingredients"]:
                slug = ing.get("slug", "unknown")
                if skip_duplicates:
                    existing = session.query(Ingredient).filter_by(slug=slug).first()
                    if existing:
                        result.add_skip("ingredient", slug, "Would skip (exists)")
                        continue
                result.add_success("ingredient")

        # Preview products
        if "products" in data:
            for prod in data["products"]:
                brand = prod.get("brand", "unknown")
                ing_slug = prod.get("ingredient_slug", "")
                if skip_duplicates:
                    ingredient = session.query(Ingredient).filter_by(slug=ing_slug).first()
                    if ingredient:
                        existing = (
                            session.query(Product)
                            .filter_by(
                                ingredient_id=ingredient.id,
                                brand=brand,
                                product_name=prod.get("product_name"),
                                package_size=prod.get("package_size"),
                                package_unit=prod.get("package_unit"),
                                package_unit_quantity=prod.get("package_unit_quantity"),
                            )
                            .first()
                        )
                        if existing:
                            result.add_skip("product", brand, "Would skip (exists)")
                            continue
                result.add_success("product")

        # Preview purchases
        if "purchases" in data:
            for purch in data["purchases"]:
                result.add_success("purchase")

        # Preview inventory items
        if "inventory_items" in data:
            for item in data["inventory_items"]:
                result.add_success("inventory_item")

        # Preview recipes
        # Note: Recipe model uses 'name' not 'slug' for identification
        if "recipes" in data:
            for recipe in data["recipes"]:
                name = recipe.get("name", "unknown")
                if skip_duplicates:
                    existing = session.query(Recipe).filter_by(name=name).first()
                    if existing:
                        result.add_skip("recipe", name, "Would skip (exists)")
                        continue
                result.add_success("recipe")

    return result


def import_all_from_json_v4(
    file_path: str, mode: str = "merge", dry_run: bool = False
) -> ImportResult:
    """
    Import all data from a v4.0 format JSON file.

    Supports two import modes:
    - "merge": Add new records, skip duplicates (default, safe for incremental backups)
    - "replace": Clear all existing data first, then import (full restore)

    Imports in dependency order:
    1. ingredients (no dependencies)
    2. products (depends on ingredients)
    3. purchases (depends on products)
    4. inventory_items (depends on products)
    5. recipes (depends on ingredients) - with F037 variant fields
    6. finished_units (depends on recipes)
    7. finished_goods (no dependencies)
    8. compositions (depends on finished_goods)
    9. packages (no dependencies)
    10. package_finished_goods (depends on packages, finished_goods)
    11. recipients (no dependencies)
    12. events (no dependencies) - with F039 output_mode
    13. event_recipient_packages (depends on events, recipients, packages)
    14. production_records (depends on finished_units)

    Args:
        file_path: Path to v4.0 format JSON file
        mode: Import mode - "merge" (default) or "replace"
        dry_run: If True, return preview without making any DB changes (Feature 050)

    Returns:
        ImportResult with detailed per-entity statistics.
        In dry_run mode, entity_counts show what WOULD happen without changes.

    Raises:
        ValueError: If mode is not "merge" or "replace"
    """
    # Validate mode
    if mode not in ("merge", "replace"):
        raise ValueError(f"Invalid import mode: {mode}. Must be 'merge' or 'replace'.")

    result = ImportResult()
    skip_duplicates = mode == "merge"

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Feature 050: Dry-run preview mode
        if dry_run:
            return _import_dry_run_preview(data, mode, skip_duplicates)

        # Use single transaction for atomicity
        with session_scope() as session:
            # Replace mode: clear all tables first
            if mode == "replace":
                _clear_all_tables(session)

            # Import in dependency order
            # Note: For simplicity, we use existing import functions where possible.

            # 1. Ingredients (no dependencies)
            if "ingredients" in data:
                for ing in data["ingredients"]:
                    try:
                        slug = ing.get("slug", "")
                        if skip_duplicates:
                            existing = session.query(Ingredient).filter_by(slug=slug).first()
                            if existing:
                                result.add_skip("ingredient", slug, "Already exists")
                                continue

                        # Density fields (4-field format only - v3.3)
                        density_args = {}
                        if ing.get("density_volume_value") is not None:
                            # Validate density units before adding
                            vol_unit = ing.get("density_volume_unit")
                            wgt_unit = ing.get("density_weight_unit")

                            vol_error = _validate_density_volume_unit(vol_unit, slug)
                            if vol_error:
                                result.add_error("ingredient", slug, vol_error)
                                continue

                            wgt_error = _validate_density_weight_unit(wgt_unit, slug)
                            if wgt_error:
                                result.add_error("ingredient", slug, wgt_error)
                                continue

                            density_args["density_volume_value"] = ing.get("density_volume_value")
                            density_args["density_volume_unit"] = vol_unit
                            density_args["density_weight_value"] = ing.get("density_weight_value")
                            density_args["density_weight_unit"] = wgt_unit

                        # Feature 031: hierarchy_level defaults to 2 (leaf) if not specified
                        hierarchy_level = ing.get("hierarchy_level", 2)

                        ingredient = Ingredient(
                            display_name=ing.get("display_name"),
                            slug=slug,
                            category=ing.get("category"),
                            description=ing.get("description"),
                            notes=ing.get("notes"),
                            hierarchy_level=hierarchy_level,  # Feature 031
                            **density_args,
                        )
                        session.add(ingredient)
                        result.add_success("ingredient")
                    except Exception as e:
                        result.add_error("ingredient", ing.get("slug", "unknown"), str(e))

            # Flush to get IDs for foreign keys
            session.flush()

            # Feature 031: Second pass to resolve parent_slug references
            if "ingredients" in data:
                for ing in data["ingredients"]:
                    parent_slug = ing.get("parent_slug")
                    if parent_slug:
                        try:
                            slug = ing.get("slug", "")
                            ingredient = session.query(Ingredient).filter_by(slug=slug).first()
                            parent = session.query(Ingredient).filter_by(slug=parent_slug).first()
                            if ingredient and parent:
                                ingredient.parent_ingredient_id = parent.id
                            elif ingredient and not parent:
                                result.add_error(
                                    "ingredient", slug, f"Parent slug '{parent_slug}' not found"
                                )
                        except Exception as e:
                            result.add_error(
                                "ingredient",
                                ing.get("slug", "unknown"),
                                f"Error resolving parent: {str(e)}",
                            )

                session.flush()

            # 1.5 Feature 027: Suppliers (before products, which reference them)
            # Track old_id -> new_id mapping for FK resolution in merge mode
            supplier_id_map = {}  # old_id -> new_id
            # Feature 050: Also track slug -> id mapping for slug-based FK resolution
            supplier_slug_map = {}  # slug -> id
            if "suppliers" in data:
                for supplier_data in data["suppliers"]:
                    try:
                        name = supplier_data.get("name", "")
                        city = supplier_data.get("city", "")
                        state = supplier_data.get("state", "")
                        old_id = supplier_data.get("id")
                        # Feature 050: Get slug and supplier_type from import data
                        import_slug = supplier_data.get("slug")
                        supplier_type = supplier_data.get("supplier_type", "physical")

                        # Feature 050: Online suppliers only need name; physical need city/state
                        if not name:
                            result.add_error(
                                "supplier", name or "unknown", "Missing required field: name"
                            )
                            continue
                        if supplier_type == "physical" and (not city or not state):
                            result.add_error(
                                "supplier", name, "Physical suppliers require city and state"
                            )
                            continue

                        if skip_duplicates:
                            # Feature 050: Prefer slug-based matching, fallback to name+city+state
                            existing = None
                            if import_slug:
                                existing = (
                                    session.query(Supplier).filter_by(slug=import_slug).first()
                                )
                            if not existing and supplier_type == "physical":
                                # Fallback to name + city + state (unique supplier locations)
                                existing = (
                                    session.query(Supplier)
                                    .filter_by(
                                        name=name,
                                        city=city,
                                        state=state,
                                    )
                                    .first()
                                )
                            if not existing and supplier_type == "online":
                                # Online suppliers: fallback to name-only matching
                                existing = (
                                    session.query(Supplier)
                                    .filter_by(
                                        name=name,
                                        supplier_type="online",
                                    )
                                    .first()
                                )
                            if existing:
                                # Feature 050: Merge mode - sparse update existing suppliers
                                # Only update fields explicitly present in import (never slug)
                                updated_fields = []
                                if (
                                    "name" in supplier_data
                                    and supplier_data["name"] != existing.name
                                ):
                                    existing.name = supplier_data["name"]
                                    updated_fields.append("name")
                                if (
                                    "supplier_type" in supplier_data
                                    and supplier_data["supplier_type"] != existing.supplier_type
                                ):
                                    existing.supplier_type = supplier_data["supplier_type"]
                                    updated_fields.append("supplier_type")
                                if (
                                    "street_address" in supplier_data
                                    and supplier_data.get("street_address")
                                    != existing.street_address
                                ):
                                    existing.street_address = supplier_data.get("street_address")
                                    updated_fields.append("street_address")
                                if (
                                    "city" in supplier_data
                                    and supplier_data["city"] != existing.city
                                ):
                                    existing.city = supplier_data["city"]
                                    updated_fields.append("city")
                                if (
                                    "state" in supplier_data
                                    and supplier_data["state"] != existing.state
                                ):
                                    existing.state = supplier_data["state"]
                                    updated_fields.append("state")
                                if (
                                    "zip_code" in supplier_data
                                    and supplier_data.get("zip_code") != existing.zip_code
                                ):
                                    existing.zip_code = supplier_data.get("zip_code", "")
                                    updated_fields.append("zip_code")
                                if (
                                    "website_url" in supplier_data
                                    and supplier_data.get("website_url") != existing.website_url
                                ):
                                    existing.website_url = supplier_data.get("website_url")
                                    updated_fields.append("website_url")
                                if (
                                    "notes" in supplier_data
                                    and supplier_data.get("notes") != existing.notes
                                ):
                                    existing.notes = supplier_data.get("notes")
                                    updated_fields.append("notes")
                                if (
                                    "is_active" in supplier_data
                                    and supplier_data.get("is_active") != existing.is_active
                                ):
                                    existing.is_active = supplier_data.get("is_active", True)
                                    updated_fields.append("is_active")
                                # Note: slug is NEVER updated (immutability)

                                if updated_fields:
                                    result.add_update(
                                        "supplier",
                                        f"{name} ({city or 'online'}, {state or ''})",
                                        f"Updated: {', '.join(updated_fields)}",
                                    )
                                else:
                                    result.add_skip(
                                        "supplier",
                                        f"{name} ({city or 'online'}, {state or ''})",
                                        "Already exists (no changes)",
                                    )
                                # Track mapping for existing suppliers
                                if old_id:
                                    supplier_id_map[old_id] = existing.id
                                # Feature 050: Track slug mapping
                                if existing.slug:
                                    supplier_slug_map[existing.slug] = existing.id
                                continue

                        # Feature 050: Generate slug if not provided
                        slug = import_slug
                        if not slug:
                            slug = generate_supplier_slug(
                                name=name,
                                supplier_type=supplier_type,
                                city=city,
                                state=state,
                                session=session,
                            )

                        # Feature 050: For online suppliers, use None instead of empty strings
                        # to satisfy database CHECK constraints
                        supplier = Supplier(
                            name=name,
                            slug=slug,
                            supplier_type=supplier_type,
                            street_address=supplier_data.get("street_address"),
                            city=city if city else None,
                            state=state if state else None,
                            zip_code=supplier_data.get("zip_code") or None,
                            website_url=supplier_data.get("website_url"),
                            notes=supplier_data.get("notes"),
                            is_active=supplier_data.get("is_active", True),
                        )
                        # Preserve original ID if provided (for FK consistency in replace mode)
                        if old_id and mode == "replace":
                            supplier.id = old_id
                        if supplier_data.get("uuid"):
                            supplier.uuid = supplier_data["uuid"]

                        session.add(supplier)
                        session.flush()  # Get the new ID
                        result.add_success("supplier")

                        # Track old->new ID mapping for product FK resolution
                        if old_id:
                            supplier_id_map[old_id] = supplier.id
                        # Feature 050: Track slug mapping
                        supplier_slug_map[slug] = supplier.id
                    except Exception as e:
                        result.add_error("supplier", supplier_data.get("name", "unknown"), str(e))

            session.flush()

            # 2. Products (depends on ingredients and suppliers)
            if "products" in data:
                for prod_data in data["products"]:
                    try:
                        ing_slug = prod_data.get("ingredient_slug", "")
                        ingredient = session.query(Ingredient).filter_by(slug=ing_slug).first()
                        if not ingredient:
                            result.add_error(
                                "product",
                                prod_data.get("brand", "unknown"),
                                f"Ingredient not found: {ing_slug}",
                                suggestion=f"Add ingredient '{ing_slug}' to the catalog first.",
                            )
                            continue

                        brand = prod_data.get("brand", "")
                        # product_name may be None if not in export (backward compat)
                        product_name = prod_data.get("product_name")
                        package_size = prod_data.get("package_size")
                        package_unit = prod_data.get("package_unit")
                        package_unit_quantity = prod_data.get("package_unit_quantity")
                        if skip_duplicates:
                            # Match all 6 fields in UniqueConstraint uq_product_variant
                            # Must include package_unit_quantity to distinguish different sizes
                            existing = (
                                session.query(Product)
                                .filter_by(
                                    ingredient_id=ingredient.id,
                                    brand=brand,
                                    product_name=product_name,
                                    package_size=package_size,
                                    package_unit=package_unit,
                                    package_unit_quantity=package_unit_quantity,
                                )
                                .first()
                            )
                            if existing:
                                # Update preferred_supplier_id on existing product if import has one
                                # Feature 050: Prefer slug-based resolution, fallback to ID
                                if not existing.preferred_supplier_id:
                                    new_supplier_id = None
                                    supplier_slug = prod_data.get("preferred_supplier_slug")
                                    if supplier_slug:
                                        # Try slug-based lookup
                                        new_supplier_id = supplier_slug_map.get(supplier_slug)
                                        if not new_supplier_id:
                                            # Try direct database lookup
                                            sup = (
                                                session.query(Supplier)
                                                .filter_by(slug=supplier_slug)
                                                .first()
                                            )
                                            if sup:
                                                new_supplier_id = sup.id
                                            else:
                                                logger.warning(
                                                    f"Supplier slug not found: {supplier_slug}"
                                                )
                                    if not new_supplier_id:
                                        # Fallback to ID-based resolution (legacy support)
                                        old_supplier_id = prod_data.get("preferred_supplier_id")
                                        if old_supplier_id:
                                            new_supplier_id = supplier_id_map.get(old_supplier_id)
                                            if new_supplier_id:
                                                logger.info(
                                                    f"Using legacy supplier_id fallback: {old_supplier_id}"
                                                )
                                    if new_supplier_id:
                                        existing.preferred_supplier_id = new_supplier_id
                                        result.add_success(
                                            "product"
                                        )  # Count as success since we updated it
                                        continue
                                result.add_skip(
                                    "product",
                                    f"{brand} ({package_unit_quantity} {package_unit})",
                                    "Already exists",
                                )
                                continue

                        # Validate package_unit
                        unit_error = _validate_package_unit(package_unit, f"{ing_slug}/{brand}")
                        if unit_error:
                            result.add_error("product", brand, unit_error)
                            continue

                        # Feature 050: Resolve preferred_supplier_id - prefer slug, fallback to ID
                        new_supplier_id = None
                        supplier_slug = prod_data.get("preferred_supplier_slug")
                        if supplier_slug:
                            # Try slug-based lookup from mapping first
                            new_supplier_id = supplier_slug_map.get(supplier_slug)
                            if not new_supplier_id:
                                # Try direct database lookup
                                existing_supplier = (
                                    session.query(Supplier).filter_by(slug=supplier_slug).first()
                                )
                                if existing_supplier:
                                    new_supplier_id = existing_supplier.id
                                else:
                                    logger.warning(f"Supplier slug not found: {supplier_slug}")
                        if not new_supplier_id:
                            # Fallback to ID-based resolution (legacy support)
                            old_supplier_id = prod_data.get("preferred_supplier_id")
                            if old_supplier_id:
                                new_supplier_id = supplier_id_map.get(old_supplier_id)
                                if not new_supplier_id:
                                    # Supplier might already exist with same ID (replace mode)
                                    existing_supplier = (
                                        session.query(Supplier)
                                        .filter_by(id=old_supplier_id)
                                        .first()
                                    )
                                    if existing_supplier:
                                        new_supplier_id = old_supplier_id
                                        logger.info(
                                            f"Using legacy supplier_id fallback: {old_supplier_id}"
                                        )
                                    else:
                                        logger.warning(
                                            f"Legacy supplier_id not found: {old_supplier_id}"
                                        )
                                else:
                                    logger.info(
                                        f"Using legacy supplier_id fallback: {old_supplier_id}"
                                    )

                        product = Product(
                            ingredient_id=ingredient.id,
                            brand=brand,
                            product_name=product_name,  # None if not in old exports (backward compat)
                            package_size=prod_data.get("package_size"),
                            package_type=prod_data.get("package_type"),
                            package_unit=package_unit,
                            package_unit_quantity=prod_data.get("package_unit_quantity"),
                            upc_code=prod_data.get("upc_code"),
                            preferred=prod_data.get(
                                "is_preferred", prod_data.get("preferred", False)
                            ),
                            notes=prod_data.get("notes"),
                            # Feature 027: New fields - use mapped supplier ID
                            preferred_supplier_id=new_supplier_id,
                            is_hidden=prod_data.get("is_hidden", False),
                        )
                        session.add(product)
                        result.add_success("product")
                    except Exception as e:
                        result.add_error("product", prod_data.get("brand", "unknown"), str(e))

            session.flush()

            # 4. Purchases (depends on products AND suppliers)
            # Feature 027: Must come BEFORE inventory_items (which may reference purchases)
            # Updated to use supplier_id FK and unit_price
            if "purchases" in data:
                from decimal import Decimal
                from datetime import datetime as dt

                for purch_data in data["purchases"]:
                    try:
                        # Current-spec purchase format: direct foreign keys.
                        product_id = purch_data.get("product_id")
                        supplier_id = purch_data.get("supplier_id")

                        if product_id is None or supplier_id is None:
                            result.add_error(
                                "purchase",
                                "unknown",
                                "Missing required fields: product_id and/or supplier_id",
                                suggestion="Adjust the import file to include product_id and supplier_id per current spec.",
                            )
                            continue

                        # Validate product exists
                        product = session.query(Product).filter_by(id=product_id).first()
                        if not product:
                            result.add_error(
                                "purchase",
                                f"product_id={product_id}",
                                f"Product not found: ID {product_id}",
                            )
                            continue

                        # Validate supplier exists
                        supplier = session.query(Supplier).filter_by(id=supplier_id).first()
                        if not supplier:
                            result.add_error(
                                "purchase",
                                f"supplier_id={supplier_id}",
                                f"Supplier not found: ID {supplier_id}",
                            )
                            continue

                        # Parse purchase date (current field name only)
                        purchase_date = None
                        date_str = purch_data.get("purchase_date")
                        if not date_str:
                            result.add_error(
                                "purchase",
                                f"product_id={product_id}",
                                "Missing required field: purchase_date",
                            )
                            continue
                        try:
                            # Handle both date and datetime formats
                            if "T" in date_str:
                                purchase_date = dt.fromisoformat(
                                    date_str.replace("Z", "+00:00")
                                ).date()
                            else:
                                from datetime import date as dt_date

                                purchase_date = dt_date.fromisoformat(date_str)
                        except ValueError:
                            result.add_error(
                                "purchase",
                                f"product_id={product_id}",
                                f"Invalid date format: {date_str}",
                            )
                            continue

                        # Parse unit_price (current field name only)
                        if purch_data.get("unit_price") is None:
                            result.add_error(
                                "purchase",
                                f"product_id={product_id}",
                                "Missing required field: unit_price",
                            )
                            continue
                        unit_price = Decimal(str(purch_data.get("unit_price")))

                        if purch_data.get("quantity_purchased") is None:
                            result.add_error(
                                "purchase",
                                f"product_id={product_id}",
                                "Missing required field: quantity_purchased",
                            )
                            continue

                        purchase = Purchase(
                            product_id=product_id,
                            supplier_id=supplier_id,
                            purchase_date=purchase_date,
                            unit_price=unit_price,
                            quantity_purchased=purch_data.get("quantity_purchased"),
                            notes=purch_data.get("notes"),
                        )
                        # Preserve original ID if provided (for FK consistency in replace mode)
                        if purch_data.get("id") and mode == "replace":
                            purchase.id = purch_data["id"]
                        if purch_data.get("uuid"):
                            purchase.uuid = purch_data["uuid"]

                        session.add(purchase)
                        result.add_success("purchase")
                    except Exception as e:
                        result.add_error(
                            "purchase", purch_data.get("ingredient_slug", "unknown"), str(e)
                        )

            session.flush()

            # 5. Inventory Items (depends on products, may reference purchases)
            if "inventory_items" in data:
                from src.models.inventory_item import InventoryItem
                from datetime import datetime as dt

                for item_data in data["inventory_items"]:
                    try:
                        ing_slug = item_data.get("ingredient_slug", "")
                        product_brand = item_data.get("product_brand", "")
                        # Product identification fields (may be missing in old exports)
                        product_name = item_data.get("product_name")
                        package_size = item_data.get("package_size")
                        package_unit = item_data.get("package_unit")
                        package_unit_quantity = item_data.get("package_unit_quantity")

                        # Find ingredient
                        ingredient = session.query(Ingredient).filter_by(slug=ing_slug).first()
                        if not ingredient:
                            result.add_error(
                                "inventory_item",
                                f"{ing_slug}/{product_brand}",
                                f"Ingredient not found: {ing_slug}",
                                suggestion="Import ingredients and products before inventory items.",
                            )
                            continue

                        # Build product filter with all available identification fields
                        product_filter = {
                            "ingredient_id": ingredient.id,
                            "brand": product_brand,
                        }
                        # Add additional fields if present in export (v3.5+ format)
                        if product_name is not None:
                            product_filter["product_name"] = product_name
                        if package_size is not None:
                            product_filter["package_size"] = package_size
                        if package_unit is not None:
                            product_filter["package_unit"] = package_unit
                        if package_unit_quantity is not None:
                            product_filter["package_unit_quantity"] = package_unit_quantity

                        # Query for matching products
                        matching_products = session.query(Product).filter_by(**product_filter).all()

                        if len(matching_products) == 0:
                            result.add_error(
                                "inventory_item",
                                f"{ing_slug}/{product_brand}",
                                f"Product not found: {product_brand}",
                                suggestion=f"Add product '{product_brand}' for ingredient '{ing_slug}' first.",
                            )
                            continue
                        elif len(matching_products) > 1:
                            # Ambiguous match - multiple products with same brand (old export format)
                            result.add_error(
                                "inventory_item",
                                f"{ing_slug}/{product_brand}",
                                f"Ambiguous product match: {len(matching_products)} products found with brand '{product_brand}'. "
                                f"Export file may be from older version without product_name field.",
                                suggestion="Re-export data using latest version to include product_name field.",
                            )
                            continue

                        product = matching_products[0]

                        # Parse dates
                        purchase_date = None
                        if item_data.get("purchase_date"):
                            purchase_date = dt.fromisoformat(
                                item_data["purchase_date"].replace("Z", "+00:00")
                            )

                        expiration_date = None
                        if item_data.get("expiration_date"):
                            expiration_date = dt.fromisoformat(
                                item_data["expiration_date"].replace("Z", "+00:00")
                            )

                        inventory_item = InventoryItem(
                            product_id=product.id,
                            quantity=item_data.get("quantity", 0),
                            purchase_date=purchase_date,
                            expiration_date=expiration_date,
                            location=item_data.get("location"),
                            notes=item_data.get("notes"),
                            # Feature 027: purchase_id FK (may be None for old data)
                            purchase_id=item_data.get("purchase_id"),
                        )
                        session.add(inventory_item)
                        result.add_success("inventory_item")
                    except Exception as e:
                        result.add_error(
                            "inventory_item", item_data.get("ingredient_slug", "unknown"), str(e)
                        )

            session.flush()

            # 6. Recipes (depends on ingredients)
            # Feature 040 / F037: Import recipes with variant support
            if "recipes" in data:
                # T006: Sort recipes - import base recipes before variants
                # This ensures base_recipe exists when importing a variant
                recipes_data = data["recipes"]
                base_recipes = [r for r in recipes_data if not r.get("base_recipe_slug")]
                variant_recipes = [r for r in recipes_data if r.get("base_recipe_slug")]
                sorted_recipes = base_recipes + variant_recipes

                for recipe_data in sorted_recipes:
                    try:
                        name = recipe_data.get("name", "")

                        if skip_duplicates:
                            existing = session.query(Recipe).filter_by(name=name).first()
                            if existing:
                                result.add_skip("recipe", name, "Already exists")
                                continue

                        # T007: Resolve base_recipe_slug to base_recipe_id
                        base_recipe_id = None
                        base_recipe_slug = recipe_data.get("base_recipe_slug")
                        if base_recipe_slug:
                            # Convert slug back to name (slug format: lowercase with underscores)
                            # Look up by matching the name pattern
                            base_recipes_candidates = session.query(Recipe).all()
                            base_recipe = None
                            for candidate in base_recipes_candidates:
                                # Generate slug from candidate name and compare
                                candidate_slug = candidate.name.lower().replace(" ", "_")
                                if candidate_slug == base_recipe_slug:
                                    base_recipe = candidate
                                    break

                            if not base_recipe:
                                result.add_error(
                                    "recipe",
                                    name,
                                    f"Base recipe not found: {base_recipe_slug}",
                                    suggestion="Ensure base recipe is exported and listed before variants.",
                                )
                                continue
                            base_recipe_id = base_recipe.id

                        # T010: Validate ingredients exist before creating recipe
                        recipe_ingredients_data = recipe_data.get("ingredients", [])
                        validated_ingredients = []
                        missing_ingredients = []
                        invalid_units = []

                        for ri_data in recipe_ingredients_data:
                            ing_slug = ri_data.get("ingredient_slug", "")
                            ingredient = session.query(Ingredient).filter_by(slug=ing_slug).first()
                            if ingredient:
                                # Validate unit
                                unit = ri_data.get("unit")
                                unit_error = _validate_recipe_ingredient_unit(unit, name, ing_slug)
                                if unit_error:
                                    invalid_units.append(unit_error)
                                else:
                                    validated_ingredients.append(
                                        {
                                            "ingredient_id": ingredient.id,
                                            "quantity": ri_data.get("quantity"),
                                            "unit": unit,
                                            "notes": ri_data.get("notes"),
                                        }
                                    )
                            else:
                                missing_ingredients.append(ing_slug)

                        if missing_ingredients:
                            result.add_error(
                                "recipe",
                                name,
                                f"Missing ingredients: {', '.join(missing_ingredients)}",
                                suggestion="Import ingredients first, or add missing ingredients to the ingredients catalog.",
                            )
                            continue

                        if invalid_units:
                            for err in invalid_units:
                                result.add_error("recipe", name, err)
                            continue

                        # T010: Validate finished_units yield_mode values before creating
                        finished_units_data = recipe_data.get("finished_units", [])
                        valid_yield_modes = [e.value for e in YieldMode]
                        invalid_yield_mode = False
                        for fu_data in finished_units_data:
                            yield_mode_str = fu_data.get("yield_mode")
                            if yield_mode_str and yield_mode_str not in valid_yield_modes:
                                result.add_error(
                                    "recipe",
                                    name,
                                    f"Invalid yield_mode: {yield_mode_str}. Valid values: {valid_yield_modes}",
                                )
                                invalid_yield_mode = True
                                break
                        if invalid_yield_mode:
                            continue

                        # Create recipe with F037 fields
                        # T008: Import variant_name and is_production_ready
                        # F056: yield_quantity, yield_unit, yield_description removed
                        # Import files may still have these fields for backward compat, but they're ignored
                        recipe = Recipe(
                            name=name,
                            category=recipe_data.get("category"),
                            source=recipe_data.get("source"),
                            estimated_time_minutes=recipe_data.get(
                                "estimated_time_minutes",
                                recipe_data.get("prep_time_minutes", 0)
                                + recipe_data.get("cook_time_minutes", 0),
                            ),
                            notes=recipe_data.get("notes"),
                            # F037 fields
                            base_recipe_id=base_recipe_id,
                            variant_name=recipe_data.get("variant_name"),
                            is_production_ready=recipe_data.get("is_production_ready", True),
                        )
                        session.add(recipe)
                        session.flush()  # Get recipe ID

                        # Create recipe ingredients
                        for vi in validated_ingredients:
                            ri = RecipeIngredient(
                                recipe_id=recipe.id,
                                ingredient_id=vi["ingredient_id"],
                                quantity=vi["quantity"],
                                unit=vi["unit"],
                                notes=vi.get("notes"),
                            )
                            session.add(ri)

                        # T009: Import finished_units[] with yield_mode
                        for fu_data in finished_units_data:
                            fu_slug = fu_data.get("slug")
                            if not fu_slug:
                                # Generate slug from name if not provided
                                fu_name = fu_data.get("name", f"{name}_unit")
                                fu_slug = fu_name.lower().replace(" ", "_")

                            # Check for existing in merge mode
                            if skip_duplicates:
                                existing_fu = (
                                    session.query(FinishedUnit).filter_by(slug=fu_slug).first()
                                )
                                if existing_fu:
                                    result.add_skip(
                                        "finished_unit",
                                        fu_slug,
                                        "Already exists (from recipe import)",
                                    )
                                    continue

                            # Convert yield_mode string to enum
                            yield_mode_str = fu_data.get("yield_mode")
                            yield_mode = (
                                YieldMode(yield_mode_str)
                                if yield_mode_str
                                else YieldMode.DISCRETE_COUNT
                            )

                            # Build finished unit with mode-specific fields
                            finished_unit = FinishedUnit(
                                recipe_id=recipe.id,
                                slug=fu_slug,
                                display_name=fu_data.get("name", name),
                                yield_mode=yield_mode,
                            )

                            # Set mode-specific fields based on yield_mode
                            if yield_mode == YieldMode.DISCRETE_COUNT:
                                if fu_data.get("unit_yield_quantity") is not None:
                                    finished_unit.items_per_batch = int(
                                        fu_data["unit_yield_quantity"]
                                    )
                                if fu_data.get("unit_yield_unit"):
                                    finished_unit.item_unit = fu_data["unit_yield_unit"]
                            elif yield_mode == YieldMode.BATCH_PORTION:
                                if fu_data.get("unit_yield_quantity") is not None:
                                    from decimal import Decimal

                                    finished_unit.batch_percentage = Decimal(
                                        str(fu_data["unit_yield_quantity"])
                                    )
                                if fu_data.get("unit_yield_unit"):
                                    finished_unit.portion_description = fu_data["unit_yield_unit"]

                            session.add(finished_unit)
                            result.add_success("finished_unit")

                        result.add_success("recipe")
                    except Exception as e:
                        result.add_error("recipe", recipe_data.get("name", "unknown"), str(e))

            session.flush()

            # 6.5 Recipe components (depends on all recipes being created)
            # Import validation functions from recipe_service
            from src.services.recipe_service import (
                _would_create_cycle,
                _would_exceed_depth,
                MAX_RECIPE_NESTING_DEPTH,
            )

            for recipe_data in data.get("recipes", []):
                recipe_name = recipe_data.get("name", "")
                components = recipe_data.get("components", [])

                if not components:
                    continue

                # Find the parent recipe we created earlier
                parent_recipe = session.query(Recipe).filter_by(name=recipe_name).first()
                if not parent_recipe:
                    # Recipe creation failed earlier, skip components
                    continue

                for comp_data in components:
                    try:
                        component_recipe_name = comp_data.get("recipe_name")
                        quantity = float(comp_data.get("quantity", 1.0))
                        notes = comp_data.get("notes")

                        # Validate quantity
                        if quantity <= 0:
                            result.add_error(
                                "recipe_component",
                                f"{recipe_name}->{component_recipe_name}",
                                "Quantity must be greater than 0",
                            )
                            continue

                        # Resolve component recipe by name
                        component_recipe = (
                            session.query(Recipe).filter_by(name=component_recipe_name).first()
                        )
                        if not component_recipe:
                            result.add_error(
                                "recipe_component",
                                f"{recipe_name}->{component_recipe_name}",
                                f"Component recipe not found: {component_recipe_name}",
                            )
                            continue

                        # Check for duplicate
                        if skip_duplicates:
                            existing = (
                                session.query(RecipeComponent)
                                .filter_by(
                                    recipe_id=parent_recipe.id,
                                    component_recipe_id=component_recipe.id,
                                )
                                .first()
                            )
                            if existing:
                                result.add_skip(
                                    "recipe_component",
                                    f"{recipe_name}->{component_recipe_name}",
                                    "Already exists",
                                )
                                continue

                        # Check for circular reference
                        if _would_create_cycle(parent_recipe.id, component_recipe.id, session):
                            result.add_error(
                                "recipe_component",
                                f"{recipe_name}->{component_recipe_name}",
                                "Would create circular reference",
                            )
                            continue

                        # Check depth limit
                        if _would_exceed_depth(parent_recipe.id, component_recipe.id, session):
                            result.add_error(
                                "recipe_component",
                                f"{recipe_name}->{component_recipe_name}",
                                f"Would exceed maximum nesting depth of {MAX_RECIPE_NESTING_DEPTH}",
                            )
                            continue

                        # Create recipe component
                        comp = RecipeComponent(
                            recipe_id=parent_recipe.id,
                            component_recipe_id=component_recipe.id,
                            quantity=quantity,
                            notes=notes,
                        )
                        session.add(comp)
                        result.add_success("recipe_component")

                    except Exception as e:
                        result.add_error(
                            "recipe_component",
                            f"{recipe_name}->{comp_data.get('recipe_name', 'unknown')}",
                            str(e),
                        )

            session.flush()

            # 7. Finished units (depends on recipes)
            if "finished_units" in data:
                fu_result = import_finished_units_from_json(
                    data["finished_units"], session, skip_duplicates
                )
                result.merge(fu_result)

            session.flush()

            # 8. Finished goods
            if "finished_goods" in data:
                for fg_data in data["finished_goods"]:
                    try:
                        slug = fg_data.get("slug", "")
                        if skip_duplicates:
                            existing = session.query(FinishedGood).filter_by(slug=slug).first()
                            if existing:
                                result.add_skip("finished_good", slug, "Already exists")
                                continue

                        from src.models.assembly_type import AssemblyType

                        assembly_type_str = fg_data.get("assembly_type", "custom_order")
                        try:
                            assembly_type = AssemblyType(assembly_type_str)
                        except ValueError:
                            assembly_type = AssemblyType.CUSTOM_ORDER

                        fg = FinishedGood(
                            slug=slug,
                            display_name=fg_data.get("display_name"),
                            assembly_type=assembly_type,
                            description=fg_data.get("description"),
                            packaging_instructions=fg_data.get("packaging_instructions"),
                            notes=fg_data.get("notes"),
                        )
                        session.add(fg)
                        result.add_success("finished_good")
                    except Exception as e:
                        result.add_error("finished_good", fg_data.get("slug", "unknown"), str(e))

            session.flush()

            # 9. Compositions (new)
            if "compositions" in data:
                comp_result = import_compositions_from_json(
                    data["compositions"], session, skip_duplicates
                )
                result.merge(comp_result)

            session.flush()

            # 10. Packages
            if "packages" in data:
                for pkg in data["packages"]:
                    try:
                        name = pkg.get("name", "")
                        if skip_duplicates:
                            existing = session.query(Package).filter_by(name=name).first()
                            if existing:
                                result.add_skip("package", name, "Already exists")
                                continue

                        package = Package(
                            name=name,
                            description=pkg.get("description"),
                            is_template=pkg.get("is_template", False),
                            notes=pkg.get("notes"),
                        )
                        session.add(package)
                        result.add_success("package")
                    except Exception as e:
                        result.add_error("package", pkg.get("name", "unknown"), str(e))

            session.flush()

            # 11. Package-finished-goods (new)
            if "package_finished_goods" in data:
                pfg_result = import_package_finished_goods_from_json(
                    data["package_finished_goods"], session, skip_duplicates
                )
                result.merge(pfg_result)

            session.flush()

            # 12. Recipients
            if "recipients" in data:
                from src.models.recipient import Recipient

                for rec in data["recipients"]:
                    try:
                        name = rec.get("name", "")
                        if skip_duplicates:
                            existing = session.query(Recipient).filter_by(name=name).first()
                            if existing:
                                result.add_skip("recipient", name, "Already exists")
                                continue

                        recipient = Recipient(
                            name=name,
                            household_name=rec.get("household", rec.get("household_name")),
                            address=rec.get("address"),
                            notes=rec.get("notes"),
                        )
                        session.add(recipient)
                        result.add_success("recipient")
                    except Exception as e:
                        result.add_error("recipient", rec.get("name", "unknown"), str(e))

            session.flush()

            # 13. Events
            # Feature 040 / F039: Import output_mode field
            # Feature 068: Import expected_attendees and plan_state
            if "events" in data:
                for evt in data["events"]:
                    try:
                        name = evt.get("name", "")
                        year = evt.get("year")
                        if skip_duplicates and year:
                            existing = session.query(Event).filter_by(name=name, year=year).first()
                            if existing:
                                result.add_skip("event", name, "Already exists")
                                continue

                        from datetime import date

                        event_date_str = evt.get("event_date")
                        event_date = date.fromisoformat(event_date_str) if event_date_str else None

                        # Extract year from event_date if not provided
                        if not year and event_date:
                            year = event_date.year

                        # T013: Parse output_mode enum
                        output_mode = None
                        output_mode_str = evt.get("output_mode")
                        if output_mode_str:
                            try:
                                output_mode = OutputMode(output_mode_str)
                            except ValueError:
                                result.add_error(
                                    "event",
                                    name,
                                    f"Invalid output_mode: {output_mode_str}. Valid values: {[e.value for e in OutputMode]}",
                                )
                                continue

                        # Feature 068: Parse plan_state enum
                        plan_state = PlanState.DRAFT  # Default
                        plan_state_str = evt.get("plan_state")
                        if plan_state_str:
                            try:
                                plan_state = PlanState(plan_state_str)
                            except ValueError:
                                result.add_error(
                                    "event",
                                    name,
                                    f"Invalid plan_state: {plan_state_str}. Valid values: {[e.value for e in PlanState]}",
                                )
                                continue

                        event = Event(
                            name=name,
                            event_date=event_date,
                            year=year,
                            notes=evt.get("notes"),
                            output_mode=output_mode,  # Feature 040 / F039
                            expected_attendees=evt.get("expected_attendees"),  # Feature 068
                            plan_state=plan_state,  # Feature 068
                        )
                        session.add(event)
                        result.add_success("event")
                    except Exception as e:
                        result.add_error("event", evt.get("name", "unknown"), str(e))

            session.flush()

            # 14. Event-recipient-packages (new - separate from events in v3.0)
            if "event_recipient_packages" in data:
                erp_result = import_event_recipient_packages_from_json(
                    data["event_recipient_packages"], session, skip_duplicates
                )
                result.merge(erp_result)

            session.flush()

            # 15. Production records (new)
            if "production_records" in data:
                pr_result = import_production_records_from_json(
                    data["production_records"], session, skip_duplicates
                )
                result.merge(pr_result)

            session.flush()

            # 16. Event production targets (Feature 016)
            if "event_production_targets" in data:
                ept_result = import_event_production_targets_from_json(
                    data["event_production_targets"], session, skip_duplicates
                )
                result.merge(ept_result)

            session.flush()

            # 17. Event assembly targets (Feature 016)
            if "event_assembly_targets" in data:
                eat_result = import_event_assembly_targets_from_json(
                    data["event_assembly_targets"], session, skip_duplicates
                )
                result.merge(eat_result)

            session.flush()

            # T014: Validate output_mode vs targets consistency
            # Check if events with specific output_mode have corresponding targets
            if "events" in data:
                for evt in data["events"]:
                    name = evt.get("name", "")
                    output_mode_str = evt.get("output_mode")

                    if output_mode_str:
                        # Check event_assembly_targets for this event
                        has_assembly_targets = any(
                            t.get("event_name") == name
                            for t in data.get("event_assembly_targets", [])
                        )
                        # Check event_production_targets for this event
                        has_production_targets = any(
                            t.get("event_name") == name
                            for t in data.get("event_production_targets", [])
                        )

                        if output_mode_str == "bundled" and not has_assembly_targets:
                            result.add_warning(
                                "event",
                                name,
                                "output_mode='bundled' but no event_assembly_targets provided",
                                suggestion="Add assembly targets or change output_mode",
                            )
                        elif output_mode_str == "bulk_count" and not has_production_targets:
                            result.add_warning(
                                "event",
                                name,
                                "output_mode='bulk_count' but no event_production_targets provided",
                                suggestion="Add production targets or change output_mode",
                            )

            # 18. Production runs (Feature 016)
            if "production_runs" in data:
                pr_run_result = import_production_runs_from_json(
                    data["production_runs"], session, skip_duplicates
                )
                result.merge(pr_run_result)

            session.flush()

            # 19. Assembly runs (Feature 016)
            if "assembly_runs" in data:
                ar_result = import_assembly_runs_from_json(
                    data["assembly_runs"], session, skip_duplicates
                )
                result.merge(ar_result)

            # 20. Materials (Feature 047 - materials catalog)
            # Import order: categories -> subcategories -> materials -> products -> units
            import_mode = "add" if skip_duplicates else "augment"

            if "material_categories" in data:
                mat_cat_result = catalog_import_service.import_material_categories(
                    data["material_categories"], mode=import_mode, session=session
                )
                counts = mat_cat_result.entity_counts["material_categories"]
                result.entity_counts["material_category"] = {
                    "imported": counts.added,
                    "skipped": counts.skipped,
                    "errors": counts.failed,
                }
                result.successful += counts.added
                result.skipped += counts.skipped
                result.failed += counts.failed
                result.total_records += counts.added + counts.skipped + counts.failed
                session.flush()

            if "material_subcategories" in data:
                mat_subcat_result = catalog_import_service.import_material_subcategories(
                    data["material_subcategories"], mode=import_mode, session=session
                )
                counts = mat_subcat_result.entity_counts["material_subcategories"]
                result.entity_counts["material_subcategory"] = {
                    "imported": counts.added,
                    "skipped": counts.skipped,
                    "errors": counts.failed,
                }
                result.successful += counts.added
                result.skipped += counts.skipped
                result.failed += counts.failed
                result.total_records += counts.added + counts.skipped + counts.failed
                session.flush()

            if "materials" in data:
                mat_result = catalog_import_service.import_materials(
                    data["materials"], mode=import_mode, session=session
                )
                counts = mat_result.entity_counts["materials"]
                result.entity_counts["material"] = {
                    "imported": counts.added,
                    "skipped": counts.skipped,
                    "errors": counts.failed,
                }
                result.successful += counts.added
                result.skipped += counts.skipped
                result.failed += counts.failed
                result.total_records += counts.added + counts.skipped + counts.failed
                session.flush()

            if "material_products" in data:
                mat_prod_result = catalog_import_service.import_material_products(
                    data["material_products"], mode=import_mode, session=session
                )
                counts = mat_prod_result.entity_counts["material_products"]
                result.entity_counts["material_product"] = {
                    "imported": counts.added,
                    "skipped": counts.skipped,
                    "errors": counts.failed,
                }
                result.successful += counts.added
                result.skipped += counts.skipped
                result.failed += counts.failed
                result.total_records += counts.added + counts.skipped + counts.failed
                session.flush()

            if "material_units" in data:
                mat_unit_result = catalog_import_service.import_material_units(
                    data["material_units"], mode=import_mode, session=session
                )
                counts = mat_unit_result.entity_counts["material_units"]
                result.entity_counts["material_unit"] = {
                    "imported": counts.added,
                    "skipped": counts.skipped,
                    "errors": counts.failed,
                }
                result.successful += counts.added
                result.skipped += counts.skipped
                result.failed += counts.failed
                result.total_records += counts.added + counts.skipped + counts.failed

            # 21. Planning entities (Feature 068)
            # Import order respects FK dependencies:
            # - event_recipes (depends on: events, recipes)
            # - event_finished_goods (depends on: events, finished_goods)
            # - batch_decisions (depends on: events, recipes, finished_units)
            # - plan_amendments (depends on: events)

            # Build lookup tables for FK resolution
            all_events = {e.name: e.id for e in session.query(Event).all()}
            all_recipes = {r.name: r.id for r in session.query(Recipe).all()}
            all_fgs = {fg.display_name: fg.id for fg in session.query(FinishedGood).all()}
            all_fus = {fu.display_name: fu.id for fu in session.query(FinishedUnit).all()}

            # Import event_recipes
            if "event_recipes" in data:
                for er_data in data["event_recipes"]:
                    try:
                        event_name = er_data.get("event_name")
                        recipe_name = er_data.get("recipe_name")

                        event_id = all_events.get(event_name)
                        recipe_id = all_recipes.get(recipe_name)

                        if not event_id:
                            result.add_error(
                                "event_recipe", f"{event_name}/{recipe_name}",
                                f"Event not found: {event_name}"
                            )
                            continue
                        if not recipe_id:
                            result.add_error(
                                "event_recipe", f"{event_name}/{recipe_name}",
                                f"Recipe not found: {recipe_name}"
                            )
                            continue

                        if skip_duplicates:
                            existing = session.query(EventRecipe).filter_by(
                                event_id=event_id, recipe_id=recipe_id
                            ).first()
                            if existing:
                                result.add_skip(
                                    "event_recipe", f"{event_name}/{recipe_name}",
                                    "Already exists"
                                )
                                continue

                        er = EventRecipe(event_id=event_id, recipe_id=recipe_id)
                        session.add(er)
                        result.add_success("event_recipe")
                    except Exception as e:
                        result.add_error(
                            "event_recipe",
                            f"{er_data.get('event_name')}/{er_data.get('recipe_name')}",
                            str(e)
                        )
                session.flush()

            # Import event_finished_goods
            if "event_finished_goods" in data:
                for efg_data in data["event_finished_goods"]:
                    try:
                        event_name = efg_data.get("event_name")
                        fg_name = efg_data.get("finished_good_name")
                        quantity = efg_data.get("quantity", 1)

                        event_id = all_events.get(event_name)
                        fg_id = all_fgs.get(fg_name)

                        if not event_id:
                            result.add_error(
                                "event_finished_good", f"{event_name}/{fg_name}",
                                f"Event not found: {event_name}"
                            )
                            continue
                        if not fg_id:
                            result.add_error(
                                "event_finished_good", f"{event_name}/{fg_name}",
                                f"Finished good not found: {fg_name}"
                            )
                            continue

                        if skip_duplicates:
                            existing = session.query(EventFinishedGood).filter_by(
                                event_id=event_id, finished_good_id=fg_id
                            ).first()
                            if existing:
                                result.add_skip(
                                    "event_finished_good", f"{event_name}/{fg_name}",
                                    "Already exists"
                                )
                                continue

                        efg = EventFinishedGood(
                            event_id=event_id,
                            finished_good_id=fg_id,
                            quantity=quantity,
                        )
                        session.add(efg)
                        result.add_success("event_finished_good")
                    except Exception as e:
                        result.add_error(
                            "event_finished_good",
                            f"{efg_data.get('event_name')}/{efg_data.get('finished_good_name')}",
                            str(e)
                        )
                session.flush()

            # Import batch_decisions
            if "batch_decisions" in data:
                for bd_data in data["batch_decisions"]:
                    try:
                        event_name = bd_data.get("event_name")
                        recipe_name = bd_data.get("recipe_name")
                        batches = bd_data.get("batches", 1)

                        event_id = all_events.get(event_name)
                        recipe_id = all_recipes.get(recipe_name)

                        if not event_id:
                            result.add_error(
                                "batch_decision", f"{event_name}/{recipe_name}",
                                f"Event not found: {event_name}"
                            )
                            continue
                        if not recipe_id:
                            result.add_error(
                                "batch_decision", f"{event_name}/{recipe_name}",
                                f"Recipe not found: {recipe_name}"
                            )
                            continue

                        # Optional finished_unit_id
                        fu_id = None
                        fu_name = bd_data.get("finished_unit_name")
                        if fu_name:
                            fu_id = all_fus.get(fu_name)
                            if not fu_id:
                                result.add_warning(
                                    "batch_decision", f"{event_name}/{recipe_name}",
                                    f"Finished unit not found: {fu_name}",
                                    suggestion="Import will continue without finished_unit reference"
                                )

                        if skip_duplicates:
                            existing = session.query(BatchDecision).filter_by(
                                event_id=event_id, recipe_id=recipe_id
                            ).first()
                            if existing:
                                result.add_skip(
                                    "batch_decision", f"{event_name}/{recipe_name}",
                                    "Already exists"
                                )
                                continue

                        bd = BatchDecision(
                            event_id=event_id,
                            recipe_id=recipe_id,
                            batches=batches,
                            finished_unit_id=fu_id,
                        )
                        session.add(bd)
                        result.add_success("batch_decision")
                    except Exception as e:
                        result.add_error(
                            "batch_decision",
                            f"{bd_data.get('event_name')}/{bd_data.get('recipe_name')}",
                            str(e)
                        )
                session.flush()

            # Import plan_amendments
            if "plan_amendments" in data:
                for pa_data in data["plan_amendments"]:
                    try:
                        event_name = pa_data.get("event_name")
                        amendment_type_str = pa_data.get("amendment_type")
                        amendment_data_raw = pa_data.get("amendment_data", {})
                        reason = pa_data.get("reason")

                        event_id = all_events.get(event_name)
                        if not event_id:
                            result.add_error(
                                "plan_amendment", event_name,
                                f"Event not found: {event_name}"
                            )
                            continue

                        # Parse amendment_type enum
                        try:
                            amendment_type = AmendmentType(amendment_type_str)
                        except ValueError:
                            result.add_error(
                                "plan_amendment", event_name,
                                f"Invalid amendment_type: {amendment_type_str}. "
                                f"Valid values: {[e.value for e in AmendmentType]}"
                            )
                            continue

                        pa = PlanAmendment(
                            event_id=event_id,
                            amendment_type=amendment_type,
                            amendment_data=amendment_data_raw,
                            reason=reason,
                        )
                        session.add(pa)
                        result.add_success("plan_amendment")
                    except Exception as e:
                        result.add_error(
                            "plan_amendment",
                            pa_data.get("event_name", "unknown"),
                            str(e)
                        )
                session.flush()

            # Commit transaction
            session.commit()

    except Exception as e:
        result.add_error("file", file_path, str(e))

    return result


def import_purchases_from_bt_mobile(file_path: str) -> ImportResult:
    """
    Import purchases from BT Mobile JSON file.

    This function imports purchase data scanned from BT Mobile app, matching
    UPCs against existing products and creating Purchase + InventoryItem records.

    The import is ATOMIC per SC-008: if any record fails validation or creation,
    the entire import is rolled back with no partial data changes.

    Args:
        file_path: Path to JSON file with schema_version="4.0", import_type="purchases"

    Returns:
        ImportResult with:
        - successful: Number of purchases that would be created (0 if any errors)
        - failed: Number of errors (causes full rollback)
        - unmatched_purchases: List of purchase data for UPCs not found in products

    Note:
        Feature 040: Part of BT Mobile workflow for scanning receipts.
    """
    result = ImportResult()
    result.unmatched_purchases = []  # T022: Collect unmatched for UI resolution

    # T019: Read and validate JSON
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except FileNotFoundError:
        result.add_error("file", file_path, f"File not found: {file_path}")
        return result

    # Schema validation
    schema_version = data.get("schema_version")
    if schema_version != "4.0":
        result.add_error(
            "file",
            file_path,
            f"Unsupported schema version: {schema_version}. Expected '4.0'.",
        )
        return result

    import_type = data.get("import_type")
    if import_type != "purchases":
        result.add_error(
            "file",
            file_path,
            f"Wrong import type: {import_type}. Expected 'purchases'.",
        )
        return result

    # T020-T023: Process purchases
    default_supplier = data.get("supplier")
    purchases_data = data.get("purchases", [])

    if not purchases_data:
        # No purchases to import
        return result

    with session_scope() as session:
        for purchase_data in purchases_data:
            upc = purchase_data.get("upc")
            if not upc:
                result.add_error("purchase", "unknown", "Missing UPC field")
                continue

            # T020: UPC lookup
            product = session.query(Product).filter_by(upc_code=upc).first()

            if not product:
                # Collect for UI resolution (WP06)
                result.unmatched_purchases.append(purchase_data)
                continue

            # T021: Product found - create Purchase + InventoryItem
            try:
                # Resolve supplier - create default "Unknown" if not provided
                supplier_name = purchase_data.get("supplier") or default_supplier
                if not supplier_name:
                    supplier_name = "Unknown"

                supplier = session.query(Supplier).filter_by(name=supplier_name).first()
                if not supplier:
                    supplier = Supplier(name=supplier_name)
                    session.add(supplier)
                    session.flush()

                # Parse scanned_at date
                scanned_at = purchase_data.get("scanned_at")
                if scanned_at:
                    try:
                        # Handle ISO format with Z suffix
                        if scanned_at.endswith("Z"):
                            scanned_at = scanned_at[:-1] + "+00:00"
                        purchase_date = datetime.fromisoformat(scanned_at).date()
                    except ValueError:
                        purchase_date = date.today()
                else:
                    purchase_date = date.today()

                # Parse price and quantity
                unit_price = Decimal(str(purchase_data.get("unit_price", 0)))
                quantity_purchased = int(purchase_data.get("quantity_purchased", 1))

                # Create Purchase record
                purchase = Purchase(
                    product_id=product.id,
                    supplier_id=supplier.id,
                    purchase_date=purchase_date,
                    unit_price=unit_price,
                    quantity_purchased=quantity_purchased,
                    notes=purchase_data.get("notes"),
                )
                session.add(purchase)
                session.flush()  # Get purchase.id

                # Create InventoryItem linked to Purchase
                inventory_item = InventoryItem(
                    product_id=product.id,
                    purchase_id=purchase.id,
                    quantity=float(quantity_purchased),
                    unit_cost=float(unit_price),
                    purchase_date=purchase_date,
                )
                session.add(inventory_item)

                result.add_success("purchase")

            except Exception as e:
                result.add_error("purchase", upc, f"Failed to create purchase: {str(e)}")
                continue

        # SC-008 Atomic: Only commit if zero errors
        if result.failed == 0:
            session.commit()
        else:
            # Rollback happens automatically when session_scope exits without commit
            # Reset successful count since nothing was committed
            result.successful = 0

    return result


# ============================================================================
# v4.0 BT Mobile Inventory Update Import
# ============================================================================


def import_inventory_updates_from_bt_mobile(file_path: str) -> ImportResult:
    """
    Import inventory updates from BT Mobile JSON file.

    Adjusts InventoryItem quantities based on percentage remaining.
    Uses FIFO selection (oldest purchase_date first).

    The import is ATOMIC per SC-008: if any record fails validation,
    the entire import is rolled back with no partial data changes.

    Args:
        file_path: Path to JSON file with schema_version="4.0", import_type="inventory_updates"

    Returns:
        ImportResult with success_count (0 if any errors), error_count, and details
    """
    result = ImportResult()

    # Read JSON
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result

    # Validate schema
    if data.get("schema_version") != "4.0":
        result.add_error(
            "file", file_path, f"Unsupported schema version: {data.get('schema_version')}"
        )
        return result

    if data.get("import_type") != "inventory_updates":
        result.add_error(
            "file",
            file_path,
            f"Wrong import type: {data.get('import_type')} (expected 'inventory_updates')",
        )
        return result

    # Process updates
    with session_scope() as session:
        for update_data in data.get("inventory_updates", []):
            upc = update_data.get("upc")
            if not upc:
                result.add_error("inventory_update", "unknown", "Missing UPC")
                continue

            # UPC lookup
            product = session.query(Product).filter_by(upc_code=upc).first()

            if not product:
                result.add_error("inventory_update", upc, f"No product found with UPC: {upc}")
                continue

            # FIFO: oldest purchase_date first, with remaining quantity
            inventory_item = (
                session.query(InventoryItem)
                .filter_by(product_id=product.id)
                .filter(InventoryItem.quantity > 0)
                .order_by(InventoryItem.purchase_date.asc())
                .first()
            )

            if not inventory_item:
                result.add_error(
                    "inventory_update",
                    upc,
                    f"No inventory with remaining quantity for product: {product.display_name}",
                )
                continue

            # Get percentage from update data
            percentage = update_data.get("remaining_percentage")
            if percentage is None:
                result.add_error("inventory_update", upc, "Missing remaining_percentage")
                continue

            # Validate percentage range
            if not (0 <= percentage <= 100):
                result.add_error(
                    "inventory_update", upc, f"Invalid percentage: {percentage} (must be 0-100)"
                )
                continue

            # Get original quantity from linked purchase
            if not inventory_item.purchase_id:
                result.add_error(
                    "inventory_update",
                    upc,
                    "Cannot calculate percentage - inventory item has no linked purchase",
                )
                continue

            purchase = session.get(Purchase, inventory_item.purchase_id)
            if not purchase:
                result.add_error(
                    "inventory_update",
                    upc,
                    "Cannot calculate percentage - linked purchase not found",
                )
                continue

            original_quantity = Decimal(str(purchase.quantity_purchased))

            # Calculate target and adjustment
            pct_decimal = Decimal(str(percentage)) / Decimal("100")
            target_quantity = original_quantity * pct_decimal

            # Current quantity as Decimal
            current_quantity = Decimal(str(inventory_item.quantity))
            adjustment = target_quantity - current_quantity

            # Update inventory item quantity
            new_quantity = current_quantity + adjustment

            # Validate no negative inventory
            if new_quantity < 0:
                result.add_error(
                    "inventory_update",
                    upc,
                    f"Adjustment would result in negative inventory: {new_quantity}",
                )
                continue

            # Update quantity (convert to float for model compatibility)
            inventory_item.quantity = float(new_quantity)

            result.add_success("inventory_update")

        # SC-008 Atomic: Only commit if zero errors
        if result.failed == 0:
            session.commit()
        else:
            # Rollback happens automatically when session_scope exits without commit
            # Reset successful count since nothing was committed
            result.successful = 0

    return result
