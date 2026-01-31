---
work_package_id: WP03
title: Service Layer - Update and Validation
lane: "for_review"
dependencies: [WP02]
base_branch: 088-finished-goods-catalog-ui-WP02
base_commit: 8bdd6490de7fdc390af16873f9e19f46b067fef5
created_at: '2026-01-31T04:45:27.350747+00:00'
subtasks: [T014, T015, T016, T017, T018, T019, T020]
shell_pid: "26038"
history:
- date: '2026-01-30'
  action: created
  agent: claude
estimated_lines: 450
priority: P0
---

# WP03: Service Layer - Update and Validation

## Objective

Implement update functionality with component replacement and add circular reference validation to prevent invalid nesting. Also implement delete safety checks to prevent deleting FinishedGoods that are referenced elsewhere.

## Context

- **Feature**: 088-finished-goods-catalog-ui
- **Priority**: P0 (required for edit/delete operations)
- **Dependencies**: WP02 (create pattern established)
- **Estimated Size**: ~450 lines

### Reference Files

- `src/services/finished_good_service.py` - Service to enhance (from WP02)
- `src/models/composition.py` - Composition model
- `src/models/finished_good.py` - FinishedGood model

### Update Strategy

Delete all existing Compositions for the FinishedGood, then create new ones. This is simpler and safer than trying to diff and update individual compositions.

### Circular Reference Algorithm

Graph traversal from target FinishedGood, checking if current ID is reachable:
1. Cannot add self (A → A)
2. Cannot add if target contains current (A → B where B contains A)
3. Cannot add if target's descendants contain current (transitive closure)

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

---

## Subtasks

### T014: Implement `update_finished_good()` with component replacement

**Purpose**: Create update function that replaces all components atomically.

**Steps**:
1. Add `update_finished_good()` function:
   ```python
   def update_finished_good(
       finished_good_id: int,
       display_name: Optional[str] = None,
       assembly_type: Optional[AssemblyType] = None,
       components: Optional[List[Dict]] = None,
       packaging_instructions: Optional[str] = None,
       notes: Optional[str] = None,
       session=None
   ) -> FinishedGood:
       if session is not None:
           return _update_finished_good_impl(finished_good_id, display_name, assembly_type,
                                             components, packaging_instructions, notes, session)
       with session_scope() as session:
           return _update_finished_good_impl(finished_good_id, display_name, assembly_type,
                                             components, packaging_instructions, notes, session)
   ```
2. Implement `_update_finished_good_impl()`:
   ```python
   def _update_finished_good_impl(finished_good_id, display_name, assembly_type,
                                   components, packaging_instructions, notes, session):
       fg = session.query(FinishedGood).filter_by(id=finished_good_id).first()
       if not fg:
           raise ValueError(f"FinishedGood {finished_good_id} not found")

       # Update basic fields if provided
       if display_name is not None:
           fg.display_name = display_name
           fg.slug = generate_slug(display_name)
       if assembly_type is not None:
           fg.assembly_type = assembly_type
       if packaging_instructions is not None:
           fg.packaging_instructions = packaging_instructions
       if notes is not None:
           fg.notes = notes

       # Replace components if provided
       if components is not None:
           # Validate new components (including circular reference check)
           _validate_components(components, session)
           _validate_no_circular_references(finished_good_id, components, session)

           # Delete existing compositions
           session.query(Composition).filter_by(assembly_id=finished_good_id).delete()

           # Create new compositions
           for comp_data in components:
               composition = _create_composition(finished_good_id, comp_data, session)
               session.add(composition)

       session.flush()
       return fg
   ```

**Files**:
- `src/services/finished_good_service.py` (~50 lines added)

**Validation**:
- [ ] Basic field updates work
- [ ] Component replacement works (old deleted, new created)
- [ ] Validation runs before changes
- [ ] Returns updated FinishedGood

---

### T015: Add `validate_no_circular_references()` using graph traversal

**Purpose**: Prevent circular references in nested FinishedGoods.

