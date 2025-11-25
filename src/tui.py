# src/tui.py

import os
import sys
from datetime import datetime

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static, Label
from textual.containers import Container, Horizontal, VerticalScroll
from textual.binding import Binding
from textual.widgets.tree import TreeNode

# Ensure we can import from src
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.common import manifest, cas

class ProjectVaultApp(App):
    """A Textual app for browsing Project Vault snapshots."""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 30%;
        height: 100%;
        dock: left;
        border-right: solid $accent;
        background: $surface;
    }

    #main-window {
        width: 70%;
        height: 100%;
        padding: 1 2;
    }

    .file-content {
        background: $panel;
        padding: 1;
        border: solid $secondary;
    }
    
    Label {
        margin-bottom: 1;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "restore_file", "Restore File"),
    ]

    def __init__(self, vault_path: str, project_name: str):
        super().__init__()
        self.vault_path = vault_path
        self.project_name = project_name
        self.current_manifest = None
        self.current_file_node = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Tree(f"Snapshots: {self.project_name}", id="snapshot-tree"),
            id="sidebar"
        )
        yield VerticalScroll(
            Label("Select a file to view content...", id="file-path"),
            Static(id="file-viewer", classes="file-content"),
            id="main-window"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load snapshots on startup."""
        tree = self.query_one("#snapshot-tree", Tree)
        root = tree.root
        root.expand()
        
        snapshots_dir = os.path.join(self.vault_path, "snapshots", self.project_name)
        if not os.path.exists(snapshots_dir):
            root.add("No snapshots found.", allow_expand=False)
            return

        # List JSON files, sorted new -> old
        files = sorted(
            [f for f in os.listdir(snapshots_dir) if f.endswith(".json")],
            reverse=True
        )

        for f in files:
            # Label: timestamp or just filename
            # We store the full path in data
            full_path = os.path.join(snapshots_dir, f)
            # Try to parse timestamp from filename or content? Filename is usually the timestamp.
            # Format: 20231125_120000.json -> 2023-11-25 12:00:00
            label = f.replace(".json", "")
            
            # Add snapshot node
            # data stores (type="snapshot", path=full_path)
            root.add(label, data={"type": "snapshot", "path": full_path}, expand=False)

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Lazy load manifest files when a snapshot node is expanded."""
        node = event.node
        if not node.data:
            return
            
        if node.data.get("type") == "snapshot" and not node.children:
            self.load_snapshot_into_node(node, node.data["path"])

    def load_snapshot_into_node(self, parent_node: TreeNode, manifest_path: str):
        """Parses manifest and builds file tree."""
        try:
            data = manifest.load_manifest(manifest_path)
            files = data.get("files", {})
            
            # Helper to build tree structure from flat paths
            # files keys are like "src/main.py", "README.md"
            
            # We need to turn flat paths into a tree structure.
            # Simple approach: just add all as children? No, directories are better.
            
            # Build a nested dict structure first
            tree_struct = {}
            for file_path, metadata in files.items():
                parts = file_path.split('/')
                current = tree_struct
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                # Leaf
                current[parts[-1]] = metadata

            self._build_tree_recursive(parent_node, tree_struct)
            
        except Exception as e:
            parent_node.add(f"Error loading manifest: {e}")

    def _build_tree_recursive(self, parent_node: TreeNode, current_struct: dict, current_path_prefix: str = ""):
        # Sort: directories first, then files
        items = sorted(current_struct.items(), key=lambda x: (not isinstance(x[1], dict), x[0]))
        
        for name, data in items:
            if isinstance(data, dict) and "hash" not in data:
                # It's a directory (nested dict)
                # Note: The check "hash" not in data covers V2. 
                # V1 was just string hash, but we wrapped it. 
                # Actually, my tree construction logic above puts dicts for dirs.
                # Snapshot V2 files are dicts WITH 'hash'.
                # So if it's a dict WITHOUT 'hash', it's our intermediate dir structure.
                
                dir_node = parent_node.add(f"📁 {name}/", data={"type": "directory"}, expand=False)
                new_prefix = os.path.join(current_path_prefix, name) if current_path_prefix else name
                self._build_tree_recursive(dir_node, data, new_prefix)
            else:
                # It's a file
                # V1: data is string hash. V2: data is dict with 'hash'.
                file_hash = data if isinstance(data, str) else data.get("hash")
                full_rel_path = os.path.join(current_path_prefix, name) if current_path_prefix else name
                
                parent_node.add_leaf(
                    f"📄 {name}", 
                    data={
                        "type": "file", 
                        "hash": file_hash, 
                        "name": name,
                        "rel_path": full_rel_path
                    }
                )

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Display file content when a file node is selected."""
        node = event.node
        if not node.data or node.data.get("type") != "file":
            return

        self.current_file_node = node
        file_hash = node.data.get("hash")
        rel_path = node.data.get("rel_path")
        
        # Update Label
        self.query_one("#file-path", Label).update(f"Viewing: {rel_path}")
        
        # Load Content
        viewer = self.query_one("#file-viewer", Static)
        
        object_path = os.path.join(self.vault_path, "objects", file_hash)
        if not os.path.exists(object_path):
            viewer.update("[red]Error: Object missing in vault.[/red]")
            return

        try:
            # Use our new Zstd-aware reader
            lines = cas.read_object_text(object_path)
            content = "".join(lines)
            viewer.update(content)
        except Exception as e:
            viewer.update(f"[red]Error reading file:[/red] {e}")

    def action_restore_file(self) -> None:
        """Restore the currently selected file."""
        if not self.current_file_node:
            self.notify("No file selected.", severity="warning")
            return
            
        data = self.current_file_node.data
        if data.get("type") != "file":
            return

        rel_path = data["rel_path"]
        file_hash = data["hash"]
        
        # Determine restore path (current working dir + rel_path)
        # We assume the user is running 'pv browse' from the project root
        cwd = os.getcwd()
        target_path = os.path.join(cwd, rel_path)
        
        object_path = os.path.join(self.vault_path, "objects", file_hash)
        
        try:
            # We assume the user is okay with this since they pressed 'r'
            # Ideally we'd pop a confirmation modal, but for this version we notify.
            
            if os.path.exists(target_path):
                 self.notify(f"Overwriting {rel_path}...", severity="warning")
            
            cas.restore_object_to_file(object_path, target_path)
            self.notify(f"Restored {rel_path}", severity="information")
            
        except Exception as e:
            self.notify(f"Failed to restore: {e}", severity="error")

if __name__ == "__main__":
    # Test run
    app = ProjectVaultApp(".", "test_project")
    app.run()
