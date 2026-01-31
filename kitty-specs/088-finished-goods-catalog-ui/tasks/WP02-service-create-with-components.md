---
work_package_id: "WP02"
title: "Service Layer - Create with Components"
lane: "for_review"
dependencies: []
subtasks: ["T008", "T009", "T010", "T011", "T012", "T013"]
priority: "P0"
estimated_lines: 400
agent: "gemini-wp02"
shell_pid: "21725"
history:
  - date: "2026-01-30"
    action: "created"
    agent: "claude"
---

# WP02: Service Layer - Create with Components

## Objective

Enhance the service layer to create FinishedGoods with atomic component creation. The enhanced `create_finished_good()` function accepts a `components` list parameter and creates all Composition records within a single transaction.

## Context

- **Feature**: 088-finished-goods-catalog-ui
- **Priority**: P0 (service layer foundation)
- **Dependencies**: None (independent of UI)
- **Estimated Size**: ~400 lines

### Reference Files

- `src/services/finished_good_service.py` - Service to enhance
- `src/models/composition.py` - Composition factory methods
- `src/models/finished_good.py` - FinishedGood model
- `src/utils/session_scope.py` - Session management pattern

### Component Data Structure

```python
components = [
    {"type": "finished_unit", "id": 1, "quantity": 2, "notes": None, "sort_order": 0},
    {"type": "material_unit", "id": 3, "quantity": 1, "notes": "Gift wrap", "sort_order": 1},
    {"type": "finished_good", "id": 5, "quantity": 1, "notes": None, "sort_order": 2},
]
```

### Composition Factory Methods

```python
Composition.create_unit_composition(assembly_id, finished_unit_id, quantity, notes=None, sort_order=0)
Composition.create_assembly_composition(assembly_id, finished_good_id, quantity, notes=None, sort_order=0)
Composition.create_material_unit_composition(assembly_id, material_unit_id, quantity, notes=None, sort_order=0)
```

## Implementation Command

```bash
spec-kitty implement WP02
```

---

## Subtasks

### T008: Enhance `create_finished_good()` to accept `components` list parameter

**Purpose**: Extend the service function signature to accept component data.

**Steps**:
1. Open `src/services/finished_good_service.py`
2. Find `create_finished_good()` function
3. Add `components` parameter with default None:
   ```python
   def create_finished_good(
       display_name: str,
       assembly_type: AssemblyType = AssemblyType.CUSTOM_ORDER,
       components: Optional[List[Dict]] = None,
       session=None,
       **kwargs
   ) -> FinishedGood:
   ```
4. Follow session management pattern:
   ```python
   if session is not None:
       return _create_finished_good_impl(display_name, assembly_type, components, session, **kwargs)
   with session_scope() as session:
       return _create_finished_good_impl(display_name, assembly_type, components, session, **kwargs)
   ```
5. Create `_create_finished_good_impl()` internal function

**Files**:
- `src/services/finished_good_service.py` (~30 lines modified)

**Validation**:
- [ ] Function signature updated
- [ ] Existing calls still work (components=None default)
- [ ] Session management pattern followed

---

### T009: Implement atomic component creation using Composition factory methods [P]

**Purpose**: Create all Composition records within the same transaction.

**Steps**:
1. In `_create_finished_good_impl()`, after creating the FinishedGood:
   ```python
   # Create the FinishedGood
   finished_good = FinishedGood(
       display_name=display_name,
       slug=generate_slug(display_name),
       assembly_type=assembly_type,
       **kwargs
   )
   session.add(finished_good)
   session.flush()  # Get ID for compositions
   ```
2. Create components if provided:
   ```python
   if components:
       for comp_data in components:
           composition = _create_composition(finished_good.id, comp_data, session)
           session.add(composition)
   ```
3. Implement `_create_composition()` helper:
   ```python
   def _create_composition(assembly_id: int, comp_data: dict, session) -> Composition:
       comp_type = comp_data["type"]
       comp_id = comp_data["id"]
       quantity = comp_data.get("quantity", 1)
       notes = comp_data.get("notes")
       sort_order = comp_data.get("sort_order", 0)

       if comp_type == "finished_unit":
           return Composition.create_unit_composition(
               assembly_id=assembly_id,
               finished_unit_id=comp_id,
               quantity=quantity,
               notes=notes,
               sort_order=sort_order
           )
       elif comp_type == "material_unit":
           return Composition.create_material_unit_composition(
               assembly_id=assembly_id,
               material_unit_id=comp_id,
               quantity=quantity,
               notes=notes,
               sort_order=sort_order
           )
       elif comp_type == "finished_good":
           return Composition.create_assembly_composition(
               assembly_id=assembly_id,
               finished_good_id=comp_id,
               quantity=quantity,
               notes=notes,
               sort_order=sort_order
           )
       else:
           raise ValueError(f"Unknown component type: {comp_type}")
   ```

