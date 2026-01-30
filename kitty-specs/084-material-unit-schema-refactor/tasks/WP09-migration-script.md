---
work_package_id: WP09
title: Migration Transformation Script
lane: "for_review"
dependencies: [WP06]
base_branch: 084-material-unit-schema-refactor-WP06
base_commit: d9c2ca251e85fea7ce79202b8f26d1eacdec9076
created_at: '2026-01-30T18:15:23.377609+00:00'
subtasks:
- T041
- T042
- T043
- T044
- T045
phase: Wave 4 - Migration
assignee: ''
agent: ''
shell_pid: "37570"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-30T17:11:03Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 – Migration Transformation Script

## Implementation Command

```bash
spec-kitty implement WP09 --base WP06
```

Depends on WP06 (must match final export/import format).

---

## Objectives & Success Criteria

**Goal**: Create standalone script to transform old-format exports to new schema.

**Success Criteria**:
- [ ] Script transforms MaterialUnits from material_slug to material_product_slug
- [ ] N products × M units = N×M MaterialUnits created (duplication strategy)
- [ ] Orphaned MaterialUnits (Materials with 0 products) flagged in log
- [ ] Compositions with material_id skipped and logged
- [ ] Migration log documents all transformation decisions
- [ ] Script tests pass

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/084-material-unit-schema-refactor/spec.md` (FR-018, FR-019)
- Data Model: `kitty-specs/084-material-unit-schema-refactor/data-model.md`
- Plan: `kitty-specs/084-material-unit-schema-refactor/plan.md`

**Migration Strategy** (from data-model.md):
```
Input (old schema):
{
  "material_slug": "red-satin-ribbon",
  "name": "6-inch Red Ribbon",
  "slug": "6-inch-red-ribbon",
  "quantity_per_unit": 0.1524
}

Transformation:
1. Lookup Material by material_slug
2. Get all MaterialProducts for that Material
3. For each MaterialProduct:
   - Create new MaterialUnit with material_product_slug = product.slug

