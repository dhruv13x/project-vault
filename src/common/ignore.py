# src/common/ignore.py

import fnmatch
import os
from typing import List

def parse_ignore_file(file_path: str) -> List[str]:
    """
    Parses a gitignore-style file and returns a list of ignore patterns.

    Args:
        file_path: The path to the ignore file (e.g., .gitignore).

    Returns:
        A list of valid ignore patterns. Returns an empty list if the file
        cannot be read or does not exist.
    """
    patterns = []
    if not os.path.exists(file_path):
        return patterns

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
    except OSError:
        pass
    
    return patterns


def should_ignore(path: str, patterns: List[str], base_dir: str) -> bool:
    """
    Determines if a given path should be ignored based on the provided patterns.

    Args:
        path: The absolute path of the file or directory to check.
        patterns: A list of glob patterns (e.g., ["*.pyc", "node_modules/"]).
        base_dir: The root directory of the project (used to calculate relative paths).

    Returns:
        True if the path matches any ignore pattern, False otherwise.
    """
    rel_path = os.path.relpath(path, base_dir)
    
    # Normalizing path separators for consistent matching
    rel_path = rel_path.replace(os.sep, '/')

    # If we are checking the base_dir itself, don't ignore it unless explicitly told to
    if rel_path == ".":
        return False

    for pattern in patterns:
        # Handling directory-specific patterns (ending with /)
        if pattern.endswith("/"):
            # If pattern expects a directory, but our path isn't one or doesn't match, skip
            # Note: checking os.path.isdir might be slow if doing this for many files.
            # Often, ignoring "dir/" implies ignoring "dir" and everything under it.
            
            clean_pattern = pattern.rstrip("/")
            
            # 1. Check if the directory itself matches (dist/ matches dist)
            if fnmatch.fnmatch(rel_path, clean_pattern):
                return True
            
            # 2. Check if the file is inside the ignored directory (dist/ matches dist/file.txt)
            if rel_path.startswith(clean_pattern + "/"):
                return True
        else:
            # Standard file matching
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            
            # Check if the file is inside a directory that matches the pattern
            # (e.g. pattern "build" should match "build/output.txt")
            # This is a simplification; precise gitignore logic is complex, 
            # but this covers the "ignore folder content" case.
            if rel_path.startswith(pattern + "/"):
                return True
                
            # Handle "name" matching anywhere in path if no slash in pattern
            # (e.g. "*.pyc" matches "src/foo.pyc")
            if "/" not in pattern:
                if fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                    return True

    return False
