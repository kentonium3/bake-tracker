# Feature 004 Work Extraction Plan

**Date**: 2025-11-16
**Purpose**: Extract completed work from over-scoped Feature 004 into properly-scoped sub-features

---

## Work Assessment

### Completed Work in 004 Worktree

**Models** (production-ready):
- ✅ `finished_unit.py` - Complete, well-documented, includes migration factory method
- ✅ `composition.py` - Complete, includes polymorphic validation, circular reference checks
- ✅ `assembly_type.py` - Enum for assembly categorization
- ✅ Updated `finished_good.py` - Refactored for assembly usage

**Status**: These files represent substantial completed work that should be preserved.

---

## Extraction Strategy

### Step 1: Create Work Package Patches

**YOU run these commands** to extract completed code:

```bash
cd C:\Users\Kent\Vaults-repos\bake-tracker\.worktrees\004-finishedunit-model-refactoring

# Create patches directory
mkdir -p ../../archive/2025-11-feature-004-patches

# Extract FinishedUnit model
git diff main -- src/models/finished_unit.py > ../../archive/2025-11-feature-004-patches/01-finished-unit-model.patch

# Extract Composition model
git diff main -- src/models/composition.py > ../../archive/2025-11-feature-004-patches/02-composition-model.patch

# Extract AssemblyType enum
git diff main -- src/models/assembly_type.py > ../../archive/2025-11-feature-004-patches/03-assembly-type-enum.patch

# Extract FinishedGood updates
git diff main -- src/models/finished_good.py > ../../archive/2025-11-feature-004-patches/04-finished-good-updates.patch

# Extract __init__.py updates (if any)
git diff main -- src/models/__init__.py > ../../archive/2025-11-feature-004-patches/05-models-init-updates.patch

# Create a comprehensive patch for ALL model changes
git diff main -- src/models/ > ../../archive/2025-11-feature-004-patches/00-all-model-changes.patch
```

### Step 2: Document What Each Patch Contains

```bash
# For each patch, create a summary
cd C:\Users\Kent\Vaults-repos\bake-tracker\archive\2025-11-feature-004-patches

# Example for FinishedUnit patch:
echo "# FinishedUnit Model Patch

## What it contains:
- Complete FinishedUnit model class
- YieldMode enum (DISCRETE_COUNT, BATCH_PORTION)
- Factory method for migration from FinishedGood
- Inventory management methods
- Cost calculation methods
- All database constraints and indexes

## Dependencies:
- None (standalone model)

## Apply to:
- Feature 004A: FinishedUnit Model Creation

## Apply command:
git apply 01-finished-unit-model.patch
" > 01-finished-unit-model.README.md
```

---

## New Feature Breakdown

Based on completed work, here's the proper feature sequence:

### Feature 004A: FinishedUnit Model & Migration ⭐ PRIORITY 1

**What**: Rename FinishedGood → FinishedUnit, preserve all functionality

**Already Complete in 004 worktree**:
- ✅ FinishedUnit model with all fields
- ✅ YieldMode enum
- ✅ Migration factory method
- ✅ Inventory and cost methods

**Still Needed**:
- Migration script to convert existing FinishedGood records
- Update FinishedGood model to reference FinishedUnits
- Update services to use FinishedUnit
- Update UI to show "FinishedUnit" terminology
- Tests for FinishedUnit model

**Estimated Completion**: 60% done (model complete, services/UI pending)

**Apply patches**: `01-finished-unit-model.patch`

---

### Feature 004B: Composition Junction Entity ⭐ PRIORITY 2

**What**: Enable assemblies to contain FinishedUnits and other assemblies

**Already Complete in 004 worktree**:
- ✅ Composition model with polymorphic references
- ✅ Validation methods (circular reference, polymorphic constraint)
- ✅ Cost calculation methods
- ✅ Availability checking

**Still Needed**:
- Service layer for composition operations
- Circular reference validation at service level (BFS traversal)
- Tests for composition validation logic
- Migration to update schema

**Estimated Completion**: 70% done (model complete, services pending)

**Apply patches**: `02-composition-model.patch`

---

### Feature 004C: FinishedGood Assembly Model ⭐ PRIORITY 3

**What**: Refactor FinishedGood to represent assemblies (not individual items)

**Already Complete in 004 worktree**:
- ✅ Updated FinishedGood model structure
- ✅ AssemblyType enum

**Still Needed**:
- FinishedGood service updates for assembly operations
- Cost aggregation from components
- Inventory management for assemblies
- Tests for assembly operations

**Estimated Completion**: 40% done (partial model, services pending)

