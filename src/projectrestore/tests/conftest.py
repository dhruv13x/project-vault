# src/projectrestore/tests/conftest.py

import sys
import os

# Get the path to project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_restore_root = os.path.abspath(os.path.join(current_dir, ".."))
src_root = os.path.abspath(os.path.join(project_restore_root, ".."))
app_root = os.path.abspath(os.path.join(src_root, ".."))

# Ensure app_root is in sys.path so we can do 'from src import ...'
if app_root not in sys.path:
    sys.path.insert(0, app_root)

from src.projectrestore import modules