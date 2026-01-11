---
work_package_id: "WP05"
subtasks:
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
title: "Composition Integration - User Stories 4 & 5"
phase: "Phase 2 - Integration"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Composition Integration - User Stories 4 & 5

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Extend the Composition model to support materials; enable adding MaterialUnits and generic Material placeholders to FinishedGoods.

**User Stories:**
- US4: As a baker, I need to specify what materials go into each finished good
- US5: As a baker, I want to defer specific material choices until assembly time

**Success Criteria:**
- Can add MaterialUnit (specific) to FinishedGood composition
- Can add Material (generic placeholder) to FinishedGood composition
- Cost summary shows food costs separate from material costs
- Generic materials show "selection pending" indicator
- All acceptance scenarios from spec.md User Stories 4 & 5 pass

## Context & Constraints

**Reference Documents:**
- `kitty-specs/047-materials-management-system/spec.md` - User Stories 4 & 5
- `kitty-specs/047-materials-management-system/data-model.md` - Composition extension
- `src/models/composition.py` - Existing model to extend
- `src/services/composition_service.py` - Existing service to update

**Current Composition XOR Constraint (3-way):**
```python
(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL) OR
(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND packaging_product_id IS NULL) OR
(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NOT NULL)
```

**New XOR Constraint (5-way):**
Adds `material_unit_id` and `material_id` as two additional mutually exclusive options.

**Dependencies:**
- WP01 (Material models)
- WP04 (MaterialUnit service for cost calculations)

## Subtasks & Detailed Guidance

### Subtask T030 - Add material_unit_id Column
- **Purpose**: Allow specific MaterialUnit as composition component
- **File**: `src/models/composition.py`
- **Parallel?**: No
- **Steps**:
  1. Add new column:
     ```python
     material_unit_id = Column(
         Integer, ForeignKey("material_units.id", ondelete="RESTRICT"),
         nullable=True, index=True
     )
     ```
  2. Add index: `Index("idx_composition_material_unit", "material_unit_id")`
- **Notes**: Use RESTRICT to prevent deleting MaterialUnit used in compositions

### Subtask T031 - Add material_id Column
- **Purpose**: Allow generic Material as placeholder in composition
- **File**: `src/models/composition.py`
- **Parallel?**: No
- **Steps**:
  1. Add new column:
     ```python
     material_id = Column(
         Integer, ForeignKey("materials.id", ondelete="RESTRICT"),
         nullable=True, index=True
     )
     ```
  2. Add index: `Index("idx_composition_material", "material_id")`
- **Notes**: Generic placeholder - resolved to specific product at assembly time

### Subtask T032 - Update XOR Constraint to 5-way
- **Purpose**: Ensure exactly one component type per composition
- **File**: `src/models/composition.py`
- **Parallel?**: No
- **Steps**:
  1. Remove existing `ck_composition_exactly_one_component` constraint
  2. Add new 5-way constraint:
     ```python
     CheckConstraint(
         "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL AND material_unit_id IS NULL AND material_id IS NULL) OR "
         "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND packaging_product_id IS NULL AND material_unit_id IS NULL AND material_id IS NULL) OR "
         "(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NOT NULL AND material_unit_id IS NULL AND material_id IS NULL) OR "
         "(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL AND material_unit_id IS NOT NULL AND material_id IS NULL) OR "
         "(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL AND material_unit_id IS NULL AND material_id IS NOT NULL)",
         name="ck_composition_exactly_one_component"
     )
     ```
  3. Add unique constraints for new component types:
     ```python
     UniqueConstraint("assembly_id", "material_unit_id", name="uq_composition_assembly_material_unit"),
     UniqueConstraint("assembly_id", "material_id", name="uq_composition_assembly_material"),
     ```

### Subtask T033 - Add Material Relationships
- **Purpose**: Enable navigation from Composition to material components
- **File**: `src/models/composition.py`
- **Parallel?**: No
- **Steps**:
  1. Add relationships:
     ```python
     material_unit_component = relationship(
         "MaterialUnit", foreign_keys=[material_unit_id], lazy="joined"
     )
     material_component = relationship(
         "Material", foreign_keys=[material_id], lazy="joined"
     )
     ```
  2. Update `component_type` property to include new types
  3. Update `component_id` property
  4. Update `component_name` property

### Subtask T034 - Update Factory Methods
- **Purpose**: Provide clean API for creating material compositions
- **File**: `src/models/composition.py`
- **Parallel?**: No
- **Steps**:
  1. Add `create_material_unit_composition(assembly_id, material_unit_id, quantity, notes, sort_order)`:
     ```python
     @classmethod
     def create_material_unit_composition(cls, assembly_id, material_unit_id, quantity=1, notes=None, sort_order=0):
         return cls(
             assembly_id=assembly_id,
             finished_unit_id=None,
             finished_good_id=None,
             packaging_product_id=None,
             material_unit_id=material_unit_id,
             material_id=None,
             component_quantity=quantity,
             component_notes=notes,
             sort_order=sort_order,
             is_generic=False
         )
     ```
  2. Add `create_material_placeholder_composition(assembly_id, material_id, quantity, notes, sort_order)`:
     ```python
     @classmethod
     def create_material_placeholder_composition(cls, assembly_id, material_id, quantity=1, notes=None, sort_order=0):
         return cls(
             assembly_id=assembly_id,
             finished_unit_id=None,
             finished_good_id=None,
             packaging_product_id=None,
             material_unit_id=None,
             material_id=material_id,
             component_quantity=quantity,
             component_notes=notes,
             sort_order=sort_order,
             is_generic=True  # Generic placeholder
         )
     ```

