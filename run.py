#!/usr/bin/env python
"""
Launcher script for the Seasonal Baking Tracker application.

This script ensures the correct Python path is set before launching the app.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and run the main application
from src.main import main

if __name__ == "__main__":
    main()
