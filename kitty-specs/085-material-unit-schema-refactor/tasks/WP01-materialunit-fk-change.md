---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "MaterialUnit FK Change"
phase: "Wave 1 - Schema Foundation"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "42490"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: []
history:
  - timestamp: "2026-01-30T17:11:03Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – MaterialUnit FK Change

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this is the starting work package.

---

## Objectives & Success Criteria

**Goal**: Change MaterialUnit's parent from Material to MaterialProduct by refactoring the foreign key relationship.

**Success Criteria**:
- [ ] MaterialUnit model has `material_product_id` FK (NOT NULL, indexed, CASCADE delete)
- [ ] MaterialUnit model does NOT have `material_id` field
- [ ] MaterialProduct model has `material_units` relationship with cascade delete-orphan
- [ ] Material model does NOT have `units` relationship
- [ ] UniqueConstraint enforces (material_product_id, slug) and (material_product_id, name)
- [ ] All existing MaterialUnit model tests pass (updated for new FK)

---

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md`
- Plan: `kitty-specs/085-material-unit-schema-refactor/plan.md`
- Data Model: `kitty-specs/085-material-unit-schema-refactor/data-model.md`
- Spec: `kitty-specs/085-material-unit-schema-refactor/spec.md`

**Key Patterns** (from research.md):
- FK Pattern: Follow FinishedUnit→Recipe relationship as template
- Use `lazy="joined"` on child side (MaterialUnit)
- Use `cascade="all, delete-orphan"` on parent side (MaterialProduct)

**Architectural Constraints**:
- Models layer defines schema only (no business logic)
- Changes must not break SQLAlchemy relationship loading
- Unique constraints scoped to parent (not global)

---

## Subtasks & Detailed Guidance

### Subtask T001 – Update MaterialUnit Model FK

**Purpose**: Change the foreign key from Material to MaterialProduct.

**Files**: `src/models/material_unit.py`

**Steps**:
1. Locate the current `material_id` column definition:
   ```python
   material_id = Column(
       Integer,
       ForeignKey("materials.id", ondelete="CASCADE"),
       nullable=False,
       index=True,
   )
   ```

2. Replace with `material_product_id`:
   ```python
   material_product_id = Column(
       Integer,
       ForeignKey("material_products.id", ondelete="CASCADE"),
       nullable=False,
       index=True,
   )
   ```

3. Update the relationship definition:
   ```python
   # OLD:
   material = relationship("Material", back_populates="units")

   # NEW:
   material_product = relationship(
       "MaterialProduct",
       back_populates="material_units",
       lazy="joined",
   )
   ```

4. Update any `__repr__` or `to_dict()` methods that reference `material_id`

**Validation**:
- [ ] Column named `material_product_id` exists
- [ ] ForeignKey references `material_products.id`
- [ ] Relationship named `material_product` with correct back_populates
- [ ] `lazy="joined"` set on relationship

---

### Subtask T002 – Add Unique Constraints

**Purpose**: Enforce slug and name uniqueness scoped to MaterialProduct (not global).

**Files**: `src/models/material_unit.py`

**Steps**:
1. Locate the `__table_args__` tuple in the MaterialUnit class

2. Remove or modify the existing global unique constraint on `slug`:
   ```python
   # OLD (if exists):
   UniqueConstraint("slug", name="uq_material_unit_slug"),
   ```

3. Add compound unique constraints:
   ```python
   __table_args__ = (
       UniqueConstraint(
           "material_product_id", "slug",
           name="uq_material_unit_product_slug"
       ),
       UniqueConstraint(
           "material_product_id", "name",
           name="uq_material_unit_product_name"
       ),
       CheckConstraint(
           "quantity_per_unit > 0",
           name="ck_material_unit_quantity_positive"
       ),
       {"extend_existing": True},
   )
   ```

4. Verify the existing CheckConstraint for quantity_per_unit > 0 is preserved

**Validation**:
- [ ] UniqueConstraint for (material_product_id, slug) exists
- [ ] UniqueConstraint for (material_product_id, name) exists
- [ ] No global unique constraint on slug alone
- [ ] CheckConstraint for quantity_per_unit > 0 preserved

---

### Subtask T003 – Add material_units Relationship to MaterialProduct

**Purpose**: Enable MaterialProduct to access its child MaterialUnits.

**Files**: `src/models/material_product.py`

**Steps**:
1. Add the relationship definition to MaterialProduct class:
   ```python
   material_units = relationship(
       "MaterialUnit",
       back_populates="material_product",
       cascade="all, delete-orphan",
       lazy="select",
   )
   ```

2. Ensure the import for MaterialUnit is NOT added (SQLAlchemy resolves by string)

3. Place the relationship near other relationships (purchases, inventory_items)

**Validation**:
- [ ] `material_units` relationship exists on MaterialProduct
- [ ] `back_populates="material_product"` matches MaterialUnit's relationship name
- [ ] `cascade="all, delete-orphan"` set (child units deleted with product)
- [ ] `lazy="select"` set (don't eagerly load units)

---

### Subtask T004 – Remove units Relationship from Material

**Purpose**: Material should no longer directly own MaterialUnits.

**Files**: `src/models/material.py`

**Steps**:
1. Locate the `units` relationship in Material class:
   ```python
   units = relationship(
       "MaterialUnit",
       back_populates="material",
       lazy="select",
   )
   ```

2. Remove this relationship entirely

3. Verify no other code in the file references `self.units`

4. Check if any imports need cleanup

**Validation**:
- [ ] `units` relationship removed from Material
- [ ] No references to `self.units` in Material class
- [ ] File still imports correctly (no broken references)

---

### Subtask T005 – Update MaterialUnit Model Tests

**Purpose**: Ensure model tests work with new FK structure.

**Files**: `src/tests/test_material_unit.py` (or similar)

**Steps**:
1. Find existing MaterialUnit model tests

2. Update test fixtures to create MaterialProduct instead of Material:
   ```python
   # OLD:
   material = Material(name="Red Ribbon", slug="red-ribbon", ...)
   unit = MaterialUnit(material_id=material.id, name="6-inch", ...)

   # NEW:
   material = Material(name="Red Ribbon", slug="red-ribbon", ...)
   product = MaterialProduct(material_id=material.id, name="25m Spool", slug="25m-spool", ...)
   unit = MaterialUnit(material_product_id=product.id, name="6-inch", ...)
   ```

3. Update any assertions that check `material_id` to check `material_product_id`

4. Add tests for the new unique constraints:
   - Test: Same slug allowed for different products
   - Test: Same slug rejected for same product
   - Test: Same name rejected for same product

5. Run tests to verify all pass:
   ```bash
   ./run-tests.sh src/tests/test_material_unit.py -v
   ```

**Validation**:
- [ ] All existing model tests updated
- [ ] Tests create MaterialProduct as intermediate object
- [ ] Unique constraint tests added
- [ ] All tests pass

---

## Test Strategy

**Required Tests**:
1. Model creation with valid material_product_id
2. Model creation fails with NULL material_product_id
3. Cascade delete: Deleting MaterialProduct deletes its MaterialUnits
4. Unique constraint: Same slug works for different products
5. Unique constraint: Same slug fails for same product
6. Unique constraint: Same name fails for same product

**Test Commands**:
```bash
# Run MaterialUnit model tests
./run-tests.sh src/tests/test_material_unit.py -v

