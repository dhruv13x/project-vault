# src/common/ignore.py

import fnmatch
import re
import os
from typing import List, Pattern, Tuple, Optional

class PathSpec:
    def __init__(self, patterns: List[Tuple[Pattern, bool, bool]]):
        # List of (regex, is_negated, dir_only)
        self.patterns = patterns

    @classmethod
    def from_lines(cls, lines: List[str]) -> 'PathSpec':
        patterns = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            is_negated = line.startswith('!')
            if is_negated:
                pattern = line[1:]
            else:
                pattern = line

            dir_only = pattern.endswith('/')
            if dir_only:
                pattern = pattern[:-1]

            regex = cls._glob_to_regex(pattern, dir_only)
            patterns.append((re.compile(regex), is_negated, dir_only))

        return cls(patterns)

    @staticmethod
    def _glob_to_regex(pattern: str, dir_only: bool) -> str:
        # Check for anchors
        anchored = pattern.startswith('/')
        if anchored:
            pattern = pattern[1:]

        has_slash = '/' in pattern

        # Build regex body
        i = 0
        n = len(pattern)
        res = []
        while i < n:
            c = pattern[i]
            i += 1
            if c == '*':
                if i < n and pattern[i] == '*':
                    i += 1
                    if i < n and pattern[i] == '/':
                        i += 1
                        res.append('(?:.*/)?') # **/ matches zero or more dirs
                    else:
                        res.append('.*') # ** matches anything
                else:
                    res.append('[^/]*') # * matches anything except separator
            elif c == '?':
                res.append('[^/]')
            elif c == '[':
                j = i
                if j < n and pattern[j] == '!':
                    j += 1
                if j < n and pattern[j] == ']':
                    j += 1
                while j < n and pattern[j] != ']':
                    j += 1
                if j >= n:
                    res.append('\\[')
                else:
                    stuff = pattern[i:j].replace('\\', '\\\\')
                    i = j + 1
                    if stuff.startswith('!'):
                        stuff = '^' + stuff[1:]
                    elif stuff.startswith('^'):
                        stuff = '\\^' + stuff[1:]
                    res.append(f'[{stuff}]')
            elif c == '/':
                res.append('/')
            else:
                res.append(re.escape(c))

        regex_body = "".join(res)

        # Base regex construction
        if anchored or has_slash:
             base = f"^{regex_body}"
        else:
             base = f"(?:^|/){regex_body}"

        # If dir_only, we match ONLY if followed by / (or end of string if we append / to candidate)
        if dir_only:
            return f"{base}/(?:.*)?$"
        else:
            return f"{base}(?:/.*)?$"

    def match_file(self, path: str, is_dir: bool = False) -> bool:
        """
        Check if the file matches the ignore patterns.
        Returns True if ignored, False otherwise.
        """
        path = path.replace('\\', '/')

        candidate = path
        if is_dir:
            candidate += '/'

        ignored = False

        for regex, is_negated, dir_only in self.patterns:
            if regex.search(candidate):
                if is_negated:
                    ignored = False
                else:
                    ignored = True

        return ignored

def parse_ignore_file(file_path: str) -> List[str]:
    """
    Parses a gitignore-style file and returns a list of ignore patterns.
    Kept for backward compatibility but use PathSpec.from_lines usually.
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
    Legacy helper. Inefficient for loop use as it recompiles regexes.
    Use PathSpec for bulk operations.
    """
    spec = PathSpec.from_lines(patterns)
    rel_path = os.path.relpath(path, base_dir)
    if rel_path == ".":
        return False

    is_dir = os.path.isdir(path) # This might be costly if called often!
    # Callers should preferably pass is_dir if known.
    # But for compatibility, we check.

    return spec.match_file(rel_path, is_dir=is_dir)
