import os
import sys
import subprocess
import time
import json
import hashlib
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any

from src.common.console import console
from src.projectvault.drivers.postgres import PostgresDriver
from src.projectclone import cas_engine

# Map driver names to classes
DRIVERS = {
    "postgres": PostgresDriver,
    "postgresql": PostgresDriver
}

class DatabaseEngine:
    def __init__(self, driver_name: str, config: Dict[str, Any]):
        driver_cls = DRIVERS.get(driver_name.lower())
        if not driver_cls:
            raise ValueError(f"Unsupported database driver: {driver_name}")
        self.driver = driver_cls()
        self.config = config
        # We delay env creation to allow dynamic secret resolution if needed
        self.env = self.driver._get_env(config)

    def _resolve_password(self, credentials_module=None):
        """
        Resolves database password from config or credentials module (Doppler/Env).
        Updates self.config and self.env.
        """
        # If password is in config, use it (insecure but supported)
        if self.config.get("password"):
            return

        # Attempt to resolve via credentials module if provided
        # We look for standard env vars like DB_PASSWORD, PG_PASSWORD, or specific PV_DB_PASSWORD
        if credentials_module:
            full_env = credentials_module.get_full_env()

            # Candidates for password
            candidates = ["PV_DB_PASSWORD", "DB_PASSWORD", "PGPASSWORD", "POSTGRES_PASSWORD"]
            for key in candidates:
                if full_env.get(key):
                    self.config["password"] = full_env[key]
                    # Update env
                    self.env = self.driver._get_env(self.config)
                    console.print(f"[dim]Resolved database password from {key}[/dim]")
                    return

    def backup(self, vault_path: str, project_name: str, cloud_sync: bool = False, credentials_module=None, bucket: str = None, endpoint: str = None) -> str:
        """
        Backs up the database to the vault.
        Returns the path to the manifest file.
        """
        self._resolve_password(credentials_module)

        console.print(f"[info]Starting database backup for {project_name} using {self.config.get('driver')}...[/info]")

        # 1. Prepare Command
        cmd = self.driver.get_backup_command(self.config)

        # 2. Execute and Stream to Vault
        # We need to capture the output of the subprocess and write it to a file in the object store.
        # Since CAS engine works with files, we probably need to stream to a temp file or
        # extend CAS engine to accept a stream.
        # Looking at cas_engine.py might be useful.
        # For now, let's stream to a temp file in the vault's temp area or system temp,
        # then register it with CAS.

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_name = f"db_dump_{timestamp}.sql"

        # We can use a temp file
        import tempfile

        # Check connection first
        verify_cmd = self.driver.get_verification_command(self.config)
        try:
            subprocess.run(verify_cmd, env=self.env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise ConnectionError(f"Could not connect to database: {e.stderr.decode()}")

        console.print("[info]Streaming database dump...[/info]")

        # Create temp file for the DUMP (uncompressed stream, but piped to compression)
        # Requirement: "Backups must be streamed via pipes... to avoid writing large uncompressed SQL files to disk."
        # CAS engine normally compresses data.
        # But we need to feed it a file.
        # If we write UNCOMPRESSED sql to disk, we violate the rule.
        # So we should compress ON THE FLY to a temp file, and tell CAS to store that.
        # BUT cas_engine.store_object() RE-COMPRESSES by default (Zstd).
        # Double compression is inefficient but safe.
        # However, if we compress here with gzip, then CAS compresses with zstd, it's weird.
        # Ideally, we write the UNCOMPRESSED stream to a NamedPipe (FIFO) and let CAS read from it?
        # CAS `store_object` reads from file path and calculates hash.
        # Hashing requires reading the whole stream.
        # If we use a pipe, we can read it once.
        # But `store_object` reads twice? No, `calculate_hash` reads it, then `store_object` reads again to compress/copy.
        # So a FIFO won't work easily because you can't rewind it.

        # Compromise: We stream the dump through GZIP (or ZSTD) to a temp file on disk.
        # This satisfies "avoid writing large UNCOMPRESSED SQL files".
        # Then we let CAS ingest that compressed file.
        # CAS will hash the COMPRESSED content (treating it as the file).
        # And CAS will likely ZSTD compress it AGAIN (overhead but okay).
        # To avoid double compression, we might need a raw storage mode in CAS, but let's stick to standard flow for now.

        # Actually, let's use gzip for the dump file itself. It's standard for SQL dumps.
        # The file stored in CAS will be "dump.sql.gz".

        import gzip

        # We write to a temp file, but we do it via python streaming to ensure we don't hold it all in RAM.
        # And we don't write uncompressed data to disk.

        blob_name_gz = blob_name + ".gz"

        with tempfile.NamedTemporaryFile(mode='wb', delete=False, prefix=f"pv_db_{project_name}_", suffix=".sql.gz") as tmp_file:
            temp_path = tmp_file.name

            # Start the dump process with stdout piped
            # Redirect stderr to a temp file to avoid deadlock
            # Tip: Use bufsize=-1 (system default) to handle large streams efficiently
            with tempfile.TemporaryFile() as stderr_file:
                dump_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=stderr_file, env=self.env, bufsize=-1)

                # Stream from dump -> gzip -> temp file
                # We can use gzip.GzipFile wrapping the temp file
                try:
                    with gzip.GzipFile(mode='wb', fileobj=tmp_file) as gz_file:
                        # Copy stream
                        while True:
                            chunk = dump_process.stdout.read(64 * 1024)
                            if not chunk:
                                break
                            gz_file.write(chunk)
                except Exception as e:
                    dump_process.kill()
                    os.unlink(temp_path)
                    raise RuntimeError(f"Streaming compression failed: {e}")

                dump_process.wait()

                if dump_process.returncode != 0:
                    # Read stderr for error message
                    stderr_file.seek(0)
                    error_msg = stderr_file.read().decode('utf-8', errors='replace')
                    os.unlink(temp_path)
                    raise RuntimeError(f"Database dump failed: {error_msg}")

        try:
            # 3. Register with CAS
            with tempfile.TemporaryDirectory() as temp_dir:
                # Move the compressed dump to the temp dir
                final_dump_path = os.path.join(temp_dir, blob_name_gz)
                os.replace(temp_path, final_dump_path)

                # Use CAS engine to backup this directory
                manifest_path = cas_engine.backup_to_vault(
                    temp_dir,
                    vault_path,
                    project_name=project_name,
                    follow_symlinks=False
                )

                # Tag metadata
                with open(manifest_path, 'r') as f:
                    manifest_data = json.load(f)

                manifest_data['snapshot_type'] = 'database'
                manifest_data['database_config'] = {
                    'driver': self.config.get('driver'),
                    'dbname': self.config.get('dbname'),
                    'host': self.config.get('host'),
                    'port': self.config.get('port'),
                    'user': self.config.get('user'),
                    'compression': 'gzip'
                }

                with open(manifest_path, 'w') as f:
                    json.dump(manifest_data, f, indent=2)

        finally:
             if os.path.exists(temp_path):
                 os.unlink(temp_path)

        console.print(f"[success]✅ Database snapshot created: {manifest_path}[/success]")

        # 4. Cloud Sync
        if cloud_sync:
            # Check if we have credentials
            key_id = None
            app_key = None

            # If credentials_module is passed, use it to resolve
            if credentials_module:
                # We need to construct a dummy args object or use the resolve function differently
                # But here we might not have 'args'.
                # However, if 'bucket' is passed, we can try to get credentials from env/config if not explicitly provided?
                # The CLI handler calls resolve_credentials and passes results usually.
                # But here we just have 'credentials_module'.

                # Let's assume the caller (CLI) should have resolved them, but the method sig has credentials_module.
                # Actually, in the CLI dispatch, we passed `credentials_module`.
                # Let's try to use it.

                # We create a dummy object to satisfy resolve_credentials interface if needed
                class DummyArgs:
                    def __init__(self, bucket, endpoint):
                        self.bucket = bucket
                        self.endpoint = endpoint
                        self.key_id = None
                        self.secret_key = None

                d_args = DummyArgs(bucket, endpoint)
                k, s, src = credentials_module.resolve_credentials(d_args)
                key_id = k
                app_key = s

            if bucket and key_id and app_key:
                console.print(f"[info]Pushing to cloud bucket '{bucket}'...[/info]")
                from src.projectclone import sync_engine
                try:
                    sync_engine.sync_to_cloud(
                        vault_path,
                        bucket,
                        endpoint,
                        key_id,
                        app_key,
                        dry_run=False
                    )
                    console.print(f"[success]☁️ Cloud Push Successful[/success]")
                except Exception as e:
                    console.print(f"[error]Cloud Push Failed: {e}[/error]")
                    # We don't raise here to preserve the local backup
            else:
                 if cloud_sync:
                     console.print("[warning]Skipping cloud sync: Missing credentials or bucket configuration.[/warning]")

        return manifest_path

    def restore(self, manifest_path: str, vault_path: str, force: bool = False, credentials_module=None):
        """
        Restores the database from a snapshot.
        """
        # Resolve password just in case (e.g. for connection check)
        self._resolve_password(credentials_module)

        console.print(f"[info]Restoring database from {manifest_path}...[/info]")

        # 1. Load Manifest
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)

        if manifest_data.get('snapshot_type') != 'database':
            console.print("[warning]Warning: This snapshot does not appear to be a database snapshot.[/warning]")
            # We continue but warn.

        # 2. Extract Dump
        # We need to restore the file from the vault to a temp location.
        from src.projectrestore import restore_engine

        with tempfile.TemporaryDirectory() as temp_dir:
            restore_engine.restore_snapshot(manifest_path, temp_dir)

            # Find the .sql file
            dump_file = None
            is_compressed = False
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".sql"):
                        dump_file = os.path.join(root, file)
                        break
                    elif file.endswith(".sql.gz"):
                        dump_file = os.path.join(root, file)
                        is_compressed = True
                        break

            if not dump_file:
                raise FileNotFoundError("No SQL dump file found in the snapshot.")

            # 3. Prepare DB (Force / Check)
            if force:
                console.print("[warning]--force specified. Recreating database...[/warning]")
                drop_cmd = self.driver.get_drop_command(self.config)
                create_cmd = self.driver.get_create_command(self.config)

                try:
                    subprocess.run(drop_cmd, env=self.env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    subprocess.run(create_cmd, env=self.env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"Failed to recreate database: {e.stderr.decode()}")
            else:
                 # Verify connection
                verify_cmd = self.driver.get_verification_command(self.config)
                try:
                    subprocess.run(verify_cmd, env=self.env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError:
                     raise ConnectionError("Target database not reachable. Use --force to attempt creation/reset.")

            # 4. Stream Restore
            console.print("[info]Applying database dump...[/info]")
            restore_cmd = self.driver.get_restore_command(self.config)

            # Handle decompression if needed
            try:
                if is_compressed:
                     # Use a pipe chain: gzip -dc dump_file | psql ...
                     # This is more efficient and avoids Python-level streaming issues
                     # Use a pipe chain: gzip -dc dump_file | sed filter | psql ...
                     cat_cmd = ["gzip", "-dc", dump_file]
                     cat_proc = subprocess.Popen(cat_cmd, stdout=subprocess.PIPE)
                     
                     # Filter out 'transaction_timeout' which causes errors on older server versions
                     filter_cmd = ["sed", "s/SET transaction_timeout = 0;//g"]
                     filter_proc = subprocess.Popen(filter_cmd, stdin=cat_proc.stdout, stdout=subprocess.PIPE)
                     cat_proc.stdout.close()
                     
                     process = subprocess.Popen(restore_cmd, stdin=filter_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
                     filter_proc.stdout.close()
                     stdout, stderr = process.communicate()
                     cat_proc.wait()
                else:
                    with open(dump_file, 'rb') as f:
                        process = subprocess.Popen(restore_cmd, stdin=f, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
                        stdout, stderr = process.communicate()

                if process.returncode != 0:
                    raise RuntimeError(f"Restore failed: {stderr.decode(errors='replace')}")
            except Exception as e:
                raise RuntimeError(f"Restore execution failed: {e}")

            console.print("[success]✅ Database restored successfully.[/success]")
