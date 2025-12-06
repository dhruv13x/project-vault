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

# We used to remove root_dir here to avoid namespace confusion, but that caused
# the installed 'site-packages' version to win over the local version.
# Now we simply rely on prepending (insert at 0) to ensure local files win.


print(f"DEBUG: inserting {pclone}")
print(f"DEBUG: inserting {prestore}")
print(f"DEBUG: inserting {psrc}")
print(f"DEBUG: inserting {root_dir}")

# Insert all required paths at the beginning to ensure local versions take precedence
# over site-packages. Order matters: sub-projects first, then root.
sys.path.insert(0, psrc)      # For 'common' if imported directly (legacy)
sys.path.insert(0, prestore)
sys.path.insert(0, pclone)
sys.path.insert(0, root_dir)  # For 'src.common' style imports

print(f"DEBUG: sys.path={sys.path}")
