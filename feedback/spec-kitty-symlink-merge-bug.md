# Feedback: Spec-Kitty Worktree Symlinks Overwrite Main Repo Files on Merge

**Date**: 2026-01-15
**Spec-Kitty Version**: 0.10.13
**Status**: Pending diagnostic confirmation
**Severity**: High (causes data loss)

## Summary

Worktree symlinks for `.kittify/memory` get committed during feature development and overwrite the actual `constitution.md` file in the main branch when features are merged. This has occurred 5+ times in a single project despite multiple repair attempts and a clean reinstall.

## Environment

- **OS**: macOS Darwin 25.2.0
- **Spec-kitty**: v0.10.13 (installed via pip)
- **Project**: Multi-feature development with git worktrees
- **Git**: Standard git workflow with feature branches

## Steps to Reproduce

1. Initialize spec-kitty project with `spec-kitty init`
2. Create feature with `spec-kitty specify "Feature name"`
3. Work in worktree, make commits
4. Merge feature branch to main (via `git merge` or `spec-kitty merge`)
5. Check `.kittify/memory/` in main - constitution.md is now a broken symlink

## Expected Behavior

Per v0.10.8 changelog ("Critical symlink fix"):
- Main repo should retain `.kittify/memory/constitution.md` as a **real file**
- Worktree symlinks should NOT be committed or should be excluded from merges
- Merging a feature should not alter `.kittify/` structure in main

## Actual Behavior

- Worktree `.kittify/memory` symlink (`-> ../../../.kittify/memory`) gets staged
- On merge, symlink overwrites the real directory in main
- Symlink path resolves to **outside the repository** when in main branch
- Constitution file becomes inaccessible, breaking spec-kitty commands

## Evidence

### Git History Pattern

```
ee7c722 - fix: Restore constitution.md (4th time)
62a6c7c - fix: Restore constitution.md (3rd time)
4d04e36 - fix: Restore constitution.md (2nd time)
4e45c82 - fix: Restore constitution.md (1st time)
```

### Symlink Analysis

From worktree `.worktrees/054-feature/.kittify/`:
```
memory -> ../../../.kittify/memory
```
- Resolves correctly: `.worktrees/054-feature/../../.kittify/memory` = `.kittify/memory`

From main `.kittify/`:
```
memory -> ../../../.kittify/memory
```
- Resolves incorrectly: Goes **outside** the repository

## Changelog Reference

**v0.10.8 (2025-12-30):**
> - Critical symlink fix: "Moved `memory/` directory from root to `.kittify/memory/`"
> - Broken symlinks removed: ".kittify/memory → ../../../.kittify/memory" was broken
> - Migration: "Automatically moves `memory/` to `.kittify/memory/` in existing projects"

The fix appears to address the symlink path but not the merge-time overwrite issue.

## Potential Root Causes

1. **Worktree setup commits symlink**: The symlink is created and staged during worktree creation
2. **No .gitignore protection**: `.kittify/memory` is not in .gitignore (can't be, since constitution.md needs tracking)
3. **Merge doesn't filter**: Neither `git merge` nor `spec-kitty merge` excludes worktree-specific symlinks
4. **Path calculation assumes worktree context**: The `../../../` path only works from worktree depth

## Suggested Fixes

### Option A: Don't create symlinks in worktrees
Copy constitution.md to worktrees instead of symlinking. Slightly more disk usage but eliminates the problem.

### Option B: Use absolute paths
If symlinks are needed, use absolute paths that work from any location.

### Option C: Add to .gitattributes
```
.kittify/memory merge=ours
```
Prevent worktree version from overwriting main on merge.

### Option D: Post-merge hook
Automatically restore constitution.md if it becomes a symlink after merge.

### Option E: Exclude from worktree commits
Add worktree-specific `.kittify/memory` to a local exclude file that doesn't get committed.

## Workaround

Before merging any feature branch:
```bash
# In the feature worktree
rm -f .kittify/memory
mkdir -p .kittify/memory
cp /path/to/main/repo/.kittify/memory/constitution.md .kittify/memory/
git add .kittify/memory
git commit -m "fix: Replace symlink with real constitution.md before merge"
```

## Impact

- Breaks spec-kitty commands that need constitution.md
- Requires manual intervention after every feature merge
- Data loss risk if constitution.md is customized and not backed up
- Erodes trust in the workflow automation

## Related Issues

- Prior investigation: `feedback/spec-kitty-template-cli-mismatch.md`
- Diagnostic procedure: `SPEC-KITTY-DIAGNOSTIC.md`

## Notes for Maintainers

- v0.11.0 (unreleased) significantly changes constitution handling ("consolidate into single project-level model")
- This bug may be resolved by v0.11.0's architectural changes
- Consider whether to fix in 0.10.x or wait for 0.11.0

---

## Diagnostic Results

*[To be filled in after running SPEC-KITTY-DIAGNOSTIC.md procedure]*

### Test Project Findings
- [ ] Test project exhibits same behavior (spec-kitty bug confirmed)
- [ ] Test project works correctly (bake-tracker specific issue)

### Comparison Details
```
[Paste diagnostic output here]
```

### Root Cause Determination
- [ ] Confirmed spec-kitty bug
- [ ] Project-specific corruption
- [ ] Repair artifact propagation
- [ ] Other: ___

### Recommendation
```
[Based on diagnostic findings]
```
