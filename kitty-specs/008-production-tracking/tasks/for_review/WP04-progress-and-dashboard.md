---
work_package_id: "WP04"
subtasks:
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "Progress & Dashboard Services"
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

# Work Package Prompt: WP04 - Progress & Dashboard Services

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Implement `get_production_progress()` for single-event progress data
- Implement `get_dashboard_summary()` for multi-event overview
- Implement `get_recipe_cost_breakdown()` for cost drill-down
- Support actual vs planned cost comparisons at event and recipe levels
- Achieve >70% test coverage

## Context & Constraints

**Reference Documents**:
- Service Contract: `kitty-specs/008-production-tracking/contracts/production_service.md`
- Research: `kitty-specs/008-production-tracking/research.md` (get_recipe_needs API)
- Spec: `kitty-specs/008-production-tracking/spec.md` (User Story 4, User Story 5)

**Key Dependencies**:
- `event_service.get_recipe_needs(event_id)` - provides required batches per recipe
- ProductionRecord - provides produced batches and actual costs
- EventRecipientPackage.status - provides package status counts

**Performance Constraint**: Dashboard must load within 2 seconds for 10 events

---

## Subtasks & Detailed Guidance

### Subtask T015 - Implement get_production_progress() [P]

**Purpose**: Get comprehensive progress data for a single event.

**Steps**:
```python
def get_production_progress(event_id: int) -> Dict[str, Any]:
    """
    Get production progress for an event.

    Aggregates recipe production status, package status, and costs.

    Args:
        event_id: Event to get progress for

    Returns:
        Dict with recipes, packages, costs, and completion status
    """
    try:
        with session_scope() as session:
            # Verify event exists
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise EventNotFoundError(event_id)

            # Get required batches from event_service
            recipe_needs = event_service.get_recipe_needs(event_id)

            # Get produced batches with actual costs
            production_data = (
                session.query(
                    ProductionRecord.recipe_id,
                    func.sum(ProductionRecord.batches).label("produced"),
                    func.sum(ProductionRecord.actual_cost).label("actual_cost")
                )
                .filter(ProductionRecord.event_id == event_id)
                .group_by(ProductionRecord.recipe_id)
                .all()
            )
            produced_map = {
                r.recipe_id: {"produced": r.produced, "actual_cost": r.actual_cost}
                for r in production_data
            }

            # Build recipe progress list
            recipes = []
            total_actual = Decimal("0.00")
            total_planned = Decimal("0.00")

            for need in recipe_needs:
                recipe_id = need["recipe_id"]
                prod = produced_map.get(recipe_id, {"produced": 0, "actual_cost": Decimal("0")})

                # Get planned cost from recipe (estimated)
                recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
                planned_per_batch = Decimal(str(recipe.calculate_cost())) if recipe else Decimal("0")
                planned_cost = planned_per_batch * Decimal(str(need["batches_needed"]))

                actual = prod["actual_cost"] or Decimal("0")

                recipes.append({
                    "recipe_id": recipe_id,
                    "recipe_name": need["recipe_name"],
                    "batches_required": need["batches_needed"],
                    "batches_produced": prod["produced"],
                    "is_complete": prod["produced"] >= need["batches_needed"],
                    "actual_cost": actual,
                    "planned_cost": planned_cost
                })

                total_actual += actual
                total_planned += planned_cost

            # Get package status counts
            package_counts = (
                session.query(
                    EventRecipientPackage.status,
                    func.count(EventRecipientPackage.id).label("count")
                )
                .filter(EventRecipientPackage.event_id == event_id)
                .group_by(EventRecipientPackage.status)
                .all()
            )

            status_map = {s.status.value: s.count for s in package_counts}
            pending = status_map.get("pending", 0)
            assembled = status_map.get("assembled", 0)
            delivered = status_map.get("delivered", 0)
            total_packages = pending + assembled + delivered

            return {
                "event_id": event_id,
                "event_name": event.name,
                "recipes": recipes,
                "packages": {
                    "total": total_packages,
                    "pending": pending,
                    "assembled": assembled,
                    "delivered": delivered
                },
                "costs": {
                    "actual_total": total_actual,
                    "planned_total": total_planned
                },
                "is_complete": delivered == total_packages and total_packages > 0
            }

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get production progress: {str(e)}")
```

**Files**: `src/services/production_service.py` (ADD)

**Parallel?**: Yes - independent function

---

### Subtask T016 - Implement get_dashboard_summary() [P]

**Purpose**: Get summary across all active events for the dashboard.

**Steps**:
```python
def get_dashboard_summary() -> List[Dict[str, Any]]:
    """
    Get production summary across all active events.

    Active events are those with packages not all delivered.

    Returns:
        List of event summaries sorted by event_date ascending
    """
    try:
        with session_scope() as session:
            # Find events with at least one package not delivered
            active_events = (
                session.query(Event)
                .join(EventRecipientPackage)
                .filter(EventRecipientPackage.status != PackageStatus.DELIVERED)
                .distinct()
                .all()
            )

            # Also include events where all packages are delivered (show as complete)
            # Actually, get all events with packages
            events_with_packages = (
                session.query(Event)
                .join(EventRecipientPackage)
                .distinct()
                .order_by(Event.event_date.asc())
                .all()
            )

            summaries = []
            for event in events_with_packages:
                progress = get_production_progress(event.id)

                # Count complete recipes
                recipes_complete = sum(
                    1 for r in progress["recipes"] if r["is_complete"]
                )
                recipes_total = len(progress["recipes"])

                summaries.append({
                    "event_id": event.id,
                    "event_name": event.name,
                    "event_date": event.event_date,
                    "recipes_complete": recipes_complete,
                    "recipes_total": recipes_total,
                    "packages_pending": progress["packages"]["pending"],
                    "packages_assembled": progress["packages"]["assembled"],
                    "packages_delivered": progress["packages"]["delivered"],
                    "packages_total": progress["packages"]["total"],
                    "actual_cost": progress["costs"]["actual_total"],
                    "planned_cost": progress["costs"]["planned_total"],
                    "is_complete": progress["is_complete"]
                })

            return summaries

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get dashboard summary: {str(e)}")
```

