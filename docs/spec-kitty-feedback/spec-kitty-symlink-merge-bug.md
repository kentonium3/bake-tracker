# Worktree Symlinks Overwrite Main Repo Files on Merge

**Date**: 2026-01-15
**Spec-Kitty Version**: 0.10.13
**Reporter:** Kent Gale (via Claude Code)
**Severity**: High (causes data loss)

## Summary

When `spec-kitty agent feature create-feature` creates a worktree, it generates symlinks for `.kittify/memory` and `.kittify/AGENTS.md`. These symlinks are not excluded from git, so they get committed during feature development. On merge, the symlink overwrites the real file/directory in main, and the relative path `../../../.kittify/memory` then points outside the repository.

## Environment

- **OS**: macOS Darwin 25.2.0
- **Spec-kitty**: v0.10.13 (installed via pip)
- **Git**: Standard git workflow with feature branches and worktrees

## Steps to Reproduce

```bash
# 1. Initialize project
spec-kitty init --here --ai claude --force
git add . && git commit -m "Initial commit"

# 2. Create constitution (required for .kittify/memory to exist)
# Run /spec-kitty.constitution via AI agent

# 3. Create feature with worktree
spec-kitty agent feature create-feature "test-feature"

# 4. Check worktree for symlinks
find .worktrees/001-test-feature/.kittify -type l -exec ls -la {} \;
# Output shows:
#   .kittify/memory -> ../../../.kittify/memory
#   .kittify/AGENTS.md -> ../../../.kittify/AGENTS.md

# 5. Check git status in worktree
cd .worktrees/001-test-feature
git status --porcelain .kittify/
# Output:
#   T .kittify/AGENTS.md     (type change: file -> symlink)
#   ?? .kittify/memory       (new symlink)

# 6. Commit changes in worktree (includes symlinks)
git add . && git commit -m "Feature work"

# 7. Merge to main
git checkout main
git merge 001-test-feature

# 8. Check main - constitution.md is now a broken symlink
file .kittify/memory
# Output: .kittify/memory: broken symbolic link to ../../../.kittify/memory
```

## Expected Behavior

- Main repo retains `.kittify/memory/constitution.md` as a real file after merge
- Worktree symlinks should not be committed or should be excluded from merges

## Actual Behavior

- Worktree symlink `../../../.kittify/memory` gets committed
- On merge, symlink replaces the real directory in main
- In main, the relative path points outside the repository
- Constitution file becomes inaccessible, breaking spec-kitty commands

## Root Cause

`spec-kitty agent feature create-feature` creates relative symlinks in the worktree's `.kittify/` directory to share files with the main repo. However:

1. These symlinks show as git changes (`T` for type change, `??` for new)
2. They are not in `.gitignore` or `.git/info/exclude`
3. When committed and merged, the symlink overwrites the real file
4. The `../../../` path only resolves correctly from worktree depth, not from main

## Changelog Reference

v0.10.8 mentions "Critical symlink fix" for moving `memory/` to `.kittify/memory/`, but this doesn't prevent the merge-time overwrite since worktree creation continues to generate committable symlinks.

## Suggested Fixes

**Option A: Exclude symlinks from git**
After creating symlinks in `create-feature`, add them to `.git/info/exclude` in the worktree so they're never committed.

**Option B: Copy instead of symlink**
Copy files to worktrees instead of symlinking. Slightly more disk usage but eliminates the problem entirely.

**Option C: Use .gitattributes**
```
.kittify/memory merge=ours
.kittify/AGENTS.md merge=ours
```

## Workaround

Before merging any feature branch, replace symlinks with real files:
```bash
# In the feature worktree
rm -f .kittify/memory .kittify/AGENTS.md
mkdir -p .kittify/memory
cp "$(git rev-parse --show-toplevel)/../.kittify/memory/constitution.md" .kittify/memory/
cp "$(git rev-parse --show-toplevel)/../.kittify/AGENTS.md" .kittify/
git add .kittify && git commit -m "fix: Replace symlinks before merge"
```

## Notes

- v0.11.0 (unreleased) changes constitution handling significantly and may resolve this
- This has occurred 5+ times in a production project requiring manual repair after each merge
