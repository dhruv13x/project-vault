import os
from typing import List, Dict
from .base import BaseDatabaseDriver

class PostgresDriver(BaseDatabaseDriver):
    """
    PostgreSQL driver implementation using pg_dump and pg_restore/psql.
    """

    def _get_env(self, config: Dict) -> Dict[str, str]:
        env = os.environ.copy()
        if config.get("password"):
            env["PGPASSWORD"] = config["password"]
        return env

    def _connection_args(self, config: Dict) -> List[str]:
        args: List[str] = []
        if config.get("host"):
            args.extend(["-h", config["host"]])
        if config.get("port"):
            args.extend(["-p", str(config["port"])])
        if config.get("user"):
            args.extend(["-U", config["user"]])
        return args

    def _maintenance_db(self, config: Dict) -> str:
        return config.get("maintenance_db") or "postgres"

    def _target_db(self, config: Dict, dbname: str | None = None) -> str:
        target = dbname or config.get("dbname")
        if not target:
            raise ValueError("Postgres database name is required.")
        return target

    def get_backup_command(self, config: Dict, dbname: str | None = None) -> List[str]:
        # pg_dump -h host -p port -U user -F c --no-owner --no-acl dbname
        # Using custom format (-F c) is good for pg_restore, but if we want
        # pure streaming compression we might use plain text or directory format?
        # The prompt says: Flow: Native Dump Utility -> Compression (Zstd/Gzip) -> Vault Storage.
        # Usually -F c is already compressed.
        # But if we want to use our own compression/CAS, maybe plain SQL (-F p) is better?
        # Or -F t (tar).
        # However, pg_dump's custom format is very robust.
        # But "Logical over Physical: Do NOT back up raw data directories."
        # "Streaming Pipes: ... Flow: Native Dump Utility -> Compression (Zstd/Gzip) -> Vault Storage."

        # If we use -F c (Custom), it is compressed by default (gzip).
        # We might want to disable internal compression if we use Zstd externally,
        # or just let pg_dump handle it.
        # But for better integration with CAS (deduplication), uncompressed output *might* be better
        # if the CAS engine does chunking. But standard CAS usually deduplicates whole files.
        # Let's stick to standard plain text dump or tar for maximum portability
        # and let the pipe handle compression if needed.
        # BUT: pg_restore requires custom or tar format for some features (like reordering).
        # Let's use -F p (plain text) so it's just SQL commands, easiest for streaming and compression.
        # Wait, the prompt says "Flow: Native Dump Utility -> Compression (Zstd/Gzip) -> Vault Storage".
        # This implies we should output uncompressed data from the DB tool.

        cmd = ["pg_dump", *self._connection_args(config)]

        # Ensure we output to stdout
        # -F p is default (plain text SQL script)
        # We want to avoid writing to disk.

        # Options for consistency
        cmd.append("--clean") # Include commands to clean (drop) database objects before creating them.
        cmd.append("--if-exists")
        cmd.append("--no-owner") # Skip restoration of object ownership
        cmd.append("--no-acl")   # Skip restoration of access privileges (grant/revoke)

        cmd.append(self._target_db(config, dbname))
        return cmd

    def get_restore_command(self, config: Dict, dbname: str | None = None) -> List[str]:
        # For plain text format, we use psql
        cmd = ["psql", *self._connection_args(config)]

        cmd.append("-d")
        cmd.append(self._target_db(config, dbname))

        # We might need -v ON_ERROR_STOP=1
        cmd.extend(["-v", "ON_ERROR_STOP=1"])

        return cmd

    def get_verification_command(self, config: Dict, dbname: str | None = None) -> List[str]:
        # Check if we can connect
        cmd = ["psql", *self._connection_args(config)]

        # Just run a simple query
        cmd.extend(["-d", self._target_db(config, dbname), "-c", "SELECT 1"])
        return cmd

    def get_drop_command(self, config: Dict, dbname: str | None = None) -> List[str]:
        # For Postgres, dropping the DB requires connecting to another DB (like postgres)
        # This might be dangerous or restricted.
        # A safer "clean" is often handled by --clean in pg_dump, but that only works if restore runs.
        # If we really want to DROP DATABASE, we need to connect to 'postgres' db.

        target_db = self._target_db(config, dbname)
        cmd = ["psql", *self._connection_args(config)]
        cmd.extend(["-d", self._maintenance_db(config), "-c", f"DROP DATABASE IF EXISTS \"{target_db}\""])
        # And create it again?
        # The prompt says: "Implement a --force flag to drop/recreate the schema for a clean state."
        # Schema usually means the tables inside the DB, or the DB itself.
        # "Clean state" usually implies empty DB.

        return cmd

    def get_create_command(self, config: Dict, dbname: str | None = None) -> List[str]:
        target_db = self._target_db(config, dbname)
        cmd = ["psql", *self._connection_args(config)]
        cmd.extend(["-d", self._maintenance_db(config), "-c", f"CREATE DATABASE \"{target_db}\""])
        return cmd

    def get_database_list_command(self, config: Dict) -> List[str]:
        cmd = ["psql", *self._connection_args(config)]
        cmd.extend([
            "-d",
            self._maintenance_db(config),
            "-At",
            "-c",
            "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres' ORDER BY datname",
        ])
        return cmd
