# Spec-Kitty Diagnostic Procedure

**Created**: 2026-01-15
**Purpose**: Diagnose recurring symlink issues in spec-kitty workflow
**For**: Fresh Claude session or human operator

## Problem Summary

The `.kittify/memory/constitution.md` file keeps being replaced by a broken symlink during feature development. This has happened **5+ times** despite:
- Deleting entire `.kittify/` directory
- Upgrading to spec-kitty v0.10.13
- Re-initializing the project

The symlink `.kittify/memory -> ../../../.kittify/memory` works from worktrees but breaks when committed to main.

## Current Environment

```
Project: bake-tracker
Location: /Users/kentgale/Vaults-repos/bake-tracker
Spec-kitty version: 0.10.13
Active worktree: .worktrees/054-cli-import-export-parity
```

## Diagnostic Procedure

### Phase 1: Create Reference Project

Create a fresh project to establish what "correct" spec-kitty setup looks like.

```bash
# Create test directory
cd /tmp
mkdir spec-kitty-test-$(date +%Y%m%d)
cd spec-kitty-test-*

# Initialize git repo
git init
git config user.email "test@example.com"
git config user.name "Test User"

# Check spec-kitty version
spec-kitty --version

# Initialize spec-kitty
spec-kitty init

# CHECKPOINT 1: Record .kittify structure
echo "=== CHECKPOINT 1: After init ==="
find .kittify -type l -exec ls -la {} \;  # Find all symlinks
find .kittify -type f -name "*.md" | head -20
ls -la .kittify/memory/
cat .kittify/memory/constitution.md | head -20
git status
```

### Phase 2: Create Feature and Worktree

```bash
# Create initial commit (required for worktrees)
echo "# Test Project" > README.md
git add . && git commit -m "Initial commit"

# Create a test feature
spec-kitty specify "Test symlink behavior"

# CHECKPOINT 2: After feature creation
echo "=== CHECKPOINT 2: After specify ==="
ls -la .worktrees/
WORKTREE=$(ls .worktrees/ | head -1)
echo "Worktree: $WORKTREE"

# Check worktree's .kittify structure
ls -la ".worktrees/$WORKTREE/.kittify/"
ls -la ".worktrees/$WORKTREE/.kittify/memory/" 2>/dev/null || echo "No memory dir"
file ".worktrees/$WORKTREE/.kittify/memory" 2>/dev/null

# Check for symlinks in worktree
find ".worktrees/$WORKTREE/.kittify" -type l -exec ls -la {} \;

# Check git status in worktree
cd ".worktrees/$WORKTREE"
git status --porcelain .kittify/
cd ../..
```

### Phase 3: Run Workflow Commands

```bash
cd ".worktrees/$WORKTREE"

# Run plan
spec-kitty plan

# CHECKPOINT 3: After plan
echo "=== CHECKPOINT 3: After plan ==="
git status --porcelain .kittify/

# Run tasks
spec-kitty tasks

# CHECKPOINT 4: After tasks
echo "=== CHECKPOINT 4: After tasks ==="
git status --porcelain .kittify/
ls -la .kittify/memory/

cd ../..
```

### Phase 4: Compare with Bake-Tracker Project

Run these commands to compare the test project with bake-tracker:

```bash
echo "=== COMPARISON: Test Project ==="
echo "Main repo .kittify/memory:"
ls -la /tmp/spec-kitty-test-*/.kittify/memory/
file /tmp/spec-kitty-test-*/.kittify/memory

echo ""
echo "Worktree .kittify/memory:"
ls -la /tmp/spec-kitty-test-*/.worktrees/*/.kittify/memory/ 2>/dev/null
file /tmp/spec-kitty-test-*/.worktrees/*/.kittify/memory 2>/dev/null

echo ""
echo "=== COMPARISON: Bake-Tracker Project ==="
echo "Main repo .kittify/memory:"
ls -la /Users/kentgale/Vaults-repos/bake-tracker/.kittify/memory/
file /Users/kentgale/Vaults-repos/bake-tracker/.kittify/memory

echo ""
echo "Worktree .kittify/memory:"
ls -la /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/.kittify/memory/
file /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/.kittify/memory
```

### Phase 5: Check Git History for Symlink Introduction

```bash
# In bake-tracker, find when symlinks were introduced
cd /Users/kentgale/Vaults-repos/bake-tracker
git log --all --oneline -- ".kittify/memory" | head -10

# Check the diff that introduced the symlink
git log --all -p -- ".kittify/memory" | head -50
```

## Expected vs Actual Behavior

### Expected (per spec-kitty v0.10.8+ changelog)
- Main repo: `.kittify/memory/constitution.md` is a **real file**
- Worktree: `.kittify/memory` may be a **symlink** pointing to main repo
- On merge: Symlink should NOT overwrite the real file in main

### Actual (observed in bake-tracker)
- Main repo: `.kittify/memory` becomes a **symlink** after merges
- Worktree: Has symlink `../../../.kittify/memory` (correct for worktree)
- On merge: Symlink DOES overwrite the real file

## Output Format

After running the diagnostic, document findings in this format:

```markdown
## Diagnostic Results - [DATE]

### Test Project Structure
- .kittify/memory in main: [file/symlink/directory]
- .kittify/memory in worktree: [file/symlink/directory]
- Symlinks found: [list]

### Bake-Tracker Structure
- .kittify/memory in main: [file/symlink/directory]
- .kittify/memory in worktree: [file/symlink/directory]
- Symlinks found: [list]

### Discrepancies
[List differences between test project and bake-tracker]

### Root Cause Assessment
- [ ] Spec-kitty bug (test project also has issue)
- [ ] Bake-tracker specific (test project is clean)
- [ ] Repair artifact propagation
- [ ] Other: ___

### Recommended Fix
[Based on findings]
```

## Context for Fresh Session

If running this from a fresh Claude session, provide this context:

> I'm diagnosing a recurring spec-kitty issue where `.kittify/memory/constitution.md`
> keeps being replaced by a broken symlink. This has happened 5+ times in the
> bake-tracker project. Please run the diagnostic procedure in SPEC-KITTY-DIAGNOSTIC.md
> and document findings. The goal is to determine if this is a spec-kitty bug or
> project-specific corruption.

## Related Files

- Feedback document (if bug confirmed): `feedback/spec-kitty-symlink-merge-bug.md`
- Previous investigation: `feedback/spec-kitty-template-cli-mismatch.md`
- Spec-kitty changelog: https://github.com/Priivacy-ai/spec-kitty/blob/main/CHANGELOG.md

## Notes

- v0.10.8 changelog claims symlink fix but issue persists
- v0.11.0 (unreleased) changes constitution handling significantly
- Consider whether to report bug given imminent v0.11.0 changes
