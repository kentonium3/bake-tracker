#!/bin/bash
# run-tests.sh - Run pytest from anywhere (main repo or worktree)
#
# This script automatically finds and activates the main repo's venv,
# then runs pytest with any arguments passed to it.
#
# Usage:
#   ./run-tests.sh                    # Run all tests
#   ./run-tests.sh -v                 # Verbose
#   ./run-tests.sh src/tests/test_specific.py -v
#   ./run-tests.sh -k "test_name"     # Run specific test by name
#   ./run-tests.sh --cov=src          # With coverage

set -e

# Get the git repo root (works in worktrees too)
REPO_ROOT="$(git rev-parse --show-toplevel)"

# If we're in a worktree (.worktrees/NNN-feature/), get the main repo path
# Worktrees have REPO_ROOT like /path/to/main/.worktrees/NNN-feature
# Main repo has REPO_ROOT like /path/to/main
if [[ "$REPO_ROOT" == *"/.worktrees/"* ]]; then
    MAIN_REPO="${REPO_ROOT%%/.worktrees/*}"
else
    MAIN_REPO="$REPO_ROOT"
fi

# Verify venv exists
if [[ ! -f "$MAIN_REPO/venv/bin/activate" ]]; then
    echo "Error: venv not found at $MAIN_REPO/venv"
    echo "Run: cd $MAIN_REPO && python -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# Activate venv and run pytest
source "$MAIN_REPO/venv/bin/activate"

# Change to main repo so pytest finds src/tests correctly
cd "$MAIN_REPO"

# Run pytest with all passed arguments
pytest "$@"
