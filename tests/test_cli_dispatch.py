
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from src import cli_dispatch

# Custom exception to simulate exit
class ExitException(Exception):
    pass

class TestCliDispatch:

    @pytest.fixture
    def mock_console(self):
        with patch("src.cli_dispatch.console") as mock:
            yield mock

    @pytest.fixture
    def mock_exit(self):
        with patch("sys.exit", side_effect=ExitException) as mock:
            yield mock

    def test_resolve_path(self, fs):
        # Allow os.path.expanduser to work as expected by pyfakefs
        # pyfakefs usually mocks the home directory

        path = cli_dispatch.resolve_path("~/foo")
        expected = os.path.abspath(os.path.expanduser("~/foo"))
        assert path == expected

        # abspath logic
        cwd = os.getcwd()
        path = cli_dispatch.resolve_path("foo/bar")
        expected = os.path.abspath("foo/bar")
        assert path == expected

        os.environ["TEST_VAR"] = "bar"
        path = cli_dispatch.resolve_path("foo/$TEST_VAR")
        expected = os.path.abspath("foo/bar")
        assert path == expected

        assert cli_dispatch.resolve_path(None) is None

    @patch("src.common.paths.get_default_vault_path")
    @patch("src.projectclone.cas_engine.backup_to_vault")
    def test_handle_vault_command_missing_path(self, mock_backup, mock_get_default, mock_console, mock_exit, tmp_path):
        args = MagicMock(vault_path=None, source="/source")
        args.name = None
        mock_get_default.return_value = str(tmp_path / "default_vault")
        mock_backup.return_value = "manifest"
        
        cli_dispatch.handle_vault_command(args, {})
        
        mock_get_default.assert_called_once()
        mock_backup.assert_called_once()
        mock_exit.assert_not_called()

    @patch("src.projectclone.cas_engine.backup_to_vault")
    def test_handle_vault_command_success(self, mock_backup, mock_console):
        args = MagicMock(vault_path="vault", source="source")
        args.name = "name"
        args.include_db = False
        mock_backup.return_value = "manifest_path"

        cli_dispatch.handle_vault_command(args, {})

        mock_backup.assert_called_once()

    @patch("src.projectclone.cas_engine.backup_to_vault")
    def test_handle_vault_command_with_hooks(self, mock_backup, mock_console):
        args = MagicMock(vault_path="vault", source="source")
        args.name = "name"
        args.include_db = False
        defaults = {"hooks": {"pre-backup": "echo hello"}}

        cli_dispatch.handle_vault_command(args, defaults)

        mock_console.print.assert_any_call("[bold yellow]⚠ Lifecycle Hooks Detected[/bold yellow]")
        _, kwargs = mock_backup.call_args
        assert kwargs['hooks'] == defaults['hooks']

    @patch("src.projectclone.cas_engine.backup_to_vault")
    def test_handle_vault_command_exception(self, mock_backup, mock_console):
        args = MagicMock(vault_path="vault", source="source")
        args.name = "name"
        args.include_db = False
        mock_backup.side_effect = Exception("error")
        notifier = MagicMock()

        with pytest.raises(Exception):
            cli_dispatch.handle_vault_command(args, {}, notifier=notifier)

        notifier.send_message.assert_called()

    def test_handle_vault_restore_command_missing_dest(self, mock_console, mock_exit):
        args = MagicMock(dest=None)
        with pytest.raises(ExitException):
            cli_dispatch.handle_vault_restore_command(args, {})
        mock_exit.assert_called_with(1)

    @patch("src.projectrestore.restore_engine.restore_snapshot")
    def test_handle_vault_restore_command_success(self, mock_restore, mock_console):
        args = MagicMock(dest="dest", manifest="manifest")

        cli_dispatch.handle_vault_restore_command(args, {})

        mock_restore.assert_called_once()

    @patch("src.projectrestore.restore_engine.restore_snapshot")
    def test_handle_vault_restore_command_with_hooks(self, mock_restore, mock_console):
        args = MagicMock(dest="dest", manifest="manifest")
        defaults = {"hooks": {"pre-restore": "echo hello"}}

        cli_dispatch.handle_vault_restore_command(args, defaults)

        mock_console.print.assert_any_call("[bold red]⚠ Lifecycle Hooks Detected[/bold red]")
        _, kwargs = mock_restore.call_args
        assert kwargs['hooks'] == defaults['hooks']

    def test_handle_capsule_export_missing_args(self, mock_console, mock_exit):
        args = MagicMock(manifest=None)
        with pytest.raises(ExitException):
            cli_dispatch.handle_capsule_export_command(args, {})
        mock_exit.assert_called_with(1)

        args = MagicMock(manifest="manifest", output=None)
        with pytest.raises(ExitException):
            cli_dispatch.handle_capsule_export_command(args, {})
        mock_exit.assert_called_with(1)

    @patch("src.common.capsule.pack_capsule")
    def test_handle_capsule_export_success(self, mock_pack, mock_console):
        args = MagicMock(manifest="manifest", output="output")
        mock_pack.return_value = "capsule_path"

        cli_dispatch.handle_capsule_export_command(args, {})

        mock_pack.assert_called_once()
        mock_console.print.assert_called_with("[success]✅ Capsule exported to: capsule_path[/success]")

    @patch("src.common.capsule.pack_capsule")
    def test_handle_capsule_export_exception(self, mock_pack, mock_console, mock_exit):
        args = MagicMock(manifest="manifest", output="output")
        mock_pack.side_effect = Exception("error")

        with pytest.raises(ExitException):
            cli_dispatch.handle_capsule_export_command(args, {})

        mock_console.print.assert_called_with("[error]Error exporting capsule: error[/error]")
        mock_exit.assert_called_with(1)

    def test_handle_capsule_import_missing_args(self, mock_console, mock_exit):
        args = MagicMock(capsule=None)
        with pytest.raises(ExitException):
            cli_dispatch.handle_capsule_import_command(args, {})
        mock_exit.assert_called_with(1)

    @patch("src.common.capsule.unpack_capsule")
    def test_handle_capsule_import_success(self, mock_unpack, mock_console):
        args = MagicMock(capsule="capsule", vault_path="vault")
        mock_unpack.return_value = "manifest_path"

        cli_dispatch.handle_capsule_import_command(args, {})

        mock_unpack.assert_called_once()

    @patch("src.common.capsule.unpack_capsule")
    def test_handle_capsule_import_exception(self, mock_unpack, mock_console, mock_exit):
        args = MagicMock(capsule="capsule", vault_path="vault")
        mock_unpack.side_effect = Exception("error")

        with pytest.raises(ExitException):
            cli_dispatch.handle_capsule_import_command(args, {})

        mock_console.print.assert_called_with("[error]Error importing capsule: error[/error]")
        mock_exit.assert_called_with(1)

    def test_handle_init_command_pyproject(self, capsys):
        args = MagicMock(pyproject=True)
        cli_dispatch.handle_init_command(args)
        captured = capsys.readouterr()
        assert "[tool.project-vault]" in captured.out

    def test_handle_init_command_default(self, capsys):
        # We need to mock 'src.common.config' and 'src.common.smart_init'
        # Since these are imported inside the function, we patch sys.modules

        args = MagicMock(pyproject=False, smart=True)

        mock_config = MagicMock()
        mock_smart = MagicMock()

        with patch.dict(sys.modules, {
            'src.common.config': mock_config,
            'src.common.smart_init': mock_smart,
            'src.common': MagicMock(config=mock_config, smart_init=mock_smart)
        }):
            cli_dispatch.handle_init_command(args)

        # Verify calls
        mock_config.generate_init_file.assert_called_with("pv.toml")
        mock_smart.generate_smart_ignore.assert_called_once()

    @patch("src.common.paths.get_default_vault_path")
    @patch("src.projectclone.status_engine.show_status")
    def test_handle_status_command_missing_path(self, mock_status, mock_get_default, mock_console, mock_exit, tmp_path):
        args = MagicMock(vault_path=None, source="/source", bucket=None)
        mock_get_default.return_value = str(tmp_path / "default_vault")
        
        cli_dispatch.handle_status_command(args, {}, None)
        
        mock_get_default.assert_called_once()
        mock_status.assert_called_once()
        mock_exit.assert_not_called()

    @patch("src.projectclone.status_engine.show_status")
    def test_handle_status_command_success(self, mock_status, mock_console):
        args = MagicMock(vault_path="vault", source="source", bucket=None)
        cli_dispatch.handle_status_command(args, {}, None)
        mock_status.assert_called_once()

    @patch("src.projectclone.status_engine.show_status")
    def test_handle_status_command_cloud(self, mock_status, mock_console):
        args = MagicMock(vault_path="vault", source="source", bucket="bucket", endpoint="endpoint")
        creds_module = MagicMock()
        creds_module.resolve_credentials.return_value = ("key", "secret", "source")

        cli_dispatch.handle_status_command(args, {}, creds_module)

        mock_status.assert_called_once()

    @patch("src.common.paths.get_default_vault_path")
    @patch("src.projectclone.diff_engine.show_diff")
    def test_handle_diff_command_missing_path(self, mock_diff, mock_get_default, mock_console, mock_exit, tmp_path):
        args = MagicMock(vault_path=None, file="file")
        mock_get_default.return_value = str(tmp_path / "default_vault")
        
        cli_dispatch.handle_diff_command(args, {})
        
        mock_get_default.assert_called_once()
        mock_diff.assert_called_once()
        mock_exit.assert_not_called()

    @patch("src.projectclone.diff_engine.show_diff")
    def test_handle_diff_command_success(self, mock_diff, mock_console):
        args = MagicMock(vault_path="vault", file="file")
        cli_dispatch.handle_diff_command(args, {})
        mock_diff.assert_called_once()

    @patch("src.common.paths.get_default_vault_path")
    @patch("src.projectclone.checkout_engine.checkout_file")
    def test_handle_checkout_command_missing_path(self, mock_checkout, mock_get_default, mock_console, mock_exit, tmp_path):
        args = MagicMock(vault_path=None, file="file", force=False)
        mock_get_default.return_value = str(tmp_path / "default_vault")
        
        cli_dispatch.handle_checkout_command(args, {})
        
        mock_get_default.assert_called_once()
        mock_checkout.assert_called_once()
        mock_exit.assert_not_called()

    @patch("src.projectclone.checkout_engine.checkout_file")
    def test_handle_checkout_command_success(self, mock_checkout, mock_console):
        args = MagicMock(vault_path="vault", file="file", force=False)
        cli_dispatch.handle_checkout_command(args, {})
        mock_checkout.assert_called_once()

    @patch("src.common.paths.get_default_vault_path")
    @patch("src.tui.ProjectVaultApp")
    def test_handle_browse_command_missing_path(self, mock_app, mock_get_default, mock_console, mock_exit, tmp_path):
        args = MagicMock(vault_path=None)
        args.name = None
        mock_get_default.return_value = str(tmp_path / "default_vault")
        
        cli_dispatch.handle_browse_command(args, {})
        
        mock_get_default.assert_called_once()
        mock_app.assert_called_once()
        mock_exit.assert_not_called()

    @patch("src.tui.ProjectVaultApp")
    def test_handle_browse_command_success(self, mock_app, mock_console):
        args = MagicMock(vault_path="vault")
        args.name = "myproject" # Set attribute explicitly to avoid MagicMock(name=...) confusion

        cli_dispatch.handle_browse_command(args, {})

        mock_app.assert_called_once()
        mock_app.return_value.run.assert_called_once()

    def test_handle_list_command_cloud_missing_bucket(self, mock_console, mock_exit):
        args = MagicMock(cloud=True, bucket=None)
        with pytest.raises(ExitException):
            cli_dispatch.handle_list_command(args, {}, None)
        mock_exit.assert_called_with(1)

    def test_handle_list_command_cloud_missing_creds(self, mock_console, mock_exit):
        args = MagicMock(cloud=True, bucket="bucket")
        creds_module = MagicMock()
        creds_module.resolve_credentials.return_value = (None, None, None)

        with pytest.raises(ExitException):
            cli_dispatch.handle_list_command(args, {}, creds_module)
        mock_exit.assert_called_with(1)

    @patch("src.projectclone.list_engine.list_cloud_snapshots")
    def test_handle_list_command_cloud_success(self, mock_list, mock_console):
        args = MagicMock(cloud=True, bucket="bucket", endpoint="endpoint")
        creds_module = MagicMock()
        creds_module.resolve_credentials.return_value = ("key", "secret", "source")

        cli_dispatch.handle_list_command(args, {}, creds_module)

        mock_list.assert_called_once()

    @patch("src.common.paths.get_default_vault_path")
    @patch("src.projectclone.list_engine.list_local_snapshots")
    def test_handle_list_command_local_missing_path(self, mock_list, mock_get_default, mock_console, mock_exit, tmp_path):
        args = MagicMock(cloud=False, vault_path=None)
        mock_get_default.return_value = str(tmp_path / "default_vault")
        
        cli_dispatch.handle_list_command(args, {}, None)
        
        mock_get_default.assert_called_once()
        mock_list.assert_called_once()
        mock_exit.assert_not_called()

    @patch("src.projectclone.list_engine.list_local_snapshots")
    def test_handle_list_command_local_success(self, mock_list, mock_console):
        args = MagicMock(cloud=False, vault_path="vault")
        cli_dispatch.handle_list_command(args, {}, None)
        mock_list.assert_called_once()

    @patch("src.common.paths.get_default_vault_path")
    def test_handle_push_command_missing_args(self, mock_get_default, mock_console, mock_exit):
        # Test missing vault path (gets defaulted) AND missing bucket (errors out)
        args = MagicMock(vault_path=None, bucket=None)
        mock_get_default.return_value = "/default/vault"
        
        with pytest.raises(ExitException):
            cli_dispatch.handle_push_command(args, {}, None)
        
        # Ensure default path was fetched
        mock_get_default.assert_called()
        # Ensure bucket check failed
        mock_console.print.assert_called_with("[error]Error: Bucket must be specified in CLI or pyproject.toml[/error]")
        mock_exit.assert_called_with(1)

        # Reset for next case
        mock_exit.reset_mock()
        
        # Provided path but missing bucket
        args = MagicMock(vault_path="vault", bucket=None)
        with pytest.raises(ExitException):
            cli_dispatch.handle_push_command(args, {}, None)
        mock_exit.assert_called_with(1)

    def test_handle_push_command_missing_creds(self, mock_console, mock_exit):
        args = MagicMock(vault_path="vault", bucket="bucket")
        creds_module = MagicMock()
        creds_module.resolve_credentials.return_value = (None, None, None)
        with pytest.raises(ExitException):
            cli_dispatch.handle_push_command(args, {}, creds_module)
        mock_exit.assert_called_with(1)

    @patch("src.projectclone.sync_engine.sync_to_cloud")
    def test_handle_push_command_success(self, mock_sync, mock_console):
        args = MagicMock(vault_path="vault", bucket="bucket", endpoint="endpoint", dry_run=False)
        creds_module = MagicMock()
        creds_module.resolve_credentials.return_value = ("key", "secret", "source")
        notifier = MagicMock()

        cli_dispatch.handle_push_command(args, {}, creds_module, notifier)

        mock_sync.assert_called_once()
        notifier.send_message.assert_called_once()

    @patch("src.projectclone.sync_engine.sync_to_cloud")
    def test_handle_push_command_exception(self, mock_sync, mock_console):
        args = MagicMock(vault_path="vault", bucket="bucket", endpoint="endpoint", dry_run=False)
        creds_module = MagicMock()
        creds_module.resolve_credentials.return_value = ("key", "secret", "source")
        notifier = MagicMock()
        mock_sync.side_effect = Exception("error")

        with pytest.raises(Exception):
            cli_dispatch.handle_push_command(args, {}, creds_module, notifier)

        notifier.send_message.assert_called()

    @patch("src.common.paths.get_default_vault_path")
    def test_handle_pull_command_missing_args(self, mock_get_default, mock_console, mock_exit, tmp_path):
        # Test missing vault path (gets defaulted) AND missing bucket (errors out)
        args = MagicMock(vault_path=None, bucket=None)
        mock_get_default.return_value = str(tmp_path / "default_vault")
        
        with pytest.raises(ExitException):
            cli_dispatch.handle_pull_command(args, {}, None)
            
        mock_get_default.assert_called()
        mock_exit.assert_called_with(1)

        args = MagicMock(vault_path="vault", bucket=None)
        with pytest.raises(ExitException):
            cli_dispatch.handle_pull_command(args, {}, None)
        mock_exit.assert_called_with(1)

    def test_handle_pull_command_missing_creds(self, mock_console, mock_exit):
        args = MagicMock(vault_path="vault", bucket="bucket")
        creds_module = MagicMock()
        creds_module.resolve_credentials.return_value = (None, None, None)
        with pytest.raises(ExitException):
            cli_dispatch.handle_pull_command(args, {}, creds_module)
        mock_exit.assert_called_with(1)

    @patch("src.projectclone.sync_engine.sync_from_cloud")
    def test_handle_pull_command_success(self, mock_sync, mock_console):
        args = MagicMock(vault_path="vault", bucket="bucket", endpoint="endpoint", dry_run=False)
        creds_module = MagicMock()
        creds_module.resolve_credentials.return_value = ("key", "secret", "source")

        cli_dispatch.handle_pull_command(args, {}, creds_module)

        mock_sync.assert_called_once()

    @patch("src.common.paths.get_default_vault_path")
    @patch("src.projectclone.integrity_engine.verify_vault")
    def test_handle_check_integrity_command_missing_path(self, mock_verify, mock_get_default, mock_console, mock_exit, tmp_path):
        args = MagicMock(vault_path=None)
        mock_get_default.return_value = str(tmp_path / "default_vault")
        mock_verify.return_value = True
        
        cli_dispatch.handle_check_integrity_command(args, {})
        
        mock_get_default.assert_called_once()
        mock_verify.assert_called_once()
        mock_exit.assert_not_called()

    @patch("src.projectclone.integrity_engine.verify_vault")
    def test_handle_check_integrity_command_success(self, mock_verify, mock_console, mock_exit):
        args = MagicMock(vault_path="vault")
        mock_verify.return_value = True
        cli_dispatch.handle_check_integrity_command(args, {})
        mock_verify.assert_called_once()
        mock_exit.assert_not_called()

    @patch("src.projectclone.integrity_engine.verify_vault")
    def test_handle_check_integrity_command_fail(self, mock_verify, mock_console, mock_exit):
        args = MagicMock(vault_path="vault")
        mock_verify.return_value = False
        with pytest.raises(ExitException):
            cli_dispatch.handle_check_integrity_command(args, {})
        mock_exit.assert_called_with(1)

    @patch("src.common.paths.get_default_vault_path")
    @patch("src.projectclone.gc_engine.run_garbage_collection")
    def test_handle_gc_command_missing_path(self, mock_gc, mock_get_default, mock_console, mock_exit, tmp_path):
        args = MagicMock(vault_path=None, dry_run=True)
        mock_get_default.return_value = str(tmp_path / "default_vault")
        
        cli_dispatch.handle_gc_command(args, {})
        
        mock_get_default.assert_called_once()
        mock_gc.assert_called_once()
        mock_exit.assert_not_called()

    @patch("src.projectclone.gc_engine.run_garbage_collection")
    def test_handle_gc_command_success(self, mock_gc, mock_console):
        args = MagicMock(vault_path="vault", dry_run=False)
        cli_dispatch.handle_gc_command(args, {})
        mock_gc.assert_called_once()

    def test_handle_verify_clone_command_missing_paths(self, mock_console, mock_exit):
        args = MagicMock(original_path="nonexistent", clone_path="nonexistent")
        # pyfakefs default state is empty, so paths don't exist
        with pytest.raises(ExitException):
            cli_dispatch.handle_verify_clone_command(args, {})
        mock_exit.assert_called_with(1)

    @patch("src.projectclone.verify_engine.verify_directories")
    def test_handle_verify_clone_command_success(self, mock_verify, mock_console, fs):
        args = MagicMock(original_path="/orig", clone_path="/clone")
        fs.create_dir("/orig")
        fs.create_dir("/clone")

        mock_verify.return_value = MagicMock(success=True)

        cli_dispatch.handle_verify_clone_command(args, {})

        mock_verify.assert_called_with(os.path.abspath("/orig"), os.path.abspath("/clone"))

    @patch("src.projectclone.verify_engine.verify_directories")
    def test_handle_verify_clone_command_fail(self, mock_verify, mock_console, mock_exit, fs):
        args = MagicMock(original_path="/orig", clone_path="/clone")
        fs.create_dir("/orig")
        fs.create_dir("/clone")

        mock_verify.return_value = MagicMock(success=False, errors=["Error 1"])

        with pytest.raises(ExitException):
            cli_dispatch.handle_verify_clone_command(args, {})

        mock_exit.assert_called_with(1)

    def test_handle_config_command_missing_file(self, mock_console, mock_exit, fs):
        # fs is empty
        args = MagicMock(config_command="set-creds")
        with pytest.raises(ExitException):
            cli_dispatch.handle_config_command(args)

        mock_exit.assert_called_with(1)

    def test_handle_config_command_security_lock(self, mock_console, mock_exit, fs):
        args = MagicMock(config_command="set-creds")
        fs.create_file("pv.toml", contents="[credentials]\n")

        with pytest.raises(ExitException):
            cli_dispatch.handle_config_command(args)

        mock_exit.assert_called_with(1)

    def test_handle_config_command_success(self, mock_console, fs):
        args = MagicMock(config_command="set-creds", key_id="new_key", secret_key="new_secret")

        fs.create_file("pv.toml", contents="[credentials]\nallow_insecure_storage = true\nkey_id = \"old\"\n")

        cli_dispatch.handle_config_command(args)

        with open("pv.toml", "r") as f:
            content = f.read()

        assert 'key_id = "new_key"' in content
        assert 'secret_key = "new_secret"' in content

    def test_check_cloud_env(self, mock_console):
        creds_module = MagicMock()
        creds_module.resolve_credentials.return_value = ("key", "secret", "source")
        creds_module.get_cloud_provider_info.return_value = ("AWS", "bucket", "endpoint")

        cli_dispatch.check_cloud_env(creds_module)

    def test_handle_notify_test_command(self, mock_console):
        notifier = MagicMock()
        cli_dispatch.handle_notify_test_command(notifier)
        notifier.send_message.assert_called_once()

        cli_dispatch.handle_notify_test_command(None)
        mock_console.print.assert_called_with("[error]Notifier not initialized. Check your config/env.[/error]")
