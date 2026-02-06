---
work_package_id: "WP02"
subtasks:
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Replace Hardcoded Maps in UI Files"
phase: "Phase 2 - Core Fix"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-02-06T01:55:28Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 -- Replace Hardcoded Maps in UI Files

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
spec-kitty implement WP02 --base WP01
```

Depends on WP01 (needs `from_display_name()` method).

---

## Objectives & Success Criteria

- Remove all hardcoded `AssemblyType` display maps from `src/ui/finished_goods_tab.py` and `src/ui/forms/finished_good_form.py`.
- Replace every usage with calls to `get_display_name()`, `from_display_name()`, or `get_assembly_type_choices()`.
- UI display of assembly types must remain **visually identical** -- no user-visible changes.
- All existing tests continue to pass.

**Success criteria (FR-001 through FR-003, FR-007):**
- Zero hardcoded AssemblyType-to-string maps in either file
- Assembly types display with same labels in Finished Goods tab and form
- Dropdown population works correctly
- Selection/filtering by assembly type works correctly

## Context & Constraints

- **Spec**: `kitty-specs/095-enum-display-pattern-standardization/spec.md`
- **Plan**: `kitty-specs/095-enum-display-pattern-standardization/plan.md`
- **Constitution**: `.kittify/memory/constitution.md` -- Principle V (Layered Architecture: display logic belongs in model layer)

**Key files to modify:**
- `src/ui/finished_goods_tab.py` -- 2 methods with hardcoded maps
- `src/ui/forms/finished_good_form.py` -- 2 class attributes with hardcoded maps

**Key imports to add (from `src.models.assembly_type`):**
- `AssemblyType` (already imported in both files)
- `get_assembly_type_choices` (may need to be added to imports)

**Reference: Correct patterns already in codebase:**
- `src/ui/forms/record_production_dialog.py:668` -- `LossCategory` enum used dynamically (no hardcoded map)

## Subtasks & Detailed Guidance

### Subtask T004 -- Replace `_get_assembly_type_display()` in finished_goods_tab.py

- **Purpose**: Replace the forward lookup method that converts `AssemblyType` enum to display string.
- **Steps**:
  1. Open `src/ui/finished_goods_tab.py`
  2. Find the `_get_assembly_type_display()` method (around line 362):
     ```python
     def _get_assembly_type_display(self, assembly_type: Optional[AssemblyType]) -> str:
         """Convert AssemblyType enum to display string."""
         if not assembly_type:
             return "Custom Order"
         type_map = {
             AssemblyType.BARE: "Bare",
             AssemblyType.CUSTOM_ORDER: "Custom Order",
             AssemblyType.GIFT_BOX: "Gift Box",
             AssemblyType.VARIETY_PACK: "Variety Pack",
             AssemblyType.HOLIDAY_SET: "Holiday Set",
             AssemblyType.BULK_PACK: "Bulk Pack",
         }
         return type_map.get(assembly_type, "Unknown")
     ```
  3. Replace with:
     ```python
     def _get_assembly_type_display(self, assembly_type: Optional[AssemblyType]) -> str:
         """Convert AssemblyType enum to display string."""
         if not assembly_type:
             return "Custom Order"
         return assembly_type.get_display_name()
     ```
  4. **CRITICAL**: Preserve the `None` guard. When `assembly_type` is `None`, it defaults to "Custom Order". This is existing behavior and must not change.
  5. Note: The old code had a fallback to "Unknown" for unrecognized values. Since `get_display_name()` uses a dict keyed by enum members, it will raise `KeyError` for non-enum values. This is actually better -- it makes bugs immediately visible rather than silently showing "Unknown".

- **Files**: `src/ui/finished_goods_tab.py`
- **Parallel?**: Yes (can proceed alongside T006+T007+T008 in the other file)
- **Notes**: This method is called at lines 353 and 593. No changes needed at call sites.

### Subtask T005 -- Replace `_get_assembly_type_from_display()` in finished_goods_tab.py

- **Purpose**: Replace the reverse lookup method that converts display string back to `AssemblyType` enum.
- **Steps**:
  1. Find the `_get_assembly_type_from_display()` method (around line 376):
     ```python
     def _get_assembly_type_from_display(self, display: str) -> Optional[AssemblyType]:
         """Convert display string to AssemblyType enum."""
         if display == "All Types":
             return None
         display_map = {
             "Bare": AssemblyType.BARE,
             "Custom Order": AssemblyType.CUSTOM_ORDER,
             "Gift Box": AssemblyType.GIFT_BOX,
             "Variety Pack": AssemblyType.VARIETY_PACK,
             "Holiday Set": AssemblyType.HOLIDAY_SET,
             "Bulk Pack": AssemblyType.BULK_PACK,
         }
         return display_map.get(display)
     ```
  2. Replace with:
     ```python
     def _get_assembly_type_from_display(self, display: str) -> Optional[AssemblyType]:
         """Convert display string to AssemblyType enum."""
         if display == "All Types":
             return None
         return AssemblyType.from_display_name(display)
     ```
  3. **CRITICAL**: Preserve the "All Types" guard. This is a UI filter option that means "no filter", not an actual assembly type.
  4. `from_display_name()` returns `None` for unrecognized strings, matching the old `display_map.get(display)` behavior.

- **Files**: `src/ui/finished_goods_tab.py`
- **Parallel?**: Yes (can proceed alongside T006+T007+T008)
- **Notes**: Called at lines 396 and 634. No changes needed at call sites.

### Subtask T006 -- Remove `_type_to_enum` from finished_good_form.py

- **Purpose**: Remove the class-level forward mapping dict and replace all usages with `AssemblyType.from_display_name()`.
- **Steps**:
  1. Open `src/ui/forms/finished_good_form.py`
  2. Delete the `_type_to_enum` class attribute (lines 203-210):
     ```python
     _type_to_enum: Dict[str, AssemblyType] = {
         "Bare": AssemblyType.BARE,
         "Custom Order": AssemblyType.CUSTOM_ORDER,
         "Gift Box": AssemblyType.GIFT_BOX,
         "Variety Pack": AssemblyType.VARIETY_PACK,
         "Holiday Set": AssemblyType.HOLIDAY_SET,
         "Bulk Pack": AssemblyType.BULK_PACK,
     }
     ```
  3. Find and replace all usages:
     - **Line 342**: `type_values = list(self._type_to_enum.keys())`
       Replace with: `type_values = [at.get_display_name() for at in AssemblyType]`
     - **Line 736**: `return list(self._type_to_enum.keys())`
       Replace with: `return [at.get_display_name() for at in AssemblyType]`
     - **Line 967**: `enum_value = self._type_to_enum.get(selected, AssemblyType.BARE)`
       Replace with: `enum_value = AssemblyType.from_display_name(selected) or AssemblyType.BARE`
       (The `or AssemblyType.BARE` preserves the fallback default behavior)

- **Files**: `src/ui/forms/finished_good_form.py`
- **Parallel?**: Yes (different file from T004+T005)
- **Notes**: Verify the `Dict` import from `typing` is still needed for other attributes. If not, clean it up. Also ensure `get_assembly_type_choices` is imported from `src.models.assembly_type` if needed.

### Subtask T007 -- Remove `_enum_to_type` from finished_good_form.py

- **Purpose**: Remove the class-level reverse mapping dict and replace all usages with `get_display_name()`.
- **Steps**:
  1. Delete the `_enum_to_type` class attribute (lines 213-220):
     ```python
     _enum_to_type: Dict[AssemblyType, str] = {
         AssemblyType.BARE: "Bare",
         AssemblyType.CUSTOM_ORDER: "Custom Order",
         AssemblyType.GIFT_BOX: "Gift Box",
         AssemblyType.VARIETY_PACK: "Variety Pack",
         AssemblyType.HOLIDAY_SET: "Holiday Set",
         AssemblyType.BULK_PACK: "Bulk Pack",
     }
     ```
  2. Find and replace all usages:
     - **Line 758**: `type_display = self._enum_to_type.get(fg.assembly_type, "Custom Order")`
       Replace with: `type_display = fg.assembly_type.get_display_name() if fg.assembly_type else "Custom Order"`
     - **Line 891**: `type_display = self._enum_to_type.get(...)` (check exact context)
       Replace with similar pattern using `get_display_name()` with appropriate None guard

- **Files**: `src/ui/forms/finished_good_form.py`
- **Parallel?**: Yes (same file as T006 but different attribute)
- **Notes**: When `assembly_type` could be `None`, always guard with a conditional before calling `get_display_name()`. The old code used `.get(key, "Custom Order")` as a default -- preserve this fallback.

### Subtask T008 -- Update dropdown population to use `get_assembly_type_choices()`

- **Purpose**: Where appropriate, use the existing `get_assembly_type_choices()` helper for populating dropdown/combobox options.
- **Steps**:
  1. Review how the assembly type dropdown is populated in `finished_good_form.py`.
  2. The `get_assembly_type_choices()` function returns `[(value, display_name), ...]` which may or may not match the current dropdown format.
  3. If the dropdown uses display names as values (which it appears to), then the list comprehension from T006 (`[at.get_display_name() for at in AssemblyType]`) is the correct replacement.
  4. Only use `get_assembly_type_choices()` if the dropdown needs both the value and display name (e.g., for a combobox that shows display names but stores values).
  5. Add `from src.models.assembly_type import get_assembly_type_choices` to imports if used.

- **Files**: `src/ui/forms/finished_good_form.py`
- **Parallel?**: Yes (same file, but logical separate concern)
- **Notes**: This subtask may be a no-op if the list comprehension from T006 already covers all dropdown population. Evaluate and skip if unnecessary.

### Subtask T009 -- Run existing tests for regression check

- **Purpose**: Confirm all UI changes work correctly and no tests break.
- **Steps**:
  1. Run: `./run-tests.sh -v`
  2. All existing tests should pass unchanged.
  3. If any test fails, investigate the specific failure. Common issues:
     - Import errors (if you removed imports that are still needed)
     - Attribute errors (if code still references `_type_to_enum` or `_enum_to_type`)
  4. Fix any issues found.

- **Files**: None (test runner only)
- **Parallel?**: No (must run after all code changes)

## Risks & Mitigations

- **Risk**: Display strings from `get_display_name()` don't exactly match the hardcoded strings.
  **Mitigation**: Verified -- `ASSEMBLY_TYPE_METADATA` contains identical strings: "Bare", "Custom Order", "Gift Box", "Variety Pack", "Holiday Set", "Bulk Pack".

- **Risk**: None handling differs between old maps (`.get()` returns `None`) and new methods.
  **Mitigation**: Explicit None guards preserved in every replacement. `from_display_name()` also returns `None` for unrecognized strings.

- **Risk**: Removing class attributes breaks subclasses or external references.
  **Mitigation**: These are private attributes (prefixed with `_`). No external usage expected.

## Definition of Done Checklist

- [ ] No `type_map` dict in `finished_goods_tab.py`
- [ ] No `display_map` dict in `finished_goods_tab.py`
- [ ] No `_type_to_enum` attribute in `finished_good_form.py`
- [ ] No `_enum_to_type` attribute in `finished_good_form.py`
- [ ] All assembly type display uses `get_display_name()`
- [ ] All reverse lookups use `AssemblyType.from_display_name()`
- [ ] None handling preserved (no crashes on null assembly types)
- [ ] All existing tests pass

## Review Guidance

- **Verify display string parity**: Compare old hardcoded strings with `ASSEMBLY_TYPE_METADATA` values -- they must be identical.
- **Verify None guards**: Every place that previously handled `None` assembly types must still handle them.
- **Verify "All Types" filter**: The finished_goods_tab filter option "All Types" must still work (returns None to show all).
- **Verify dropdown population**: Assembly type dropdowns must show all 6 types in the form.
- **Grep check**: `grep -rn "type_map\|display_map\|_type_to_enum\|_enum_to_type" src/ui/` should return zero results for AssemblyType maps.

## Activity Log

- 2026-02-06T01:55:28Z -- system -- lane=planned -- Prompt created.
