# Spec-Kitty AI Assistant Command Generation Analysis

**Submitted:** 2026-01-13
**Spec-Kitty Version:** 0.10.12, 0.10.13

## 1. Executive Summary

This report analyzes a recurring issue where an AI assistant (Claude Code) consistently fails to generate correct command-line invocations for the `spec-kitty` CLI. The root cause is not a single issue, but a combination of three factors:

1.  **AI Model Bias:** The assistant exhibits a strong bias towards a deprecated `spec-kitty` workflow, particularly the use of lane-based subdirectories (`tasks/planned/`, `tasks/doing/`). This behavior persists despite explicit instructions to the contrary.
2.  **Inconsistent Prompt Engineering:** The custom command prompts (`/spec-kitty.*`) provided to the assistant are inconsistent. Some are too vague, forcing the assistant to hallucinate parameters. Others are overly complex, leading to execution errors even when the instructions are technically correct.
3.  **Instruction Adherence Failure:** The assistant demonstrates difficulty in adhering to complex, multi-part instructions, often making small but critical errors, such as omitting a subcommand from a CLI call.

The result is frequent, predictable errors that disrupt the development workflow and require manual intervention.

## 2. Evidence of Failure Modes

The following examples, captured from user-provided logs, illustrate the recurring failure patterns.

### Pattern 1: Hallucinated CLI Arguments

The assistant frequently invents CLI options that do not exist. This occurs when the guiding prompt is too vague.

*   **Command:** `/spec-kitty.specify`
*   **Invocation:** `spec-kitty agent feature create-feature --feature-name "..."`
*   **Error:** `No such option: --feature-name`
*   **Analysis:** The assistant incorrectly used a named option instead of the required positional `FEATURE_SLUG`.

*   **Command:** `/spec-kitty.accept`
*   **Invocation:** `spec-kitty agent feature accept --actor "claude" ...`
*   **Error:** `No such option: --actor`
*   **Analysis:** The assistant invented the `--actor` parameter.

### Pattern 2: Hallucinated CLI Commands

The assistant invents entire commands that do not exist.

*   **Command:** `/spec-kitty.plan`
*   **Invocation:** `spec-kitty agent setup-plan --json`
*   **Error:** `No such command 'setup-plan'`
*   **Analysis:** The assistant attempted to execute a conceptual step ("setup plan") by creating a command name that seemed plausible.

### Pattern 3: Failure to Follow Explicit Instructions

The assistant fails to execute commands exactly as specified in its prompts, particularly when the commands are complex.

*   **Commands:** `/spec-kitty.tasks`, `/spec-kitty.review`
*   **Correct Instruction (from prompt):** `spec-kitty agent feature check-prerequisites ...`
*   **Incorrect Invocation:** `spec-kitty agent check-prerequisites ...`
*   **Error:** `No such command 'check-prerequisites'`
*   **Analysis:** The assistant correctly identified the command but failed to include the required `feature` subcommand. This indicates a failure in precise instruction adherence, likely due to the command's complexity.

### Pattern 4: Reverting to Deprecated Workflows (Model Bias)

This is the most critical issue. The assistant ignores direct, repeated, and emphasized instructions to follow the current workflow, instead reverting to a deprecated one.

*   **Command:** `/spec-kitty.implement`
*   **Project Instructions (`CLAUDE.md`, `tasks.md`):** Explicitly and repeatedly forbid the creation of lane-based subdirectories (`tasks/planned/`, etc.), stating that task state is managed via frontmatter.
*   **Assistant Action:** The logs show the assistant creating and checking for files within `tasks/planned/` and `tasks/doing/`, directly violating its core instructions.
*   **Analysis:** This demonstrates a powerful model bias that overrides explicit, negative constraints. The assistant is "stuck" on an old workflow pattern it learned from its training data, and the current prompting strategy is insufficient to correct it.

## 3. Root Cause Analysis

The investigation of the project's AI guidance files (`CLAUDE.md`, `.kittify/missions/*`) reveals the underlying causes of the failures above.

1.  **Vague Prompts Cause Hallucination:** Prompts like `/spec-kitty.implement` simply instruct the AI to run `spec-kitty ... $ARGUMENTS` without defining what arguments are valid. This directly encourages the model to guess or "hallucinate" parameters, leading to the errors seen in Pattern 1 and 2.

2.  **Overly Complex Prompts Cause Execution Errors:** The prompt for `/spec-kitty.tasks` is a long, multi-step procedure. While it contains the correct command, its complexity increases the cognitive load on the assistant, making it more likely to make small execution errors like omitting a subcommand (Pattern 3).

3.  **Prompting is Insufficient to Overcome Model Bias:** The project maintainers are clearly aware of the assistant's bias (Pattern 4), as evidenced by the numerous, "CRITICAL" warnings in `CLAUDE.md` and `tasks.md`. However, these warnings are not working reliably. The model's ingrained "habit" is proving stronger than the negative constraints in the prompts.

## 4. Recommendations for `spec-kitty`

To create a more reliable AI-assisted workflow, the `spec-kitty` project's command templates should be updated to account for the specific strengths and weaknesses of LLM agents.

1.  **Replace Vague Prompts with Explicit Instructions:** Prompts should never force the agent to guess.
    *   **Bad:** `run command $ARGUMENTS`
    *   **Good:** `Run 'spec-kitty my-command --help' to see available options. Then, run the command with the required '--name' and '--output' parameters.`
    This encourages an interactive, discovery-based approach that is more reliable than memory or guessing.

2.  **Simplify Command-Chains:** A single prompt that requires a 7-step process with file I/O and data parsing is too fragile for current models. Break down complex operations.
    *   **Instead of one `/tasks` command:** Create `/tasks.check`, `/tasks.generate`, `/tasks.write-prompts` as separate, simpler skills. Each step can validate its predecessor's output, creating a more robust and debuggable workflow.

3.  **Reinforce Against Bias with Guardrails:** Since negative constraints ("don't do X") are not sufficient, add programmatic guardrails or validation steps.
    *   **Example:** Before the main `implement` logic, add a command to the prompt: `spec-kitty agent feature validate-task-structure`. This command would fail if it detects any deprecated subdirectory, stopping the AI before it proceeds with the incorrect workflow. This turns a "rule" into a "verifiable condition."

By making prompts more explicit, simplifying complex workflows, and adding validation guardrails, `spec-kitty` can provide a more robust and reliable experience for users leveraging AI assistants.
