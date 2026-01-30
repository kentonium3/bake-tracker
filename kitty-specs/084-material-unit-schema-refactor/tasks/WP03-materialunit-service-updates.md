---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "MaterialUnit Service Updates"
phase: "Wave 2 - Service Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01", "WP02"]
history:
  - timestamp: "2026-01-30T17:11:03Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – MaterialUnit Service Updates

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

Depends on WP01 and WP02 (schema changes must be complete).

---

## Objectives & Success Criteria

**Goal**: Update MaterialUnit service to use new material_product_id FK with validation.

**Success Criteria**:
- [ ] All CRUD operations use material_product_id (not material_id)
- [ ] Name uniqueness validation enforced per product
- [ ] Slug generation scoped to product (same slug allowed for different products)
- [ ] Deletion prevented if MaterialUnit is referenced by Composition
- [ ] Service tests achieve >80% coverage
- [ ] All tests pass

---

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/084-material-unit-schema-refactor/plan.md`
- Research: `kitty-specs/084-material-unit-schema-refactor/research.md`
- Data Model: `kitty-specs/084-material-unit-schema-refactor/data-model.md`

**Key Patterns** (from research.md):
```python
# Slug generation (hyphen style from recipe_service)
def _generate_material_unit_slug(name: str) -> str:
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    slug = slug.lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug or "unknown-unit"

# Unique slug within product scope
def _generate_unique_slug(name: str, session: Session, material_product_id: int) -> str:
    base_slug = _generate_material_unit_slug(name)
    for attempt in range(1000):
        candidate = base_slug if attempt == 0 else f"{base_slug}-{attempt + 1}"
        existing = session.query(MaterialUnit).filter(
            MaterialUnit.material_product_id == material_product_id,
            MaterialUnit.slug == candidate
        ).first()
        if not existing:
            return candidate
    raise ValidationError(f"Unable to generate unique slug for '{name}'")
```

**Session Management Pattern**:
- Functions must accept optional `session` parameter
- If session provided, use it directly (caller manages transaction)
- If None, create new session_scope

---

## Subtasks & Detailed Guidance

### Subtask T013 – Update CRUD to Use material_product_id

**Purpose**: Change all service operations from material_id to material_product_id.

**Files**: `src/services/material_unit_service.py`

**Steps**:
1. Update `create_material_unit()`:
   ```python
   def create_material_unit(
       material_product_id: int,  # Changed from material_id
       name: str,
       quantity_per_unit: float,
       slug: Optional[str] = None,
       description: Optional[str] = None,
       session: Optional[Session] = None,
   ) -> MaterialUnit:
   ```

2. Update the model creation:
   ```python
   unit = MaterialUnit(
       material_product_id=material_product_id,  # Changed
       name=name.strip(),
       slug=generated_slug,
       quantity_per_unit=quantity_per_unit,
       description=description,
   )
   ```

3. Update `get_material_unit()`, `update_material_unit()`, `delete_material_unit()` if they filter by material_id

4. Update any `get_material_units_by_material()` to `get_material_units_by_product()`:
   ```python
   def get_material_units_by_product(
       material_product_id: int,
       session: Optional[Session] = None,
   ) -> List[MaterialUnit]:
       def _impl(sess: Session) -> List[MaterialUnit]:
           return sess.query(MaterialUnit).filter(
               MaterialUnit.material_product_id == material_product_id
           ).all()
       ...
   ```

5. Update any query joins to use `material_product` relationship instead of `material`

**Validation**:
- [ ] create_material_unit() accepts material_product_id parameter
- [ ] No references to material_id in service code
- [ ] Query joins use material_product relationship

---

### Subtask T014 – Add Name Uniqueness Validation

**Purpose**: Prevent duplicate MaterialUnit names within the same MaterialProduct.

**Files**: `src/services/material_unit_service.py`

**Steps**:
1. Add validation in `create_material_unit()`:
   ```python
   def create_material_unit(...):
       def _impl(sess: Session) -> MaterialUnit:
           # Check for duplicate name within product
           existing = sess.query(MaterialUnit).filter(
               MaterialUnit.material_product_id == material_product_id,
               MaterialUnit.name == name.strip()
           ).first()
           if existing:
               raise ValidationError(
                   [f"MaterialUnit with name '{name}' already exists for this product"]
               )
           ...
   ```

2. Add validation in `update_material_unit()`:
   ```python
   def update_material_unit(unit_id: int, name: Optional[str] = None, ...):
       def _impl(sess: Session) -> MaterialUnit:
           unit = sess.query(MaterialUnit).get(unit_id)
           if not unit:
               raise NotFoundError(f"MaterialUnit {unit_id} not found")

           if name and name.strip() != unit.name:
               # Check for duplicate name within same product
               existing = sess.query(MaterialUnit).filter(
                   MaterialUnit.material_product_id == unit.material_product_id,
                   MaterialUnit.name == name.strip(),
                   MaterialUnit.id != unit_id
               ).first()
               if existing:
                   raise ValidationError(
                       [f"MaterialUnit with name '{name}' already exists for this product"]
                   )
               unit.name = name.strip()
           ...
   ```

**Validation**:
- [ ] Create rejects duplicate names within same product
- [ ] Update rejects duplicate names within same product
- [ ] Same name allowed for different products

---

### Subtask T015 – Add Slug Generation Scoped to Product

**Purpose**: Generate unique slugs within product scope (same slug allowed for different products).

**Files**: `src/services/material_unit_service.py`

**Steps**:
1. Add slug generation helper (if not exists):
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
       return slug if slug else "unknown-unit"
   ```

