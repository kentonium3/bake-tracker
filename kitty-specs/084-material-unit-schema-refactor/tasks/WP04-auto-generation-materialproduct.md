---
work_package_id: "WP04"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
title: "Auto-Generation in MaterialProduct Service"
phase: "Wave 2 - Service Layer"
lane: "doing"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01", "WP03"]
history:
  - timestamp: "2026-01-30T17:11:03Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Auto-Generation in MaterialProduct Service

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

Depends on WP01 (MaterialUnit FK) and WP03 (MaterialUnit service must work).

---

## Objectives & Success Criteria

**Goal**: Auto-generate MaterialUnit when creating MaterialProduct with package_count.

**Success Criteria**:
- [ ] Creating MaterialProduct with package_count auto-creates "1 {name}" MaterialUnit
- [ ] Creating MaterialProduct with package_length_m does NOT auto-create unit
- [ ] Creating MaterialProduct with package_sq_m does NOT auto-create unit
- [ ] Auto-generated unit has quantity_per_unit=1.0
- [ ] Auto-generation completes in <500ms
- [ ] Service tests achieve >80% coverage

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/084-material-unit-schema-refactor/spec.md` (FR-003)
- Plan: `kitty-specs/084-material-unit-schema-refactor/plan.md`
- Data Model: `kitty-specs/084-material-unit-schema-refactor/data-model.md`

**Auto-Generation Rules** (from data-model.md):
| Condition | Action |
|-----------|--------|
| `package_count IS NOT NULL` AND `package_length_m IS NULL` AND `package_sq_m IS NULL` | Auto-create "1 {product.name}" MaterialUnit |
| Any other combination | No auto-generation |

**Session Management** (CRITICAL):
- Auto-generation must use the SAME session as product creation
- This ensures atomic transaction (product + unit committed together)
- Follow the pattern from CLAUDE.md Session Management section

---

## Subtasks & Detailed Guidance

### Subtask T018 – Add Auto-Generation Logic to create_material_product()

**Purpose**: Trigger MaterialUnit auto-creation when appropriate product type is created.

**Files**: `src/services/material_product_service.py`

**Steps**:
1. Locate `create_material_product()` function

2. Add auto-generation call after product is flushed:
   ```python
   def create_material_product(
       material_id: int,
       name: str,
       slug: Optional[str] = None,
       package_count: Optional[int] = None,
       package_length_m: Optional[float] = None,
       package_sq_m: Optional[float] = None,
       # ... other params
       session: Optional[Session] = None,
   ) -> MaterialProduct:
       def _impl(sess: Session) -> MaterialProduct:
           # ... existing validation and creation code ...

           product = MaterialProduct(
               material_id=material_id,
               name=name.strip(),
               slug=generated_slug,
               package_count=package_count,
               package_length_m=package_length_m,
               package_sq_m=package_sq_m,
               # ... other fields
           )
           sess.add(product)
           sess.flush()  # Get product.id
           sess.refresh(product)

           # Auto-generate MaterialUnit for "each" type products
           if _should_auto_generate_unit(product):
               _create_auto_generated_unit(product, sess)

           return product

       if session is not None:
           return _impl(session)
       with session_scope() as sess:
           return _impl(sess)
   ```

3. Ensure the session is passed to the auto-generation function (atomic transaction)

**Validation**:
- [ ] Auto-generation called after product flush
- [ ] Session passed to auto-generation function
- [ ] Product returned after auto-generation completes

---

### Subtask T019 – Implement _should_auto_generate_unit() Helper

**Purpose**: Determine if a product should have an auto-generated MaterialUnit.

**Files**: `src/services/material_product_service.py`

**Steps**:
1. Add the helper function:
   ```python
   def _should_auto_generate_unit(product: MaterialProduct) -> bool:
       """
       Determine if product should have auto-generated MaterialUnit.

       Auto-generate only when:
       - package_count IS NOT NULL (discrete items like bags, boxes)
       - package_length_m IS NULL (not linear material like ribbon)
       - package_sq_m IS NULL (not area material like fabric)

       Args:
           product: The MaterialProduct to check

       Returns:
           True if auto-generation should occur, False otherwise
       """
       return (
           product.package_count is not None
           and product.package_length_m is None
           and product.package_sq_m is None
       )
   ```

2. Add docstring explaining the business logic

**Validation**:
- [ ] Returns True for package_count=100, no length/area
- [ ] Returns False for package_length_m=25.0
- [ ] Returns False for package_sq_m=1.0
- [ ] Returns False for package_count=None

---

### Subtask T020 – Implement _create_auto_generated_unit() Helper

**Purpose**: Create the auto-generated MaterialUnit for a product.

**Files**: `src/services/material_product_service.py`

**Steps**:
1. Add the helper function:
   ```python
   from src.models.material_unit import MaterialUnit

   def _create_auto_generated_unit(
       product: MaterialProduct,
       session: Session,
   ) -> MaterialUnit:
       """
       Create auto-generated MaterialUnit for a product.

       Creates a unit named "1 {product.name}" with quantity_per_unit=1.0.
       Used for discrete/each-type products where one unit = one item.

       Args:
           product: The MaterialProduct to create unit for
           session: Database session (must be same as product creation)

       Returns:
           The created MaterialUnit
       """
       unit_name = f"1 {product.name}"
       unit_slug = _generate_material_unit_slug(unit_name)

       # Check for slug collision within product (shouldn't happen on new product)
       unique_slug = _generate_unique_material_unit_slug(
           unit_name, session, product.id
       )

       unit = MaterialUnit(
           material_product_id=product.id,
           name=unit_name,
           slug=unique_slug,
           quantity_per_unit=1.0,
           description=f"Auto-generated unit for {product.name}",
       )
       session.add(unit)
       session.flush()

       return unit
   ```

2. Note: Uses same session as product creation for atomicity

**Validation**:
- [ ] Unit name format: "1 {product.name}"
- [ ] quantity_per_unit = 1.0
- [ ] Uses product.id for material_product_id
- [ ] Unit flushed to same session

---

### Subtask T021 – Add Slug Generation for Auto-Generated Units

**Purpose**: Generate unique slugs for auto-generated MaterialUnits.

**Files**: `src/services/material_product_service.py`

**Steps**:
1. Add slug generation helpers (or import from material_unit_service if available):
   ```python
   import unicodedata
   import re

   def _generate_material_unit_slug(name: str) -> str:
       """Generate URL-safe slug from name."""
       if not name:
           return "unknown-unit"
       slug = unicodedata.normalize("NFKD", name)
       slug = slug.encode("ascii", "ignore").decode("ascii")
       slug = slug.lower()
       slug = re.sub(r"[\s_]+", "-", slug)
       slug = re.sub(r"[^a-z0-9-]", "", slug)
       slug = re.sub(r"-+", "-", slug)
       slug = slug.strip("-")
       if len(slug) > 200:
           slug = slug[:200].rstrip("-")
       return slug if slug else "unknown-unit"

   def _generate_unique_material_unit_slug(
       name: str,
       session: Session,
       material_product_id: int,
   ) -> str:
       """Generate unique slug within product scope."""
       base_slug = _generate_material_unit_slug(name)

       for attempt in range(1000):
           candidate = base_slug if attempt == 0 else f"{base_slug}-{attempt + 1}"
           existing = session.query(MaterialUnit).filter(
               MaterialUnit.material_product_id == material_product_id,
               MaterialUnit.slug == candidate
           ).first()
           if not existing:
               return candidate

       raise ValidationError(
           [f"Unable to generate unique slug for '{name}'"]
       )
   ```

2. Alternative: Import from material_unit_service if those functions are already public:
   ```python
   from src.services.material_unit_service import (
       _generate_material_unit_slug,
       _generate_unique_slug,
   )
   ```

**Note**: Consider whether to centralize slug generation in a shared module.

**Validation**:
- [ ] Slug generated from "1 {product.name}"
- [ ] Unicode normalized (e.g., "Café" → "cafe")
- [ ] Spaces replaced with hyphens
- [ ] Collision handled with numeric suffix

---

### Subtask T022 – Add MaterialProduct Service Tests for Auto-Generation

**Purpose**: Test auto-generation behavior for different product types.

**Files**: `src/tests/test_material_product_service.py`

**Steps**:
1. Add test for package_count product:
   ```python
   def test_create_product_with_package_count_auto_generates_unit(session, material):
       """Creating product with package_count should auto-generate MaterialUnit."""
       product = create_material_product(
           material_id=material.id,
           name="Clear Bags 100pk",
           package_count=100,
           session=session,
       )

       # Verify unit was created
       assert len(product.material_units) == 1
       unit = product.material_units[0]
       assert unit.name == "1 Clear Bags 100pk"
       assert unit.quantity_per_unit == 1.0
       assert unit.material_product_id == product.id
   ```

2. Add test for linear product (no auto-generation):
   ```python
   def test_create_product_with_length_no_auto_generation(session, material):
       """Creating product with package_length_m should NOT auto-generate unit."""
       product = create_material_product(
           material_id=material.id,
           name="Red Ribbon 25m",
           package_length_m=25.0,
           session=session,
       )

       # Verify no unit was created
       assert len(product.material_units) == 0
   ```

3. Add test for area product (no auto-generation):
   ```python
   def test_create_product_with_area_no_auto_generation(session, material):
       """Creating product with package_sq_m should NOT auto-generate unit."""
       product = create_material_product(
           material_id=material.id,
           name="Fabric 1sqm",
           package_sq_m=1.0,
           session=session,
       )

       # Verify no unit was created
       assert len(product.material_units) == 0
   ```

4. Add test for mixed fields (no auto-generation):
   ```python
   def test_create_product_with_count_and_length_no_auto_generation(session, material):
       """Product with both package_count and package_length_m should NOT auto-generate."""
       # Note: This might be invalid per schema, but test the logic anyway
       product = create_material_product(
           material_id=material.id,
           name="Mixed Product",
           package_count=10,
           package_length_m=5.0,
           session=session,
       )

       # Should not auto-generate because length is present
       assert len(product.material_units) == 0
   ```

5. Add test for slug generation:
   ```python
   def test_auto_generated_unit_has_correct_slug(session, material):
       """Auto-generated unit should have slug derived from name."""
       product = create_material_product(
           material_id=material.id,
           name="Gift Boxes (Large)",
           package_count=50,
           session=session,
       )

       unit = product.material_units[0]
       assert unit.slug == "1-gift-boxes-large"
   ```

6. Add performance test (optional):
   ```python
   import time

   def test_auto_generation_performance(session, material):
       """Auto-generation should complete in <500ms."""
       start = time.time()
       product = create_material_product(
           material_id=material.id,
           name="Performance Test Product",
           package_count=100,
           session=session,
       )
       elapsed = time.time() - start

       assert elapsed < 0.5, f"Auto-generation took {elapsed:.2f}s, expected <0.5s"
       assert len(product.material_units) == 1
   ```

7. Run tests:
   ```bash
   ./run-tests.sh src/tests/test_material_product_service.py -v --cov=src/services/material_product_service
   ```

**Validation**:
- [ ] Test for package_count product (auto-generates)
- [ ] Test for package_length_m product (no auto-generation)
- [ ] Test for package_sq_m product (no auto-generation)
- [ ] Test for slug generation
- [ ] All tests pass
- [ ] Coverage >80%

---

## Test Strategy

**Required Tests**:
1. Package_count product → auto-generates "1 {name}" unit
2. Package_length_m product → no auto-generation
3. Package_sq_m product → no auto-generation
4. Auto-generated unit has correct name, slug, quantity
5. Auto-generation uses same transaction (atomic)

**Test Commands**:
```bash
./run-tests.sh src/tests/test_material_product_service.py -v --cov=src/services/material_product_service
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Auto-generation in wrong transaction | Pass session explicitly; single session_scope |
| Auto-creates unwanted units | Allow deletion in WP03 (if not referenced) |
| Name/slug collision | Use unique generators with collision handling |
| Performance regression | Test ensures <500ms; simple single query |

---

## Definition of Done Checklist

- [ ] _should_auto_generate_unit() implemented
- [ ] _create_auto_generated_unit() implemented
- [ ] create_material_product() calls auto-generation
- [ ] Slug generation for auto-generated units works
- [ ] Service tests pass with >80% coverage
- [ ] Auto-generation completes in <500ms
- [ ] No linting errors

---

## Review Guidance

**Key Checkpoints**:
1. Verify auto-generation uses same session (atomic)
2. Verify condition logic matches data-model.md rules
3. Verify unit name format is "1 {product.name}"
4. Verify quantity_per_unit is always 1.0
5. Run test suite to confirm >80% coverage

---

## Activity Log

- 2026-01-30T17:11:03Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-30T17:52:03Z – unknown – lane=doing – Starting auto-generation implementation