### Subtask T035 - Update composition_service for Material Costs
- **Purpose**: Include material costs in composition calculations
- **File**: `src/services/composition_service.py`
- **Parallel?**: No
- **Steps**:
  1. Update `get_component_cost()` to handle MaterialUnit:
     - Call `material_unit_service.get_current_cost()`
  2. Update `get_component_cost()` to handle Material (generic):
     - Calculate estimated cost as average across all products
  3. Ensure `get_total_cost()` sums all component types

### Subtask T036 - Implement Food vs Material Cost Totals
- **Purpose**: Show separate cost breakdowns by component type
- **File**: `src/services/composition_service.py`
- **Parallel?**: No
- **Steps**:
  1. Implement `get_cost_breakdown(finished_good_id, session=None)`:
     ```python
     return {
         'food_cost': Decimal,      # FinishedUnit components
         'material_cost': Decimal,  # MaterialUnit + Material components
         'packaging_cost': Decimal, # packaging_product components
         'total_cost': Decimal,
         'has_estimated_costs': bool  # True if any generic materials
     }
     ```
  2. Mark costs as "estimated" when generic Material placeholders exist

### Subtask T037 - Update Composition Tests
- **Purpose**: Test new component types
- **File**: `src/tests/test_composition.py` (or existing composition tests)
- **Parallel?**: Yes
- **Steps**:
  1. Test creating MaterialUnit composition
  2. Test creating Material placeholder composition
  3. Test XOR constraint (only one component type allowed)
  4. Test cost calculation for MaterialUnit
  5. Test estimated cost for generic Material
  6. Test cost breakdown returns separate food/material totals

## Test Strategy

```python
import pytest
from src.models.composition import Composition
from src.services.composition_service import get_cost_breakdown

def test_create_material_unit_composition(db_session, sample_finished_good, sample_material_unit):
    """Can add MaterialUnit to FinishedGood composition."""
    comp = Composition.create_material_unit_composition(
        assembly_id=sample_finished_good.id,
        material_unit_id=sample_material_unit.id,
        quantity=2
    )
    db_session.add(comp)
    db_session.commit()

    assert comp.material_unit_id == sample_material_unit.id
    assert comp.is_generic is False
    assert comp.component_type == "material_unit"

def test_create_material_placeholder(db_session, sample_finished_good, sample_material):
    """Can add generic Material placeholder."""
    comp = Composition.create_material_placeholder_composition(
        assembly_id=sample_finished_good.id,
        material_id=sample_material.id,
        quantity=1
    )
    db_session.add(comp)
    db_session.commit()

    assert comp.material_id == sample_material.id
    assert comp.is_generic is True

def test_cost_breakdown_separates_food_and_material(db_session, fg_with_food_and_materials):
    """Cost breakdown shows food and material costs separately."""
    breakdown = get_cost_breakdown(fg_with_food_and_materials.id, session=db_session)

    assert breakdown['food_cost'] > 0
    assert breakdown['material_cost'] > 0
    assert breakdown['total_cost'] == breakdown['food_cost'] + breakdown['material_cost'] + breakdown['packaging_cost']
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Database migration needed | Since adding nullable columns, existing data remains valid |
| XOR constraint complexity | Thorough testing of all 5 valid states + invalid combinations |
| Circular imports | Use TYPE_CHECKING for Material/MaterialUnit imports |
| Cost calculation for generics | Mark as "estimated" clearly in UI |

## Definition of Done Checklist

- [ ] material_unit_id column added with index
- [ ] material_id column added with index
- [ ] XOR constraint updated to 5-way
- [ ] Relationships added with lazy="joined"
- [ ] Factory methods created for both component types
- [ ] Cost calculation includes material components
- [ ] Cost breakdown separates food/material/packaging
- [ ] Generic materials marked as "estimated" cost
- [ ] Tests cover all new functionality

## Review Guidance

**Reviewer should verify:**
1. XOR constraint allows exactly one of 5 component types
2. Factory methods set is_generic correctly (True for Material, False for MaterialUnit)
3. Cost calculation calls MaterialUnit service correctly
4. Estimated cost handling is clear for generic placeholders

## Activity Log

- 2026-01-10T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-10T20:56:39Z – claude – lane=doing – Starting composition integration for materials
- 2026-01-10T22:00:44Z – claude – lane=for_review – All subtasks complete: model columns, XOR constraint, relationships, factories, service updates, tests (24 passing)
- 2026-01-11T01:06:46Z – claude – lane=done – Review passed: Composition extended with material_unit_id/material_id, 5-way XOR constraint, factory methods. Layering violation fixed.
