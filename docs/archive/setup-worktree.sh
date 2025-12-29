#!/bin/bash
# Worktree Development Environment Setup Script
# Usage: ./setup-worktree.sh <worktree-path>
# Example: ./setup-worktree.sh .worktrees/004-finishedunit

if [ $# -eq 0 ]; then
    echo "Usage: $0 <worktree-path>"
    echo "Example: $0 .worktrees/004-finishedunit"
    exit 1
fi

WORKTREE_PATH="$1"
MAIN_PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Setting up development environment for worktree: $WORKTREE_PATH"

# Check if worktree exists
if [ ! -d "$MAIN_PROJECT/$WORKTREE_PATH" ]; then
    echo "Error: Worktree path does not exist: $MAIN_PROJECT/$WORKTREE_PATH"
    exit 1
fi

cd "$MAIN_PROJECT/$WORKTREE_PATH"

# Create Python environment script (Windows batch)
cat > python-dev.bat << 'EOF'
@echo off
REM Auto-generated Python development environment for worktree
set PYTHONPATH=.;%PYTHONPATH%
"C:\Users\Kent\Vaults-repos\bake-tracker\venv\Scripts\python.exe" %*
EOF

# Create Shell version
cat > python-dev.sh << 'EOF'
#!/bin/bash
# Auto-generated Python development environment for worktree
export PYTHONPATH=".:$PYTHONPATH"
"C:/Users/Kent/Vaults-repos/bake-tracker/venv/Scripts/python.exe" "$@"
EOF
chmod +x python-dev.sh

# Create Python script version
cat > python-dev.py << 'EOF'
import os, sys, subprocess
# Auto-generated Python development environment for worktree
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONPATH'] = '.' + os.pathsep + os.environ.get('PYTHONPATH', '')
sys.exit(subprocess.call([r'C:\Users\Kent\Vaults-repos\bake-tracker\venv\Scripts\python.exe'] + sys.argv[1:]))
EOF

# Create test script
cat > test-setup.sh << 'EOF'
#!/bin/bash
echo "Testing worktree Python environment..."
./python-dev.sh -c "import sys; sys.path.insert(0, '.'); from src.services.migration_service import MigrationService; print('SUCCESS: Worktree environment working!')"
EOF
chmod +x test-setup.sh

echo
echo "✅ Worktree setup complete!"
echo
echo "Available commands in $WORKTREE_PATH:"
echo "  python-dev.bat \"python code\"     # Windows batch"
echo "  ./python-dev.sh \"python code\"    # Shell script"
echo "  python python-dev.py \"args\"      # Python wrapper"
echo "  ./test-setup.sh                   # Test the setup"
echo
echo "Example:"
echo "  ./python-dev.sh -c \"from src.services.migration_service import MigrationService; print('works!')\""