**Files**:
- `src/services/finished_good_service.py` (~50 lines added)

**Validation**:
- [ ] Components created in same transaction
- [ ] All three component types work
- [ ] Factory methods used correctly
- [ ] sort_order preserved

---

### T010: Add input validation for component data structure [P]

**Purpose**: Validate component data before attempting database operations.

**Steps**:
1. Create `_validate_components()` function:
   ```python
   def _validate_components(components: List[Dict], session) -> None:
       """Validate component data structure and references."""
       if not components:
           return

       valid_types = {"finished_unit", "material_unit", "finished_good"}

       for i, comp in enumerate(components):
           # Check required fields
           if "type" not in comp:
               raise ValueError(f"Component {i}: missing 'type' field")
           if "id" not in comp:
               raise ValueError(f"Component {i}: missing 'id' field")

           comp_type = comp["type"]
           if comp_type not in valid_types:
               raise ValueError(f"Component {i}: invalid type '{comp_type}'")

           # Validate quantity if present
           quantity = comp.get("quantity", 1)
           if quantity <= 0:
               raise ValueError(f"Component {i}: quantity must be positive")

           # Validate reference exists
           _validate_component_reference(comp_type, comp["id"], session, i)
   ```
2. Implement reference validation:
   ```python
   def _validate_component_reference(comp_type: str, comp_id: int, session, index: int) -> None:
       if comp_type == "finished_unit":
           from src.models.finished_unit import FinishedUnit
           exists = session.query(FinishedUnit).filter_by(id=comp_id).first()
           if not exists:
               raise ValueError(f"Component {index}: FinishedUnit {comp_id} not found")
       elif comp_type == "material_unit":
           from src.models.material_unit import MaterialUnit
           exists = session.query(MaterialUnit).filter_by(id=comp_id).first()
           if not exists:
               raise ValueError(f"Component {index}: MaterialUnit {comp_id} not found")
       elif comp_type == "finished_good":
           exists = session.query(FinishedGood).filter_by(id=comp_id).first()
           if not exists:
               raise ValueError(f"Component {index}: FinishedGood {comp_id} not found")
   ```
3. Call validation at start of `_create_finished_good_impl()`:
   ```python
   _validate_components(components, session)
   ```

**Files**:
- `src/services/finished_good_service.py` (~45 lines added)

**Validation**:
- [ ] Missing type/id raises ValueError
- [ ] Invalid type raises ValueError
- [ ] Non-positive quantity raises ValueError
- [ ] Non-existent references raise ValueError
- [ ] Clear error messages include component index

---

### T011: Add service layer tests for create with foods components

**Purpose**: Test creating FinishedGood with FinishedUnit components.

**Steps**:
1. Create or update `src/tests/test_finished_good_service.py`
2. Add test fixture for FinishedUnit:
   ```python
   @pytest.fixture
   def finished_unit(db_session, recipe):
       from src.models.finished_unit import FinishedUnit
       fu = FinishedUnit(
           display_name="Test Cookie",
           recipe_id=recipe.id,
           yield_quantity=24
       )
       db_session.add(fu)
       db_session.commit()
       return fu
   ```
3. Add test:
   ```python
   def test_create_finished_good_with_foods(db_session, finished_unit):
       components = [
           {"type": "finished_unit", "id": finished_unit.id, "quantity": 6, "sort_order": 0}
       ]
       fg = finished_good_service.create_finished_good(
           display_name="Cookie Gift Box",
           assembly_type=AssemblyType.GIFT_BOX,
           components=components,
           session=db_session
       )
       assert fg.id is not None
       assert len(fg.components) == 1
       assert fg.components[0].finished_unit_id == finished_unit.id
       assert fg.components[0].component_quantity == 6
   ```
4. Add test for multiple foods:
   ```python
   def test_create_finished_good_with_multiple_foods(db_session, finished_unit, another_finished_unit):
       components = [
           {"type": "finished_unit", "id": finished_unit.id, "quantity": 3},
           {"type": "finished_unit", "id": another_finished_unit.id, "quantity": 3},
       ]
       fg = finished_good_service.create_finished_good(
           display_name="Variety Cookie Box",
           components=components,
           session=db_session
       )
       assert len(fg.components) == 2
   ```

**Files**:
- `src/tests/test_finished_good_service.py` (~60 lines added)

**Validation**:
- [ ] Test passes with single food component
- [ ] Test passes with multiple food components
- [ ] Composition relationships correct
- [ ] Quantities preserved

---

### T012: Add service layer tests for create with materials components [P]

**Purpose**: Test creating FinishedGood with MaterialUnit components.

