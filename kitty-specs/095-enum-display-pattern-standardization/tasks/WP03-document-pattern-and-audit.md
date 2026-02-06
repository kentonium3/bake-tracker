---
work_package_id: "WP03"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "Document Pattern and Audit Enums"
phase: "Phase 3 - Documentation & Audit"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
history:
  - timestamp: "2026-02-06T01:55:28Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 -- Document Pattern and Audit Enums

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
spec-kitty implement WP03 --base WP02
```

Depends on WP02 (audit should verify the code fixes are in place).

---

## Objectives & Success Criteria

- Add "Enum Display Pattern" section to `CLAUDE.md` with correct/incorrect code examples, rationale, and references to good codebase examples.
- Add enum-related items to a code review checklist in `CLAUDE.md`.
- Audit all 11 enums in `src/models/` for pattern compliance.
- Document audit findings.

**Success criteria (FR-004 through FR-006):**
- CLAUDE.md contains "Enum Display Pattern" section
- Pattern includes correct and incorrect examples
- Code review checklist covers enum usage
- All enums audited and findings documented

## Context & Constraints

- **Spec**: `kitty-specs/095-enum-display-pattern-standardization/spec.md`
- **Plan**: `kitty-specs/095-enum-display-pattern-standardization/plan.md`
- **Constitution**: `.kittify/memory/constitution.md` -- Principle VI.G (Code Organization), VI.D (API Consistency)
- **Func-spec reference**: `docs/func-spec/F095_enum_display_pattern_standardization.md` (contains the documentation content to add)

**Key file to modify:** `CLAUDE.md` (project root)

**Placement guidance**: Add the new section after the existing "Validation Pattern (F094)" section. This follows the natural documentation flow of pattern sections in CLAUDE.md.

**Enums to audit** (from `src/models/`):
1. `AssemblyType` -- `src/models/assembly_type.py` (fixed by WP01+WP02)
2. `LossCategory` -- `src/models/enums.py`
3. `DepletionReason` -- `src/models/enums.py`
4. `ProductionStatus` -- `src/models/enums.py`
5. `FulfillmentStatus` -- `src/models/event.py`
6. `OutputMode` -- `src/models/event.py`
7. `PlanState` -- `src/models/event.py`
8. `YieldMode` -- `src/models/finished_unit.py`
9. `SnapshotType` -- `src/models/planning_snapshot.py`
10. `AmendmentType` -- `src/models/plan_amendment.py`
11. `PackageStatus` -- `src/models/package_status.py`

## Subtasks & Detailed Guidance

### Subtask T010 -- Add "Enum Display Pattern" section to CLAUDE.md

- **Purpose**: Document the correct pattern for displaying enum values in UI code, so future developers and AI agents follow it consistently.
- **Steps**:
  1. Open `CLAUDE.md` at the project root
  2. Find the "Validation Pattern (F094)" section (search for `## Validation Pattern`)
  3. Add the following section AFTER the Validation Pattern section:

     ```markdown
     ## Enum Display Pattern

     **ALWAYS use enum methods for display strings, NEVER create hardcoded maps.**

     ### Correct Pattern

     ```python
     # Enum definition (models/example_type.py)
     class ExampleType(Enum):
         VALUE_A = "value_a"
         VALUE_B = "value_b"

         def get_display_name(self) -> str:
             """Return human-readable display name."""
             return {
                 ExampleType.VALUE_A: "Value A",
                 ExampleType.VALUE_B: "Value B",
             }[self]

         @classmethod
         def from_display_name(cls, display_name: str) -> Optional["ExampleType"]:
             """Get enum from display name. Returns None if not found."""
             for member in cls:
                 if member.get_display_name() == display_name:
                     return member
             return None

     # UI usage (ui/example_form.py)
     display = example_type.get_display_name()  # Forward lookup
     enum_val = ExampleType.from_display_name("Value A")  # Reverse lookup
     ```

     ### Incorrect Pattern

     ```python
     # UI file (ui/example_form.py)
     # WRONG - Hardcoded map duplicates enum logic
     type_map = {
         ExampleType.VALUE_A: "Value A",
         ExampleType.VALUE_B: "Value B",
     }
     display = type_map.get(example_type)  # Don't do this
     ```

     ### Why This Matters

     - **Single source of truth**: Display logic lives in enum, not scattered in UI
     - **Easier updates**: Adding new enum value requires 1 change, not N changes
     - **Type safety**: Enum methods are type-checked, maps are not
     - **Consistency**: All code uses same display strings automatically

     ### Good Examples in Codebase

     - `AssemblyType` (`src/models/assembly_type.py`) -- Uses `get_display_name()` and `from_display_name()` with centralized metadata
     - `LossCategory` (`src/models/enums.py`) -- Uses `str(Enum)` with `.value.replace("_", " ").title()` for dynamic display
     - `get_assembly_type_choices()` -- Helper function returning `[(value, display_name)]` for dropdowns
     ```

  4. Ensure the code examples use proper markdown code fences with language identifiers.
  5. Keep the documentation style consistent with existing CLAUDE.md pattern sections (Exception-Based Error Handling, Validation Pattern, etc.).

