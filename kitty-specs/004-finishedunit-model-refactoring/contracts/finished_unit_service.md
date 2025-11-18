# FinishedUnit Service Contract

**Feature**: FinishedUnit Model Refactoring
**Service**: `finished_unit_service.py`
**Purpose**: CRUD operations and business logic for individual consumable items

## Service Interface

### Core Operations

#### `get_finished_unit_count() -> int`
**Purpose**: Get total count of all FinishedUnits
**Returns**: Integer count of FinishedUnit records
**Performance**: Must complete in <100ms

#### `get_finished_unit_by_id(finished_unit_id: int) -> Optional[FinishedUnit]`
**Purpose**: Retrieve a specific FinishedUnit by ID
**Parameters**:
- `finished_unit_id`: Integer ID of the FinishedUnit
**Returns**: FinishedUnit instance or None if not found
**Performance**: Must complete in <50ms

#### `get_finished_unit_by_slug(slug: str) -> Optional[FinishedUnit]`
**Purpose**: Retrieve a specific FinishedUnit by slug identifier
**Parameters**:
- `slug`: String slug identifier
**Returns**: FinishedUnit instance or None if not found
**Performance**: Must complete in <50ms (indexed lookup)

#### `get_all_finished_units() -> List[FinishedUnit]`
**Purpose**: Retrieve all FinishedUnits
**Returns**: List of all FinishedUnit instances
**Performance**: Must complete in <200ms for up to 10k records

#### `create_finished_unit(display_name: str, recipe_id: Optional[int] = None, unit_cost: Decimal = 0, **kwargs) -> FinishedUnit`
**Purpose**: Create a new FinishedUnit
**Parameters**:
- `display_name`: Required string name
- `recipe_id`: Optional Recipe ID reference
- `unit_cost`: Optional unit cost (default 0)
- `**kwargs`: Additional optional fields
**Returns**: Created FinishedUnit instance
**Validation**: Must validate slug uniqueness, non-negative costs
**Performance**: Must complete in <500ms

#### `update_finished_unit(finished_unit_id: int, **updates) -> FinishedUnit`
**Purpose**: Update an existing FinishedUnit
**Parameters**:
- `finished_unit_id`: ID of FinishedUnit to update
- `**updates`: Dictionary of fields to update
**Returns**: Updated FinishedUnit instance
**Validation**: Must maintain data integrity constraints
**Performance**: Must complete in <500ms

#### `delete_finished_unit(finished_unit_id: int) -> bool`
**Purpose**: Delete a FinishedUnit
**Parameters**:
- `finished_unit_id`: ID of FinishedUnit to delete
**Returns**: True if deleted, False if not found
**Constraints**: Must check for composition references before deletion
**Performance**: Must complete in <500ms

### Inventory Management

#### `update_inventory(finished_unit_id: int, quantity_change: int) -> FinishedUnit`
**Purpose**: Adjust inventory count for a FinishedUnit
**Parameters**:
- `finished_unit_id`: ID of FinishedUnit
- `quantity_change`: Positive or negative integer change
**Returns**: Updated FinishedUnit instance
**Validation**: Must prevent negative inventory
**Performance**: Must complete in <200ms

#### `check_availability(finished_unit_id: int, required_quantity: int) -> bool`
**Purpose**: Check if sufficient inventory exists
**Parameters**:
- `finished_unit_id`: ID of FinishedUnit to check
- `required_quantity`: Required quantity
**Returns**: True if available, False otherwise
**Performance**: Must complete in <50ms

### Cost Calculation

#### `calculate_unit_cost(finished_unit_id: int) -> Decimal`
**Purpose**: Calculate current unit cost based on recipe and pantry consumption
**Parameters**:
- `finished_unit_id`: ID of FinishedUnit
**Returns**: Calculated unit cost
**Integration**: Uses existing FIFO calculation patterns
**Performance**: Must complete in <200ms

### Query Operations

#### `search_finished_units(query: str) -> List[FinishedUnit]`
**Purpose**: Search FinishedUnits by display name or description
**Parameters**:
- `query`: String search term
**Returns**: List of matching FinishedUnit instances
**Performance**: Must complete in <300ms

#### `get_units_by_recipe(recipe_id: int) -> List[FinishedUnit]`
**Purpose**: Get all FinishedUnits associated with a specific recipe
**Parameters**:
- `recipe_id`: Recipe ID to filter by
**Returns**: List of FinishedUnit instances
**Performance**: Must complete in <200ms

## Error Handling

### Exception Types
- `FinishedUnitNotFoundError`: When unit doesn't exist
- `InvalidInventoryError`: When inventory operations would create invalid state
- `DuplicateSlugError`: When slug uniqueness is violated
- `ReferencedUnitError`: When attempting to delete unit used in compositions

### Validation Rules
- Display name required and non-empty
- Slug must be unique across all FinishedUnits
- Unit cost must be non-negative
- Inventory count must be non-negative
- Recipe ID must reference valid Recipe if provided

## Integration Points

### Database Models
- Primary: `FinishedUnit` model
- Related: `Recipe`, `PantryConsumption`, `ProductionRun`, `Composition`

### Service Dependencies
- `recipe_service`: For recipe validation and cost calculation
- `pantry_service`: For FIFO cost calculations
- `composition_service`: For component usage validation

### Event Handling
- `finished_unit_created`: Fired when new unit created
- `finished_unit_updated`: Fired when unit modified
- `inventory_changed`: Fired when inventory count changes

## Migration Compatibility

### Legacy API Support
During transition period, service must support both:
- New FinishedUnit-based operations
- Legacy FinishedGood API calls (with deprecation warnings)

### Data Migration Integration
- `migrate_from_finished_good(finished_good_data: dict) -> FinishedUnit`: Convert legacy data
- `validate_migration_data() -> bool`: Verify migration integrity
- `rollback_migration() -> bool`: Reverse migration if needed

## Testing Requirements

### Unit Tests Required
- All CRUD operations with valid and invalid inputs
- Inventory management edge cases
- Cost calculation scenarios
- Search and filter operations
- Error handling and validation

### Integration Tests Required
- Database transaction handling
- Service dependency interactions
- Migration workflow validation
- Performance benchmarks for all operations

## Performance Targets

- **Single record operations**: <100ms
- **Bulk operations**: <500ms for up to 1000 records
- **Search operations**: <300ms for full-text search
- **Cost calculations**: <200ms including FIFO computation
- **Memory usage**: <50MB for 10k FinishedUnit dataset