---
description: Validate feature readiness and guide final acceptance steps.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Discovery (mandatory)

Before running the acceptance workflow, gather the following:

1. **Feature slug** (e.g., `005-awesome-thing`). If omitted, detect automatically from current branch.
2. **Acceptance mode**:
   - `auto` (default): Automatically determine based on context
   - `pr` when the feature will merge via hosted pull request.
   - `local` when the feature will merge locally without a PR.
   - `checklist` to run the readiness checklist without committing or producing merge instructions.
3. **Lenient mode** (optional): Whether to skip strict metadata validation (default: false)
4. **No-commit mode** (optional): Whether to skip auto-commit and produce report only (default: false)

Ask one focused question per item and confirm the summary before continuing. End the discovery turn with `WAITING_FOR_ACCEPTANCE_INPUT` until all answers are provided.

## Execution Plan

1. Compile the acceptance options into an argument list:
   - Append `--feature "<slug>"` when the user supplied a slug (otherwise auto-detected).
   - Append `--mode <mode>` (`auto`, `pr`, `local`, or `checklist`).
   - Append `--lenient` if user requested lenient validation.
   - Append `--no-commit` if user requested report-only mode.
2. Run `spec-kitty agent feature accept` with the assembled arguments **and** `--json`.
3. Parse the JSON response. It contains:
   - `summary.ok` (boolean) and other readiness details.
   - `summary.outstanding` categories when issues remain.
   - `instructions` (merge steps) and `cleanup_instructions`.
   - `notes` (e.g., acceptance commit hash).
4. Present the outcome:
   - If `summary.ok` is `false`, list each outstanding category with bullet points and advise the user to resolve them before retrying acceptance.
   - If `summary.ok` is `true`, display:
     - Acceptance timestamp and (if present) acceptance commit hash.
     - Merge instructions and cleanup instructions as ordered steps.
5. When the mode is `checklist`, make it clear no commits or merge instructions were produced.

## Output Requirements

- Summaries must be in plain text (no tables). Use short bullet lists for instructions.
- Surface outstanding issues before any congratulations or success messages.
- If the JSON payload includes warnings, surface them under an explicit **Warnings** section.
- Never fabricate results; only report what the JSON contains.

## Error Handling

- If the command fails or returns invalid JSON, report the failure and request user guidance (do not retry automatically).
- When outstanding issues exist, do **not** attempt to force acceptance—return the checklist and prompt the user to fix the blockers.

## CLI Reference

```bash
# Basic acceptance (auto-detect feature and mode)
spec-kitty agent feature accept --json

# Explicit feature and mode
spec-kitty agent feature accept --json --feature "001-my-feature" --mode local

# Lenient mode (skip strict validation)
spec-kitty agent feature accept --json --lenient

# Report only (no commit)
spec-kitty agent feature accept --json --no-commit
```

## Available Options

| Option | Description | Default |
|--------|-------------|---------|
| `--feature` | Feature directory slug | Auto-detected from branch |
| `--mode` | Acceptance mode: auto, pr, local, checklist | auto |
| `--json` | Output results as JSON for agent parsing | - |
| `--lenient` | Skip strict metadata validation | false |
| `--no-commit` | Skip auto-commit (report only) | false |
