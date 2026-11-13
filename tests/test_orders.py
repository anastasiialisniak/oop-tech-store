import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from pwdlib import PasswordHash

# Імпортуємо TestClient та in-memory ASGI адаптер із test_api_products
from tests.test_api_products import TestClient
from src.api.dependencies import get_user_service
from src.api.main import app
from src.api.orders import get_order_service
from src.api.products import get_product_service
from src.models.delivery import CourierDelivery, PickupDelivery
from src.models.payment import CardPayment, CashPayment
from src.services.database import Database
from src.services.order_service import OrderService
from src.services.payment_delivery_factory import PaymentDeliveryFactory
from src.services.product_service import ProductService
from src.services.token_service import create_access_token
from src.services.user_service import UserService


class DatabaseForTest(Database):
    """Ізольована тестова база даних SQLite у тимчасовому файлі."""

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class TestPaymentDeliveryFactory(unittest.TestCase):

    def test_create_pickup_and_courier_delivery(self):
        pickup = PaymentDeliveryFactory.create_delivery(
            "pickup",
            address="Kyiv, Khreshchatyk 10",
        )
        self.assertIsInstance(pickup, PickupDelivery)
        self.assertEqual(pickup.calculate_cost(), 0.0)
        self.assertEqual(pickup.get_address(), "Kyiv, Khreshchatyk 10")

        pickup_default = PaymentDeliveryFactory.create_delivery("pickup")
        self.assertIsInstance(pickup_default, PickupDelivery)
        self.assertEqual(pickup_default.calculate_cost(), 0.0)

        courier = PaymentDeliveryFactory.create_delivery(
            "courier",
            address="Kyiv, Khreshchatyk 1",
            distance_km=10,
        )
        self.assertIsInstance(courier, CourierDelivery)
        self.assertEqual(courier.calculate_cost(), 80 + 10 * 15)

    def test_create_card_and_cash_payment(self):
        card = PaymentDeliveryFactory.create_payment(
            "card",
            amount=2500,
            card_number="1234567890123456",
        )
        self.assertIsInstance(card, CardPayment)
        self.assertEqual(
            card.process_payment(),
            "Card payment of 2500.00 UAH processed.",
        )

        cash = PaymentDeliveryFactory.create_payment("cash", amount=1500)
        self.assertIsInstance(cash, CashPayment)
        self.assertEqual(
            cash.process_payment(),
            "Cash payment of 1500.00 UAH processed.",
        )

    def test_factory_rejects_invalid_inputs(self):
        for bad_delivery in ("drone", "", "   ", None, 123):
            with self.assertRaises(ValueError):
                PaymentDeliveryFactory.create_delivery(
                    bad_delivery,
                    address="Kyiv",
                )

        for bad_address in ("", "   ", None, 123):
            with self.assertRaises(ValueError):
                PaymentDeliveryFactory.create_delivery(
                    "courier",
                    address=bad_address,
                )

        for bad_distance in (0, -5, True, "10", float("nan")):
            with self.assertRaises(ValueError):
                PaymentDeliveryFactory.create_delivery(
                    "courier",
                    address="Kyiv",
                    distance_km=bad_distance,
                )

        for bad_payment in ("crypto", "", None, 123):
            with self.assertRaises(ValueError):
                PaymentDeliveryFactory.create_payment(bad_payment, amount=100)

        for bad_amount in (0, -100, True, "100", float("inf")):
            with self.assertRaises(ValueError):
                PaymentDeliveryFactory.create_payment("cash", amount=bad_amount)

        with self.assertRaises(ValueError):
            PaymentDeliveryFactory.create_payment(
                "card",
                amount=100,
                card_number="12",
            )


