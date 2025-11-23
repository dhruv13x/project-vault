import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Dynamically add src to sys.path for testing purposes
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Import the cli module after adjusting sys.path
from cli import main, b2_check_main

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
    def test_no_command_prints_help(self, mock_sys_exit, capture_stdout, mock_config_load):
        sys.argv = ['pv']
        main()
        output = capture_stdout()
        assert "Project Vault: The Unified Project Lifecycle Manager" in output
        assert "Available Commands" in output
        mock_sys_exit.assert_called_once_with(0)

    def test_clone_command_dispatches(self, mock_sys_exit, mock_projectclone_cli, mock_config_load):
        sys.argv = ['pv', 'clone', 'source_dir', '--dest', 'dest_dir']
        main()
        mock_projectclone_cli.main.assert_called_once()
        # Ensure sys.argv was correctly transformed
        assert sys.argv == ['projectclone', 'source_dir', '--dest', 'dest_dir']
        # The hijack calls sys.exit(0), but the sub-cli might also call it.
        # We only care that the dispatch happened correctly.

    def test_clone_command_dispatches_with_vault_path_from_config(self, mock_sys_exit, mock_projectclone_cli):
        with patch('cli.config.load_project_config', return_value={'vault_path': '/config/vault'}) as mock_load:
            sys.argv = ['pv', 'clone', 'source_dir']
            main()
            mock_projectclone_cli.main.assert_called_once()
            assert sys.argv == ['projectclone', 'source_dir', '--dest', '/config/vault']
            mock_sys_exit.assert_called_once_with(0)

    def test_restore_command_dispatches(self, mock_sys_exit, mock_projectrestore_cli, mock_config_load):
        sys.argv = ['pv', 'restore', 'some_arg']
        main()
        mock_projectrestore_cli.main.assert_called_once()
        assert sys.argv == ['projectrestore', 'some_arg']
        # The hijack calls sys.exit(0), but the sub-cli might also call it.
        # We only care that the dispatch happened correctly.

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
        sys.argv = ['pv', 'vault', 'my_source'] # vault_path is not provided
        main()
        output = capture_stdout()
        assert "Error: vault_path must be specified in CLI or pv.toml" in output
        mock_sys_exit.assert_called_once_with(1)
        mock_cas_engine.backup_to_vault.assert_not_called()

    def test_vault_command_missing_vault_path_from_config_exits(self, mock_sys_exit, capture_stdout, mock_cas_engine):
        with patch('cli.config.load_project_config', return_value={'vault_path': None}) as mock_load:
            sys.argv = ['pv', 'vault', 'my_source'] # vault_path is not provided
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

    def test_b2_check_command_calls_b2_check_main(self, mock_sys_exit, mock_config_load):
        sys.argv = ['pv', 'b2-check']
        with patch('cli.b2_check_main') as mock_b2_check:
            main()
            mock_b2_check.assert_called_once()
            mock_sys_exit.assert_not_called() # b2_check_main doesn't exit directly
            
class TestB2CheckMain:
    @patch('cli.Console')
    @patch('os.environ.get')
    def test_b2_check_main_all_present(self, mock_environ_get, MockConsole):
        mock_environ_get.side_effect = lambda x: {"B2_KEY_ID": "id", "B2_APP_KEY": "key"}.get(x)
        mock_console_instance = MockConsole.return_value
        with patch('importlib.import_module', return_value=MagicMock(boto3=True)):
            b2_check_main()
            mock_console_instance.print.assert_any_call("[green]✅ Found B2_KEY_ID[/green]")
            mock_console_instance.print.assert_any_call("[green]✅ Found B2_APP_KEY[/green]")
            mock_console_instance.print.assert_any_call("[green]✅ boto3 is installed[/green]")

    @patch('cli.Console')
    @patch('os.environ.get')
    def test_b2_check_main_missing_key_id(self, mock_environ_get, MockConsole):
        mock_environ_get.side_effect = lambda x: {"B2_APP_KEY": "key"}.get(x)
        mock_console_instance = MockConsole.return_value
        with patch('importlib.import_module', return_value=MagicMock(boto3=True)):
            b2_check_main()
            mock_console_instance.print.assert_any_call("[red]❌ Missing B2_KEY_ID[/red]")
            mock_console_instance.print.assert_any_call("   [yellow]Run:[/yellow] export B2_KEY_ID='your_key_id'")
            mock_console_instance.print.assert_any_call("[green]✅ Found B2_APP_KEY[/green]")
            mock_console_instance.print.assert_any_call("[green]✅ boto3 is installed[/green]")

    @patch('cli.Console')
    @patch('os.environ.get')
    def test_b2_check_main_missing_app_key(self, mock_environ_get, MockConsole):
        mock_environ_get.side_effect = lambda x: {"B2_KEY_ID": "id"}.get(x)
        mock_console_instance = MockConsole.return_value
        with patch('importlib.import_module', return_value=MagicMock(boto3=True)):
            b2_check_main()
            mock_console_instance.print.assert_any_call("[green]✅ Found B2_KEY_ID[/green]")
            mock_console_instance.print.assert_any_call("[red]❌ Missing B2_APP_KEY[/red]")
            mock_console_instance.print.assert_any_call("   [yellow]Run:[/yellow] export B2_APP_KEY='your_app_key'")
            mock_console_instance.print.assert_any_call("[green]✅ boto3 is installed[/green]")

    @patch('cli.Console')
    @patch('os.environ.get')
    def test_b2_check_main_boto3_missing(self, mock_environ_get, MockConsole):
        mock_environ_get.side_effect = lambda x: {"B2_KEY_ID": "id", "B2_APP_KEY": "key"}.get(x)
        mock_console_instance = MockConsole.return_value

        # More robust way to mock a missing module
        original_import = __import__
        def import_mock(name, *args, **kwargs):
            if name == 'boto3':
                raise ImportError
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=import_mock):
            b2_check_main()

        mock_console_instance.print.assert_any_call("[red]❌ boto3 is missing[/red]")
        mock_console_instance.print.assert_any_call("   [yellow]Run:[/yellow] pip install boto3")

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