# Instructions for Claude Code: Generating Cursor Review Prompts

## Purpose
Create a prompt that enables Cursor to perform an independent code review as a senior software engineer discovering this feature for the first time. The goal is to leverage Cursor's fresh perspective to find issues that might be missed when the implementer reviews their own work.

## Output Location
Write the prompt to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F[FEATURE_NUMBER]-review-prompt.md`

Example: For F040, write to `cursor-F040-review-prompt.md`

## Context to Provide

**Feature Information:**
- Feature number, title, and high-level user goal
- Full path to spec file(s) defining requirements

**Code Changes:**
- List of files modified (full paths)
- Note: "These are the primary changes, but review should extend to any related code, dependencies, or callers as needed"

**Environment Setup:**
- Basic verification commands to confirm environment is functional (imports work, tests run)
- **CRITICAL: Explicitly state "Run these commands OUTSIDE the sandbox"**
- **Explain why: "Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures."**
- Keep commands minimal - just enough to verify setup, NOT feature-specific test scenarios

**Report Template:**
- Direct Cursor to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_cursor_report.md`

**Report Output Location:**
- Instruct Cursor to write report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F[FEATURE_NUMBER]-review.md`
- Example: For F040, write to `cursor-F040-review.md`
- Emphasize: Write to docs/code-reviews/ directory, NOT in worktree

## Review Approach - Instruct Cursor To:

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - Cursor's sandbox cannot activate venvs. If ANY command fails, STOP immediately and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use template format and write to specified location

## What NOT to Include

- Detailed test cases or verification procedures (let Cursor devise its own)
- Specific code locations to examine beyond listing modified files
- Expected findings or known issues
- Prescriptive checklists of what to verify
- Implementation approach guidance
- Suggestions about what issues to look for

## Key Principle
Provide enough context for Cursor to understand what was built and why, but let Cursor determine independently how to evaluate quality, what to test, and what might be wrong. The value comes from Cursor's different perspective and priorities.

## Operational Notes
- Verification commands MUST be run outside sandbox to avoid venv activation failures
- If verification commands fail, Cursor should stop and report blocker before attempting fixes
- Report goes in docs/code-reviews/ directory, not in worktree
- Issues will be fixed before running spec-kitty.review command
