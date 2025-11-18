# Composition Service Contract

**Feature**: FinishedUnit Model Refactoring
**Service**: `composition_service.py`
**Purpose**: Junction table operations and relationship management for assembly components

## Service Interface

### Core Operations

#### `create_composition(assembly_id: int, component_type: str, component_id: int, quantity: int, **kwargs) -> Composition`
**Purpose**: Create a new composition relationship
**Parameters**:
- `assembly_id`: ID of the FinishedGood assembly
- `component_type`: "finished_unit" or "finished_good"
- `component_id`: ID of the component
- `quantity`: Number of this component in the assembly
- `**kwargs`: Optional fields (notes, sort_order)
**Returns**: Created Composition instance
**Validation**: Must validate component exists and prevent circular references
**Performance**: Must complete in <200ms

#### `get_composition_by_id(composition_id: int) -> Optional[Composition]`
**Purpose**: Retrieve a specific composition relationship
**Parameters**:
- `composition_id`: ID of the composition
**Returns**: Composition instance or None if not found
**Performance**: Must complete in <50ms

#### `update_composition(composition_id: int, **updates) -> Composition`
**Purpose**: Update an existing composition relationship
**Parameters**:
- `composition_id`: ID of composition to update
- `**updates`: Dictionary of fields to update
**Returns**: Updated Composition instance
**Validation**: Must maintain referential integrity
**Performance**: Must complete in <200ms

#### `delete_composition(composition_id: int) -> bool`
**Purpose**: Delete a composition relationship
**Parameters**:
- `composition_id`: ID of composition to delete
**Returns**: True if deleted, False if not found
**Performance**: Must complete in <100ms

### Assembly Composition Queries

#### `get_assembly_components(assembly_id: int, ordered: bool = True) -> List[Composition]`
**Purpose**: Get all direct components of an assembly
**Parameters**:
- `assembly_id`: ID of the FinishedGood assembly
- `ordered`: If True, return in sort_order sequence
**Returns**: List of Composition instances
**Performance**: Must complete in <100ms

#### `get_component_usages(component_type: str, component_id: int) -> List[Composition]`
**Purpose**: Find all assemblies that use a specific component
**Parameters**:
- `component_type`: "finished_unit" or "finished_good"
- `component_id`: ID of the component
**Returns**: List of Composition instances
**Performance**: Must complete in <200ms

#### `get_assembly_hierarchy(assembly_id: int, max_depth: int = 5) -> dict`
**Purpose**: Get complete hierarchy structure for an assembly
**Parameters**:
- `assembly_id`: ID of the FinishedGood assembly
- `max_depth`: Maximum hierarchy levels to traverse
**Returns**: Nested dictionary representing full component hierarchy
**Performance**: Must complete in <500ms for maximum depth
**Algorithm**: Iterative breadth-first search

#### `flatten_assembly_components(assembly_id: int) -> List[dict]`
**Purpose**: Get flattened list of all components at all hierarchy levels
**Parameters**:
- `assembly_id`: ID of the FinishedGood assembly
**Returns**: List of dictionaries with component details and total quantities
**Performance**: Must complete in <400ms
**Use Case**: Bill of materials generation

### Validation Operations

#### `validate_no_circular_reference(assembly_id: int, new_component_id: int) -> bool`
**Purpose**: Check if adding a component would create circular dependency
**Parameters**:
- `assembly_id`: ID of assembly to add component to
- `new_component_id`: ID of component being added (must be FinishedGood)
**Returns**: True if safe, False if would create cycle
**Algorithm**: Breadth-first traversal with visited tracking
**Performance**: Must complete in <200ms

#### `validate_component_exists(component_type: str, component_id: int) -> bool`
**Purpose**: Verify that a component exists and is valid
**Parameters**:
- `component_type`: "finished_unit" or "finished_good"
- `component_id`: ID of the component
**Returns**: True if component exists and is valid
**Performance**: Must complete in <50ms

#### `check_composition_integrity(assembly_id: int) -> dict`
**Purpose**: Validate integrity of all compositions for an assembly
**Parameters**:
- `assembly_id`: ID of the assembly to check
**Returns**: Dictionary with validation results and any issues found
**Performance**: Must complete in <300ms

### Bulk Operations

#### `bulk_create_compositions(compositions: List[dict]) -> List[Composition]`
**Purpose**: Create multiple composition relationships efficiently
**Parameters**:
- `compositions`: List of composition specification dictionaries
**Returns**: List of created Composition instances
**Validation**: Must validate all compositions before creating any
**Performance**: Must complete in <1s for up to 100 compositions

