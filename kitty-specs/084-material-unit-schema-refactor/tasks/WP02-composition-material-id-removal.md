---
work_package_id: WP02
title: Composition material_id Removal
lane: "doing"
dependencies: [WP01]
base_branch: 084-material-unit-schema-refactor-WP01
base_commit: 64b0d902e56932294608362cfea41eec2fba009a
created_at: '2026-01-30T17:35:56.645658+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Wave 1 - Schema Foundation
assignee: ''
agent: "claude-opus"
shell_pid: "43497"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-30T17:11:03Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Composition material_id Removal

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 (MaterialUnit FK must exist before Composition cleanup).

---

## Objectives & Success Criteria

**Goal**: Remove material_id from Composition model and update XOR constraint from 5-way to 4-way.

**Success Criteria**:
- [ ] Composition model does NOT have `material_id` column
- [ ] Composition model does NOT have `material_component` relationship
- [ ] XOR CheckConstraint validates exactly one of 4 component types (not 5)
- [ ] `create_material_placeholder_composition()` factory method removed
- [ ] `component_type` property does NOT return "material"
- [ ] `_estimate_material_cost()` method removed
- [ ] All Composition model tests pass (updated for 4-way XOR)

---

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md`
- Plan: `kitty-specs/084-material-unit-schema-refactor/plan.md`
- Data Model: `kitty-specs/084-material-unit-schema-refactor/data-model.md`

**Key Pattern** (from plan.md):
```python
# 4-way XOR constraint
CheckConstraint(
    "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL AND material_unit_id IS NULL) OR "
    "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND packaging_product_id IS NULL AND material_unit_id IS NULL) OR "
    "(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NOT NULL AND material_unit_id IS NULL) OR "
    "(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL AND material_unit_id IS NOT NULL)",
    name="ck_composition_exactly_one_component",
)
```

**Architectural Constraints**:
- Existing Compositions with material_id will be handled by migration script (WP09)
- material_unit_id remains the only path for material components
- Must update all helper methods that reference material_id

---

## Subtasks & Detailed Guidance

### Subtask T006 – Remove material_id Column

**Purpose**: Eliminate the generic material reference from Composition.

**Files**: `src/models/composition.py`

**Steps**:
1. Locate the `material_id` column definition:
   ```python
   material_id = Column(
       Integer,
       ForeignKey("materials.id", ondelete="RESTRICT"),
       nullable=True,
       index=True,
   )
   ```

2. Remove this column definition entirely

3. Locate the `material_component` relationship:
   ```python
   material_component = relationship("Material", foreign_keys=[material_id], lazy="joined")
   ```

4. Remove this relationship entirely

5. Check for any type hints or docstrings that mention material_id

**Validation**:
- [ ] `material_id` column removed
- [ ] `material_component` relationship removed
- [ ] No remaining references to material_id in class definition

---

### Subtask T007 – Update XOR CheckConstraint

**Purpose**: Change from 5-way to 4-way XOR (remove material_id condition).

**Files**: `src/models/composition.py`

**Steps**:
1. Locate the existing XOR CheckConstraint in `__table_args__`:
   ```python
   CheckConstraint(
       "(finished_unit_id IS NOT NULL AND ... AND material_id IS NULL) OR "
       "...(5 conditions)...",
       name="ck_composition_exactly_one_component",
   )
   ```

2. Replace with 4-way constraint (remove all material_id references):
   ```python
   CheckConstraint(
       "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND "
       "packaging_product_id IS NULL AND material_unit_id IS NULL) OR "
       "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND "
       "packaging_product_id IS NULL AND material_unit_id IS NULL) OR "
       "(finished_unit_id IS NULL AND finished_good_id IS NULL AND "
       "packaging_product_id IS NOT NULL AND material_unit_id IS NULL) OR "
       "(finished_unit_id IS NULL AND finished_good_id IS NULL AND "
       "packaging_product_id IS NULL AND material_unit_id IS NOT NULL)",
       name="ck_composition_exactly_one_component",
   )
   ```

3. Verify the constraint covers all 4 component types:
   - finished_unit_id
   - finished_good_id
   - packaging_product_id
   - material_unit_id

**Validation**:
- [ ] XOR constraint has exactly 4 conditions (OR clauses)
- [ ] No mention of material_id in constraint
- [ ] Each condition sets exactly one FK to NOT NULL
- [ ] Constraint name unchanged (for migration continuity)

---

### Subtask T008 – Remove Factory Method

**Purpose**: Remove the material placeholder factory since generic materials are no longer supported.

**Files**: `src/models/composition.py`

**Steps**:
1. Locate the factory method:
   ```python
   @classmethod
   def create_material_placeholder_composition(
       cls,
       assembly_id: int,
       material_id: int,
       quantity: int = 1,
       notes: str = None,
       sort_order: int = 0,
   ) -> "Composition":
       """Factory for generic Material placeholder - TO BE REMOVED."""
       ...
   ```

2. Remove the entire method

3. Check if there are any calls to this method in the codebase:
   ```bash
   grep -r "create_material_placeholder_composition" src/
   ```

4. If calls exist, they must be removed in the service layer (WP05)

**Validation**:
- [ ] `create_material_placeholder_composition()` method removed
- [ ] No calls to removed method remain in models layer
- [ ] Other factory methods (create_material_unit_composition, etc.) remain intact

---

### Subtask T009 – Update Component Properties

**Purpose**: Remove material_id handling from component_type, component_id, component_name properties.

**Files**: `src/models/composition.py`

**Steps**:
1. Update `component_type` property:
   ```python
   @property
   def component_type(self) -> str:
       if self.finished_unit_id is not None:
           return "finished_unit"
       elif self.finished_good_id is not None:
           return "finished_good"
       elif self.packaging_product_id is not None:
           return "packaging_product"
       elif self.material_unit_id is not None:
           return "material_unit"
       # REMOVE: elif self.material_id is not None: return "material"
       return "unknown"
   ```

2. Update `component_id` property:
   ```python
   @property
   def component_id(self) -> Optional[int]:
       return (
           self.finished_unit_id
           or self.finished_good_id
           or self.packaging_product_id
           or self.material_unit_id
           # REMOVE: or self.material_id
       )
   ```

3. Update `component_name` property:
   ```python
   @property
   def component_name(self) -> str:
       if self.finished_unit:
           return self.finished_unit.display_name
       elif self.finished_good:
           return self.finished_good.name
       elif self.packaging_product:
           return self.packaging_product.name
       elif self.material_unit:
           return self.material_unit.name
       # REMOVE: elif self.material_component: return self.material_component.name
       return "Unknown"
   ```

**Validation**:
- [ ] `component_type` returns only 4 values + "unknown"
- [ ] `component_id` checks only 4 FK fields
- [ ] `component_name` handles only 4 relationship types
- [ ] No references to `material_component` or `material_id`

---

### Subtask T010 – Remove Cost Methods

**Purpose**: Remove material-specific cost estimation code.

**Files**: `src/models/composition.py`

**Steps**:
1. Locate `get_component_cost()` method and remove the material branch:
   ```python
   def get_component_cost(self) -> Decimal:
       if self.material_unit:
           return self._calculate_material_unit_cost()
       # REMOVE: elif self.material_component:
       #     return self._estimate_material_cost()
       elif self.finished_unit:
           ...
   ```

2. Remove `_estimate_material_cost()` method entirely:
   ```python
   # REMOVE THIS ENTIRE METHOD:
   def _estimate_material_cost(self) -> Decimal:
       """Estimate cost for generic material placeholder."""
       ...
   ```

3. Verify `_calculate_material_unit_cost()` method is preserved (handles material_unit_id)

**Validation**:
- [ ] `get_component_cost()` no longer has material_component branch
- [ ] `_estimate_material_cost()` method removed
- [ ] `_calculate_material_unit_cost()` preserved and unchanged

---

### Subtask T011 – Update Validation Method

**Purpose**: Update validate_polymorphic_constraint() for 4-way validation.

**Files**: `src/models/composition.py`

**Steps**:
1. Locate the validation method:
   ```python
   def validate_polymorphic_constraint(self) -> bool:
       """Validate exactly one component type is set."""
       component_ids = [
           self.finished_unit_id,
           self.finished_good_id,
           self.packaging_product_id,
           self.material_unit_id,
           # REMOVE: self.material_id,
       ]
       set_count = sum(1 for cid in component_ids if cid is not None)
       return set_count == 1
   ```

2. Remove `self.material_id` from the list

3. Update any docstrings or comments that mention 5 component types

**Validation**:
- [ ] Validation checks exactly 4 component IDs
- [ ] No reference to material_id in validation
- [ ] Docstrings updated to mention 4 component types

---

### Subtask T012 – Update Composition Model Tests

**Purpose**: Ensure model tests work with 4-way XOR constraint.

**Files**: `src/tests/test_composition.py` (or similar)

**Steps**:
1. Find existing Composition model tests

2. Remove tests for material_id / material placeholder:
   - Tests for `create_material_placeholder_composition()`
   - Tests that set material_id directly
   - Tests that expect component_type == "material"

3. Update XOR constraint tests:
   ```python
   def test_xor_constraint_rejects_two_components():
       # Should only test 4 component types now
       ...

   def test_xor_constraint_requires_one_component():
       # Update to check 4 component types
       ...
   ```

4. Update any helper fixtures that create Compositions with material_id

5. Run tests:
   ```bash
   ./run-tests.sh src/tests/test_composition.py -v
   ```

**Validation**:
- [ ] No tests reference material_id or material_component
- [ ] XOR tests validate 4-way constraint
- [ ] All tests pass

---

## Test Strategy

**Required Tests**:
1. XOR constraint: Each of 4 component types can be set alone
2. XOR constraint: Two component types set simultaneously fails
3. XOR constraint: Zero component types set fails
4. component_type property returns correct value for each type
5. component_name property returns correct name for each type
6. get_component_cost() works for material_unit_id

**Test Commands**:
```bash
# Run Composition model tests
./run-tests.sh src/tests/test_composition.py -v

