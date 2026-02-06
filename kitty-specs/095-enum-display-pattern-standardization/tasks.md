# Work Packages: Enum Display Pattern Standardization

**Inputs**: Design documents from `kitty-specs/095-enum-display-pattern-standardization/`
**Prerequisites**: plan.md (required), spec.md (user stories)

**Tests**: Not explicitly requested. Existing tests must continue to pass.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: Add Reverse Lookup to AssemblyType Enum (Priority: P1)

**Goal**: Add `from_display_name()` class method to `AssemblyType` so UI files can look up enums from display strings without hardcoded maps.
**Independent Test**: Call `AssemblyType.from_display_name("Gift Box")` and verify it returns `AssemblyType.GIFT_BOX`. Call with unknown string and verify `None`.
**Prompt**: `tasks/WP01-add-reverse-lookup-to-assembly-type.md`
**Estimated size**: ~200 lines

### Included Subtasks
- [x] T001 Add `from_display_name()` class method to `AssemblyType` in `src/models/assembly_type.py`
- [x] T002 Verify `get_display_name()` and `from_display_name()` are symmetric for all enum values
- [x] T003 Run existing tests to confirm no regressions

### Implementation Notes
- Add a single `@classmethod` that iterates `cls` members and matches on `get_display_name()`
- Returns `Optional[AssemblyType]` — `None` for unrecognized strings
- This is a prerequisite for WP02 since the UI files need `from_display_name()` to replace their reverse maps

### Parallel Opportunities
- None — this is a single-file change.

### Dependencies
- None (starting package).

### Risks & Mitigations
- Minimal risk. Adding a method to an existing enum with no side effects.

---

## Work Package WP02: Replace Hardcoded Maps in UI Files (Priority: P1) MVP

**Goal**: Remove all hardcoded AssemblyType display maps from `finished_goods_tab.py` and `finished_good_form.py`, replacing them with calls to `get_display_name()`, `from_display_name()`, and `get_assembly_type_choices()`.
**Independent Test**: Run the application, navigate to Finished Goods tab, verify assembly types display correctly. Open Finished Good form, verify dropdown populates and selection works.
**Prompt**: `tasks/WP02-replace-hardcoded-maps-in-ui.md`
**Estimated size**: ~450 lines

### Included Subtasks
- [ ] T004 Replace `_get_assembly_type_display()` in `src/ui/finished_goods_tab.py` with `get_display_name()` call
- [ ] T005 Replace `_get_assembly_type_from_display()` in `src/ui/finished_goods_tab.py` with `AssemblyType.from_display_name()` call
- [ ] T006 Remove `_type_to_enum` class attribute from `src/ui/forms/finished_good_form.py` and replace all usages with `AssemblyType.from_display_name()`
- [ ] T007 Remove `_enum_to_type` class attribute from `src/ui/forms/finished_good_form.py` and replace all usages with `get_display_name()`
- [ ] T008 Update dropdown population in `finished_good_form.py` to use `get_assembly_type_choices()` where applicable
- [ ] T009 Run existing tests to confirm no regressions

### Implementation Notes
- **finished_goods_tab.py**: The `_get_assembly_type_display()` method (lines 362-374) has a None guard that defaults to "Custom Order" — preserve this behavior. The `_get_assembly_type_from_display()` method (lines 376-388) filters out "All Types" — preserve this guard.
- **finished_good_form.py**: Class attributes `_type_to_enum` (lines 203-210) and `_enum_to_type` (lines 213-220) are used at 5 locations (lines 342, 736, 758, 891, 967). Each usage must be replaced with the appropriate enum method.
- Import `get_assembly_type_choices` from `src.models.assembly_type` where needed.

### Parallel Opportunities
- T004+T005 (finished_goods_tab.py) can proceed in parallel with T006+T007+T008 (finished_good_form.py) if split across agents.

### Dependencies
- Depends on WP01 (needs `from_display_name()` method).

