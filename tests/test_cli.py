#!/usr/bin/env python3
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Dynamically add src to sys.path for testing purposes
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Import the cli module after adjusting sys.path
from cli import main, check_cloud_env

@pytest.fixture
def mock_config_load():
    with patch('cli.config.load_project_config') as mock_load:
        mock_load.return_value = {} # Default to empty config
        yield mock_load

@pytest.fixture
def mock_sys_exit():
    with patch('sys.exit') as mock_exit:
        yield mock_exit

@pytest.fixture
def capture_stdout(capsys):
    def _capture():
        return capsys.readouterr().out
    return _capture

@pytest.fixture
def mock_projectclone_cli():
    with patch.dict('sys.modules', {'projectclone': MagicMock(), 'projectclone.cli': MagicMock()}):
        yield sys.modules['projectclone'].cli

@pytest.fixture
def mock_projectrestore_cli():
    with patch.dict('sys.modules', {'projectrestore': MagicMock(), 'projectrestore.cli': MagicMock()}):
        yield sys.modules['projectrestore'].cli

@pytest.fixture
def mock_cas_engine():
    with patch.dict('sys.modules', {'projectclone': MagicMock(), 'projectclone.cas_engine': MagicMock()}):
        yield sys.modules['projectclone'].cas_engine

@pytest.fixture
def mock_restore_engine():
    with patch.dict('sys.modules', {'projectrestore': MagicMock(), 'projectrestore.restore_engine': MagicMock()}):
        yield sys.modules['projectrestore'].restore_engine

@pytest.fixture
def mock_list_engine():
    with patch.dict('sys.modules', {'projectclone': MagicMock(), 'projectclone.list_engine': MagicMock()}):
        yield sys.modules['projectclone'].list_engine

@pytest.fixture
def mock_sync_engine():
    with patch.dict('sys.modules', {'projectclone': MagicMock(), 'projectclone.sync_engine': MagicMock()}):
        yield sys.modules['projectclone'].sync_engine

@pytest.fixture
def mock_integrity_engine():
    with patch.dict('sys.modules', {'projectclone': MagicMock(), 'projectclone.integrity_engine': MagicMock()}):
        yield sys.modules['projectclone'].integrity_engine

@pytest.fixture
def mock_gc_engine():
    with patch.dict('sys.modules', {'projectclone': MagicMock(), 'projectclone.gc_engine': MagicMock()}):
        yield sys.modules['projectclone'].gc_engine

