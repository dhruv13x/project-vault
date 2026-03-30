import gzip
import json
import sys
from pathlib import Path
from unittest.mock import patch

from src.common import cas
from src.projectclone.cli import main


def test_archive_include_db_restores_original_dump_before_bundling(tmp_path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.txt").write_text("content")

    dest = tmp_path / "dest"
    dest.mkdir()

    original_dump = tmp_path / "db_dump.sql.gz"
    with gzip.open(original_dump, "wb") as fh:
        fh.write(b"select 1;\n")
    original_bytes = original_dump.read_bytes()

    class FakeDatabaseEngine:
        def __init__(self, driver_name, config):
            self.driver_name = driver_name
            self.config = config

        def backup(self, vault_path, project_name):
            vault_root = Path(vault_path)
            objects_dir = vault_root / "objects"
            snapshot_dir = vault_root / "snapshots" / project_name
            snapshot_dir.mkdir(parents=True, exist_ok=True)

            file_hash = cas.store_object(str(original_dump), str(objects_dir))
            manifest_path = snapshot_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "files": {
                            "db_dump_20260330.sql.gz": {
                                "hash": file_hash,
                            }
                        }
                    }
                )
            )
            return str(manifest_path)

    captured = {}

    def fake_create_archive(*args, **kwargs):
        extra_files = kwargs["extra_files"]
        bundled = extra_files[".pv/database_dump.sql.gz"]
        captured["bundled_path"] = bundled
        captured["bundled_bytes"] = bundled.read_bytes()
        archive_path = args[1]
        archive_path.touch()
        return archive_path

    monkeypatch.setattr(sys, "argv", ["script.py", "note", "--archive", "--include-db", "--dest", str(dest), "--yes"])
    monkeypatch.setattr(Path, "cwd", lambda: src)

    with patch("src.projectclone.cli.walk_stats", return_value=(1, 10)), \
         patch("src.projectclone.cli.print_logo"), \
         patch("src.projectclone.cli.create_archive", side_effect=fake_create_archive), \
         patch("src.projectclone.cli.make_unique_path", side_effect=lambda p: p), \
         patch("src.projectclone.cli.atomic_move"), \
         patch("src.projectvault.engines.db_engine.DatabaseEngine", FakeDatabaseEngine), \
         patch("src.common.config.load_project_config", return_value={"database": {"driver": "postgres"}}):
        main()

    assert captured["bundled_path"].name == "database_dump.sql.gz"
    assert captured["bundled_bytes"] == original_bytes
    assert cas.is_zstd_compressed(str(captured["bundled_path"])) is False
