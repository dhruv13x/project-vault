import sys
import pytest
from unittest.mock import MagicMock, patch
from src import cli

class TestSrcCliCommands:
    def test_status_command(self):
        with patch("src.projectclone.status_engine.show_status") as mock_status:
            # Patch the config module as imported in src.cli
            with patch("src.cli.config.load_project_config", return_value={'vault_path': 'v'}):
                with patch.object(sys, 'argv', ['pv', 'status', 'src', '--bucket', 'b']):
                    with patch("src.cli.credentials.resolve_credentials", return_value=("k", "s", "Env")):
                        cli.main()
        mock_status.assert_called()

    def test_diff_command(self):
        with patch("src.projectclone.diff_engine.show_diff") as mock_diff:
            with patch("src.cli.config.load_project_config", return_value={'vault_path': 'v'}):
                with patch.object(sys, 'argv', ['pv', 'diff', 'file.txt']):
                    cli.main()
        mock_diff.assert_called()

    def test_checkout_command(self):
        with patch("src.projectclone.checkout_engine.checkout_file") as mock_checkout:
            with patch("src.cli.config.load_project_config", return_value={'vault_path': 'v'}):
                with patch.object(sys, 'argv', ['pv', 'checkout', 'file.txt', '--force']):
                    cli.main()
        mock_checkout.assert_called()
        assert mock_checkout.call_args[1]['force'] is True

    def test_init_command(self):
        with patch("src.common.config.generate_init_file") as mock_gen:
            with patch.object(sys, 'argv', ['pv', 'init']):
                cli.main()
        mock_gen.assert_called_with("pv.toml")

    def test_gc_command(self):
        with patch("src.projectclone.gc_engine.run_garbage_collection") as mock_gc:
            with patch("src.cli.config.load_project_config", return_value={'vault_path': 'v'}):
                with patch.object(sys, 'argv', ['pv', 'gc']):
                    cli.main()
        mock_gc.assert_called()

    def test_check_integrity_command(self):
        with patch("src.projectclone.integrity_engine.verify_vault", return_value=True) as mock_verify:
            with patch("src.cli.config.load_project_config", return_value={'vault_path': 'v'}):
                with patch.object(sys, 'argv', ['pv', 'check-integrity']):
                    cli.main()
        mock_verify.assert_called()

    def test_check_integrity_fail(self):
        with patch("src.projectclone.integrity_engine.verify_vault", return_value=False):
            with patch("src.cli.config.load_project_config", return_value={'vault_path': 'v'}):
                with patch.object(sys, 'argv', ['pv', 'check-integrity']):
                    with pytest.raises(SystemExit) as exc:
                        cli.main()
                    assert exc.value.code == 1
