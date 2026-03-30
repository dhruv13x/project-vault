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

    def _database_file_name(self, dbname: str) -> str:
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in dbname)
        return f"{safe_name}.sql.gz"

    def _database_name_from_dump_path(self, dump_path: str) -> str:
        name = os.path.basename(dump_path)
        if name.endswith(".sql.gz"):
            return name[:-7]
        if name.endswith(".sql"):
            return name[:-4]
        return name

    def _get_backup_targets(self) -> list[str]:
        configured = self.config.get("dbnames")
        if configured:
            if isinstance(configured, str):
                return [configured]
            return list(configured)

        if self.config.get("all_databases"):
            list_cmd = self.driver.get_database_list_command(self.config)
            result = subprocess.run(
                list_cmd,
                env=self.env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]

        if self.config.get("dbname"):
            return [self.config["dbname"]]

        raise ValueError("No database target configured. Set 'dbname', 'dbnames', or 'all_databases = true'.")

    def backup(self, vault_path: str, project_name: str, cloud_sync: bool = False, credentials_module=None, bucket: str = None, endpoint: str = None) -> str:
        """
        Backs up the database to the vault.
        Returns the path to the manifest file.
        """
        self._resolve_password(credentials_module)

        console.print(f"[info]Starting database backup for {project_name} using {self.config.get('driver')}...[/info]")

        targets = self._get_backup_targets()
        if not targets:
            raise ValueError("No databases found to back up.")

        for dbname in targets:
            verify_cmd = self.driver.get_verification_command(self.config, dbname=dbname)
            try:
                subprocess.run(verify_cmd, env=self.env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                raise ConnectionError(f"Could not connect to database '{dbname}': {e.stderr.decode()}")

        console.print(f"[info]Streaming database dump for {len(targets)} database(s)...[/info]")

        import gzip

        with tempfile.TemporaryDirectory() as temp_dir:
            for dbname in targets:
                final_dump_path = os.path.join(temp_dir, self._database_file_name(dbname))
                cmd = self.driver.get_backup_command(self.config, dbname=dbname)
                with open(final_dump_path, "wb") as tmp_file:
                    with tempfile.TemporaryFile() as stderr_file:
                        dump_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=stderr_file, env=self.env, bufsize=-1)
                        try:
                            with gzip.GzipFile(mode='wb', fileobj=tmp_file) as gz_file:
                                while True:
                                    chunk = dump_process.stdout.read(64 * 1024)
                                    if not chunk:
                                        break
                                    gz_file.write(chunk)
                        except Exception as e:
                            dump_process.kill()
                            raise RuntimeError(f"Streaming compression failed for '{dbname}': {e}")

                        dump_process.wait()

                        if dump_process.returncode != 0:
                            stderr_file.seek(0)
                            error_msg = stderr_file.read().decode('utf-8', errors='replace')
                            raise RuntimeError(f"Database dump failed for '{dbname}': {error_msg}")

            manifest_path = cas_engine.backup_to_vault(
                temp_dir,
                vault_path,
                project_name=project_name,
                follow_symlinks=False
            )

            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)

            manifest_data['snapshot_type'] = 'database'
            manifest_data['database_config'] = {
                'driver': self.config.get('driver'),
                'dbname': self.config.get('dbname'),
                'dbnames': targets,
                'all_databases': self.config.get('all_databases', False),
                'host': self.config.get('host'),
                'port': self.config.get('port'),
                'user': self.config.get('user'),
                'compression': 'gzip'
            }

            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f, indent=2)

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

            # Find SQL dump files restored from the snapshot
            dump_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".sql"):
                        dump_files.append((os.path.join(root, file), False))
                    elif file.endswith(".sql.gz"):
                        dump_files.append((os.path.join(root, file), True))

            if not dump_files:
                raise FileNotFoundError("No SQL dump file found in the snapshot.")

            manifest_targets = manifest_data.get("database_config", {}).get("dbnames")
            if manifest_targets:
                db_targets = list(manifest_targets)
            elif self.config.get("dbnames"):
                configured_targets = self.config.get("dbnames")
                db_targets = list(configured_targets) if isinstance(configured_targets, list) else [configured_targets]
            elif self.config.get("dbname"):
                db_targets = [self.config["dbname"]]
            else:
                db_targets = []

            dump_files.sort(key=lambda item: item[0])
            derived_targets = [(self._database_name_from_dump_path(path), (path, is_compressed)) for path, is_compressed in dump_files]

            if len(dump_files) > 1 and db_targets:
                target_set = set(db_targets)
                if all(derived_name in target_set for derived_name, _ in derived_targets):
                    dump_plan = [(derived_name, dump_info) for derived_name, dump_info in derived_targets]
                elif len(db_targets) == len(dump_files):
                    dump_plan = list(zip(db_targets, dump_files))
                else:
                    raise ValueError("Snapshot contains multiple database dumps but restore targets could not be mapped.")
            elif len(dump_files) > 1:
                dump_plan = [(derived_name, dump_info) for derived_name, dump_info in derived_targets]
            elif len(dump_files) == 1:
                target = db_targets[0] if db_targets else self.config.get("dbname") or derived_targets[0][0]
                if not target:
                    raise ValueError("Restore target database is unknown.")
                dump_plan = [(target, dump_files[0])]

            for target_db, (dump_file, is_compressed) in dump_plan:
                console.print(f"[info]Applying database dump to {target_db}...[/info]")

                if force:
                    console.print(f"[warning]--force specified. Recreating database '{target_db}'...[/warning]")
                    drop_cmd = self.driver.get_drop_command(self.config, dbname=target_db)
                    create_cmd = self.driver.get_create_command(self.config, dbname=target_db)

                    try:
                        subprocess.run(drop_cmd, env=self.env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        subprocess.run(create_cmd, env=self.env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    except subprocess.CalledProcessError as e:
                        raise RuntimeError(f"Failed to recreate database '{target_db}': {e.stderr.decode()}")
                else:
                    verify_cmd = self.driver.get_verification_command(self.config, dbname=target_db)
                    try:
                        subprocess.run(verify_cmd, env=self.env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    except subprocess.CalledProcessError:
                        raise ConnectionError(f"Target database '{target_db}' not reachable. Use --force to attempt creation/reset.")

                restore_cmd = self.driver.get_restore_command(self.config, dbname=target_db)

                try:
                    if is_compressed:
                        cat_cmd = ["gzip", "-dc", dump_file]
                        cat_proc = subprocess.Popen(cat_cmd, stdout=subprocess.PIPE)

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
                        raise RuntimeError(f"Restore failed for '{target_db}': {stderr.decode(errors='replace')}")
                except Exception as e:
                    raise RuntimeError(f"Restore execution failed for '{target_db}': {e}")

            console.print("[success]✅ Database restored successfully.[/success]")
