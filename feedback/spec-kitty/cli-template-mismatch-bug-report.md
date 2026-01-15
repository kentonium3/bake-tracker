# Bug Report: CLI Command Path and Option Mismatches in spec-kitty Templates

**Version:** spec-kitty-cli 0.10.13
**Platform:** macOS Darwin 25.2.0 (darwin)
**Python:** 3.13.11
**Date:** 2026-01-14
**Reporter:** Kent Gale (via Claude Code agent)

---

## Executive Summary

Multiple spec-kitty workflow commands fail when agents execute them due to mismatches between:
1. What templates instruct agents to run
2. What the actual CLI accepts

The root cause is that CLI commands were reorganized under `spec-kitty agent feature` subcommand, but template expansion logic and template documentation were not updated to match.

**Impact:** High - Agents cannot execute workflows without manual intervention, breaking the automated spec-kitty workflow.

---

## Issues Found

### Issue 1: `{SCRIPT}` Placeholder Expands to Incorrect Command Paths

**Severity:** Critical
**Affects:** clarify, analyze, checklist, research/plan, research/review

**Description:**
The `{SCRIPT}` placeholder in templates expands to `spec-kitty agent check-prerequisites` when it should expand to `spec-kitty agent feature check-prerequisites`.

**How to Reproduce:**
1. Run `/spec-kitty.clarify` in a feature worktree
2. Observe the command the agent attempts to execute

**Expected:**
```bash
spec-kitty agent feature check-prerequisites --json --paths-only
```

**Actual (delivered to agent via template expansion):**
```bash
spec-kitty agent check-prerequisites --json --paths-only
```

**Error:**
```
Usage: spec-kitty agent [OPTIONS] COMMAND [ARGS]...
Try 'spec-kitty agent --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'check-prerequisites'.                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Affected Templates:**
- `.kittify/missions/software-dev/command-templates/clarify.md` (line 20)
- `.kittify/missions/software-dev/command-templates/analyze.md` (line 26)
- `.kittify/missions/software-dev/command-templates/checklist.md` (line 33)
- `.kittify/missions/research/command-templates/plan.md` (lines 56, 59)
- `.kittify/missions/research/command-templates/review.md` (line 64)

**Suggested Fix:**
Update the template expansion logic in spec-kitty to expand `{SCRIPT}` to include the `feature` subcommand:
- `spec-kitty agent feature check-prerequisites` (not `spec-kitty agent check-prerequisites`)
- `spec-kitty agent feature setup-plan` (not `spec-kitty agent setup-plan`)
- `spec-kitty agent feature accept` (not `spec-kitty agent accept`)

---

### Issue 2: specify.md References Non-Existent CLI Options

**Severity:** High
**Affects:** /spec-kitty.specify

**Description:**
The specify.md template instructs agents to use `--feature-name` and `--mission` options that do not exist on the `create-feature` command.

**Template Content (lines 74, 82):**
```markdown
Store the final mission selection to pass to the script via `--mission "<selected-mission>"`.
...
You will pass this confirmed title to the feature creation script via `--feature-name "<Friendly Title>"`
```

**Actual CLI Signature:**
```
Usage: spec-kitty agent feature create-feature [OPTIONS] FEATURE_SLUG

Arguments:
  FEATURE_SLUG  TEXT  Feature slug (e.g., 'user-auth') [required]

Options:
  --json   Output JSON format
  --help   Show this message and exit.
```

**How to Reproduce:**
1. Run `/spec-kitty.specify` with a feature description
2. Agent attempts: `spec-kitty agent feature create-feature --json --feature-name "My Feature" --mission "software-dev"`
3. Command fails

**Error:**
```
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such option: --feature-name                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Suggested Fix:**
Update specify.md to use correct syntax:
- Remove references to `--feature-name` - use positional `FEATURE_SLUG` instead
- Remove references to `--mission` - this option doesn't exist
- Update lines 74, 82, and the command example at line 98-99

**Fixed Template:** See `feedback/spec-kitty/fixed-templates/specify.md`

---

### Issue 3: accept.md References Non-Existent CLI Options

**Severity:** High
**Affects:** /spec-kitty.accept

**Description:**
The accept.md template instructs agents to use `--actor` and `--test` options that do not exist.

**Template Content (lines 29-32):**
```markdown
1. Compile the acceptance options into an argument list:
   - Always include `--actor "__AGENT__"`.
   ...
   - Append `--test "<command>"` for each validation command provided.
```

