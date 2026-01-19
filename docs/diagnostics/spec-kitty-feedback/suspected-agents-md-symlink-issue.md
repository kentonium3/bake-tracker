# Suspected Issue: AGENTS.md Symlink Incorrectly Created in Main Repo

**Status:** Workaround applied, likely NOT the primary cause
**Discovered:** 2026-01-15
**Updated:** 2026-01-15
**Priority:** Low (resolved locally, investigation optional)
**Reporter:** bake-tracker project

---

## Summary

The main repo's `.kittify/AGENTS.md` was found to be a broken symlink pointing to a non-existent global location, when it should have been a regular file.

## Observed State

**Before fix:**
```
.kittify/AGENTS.md -> ../../../.kittify/AGENTS.md
```

From the main repo root, this resolves to `/Users/kentgale/.kittify/AGENTS.md` which does not exist.

**Expected state:**
- Main repo: `.kittify/AGENTS.md` should be a regular file (source of truth)
- Worktrees: `.kittify/AGENTS.md` should be a symlink pointing back to main repo

## Workaround Applied

Replaced the broken symlink with a copy of the actual file from the spec-kitty package:
```bash
rm .kittify/AGENTS.md
cp /path/to/specify_cli/templates/AGENTS.md .kittify/AGENTS.md
```

## Possible Causes

### Cause A: spec-kitty init bug

`spec-kitty init` may incorrectly create the main repo's AGENTS.md as a symlink to a global `~/.kittify/` directory that it expects to exist but doesn't create.

**Evidence for:** The symlink pattern `../../../.kittify/AGENTS.md` would make sense if there was supposed to be a global `~/.kittify/` directory shared across projects.

**Evidence against:** No documentation mentions a global `~/.kittify/` directory.

### Cause B: Rogue AI actions during early project setup

Early in the bake-tracker project lifecycle, there were numerous spec-kitty workflow issues and bugs. AI agents may have attempted repairs that inadvertently created this broken symlink.

**Evidence for:** The project went through multiple `spec-kitty init` and reinitializations to resolve other issues. AI actions during troubleshooting could have created unintended artifacts.

**Evidence against:** The symlink target pattern matches what worktrees use, suggesting it came from spec-kitty's own logic.

### Cause C: Upgrade path issue

A `spec-kitty upgrade` migration may have incorrectly converted the file to a symlink or failed to properly handle an edge case.

**Evidence for:** The project has been through multiple spec-kitty version upgrades.

## Investigation Steps (for later)

1. Check spec-kitty source code for where AGENTS.md symlinks are created
2. Check if `spec-kitty init` on a fresh project creates a symlink or regular file
3. Review upgrade migration code for AGENTS.md handling
4. Check git history for when the symlink was introduced (if committed)

## Related Issues

- `feedback/spec-kitty-template-cli-mismatch.md` - Documents the template/CLI mismatch that led to discovering this issue

## Notes

This issue was discovered while investigating why Claude Code's skill loader was using package templates instead of local templates. Fixing this symlink may or may not have resolved that issue - further testing required.

---

## Update: 2026-01-15 - Root Cause Clarified

### Additional Issue Found

Further investigation revealed that **malformed YAML frontmatter** in local templates was likely a more significant contributor to the package template fallback behavior than the AGENTS.md symlink issue.

Five local templates were missing the closing `---` delimiter in their YAML frontmatter:
- accept.md
- analyze.md
- checklist.md
- clarify.md
- merge.md

### Current Assessment

The command failures (e.g., `/spec-kitty.accept` using `--actor` flag) were caused by a **combination of factors**:

1. **Malformed local templates** (primary cause) - Parsing failures caused fallback to package templates
2. **Broken AGENTS.md symlink** (secondary/uncertain) - May have contributed to template discovery issues
3. **Package template CLI mismatch** (upstream bug) - Package templates have `scripts:` frontmatter with incorrect commands

### Resolution Status

| Issue | Status |
|-------|--------|
| AGENTS.md symlink | Fixed (replaced with real file) |
| Malformed frontmatter | Fixed (added closing `---` to 5 templates) |
| Package CLI mismatch | Upstream bug - reported in `spec-kitty-template-cli-mismatch.md` |

### Recommendation

This symlink issue can be closed as "resolved locally". The upstream investigation (whether `spec-kitty init` creates broken symlinks) is low priority since:
1. The workaround is simple (replace symlink with real file)
2. The malformed frontmatter was the more likely cause of the failures
3. Fresh projects may not encounter this issue
