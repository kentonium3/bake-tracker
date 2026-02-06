# Implementation Plan: Enum Display Pattern Standardization

**Branch**: `095-enum-display-pattern-standardization` | **Date**: 2026-02-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/095-enum-display-pattern-standardization/spec.md`

## Summary

Remove 2 sets of hardcoded AssemblyType display maps from UI files and replace them with calls to the existing `AssemblyType.get_display_name()` method. Document the enum display pattern in CLAUDE.md with examples and a code review checklist. Audit all enums for compliance.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode
**Testing**: pytest
**Target Platform**: Desktop (macOS/Windows)
**Project Type**: Single desktop application
**Performance Goals**: N/A (no performance impact — display string lookups)
**Constraints**: UI display must remain visually identical after refactor
**Scale/Scope**: 2 UI files modified, 1 documentation file updated, full enum audit

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | No user-visible changes. Display strings remain identical. |
| II. Data Integrity & FIFO | N/A | No data changes. |
| III. Future-Proof Schema | N/A | No schema changes. |
| IV. Test-Driven Development | PASS | Existing tests validate behavior. Enum `get_display_name()` already tested via usage. |
| V. Layered Architecture | PASS | This change *improves* layer discipline — moving display logic responsibility to model layer. |
| VI.D. API Consistency | PASS | Standardizes enum display interface. |
| VI.G. Code Organization | PASS | Removes dead code (redundant maps), enforces pattern consistency. |
| VII. Schema Change Strategy | N/A | No schema changes. |
| VIII. Pragmatic Aspiration | PASS | No web migration impact. |

No violations. No complexity tracking needed.

## Research Findings

No formal research phase needed. The inspection report (`docs/inspections/hardcoded_maps_categories_dropdowns_inspection.md`) provides complete analysis. Key findings confirmed via code review:

### Violation Inventory (Confirmed)

**File 1: `src/ui/finished_goods_tab.py`**
- Lines 362-374: `_get_assembly_type_display()` method with hardcoded `type_map`
- Lines 376-388: `_get_assembly_type_from_display()` method with hardcoded `display_map` (reverse mapping)
- Used at: lines 353, 593 (forward), lines 396, 634 (reverse)

**File 2: `src/ui/forms/finished_good_form.py`**
- Lines 203-210: Class attribute `_type_to_enum` (display string -> enum)
- Lines 213-220: Class attribute `_enum_to_type` (enum -> display string)
- Used at: lines 342, 736 (forward list), lines 758, 891 (reverse lookup), line 967 (forward lookup)

### Existing Enum Method (Already Correct)

**`src/models/assembly_type.py`**:
- `get_display_name()` (line 40) — returns display string from `ASSEMBLY_TYPE_METADATA` dict
- `get_assembly_type_choices()` (line 273) — returns `[(value, display_name), ...]` for dropdowns
- `__str__()` (line 37) — delegates to `get_display_name()`

### Reverse Mapping Need

Both UI files need to convert display strings BACK to enum values (for dropdown selection handling). The enum currently lacks a `from_display_name()` class method. This will need to be added to `AssemblyType` to eliminate the reverse maps.

**Decision**: Add `AssemblyType.from_display_name(display: str) -> Optional[AssemblyType]` class method to the enum, keeping all mapping logic centralized.

### Other Enums Audit (Pre-scan)

| Enum | File | Has Display Method | UI Hardcoded Map | Status |
|------|------|--------------------|-------------------|--------|
| AssemblyType | `models/assembly_type.py` | Yes (`get_display_name()`, `from_display_name()`) | None (fixed by WP01+WP02) | COMPLIANT |
| LossCategory | `models/enums.py` | Dynamic (`.value.replace("_"," ").title()`) | None | COMPLIANT |
| DepletionReason | `models/enums.py` | No | Yes (`REASON_LABELS` in `ui/dialogs/adjustment_dialog.py`) | VIOLATION* |
| ProductionStatus | `models/enums.py` | No | Not used in UI | N/A |
| FulfillmentStatus | `models/event.py` | No | State machine transitions only, not display | COMPLIANT |
| OutputMode | `models/event.py` | No | Not used in UI | N/A |
| PlanState | `models/event.py` | Dynamic (`.value.replace("_"," ").title()`) | None | COMPLIANT |
| YieldMode | `models/finished_unit.py` | No | Form value conversion only, no display map | COMPLIANT |
| SnapshotType | `models/planning_snapshot.py` | No | Not used in UI | N/A |
| AmendmentType | `models/plan_amendment.py` | No | Not used in UI | N/A |
| PackageStatus | `models/package_status.py` | No | Not used in UI | N/A |

*DepletionReason has a `REASON_LABELS` hardcoded dict in `src/ui/dialogs/adjustment_dialog.py` (lines 32-37) with custom labels like "Spoilage/Waste" and "Gift/Donation". This is a pre-existing violation outside the scope of this feature — documented as follow-up work.

**Audit completed by WP03 (2026-02-06). Summary: 10/11 enums compliant or not applicable. 1 pre-existing violation (DepletionReason) documented for follow-up.**

## Project Structure

### Files Modified (this feature)

```
src/models/assembly_type.py          # Add from_display_name() class method
src/ui/finished_goods_tab.py         # Replace hardcoded maps with enum methods
src/ui/forms/finished_good_form.py   # Replace hardcoded maps with enum methods
CLAUDE.md                            # Add Enum Display Pattern section + code review checklist
```

### Documentation (this feature)

```
kitty-specs/095-enum-display-pattern-standardization/
├── spec.md
├── plan.md              # This file
├── checklists/
│   └── requirements.md
└── tasks.md             # Generated by /spec-kitty.tasks
```

**Structure Decision**: Minimal footprint. 3 source files modified, 1 documentation file updated. No new files created except the `from_display_name()` addition to the existing enum.

## Implementation Approach

### WP01: Add `from_display_name()` to AssemblyType enum

Add a class method to `AssemblyType` that converts a display string back to an enum value. This centralizes the reverse mapping that currently exists as hardcoded dicts in 2 UI files.

```python
@classmethod
def from_display_name(cls, display_name: str) -> Optional["AssemblyType"]:
    """Get AssemblyType from its display name. Returns None if not found."""
    for assembly_type in cls:
        if assembly_type.get_display_name() == display_name:
            return assembly_type
    return None
```

### WP02: Replace hardcoded maps in UI files

**`finished_goods_tab.py`**:
- Replace `_get_assembly_type_display()` body: use `assembly_type.get_display_name()` (keep None guard)
- Replace `_get_assembly_type_from_display()` body: use `AssemblyType.from_display_name(display)`

**`finished_good_form.py`**:
- Remove `_type_to_enum` class attribute — replace usages with `AssemblyType.from_display_name()`
- Remove `_enum_to_type` class attribute — replace usages with `assembly_type.get_display_name()`
- Update dropdown population to use `get_assembly_type_choices()`

### WP03: Document pattern in CLAUDE.md + audit enums

- Add "Enum Display Pattern" section to CLAUDE.md with correct/incorrect examples
- Add enum usage items to the Code Review Checklist in CLAUDE.md
- Complete full audit of all 11 enums listed above
- Document audit findings

## Complexity Tracking

No constitution violations. No complexity justification needed.
