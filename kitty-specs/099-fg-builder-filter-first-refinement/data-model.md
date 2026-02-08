# Data Model: FG Builder Filter-First Refinement

## No Schema Changes Required

This feature uses existing data model structures. No new tables, columns, or migrations.

## Existing Entities Used

### FinishedGood (`src/models/finished_good.py`)

- **assembly_type** (Enum: AssemblyType) - Distinguishes atomic vs assembled:
  - `AssemblyType.BARE` - Auto-generated 1:1 wrapper around a FinishedUnit
  - `AssemblyType.BUNDLE` - User-built multi-component assembly
- Used for: Filter logic ("Finished Units" vs "Existing Assemblies"), edit protection

### FinishedUnit (`src/models/finished_unit.py`)

- **category** (String) - Used for category filter dropdown
- **display_name** (String) - Used for search filtering and display
- **recipe_id** (FK) - Links to source recipe

### AssemblyType Enum (`src/models/assembly_type.py`)

- `BARE` = "bare" - Single FinishedUnit, no additional packaging (min/max components: 1/1)
- `BUNDLE` = "bundle" - Multi-component assembly (min/max components: 1/50)

### Composition (`src/models/composition.py`)

- Junction table linking FinishedGood to its components
- `component_type` - "finished_unit" or "finished_good"
- `component_quantity` - Number of each component
- Used by builder to save/load component selections

## Filter-to-Query Mapping

| UI Filter | Query Target | Filter Parameter |
|-----------|-------------|-----------------|
| "Finished Units" | `finished_unit_service.get_all_finished_units()` | `name_search`, `category` |
| "Existing Assemblies" | `finished_good_service.get_all_finished_goods()` | `assembly_type=AssemblyType.BUNDLE`, `name_search` |
| "Both" | Both services above | Combined results |
