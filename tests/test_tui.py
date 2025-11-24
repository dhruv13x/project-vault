import unittest
from unittest.mock import MagicMock, patch
import os

# Mock textual to avoid needing a display/terminal
# We only need the class definition to exist for inheritance
# But importing src.tui imports textual.app.App
# So we need textual installed, which it is.

from src.tui import ProjectVaultApp
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

class TestTuiLogic(unittest.TestCase):
    def setUp(self):
        self.vault_path = "/tmp/vault"
        self.project_name = "test_project"
        self.app = ProjectVaultApp(self.vault_path, self.project_name)

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

    @patch("pv_core.manifest.load_manifest")
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
    @patch("pv_core.cas.read_object_text")
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

if __name__ == "__main__":
    unittest.main()
