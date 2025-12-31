---
work_package_id: "WP07"
subtasks:
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
title: "Migration Tooling"
phase: "Phase 4 - Migration"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "4712"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-30T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 – Migration Tooling

## Objectives & Success Criteria

**Goal**: Create scripts to migrate existing 487 ingredients to hierarchical structure.

**Success Criteria**:
- Export script extracts current ingredient data
- Transform script merges AI-generated hierarchy suggestions
- Validate script checks hierarchy integrity before import
- AI prompt template provides clear instructions for external AI
- Process documented for reproducibility
- Scripts handle edge cases gracefully

## Context & Constraints

**References**:
- Constitution: `.kittify/memory/constitution.md` - Principle VI (Schema Change Strategy)
- Plan: `kitty-specs/031-ingredient-hierarchy-taxonomy/plan.md` - Migration Strategy
- Research: `kitty-specs/031-ingredient-hierarchy-taxonomy/research.md` - Decision D6 (Hybrid AI)

**Constraints**:
- Scripts accept pre-generated JSON (no API calls required)
- Human review step required before final import
- Must preserve all existing ingredient data
- Rollback plan: retain category field as backup

**PARALLEL SAFE**: This entire work package can be done in parallel with WP05 (widget) and WP02-WP04 (services). Different file set (scripts/).

## Subtasks & Detailed Guidance

### Subtask T037 – Create export_ingredients.py [PARALLEL SAFE]
- **Purpose**: Export current ingredient data for AI analysis.
- **Steps**:
  1. Create `scripts/migrate_hierarchy/export_ingredients.py`
  2. Connect to database, query all ingredients
  3. Export to JSON with fields:
     - id, slug, display_name, category (current)
     - Any other relevant fields for categorization
  4. Include metadata: export date, record count
  5. Save to `scripts/migrate_hierarchy/output/ingredients_export.json`
- **Files**: `scripts/migrate_hierarchy/export_ingredients.py`
- **Parallel?**: Yes (independent script)
- **Notes**: Export should be idempotent; can re-run safely

### Subtask T038 – Create transform_hierarchy.py [PARALLEL SAFE]
- **Purpose**: Merge AI suggestions with export data.
- **Steps**:
  1. Create `scripts/migrate_hierarchy/transform_hierarchy.py`
  2. Accept two inputs:
     - Original export: `ingredients_export.json`
     - AI suggestions: `ai_hierarchy_suggestions.json`
  3. AI suggestions format:
     ```json
     {
       "categories": [
         {"name": "Chocolate", "level": 0, "children": ["Dark Chocolate", "Milk Chocolate"]},
         {"name": "Dark Chocolate", "level": 1, "parent": "Chocolate", "children": ["Semi-Sweet Chips"]}
       ],
       "assignments": [
         {"ingredient_slug": "semi_sweet_chips", "parent_name": "Dark Chocolate"}
       ]
     }
     ```
  4. Transform to import-ready format:
     - Add parent_ingredient_id for each ingredient
     - Calculate hierarchy_level
     - Create new category ingredients if needed
  5. Output: `transformed_ingredients.json`
- **Files**: `scripts/migrate_hierarchy/transform_hierarchy.py`
- **Parallel?**: Yes
- **Notes**: Handle missing assignments gracefully (default to level 2 leaf)

