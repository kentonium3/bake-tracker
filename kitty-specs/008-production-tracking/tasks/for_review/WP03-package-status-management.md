---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
title: "Package Status Management"
phase: "Phase 2 - Service Layer"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "58999"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Package Status Management

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Implement `update_package_status()` with strict transition validation
- Implement `can_assemble_package()` to check production completeness
- Enforce status progression: pending -> assembled -> delivered
- Block invalid transitions and provide clear error messages
- Achieve >70% test coverage

## Context & Constraints

**Reference Documents**:
- Service Contract: `kitty-specs/008-production-tracking/contracts/production_service.md`
- Data Model: `kitty-specs/008-production-tracking/data-model.md` (Status Transitions section)
- Spec: `kitty-specs/008-production-tracking/spec.md` (FR-004, FR-005)

**Valid Status Transitions**:
```
PENDING -> ASSEMBLED (allowed, requires all recipes produced)
ASSEMBLED -> DELIVERED (allowed)

Invalid transitions (BLOCKED):
- PENDING -> DELIVERED (must assemble first)
- ASSEMBLED -> PENDING (no rollback)
- DELIVERED -> * (no rollback from delivered)
```

**Dependencies**:
- WP01: PackageStatus enum, EventRecipientPackage.status field
- WP02: ProductionRecord must exist to check assembly readiness

---

## Subtasks & Detailed Guidance

### Subtask T013 - Add Status Transition Exceptions

**Purpose**: Clear exception types for invalid operations.

**Steps**:
Add to `src/services/production_service.py`:

```python
class InvalidStatusTransitionError(Exception):
    """Raised when package status transition is not allowed."""
    def __init__(self, current: PackageStatus, target: PackageStatus):
        self.current = current
        self.target = target
        super().__init__(
            f"Cannot transition from {current.value} to {target.value}"
        )


class IncompleteProductionError(Exception):
    """Raised when trying to assemble package with incomplete production."""
    def __init__(self, assignment_id: int, missing_recipes: List[Dict]):
        self.assignment_id = assignment_id
        self.missing_recipes = missing_recipes
        recipe_names = ", ".join(r["recipe_name"] for r in missing_recipes)
        super().__init__(
            f"Cannot assemble package {assignment_id}: missing production for {recipe_names}"
        )


class AssignmentNotFoundError(Exception):
    """Raised when EventRecipientPackage not found."""
    def __init__(self, assignment_id: int):
        self.assignment_id = assignment_id
        super().__init__(f"Assignment with ID {assignment_id} not found")
```

**Files**: `src/services/production_service.py` (ADD)

---

### Subtask T012 - Implement can_assemble_package()

**Purpose**: Check if all required recipes have been fully produced before assembly.