# Run with coverage
./run-tests.sh src/tests/test_composition.py -v --cov=src/models
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing Compositions with material_id | Migration script (WP09) handles data transformation |
| Breaking service layer code | Services updated in WP05 (sequenced dependency) |
| Orphaned material references in codebase | Search and remove in service layer work |
| Constraint migration issues | Keep constraint name same for continuity |

---

## Definition of Done Checklist

- [ ] material_id column removed from Composition model
- [ ] material_component relationship removed
- [ ] XOR constraint updated to 4-way
- [ ] create_material_placeholder_composition() removed
- [ ] component_type, component_id, component_name updated
- [ ] _estimate_material_cost() removed
- [ ] validate_polymorphic_constraint() updated
- [ ] All model tests pass
- [ ] No linting errors

---

## Review Guidance

**Key Checkpoints**:
1. Verify XOR constraint has exactly 4 OR conditions
2. Verify no remaining references to material_id in model file
3. Verify no remaining references to material_component
4. Verify factory methods are complete (only 4 remain)
5. Run test suite to confirm no regressions

---

## Activity Log

- 2026-01-30T17:11:03Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-30T17:41:16Z – unknown – shell_pid=28991 – lane=for_review – Ready for review: material_id column removed, XOR constraint updated to 4-way, 14 model tests pass
- 2026-01-30T18:38:51Z – claude-opus – shell_pid=43497 – lane=doing – Started review via workflow command
