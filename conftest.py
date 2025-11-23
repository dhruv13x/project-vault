import sys
import os

# Get the absolute path of the project root
root_dir = os.path.dirname(os.path.abspath(__file__))

# Add the sub-project roots to sys.path so 'import projectclone' and 'import projectrestore' work
sys.path.insert(0, os.path.join(root_dir, "projectclone"))
sys.path.insert(0, os.path.join(root_dir, "projectrestore"))
sys.path.insert(0, os.path.join(root_dir, "src"))  # For 'common'