**Steps**:
```python
def can_assemble_package(assignment_id: int) -> Dict[str, Any]:
    """
    Check if a package can be marked as assembled.

    Verifies all required recipes for the package's contents have
    sufficient production records for the event.

    Args:
        assignment_id: EventRecipientPackage ID

    Returns:
        Dict with:
        - can_assemble: bool
        - missing_recipes: List of recipes needing more production
    """
    try:
        with session_scope() as session:
            # Load assignment with full chain
            assignment = (
                session.query(EventRecipientPackage)
                .options(
                    joinedload(EventRecipientPackage.package)
                    .joinedload(Package.package_finished_goods)
                    .joinedload(PackageFinishedGood.finished_good)
                    .joinedload(FinishedGood.components)
                    .joinedload(Composition.finished_unit_component)
                )
                .filter(EventRecipientPackage.id == assignment_id)
                .first()
            )

            if not assignment:
                raise AssignmentNotFoundError(assignment_id)

            event_id = assignment.event_id

            # Get recipe needs for this specific package
            # (Similar logic to event_service.get_recipe_needs but for single package)
            recipe_needs = _calculate_package_recipe_needs(assignment)

            # Get production totals for this event
            production_totals = (
                session.query(
                    ProductionRecord.recipe_id,
                    func.sum(ProductionRecord.batches).label("produced")
                )
                .filter(ProductionRecord.event_id == event_id)
                .group_by(ProductionRecord.recipe_id)
                .all()
            )
            produced_map = {r.recipe_id: r.produced for r in production_totals}

            # Check each required recipe
            missing = []
            for need in recipe_needs:
                produced = produced_map.get(need["recipe_id"], 0)
                if produced < need["batches_required"]:
                    missing.append({
                        "recipe_id": need["recipe_id"],
                        "recipe_name": need["recipe_name"],
                        "batches_required": need["batches_required"],
                        "batches_produced": produced,
                        "batches_missing": need["batches_required"] - produced
                    })

            return {
                "can_assemble": len(missing) == 0,
                "missing_recipes": missing
            }

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to check assembly readiness: {str(e)}")


def _calculate_package_recipe_needs(assignment: EventRecipientPackage) -> List[Dict]:
    """Helper to calculate recipe needs for a single package assignment."""
    recipe_totals = {}
    recipe_info = {}

    if not assignment.package:
        return []

    for pfg in assignment.package.package_finished_goods:
        if not pfg.finished_good:
            continue

        for composition in pfg.finished_good.components:
            if not composition.finished_unit_component:
                continue

            fu = composition.finished_unit_component
            if not fu.recipe:
                continue

            recipe_id = fu.recipe_id
            items_per_batch = fu.items_per_batch or 1
            units = int(composition.component_quantity) * pfg.quantity * assignment.quantity

            recipe_totals[recipe_id] = recipe_totals.get(recipe_id, 0) + units
            recipe_info[recipe_id] = {
                "name": fu.recipe.name,
                "items_per_batch": items_per_batch
            }

    result = []
    for recipe_id, total_units in recipe_totals.items():
        info = recipe_info[recipe_id]
        batches_needed = ceil(total_units / info["items_per_batch"])
        result.append({
            "recipe_id": recipe_id,
            "recipe_name": info["name"],
            "batches_required": batches_needed
        })

    return result
```

**Files**: `src/services/production_service.py` (ADD)

**Notes**:
- This checks production against the full traversal chain
- Considers assignment.quantity (multiple packages for same recipient)

---

### Subtask T011 - Implement update_package_status()

**Purpose**: Update package status with validation of allowed transitions.

**Steps**:
```python
# Valid transitions map
VALID_TRANSITIONS = {
    PackageStatus.PENDING: {PackageStatus.ASSEMBLED},
    PackageStatus.ASSEMBLED: {PackageStatus.DELIVERED},
    PackageStatus.DELIVERED: set(),  # No transitions from delivered
}


def update_package_status(
    assignment_id: int,
    new_status: PackageStatus,
    delivered_to: Optional[str] = None
) -> EventRecipientPackage:
    """
    Update the status of a package assignment.

    Args:
        assignment_id: EventRecipientPackage ID
        new_status: Target status
        delivered_to: Optional delivery note (only for DELIVERED status)

    Returns:
        Updated EventRecipientPackage

    Raises:
        AssignmentNotFoundError: Assignment doesn't exist
        InvalidStatusTransitionError: Transition not allowed
        IncompleteProductionError: Trying to assemble with incomplete production
    """
    try:
        with session_scope() as session:
            assignment = (
                session.query(EventRecipientPackage)
                .filter(EventRecipientPackage.id == assignment_id)
                .first()
            )

            if not assignment:
                raise AssignmentNotFoundError(assignment_id)

            current_status = assignment.status

            # Validate transition
            if new_status not in VALID_TRANSITIONS.get(current_status, set()):
                raise InvalidStatusTransitionError(current_status, new_status)

            # If transitioning to ASSEMBLED, verify production complete
            if new_status == PackageStatus.ASSEMBLED:
                assembly_check = can_assemble_package(assignment_id)
                if not assembly_check["can_assemble"]:
                    raise IncompleteProductionError(
                        assignment_id,
                        assembly_check["missing_recipes"]
                    )

            # Update status
            assignment.status = new_status

            # Set delivered_to if transitioning to DELIVERED
            if new_status == PackageStatus.DELIVERED and delivered_to:
                assignment.delivered_to = delivered_to

            session.flush()
            session.refresh(assignment)
            return assignment

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update package status: {str(e)}")
```

