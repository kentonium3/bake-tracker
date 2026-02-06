# Feature Specification: Enum Display Pattern Standardization

**Feature Branch**: `095-enum-display-pattern-standardization`
**Created**: 2026-02-05
**Status**: Draft
**Input**: F095 func-spec — eliminate 2 hardcoded enum display maps, document the correct pattern in CLAUDE.md, and audit all enums for compliance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assembly Type Displays Correctly After Map Removal (Priority: P1)

A developer (or AI agent) removes the hardcoded AssemblyType display maps from 2 UI files and replaces them with calls to the enum's built-in `get_display_name()` method. The end user (bake tracker operator) sees no change in behavior — assembly types still display with the same human-readable labels in the Finished Goods tab and Finished Good form.

**Why this priority**: This is the core code fix. If display strings break, the user sees garbled or missing assembly type labels in the UI. Must work correctly before any documentation changes matter.

**Independent Test**: Run the app, navigate to the Finished Goods tab and open a Finished Good form. Verify all assembly types (BARE, ASSEMBLED, GIFT_BOX, SAMPLER, CUSTOM) display with readable names. Run existing tests to confirm no regressions.

**Acceptance Scenarios**:

1. **Given** the finished goods tab displays a list of finished goods with assembly types, **When** the hardcoded map in `finished_goods_tab.py` is removed and replaced with `get_display_name()`, **Then** all assembly types display identical labels as before (e.g., "Bare", "Assembled", "Gift Box", "Sampler", "Custom").
2. **Given** the finished good form shows an assembly type field, **When** the hardcoded map in `finished_good_form.py` is removed and replaced with `get_display_name()`, **Then** the assembly type label displays correctly for all enum values.
3. **Given** a new enum value is added to AssemblyType in the future, **When** only the enum definition is updated with a new value and display name, **Then** the UI automatically picks up the new label without any additional UI code changes.

---

### User Story 2 - Enum Display Pattern Documented in CLAUDE.md (Priority: P2)

A developer or AI agent working on the codebase can look up the correct pattern for displaying enum values in the UI. CLAUDE.md contains a clear "Enum Display Pattern" section with correct and incorrect examples, rationale, references to good codebase examples, and a code review checklist item.

**Why this priority**: Documentation prevents future violations. Without it, the same hardcoded map anti-pattern will recur as new enums or UI components are added.

**Independent Test**: Open CLAUDE.md and verify the "Enum Display Pattern" section exists with correct/incorrect code examples, a "Why This Matters" explanation, references to LossCategory and DepletionReason as good examples, and a code review checklist for enum usage.

**Acceptance Scenarios**:

1. **Given** CLAUDE.md exists with existing pattern documentation, **When** the enum display pattern section is added, **Then** it includes a correct pattern example showing `get_display_name()` usage and an incorrect pattern example showing a hardcoded map.
2. **Given** an AI agent is performing code review, **When** it checks CLAUDE.md for enum standards, **Then** it finds a code review checklist with items covering: no hardcoded enum-to-string maps, enum display methods used, new enums include display methods, and dropdown options use enum helpers.

---

### User Story 3 - All Enums Verified for Pattern Compliance (Priority: P3)

An audit confirms that all enums in the codebase either follow the display pattern or are documented as not needing display methods. No other hardcoded enum display maps exist outside the 2 known violations.

**Why this priority**: Ensures the fix is complete and no other violations were missed by the inspection. Lower priority because the inspection already found 95% compliance.

**Independent Test**: Search the codebase for any remaining hardcoded enum-to-display-string maps. Verify all enums that provide UI-facing labels have `get_display_name()` or equivalent methods.

**Acceptance Scenarios**:

1. **Given** the codebase contains multiple enum types, **When** an audit is performed searching for hardcoded display maps, **Then** no violations are found beyond the 2 already fixed in User Story 1.
2. **Given** enums like LossCategory and DepletionReason already follow the pattern, **When** audited, **Then** they are confirmed as compliant with no changes needed.

---

### Edge Cases

- What happens if `get_display_name()` is called on a newly added enum value that was not added to the display name mapping inside the enum? The enum method should raise a KeyError, making the omission immediately visible rather than silently returning "Unknown".
- What happens if assembly type is None (e.g., a database record with a null assembly_type)? Callers must handle None before calling `get_display_name()` — this is existing behavior and should not change.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST NOT contain hardcoded AssemblyType-to-display-string maps in `finished_goods_tab.py`
- **FR-002**: System MUST NOT contain hardcoded AssemblyType-to-display-string maps in `finished_good_form.py`
- **FR-003**: All UI locations displaying AssemblyType labels MUST use the `AssemblyType.get_display_name()` enum method
- **FR-004**: CLAUDE.md MUST contain an "Enum Display Pattern" section documenting the correct pattern with code examples (correct and incorrect), rationale, and codebase references
- **FR-005**: CLAUDE.md MUST contain a code review checklist covering enum usage standards (no hardcoded maps, display methods required, dropdown helpers used)
- **FR-006**: All enums in the codebase MUST be audited to confirm they follow the display pattern or are documented as not requiring display methods
- **FR-007**: UI display of assembly types MUST remain visually identical after the refactor — no user-visible changes

### Key Entities

- **AssemblyType**: Enum in `src/models/assembly_type.py` with values BARE, ASSEMBLED, GIFT_BOX, SAMPLER, CUSTOM. Already has `get_display_name()` method and `get_assembly_type_choices()` helper.
- **LossCategory**: Enum in `src/models/loss_category.py` — existing good example of correct pattern usage.
- **DepletionReason**: Enum — existing good example of correct pattern usage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero hardcoded enum display maps remain in the codebase (down from 2)
- **SC-002**: Assembly type labels display identically in the UI before and after the change — no user-visible regression
- **SC-003**: CLAUDE.md contains the enum display pattern section with correct/incorrect examples, rationale, and code review checklist
- **SC-004**: 100% of enums in the codebase are verified as compliant or documented as not needing display methods
- **SC-005**: All existing tests pass without modification