2. Add unique slug generator scoped to product:
   ```python
   def _generate_unique_slug(
       name: str,
       session: Session,
       material_product_id: int,
       exclude_id: Optional[int] = None,
   ) -> str:
       """Generate unique slug within product scope."""
       base_slug = _generate_material_unit_slug(name)
       max_attempts = 1000

       for attempt in range(max_attempts):
           candidate = base_slug if attempt == 0 else f"{base_slug}-{attempt + 1}"
           query = session.query(MaterialUnit).filter(
               MaterialUnit.material_product_id == material_product_id,
               MaterialUnit.slug == candidate
           )
           if exclude_id:
               query = query.filter(MaterialUnit.id != exclude_id)

           if not query.first():
               return candidate

       raise ValidationError(
           [f"Unable to generate unique slug for '{name}' after {max_attempts} attempts"]
       )
   ```

3. Update create_material_unit() to use product-scoped slug:
   ```python
   if not slug:
       slug = _generate_unique_slug(name, sess, material_product_id)
   else:
       # Validate provided slug is unique within product
       existing = sess.query(MaterialUnit).filter(
           MaterialUnit.material_product_id == material_product_id,
           MaterialUnit.slug == slug
       ).first()
       if existing:
           raise ValidationError([f"Slug '{slug}' already exists for this product"])
   ```

4. Update update_material_unit() for slug changes

**Validation**:
- [ ] Slug auto-generated from name if not provided
- [ ] Slug uniqueness checked within product scope
- [ ] Same slug allowed for different products
- [ ] Collision handled with numeric suffix (-2, -3)

---

### Subtask T016 – Add Deletion Validation

**Purpose**: Prevent deletion of MaterialUnits that are referenced by Compositions.

**Files**: `src/services/material_unit_service.py`

**Steps**:
1. Update `delete_material_unit()`:
   ```python
   from src.models.composition import Composition

   def delete_material_unit(
       unit_id: int,
       session: Optional[Session] = None,
   ) -> bool:
       def _impl(sess: Session) -> bool:
           unit = sess.query(MaterialUnit).get(unit_id)
           if not unit:
               raise NotFoundError(f"MaterialUnit {unit_id} not found")

           # Check if referenced by any Composition
           references = sess.query(Composition).filter(
               Composition.material_unit_id == unit_id
           ).all()

           if references:
               # Build list of FinishedGoods that reference this unit
               fg_names = []
               for comp in references:
                   if comp.assembly and comp.assembly.finished_good:
                       fg_names.append(comp.assembly.finished_good.name)
                   else:
                       fg_names.append(f"Assembly #{comp.assembly_id}")

               raise ValidationError(
                   [f"Cannot delete MaterialUnit '{unit.name}': referenced by "
                    f"{len(references)} composition(s) in: {', '.join(set(fg_names))}"]
               )

           sess.delete(unit)
           return True

       if session is not None:
           return _impl(session)
       with session_scope() as sess:
           return _impl(sess)
   ```

**Validation**:
- [ ] Deletion fails if unit is referenced by Composition
- [ ] Error message lists affected FinishedGoods
- [ ] Deletion succeeds if unit is not referenced

---

