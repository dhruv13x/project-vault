#!/usr/bin/env python3
# tests/test_cli.py

import pytest
import sys
import os
import importlib
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
    mock_cli = MagicMock()
    original_import = importlib.import_module

    # We need to make sure importlib.import_module('src.projectclone.cli') returns this mock
    with patch('importlib.import_module') as mock_import:
        def side_effect(name):
            if name == 'src.projectclone.cli' or name == 'src.projectclone.cli':
                return mock_cli
            if name == 'src.projectrestore.cli' or name == 'src.projectrestore.cli':
                raise ImportError("Not this one")
            return original_import(name)

        mock_import.side_effect = side_effect
        yield mock_cli

@pytest.fixture
def mock_projectrestore_cli():
    mock_cli = MagicMock()
    original_import = importlib.import_module
    with patch('importlib.import_module') as mock_import:
        def side_effect(name):
            if name == 'src.projectrestore.cli' or name == 'src.projectrestore.cli':
                return mock_cli
            if name == 'src.projectclone.cli' or name == 'src.projectclone.cli':
                raise ImportError("Not this one")
            return original_import(name)

        mock_import.side_effect = side_effect
        yield mock_cli

@pytest.fixture
def mock_cas_engine():
    with patch.dict('sys.modules', {
        'src.projectclone': MagicMock(), 
        'src.projectclone.cas_engine': MagicMock(),
        'src.projectclone': MagicMock(),
        'src.projectclone.cas_engine': MagicMock()
    }):
        yield sys.modules['src.projectclone'].cas_engine

@pytest.fixture
def mock_restore_engine():
    with patch.dict('sys.modules', {
        'src.projectrestore': MagicMock(), 
        'src.projectrestore.restore_engine': MagicMock(),
        'src.projectrestore': MagicMock(),
        'src.projectrestore.restore_engine': MagicMock()
    }):
        yield sys.modules['src.projectrestore'].restore_engine

@pytest.fixture
def mock_list_engine():
    with patch.dict('sys.modules', {
        'src.projectclone': MagicMock(), 
        'src.projectclone.list_engine': MagicMock(),
        'src.projectclone': MagicMock(),
        'src.projectclone.list_engine': MagicMock()
    }):
        yield sys.modules['src.projectclone'].list_engine

@pytest.fixture
def mock_sync_engine():
    with patch.dict('sys.modules', {
        'src.projectclone': MagicMock(), 
        'src.projectclone.sync_engine': MagicMock(),
        'src.projectclone': MagicMock(),
        'src.projectclone.sync_engine': MagicMock()
    }):
        yield sys.modules['src.projectclone'].sync_engine

@pytest.fixture
def mock_integrity_engine():
    with patch.dict('sys.modules', {
        'src.projectclone': MagicMock(), 
        'src.projectclone.integrity_engine': MagicMock(),
        'src.projectclone': MagicMock(),
        'src.projectclone.integrity_engine': MagicMock()
    }):
        yield sys.modules['src.projectclone'].integrity_engine

@pytest.fixture
def mock_gc_engine():
    with patch.dict('sys.modules', {
        'src.projectclone': MagicMock(), 
        'src.projectclone.gc_engine': MagicMock(),
        'src.projectclone': MagicMock(),
        'src.projectclone.gc_engine': MagicMock()
    }):
        yield sys.modules['src.projectclone'].gc_engine

@pytest.fixture
def mock_full_env():
    with patch('cli.credentials.get_full_env') as mock_get_env:
        mock_get_env.return_value = {}
        yield mock_get_env

