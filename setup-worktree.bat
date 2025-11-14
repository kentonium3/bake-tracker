@echo off
REM Worktree Development Environment Setup Script
REM Usage: setup-worktree.bat <worktree-path>
REM Example: setup-worktree.bat .worktrees\004-finishedunit

if "%1"=="" (
    echo Usage: setup-worktree.bat ^<worktree-path^>
    echo Example: setup-worktree.bat .worktrees\004-finishedunit
    exit /b 1
)

set WORKTREE_PATH=%1
set MAIN_PROJECT=%~dp0

echo Setting up development environment for worktree: %WORKTREE_PATH%

REM Check if worktree exists
if not exist "%MAIN_PROJECT%%WORKTREE_PATH%" (
    echo Error: Worktree path does not exist: %MAIN_PROJECT%%WORKTREE_PATH%
    exit /b 1
)

cd /d "%MAIN_PROJECT%%WORKTREE_PATH%"

REM Create Python environment script
echo @echo off > python-dev.bat
echo REM Auto-generated Python development environment for worktree >> python-dev.bat
echo set PYTHONPATH=.;%%PYTHONPATH%% >> python-dev.bat
echo "%MAIN_PROJECT%venv\Scripts\python.exe" %%* >> python-dev.bat

REM Create Shell version
echo #!/bin/bash > python-dev.sh
echo # Auto-generated Python development environment for worktree >> python-dev.sh
echo export PYTHONPATH=".:$PYTHONPATH" >> python-dev.sh
echo "\"%MAIN_PROJECT%venv/Scripts/python.exe\" \"$@\"" >> python-dev.sh
chmod +x python-dev.sh

REM Create Python script version
echo import os, sys, subprocess > python-dev.py
echo # Auto-generated Python development environment for worktree >> python-dev.py
echo os.chdir(os.path.dirname(os.path.abspath(__file__))) >> python-dev.py
echo os.environ['PYTHONPATH'] = '.' + os.pathsep + os.environ.get('PYTHONPATH', '') >> python-dev.py
echo sys.exit(subprocess.call([r'%MAIN_PROJECT%venv\Scripts\python.exe'] + sys.argv[1:])) >> python-dev.py

REM Create test script
echo @echo off > test-setup.bat
echo echo Testing worktree Python environment... >> test-setup.bat
echo python-dev.bat -c "import sys; sys.path.insert(0, '.'); from src.services.migration_service import MigrationService; print('SUCCESS: Worktree environment working!')" >> test-setup.bat

echo.
echo ✅ Worktree setup complete!
echo.
echo Available commands in %WORKTREE_PATH%:
echo   python-dev.bat "python code"     # Windows batch
echo   ./python-dev.sh "python code"    # Shell script
echo   python python-dev.py "args"      # Python wrapper
echo   test-setup.bat                   # Test the setup
echo.
echo Example:
echo   python-dev.bat -c "from src.services.migration_service import MigrationService; print('works!')"