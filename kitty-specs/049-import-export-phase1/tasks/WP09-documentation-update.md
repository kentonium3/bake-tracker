---
work_package_id: "WP09"
subtasks:
  - "T076"
  - "T077"
  - "T078"
  - "T079"
  - "T080"
  - "T081"
  - "T082"
  - "T083"
  - "T084"
  - "T085"
title: "Documentation Update"
phase: "Phase 3 - Wave 2"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "13882"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2026-01-12T16:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 - Documentation Update

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Update `docs/design/spec_import_export.md` to document all new import/export capabilities for AI system reference.

**Success Criteria**:
- All new import/export formats accurately documented
- AI systems (BT Mobile) can use documentation as reference
- Examples provided for each new format

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/049-import-export-phase1/spec.md`
- Plan: `kitty-specs/049-import-export-phase1/plan.md`
- Existing doc: `docs/design/spec_import_export.md`

**Document Purpose**: This specification is the canonical reference for:
- External AI systems (BT Mobile app)
- Future developers
- Schema validation
- Integration testing

**Style Guide**: Follow existing document style:
- Schema tables with Field, Type, Required, Description columns
- Complete JSON examples for each format
- Clear section headers

---

## Subtasks & Detailed Guidance

### Subtask T076 - Update entity list to 16 types

**Purpose**: Document complete entity coverage.

**Steps**:
1. Open `docs/design/spec_import_export.md`
2. Update entity list in overview/summary section:
```markdown
## Supported Entity Types

The full backup export includes all 16 entity types:

| Entity | Import Order | Dependencies |
|--------|--------------|--------------|
| suppliers | 1 | None |
| ingredients | 2 | None |
| products | 3 | ingredients |
| recipes | 4 | ingredients |
| purchases | 5 | products, suppliers |
| inventory_items | 6 | products, purchases |
| material_categories | 7 | None |
| material_subcategories | 8 | material_categories |
| materials | 9 | material_subcategories |
| material_products | 10 | materials, suppliers |
| material_units | 11 | materials |
| material_purchases | 12 | material_products, suppliers |
| finished_goods | 13 | None |
| events | 14 | None |
| production_runs | 15 | recipes, events |
| inventory_depletions | 16 | inventory_items |
```

**Files**: `docs/design/spec_import_export.md`

### Subtask T077 - Document manifest format with new entities

**Purpose**: Explain backup manifest structure.

**Steps**:
1. Add/update manifest section:
```markdown
## Full Backup Manifest

The `manifest.json` file contains metadata about the export:

```json
{
  "version": "1.0",
  "export_date": "2026-01-12T10:30:00Z",
  "source": "Bake Tracker v1.0.0",
  "files": [
    {
      "filename": "01_suppliers.json",
      "entity_type": "suppliers",
      "record_count": 15,
      "sha256": "abc123...",
      "dependencies": [],
      "import_order": 1
    },
    // ... 16 entries total
  ]
}
```

### Manifest Fields

| Field | Type | Description |
|-------|------|-------------|
| version | string | Manifest format version |
| export_date | ISO8601 | When export was created |
| source | string | Application and version |
| files | array | File entries for each entity |
| files[].filename | string | Entity file name |
| files[].entity_type | string | Entity type name |
| files[].record_count | integer | Number of records |
| files[].sha256 | string | File content hash |
| files[].dependencies | array | Required entities |
| files[].import_order | integer | Import sequence |
```

**Files**: `docs/design/spec_import_export.md`

### Subtask T078 - Add materials and material_products import schemas

**Purpose**: Document materials catalog import format.

**Steps**:
1. Add materials section:
```markdown
## Materials Import Schema

### Materials

```json
{
  "version": "4.0",
  "materials": [
    {
      "slug": "kraft_boxes",
      "display_name": "Kraft Boxes",
      "category_slug": "packaging",
      "description": "Brown kraft paper boxes",
      "notes": "Various sizes available"
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| slug | string | Yes | Unique identifier |
| display_name | string | Yes | Human-readable name |
| category_slug | string | No | Parent category reference |
| description | string | No | Detailed description |
| notes | string | No | Additional notes |

### Material Products

```json
{
  "version": "4.0",
  "material_products": [
    {
      "material_slug": "kraft_boxes",
      "brand": "Uline",
      "product_name": "6x6x6 Kraft Box",
      "package_quantity": 25,
      "package_unit": "count",
      "supplier_name": "Uline",
      "upc_code": "012345678901"
    }
  ]
}
```
```

**Files**: `docs/design/spec_import_export.md`

### Subtask T079 - Document context-rich export schemas

**Purpose**: Document view export formats for AI tools.