**Files**: `src/services/production_service.py` (ADD)

---

### Subtask T014 - Write Tests for Status Management

**Purpose**: Comprehensive tests for status transitions.

**Steps**:
Add to `src/tests/services/test_production_service.py`:

```python
class TestUpdatePackageStatus:
    """Tests for update_package_status() function."""

    def test_pending_to_assembled_success(self, test_db):
        """Test: Can transition PENDING -> ASSEMBLED when production complete."""
        # Setup: Create assignment, record sufficient production
        # ...
        result = update_package_status(assignment.id, PackageStatus.ASSEMBLED)
        assert result.status == PackageStatus.ASSEMBLED

    def test_assembled_to_delivered_success(self, test_db):
        """Test: Can transition ASSEMBLED -> DELIVERED."""
        # Setup: Create assembled assignment
        # ...
        result = update_package_status(
            assignment.id,
            PackageStatus.DELIVERED,
            delivered_to="Left with neighbor"
        )
        assert result.status == PackageStatus.DELIVERED
        assert result.delivered_to == "Left with neighbor"

    def test_pending_to_delivered_blocked(self, test_db):
        """Test: Cannot skip PENDING -> DELIVERED."""
        # Setup: Create pending assignment
        # ...
        with pytest.raises(InvalidStatusTransitionError):
            update_package_status(assignment.id, PackageStatus.DELIVERED)

    def test_assembled_to_pending_blocked(self, test_db):
        """Test: Cannot rollback ASSEMBLED -> PENDING."""
        # ...
        with pytest.raises(InvalidStatusTransitionError):
            update_package_status(assignment.id, PackageStatus.PENDING)

    def test_delivered_to_any_blocked(self, test_db):
        """Test: Cannot transition from DELIVERED."""
        # ...
        with pytest.raises(InvalidStatusTransitionError):
            update_package_status(assignment.id, PackageStatus.ASSEMBLED)

    def test_assemble_incomplete_production(self, test_db):
        """Test: Cannot assemble when recipes not fully produced."""
        # Setup: Create assignment needing 2 batches, produce only 1
        # ...
        with pytest.raises(IncompleteProductionError) as exc_info:
            update_package_status(assignment.id, PackageStatus.ASSEMBLED)

        assert len(exc_info.value.missing_recipes) > 0


class TestCanAssemblePackage:
    """Tests for can_assemble_package() function."""

    def test_can_assemble_all_produced(self, test_db):
        """Test: Returns True when all recipes fully produced."""
        # ...
        result = can_assemble_package(assignment.id)
        assert result["can_assemble"] is True
        assert len(result["missing_recipes"]) == 0

    def test_cannot_assemble_partial_production(self, test_db):
        """Test: Returns False with missing recipes list."""
        # ...
        result = can_assemble_package(assignment.id)
        assert result["can_assemble"] is False
        assert len(result["missing_recipes"]) > 0
```

**Files**: `src/tests/services/test_production_service.py` (ADD)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Complex traversal for assembly check | Reuse pattern from event_service.get_recipe_needs |
| Status rollback not supported | Clear error messages explaining constraints |

---

## Definition of Done Checklist

- [ ] InvalidStatusTransitionError and IncompleteProductionError defined
- [ ] can_assemble_package() checks all recipes produced
- [ ] update_package_status() validates transitions
- [ ] PENDING -> DELIVERED blocked
- [ ] Rollback from ASSEMBLED/DELIVERED blocked
- [ ] Tests cover all valid and invalid transitions
- [ ] >70% coverage on new functions
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

- Verify VALID_TRANSITIONS map is complete
- Verify assembly check uses same traversal as event_service
- Verify delivered_to only set when transitioning to DELIVERED
- Check all exception types have useful error messages

---

## Activity Log

- 2025-12-04T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-04T16:27:17Z – claude – shell_pid=58999 – lane=doing – Started implementation (retroactive recovery)
- 2025-12-04T16:28:29Z – claude – shell_pid=58999 – lane=for_review – Implementation complete, ready for review (retroactive recovery)
