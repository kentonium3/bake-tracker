# F095: Enum Display Pattern Standardization

**Version**: 1.0
**Priority**: MEDIUM
**Type**: Code Quality Enhancement

---

## Executive Summary

Current gaps:
- ❌ 2 UI files maintain hardcoded AssemblyType display maps
- ❌ AssemblyType enum's `get_display_name()` method ignored by UI
- ❌ Pattern not documented in code standards
- ❌ No prevention of future violations

This spec eliminates the 2 hardcoded enum-to-string maps, documents the correct enum display pattern in CLAUDE.md, and establishes code review standards to prevent future violations.

---

## Problem Statement

**Current State (INCONSISTENT):**
```
AssemblyType Enum
├─ ✅ Has get_display_name() method in assembly_type.py
├─ ❌ finished_goods_tab.py maintains separate display map (lines 367-372)
├─ ❌ finished_good_form.py maintains separate display map (lines 214-219)
└─ ❌ Adding BARE required updating 3 places (enum + 2 maps)

Pattern Documentation
├─ ❌ Correct enum pattern not in CLAUDE.md
├─ ❌ No code review checklist item
└─ ❌ Easy to repeat this mistake
```

**Target State (STANDARDIZED):**
```
AssemblyType Enum
├─ ✅ Has get_display_name() method (unchanged)
├─ ✅ finished_goods_tab.py uses enum method directly
├─ ✅ finished_good_form.py uses enum method directly
└─ ✅ Future enum changes require 1 update, not 3

Pattern Documentation
├─ ✅ Enum display pattern documented in CLAUDE.md
├─ ✅ Code review checklist includes enum pattern check
└─ ✅ Pattern enforced consistently
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Cursor Inspection Report**
   - Find `docs/inspections/hardcoded_maps_categories_dropdowns_inspection.md` - full analysis
   - Find `docs/inspections/hardcoded_maps_categories_summary.md` - executive summary
   - Study Section 1: Enum Display Violations (only 2 violations found)
   - Note that 95% of dropdowns already follow correct patterns

2. **AssemblyType Enum Implementation**
   - Find `src/models/assembly_type.py` - enum definition
   - Study `get_display_name()` method - already provides display strings
   - Note `get_assembly_type_choices()` helper - returns list of tuples for dropdowns

3. **Current Violations**
   - Find `src/ui/finished_goods_tab.py:367-372` - hardcoded display map
   - Find `src/ui/finished_good_form.py:214-219` - hardcoded display map
   - Study how these maps are currently used
   - Note the duplication of logic already in enum

4. **Good Examples (Already Correct)**
   - Find `src/ui/consumption_form.py` - LossCategory enum used correctly
   - Find `src/models/loss_category.py` - example of enum with display labels
   - Study how these implementations avoid hardcoded maps

---

## Requirements Reference

This specification implements:
- **Code Quality Principle VI.G**: Code Organization Patterns
  - No dead code (remove redundant maps)
  - Pattern consistency
- **Code Quality Principle VI.D**: API Consistency & Contracts
  - Predictable interfaces

From: `docs/design/code_quality_principles_revised.md` (v1.0)

Also addresses findings from:
- `docs/inspections/hardcoded_maps_categories_dropdowns_inspection.md` - Section 1: Enum Display Violations

---

## Functional Requirements

### FR-1: Remove Hardcoded AssemblyType Maps

**What it must do:**
- Remove hardcoded display map in `finished_goods_tab.py:367-372`
- Remove hardcoded display map in `finished_good_form.py:214-219`
- Replace all map usage with `assembly_type.get_display_name()` calls
- Verify UI displays correctly after changes

**Pattern reference:** Study `consumption_form.py` and `LossCategory` enum - already using enum methods correctly

**Current pattern (WRONG):**
```python
# finished_goods_tab.py:367-372
type_display_map = {
    AssemblyType.BARE: "Bare",
    AssemblyType.ASSEMBLED: "Assembled",
    # ... etc
}
display = type_display_map.get(assembly_type, "Unknown")
```

**Target pattern (CORRECT):**
```python
# Use enum method directly
display = assembly_type.get_display_name()
```

**Success criteria:**
- [ ] No hardcoded AssemblyType display maps in finished_goods_tab.py
- [ ] No hardcoded AssemblyType display maps in finished_good_form.py
- [ ] All AssemblyType display uses `get_display_name()` method
- [ ] UI displays assembly types correctly
- [ ] All tests pass

---

### FR-2: Document Enum Display Pattern

**What it must do:**
- Add "Enum Display Pattern" section to CLAUDE.md
- Document when to use enum methods vs hardcoded maps (always use enum)
- Provide code examples of correct and incorrect patterns
- Reference LossCategory and DepletionReason as good examples

**Pattern reference:** Study existing CLAUDE.md documentation style, add new pattern section

**Documentation requirements:**

**Section to add to CLAUDE.md:**
```markdown
## Enum Display Pattern

