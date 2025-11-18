
How to Safely Abandon a Feature in Progress

Since your feature worktree has no useful code and only contains specs/planning, here's the safe cleanup process:

Step 1: Navigate out of the worktree (if you're in it)

cd /path/to/your/main/project/root

Step 2: Remove the worktree

git worktree remove .worktrees/NNN-feature-name

If that gives an error about the worktree being modified, use force:  
git worktree remove .worktrees/NNN-feature-name --force

Step 3: Delete the feature branch

git branch -D NNN-feature-name

The -D flag force-deletes the branch even if it hasn't been merged (which is what you want for abandoned work).

Step 4: (Optional) Clean up any orphaned git metadata

git worktree prune

This removes stale worktree references from .git/worktrees/.

About Feature Numbers

Regarding your concern about it being the highest feature number - don't worry about gaps in feature numbers. It's completely normal and safe to have:

- 001-feature-one
- 002-abandoned-feature (deleted)
- 003-feature-three

The numbering is just for organization and chronology. Gaps don't cause any issues and actually serve as a record that a feature was started but abandoned.

Complete Example

# From your project root

cd /path/to/project

# Remove the worktree

git worktree remove .worktrees/005-redundant-feature --force

# Delete the branch

git branch -D 005-redundant-feature

# Clean up

git worktree prune

# Verify it's gone

git worktree list # Should not show the removed worktree  
git branch # Should not show the deleted branch

Verification

After cleanup, verify everything is clean:  
git worktree list # Check worktrees  
git branch --all # Check branches  
ls .worktrees/ # Check directory is gone

That's it! The feature is cleanly abandoned with no residue.