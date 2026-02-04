---
work_package_id: WP09
title: Documentation Update
lane: "for_review"
dependencies:
- WP02
base_branch: 094-core-api-standardization-WP02
base_commit: 4c4d4216b4fe996a812efe70fdee54773e407f15
created_at: '2026-02-03T22:56:25.477591+00:00'
subtasks:
- T047
- T048
- T049
- T050
phase: Phase 5 - Documentation
assignee: ''
agent: ''
shell_pid: "38903"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T16:10:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 - Documentation Update

## Objectives & Success Criteria

- Update CLAUDE.md with new exception and validation patterns
- Document which services have been standardized
- Provide code examples for future developers
- Ensure patterns are discoverable

## Context & Constraints

- **Depends on WP08**: All patterns should be established first
- Reference: `CLAUDE.md` - project documentation for AI and human developers
- Follow existing CLAUDE.md structure and style
- Include practical code examples

## Subtasks & Detailed Guidance

### Subtask T047 - Add "Exception Pattern" section to CLAUDE.md

**Purpose**: Document the standardized exception pattern for service functions.

**Steps**:
1. Add new section after "Session Management" section
2. Include:
   - Rationale for exception-based error handling
   - Pattern description
   - Code examples
   - List of exception types

**Content to add**:

```markdown
## Exception-Based Error Handling (F094)

**Problem:** Functions returning `None` for not-found cases lead to "forgot to check None" bugs.

### The Pattern

All `get_*` service functions that look up entities by ID, slug, or name raise domain-specific exceptions instead of returning None.

**Correct Pattern:**
\`\`\`python
def get_recipe_by_slug(slug: str, session: Optional[Session] = None) -> Recipe:
    """
    Get recipe by slug.

    Raises:
        RecipeNotFoundBySlug: If recipe doesn't exist
    """
    with session_scope(session) as sess:
        recipe = sess.query(Recipe).filter_by(slug=slug).first()
        if not recipe:
            raise RecipeNotFoundBySlug(slug)
        return recipe

# Calling code:
try:
    recipe = get_recipe_by_slug("chocolate-cake")
    # Use recipe - guaranteed not None
except RecipeNotFoundBySlug as e:
    show_error(f"Recipe '{e.slug}' not found")
\`\`\`

### Exception Naming Convention

Pattern: `{Entity}NotFoundBy{LookupField}`

Examples:
- `RecipeNotFoundBySlug` - Recipe lookup by slug
- `RecipeNotFoundByName` - Recipe lookup by name
- `EventNotFoundById` - Event lookup by ID
- `IngredientNotFoundBySlug` - Ingredient lookup by slug

### Available Exception Types

See `src/services/exceptions.py` for the full hierarchy.
```

**Files**: `CLAUDE.md`

### Subtask T048 - Add "Validation Pattern" section to CLAUDE.md

**Purpose**: Document the standardized validation pattern.

**Steps**:
1. Add section after "Exception Pattern" section
2. Include:
   - Rationale for exception-based validation
   - Pattern description
   - Code examples

**Content to add**:

```markdown
## Validation Pattern (F094)

**Problem:** Functions returning `Tuple[bool, str/list]` create awkward calling code with tuple unpacking.

### The Pattern

Validation functions raise `ValidationError` instead of returning tuples.

**Correct Pattern:**
\`\`\`python
def validate_required_string(value: Optional[str], field_name: str = "Field") -> None:
    """
    Validate that a string is not empty.

    Raises:
        ValidationError: If value is empty or whitespace
    """
    if not value or not value.strip():
        raise ValidationError([f"{field_name} is required"])

# Calling code:
try:
    validate_required_string(name, "Name")
    validate_required_string(category, "Category")
    # All validations passed
except ValidationError as e:
    show_errors(e.errors)  # List of error messages
\`\`\`

### Key Points

- Return `None` on success (no exception)
- Raise `ValidationError(errors: List[str])` on failure
- `ValidationError.errors` contains list of error messages
- No tuple unpacking needed at call sites
```

**Files**: `CLAUDE.md`

### Subtask T049 - Update existing "Key Design Decisions" section

**Purpose**: Reference the new patterns in the design decisions.

**Steps**:
1. Find "Key Design Decisions" section in CLAUDE.md
2. Add bullet point referencing F094 patterns

**Content to add**:

```markdown
- **Exception-Based Returns**: All `get_*` functions raise domain-specific exceptions instead of returning None. Validation functions raise `ValidationError` instead of returning tuples. See "Exception-Based Error Handling" and "Validation Pattern" sections.
```

**Files**: `CLAUDE.md`

### Subtask T050 - Document which services have been updated

**Purpose**: Help future developers know which services follow the new patterns.

**Steps**:
1. Add a note to the Exception Pattern section listing updated services
2. This helps identify any remaining services that haven't been updated

**Content to add**:

```markdown
### Services Updated (F094)

The following services have been fully updated to use exception-based patterns:

**Core Services:**
- `ingredient_service.py` - Already used exceptions (model for others)
- `recipe_service.py` - Updated: get_recipe_by_slug, get_recipe_by_name
- `event_service.py` - Updated: get_event_by_id, get_event_by_name
- `package_service.py` - Updated: get_package_by_id, get_package_by_name
- `finished_good_service.py` - Updated: get_finished_good_by_id/slug
- `finished_unit_service.py` - Updated: get_finished_unit_by_id/slug

**Secondary Services:**
- `composition_service.py` - Updated: get_composition_by_id
- `supplier_service.py` - Updated: get_supplier, get_supplier_by_uuid
- `recipient_service.py` - Updated: get_recipient_by_name
- `unit_service.py` - Updated: get_unit_by_code
- `material_catalog_service.py` - Updated: get_category, get_subcategory, get_material, get_product

**Validators:**
- `utils/validators.py` - All validation functions use exceptions
- `unit_converter.py` - Conversion functions raise ConversionError
- `material_unit_converter.py` - Conversion functions raise ConversionError
```

**Files**: `CLAUDE.md`

## Test Strategy

No code tests needed - this is documentation only.

Manual review:
1. Read through CLAUDE.md after changes
2. Verify code examples are correct
3. Check formatting renders properly

## Risks & Mitigations

- **Stale documentation**: Keep examples consistent with actual code
- **Missing services**: Update the list if more services are standardized

## Definition of Done Checklist

- [ ] "Exception-Based Error Handling" section added to CLAUDE.md
- [ ] "Validation Pattern" section added to CLAUDE.md
- [ ] "Key Design Decisions" section updated
- [ ] List of updated services documented
- [ ] Code examples are accurate and tested
- [ ] Markdown formatting is correct

## Review Guidance

- Verify code examples compile/run
- Check pattern descriptions match actual implementation
- Ensure all services from WP02-WP07 are listed

## Activity Log

- 2026-02-03T16:10:45Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
- 2026-02-04T02:50:50Z – unknown – shell_pid=38903 – lane=for_review – Ready for review: Added exception and validation pattern documentation to CLAUDE.md