**ALWAYS use enum methods for display strings, NEVER create hardcoded maps.**

### Correct Pattern ✅

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

# UI usage (ui/example_form.py)
display = example_type.get_display_name()  # ✅ Correct
```

### Incorrect Pattern ❌

```python
# UI file (ui/example_form.py)
# ❌ WRONG - Hardcoded map duplicates enum logic
type_map = {
    ExampleType.VALUE_A: "Value A",
    ExampleType.VALUE_B: "Value B",
}
display = type_map.get(example_type)  # ❌ Don't do this
```

### Why This Matters

- **Single source of truth**: Display logic lives in enum, not scattered in UI
- **Easier updates**: Adding new enum value requires 1 change, not N changes
- **Type safety**: Enum methods are type-checked, maps are not
- **Consistency**: All code uses same display strings automatically

### Good Examples in Codebase

- `LossCategory` - Uses centralized display labels correctly
- `DepletionReason` - Enum methods used throughout UI
- `MaterialCategory` - Database-driven, not hardcoded maps
```

**Success criteria:**
- [ ] CLAUDE.md contains "Enum Display Pattern" section
- [ ] Pattern includes correct and incorrect examples
- [ ] References to good examples in codebase
- [ ] Clear explanation of why pattern matters

---

### FR-3: Add Code Review Checklist Item

**What it must do:**
- Add enum display pattern check to code review process
- Create checklist item for AI agents to verify
- Include in pull request template (if exists)
- Document in AGENTS.md for multi-agent review

**Pattern reference:** Study existing code review documentation, add enum pattern check

**Checklist item to add:**
```markdown
## Code Review Checklist

### Enum Usage
- [ ] No hardcoded enum-to-string maps in UI code
- [ ] Enum display methods used instead of manual mapping
- [ ] New enums include `get_display_name()` or similar method
- [ ] Dropdown options use enum helper methods
```

**Success criteria:**
- [ ] Code review checklist includes enum pattern check
- [ ] AGENTS.md documents enum pattern requirement
- [ ] AI agents instructed to flag enum map violations
- [ ] Pattern becomes part of standard code review

---

### FR-4: Verify Other Enums Follow Pattern

**What it must do:**
- Audit all other enums in codebase
- Verify they have display methods
- Check that UI code uses enum methods (not maps)
- Document any other enums that need display methods added

**Pattern reference:** Use Cursor inspection findings - LossCategory and DepletionReason already correct

**Enums to verify (from inspection):**
- ✅ LossCategory - already has display labels, used correctly
- ✅ DepletionReason - already uses enum methods
- ✅ AssemblyType - will be fixed by FR-1
- Check any other enums not in inspection report