**Steps**:
1. Implement validation function:
   ```python
   def _validate_no_circular_references(current_fg_id: int, components: List[Dict], session) -> None:
       """
       Validate that adding these components won't create circular references.

       A circular reference occurs when:
       1. Component is the current FinishedGood itself (A → A)
       2. Component contains the current FinishedGood (A → B where B → A)
       3. Component's descendants contain current FinishedGood (transitive)
       """
       # Extract finished_good component IDs
       fg_component_ids = [
           c["id"] for c in components if c["type"] == "finished_good"
       ]

       if not fg_component_ids:
           return  # No nested FinishedGoods, no cycle possible

       # Check for self-reference
       if current_fg_id in fg_component_ids:
           raise ValueError("Cannot add a FinishedGood as a component of itself")

       # Check for cycles using BFS
       for target_id in fg_component_ids:
           if _would_create_cycle(current_fg_id, target_id, session):
               target = session.query(FinishedGood).get(target_id)
               raise ValueError(
                   f"Cannot add '{target.display_name}' as component: "
                   f"it would create a circular reference"
               )
   ```
2. Implement cycle detection:
   ```python
   def _would_create_cycle(current_fg_id: int, target_fg_id: int, session) -> bool:
       """
       Check if adding target_fg_id as a component of current_fg_id would create a cycle.
       Returns True if target_fg_id (or any of its descendants) contains current_fg_id.
       """
       visited = set()
       queue = [target_fg_id]

       while queue:
           fg_id = queue.pop(0)
           if fg_id in visited:
               continue
           visited.add(fg_id)

           # Get all FinishedGood components of this fg
           compositions = session.query(Composition).filter_by(assembly_id=fg_id).all()
           for comp in compositions:
               if comp.finished_good_id is not None:
                   if comp.finished_good_id == current_fg_id:
                       return True  # Cycle detected!
                   queue.append(comp.finished_good_id)

       return False
   ```

**Files**:
- `src/services/finished_good_service.py` (~55 lines added)

**Validation**:
- [ ] Self-reference detected and rejected
- [ ] Direct cycle detected (A → B → A)
- [ ] Transitive cycle detected (A → B → C → A)
- [ ] Clear error messages

---

### T016: Add delete safety checks (check if referenced by other FinishedGoods)

**Purpose**: Prevent deleting FinishedGoods that are components of other FinishedGoods.

**Steps**:
1. Implement check function:
   ```python
   def _check_finished_good_references(finished_good_id: int, session) -> List[str]:
       """
       Check if this FinishedGood is referenced by other FinishedGoods.
       Returns list of referencing FinishedGood names.
       """
       refs = session.query(Composition).filter_by(finished_good_id=finished_good_id).all()
       referencing_names = []
       for ref in refs:
           parent = session.query(FinishedGood).get(ref.assembly_id)
           if parent:
               referencing_names.append(parent.display_name)
       return referencing_names
   ```
2. Add to delete function (or create if not exists):
   ```python
   def delete_finished_good(finished_good_id: int, session=None) -> bool:
       if session is not None:
           return _delete_finished_good_impl(finished_good_id, session)
       with session_scope() as session:
           return _delete_finished_good_impl(finished_good_id, session)

   def _delete_finished_good_impl(finished_good_id: int, session) -> bool:
       # Check for references
       fg_refs = _check_finished_good_references(finished_good_id, session)
       if fg_refs:
           raise ValueError(
               f"Cannot delete: referenced by {len(fg_refs)} Finished Good(s): {', '.join(fg_refs[:3])}"
               + ("..." if len(fg_refs) > 3 else "")
           )

       # Check for event references (T017)
       # ...

       # Delete
       fg = session.query(FinishedGood).get(finished_good_id)
       if not fg:
           return False
       session.delete(fg)
       return True
   ```

**Files**:
- `src/services/finished_good_service.py` (~35 lines added)

**Validation**:
- [ ] Referenced FinishedGood cannot be deleted
- [ ] Error message lists referencing items
- [ ] Unreferenced FinishedGood can be deleted

---

### T017: Add delete safety checks (check if referenced by events/planning)

**Purpose**: Prevent deleting FinishedGoods that are used in event planning.

**Steps**:
1. Check for event references:
   ```python
   def _check_event_references(finished_good_id: int, session) -> List[str]:
       """
       Check if this FinishedGood is referenced by events.
       Returns list of event names.
       """
       from src.models.event_finished_good import EventFinishedGood
       from src.models.event import Event

       refs = session.query(EventFinishedGood).filter_by(finished_good_id=finished_good_id).all()
       event_names = []
       for ref in refs:
           event = session.query(Event).get(ref.event_id)
           if event:
               event_names.append(event.name)
       return event_names
   ```