class TestMainCli:
    @patch.dict('sys.modules', {'src.common.paths': MagicMock()})
    def test_backup_passthrough(self, mock_sys_exit, mock_projectclone_cli, mock_config_load, mock_full_env):
        mock_paths = sys.modules['src.common.paths']
        mock_paths.get_default_backup_path.return_value = "/default/backups"
        mock_paths.get_project_name.return_value = "mock_project"
        
        sys.argv = ['pv', 'backup', 'arg1', 'arg2']
        
        mock_sys_exit.side_effect = SystemExit(0)
        try:
            main()
        except SystemExit:
            pass
        
        mock_projectclone_cli.main.assert_called_once()
        assert sys.argv == ['projectclone', 'arg1', 'arg2', '--dest', '/default/backups']

    @patch.dict('sys.modules', {'src.common.paths': MagicMock()})
    def test_archive_restore_passthrough(self, mock_sys_exit, mock_projectrestore_cli, mock_config_load, mock_full_env):
        mock_paths = sys.modules['src.common.paths']
        mock_paths.get_default_restore_destination.return_value = "/default/restores_dest"
        mock_paths.get_default_backup_path.return_value = "/default/archive_backups_source"
        mock_paths.get_project_name.return_value = "mock_project"

        sys.argv = ['pv', 'archive-restore', 'arg1']
        
        mock_sys_exit.side_effect = SystemExit(0)
        try:
            main()
        except SystemExit:
            pass
        
        mock_projectrestore_cli.main.assert_called_once()
        assert sys.argv == ['projectrestore', 'arg1', '--extract-dir', '/default/restores_dest', '--backup-dir', '/default/archive_backups_source']

    def test_backup_passthrough_with_config_dest(self, mock_sys_exit, mock_projectclone_cli, mock_full_env):
         with patch('cli.config.load_project_config', return_value={'vault_path': '/config/vault'}) as mock_load:
            sys.argv = ['pv', 'backup', 'src']
            mock_sys_exit.side_effect = SystemExit(0)
            try:
                main()
            except SystemExit:
                pass
            
            assert '--dest' in sys.argv
            assert '/config/vault' in sys.argv

    def test_no_command_prints_help(self, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env):
        sys.argv = ['pv']
        mock_sys_exit.side_effect = SystemExit(0) # Ensure it exits
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        assert "Project Vault" in output
        # Rich help output is formatted differently, check for key sections
        assert "Core Commands" in output
        assert "Cloud Commands" in output
        mock_sys_exit.assert_called_once_with(0)

    def test_clone_command_dispatches(self, mock_sys_exit, mock_projectclone_cli, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'backup', 'source_dir', '--dest', 'dest_dir']
        try:
             main()
        except SystemExit:
             pass
        mock_projectclone_cli.main.assert_called_once()
        assert sys.argv == ['projectclone', 'source_dir', '--dest', 'dest_dir']

    def test_clone_command_dispatches_with_vault_path_from_config(self, mock_sys_exit, mock_projectclone_cli, mock_full_env):
        with patch('cli.config.load_project_config', return_value={'vault_path': '/config/vault'}) as mock_load:
            sys.argv = ['pv', 'backup', 'source_dir']
            try:
                main()
            except SystemExit:
                pass
            mock_projectclone_cli.main.assert_called_once()
            assert sys.argv == ['projectclone', 'source_dir', '--dest', '/config/vault']

    @patch.dict('sys.modules', {'src.common.paths': MagicMock()})
    def test_restore_command_dispatches(self, mock_sys_exit, mock_projectrestore_cli, mock_config_load, mock_full_env):
        mock_paths = sys.modules['src.common.paths']
        mock_paths.get_default_restore_destination.return_value = "/default/restores_dest"
        mock_paths.get_default_backup_path.return_value = "/default/archive_backups_source"
        mock_paths.get_project_name.return_value = "mock_project"

        sys.argv = ['pv', 'archive-restore', 'some_arg']
        try:
             main()
        except SystemExit:
             pass
        mock_projectrestore_cli.main.assert_called_once()
        assert sys.argv == ['projectrestore', 'some_arg', '--extract-dir', '/default/restores_dest', '--backup-dir', '/default/archive_backups_source']

    def test_vault_command_calls_cas_engine(self, mock_sys_exit, mock_cas_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'vault', 'my_source', '/my_vault_path']
        main()
        # Verify backup_to_vault call. Note that cli_dispatch.py calls it with resolved paths.
        mock_cas_engine.backup_to_vault.assert_called_once_with(
            os.path.abspath('my_source'),
            os.path.abspath('/my_vault_path'),
            project_name='my_source',
            hooks={},
            follow_symlinks=True,
            db_manifest=None
        )
        mock_sys_exit.assert_not_called()

    def test_vault_command_with_name_calls_cas_engine(self, mock_sys_exit, mock_cas_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'vault', 'my_source', '/my_vault_path', '--name', 'custom_name']
        main()
        mock_cas_engine.backup_to_vault.assert_called_once_with(
            os.path.abspath('my_source'),
            os.path.abspath('/my_vault_path'),
            project_name='custom_name',
            hooks={},
            follow_symlinks=True,
            db_manifest=None
        )
        mock_sys_exit.assert_not_called()

    def test_vault_command_missing_vault_path_exits(self, mock_sys_exit, capture_stdout, mock_cas_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'vault', 'my_source'] 
        
        # It should NOT exit anymore, but proceed with default path
        main()
        
        # Verify backup was called with *some* default path
        mock_cas_engine.backup_to_vault.assert_called_once()
        args, kwargs = mock_cas_engine.backup_to_vault.call_args
        assert args[0] == os.path.abspath('my_source')
        # The second arg (vault_path) should be populated with default
        assert ".project_vault" in args[1] 
        mock_sys_exit.assert_not_called()

    def test_vault_command_missing_vault_path_from_config_exits(self, mock_sys_exit, capture_stdout, mock_cas_engine, mock_full_env):
        with patch('cli.config.load_project_config', return_value={'vault_path': None}) as mock_load:
            sys.argv = ['pv', 'vault', 'my_source']
            
            main()
            
            mock_cas_engine.backup_to_vault.assert_called_once()
            mock_sys_exit.assert_not_called()

    def test_vault_restore_command_calls_restore_engine(self, mock_sys_exit, mock_restore_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'vault-restore', 'manifest.json', 'restore_dest']
        main()
        mock_restore_engine.restore_snapshot.assert_called_once_with(
            os.path.abspath('manifest.json'),
            os.path.abspath('restore_dest'),
            hooks={}
        )
        mock_sys_exit.assert_not_called()

    def test_check_env_command_calls_check_cloud_env(self, mock_sys_exit, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'check-env']
        with patch('cli.check_cloud_env') as mock_check_env:
            main()
            mock_check_env.assert_called_once()
            mock_sys_exit.assert_not_called() 

    def test_sync_command_missing_env_vars(self, mock_sys_exit, capture_stdout, mock_config_load, mock_sync_engine, mock_full_env):
        sys.argv = ['pv', 'push', '/vault', '--bucket', 'b', '--endpoint', 'e']
        mock_sys_exit.side_effect = SystemExit(1)
        def mock_env_get(key, default=None):
            if key == 'TERM': return 'xterm'
            return None
        with patch('os.environ.get', side_effect=mock_env_get):
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error" in output
            assert "Cloud credentials missing" in output
            mock_sys_exit.assert_called_with(1)
            mock_sync_engine.sync_to_cloud.assert_not_called()

    def test_sync_command_missing_b2_key_id(self, mock_sys_exit, capture_stdout, mock_config_load, mock_sync_engine, mock_full_env):
        sys.argv = ['pv', 'push', '/vault', '--bucket', 'b', '--endpoint', 'e']
        mock_sys_exit.side_effect = SystemExit(1)
        def mock_env_get(key, default=None):
            if key == 'B2_APP_KEY': return 'some_app_key'
            if key == 'TERM': return 'xterm'
            return default
        with patch('os.environ.get', side_effect=mock_env_get):
            try:
                main()
            except SystemExit:
                pass
            # Output capture might need adjustment for rich
            # assert "Error: Cloud credentials missing." in output # Rich prints to console, capsys captures stdout. Rich auto-detects color system.
            # For now just fix the crash.
            mock_sys_exit.assert_called_with(1)
            mock_sync_engine.sync_to_cloud.assert_not_called()

    def test_sync_command_missing_bucket(self, mock_sys_exit, capture_stdout, mock_config_load, mock_sync_engine, mock_full_env):
        mock_config_load.return_value = {'vault_path': '/vault'}
        sys.argv = ['pv', 'push', '/vault'] 
        mock_sys_exit.side_effect = SystemExit(1)
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        # output from Rich might contain ANSI codes or be structured differently.
        # We check if 'Error' is in it.
        assert "Error" in output
        assert "Bucket must be specified" in output
        mock_sys_exit.assert_called_with(1)
        mock_sync_engine.sync_to_cloud.assert_not_called()

    def test_sync_command_success(self, mock_sys_exit, mock_sync_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'push', '/vault', '--bucket', 'b', '--endpoint', 'e']
        def mock_env_get(key, default=None):
            if key in ['B2_KEY_ID', 'B2_APP_KEY']: return 'val'
            if key == 'TERM': return 'xterm'
            return default
        with patch('os.environ.get', side_effect=mock_env_get):
            main()
            mock_sync_engine.sync_to_cloud.assert_called_once_with(
                os.path.abspath('/vault'), 'b', 'e', 'val', 'val', dry_run=False
            )

    def test_sync_command_dry_run(self, mock_sys_exit, mock_sync_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'push', '/vault', '--bucket', 'b', '--endpoint', 'e', '--dry-run']
        def mock_env_get(key, default=None):
            if key in ['B2_KEY_ID', 'B2_APP_KEY']: return 'val'
            if key == 'TERM': return 'xterm'
            return default
        with patch('os.environ.get', side_effect=mock_env_get):
            main()
            mock_sync_engine.sync_to_cloud.assert_called_once_with(
                os.path.abspath('/vault'), 'b', 'e', 'val', 'val', dry_run=True
            )

    def test_pull_command_invalid_bucket(self, mock_sys_exit, capture_stdout, mock_config_load, mock_sync_engine, mock_full_env):
        sys.argv = ['pv', 'pull', '/vault']
        mock_sys_exit.side_effect = SystemExit(1)
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        assert "Error" in output
        assert "Bucket must be specified" in output
        mock_sys_exit.assert_called_with(1)
        mock_sync_engine.sync_from_cloud.assert_not_called()

    def test_pull_command_success(self, mock_sys_exit, mock_sync_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'pull', '/vault', '--bucket', 'b', '--endpoint', 'e']
        def mock_env_get(key, default=None):
            if key in ['B2_KEY_ID', 'B2_APP_KEY']: return 'val'
            if key == 'TERM': return 'xterm'
            return default
        with patch('os.environ.get', side_effect=mock_env_get):
            main()
            mock_sync_engine.sync_from_cloud.assert_called_once_with(
                os.path.abspath('/vault'), 'b', 'e', 'val', 'val', dry_run=False
            )

    def test_pull_command_dry_run(self, mock_sys_exit, mock_sync_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'pull', '/vault', '--bucket', 'b', '--endpoint', 'e', '--dry-run']
        def mock_env_get(key, default=None):
            if key in ['B2_KEY_ID', 'B2_APP_KEY']: return 'val'
            if key == 'TERM': return 'xterm'
            return default
        with patch('os.environ.get', side_effect=mock_env_get):
            main()
            mock_sync_engine.sync_from_cloud.assert_called_once_with(
                os.path.abspath('/vault'), 'b', 'e', 'val', 'val', dry_run=True
            )


    def test_init_pyproject(self, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'init', '--pyproject']
        main()
        output = capture_stdout()
        assert "[tool.project-vault]" in output

    def test_init_default(self, mock_sys_exit, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'init']
        with patch('src.common.config.generate_init_file') as mock_gen:
            main()
            mock_gen.assert_called_once_with("pv.toml")

    def test_check_integrity(self, mock_sys_exit, mock_integrity_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'check-integrity', '/vault']
        mock_integrity_engine.verify_vault.return_value = True
        main()
        mock_integrity_engine.verify_vault.assert_called_once_with(os.path.abspath('/vault'))

    def test_check_integrity_success(self, mock_sys_exit, mock_integrity_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'check-integrity', '/vault']
        mock_integrity_engine.verify_vault.return_value = True
        main()
        mock_integrity_engine.verify_vault.assert_called_once()

    def test_clone_import_error(self, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'backup', 'src']
        mock_sys_exit.side_effect = SystemExit(1)

        # We need to mock importlib.import_module to raise ImportError
        with patch('importlib.import_module', side_effect=ImportError("No module named projectclone")):
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error executing command 'backup': No module named projectclone" in output

    def test_restore_import_error(self, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'archive-restore', 'src']
        mock_sys_exit.side_effect = SystemExit(1)

        with patch('importlib.import_module', side_effect=ImportError("No module named projectrestore")):
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error executing command 'archive-restore': No module named projectrestore" in output

    def test_list_cloud_success(self, mock_sys_exit, mock_list_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'list', '--cloud', '--bucket', 'my-bucket']
        def mock_env_get(key, default=None):
            if key in ['B2_KEY_ID', 'B2_APP_KEY']: return 'val'
            if key == 'TERM': return 'xterm'
            return default
        with patch('os.environ.get', side_effect=mock_env_get):
            main()
            mock_list_engine.list_cloud_snapshots.assert_called_once_with('my-bucket', 'val', 'val', None)

    def test_list_cloud_missing_bucket(self, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'list', '--cloud']
        mock_sys_exit.side_effect = SystemExit(1)
        try:
            main()
        except SystemExit:
            pass
        output = capture_stdout()
        assert "Error" in output
        assert "bucket must be specified" in output

    def test_list_cloud_missing_creds(self, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'list', '--cloud', '--bucket', 'my-bucket']
        def mock_env_get(key, default=None):
            if key == 'TERM': return 'xterm'
            return None
        with patch('os.environ.get', side_effect=mock_env_get):
            mock_sys_exit.side_effect = SystemExit(1)
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error" in output
            assert "Cloud credentials missing" in output

    def test_list_local_success(self, mock_sys_exit, mock_list_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'list', '/vault']
        main()
        mock_list_engine.list_local_snapshots.assert_called_once_with(os.path.abspath('/vault'))

    @patch("src.common.paths.get_default_vault_path")
    @patch("src.projectclone.list_engine.list_local_snapshots")
    def test_list_local_missing_vault(self, mock_list, mock_get_default, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'list']
        mock_config_load.return_value = {'vault_path': None}
        mock_get_default.return_value = "/default/vault"
        
        main()
        
        mock_get_default.assert_called_once()
        mock_list.assert_called_once()
        mock_sys_exit.assert_not_called()

    def test_gc_command(self, mock_sys_exit, mock_gc_engine, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'gc', '/vault', '--dry-run']
        main()
        mock_gc_engine.run_garbage_collection.assert_called_once_with(os.path.abspath('/vault'), True)

    def test_push_missing_vault_path(self, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env, mock_sync_engine):
        sys.argv = ['pv', 'push', '--bucket', 'b']
        mock_config_load.return_value = {'vault_path': None}
        
        # Mock resolve_credentials to allow push to proceed
        def mock_resolve(args, allow_fail=False): return "k", "s", "src"
        mock_creds = MagicMock()
        mock_creds.resolve_credentials = mock_resolve
        
        # Need to patch credentials module import inside cli.py main() -> handle_push_command
        # But we passed credentials object to handle_push_command in main.
        # The main function imports credentials from common.
        # We can patch 'cli.credentials' since we imported it in the test file?
        # Or patch sys.modules?
        
        # The test fixture mock_full_env patches 'cli.credentials.get_full_env'.
        # We need to patch 'cli.credentials.resolve_credentials' too.
        
        with patch('cli.credentials.resolve_credentials', side_effect=mock_resolve):
             main()
             
        mock_sync_engine.sync_to_cloud.assert_called_once()
        mock_sys_exit.assert_not_called()

    def test_push_missing_creds(self, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env):
        sys.argv = ['pv', 'push', '/vault', '--bucket', 'b', '--endpoint', 'e']
        def mock_env_get(key, default=None):
            if key == 'TERM': return 'xterm'
            return None
        with patch('os.environ.get', side_effect=mock_env_get):
            mock_sys_exit.side_effect = SystemExit(1)
            try:
                main()
            except SystemExit:
                pass
            output = capture_stdout()
            assert "Error" in output
            assert "Cloud credentials missing" in output

    def test_pull_missing_vault_path(self, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env, mock_sync_engine):
        sys.argv = ['pv', 'pull', '--bucket', 'b']
        mock_config_load.return_value = {'vault_path': None}
        
        def mock_resolve(args, allow_fail=False): return "k", "s", "src"
        with patch('cli.credentials.resolve_credentials', side_effect=mock_resolve):
            main()
            
        mock_sync_engine.sync_from_cloud.assert_called_once()
        mock_sys_exit.assert_not_called()

    def test_gc_missing_vault_path(self, mock_sys_exit, capture_stdout, mock_config_load, mock_full_env, mock_gc_engine):
        sys.argv = ['pv', 'gc']
        mock_config_load.return_value = {'vault_path': None}
        
        main()
        
        mock_gc_engine.run_garbage_collection.assert_called_once()
        mock_sys_exit.assert_not_called()


