# Context Continuity

Created: 2026-01-21
Repo: /Users/kentgale/Vaults-repos/bake-tracker

## Why
We are diagnosing why Codex custom "/" commands are not appearing in the command list. Built-in
Codex commands do appear.

## Current State
- Codex CLI version: 0.87.0 (`codex --version`).
- `~/.codex/commands` and `~/.codex/prompts` do not exist.
- Repo had `.codex/prompts` with spec-kitty markdown files.
- The previous `.codex/commands -> prompts` symlink was removed.
- A real `.codex/commands` directory now exists with a minimal test command.

## Test Command Added
- File: `.codex/commands/hello.md`
- Contents:
  - YAML frontmatter `description: Minimal custom command for discovery test.`
  - Command header `# /hello`
  - Body `Say hello.`

## Next Step After Restart
- Restart Codex and check if `/hello` appears in the command list.
- If it does not, we need to determine whether Codex scans `.codex/commands` in the repo at all
  or if it only scans a global location.

## Notes
- The removal and creation steps required elevated sandbox permissions in this session.

## Update (Latest)
- `/hello` still does not appear after restart.
- Created a global commands directory and copied the test command:
  - `~/.codex/commands/hello.md` (copied from `.codex/commands/hello.md`)

## Next Step
- Restart Codex again and check whether `/hello` appears now.
  - If it appears, Codex is likely only scanning `~/.codex/commands`.
  - If it still does not appear, check `~/.codex/log/codex-tui.log` for command discovery or
    parse errors, and verify any Codex config flags related to custom commands.

## Update (Latest)
- `/hello` still does not appear after restart, even with `~/.codex/commands/hello.md`.
- `~/.codex/log/codex-tui.log` has no custom command discovery or parse error entries.
- `~/.codex/config.toml` only contains project trust config:
  - `[projects."/Users/kentgale/Vaults-repos/bake-tracker"]`
  - `trust_level = "trusted"`
- CLI binary strings include a reference to custom slash commands and
  `https://developers.openai.com/codex/guides/slash-commands#create-your-own-slash-commands-with-custom-prompts`.
- Copied the test command into the global prompts directory:
  - `~/.codex/prompts/hello.md` (copied from `~/.codex/commands/hello.md`)

## Next Step
- Restart Codex and check whether `/hello` appears with the prompt in `~/.codex/prompts`.

## Update (Latest)
- After restart, `/hello` appeared and works when `~/.codex/prompts/hello.md` is present.

## Current Best Hypothesis
- Codex CLI 0.87.0 discovers custom slash commands from `~/.codex/prompts` (not `~/.codex/commands`
  and not repo-local `.codex/commands`).

## Update (Latest)
- Running Codex with debug logging in a real terminal shows:
  - `DEBUG codex_core::codex: Submission ... op: ListCustomPrompts`
  - `DEBUG codex_tui::chatwidget: received 1 custom prompts`
- No log entries show which directories are scanned for custom prompts.

## Update (Latest)
- Added distinct prompts in each location:
  - Repo: `.codex/commands/hello_repo.md` with `/hello_repo`
  - Global: `~/.codex/prompts/hello_global.md` with `/hello_global`
- After restart, the slash command list shows `/hello` and `/hello_global`, but not `/hello_repo`.
- This strongly suggests Codex only scans `~/.codex/prompts` and ignores repo-local `.codex/commands`.

## Update (Latest)
- Found guidance: custom prompts must be in top-level `~/.codex/prompts` (or `$CODEX_HOME/prompts`).
- `CODEX_HOME` is not set in the environment here, so default `~/.codex` is in use.
- No mention of `CODEX_HOME` in spec-kitty docs.
