# Cursor terminal runner flakiness (macOS) — diagnosis & permanent mitigation

This repo is frequently reviewed via Cursor’s agent-driven terminal runner (pytest, greps, etc.). If you repeatedly see errors like:

- `spawn /usr/bin/sandbox-exec ENOENT`
- `spawn /bin/zsh ENOENT`
- Python venv access errors when running commands “in sandbox”

…and a Cursor restart temporarily “fixes” it, use this doc to stabilize the environment.

## What’s happening (most common causes)

- **Workspace settings point at Windows executables** (e.g. `venv/Scripts/python.exe`). On macOS, this can break Python/terminal integration and contribute to runner instability.
- **Shell mismatch**: Cursor (or the agent runner) tries to spawn `/bin/zsh`, but the runner process ends up in a context where zsh spawning fails.
- **Sandbox incompatibility**: When commands run through a sandbox mechanism, the runner may not be able to access your `venv/` or may fail to launch the sandbox helper.
- **Deleted worktree / invalid working directory (very common with Spec Kitty)**: if a feature worktree is removed while Cursor (or its runner helper) still has that worktree as its `cwd`, subsequent spawns can fail with `spawn ... ENOENT` until Cursor is restarted.

## Permanent mitigation (recommended)

### 1) Force a stable shell for the workspace (bash on macOS)

This repo now includes workspace settings that prefer `/bin/bash` on macOS:

- `.vscode/settings.json` sets:
  - `terminal.integrated.defaultProfile.osx = bash`
  - `terminal.integrated.profiles.osx.bash.path = /bin/bash`

After pulling the change:
- Fully restart Cursor once.
- Open a new integrated terminal tab to ensure the profile takes effect.

### 2) Ensure the Python interpreter path is correct for macOS

This repo now points to:
- `python.defaultInterpreterPath = ${workspaceFolder}/venv/bin/python3`

If your venv is elsewhere, update your **User** settings (preferred) rather than editing the repo.

### 3) Disable sandboxed execution for local commands (if enabled)

If Cursor has any setting resembling “run commands in sandbox / restricted mode”, disable it for this workspace. The symptoms usually include:
- inability to read `venv/pyvenv.cfg`
- commands failing only when run via the agent runner, but succeeding in your normal terminal

Exact label varies by Cursor version; search in Settings for: `sandbox`, `restricted`, `secure`, `command execution`.

### 4) Avoid deleting a worktree while Cursor is “inside” it

This is the most common “it breaks once per review, restart fixes it” pattern when using Spec Kitty worktrees.

- Before running `/spec-kitty.merge` (which may remove the feature worktree), ensure **all terminals** are not currently `cd`’d into the feature worktree.
- After merge completes, do a quick reset:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker
```

If you still see runner failures after merge, open a **new** integrated terminal tab (or use “Developer: Reload Window”) to force Cursor to drop any stale `cwd`.

## Quick health check

Run these in a normal integrated terminal (not via agent) to validate your environment:

```bash
echo "$SHELL"
command -v bash zsh python3
ls -l /bin/bash /bin/zsh
python3 -V
./venv/bin/python3 -V
PYTHONPATH=. ./venv/bin/pytest -q src/tests
```

If those pass but agent-run commands fail, the issue is in Cursor’s runner layer; apply the mitigations above and restart Cursor.

## If it still happens

Collect the following and attach it to a Cursor bug report (or keep in `docs/diagnostics/`):

- Cursor version
- Whether the workspace is local vs remote
- The exact error text (`spawn ... ENOENT`, etc.)
- Output of the health check above
- Whether it reproduces only after long sessions or after sleep/wake


