
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.services.user_service import UserService
from src.services.database import Database


class TestUserService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"

        self.database_patcher = patch(
            "src.services.user_service.Database",
            lambda: DatabaseForTest(self.database_path)
        )
        self.database_patcher.start()

        self.user_service = UserService()

    def tearDown(self):
        self.database_patcher.stop()
        self.temp_dir.cleanup()

    def test_register_user(self):
        user = self.user_service.register_user(
            "Anna",
            "anna@gmail.com",
            "Password123!"
        )
        self.assertEqual(user.get_role(), "Customer")

    def test_duplicate_email(self):
        self.user_service.register_user(
            "Anna",
            "anna@gmail.com",
            "Password123!"
        )

        with self.assertRaises(ValueError):
            self.user_service.register_user(
                "Alex",
                "anna@gmail.com",
                "Password456!"
            )

    def test_authenticate_user(self):
        self.user_service.register_user(
            "Anna",
            "anna@gmail.com",
            "Password123!"
        )

        user = self.user_service.authenticate_user(
            "anna@gmail.com",
            "Password123!"
        )

        self.assertIsNotNone(user)

    def test_wrong_password(self):
        self.user_service.register_user(
            "Anna",
            "anna@gmail.com",
            "Password123!"
        )

        user = self.user_service.authenticate_user(
            "anna@gmail.com",
            "WrongPassword!"
        )

        self.assertIsNone(user)


class DatabaseForTest(Database):

    def __init__(self, database_path):
        self.database_path = database_path
        self.initialize()

    def connect(self):
        import sqlite3
        return sqlite3.connect(self.database_path)


if __name__ == "__main__":
    unittest.main()
