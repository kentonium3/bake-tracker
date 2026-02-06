# Data Model: Finished Goods Builder UI

**Feature**: 097-finished-goods-builder-ui
**Date**: 2026-02-06

## Existing Entities (No Schema Changes Required)

This feature is purely UI — it builds on existing data models with no schema modifications.

### FinishedGood (existing: `src/models/finished_good.py`)

Parent assembly record created/updated by the builder.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | Auto-generated |
| slug | String(200) | Auto-generated from display_name, unique |
| display_name | String(200) | User-entered name in Step 3 |
| assembly_type | Enum(AssemblyType) | Builder creates as CUSTOM_ORDER (or user-selected) |
| description | Text | Optional |
| packaging_instructions | Text | Optional |
| notes | Text | User-entered in Step 3 |
| inventory_count | Integer | Default 0 for new assemblies |

**Relationships:**
- `components` → List[Composition] via `assembly_id` FK (one-to-many)

### Composition (existing: `src/models/composition.py`)

Junction table linking FinishedGood to its components. **This is the entity the func spec calls "FinishedGoodComponent".**

| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | Auto-generated |
| assembly_id | Integer FK → finished_goods.id | Parent FinishedGood |
| finished_unit_id | Integer FK (nullable) | Food: FinishedUnit component |
| finished_good_id | Integer FK (nullable) | Food: Nested FinishedGood component |
| packaging_product_id | Integer FK (nullable) | Legacy packaging (not used by builder) |
| material_unit_id | Integer FK (nullable) | Material: MaterialUnit component |
| component_quantity | Float | Quantity (1-999 per spec) |
| component_notes | Text | Optional per-component notes |
| sort_order | Integer | Display order |

**Constraints:**
- 4-way XOR: Exactly one of `finished_unit_id`, `finished_good_id`, `packaging_product_id`, `material_unit_id` must be non-null
- Parent XOR: Exactly one of `assembly_id`, `package_id` must be non-null
- Positive quantity: `component_quantity > 0`
- No self-reference: `assembly_id != finished_good_id`
- Unique component per assembly (prevents duplicate component entries)

**Factory Methods:**
- `Composition.create_unit_composition(assembly_id, finished_unit_id, quantity, notes, sort_order)`
- `Composition.create_assembly_composition(assembly_id, finished_good_id, quantity, notes, sort_order)`
- `Composition.create_material_unit_composition(assembly_id, material_unit_id, quantity, notes, sort_order)`

### FinishedUnit (existing: `src/models/finished_unit.py`)

Selectable food items in Step 1.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | |
| display_name | String(200) | Shown in selection list |
| category | String(100) | Used for category dropdown filter |
| recipe_id | Integer FK | Parent recipe |

### MaterialUnit (existing: `src/models/material_unit.py`)

Selectable material items in Step 2.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | |
| name | String(200) | Shown in selection list |
| slug | String(200) | |
| material_product_id | Integer FK | Parent MaterialProduct |
| quantity_per_unit | Float | Base units consumed per use |

**Relationship:** `material_product` → MaterialProduct (has `material_category_id` for filtering)

### AssemblyType (existing: `src/models/assembly_type.py`)

Enum distinguishing bare items from assemblies.

| Value | Display Name | Builder Relevance |
|-------|-------------|-------------------|
| BARE | Bare | "Bare items only" filter = this type |
| CUSTOM_ORDER | Custom Order | Default for new builder-created items |
| GIFT_BOX | Gift Box | User can select |
| VARIETY_PACK | Variety Pack | User can select |
| HOLIDAY_SET | Holiday Set | User can select |
| BULK_PACK | Bulk Pack | User can select |

## Builder Internal State (UI-only, not persisted)

The builder dialog manages transient selection state between steps:

```
BuilderState:
  mode: "create" | "edit"
  finished_good_id: Optional[int]  # Set in edit mode
  name: str
  notes: str
  assembly_type: AssemblyType

  food_selections: List[ComponentSelection]
  material_selections: List[ComponentSelection]

  step1_complete: bool
  step2_complete: bool  # True even if skipped

ComponentSelection:
  type: "finished_unit" | "finished_good" | "material_unit"
  id: int
  display_name: str
  quantity: int  # 1-999
  sort_order: int
```

## Service Layer Interface (Existing)

### Create

```python
FinishedGoodService.create_finished_good(
    display_name: str,
    assembly_type: AssemblyType = AssemblyType.CUSTOM_ORDER,
    components: Optional[List[Dict]] = None,  # [{"type": str, "id": int, "quantity": int, "notes": str, "sort_order": int}]
    session=None,
    **kwargs  # notes, description, packaging_instructions
) -> FinishedGood
```

### Update (delete-and-replace components)

```python
FinishedGoodService.update_finished_good(
    finished_good_id: int,
    display_name: Optional[str] = None,
    assembly_type: Optional[AssemblyType] = None,
    components: Optional[List[Dict]] = None,  # Full replacement list
    notes: Optional[str] = None,
    session=None,
) -> FinishedGood
```

### Query

```python
FinishedGoodService.get_all_finished_goods() -> List[FinishedGood]
FinishedGoodService.get_finished_good_by_id(id: int) -> FinishedGood

finished_unit_service.get_all_finished_units(
    name_search=None, category=None, recipe_id=None
) -> List[FinishedUnit]
```

## Data Flow

```
Step 1 (Food)                    Step 2 (Materials)              Step 3 (Review)
─────────────                    ──────────────────              ───────────────
Query:                           Query:                          Display:
  FinishedGoods (bare/assembly)    MaterialUnits                   food_selections[]
  Categories (distinct)            MaterialCategories              material_selections[]

User selects → food_selections[] User selects → material_sel[]  User enters name, notes

                                                                 Save → service call:
                                                                   components = food_sel + material_sel
                                                                   create_finished_good() or
                                                                   update_finished_good()
```