**Steps**:
1. Add context-rich section:
```markdown
## Context-Rich Export Schemas

Context-rich exports include computed values and nested relationships for AI augmentation workflows.

### Common Structure

All context-rich exports share this structure:

```json
{
  "view_type": "<entity_type>",
  "export_date": "2026-01-12T10:30:00Z",
  "record_count": 150,
  "_meta": {
    "editable_fields": ["field1", "field2"],
    "readonly_fields": ["id", "slug", "computed_field"]
  },
  "records": [...]
}
```

### Ingredients View

Includes: hierarchy paths, related products, inventory totals

```json
{
  "view_type": "ingredients",
  "_meta": {
    "editable_fields": ["description", "notes", "density_volume_value", "density_volume_unit"],
    "readonly_fields": ["id", "uuid", "slug", "display_name", "category_hierarchy", "product_count", "inventory_total", "average_cost"]
  },
  "records": [
    {
      "id": 1,
      "slug": "all_purpose_flour",
      "display_name": "All-Purpose Flour",
      "category_hierarchy": "Flours & Starches > Wheat Flours > All-Purpose",
      "description": "Standard white flour",
      "product_count": 3,
      "inventory_total": 15.5,
      "average_cost": 0.45,
      "products": [
        {"brand": "King Arthur", "product_name": "AP Flour 5lb"}
      ]
    }
  ]
}
```

### Materials View

Similar structure to ingredients.

### Recipes View

Includes: embedded ingredients, computed costs

```json
{
  "view_type": "recipes",
  "_meta": {
    "editable_fields": ["instructions", "notes", "prep_time_minutes", "cook_time_minutes"],
    "readonly_fields": ["id", "slug", "name", "yield_quantity", "computed_cost", "ingredients"]
  },
  "records": [
    {
      "slug": "sugar_cookies",
      "name": "Sugar Cookies",
      "instructions": "Mix dry ingredients...",
      "computed_cost": 4.50,
      "ingredients": [
        {"ingredient_name": "All-Purpose Flour", "quantity": 2, "unit": "cup"}
      ]
    }
  ]
}
```
```

**Files**: `docs/design/spec_import_export.md`

### Subtask T080 - Document `_meta` section format

**Purpose**: Explain _meta for format detection and import filtering.

**Steps**:
1. Add _meta documentation:
```markdown
## _meta Section

The `_meta` section enables:
1. **Format auto-detection**: Presence of `_meta` identifies context-rich format
2. **Import field filtering**: Only `editable_fields` are imported

### editable_fields

Fields that can be modified via import. AI tools can augment these.

### readonly_fields

Fields included for context but ignored during import:
- `id`, `uuid` - Database identifiers
- `slug` - Used for lookup, not modification
- Computed values (totals, costs, counts)
- Nested relationships
```

**Files**: `docs/design/spec_import_export.md`

### Subtask T081 - Add purchase transaction import schema

**Purpose**: Document purchase import for BT Mobile.

