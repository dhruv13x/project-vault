# conftest.py

import sys
import os

# Get the absolute path of the project root
root_dir = os.path.dirname(os.path.abspath(__file__))

print(f"DEBUG: root_dir={root_dir}")

# Add the sub-project roots to sys.path so 'import projectclone' and 'import projectrestore' work
pclone = os.path.join(root_dir, "projectclone")
prestore = os.path.join(root_dir, "projectrestore")
psrc = os.path.join(root_dir, "src")

# Remove root_dir from sys.path to avoid namespace package confusion
if root_dir in sys.path:
    print(f"DEBUG: removing {root_dir} from sys.path")
    sys.path.remove(root_dir)
# Also remove cwd if it matches root_dir (common case)
cwd = os.getcwd()
if cwd == root_dir and cwd in sys.path:
    print(f"DEBUG: removing cwd {cwd} from sys.path")
    sys.path.remove(cwd)

# Also remove "." if present
if "." in sys.path:
    print(f"DEBUG: removing '.' from sys.path")
    sys.path.remove(".")

print(f"DEBUG: inserting {pclone}")
print(f"DEBUG: inserting {prestore}")
print(f"DEBUG: inserting {psrc}")

sys.path.insert(0, pclone)
sys.path.insert(0, prestore)
sys.path.insert(0, psrc)  # For 'common'

# Add root_dir to the END of sys.path to allow imports of scripts/modules in root if any (like conftest itself?)
# But strictly after package roots.
sys.path.append(root_dir)

print(f"DEBUG: sys.path={sys.path}")
