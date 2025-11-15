# FinishedGood Service Contract

**Feature**: FinishedUnit Model Refactoring
**Service**: `finished_good_service.py`
**Purpose**: Assembly management and hierarchical composition operations

## Service Interface

### Core Operations

#### `get_finished_good_by_id(finished_good_id: int) -> Optional[FinishedGood]`
**Purpose**: Retrieve a specific FinishedGood assembly by ID
**Parameters**:
- `finished_good_id`: Integer ID of the FinishedGood
**Returns**: FinishedGood instance or None if not found
**Performance**: Must complete in <50ms

#### `get_finished_good_by_slug(slug: str) -> Optional[FinishedGood]`
**Purpose**: Retrieve a specific FinishedGood by slug identifier
**Parameters**:
- `slug`: String slug identifier
**Returns**: FinishedGood instance or None if not found
**Performance**: Must complete in <50ms (indexed lookup)

#### `get_all_finished_goods() -> List[FinishedGood]`
**Purpose**: Retrieve all FinishedGood assemblies
**Returns**: List of all FinishedGood instances
**Performance**: Must complete in <300ms for up to 1000 assemblies

#### `create_finished_good(display_name: str, assembly_type: AssemblyType, components: List[dict], **kwargs) -> FinishedGood`
**Purpose**: Create a new assembly package
**Parameters**:
- `display_name`: Required string name
- `assembly_type`: AssemblyType enum value
- `components`: List of component specifications with quantities
- `**kwargs`: Additional optional fields
**Returns**: Created FinishedGood instance
**Validation**: Must validate component availability and prevent circular references
**Performance**: Must complete in <2s for assemblies with up to 20 components

#### `update_finished_good(finished_good_id: int, **updates) -> FinishedGood`
**Purpose**: Update an existing FinishedGood
**Parameters**:
- `finished_good_id`: ID of FinishedGood to update
- `**updates`: Dictionary of fields to update
**Returns**: Updated FinishedGood instance
**Validation**: Must maintain composition integrity
**Performance**: Must complete in <1s

#### `delete_finished_good(finished_good_id: int) -> bool`
**Purpose**: Delete a FinishedGood assembly
**Parameters**:
- `finished_good_id`: ID of FinishedGood to delete
**Returns**: True if deleted, False if not found
**Constraints**: Must handle cascading composition deletions
**Performance**: Must complete in <1s

### Component Management

#### `add_component(finished_good_id: int, component_type: str, component_id: int, quantity: int) -> bool`
**Purpose**: Add a component to an assembly
**Parameters**:
- `finished_good_id`: ID of the assembly
- `component_type`: "finished_unit" or "finished_good"
- `component_id`: ID of the component to add
- `quantity`: Quantity of the component
**Returns**: True if added successfully
**Validation**: Must prevent circular references and check availability
**Performance**: Must complete in <500ms

#### `remove_component(finished_good_id: int, composition_id: int) -> bool`
**Purpose**: Remove a component from an assembly
**Parameters**:
- `finished_good_id`: ID of the assembly
- `composition_id`: ID of the composition record to remove
**Returns**: True if removed successfully
**Performance**: Must complete in <300ms

#### `update_component_quantity(composition_id: int, new_quantity: int) -> bool`
**Purpose**: Update quantity of a component in an assembly
**Parameters**:
- `composition_id`: ID of the composition record
- `new_quantity`: New quantity value
**Returns**: True if updated successfully
**Validation**: Must be positive integer
**Performance**: Must complete in <200ms

### Hierarchy Operations

#### `get_all_components(finished_good_id: int, flatten: bool = False) -> List[dict]`
**Purpose**: Get complete component hierarchy for an assembly
**Parameters**:
- `finished_good_id`: ID of the assembly
- `flatten`: If True, returns flattened list; if False, maintains hierarchy
**Returns**: List of component information with quantities and relationships
**Performance**: Must complete in <500ms for 5-level hierarchies
**Algorithm**: Uses iterative breadth-first search pattern

#### `calculate_total_cost(finished_good_id: int) -> Decimal`
**Purpose**: Calculate total cost of assembly including all components
**Parameters**:
- `finished_good_id`: ID of the assembly
**Returns**: Total calculated cost
**Performance**: Must complete in <500ms for complex hierarchies
**Integration**: Uses FinishedUnit cost calculations

