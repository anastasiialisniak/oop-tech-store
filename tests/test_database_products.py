import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.services.database import (
    DEFAULT_DATABASE_PATH,
    PROJECT_ROOT,
    SEED_PRODUCTS,
    Database,
    DatabaseConfigurationError,
    get_application_mode,
    resolve_database_path,
    verify_and_log_database_config,
)


class DatabaseForTest(Database):
    """Database, яка працює з окремим тимчасовим файлом SQLite."""

    def __init__(self, database_path):
        self.database_path = database_path
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class TestDatabaseProducts(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.database = DatabaseForTest(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_products_table_exists(self):
        with sqlite3.connect(self.database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        connection.close()

        self.assertIn("products", tables)
        self.assertIn("users", tables)

    def test_seed_adds_eight_products(self):
        products = self.database.get_all_products()

        self.assertEqual(len(products), 8)
        self.assertEqual(len(SEED_PRODUCTS), 8)
        self.assertEqual(
            [product["id"] for product in products],
            [1, 2, 3, 4, 5, 6, 7, 8]
        )

    def test_seed_is_not_repeated(self):
        self.database.initialize()
        self.database.initialize()

        self.assertEqual(len(self.database.get_all_products()), 8)

    def test_seed_does_not_run_when_table_not_empty(self):
        self.database.delete_product(1)
        self.database.initialize()

        self.assertEqual(len(self.database.get_all_products()), 7)
        self.assertIsNone(self.database.get_product_by_id(1))

    def test_seed_does_not_touch_existing_users(self):
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "INSERT INTO users (name, email, password_hash) "
                "VALUES (?, ?, ?)",
                ("Anna", "anna@gmail.com", "hash")
            )
        connection.close()

        self.database.initialize()

        user = self.database.get_user_by_email("anna@gmail.com")
        self.assertIsNotNone(user)
        self.assertEqual(user[1], "Anna")
        self.assertEqual(user[4], "Customer")

    def test_get_product_by_id(self):
        product = self.database.get_product_by_id(1)

        self.assertEqual(product["name"], "Mechanical Keyboard")
        self.assertEqual(product["brand"], "Logitech")
        self.assertEqual(product["category"], "keyboard")
        self.assertEqual(product["price"], 2500)
        self.assertEqual(product["stock_quantity"], 10)
        self.assertEqual(product["image"], "images/mechanical-keyboard.jpg.jpg")

    def test_get_product_by_id_not_found(self):
        self.assertIsNone(self.database.get_product_by_id(999))

    def test_attributes_json_by_category(self):
        keyboard = self.database.get_product_by_id(1)
        mouse = self.database.get_product_by_id(2)
        headphones = self.database.get_product_by_id(3)
        webcam = self.database.get_product_by_id(4)

        self.assertEqual(
            keyboard["attributes"],
            {"switch_type": "Red", "layout": "US"}
        )
        self.assertEqual(
            mouse["attributes"],
            {"dpi": 12000, "connection_type": "Wireless"}
        )
        self.assertEqual(
            headphones["attributes"],
            {"wireless": True, "has_microphone": True}
        )
        self.assertEqual(
            webcam["attributes"],
            {"resolution": "1920x1080", "frame_rate": 60}
        )

    def test_create_product(self):
        product_id = self.database.create_product(
            name="Test Mouse",
            brand="Test",
            category="mouse",
            price=999.5,
            stock_quantity=3,
            image="images/test.jpg",
            attributes={"dpi": 8000, "connection_type": "Wired"}
        )

        self.assertEqual(product_id, 9)

        product = self.database.get_product_by_id(product_id)
        self.assertEqual(product["name"], "Test Mouse")
        self.assertEqual(product["price"], 999.5)
        self.assertEqual(product["stock_quantity"], 3)
        self.assertEqual(
            product["attributes"],
            {"dpi": 8000, "connection_type": "Wired"}
        )
        self.assertEqual(len(self.database.get_all_products()), 9)

    def test_create_product_without_attributes(self):
        product_id = self.database.create_product(
            "Simple", "Brand", "keyboard", 100, 1
        )

        product = self.database.get_product_by_id(product_id)
        self.assertEqual(product["attributes"], {})
        self.assertIsNone(product["image"])

    def test_create_product_rejects_negative_price_or_stock(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.database.create_product("Bad", "B", "mouse", -1, 1)

        with self.assertRaises(ValueError):
            self.database.create_product("Bad", "B", "mouse", 1, -1)

    def test_stock_validation_rejects_fractional_and_boolean_values(self):
        for bad_stock in (2.5, 2.0, True, False, "10", None):
            with self.assertRaises(ValueError):
                self.database.create_product("Bad", "B", "mouse", 100, bad_stock)

            with self.assertRaises(ValueError):
                self.database.update_product_stock(1, bad_stock)

    def test_seed_products_5_to_8_have_empty_unverified_attributes(self):
        for product_id in (5, 6, 7, 8):
            product = self.database.get_product_by_id(product_id)
            self.assertEqual(product["attributes"], {})

    def test_sql_injection_is_treated_as_plain_text(self):
        evil_name = "x'); DROP TABLE products; --"
        product_id = self.database.create_product(
            evil_name, "Brand", "mouse", 10, 1
        )

        self.assertEqual(
            self.database.get_product_by_id(product_id)["name"],
            evil_name
        )
        self.assertEqual(len(self.database.get_all_products()), 9)

    def test_update_product_stock(self):
        self.assertTrue(self.database.update_product_stock(1, 4))

        self.assertEqual(
            self.database.get_product_by_id(1)["stock_quantity"],
            4
        )

    def test_update_product_stock_to_zero(self):
        self.assertTrue(self.database.update_product_stock(1, 0))

        self.assertEqual(
            self.database.get_product_by_id(1)["stock_quantity"],
            0
        )

    def test_update_product_stock_missing_product(self):
        self.assertFalse(self.database.update_product_stock(999, 5))

    def test_update_product_stock_negative_raises(self):
        with self.assertRaises(ValueError):
            self.database.update_product_stock(1, -1)

        self.assertEqual(
            self.database.get_product_by_id(1)["stock_quantity"],
            10
        )

    def test_delete_product(self):
        self.assertTrue(self.database.delete_product(1))

        self.assertIsNone(self.database.get_product_by_id(1))
        self.assertEqual(len(self.database.get_all_products()), 7)

    def test_delete_missing_product(self):
        self.assertFalse(self.database.delete_product(999))
        self.assertEqual(len(self.database.get_all_products()), 8)


class TestDatabaseSafetyGuard(unittest.TestCase):

    def test_test_mode_with_db_test_sqlite3(self):
        expected_test_path = (PROJECT_ROOT / "db.test.sqlite3").resolve()
        with patch.dict(
            os.environ,
            {"NEXORA_ENV": "test", "NEXORA_DB_PATH": "db.test.sqlite3"},
            clear=False,
        ):
            self.assertEqual(get_application_mode(), "test")
            self.assertEqual(resolve_database_path(), expected_test_path)

            with self.assertLogs("nexora.database", level="INFO") as log_ctx:
                mode, resolved = verify_and_log_database_config()

            self.assertEqual(mode, "test")
            self.assertEqual(resolved, expected_test_path)
            combined_logs = "\n".join(log_ctx.output)
            self.assertIn("mode=test", combined_logs)
            self.assertIn(str(expected_test_path), combined_logs)

    def test_test_mode_without_nexora_db_path(self):
        for invalid_value in (None, "", "   "):
            env_patch = {"NEXORA_ENV": "test"}
            with patch.dict(os.environ, env_patch, clear=False):
                if invalid_value is None:
                    os.environ.pop("NEXORA_DB_PATH", None)
                else:
                    os.environ["NEXORA_DB_PATH"] = invalid_value

                with self.assertRaises(DatabaseConfigurationError):
                    resolve_database_path()

                with self.assertRaises(RuntimeError):
                    verify_and_log_database_config()

    def test_test_mode_pointing_to_db_sqlite3(self):
        prod_Candidates = [
            "db.sqlite3",
            "./db.sqlite3",
            str(DEFAULT_DATABASE_PATH),
        ]
        for candidate in prod_Candidates:
            with patch.dict(
                os.environ,
                {"NEXORA_ENV": "test", "NEXORA_DB_PATH": candidate},
                clear=False,
            ):
                with self.assertRaises(DatabaseConfigurationError):
                    resolve_database_path()

                with self.assertRaises(RuntimeError):
                    verify_and_log_database_config()

        with patch.dict(
            os.environ,
            {"NEXORA_ENV": "test", "NEXORA_DB_PATH": "db.test.sqlite3"},
            clear=False,
        ):
            with self.assertRaises(DatabaseConfigurationError):
                Database(database_path=DEFAULT_DATABASE_PATH)

    def test_normal_production_mode(self):
        expected_prod_path = DEFAULT_DATABASE_PATH.resolve()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEXORA_ENV", None)
            os.environ.pop("NEXORA_DB_PATH", None)

            self.assertEqual(get_application_mode(), "production")
            self.assertEqual(resolve_database_path(), expected_prod_path)

            with self.assertLogs("nexora.database", level="INFO") as log_ctx:
                mode, resolved = verify_and_log_database_config()

            self.assertEqual(mode, "production")
            self.assertEqual(resolved, expected_prod_path)
            combined_logs = "\n".join(log_ctx.output)
            self.assertIn("mode=production", combined_logs)
            self.assertIn(str(expected_prod_path), combined_logs)


if __name__ == "__main__":
    unittest.main()
