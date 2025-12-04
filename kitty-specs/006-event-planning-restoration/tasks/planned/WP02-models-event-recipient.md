---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
title: "Models Layer - Event & Recipient"
phase: "Phase 1 - Models Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-03"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Models Layer - Event & Recipient

## Objectives & Success Criteria

- Re-enable Event and EventRecipientPackage models that were disabled during Phase 4 refactor
- Remove any Bundle references from event.py
- Verify Recipient model is functional
- Ensure cost calculation chains work correctly

**Success Criteria**:
- `from src.models import Event, EventRecipientPackage, Recipient, Package` works
- Event.get_total_cost() returns correct sum of assignment costs
- EventRecipientPackage.calculate_cost() uses Package.calculate_cost()
- All foreign key relationships work

## Context & Constraints

**Background**: Event and EventRecipientPackage models exist in `src/models/event.py` but are disabled in `__init__.py` because they referenced the removed Bundle model chain.

**Key Documents**:
- `kitty-specs/006-event-planning-restoration/data-model.md` - Entity relationships
- `kitty-specs/006-event-planning-restoration/contracts/event_service.md` - Service interface
- `kitty-specs/006-event-planning-restoration/research.md` - Research findings

**Dependencies**: Requires WP01 complete (Package model must be updated first).

## Subtasks & Detailed Guidance

### Subtask T006 - Review and verify `src/models/event.py` Event model

**Purpose**: Ensure Event model works with current schema and has no Bundle references.

**Steps**:
1. Read `src/models/event.py`
2. Verify Event model has these fields per data-model.md:
   - `id` (Integer, PK)
   - `name` (String(200), required, indexed)
   - `event_date` (Date, required)
   - `year` (Integer, required, indexed)
   - `notes` (Text, optional)
   - Inherited: date_added, last_modified from BaseModel
3. Remove any references to Bundle or obsolete patterns
4. Verify relationship to EventRecipientPackage:
   ```python
   event_recipient_packages = relationship("EventRecipientPackage", back_populates="event", cascade="all, delete-orphan")
   ```

**Files**: `src/models/event.py`

### Subtask T007 - Review and verify EventRecipientPackage model

**Purpose**: Ensure the junction model works with Package (not Bundle).

**Steps**:
1. In `src/models/event.py`, find EventRecipientPackage class
2. Verify fields per data-model.md:
   - `id` (Integer, PK)
   - `event_id` (Integer, FK -> events.id, CASCADE)
   - `recipient_id` (Integer, FK -> recipients.id, RESTRICT)
   - `package_id` (Integer, FK -> packages.id, RESTRICT)
   - `quantity` (Integer, default=1)
   - `notes` (Text, optional)
3. Verify relationships:
   ```python
   event = relationship("Event", back_populates="event_recipient_packages")
   recipient = relationship("Recipient")
   package = relationship("Package")
   ```
4. Remove any Bundle references

**Files**: `src/models/event.py`

### Subtask T008 - Update EventRecipientPackage.calculate_cost()

**Purpose**: Cost calculation must use Package.calculate_cost() and multiply by quantity.

**Steps**:
1. Find or add calculate_cost() method in EventRecipientPackage:
   ```python
   def calculate_cost(self) -> Decimal:
       """Calculate cost of this assignment (package cost * quantity)."""
       package_cost = self.package.calculate_cost() if self.package else Decimal("0")
       return package_cost * self.quantity
   ```
2. Handle edge cases:
   - Package is None
   - Package.calculate_cost() returns None

**Files**: `src/models/event.py`

### Subtask T009 - Verify Event aggregation methods

**Purpose**: Event should have methods to calculate totals across assignments.

**Steps**:
1. Verify or add get_total_cost():
   ```python
   def get_total_cost(self) -> Decimal:
       """Calculate total cost of all assignments for this event."""
       return sum(
           (erp.calculate_cost() for erp in self.event_recipient_packages),
           start=Decimal("0")
       )
   ```
2. Verify or add get_recipient_count():
   ```python
   def get_recipient_count(self) -> int:
       """Count unique recipients with assignments."""
       return len(set(erp.recipient_id for erp in self.event_recipient_packages))
   ```
3. Verify or add get_package_count():
   ```python
   def get_package_count(self) -> int:
       """Count total packages (sum of quantities)."""
       return sum(erp.quantity for erp in self.event_recipient_packages)
   ```

**Files**: `src/models/event.py`

### Subtask T010 - Verify Recipient model is functional

**Purpose**: Recipient model should already be enabled - verify it works.

**Steps**:
1. Read `src/models/recipient.py`
2. Verify fields per data-model.md:
   - `id` (Integer, PK)
   - `name` (String(200), required)
   - `household_name` (String(200), optional)
   - `address` (Text, optional)
   - `notes` (Text, optional)
3. Verify no broken imports or references
4. Check it's enabled in `__init__.py`

**Files**: `src/models/recipient.py`

### Subtask T011 - Update `src/models/__init__.py` to re-enable models

**Purpose**: Enable all event planning models for import.

**Steps**:
1. Open `src/models/__init__.py`
2. Find commented-out imports for Event, EventRecipientPackage
3. Enable/add:
   ```python
   from .event import Event, EventRecipientPackage
   from .package import Package, PackageFinishedGood
   # Recipient should already be enabled
   from .recipient import Recipient
   ```
4. Update `__all__` list to include all models
5. Remove any Bundle or PackageBundle references
6. Test import: `python -c "from src.models import Event, EventRecipientPackage, Package, Recipient"`

**Files**: `src/models/__init__.py`

**Critical**: Import order matters. Ensure no circular import issues.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Use string references in relationships |
| Missing Package model | Requires WP01 complete first |
| Event model has breaking changes | Review carefully before enabling |

## Definition of Done Checklist

- [ ] Event model verified and cleaned of Bundle references
- [ ] EventRecipientPackage model verified with Package relationship
- [ ] EventRecipientPackage.calculate_cost() works correctly
- [ ] Event.get_total_cost(), get_recipient_count(), get_package_count() work
- [ ] Recipient model verified functional
- [ ] All models importable: `from src.models import Event, EventRecipientPackage, Package, PackageFinishedGood, Recipient`
- [ ] No Bundle or PackageBundle references remain
- [ ] `tasks.md` updated with status change

## Review Guidance

- Test that cost chain works: Event -> ERP -> Package -> FinishedGood
- Verify cascade delete behavior on Event deletion
- Check import order doesn't cause circular import errors

## Activity Log

- 2025-12-03 - system - lane=planned - Prompt created.
