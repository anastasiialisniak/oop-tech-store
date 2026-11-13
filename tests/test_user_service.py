from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import jwt
from pwdlib import PasswordHash

from src.config import JWT_ALGORITHM, JWT_SECRET_KEY
from src.models.user import Admin, Customer
from src.scripts.bootstrap_admin import (
    format_bootstrap_success_message,
    main as bootstrap_main,
    run_bootstrap,
)
from src.scripts.create_admin import main as create_admin_main
from src.services.database import Database
from src.services.token_service import create_access_token, verify_access_token
from src.services.user_service import UserService


class DatabaseForTest(Database):

    def __init__(self, database_path):
        self.database_path = database_path
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class TestUserService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.test_db = DatabaseForTest(self.database_path)

        self.database_patcher = patch(
            "src.services.user_service.Database",
            lambda: self.test_db
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
        self.assertIsInstance(user, Customer)
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
        self.assertIsInstance(user, Customer)
        self.assertEqual(user.get_role(), "Customer")

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

    def test_authenticate_admin_returns_admin_domain_object(self):
        password_hash = PasswordHash.recommended().hash("AdminPass123!")
        admin_id = self.test_db.create_user(
            name="System Admin",
            email="admin@nexora.ua",
            password_hash=password_hash,
            role="Admin",
        )

        user = self.user_service.authenticate_user(
            "admin@nexora.ua",
            "AdminPass123!",
        )

        self.assertIsNotNone(user)
        self.assertIsInstance(user, Admin)
        self.assertEqual(user.get_user_id(), admin_id)
        self.assertEqual(user.get_name(), "System Admin")
        self.assertEqual(user.get_email(), "admin@nexora.ua")
        self.assertEqual(user.get_role(), "Admin")
        self.assertTrue(user.can_manage_products())

        # Невірний пароль для Admin також відхиляється
        self.assertIsNone(
            self.user_service.authenticate_user("admin@nexora.ua", "WrongPass!")
        )

    def test_get_user_by_email_and_id_for_customer_and_admin(self):
        customer = self.user_service.register_user(
            "Customer One",
            "customer1@nexora.ua",
            "Password123!",
        )
        password_hash = PasswordHash.recommended().hash("AdminPass123!")
        admin_id = self.test_db.create_user(
            name="Admin One",
            email="admin1@nexora.ua",
            password_hash=password_hash,
            role="Admin",
        )

        by_email_cust = self.user_service.get_user_by_email("customer1@nexora.ua")
        self.assertIsInstance(by_email_cust, Customer)

        by_email_admin = self.user_service.get_user_by_email("admin1@nexora.ua")
        self.assertIsInstance(by_email_admin, Admin)

        by_id_cust = self.user_service.get_user_by_id(customer.get_user_id())
        self.assertIsInstance(by_id_cust, Customer)

        by_id_admin = self.user_service.get_user_by_id(admin_id)
        self.assertIsInstance(by_id_admin, Admin)

        self.assertIsNone(self.user_service.get_user_by_id(999))
        self.assertIsNone(self.user_service.get_user_by_id(0))
        self.assertIsNone(self.user_service.get_user_by_id(-5))
        self.assertIsNone(self.user_service.get_user_by_id(True))

    def test_bootstrap_admin_creates_admin_only_when_no_admin_exists(self):
        self.assertFalse(self.user_service.has_admin_user())

        admin = self.user_service.bootstrap_admin(
            "Initial Admin",
            "Admin.Bootstrap@Nexora.ua",
            "StrongAdminPass123!",
        )
        self.assertIsInstance(admin, Admin)
        self.assertEqual(admin.get_role(), "Admin")
        self.assertEqual(admin.get_email(), "admin.bootstrap@nexora.ua")
        self.assertTrue(self.user_service.has_admin_user())

        # Password is stored hashed, never in plain text
        raw_row = self.test_db.get_user_by_email("admin.bootstrap@nexora.ua")
        self.assertIsNotNone(raw_row)
        self.assertNotEqual(raw_row[3], "StrongAdminPass123!")
        self.assertEqual(raw_row[4], "Admin")

        # Bootstrapped Admin can authenticate normally
        authenticated = self.user_service.authenticate_user(
            "admin.bootstrap@nexora.ua",
            "StrongAdminPass123!",
        )
        self.assertIsInstance(authenticated, Admin)
        self.assertEqual(authenticated.get_role(), "Admin")

        # Second bootstrap attempt is refused
        with self.assertRaises(ValueError):
            self.user_service.bootstrap_admin(
                "Second Admin",
                "admin2@nexora.ua",
                "AnotherStrongPass123!",
            )

    def test_bootstrap_admin_never_promotes_existing_customer(self):
        customer = self.user_service.register_user(
            "Existing Customer",
            "buyer@nexora.ua",
            "CustomerPass123!",
        )
        self.assertEqual(customer.get_role(), "Customer")

        with self.assertRaises(ValueError):
            self.user_service.bootstrap_admin(
                "Attempted Promotion",
                "buyer@nexora.ua",
                "NewAdminPass123!",
            )

        # Verify customer was NOT promoted to Admin
        still_customer = self.user_service.get_user_by_email("buyer@nexora.ua")
        self.assertIsInstance(still_customer, Customer)
        self.assertEqual(still_customer.get_role(), "Customer")
        self.assertFalse(self.user_service.has_admin_user())

    def test_bootstrap_admin_validates_inputs(self):
        for invalid_args in (
            ("", "admin@nexora.ua", "StrongPass123!"),
            ("   ", "admin@nexora.ua", "StrongPass123!"),
            ("Admin", "not-an-email", "StrongPass123!"),
            ("Admin", "admin@invalid", "StrongPass123!"),
            ("Admin", "admin@nexora.ua", "short"),
        ):
            with self.assertRaises(ValueError):
                self.user_service.bootstrap_admin(*invalid_args)

    def test_cli_run_bootstrap_reads_env_and_refuses_duplicate_admin(self):
        env_vars = {
            "NEXORA_ADMIN_NAME": "CLI Admin",
            "NEXORA_ADMIN_EMAIL": "cli.admin@nexora.ua",
            "NEXORA_ADMIN_PASSWORD": "CliStrongPassword123!",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            admin = run_bootstrap(database=self.test_db, interactive=False)
            self.assertIsInstance(admin, Admin)
            self.assertEqual(admin.get_email(), "cli.admin@nexora.ua")
            self.assertEqual(admin.get_role(), "Admin")

            with self.assertRaises(ValueError):
                run_bootstrap(database=self.test_db, interactive=False)

    def test_cli_main_prints_success_message_with_existing_admin_getters(self):
        env_vars = {
            "NEXORA_ENV": "test",
            "NEXORA_DB_PATH": str(self.database_path),
            "NEXORA_ADMIN_NAME": "Лілія",
            "NEXORA_ADMIN_EMAIL": "liliia.admin@nexora.ua",
            "NEXORA_ADMIN_PASSWORD": "SecretAdminPassword123!",
        }
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        with (
            patch.dict("os.environ", env_vars, clear=False),
            patch("src.scripts.bootstrap_admin.Database", lambda: self.test_db),
            patch("src.scripts.bootstrap_admin.sys.stdin.isatty", return_value=False),
            redirect_stdout(stdout_buf),
            redirect_stderr(stderr_buf),
        ):
            exit_code = bootstrap_main()

        self.assertEqual(exit_code, 0)
        output = stdout_buf.getvalue().strip()
        self.assertIn(
            "[Nexora Bootstrap] Administrator account created successfully "
            "(id=1, name='Лілія', email='liliia.admin@nexora.ua', role=Admin).",
            output,
        )
        # Пароль ніколи не виводиться у stdout або stderr
        self.assertNotIn("SecretAdminPassword123!", output)
        self.assertNotIn("SecretAdminPassword123!", stderr_buf.getvalue())

        # Повторний виклик main() без --allow-additional повертає код 1 і повідомлення про помилку в stderr
        stdout_buf_2 = io.StringIO()
        stderr_buf_2 = io.StringIO()
        with (
            patch.dict("os.environ", env_vars, clear=False),
            patch("src.scripts.bootstrap_admin.Database", lambda: self.test_db),
            patch("src.scripts.bootstrap_admin.sys.stdin.isatty", return_value=False),
            redirect_stdout(stdout_buf_2),
            redirect_stderr(stderr_buf_2),
        ):
            second_exit_code = bootstrap_main()

        self.assertEqual(second_exit_code, 1)
        self.assertIn("[Nexora Bootstrap Error]", stderr_buf_2.getvalue())

    def test_create_additional_admin_preserves_existing_accounts_and_rejects_duplicates(self):
        # 1. Створюємо Customer та першого Admin
        customer = self.user_service.register_user(
            "Existing Customer",
            "customer@nexora.ua",
            "CustomerPass123!",
        )
        first_admin = self.user_service.bootstrap_admin(
            "First Admin",
            "admin1@nexora.ua",
            "FirstAdminPass123!",
        )

        # 2. Створюємо другого Admin через create_admin_user / allow_additional=True
        second_admin = self.user_service.create_admin_user(
            "Second Admin",
            "admin2@nexora.ua",
            "SecondAdminPass123!",
        )
        self.assertIsInstance(second_admin, Admin)
        self.assertEqual(second_admin.get_role(), "Admin")
        self.assertEqual(second_admin.get_email(), "admin2@nexora.ua")
        self.assertNotEqual(first_admin.get_user_id(), second_admin.get_user_id())

        # 3. Обидва Admin та існуючий Customer збережені й працюють
        self.assertIsInstance(
            self.user_service.authenticate_user("admin1@nexora.ua", "FirstAdminPass123!"),
            Admin,
        )
        self.assertIsInstance(
            self.user_service.authenticate_user("admin2@nexora.ua", "SecondAdminPass123!"),
            Admin,
        )
        still_customer = self.user_service.authenticate_user(
            "customer@nexora.ua",
            "CustomerPass123!",
        )
        self.assertIsInstance(still_customer, Customer)
        self.assertEqual(still_customer.get_user_id(), customer.get_user_id())
        self.assertEqual(still_customer.get_role(), "Customer")

        # 4. Дублікат email (існуючого Admin або існуючого Customer) відхиляється, роль Customer захищена
        with self.assertRaises(ValueError):
            self.user_service.create_admin_user(
                "Duplicate Admin",
                "admin1@nexora.ua",
                "AnotherStrongPass123!",
            )
        with self.assertRaises(ValueError):
            self.user_service.create_admin_user(
                "Promote Attempt",
                "customer@nexora.ua",
                "AnotherStrongPass123!",
            )
        self.assertEqual(
            self.user_service.get_user_by_email("customer@nexora.ua").get_role(),
            "Customer",
        )

    def test_create_admin_cli_interactive_getpass_and_invisible_typing_notice(self):
        # Спочатку створюємо першого Admin
        self.user_service.bootstrap_admin(
            "First Admin",
            "admin1@nexora.ua",
            "FirstAdminPass123!",
        )

        # Інтерактивне створення другого Admin через create_admin CLI
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        clean_env = {
            "NEXORA_ENV": "test",
            "NEXORA_DB_PATH": str(self.database_path),
            "NEXORA_ADMIN_NAME": "",
            "NEXORA_ADMIN_EMAIL": "",
            "NEXORA_ADMIN_PASSWORD": "",
        }
        with (
            patch.dict("os.environ", clean_env, clear=False),
            patch("src.scripts.bootstrap_admin.Database", lambda: self.test_db),
            patch("src.scripts.bootstrap_admin.sys.stdin.isatty", return_value=True),
            patch(
                "builtins.input",
                side_effect=["Анастасія Адмін", "anastasiia.admin@nexora.ua"],
            ),
            patch(
                "src.scripts.bootstrap_admin.getpass.getpass",
                side_effect=["HiddenPass123!", "HiddenPass123!"],
            ) as mock_getpass,
            redirect_stdout(stdout_buf),
            redirect_stderr(stderr_buf),
        ):
            exit_code = create_admin_main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_getpass.call_count, 2)
        output = stdout_buf.getvalue()
        self.assertIn("символи НЕ відображаються на екрані", output)
        self.assertIn(
            "(id=2, name='Анастасія Адмін', email='anastasiia.admin@nexora.ua', role=Admin)",
            output,
        )
        self.assertNotIn("HiddenPass123!", output)
        self.assertNotIn("HiddenPass123!", stderr_buf.getvalue())


class TestTokenService(unittest.TestCase):

    def test_create_and_verify_token_includes_role(self):
        customer_token = create_access_token(user_id=1, role="Customer")
        payload_cust = verify_access_token(customer_token)

        self.assertIsNotNone(payload_cust)
        self.assertEqual(payload_cust["sub"], "1")
        self.assertEqual(payload_cust["role"], "Customer")
        self.assertIn("exp", payload_cust)
        self.assertIn("iat", payload_cust)

        admin_token = create_access_token(user_id=2, role="Admin")
        payload_admin = verify_access_token(admin_token)

        self.assertIsNotNone(payload_admin)
        self.assertEqual(payload_admin["sub"], "2")
        self.assertEqual(payload_admin["role"], "Admin")

    def test_expired_token_is_rejected(self):
        expired_token = create_access_token(
            user_id=1,
            role="Customer",
            expires_delta=timedelta(minutes=-5),
        )
        self.assertIsNone(verify_access_token(expired_token))

    def test_invalid_malformed_and_wrong_signature_tokens_are_rejected(self):
        now = datetime.now(timezone.utc)
        wrong_secret_token = jwt.encode(
            {
                "sub": "1",
                "role": "Admin",
                "iat": now,
                "exp": now + timedelta(minutes=15),
            },
            "wrong-secret-key-with-at-least-32-bytes-length",
            algorithm=JWT_ALGORITHM,
        )
        invalid_role_token = jwt.encode(
            {
                "sub": "1",
                "role": "SuperUser",
                "iat": now,
                "exp": now + timedelta(minutes=15),
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        invalid_sub_token = jwt.encode(
            {
                "sub": "not-an-int",
                "role": "Customer",
                "iat": now,
                "exp": now + timedelta(minutes=15),
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )

        for bad_token in (
            "",
            "   ",
            None,
            "not.a.jwt",
            wrong_secret_token,
            invalid_role_token,
            invalid_sub_token,
        ):
            self.assertIsNone(verify_access_token(bad_token))


if __name__ == "__main__":
    unittest.main()
