# AI-Assisted Development Workflow

**Version**: 1.0
**Last Updated**: 2026-01-10
**Purpose**: Guidelines for working with Claude and spec-kitty on bake-tracker

---

## Overview

This project uses a hybrid human-AI development workflow:
- **User** (Kent): Requirements, architectural decisions, user testing
- **Claude**: Specification authoring, code review, design analysis
- **Spec-Kitty**: Pattern discovery, implementation, testing
- **Claude Code**: Primary implementation agent

---

## Three-Phase Development Process

### Phase 1: Requirements Analysis (User-Led)

**User creates requirements document:**
- Location: `docs/requirements/REQ-*.md`
- Purpose: Think through scenarios, edge cases, constraints
- Content: What/why, not how
- Benefits:
  - Forces scenario thinking
  - Uncovers edge cases and design issues
  - Documents decisions and rationale
  - Captures success criteria

**Example**: `docs/requirements/req_materials.md`

**Key principle**: Requirements docs are valuable for the thinking process itself, not just documentation.

---

### Phase 2: Specification (AI-Led with User Guidance)

**Claude creates feature specification:**
- Location: `docs/design/F0XX_feature_name.md`
- Purpose: Implementation guidance for spec-kitty
- **Critical balance**: Lightweight on patterns, detailed on UI

#### Specification Content Guidelines

**Lightweight Sections (~30% of spec):**

Focus: Point to existing patterns, let spec-kitty discover

- **Data Models**: "Study ingredient.py patterns and parallel exactly"
  - List required models
  - Point to parallel implementations
  - Note key constraints
  - Don't write full SQLAlchemy code

- **Service Layer**: "Follow ingredient service patterns"
  - List required services
  - Reference existing service structure
  - Note business rule differences
  - Don't write method signatures

- **Business Logic**: High-level rules only
  - Core algorithms (e.g., weighted average costing)
  - Validation rules
  - State transitions
  - Not implementation details

- **Testing**: Checklists and criteria
  - What to test (not how)
  - Success criteria
  - Edge cases to cover
  - Not test code

**Detailed Sections (~70% of spec):**

Focus: Prevent poor UI/UX through explicit specifications

- **UI Mockups**: ASCII diagrams with exact widgets
  ```
  ┌─ Dialog Title ──────────────┐
  │                              │
  │ Label: [CTkEntry    ]       │  ← Specific widget types
  │                              │
  │ Grid: 2 cols (120px, flex)  │  ← Exact layout specs
  │ Padding: 15px all sides     │  ← Spacing details
  │                              │
  │        [Cancel] [Submit]    │  ← Button placement
  └──────────────────────────────┘
  ```

- **Form Layouts**: Grid positions, padding, sizing
  - Column widths (px or proportional)
  - Row heights where critical
  - Padding between elements
  - Alignment specifications

- **Validation Patterns**: When/how to show errors
  - Field-level validation triggers
  - Error message placement
  - Visual feedback (colors, icons)
  - Form-level validation

- **Widget Selection**: Specific CustomTkinter components
  - CTkEntry vs CTkTextbox
  - CTkComboBox vs CTkOptionMenu
  - CTkTreeview for hierarchies
  - CTkScrollableFrame for lists

- **User Workflows**: Step-by-step interactions
  - Screen transitions
  - Data flow between forms
  - User feedback at each step
  - Error recovery paths

#### Target Specification Length

- **Total**: 400-600 lines (not 1,600+)
- **Data/Service**: ~150 lines (point to patterns)
- **UI Details**: ~350 lines (explicit mockups)
- **Testing**: ~100 lines (checklists)

#### Why This Balance?

**Lightweight on patterns:**
- Leverages AI pattern discovery strengths
- Ensures consistency with existing code
- Prevents architectural divergence
- Faster spec authoring

**Detailed on UI:**
- Prevents poor usability
- Ensures consistent styling
- Maintains visual hierarchy
- Avoids reinventing widgets

**Anti-pattern**: F047 v1.0 was 1,673 lines with full SQLAlchemy models, complete service code, and exhaustive implementation details. This bypassed spec-kitty's pattern discovery and led to missing the slug pattern that existed in ingredients.

---

### Phase 3: Implementation (Spec-Kitty-Led)

**Spec-kitty workflow:**
1. **Discovery**: Reads codebase to find patterns
2. **Analysis**: Identifies existing implementations to parallel
3. **Implementation**: Follows discovered patterns + spec UI details
4. **Testing**: Validates against requirements

**User responsibilities:**
- Review spec-kitty discoveries
- Test implementations
- Provide feedback
- Approve completions

**Critical**: Spec must explicitly direct pattern discovery
- "Study ingredient.py before implementing"
- "Parallel existing X service exactly"
- "Match Y import format"

---