class TestOrderServiceAndTransactions(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test_orders.sqlite3"
        self.database = DatabaseForTest(self.database_path)
        self.product_service = ProductService(self.database)
        self.order_service = OrderService(self.database, self.product_service)

        hasher = PasswordHash.recommended()
        self.customer_id = self.database.create_user(
            "Anna",
            "anna@nexora.ua",
            hasher.hash("Password123!"),
            role="Customer",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_guest_and_customer_checkout_totals_and_stock_reduction(self):
        # 1. Guest checkout із самовивозом (доставка = 0 грн) та готівкою
        guest_order = self.order_service.create_order(
            customer_name="Guest Buyer",
            customer_email="guest@example.com",
            delivery_type="pickup",
            payment_type="cash",
            items=[{"product_id": 1, "quantity": 2}],
        )

        self.assertEqual(guest_order["id"], 1)
        self.assertIsNone(guest_order["user_id"])
        self.assertEqual(guest_order["items_total"], 5000.0)
        self.assertEqual(guest_order["delivery_cost"], 0.0)
        self.assertEqual(guest_order["total_amount"], 5000.0)
        self.assertEqual(guest_order["status"], "Created")
        self.assertEqual(
            guest_order["payment_message"],
            "Cash payment of 5000.00 UAH processed.",
        )
        # Залишок товару 1 зменшився з 10 до 8
        self.assertEqual(
            self.product_service.get_product_by_id(1)["stock_quantity"],
            8,
        )

        # 2. Customer checkout із кур'єрською доставкою (80 + 4 * 15 = 140 грн) та карткою
        cust_order = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="courier",
            delivery_address="м. Київ, вул. Хрещатик, 1",
            distance_km=4,
            payment_type="card",
            card_number="4111222233334444",
            items=[
                {"product_id": 2, "quantity": 1},  # 1500 грн
                {"product_id": 4, "quantity": 2},  # 2 * 2200 = 4400 грн
            ],
            user_id=self.customer_id,
        )

        self.assertEqual(cust_order["id"], 2)
        self.assertEqual(cust_order["user_id"], self.customer_id)
        self.assertEqual(cust_order["items_total"], 5900.0)
        self.assertEqual(cust_order["delivery_cost"], 140.0)
        self.assertEqual(cust_order["total_amount"], 6040.0)
        self.assertEqual(
            cust_order["payment_message"],
            "Card payment of 6040.00 UAH processed.",
        )
        self.assertEqual(
            self.product_service.get_product_by_id(2)["stock_quantity"],
            19,
        )
        self.assertEqual(
            self.product_service.get_product_by_id(4)["stock_quantity"],
            6,
        )

    def test_historical_snapshot_preserved_when_product_deleted(self):
        order = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="card",
            items=[{"product_id": 1, "quantity": 1}],
            user_id=self.customer_id,
        )

        # Видаляємо товар 1 із каталогу
        self.product_service.delete_product(1)
        self.assertIsNone(self.product_service.get_product_by_id(1))

        # Історичні дані в замовленні залишаються незмінними
        fetched = self.order_service.get_order_by_id(order["id"])
        self.assertEqual(len(fetched["items"]), 1)
        self.assertEqual(fetched["items"][0]["product_id"], 1)
        self.assertEqual(fetched["items"][0]["product_name"], "Mechanical Keyboard")
        self.assertEqual(fetched["items"][0]["price"], 2500.0)
        self.assertEqual(fetched["total_amount"], 2500.0)

    def test_insufficient_stock_and_invalid_items_rejected(self):
        # Запит більшої кількості, ніж є на складі (товар 8 має stock = 4)
        with self.assertRaises(ValueError):
            self.order_service.create_order(
                customer_name="Anna",
                customer_email="anna@nexora.ua",
                delivery_type="pickup",
                payment_type="cash",
                items=[{"product_id": 8, "quantity": 5}],
            )

        # Дубльовані позиції одного товару в замовленні, що сумарно перевищують залишок (3 + 2 > 4)
        with self.assertRaises(ValueError):
            self.order_service.create_order(
                customer_name="Anna",
                customer_email="anna@nexora.ua",
                delivery_type="pickup",
                payment_type="cash",
                items=[
                    {"product_id": 8, "quantity": 3},
                    {"product_id": 8, "quantity": 2},
                ],
            )

        # Неіснуючий товар та некоректні кількості
        invalid_item_lists = [
            [],
            [{"product_id": 999, "quantity": 1}],
            [{"product_id": 1, "quantity": 0}],
            [{"product_id": 1, "quantity": -2}],
            [{"product_id": 1, "quantity": 1.5}],
            [{"product_id": 1, "quantity": True}],
            [{"product_id": -1, "quantity": 1}],
        ]
        for bad_items in invalid_item_lists:
            with self.assertRaises(ValueError):
                self.order_service.create_order(
                    customer_name="Anna",
                    customer_email="anna@nexora.ua",
                    delivery_type="pickup",
                    payment_type="cash",
                    items=bad_items,
                )

        # Залишок товару 8 та 1 не змінився, жодного замовлення не створено
        self.assertEqual(self.product_service.get_product_by_id(8)["stock_quantity"], 4)
        self.assertEqual(self.product_service.get_product_by_id(1)["stock_quantity"], 10)
        self.assertEqual(len(self.order_service.get_all_orders()), 0)

    def test_transaction_rollback_when_order_creation_fails_mid_transaction(self):
        # Сценарій 1: у create_order_transaction перший товар має достатній залишок,
        # а другий товар не має достатнього залишку — транзакція має відкотити списання першого товару
        with self.assertRaises(ValueError):
            self.database.create_order_transaction(
                user_id=self.customer_id,
                customer_name="Anna",
                customer_email="anna@nexora.ua",
                delivery_type="pickup",
                delivery_address="Самовивіз",
                payment_type="cash",
                total_amount=5000.0,
                status="Created",
                date="2026-11-12 12:00:00",
                items=[
                    {
                        "product_id": 1,
                        "product_name": "Mechanical Keyboard",
                        "price": 2500.0,
                        "quantity": 3,
                    },
                    {
                        "product_id": 8,
                        "product_name": "Streaming Webcam",
                        "price": 3900.0,
                        "quantity": 99,  # Перевищує залишок (4)
                    },
                ],
            )

        # Сценарій 2: помилка обмеження ЦІЛІСНОСТІ БД під час вставки другого order_item (price < 0)
        # після того, як залишки вже були зменшені і запис в orders вже був створений!
        with self.assertRaises(sqlite3.IntegrityError):
            self.database.create_order_transaction(
                user_id=self.customer_id,
                customer_name="Anna",
                customer_email="anna@nexora.ua",
                delivery_type="pickup",
                delivery_address="Самовивіз",
                payment_type="cash",
                total_amount=2500.0,
                status="Created",
                date="2026-11-12 12:00:00",
                items=[
                    {
                        "product_id": 1,
                        "product_name": "Mechanical Keyboard",
                        "price": -100.0,  # Порушує CHECK (price >= 0) в order_items
                        "quantity": 2,
                    },
                ],
            )

        # Перевіряємо повний відкат (ROLLBACK): залишок товару 1 лишився 10, замовлень = 0
        self.assertEqual(self.product_service.get_product_by_id(1)["stock_quantity"], 10)
        self.assertEqual(self.product_service.get_product_by_id(8)["stock_quantity"], 4)
        self.assertEqual(len(self.database.get_all_orders()), 0)

    def test_valid_and_invalid_status_transitions(self):
        order = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="card",
            items=[{"product_id": 1, "quantity": 1}],
            user_id=self.customer_id,
        )
        oid = order["id"]

        # Created -> Completed напряму заборонено (лише через Shipped)
        with self.assertRaises(ValueError):
            self.order_service.update_order_status(oid, "Completed")

        # Created -> Paid -> Shipped -> Completed
        paid = self.order_service.update_order_status(oid, "Paid")
        self.assertEqual(paid["status"], "Paid")
        self.assertTrue(paid["can_be_cancelled"])

        # Paid -> Completed напряму також заборонено
        with self.assertRaises(ValueError):
            self.order_service.update_order_status(oid, "Completed")

        shipped = self.order_service.update_order_status(oid, "Shipped")
        self.assertEqual(shipped["status"], "Shipped")
        self.assertFalse(shipped["can_be_cancelled"])

        # Shipped -> Cancelled заборонено (Order.can_be_cancelled() == False)
        with self.assertRaises(ValueError):
            self.order_service.update_order_status(oid, "Cancelled")

        completed = self.order_service.update_order_status(oid, "Completed")
        self.assertEqual(completed["status"], "Completed")

        # Зміна статусу завершеного замовлення заборонена
        with self.assertRaises(ValueError):
            self.order_service.update_order_status(oid, "Cancelled")

        # Друге замовлення: Created -> Cancelled
        order2 = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="cash",
            items=[{"product_id": 2, "quantity": 1}],
            user_id=self.customer_id,
        )
        cancelled = self.order_service.update_order_status(
            order2["id"],
            "Cancelled",
        )
        self.assertEqual(cancelled["status"], "Cancelled")

        # Зміна статусу скасованого замовлення заборонена
        with self.assertRaises(ValueError):
            self.order_service.update_order_status(order2["id"], "Paid")

        # Невідомий статус відхиляється
        with self.assertRaises(ValueError):
            self.order_service.update_order_status(order2["id"], "UnknownStatus")

    def test_foreign_keys_pragma_and_on_delete_behaviors(self):
        # 1. PRAGMA foreign_keys == 1 як у тестовому DatabaseForTest, так і в базовому Database.connect()
        with closing(self.database.connect()) as conn:
            fk_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(fk_enabled, 1)

        with closing(Database.connect(self.database)) as base_conn:
            base_fk_enabled = base_conn.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(base_fk_enabled, 1)

        # 2. Створюємо замовлення, прив'язане до користувача self.customer_id
        order = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="card",
            items=[
                {"product_id": 1, "quantity": 1},
                {"product_id": 2, "quantity": 2},
            ],
            user_id=self.customer_id,
        )
        order_id = order["id"]
        self.assertEqual(order["user_id"], self.customer_id)

        # Видаляємо користувача з таблиці users -> orders.user_id має стати NULL (ON DELETE SET NULL)
        with closing(self.database.connect()) as conn:
            with conn:
                conn.execute("DELETE FROM users WHERE id = ?", (self.customer_id,))

        order_after_user_delete = self.order_service.get_order_by_id(order_id)
        self.assertIsNotNone(order_after_user_delete)
        self.assertIsNone(order_after_user_delete["user_id"])
        self.assertEqual(len(order_after_user_delete["items"]), 2)

        # 3. Видаляємо замовлення з таблиці orders -> записи в order_items видаляються каскадно (ON DELETE CASCADE)
        with closing(self.database.connect()) as conn:
            with conn:
                conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            remaining_items = conn.execute(
                "SELECT COUNT(*) FROM order_items WHERE order_id = ?",
                (order_id,),
            ).fetchone()[0]

        self.assertEqual(remaining_items, 0)
        self.assertIsNone(self.order_service.get_order_by_id(order_id))

    def test_stock_restoration_on_order_cancellation(self):
        # Сценарій 1: Скасування замовлення зі статусу Created повертає залишки на склад
        order_created = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="cash",
            items=[
                {"product_id": 1, "quantity": 3},  # stock: 10 -> 7
                {"product_id": 2, "quantity": 4},  # stock: 20 -> 16
            ],
            user_id=self.customer_id,
        )
        self.assertEqual(self.product_service.get_product_by_id(1)["stock_quantity"], 7)
        self.assertEqual(self.product_service.get_product_by_id(2)["stock_quantity"], 16)

        cancelled_from_created = self.order_service.update_order_status(
            order_created["id"],
            "Cancelled",
        )
        self.assertEqual(cancelled_from_created["status"], "Cancelled")
        self.assertFalse(cancelled_from_created["can_be_cancelled"])
        self.assertEqual(self.product_service.get_product_by_id(1)["stock_quantity"], 10)
        self.assertEqual(self.product_service.get_product_by_id(2)["stock_quantity"], 20)

        # Сценарій 2: Скасування замовлення зі статусу Paid також повертає залишки на склад
        order_paid = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="card",
            items=[{"product_id": 3, "quantity": 5}],  # stock: 15 -> 10
            user_id=self.customer_id,
        )
        self.assertEqual(self.product_service.get_product_by_id(3)["stock_quantity"], 10)
        self.order_service.update_order_status(order_paid["id"], "Paid")

        cancelled_from_paid = self.order_service.update_order_status(
            order_paid["id"],
            "Cancelled",
        )
        self.assertEqual(cancelled_from_paid["status"], "Cancelled")
        self.assertEqual(self.product_service.get_product_by_id(3)["stock_quantity"], 15)

        # Сценарій 3: Невдала спроба скасування зі статусу Shipped або Completed НЕ змінює залишки
        order_shipped = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="card",
            items=[{"product_id": 4, "quantity": 2}],  # stock: 8 -> 6
            user_id=self.customer_id,
        )
        self.assertEqual(self.product_service.get_product_by_id(4)["stock_quantity"], 6)
        self.order_service.update_order_status(order_shipped["id"], "Shipped")

        with self.assertRaises(ValueError):
            self.order_service.update_order_status(order_shipped["id"], "Cancelled")
        self.assertEqual(self.product_service.get_product_by_id(4)["stock_quantity"], 6)

        self.order_service.update_order_status(order_shipped["id"], "Completed")
        with self.assertRaises(ValueError):
            self.order_service.update_order_status(order_shipped["id"], "Cancelled")
        self.assertEqual(self.product_service.get_product_by_id(4)["stock_quantity"], 6)

    def test_idempotent_status_updates_and_no_duplicate_stock_restoration(self):
        # 1. Перевірка ідемпотентності для Created -> Created, Paid -> Paid, Shipped -> Shipped, Completed -> Completed
        order = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="card",
            items=[{"product_id": 1, "quantity": 2}],  # stock: 10 -> 8
            user_id=self.customer_id,
        )
        oid = order["id"]

        same_created = self.order_service.update_order_status(oid, "Created")
        self.assertEqual(same_created["status"], "Created")
        self.assertEqual(self.product_service.get_product_by_id(1)["stock_quantity"], 8)

        self.order_service.update_order_status(oid, "Paid")
        same_paid = self.order_service.update_order_status(oid, "Paid")
        self.assertEqual(same_paid["status"], "Paid")
        self.assertEqual(self.product_service.get_product_by_id(1)["stock_quantity"], 8)

        self.order_service.update_order_status(oid, "Shipped")
        same_shipped = self.order_service.update_order_status(oid, "Shipped")
        self.assertEqual(same_shipped["status"], "Shipped")
        self.assertEqual(self.product_service.get_product_by_id(1)["stock_quantity"], 8)

        self.order_service.update_order_status(oid, "Completed")
        same_completed = self.order_service.update_order_status(oid, "Completed")
        self.assertEqual(same_completed["status"], "Completed")
        self.assertEqual(self.product_service.get_product_by_id(1)["stock_quantity"], 8)

        # 2. Перевірка ідемпотентності для Cancelled -> Cancelled (залишок відновлюється РІВНО один раз)
        order_to_cancel = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="cash",
            items=[{"product_id": 2, "quantity": 5}],  # stock: 20 -> 15
            user_id=self.customer_id,
        )
        cancel_id = order_to_cancel["id"]
        self.assertEqual(self.product_service.get_product_by_id(2)["stock_quantity"], 15)

        first_cancel = self.order_service.update_order_status(cancel_id, "Cancelled")
        self.assertEqual(first_cancel["status"], "Cancelled")
        self.assertEqual(self.product_service.get_product_by_id(2)["stock_quantity"], 20)

        # Повторний виклик через OrderService.update_order_status
        second_cancel = self.order_service.update_order_status(cancel_id, "Cancelled")
        self.assertEqual(second_cancel["status"], "Cancelled")
        self.assertEqual(self.product_service.get_product_by_id(2)["stock_quantity"], 20)

        # Повторний прямий виклик через Database.cancel_order_transaction
        self.assertTrue(self.database.cancel_order_transaction(cancel_id))
        self.assertEqual(self.product_service.get_product_by_id(2)["stock_quantity"], 20)

    def test_cancel_order_when_product_was_deleted_from_catalog(self):
        # Замовлення містить два товари; один з них видаляється з каталогу до скасування замовлення
        order = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="cash",
            items=[
                {"product_id": 1, "quantity": 2},  # stock: 10 -> 8
                {"product_id": 2, "quantity": 3},  # stock: 20 -> 17
            ],
            user_id=self.customer_id,
        )
        oid = order["id"]

        # Видаляємо товар 1 з каталогу
        self.assertTrue(self.product_service.delete_product(1))
        self.assertIsNone(self.product_service.get_product_by_id(1))

        # Скасування замовлення виконується без помилок, відновлює залишок товару 2 та зберігає історію
        cancelled = self.order_service.update_order_status(oid, "Cancelled")
        self.assertEqual(cancelled["status"], "Cancelled")
        self.assertEqual(self.product_service.get_product_by_id(2)["stock_quantity"], 20)
        self.assertEqual(len(cancelled["items"]), 2)

    def test_cancellation_rollback_when_database_fails_mid_transaction(self):
        order = self.order_service.create_order(
            customer_name="Anna",
            customer_email="anna@nexora.ua",
            delivery_type="pickup",
            payment_type="cash",
            items=[{"product_id": 1, "quantity": 4}],  # stock: 10 -> 6
            user_id=self.customer_id,
        )
        oid = order["id"]
        self.assertEqual(self.product_service.get_product_by_id(1)["stock_quantity"], 6)

        # Імітуємо збій БД після оновлення залишків у products, але на кроці UPDATE orders SET status = 'Cancelled'
        class FailingOnOrderStatusUpdateConnection:
            def __init__(self, real_conn):
                self._real_conn = real_conn

            def execute(self, sql, parameters=()):
                if "UPDATE orders" in sql and "Cancelled" in sql:
                    raise sqlite3.OperationalError("Simulated DB failure during order cancellation")
                return self._real_conn.execute(sql, parameters)

            def __enter__(self):
                self._real_conn.__enter__()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return self._real_conn.__exit__(exc_type, exc_val, exc_tb)

            def close(self):
                return self._real_conn.close()

        original_connect = self.database.connect
        self.database.connect = lambda: FailingOnOrderStatusUpdateConnection(original_connect())
        try:
            with self.assertRaises(sqlite3.OperationalError):
                self.order_service.update_order_status(oid, "Cancelled")
        finally:
            self.database.connect = original_connect

        # Транзакція мала повністю відкотитися: залишок лишився 6, статус замовлення лишився Created
        self.assertEqual(self.product_service.get_product_by_id(1)["stock_quantity"], 6)
        self.assertEqual(self.order_service.get_order_by_id(oid)["status"], "Created")


