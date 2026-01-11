# Research: Materials Management System

**Feature**: 047-materials-management-system
**Date**: 2026-01-10
**Status**: Complete

## Executive Summary

This research documents the patterns and decisions for implementing a materials management system that parallels the existing ingredient system. The materials system handles non-edible packaging materials (ribbons, boxes, bags, tissue) used in baking assemblies.

## Research Questions & Findings

### RQ-1: How should material hierarchy be structured?

**Decision**: Mandatory 3-level hierarchy (Category > Subcategory > Material > Product)

**Rationale**:
- Mirrors the Ingredient hierarchy pattern (parent_ingredient_id with hierarchy_level)
- Provides consistent organization for browsing and filtering
- Enables future expansion without schema changes

**Alternatives Considered**:
- Optional subcategory: Rejected for consistency; user confirmed mandatory levels
- Flat list with tags: Rejected; doesn't match user mental model

**Evidence**: Existing Ingredient model uses hierarchy_level 0/1/2 pattern with self-referential FK

### RQ-2: How should unit conversion work for materials?

**Decision**: Products store native purchase units; system converts to base units for storage

**Rationale**:
- Linear measurements stored in inches (feet, yards converted)
- Area measurements stored in square inches (square feet converted)
- "Each" items need no conversion
- Aggregation across products becomes simple addition in base units

**Alternatives Considered**:
- Store in native units with conversion at query time: More complex queries
- Require single unit per material: Too restrictive for real-world purchasing

**Evidence**: User clarification confirmed this approach (Session 2026-01-10)

### RQ-3: How should inventory enforcement work during assembly?

**Decision**: Block assembly when material inventory is insufficient (no bypass)

**Rationale**:
- Aligns with constitution principle II (Data Integrity)
- Prevents inventory going negative
- Forces user to correct inventory before proceeding

**Alternatives Considered**:
- "Record Anyway" bypass with flag: Rejected by user; creates reconciliation complexity

**Evidence**: User clarification explicitly selected strict enforcement (Session 2026-01-10)

### RQ-4: What fields should MaterialConsumption capture?

**Decision**: Full denormalized snapshot for historical accuracy

**Fields**:
- product_name (at time of consumption)
- material_name (at time of consumption)
- category_name (at time of consumption)
- subcategory_name (at time of consumption)
- quantity (consumed)
- unit_cost (at time of consumption)
- supplier_name (at time of consumption)

**Rationale**:
- Matches existing ProductionConsumption pattern
- Enables historical queries even after catalog changes
- Aligns with food consumption model

**Evidence**: User clarification confirmed full snapshot approach (Session 2026-01-10)

### RQ-5: How should generic material placeholders be resolved?

**Decision**: Inline resolution during assembly via dropdown per pending material

**Rationale**:
- Streamlined UX - no separate "finalize packaging" step
- User sees pending materials alongside resolved ones
- Validation ensures all materials resolved before save

**Alternatives Considered**:
- Modal dialog at assembly start: More disruptive
- Separate pre-assembly step: Extra workflow friction

**Evidence**: User clarification selected inline approach (Session 2026-01-10)

### RQ-6: Should materials use FIFO or weighted average costing?

**Decision**: Weighted average costing

**Rationale**:
- Materials are non-perishable
- FIFO overhead not justified for packaging materials
- Simpler implementation without FIFO lot tracking

**Evidence**: Spec assumptions section explicitly states this design choice

## Existing Code Patterns

### BaseModel Pattern
- All models inherit from `BaseModel` in `src/models/base.py`
- Provides: id (Integer PK), uuid (String), created_at, updated_at, to_dict()
- New material models will follow this pattern

### Hierarchy Pattern (from Ingredient)
- `parent_ingredient_id` as self-referential FK
- `hierarchy_level` column (0=root, 1=mid, 2=leaf)
- `children` relationship with dynamic loading
- For materials: MaterialCategory (0) > MaterialSubcategory (1) > Material (2)

### Purchase Pattern
- Immutable records (no updated_at)
- `unit_price` as Numeric(10, 4)
- `quantity_purchased` as Integer
- Links to Product via FK

### Consumption Snapshot Pattern (from ProductionConsumption)
- Denormalized fields (ingredient_slug, not FK)
- Quantity and unit stored together
- total_cost captured at consumption time
- Linked to parent run via FK with CASCADE delete

### Composition Pattern
- Polymorphic component references (finished_unit_id, finished_good_id, packaging_product_id)
- XOR constraint ensures exactly one component type
- `is_generic` flag for deferred resolution
- Will extend with material_unit_id and material_id columns

## Integration Points

### Composition Model Extension
The existing Composition model needs two new nullable columns:
- `material_unit_id` - FK to MaterialUnit for specific material assignments
- `material_id` - FK to Material for generic placeholder assignments

XOR constraint will be extended to 5-way (finished_unit, finished_good, packaging_product, material_unit, material).

### AssemblyRun Integration
When recording assembly:
1. Query Compositions with material components
2. For generic materials, resolve via inline dropdown
3. Create MaterialConsumption records with full snapshots
4. Decrement MaterialProduct inventory
5. Calculate total material cost for assembly run

### Import/Export Integration
Extend existing import/export v4.x format:
- New catalog sections: material_categories, material_subcategories, materials, material_products, material_units
- New transaction section: material_purchases
- MaterialConsumption included in assembly exports

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Composition XOR constraint complexity | Medium | Medium | Test constraint thoroughly; use factory methods |
| Unit conversion edge cases | Low | Medium | Comprehensive unit tests; validation on purchase |
| Historical snapshot data growth | Low | Low | Acceptable for single-user desktop app |

## Recommendations

1. **Implement models first** - All 7 models can be built in parallel (no internal dependencies)
2. **Service tests next** - Write test scaffolding while models are reviewed
3. **Composition integration last** - Most complex; requires careful XOR constraint handling
4. **Delegate import/export to Gemini** - Independent work package after core models exist
