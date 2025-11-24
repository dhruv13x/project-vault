# src/common/smart_init.py
import os

# Default ignore patterns for all project types
BASE_IGNORE = [
    "# Project Vault Ignore File",
    "# Add files and directories here that you want to exclude from snapshots.",
    "",
    "# VCS directories",
    ".git/",
    ".hg/",
    ".svn/",
    "",
    "# Common temporary files",
    "*.swp",
    "*.swo",
    "*~",
    "",
    "# OS-specific files",
    ".DS_Store",
    "Thumbs.db",
    "",
]

# Project-specific ignore patterns
PROJECT_TEMPLATES = {
    "python": [
        "# Python specific",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".Python",
        "build/",
        "develop-eggs/",
        "dist/",
        "downloads/",
        "eggs/",
        ".eggs/",
        "lib/",
        "lib64/",
        "parts/",
        "sdist/",
        "var/",
        "wheels/",
        "share/python-wheels/",
        "*.egg-info/",
        ".installed.cfg",
        "*.egg",
        "MANIFEST",
        "*.manifest",
        "*.spec",
        ".venv/",
        "venv/",
        "ENV/",
        "env/",
        "env.bak/",
        "venv.bak/",
    ],
    "node": [
        "# Node.js specific",
        "node_modules/",
        "npm-debug.log",
        "yarn-debug.log",
        "yarn-error.log",
        "pnpm-debug.log",
        ".npm",
        ".pnpm-store",
        ".yarn-cache",
        ".yarn-integrity",
        ".yarn-metadata.json",
        ".yarn-staging",
        ".yarn-tarball.tgz",
        "*.suo",
        "*.user",
        "*.userosscache",
        "*.sln.docstates",
        ".vs/",
        ".vscode/",
        "*.njsproj",
        "*.sln",
        "*.vsproj",
        ".next/",
        ".nuxt/",
        "dist/",
        "build/",
        "coverage/",
    ],
    "rust": [
        "# Rust specific",
        "target/",
        "Cargo.lock", # Often committed, but for state-capsules maybe not
    ],
}

def detect_project_type(path: str = ".") -> set:
    """
    Detects the project type(s) in a given directory.
    
    Returns a set of strings like {"python", "node"}.
    """
    detected = set()
    if os.path.exists(os.path.join(path, "pyproject.toml")) or \
       os.path.exists(os.path.join(path, "requirements.txt")) or \
       os.path.exists(os.path.join(path, "setup.py")):
        detected.add("python")
        
    if os.path.exists(os.path.join(path, "package.json")):
        detected.add("node")
        
    if os.path.exists(os.path.join(path, "Cargo.toml")):
        detected.add("rust")
        
    return detected

def generate_smart_ignore(path: str = "."):
    """
    Detects project type and creates a .pvignore file.
    """
    project_types = detect_project_type(path)
    
    if not project_types:
        print("Could not detect a specific project type. Creating a generic .pvignore file.")
    else:
        print(f"Detected project types: {', '.join(project_types)}")

    # Combine ignore lists
    content_lines = list(BASE_IGNORE) # Start with a copy
    for p_type in project_types:
        content_lines.append("")
        content_lines.extend(PROJECT_TEMPLATES.get(p_type, []))
        
    # Add self to ignore list
    content_lines.append("")
    content_lines.append("# Ignore the ignore file itself")
    content_lines.append(".pvignore")

    ignore_file_path = os.path.join(path, ".pvignore")
    
    if os.path.exists(ignore_file_path):
        print(f"'{ignore_file_path}' already exists. Skipping.")
        return

    try:
        with open(ignore_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines) + "\n")
        print(f"✅ Created smart .pvignore file at {os.path.abspath(ignore_file_path)}")
    except Exception as e:
        print(f"Error creating .pvignore file: {e}")

if __name__ == '__main__':
    # For direct testing
    generate_smart_ignore()
