# Cursor Agent Support Issues

**Date**: 2026-01-17
**Spec-Kitty Version**: 0.11.1
**Reporter:** Kent Gale (via Claude Code)
**Severity**: Medium (incomplete agent support)

## Summary

Two issues with Cursor IDE agent support in spec-kitty v0.11.1:

1. **`verify-setup` fails to detect installed Cursor CLI** - Reports "Cursor IDE agent (not found)" even though the `cursor` command is installed and functional
2. **`init --ai cursor` does not create `.cursorrules`** - The context file for Cursor is not generated, despite being mentioned in `--help` output

## Environment

- **OS**: macOS Darwin 25.2.0
- **Spec-kitty**: v0.11.1 (installed via pip)
- **Cursor**: v2.3.41 installed at `/usr/local/bin/cursor`

## Issue 1: Cursor Detection Failure

### Steps to Reproduce

```bash
# Verify cursor is installed and working
which cursor
# Output: /usr/local/bin/cursor

cursor --version
# Output:
# Cursor 2.3.41
# 2ca326e0d1ce10956aea33d54c0e2d8c13c58a30
# x64

# Run verify-setup
spec-kitty verify-setup
# Output includes:
# ├── ● Cursor IDE agent (not found)
```

### Expected Behavior

`verify-setup` should detect Cursor as "available" since the CLI is installed and functional.

### Actual Behavior

Reports "not found" despite the cursor CLI being in PATH and responding to `--version`.

### Possible Cause

The detection logic may be looking for a different command name, checking a specific path, or expecting a particular response format from `cursor --version`.

## Issue 2: Missing `.cursorrules` Context File

### Steps to Reproduce

```bash
# Initialize with cursor agent
spec-kitty init --here --ai claude,gemini,cursor --force

# Check for context files
ls -la CLAUDE.md GEMINI.md .cursorrules

# Output:
# -rw-r--r--  CLAUDE.md   (exists)
# -rw-r--r--  GEMINI.md   (exists)
# ls: .cursorrules: No such file or directory

# Check that cursor commands directory was created
ls .cursor/commands/
# Output: (16 command files present)
```

### Expected Behavior

`spec-kitty init --ai cursor` should create `.cursorrules` as the Cursor context file, similar to how it creates `CLAUDE.md` for Claude and `GEMINI.md` for Gemini.

The `--help` output explicitly mentions this:
```
Context files (CLAUDE.md, .cursorrules, AGENTS.md, etc.)
```

### Actual Behavior

- `.cursor/commands/` directory is created with 16 command files
- `.cursorrules` is NOT created
- No error or warning is displayed

## Comparison of Agent Setup

| Agent | Context File | Commands Dir | Status |
|-------|--------------|--------------|--------|
| Claude | `CLAUDE.md` | `.claude/commands/` | Complete |
| Gemini | `GEMINI.md` | `.gemini/commands/` | Complete |
| Cursor | `.cursorrules` | `.cursor/commands/` | **Incomplete** |

## Suggested Fixes

### Issue 1: Detection

Review the Cursor detection logic to:
- Check for `cursor` command in PATH
- Accept the version output format from Cursor 2.x
- Consider checking for `/Applications/Cursor.app` on macOS as fallback

### Issue 2: Context File

Ensure `init --ai cursor` creates `.cursorrules` with appropriate project context, following the same pattern as other agents.

## Workaround

For `.cursorrules`, users can manually create the file by adapting `CLAUDE.md` content. However, the detection issue has no workaround - it will always show "not found" in `verify-setup`.

## Notes

- These issues do not prevent using Cursor with spec-kitty - the `.cursor/commands/` directory works correctly
- The detection failure is cosmetic but may confuse users into thinking Cursor isn't supported
- The missing `.cursorrules` means Cursor won't have project-specific context unless manually created
