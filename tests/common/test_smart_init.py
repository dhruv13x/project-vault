import os
import pytest
from src.common import smart_init

class TestSmartInit:
    def test_smart_init_detect_python(self, tmp_path):
        (tmp_path / "pyproject.toml").touch()
        ptypes = smart_init.detect_project_type(str(tmp_path))
        assert "python" in ptypes

    def test_smart_init_detect_node(self, tmp_path):
        (tmp_path / "package.json").touch()
        ptypes = smart_init.detect_project_type(str(tmp_path))
        assert "node" in ptypes

    def test_smart_init_detect_rust(self, tmp_path):
        (tmp_path / "Cargo.toml").touch()
        ptypes = smart_init.detect_project_type(str(tmp_path))
        assert "rust" in ptypes

    def test_smart_init_generate_ignore(self, tmp_path, capsys):
        (tmp_path / "pyproject.toml").touch()
        smart_init.generate_smart_ignore(str(tmp_path))
        captured = capsys.readouterr()
        assert "Created smart .pvignore" in captured.out
        assert (tmp_path / ".pvignore").exists()

    def test_smart_init_generate_ignore_existing(self, tmp_path, capsys):
        (tmp_path / ".pvignore").touch()
        smart_init.generate_smart_ignore(str(tmp_path))
        captured = capsys.readouterr()
        assert "already exists" in captured.out
