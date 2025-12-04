# Recipient Service Contract

**Feature**: 006-event-planning-restoration
**Service**: `recipient_service.py`
**Purpose**: Recipient management for gift planning

## Architecture Context

The Recipient model is already enabled in `__init__.py` (E012). This service may already exist
and be functional. Contract defines expected interface for integration with event planning.

## Service Interface

### Core Operations

#### `get_recipient_by_id(recipient_id: int) -> Optional[Recipient]`
**Purpose**: Retrieve a specific recipient by ID
**Parameters**:
- `recipient_id`: Integer ID of the recipient
**Returns**: Recipient instance or None if not found
**Performance**: Must complete in <50ms

#### `get_recipient_by_name(name: str) -> Optional[Recipient]`
**Purpose**: Retrieve a recipient by name
**Parameters**:
- `name`: String name of the recipient
**Returns**: Recipient instance or None if not found
**Note**: Names may not be unique; returns first match
**Performance**: Must complete in <50ms

#### `get_all_recipients() -> List[Recipient]`
**Purpose**: Retrieve all recipients
**Returns**: List of all Recipient instances, ordered by name
**Performance**: Must complete in <300ms for up to 500 recipients

#### `create_recipient(name: str, household_name: str = None, address: str = None, notes: str = None) -> Recipient`
**Purpose**: Create a new recipient (FR-016)
**Parameters**:
- `name`: Required string name (max 200 chars)
- `household_name`: Optional household name
- `address`: Optional address text
- `notes`: Optional notes text
**Returns**: Created Recipient instance
**Validation**: Name required and non-empty
**Performance**: Must complete in <500ms

#### `update_recipient(recipient_id: int, **updates) -> Recipient`
**Purpose**: Update an existing recipient (FR-017)
**Parameters**:
- `recipient_id`: ID of recipient to update
- `**updates`: Dictionary of fields to update
**Returns**: Updated Recipient instance
**Performance**: Must complete in <500ms

#### `delete_recipient(recipient_id: int, force: bool = False) -> bool`
**Purpose**: Delete a recipient (FR-018)
**Parameters**:
- `recipient_id`: ID of recipient to delete
- `force`: If True, delete even if has event assignments (with confirmation assumed)
**Returns**: True if deleted, False if not found
**Behavior**:
- If `force=False` and has event assignments, raises `RecipientHasAssignmentsError`
- If `force=True`, deletes all EventRecipientPackage records first
**Performance**: Must complete in <1s

### Query Operations

#### `search_recipients(query: str) -> List[Recipient]`
**Purpose**: Search recipients by name or household name
**Parameters**:
- `query`: String search term
**Returns**: List of matching Recipient instances
**Performance**: Must complete in <300ms

#### `get_recipients_by_household(household_name: str) -> List[Recipient]`
**Purpose**: Find all recipients in a household
**Parameters**:
- `household_name`: Name of the household
**Returns**: List of Recipient instances
**Performance**: Must complete in <200ms

### Dependency Checking

#### `check_recipient_has_assignments(recipient_id: int) -> bool`
**Purpose**: Check if recipient has any event assignments
**Parameters**:
- `recipient_id`: ID of the recipient
**Returns**: True if has assignments, False otherwise
**Use Case**: Deletion confirmation (FR-018)
**Performance**: Must complete in <100ms

#### `get_recipient_assignment_count(recipient_id: int) -> int`
**Purpose**: Count total assignments across all events
**Parameters**:
- `recipient_id`: ID of the recipient
**Returns**: Total number of assignments
**Use Case**: Displaying in deletion confirmation dialog
**Performance**: Must complete in <100ms

#### `get_recipient_events(recipient_id: int) -> List[Event]`
**Purpose**: Get all events where recipient has assignments
**Parameters**:
- `recipient_id`: ID of the recipient
**Returns**: List of Event instances
**Performance**: Must complete in <300ms

## Error Handling

### Exception Types
- `RecipientNotFoundError`: When recipient doesn't exist
- `RecipientHasAssignmentsError`: When deletion blocked without force flag
- `DuplicateRecipientError`: When creating duplicate (if uniqueness enforced)

### Validation Rules
- Name required, max 200 characters
- Household name optional, max 200 characters
- Address and notes optional, text length reasonable for UI display

## Integration Points

### Database Models
- Primary: `Recipient`
- Related: `EventRecipientPackage`, `Event`

### Service Dependencies
- `event_service`: For checking event assignments

## Performance Targets

- **Single recipient operations**: <500ms
- **Dependency checks**: <100ms
- **Search operations**: <300ms
- **Bulk operations**: <1s

## Testing Requirements

### Unit Tests Required
- All CRUD operations with validation
- Search functionality
- Dependency checking for deletion
- Force delete behavior

### Integration Tests Required
- Deletion with event assignments
- Search across households
