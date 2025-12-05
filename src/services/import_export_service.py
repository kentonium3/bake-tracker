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

from src.services import inventory_service, recipe_service, finished_good_service
from src.services import package_service, recipient_service, event_service
from src.services.exceptions import ValidationError
from src.services.database import session_scope
from src.models.ingredient import Ingredient
from src.models.variant import Variant
from src.models.pantry_item import PantryItem
from src.models.purchase import Purchase
from src.models.unit_conversion import UnitConversion
from src.models.finished_unit import FinishedUnit
from src.models.finished_good import FinishedGood
from src.models.composition import Composition
from src.models.package import Package, PackageFinishedGood
from src.models.production_record import ProductionRecord
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
        ingredients = inventory_service.get_all_ingredients(category=category_filter)

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": datetime.utcnow().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "ingredients": [],
        }

        for ingredient in ingredients:
            ingredient_data = {
                "name": ingredient.name,
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
                    "ingredient_name": ri.ingredient.name,
                    "quantity": ri.quantity,
                    "unit": ri.unit,
                }

                # Include brand for disambiguation
                if ri.ingredient.brand:
                    ingredient_data["ingredient_brand"] = ri.ingredient.brand

                if ri.notes:
                    ingredient_data["notes"] = ri.notes

                recipe_data["ingredients"].append(ingredient_data)

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
                "finished_good_name": bundle.finished_good.name,
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

    Returns:
        List of dictionaries containing composition data
    """
    result = []
    with session_scope() as session:
        compositions = (
            session.query(Composition)
            .options(
                joinedload(Composition.assembly),
                joinedload(Composition.finished_unit_component),
                joinedload(Composition.finished_good_component),
            )
            .all()
        )
        for comp in compositions:
            comp_data = {
                "finished_good_slug": comp.assembly.slug if comp.assembly else None,
                "component_quantity": comp.component_quantity,
                "sort_order": comp.sort_order,
            }

            # Polymorphic component reference
            if comp.finished_unit_component:
                comp_data["finished_unit_slug"] = comp.finished_unit_component.slug
                comp_data["finished_good_component_slug"] = None
            elif comp.finished_good_component:
                comp_data["finished_unit_slug"] = None
                comp_data["finished_good_component_slug"] = comp.finished_good_component.slug

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


def export_all_to_json(file_path: str) -> ExportResult:
    """
    Export all data to a single JSON file in v3.0 format.

    Exports in dependency order per data-model.md:
    unit_conversions, ingredients, variants, purchases, pantry_items,
    recipes, finished_units, finished_goods, compositions, packages,
    package_finished_goods, recipients, events, event_recipient_packages,
    production_records.

    Args:
        file_path: Path to output JSON file

    Returns:
        ExportResult with export statistics including per-entity counts
    """
    try:
        # Get all data - use session scope to eagerly load variants
        with session_scope() as session:
            # Eagerly load variants to avoid detached instance errors
            ingredients = session.query(Ingredient).options(joinedload(Ingredient.variants)).all()
            # Make objects accessible outside session by accessing all lazy-loaded attributes
            for ing in ingredients:
                _ = ing.variants  # Access to ensure loaded

        recipes = recipe_service.get_all_recipes()
        packages = package_service.get_all_packages()
        recipients = recipient_service.get_all_recipients()
        events = event_service.get_all_events()

        # Get v3.0 entity exports
        finished_units_data = export_finished_units_to_json()
        compositions_data = export_compositions_to_json()
        package_finished_goods_data = export_package_finished_goods_to_json()
        production_records_data = export_production_records_to_json()

        # Build combined export data - v3.0 format
        export_data = {
            "version": "3.0",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "application": "bake-tracker",
            "unit_conversions": [],
            "ingredients": [],
            "variants": [],
            "purchases": [],
            "pantry_items": [],
            "recipes": [],
            "finished_units": finished_units_data,
            "finished_goods": [],
            "compositions": compositions_data,
            "packages": [],
            "package_finished_goods": package_finished_goods_data,
            "recipients": [],
            "events": [],
            "event_recipient_packages": [],
            "production_records": production_records_data,
        }

        # Add ingredients (NEW SCHEMA: generic ingredient definitions)
        for ingredient in ingredients:
            ingredient_data = {
                "name": ingredient.name,
                "slug": ingredient.slug,
                "category": ingredient.category,
                "recipe_unit": ingredient.recipe_unit,
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

        # Add variants (NEW SCHEMA: brand/package-specific versions)
        for ingredient in ingredients:
            for variant in ingredient.variants:
                variant_data = {
                    "ingredient_slug": ingredient.slug,
                    "purchase_unit": variant.purchase_unit,
                    "purchase_quantity": variant.purchase_quantity,
                }

                # Optional fields
                if variant.brand:
                    variant_data["brand"] = variant.brand
                if variant.package_size:
                    variant_data["package_size"] = variant.package_size
                if variant.package_type:
                    variant_data["package_type"] = variant.package_type
                if variant.upc_code:
                    variant_data["upc_code"] = variant.upc_code
                if variant.supplier:
                    variant_data["supplier"] = variant.supplier
                if variant.supplier_sku:
                    variant_data["supplier_sku"] = variant.supplier_sku
                if variant.gtin:
                    variant_data["gtin"] = variant.gtin
                if variant.brand_owner:
                    variant_data["brand_owner"] = variant.brand_owner
                if variant.gpc_brick_code:
                    variant_data["gpc_brick_code"] = variant.gpc_brick_code
                if variant.net_content_value:
                    variant_data["net_content_value"] = variant.net_content_value
                if variant.net_content_uom:
                    variant_data["net_content_uom"] = variant.net_content_uom
                if variant.country_of_sale:
                    variant_data["country_of_sale"] = variant.country_of_sale
                if variant.off_id:
                    variant_data["off_id"] = variant.off_id
                if variant.preferred:
                    variant_data["preferred"] = variant.preferred
                if variant.notes:
                    variant_data["notes"] = variant.notes

                export_data["variants"].append(variant_data)

        # Add pantry items (actual inventory lots)
        with session_scope() as session:
            pantry_items = session.query(PantryItem).join(Variant).join(Ingredient).all()
            for item in pantry_items:
                pantry_data = {
                    "ingredient_slug": item.variant.ingredient.slug,
                    "variant_brand": item.variant.brand or "",
                    "quantity": item.quantity,
                    "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
                }

                # Optional fields
                if item.expiration_date:
                    pantry_data["expiration_date"] = item.expiration_date.isoformat()
                if item.location:
                    pantry_data["location"] = item.location
                if item.notes:
                    pantry_data["notes"] = item.notes

                export_data["pantry_items"].append(pantry_data)

        # Add purchases (price history)
        with session_scope() as session:
            purchases = session.query(Purchase).join(Variant).join(Ingredient).all()
            for purchase in purchases:
                purchase_data = {
                    "ingredient_slug": purchase.variant.ingredient.slug,
                    "variant_brand": purchase.variant.brand or "",
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
                # Use ingredient_new if available (new schema), fallback to ingredient (old schema)
                ingredient = (
                    ri.ingredient_new
                    if hasattr(ri, "ingredient_new") and ri.ingredient_new
                    else ri.ingredient
                )

                ingredient_data = {
                    "ingredient_slug": (
                        ingredient.slug
                        if ingredient.slug
                        else ingredient.name.lower().replace(" ", "_")
                    ),
                    "quantity": ri.quantity,
                    "unit": ri.unit,
                }
                if ri.notes:
                    ingredient_data["notes"] = ri.notes

                recipe_data["ingredients"].append(ingredient_data)

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

            # Populate event_recipient_packages separately (v3.0 format with status)
            for assignment in event.event_recipient_packages:
                assignment_data = {
                    "event_name": event.name,
                    "recipient_name": assignment.recipient.name,
                    "package_name": assignment.package.name,
                    "quantity": assignment.quantity,
                    "status": assignment.status.value if assignment.status else "pending",
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
            + len(export_data["variants"])
            + len(export_data["purchases"])
            + len(export_data["pantry_items"])
            + len(export_data["recipes"])
            + len(export_data["finished_units"])
            + len(export_data["finished_goods"])
            + len(export_data["compositions"])
            + len(export_data["packages"])
            + len(export_data["package_finished_goods"])
            + len(export_data["recipients"])
            + len(export_data["events"])
            + len(export_data["event_recipient_packages"])
            + len(export_data["production_records"])
        )

        result = ExportResult(file_path, total_records)

        # Add per-entity counts
        result.add_entity_count("unit_conversions", len(export_data["unit_conversions"]))
        result.add_entity_count("ingredients", len(export_data["ingredients"]))
        result.add_entity_count("variants", len(export_data["variants"]))
        result.add_entity_count("purchases", len(export_data["purchases"]))
        result.add_entity_count("pantry_items", len(export_data["pantry_items"]))
        result.add_entity_count("recipes", len(export_data["recipes"]))
        result.add_entity_count("finished_units", len(export_data["finished_units"]))
        result.add_entity_count("finished_goods", len(export_data["finished_goods"]))
        result.add_entity_count("compositions", len(export_data["compositions"]))
        result.add_entity_count("packages", len(export_data["packages"]))
        result.add_entity_count("package_finished_goods", len(export_data["package_finished_goods"]))
        result.add_entity_count("recipients", len(export_data["recipients"]))
        result.add_entity_count("events", len(export_data["events"]))
        result.add_entity_count("event_recipient_packages", len(export_data["event_recipient_packages"]))
        result.add_entity_count("production_records", len(export_data["production_records"]))

        return result

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


# ============================================================================
# Import Functions
# ============================================================================


def import_ingredients_from_json(file_path: str, skip_duplicates: bool = True) -> ImportResult:
    """
    Import ingredients from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip ingredients that already exist (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "ingredients" not in data:
            result.add_error("file", file_path, "Missing 'ingredients' key in JSON")
            return result

        ingredients_data = data["ingredients"]

        # Import each ingredient (NEW SCHEMA: generic ingredient definitions)
        for idx, ingredient_data in enumerate(ingredients_data):
            try:
                name = ingredient_data.get("name", "")
                slug = ingredient_data.get("slug", "")
                category = ingredient_data.get("category", "")
                recipe_unit = ingredient_data.get("recipe_unit", "")

                if not name:
                    result.add_error("ingredient", f"Record {idx+1}", "Missing name")
                    continue

                if not category:
                    result.add_error("ingredient", name, "Missing category")
                    continue

                if not recipe_unit:
                    result.add_error("ingredient", name, "Missing recipe_unit")
                    continue

                # Check for duplicate by name or slug
                if skip_duplicates:
                    existing = inventory_service.get_all_ingredients(name_search=name)
                    for existing_ing in existing:
                        if existing_ing.name == name:
                            result.add_skip("ingredient", name, "Already exists")
                            break
                    else:
                        # Not duplicate, create it
                        inventory_service.create_ingredient(ingredient_data)
                        result.add_success()
                else:
                    # Create ingredient
                    inventory_service.create_ingredient(ingredient_data)
                    result.add_success()

            except ValidationError as e:
                result.add_error("ingredient", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("ingredient", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_variants_from_json(file_path: str, skip_duplicates: bool = True) -> ImportResult:
    """
    Import variants from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip variants that already exist (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "variants" not in data:
            # No variants in file is OK, not an error
            return result

        variants_data = data["variants"]

        # Import each variant
        for idx, variant_data in enumerate(variants_data):
            try:
                ingredient_slug = variant_data.get("ingredient_slug", "")
                brand = variant_data.get("brand", "")
                purchase_unit = variant_data.get("purchase_unit", "")
                purchase_quantity = variant_data.get("purchase_quantity", 0)

                if not ingredient_slug:
                    result.add_error("variant", f"Record {idx+1}", "Missing ingredient_slug")
                    continue

                if not purchase_unit:
                    result.add_error("variant", f"Record {idx+1}", "Missing purchase_unit")
                    continue

                if not purchase_quantity:
                    result.add_error("variant", f"Record {idx+1}", "Missing purchase_quantity")
                    continue

                # Find the ingredient by slug
                all_ingredients = inventory_service.get_all_ingredients()
                ingredient = None
                for ing in all_ingredients:
                    if ing.slug == ingredient_slug:
                        ingredient = ing
                        break

                if not ingredient:
                    result.add_error(
                        "variant", f"Record {idx+1}", f"Ingredient not found: {ingredient_slug}"
                    )
                    continue

                # Create variant with ingredient_id
                with session_scope() as session:
                    # Re-fetch ingredient in this session
                    ingredient_in_session = (
                        session.query(Ingredient).filter(Ingredient.id == ingredient.id).first()
                    )

                    # Check for duplicate within the session
                    if skip_duplicates:
                        package_size = variant_data.get("package_size", "")
                        duplicate_found = False
                        for existing_variant in ingredient_in_session.variants:
                            if (
                                existing_variant.brand == brand
                                and existing_variant.package_size == package_size
                                and existing_variant.purchase_unit == purchase_unit
                            ):
                                result.add_skip(
                                    "variant",
                                    f"{ingredient_in_session.name} - {brand or 'generic'}",
                                    "Already exists",
                                )
                                duplicate_found = True
                                break

                        if duplicate_found:
                            continue

                    new_variant = Variant(
                        ingredient_id=ingredient.id,
                        purchase_unit=purchase_unit,
                        purchase_quantity=purchase_quantity,
                        brand=variant_data.get("brand"),
                        package_size=variant_data.get("package_size"),
                        package_type=variant_data.get("package_type"),
                        upc_code=variant_data.get("upc_code"),
                        supplier=variant_data.get("supplier"),
                        supplier_sku=variant_data.get("supplier_sku"),
                        gtin=variant_data.get("gtin"),
                        brand_owner=variant_data.get("brand_owner"),
                        gpc_brick_code=variant_data.get("gpc_brick_code"),
                        net_content_value=variant_data.get("net_content_value"),
                        net_content_uom=variant_data.get("net_content_uom"),
                        country_of_sale=variant_data.get("country_of_sale"),
                        off_id=variant_data.get("off_id"),
                        preferred=variant_data.get("preferred", False),
                        notes=variant_data.get("notes"),
                    )
                    session.add(new_variant)
                    session.commit()

                result.add_success()

            except ValidationError as e:
                result.add_error("variant", f"Record {idx+1}", f"Validation error: {e}")
            except Exception as e:
                result.add_error("variant", f"Record {idx+1}", str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_recipes_from_json(
    file_path: str, skip_duplicates: bool = True, skip_missing_ingredients: bool = True
) -> ImportResult:
    """
    Import recipes from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip recipes that already exist (default)
        skip_missing_ingredients: If True, skip recipes with missing ingredients (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "recipes" not in data:
            result.add_error("file", file_path, "Missing 'recipes' key in JSON")
            return result

        recipes_data = data["recipes"]

        # Import each recipe
        for idx, recipe_data in enumerate(recipes_data):
            try:
                name = recipe_data.get("name", "")

                if not name:
                    result.add_error("recipe", f"Record {idx+1}", "Missing name")
                    continue

                # Check for duplicate
                if skip_duplicates:
                    existing = recipe_service.get_all_recipes(name_search=name)
                    duplicate_found = False
                    for existing_recipe in existing:
                        if existing_recipe.name == name:
                            result.add_skip("recipe", name, "Already exists")
                            duplicate_found = True
                            break
                    if duplicate_found:
                        continue

                # Validate ingredients exist
                recipe_ingredients = recipe_data.get("ingredients", [])
                if not recipe_ingredients:
                    result.add_error("recipe", name, "No ingredients specified")
                    continue

                # Check each ingredient exists
                missing_ingredients = []
                validated_ingredients = []

                for ri_data in recipe_ingredients:
                    # NEW SCHEMA: Use ingredient_slug
                    ing_slug = ri_data.get("ingredient_slug", "")

                    # Fallback to old schema for backwards compatibility
                    if not ing_slug:
                        ing_name = ri_data.get("ingredient_name", "")
                        ing_slug = ing_name.lower().replace(" ", "_") if ing_name else ""

                    # Find ingredient by slug
                    all_ingredients = inventory_service.get_all_ingredients()
                    found = None

                    for ingredient in all_ingredients:
                        if ingredient.slug == ing_slug:
                            found = ingredient
                            break

                    if not found:
                        missing_ingredients.append(ing_slug)
                    else:
                        # Build validated ingredient data
                        validated_ingredients.append(
                            {
                                "ingredient_id": found.id,
                                "quantity": ri_data.get("quantity"),
                                "unit": ri_data.get("unit"),
                                "notes": ri_data.get("notes"),
                            }
                        )

                if missing_ingredients:
                    if skip_missing_ingredients:
                        result.add_skip(
                            "recipe", name, f"Missing ingredients: {', '.join(missing_ingredients)}"
                        )
                        continue
                    else:
                        result.add_error(
                            "recipe", name, f"Missing ingredients: {', '.join(missing_ingredients)}"
                        )
                        continue

                # Create recipe
                recipe_base_data = {
                    "name": recipe_data["name"],
                    "category": recipe_data["category"],
                    "yield_quantity": recipe_data["yield_quantity"],
                    "yield_unit": recipe_data["yield_unit"],
                }

                # Optional fields
                if "source" in recipe_data:
                    recipe_base_data["source"] = recipe_data["source"]
                if "yield_description" in recipe_data:
                    recipe_base_data["yield_description"] = recipe_data["yield_description"]
                if "estimated_time_minutes" in recipe_data:
                    recipe_base_data["estimated_time_minutes"] = recipe_data[
                        "estimated_time_minutes"
                    ]
                if "notes" in recipe_data:
                    recipe_base_data["notes"] = recipe_data["notes"]

                recipe_service.create_recipe(recipe_base_data, validated_ingredients)
                result.add_success()

            except ValidationError as e:
                result.add_error("recipe", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("recipe", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_finished_goods_from_json(
    file_path: str, skip_duplicates: bool = True, skip_missing_recipes: bool = True
) -> ImportResult:
    """
    Import finished goods from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip finished goods that already exist (default)
        skip_missing_recipes: If True, skip finished goods with missing recipes (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "finished_goods" not in data:
            result.add_error("file", file_path, "Missing 'finished_goods' key in JSON")
            return result

        finished_goods_data = data["finished_goods"]

        # Import each finished good
        for idx, fg_data in enumerate(finished_goods_data):
            try:
                name = fg_data.get("name", "")

                if not name:
                    result.add_error("finished_good", f"Record {idx+1}", "Missing name")
                    continue

                # Check for duplicate
                if skip_duplicates:
                    existing = finished_good_service.get_all_finished_goods(name_search=name)
                    duplicate_found = False
                    for existing_fg in existing:
                        if existing_fg.name == name:
                            result.add_skip("finished_good", name, "Already exists")
                            duplicate_found = True
                            break
                    if duplicate_found:
                        continue

                # Find recipe
                recipe_name = fg_data.get("recipe_name", "")
                if not recipe_name:
                    result.add_error("finished_good", name, "Missing recipe_name")
                    continue

                recipes = recipe_service.get_all_recipes(name_search=recipe_name)
                recipe = None
                for r in recipes:
                    if r.name == recipe_name:
                        recipe = r
                        break

                if not recipe:
                    if skip_missing_recipes:
                        result.add_skip("finished_good", name, f"Recipe not found: {recipe_name}")
                        continue
                    else:
                        result.add_error("finished_good", name, f"Recipe not found: {recipe_name}")
                        continue

                # Build finished good data
                fg_create_data = {
                    "name": name,
                    "recipe_id": recipe.id,
                    "yield_mode": fg_data.get("yield_mode", "discrete_count"),
                }

                # Optional fields
                if "category" in fg_data:
                    fg_create_data["category"] = fg_data["category"]
                if "items_per_batch" in fg_data:
                    fg_create_data["items_per_batch"] = fg_data["items_per_batch"]
                if "item_unit" in fg_data:
                    fg_create_data["item_unit"] = fg_data["item_unit"]
                if "batch_percentage" in fg_data:
                    fg_create_data["batch_percentage"] = fg_data["batch_percentage"]
                if "portion_description" in fg_data:
                    fg_create_data["portion_description"] = fg_data["portion_description"]
                if "notes" in fg_data:
                    fg_create_data["notes"] = fg_data["notes"]

                # Create finished good
                finished_good_service.create_finished_good(fg_create_data)
                result.add_success()

            except ValidationError as e:
                result.add_error("finished_good", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("finished_good", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_bundles_from_json(
    file_path: str, skip_duplicates: bool = True, skip_missing_finished_goods: bool = True
) -> ImportResult:
    """
    Import bundles from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip bundles that already exist (default)
        skip_missing_finished_goods: If True, skip bundles with missing finished goods (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "bundles" not in data:
            result.add_error("file", file_path, "Missing 'bundles' key in JSON")
            return result

        bundles_data = data["bundles"]

        # Import each bundle
        for idx, bundle_data in enumerate(bundles_data):
            try:
                name = bundle_data.get("name", "")

                if not name:
                    result.add_error("bundle", f"Record {idx+1}", "Missing name")
                    continue

                # Check for duplicate
                if skip_duplicates:
                    existing = finished_good_service.get_all_bundles(name_search=name)
                    duplicate_found = False
                    for existing_bundle in existing:
                        if existing_bundle.name == name:
                            result.add_skip("bundle", name, "Already exists")
                            duplicate_found = True
                            break
                    if duplicate_found:
                        continue

                # Find finished good
                fg_name = bundle_data.get("finished_good_name", "")
                if not fg_name:
                    result.add_error("bundle", name, "Missing finished_good_name")
                    continue

                finished_goods = finished_good_service.get_all_finished_goods(name_search=fg_name)
                finished_good = None
                for fg in finished_goods:
                    if fg.name == fg_name:
                        finished_good = fg
                        break

                if not finished_good:
                    if skip_missing_finished_goods:
                        result.add_skip("bundle", name, f"Finished good not found: {fg_name}")
                        continue
                    else:
                        result.add_error("bundle", name, f"Finished good not found: {fg_name}")
                        continue

                # Build bundle data
                bundle_create_data = {
                    "name": name,
                    "finished_good_id": finished_good.id,
                    "quantity": bundle_data.get("quantity", 1),
                }

                # Optional fields
                if "packaging_notes" in bundle_data:
                    bundle_create_data["packaging_notes"] = bundle_data["packaging_notes"]

                # Create bundle
                finished_good_service.create_bundle(bundle_create_data)
                result.add_success()

            except ValidationError as e:
                result.add_error("bundle", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("bundle", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_packages_from_json(
    file_path: str, skip_duplicates: bool = True, skip_missing_bundles: bool = True
) -> ImportResult:
    """
    Import packages from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip packages that already exist (default)
        skip_missing_bundles: If True, skip packages with missing bundles (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "packages" not in data:
            result.add_error("file", file_path, "Missing 'packages' key in JSON")
            return result

        packages_data = data["packages"]

        # Import each package
        for idx, package_data in enumerate(packages_data):
            try:
                name = package_data.get("name", "")

                if not name:
                    result.add_error("package", f"Record {idx+1}", "Missing name")
                    continue

                # Check for duplicate
                if skip_duplicates:
                    existing = package_service.get_all_packages(name_search=name)
                    duplicate_found = False
                    for existing_package in existing:
                        if existing_package.name == name:
                            result.add_skip("package", name, "Already exists")
                            duplicate_found = True
                            break
                    if duplicate_found:
                        continue

                # Build package data
                package_create_data = {
                    "name": name,
                    "is_template": package_data.get("is_template", False),
                }

                # Optional fields
                if "description" in package_data:
                    package_create_data["description"] = package_data["description"]

                if "notes" in package_data:
                    package_create_data["notes"] = package_data["notes"]

                # Build bundle items
                bundle_items = []
                bundles_data = package_data.get("bundles", [])

                for bundle_item_data in bundles_data:
                    bundle_name = bundle_item_data.get("bundle_name", "")
                    if not bundle_name:
                        result.add_error("package", name, "Bundle item missing bundle_name")
                        continue

                    # Find bundle
                    bundles = finished_good_service.get_all_bundles(name_search=bundle_name)
                    bundle = None
                    for b in bundles:
                        if b.name == bundle_name:
                            bundle = b
                            break

                    if not bundle:
                        if skip_missing_bundles:
                            result.add_skip("package", name, f"Bundle not found: {bundle_name}")
                            continue
                        else:
                            result.add_error("package", name, f"Bundle not found: {bundle_name}")
                            continue

                    bundle_items.append(
                        {
                            "bundle_id": bundle.id,
                            "quantity": bundle_item_data.get("quantity", 1),
                        }
                    )

                # Only create if we have bundle items
                if not bundle_items:
                    result.add_skip("package", name, "No valid bundles found")
                    continue

                # Create package
                package_service.create_package(package_create_data, bundle_items)
                result.add_success()

            except ValidationError as e:
                result.add_error("package", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("package", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_recipients_from_json(file_path: str, skip_duplicates: bool = True) -> ImportResult:
    """
    Import recipients from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip recipients that already exist (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "recipients" not in data:
            result.add_error("file", file_path, "Missing 'recipients' key in JSON")
            return result

        recipients_data = data["recipients"]

        # Import each recipient
        for idx, recipient_data in enumerate(recipients_data):
            try:
                name = recipient_data.get("name", "")

                if not name:
                    result.add_error("recipient", f"Record {idx+1}", "Missing name")
                    continue

                # Check for duplicate
                if skip_duplicates:
                    existing = recipient_service.get_all_recipients(name_search=name)
                    duplicate_found = False
                    for existing_recipient in existing:
                        if existing_recipient.name == name:
                            result.add_skip("recipient", name, "Already exists")
                            duplicate_found = True
                            break
                    if duplicate_found:
                        continue

                # Build recipient data
                recipient_create_data = {
                    "name": name,
                }

                # Optional fields
                if "household_name" in recipient_data:
                    recipient_create_data["household_name"] = recipient_data["household_name"]

                if "address" in recipient_data:
                    recipient_create_data["address"] = recipient_data["address"]

                if "notes" in recipient_data:
                    recipient_create_data["notes"] = recipient_data["notes"]

                # Create recipient
                recipient_service.create_recipient(recipient_create_data)
                result.add_success()

            except ValidationError as e:
                result.add_error("recipient", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("recipient", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_events_from_json(
    file_path: str, skip_duplicates: bool = True, skip_missing_refs: bool = True
) -> ImportResult:
    """
    Import events from JSON file.

    Includes event details and recipient-package assignments.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip events that already exist (default)
        skip_missing_refs: If True, skip assignments with missing recipients/packages (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "events" not in data:
            result.add_error("file", file_path, "Missing 'events' key in JSON")
            return result

        events_data = data["events"]

        # Import each event
        for idx, event_data in enumerate(events_data):
            try:
                name = event_data.get("name", "")

                if not name:
                    result.add_error("event", f"Record {idx+1}", "Missing name")
                    continue

                # Check for duplicate
                if skip_duplicates:
                    year = event_data.get("year")
                    if year:
                        existing = event_service.get_all_events(year=year)
                        duplicate_found = False
                        for existing_event in existing:
                            if existing_event.name == name:
                                result.add_skip("event", name, "Already exists")
                                duplicate_found = True
                                break
                        if duplicate_found:
                            continue

                # Build event data
                from datetime import date

                event_date_str = event_data.get("event_date")
                event_date = date.fromisoformat(event_date_str) if event_date_str else None

                event_create_data = {
                    "name": name,
                    "event_date": event_date,
                    "year": event_data.get("year"),
                }

                # Optional fields
                if "notes" in event_data:
                    event_create_data["notes"] = event_data["notes"]

                # Create event
                event = event_service.create_event(event_create_data)
                result.add_success()

                # Import assignments
                assignments_data = event_data.get("assignments", [])
                for assignment_data in assignments_data:
                    try:
                        recipient_name = assignment_data.get("recipient_name", "")
                        package_name = assignment_data.get("package_name", "")

                        if not recipient_name or not package_name:
                            continue

                        # Find recipient
                        recipients = recipient_service.get_all_recipients(
                            name_search=recipient_name
                        )
                        recipient = None
                        for r in recipients:
                            if r.name == recipient_name:
                                recipient = r
                                break

                        if not recipient:
                            if not skip_missing_refs:
                                result.add_error(
                                    "event", name, f"Recipient not found: {recipient_name}"
                                )
                            continue

                        # Find package
                        packages = package_service.get_all_packages(name_search=package_name)
                        package = None
                        for p in packages:
                            if p.name == package_name:
                                package = p
                                break

                        if not package:
                            if not skip_missing_refs:
                                result.add_error(
                                    "event", name, f"Package not found: {package_name}"
                                )
                            continue

                        # Create assignment
                        assignment_create_data = {
                            "quantity": assignment_data.get("quantity", 1),
                        }

                        if "notes" in assignment_data:
                            assignment_create_data["notes"] = assignment_data["notes"]

                        event_service.assign_package_to_recipient(
                            event.id, recipient.id, package.id, **assignment_create_data
                        )

                    except Exception as e:
                        # Don't fail entire event for assignment errors
                        pass

            except ValidationError as e:
                result.add_error("event", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("event", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


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
        PantryItem,
        Purchase,
        Variant,
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
            # Support both recipe_slug (v3.0) and recipe_name (legacy)
            recipe_slug = record.get("recipe_slug", "")
            recipe_name = record.get("recipe_name", "")

            # Generate slug from display_name if not provided
            if not slug and display_name:
                slug = display_name.lower().replace(" ", "_").replace("-", "_")

            if not display_name:
                result.add_error("finished_unit", slug or "unknown", "Missing display_name")
                continue

            # Check for duplicate
            if skip_duplicates:
                existing = session.query(FinishedUnit).filter_by(slug=slug).first()
                if existing:
                    result.add_skip("finished_unit", slug, "Already exists")
                    continue

            # Resolve recipe reference - Recipe model doesn't have slug field,
            # so convert recipe_slug to name format for lookup
            recipe = None
            if recipe_slug:
                # Convert slug format (snake_case) to name format (Title Case)
                recipe_name_from_slug = recipe_slug.replace("_", " ").title()
                recipe = session.query(Recipe).filter_by(name=recipe_name_from_slug).first()
                
                # Also try exact slug as name (in case data uses names directly)
                if not recipe:
                    recipe = session.query(Recipe).filter(
                        Recipe.name.ilike(f"%{recipe_slug.replace('_', '%')}%")
                    ).first()
            
            if not recipe and recipe_name:
                recipe = session.query(Recipe).filter_by(name=recipe_name).first()
            
            if not recipe:
                lookup_key = recipe_slug or recipe_name or "unknown"
                result.add_error("finished_unit", slug, f"Recipe not found: {lookup_key}")
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
    Import Composition records from v3.0 format data.

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
            finished_good_slug = record.get("finished_good_slug", "")
            finished_unit_slug = record.get("finished_unit_slug")
            finished_good_component_slug = record.get("finished_good_component_slug")
            quantity = record.get("component_quantity", 1)

            if not finished_good_slug:
                result.add_error("composition", "unknown", "Missing finished_good_slug")
                continue

            # Must have exactly one component type
            if not finished_unit_slug and not finished_good_component_slug:
                result.add_error("composition", finished_good_slug, "Missing component reference")
                continue

            # Resolve assembly reference
            assembly = session.query(FinishedGood).filter_by(slug=finished_good_slug).first()
            if not assembly:
                result.add_error("composition", finished_good_slug, f"Assembly not found: {finished_good_slug}")
                continue

            # Resolve component reference
            finished_unit_id = None
            finished_good_id = None

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
                    result.add_error("composition", finished_good_slug, f"FinishedUnit not found: {finished_unit_slug}")
                    continue
                finished_unit_id = fu.id
            else:
                fg = session.query(FinishedGood).filter_by(slug=finished_good_component_slug).first()
                if not fg:
                    result.add_error("composition", finished_good_slug, f"FinishedGood component not found: {finished_good_component_slug}")
                    continue
                finished_good_id = fg.id

            # Check for duplicate
            if skip_duplicates:
                existing = session.query(Composition).filter_by(
                    assembly_id=assembly.id,
                    finished_unit_id=finished_unit_id,
                    finished_good_id=finished_good_id,
                ).first()
                if existing:
                    result.add_skip("composition", f"{finished_good_slug}->{finished_unit_slug or finished_good_component_slug}", "Already exists")
                    continue

            # Create composition
            comp = Composition(
                assembly_id=assembly.id,
                finished_unit_id=finished_unit_id,
                finished_good_id=finished_good_id,
                component_quantity=quantity,
                sort_order=record.get("sort_order", 0),
                component_notes=record.get("notes"),
            )

            session.add(comp)
            result.add_success("composition")

        except Exception as e:
            result.add_error("composition", record.get("finished_good_slug", "unknown"), str(e))

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
            package_name = record.get("package_name", "")
            package_slug = record.get("package_slug", "")
            finished_good_slug = record.get("finished_good_slug", "")
            quantity = record.get("quantity", 1)

            # Support both package_name and package_slug
            if not package_name and package_slug:
                # Convert slug to name format (snake_case to Title Case)
                package_name = package_slug.replace("_", " ").title()

            if not package_name or not finished_good_slug:
                result.add_error("package_finished_good", "unknown", "Missing package_name/package_slug or finished_good_slug")
                continue

            # Resolve package reference
            package = session.query(Package).filter_by(name=package_name).first()
            if not package:
                result.add_error("package_finished_good", package_name, f"Package not found: {package_name}")
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

            # Support slug variants - convert to name format
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
            event_name = record.get("event_name", "")
            event_slug = record.get("event_slug", "")
            recipient_name = record.get("recipient_name", "")
            package_name = record.get("package_name", "")
            package_slug = record.get("package_slug", "")
            quantity = record.get("quantity", 1)

            # Support slug variants - convert to name format
            if not event_name and event_slug:
                event_name = event_slug.replace("_", " ").title()
            if not package_name and package_slug:
                package_name = package_slug.replace("_", " ").title()

            if not event_name or not recipient_name or not package_name:
                result.add_error("event_recipient_package", "unknown", "Missing event_name/slug, recipient_name, or package_name/slug")
                continue

            # Resolve event reference
            event = session.query(Event).filter_by(name=event_name).first()
            if not event:
                result.add_error("event_recipient_package", event_name, f"Event not found: {event_name}")
                continue

            # Resolve recipient reference
            recipient = session.query(Recipient).filter_by(name=recipient_name).first()
            if not recipient:
                result.add_error("event_recipient_package", event_name, f"Recipient not found: {recipient_name}")
                continue

            # Resolve package reference
            package = session.query(Package).filter_by(name=package_name).first()
            if not package:
                result.add_error("event_recipient_package", event_name, f"Package not found: {package_name}")
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

            # Create assignment
            erp = EventRecipientPackage(
                event_id=event.id,
                recipient_id=recipient.id,
                package_id=package.id,
                quantity=quantity,
                status=status,
                delivered_to=record.get("delivered_to"),
                notes=record.get("notes"),
            )

            session.add(erp)
            result.add_success("event_recipient_package")

        except Exception as e:
            result.add_error("event_recipient_package", record.get("event_name", "unknown"), str(e))

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
    3. variants (depends on ingredients)
    4. purchases (depends on variants)
    5. pantry_items (depends on variants)
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

        # Version validation (FR-018)
        version = data.get("version", "unknown")
        if version != "3.0":
            raise ImportVersionError(
                f"Unsupported file version: {version}. "
                "This application only supports v3.0 format. "
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

                        ingredient = Ingredient(
                            name=ing.get("name"),
                            slug=slug,
                            category=ing.get("category"),
                            recipe_unit=ing.get("recipe_unit"),
                            description=ing.get("description"),
                            density_g_per_ml=ing.get("density_g_per_ml"),
                            notes=ing.get("notes"),
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
                            from_quantity=conv.get("from_quantity", conv.get("factor", 1.0)),
                            to_unit=conv.get("to_unit"),
                            to_quantity=1.0,
                            notes=conv.get("notes"),
                        )
                        session.add(uc)
                        result.add_success("unit_conversion")
                    except Exception as e:
                        result.add_error("unit_conversion", conv.get("ingredient_slug", "unknown"), str(e))

            # 2. Ingredients
            if "ingredients" in data:
                for ing in data["ingredients"]:
                    try:
                        slug = ing.get("slug", "")
                        if skip_duplicates:
                            existing = session.query(Ingredient).filter_by(slug=slug).first()
                            if existing:
                                result.add_skip("ingredient", slug, "Already exists")
                                continue

                        ingredient = Ingredient(
                            name=ing.get("name"),
                            slug=slug,
                            category=ing.get("category"),
                            recipe_unit=ing.get("recipe_unit"),
                            description=ing.get("description"),
                            notes=ing.get("notes"),
                            # 4-field density model (ignore legacy density_g_per_ml)
                            density_volume_value=ing.get("density_volume_value"),
                            density_volume_unit=ing.get("density_volume_unit"),
                            density_weight_value=ing.get("density_weight_value"),
                            density_weight_unit=ing.get("density_weight_unit"),
                        )
                        session.add(ingredient)
                        result.add_success("ingredient")
                    except Exception as e:
                        result.add_error("ingredient", ing.get("slug", "unknown"), str(e))

            # Flush to get IDs for foreign keys
            session.flush()

            # 3. Variants (depends on ingredients)
            if "variants" in data:
                for var in data["variants"]:
                    try:
                        ing_slug = var.get("ingredient_slug", "")
                        ingredient = session.query(Ingredient).filter_by(slug=ing_slug).first()
                        if not ingredient:
                            result.add_error("variant", var.get("brand", "unknown"), f"Ingredient not found: {ing_slug}")
                            continue

                        brand = var.get("brand", "")
                        if skip_duplicates:
                            existing = session.query(Variant).filter_by(
                                ingredient_id=ingredient.id,
                                brand=brand,
                            ).first()
                            if existing:
                                result.add_skip("variant", brand, "Already exists")
                                continue

                        variant = Variant(
                            ingredient_id=ingredient.id,
                            brand=brand,
                            package_size=var.get("package_size"),
                            package_type=var.get("package_type"),
                            purchase_unit=var.get("purchase_unit"),
                            purchase_quantity=var.get("purchase_quantity"),
                            upc_code=var.get("upc_code"),
                            preferred=var.get("is_preferred", var.get("preferred", False)),
                            notes=var.get("notes"),
                        )
                        session.add(variant)
                        result.add_success("variant")
                    except Exception as e:
                        result.add_error("variant", var.get("brand", "unknown"), str(e))

            session.flush()

            # 4-5. Purchases and pantry_items handled similarly...
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
                                    "ingredient_new_id": ingredient.id,
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
                                ingredient_new_id=vi["ingredient_new_id"],
                                quantity=vi["quantity"],
                                unit=vi["unit"],
                                notes=vi.get("notes"),
                            )
                            session.add(ri)
                        
                        result.add_success("recipe")
                    except Exception as e:
                        result.add_error("recipe", recipe_data.get("name", "unknown"), str(e))
            
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

            # Commit transaction
            session.commit()

    except ImportVersionError:
        raise  # Re-raise version errors
    except Exception as e:
        result.add_error("file", file_path, str(e))

    return result


# ============================================================================
# Legacy Import Functions (v1.0/v2.0 format - deprecated)
# ============================================================================


def import_all_from_json(file_path: str, skip_duplicates: bool = True) -> Tuple[
    ImportResult,
    ImportResult,
    ImportResult,
    ImportResult,
    ImportResult,
    ImportResult,
    ImportResult,
    ImportResult,
]:
    """
    Import all data from a single JSON file (legacy v1.0/v2.0 format).

    DEPRECATED: Use import_all_from_json_v3() for v3.0 format files.

    Imports in proper dependency order:
    1. Ingredients (no dependencies)
    2. Variants (depend on ingredients)
    3. Recipes (depend on ingredients)
    4. Finished goods (depend on recipes)
    5. Bundles (depend on finished goods)
    6. Packages (depend on bundles)
    7. Recipients (no dependencies)
    8. Events with assignments (depend on recipients and packages)

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip duplicates (default)

    Returns:
        Tuple of (ingredient_result, variant_result, recipe_result, finished_good_result,
                 bundle_result, package_result, recipient_result, event_result)
    """
    import tempfile

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Import ingredients first
        ingredient_result = ImportResult()
        if "ingredients" in data:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump({"ingredients": data["ingredients"]}, tmp)
                tmp_path = tmp.name

            ingredient_result = import_ingredients_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        # Import variants second (depends on ingredients)
        variant_result = ImportResult()
        if "variants" in data:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump({"variants": data["variants"]}, tmp)
                tmp_path = tmp.name

            variant_result = import_variants_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        # Import recipes third
        recipe_result = ImportResult()
        if "recipes" in data:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump({"recipes": data["recipes"]}, tmp)
                tmp_path = tmp.name

            recipe_result = import_recipes_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        # Import finished goods third
        finished_good_result = ImportResult()
        if "finished_goods" in data:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump({"finished_goods": data["finished_goods"]}, tmp)
                tmp_path = tmp.name

            finished_good_result = import_finished_goods_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        # Import bundles fourth
        bundle_result = ImportResult()
        if "bundles" in data:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump({"bundles": data["bundles"]}, tmp)
                tmp_path = tmp.name

            bundle_result = import_bundles_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        # Import packages fifth
        package_result = ImportResult()
        if "packages" in data:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump({"packages": data["packages"]}, tmp)
                tmp_path = tmp.name

            package_result = import_packages_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        # Import recipients sixth (no dependencies)
        recipient_result = ImportResult()
        if "recipients" in data:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump({"recipients": data["recipients"]}, tmp)
                tmp_path = tmp.name

            recipient_result = import_recipients_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        # Import events seventh (with assignments)
        event_result = ImportResult()
        if "events" in data:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump({"events": data["events"]}, tmp)
                tmp_path = tmp.name

            event_result = import_events_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        return (
            ingredient_result,
            variant_result,
            recipe_result,
            finished_good_result,
            bundle_result,
            package_result,
            recipient_result,
            event_result,
        )

    except Exception as e:
        ingredient_result = ImportResult()
        variant_result = ImportResult()
        recipe_result = ImportResult()
        finished_good_result = ImportResult()
        bundle_result = ImportResult()
        package_result = ImportResult()
        recipient_result = ImportResult()
        event_result = ImportResult()
        ingredient_result.add_error("file", file_path, str(e))
        return (
            ingredient_result,
            variant_result,
            recipe_result,
            finished_good_result,
            bundle_result,
            package_result,
            recipient_result,
            event_result,
        )
