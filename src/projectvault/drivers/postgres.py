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

    def get_backup_command(self, config: Dict) -> List[str]:
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

        cmd = ["pg_dump"]
        if config.get("host"):
            cmd.extend(["-h", config["host"]])
        if config.get("port"):
            cmd.extend(["-p", str(config["port"])])
        if config.get("user"):
            cmd.extend(["-U", config["user"]])

        # Ensure we output to stdout
        # -F p is default (plain text SQL script)
        # We want to avoid writing to disk.

        # Options for consistency
        cmd.append("--clean") # Include commands to clean (drop) database objects before creating them.
        cmd.append("--if-exists")
        cmd.append("--no-owner") # Skip restoration of object ownership
        cmd.append("--no-acl")   # Skip restoration of access privileges (grant/revoke)

        cmd.append(config["dbname"])
        return cmd

    def get_restore_command(self, config: Dict) -> List[str]:
        # For plain text format, we use psql
        cmd = ["psql"]
        if config.get("host"):
            cmd.extend(["-h", config["host"]])
        if config.get("port"):
            cmd.extend(["-p", str(config["port"])])
        if config.get("user"):
            cmd.extend(["-U", config["user"]])

        cmd.append("-d")
        cmd.append(config["dbname"])

        # We might need -v ON_ERROR_STOP=1
        cmd.extend(["-v", "ON_ERROR_STOP=1"])

        return cmd

    def get_verification_command(self, config: Dict) -> List[str]:
        # Check if we can connect
        cmd = ["psql"]
        if config.get("host"):
            cmd.extend(["-h", config["host"]])
        if config.get("port"):
            cmd.extend(["-p", str(config["port"])])
        if config.get("user"):
            cmd.extend(["-U", config["user"]])

        # Just run a simple query
        cmd.extend(["-d", config["dbname"], "-c", "SELECT 1"])
        return cmd

    def get_drop_command(self, config: Dict) -> List[str]:
        # For Postgres, dropping the DB requires connecting to another DB (like postgres)
        # This might be dangerous or restricted.
        # A safer "clean" is often handled by --clean in pg_dump, but that only works if restore runs.
        # If we really want to DROP DATABASE, we need to connect to 'postgres' db.

        cmd = ["psql"]
        if config.get("host"):
            cmd.extend(["-h", config["host"]])
        if config.get("port"):
            cmd.extend(["-p", str(config["port"])])
        if config.get("user"):
            cmd.extend(["-U", config["user"]])

        cmd.extend(["-d", "postgres", "-c", f"DROP DATABASE IF EXISTS \"{config['dbname']}\""])
        # And create it again?
        # The prompt says: "Implement a --force flag to drop/recreate the schema for a clean state."
        # Schema usually means the tables inside the DB, or the DB itself.
        # "Clean state" usually implies empty DB.

        return cmd

    def get_create_command(self, config: Dict) -> List[str]:
        cmd = ["psql"]
        if config.get("host"):
            cmd.extend(["-h", config["host"]])
        if config.get("port"):
            cmd.extend(["-p", str(config["port"])])
        if config.get("user"):
            cmd.extend(["-U", config["user"]])

        cmd.extend(["-d", "postgres", "-c", f"CREATE DATABASE \"{config['dbname']}\""])
        return cmd
