# Feedback Report: specify.md Template Uses Incorrect CLI Command Path

**Repository:** Priivacy-ai/spec-kitty
**Status:** Not yet filed - local fix applied
**Discovered:** 2026-01-10
**Reporter:** bake-tracker project (F047 Materials Management System)

---

## Summary

The `specify.md` command template contains an incorrect CLI command path. The template references `spec-kitty agent create-feature` but the actual CLI structure is `spec-kitty agent feature create-feature`.

## Error Encountered

```
$ spec-kitty agent create-feature --json --feature-name "Materials Management System" --mission "software-dev"
Error: Exit code 2
Usage: spec-kitty agent [OPTIONS] COMMAND [ARGS]...
Try 'spec-kitty agent --help' for help.

No such command 'create-feature'. Did you mean 'feature'?
```

## Root Cause

The template files have incorrect command paths in the YAML frontmatter:

**Affected files:**
- `.kittify/templates/command-templates/specify.md` (lines 4-5)
- `.kittify/missions/software-dev/command-templates/specify.md` (lines 4-5)

**Incorrect (in templates):**
```yaml
scripts:
  sh: spec-kitty agent create-feature --json "{ARGS}"
  ps: spec-kitty agent create-feature --json "{ARGS}"
```

**Also incorrect example on line 144:**
```
spec-kitty agent create-feature --json --feature-name "Checkout Upsell Flow" --mission "software-dev"
```

**Correct (per actual CLI):**
```yaml
scripts:
  sh: spec-kitty agent feature create-feature --json "{ARGS}"
  ps: spec-kitty agent feature create-feature --json "{ARGS}"
```

## CLI Structure Verification

```
$ spec-kitty agent --help
Commands:
  feature    Feature lifecycle commands for AI agents
  tasks      Task workflow commands for AI agents
  context    Agent context management commands
  release    Release packaging commands for AI agents
  workflow   Workflow commands that display prompts and instructions for agents

$ spec-kitty agent feature --help
Commands:
  create-feature        Create new feature with worktree and directory structure.
  check-prerequisites   Validate feature structure and prerequisites.
  setup-plan            Scaffold implementation plan template.
  accept                Perform feature acceptance workflow.
  merge                 Merge feature branch into target branch.
```

The command hierarchy is:
- `spec-kitty agent` -> top-level agent commands
- `spec-kitty agent feature` -> feature lifecycle commands
- `spec-kitty agent feature create-feature` -> the actual create command

The template is missing the `feature` subcommand level.

## Workaround Applied

Agent was able to recover by:
1. Checking `spec-kitty agent --help` when the command failed
2. Discovering the correct command path
3. Running the correct command: `spec-kitty agent feature create-feature --json ...`

## Local Fix Applied

Updated the following files in the main bake-tracker repository:
- `.kittify/templates/command-templates/specify.md`
- `.kittify/missions/software-dev/command-templates/specify.md`

Changed:
- Lines 4-5: `spec-kitty agent create-feature` -> `spec-kitty agent feature create-feature`
- Line 144: Updated example to use correct path

## Relationship to Previous Issue

This is similar to the issue documented in `spec-kitty-template-cli-mismatch.md` where upgrade paths don't refresh template content. Both issues stem from templates containing outdated CLI syntax that doesn't match the actual v0.10.12 CLI structure.

## Recommendation

1. **Immediate:** Fix the command path in upstream spec-kitty templates
2. **Upgrade path:** Consider adding template content validation during `spec-kitty upgrade` to detect CLI command mismatches
3. **Defense in depth:** Templates could use the simplified `spec-kitty agent workflow specify` pattern instead of embedding CLI syntax directly