class TestOrdersAPI(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test_orders_api.sqlite3"
        self.database = DatabaseForTest(self.database_path)
        self.product_service = ProductService(self.database)
        self.user_service = UserService(self.database)
        self.order_service = OrderService(self.database, self.product_service)

        hasher = PasswordHash.recommended()
        self.customer1_id = self.database.create_user(
            name="Customer One",
            email="c1@nexora.ua",
            password_hash=hasher.hash("CustomerPass1!"),
            role="Customer",
        )
        self.customer2_id = self.database.create_user(
            name="Customer Two",
            email="c2@nexora.ua",
            password_hash=hasher.hash("CustomerPass2!"),
            role="Customer",
        )
        self.admin_id = self.database.create_user(
            name="Admin User",
            email="admin@nexora.ua",
            password_hash=hasher.hash("AdminPass1!"),
            role="Admin",
        )

        self.c1_headers = {
            "Authorization": f"Bearer {create_access_token(self.customer1_id, 'Customer')}"
        }
        self.c2_headers = {
            "Authorization": f"Bearer {create_access_token(self.customer2_id, 'Customer')}"
        }
        self.admin_headers = {
            "Authorization": f"Bearer {create_access_token(self.admin_id, 'Admin')}"
        }

        app.dependency_overrides[get_product_service] = lambda: self.product_service
        app.dependency_overrides[get_user_service] = lambda: self.user_service
        app.dependency_overrides[get_order_service] = lambda: self.order_service
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.temp_dir.cleanup()

    def test_post_orders_guest_and_authenticated_ownership(self):
        # Гість створює замовлення; переданий у тілі user_id ігнорується!
        res_guest = self.client.post(
            "/orders",
            json={
                "customer_name": "Guest User",
                "customer_email": "guest@nexora.ua",
                "delivery_type": "pickup",
                "payment_type": "cash",
                "user_id": self.customer1_id,
                "items": [{"product_id": 1, "quantity": 1}],
            },
        )
        self.assertEqual(res_guest.status_code, 201)
        guest_order = res_guest.json()
        self.assertIsNone(guest_order["user_id"])
        self.assertEqual(guest_order["total_amount"], 2500.0)

        # Клієнт 1 створює замовлення; навіть якщо передати user_id Клієнта 2, власником стає Клієнт 1
        res_c1 = self.client.post(
            "/orders",
            headers=self.c1_headers,
            json={
                "customer_name": "Customer One",
                "customer_email": "c1@nexora.ua",
                "delivery_type": "courier",
                "delivery_address": "Kyiv, Main St 10",
                "distance_km": 2,
                "payment_type": "card",
                "user_id": self.customer2_id,
                "items": [{"product_id": 2, "quantity": 2}],
            },
        )
        self.assertEqual(res_c1.status_code, 201)
        c1_order = res_c1.json()
        self.assertEqual(c1_order["user_id"], self.customer1_id)
        # 2 * 1500 + (80 + 2 * 15) = 3110.0
        self.assertEqual(c1_order["total_amount"], 3110.0)

    def test_get_my_orders_and_order_access_restrictions(self):
        # Створюємо замовлення для клієнта 1, клієнта 2 та гостя
        res_guest = self.client.post(
            "/orders",
            json={
                "customer_name": "Guest",
                "customer_email": "guest@nexora.ua",
                "delivery_type": "pickup",
                "payment_type": "cash",
                "items": [{"product_id": 1, "quantity": 1}],
            },
        )
        guest_order_id = res_guest.json()["id"]

        res_c1 = self.client.post(
            "/orders",
            headers=self.c1_headers,
            json={
                "customer_name": "Customer One",
                "customer_email": "c1@nexora.ua",
                "delivery_type": "pickup",
                "payment_type": "card",
                "items": [{"product_id": 2, "quantity": 1}],
            },
        )
        c1_order_id = res_c1.json()["id"]

        res_c2 = self.client.post(
            "/orders",
            headers=self.c2_headers,
            json={
                "customer_name": "Customer Two",
                "customer_email": "c2@nexora.ua",
                "delivery_type": "pickup",
                "payment_type": "cash",
                "items": [{"product_id": 3, "quantity": 1}],
            },
        )
        c2_order_id = res_c2.json()["id"]

        # GET /orders/my без авторизації -> 401
        self.assertEqual(self.client.get("/orders/my").status_code, 401)

        # GET /orders/my для клієнта 1 повертає лише його замовлення
        my_c1 = self.client.get("/orders/my", headers=self.c1_headers)
        self.assertEqual(my_c1.status_code, 200)
        self.assertEqual([o["id"] for o in my_c1.json()], [c1_order_id])

        # Клієнт 1 має доступ до свого замовлення, але отримує 403 для замовлення клієнта 2 та гостя
        self.assertEqual(
            self.client.get(f"/orders/{c1_order_id}", headers=self.c1_headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/orders/{c2_order_id}", headers=self.c1_headers).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(f"/orders/{guest_order_id}", headers=self.c1_headers).status_code,
            403,
        )

        # Адміністратор має доступ до будь-якого замовлення та списку всіх замовлень
        self.assertEqual(
            self.client.get(f"/orders/{c1_order_id}", headers=self.admin_headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/orders/{guest_order_id}", headers=self.admin_headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/orders/999", headers=self.admin_headers).status_code,
            404,
        )

        # GET /orders: 401 для гостя, 403 для клієнта, 200 для адміністратора
        self.assertEqual(self.client.get("/orders").status_code, 401)
        self.assertEqual(
            self.client.get("/orders", headers=self.c1_headers).status_code,
            403,
        )
        all_orders_res = self.client.get("/orders", headers=self.admin_headers)
        self.assertEqual(all_orders_res.status_code, 200)
        self.assertEqual(len(all_orders_res.json()), 3)

    def test_patch_order_status_rbac_and_validation(self):
        res_order = self.client.post(
            "/orders",
            headers=self.c1_headers,
            json={
                "customer_name": "Customer One",
                "customer_email": "c1@nexora.ua",
                "delivery_type": "pickup",
                "payment_type": "card",
                "items": [{"product_id": 1, "quantity": 1}],
            },
        )
        order_id = res_order.json()["id"]

        # Гість -> 401, Клієнт -> 403
        self.assertEqual(
            self.client.patch(
                f"/orders/{order_id}/status",
                json={"status": "Paid"},
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.patch(
                f"/orders/{order_id}/status",
                headers=self.c1_headers,
                json={"status": "Paid"},
            ).status_code,
            403,
        )

        # Адміністратор оновлює статус: Created -> Paid -> Shipped -> Completed
        for next_status in ("Paid", "Shipped", "Completed"):
            res_patch = self.client.patch(
                f"/orders/{order_id}/status",
                headers=self.admin_headers,
                json={"status": next_status},
            )
            self.assertEqual(res_patch.status_code, 200)
            self.assertEqual(res_patch.json()["status"], next_status)

        # Невалідний перехід зі стану Completed -> 400
        res_invalid = self.client.patch(
            f"/orders/{order_id}/status",
            headers=self.admin_headers,
            json={"status": "Cancelled"},
        )
        self.assertEqual(res_invalid.status_code, 400)

        # Неіснуюче замовлення -> 404
        res_missing = self.client.patch(
            "/orders/999/status",
            headers=self.admin_headers,
            json={"status": "Paid"},
        )
        self.assertEqual(res_missing.status_code, 404)

    def test_patch_order_cancellation_restores_stock_and_idempotency(self):
        # Створюємо замовлення на 3 одиниці товару 1 (stock: 10 -> 7)
        res_order = self.client.post(
            "/orders",
            headers=self.c1_headers,
            json={
                "customer_name": "Customer One",
                "customer_email": "c1@nexora.ua",
                "delivery_type": "pickup",
                "payment_type": "card",
                "items": [{"product_id": 1, "quantity": 3}],
            },
        )
        self.assertEqual(res_order.status_code, 201)
        order_id = res_order.json()["id"]
        self.assertEqual(self.client.get("/products/1").json()["stock_quantity"], 7)

        # Ідемпотентний запит Created -> Created -> 200 OK, залишок без змін (7)
        res_same_created = self.client.patch(
            f"/orders/{order_id}/status",
            headers=self.admin_headers,
            json={"status": "Created"},
        )
        self.assertEqual(res_same_created.status_code, 200)
        self.assertEqual(res_same_created.json()["status"], "Created")
        self.assertEqual(self.client.get("/products/1").json()["stock_quantity"], 7)

        # Скасування замовлення через PATCH /orders/{id}/status -> залишок відновлюється до 10
        res_cancel = self.client.patch(
            f"/orders/{order_id}/status",
            headers=self.admin_headers,
            json={"status": "Cancelled"},
        )
        self.assertEqual(res_cancel.status_code, 200)
        self.assertEqual(res_cancel.json()["status"], "Cancelled")
        self.assertEqual(self.client.get("/products/1").json()["stock_quantity"], 10)

        # Повторне скасування того ж замовлення через API є ідемпотентним і НЕ збільшує залишок повторно
        res_cancel_again = self.client.patch(
            f"/orders/{order_id}/status",
            headers=self.admin_headers,
            json={"status": "Cancelled"},
        )
        self.assertEqual(res_cancel_again.status_code, 200)
        self.assertEqual(res_cancel_again.json()["status"], "Cancelled")
        self.assertEqual(self.client.get("/products/1").json()["stock_quantity"], 10)

        # Спроба перевести скасоване замовлення у Paid повертає 400
        res_invalid = self.client.patch(
            f"/orders/{order_id}/status",
            headers=self.admin_headers,
            json={"status": "Paid"},
        )
        self.assertEqual(res_invalid.status_code, 400)


if __name__ == "__main__":
    unittest.main()
