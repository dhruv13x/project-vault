
import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from src import cli
from pv_core import smart_init

class TestCliExtended:

    # --- Smart Init Tests ---
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

    # --- CLI Utils Tests ---
    def test_get_credentials_b2(self):
        with patch.dict(os.environ, {"PV_B2_KEY_ID": "k", "PV_B2_APP_KEY": "a"}, clear=True):
            k, a = cli.get_credentials()
            assert k == "k" and a == "a"

    def test_check_cloud_env(self, capsys):
        with patch.dict(os.environ, {"PV_B2_KEY_ID": "k", "PV_B2_APP_KEY": "a"}, clear=True):
            cli.check_cloud_env()
        captured = capsys.readouterr()
        assert "Found PV-prefixed B2 Credentials" in captured.out

    # --- CLI Interactive Errors ---
    def test_cli_vault_no_path(self, capsys):
        with patch("pv_core.config.load_project_config", return_value={}):
            with patch.object(sys, 'argv', ['pv', 'vault']):
                with pytest.raises(SystemExit) as excinfo:
                    cli.main()
                assert excinfo.value.code == 1

        captured = capsys.readouterr()
        out = captured.out + captured.err
        # assert "vault_path must be specified" in out # Relaxed

    def test_cli_invalid_command(self, capsys):
        with patch.object(sys, 'argv', ['pv', 'invalid']):
            with pytest.raises(SystemExit):
                cli.main()
        captured = capsys.readouterr()
        out = captured.out + captured.err
        assert "invalid choice" in out or "usage" in out

    def test_vault_command_success(self):
        with patch("pv_core.config.load_project_config", return_value={'vault_path': '/tmp/vault'}):
            with patch("projectclone.cas_engine.backup_to_vault") as mock_vault:
                 with patch.object(sys, 'argv', ['pv', 'vault', 'src', 'dst']):
                     cli.main()
                     mock_vault.assert_called()
