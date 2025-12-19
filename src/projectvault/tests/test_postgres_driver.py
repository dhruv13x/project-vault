import unittest
from unittest.mock import MagicMock
from src.projectvault.drivers.postgres import PostgresDriver

class TestPostgresDriver(unittest.TestCase):
    def setUp(self):
        self.driver = PostgresDriver()
        self.config = {
            "dbname": "test_db",
            "host": "localhost",
            "port": 5432,
            "user": "admin",
            "password": "secret_password"
        }

    def test_get_env(self):
        env = self.driver._get_env(self.config)
        self.assertEqual(env.get("PGPASSWORD"), "secret_password")

    def test_get_backup_command(self):
        cmd = self.driver.get_backup_command(self.config)
        self.assertEqual(cmd[0], "pg_dump")
        self.assertIn("-h", cmd)
        self.assertIn("localhost", cmd)
        self.assertIn("-p", cmd)
        self.assertIn("5432", cmd)
        self.assertIn("-U", cmd)
        self.assertIn("admin", cmd)
        self.assertIn("test_db", cmd)
        self.assertIn("--clean", cmd)
        self.assertIn("--if-exists", cmd)
        self.assertIn("--no-owner", cmd)
        self.assertIn("--no-acl", cmd)

    def test_get_restore_command(self):
        cmd = self.driver.get_restore_command(self.config)
        self.assertEqual(cmd[0], "psql")
        self.assertIn("-h", cmd)
        self.assertIn("localhost", cmd)
        self.assertIn("-p", cmd)
        self.assertIn("5432", cmd)
        self.assertIn("-U", cmd)
        self.assertIn("admin", cmd)
        self.assertIn("-d", cmd)
        self.assertIn("test_db", cmd)
        self.assertIn("ON_ERROR_STOP=1", cmd)

    def test_get_verification_command(self):
        cmd = self.driver.get_verification_command(self.config)
        self.assertEqual(cmd[0], "psql")
        self.assertIn("-c", cmd)
        self.assertIn("SELECT 1", cmd)

    def test_get_drop_command(self):
        cmd = self.driver.get_drop_command(self.config)
        self.assertEqual(cmd[0], "psql")
        self.assertIn("-d", cmd)
        self.assertIn("postgres", cmd)
        self.assertTrue(any("DROP DATABASE IF EXISTS" in c for c in cmd))
        self.assertTrue(any("\"test_db\"" in c for c in cmd))

    def test_get_create_command(self):
        cmd = self.driver.get_create_command(self.config)
        self.assertEqual(cmd[0], "psql")
        self.assertIn("-d", cmd)
        self.assertIn("postgres", cmd)
        self.assertTrue(any("CREATE DATABASE" in c for c in cmd))
        self.assertTrue(any("\"test_db\"" in c for c in cmd))