- **Files**: `CLAUDE.md`
- **Parallel?**: Yes (can proceed alongside T012)
- **Notes**: The func-spec (`docs/func-spec/F095_enum_display_pattern_standardization.md`, FR-2) contains a reference version of this content. Use it as inspiration but adapt to match the actual codebase state (e.g., include `from_display_name()` which was added by WP01).

### Subtask T011 -- Add enum code review checklist to CLAUDE.md

- **Purpose**: Ensure AI agents and reviewers check for enum pattern compliance during code reviews.
- **Steps**:
  1. In the same "Enum Display Pattern" section added in T010, add a subsection:

     ```markdown
     ### Enum Code Review Checklist

     When reviewing code that uses enums:
     - No hardcoded enum-to-string maps in UI code
     - Enum display methods (`get_display_name()`) used instead of manual mapping
     - New enums include `get_display_name()` method (if displayed in UI)
     - New enums include `from_display_name()` class method (if reverse lookup needed)
     - Dropdown options use enum helper methods or list comprehensions over enum members
     ```

  2. This is a subsection within the Enum Display Pattern section, not a standalone section.

- **Files**: `CLAUDE.md`
- **Parallel?**: Yes (same file as T010 but different subsection -- in practice, do T010 and T011 together)
- **Notes**: Keep it concise. This is a quick-reference checklist, not a tutorial.

### Subtask T012 -- Audit all enums for display method compliance

- **Purpose**: Verify that no other hardcoded enum display maps exist in the codebase, and document which enums have display methods.
- **Steps**:
  1. For each enum listed in Context & Constraints above, check:
     - Does it have a `get_display_name()` or equivalent method?
     - Is it displayed in the UI? (search for usage in `src/ui/`)
     - Are there any hardcoded display maps for it in UI code?

  2. Search for potential violations:
     ```bash
     # Search for dict literals mapping enum values to strings in UI code
     grep -rn "AssemblyType\.\|LossCategory\.\|DepletionReason\.\|ProductionStatus\.\|FulfillmentStatus\.\|OutputMode\.\|PlanState\.\|YieldMode\.\|SnapshotType\.\|AmendmentType\.\|PackageStatus\." src/ui/ | grep -i "map\|dict\|display"
     ```

  3. For each enum, classify as:
     - **Compliant**: Has display method OR not displayed in UI
     - **Needs display method**: Displayed in UI without a centralized method (but no hardcoded map -- acceptable for now)
     - **Violation**: Has hardcoded display map in UI code (should be zero after WP02)

  4. Enums that are internal-only (never shown to users) don't need display methods. Document this finding.

- **Files**: Multiple files read-only, no modifications
- **Parallel?**: Yes (can proceed alongside T010+T011)
- **Notes**: The inspection report (`docs/inspections/hardcoded_maps_categories_summary.md`) already found 95% compliance. This audit confirms and documents the full picture.

### Subtask T013 -- Document audit findings

- **Purpose**: Record the audit results so they are available for future reference.
- **Steps**:
  1. Create a brief summary of audit findings. This can go in one of:
     - The plan.md file (update the "Other Enums Audit" table with final results)
     - A comment in the spec.md
     - An inline note in the CLAUDE.md enum section (only if relevant for ongoing guidance)

  2. Recommended format (update plan.md's audit table):
     ```
     | Enum | Has Display Method | UI Usage | Hardcoded Maps | Status |
     |------|--------------------|----------|----------------|--------|
     | AssemblyType | Yes | Yes | None (fixed) | Compliant |
     | LossCategory | Dynamic (.value) | Yes | None | Compliant |
     | ... | ... | ... | ... | ... |
     ```

  3. If any violations are found, document them as follow-up work items (do NOT fix them in this feature unless trivial).

- **Files**: `kitty-specs/095-enum-display-pattern-standardization/plan.md` (update audit table)
- **Parallel?**: No (depends on T012 results)

## Risks & Mitigations

- **Risk**: Audit finds unexpected violations requiring additional code changes.
  **Mitigation**: Document findings but don't expand scope. Any new violations become follow-up work.

- **Risk**: CLAUDE.md changes conflict with other in-flight features.
  **Mitigation**: The new section is additive (new section at end of patterns). Low conflict risk.

## Definition of Done Checklist

- [ ] CLAUDE.md contains "Enum Display Pattern" section with correct/incorrect examples
- [ ] CLAUDE.md contains "Why This Matters" explanation
- [ ] CLAUDE.md contains "Good Examples in Codebase" references
- [ ] CLAUDE.md contains "Enum Code Review Checklist" subsection
- [ ] All 11 enums audited for compliance
- [ ] Audit findings documented (in plan.md or equivalent)
- [ ] No additional hardcoded enum maps found (or documented for follow-up)

## Review Guidance

- **CLAUDE.md**: Verify the new section follows the existing documentation style (compare with "Exception-Based Error Handling" and "Validation Pattern" sections).
- **Code examples**: Verify they compile conceptually and show clear correct vs incorrect patterns.
- **Audit completeness**: Verify all 11 enums from the models directory were checked.
- **No scope creep**: Verify no code changes were made beyond documentation. Any new violations should be documented, not fixed.

## Activity Log

- 2026-02-06T01:55:28Z -- system -- lane=planned -- Prompt created.