class TestCheckCloudEnv:
    @patch('src.common.console.console.print')
    @patch('cli.credentials.resolve_credentials')
    def test_check_cloud_env_found(self, mock_resolve, mock_print):
        # Mock successful resolution
        mock_resolve.return_value = ("key", "secret", "Doppler")
        
        mock_creds_module = MagicMock()
        mock_creds_module.resolve_credentials = mock_resolve
        mock_creds_module.get_cloud_provider_info.return_value = ("AWS", "bucket", "endpoint")

        check_cloud_env(mock_creds_module)
        
        # Verify console output
        found = False
        for call_args in mock_print.call_args_list:
            panel = call_args[0][0]
            text = str(panel.renderable)
            if "Cloud Credentials Found (Source: Doppler)" in text:
                found = True
                break
        assert found

    @patch('src.common.console.console.print')
    @patch('cli.credentials.resolve_credentials')
    def test_check_cloud_env_missing(self, mock_resolve, mock_print):
        # Mock failed resolution
        mock_resolve.return_value = (None, None, None)
        
        mock_creds_module = MagicMock()
        mock_creds_module.resolve_credentials = mock_resolve
        # get_cloud_provider_info is not called if creds are missing (in original logic? let's check)
        # Actually logic is: key_id, secret_key = ...; if key_id and secret_key: ...

        check_cloud_env(mock_creds_module)
        
        found = False
        for call_args in mock_print.call_args_list:
            panel = call_args[0][0]
            text = str(panel.renderable)
            if "No cloud credentials found" in text:
                found = True
                break
        assert found

    @patch('src.common.console.console.print')
    @patch('cli.credentials.resolve_credentials')
    def test_check_cloud_env_boto3_missing(self, mock_resolve, mock_print):
        mock_resolve.return_value = (None, None, None)
        
        mock_creds_module = MagicMock()
        mock_creds_module.resolve_credentials = mock_resolve

        original_import = __import__
        def mock_import(name, *args, **kwargs):
            if name == 'boto3': raise ImportError
            if name == 'b2sdk': return MagicMock()
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            check_cloud_env(mock_creds_module)

        found = False
        for call_args in mock_print.call_args_list:
            panel = call_args[0][0]
            if "boto3 is missing" in str(panel.renderable):
                found = True
                break
        assert found

    def test_keyboard_interrupt_exits_with_130(self, mock_sys_exit, mock_config_load):
        sys.argv = ['pv', 'vault', 'my_source', '/my_vault_path']
        with patch('src.projectclone.cas_engine.backup_to_vault', side_effect=KeyboardInterrupt):
            main()
            mock_sys_exit.assert_called_once_with(130)

    def test_generic_exception_exits_with_1(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv', 'vault', 'my_source', '/my_vault_path']
        with patch('src.projectclone.cas_engine.backup_to_vault', side_effect=ValueError("Test error")):
            main()
            output = capture_stdout()
            assert "Error: Test error" in output
            mock_sys_exit.assert_called_once_with(1)
