# Cursor Code Review Prompt - Feature 041: Manual Inventory Adjustments

## Your Role

You are a senior software engineer performing an independent code review. Approach this as if discovering the feature for the first time. Read the spec first, form your own expectations, then evaluate the implementation.

## Feature Context

**Feature:** 041 - Manual Inventory Adjustments
**User Goal:** Record manual inventory depletions (spoilage, gifts, corrections, ad hoc usage) to maintain accurate inventory records when real-world changes occur outside the application
**Spec File:** `kitty-specs/041-manual-inventory-adjustments/spec.md`

## Files to Review

```
src/models/enums.py
src/models/inventory_depletion.py
src/models/inventory_item.py
src/models/__init__.py
src/services/inventory_item_service.py
src/tests/services/test_inventory_adjustment.py
src/ui/dialogs/__init__.py
src/ui/dialogs/adjustment_dialog.py
src/ui/inventory_tab.py
```

## Spec Files (Read First)

```
kitty-specs/041-manual-inventory-adjustments/spec.md
kitty-specs/041-manual-inventory-adjustments/data-model.md
docs/design/_F041_manual_inventory_adjust.md
```

## Verification Commands
Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

Run from worktree: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/041-manual-inventory-adjustments`

```bash
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Imports
PYTHONPATH=. python3 -c "
from src.models.enums import DepletionReason
from src.models.inventory_depletion import InventoryDepletion
from src.services.inventory_item_service import manual_adjustment, get_depletion_history
from src.ui.dialogs.adjustment_dialog import AdjustmentDialog
print('All imports successful')
"

# Tests
PYTHONPATH=. python3 -m pytest src/tests/services/test_inventory_adjustment.py -v --tb=short
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -50
```

**If ANY verification fails, STOP and report as blocking issue.**

## Review Instructions

1. **Read the spec** (`spec.md`) to understand intended behavior
2. **Form expectations** about how this SHOULD work before reading code
3. **Run verification commands** - stop if failures
4. **Review implementation** comparing against your expectations
5. **Write report** to `docs/code-reviews/cursor-F041-review.md`

Focus on:
- Logic gaps or edge cases
- Data integrity risks (especially negative inventory, immutable audit records)
- User workflow friction
- Deviation from codebase patterns
- Session management (see CLAUDE.md - CRITICAL)
- Validation completeness (quantity > 0, quantity <= available, notes required for OTHER)

## Report Template

Write your report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F041-review.md`

```markdown
# Code Review Report: F041 - Manual Inventory Adjustments

**Reviewer:** Cursor (Independent Review)
**Date:** [YYYY-MM-DD]
**Feature Spec:** kitty-specs/041-manual-inventory-adjustments/spec.md

## Executive Summary
[2-3 sentences: What this feature does, overall assessment, key concerns if any]

## Review Scope
**Files Modified:**
- src/models/enums.py
- src/models/inventory_depletion.py (NEW)
- src/models/inventory_item.py
- src/models/__init__.py
- src/services/inventory_item_service.py
- src/tests/services/test_inventory_adjustment.py (NEW)
- src/ui/dialogs/__init__.py (NEW)
- src/ui/dialogs/adjustment_dialog.py (NEW)
- src/ui/inventory_tab.py

**Dependencies Reviewed:**
- [any related systems, services, or data models examined]

## Environment Verification
**Commands Run:**
```bash
[list verification commands executed]
```

**Results:**
- [ ] All imports successful
- [ ] All tests passed
- [ ] Database migrations valid (if applicable)

[If any failed: STOP - blocking issues must be resolved before continuing]

## Findings

### Critical Issues
[Issues that could cause data loss, corruption, crashes, or security problems]

**[Issue Title]**
- **Location:** [file:line or general area]
- **Problem:** [what's wrong]
- **Impact:** [what could happen]
- **Recommendation:** [how to fix]

### Major Concerns
[Issues affecting core functionality, user workflows, or maintainability]

### Minor Issues
[Code quality, style inconsistencies, optimization opportunities]

### Positive Observations
[What was done well - good patterns, clever solutions, solid error handling]

## Spec Compliance
- [ ] Meets stated requirements (FR-001 through FR-016)
- [ ] Handles edge cases appropriately (zero quantity, decimal quantities)
- [ ] Error handling adequate
- [ ] User workflow feels natural
- [ ] Live preview updates within 100ms (SC-003)

[Note any gaps between spec and implementation]

## Code Quality Assessment

**Consistency with Codebase:**
[Does this follow established patterns? Any deviations and why they matter?]

**Maintainability:**
[How easy will this be for future developers to understand and modify?]

**Test Coverage:**
[Are the right things tested? Any obvious gaps?]

## Recommendations Priority

**Must Fix Before Merge:**
1. [Critical/blocking items]

**Should Fix Soon:**
1. [Important but not blocking]

**Consider for Future:**
1. [Nice-to-haves, refactoring opportunities]

## Overall Assessment
[Pass/Pass with minor fixes/Needs revision/Major rework needed]

[Final paragraph: Would you ship this to users? Why or why not?]
```

## Context Notes

- SQLAlchemy 2.x, CustomTkinter UI, pytest
- This is a depletions-only feature - inventory increases go through Purchase workflow
- DepletionReason enum includes both automatic (PRODUCTION, ASSEMBLY) and manual reasons
- InventoryDepletion records are immutable (audit trail)
- User identifier hardcoded as "desktop-user" (single-user desktop app)
- Session management pattern is CRITICAL - see CLAUDE.md
- Cost calculation: quantity_depleted * unit_cost
- History sorted by depletion_date DESC (newest first)
