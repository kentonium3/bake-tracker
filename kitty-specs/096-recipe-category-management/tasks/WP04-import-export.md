---
work_package_id: WP04
title: Import/Export Support
lane: "planned"
dependencies: [WP01]
subtasks:
- T018
- T019
- T020
- T021
- T022
phase: Phase 3 - User Story 4 (Data Portability)
assignee: ''
agent: ""
shell_pid: ""
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-06T04:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 -- Import/Export Support

## Important: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

Depends on WP01 (needs RecipeCategory model and service). Independent of WP02 and WP03.

---

## Objectives & Success Criteria

- Add recipe categories to full backup export.
- Add recipe categories to catalog export.
- Create import function with duplicate detection by UUID/slug.
- Wire import into the existing import orchestration.
- Verify round-trip export/import preserves data.

**Success criteria:**
- Full backup JSON includes `recipe_categories` array
- Catalog export includes `recipe_categories` array
- Import creates new categories, skips duplicates (by UUID then slug)
- Import/export round-trip preserves all category data
- Old export files without `recipe_categories` import gracefully

## Context & Constraints

- **Spec**: `kitty-specs/096-recipe-category-management/spec.md`
- **Plan**: `kitty-specs/096-recipe-category-management/plan.md`
- **Constitution**: `.kittify/memory/constitution.md` -- Principle II (Data Integrity)

**Exemplar files to study**:
- `src/services/import_export_service.py` lines 1752-1762 -- MaterialCategory export pattern
- `src/services/import_export_service.py` lines 4473-4487 -- MaterialCategory import wiring
- `src/services/catalog_import_service.py` line 1652+ -- `import_material_categories()` implementation
- `src/services/catalog_import_service.py` -- `CatalogImportResult` return type

**Export format**:
```json
{
  "recipe_categories": [
    {
      "uuid": "abc-123",
      "name": "Cakes",
      "slug": "cakes",
      "sort_order": 10,
      "description": "Layer cakes, sheet cakes, bundt cakes"
    }
  ]
}
```

## Subtasks & Detailed Guidance

### Subtask T018 -- Add recipe_categories to full backup export

- **Purpose**: Include recipe categories in full backup so they can be restored.
- **Steps**:
  1. Open `src/services/import_export_service.py`
  2. Find the full backup export function (look for where `material_categories` is exported, around line 1752)
  3. Add a similar block for recipe categories:
     ```python
     # Add recipe categories
     from src.models.recipe_category import RecipeCategory
     with session_scope() as session:
         recipe_cats = session.query(RecipeCategory).order_by(RecipeCategory.sort_order).all()
         for rc in recipe_cats:
             export_data["recipe_categories"].append({
                 "uuid": str(rc.uuid) if rc.uuid else None,
                 "name": rc.name,
                 "slug": rc.slug,
                 "sort_order": rc.sort_order,
                 "description": rc.description,
             })
     ```
  4. Ensure `export_data["recipe_categories"]` is initialized as an empty list earlier in the function
- **Files**: `src/services/import_export_service.py` (modify)
- **Parallel?**: Yes -- different section from T020-T021
- **Notes**: Search for where `export_data["material_categories"]` is initialized and add `export_data["recipe_categories"] = []` nearby. Follow the exact same pattern.

### Subtask T019 -- Add recipe_categories to catalog export

- **Purpose**: Include recipe categories in catalog-specific exports.
- **Steps**:
  1. Find the catalog export function in `import_export_service.py`
  2. Add recipe categories export (same serialization as T018)
  3. This may be the same function or a different one -- study the code to determine
- **Files**: `src/services/import_export_service.py` (modify)
- **Parallel?**: Yes -- likely near T018
- **Notes**: If catalog export and full backup share the same code path, this may already be handled by T018. Verify by reading the export functions.

### Subtask T020 -- Create import_recipe_categories() in catalog_import_service.py

