import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.models.product import Product
from src.models.keyboard import Keyboard
from src.models.mouse import Mouse
from src.models.headphones import Headphones
from src.models.webcam import Webcam
from src.services.database import Database, UNVERIFIED_SEED_ATTRIBUTES
from src.services.product_factory import ProductFactory
from src.services.product_service import ProductService


class DatabaseForTest(Database):
    """Ізольована тестова база даних SQLite у тимчасовому файлі."""

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class TestProductFactory(unittest.TestCase):

    def test_create_keyboard_subclass(self):
        product = ProductFactory.create_product(
            name="Mechanical Keyboard",
            brand="Logitech",
            category="keyboard",
            price=2500,
            stock_quantity=10,
            attributes={"switch_type": "Red", "layout": "US"},
            product_id=1,
        )

        self.assertIsInstance(product, Product)
        self.assertIsInstance(product, Keyboard)
        self.assertEqual(product.get_product_id(), 1)
        self.assertEqual(product.get_name(), "Mechanical Keyboard")
        self.assertEqual(product.get_brand(), "Logitech")
        self.assertEqual(product.get_price(), 2500.0)
        self.assertEqual(product.get_stock_quantity(), 10)
        self.assertEqual(
            product.get_description(),
            "Keyboard with Red switches and US layout.",
        )

    def test_create_mouse_subclass(self):
        product = ProductFactory.create_product(
            name="Gaming Mouse",
            brand="Logitech",
            category="MOUSE",
            price=1500,
            stock_quantity=20,
            attributes={"dpi": 12000, "connection_type": "Wireless"},
            product_id=2,
        )

        self.assertIsInstance(product, Mouse)
        self.assertEqual(
            product.get_description(),
            "Mouse with 12000 DPI and Wireless connection.",
        )

    def test_create_headphones_subclass(self):
        product = ProductFactory.create_product(
            name="Gaming Headset",
            brand="HyperX",
            category="headphones",
            price=3200,
            stock_quantity=15,
            attributes={"wireless": True, "has_microphone": True},
            product_id=3,
        )

        self.assertIsInstance(product, Headphones)
        self.assertEqual(
            product.get_description(),
            "Headphones: Wireless, with microphone.",
        )

    def test_create_webcam_subclass(self):
        product = ProductFactory.create_product(
            name="Full HD Webcam",
            brand="Logitech",
            category="webcam",
            price=2200,
            stock_quantity=8,
            attributes={"resolution": "1920x1080", "frame_rate": 60},
            product_id=4,
        )

        self.assertIsInstance(product, Webcam)
        self.assertEqual(
            product.get_description(),
            "Webcam with 1920x1080 resolution and 60 FPS.",
        )

    def test_empty_attributes_do_not_invent_specifications(self):
        product = ProductFactory.create_product(
            name="Wireless Keyboard",
            brand="Logitech",
            category="keyboard",
            price=1800,
            stock_quantity=12,
            attributes={},
            product_id=5,
        )

        self.assertIsInstance(product, Keyboard)
        self.assertEqual(product.get_description(), "")

    def test_require_attributes_rejects_empty_attributes(self):
        with self.assertRaises(ValueError):
            ProductFactory.create_product(
                name="Wireless Keyboard",
                brand="Logitech",
                category="keyboard",
                price=1800,
                stock_quantity=12,
                attributes={},
                require_attributes=True,
            )

    def test_rejects_empty_name_and_brand(self):
        for bad_text in ("", "   ", None, 123):
            with self.assertRaises(ValueError):
                ProductFactory.create_product(
                    name=bad_text,
                    brand="Logitech",
                    category="mouse",
                    price=1000,
                    stock_quantity=5,
                )

            with self.assertRaises(ValueError):
                ProductFactory.create_product(
                    name="Mouse",
                    brand=bad_text,
                    category="mouse",
                    price=1000,
                    stock_quantity=5,
                )

    def test_rejects_unsupported_category(self):
        for bad_category in ("monitor", "laptop", "", "   ", None, 42):
            with self.assertRaises(ValueError):
                ProductFactory.create_product(
                    name="Item",
                    brand="Brand",
                    category=bad_category,
                    price=1000,
                    stock_quantity=5,
                )

    def test_rejects_invalid_and_negative_prices(self):
        for bad_price in (-1, -0.01, "1000", None, True, False, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                ProductFactory.create_product(
                    name="Item",
                    brand="Brand",
                    category="mouse",
                    price=bad_price,
                    stock_quantity=5,
                )

    def test_rejects_fractional_negative_and_invalid_stock(self):
        for bad_stock in (1.5, 5.0, -1, "10", None, True, False):
            with self.assertRaises(ValueError):
                ProductFactory.create_product(
                    name="Item",
                    brand="Brand",
                    category="mouse",
                    price=1000,
                    stock_quantity=bad_stock,
                )

    def test_rejects_invalid_category_specific_attributes(self):
        invalid_cases = [
            ("keyboard", {"switch_type": "Red"}),
            ("keyboard", {"switch_type": "", "layout": "US"}),
            ("keyboard", {"switch_type": "Red", "layout": "US", "extra": 1}),
            ("mouse", {"dpi": -100, "connection_type": "Wired"}),
            ("mouse", {"dpi": 0, "connection_type": "Wired"}),
            ("mouse", {"dpi": True, "connection_type": "Wired"}),
            ("mouse", {"dpi": 8000, "connection_type": ""}),
            ("headphones", {"wireless": "yes", "has_microphone": True}),
            ("headphones", {"wireless": True, "has_microphone": 1}),
            ("webcam", {"resolution": "", "frame_rate": 60}),
            ("webcam", {"resolution": "1080p", "frame_rate": 0}),
            ("webcam", {"resolution": "1080p", "frame_rate": False}),
            ("webcam", "not-a-dict"),
        ]

        for category, attrs in invalid_cases:
            with self.assertRaises(ValueError):
                ProductFactory.create_product(
                    name="Item",
                    brand="Brand",
                    category=category,
                    price=1000,
                    stock_quantity=5,
                    attributes=attrs,
                )


class TestProductService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test_service.sqlite3"
        self.database = DatabaseForTest(self.database_path)
        self.service = ProductService(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_preserves_eight_seeded_products_and_ids(self):
        products = self.service.get_all_products()

        self.assertEqual(len(products), 8)
        self.assertEqual([p["id"] for p in products], [1, 2, 3, 4, 5, 6, 7, 8])

    def test_converts_records_to_domain_subclasses(self):
        self.assertIsInstance(self.service.get_domain_product(1), Keyboard)
        self.assertIsInstance(self.service.get_domain_product(2), Mouse)
        self.assertIsInstance(self.service.get_domain_product(3), Headphones)
        self.assertIsInstance(self.service.get_domain_product(4), Webcam)
        self.assertIsInstance(self.service.get_domain_product(5), Keyboard)
        self.assertIsInstance(self.service.get_domain_product(6), Mouse)
        self.assertIsInstance(self.service.get_domain_product(7), Headphones)
        self.assertIsInstance(self.service.get_domain_product(8), Webcam)
        self.assertIsNone(self.service.get_domain_product(999))

    def test_verified_products_1_to_4_have_polymorphic_descriptions(self):
        p1 = self.service.get_product_by_id(1)
        p2 = self.service.get_product_by_id(2)
        p3 = self.service.get_product_by_id(3)
        p4 = self.service.get_product_by_id(4)

        self.assertEqual(
            p1["description"],
            "Keyboard with Red switches and US layout.",
        )
        self.assertEqual(
            p2["description"],
            "Mouse with 12000 DPI and Wireless connection.",
        )
        self.assertEqual(
            p3["description"],
            "Headphones: Wireless, with microphone.",
        )
        self.assertEqual(
            p4["description"],
            "Webcam with 1920x1080 resolution and 60 FPS.",
        )

    def test_products_5_to_8_do_not_expose_unverified_specifications(self):
        for product_id in (5, 6, 7, 8):
            product = self.service.get_product_by_id(product_id)
            self.assertEqual(product["attributes"], {})
            self.assertEqual(product["description"], "")

    def test_legacy_unverified_seed_attributes_are_neutralized_without_overwriting_db(self):
        # Імітуємо наявність припущених атрибутів з Етапу 2 у таблиці products
        with sqlite3.connect(self.database_path) as connection:
            for pid, legacy_attrs in UNVERIFIED_SEED_ATTRIBUTES.items():
                connection.execute(
                    "UPDATE products SET attributes_json = ? WHERE id = ?",
                    (json.dumps(legacy_attrs), pid),
                )
        connection.close()

        for pid in (5, 6, 7, 8):
            product = self.service.get_product_by_id(pid)
            self.assertEqual(product["attributes"], {})
            self.assertEqual(product["description"], "")

    def test_filters_by_category_brand_price_and_search(self):
        keyboards = self.service.get_all_products(category="keyboard")
        self.assertEqual([p["id"] for p in keyboards], [1, 5])

        all_cat = self.service.get_all_products(category="all")
        self.assertEqual(len(all_cat), 8)

        logitech = self.service.get_all_products(brand="Logitech")
        self.assertEqual([p["id"] for p in logitech], [1, 2, 4, 5])

        multi_brand = self.service.get_all_products(brand=["Razer", "Sony"])
        self.assertEqual([p["id"] for p in multi_brand], [6, 7])

        under_2000 = self.service.get_all_products(max_price=2000)
        self.assertEqual([p["id"] for p in under_2000], [2, 5])

        searched = self.service.get_all_products(search="webcam")
        self.assertEqual([p["id"] for p in searched], [4, 8])

        combined = self.service.get_all_products(
            category="keyboard",
            brand="Logitech",
            max_price=2000,
            search="wireless",
        )
        self.assertEqual([p["id"] for p in combined], [5])

    def test_create_update_stock_and_delete_product(self):
        created = self.service.create_product(
            name="Pro Mechanical Keyboard",
            brand="Keychron",
            category="keyboard",
            price=4200,
            stock_quantity=6,
            image="images/keychron.jpg",
            attributes={"switch_type": "Brown", "layout": "UA"},
        )

        self.assertEqual(created["id"], 9)
        self.assertEqual(created["name"], "Pro Mechanical Keyboard")
        self.assertEqual(created["stock_quantity"], 6)
        self.assertEqual(created["stock"], 6)
        self.assertTrue(created["available"])
        self.assertEqual(
            created["description"],
            "Keyboard with Brown switches and UA layout.",
        )
        self.assertEqual(len(self.service.get_all_products()), 9)

        self.assertTrue(self.service.update_product_stock(9, 0))
        updated = self.service.get_product_by_id(9)
        self.assertEqual(updated["stock_quantity"], 0)
        self.assertFalse(updated["available"])

        with self.assertRaises(ValueError):
            self.service.update_product_stock(9, -1)

        with self.assertRaises(ValueError):
            self.service.update_product_stock(9, 2.5)

        self.assertTrue(self.service.delete_product(9))
        self.assertIsNone(self.service.get_product_by_id(9))
        self.assertFalse(self.service.delete_product(9))
        self.assertEqual(len(self.service.get_all_products()), 8)

    def test_update_product_fields_attributes_and_description(self):
        updated = self.service.update_product(
            product_id=1,
            name="Mechanical Keyboard Pro",
            brand="Keychron",
            category="keyboard",
            price=3100,
            stock_quantity=14,
            image="images/keyboard-pro.jpg",
            attributes={"switch_type": "Brown", "layout": "UA"},
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated["id"], 1)
        self.assertEqual(updated["name"], "Mechanical Keyboard Pro")
        self.assertEqual(updated["brand"], "Keychron")
        self.assertEqual(updated["price"], 3100.0)
        self.assertEqual(updated["stock_quantity"], 14)
        self.assertEqual(updated["image"], "images/keyboard-pro.jpg")
        self.assertEqual(
            updated["attributes"],
            {"switch_type": "Brown", "layout": "UA"},
        )
        self.assertEqual(
            updated["description"],
            "Keyboard with Brown switches and UA layout.",
        )

        # Кастомний опис має пріоритет над автоматичним описом
        with_custom_desc = self.service.update_product(
            product_id=1,
            description="Механічна клавіатура з підсвіткою та українською розкладкою.",
        )
        self.assertEqual(
            with_custom_desc["description"],
            "Механічна клавіатура з підсвіткою та українською розкладкою.",
        )

        # Очищення кастомного опису повертає поліморфний опис від підкласу
        cleared_desc = self.service.update_product(
            product_id=1,
            description="",
            replace_description=True,
        )
        self.assertEqual(
            cleared_desc["description"],
            "Keyboard with Brown switches and UA layout.",
        )

        # Неіснуючий ID повертає None
        self.assertIsNone(
            self.service.update_product(product_id=999, name="Missing")
        )


if __name__ == "__main__":
    unittest.main()