**Apply patches**: `03-assembly-type-enum.patch`, `04-finished-good-updates.patch`

---

### Feature 004D: Service Layer for Assemblies

**What**: Business logic for creating, managing, and validating assemblies

**Already Complete**: None (services not started)

**Needed**:
- FinishedUnitService (CRUD)
- CompositionService (hierarchy management)
- FinishedGoodService updates (assembly operations)
- Circular reference prevention (BFS algorithm)
- Cost calculation service methods
- Inventory availability checking

**Estimated Completion**: 0% done

**Apply patches**: None (new work)

---

### Feature 004E: UI for FinishedUnits

**What**: Update UI to manage FinishedUnits (renamed from FinishedGoods)

**Already Complete**: None (UI not updated)

**Needed**:
- Update "Finished Goods" tab → "FinishedUnits" tab
- Update forms and dialogs
- Update table displays
- Inventory tracking UI

**Estimated Completion**: 0% done

**Apply patches**: None (new work)

---

### Feature 004F: UI for Assemblies

**What**: New UI for creating and managing assemblies

**Already Complete**: None (UI not created)

**Needed**:
- New "Assemblies" tab for FinishedGood assemblies
- Component selection UI
- Hierarchy visualization
- Cost display with component breakdown

**Estimated Completion**: 0% done

**Apply patches**: None (new work)

---

## Workflow to Preserve Code

### Phase 1: Extract Patches (TODAY)

**YOU execute the commands in Step 1 above** to create all patches

### Phase 2: Start Feature 004A (THIS WEEK)

```bash
# In main repo directory
cd C:\Users\Kent\Vaults-repos\bake-tracker

# Ensure on main branch
git checkout main

# Start Feature 004A using spec-kitty
/spec-kitty.specify

# When prompted:
"Rename FinishedGood model to FinishedUnit to represent individual 
consumable items. Preserve all existing functionality including yield 
modes, cost calculation, and inventory tracking. Add migration support 
to convert existing FinishedGood records."
```

### Phase 3: Apply Patches to New Feature

Once spec-kitty creates the Feature 004A worktree:

```bash
# Switch to new 004A worktree
cd C:\Users\Kent\Vaults-repos\bake-tracker\.worktrees\<new-worktree-name>

# Apply the FinishedUnit model patch
git apply ../../archive/2025-11-feature-004-patches/01-finished-unit-model.patch

# Verify it applied cleanly
git status

# If successful, commit
git add src/models/finished_unit.py
git commit -m "feat: Add FinishedUnit model (extracted from Feature 004)"

# Continue with remaining Feature 004A work (migration script, services, tests)
```

### Phase 4: Repeat for Other Features

For each subsequent feature (004B, 004C, etc.):
1. Complete previous feature and merge to main
2. Start new feature with spec-kitty
3. Apply relevant patches
4. Complete remaining work
5. Merge to main

---

## Benefits of This Approach

✅ **Preserves completed work** - No code is lost
✅ **Proper feature scoping** - Each feature is independently testable and mergeable
✅ **Clean git history** - Proper commits in properly-scoped features
✅ **Constitution compliance** - Follows spec-kitty workflow
✅ **Incremental progress** - Can merge work as it completes
✅ **Clear tracking** - Each feature has defined scope and completion criteria

---

## Questions for Spec-Kitty Maintainer

When asking about Feature 004/005 situation, include these questions:

1. **Abandoning features**: "What's the recommended way to abandon a feature that was over-scoped? Should I just delete the worktree and branch, or is there a cleaner approach?"

2. **Extracting work**: "If a feature worktree contains completed work that should be preserved, what's the best workflow? I'm thinking:
   - Extract patches from over-scoped feature
   - Start properly-scoped features with spec-kitty
   - Apply patches to new feature worktrees
   - Complete and merge incrementally
   Is this aligned with spec-kitty best practices?"

3. **Feature numbering**: "If I abandon Feature 004 and start new features, will spec-kitty reuse the number 004 or continue with 006+? Should I care about number continuity?"

---

## Next Steps (Priority Order)

1. ✅ **App works** (confirmed)
2. **TODAY: Extract patches** (run commands in Step 1)
3. **TODAY: Ask maintainer** (questions above)
4. **THIS WEEK: Start Feature 004A** (with spec-kitty.specify)
5. **THIS WEEK: Apply patches and complete 004A**
6. **NEXT WEEK: Features 004B, 004C** (repeat pattern)

---

**Document Status**: Action plan ready
**Blocking Issue**: None (can proceed with extraction)
**Confidence**: High - This approach preserves work and follows proper workflow