2. Add to delete implementation:
   ```python
   def _delete_finished_good_impl(finished_good_id: int, session) -> bool:
       # Check for FG references
       fg_refs = _check_finished_good_references(finished_good_id, session)
       if fg_refs:
           raise ValueError(...)

       # Check for event references
       event_refs = _check_event_references(finished_good_id, session)
       if event_refs:
           raise ValueError(
               f"Cannot delete: used in {len(event_refs)} event(s): {', '.join(event_refs[:3])}"
               + ("..." if len(event_refs) > 3 else "")
           )

       # Delete if no references
       fg = session.query(FinishedGood).get(finished_good_id)
       if not fg:
           return False
       session.delete(fg)
       return True
   ```

**Files**:
- `src/services/finished_good_service.py` (~30 lines added)

**Validation**:
- [ ] Event-referenced FinishedGood cannot be deleted
- [ ] Error message lists event names
- [ ] FinishedGood with no event refs can be deleted

**Note**: If `EventFinishedGood` model doesn't exist yet, implement a stub that returns empty list and add a TODO comment.

---

### T018: Add service tests for update with component changes [P]

**Purpose**: Test the update functionality with component replacement.

**Steps**:
1. Add test for basic field update:
   ```python
   def test_update_finished_good_basic_fields(db_session, finished_good):
       updated = finished_good_service.update_finished_good(
           finished_good.id,
           display_name="Updated Name",
           assembly_type=AssemblyType.SEASONAL_BOX,
           notes="New notes",
           session=db_session
       )
       assert updated.display_name == "Updated Name"
       assert updated.assembly_type == AssemblyType.SEASONAL_BOX
       assert updated.notes == "New notes"
   ```
2. Add test for component replacement:
   ```python
   def test_update_finished_good_replace_components(db_session, finished_good_with_components, another_finished_unit):
       original_count = len(finished_good_with_components.components)
       assert original_count > 0

       new_components = [
           {"type": "finished_unit", "id": another_finished_unit.id, "quantity": 10}
       ]
       updated = finished_good_service.update_finished_good(
           finished_good_with_components.id,
           components=new_components,
           session=db_session
       )
       assert len(updated.components) == 1
       assert updated.components[0].finished_unit_id == another_finished_unit.id
       assert updated.components[0].component_quantity == 10
   ```
3. Add test for empty components (clear all):
   ```python
   def test_update_finished_good_clear_components(db_session, finished_good_with_components):
       updated = finished_good_service.update_finished_good(
           finished_good_with_components.id,
           components=[],
           session=db_session
       )
       assert len(updated.components) == 0
   ```

**Files**:
- `src/tests/test_finished_good_service.py` (~60 lines added)

**Validation**:
- [ ] Basic field updates work
- [ ] Component replacement works
- [ ] Empty components list clears all

---

### T019: Add service tests for circular reference detection [P]

**Purpose**: Test all circular reference edge cases.

**Steps**:
1. Test self-reference:
   ```python
   def test_circular_reference_self(db_session, finished_good):
       components = [{"type": "finished_good", "id": finished_good.id, "quantity": 1}]
       with pytest.raises(ValueError) as exc:
           finished_good_service.update_finished_good(
               finished_good.id,
               components=components,
               session=db_session
           )
       assert "itself" in str(exc.value)
   ```
2. Test direct cycle (A → B → A):
   ```python
   def test_circular_reference_direct(db_session, finished_unit):
       # Create A
       fg_a = finished_good_service.create_finished_good("FG A", session=db_session)
       # Create B containing A
       fg_b = finished_good_service.create_finished_good(
           "FG B",
           components=[{"type": "finished_good", "id": fg_a.id, "quantity": 1}],
           session=db_session
       )
       # Try to add B to A - should fail
       with pytest.raises(ValueError) as exc:
           finished_good_service.update_finished_good(
               fg_a.id,
               components=[{"type": "finished_good", "id": fg_b.id, "quantity": 1}],
               session=db_session
           )
       assert "circular reference" in str(exc.value).lower()
   ```
