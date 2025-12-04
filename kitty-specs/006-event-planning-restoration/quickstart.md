# Quickstart: Event Planning Restoration

**Feature**: 006-event-planning-restoration
**Purpose**: Quick reference for using the restored event planning system

## Core Workflow

```
1. Create FinishedUnits (baked items linked to recipes)
2. Create FinishedGoods (assemblies of FinishedUnits - e.g., "Cookie Assortment")
3. Create Packages (gift packages containing FinishedGoods)
4. Create Recipients (people receiving gifts)
5. Create Events (occasions like "Christmas 2024")
6. Assign Packages to Recipients for Events
7. View Recipe Needs, Shopping List, and Summary
```

## Service Usage Examples

### Package Service

```python
from src.services.package_service import PackageService

# Create a package
package = PackageService.create_package(
    name="Premium Gift Box",
    description="Deluxe assortment for special recipients",
    is_template=True
)

# Add FinishedGoods to package
PackageService.add_finished_good_to_package(
    package_id=package.id,
    finished_good_id=cookie_assortment.id,
    quantity=1
)
PackageService.add_finished_good_to_package(
    package_id=package.id,
    finished_good_id=brownie_box.id,
    quantity=2
)

# Calculate package cost (uses FIFO recipe costs)
total_cost = PackageService.calculate_package_cost(package.id)

# Get itemized breakdown
breakdown = PackageService.get_package_cost_breakdown(package.id)
# {
#     "items": [
#         {"name": "Cookie Assortment", "quantity": 1, "unit_cost": 12.50, "line_total": 12.50},
#         {"name": "Brownie Box", "quantity": 2, "unit_cost": 8.00, "line_total": 16.00}
#     ],
#     "total": 28.50
# }
```

### Event Service

```python
from src.services.event_service import EventService
from datetime import date

# Create an event
event = EventService.create_event(
    name="Christmas 2024",
    event_date=date(2024, 12, 25),
    year=2024,
    notes="Annual holiday baking"
)

# Assign packages to recipients
EventService.assign_package_to_recipient(
    event_id=event.id,
    recipient_id=grandma.id,
    package_id=premium_box.id,
    quantity=1
)

# Get event summary
summary = EventService.get_event_summary(event.id)
# {
#     "total_cost": Decimal("285.00"),
#     "recipient_count": 10,
#     "package_count": 12,
#     "assignment_count": 10,
#     "cost_by_recipient": [...]
# }

# Get recipe needs for baking planning
needs = EventService.get_recipe_needs(event.id)
# [
#     {"recipe_name": "Chocolate Chip Cookies", "batches_needed": 5},
#     {"recipe_name": "Brownies", "batches_needed": 3}
# ]

# Get shopping list with pantry comparison
shopping = EventService.get_shopping_list(event.id)
# [
#     {"ingredient_name": "Flour", "quantity_needed": 10.5, "quantity_on_hand": 5.0, "shortfall": 5.5},
#     {"ingredient_name": "Sugar", "quantity_needed": 8.0, "quantity_on_hand": 10.0, "shortfall": 0}
# ]
```

### Recipient Service

```python
from src.services.recipient_service import RecipientService

# Create recipients
recipient = RecipientService.create_recipient(
    name="Grandma Smith",
    household_name="Smith Family",
    address="123 Main St",
    notes="Loves chocolate, no nuts"
)

# Search recipients
matches = RecipientService.search_recipients("Smith")

# Check assignments before deletion
if RecipientService.check_recipient_has_assignments(recipient.id):
    # Show confirmation dialog
    count = RecipientService.get_recipient_assignment_count(recipient.id)
    # "Delete recipient with {count} event assignments?"
```

## Cost Calculation Chain

The cost flows through the system as follows:

```
Recipe.calculate_cost() (via RecipeService.calculate_actual_cost() - FIFO)
    |
    v
FinishedUnit.unit_cost = Recipe.cost / items_per_batch
    |
    v
Composition.total_cost = FinishedUnit.unit_cost * quantity
    |
    v
FinishedGood.total_cost = sum(Composition.total_cost)
    |
    v
PackageFinishedGood.line_total = FinishedGood.total_cost * quantity
    |
    v
Package.cost = sum(PackageFinishedGood.line_total)
    |
    v
EventRecipientPackage.cost = Package.cost * quantity
    |
    v
Event.total_cost = sum(EventRecipientPackage.cost)
```

## Data Model Overview

```
Recipe <-- FinishedUnit <-- Composition --> FinishedGood
                                                  |
                               PackageFinishedGood
                                                  |
                                              Package
                                                  |
                               EventRecipientPackage
                                    /           \
                               Event          Recipient
```

## Key Differences from Phase 3b

| Aspect | Phase 3b | Feature 006 |
|--------|----------|-------------|
| Bundle model | Existed as separate entity | Eliminated - FinishedGood assemblies |
| Package contents | PackageBundle -> Bundle -> FinishedGood | PackageFinishedGood -> FinishedGood |
| Cost calculation | Direct recipe costs | FIFO-based via RecipeService |
| FinishedGood role | Individual baked item | Assembly container |
| FinishedUnit | Did not exist | Individual baked item |

## Common Operations

### Year Filtering

```python
# Get available years for filter dropdown
years = EventService.get_available_years()  # [2024, 2023, 2022]

# Filter events by year
events_2024 = EventService.get_events_by_year(2024)
```

### Template Packages

```python
# Create reusable package template
template = PackageService.create_package(
    name="Standard Gift Box",
    is_template=True
)

# Duplicate template for specific use
custom = PackageService.duplicate_package(
    package_id=template.id,
    new_name="Mom's Gift Box"
)
```

### Dependency Checking

```python
# Before deleting a FinishedGood
packages = PackageService.get_packages_containing_finished_good(fg.id)
if packages:
    raise Error(f"Cannot delete: used in {len(packages)} packages")

# Before deleting a Package
if PackageService.check_package_has_event_assignments(package.id):
    raise Error("Cannot delete: assigned to events")
```

## Performance Notes

- Event Summary, Recipe Needs, and Shopping List tabs must load in <2 seconds for 50 assignments
- Cost calculations chain through multiple services - ensure eager loading for relationships
- Year filtering is indexed for fast lookups
