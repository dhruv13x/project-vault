import pytest
import os
from unittest.mock import patch

from src.common import ignore

@pytest.fixture
def temp_project(tmp_path):
    proj_dir = tmp_path / "my-project"
    proj_dir.mkdir()
    
    (proj_dir / "file.txt").touch()
    (proj_dir / "file.log").touch()
    
    src_dir = proj_dir / "src"
    src_dir.mkdir()
    (src_dir / "main.py").touch()
    (src_dir / "main.pyc").touch()
    
    node_modules = proj_dir / "node_modules"
    node_modules.mkdir()
    (node_modules / "some-lib").touch()
    
    build_dir = proj_dir / "build"
    build_dir.mkdir()
    (build_dir / "output.bin").touch()
    
    return proj_dir

class TestParseIgnoreFile:
    def test_parses_valid_file(self, tmp_path):
        ignore_content = """
# This is a comment
*.log
/node_modules/
build/

# Empty line above
"""
        ignore_file = tmp_path / ".gitignore"
        ignore_file.write_text(ignore_content)
        
        patterns = ignore.parse_ignore_file(str(ignore_file))
        
        assert "*.log" in patterns
        assert "/node_modules/" in patterns
        assert "build/" in patterns
        assert len(patterns) == 3

    def test_returns_empty_for_non_existent_file(self):
        patterns = ignore.parse_ignore_file("non_existent_ignore_file.txt")
        assert patterns == []

    def test_handles_os_error_gracefully(self, tmp_path):
        ignore_file = tmp_path / ".gitignore"
        ignore_file.write_text("dummy content")
        
        with patch("builtins.open", side_effect=OSError("Test read error")):
            patterns = ignore.parse_ignore_file(str(ignore_file))
            assert patterns == []

class TestShouldIgnore:
    def test_basic_file_pattern(self, temp_project):
        patterns = ["*.log"]
        log_file = temp_project / "file.log"
        text_file = temp_project / "file.txt"
        
        assert ignore.should_ignore(str(log_file), patterns, str(temp_project))
        assert not ignore.should_ignore(str(text_file), patterns, str(temp_project))

    def test_directory_pattern(self, temp_project):
        patterns = ["node_modules/"]
        lib_file = temp_project / "node_modules" / "some-lib"
        
        assert ignore.should_ignore(str(lib_file), patterns, str(temp_project))
        # Also test ignoring the directory itself
        assert ignore.should_ignore(str(temp_project / "node_modules"), patterns, str(temp_project))

    def test_ignore_directory_and_contents(self, temp_project):
        patterns = ["build"]
        build_output = temp_project / "build" / "output.bin"
        
        assert ignore.should_ignore(str(build_output), patterns, str(temp_project))
        assert ignore.should_ignore(str(temp_project / "build"), patterns, str(temp_project))

    def test_pattern_in_subdirectory(self, temp_project):
        patterns = ["*.pyc"]
        pyc_file = temp_project / "src" / "main.pyc"
        py_file = temp_project / "src" / "main.py"
        
        assert ignore.should_ignore(str(pyc_file), patterns, str(temp_project))
        assert not ignore.should_ignore(str(py_file), patterns, str(temp_project))

    def test_base_dir_is_not_ignored(self, temp_project):
        patterns = ["my-project/"]
        assert not ignore.should_ignore(str(temp_project), patterns, str(temp_project))
        
    def test_no_match(self, temp_project):
        patterns = ["*.tmp", "dist/"]
        text_file = temp_project / "file.txt"
        py_file = temp_project / "src" / "main.py"
        
        assert not ignore.should_ignore(str(text_file), patterns, str(temp_project))
        assert not ignore.should_ignore(str(py_file), patterns, str(temp_project))