### Subtask T017 – Update MaterialUnit Service Tests

**Purpose**: Ensure service tests work with new FK and validation logic.

**Files**: `src/tests/test_material_unit_service.py`

**Steps**:
1. Update test fixtures to create MaterialProduct:
   ```python
   @pytest.fixture
   def material_product(session, material):
       """Create a MaterialProduct for testing."""
       product = MaterialProduct(
           material_id=material.id,
           name="Test Product",
           slug="test-product",
           package_count=100,
       )
       session.add(product)
       session.flush()
       return product

   @pytest.fixture
   def material_unit(session, material_product):
       """Create a MaterialUnit for testing."""
       unit = MaterialUnit(
           material_product_id=material_product.id,
           name="Test Unit",
           slug="test-unit",
           quantity_per_unit=1.0,
       )
       session.add(unit)
       session.flush()
       return unit
   ```

2. Add tests for name uniqueness:
   ```python
   def test_create_material_unit_rejects_duplicate_name(session, material_product):
       create_material_unit(material_product.id, "Test Unit", 1.0, session=session)
       with pytest.raises(ValidationError) as exc:
           create_material_unit(material_product.id, "Test Unit", 1.0, session=session)
       assert "already exists" in str(exc.value)

   def test_create_material_unit_allows_same_name_different_product(
       session, material_product, material_product_2
   ):
       create_material_unit(material_product.id, "Test Unit", 1.0, session=session)
       # Should not raise
       create_material_unit(material_product_2.id, "Test Unit", 1.0, session=session)
   ```

3. Add tests for slug generation:
   ```python
   def test_slug_generated_from_name(session, material_product):
       unit = create_material_unit(material_product.id, "6-inch Ribbon", 0.15, session=session)
       assert unit.slug == "6-inch-ribbon"

   def test_slug_collision_adds_suffix(session, material_product):
       create_material_unit(material_product.id, "Test", 1.0, slug="test", session=session)
       unit2 = create_material_unit(material_product.id, "Test 2", 1.0, session=session)
       # First attempt would be "test-2", but "test" already taken, so might be "test-2-2"
       assert unit2.slug.startswith("test")
   ```

4. Add tests for deletion validation:
   ```python
   def test_delete_fails_if_referenced_by_composition(session, material_unit, composition):
       composition.material_unit_id = material_unit.id
       session.flush()
       with pytest.raises(ValidationError) as exc:
           delete_material_unit(material_unit.id, session=session)
       assert "referenced by" in str(exc.value)

   def test_delete_succeeds_if_not_referenced(session, material_unit):
       result = delete_material_unit(material_unit.id, session=session)
       assert result is True
   ```

5. Run tests:
   ```bash
   ./run-tests.sh src/tests/test_material_unit_service.py -v --cov=src/services/material_unit_service
   ```

**Validation**:
- [ ] All tests use material_product_id (not material_id)
- [ ] Name uniqueness tests added
- [ ] Slug generation tests added
- [ ] Deletion validation tests added
- [ ] Coverage >80%

---

## Test Strategy

**Required Tests**:
1. CRUD operations with material_product_id
2. Name uniqueness: reject duplicate within product
3. Name uniqueness: allow duplicate across products
4. Slug generation: auto-generate from name
5. Slug generation: collision handling with suffix
6. Deletion: fails if referenced by Composition
7. Deletion: succeeds if not referenced

**Test Commands**:
```bash
./run-tests.sh src/tests/test_material_unit_service.py -v --cov=src/services/material_unit_service
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking callers that pass material_id | Clear parameter rename; compiler errors will surface |
| Slug collision infinite loop | Max attempts limit (1000) with clear error |
| Deletion blocking on unexpected references | Include FinishedGood names in error for debugging |

---

## Definition of Done Checklist

- [ ] All CRUD operations use material_product_id
- [ ] Name uniqueness validation implemented
- [ ] Slug generation scoped to product
- [ ] Deletion validation prevents orphaning Compositions
- [ ] Service tests pass with >80% coverage
- [ ] No linting errors

---

## Review Guidance

**Key Checkpoints**:
1. Verify no remaining material_id references in service
2. Verify validation error messages are user-friendly
3. Verify slug generation follows hyphen pattern (not underscore)
4. Verify session management pattern followed (optional session param)
5. Run test suite to confirm >80% coverage

---

## Activity Log

- 2026-01-30T17:11:03Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
