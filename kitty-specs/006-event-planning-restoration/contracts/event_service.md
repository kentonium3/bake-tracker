# Event Service Contract

**Feature**: 006-event-planning-restoration
**Service**: `event_service.py`
**Purpose**: Event management, recipient assignments, and aggregated planning calculations

## Service Interface

### Core Event Operations

#### `get_event_by_id(event_id: int) -> Optional[Event]`
**Purpose**: Retrieve a specific event by ID
**Parameters**:
- `event_id`: Integer ID of the event
**Returns**: Event instance or None if not found
**Performance**: Must complete in <50ms

#### `get_event_by_name(name: str) -> Optional[Event]`
**Purpose**: Retrieve an event by name
**Parameters**:
- `name`: String name of the event
**Returns**: Event instance or None if not found
**Performance**: Must complete in <50ms (indexed lookup)

#### `get_all_events() -> List[Event]`
**Purpose**: Retrieve all events
**Returns**: List of all Event instances, ordered by event_date descending
**Performance**: Must complete in <300ms for up to 100 events

#### `get_events_by_year(year: int) -> List[Event]`
**Purpose**: Retrieve events for a specific year (FR-020)
**Parameters**:
- `year`: Integer year to filter by
**Returns**: List of Event instances for that year
**Performance**: Must complete in <200ms (indexed lookup)

#### `get_available_years() -> List[int]`
**Purpose**: Get list of years that have events
**Returns**: List of unique years, sorted descending
**Use Case**: Populating year filter dropdown
**Performance**: Must complete in <100ms

#### `create_event(name: str, event_date: date, year: int, notes: str = None) -> Event`
**Purpose**: Create a new event (FR-019)
**Parameters**:
- `name`: Required string name (max 200 chars)
- `event_date`: Required date of the event
- `year`: Required integer year
- `notes`: Optional notes text
**Returns**: Created Event instance
**Validation**: Name required, year must be positive
**Performance**: Must complete in <500ms

#### `update_event(event_id: int, **updates) -> Event`
**Purpose**: Update an existing event (FR-021)
**Parameters**:
- `event_id`: ID of event to update
- `**updates`: Dictionary of fields to update
**Returns**: Updated Event instance
**Performance**: Must complete in <500ms

#### `delete_event(event_id: int, cascade_assignments: bool = False) -> bool`
**Purpose**: Delete an event (FR-022)
**Parameters**:
- `event_id`: ID of event to delete
- `cascade_assignments`: If True, delete all assignments; if False, fail if assignments exist
**Returns**: True if deleted, False if not found
**Behavior**:
- If `cascade_assignments=False` and assignments exist, raises `EventHasAssignmentsError`
- If `cascade_assignments=True`, deletes all EventRecipientPackage records first
**Performance**: Must complete in <1s

### Assignment Operations

#### `assign_package_to_recipient(event_id: int, recipient_id: int, package_id: int, quantity: int = 1, notes: str = None) -> EventRecipientPackage`
**Purpose**: Assign a package to a recipient for an event (FR-024)
**Parameters**:
- `event_id`: ID of the event
- `recipient_id`: ID of the recipient
- `package_id`: ID of the package to assign
- `quantity`: Number of packages (default 1)
- `notes`: Optional notes for this assignment
**Returns**: Created EventRecipientPackage instance
**Validation**: All IDs must reference existing records, quantity must be positive
**Performance**: Must complete in <300ms

#### `update_assignment(assignment_id: int, **updates) -> EventRecipientPackage`
**Purpose**: Update an assignment (change package, quantity, notes)
**Parameters**:
- `assignment_id`: ID of the assignment to update
- `**updates`: Fields to update (package_id, quantity, notes)
**Returns**: Updated EventRecipientPackage instance
**Performance**: Must complete in <300ms

#### `remove_assignment(assignment_id: int) -> bool`
**Purpose**: Remove a recipient-package assignment
**Parameters**:
- `assignment_id`: ID of the assignment to remove
**Returns**: True if removed successfully
**Performance**: Must complete in <200ms

#### `get_event_assignments(event_id: int) -> List[EventRecipientPackage]`
**Purpose**: Get all assignments for an event
**Parameters**:
- `event_id`: ID of the event
**Returns**: List of EventRecipientPackage instances with loaded relationships
**Performance**: Must complete in <500ms for up to 100 assignments

#### `get_recipient_assignments_for_event(event_id: int, recipient_id: int) -> List[EventRecipientPackage]`
**Purpose**: Get assignments for a specific recipient in an event
**Parameters**:
- `event_id`: ID of the event
- `recipient_id`: ID of the recipient
**Returns**: List of EventRecipientPackage instances
**Performance**: Must complete in <200ms

### Event Summary Operations (FR-027)

#### `get_event_total_cost(event_id: int) -> Decimal`
**Purpose**: Calculate total cost of all assignments for an event
**Parameters**:
- `event_id`: ID of the event
**Returns**: Total cost (sum of package_cost * quantity for all assignments)
**Integration**: Uses PackageService.calculate_package_cost() which chains to FIFO costs (FR-028)
**Performance**: Must complete in <1s for 50 assignments