3. Test transitive cycle (A → B → C → A):
   ```python
   def test_circular_reference_transitive(db_session):
       # Create A (empty)
       fg_a = finished_good_service.create_finished_good("FG A", session=db_session)
       # Create B containing A
       fg_b = finished_good_service.create_finished_good(
           "FG B",
           components=[{"type": "finished_good", "id": fg_a.id, "quantity": 1}],
           session=db_session
       )
       # Create C containing B
       fg_c = finished_good_service.create_finished_good(
           "FG C",
           components=[{"type": "finished_good", "id": fg_b.id, "quantity": 1}],
           session=db_session
       )
       # Try to add C to A - should fail (A → C → B → A)
       with pytest.raises(ValueError) as exc:
           finished_good_service.update_finished_good(
               fg_a.id,
               components=[{"type": "finished_good", "id": fg_c.id, "quantity": 1}],
               session=db_session
           )
       assert "circular reference" in str(exc.value).lower()
   ```

**Files**:
- `src/tests/test_finished_good_service.py` (~70 lines added)

**Validation**:
- [ ] Self-reference rejected
- [ ] Direct cycle rejected (A → B → A)
- [ ] Transitive cycle rejected (A → B → C → A)
- [ ] Error messages are clear

---

### T020: Add service tests for delete safety checks [P]

**Purpose**: Test delete blocking when references exist.

**Steps**:
1. Test delete blocks when used by another FinishedGood:
   ```python
   def test_delete_blocked_by_finished_good_reference(db_session, finished_unit):
       # Create inner FG
       inner = finished_good_service.create_finished_good(
           "Inner Box",
           components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 1}],
           session=db_session
       )
       # Create outer FG containing inner
       outer = finished_good_service.create_finished_good(
           "Outer Box",
           components=[{"type": "finished_good", "id": inner.id, "quantity": 1}],
           session=db_session
       )
       # Try to delete inner - should fail
       with pytest.raises(ValueError) as exc:
           finished_good_service.delete_finished_good(inner.id, session=db_session)
       assert "Outer Box" in str(exc.value)
   ```
2. Test delete succeeds when no references:
   ```python
   def test_delete_succeeds_no_references(db_session, finished_unit):
       fg = finished_good_service.create_finished_good(
           "Standalone Box",
           components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 1}],
           session=db_session
       )
       result = finished_good_service.delete_finished_good(fg.id, session=db_session)
       assert result is True
       # Verify deleted
       deleted = session.query(FinishedGood).get(fg.id)
       assert deleted is None
   ```
3. Test cascade deletes compositions:
   ```python
   def test_delete_cascades_compositions(db_session, finished_unit):
       fg = finished_good_service.create_finished_good(
           "Test Box",
           components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 2}],
           session=db_session
       )
       fg_id = fg.id
       # Delete
       finished_good_service.delete_finished_good(fg_id, session=db_session)
       # Verify compositions also deleted
       remaining = session.query(Composition).filter_by(assembly_id=fg_id).count()
       assert remaining == 0
   ```

**Files**:
- `src/tests/test_finished_good_service.py` (~60 lines added)

**Validation**:
- [ ] Delete blocked when referenced by other FG
- [ ] Delete succeeds when no references
- [ ] Compositions cascade deleted

---

## Definition of Done

- [ ] All 7 subtasks completed
- [ ] `update_finished_good()` implemented with component replacement
- [ ] Circular reference validation catches all cycle types
- [ ] Delete safety checks prevent orphaning
- [ ] All tests pass with >80% coverage for new code

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missed circular reference edge case | Explicit tests for A→A, A→B→A, A→B→C→A |
| EventFinishedGood may not exist | Stub the check, add TODO, document in notes |
| Complex graph traversal bugs | Use BFS (simpler than DFS), add debug logging |

## Reviewer Guidance

1. Verify circular reference algorithm catches all edge cases
2. Check that update replaces components atomically (delete all, create new)
3. Confirm delete safety checks query correct tables
4. Test with deeply nested FinishedGoods (3+ levels)
5. Verify error messages are user-friendly

## Activity Log

- 2026-01-31T04:52:02Z – unknown – shell_pid=26038 – lane=for_review – Ready for review: Implements update_finished_good with component replacement, circular reference validation, and delete safety checks. All 37 tests passing.
