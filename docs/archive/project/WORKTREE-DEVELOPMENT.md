# Worktree Development Environment Setup

This guide explains how to set up Python development environments for git worktrees in the bake-tracker project.

## The Problem

Each git worktree is a separate working directory. When developing in worktrees, Python can't automatically find the `src/` modules without proper configuration.

## Permanent Solutions

### Solution 1: Automatic Worktree Setup (Recommended)

Use the provided setup scripts to automatically configure any worktree:

#### Windows
```cmd
# From the main project directory
setup-worktree.bat .worktrees\your-worktree-name
```

#### Linux/Mac/WSL
```bash
# From the main project directory
./setup-worktree.sh .worktrees/your-worktree-name
```

This creates several convenience scripts in the worktree:
- `python-dev.bat` / `python-dev.sh` - Python with proper environment
- `test-setup.bat` / `test-setup.sh` - Test the environment setup

#### Example Usage
```bash
cd .worktrees/004-finishedunit
./python-dev.sh -c "from src.services.migration_service import MigrationService; print('works!')"
```

### Solution 2: Development Mode Installation

Install the package in development mode for direct imports:

```bash
cd .worktrees/your-worktree-name
C:\Users\Kent\Vaults-repos\bake-tracker\venv\Scripts\pip.exe install -e .
```

After this, you can use Python directly:
```bash
C:\Users\Kent\Vaults-repos\bake-tracker\venv\Scripts\python.exe -c "from src.services.migration_service import MigrationService; print('works!')"
```

### Solution 3: Manual PYTHONPATH Setup

Set environment variables manually:

#### Windows
```cmd
set PYTHONPATH=.;%PYTHONPATH%
C:\Users\Kent\Vaults-repos\bake-tracker\venv\Scripts\python.exe your_script.py
```

#### Linux/Mac/WSL
```bash
export PYTHONPATH=".:$PYTHONPATH"
C:/Users/Kent/Vaults-repos/bake-tracker/venv/Scripts/python.exe your_script.py
```

## For Claude Code (Bash Tool)

When using Claude Code with the Bash tool, use one of these patterns:

### Method 1: Direct command (current working method)
```bash
cd "C:\Users\Kent\Vaults-repos\bake-tracker\.worktrees\004-finishedunit" && "C:\Users\Kent\Vaults-repos\bake-tracker\venv\Scripts\python.exe" -c "
import sys
sys.path.insert(0, '.')
from src.services.migration_service import MigrationService
result = MigrationService.validate_pre_migration()
print(f'Ready: {result[\"is_ready\"]}')
"
```

### Method 2: Using worktree scripts (after setup)
```bash
cd "C:\Users\Kent\Vaults-repos\bake-tracker\.worktrees\004-finishedunit" && ./python-dev.sh -c "from src.services.migration_service import MigrationService; print('works!')"
```

### Method 3: After development installation
```bash
cd "C:\Users\Kent\Vaults-repos\bake-tracker\.worktrees\004-finishedunit" && "C:\Users\Kent\Vaults-repos\bake-tracker\venv\Scripts\python.exe" -c "from src.services.migration_service import MigrationService; print('works!')"
```

## Quick Setup for New Worktrees

1. **Create worktree** (if not already created):
   ```bash
   git worktree add .worktrees/feature-name origin/feature-name
   ```

2. **Setup development environment**:
   ```bash
   # Option A: Automatic setup
   ./setup-worktree.sh .worktrees/feature-name

   # Option B: Development installation
   cd .worktrees/feature-name
   ../../venv/Scripts/pip.exe install -e .
   ```

3. **Test the setup**:
   ```bash
   cd .worktrees/feature-name
   ./test-setup.sh  # or test-setup.bat on Windows
   ```

## Troubleshooting

### "Module not found" errors
- Ensure you're using the main project's virtual environment
- Check that `src/` directory exists in the worktree
- Verify PYTHONPATH includes current directory

### Import errors with model relationships
- Some models may have relationship issues before database migration
- Use raw SQL queries for pre-migration validation when needed

### Permission errors
- Ensure scripts are executable: `chmod +x script-name.sh`
- Run from correct directory with proper permissions

## Project Structure

```
bake-tracker/                    # Main project
├── venv/                       # Shared virtual environment
├── setup-worktree.bat/.sh     # Worktree setup scripts
├── .worktrees/                 # Worktrees directory
│   └── 004-finishedunit/       # Example worktree
│       ├── python-dev.bat/.sh # Generated environment scripts
│       ├── test-setup.bat/.sh # Generated test scripts
│       └── src/               # Project source code
├── src/                       # Main project source
└── pyproject.toml             # Enhanced with development config
```

## Notes

- All worktrees share the main project's virtual environment
- Development mode installation creates an editable package link
- Setup scripts need to be run only once per worktree
- Scripts are generated automatically and don't need version control