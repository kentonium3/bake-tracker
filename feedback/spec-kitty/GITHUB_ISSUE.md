# [BUG] Template-to-CLI command path and option mismatches break agent workflows

## Summary

Multiple spec-kitty workflow commands fail when AI agents attempt to execute them because the templates instruct agents to use command paths and options that don't exist in the CLI.

## Environment

- **spec-kitty version:** 0.10.13
- **Python:** 3.13.11
- **Platform:** macOS Darwin 25.2.0

## Root Cause

The CLI commands were reorganized under `spec-kitty agent feature` subcommand, but:
1. The `{SCRIPT}` placeholder expansion logic was not updated
2. Template documentation still references old/non-existent CLI options

## Issues

### 1. Missing `feature` subcommand in CLI paths (Critical)

**Affected commands:** clarify, analyze, checklist, research/plan, research/review

The `{SCRIPT}` placeholder expands to:
```bash
spec-kitty agent check-prerequisites --json
```

But the correct command is:
```bash
spec-kitty agent feature check-prerequisites --json
```

Same issue affects `setup-plan` and `accept`.

### 2. specify.md references non-existent options (High)

Template instructs agents to use:
- `--feature-name "<title>"` - **Does not exist** (should use positional `FEATURE_SLUG`)
- `--mission "<mission>"` - **Does not exist**

### 3. accept.md references non-existent options (High)

Template instructs agents to use:
- `--actor "__AGENT__"` - **Does not exist**
- `--test "<command>"` - **Does not exist**

### 4. CLI help text shows incorrect examples (Low)

`--help` output shows:
```
Examples: spec-kitty agent check-prerequisites --json
```

Should be:
```
Examples: spec-kitty agent feature check-prerequisites --json
```

## Reproduction Steps

1. Initialize a spec-kitty project
2. Run `/spec-kitty.clarify` in a feature worktree
3. Agent attempts: `spec-kitty agent check-prerequisites --json --paths-only`
4. Command fails with "No such command 'check-prerequisites'"

## Expected Behavior

Commands should execute successfully with the syntax documented in templates.

## Actual Behavior

```
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'check-prerequisites'.                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Suggested Fixes

### For spec-kitty codebase:

1. **Template expansion logic**: Update `{SCRIPT}` expansion to include `feature` subcommand
2. **CLI help text**: Update example strings in command decorators

### For template files (attached):

1. **specify.md**: Remove `--feature-name` and `--mission` references; use positional FEATURE_SLUG
2. **accept.md**: Remove `--actor` and `--test` references; document actual options

## Attachments

See attached files:
- `cli-template-mismatch-bug-report.md` - Full investigation report
- `fixed-templates/specify.md` - Fixed specify template
- `fixed-templates/accept.md` - Fixed accept template

## Impact

**High** - Agents cannot execute workflows without manual intervention, breaking the core spec-kitty automation promise.

## Workaround

Agents must manually determine correct CLI syntax by running `--help` commands, which defeats the purpose of the template system.
