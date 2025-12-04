# Package Service Contract

**Feature**: 006-event-planning-restoration
**Service**: `package_service.py`
**Purpose**: Package management and FinishedGood composition for gift planning

## Architecture Context

Based on research decision D1, Package directly references FinishedGood assemblies.
The Bundle concept is eliminated - FinishedGood assemblies serve this role.

## Service Interface

### Core Operations

#### `get_package_by_id(package_id: int) -> Optional[Package]`
**Purpose**: Retrieve a specific package by ID
**Parameters**:
- `package_id`: Integer ID of the package
**Returns**: Package instance or None if not found
**Performance**: Must complete in <50ms

#### `get_package_by_name(name: str) -> Optional[Package]`
**Purpose**: Retrieve a package by name
**Parameters**:
- `name`: String name of the package
**Returns**: Package instance or None if not found
**Performance**: Must complete in <50ms (indexed lookup)

#### `get_all_packages(include_templates: bool = True) -> List[Package]`
**Purpose**: Retrieve all packages
**Parameters**:
- `include_templates`: If False, exclude template packages
**Returns**: List of all Package instances
**Performance**: Must complete in <300ms for up to 500 packages

#### `get_template_packages() -> List[Package]`
**Purpose**: Retrieve packages marked as templates
**Returns**: List of template Package instances
**Performance**: Must complete in <200ms

#### `create_package(name: str, is_template: bool = False, description: str = None, **kwargs) -> Package`
**Purpose**: Create a new package
**Parameters**:
- `name`: Required string name (max 200 chars)
- `is_template`: Whether this is a reusable template
- `description`: Optional description text
- `**kwargs`: Additional optional fields (notes)
**Returns**: Created Package instance
**Validation**: Name required and non-empty
**Performance**: Must complete in <500ms

#### `update_package(package_id: int, **updates) -> Package`
**Purpose**: Update an existing package
**Parameters**:
- `package_id`: ID of package to update
- `**updates`: Dictionary of fields to update
**Returns**: Updated Package instance
**Performance**: Must complete in <500ms

#### `delete_package(package_id: int) -> bool`
**Purpose**: Delete a package
**Parameters**:
- `package_id`: ID of package to delete
**Returns**: True if deleted, False if not found
**Constraints**: Must check for event assignment dependencies (FR-015)
**Raises**: `PackageInUseError` if assigned to events
**Performance**: Must complete in <500ms

### Content Management

#### `add_finished_good_to_package(package_id: int, finished_good_id: int, quantity: int = 1) -> PackageFinishedGood`
**Purpose**: Add a FinishedGood assembly to a package
**Parameters**:
- `package_id`: ID of the package
- `finished_good_id`: ID of the FinishedGood to add
- `quantity`: Number of this assembly in the package (default 1)
**Returns**: Created PackageFinishedGood junction record
**Validation**:
- Quantity must be positive integer
- FinishedGood must exist
**Performance**: Must complete in <300ms

#### `remove_finished_good_from_package(package_id: int, finished_good_id: int) -> bool`
**Purpose**: Remove a FinishedGood from a package
**Parameters**:
- `package_id`: ID of the package
- `finished_good_id`: ID of the FinishedGood to remove
**Returns**: True if removed successfully
**Performance**: Must complete in <200ms

#### `update_finished_good_quantity(package_id: int, finished_good_id: int, new_quantity: int) -> bool`
**Purpose**: Update quantity of a FinishedGood in a package
**Parameters**:
- `package_id`: ID of the package
- `finished_good_id`: ID of the FinishedGood
- `new_quantity`: New quantity value
**Returns**: True if updated successfully
**Validation**: Quantity must be positive integer
**Performance**: Must complete in <200ms

#### `get_package_contents(package_id: int) -> List[dict]`
**Purpose**: Get all FinishedGoods in a package with quantities
**Parameters**:
- `package_id`: ID of the package
**Returns**: List of dicts with finished_good, quantity, item_cost, line_total
**Performance**: Must complete in <300ms

### Cost Calculation

#### `calculate_package_cost(package_id: int) -> Decimal`
**Purpose**: Calculate total cost of package from FinishedGood costs (FR-014)
**Parameters**:
- `package_id`: ID of the package
**Returns**: Total calculated cost
**Calculation**: Sum of (FinishedGood.total_cost * quantity) for all items
**Integration**: Uses FinishedGood.calculate_component_cost() which chains to Recipe FIFO costs (FR-028)
**Performance**: Must complete in <500ms

#### `get_package_cost_breakdown(package_id: int) -> dict`
**Purpose**: Get itemized cost breakdown for a package
**Parameters**:
- `package_id`: ID of the package
**Returns**: Dict with items (list of line items), subtotals, and total
**Performance**: Must complete in <500ms

### Query Operations

#### `search_packages(query: str) -> List[Package]`
**Purpose**: Search packages by name or description
**Parameters**:
- `query`: String search term
**Returns**: List of matching Package instances
**Performance**: Must complete in <300ms

#### `get_packages_containing_finished_good(finished_good_id: int) -> List[Package]`
**Purpose**: Find all packages containing a specific FinishedGood
**Parameters**:
- `finished_good_id`: ID of the FinishedGood
**Returns**: List of Package instances
**Use Case**: Dependency checking before FinishedGood deletion
**Performance**: Must complete in <300ms

#### `check_package_has_event_assignments(package_id: int) -> bool`
**Purpose**: Check if package is assigned to any events
**Parameters**:
- `package_id`: ID of the package
**Returns**: True if has assignments, False otherwise
**Use Case**: Deletion prevention (FR-015)
**Performance**: Must complete in <100ms

### Duplication

#### `duplicate_package(package_id: int, new_name: str) -> Package`
**Purpose**: Create a copy of a package with new name
**Parameters**:
- `package_id`: ID of package to copy
- `new_name`: Name for the new package
**Returns**: New Package instance with copied contents
**Use Case**: Creating variations from templates
**Performance**: Must complete in <1s

## Error Handling

### Exception Types
- `PackageNotFoundError`: When package doesn't exist
- `PackageInUseError`: When deletion blocked by event assignments
- `InvalidFinishedGoodError`: When FinishedGood doesn't exist
- `DuplicatePackageNameError`: When name already exists

### Validation Rules
- Name required, max 200 characters
- Quantity must be positive integer
- FinishedGood must exist before adding to package
- Cannot delete package with event assignments

## Integration Points

### Database Models
- Primary: `Package`, `PackageFinishedGood`
- Related: `FinishedGood`, `EventRecipientPackage`

### Service Dependencies
- `finished_good_service`: For FinishedGood validation and cost data
- `event_service`: For assignment dependency checking

### Cost Chain (FR-028)
```
FinishedGood.calculate_component_cost()
    -> Composition costs
        -> FinishedUnit.unit_cost
            -> RecipeService.calculate_actual_cost() (FIFO)
```

## Performance Targets

- **Single package operations**: <500ms
- **Cost calculations**: <500ms
- **Search operations**: <300ms
- **Dependency checks**: <100ms

## Testing Requirements

### Unit Tests Required
- All CRUD operations with validation
- Cost calculation accuracy with FIFO chain
- Dependency checking for deletion
- Quantity update validation

### Integration Tests Required
- Cost chain through FinishedGood to Recipe
- Event assignment blocking deletion
- Template duplication workflow
