import json
import sys
from pathlib import Path
from unittest.mock import patch

from src.projectrestore import cli


def test_archive_restore_include_db_restores_multiple_bundled_dumps(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    tar_path = backup_dir / "backup.tar.gz"
    tar_path.touch()

    extract_dir = tmp_path / "restore"

    def fake_extract(*args, **kwargs):
        pv_dir = extract_dir / ".pv"
        db_dir = pv_dir / "databases"
        db_dir.mkdir(parents=True, exist_ok=True)
        (db_dir / "accounts_db.sql.gz").write_bytes(b"accounts")
        (db_dir / "botdb.sql.gz").write_bytes(b"bot")
        (pv_dir / "databases.json").write_text(
            json.dumps({"dbnames": ["accounts_db", "botdb"]}),
            encoding="utf-8",
        )

    restored = {}

    class FakeDatabaseEngine:
        def __init__(self, driver_name, config):
            self.driver_name = driver_name
            self.config = config

        def restore(self, manifest_path, vault_path, force=False, credentials_module=None):
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            restored["dbnames"] = manifest["database_config"]["dbnames"]
            restored["files"] = sorted(manifest["files"].keys())
            restored["force"] = force

    monkeypatch.setattr(
        sys,
        "argv",
        ["script.py", "--backup-dir", str(backup_dir), "--extract-dir", str(extract_dir), "--file", "backup.tar.gz", "--include-db", "--force"],
    )

    with patch("src.projectrestore.cli.print_logo"), \
         patch("src.projectrestore.cli.find_latest_backup", return_value=tar_path), \
         patch("src.projectrestore.cli.safe_extract_atomic", side_effect=fake_extract), \
         patch("src.projectrestore.cli.count_files", return_value=3), \
         patch("src.projectrestore.cli.create_pid_lock"), \
         patch("src.projectrestore.cli.release_pid_lock"), \
         patch("src.projectrestore.cli.setup_logging"), \
         patch("src.projectrestore.cli.DatabaseEngine", create=True), \
         patch("src.projectvault.engines.db_engine.DatabaseEngine", FakeDatabaseEngine), \
         patch("src.common.config.load_project_config", return_value={"database": {"driver": "postgres"}}):
        rc = cli.main()

    assert rc == 0
    assert restored["dbnames"] == ["accounts_db", "botdb"]
    assert restored["files"] == ["accounts_db.sql.gz", "botdb.sql.gz"]
    assert restored["force"] is True