## Multi-Agent Development System

### Agent Roles

**Claude Code** (Primary Implementation):
- Reads spec-kitty specifications
- Implements features following patterns
- Runs tests and fixes issues
- Primary development agent

**Cursor** (Independent Code Review):
- Reviews code without context from Claude Code
- Finds issues missed by self-review
- Provides independent validation
- Quality assurance agent

**Claude (This Interface)** (Design & Analysis):
- Creates specifications from requirements
- Analyzes architectural patterns
- Reviews discoveries and proposals
- Design consultation agent

**Spec-Kitty** (Orchestration):
- Manages development workflow
- Tracks feature progress
- Enforces process discipline
- Workflow management tool

### Development Workflow Example

```
1. User creates requirements → REQ-MATERIALS-001
2. Claude creates lightweight spec → F047 (500 lines)
3. Spec-kitty.specify → reads spec + discovers patterns
4. Claude Code implements → following discovered patterns
5. Cursor reviews → independent validation
6. User tests → real-world validation
7. Iterate until complete
```

---

## Key Patterns and Practices

### Pattern Discovery Directives

**In specifications, use explicit discovery instructions:**

✅ Good:
```markdown
## Data Models
Study ingredient.py and parallel exactly:
- Check for slug field (required for import stability)
- Match hierarchy structure
- Follow same relationship patterns
```

❌ Bad:
```markdown
## Data Models
```python
class Material(BaseModel):
    id: int
    display_name: str
    # ... 50 lines of SQLAlchemy code
```
```

### UI Specification Standards

**Always include for each UI component:**
1. ASCII mockup with dimensions
2. Specific widget types (CTkEntry, etc.)
3. Grid layout specifications
4. Padding/spacing values
5. Validation behavior
6. User interaction flow

**Example**:
```
### Purchase Dialog

Layout: 2-column grid (120px labels, flexible inputs)
Padding: 15px all sides, 8px between rows
Validation: Real-time on blur, form-level on submit

┌─ Record Purchase ────────────────┐
│                                   │
│ Product: [CTkComboBox      ▼]   │ ← 400px wide, required
│ Quantity: [CTkEntry      ]       │ ← Numeric only, >0
│ Cost: $[CTkEntry      ]          │ ← Currency format
│                                   │
│ Error: [red label if invalid]    │ ← Below invalid field
│                                   │
│              [Cancel] [Purchase]  │ ← Right-aligned
└───────────────────────────────────┘

Submit button: Disabled until all fields valid
Cancel button: No validation, closes dialog
```

### Architectural Principles

**Parallelism**: When implementing features similar to existing ones, they MUST match patterns exactly:
- Same field names (e.g., slug, display_name)
- Same relationship structures
- Same service layer patterns
- Same import/export formats

**Discovery First**: Before writing implementation details, spec must direct pattern discovery:
- Point to files to study
- Identify patterns to match
- Note constraints to preserve

**UI Quality**: Never sacrifice usability for speed:
- Detailed mockups required
- Widget selection explicit
- Validation patterns specified
- User workflows documented

---

## Common Pitfalls

### Over-Specification
**Problem**: Writing 1,600+ line specs with full implementation code
**Impact**: Bypasses pattern discovery, leads to architectural divergence
**Solution**: Point to patterns, let spec-kitty discover details

### Under-Specification of UI
**Problem**: "Create a form for X" without layout details
**Impact**: Poor usability, inconsistent styling, bad UX
**Solution**: Always include detailed UI mockups and specifications

### Missing Pattern References
**Problem**: Not directing spec-kitty to study existing code
**Impact**: Reimplements patterns differently, breaks consistency
**Solution**: Explicit "Study X file" directives in spec

### Skipping Code Review
**Problem**: Relying only on Claude Code's self-review
**Impact**: Misses issues, lower quality
**Solution**: Always use Cursor for independent review

---

## Tools and Resources

### Filesystem Tools
- Used extensively for reading project documentation
- Creating specification documents
- Making targeted code edits
- Essential for cross-referencing patterns

### Spec-Kitty Commands
- `spec-kitty.specify`: Start feature implementation
- `spec-kitty.constitution`: Update project principles
- Real-time kanban tracking

### Development Environment
- VS Code with Claude Code extension
- Cursor for independent reviews
- Git worktrees for feature isolation

---

## Evolution Notes

**Version History:**
- v1.0 (2026-01-10): Initial workflow documentation
  - Established lightweight spec pattern (30% data/70% UI)
  - Documented multi-agent review process
  - Captured pattern discovery approach

**Future Considerations:**
- Test lightweight spec approach on next feature
- Monitor spec-kitty pattern discovery effectiveness
- Refine UI detail level based on outcomes
- Consider additional AI agents (Gemini CLI for validation)

---

**END OF DOCUMENT**