#### `check_assembly_availability(finished_good_id: int, required_quantity: int = 1) -> dict`
**Purpose**: Check if assembly can be created with available components
**Parameters**:
- `finished_good_id`: ID of the assembly
- `required_quantity`: Number of assemblies needed
**Returns**: Dictionary with availability status and missing components
**Performance**: Must complete in <500ms

#### `validate_no_circular_references(finished_good_id: int, new_component_id: int) -> bool`
**Purpose**: Ensure adding a component won't create circular references
**Parameters**:
- `finished_good_id`: ID of the assembly
- `new_component_id`: ID of component being added (if it's a FinishedGood)
**Returns**: True if safe to add, False if would create cycle
**Algorithm**: Uses visited set tracking in breadth-first traversal
**Performance**: Must complete in <200ms

### Assembly Production

#### `create_assembly_from_inventory(finished_good_id: int, quantity: int) -> bool`
**Purpose**: Create assemblies by consuming available component inventory
**Parameters**:
- `finished_good_id`: ID of assembly to create
- `quantity`: Number of assemblies to create
**Returns**: True if successful
**Side Effects**: Decrements component inventory, increments assembly inventory
**Validation**: Must verify component availability before consumption
**Performance**: Must complete in <1s

#### `disassemble_into_components(finished_good_id: int, quantity: int) -> bool`
**Purpose**: Break down assemblies back into component inventory
**Parameters**:
- `finished_good_id`: ID of assembly to disassemble
- `quantity`: Number of assemblies to break down
**Returns**: True if successful
**Side Effects**: Decrements assembly inventory, increments component inventory
**Performance**: Must complete in <1s

### Query Operations

#### `search_finished_goods(query: str) -> List[FinishedGood]`
**Purpose**: Search assemblies by name or description
**Parameters**:
- `query`: String search term
**Returns**: List of matching FinishedGood instances
**Performance**: Must complete in <300ms

#### `get_assemblies_by_type(assembly_type: AssemblyType) -> List[FinishedGood]`
**Purpose**: Get all assemblies of a specific type
**Parameters**:
- `assembly_type`: AssemblyType enum value
**Returns**: List of FinishedGood instances
**Performance**: Must complete in <200ms

#### `get_assemblies_containing_component(component_type: str, component_id: int) -> List[FinishedGood]`
**Purpose**: Find all assemblies that contain a specific component
**Parameters**:
- `component_type`: "finished_unit" or "finished_good"
- `component_id`: ID of the component
**Returns**: List of FinishedGood instances
**Performance**: Must complete in <400ms

## Error Handling

### Exception Types
- `FinishedGoodNotFoundError`: When assembly doesn't exist
- `CircularReferenceError`: When operation would create circular dependency
- `InsufficientInventoryError`: When components unavailable for assembly
- `InvalidComponentError`: When component doesn't exist or is invalid
- `AssemblyIntegrityError`: When assembly state becomes invalid

### Validation Rules
- Display name required and non-empty
- Assembly type must be valid enum value
- Component quantities must be positive integers
- Circular references prohibited in composition hierarchy
- Component availability must be verified before assembly creation

## Integration Points

### Database Models
- Primary: `FinishedGood`, `Composition`
- Related: `FinishedUnit`, `AssemblyType`

### Service Dependencies
- `finished_unit_service`: For component validation and inventory management
- `composition_service`: For relationship management
- `inventory_service`: For availability checking

### Event Handling
- `finished_good_created`: Fired when new assembly created
- `finished_good_updated`: Fired when assembly modified
- `assembly_produced`: Fired when assemblies created from inventory
- `assembly_disassembled`: Fired when assemblies broken down

## Performance Targets

- **Single assembly operations**: <1s
- **Hierarchy traversal**: <500ms for 5-level depth
- **Circular reference validation**: <200ms
- **Cost calculations**: <500ms for complex assemblies
- **Search operations**: <300ms
- **Memory usage**: <100MB for 1000 assemblies with full hierarchy

## Testing Requirements

### Unit Tests Required
- All CRUD operations with validation
- Hierarchy traversal algorithms
- Circular reference prevention
- Cost calculation accuracy
- Component availability checking
- Assembly production workflows

### Integration Tests Required
- Complex hierarchy creation and modification
- Cross-service inventory management
- Performance benchmarks for large assemblies
- Error handling in failure scenarios