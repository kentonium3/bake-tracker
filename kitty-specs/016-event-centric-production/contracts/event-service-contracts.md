# Service Contracts: EventService Extensions

**Feature**: 016-event-centric-production
**Date**: 2025-12-10

This document defines the service method contracts for Feature 016.

---

## Target Management Methods

### set_production_target

```python
def set_production_target(
    self,
    event_id: int,
    recipe_id: int,
    target_batches: int,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> EventProductionTarget:
    """
    Create or update a production target for a recipe in an event.

    Args:
        event_id: ID of the event
        recipe_id: ID of the recipe
        target_batches: Number of batches to produce (must be > 0)
        notes: Optional planning notes
        session: Optional database session

    Returns:
        The created or updated EventProductionTarget

    Raises:
        ValueError: If target_batches <= 0
        NotFoundError: If event_id or recipe_id not found

    Behavior:
        - If target exists for (event_id, recipe_id), updates it
        - If no target exists, creates new one
        - Validates target_batches > 0 before insert
    """
```

### set_assembly_target

```python
def set_assembly_target(
    self,
    event_id: int,
    finished_good_id: int,
    target_quantity: int,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> EventAssemblyTarget:
    """
    Create or update an assembly target for a finished good in an event.

    Args:
        event_id: ID of the event
        finished_good_id: ID of the finished good
        target_quantity: Number of units to assemble (must be > 0)
        notes: Optional planning notes
        session: Optional database session

    Returns:
        The created or updated EventAssemblyTarget

    Raises:
        ValueError: If target_quantity <= 0
        NotFoundError: If event_id or finished_good_id not found

    Behavior:
        - If target exists for (event_id, finished_good_id), updates it
        - If no target exists, creates new one
        - Validates target_quantity > 0 before insert
    """
```

### get_production_targets

```python
def get_production_targets(
    self,
    event_id: int,
    session: Optional[Session] = None
) -> List[EventProductionTarget]:
    """
    Get all production targets for an event.

    Args:
        event_id: ID of the event
        session: Optional database session

    Returns:
        List of EventProductionTarget objects (may be empty)
        Eagerly loads recipe relationship for display
    """
```

### get_assembly_targets

```python
def get_assembly_targets(
    self,
    event_id: int,
    session: Optional[Session] = None
) -> List[EventAssemblyTarget]:
    """
    Get all assembly targets for an event.

    Args:
        event_id: ID of the event
        session: Optional database session

    Returns:
        List of EventAssemblyTarget objects (may be empty)
        Eagerly loads finished_good relationship for display
    """
```

### delete_production_target

```python
def delete_production_target(
    self,
    event_id: int,
    recipe_id: int,
    session: Optional[Session] = None
) -> bool:
    """
    Remove a production target.

    Args:
        event_id: ID of the event
        recipe_id: ID of the recipe
        session: Optional database session

    Returns:
        True if target was deleted, False if not found
    """
```

### delete_assembly_target

```python
def delete_assembly_target(
    self,
    event_id: int,
    finished_good_id: int,
    session: Optional[Session] = None
) -> bool:
    """
    Remove an assembly target.

    Args:
        event_id: ID of the event
        finished_good_id: ID of the finished good
        session: Optional database session

    Returns:
        True if target was deleted, False if not found
    """
```

---

## Progress Tracking Methods

### get_production_progress

```python
def get_production_progress(
    self,
    event_id: int,
    session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Get production progress for an event.

    Args:
        event_id: ID of the event
        session: Optional database session

    Returns:
        List of progress records, one per production target:
        [
            {
                'recipe': Recipe,           # Recipe object
                'recipe_name': str,         # Recipe display name
                'target_batches': int,      # From EventProductionTarget
                'produced_batches': int,    # Sum of ProductionRun.num_batches where event_id matches
                'produced_yield': int,      # Sum of ProductionRun.actual_yield
                'progress_pct': float,      # (produced_batches / target_batches) * 100
                'is_complete': bool         # produced_batches >= target_batches
            },
            ...
        ]

    Behavior:
        - Only counts ProductionRun records where event_id matches
        - Returns empty list if no targets set
        - progress_pct can exceed 100 for over-production
    """
```

### get_assembly_progress

