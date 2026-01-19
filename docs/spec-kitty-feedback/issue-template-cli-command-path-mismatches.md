# Template-to-CLI Command Path and Option Mismatches Break Agent Workflows

## Summary

Multiple spec-kitty workflow commands fail when AI agents attempt to execute them because the templates instruct agents to use command paths and options that don't exist in the CLI. The root cause is that CLI commands were reorganized under `spec-kitty agent feature` subcommand, but template expansion logic and template documentation were not updated to match.

**This IS a spec-kitty bug.** The templates and expansion logic reference commands and options that do not exist in the CLI.

## Environment

- **spec-kitty version:** 0.10.13
- **Project:** bake-tracker (multiple features affected)
- **Date observed:** 2026-01-14
- **Platform:** macOS Darwin 25.2.0
- **Python:** 3.13.11
- **Reporter:** Kent Gale (via Claude Code)

## Issues Found

### Issue 1: `{SCRIPT}` Placeholder Expands to Incorrect Command Paths (Critical)

**Affected commands:** clarify, analyze, checklist, research/plan, research/review

The `{SCRIPT}` placeholder in templates expands to `spec-kitty agent check-prerequisites` when it should expand to `spec-kitty agent feature check-prerequisites`.

**Reproduction:**
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

---

### Issue 2: specify.md References Non-Existent CLI Options (High)

**Affected command:** /spec-kitty.specify

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

**Error:**
```
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such option: --feature-name                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

### Issue 3: accept.md References Non-Existent CLI Options (High)

**Affected command:** /spec-kitty.accept

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

**Error:**
```
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such option: --actor Did you mean --feature?                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

### Issue 4: CLI Help Text Shows Incorrect Command Examples (Low)

**Affected:** All `spec-kitty agent feature` subcommands

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

## Proposed Solution

### For spec-kitty Codebase (Maintainer Action Required)

1. **Template Expansion Logic** - Update `{SCRIPT}` expansion to include `feature` subcommand where appropriate:
   - `spec-kitty agent feature check-prerequisites` (not `spec-kitty agent check-prerequisites`)
   - `spec-kitty agent feature setup-plan` (not `spec-kitty agent setup-plan`)
   - `spec-kitty agent feature accept` (not `spec-kitty agent accept`)

2. **CLI Help Text** - Update example strings in command decorators to show full command paths

### For Template Files

1. **specify.md** - Fix lines 74, 82 to use positional FEATURE_SLUG instead of non-existent options
2. **accept.md** - Fix lines 29-32 to remove non-existent `--actor` and `--test` options

## Attachments

Fixed template versions provided:
- `feedback/spec-kitty/fixed-templates/specify.md`
- `feedback/spec-kitty/fixed-templates/accept.md`

## Verification

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

These commands were tested and confirmed working with correct syntax on spec-kitty 0.10.13.