### Risks & Mitigations
- **Risk**: Display strings from `get_display_name()` might not exactly match the hardcoded strings. **Mitigation**: Verified — they match exactly (both source from `ASSEMBLY_TYPE_METADATA`).
- **Risk**: None handling differs between old and new code. **Mitigation**: Preserve explicit None guards in both files.

---

## Work Package WP03: Document Pattern and Audit Enums (Priority: P2)

**Goal**: Add "Enum Display Pattern" section and code review checklist to CLAUDE.md. Audit all 11 enums in the codebase for compliance.
**Independent Test**: Open CLAUDE.md and verify the enum pattern section exists with correct/incorrect examples and code review checklist. Verify audit findings are documented.
**Prompt**: `tasks/WP03-document-pattern-and-audit.md`
**Estimated size**: ~350 lines

### Included Subtasks
- [ ] T010 [P] Add "Enum Display Pattern" section to `CLAUDE.md` with correct/incorrect code examples, rationale, and references to good codebase examples
- [ ] T011 [P] Add enum usage items to code review checklist in `CLAUDE.md`
- [ ] T012 Audit all enums in `src/models/` for display method compliance (AssemblyType, LossCategory, DepletionReason, ProductionStatus, FulfillmentStatus, OutputMode, PlanState, YieldMode, SnapshotType, AmendmentType, PackageStatus)
- [ ] T013 Document audit findings in the plan or as inline comments in the spec

### Implementation Notes
- Place the "Enum Display Pattern" section after the "Validation Pattern (F094)" section in CLAUDE.md (follows the existing pattern documentation style).
- Include the `from_display_name()` pattern (added in WP01) in the "Correct Pattern" example.
- Code review checklist items should be added to the existing CLAUDE.md structure — look for a natural place or create a new "Code Review Checklist" subsection.
- Audit should check: (a) does the enum have a display method? (b) are there hardcoded maps in UI for this enum? Enums that are not displayed in the UI (e.g., internal state machines) don't need display methods.

### Parallel Opportunities
- T010+T011 (documentation) can proceed in parallel with T012 (audit) since they touch different files.

### Dependencies
- Depends on WP02 (audit should verify the fixes are in place).

### Risks & Mitigations
- **Risk**: Audit finds additional violations not in the inspection report. **Mitigation**: Document them but don't fix in this feature unless trivial. Out-of-scope fixes should be tracked as follow-up work.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03
- **Parallelization**: WP01 is small and fast (single method addition). WP02 has two independent files that can be parallelized. WP03 documentation and audit can be parallelized.
- **MVP Scope**: WP01 + WP02 (core code fixes). WP03 is important for long-term value but the code is correct after WP02.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Add `from_display_name()` to AssemblyType | WP01 | P1 | No |
| T002 | Verify symmetry of display name methods | WP01 | P1 | No |
| T003 | Run tests for WP01 regression check | WP01 | P1 | No |
| T004 | Replace `_get_assembly_type_display()` in finished_goods_tab.py | WP02 | P1 | Yes |
| T005 | Replace `_get_assembly_type_from_display()` in finished_goods_tab.py | WP02 | P1 | Yes |
| T006 | Remove `_type_to_enum` from finished_good_form.py | WP02 | P1 | Yes |
| T007 | Remove `_enum_to_type` from finished_good_form.py | WP02 | P1 | Yes |
| T008 | Update dropdown population in finished_good_form.py | WP02 | P1 | Yes |
| T009 | Run tests for WP02 regression check | WP02 | P1 | No |
| T010 | Add "Enum Display Pattern" section to CLAUDE.md | WP03 | P2 | Yes |
| T011 | Add enum code review checklist to CLAUDE.md | WP03 | P2 | Yes |
| T012 | Audit all enums for display method compliance | WP03 | P2 | Yes |
| T013 | Document audit findings | WP03 | P2 | No |
