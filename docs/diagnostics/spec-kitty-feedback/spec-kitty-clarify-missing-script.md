# spec-kitty Bug Report: /spec-kitty.clarify Fails - Missing CLI Command

**Date:** 2026-01-25
**Version:** spec-kitty-cli 0.12.1
**Severity:** High - Entire skill is non-functional
**Reporter:** Claude Opus (via Kent Gale)
**Status:** OPEN - No workaround available

## Summary

The `/spec-kitty.clarify` skill always fails because its template references a CLI command that was never implemented. The template uses a `{SCRIPT}` placeholder that should resolve to a command providing feature paths in JSON format, but:

1. The placeholder is not filled during template generation
2. The generated command file shows `(Missing script command for sh)`
3. No corresponding CLI command exists in spec-kitty

## Root Cause

The clarify template was designed to use a path-discovery script, but that script/command was never implemented:

| Template Variable | Expected | Actual |
|-------------------|----------|--------|
| `{SCRIPT}` | CLI command returning feature paths as JSON | Not implemented |
| Generated output | Valid command | `(Missing script command for sh)` |

## Command Attempted

When the agent tries to interpret the broken template, it guesses at likely commands:

```bash
spec-kitty agent feature get-paths --feature 067-recipe-ui-polish-yield-variants --json
```

## Error Message

```
Usage: spec-kitty agent feature [OPTIONS] COMMAND [ARGS]...
Try 'spec-kitty agent feature --help' for help.
╭─ Error ──────────────────────────────────────────────────────────────────────╮
│ No such command 'get-paths'.                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Available Commands (from --help)

```
spec-kitty agent feature --help

╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ create-feature       Create new feature directory structure in main         │
│                      repository.                                             │
│ check-prerequisites  Validate feature structure and prerequisites.           │
│ setup-plan           Scaffold implementation plan template in main           │
│                      repository.                                             │
│ accept               Perform feature acceptance workflow.                    │
│ merge                Merge feature branch into target branch.                │
│ finalize-tasks       Parse dependencies from tasks.md and update WP          │
│                      frontmatter, then commit to main.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

No `get-paths` command exists.

## Template Analysis

**Source template** (`.kittify/missions/software-dev/command-templates/clarify.md` line 21):

```markdown
1. Run `{SCRIPT}` from repo root **once** (combined `--json --paths-only` mode / `-Json -PathsOnly`). Parse minimal JSON payload fields:
   - `FEATURE_DIR`
   - `FEATURE_SPEC`
   - (Optionally capture `IMPL_PLAN`, `TASKS` for future chained flows.)
```

**Generated Claude command** (`.claude/commands/spec-kitty.clarify.md` line 22):

```markdown
1. Run `(Missing script command for sh)` from repo root **once** (combined `--json --paths-only` mode / `-Json -PathsOnly`).
```

## Comparison with Working Templates

Other skills have proper CLI command references:

| Skill | Template Reference | CLI Command | Status |
|-------|-------------------|-------------|--------|
| `/spec-kitty.plan` | Explicit command | `spec-kitty agent feature setup-plan --json` | ✅ Works |
| `/spec-kitty.implement` | Explicit command | `spec-kitty agent workflow implement WP## --agent` | ✅ Works |
| `/spec-kitty.clarify` | `{SCRIPT}` placeholder | None implemented | ❌ Broken |

## Reproduction Steps

1. Run `/spec-kitty.specify` to create a feature (works fine)
2. Run `/spec-kitty.clarify` on the newly created feature
3. Skill fails immediately when attempting to run the non-existent command

## Impact

**Entire clarify workflow is unusable:**

- Users cannot run the intended spec clarification workflow
- The ambiguity detection and question-asking loop never executes
- Spec quality validation step is skipped

**Workaround burden:**

Currently, agents must manually:
1. Detect the active feature via git branch or glob patterns
2. Construct paths to spec files manually
3. Perform ambiguity scanning without the structured workflow

## Expected Behavior

The template should reference a working CLI command that returns:

```json
{
  "FEATURE_DIR": "/path/to/kitty-specs/###-feature-name",
  "FEATURE_SPEC": "/path/to/kitty-specs/###-feature-name/spec.md",
  "IMPL_PLAN": "/path/to/kitty-specs/###-feature-name/plan.md",
  "TASKS": "/path/to/kitty-specs/###-feature-name/tasks.md"
}
```

## Suggested Fixes

### Option 1: Implement the Missing CLI Command

Add `spec-kitty agent feature get-paths` command:

```python
@feature.command("get-paths")
@click.option("--feature", type=str, help="Feature slug (auto-detected if omitted)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def get_paths(feature: str, as_json: bool):
    """Return paths to feature artifacts."""
    # Detect feature from git branch if not provided
    # Return FEATURE_DIR, FEATURE_SPEC, IMPL_PLAN, TASKS paths
```

### Option 2: Update Template to Use Existing Detection

Replace the `{SCRIPT}` approach with pattern matching:

```markdown
1. Detect active feature:
   - Parse git branch name for feature slug pattern `###-feature-name`
   - OR glob for `kitty-specs/*/spec.md` and select most recent
2. Construct paths:
   - `FEATURE_DIR`: `kitty-specs/{slug}/`
   - `FEATURE_SPEC`: `kitty-specs/{slug}/spec.md`
```

### Option 3: Require Feature Slug as Argument

Update skill to require explicit feature identification:

```markdown
## Usage

/spec-kitty.clarify 067-recipe-ui-polish-yield-variants
```

## Related Issues

- Template variable resolution appears incomplete across the kittify system
- Other templates may have similar unresolved placeholders

## Environment

- OS: macOS Darwin 25.2.0
- spec-kitty-cli: 0.12.1
- Feature attempted: 067-recipe-ui-polish-yield-variants
- Agent: Claude Opus 4.5

## Current Workaround

No automated workaround. Agents must manually:

1. Identify feature path from context or glob patterns
2. Read the spec file directly
3. Perform ambiguity analysis manually
4. Skip the structured clarification workflow

This defeats the purpose of having a `/spec-kitty.clarify` skill.