### Subtask T039 – Create validate_hierarchy.py [PARALLEL SAFE]
- **Purpose**: Pre-import validation of hierarchy integrity.
- **Steps**:
  1. Create `scripts/migrate_hierarchy/validate_hierarchy.py`
  2. Load transformed data
  3. Validation checks:
     - No orphans (parent exists for all children)
     - Valid levels (0, 1, or 2 only)
     - No cycles (parent chain doesn't loop)
     - All referenced parents exist
     - No duplicate slugs
     - Leaf ingredients preserved (existing ones remain)
  4. Report:
     - Total ingredients
     - Count by level
     - Any validation errors
     - Any warnings (e.g., ingredients without assignments)
  5. Exit code: 0 if valid, 1 if errors
- **Files**: `scripts/migrate_hierarchy/validate_hierarchy.py`
- **Parallel?**: Yes
- **Notes**: Critical gate before import; must catch all issues

### Subtask T040 – Create AI prompt template [PARALLEL SAFE]
- **Purpose**: Provide clear instructions for external AI categorization.
- **Steps**:
  1. Create `scripts/prompts/hierarchy_categorization_prompt.md`
  2. Include:
     - Context: What this is for
     - Input format: Description of export JSON
     - Output format: Expected JSON structure (with example)
     - Guidelines:
       - Create 10-20 root categories (Chocolate, Flour, Sugar, etc.)
       - Each root has 2-5 mid-tier categories
       - Assign each existing ingredient to a leaf position
       - Suggest new mid-tier categories as needed
     - Example categorizations
  3. Include sample input/output for testing
- **Files**: `scripts/prompts/hierarchy_categorization_prompt.md`
- **Parallel?**: Yes
- **Notes**: Prompt should work with various AI models (Claude, GPT, Gemini)

### Subtask T041 – Document migration process [PARALLEL SAFE]
- **Purpose**: Enable reproducible migration execution.
- **Steps**:
  1. Create `scripts/migrate_hierarchy/README.md`
  2. Document:
     - Prerequisites (Python, database access)
     - Step-by-step process:
       1. Export ingredients
       2. Run AI prompt (external)
       3. Transform with AI output
       4. Validate hierarchy
       5. Human review step
       6. Import (using existing import service)
     - Troubleshooting common issues
     - Rollback procedure
  3. Include example commands
  4. Note backup requirements
- **Files**: `scripts/migrate_hierarchy/README.md`
- **Parallel?**: Yes
- **Notes**: Documentation should be standalone; user can follow without code knowledge

## Test Strategy

- **Script Testing**:
  - Test each script with sample data
  - Test edge cases: empty input, invalid JSON
  - Test validation catches known error types

- **Integration Testing**:
  - Full pipeline with sample 20-30 ingredients
  - Verify import service accepts transformed data

- **Commands**:
  ```bash
  # Export
  python scripts/migrate_hierarchy/export_ingredients.py

  # Transform (after running AI)
  python scripts/migrate_hierarchy/transform_hierarchy.py \
    --input scripts/migrate_hierarchy/output/ingredients_export.json \
    --ai-suggestions scripts/migrate_hierarchy/output/ai_hierarchy_suggestions.json \
    --output scripts/migrate_hierarchy/output/transformed_ingredients.json

  # Validate
  python scripts/migrate_hierarchy/validate_hierarchy.py \
    --input scripts/migrate_hierarchy/output/transformed_ingredients.json
  ```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| AI categorization quality varies | Human review step; manual editing capability |
| Missing ingredients in transform | Default unassigned to level 2 leaf |
| Import fails with new fields | Test import service handles hierarchy fields |

## Definition of Done Checklist

- [ ] T037: Export script works with current database
- [ ] T038: Transform script merges AI suggestions correctly
- [ ] T039: Validate script catches all error types
- [ ] T040: AI prompt template is clear and complete
- [ ] T041: Migration process fully documented
- [ ] Scripts handle edge cases gracefully
- [ ] Full pipeline tested with sample data

## Review Guidance

- Verify scripts use consistent JSON formats
- Verify validation covers all integrity rules
- Check prompt template produces expected output format
- Verify documentation is complete and accurate
- Test with both empty and populated databases

## Activity Log

- 2025-12-30T12:00:00Z – system – lane=planned – Prompt created.
- 2025-12-31T14:24:31Z – gemini – shell_pid=31123 – lane=doing – Started parallel implementation
- 2025-12-31T14:35:05Z – gemini – shell_pid=34398 – lane=for_review – Ready for review - all scripts implemented and tested
- 2025-12-31T19:45:10Z – claude-reviewer – shell_pid=4712 – lane=done – Code review passed: Export/transform/validate scripts, AI prompt template, comprehensive README with examples and troubleshooting, test pipeline passes
