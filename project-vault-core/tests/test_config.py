import pytest
import os
from unittest.mock import patch

from pv_core import config

@pytest.fixture
def temp_dir(tmp_path):
    d = tmp_path / "project"
    d.mkdir()
    return d

class TestLoadProjectConfig:
    def test_load_from_pv_toml(self, temp_dir):
        pv_toml_content = """
bucket = "pv-bucket"
endpoint = "pv-endpoint"
"""
        (temp_dir / "pv.toml").write_text(pv_toml_content)
        
        cfg = config.load_project_config(start_path=str(temp_dir))
        
        assert cfg["bucket"] == "pv-bucket"
        assert cfg["endpoint"] == "pv-endpoint"

    def test_load_from_pyproject_toml(self, temp_dir):
        pyproject_content = """
[tool.project-vault]
bucket = "pyproject-bucket"
vault_path = "/pyproject/vault"
"""
        (temp_dir / "pyproject.toml").write_text(pyproject_content)
        
        cfg = config.load_project_config(start_path=str(temp_dir))
        
        assert cfg["bucket"] == "pyproject-bucket"
        assert cfg["vault_path"] == "/pyproject/vault"

    def test_pv_toml_has_priority(self, temp_dir):
        pv_toml_content = 'bucket = "priority-bucket"'
        (temp_dir / "pv.toml").write_text(pv_toml_content)
        
        pyproject_content = """
[tool.project-vault]
bucket = "secondary-bucket"
"""
        (temp_dir / "pyproject.toml").write_text(pyproject_content)
        
        cfg = config.load_project_config(start_path=str(temp_dir))
        
        assert cfg["bucket"] == "priority-bucket"

    def test_no_config_file_returns_empty(self, temp_dir):
        cfg = config.load_project_config(start_path=str(temp_dir))
        assert cfg == {}

    def test_malformed_pv_toml_is_handled(self, temp_dir, capsys):
        (temp_dir / "pv.toml").write_text("this is not valid toml")
        
        cfg = config.load_project_config(start_path=str(temp_dir))
        
        assert cfg == {}
        captured = capsys.readouterr()
        assert "Warning: Failed to parse" in captured.out

    def test_malformed_pyproject_toml_is_handled(self, temp_dir, capsys):
        (temp_dir / "pyproject.toml").write_text("this is not valid toml")
        
        cfg = config.load_project_config(start_path=str(temp_dir))
        
        assert cfg == {}
        captured = capsys.readouterr()
        assert "Warning: Failed to parse" in captured.out

    @patch('pv_core.config.tomllib', None)
    def test_tomllib_not_available(self, temp_dir):
        cfg = config.load_project_config(start_path=str(temp_dir))
        assert cfg == {}

class TestGenerateInitFile:
    def test_generates_file_with_correct_content(self, temp_dir, capsys):
        target_path = temp_dir / "new_pv.toml"
        
        config.generate_init_file(target_path=str(target_path))
        
        assert target_path.exists()
        content = target_path.read_text()
        assert 'bucket = "my-project-backups"' in content
        assert 'endpoint = "https://s3.eu-central-003.backblazeb2.com"' in content
        
        captured = capsys.readouterr()
        assert f"✅ Created configuration file at {os.path.abspath(target_path)}" in captured.out

    def test_handles_file_creation_error(self, temp_dir, capsys):
        # Path is a directory, so open will fail
        target_path = temp_dir
        
        config.generate_init_file(target_path=str(target_path))
        
        captured = capsys.readouterr()
        assert "Error creating config file:" in captured.out