- **Purpose**: Import recipe categories with duplicate detection.
- **Steps**:
  1. Open `src/services/catalog_import_service.py`
  2. Find `import_material_categories()` as the exemplar (line 1652+)
  3. Create `import_recipe_categories()` following the same pattern:
     ```python
     def import_recipe_categories(
         categories_data: List[dict],
         mode: str = "add",
         session: Optional[Session] = None,
     ) -> CatalogImportResult:
     ```
  4. Implementation:
     - For each category in input data:
       - Check for existing by UUID first (if provided)
       - If no UUID match, check by slug
       - If match found: skip (ADD_ONLY) or update (augment mode)
       - If no match: create new RecipeCategory
     - Track counts: added, skipped, failed
     - Return CatalogImportResult with entity_counts
  5. Handle edge cases:
     - Missing required fields (name, slug)
     - Duplicate names in import data
     - Empty categories_data list
- **Files**: `src/services/catalog_import_service.py` (modify)
- **Notes**: Follow the `import_material_categories()` implementation closely. Use the same `CatalogImportResult` type and `EntityCounts` tracking.

### Subtask T021 -- Wire recipe category import into main import orchestration

- **Purpose**: Connect the import function to the main import flow.
- **Steps**:
  1. Find where `material_categories` import is wired in `import_export_service.py` (around line 4473)
  2. Add a similar block for recipe categories:
     ```python
     if "recipe_categories" in data:
         rc_result = catalog_import_service.import_recipe_categories(
             data["recipe_categories"], mode=import_mode, session=session
         )
         counts = rc_result.entity_counts["recipe_categories"]
         result.entity_counts["recipe_category"] = {
             "imported": counts.added,
             "skipped": counts.skipped,
         }
         result.successful += counts.added
         result.skipped += counts.skipped
         result.failed += counts.failed
         result.total_records += counts.added + counts.skipped + counts.failed
         session.flush()
     ```
  3. Ensure the `if` check handles old export files that don't have `recipe_categories`
- **Files**: `src/services/import_export_service.py` (modify)
- **Notes**: The `if "recipe_categories" in data` check ensures backward compatibility with exports from before this feature.

### Subtask T022 -- Add round-trip test

- **Purpose**: Verify that export -> import preserves all recipe category data.
- **Steps**:
  1. Create or extend a test in `src/tests/` (find existing import/export tests for placement)
  2. Test scenario:
     - Create several RecipeCategory records with various fields
     - Export (full backup)
     - Verify `recipe_categories` key exists in export data
     - Verify all categories are serialized correctly
     - Clear categories from database
     - Import the exported data
     - Verify all categories restored with correct field values
  3. Test duplicate handling:
     - Import the same data again
     - Verify no duplicates created (all skipped)
  4. Test backward compatibility:
     - Import data without `recipe_categories` key
     - Verify no error (graceful skip)
- **Files**: `src/tests/test_recipe_category_import_export.py` (new file, or extend existing)
- **Notes**: Find existing import/export tests to understand the test pattern. Use the same test fixtures and database setup.

## Risks & Mitigations

- **Risk**: Old export files don't have `recipe_categories` key.
  **Mitigation**: Import checks `if "recipe_categories" in data` before processing.

- **Risk**: UUID collisions between environments.
  **Mitigation**: UUID matching is first-pass only. Slug matching is fallback.

- **Risk**: Import creates categories that conflict with seeded defaults.
  **Mitigation**: Slug-based dedup handles this (seeded "cakes" matches imported "cakes").

## Definition of Done Checklist

- [ ] Full backup export includes `recipe_categories` array
- [ ] Catalog export includes `recipe_categories` array
- [ ] `import_recipe_categories()` function exists with UUID/slug dedup
- [ ] Import wired into main orchestration
- [ ] Old exports without `recipe_categories` import gracefully
- [ ] Round-trip test passes (export -> import -> verify)
- [ ] Duplicate import test passes (no duplicates created)
- [ ] All existing tests continue to pass

## Review Guidance

- **Export**: Verify `recipe_categories` appears in exported JSON with all fields
- **Import**: Test with both fresh import and duplicate import
- **Backward compat**: Import an old export file (without recipe_categories)
- **Pattern match**: Compare with material_categories import/export code -- should be nearly identical structure

## Activity Log

- 2026-02-06T04:30:00Z -- system -- lane=planned -- Prompt created.
