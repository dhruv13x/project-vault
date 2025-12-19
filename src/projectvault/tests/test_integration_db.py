import unittest
import subprocess
import time
import os
import shutil
import tempfile
import json
from src.projectvault.engines.db_engine import DatabaseEngine

# Check if docker is available and usable
def is_docker_available():
    try:
        # Check version
        subprocess.run(["docker", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        # Check permissions/daemon status by running hello-world or similar, or just docker info
        subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

@unittest.skipUnless(is_docker_available(), "Docker not available or not usable")
class TestIntegrationDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start Postgres Container
        cls.container_name = "pv_test_postgres"
        cls.db_password = "mysecretpassword"
        cls.db_user = "postgres"
        cls.db_name = "testdb"
        cls.port = 5433 # Use non-standard port to avoid conflict

        print(f"Starting Docker container {cls.container_name}...")
        try:
            subprocess.run([
                "docker", "run", "--name", cls.container_name,
                "-e", f"POSTGRES_PASSWORD={cls.db_password}",
                "-e", f"POSTGRES_DB={cls.db_name}",
                "-p", f"{cls.port}:5432",
                "-d", "postgres:alpine"
            ], check=True, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            # Cleanup if it failed (maybe exists)
            subprocess.run(["docker", "rm", "-f", cls.container_name], stderr=subprocess.DEVNULL)
            # Try again
            subprocess.run([
                "docker", "run", "--name", cls.container_name,
                "-e", f"POSTGRES_PASSWORD={cls.db_password}",
                "-e", f"POSTGRES_DB={cls.db_name}",
                "-p", f"{cls.port}:5432",
                "-d", "postgres:alpine"
            ], check=True, stdout=subprocess.DEVNULL)

        # Wait for DB to be ready
        print("Waiting for Postgres to be ready...")
        time.sleep(5)
        # Better check loop
        for _ in range(30):
            try:
                subprocess.run([
                    "psql", f"postgres://{cls.db_user}:{cls.db_password}@localhost:{cls.port}/{cls.db_name}",
                    "-c", "SELECT 1"
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                time.sleep(1)
        else:
            print("Warning: Postgres did not start in time or psql not found. Tests might fail.")

    @classmethod
    def tearDownClass(cls):
        print(f"Stopping Docker container {cls.container_name}...")
        subprocess.run(["docker", "rm", "-f", cls.container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def setUp(self):
        self.vault_dir = tempfile.mkdtemp()
        self.config = {
            "driver": "postgres",
            "dbname": self.db_name,
            "host": "localhost",
            "port": self.port,
            "user": self.db_user,
            "password": self.db_password
        }
        self.engine = DatabaseEngine("postgres", self.config)

        # Populate Data
        self._run_sql("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT);")
        self._run_sql("INSERT INTO users (name) VALUES ('Alice'), ('Bob');")

    def tearDown(self):
        shutil.rmtree(self.vault_dir)

    def _run_sql(self, sql):
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_password
        subprocess.run([
            "psql", "-h", "localhost", "-p", str(self.port), "-U", self.db_user, "-d", self.db_name, "-c", sql
        ], env=env, check=True, stdout=subprocess.DEVNULL)

    def _get_row_count(self):
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_password
        result = subprocess.run([
            "psql", "-h", "localhost", "-p", str(self.port), "-U", self.db_user, "-d", self.db_name, "-t", "-c", "SELECT COUNT(*) FROM users;"
        ], env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return int(result.stdout.decode().strip())

    def test_backup_restore_cycle(self):
        # 1. Verify initial state
        self.assertEqual(self._get_row_count(), 2)

        # 2. Backup
        manifest_path = self.engine.backup(self.vault_dir, "test_project")
        self.assertTrue(os.path.exists(manifest_path))

        # 3. Modify Data (Simulate corruption/loss)
        self._run_sql("DELETE FROM users WHERE name = 'Bob';")
        self.assertEqual(self._get_row_count(), 1)

        # 4. Restore
        # Since we are restoring to same DB, we might need force to drop/create or just restore over it?
        # pg_restore/psql usually appends unless we clean.
        # Our driver uses --clean in backup, so it should handle existing objects.
        self.engine.restore(manifest_path, self.vault_dir, force=True)

        # 5. Verify restored state
        self.assertEqual(self._get_row_count(), 2)