class TestMainCli:
    def test_backup_passthrough(self, mock_sys_exit, mock_projectclone_cli, mock_config_load):
        sys.argv = ['pv', 'backup', 'arg1', 'arg2']
        # mock_projectclone_cli is already the mock for the module 'projectclone.cli'
        # so when main() imports it, it gets this mock.
        
        mock_sys_exit.side_effect = SystemExit(0)
        try:
            main()
        except SystemExit:
            pass
        
        mock_projectclone_cli.main.assert_called_once()
        assert sys.argv == ['projectclone', 'arg1', 'arg2']

    def test_archive_restore_passthrough(self, mock_sys_exit, mock_projectrestore_cli, mock_config_load):
        sys.argv = ['pv', 'archive-restore', 'arg1']
        
        mock_sys_exit.side_effect = SystemExit(0)
        try:
            main()
        except SystemExit:
            pass
        
        mock_projectrestore_cli.main.assert_called_once()
        assert sys.argv == ['projectrestore', 'arg1']

    def test_backup_passthrough_with_config_dest(self, mock_sys_exit, mock_projectclone_cli):
         with patch('cli.config.load_project_config', return_value={'vault_path': '/config/vault'}) as mock_load:
            sys.argv = ['pv', 'backup', 'src']
            mock_sys_exit.side_effect = SystemExit(0)
            try:
                main()
            except SystemExit:
                pass
            
            assert '--dest' in sys.argv
            assert '/config/vault' in sys.argv

    def test_no_command_prints_help(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv']
        main()
        output = capture_stdout()
        assert "Project Vault: The Unified Project Lifecycle Manager" in output
        assert "Available Commands" in output
        mock_sys_exit.assert_called_once_with(0)

    def test_clone_command_dispatches(self, mock_sys_exit, mock_projectclone_cli, mock_config_load):
        sys.argv = ['pv', 'backup', 'source_dir', '--dest', 'dest_dir']
        main()
        mock_projectclone_cli.main.assert_called_once()
        assert sys.argv == ['projectclone', 'source_dir', '--dest', 'dest_dir']

    def test_clone_command_dispatches_with_vault_path_from_config(self, mock_sys_exit, mock_projectclone_cli):
        with patch('cli.config.load_project_config', return_value={'vault_path': '/config/vault'}) as mock_load:
            sys.argv = ['pv', 'backup', 'source_dir']
            main()
            mock_projectclone_cli.main.assert_called_once()
            assert sys.argv == ['projectclone', 'source_dir', '--dest', '/config/vault']
            mock_sys_exit.assert_called_once_with(0)

    def test_restore_command_dispatches(self, mock_sys_exit, mock_projectrestore_cli, mock_config_load):
        sys.argv = ['pv', 'archive-restore', 'some_arg']
        main()
        mock_projectrestore_cli.main.assert_called_once()
        assert sys.argv == ['projectrestore', 'some_arg']

    def test_vault_command_calls_cas_engine(self, mock_sys_exit, mock_cas_engine, mock_config_load):
        sys.argv = ['pv', 'vault', 'my_source', '/my_vault_path']
        main()
        mock_cas_engine.backup_to_vault.assert_called_once_with(
            os.path.abspath('my_source'),
            os.path.abspath('/my_vault_path'),
            project_name='my_source'
        )
        mock_sys_exit.assert_not_called()

    def test_vault_command_with_name_calls_cas_engine(self, mock_sys_exit, mock_cas_engine, mock_config_load):
        sys.argv = ['pv', 'vault', 'my_source', '/my_vault_path', '--name', 'custom_name']
        main()
        mock_cas_engine.backup_to_vault.assert_called_once_with(
            os.path.abspath('my_source'),
            os.path.abspath('/my_vault_path'),
            project_name='custom_name'
        )
        mock_sys_exit.assert_not_called()

    def test_vault_command_missing_vault_path_exits(self, mock_sys_exit, capture_stdout, mock_cas_engine, mock_config_load):
        sys.argv = ['pv', 'vault', 'my_source'] 
        main()
        output = capture_stdout()
        assert "Error: vault_path must be specified in CLI or pv.toml" in output
        mock_sys_exit.assert_called_once_with(1)
        mock_cas_engine.backup_to_vault.assert_not_called()

    def test_vault_command_missing_vault_path_from_config_exits(self, mock_sys_exit, capture_stdout, mock_cas_engine):
        with patch('cli.config.load_project_config', return_value={'vault_path': None}) as mock_load:
            sys.argv = ['pv', 'vault', 'my_source']
            main()
            output = capture_stdout()
            assert "Error: vault_path must be specified in CLI or pv.toml" in output
            mock_sys_exit.assert_called_once_with(1)
            mock_cas_engine.backup_to_vault.assert_not_called()

    def test_vault_restore_command_calls_restore_engine(self, mock_sys_exit, mock_restore_engine, mock_config_load):
        sys.argv = ['pv', 'vault-restore', 'manifest.json', 'restore_dest']
        main()
        mock_restore_engine.restore_snapshot.assert_called_once_with(
            os.path.abspath('manifest.json'),
            os.path.abspath('restore_dest')
        )
        mock_sys_exit.assert_not_called()

    def test_check_env_command_calls_check_cloud_env(self, mock_sys_exit, mock_config_load):
        sys.argv = ['pv', 'check-env']
        with patch('cli.check_cloud_env') as mock_check_env:
            main()
            mock_check_env.assert_called_once()
            mock_sys_exit.assert_not_called() 

    def test_sync_command_missing_env_vars(self, mock_sys_exit, capture_stdout, mock_config_load, mock_sync_engine):
        sys.argv = ['pv', 'push', '/vault', '--bucket', 'b', '--endpoint', 'e']
        mock_sys_exit.side_effect = SystemExit(1)
        with patch('os.environ.get', return_value=None):
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error: Cloud credentials missing." in output
            mock_sys_exit.assert_called_with(1)
            mock_sync_engine.sync_to_cloud.assert_not_called()

    def test_sync_command_missing_b2_key_id(self, mock_sys_exit, capture_stdout, mock_config_load, mock_sync_engine):
        sys.argv = ['pv', 'push', '/vault', '--bucket', 'b', '--endpoint', 'e']
        mock_sys_exit.side_effect = SystemExit(1)
        def mock_env_get(key):
            if key == 'B2_APP_KEY': return 'some_app_key'
            return None
        with patch('os.environ.get', side_effect=mock_env_get):
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error: Cloud credentials missing." in output
            mock_sys_exit.assert_called_with(1)
            mock_sync_engine.sync_to_cloud.assert_not_called()

    def test_sync_command_missing_bucket(self, mock_sys_exit, capture_stdout, mock_config_load, mock_sync_engine):
        mock_config_load.return_value = {'vault_path': '/vault'}
        sys.argv = ['pv', 'push', '/vault'] 
        mock_sys_exit.side_effect = SystemExit(1)
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        assert "Error: Bucket must be specified in CLI or pyproject.toml" in output
        mock_sys_exit.assert_called_with(1)
        mock_sync_engine.sync_to_cloud.assert_not_called()

    def test_sync_command_success(self, mock_sys_exit, mock_sync_engine, mock_config_load):
        sys.argv = ['pv', 'push', '/vault', '--bucket', 'b', '--endpoint', 'e']
        with patch('os.environ.get', side_effect=lambda k: 'val' if k in ['B2_KEY_ID', 'B2_APP_KEY'] else None):
            main()
            mock_sync_engine.sync_to_cloud.assert_called_once_with(
                os.path.abspath('/vault'), 'b', 'e', 'val', 'val', dry_run=False
            )

    def test_sync_command_dry_run(self, mock_sys_exit, mock_sync_engine, mock_config_load):
        sys.argv = ['pv', 'push', '/vault', '--bucket', 'b', '--endpoint', 'e', '--dry-run']
        with patch('os.environ.get', side_effect=lambda k: 'val' if k in ['B2_KEY_ID', 'B2_APP_KEY'] else None):
            main()
            mock_sync_engine.sync_to_cloud.assert_called_once_with(
                os.path.abspath('/vault'), 'b', 'e', 'val', 'val', dry_run=True
            )

    def test_pull_command_invalid_bucket(self, mock_sys_exit, capture_stdout, mock_config_load, mock_sync_engine):
        sys.argv = ['pv', 'pull', '/vault']
        mock_sys_exit.side_effect = SystemExit(1)
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        assert "Error: Bucket must be specified in CLI or pyproject.toml" in output
        mock_sys_exit.assert_called_with(1)
        mock_sync_engine.sync_from_cloud.assert_not_called()

    def test_pull_command_success(self, mock_sys_exit, mock_sync_engine, mock_config_load):
        sys.argv = ['pv', 'pull', '/vault', '--bucket', 'b', '--endpoint', 'e']
        with patch('os.environ.get', side_effect=lambda k: 'val' if k in ['B2_KEY_ID', 'B2_APP_KEY'] else None):
            main()
            mock_sync_engine.sync_from_cloud.assert_called_once_with(
                os.path.abspath('/vault'), 'b', 'e', 'val', 'val', dry_run=False
            )

    def test_pull_command_dry_run(self, mock_sys_exit, mock_sync_engine, mock_config_load):
        sys.argv = ['pv', 'pull', '/vault', '--bucket', 'b', '--endpoint', 'e', '--dry-run']
        with patch('os.environ.get', side_effect=lambda k: 'val' if k in ['B2_KEY_ID', 'B2_APP_KEY'] else None):
            main()
            mock_sync_engine.sync_from_cloud.assert_called_once_with(
                os.path.abspath('/vault'), 'b', 'e', 'val', 'val', dry_run=True
            )

    def test_init_pyproject(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'init', '--pyproject']
        main()
        output = capture_stdout()
        assert "[tool.project-vault]" in output

    def test_init_default(self, mock_sys_exit, mock_config_load):
        sys.argv = ['pv', 'init']
        with patch('cli.config.generate_init_file') as mock_gen:
            main()
            mock_gen.assert_called_once_with("pv.toml")

    def test_check_integrity(self, mock_sys_exit, mock_integrity_engine, mock_config_load):
        sys.argv = ['pv', 'check-integrity', '/vault']
        mock_integrity_engine.verify_vault.return_value = True
        main()
        mock_integrity_engine.verify_vault.assert_called_once_with(os.path.abspath('/vault'))

    def test_check_integrity_success(self, mock_sys_exit, mock_integrity_engine, mock_config_load):
        sys.argv = ['pv', 'check-integrity', '/vault']
        mock_integrity_engine.verify_vault.return_value = True
        main()
        mock_integrity_engine.verify_vault.assert_called_once()

    def test_clone_import_error(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'backup', 'src']
        mock_sys_exit.side_effect = SystemExit(1)
        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name == 'projectclone':
                raise ImportError("No module named projectclone")
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error executing command 'backup': No module named projectclone" in output

    def test_restore_import_error(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'archive-restore', 'src']
        mock_sys_exit.side_effect = SystemExit(1)
        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name == 'projectrestore':
                raise ImportError("No module named projectrestore")
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error executing command 'archive-restore': No module named projectrestore" in output

    def test_list_cloud_success(self, mock_sys_exit, mock_list_engine, mock_config_load):
        sys.argv = ['pv', 'list', '--cloud', '--bucket', 'my-bucket']
        with patch('os.environ.get', side_effect=lambda k: 'val' if k in ['B2_KEY_ID', 'B2_APP_KEY'] else None):
            main()
            mock_list_engine.list_cloud_snapshots.assert_called_once_with('my-bucket', 'val', 'val', None)

    def test_list_cloud_missing_bucket(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'list', '--cloud']
        mock_sys_exit.side_effect = SystemExit(1)
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        assert "Error: --bucket must be specified" in output

    def test_list_cloud_missing_creds(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'list', '--cloud', '--bucket', 'my-bucket']
        with patch('os.environ.get', return_value=None):
            mock_sys_exit.side_effect = SystemExit(1)
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error: Cloud credentials missing." in output

    def test_list_local_success(self, mock_sys_exit, mock_list_engine, mock_config_load):
        sys.argv = ['pv', 'list', '/vault']
        main()
        mock_list_engine.list_local_snapshots.assert_called_once_with(os.path.abspath('/vault'))

    def test_list_local_missing_vault(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'list']
        mock_config_load.return_value = {'vault_path': None}
        mock_sys_exit.side_effect = SystemExit(1)
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        assert "Error: vault_path must be specified" in output

    def test_gc_command(self, mock_sys_exit, mock_gc_engine, mock_config_load):
        sys.argv = ['pv', 'gc', '/vault', '--dry-run']
        main()
        mock_gc_engine.run_garbage_collection.assert_called_once_with(os.path.abspath('/vault'), True)

    def test_push_missing_vault_path(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'push']
        mock_config_load.return_value = {'vault_path': None}
        mock_sys_exit.side_effect = SystemExit(1)
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        assert "Error: vault_path must be specified" in output

    def test_push_missing_creds(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'push', '/vault', '--bucket', 'b', '--endpoint', 'e']
        with patch('os.environ.get', return_value=None):
            mock_sys_exit.side_effect = SystemExit(1)
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error: Cloud credentials missing." in output

    def test_pull_missing_vault_path(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'pull']
        mock_config_load.return_value = {'vault_path': None}
        mock_sys_exit.side_effect = SystemExit(1)
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        assert "Error: vault_path must be specified" in output

    def test_gc_missing_vault_path(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'gc']
        mock_config_load.return_value = {'vault_path': None}
        mock_sys_exit.side_effect = SystemExit(1)
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        assert "Error: vault_path must be specified" in output

    def test_get_credentials_b2_only(self):
        from cli import get_credentials
        with patch('os.environ.get') as mock_env:
            def side_effect(key):
                if key == 'B2_KEY_ID': return 'b2key'
                if key == 'B2_APP_KEY': return 'b2app'
                return None
            mock_env.side_effect = side_effect
            key, app = get_credentials()
            assert key == 'b2key'
            assert app == 'b2app'

    def test_get_credentials_aws_priority(self):
        from cli import get_credentials
        with patch('os.environ.get') as mock_env:
            def side_effect(key):
                if key == 'AWS_ACCESS_KEY_ID': return 'awskey'
                if key == 'AWS_SECRET_ACCESS_KEY': return 'awssecret'
                if key == 'B2_KEY_ID': return 'b2key'
                if key == 'B2_APP_KEY': return 'b2app'
                return None
            mock_env.side_effect = side_effect
            key, app = get_credentials()
            assert key == 'awskey'
            assert app == 'awssecret'

class TestCheckCloudEnv:
    @patch('cli.Console')
    @patch('os.environ.get')
    def test_check_cloud_env_b2_present(self, mock_environ_get, MockConsole):
        mock_environ_get.side_effect = lambda x: {"B2_KEY_ID": "id", "B2_APP_KEY": "key"}.get(x)
        mock_console_instance = MockConsole.return_value
        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name in ['boto3', 'b2sdk']: return MagicMock()
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            check_cloud_env()
        mock_console_instance.print.assert_any_call("[green]✅ Found Standard B2 Credentials (B2_KEY_ID, B2_APP_KEY)[/green]")

    @patch('cli.Console')
    @patch('os.environ.get')
    def test_check_cloud_env_b2_pv_present(self, mock_environ_get, MockConsole):
        mock_environ_get.side_effect = lambda x: {"PV_B2_KEY_ID": "id", "PV_B2_APP_KEY": "key"}.get(x)
        mock_console_instance = MockConsole.return_value
        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name in ['boto3', 'b2sdk']: return MagicMock()
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            check_cloud_env()
        mock_console_instance.print.assert_any_call("[green]✅ Found PV-prefixed B2 Credentials (PV_B2_KEY_ID, PV_B2_APP_KEY)[/green]")

    @patch('cli.Console')
    @patch('os.environ.get')
    def test_check_cloud_env_aws_present(self, mock_environ_get, MockConsole):
        mock_environ_get.side_effect = lambda x: {"AWS_ACCESS_KEY_ID": "id", "AWS_SECRET_ACCESS_KEY": "key"}.get(x)
        mock_console_instance = MockConsole.return_value
        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name in ['boto3', 'b2sdk']: return MagicMock()
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            check_cloud_env()
        mock_console_instance.print.assert_any_call("[green]✅ Found Standard AWS/S3 Credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)[/green]")

    @patch('cli.Console')
    @patch('os.environ.get')
    def test_check_cloud_env_aws_pv_present(self, mock_environ_get, MockConsole):
        mock_environ_get.side_effect = lambda x: {"PV_AWS_ACCESS_KEY_ID": "id", "PV_AWS_SECRET_ACCESS_KEY": "key"}.get(x)
        mock_console_instance = MockConsole.return_value
        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name in ['boto3', 'b2sdk']: return MagicMock()
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            check_cloud_env()
        mock_console_instance.print.assert_any_call("[green]✅ Found PV-prefixed AWS/S3 Credentials (PV_AWS_ACCESS_KEY_ID, PV_AWS_SECRET_ACCESS_KEY)[/green]")

    @patch('cli.Console')
    @patch('os.environ.get')
    def test_check_cloud_env_missing_all(self, mock_environ_get, MockConsole):
        mock_environ_get.return_value = None
        mock_console_instance = MockConsole.return_value
        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name in ['boto3', 'b2sdk']: return MagicMock()
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            check_cloud_env()
        mock_console_instance.print.assert_any_call("[yellow]⚠️  Missing B2 Credentials[/yellow]")
        mock_console_instance.print.assert_any_call("[yellow]⚠️  Missing AWS/S3 Credentials[/yellow]")

    @patch('cli.Console')
    @patch('os.environ.get')
    def test_check_cloud_env_boto3_missing(self, mock_environ_get, MockConsole):
        mock_environ_get.return_value = None
        mock_console_instance = MockConsole.return_value
        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name == 'boto3': raise ImportError
            if name == 'b2sdk': return MagicMock()
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            check_cloud_env()
        mock_console_instance.print.assert_any_call("[red]❌ boto3 is missing[/red]")

    @patch('cli.Console')
    @patch('os.environ.get')
    def test_check_cloud_env_b2sdk_missing(self, mock_environ_get, MockConsole):
        mock_environ_get.return_value = None
        mock_console_instance = MockConsole.return_value
        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name == 'b2sdk': raise ImportError
            if name == 'boto3': return MagicMock()
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            check_cloud_env()
        mock_console_instance.print.assert_any_call("[red]❌ b2sdk is missing[/red]")

    def test_keyboard_interrupt_exits_with_130(self, mock_sys_exit, mock_config_load):
        sys.argv = ['pv', 'vault', 'my_source', '/my_vault_path']
        with patch('projectclone.cas_engine.backup_to_vault', side_effect=KeyboardInterrupt):
            main()
            mock_sys_exit.assert_called_once_with(130)

    def test_generic_exception_exits_with_1(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'vault', 'my_source', '/my_vault_path']
        with patch('projectclone.cas_engine.backup_to_vault', side_effect=ValueError("Test error")):
            main()
            output = capture_stdout()
            assert "Error executing command 'vault': Test error" in output
            mock_sys_exit.assert_called_once_with(1)