#### `get_event_recipient_count(event_id: int) -> int`
**Purpose**: Count unique recipients with assignments
**Parameters**:
- `event_id`: ID of the event
**Returns**: Count of unique recipients
**Performance**: Must complete in <100ms

#### `get_event_package_count(event_id: int) -> int`
**Purpose**: Count total packages assigned (sum of quantities)
**Parameters**:
- `event_id`: ID of the event
**Returns**: Total package count
**Performance**: Must complete in <100ms

#### `get_event_summary(event_id: int) -> dict`
**Purpose**: Get complete event summary for Summary tab
**Parameters**:
- `event_id`: ID of the event
**Returns**: Dict with:
  - `total_cost`: Decimal
  - `recipient_count`: int
  - `package_count`: int
  - `assignment_count`: int
  - `cost_by_recipient`: List of dicts with recipient_name and cost
**Performance**: Must complete in <2s for 50 assignments (SC-004)

### Recipe Needs Calculation (FR-025)

#### `get_recipe_needs(event_id: int) -> List[dict]`
**Purpose**: Calculate recipe batch counts needed for event
**Parameters**:
- `event_id`: ID of the event
**Returns**: List of dicts with:
  - `recipe_id`: int
  - `recipe_name`: str
  - `total_units_needed`: int
  - `batches_needed`: int (rounded up)
  - `items_per_batch`: int
**Calculation**:
1. Traverse all assignments -> packages -> finished_goods -> compositions -> finished_units
2. Aggregate by recipe_id
3. Calculate batches = ceil(units_needed / items_per_batch)
**Performance**: Must complete in <2s for 50 assignments (SC-004)

### Shopping List Calculation (FR-026)

#### `get_shopping_list(event_id: int) -> List[dict]`
**Purpose**: Calculate ingredients needed minus pantry inventory
**Parameters**:
- `event_id`: ID of the event
**Returns**: List of dicts with:
  - `ingredient_id`: int
  - `ingredient_name`: str
  - `unit`: str
  - `quantity_needed`: Decimal
  - `quantity_on_hand`: Decimal
  - `shortfall`: Decimal (max of 0, needed - on_hand)
**Integration**:
- Uses recipe_needs calculation for required amounts
- Uses PantryService for on-hand inventory (FR-029)
**Performance**: Must complete in <2s for 50 assignments (SC-004)

### Query Operations

#### `search_events(query: str) -> List[Event]`
**Purpose**: Search events by name
**Parameters**:
- `query`: String search term
**Returns**: List of matching Event instances
**Performance**: Must complete in <300ms

#### `get_events_with_recipient(recipient_id: int) -> List[Event]`
**Purpose**: Find all events where a recipient has assignments
**Parameters**:
- `recipient_id`: ID of the recipient
**Returns**: List of Event instances
**Use Case**: Recipient deletion dependency checking
**Performance**: Must complete in <300ms

## Error Handling

### Exception Types
- `EventNotFoundError`: When event doesn't exist
- `EventHasAssignmentsError`: When deletion blocked by assignments
- `RecipientNotFoundError`: When recipient doesn't exist
- `PackageNotFoundError`: When package doesn't exist
- `DuplicateAssignmentError`: When same recipient-package already assigned

### Validation Rules
- Name required, max 200 characters
- Year must be positive integer
- event_date required, must be valid date
- Assignment quantities must be positive integers

## Integration Points

### Database Models
- Primary: `Event`, `EventRecipientPackage`
- Related: `Recipient`, `Package`

### Service Dependencies
- `package_service`: For package validation and cost calculation
- `recipient_service`: For recipient validation
- `pantry_service`: For on-hand inventory (shopping list)
- `recipe_service`: For recipe data (batch sizes)
- `finished_good_service`: For composition traversal
- `finished_unit_service`: For recipe relationships

### Cost Chain (FR-028)
```
Event.get_total_cost()
    -> EventRecipientPackage.calculate_cost()
        -> Package.calculate_cost() * quantity
            -> FinishedGood.total_cost * quantity
                -> RecipeService.calculate_actual_cost() (FIFO)
```

## Performance Targets

- **Single event operations**: <500ms
- **Cost calculations**: <1s for 50 assignments
- **Recipe needs/shopping list**: <2s for 50 assignments (SC-004)
- **Summary generation**: <2s for 50 assignments (SC-004)
- **Search operations**: <300ms

## Testing Requirements

### Unit Tests Required
- All CRUD operations with validation
- Assignment management
- Cost calculation accuracy with FIFO chain (SC-002)
- Recipe needs aggregation
- Shopping list shortfall calculation (SC-003)
- Year filtering

### Integration Tests Required
- Full cost chain through Package to Recipe
- Recipe needs across multiple packages with shared recipes
- Shopping list with pantry inventory integration
- Cascade delete behavior