**Steps**:
1. Add purchases section:
```markdown
## Purchase Transaction Import

Used by BT Mobile to import scanned purchases.

### Schema

```json
{
  "schema_version": "4.0",
  "import_type": "purchases",
  "created_at": "2026-01-12T14:30:00Z",
  "source": "bt_mobile",
  "supplier": "Costco",
  "purchases": [
    {
      "product_slug": "flour_all_purpose_king_arthur_5lb",
      "purchased_at": "2026-01-12T14:15:23Z",
      "unit_price": 7.99,
      "quantity_purchased": 2,
      "supplier": "Costco",
      "notes": "Weekly shopping"
    }
  ]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| schema_version | string | Yes | Must be "4.0" |
| import_type | string | Yes | Must be "purchases" |
| source | string | No | Origin system |
| supplier | string | No | Default supplier for all purchases |
| purchases[].product_slug | string | Yes | Product to add inventory for |
| purchases[].purchased_at | ISO8601 | No | Purchase date/time |
| purchases[].unit_price | decimal | Yes | Price per unit |
| purchases[].quantity_purchased | decimal | Yes | Quantity (must be positive) |
| purchases[].supplier | string | No | Override default supplier |
| purchases[].notes | string | No | Purchase notes |

### Validation Rules

- `quantity_purchased` must be positive (> 0)
- `product_slug` must exist in database
- Duplicate detection: same (product_slug, date, price) skipped
```

**Files**: `docs/design/spec_import_export.md`

### Subtask T082 - Add inventory adjustment import schema

**Purpose**: Document adjustment import for BT Mobile.

**Steps**:
1. Add adjustments section:
```markdown
## Inventory Adjustment Import

Used by BT Mobile to import inventory corrections.

### Schema

```json
{
  "schema_version": "4.0",
  "import_type": "adjustments",
  "created_at": "2026-01-12T09:15:00Z",
  "source": "bt_mobile",
  "adjustments": [
    {
      "product_slug": "flour_all_purpose_king_arthur_5lb",
      "adjusted_at": "2026-01-12T09:10:12Z",
      "quantity": -2.5,
      "reason_code": "spoilage",
      "notes": "Found mold, discarding"
    }
  ]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| schema_version | string | Yes | Must be "4.0" |
| import_type | string | Yes | Must be "adjustments" |
| adjustments[].product_slug | string | Yes | Product to adjust |
| adjustments[].adjusted_at | ISO8601 | No | Adjustment date/time |
| adjustments[].quantity | decimal | Yes | Amount (must be negative) |
| adjustments[].reason_code | string | Yes | Reason for adjustment |
| adjustments[].notes | string | No | Additional details |

### Allowed Reason Codes

| Code | Description |
|------|-------------|
| spoilage | Product went bad |
| waste | Spilled, burned, or otherwise wasted |
| correction | Physical count doesn't match system |
| other | Other reason (explain in notes) |

### Validation Rules

- `quantity` must be negative (< 0)
- `reason_code` must be one of allowed values
- Cannot reduce inventory below zero
- FIFO: oldest inventory adjusted first
```

**Files**: `docs/design/spec_import_export.md`

### Subtask T083 - Document format auto-detection rules

**Purpose**: Explain how system detects import format.

**Steps**:
1. Add detection section:
```markdown
## Format Auto-Detection

The system automatically detects import file format:

### Detection Rules

1. **Context-Rich**: File has `_meta.editable_fields`
2. **Purchases**: `import_type == "purchases"`
3. **Adjustments**: `import_type in ["adjustments", "inventory_updates"]`
4. **Normalized**: Has `version` and `application == "bake-tracker"`
5. **Unknown**: None of above match

### Detection Flow

```
Load JSON
  ↓
Has _meta.editable_fields? → Yes → Context-Rich
  ↓ No
Has import_type? → "purchases" → Purchases
                → "adjustments" → Adjustments
  ↓ No
Has version + application? → Yes → Normalized
  ↓ No
Unknown
```

### UI Confirmation

After detection, UI displays format for user confirmation before proceeding.
```

**Files**: `docs/design/spec_import_export.md`

### Subtask T084 - Update Appendix sections

**Purpose**: Update reference appendices.

**Steps**:
1. Update appendix sections as needed:
   - Appendix A: Category hierarchies
   - Appendix B: Unit types
   - Appendix C: Slug format rules
   - Add any new appendices needed

**Files**: `docs/design/spec_import_export.md`

### Subtask T085 - Add complete JSON examples

**Purpose**: Provide copy-paste examples for each format.

**Steps**:
1. Create "Complete Examples" section:
```markdown
## Complete Examples

### Full Backup Example

See `src/tests/fixtures/import_export/sample_backup/`

### Purchase Import Example

```json
{
  "schema_version": "4.0",
  "import_type": "purchases",
  "created_at": "2026-01-12T14:30:00Z",
  "source": "bt_mobile",
  "supplier": "Costco Waltham MA",
  "purchases": [
    {
      "product_slug": "flour_all_purpose_king_arthur_5lb",
      "purchased_at": "2026-01-12T14:15:23Z",
      "unit_price": 7.99,
      "quantity_purchased": 2,
      "notes": "Weekly shopping"
    },
    {
      "product_slug": "sugar_granulated_domino_4lb",
      "purchased_at": "2026-01-12T14:16:45Z",
      "unit_price": 3.49,
      "quantity_purchased": 1
    }
  ]
}
```

// Additional complete examples for each format
```

**Files**: `docs/design/spec_import_export.md`

---

## Test Strategy

**Documentation Review**:
- Verify JSON examples are valid JSON
- Test examples against actual import services
- Review with AI system perspective (is it clear enough?)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Documentation drift | Review against implemented code |
| Invalid examples | Test examples programmatically |
| Missing edge cases | Cross-reference with spec.md |

---

## Definition of Done Checklist

- [ ] Entity list updated to 16 types
- [ ] Manifest format documented
- [ ] Materials import schema documented
- [ ] Context-rich export schemas documented
- [ ] _meta section explained
- [ ] Purchase import schema documented
- [ ] Adjustment import schema documented
- [ ] Auto-detection rules documented
- [ ] Appendix sections updated
- [ ] Complete JSON examples for each format
- [ ] All examples valid JSON

## Review Guidance

**Reviewers should verify**:
1. All schemas match implemented code
2. Examples are valid and complete
3. Documentation usable by external AI systems
4. No ambiguous descriptions

---

## Activity Log

- 2026-01-12T16:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-12T19:00:00Z – claude – lane=doing – Updating spec_import_export.md
- 2026-01-12T22:25:00Z – claude – shell_pid=13882 – lane=done – Approved: spec_import_export.md updated to v4.1. Added 16 entity table, materials schemas, context-rich views E.2-E.4, Appendix K/L/M for format detection and transaction imports.
