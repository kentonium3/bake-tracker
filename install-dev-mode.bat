@echo off
REM Install bake-tracker in development mode for any worktree
REM Usage: install-dev-mode.bat [worktree-path]
REM Example: install-dev-mode.bat .worktrees\004-finishedunit

if "%1"=="" (
    echo Installing in current directory...
    set WORKTREE_PATH=.
) else (
    echo Installing in worktree: %1
    set WORKTREE_PATH=%1
)

set MAIN_PROJECT=%~dp0

REM Check if target directory exists
if not exist "%MAIN_PROJECT%%WORKTREE_PATH%\src" (
    echo Error: No src directory found in %MAIN_PROJECT%%WORKTREE_PATH%
    echo This doesn't appear to be a valid bake-tracker directory.
    exit /b 1
)

cd /d "%MAIN_PROJECT%%WORKTREE_PATH%"

echo Installing bake-tracker in development mode...
"%MAIN_PROJECT%venv\Scripts\pip.exe" install -e .

if %ERRORLEVEL% == 0 (
    echo.
    echo ✅ Development mode installation successful!
    echo.
    echo You can now run Python from anywhere with:
    echo   python -c "from src.services.migration_service import MigrationService; print('works!')"
    echo.
    echo To test:
    "%MAIN_PROJECT%venv\Scripts\python.exe" -c "from src.services.migration_service import MigrationService; print('✅ Development installation working!')"
) else (
    echo.
    echo ❌ Development mode installation failed.
    echo Check that setup.py or pyproject.toml is properly configured.
)