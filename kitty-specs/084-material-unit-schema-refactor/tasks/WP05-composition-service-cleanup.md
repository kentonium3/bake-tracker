---
work_package_id: WP05
title: Composition Service Cleanup
lane: "for_review"
dependencies: [WP02]
base_branch: 084-material-unit-schema-refactor-WP02
base_commit: 96b9a8deef6854c3ee7f4cee16b0c7bc0d577e6d
created_at: '2026-01-30T17:59:19.271836+00:00'
subtasks:
- T023
- T024
- T025
- T026
phase: Wave 2 - Service Layer
assignee: ''
agent: ''
shell_pid: "33841"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-30T17:11:03Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Composition Service Cleanup

## Implementation Command

```bash
spec-kitty implement WP05 --base WP02
```

Depends on WP02 (Composition model cleanup).

---

## Objectives & Success Criteria

**Goal**: Remove material_id support from Composition service layer.

**Success Criteria**:
- [ ] CompositionService no longer accepts material_id parameter
- [ ] create_composition() rejects material_id with clear error
- [ ] get_compositions() does not return material_id in results
- [ ] Any helper methods for material_id removed
- [ ] Service tests pass with >80% coverage

---

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/084-material-unit-schema-refactor/plan.md`
- Spec: `kitty-specs/084-material-unit-schema-refactor/spec.md` (FR-006 to FR-008)

**Key Points**:
- material_unit_id is the ONLY path for material components now
- Existing code may call removed methods - search and update
- Service layer must enforce model constraints

---

## Subtasks & Detailed Guidance

### Subtask T023 – Remove material_id Support from CompositionService

**Purpose**: Eliminate all material_id handling from service layer.

**Files**: `src/services/composition_service.py`

**Steps**:
1. Search for all material_id references:
   ```bash
   grep -n "material_id" src/services/composition_service.py
   ```

2. Remove any functions that create material placeholder compositions:
   ```python
   # REMOVE entirely:
   def create_material_composition(
       assembly_id: int,
       material_id: int,
       quantity: int = 1,
       ...
   ) -> Composition:
       ...
   ```

3. Remove material_id from any generic create functions:
   ```python
   # If a generic create_composition() exists with material_id param:
   def create_composition(
       assembly_id: int,
       component_type: str,
       component_id: int,
       # REMOVE: material_id: Optional[int] = None,
       ...
   ):
   ```

4. Update any docstrings that mention material_id as a valid option

5. Update any imports that reference Material model (if no longer needed)

**Validation**:
- [ ] No material_id parameters in any function signature
- [ ] No material_id handling in any function body
- [ ] Docstrings updated to only mention 4 component types

---

### Subtask T024 – Update create_composition() to Reject material_id

**Purpose**: Explicitly reject material_id if passed (defensive programming).

**Files**: `src/services/composition_service.py`

**Steps**:
1. If using kwargs pattern, add explicit rejection:
   ```python
   def create_composition(
       assembly_id: int,
       finished_unit_id: Optional[int] = None,
       finished_good_id: Optional[int] = None,
       packaging_product_id: Optional[int] = None,
       material_unit_id: Optional[int] = None,
       quantity: int = 1,
       notes: Optional[str] = None,
       session: Optional[Session] = None,
       **kwargs,  # Catch unexpected params
   ) -> Composition:
       # Reject material_id if someone passes it
       if "material_id" in kwargs:
           raise ValidationError(
               ["material_id is no longer supported. Use material_unit_id instead."]
           )
       ...
   ```

2. Alternative: Remove kwargs and use explicit params only (cleaner):
   ```python
   def create_composition(
       assembly_id: int,
       finished_unit_id: Optional[int] = None,
       finished_good_id: Optional[int] = None,
       packaging_product_id: Optional[int] = None,
       material_unit_id: Optional[int] = None,
       quantity: int = 1,
       notes: Optional[str] = None,
       sort_order: int = 0,
       session: Optional[Session] = None,
   ) -> Composition:
       # No material_id param = can't pass it
       ...
   ```

3. Update the XOR validation to only check 4 types:
   ```python
   def _validate_composition_type(
       finished_unit_id, finished_good_id, packaging_product_id, material_unit_id
   ) -> None:
       """Validate exactly one component type is set."""
       component_ids = [
           finished_unit_id,
           finished_good_id,
           packaging_product_id,
           material_unit_id,
       ]
       set_count = sum(1 for cid in component_ids if cid is not None)
       if set_count != 1:
           raise ValidationError(
               ["Exactly one of finished_unit_id, finished_good_id, "
                "packaging_product_id, or material_unit_id must be set"]
           )
   ```

**Validation**:
- [ ] material_id cannot be passed to create_composition()
- [ ] Clear error message if attempted
- [ ] XOR validation only checks 4 types

---

### Subtask T025 – Update get_compositions() to Not Return material_id

**Purpose**: Ensure queries and return values don't reference material_id.

**Files**: `src/services/composition_service.py`

**Steps**:
1. Update any query filters that might reference material_id:
   ```python
   # REMOVE any filters like:
   # .filter(Composition.material_id == some_id)
   ```

2. Update any serialization/to_dict methods:
   ```python
   def get_composition_details(composition: Composition) -> dict:
       return {
           "id": composition.id,
           "assembly_id": composition.assembly_id,
           "component_type": composition.component_type,
           "component_id": composition.component_id,
           "component_name": composition.component_name,
           # REMOVE: "material_id": composition.material_id,
           "quantity": composition.quantity,
           "notes": composition.notes,
       }
   ```

3. Update any functions that group/filter by component type:
   ```python
   def get_compositions_by_type(assembly_id: int, component_type: str, ...):
       valid_types = ["finished_unit", "finished_good", "packaging_product", "material_unit"]
       # REMOVE: "material" from valid_types
       if component_type not in valid_types:
           raise ValidationError([f"Invalid component type: {component_type}"])
   ```

**Validation**:
- [ ] No queries filter by material_id
- [ ] Serialization does not include material_id
- [ ] Component type validation only accepts 4 types

---

### Subtask T026 – Update Composition Service Tests

**Purpose**: Update tests for 4-way composition support.

**Files**: `src/tests/test_composition_service.py`

**Steps**:
1. Remove tests for material_id compositions:
   ```python
   # REMOVE tests like:
   def test_create_material_composition():
       ...

   def test_get_compositions_by_material():
       ...
   ```

2. Update XOR validation tests:
   ```python
   def test_create_composition_requires_exactly_one_component():
       """Must specify exactly one of 4 component types."""
       with pytest.raises(ValidationError) as exc:
           create_composition(assembly_id=1, session=session)
       assert "Exactly one" in str(exc.value)

   def test_create_composition_rejects_multiple_components():
       """Cannot specify multiple component types."""
       with pytest.raises(ValidationError):
           create_composition(
               assembly_id=1,
               finished_unit_id=1,
               material_unit_id=1,  # Two components
               session=session,
           )
   ```

3. Add test for material_id rejection (if keeping defensive check):
   ```python
   def test_create_composition_rejects_material_id():
       """material_id parameter should be rejected."""
       with pytest.raises(ValidationError) as exc:
           create_composition(
               assembly_id=1,
               material_id=1,  # Old parameter
               session=session,
           )
       assert "no longer supported" in str(exc.value)
   ```

4. Verify tests for valid component types still work:
   ```python
   def test_create_composition_with_material_unit():
       """Can create composition with material_unit_id."""
       comp = create_composition(
           assembly_id=assembly.id,
           material_unit_id=unit.id,
           quantity=2,
           session=session,
       )
       assert comp.material_unit_id == unit.id
       assert comp.component_type == "material_unit"
   ```

5. Run tests:
   ```bash
   ./run-tests.sh src/tests/test_composition_service.py -v --cov=src/services/composition_service
   ```

**Validation**:
- [ ] No tests reference material_id as valid parameter
- [ ] XOR tests updated for 4 types
- [ ] material_unit_id tests still work
- [ ] All tests pass
- [ ] Coverage >80%

---

## Test Strategy

**Required Tests**:
1. create_composition() with each of 4 valid types
2. create_composition() with zero types fails
3. create_composition() with two types fails
4. create_composition() with material_id fails (if defensive check)
5. get_compositions() returns correct component types

**Test Commands**:
```bash
./run-tests.sh src/tests/test_composition_service.py -v --cov=src/services/composition_service
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Callers still passing material_id | Defensive rejection with clear error |
| Missing test updates | Search tests for "material_id" references |
| Breaking UI code | UI updated in WP07-WP08 |

---

## Definition of Done Checklist

- [ ] No material_id parameters in service functions
- [ ] create_composition() rejects material_id with clear error
- [ ] XOR validation only checks 4 types
- [ ] get_compositions() does not return material_id
- [ ] Service tests pass with >80% coverage
- [ ] No linting errors

---

## Review Guidance

**Key Checkpoints**:
1. Search for any remaining material_id references
2. Verify XOR validation only allows 4 types
3. Verify error messages are user-friendly
4. Run test suite to confirm >80% coverage

---

## Activity Log

- 2026-01-30T17:11:03Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-30T18:02:01Z – unknown – shell_pid=33841 – lane=for_review – Removed material_id support from composition service. All 35 composition tests pass.