Output (new schema - duplicated per product):
[
  {
    "material_product_slug": "michaels-red-satin-25m",
    "name": "6-inch Red Ribbon",
    "slug": "6-inch-red-ribbon",
    "quantity_per_unit": 0.1524
  },
  {
    "material_product_slug": "joann-red-satin-50m",
    "name": "6-inch Red Ribbon",
    "slug": "6-inch-red-ribbon",
    "quantity_per_unit": 0.1524
  }
]
```

---

## Subtasks & Detailed Guidance

### Subtask T041 – Create Migration Script Skeleton

**Purpose**: Set up CLI interface and basic structure.

**Files**: `scripts/migrate_material_units.py` (new file)

**Steps**:
1. Create the scripts directory if it doesn't exist:
   ```bash
   mkdir -p scripts
   ```

2. Create the script skeleton:
   ```python
   #!/usr/bin/env python3
   """
   Migration script to transform MaterialUnits from old schema (material_slug)
   to new schema (material_product_slug).

   Usage:
       python scripts/migrate_material_units.py input.json output.json

   The script:
   1. Reads old-format export JSON
   2. Transforms MaterialUnits using duplication strategy (N products × M units)
   3. Flags orphaned MaterialUnits (Materials with 0 products)
   4. Logs Compositions with material_id (user must fix manually)
   5. Writes new-format JSON for import
   """

   import argparse
   import json
   import sys
   from dataclasses import dataclass, field
   from datetime import datetime
   from pathlib import Path
   from typing import Dict, List, Optional


   @dataclass
   class MigrationLog:
       """Tracks migration decisions and statistics."""
       material_units_transformed: int = 0
       material_units_created: int = 0
       material_units_orphaned: int = 0
       compositions_skipped: int = 0
       errors: List[str] = field(default_factory=list)
       warnings: List[str] = field(default_factory=list)
       decisions: List[str] = field(default_factory=list)

       def log_decision(self, message: str):
           self.decisions.append(message)
           print(f"  [DECISION] {message}")

       def log_warning(self, message: str):
           self.warnings.append(message)
           print(f"  [WARNING] {message}")

       def log_error(self, message: str):
           self.errors.append(message)
           print(f"  [ERROR] {message}")

       def summary(self) -> str:
           return f"""
   Migration Summary
   =================
   MaterialUnits processed: {self.material_units_transformed}
   MaterialUnits created (after duplication): {self.material_units_created}
   Orphaned MaterialUnits (no products): {self.material_units_orphaned}
   Compositions skipped (material_id): {self.compositions_skipped}
   Errors: {len(self.errors)}
   Warnings: {len(self.warnings)}
   """


   def main():
       parser = argparse.ArgumentParser(
           description="Transform MaterialUnits from old schema to new schema"
       )
       parser.add_argument("input_file", help="Input JSON file (old format)")
       parser.add_argument("output_file", help="Output JSON file (new format)")
       parser.add_argument("--dry-run", action="store_true",
           help="Show what would be done without writing output")
       parser.add_argument("--log-file", help="Write detailed log to file")

       args = parser.parse_args()

       # Load input
       input_path = Path(args.input_file)
       if not input_path.exists():
           print(f"Error: Input file not found: {input_path}")
           sys.exit(1)

       with open(input_path, "r", encoding="utf-8") as f:
           data = json.load(f)

       # Run migration
       log = MigrationLog()
       output_data = transform_export_data(data, log)

       # Print summary
       print(log.summary())

       # Write output (unless dry run)
       if not args.dry_run:
           output_path = Path(args.output_file)
           with open(output_path, "w", encoding="utf-8") as f:
               json.dump(output_data, f, indent=2, ensure_ascii=False)
           print(f"Output written to: {output_path}")

       # Write log file if requested
       if args.log_file:
           with open(args.log_file, "w", encoding="utf-8") as f:
               f.write(f"Migration Log - {datetime.now().isoformat()}\n")
               f.write("=" * 50 + "\n\n")
               f.write(log.summary())
               f.write("\nDecisions:\n")
               for d in log.decisions:
                   f.write(f"  - {d}\n")
               f.write("\nWarnings:\n")
               for w in log.warnings:
                   f.write(f"  - {w}\n")
               f.write("\nErrors:\n")
               for e in log.errors:
                   f.write(f"  - {e}\n")

       # Exit with error code if there were errors
       if log.errors:
           sys.exit(1)


   def transform_export_data(data: Dict, log: MigrationLog) -> Dict:
       """Transform entire export data from old to new schema."""
       # Copy data structure
       output = {k: v for k, v in data.items() if k not in ["material_units", "compositions"]}

       # Build lookups from existing data
       materials = {m["slug"]: m for m in data.get("materials", [])}
       products = data.get("material_products", [])
       products_by_material = build_products_by_material_lookup(products)

       # Transform MaterialUnits
       output["material_units"] = transform_material_units(
           data.get("material_units", []),
           materials,
           products_by_material,
           log,
       )

       # Transform Compositions (skip material_id)
       output["compositions"] = transform_compositions(
           data.get("compositions", []),
           log,
       )

       return output


   def build_products_by_material_lookup(products: List[Dict]) -> Dict[str, List[Dict]]:
       """Build lookup: material_slug -> list of products."""
       lookup = {}
       for p in products:
           mat_slug = p.get("material_slug", "")
           if mat_slug:
               if mat_slug not in lookup:
                   lookup[mat_slug] = []
               lookup[mat_slug].append(p)
       return lookup


   if __name__ == "__main__":
       main()
   ```

3. Make executable:
   ```bash
   chmod +x scripts/migrate_material_units.py
   ```

**Validation**:
- [ ] Script runs with --help
- [ ] Script accepts input/output file arguments
- [ ] Dry-run mode works
- [ ] Log file option works

---

### Subtask T042 – Implement MaterialUnit Duplication Transformation

**Purpose**: Transform MaterialUnits from material_slug to material_product_slug.

**Files**: `scripts/migrate_material_units.py`

**Steps**:
1. Add the transformation function:
   ```python
   def transform_material_units(
       units: List[Dict],
       materials: Dict[str, Dict],
       products_by_material: Dict[str, List[Dict]],
       log: MigrationLog,
   ) -> List[Dict]:
       """
       Transform MaterialUnits from old schema to new schema.

       For each MaterialUnit with material_slug:
       - Find all MaterialProducts for that Material
       - Create one MaterialUnit per product (duplication)
       """
       transformed = []

       for unit in units:
           log.material_units_transformed += 1
           material_slug = unit.get("material_slug")

           # Check if already in new format
           if "material_product_slug" in unit and not material_slug:
               # Already migrated, pass through
               transformed.append(unit)
               log.material_units_created += 1
               continue

           if not material_slug:
               log.log_warning(f"MaterialUnit '{unit.get('name', 'unknown')}' "
                   f"has no material_slug or material_product_slug")
               continue

           # Get products for this material
           products = products_by_material.get(material_slug, [])

           if not products:
               # Orphaned unit - no products to assign
               log.material_units_orphaned += 1
               log.log_decision(
                   f"ORPHANED: MaterialUnit '{unit.get('name')}' "
                   f"(material='{material_slug}') - no MaterialProducts found"
               )
               continue

           # Create one unit per product (duplication)
           log.log_decision(
               f"DUPLICATE: MaterialUnit '{unit.get('name')}' "
               f"(material='{material_slug}') -> {len(products)} products"
           )

           for product in products:
               new_unit = {
                   "material_product_slug": product["slug"],
                   "name": unit.get("name"),
                   "slug": unit.get("slug"),
                   "quantity_per_unit": unit.get("quantity_per_unit"),
                   "description": unit.get("description"),
               }
               # Preserve UUID if present (but note: duplicates will share UUID)
               if "uuid" in unit:
                   # Generate new UUID or omit for duplicates
                   new_unit["uuid"] = None  # Let import generate new UUID

               transformed.append(new_unit)
               log.material_units_created += 1

       return transformed
   ```

2. Handle slug collisions for duplicates:
   ```python
   def transform_material_units(...) -> List[Dict]:
       ...
       # Track slugs per product to handle collisions
       slugs_by_product = {}

       for unit in units:
           ...
           for product in products:
               product_slug = product["slug"]

               # Initialize slug tracking for this product
               if product_slug not in slugs_by_product:
                   slugs_by_product[product_slug] = set()

               # Generate unique slug within product
               base_slug = unit.get("slug", "")
               unique_slug = get_unique_slug(base_slug, slugs_by_product[product_slug])
               slugs_by_product[product_slug].add(unique_slug)

               new_unit = {
                   "material_product_slug": product_slug,
                   "name": unit.get("name"),
                   "slug": unique_slug,
                   ...
               }
               ...

   def get_unique_slug(base_slug: str, existing_slugs: set) -> str:
       """Generate unique slug, adding suffix if needed."""
       if base_slug not in existing_slugs:
           return base_slug
       for i in range(2, 1000):
           candidate = f"{base_slug}-{i}"
           if candidate not in existing_slugs:
               return candidate
       return f"{base_slug}-{datetime.now().timestamp()}"
   ```

**Validation**:
- [ ] Units with material_slug are transformed
- [ ] N products × M units = N×M output units
- [ ] Each output unit has material_product_slug
- [ ] Slug collisions handled with suffix

---

### Subtask T043 – Implement Orphan Detection

**Purpose**: Flag MaterialUnits that cannot be migrated.

**Files**: `scripts/migrate_material_units.py`

**Steps**:
1. Orphan detection is already in T042 - ensure clear logging:
   ```python
   if not products:
       log.material_units_orphaned += 1
       log.log_decision(
           f"ORPHANED: MaterialUnit '{unit.get('name')}' "
           f"(material='{material_slug}') has no MaterialProducts. "
           f"ACTION: Create MaterialProducts for this Material first, "
           f"then re-run migration."
       )
       continue
   ```

2. Add summary of orphans at end:
   ```python
   def transform_export_data(data: Dict, log: MigrationLog) -> Dict:
       ...
       if log.material_units_orphaned > 0:
           log.log_warning(
               f"{log.material_units_orphaned} MaterialUnits were orphaned. "
               f"These units will NOT be in the output file. "
               f"To migrate them: create MaterialProducts for their Materials, "
               f"then re-run migration."
           )
       ...
   ```

3. Optionally write orphans to separate file:
   ```python
   # In main():
   if args.orphan_file and orphaned_units:
       with open(args.orphan_file, "w", encoding="utf-8") as f:
           json.dump(orphaned_units, f, indent=2)
       print(f"Orphaned units written to: {args.orphan_file}")
   ```

**Validation**:
- [ ] Orphaned units counted correctly
- [ ] Clear log message explains why orphaned
- [ ] Action items provided for user
- [ ] Orphaned units NOT in output file

---

### Subtask T044 – Implement Composition material_id Skip Logging

**Purpose**: Skip and log Compositions that reference material_id.

**Files**: `scripts/migrate_material_units.py`

**Steps**:
1. Add Composition transformation function:
   ```python
   def transform_compositions(
       compositions: List[Dict],
       log: MigrationLog,
   ) -> List[Dict]:
       """
       Transform Compositions, skipping those with material_slug.

       Compositions with material_slug (old generic material reference)
       cannot be auto-migrated - user must manually specify which
       MaterialUnit to use.
       """
       transformed = []

       for comp in compositions:
           material_slug = comp.get("material_slug")

           if material_slug:
               # Skip this composition
               log.compositions_skipped += 1
               assembly_slug = comp.get("assembly_slug", "unknown")
               log.log_decision(
                   f"SKIPPED: Composition in assembly '{assembly_slug}' "
                   f"references material_slug='{material_slug}'. "
                   f"ACTION: Edit export file to replace material_slug "
                   f"with specific material_unit_slug."
               )
               continue

           # Pass through compositions without material_slug
           transformed.append(comp)

       return transformed
   ```

2. Add detailed skip report:
   ```python
   def transform_compositions(...) -> List[Dict]:
       ...
       skipped_details = []

       for comp in compositions:
           if material_slug:
               skipped_details.append({
                   "assembly_slug": comp.get("assembly_slug"),
                   "material_slug": material_slug,
                   "quantity": comp.get("quantity"),
               })
               ...

       # Write skipped compositions summary
       if skipped_details:
           log.log_warning(
               f"\n{len(skipped_details)} Compositions were skipped. "
               f"These must be manually edited in the export file:\n" +
               "\n".join(
                   f"  - Assembly '{s['assembly_slug']}': "
                   f"material='{s['material_slug']}' qty={s['quantity']}"
                   for s in skipped_details
               )
           )
   ```

**Validation**:
- [ ] Compositions with material_slug are skipped
- [ ] Skip count tracked correctly
- [ ] Detailed log shows which assemblies affected
- [ ] Action items provided for user
- [ ] Non-material compositions pass through unchanged

---

### Subtask T045 – Add Migration Script Tests

**Purpose**: Test migration transformation logic.

**Files**: `src/tests/test_migrate_material_units.py` (new file)

**Steps**:
1. Create test file:
   ```python
   """Tests for migration transformation script."""

   import pytest
   import sys
   from pathlib import Path

   # Add scripts to path
   sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
   from migrate_material_units import (
       transform_export_data,
       transform_material_units,
       transform_compositions,
       build_products_by_material_lookup,
       MigrationLog,
   )


   @pytest.fixture
   def sample_materials():
       return [
           {"slug": "red-ribbon", "name": "Red Ribbon"},
           {"slug": "clear-bags", "name": "Clear Bags"},
       ]


   @pytest.fixture
   def sample_products():
       return [
           {"slug": "michaels-red-25m", "material_slug": "red-ribbon"},
           {"slug": "joann-red-50m", "material_slug": "red-ribbon"},
           {"slug": "amazon-bags-100", "material_slug": "clear-bags"},
       ]


   @pytest.fixture
   def sample_units_old_format():
       return [
           {
               "material_slug": "red-ribbon",
               "name": "6-inch cut",
               "slug": "6-inch-cut",
               "quantity_per_unit": 0.1524,
           },
           {
               "material_slug": "clear-bags",
               "name": "1 bag",
               "slug": "1-bag",
               "quantity_per_unit": 1.0,
           },
       ]


   class TestBuildProductsLookup:
       def test_groups_products_by_material(self, sample_products):
           lookup = build_products_by_material_lookup(sample_products)
           assert "red-ribbon" in lookup
           assert len(lookup["red-ribbon"]) == 2
           assert "clear-bags" in lookup
           assert len(lookup["clear-bags"]) == 1


   class TestTransformMaterialUnits:
       def test_duplicates_units_across_products(
           self, sample_materials, sample_products, sample_units_old_format
       ):
           materials = {m["slug"]: m for m in sample_materials}
           products_by_material = build_products_by_material_lookup(sample_products)
           log = MigrationLog()

           result = transform_material_units(
               sample_units_old_format, materials, products_by_material, log
           )

           # Red ribbon unit should be duplicated to 2 products
           red_units = [u for u in result if "red" in u["material_product_slug"]]
           assert len(red_units) == 2

           # Clear bags unit should map to 1 product
           bag_units = [u for u in result if "bags" in u["material_product_slug"]]
           assert len(bag_units) == 1

           # Total: 2 + 1 = 3
           assert len(result) == 3
           assert log.material_units_created == 3

       def test_orphaned_units_not_in_output(self, sample_materials):
           materials = {m["slug"]: m for m in sample_materials}
           products_by_material = {}  # No products
           log = MigrationLog()

           units = [{"material_slug": "red-ribbon", "name": "Test", "slug": "test"}]
           result = transform_material_units(units, materials, products_by_material, log)

           assert len(result) == 0
           assert log.material_units_orphaned == 1

       def test_new_format_units_pass_through(self, sample_materials, sample_products):
           materials = {m["slug"]: m for m in sample_materials}
           products_by_material = build_products_by_material_lookup(sample_products)
           log = MigrationLog()

           # Already new format
           units = [{
               "material_product_slug": "michaels-red-25m",
               "name": "6-inch cut",
               "slug": "6-inch-cut",
           }]
           result = transform_material_units(units, materials, products_by_material, log)

           assert len(result) == 1
           assert result[0]["material_product_slug"] == "michaels-red-25m"


   class TestTransformCompositions:
       def test_skips_compositions_with_material_slug(self):
           log = MigrationLog()
           compositions = [
               {"assembly_slug": "box-a", "material_slug": "red-ribbon", "quantity": 2},
               {"assembly_slug": "box-b", "material_unit_slug": "6-inch-cut", "quantity": 1},
           ]

           result = transform_compositions(compositions, log)

           assert len(result) == 1
           assert result[0]["assembly_slug"] == "box-b"
           assert log.compositions_skipped == 1

       def test_passes_valid_compositions(self):
           log = MigrationLog()
           compositions = [
               {"assembly_slug": "box-a", "material_unit_slug": "6-inch-cut"},
               {"assembly_slug": "box-b", "finished_unit_slug": "cookie-dozen"},
           ]

           result = transform_compositions(compositions, log)

           assert len(result) == 2
           assert log.compositions_skipped == 0


   class TestFullTransform:
       def test_full_export_transformation(
           self, sample_materials, sample_products, sample_units_old_format
       ):
           data = {
               "materials": sample_materials,
               "material_products": sample_products,
               "material_units": sample_units_old_format,
               "compositions": [
                   {"assembly_slug": "box", "material_slug": "red-ribbon"},
               ],
           }
           log = MigrationLog()

           result = transform_export_data(data, log)

           assert "material_units" in result
           assert len(result["material_units"]) == 3  # 2 + 1 duplicates
           assert "compositions" in result
           assert len(result["compositions"]) == 0  # All skipped
           assert log.compositions_skipped == 1
   ```

2. Run tests:
   ```bash
   ./run-tests.sh src/tests/test_migrate_material_units.py -v
   ```

**Validation**:
- [ ] Duplication tests pass
- [ ] Orphan detection tests pass
- [ ] Composition skip tests pass
- [ ] Full transform integration test passes

---

## Test Strategy

**Required Tests**:
1. Build products lookup correctly groups by material
2. MaterialUnits duplicated across products (N×M)
3. Orphaned units not in output, counted correctly
4. New-format units pass through unchanged
5. Compositions with material_slug skipped
6. Valid compositions pass through

**Test Commands**:
```bash
./run-tests.sh src/tests/test_migrate_material_units.py -v
```

**Integration Test**:
```bash
# Create test data
echo '{"materials":[{"slug":"test"}],"material_products":[{"slug":"prod","material_slug":"test"}],"material_units":[{"material_slug":"test","name":"unit","slug":"unit","quantity_per_unit":1}],"compositions":[]}' > /tmp/test_old.json

# Run migration
python scripts/migrate_material_units.py /tmp/test_old.json /tmp/test_new.json --log-file /tmp/migration.log

# Check output
cat /tmp/test_new.json
cat /tmp/migration.log
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UUID conflicts from duplication | Generate new UUIDs or set to null |
| Slug conflicts within product | Add numeric suffix |
| Large export files slow | Process in streaming if needed (future) |
| User runs on wrong file | Clear error messages, dry-run mode |

---

## Definition of Done Checklist

- [ ] Script accepts input/output file arguments
- [ ] Dry-run mode works
- [ ] MaterialUnit duplication transformation works
- [ ] Orphan detection and logging works
- [ ] Composition skip and logging works
- [ ] Migration log documents all decisions
- [ ] All tests pass
- [ ] Script tested with sample data

---

## Review Guidance

**Key Checkpoints**:
1. Verify duplication logic creates N×M units
2. Verify orphaned units logged clearly with action items
3. Verify compositions skipped clearly with action items
4. Test with real export data if available
5. Verify output format matches import expectations

---

## Activity Log

- 2026-01-30T17:11:03Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-30T18:18:37Z – unknown – shell_pid=37570 – lane=for_review – All subtasks complete, 20 tests passing, CLI verified with sample data
