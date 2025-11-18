# Data Model: FinishedUnit Model Refactoring

**Feature**: FinishedUnit Model Refactoring
**Branch**: `004-finishedunit-model-refactoring`
**Date**: 2025-11-14
**Schema Version**: 2.0.0 (hierarchical model)

## Overview

Two-tier hierarchical system with individual consumable units (FinishedUnit) and assembled packages (FinishedGood) supporting polymorphic composition relationships through a junction entity (Composition).

## Entity Definitions

### FinishedUnit (Individual Consumable Items)

**Purpose**: Represents individual baked goods that can be consumed directly or used as components in assemblies.

**Source**: Renamed and enhanced version of existing FinishedGood model.

**Attributes**:
- `id` (Primary Key): Integer, auto-increment
- `slug` (Unique): String, URL-safe identifier for references
- `display_name`: String, user-facing name (e.g., "Chocolate Chip Cookie")
- `description`: Text, optional detailed description
- `recipe_id` (Foreign Key): References Recipe entity
- `unit_cost`: Decimal, cost per individual unit
- `inventory_count`: Integer, current available quantity
- `production_notes`: Text, optional baking or storage notes
- `created_at`: DateTime, record creation timestamp
- `updated_at`: DateTime, last modification timestamp

**Relationships**:
- `recipe`: Many-to-One relationship with Recipe
- `components_in`: One-to-Many relationship with Composition (as component)
- `pantry_consumptions`: One-to-Many relationship with PantryConsumption
- `production_runs`: One-to-Many relationship with ProductionRun

**Validation Rules**:
- `slug` must be unique across all FinishedUnits
- `unit_cost` must be non-negative
- `inventory_count` must be non-negative
- `display_name` is required

### FinishedGood (Assembly Packages)

**Purpose**: Represents assembled packages containing multiple components (FinishedUnits and/or other FinishedGoods).

**Source**: New entity for hierarchical package management.

**Attributes**:
- `id` (Primary Key): Integer, auto-increment
- `slug` (Unique): String, URL-safe identifier for references
- `display_name`: String, user-facing name (e.g., "Holiday Gift Box")
- `description`: Text, optional detailed description
- `assembly_type`: Enum, categorization (gift_box, variety_pack, holiday_set)
- `packaging_instructions`: Text, optional assembly guidance
- `total_cost`: Decimal, calculated from component costs
- `inventory_count`: Integer, current available assembled packages
- `created_at`: DateTime, record creation timestamp
- `updated_at`: DateTime, last modification timestamp

**Relationships**:
- `compositions`: One-to-Many relationship with Composition (as assembly)
- `components_in`: One-to-Many relationship with Composition (as component)

**Validation Rules**:
- `slug` must be unique across all FinishedGoods
- `total_cost` must be non-negative
- `inventory_count` must be non-negative
- `display_name` is required
- `assembly_type` must be valid enum value

### Composition (Junction Entity)

**Purpose**: Links FinishedGoods to their component items, supporting polymorphic relationships where components can be either FinishedUnits or other FinishedGoods.

**Source**: New junction entity implementing separate foreign keys pattern.

**Attributes**:
- `id` (Primary Key): Integer, auto-increment
- `assembly_id` (Foreign Key): References FinishedGood (the package)
- `finished_unit_id` (Foreign Key): Optional, references FinishedUnit component
- `finished_good_id` (Foreign Key): Optional, references FinishedGood component
- `component_quantity`: Integer, number of this component in the assembly
- `component_notes`: Text, optional notes about this specific component usage
- `sort_order`: Integer, optional ordering within assembly
- `created_at`: DateTime, record creation timestamp

**Relationships**:
- `assembly`: Many-to-One relationship with FinishedGood (parent)
- `finished_unit_component`: Many-to-One relationship with FinishedUnit (child)
- `finished_good_component`: Many-to-One relationship with FinishedGood (child)

**Validation Rules**:
- Exactly one of `finished_unit_id` or `finished_good_id` must be non-null
- `component_quantity` must be positive
- `assembly_id` is required
- Circular references prohibited (assembly cannot contain itself transitively)

### AssemblyType (Enumeration)

**Purpose**: Categorizes FinishedGood assemblies for organization and business logic.

**Values**:
- `gift_box`: Traditional gift packaging
- `variety_pack`: Multiple types for sampling
- `holiday_set`: Seasonal themed collections
- `bulk_pack`: Quantity-focused packaging
- `custom_order`: Specific customer requests

## Relationship Diagram

```
FinishedUnit
    ├── 1:N → Composition (as finished_unit_component)
    ├── N:1 → Recipe
    ├── 1:N → PantryConsumption
    └── 1:N → ProductionRun

FinishedGood
    ├── 1:N → Composition (as assembly)
    └── 1:N → Composition (as finished_good_component)

Composition
    ├── N:1 → FinishedGood (assembly)
    ├── N:1 → FinishedUnit (finished_unit_component) [Optional]
    └── N:1 → FinishedGood (finished_good_component) [Optional]

Recipe
    └── 1:N → FinishedUnit

PantryConsumption
    └── N:1 → FinishedUnit

ProductionRun
    └── N:1 → FinishedUnit
```

## Migration Mapping

### Existing FinishedGood → FinishedUnit
- All current FinishedGood records become FinishedUnit records
- Field mappings preserve data integrity:
  - `id` → `id` (preserved)
  - `slug` → `slug` (preserved)
  - `display_name` → `display_name` (preserved)
  - `recipe_id` → `recipe_id` (preserved)
  - `cost_per_unit` → `unit_cost` (renamed)
  - Additional fields populated with defaults

### New Entities
- FinishedGood table created fresh
- Composition table created fresh
- AssemblyType enum defined in application code

## Constraints and Indexes

### Database Constraints
- Primary keys on all entities
- Foreign key constraints with cascading rules
- Unique constraints on slug fields
- Check constraints for non-negative costs and quantities
- Composition constraint ensuring exactly one component reference

### Performance Indexes
- Index on `FinishedUnit.slug` for lookups
- Index on `FinishedGood.slug` for lookups
- Index on `Composition.assembly_id` for hierarchy queries
- Index on `Composition.finished_unit_id` for component lookups
- Index on `Composition.finished_good_id` for component lookups
- Composite index on `(assembly_id, sort_order)` for ordered component lists

## Business Logic Rules

### Cost Calculation
- FinishedUnit cost is direct unit cost
- FinishedGood cost is sum of (component_quantity × component_unit_cost) for all components
- Hierarchical cost calculation traverses all composition levels

### Inventory Management
- FinishedUnit inventory decrements with direct consumption or assembly creation
- FinishedGood inventory represents assembled packages available
- Assembly creation checks component availability

### Hierarchy Validation
- Maximum hierarchy depth: 5 levels
- Circular reference prevention using breadth-first traversal
- Component availability validation before assembly creation

## Query Patterns

### Common Operations
- Get all components of an assembly (direct and nested)
- Calculate total cost of an assembly
- Check inventory availability for assembly creation
- Find all assemblies using a specific component
- Validate hierarchy for circular references

### Performance Considerations
- Hierarchy traversal uses iterative application logic
- Component queries leverage foreign key indexes
- Batch operations for large assembly modifications
- Lazy loading for deep hierarchy navigation

## Future Extensions

### Web Migration Compatibility
- Add `user_id` fields for multi-tenant support
- Maintain polymorphic relationships across database backends
- Service layer abstraction supports API wrapper implementation

### Enhanced Features
- Component substitution rules
- Assembly versioning and history
- Bulk pricing tiers for assemblies
- Component usage analytics