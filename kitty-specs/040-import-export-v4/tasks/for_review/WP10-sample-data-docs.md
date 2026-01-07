---
work_package_id: "WP10"
subtasks:
  - "T042"
  - "T043"
  - "T044"
title: "Sample Data & Documentation"
phase: "Phase 3 - Integration & Documentation"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP10 - Sample Data & Documentation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Update sample_data.json to v4.0 format with F037/F039 fields
- Create BT Mobile sample JSON files for testing
- Ensure all samples import successfully

**Success Criteria**:
- sample_data.json imports without errors
- BT Mobile samples match documented schema exactly
- Samples serve as documentation for file format

## Context & Constraints

**Related Documents**:
- `kitty-specs/040-import-export-v4/data-model.md` - Complete schema definitions
- `docs/design/spec_import_export.md` - Appendix I and J for BT Mobile schemas

**Key Constraints**:
- Keep samples minimal but representative
- Use realistic UPCs (valid check digits)
- Include examples of all field variations

**Files to Create/Modify**:
- `test_data/sample_data.json` - Upgrade to v4.0
- `test_data/bt_mobile_purchase_sample.json` - New file
- `test_data/bt_mobile_inventory_sample.json` - New file

**Dependencies**: WP01-WP08 (all import functions ready)

## Subtasks & Detailed Guidance

### Subtask T042 - Update sample_data.json to v4.0 format

**Purpose**: Upgrade existing sample data with new fields.

**Steps**:
1. Read current `test_data/sample_data.json`
2. Update header:
   ```json
   {
     "version": "4.0",
     "exported_at": "2026-01-06T12:00:00Z",
     "application": "bake-tracker",
     ...
   }
   ```
3. Update recipes section with F037 fields:
   - Add `base_recipe_slug` (null or slug reference)
   - Add `variant_name` (null or string)
   - Add `is_production_ready` (boolean)
   - Add `finished_units` array with yield_mode
4. Update events section with F039 fields:
   - Add `output_mode` (null, "bulk_count", "bundled", "packaged")
5. Validate import succeeds

**Schema Updates**:
```json
{
  "recipes": [
    {
      "slug": "sugar-cookie",
      "name": "Sugar Cookie",
      "base_recipe_slug": null,
      "variant_name": null,
      "is_production_ready": true,
      "finished_units": [
        {
          "slug": "sugar-cookie-dozen",
          "name": "Dozen",
          "yield_mode": "discrete_count",
          "unit_yield_quantity": "12",
          "unit_yield_unit": "cookies"
        }
      ],
      "ingredients": [...],
      ...
    },
    {
      "slug": "frosted-sugar-cookie",
      "name": "Frosted Sugar Cookie",
      "base_recipe_slug": "sugar-cookie",
      "variant_name": "Frosted",
      "is_production_ready": false,
      "finished_units": [],
      ...
    }
  ],
  "events": [
    {
      "slug": "holiday-sale-2025",
      "name": "Holiday Sale 2025",
      "output_mode": "bundled",
      "event_date": "2025-12-15",
      ...
    }
  ]
}
```

**Files**: `test_data/sample_data.json`
**Parallel?**: Yes - independent of BT Mobile samples

**Notes**:
- Preserve all existing data, only add new fields
- Include at least one base recipe and one variant
- Include recipes with and without finished_units

### Subtask T043 - Create bt_mobile_purchase_sample.json

**Purpose**: Provide sample file for testing purchase import.

**Steps**:
1. Create new file matching schema from data-model.md
2. Include multiple purchases:
   - One with known UPC (should match existing product)
   - One with unknown UPC (for resolution dialog testing)
   - One with complete metadata (supplier, notes)
3. Use realistic UPC codes (valid check digits)

**Sample Content**:
```json
{
  "schema_version": "4.0",
  "import_type": "purchases",
  "created_at": "2026-01-06T14:30:00Z",
  "source": "bt_mobile",
  "device_id": "iphone-12-bakery",
  "supplier": "Costco",
  "purchases": [
    {
      "upc": "016000196100",
      "scanned_at": "2026-01-06T14:15:23Z",
      "unit_price": 7.99,
      "quantity_purchased": 1.0,
      "notes": "5lb bag"
    },
    {
      "upc": "051000127952",
      "scanned_at": "2026-01-06T14:16:45Z",
      "unit_price": 4.29,
      "quantity_purchased": 2.0,
      "supplier": "Kroger"
    },
    {
      "upc": "999999999999",
      "scanned_at": "2026-01-06T14:18:00Z",
      "unit_price": 3.49,
      "quantity_purchased": 1.0,
      "notes": "Unknown product - will need resolution"
    }
  ]
}
```

**Files**: `test_data/bt_mobile_purchase_sample.json`
**Parallel?**: Yes - independent

**Notes**:
- Use UPCs that appear in sample_data.json for matching
- Include at least one purchase that will require resolution
- Document purpose in comments or README

### Subtask T044 - Create bt_mobile_inventory_sample.json

**Purpose**: Provide sample file for testing inventory update import.

**Steps**:
1. Create new file matching schema from data-model.md
2. Include multiple updates with varying percentages:
   - 50% remaining (typical case)
   - 100% remaining (no change)
   - 0% remaining (fully depleted)
   - 75% remaining (partial)
3. Use UPCs matching existing products

**Sample Content**:
```json
{
  "schema_version": "4.0",
  "import_type": "inventory_updates",
  "created_at": "2026-01-06T15:00:00Z",
  "source": "bt_mobile",
  "device_id": "iphone-12-bakery",
  "inventory_updates": [
    {
      "upc": "016000196100",
      "scanned_at": "2026-01-06T14:55:00Z",
      "percentage_remaining": 50,
      "notes": "About half bag left"
    },
    {
      "upc": "051000127952",
      "scanned_at": "2026-01-06T14:56:00Z",
      "percentage_remaining": 100,
      "notes": "Unopened"
    },
    {
      "upc": "012345678901",
      "scanned_at": "2026-01-06T14:57:00Z",
      "percentage_remaining": 0,
      "notes": "Empty - discard"
    },
    {
      "upc": "098765432109",
      "scanned_at": "2026-01-06T14:58:00Z",
      "percentage_remaining": 75
    }
  ]
}
```

**Files**: `test_data/bt_mobile_inventory_sample.json`
**Parallel?**: Yes - independent

**Notes**:
- Use UPCs that appear in sample_data.json
- Include edge cases (0%, 100%)
- Add notes showing expected behavior

## Test Strategy

**Required Tests**:
```bash
# Verify samples import successfully
pytest src/tests/services/test_import_export_service.py -v -k "sample"
```

**Manual Verification**:
1. Run application with fresh database
2. Import sample_data.json via UI
3. Verify all entities appear correctly
4. Import BT Mobile samples
5. Verify purchases and updates processed

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UPC collisions | Use known-good UPCs from product databases |
| Sample drift | Version samples alongside code |
| Missing fields | Validate against schema before commit |

## Definition of Done Checklist

- [ ] T042: sample_data.json updated to v4.0
- [ ] T043: bt_mobile_purchase_sample.json created
- [ ] T044: bt_mobile_inventory_sample.json created
- [ ] All samples import without errors
- [ ] Samples demonstrate all new features

## Review Guidance

- Verify JSON is valid and well-formatted
- Check UPCs have valid check digits
- Confirm samples match schema exactly
- Test imports with fresh database

## Activity Log

- 2026-01-06T12:00:00Z - system - lane=planned - Prompt created.
- 2026-01-07T03:44:54Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-07T03:47:05Z – system – shell_pid= – lane=for_review – Moved to for_review