**Actual CLI Signature:**
```
Usage: spec-kitty agent feature accept [OPTIONS]

Options:
  --feature   TEXT  Feature directory slug (auto-detected if not specified)
  --mode      TEXT  Acceptance mode: auto, pr, local, checklist [default: auto]
  --json            Output results as JSON for agent parsing
  --lenient         Skip strict metadata validation
  --no-commit       Skip auto-commit (report only)
  --help            Show this message and exit.
```

**How to Reproduce:**
1. Run `/spec-kitty.accept` after completing implementation
2. Agent attempts: `spec-kitty agent feature accept --json --actor "claude" --feature "049-import-export-phase1" --mode local --test "./run-tests.sh"`
3. Command fails

**Error:**
```
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such option: --actor Did you mean --feature?                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Suggested Fix:**
Update accept.md to use correct options:
- Remove references to `--actor` - this option doesn't exist
- Remove references to `--test` - this option doesn't exist
- Update discovery questions to only ask for options that exist (feature, mode)

**Fixed Template:** See `feedback/spec-kitty/fixed-templates/accept.md`

---

### Issue 4: CLI Help Text Shows Incorrect Command Examples

**Severity:** Low (cosmetic, but causes confusion)
**Affects:** All `spec-kitty agent feature` subcommands

**Description:**
The `--help` output for commands under `spec-kitty agent feature` shows examples without the `feature` subcommand.

**Example from `spec-kitty agent feature check-prerequisites --help`:**
```
Examples:     spec-kitty agent check-prerequisites --json     spec-kitty agent
check-prerequisites --paths-only --json
```

**Should be:**
```
Examples:     spec-kitty agent feature check-prerequisites --json     spec-kitty agent
feature check-prerequisites --paths-only --json
```

**Affected Commands:**
- `spec-kitty agent feature check-prerequisites`
- `spec-kitty agent feature create-feature`
- `spec-kitty agent feature setup-plan`
- `spec-kitty agent feature accept`

**Suggested Fix:**
Update the `Examples:` strings in the CLI command decorators to include the full command path.

---

## Complete Mismatch Inventory

| Command | Template Says | CLI Accepts | Status |
|---------|--------------|-------------|--------|
| clarify | `spec-kitty agent check-prerequisites` | `spec-kitty agent feature check-prerequisites` | BROKEN |
| specify | `--feature-name`, `--mission` | `FEATURE_SLUG` (positional), no --mission | BROKEN |
| plan | `spec-kitty agent setup-plan` | `spec-kitty agent feature setup-plan` | BROKEN (via expansion) |
| tasks | `spec-kitty agent feature check-prerequisites` | `spec-kitty agent feature check-prerequisites` | OK in template, broken in expansion |
| implement | `spec-kitty agent workflow implement` | `spec-kitty agent workflow implement` | OK |
| review | `spec-kitty agent workflow review` | `spec-kitty agent workflow review` | OK |
| accept | `--actor`, `--test` | No such options | BROKEN |
| merge | `spec-kitty merge` | `spec-kitty merge` | OK |
| analyze | `{SCRIPT}` for check-prerequisites | Missing `feature` subcommand | BROKEN |
| checklist | `{SCRIPT}` for check-prerequisites | Missing `feature` subcommand | BROKEN |

---

## Recommended Actions

### For Template Files (User-Editable)

1. **specify.md** - Fix lines 74, 82, 98-99 to use positional FEATURE_SLUG
2. **accept.md** - Fix lines 29-32 to remove non-existent options

Fixed versions provided in: `feedback/spec-kitty/fixed-templates/`

### For spec-kitty Codebase (Maintainer Action Required)

1. **Template Expansion Logic** - Update `{SCRIPT}` expansion to include `feature` subcommand where appropriate
2. **CLI Help Text** - Update example strings in command decorators to show full command paths

---

## Testing Verification

After fixes are applied, the following commands should work:

```bash
# clarify
spec-kitty agent feature check-prerequisites --json --paths-only

# specify
spec-kitty agent feature create-feature "my-feature-slug" --json

# plan
spec-kitty agent feature setup-plan --json

# tasks
spec-kitty agent feature check-prerequisites --json --paths-only --include-tasks

# accept
spec-kitty agent feature accept --json --feature "001-my-feature" --mode local
```

---

## Attachments

- `feedback/spec-kitty/fixed-templates/specify.md` - Fixed specify template
- `feedback/spec-kitty/fixed-templates/accept.md` - Fixed accept template