**Files**: `src/services/production_service.py` (ADD)

**Parallel?**: Yes - independent function (calls T015 internally)

---

### Subtask T017 - Implement get_recipe_cost_breakdown() [P]

**Purpose**: Detailed cost breakdown by recipe with variance calculations.

**Steps**:
```python
def get_recipe_cost_breakdown(event_id: int) -> List[Dict[str, Any]]:
    """
    Get detailed cost breakdown by recipe for an event.

    Args:
        event_id: Event to get breakdown for

    Returns:
        List of recipe cost details with variance
    """
    progress = get_production_progress(event_id)

    breakdown = []
    for recipe in progress["recipes"]:
        actual = recipe["actual_cost"]
        planned = recipe["planned_cost"]
        variance = actual - planned

        # Calculate variance percent (avoid division by zero)
        if planned > 0:
            variance_percent = float((variance / planned) * 100)
        else:
            variance_percent = 0.0 if actual == 0 else 100.0

        breakdown.append({
            "recipe_id": recipe["recipe_id"],
            "recipe_name": recipe["recipe_name"],
            "batches_required": recipe["batches_required"],
            "batches_produced": recipe["batches_produced"],
            "actual_cost": actual,
            "planned_cost": planned,
            "variance": variance,
            "variance_percent": round(variance_percent, 2)
        })

    return breakdown
```

**Files**: `src/services/production_service.py` (ADD)

**Parallel?**: Yes - simple wrapper around T015

---

### Subtask T018 - Write Tests for Progress/Dashboard Functions

**Purpose**: Comprehensive tests for progress calculations.

**Steps**:
```python
class TestGetProductionProgress:
    """Tests for get_production_progress() function."""

    def test_progress_no_production(self, test_db):
        """Test: Returns zero progress when nothing produced."""
        # Setup: Event with packages, no production records
        progress = get_production_progress(event.id)

        assert progress["event_id"] == event.id
        for recipe in progress["recipes"]:
            assert recipe["batches_produced"] == 0
            assert recipe["actual_cost"] == Decimal("0")

    def test_progress_partial_production(self, test_db):
        """Test: Shows partial progress correctly."""
        # Setup: 2 of 4 batches produced
        progress = get_production_progress(event.id)

        assert progress["recipes"][0]["batches_produced"] == 2
        assert progress["recipes"][0]["is_complete"] is False

    def test_progress_complete_production(self, test_db):
        """Test: Shows complete when all batches produced."""
        # ...

    def test_progress_package_status_counts(self, test_db):
        """Test: Package counts by status are accurate."""
        # ...

    def test_progress_cost_calculations(self, test_db):
        """Test: Actual and planned costs calculated correctly."""
        # ...


class TestGetDashboardSummary:
    """Tests for get_dashboard_summary() function."""

    def test_dashboard_empty(self, test_db):
        """Test: Returns empty list when no events with packages."""
        result = get_dashboard_summary()
        assert result == []

    def test_dashboard_multiple_events(self, test_db):
        """Test: Returns all events with packages."""
        # Setup: 3 events with packages
        result = get_dashboard_summary()
        assert len(result) == 3

    def test_dashboard_sorted_by_date(self, test_db):
        """Test: Events sorted by event_date ascending."""
        # ...

    def test_dashboard_complete_event(self, test_db):
        """Test: Complete events marked is_complete=True."""
        # ...


class TestGetRecipeCostBreakdown:
    """Tests for get_recipe_cost_breakdown() function."""

    def test_cost_breakdown_variance(self, test_db):
        """Test: Variance calculated correctly."""
        # actual=$45, planned=$50 -> variance=-$5, -10%
        breakdown = get_recipe_cost_breakdown(event.id)

        assert breakdown[0]["variance"] == Decimal("-5.00")
        assert breakdown[0]["variance_percent"] == -10.0
```

**Files**: `src/tests/services/test_production_service.py` (ADD)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| N+1 query problem in dashboard | Use efficient aggregation queries |
| Decimal precision in percentages | Round variance_percent to 2 decimals |
| Performance with many events | Consider pagination for large datasets |

---

## Definition of Done Checklist

- [ ] get_production_progress() returns complete progress data
- [ ] get_dashboard_summary() returns all events with packages
- [ ] get_recipe_cost_breakdown() calculates variance correctly
- [ ] Event-level cost comparison works (actual vs planned)
- [ ] Recipe-level cost breakdown works
- [ ] Tests written and passing (>70% coverage)
- [ ] Dashboard query performs within 2 seconds for 10 events
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

- Verify cost calculations use Decimal throughout
- Verify is_complete logic (all packages delivered AND packages > 0)
- Check query efficiency (no N+1 issues)
- Verify variance_percent handles zero planned gracefully

---

## Activity Log

- 2025-12-04T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-04T16:28:39Z – claude – shell_pid=58999 – lane=doing – Started implementation (retroactive recovery)
- 2025-12-04T16:28:47Z – claude – shell_pid=58999 – lane=for_review – Implementation complete, ready for review (retroactive recovery)