#### `reorder_assembly_components(assembly_id: int, new_order: List[int]) -> bool`
**Purpose**: Update sort order for all components in an assembly
**Parameters**:
- `assembly_id`: ID of the assembly
- `new_order`: List of composition_ids in desired order
**Returns**: True if reordered successfully
**Performance**: Must complete in <500ms

#### `copy_assembly_composition(source_assembly_id: int, target_assembly_id: int) -> bool`
**Purpose**: Copy all component relationships from one assembly to another
**Parameters**:
- `source_assembly_id`: ID of assembly to copy from
- `target_assembly_id`: ID of assembly to copy to
**Returns**: True if copied successfully
**Validation**: Must check for circular references with target assembly
**Performance**: Must complete in <1s

### Cost and Quantity Calculations

#### `calculate_assembly_component_costs(assembly_id: int) -> dict`
**Purpose**: Calculate total cost contribution of each component type
**Parameters**:
- `assembly_id`: ID of the assembly
**Returns**: Dictionary with cost breakdown by component
**Performance**: Must complete in <400ms

#### `calculate_required_inventory(assembly_id: int, assembly_quantity: int) -> dict`
**Purpose**: Calculate total inventory needed for assembly production
**Parameters**:
- `assembly_id`: ID of the assembly
- `assembly_quantity`: Number of assemblies to produce
**Returns**: Dictionary of component requirements
**Performance**: Must complete in <300ms

### Query Utilities

#### `search_compositions_by_component(search_term: str) -> List[Composition]`
**Purpose**: Find compositions involving components matching search term
**Parameters**:
- `search_term`: String to search in component names
**Returns**: List of matching Composition instances
**Performance**: Must complete in <400ms

#### `get_assembly_statistics(assembly_id: int) -> dict`
**Purpose**: Get statistical information about an assembly's composition
**Parameters**:
- `assembly_id`: ID of the assembly
**Returns**: Dictionary with component counts, costs, hierarchy depth, etc.
**Performance**: Must complete in <200ms

## Error Handling

### Exception Types
- `CompositionNotFoundError`: When composition doesn't exist
- `InvalidComponentTypeError`: When component_type is not valid
- `CircularReferenceError`: When operation would create circular dependency
- `DuplicateCompositionError`: When composition already exists
- `IntegrityViolationError`: When operation would violate referential integrity

### Validation Rules
- Assembly ID must reference valid FinishedGood
- Component type must be "finished_unit" or "finished_good"
- Component ID must reference valid entity of specified type
- Exactly one of finished_unit_id or finished_good_id must be non-null
- Quantity must be positive integer
- Circular references prohibited

## Integration Points

### Database Models
- Primary: `Composition`
- Related: `FinishedGood`, `FinishedUnit`

### Service Dependencies
- `finished_unit_service`: For FinishedUnit validation and cost lookup
- `finished_good_service`: For FinishedGood validation and hierarchy traversal

### Event Handling
- `composition_created`: Fired when new composition created
- `composition_updated`: Fired when composition modified
- `composition_deleted`: Fired when composition removed
- `hierarchy_changed`: Fired when assembly structure changes

## Performance Targets

- **Single composition operations**: <200ms
- **Hierarchy traversal**: <500ms for 5-level depth
- **Bulk operations**: <1s for up to 100 compositions
- **Validation operations**: <200ms
- **Search operations**: <400ms
- **Memory usage**: <50MB for 10k composition relationships

## Caching Strategy

### Cache Keys
- Assembly component lists by assembly_id
- Component usage lists by component type/id
- Hierarchy structures for frequently accessed assemblies
- Validation results for circular reference checks

### Cache Invalidation
- Clear assembly cache on composition create/update/delete
- Clear component usage cache when compositions change
- Clear validation cache when hierarchy changes

## Testing Requirements

### Unit Tests Required
- All CRUD operations with validation
- Hierarchy traversal algorithms
- Circular reference detection
- Bulk operation integrity
- Cost and quantity calculations
- Error handling scenarios

### Integration Tests Required
- Cross-service component validation
- Complex hierarchy manipulation
- Performance benchmarks for large compositions
- Cache behavior validation

### Performance Tests Required
- Hierarchy traversal with maximum depth
- Bulk operations with large datasets
- Search operations across large composition sets
- Memory usage under load