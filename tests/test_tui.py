# tests/test_tui.py

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import subprocess
import tempfile
from textual.widgets import Tree, Header, Footer, Static, Label
from textual.containers import Container, VerticalScroll
from textual.widgets.tree import TreeNode

# Mock textual to avoid needing a display/terminal
# We only need the class definition to exist for inheritance
# But importing src.tui imports textual.app.App
# So we need textual installed, which it is.

from src.tui import ProjectVaultApp

class TestTuiLogic(unittest.TestCase):
    def setUp(self):
        self.vault_path = "/tmp/vault"
        self.project_name = "test_project"
        self.app = ProjectVaultApp(self.vault_path, self.project_name)

    def test_compose(self):
        """Test the compose method yields the expected widgets."""
        widgets = list(self.app.compose())

        self.assertTrue(any(isinstance(w, Header) for w in widgets))
        self.assertTrue(any(isinstance(w, Container) for w in widgets))
        self.assertTrue(any(isinstance(w, VerticalScroll) for w in widgets))
        self.assertTrue(any(isinstance(w, Footer) for w in widgets))

    @patch("os.path.exists")
    @patch("os.listdir")
    def test_on_mount_loads_snapshots(self, mock_listdir, mock_exists):
        mock_exists.return_value = True
        mock_listdir.return_value = ["20230101_120000.json", "20230102_120000.json"]
        
        # Mock the Tree widget query
        mock_tree = MagicMock(spec=Tree)
        mock_root = MagicMock(spec=TreeNode)
        mock_tree.root = mock_root
        
        self.app.query_one = MagicMock(return_value=mock_tree)
        
        # Run on_mount
        self.app.on_mount()
        
        # Should add 2 snapshots
        self.assertEqual(mock_root.add.call_count, 2)
        
        # Check args of first add (reverse sorted -> 20230102 first)
        args, kwargs = mock_root.add.call_args_list[0]
        self.assertEqual(args[0], "20230102_120000")
        self.assertEqual(kwargs["data"]["path"], "/tmp/vault/snapshots/test_project/20230102_120000.json")

    @patch("src.common.manifest.load_manifest")
    def test_load_snapshot_into_node(self, mock_load_manifest):
        # Mock data
        mock_load_manifest.return_value = {
            "files": {
                "README.md": "hash1",
                "src/main.py": "hash2",
                "src/utils/helper.py": "hash3"
            }
        }
        
        parent_node = MagicMock(spec=TreeNode)
        # We need to mock .add() returning a mock node for directories
        dir_node_mock = MagicMock(spec=TreeNode)
        parent_node.add.return_value = dir_node_mock
        dir_node_mock.add.return_value = MagicMock(spec=TreeNode) # deeper nesting
        
        self.app.load_snapshot_into_node(parent_node, "dummy_path")
        
        # Verify tree structure
        # README.md should be a leaf on parent
        # src should be a dir on parent
        
        # Check calls to parent.add_leaf (files)
        # README.md
        parent_node.add_leaf.assert_any_call(
            "📄 README.md", 
            data={"type": "file", "hash": "hash1", "name": "README.md", "rel_path": "README.md"}
        )
        
        # Check calls to parent.add (directories)
        # src/
        parent_node.add.assert_any_call(
            "📁 src/", 
            data={"type": "directory"}, 
            expand=False
        )

    @patch("os.path.exists")
    @patch("src.common.cas.read_object_text")
    def test_file_selection_reads_content(self, mock_read_text, mock_exists):
        mock_exists.return_value = True
        mock_read_text.return_value = ["Hello World"]
        
        # Mock UI elements
        mock_label = MagicMock()
        mock_viewer = MagicMock()
        
        def query_side_effect(selector, type=None):
            if selector == "#file-path": return mock_label
            if selector == "#file-viewer": return mock_viewer
            return MagicMock()
            
        self.app.query_one = MagicMock(side_effect=query_side_effect)
        
        # Create event mock
        mock_node = MagicMock()
        mock_node.data = {"type": "file", "hash": "abc", "rel_path": "test.txt"}
        mock_event = MagicMock()
        mock_event.node = mock_node
        
        self.app.on_tree_node_selected(mock_event)
        
        mock_read_text.assert_called_with("/tmp/vault/objects/abc")
        mock_viewer.update.assert_called_with("Hello World")

    @patch("src.common.cas.restore_object_to_file")
    def test_action_restore_file(self, mock_restore):
        """
        Test that the restore action calls the correct CAS function.
        """
        # Set up a selected file node
        self.app.current_file_node = MagicMock()
        self.app.current_file_node.data = {
            "type": "file",
            "hash": "hash123",
            "rel_path": "path/to/file.txt"
        }

        # Mock notify
        self.app.notify = MagicMock()

        # Execute the action
        self.app.action_restore_file()

        # Verify
        expected_target_path = os.path.join(os.getcwd(), "path/to/file.txt")
        mock_restore.assert_called_once_with(
            "/tmp/vault/objects/hash123",
            expected_target_path
        )
        self.app.notify.assert_any_call("Restored path/to/file.txt", severity="information")

    def test_build_tree_recursive(self):
        """
        Test the recursive tree building logic.
        """
        tree_struct = {
            "file1.txt": "hash1",
            "dir1": {
                "file2.txt": "hash2"
            }
        }

        parent_node = MagicMock(spec=TreeNode)
        dir_node_mock = MagicMock(spec=TreeNode)
        parent_node.add.return_value = dir_node_mock

        self.app._build_tree_recursive(parent_node, tree_struct)

        parent_node.add_leaf.assert_called_with(
            "📄 file1.txt",
            data={"type": "file", "hash": "hash1", "name": "file1.txt", "rel_path": "file1.txt"}
        )
        parent_node.add.assert_called_with("📁 dir1/", data={"type": "directory"}, expand=False)
        dir_node_mock.add_leaf.assert_called_with(
            "📄 file2.txt",
            data={"type": "file", "hash": "hash2", "name": "file2.txt", "rel_path": "dir1/file2.txt"}
        )

    @patch("src.tui.ProjectVaultApp.load_snapshot_into_node")
    def test_on_tree_node_expanded(self, mock_load_snapshot):
        """
        Test that expanding a snapshot node lazy-loads its content.
        """
        # Create a mock event with a node representing a snapshot
        mock_node = MagicMock(spec=TreeNode)
        mock_node.data = {"type": "snapshot", "path": "/path/to/snapshot.json"}
        mock_node.children = []  # No children yet

        mock_event = MagicMock()
        mock_event.node = mock_node

        # Trigger the event
        self.app.on_tree_node_expanded(mock_event)

        # Assert that the loading function was called
        mock_load_snapshot.assert_called_once_with(mock_node, "/path/to/snapshot.json")

    @patch("src.tui.ProjectVaultApp.load_snapshot_into_node")
    def test_on_tree_node_expanded_already_loaded(self, mock_load_snapshot):
        """Test expansion when children already exist."""
        mock_node = MagicMock(spec=TreeNode)
        mock_node.data = {"type": "snapshot", "path": "/path/to/snapshot.json"}
        mock_node.children = [MagicMock()]  # Has children

        mock_event = MagicMock()
        mock_event.node = mock_node

        self.app.on_tree_node_expanded(mock_event)

        # Should NOT load again
        mock_load_snapshot.assert_not_called()

    @patch("src.tui.ProjectVaultApp.load_snapshot_into_node")
    def test_on_tree_node_expanded_not_snapshot(self, mock_load_snapshot):
        """Test expansion of non-snapshot node."""
        mock_node = MagicMock(spec=TreeNode)
        mock_node.data = {"type": "directory"}
        mock_node.children = []

        mock_event = MagicMock()
        mock_event.node = mock_node

        self.app.on_tree_node_expanded(mock_event)

        # Should NOT load again
        mock_load_snapshot.assert_not_called()

    def test_on_tree_node_expanded_no_data(self):
        """Test expansion of node without data."""
        mock_node = MagicMock(spec=TreeNode)
        mock_node.data = None
        mock_event = MagicMock()
        mock_event.node = mock_node

        self.app.on_tree_node_expanded(mock_event)
        # Should just return without error

    @patch("os.path.exists", return_value=False)
    def test_on_mount_no_snapshots_dir(self, mock_exists):
        """
        Test that on_mount handles the case where the snapshots directory does not exist.
        """
        mock_tree = MagicMock(spec=Tree)
        mock_root = MagicMock(spec=TreeNode)
        mock_tree.root = mock_root

        self.app.query_one = MagicMock(return_value=mock_tree)

        self.app.on_mount()

        mock_root.add.assert_called_once_with("No snapshots found.", allow_expand=False)

    @patch("os.path.exists", return_value=False)
    def test_file_selection_missing_object(self, mock_exists):
        """
        Test that file selection handles the case where the object file is missing.
        """
        mock_viewer = MagicMock()
        self.app.query_one = MagicMock(return_value=mock_viewer)

        mock_node = MagicMock()
        mock_node.data = {"type": "file", "hash": "missing", "rel_path": "test.txt"}
        mock_event = MagicMock()
        mock_event.node = mock_node

        self.app.on_tree_node_selected(mock_event)

        mock_viewer.update.assert_called_with("[red]Error: Object missing in vault.[/red]")

    @patch("src.common.manifest.load_manifest", side_effect=Exception("Test error"))
    def test_load_snapshot_into_node_error(self, mock_load_manifest):
        """
        Test that load_snapshot_into_node handles exceptions gracefully.
        """
        parent_node = MagicMock(spec=TreeNode)
        self.app.load_snapshot_into_node(parent_node, "dummy_path")
        parent_node.add.assert_called_with("Error loading manifest: Test error")

    def test_action_restore_file_no_selection(self):
        """
        Test that the restore action handles the case where no file is selected.
        """
        self.app.current_file_node = None
        self.app.notify = MagicMock()

        self.app.action_restore_file()

        self.app.notify.assert_called_with("No file selected.", severity="warning")

    def test_action_restore_file_not_a_file(self):
        """Test restore action when selection is not a file."""
        self.app.current_file_node = MagicMock()
        self.app.current_file_node.data = {"type": "directory"}
        self.app.action_restore_file()
        # Should just return

    def test_on_tree_node_selected_not_file(self):
        """Test selection of non-file node."""
        mock_node = MagicMock()
        mock_node.data = {"type": "directory"}
        mock_event = MagicMock()
        mock_event.node = mock_node
        self.app.on_tree_node_selected(mock_event)
        # Should return early

    @patch("src.common.cas.read_object_text", side_effect=Exception("Read fail"))
    @patch("os.path.exists", return_value=True)
    def test_file_selection_read_exception(self, mock_exists, mock_read):
        """Test exception during file read."""
        mock_viewer = MagicMock()
        self.app.query_one = MagicMock(return_value=mock_viewer)

        mock_node = MagicMock()
        mock_node.data = {"type": "file", "hash": "abc", "rel_path": "test.txt"}
        mock_event = MagicMock()
        mock_event.node = mock_node

        self.app.on_tree_node_selected(mock_event)

        mock_viewer.update.assert_called_with("[red]Error reading file:[/red] Read fail")

    @patch("src.common.cas.restore_object_to_file")
    @patch("os.path.exists", return_value=True)
    def test_action_restore_file_overwrite(self, mock_exists, mock_restore):
        """Test restore with overwrite warning."""
        self.app.current_file_node = MagicMock()
        self.app.current_file_node.data = {
            "type": "file",
            "hash": "h",
            "rel_path": "foo.txt"
        }
        self.app.notify = MagicMock()

        self.app.action_restore_file()

        self.app.notify.assert_any_call("Overwriting foo.txt...", severity="warning")
        mock_restore.assert_called_once()

    @patch("src.common.cas.restore_object_to_file", side_effect=Exception("Restore fail"))
    def test_action_restore_file_exception(self, mock_restore):
        """Test exception during restore."""
        self.app.current_file_node = MagicMock()
        self.app.current_file_node.data = {
            "type": "file",
            "hash": "h",
            "rel_path": "foo.txt"
        }
        self.app.notify = MagicMock()

        self.app.action_restore_file()

        self.app.notify.assert_called_with("Failed to restore: Restore fail", severity="error")

    def test_main_execution(self):
        """Test the __main__ block logic with strict timeout."""
        # Use subprocess to execute the file itself.
        # We need to set PYTHONPATH so it can find src
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()

        tui_path = os.path.join("src", "tui.py")
        with open(tui_path, "r") as f:
            content = f.read()

        # Inject mock
        content = "from unittest.mock import MagicMock\n" + content.replace("app.run()", "print('App ran')")

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Added timeout=5 to prevent infinite hang
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                env=env,
                timeout=5
            )
            self.assertIn("App ran", result.stdout)
        except subprocess.TimeoutExpired:
            self.fail("Test timed out - app.run() was likely not neutralized")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