**Success criteria:**
- [ ] All enums audited for display methods
- [ ] No other hardcoded enum maps found
- [ ] Any enums lacking display methods documented
- [ ] Plan for adding display methods (if needed) documented

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Adding display methods to enums that don't need them
- ❌ Creating enum helper utilities (e.g., generic `get_enum_choices()`) - YAGNI for now
- ❌ Automated linting/static analysis for pattern violations - manual code review sufficient
- ❌ Refactoring enums that already work correctly
- ❌ Category management (that's F096)

---

## Success Criteria

**Complete when:**

### Code Fixes
- [ ] No hardcoded AssemblyType maps in finished_goods_tab.py
- [ ] No hardcoded AssemblyType maps in finished_good_form.py
- [ ] All AssemblyType display uses enum methods
- [ ] UI displays assembly types correctly
- [ ] No regression in functionality

### Documentation
- [ ] CLAUDE.md contains enum display pattern section
- [ ] Pattern documented with examples (correct and incorrect)
- [ ] Good examples from codebase referenced
- [ ] Why pattern matters explained clearly

### Standards
- [ ] Code review checklist includes enum pattern check
- [ ] AGENTS.md documents pattern requirement
- [ ] All other enums verified to follow pattern
- [ ] No other violations found

### Quality
- [ ] Follows Code Quality Principle VI.G (Code Organization)
- [ ] Follows Code Quality Principle VI.D (API Consistency)
- [ ] Pattern consistency enforced
- [ ] Single source of truth for enum display logic

---

## Architecture Principles

### Single Source of Truth

**Enum display logic belongs in enum definition:**
- Display strings defined once in enum
- UI code calls enum method
- Changes to display strings happen in one place
- Type safety enforced by enum methods

### Pattern Over Duplication

**Avoid duplicating enum logic:**
- Don't create maps that mirror enum structure
- Don't hardcode enum values in multiple places
- Use enum methods consistently
- Document the pattern for future developers

### Code Organization

**Related code lives together:**
- Enum definition and display logic in same file
- UI code references enum, doesn't duplicate it
- Clear separation of concerns

---

## Constitutional Compliance

✅ **Principle VI.G: Code Organization Patterns**
- Removes dead code (redundant maps)
- Maintains pattern consistency
- Documents proper organization

✅ **Principle VI.D: API Consistency & Contracts**
- Standardizes enum usage pattern
- Predictable interface (always use enum methods)
- Type-safe display strings

✅ **Principle V: Layered Architecture Discipline**
- Business logic (display strings) in model layer
- UI layer uses model interface
- Clear separation maintained

---

## Risk Considerations

**Risk: Breaking UI display**
- Removing maps might break assembly type display
- Mitigation: Enum methods already exist and work
- Mitigation: Test all UI locations that display assembly types

**Risk: Missing enum methods**
- Other enums might not have display methods
- Mitigation: FR-4 audits all enums
- Mitigation: Document any missing methods for future work

**Risk: Pattern not followed in future**
- New code might create hardcoded maps again
- Mitigation: Code review checklist catches violations
- Mitigation: CLAUDE.md documents the pattern

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `docs/inspections/hardcoded_maps_categories_dropdowns_inspection.md` → understand scope (only 2 violations)
- Study `src/models/assembly_type.py` → see existing display method
- Study `src/ui/consumption_form.py` → see correct pattern in action
- Study `src/models/loss_category.py` → see another good example

**Key Patterns to Copy:**
- LossCategory enum usage → apply to AssemblyType
- Consumption form enum usage → replicate in finished goods files
- CLAUDE.md documentation style → apply to enum pattern section

**Focus Areas:**
- This is a small, focused fix (only 2 files)
- Documentation is as important as the code fix
- Pattern enforcement prevents future violations
- Code review standards ensure long-term compliance

**Implementation Note:**
This is a quick win (1-2 hours effort) that establishes a code quality standard. The real value is in documenting the pattern and preventing future violations, not just fixing the 2 existing instances.

**Cursor Inspection Context:**
Per `docs/inspections/hardcoded_maps_categories_summary.md`:
- 60+ dropdowns analyzed, only 2 violations found (95% correct)
- High code quality overall
- Clear patterns already exist and are mostly followed
- This spec addresses the 5% that deviate from best practice

---

**END OF SPECIFICATION**
