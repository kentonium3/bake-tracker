# Context Continuity: Spec-Kitty Skill Loading Investigation

**Created:** 2026-01-15
**Purpose:** Resume context after Claude Code restart
**Delete after:** Issue resolved

---

## TL;DR - What to Test First

After restarting Claude Code, run:
```
/spec-kitty.specify
```

**If the prompt shows:**
- `spec-kitty agent feature create-feature "<slug>" --json` = **FIXED**
- `spec-kitty agent create-feature --json` = **Still broken** (needs more investigation)

---

## What We Were Doing

Investigating why `/spec-kitty.specify` was failing with CLI errors. The skill was loading templates with **wrong CLI syntax**.

## Root Cause Discovered

1. **Claude Code discovers skills from `.claude/commands/` directory**
2. **This directory was deleted** during earlier cleanup session (we removed `.claude/`, `.gemini/`, `.cursor/` as "IDE caches")
3. **Without `.claude/commands/`**, Claude Code falls back to **package-bundled templates**
4. **Package templates have wrong CLI syntax**: `spec-kitty agent create-feature` instead of `spec-kitty agent feature create-feature`

## Fix Applied

Recreated `.claude/commands/` with local templates (which have correct syntax):

```bash
mkdir -p .claude/commands
for f in .kittify/missions/software-dev/command-templates/*.md; do
  name=$(basename "$f" .md)
  cp "$f" ".claude/commands/spec-kitty.${name}.md"
done
```

**Files created:**
- `.claude/commands/spec-kitty.specify.md` (and 11 other spec-kitty commands)

## Why Restart is Needed

Claude Code appears to cache skill templates. Even after creating `.claude/commands/`, it continued loading the old package templates. Restarting should force re-discovery.

## Files Modified This Session

1. **Created:** `.claude/commands/spec-kitty.*.md` (12 files) - skill templates with correct CLI
2. **Fixed:** `.kittify/AGENTS.md` - was broken symlink, now regular file
3. **Updated:** `feedback/spec-kitty-template-cli-mismatch.md` - added Issue 2 documentation
4. **Created:** `feedback/suspected-agents-md-symlink-issue.md` - documents AGENTS.md symlink issue

## If Still Broken After Restart

Possible next steps:
1. Check if `.claude/commands/` is being read at all (add a test file?)
2. Investigate Claude Code's skill discovery mechanism further
3. Check for additional caching layers
4. May need to report to Claude Code team if local commands aren't being prioritized

## Related Context

- Feature 053 (context-rich-export-fixes) was partially created at `.worktrees/053-context-rich-export-fixes/`
- The feature creation succeeded but spec wasn't written due to workflow interruption
- Design doc: `docs/design/F053_context_rich_export_fixes.md`

## Bug Reports Updated

- `feedback/spec-kitty-template-cli-mismatch.md` - Now documents two issues:
  - Issue 1: review.md template (upgrade path issue - resolved)
  - Issue 2: Package templates have wrong CLI syntax (upstream bug)

---

## Quick Commands Reference

```bash
# Verify .claude/commands exists
ls -la .claude/commands/

# Check specify template has correct syntax
grep "spec-kitty agent" .claude/commands/spec-kitty.specify.md

# Should show: spec-kitty agent feature create-feature "<slug>" --json
```