```python
def get_assembly_progress(
    self,
    event_id: int,
    session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Get assembly progress for an event.

    Args:
        event_id: ID of the event
        session: Optional database session

    Returns:
        List of progress records, one per assembly target:
        [
            {
                'finished_good': FinishedGood,  # FinishedGood object
                'finished_good_name': str,      # FinishedGood display name
                'target_quantity': int,         # From EventAssemblyTarget
                'assembled_quantity': int,      # Sum of AssemblyRun.quantity_assembled where event_id matches
                'progress_pct': float,          # (assembled_quantity / target_quantity) * 100
                'is_complete': bool             # assembled_quantity >= target_quantity
            },
            ...
        ]

    Behavior:
        - Only counts AssemblyRun records where event_id matches
        - Returns empty list if no targets set
        - progress_pct can exceed 100 for over-production
    """
```

### get_event_overall_progress

```python
def get_event_overall_progress(
    self,
    event_id: int,
    session: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Get overall event progress summary.

    Args:
        event_id: ID of the event
        session: Optional database session

    Returns:
        {
            'production_targets_count': int,    # Total production targets
            'production_complete_count': int,   # Targets at >= 100%
            'production_complete': bool,        # All production targets complete
            'assembly_targets_count': int,      # Total assembly targets
            'assembly_complete_count': int,     # Targets at >= 100%
            'assembly_complete': bool,          # All assembly targets complete
            'packages_pending': int,            # Count with status='pending'
            'packages_ready': int,              # Count with status='ready'
            'packages_delivered': int,          # Count with status='delivered'
            'packages_total': int               # Total packages for event
        }

    Behavior:
        - production_complete is True only if targets exist AND all are complete
        - assembly_complete is True only if targets exist AND all are complete
        - If no targets set, corresponding _complete is True (nothing to do)
    """
```

---

## Fulfillment Status Methods

### update_fulfillment_status

```python
def update_fulfillment_status(
    self,
    event_recipient_package_id: int,
    new_status: FulfillmentStatus,
    session: Optional[Session] = None
) -> EventRecipientPackage:
    """
    Update package fulfillment status with sequential workflow enforcement.

    Args:
        event_recipient_package_id: ID of the EventRecipientPackage
        new_status: New FulfillmentStatus value
        session: Optional database session

    Returns:
        Updated EventRecipientPackage

    Raises:
        NotFoundError: If package not found
        ValueError: If transition is invalid

    Valid Transitions:
        pending -> ready
        ready -> delivered
        delivered -> (none, terminal state)

    Error Message Format:
        "Invalid transition: {current} -> {new}. Allowed: {valid_list}"
    """
```

### get_packages_by_status

```python
def get_packages_by_status(
    self,
    event_id: int,
    status: Optional[FulfillmentStatus] = None,
    session: Optional[Session] = None
) -> List[EventRecipientPackage]:
    """
    Get packages filtered by fulfillment status.

    Args:
        event_id: ID of the event
        status: Optional status filter (None returns all)
        session: Optional database session

    Returns:
        List of EventRecipientPackage objects
        Eagerly loads recipient and package relationships
    """
```

---

## Modified Service Method Contracts

### BatchProductionService.record_batch_production

```python
def record_batch_production(
    self,
    recipe_id: int,
    num_batches: int,
    actual_yield: int,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
    event_id: Optional[int] = None  # NEW PARAMETER
) -> ProductionRun:
    """
    Record batch production, optionally linked to an event.

    Args:
        recipe_id: ID of the recipe
        num_batches: Number of batches produced
        actual_yield: Actual yield count
        notes: Optional production notes
        session: Optional database session
        event_id: Optional event this production is for (NEW)

    Returns:
        Created ProductionRun with event_id set if provided

    Behavior:
        - If event_id provided, validates event exists
        - Sets ProductionRun.event_id = event_id (or None)
        - Production counts toward event progress when event_id is set
    """
```

### AssemblyService.record_assembly

```python
def record_assembly(
    self,
    finished_good_id: int,
    quantity: int,
    *,
    event_id: Optional[int] = None,  # NEW PARAMETER
    assembled_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Record assembly, optionally linked to an event.

    Args:
        finished_good_id: ID of the finished good
        quantity: Number of units assembled
        event_id: Optional event this assembly is for (NEW)
        assembled_at: Optional assembly timestamp
        notes: Optional assembly notes
        session: Optional database session

    Returns:
        Dict with assembly_run and consumption details

    Behavior:
        - If event_id provided, validates event exists
        - Sets AssemblyRun.event_id = event_id (or None)
        - Assembly counts toward event progress when event_id is set
    """
```