**Steps**:
1. Add test fixture for MaterialUnit:
   ```python
   @pytest.fixture
   def material_unit(db_session, material_product):
       from src.models.material_unit import MaterialUnit
       mu = MaterialUnit(
           name="Gift Box - Medium",
           product_id=material_product.id
       )
       db_session.add(mu)
       db_session.commit()
       return mu
   ```
2. Add tests:
   ```python
   def test_create_finished_good_with_materials(db_session, material_unit):
       components = [
           {"type": "material_unit", "id": material_unit.id, "quantity": 1}
       ]
       fg = finished_good_service.create_finished_good(
           display_name="Gift Package",
           components=components,
           session=db_session
       )
       assert len(fg.components) == 1
       assert fg.components[0].material_unit_id == material_unit.id

   def test_create_finished_good_with_mixed_components(db_session, finished_unit, material_unit):
       components = [
           {"type": "finished_unit", "id": finished_unit.id, "quantity": 6},
           {"type": "material_unit", "id": material_unit.id, "quantity": 1, "notes": "Ribbon wrap"},
       ]
       fg = finished_good_service.create_finished_good(
           display_name="Complete Gift Box",
           components=components,
           session=db_session
       )
       assert len(fg.components) == 2
   ```

**Files**:
- `src/tests/test_finished_good_service.py` (~50 lines added)

**Validation**:
- [ ] Material-only component works
- [ ] Mixed food + material works
- [ ] Notes preserved on components

---

### T013: Add service layer tests for create with nested FinishedGood components [P]

**Purpose**: Test creating FinishedGood that contains another FinishedGood.

**Steps**:
1. Add test fixture for nested FinishedGood:
   ```python
   @pytest.fixture
   def inner_finished_good(db_session, finished_unit):
       fg = finished_good_service.create_finished_good(
           display_name="Small Gift Box",
           assembly_type=AssemblyType.GIFT_BOX,
           components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 2}],
           session=db_session
       )
       return fg
   ```
2. Add tests:
   ```python
   def test_create_finished_good_with_nested_component(db_session, inner_finished_good):
       components = [
           {"type": "finished_good", "id": inner_finished_good.id, "quantity": 2}
       ]
       fg = finished_good_service.create_finished_good(
           display_name="Large Gift Bundle",
           assembly_type=AssemblyType.VARIETY_PACK,
           components=components,
           session=db_session
       )
       assert len(fg.components) == 1
       assert fg.components[0].finished_good_id == inner_finished_good.id
       assert fg.components[0].component_quantity == 2

   def test_create_finished_good_with_all_component_types(db_session, finished_unit, material_unit, inner_finished_good):
       components = [
           {"type": "finished_unit", "id": finished_unit.id, "quantity": 4, "sort_order": 0},
           {"type": "material_unit", "id": material_unit.id, "quantity": 1, "sort_order": 1},
           {"type": "finished_good", "id": inner_finished_good.id, "quantity": 1, "sort_order": 2},
       ]
       fg = finished_good_service.create_finished_good(
           display_name="Ultimate Gift Package",
           components=components,
           session=db_session
       )
       assert len(fg.components) == 3
       # Verify sort order preserved
       sorted_comps = sorted(fg.components, key=lambda c: c.sort_order)
       assert sorted_comps[0].finished_unit_id is not None
       assert sorted_comps[1].material_unit_id is not None
       assert sorted_comps[2].finished_good_id is not None
   ```

**Files**:
- `src/tests/test_finished_good_service.py` (~60 lines added)

**Validation**:
- [ ] Nested FinishedGood component works
- [ ] All three component types in one FinishedGood works
- [ ] Sort order is preserved

---

## Definition of Done

- [ ] All 6 subtasks completed
- [ ] `create_finished_good()` accepts `components` parameter
- [ ] All three component types (food, material, nested) work
- [ ] Input validation catches invalid data
- [ ] All tests pass with >80% coverage for new code
- [ ] Existing tests still pass

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Follow session management pattern from CLAUDE.md |
| Factory method signature changes | Check current Composition model before using |
| Missing test fixtures | Build fixtures incrementally, reuse from other tests |

## Reviewer Guidance

1. Verify session management pattern is followed
2. Check that Composition factory methods are used correctly
3. Ensure validation provides clear error messages
4. Confirm tests cover all three component types
5. Check for proper transaction atomicity (all or nothing)

## Activity Log

- 2026-01-31T04:32:11Z – gemini-wp02 – shell_pid=21725 – lane=doing – Started implementation via workflow command
- 2026-01-31T04:41:51Z – gemini-wp02 – shell_pid=21725 – lane=for_review – Ready for review: Enhanced create_finished_good() with component creation support using Composition factory methods, input validation, and comprehensive tests
