"""
Import/Export Service - JSON-based data import and export for testing.

Provides minimal functionality to export and import ingredients and recipes
for testing purposes. No UI required - designed for programmatic use.
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import joinedload

from src.services import ingredient_crud_service
from src.services import recipe_service, finished_good_service
from src.services import package_service, recipient_service, event_service
from src.services.exceptions import ValidationError
from src.services.database import session_scope
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.inventory_item import InventoryItem
from src.models.purchase import Purchase
from src.models.unit_conversion import UnitConversion
from src.models.finished_unit import FinishedUnit
from src.models.finished_good import FinishedGood
from src.models.composition import Composition
from src.models.package import Package, PackageFinishedGood
from src.models.production_record import ProductionRecord
from src.models.production_run import ProductionRun
from src.models.assembly_run import AssemblyRun
from src.models.event import EventProductionTarget, EventAssemblyTarget, FulfillmentStatus
from src.models.recipe import Recipe, RecipeComponent
from src.utils.constants import APP_NAME, APP_VERSION


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

    def add_success(self, entity_type: str = None):
        """Record a successful import."""
        self.successful += 1
        self.total_records += 1
        if entity_type:
            self._ensure_entity(entity_type)
            self.entity_counts[entity_type]["imported"] += 1

    def add_skip(self, record_type: str, record_name: str, reason: str):
        """Record a skipped record."""
        self.skipped += 1
        self.total_records += 1
        self._ensure_entity(record_type)
        self.entity_counts[record_type]["skipped"] += 1
        self.warnings.append(
            {
                "record_type": record_type,
                "record_name": record_name,
                "warning_type": "skipped",
                "message": reason,
            }
        )

    def add_error(self, record_type: str, record_name: str, error: str):
        """Record a failed import."""
        self.failed += 1
        self.total_records += 1
        self._ensure_entity(record_type)
        self.entity_counts[record_type]["errors"] += 1
        self.errors.append(
            {
                "record_type": record_type,
                "record_name": record_name,
                "error_type": "import_error",
                "message": error,
            }
        )

    def add_warning(self, record_type: str, record_name: str, message: str):
        """Record a warning (non-fatal issue during import)."""
        self.warnings.append(
            {
                "record_type": record_type,
                "record_name": record_name,
                "warning_type": "warning",
                "message": message,
            }
        )

    def _ensure_entity(self, entity_type: str):
        """Ensure entity type exists in entity_counts."""
        if entity_type not in self.entity_counts:
            self.entity_counts[entity_type] = {"imported": 0, "skipped": 0, "errors": 0}

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
                if counts["skipped"] > 0:
                    parts.append(f"{counts['skipped']} skipped")
                if counts["errors"] > 0:
                    parts.append(f"{counts['errors']} errors")
                if parts:
                    lines.append(f"  {entity}: {', '.join(parts)}")
            lines.append("")

        lines.extend([
            f"Total Records: {self.total_records}",
            f"Successful:    {self.successful}",
            f"Skipped:       {self.skipped}",
            f"Failed:        {self.failed}",
        ])

        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors:
                lines.append(f"  - {error['record_type']}: {error['record_name']}")
                lines.append(f"    {error['message']}")

        if self.warnings and len(self.warnings) <= 10:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning['record_type']}: {warning['record_name']}")
                lines.append(f"    {warning['message']}")
        elif self.warnings:
            lines.append(f"\n{len(self.warnings)} warnings (use detailed report for full list)")

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
            "export_date": datetime.utcnow().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "ingredients": [],
        }

        for ingredient in ingredients:
            ingredient_data = {
                "name": ingredient.display_name,
                "brand": ingredient.brand,
                "category": ingredient.category,
                "purchase_quantity": ingredient.purchase_quantity,
                "purchase_unit": ingredient.purchase_unit,
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
            "export_date": datetime.utcnow().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "recipes": [],
        }

        for recipe in recipes:
            recipe_data = {
                "name": recipe.name,
                "category": recipe.category,
                "yield_quantity": recipe.yield_quantity,
                "yield_unit": recipe.yield_unit,
            }

            # Optional fields
            if recipe.source:
                recipe_data["source"] = recipe.source

            if recipe.yield_description:
                recipe_data["yield_description"] = recipe.yield_description

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
                if hasattr(ri.ingredient, 'brand') and ri.ingredient.brand:
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
            "export_date": datetime.utcnow().isoformat() + "Z",
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
            "export_date": datetime.utcnow().isoformat() + "Z",
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
            "export_date": datetime.utcnow().isoformat() + "Z",
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
            "export_date": datetime.utcnow().isoformat() + "Z",
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
        # Get events
        events = event_service.get_all_events()

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": datetime.utcnow().isoformat() + "Z",
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
        finished_units = (
            session.query(FinishedUnit)
            .options(joinedload(FinishedUnit.recipe))
            .all()
        )
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

            # Component reference - XOR: finished_unit OR finished_good OR packaging_product (Feature 011)
            if comp.finished_unit_component:
                comp_data["finished_unit_slug"] = comp.finished_unit_component.slug
                comp_data["finished_good_component_slug"] = None
                comp_data["packaging_product_id"] = None
            elif comp.finished_good_component:
                comp_data["finished_unit_slug"] = None
                comp_data["finished_good_component_slug"] = comp.finished_good_component.slug
                comp_data["packaging_product_id"] = None
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
            else:
                comp_data["finished_unit_slug"] = None
                comp_data["finished_good_component_slug"] = None
                comp_data["packaging_product_id"] = None

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


def export_all_to_json(file_path: str) -> ExportResult:
    """
    Export all data to a single JSON file in v3.0 format.

    Exports in dependency order per data-model.md:
    unit_conversions, ingredients, products, purchases, inventory_items,
    recipes, finished_units, finished_goods, compositions, packages,
    package_finished_goods, recipients, events, event_recipient_packages,
    production_records.

    Args:
        file_path: Path to output JSON file

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
        events = event_service.get_all_events()

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

        # Build combined export data - v3.2 format (Feature 016: event-centric production)
        export_data = {
            "version": "3.2",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "application": "bake-tracker",
            "unit_conversions": [],
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
        }

        # Add ingredients (NEW SCHEMA: generic ingredient definitions)
        for ingredient in ingredients:
            ingredient_data = {
                "name": ingredient.display_name,
                "slug": ingredient.slug,
                "category": ingredient.category,
                "recipe_unit": ingredient.recipe_unit,
                "is_packaging": ingredient.is_packaging,  # Feature 011
            }

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

        # Add products (brand/package-specific versions)
        for ingredient in ingredients:
            for product in ingredient.products:
                product_data = {
                    "ingredient_slug": ingredient.slug,
                    "purchase_unit": product.purchase_unit,
                    "purchase_quantity": product.purchase_quantity,
                }

                # Optional fields
                if product.brand:
                    product_data["brand"] = product.brand
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

                # Optional fields
                if item.expiration_date:
                    item_data["expiration_date"] = item.expiration_date.isoformat()
                if item.location:
                    item_data["location"] = item.location
                if item.notes:
                    item_data["notes"] = item.notes

                export_data["inventory_items"].append(item_data)

        # Add purchases (price history)
        with session_scope() as session:
            purchases = session.query(Purchase).join(Product).join(Ingredient).all()
            for purchase in purchases:
                purchase_data = {
                    "ingredient_slug": purchase.product.ingredient.slug,
                    "product_brand": purchase.product.brand or "",
                    "purchased_at": (
                        purchase.purchase_date.isoformat() if purchase.purchase_date else None
                    ),
                    "quantity_purchased": purchase.quantity_purchased,
                    "unit_cost": float(purchase.unit_cost) if purchase.unit_cost else 0.0,
                    "total_cost": float(purchase.total_cost) if purchase.total_cost else 0.0,
                }

                # Optional fields
                if purchase.supplier:
                    purchase_data["supplier"] = purchase.supplier
                if purchase.notes:
                    purchase_data["notes"] = purchase.notes

                export_data["purchases"].append(purchase_data)

        # Add unit conversions
        with session_scope() as session:
            conversions = session.query(UnitConversion).join(Ingredient).all()
            for conv in conversions:
                conv_data = {
                    "ingredient_slug": conv.ingredient.slug,
                    "from_unit": conv.from_unit,
                    "from_quantity": float(conv.from_quantity),
                    "to_unit": conv.to_unit,
                    "to_quantity": float(conv.to_quantity),
                }

                # Optional fields
                if conv.notes:
                    conv_data["notes"] = conv.notes

                export_data["unit_conversions"].append(conv_data)

        # Add recipes
        for recipe in recipes:
            recipe_data = {
                "name": recipe.name,
                "category": recipe.category,
                "yield_quantity": recipe.yield_quantity,
                "yield_unit": recipe.yield_unit,
            }

            if recipe.source:
                recipe_data["source"] = recipe.source
            if recipe.yield_description:
                recipe_data["yield_description"] = recipe.yield_description
            if recipe.estimated_time_minutes:
                recipe_data["estimated_time_minutes"] = recipe.estimated_time_minutes
            if recipe.notes:
                recipe_data["notes"] = recipe.notes

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
                session.query(FinishedGood)
                .options(joinedload(FinishedGood.components))
                .all()
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
        for event in events:
            event_data = {
                "name": event.name,
                "event_date": event.event_date.isoformat(),
                "year": event.year,
            }
            if event.notes:
                event_data["notes"] = event.notes

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

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        # Calculate total records and build entity counts
        total_records = (
            len(export_data["unit_conversions"])
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
        )

        result = ExportResult(file_path, total_records)

        # Add per-entity counts
        result.add_entity_count("unit_conversions", len(export_data["unit_conversions"]))
        result.add_entity_count("ingredients", len(export_data["ingredients"]))
        result.add_entity_count("products", len(export_data["products"]))
        result.add_entity_count("purchases", len(export_data["purchases"]))
        result.add_entity_count("inventory_items", len(export_data["inventory_items"]))
        result.add_entity_count("recipes", len(export_data["recipes"]))
        result.add_entity_count("finished_units", len(export_data["finished_units"]))
        result.add_entity_count("finished_goods", len(export_data["finished_goods"]))
        result.add_entity_count("compositions", len(export_data["compositions"]))
        result.add_entity_count("packages", len(export_data["packages"]))
        result.add_entity_count("package_finished_goods", len(export_data["package_finished_goods"]))
        result.add_entity_count("recipients", len(export_data["recipients"]))
        result.add_entity_count("events", len(export_data["events"]))
        result.add_entity_count("event_recipient_packages", len(export_data["event_recipient_packages"]))
        result.add_entity_count("event_production_targets", len(export_data["event_production_targets"]))
        result.add_entity_count("event_assembly_targets", len(export_data["event_assembly_targets"]))
        result.add_entity_count("production_records", len(export_data["production_records"]))
        result.add_entity_count("production_runs", len(export_data["production_runs"]))
        result.add_entity_count("assembly_runs", len(export_data["assembly_runs"]))

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
    tables_to_clear = [
        ProductionRecord,
        EventRecipientPackage,
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
        Ingredient,
        UnitConversion,
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
            quantity = float(record.get("component_quantity", 1.0))  # Ensure float

            # Validate quantity
            if quantity <= 0:
                result.add_error("composition", "unknown", "Quantity must be greater than 0")
                continue

            # Parent XOR validation: must have exactly one of assembly_id or package_id
            if finished_good_slug and package_name:
                result.add_error("composition", "unknown", "Composition must have exactly one parent (finished_good_slug or package_name)")
                continue
            if not finished_good_slug and not package_name:
                result.add_error("composition", "unknown", "Composition must have exactly one parent (finished_good_slug or package_name)")
                continue

            # Component XOR validation: must have exactly one component type
            component_refs = [finished_unit_slug, finished_good_component_slug, packaging_ingredient_slug]
            non_null_components = [x for x in component_refs if x is not None]
            if len(non_null_components) != 1:
                result.add_error("composition", finished_good_slug or package_name, "Composition must have exactly one component type")
                continue

            # Resolve parent reference
            assembly_id = None
            package_id = None

            if finished_good_slug:
                assembly = session.query(FinishedGood).filter_by(slug=finished_good_slug).first()
                if not assembly:
                    result.add_error("composition", finished_good_slug, f"Assembly not found: {finished_good_slug}")
                    continue
                assembly_id = assembly.id
            else:
                package = session.query(Package).filter_by(name=package_name).first()
                if not package:
                    result.add_error("composition", package_name, f"Package not found: {package_name}")
                    continue
                package_id = package.id

            # Resolve component reference
            finished_unit_id = None
            finished_good_id = None
            packaging_product_id = None

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
                    result.add_error("composition", finished_good_slug or package_name, f"FinishedUnit not found: {finished_unit_slug}")
                    continue
                finished_unit_id = fu.id
            elif finished_good_component_slug:
                fg = session.query(FinishedGood).filter_by(slug=finished_good_component_slug).first()
                if not fg:
                    result.add_error("composition", finished_good_slug or package_name, f"FinishedGood component not found: {finished_good_component_slug}")
                    continue
                finished_good_id = fg.id
            elif packaging_ingredient_slug:
                # Feature 011: Resolve packaging product by ingredient slug + brand
                ingredient = session.query(Ingredient).filter_by(slug=packaging_ingredient_slug).first()
                if not ingredient:
                    result.add_error("composition", finished_good_slug or package_name, f"Packaging ingredient not found: {packaging_ingredient_slug}")
                    continue
                # Find product by ingredient and brand
                product_query = session.query(Product).filter_by(ingredient_id=ingredient.id)
                if packaging_product_brand:
                    product_query = product_query.filter_by(brand=packaging_product_brand)
                product = product_query.first()
                if not product:
                    result.add_error("composition", finished_good_slug or package_name, f"Packaging product not found for ingredient {packaging_ingredient_slug}")
                    continue
                packaging_product_id = product.id

            # Check for duplicate
            if skip_duplicates:
                existing = session.query(Composition).filter_by(
                    assembly_id=assembly_id,
                    package_id=package_id,
                    finished_unit_id=finished_unit_id,
                    finished_good_id=finished_good_id,
                    packaging_product_id=packaging_product_id,
                ).first()
                if existing:
                    parent_name = finished_good_slug or package_name
                    component_name = finished_unit_slug or finished_good_component_slug or packaging_ingredient_slug
                    result.add_skip("composition", f"{parent_name}->{component_name}", "Already exists")
                    continue

            # Create composition
            comp = Composition(
                assembly_id=assembly_id,
                package_id=package_id,  # Feature 011
                finished_unit_id=finished_unit_id,
                finished_good_id=finished_good_id,
                packaging_product_id=packaging_product_id,  # Feature 011
                component_quantity=quantity,
                sort_order=record.get("sort_order", 0),
                component_notes=record.get("notes"),
            )

            session.add(comp)
            result.add_success("composition")

        except Exception as e:
            parent_name = record.get("finished_good_slug") or record.get("package_name") or "unknown"
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
                result.add_error("package_finished_good", "unknown", "Missing package_slug or finished_good_slug")
                continue

            # Resolve package reference - Package model doesn't have slug field,
            # so convert package_slug to name format for lookup
            package_name = package_slug.replace("_", " ").title()
            package = session.query(Package).filter_by(name=package_name).first()
            if not package:
                result.add_error("package_finished_good", package_slug, f"Package not found: {package_slug}")
                continue

            # Resolve finished good reference
            fg = session.query(FinishedGood).filter_by(slug=finished_good_slug).first()
            if not fg:
                result.add_error("package_finished_good", package_name, f"FinishedGood not found: {finished_good_slug}")
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = session.query(PackageFinishedGood).filter_by(
                    package_id=package.id,
                    finished_good_id=fg.id,
                ).first()
                if existing:
                    result.add_skip("package_finished_good", f"{package_name}->{finished_good_slug}", "Already exists")
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
                result.add_error("production_record", event_name or "unknown", "Missing event_name/slug, recipe_name/slug, or produced_at")
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
                result.add_error("production_record", event_name, f"Recipe not found: {recipe_name}")
                continue

            # Check for duplicate (by event + recipe + produced_at)
            if skip_duplicates:
                existing = session.query(ProductionRecord).filter_by(
                    event_id=event.id,
                    recipe_id=recipe.id,
                    produced_at=produced_at,
                ).first()
                if existing:
                    result.add_skip("production_record", f"{event_name}/{recipe_name}", "Already exists")
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
                result.add_error("event_recipient_package", "unknown", "Missing event_slug, recipient_name, or package_slug")
                continue

            # Resolve event reference - Event model doesn't have slug field,
            # so convert event_slug to name format for lookup
            event_name = event_slug.replace("_", " ").title()
            event = session.query(Event).filter_by(name=event_name).first()
            if not event:
                result.add_error("event_recipient_package", event_slug, f"Event not found: {event_slug}")
                continue

            # Resolve recipient reference (uses name directly)
            recipient = session.query(Recipient).filter_by(name=recipient_name).first()
            if not recipient:
                result.add_error("event_recipient_package", event_slug, f"Recipient not found: {recipient_name}")
                continue

            # Resolve package reference - Package model doesn't have slug field,
            # so convert package_slug to name format for lookup
            package_name = package_slug.replace("_", " ").title()
            package = session.query(Package).filter_by(name=package_name).first()
            if not package:
                result.add_error("event_recipient_package", event_slug, f"Package not found: {package_slug}")
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = session.query(EventRecipientPackage).filter_by(
                    event_id=event.id,
                    recipient_id=recipient.id,
                    package_id=package.id,
                ).first()
                if existing:
                    result.add_skip("event_recipient_package", f"{event_name}/{recipient_name}/{package_name}", "Already exists")
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
                result.add_error("event_production_target", "unknown", "Missing event_name or recipe_name")
                continue

            # Resolve event reference
            event = session.query(Event).filter_by(name=event_name).first()
            if not event:
                result.add_error("event_production_target", event_name, f"Event not found: {event_name}")
                continue

            # Resolve recipe reference
            recipe = session.query(Recipe).filter_by(name=recipe_name).first()
            if not recipe:
                result.add_error("event_production_target", event_name, f"Recipe not found: {recipe_name}")
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = session.query(EventProductionTarget).filter_by(
                    event_id=event.id,
                    recipe_id=recipe.id,
                ).first()
                if existing:
                    result.add_skip("event_production_target", f"{event_name}/{recipe_name}", "Already exists")
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
                result.add_error("event_assembly_target", "unknown", "Missing event_name or finished_good_slug")
                continue

            # Resolve event reference
            event = session.query(Event).filter_by(name=event_name).first()
            if not event:
                result.add_error("event_assembly_target", event_name, f"Event not found: {event_name}")
                continue

            # Resolve finished good reference
            finished_good = session.query(FinishedGood).filter_by(slug=finished_good_slug).first()
            if not finished_good:
                result.add_error("event_assembly_target", event_name, f"Finished good not found: {finished_good_slug}")
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = session.query(EventAssemblyTarget).filter_by(
                    event_id=event.id,
                    finished_good_id=finished_good.id,
                ).first()
                if existing:
                    result.add_skip("event_assembly_target", f"{event_name}/{finished_good_slug}", "Already exists")
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
                    produced_at = datetime.utcnow()

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
                result.add_error("assembly_run", finished_good_slug, f"Finished good not found: {finished_good_slug}")
                continue

            # Parse assembled_at timestamp
            assembled_at = None
            if assembled_at_str:
                try:
                    assembled_at = datetime.fromisoformat(assembled_at_str.replace("Z", "+00:00"))
                except ValueError:
                    assembled_at = datetime.utcnow()

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


def import_all_from_json_v3(file_path: str, mode: str = "merge") -> ImportResult:
    """
    Import all data from a v3.0 format JSON file.

    Supports two import modes:
    - "merge": Add new records, skip duplicates (default, safe for incremental backups)
    - "replace": Clear all existing data first, then import (full restore)

    Imports in dependency order:
    1. ingredients (no dependencies)
    2. unit_conversions (depends on ingredients)
    3. products (depends on ingredients)
    4. purchases (depends on products)
    5. inventory_items (depends on products)
    6. recipes (depends on ingredients)
    7. finished_units (depends on recipes)
    8. finished_goods (no dependencies)
    9. compositions (depends on finished_goods)
    10. packages (no dependencies)
    11. package_finished_goods (depends on packages, finished_goods)
    12. recipients (no dependencies)
    13. events (no dependencies)
    14. event_recipient_packages (depends on events, recipients, packages)
    15. production_records (depends on finished_units)

    Args:
        file_path: Path to v3.0 format JSON file
        mode: Import mode - "merge" (default) or "replace"

    Returns:
        ImportResult with detailed per-entity statistics

    Raises:
        ImportVersionError: If file version is not 3.0
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

        # Version validation - v3.2 only (no backward compatibility)
        version = data.get("version", "unknown")
        if version != "3.2":
            raise ImportVersionError(
                f"Unsupported file version: {version}. "
                "This application requires v3.2 format. "
                "Please export a new backup from a current version."
            )

        # Use single transaction for atomicity
        with session_scope() as session:
            # Replace mode: clear all tables first
            if mode == "replace":
                _clear_all_tables(session)

            # Import in dependency order
            # Note: For simplicity, we use existing import functions where possible
            # and the new v3.0 functions for new entities

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

                        # Density fields (4-field format only - v3.2)
                        density_args = {}
                        if ing.get("density_volume_value") is not None:
                            density_args["density_volume_value"] = ing.get("density_volume_value")
                            density_args["density_volume_unit"] = ing.get("density_volume_unit")
                            density_args["density_weight_value"] = ing.get("density_weight_value")
                            density_args["density_weight_unit"] = ing.get("density_weight_unit")

                        ingredient = Ingredient(
                            display_name=ing.get("display_name"),
                            slug=slug,
                            category=ing.get("category"),
                            recipe_unit=ing.get("recipe_unit"),
                            description=ing.get("description"),
                            notes=ing.get("notes"),
                            is_packaging=ing.get("is_packaging", False),  # Feature 011
                            **density_args,
                        )
                        session.add(ingredient)
                        result.add_success("ingredient")
                    except Exception as e:
                        result.add_error("ingredient", ing.get("slug", "unknown"), str(e))

            # Flush to get IDs for foreign keys
            session.flush()

            # 2. Unit conversions (depends on ingredients)
            if "unit_conversions" in data:
                for conv in data["unit_conversions"]:
                    try:
                        ing_slug = conv.get("ingredient_slug", "")
                        ingredient = session.query(Ingredient).filter_by(slug=ing_slug).first()
                        if not ingredient:
                            result.add_error("unit_conversion", ing_slug, f"Ingredient not found: {ing_slug}")
                            continue

                        if skip_duplicates:
                            existing = session.query(UnitConversion).filter_by(
                                ingredient_id=ingredient.id,
                                from_unit=conv.get("from_unit"),
                                to_unit=conv.get("to_unit"),
                            ).first()
                            if existing:
                                result.add_skip("unit_conversion", ing_slug, "Already exists")
                                continue

                        uc = UnitConversion(
                            ingredient_id=ingredient.id,
                            from_unit=conv.get("from_unit"),
                            from_quantity=conv.get("from_quantity", 1.0),
                            to_unit=conv.get("to_unit"),
                            to_quantity=1.0,
                            notes=conv.get("notes"),
                        )
                        session.add(uc)
                        result.add_success("unit_conversion")
                    except Exception as e:
                        result.add_error("unit_conversion", conv.get("ingredient_slug", "unknown"), str(e))

            session.flush()

            # 3. Products (depends on ingredients)
            if "products" in data:
                for prod_data in data["products"]:
                    try:
                        ing_slug = prod_data.get("ingredient_slug", "")
                        ingredient = session.query(Ingredient).filter_by(slug=ing_slug).first()
                        if not ingredient:
                            result.add_error("product", prod_data.get("brand", "unknown"), f"Ingredient not found: {ing_slug}")
                            continue

                        brand = prod_data.get("brand", "")
                        if skip_duplicates:
                            existing = session.query(Product).filter_by(
                                ingredient_id=ingredient.id,
                                brand=brand,
                            ).first()
                            if existing:
                                result.add_skip("product", brand, "Already exists")
                                continue

                        product = Product(
                            ingredient_id=ingredient.id,
                            brand=brand,
                            package_size=prod_data.get("package_size"),
                            package_type=prod_data.get("package_type"),
                            purchase_unit=prod_data.get("purchase_unit"),
                            purchase_quantity=prod_data.get("purchase_quantity"),
                            upc_code=prod_data.get("upc_code"),
                            preferred=prod_data.get("is_preferred", prod_data.get("preferred", False)),
                            notes=prod_data.get("notes"),
                        )
                        session.add(product)
                        result.add_success("product")
                    except Exception as e:
                        result.add_error("product", prod_data.get("brand", "unknown"), str(e))

            session.flush()

            # 4-5. Purchases and inventory_items handled similarly...
            # (Simplified for brevity - would add full implementation)

            # 6. Recipes (depends on ingredients)
            if "recipes" in data:
                from src.models.recipe import Recipe, RecipeIngredient
                
                for recipe_data in data["recipes"]:
                    try:
                        name = recipe_data.get("name", "")
                        
                        if skip_duplicates:
                            existing = session.query(Recipe).filter_by(name=name).first()
                            if existing:
                                result.add_skip("recipe", name, "Already exists")
                                continue
                        
                        # Validate ingredients exist before creating recipe
                        recipe_ingredients_data = recipe_data.get("ingredients", [])
                        validated_ingredients = []
                        missing_ingredients = []
                        
                        for ri_data in recipe_ingredients_data:
                            ing_slug = ri_data.get("ingredient_slug", "")
                            ingredient = session.query(Ingredient).filter_by(slug=ing_slug).first()
                            if ingredient:
                                validated_ingredients.append({
                                    "ingredient_id": ingredient.id,
                                    "quantity": ri_data.get("quantity"),
                                    "unit": ri_data.get("unit"),
                                    "notes": ri_data.get("notes"),
                                })
                            else:
                                missing_ingredients.append(ing_slug)
                        
                        if missing_ingredients:
                            result.add_error("recipe", name, f"Missing ingredients: {', '.join(missing_ingredients)}")
                            continue
                        
                        # Create recipe (Recipe model doesn't have slug field)
                        recipe = Recipe(
                            name=name,
                            category=recipe_data.get("category"),
                            source=recipe_data.get("source"),
                            yield_quantity=recipe_data.get("yield_quantity"),
                            yield_unit=recipe_data.get("yield_unit"),
                            yield_description=recipe_data.get("yield_description"),
                            estimated_time_minutes=recipe_data.get("estimated_time_minutes", 
                                                                   recipe_data.get("prep_time_minutes", 0) + 
                                                                   recipe_data.get("cook_time_minutes", 0)),
                            notes=recipe_data.get("notes"),
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
                        component_recipe = session.query(Recipe).filter_by(
                            name=component_recipe_name
                        ).first()
                        if not component_recipe:
                            result.add_error(
                                "recipe_component",
                                f"{recipe_name}->{component_recipe_name}",
                                f"Component recipe not found: {component_recipe_name}",
                            )
                            continue

                        # Check for duplicate
                        if skip_duplicates:
                            existing = session.query(RecipeComponent).filter_by(
                                recipe_id=parent_recipe.id,
                                component_recipe_id=component_recipe.id,
                            ).first()
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
                            display_name=fg_data.get("display_name", fg_data.get("name", "")),
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
            if "events" in data:
                from src.models.event import Event
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

                        event = Event(
                            name=name,
                            event_date=event_date,
                            year=year,
                            notes=evt.get("notes"),
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

            # Commit transaction
            session.commit()

    except ImportVersionError:
        raise  # Re-raise version errors
    except Exception as e:
        result.add_error("file", file_path, str(e))

    return result


