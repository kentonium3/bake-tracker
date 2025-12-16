# Claude Code Prompt: Unit Handling Analysis

## Context

Refer to `.kittify/memory/constitution.md` for project principles.

We are evaluating unit handling in bake-tracker to ensure standardized, unambiguous unit usage. A design reference has been created at `docs/design/unit_codes_reference.md` documenting UN/CEFACT Recommendation 20 as the target standard.

## Task

Analyze the current unit handling implementation across the codebase. Produce a report covering:

### 1. Unit Storage & Representation

- How are units stored in the database schema? (Check `src/models/`)
- Are units free-form strings or constrained to a defined set?
- Is there a units table, enum, or constants file?

### 2. Unit Usage Patterns

Identify all places where units are referenced:
- Model fields that store unit values
- Service layer unit handling
- UI unit selection/display
- Import/export unit handling

### 3. Ambiguity Analysis

Specifically look for:
- Usage of "oz" — is it weight ounce or fluid ounce? Check context.
- Any inconsistent unit representations (e.g., "cup" vs "cups" vs "c")
- Units that could be misinterpreted

### 4. Sample Data Review

Examine `data/sample_data.json`:
- List all unique unit values used
- Flag any ambiguous units (especially "oz")
- Note the context of each ambiguous usage (ingredient type, field name)

### 5. Validation & Constraints

- Does import validation check units against a valid set?
- Are there any unit validation rules in the codebase?
- What happens if an invalid unit is imported?

## Output Format

Produce a markdown report with:

1. **Summary**: High-level findings (2-3 sentences)
2. **Unit Storage Model**: Schema details
3. **Unit Values Found**: Table of all unique units in code and data
4. **Ambiguity Issues**: Specific instances of "oz" or other ambiguous units with file/line references
5. **Validation Gaps**: Missing validation that should exist
6. **Recommendations**: Prioritized list of issues to address

## Files to Examine

Start with:
- `src/models/*.py` — schema definitions
- `src/services/import_service.py` — import handling
- `src/services/export_service.py` — export handling  
- `data/sample_data.json` — test data
- `docs/design/import_export_specification.md` — current spec (v3.4)
- `docs/design/unit_codes_reference.md` — target standard

Use `grep` or similar to find all occurrences of unit-related patterns across the codebase.