# Run with coverage
./run-tests.sh src/tests/test_material_unit.py -v --cov=src/models
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing service code | Services updated in WP03 (sequence enforced) |
| Circular import issues | Use string-based relationship references |
| Missing cascade behavior | Explicit `cascade="all, delete-orphan"` on parent |
| Constraint name collisions | Use descriptive, unique constraint names |

---

## Definition of Done Checklist

- [ ] MaterialUnit.material_product_id FK implemented with CASCADE delete
- [ ] MaterialUnit.material_id column removed
- [ ] MaterialProduct.material_units relationship added
- [ ] Material.units relationship removed
- [ ] Compound unique constraints added (product_id + slug, product_id + name)
- [ ] All model tests pass
- [ ] No linting errors (`black`, `flake8`)

---

## Review Guidance

**Key Checkpoints**:
1. Verify FK definition matches pattern from data-model.md
2. Verify relationship `back_populates` values match on both sides
3. Verify cascade behavior is correct direction (parent → children)
4. Verify unique constraints are compound (not single-column)
5. Run test suite to confirm no regressions

---

## Activity Log

- 2026-01-30T17:11:03Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-30T17:24:46Z – claude-opus – shell_pid=27103 – lane=doing – Started implementation via workflow command
- 2026-01-30T17:35:09Z – claude-opus – shell_pid=27103 – lane=for_review – Ready for review: MaterialUnit FK changed from Material to MaterialProduct, compound unique constraints added, 19 model tests pass
- 2026-01-30T18:35:22Z – claude-opus – shell_pid=42490 – lane=doing – Started review via workflow command
- 2026-01-30T18:38:46Z – claude-opus – shell_pid=42490 – lane=done – Review passed: MaterialUnit FK correctly changed to MaterialProduct, compound unique constraints implemented, cascade delete-orphan working, 19 model tests pass
