
import json
import logging
import os
import sqlite3
from pathlib import Path
from contextlib import closing


logger = logging.getLogger("nexora.database")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = (PROJECT_ROOT / "db.sqlite3").resolve()


class DatabaseConfigurationError(RuntimeError, ValueError):
    """Помилка конфігурації шляху до бази даних у тестовому режимі."""


def get_application_mode() -> str:
    env_value = os.getenv("NEXORA_ENV")
    if env_value and env_value.strip().lower() == "test":
        return "test"
    return "production"


def resolve_database_path() -> Path:
    mode = get_application_mode()
    configured = os.getenv("NEXORA_DB_PATH")
    configured_clean = configured.strip() if configured else ""

    if mode == "test":
        if not configured_clean:
            raise DatabaseConfigurationError(
                "NEXORA_DB_PATH must be explicitly configured when NEXORA_ENV=test."
            )
        candidate = Path(configured_clean)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        resolved = candidate.resolve()
        if resolved == DEFAULT_DATABASE_PATH.resolve():
            raise DatabaseConfigurationError(
                "Refusing to use production database (db.sqlite3) when NEXORA_ENV=test."
            )
        return resolved

    if configured_clean:
        candidate = Path(configured_clean)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        return candidate.resolve()
    return DEFAULT_DATABASE_PATH.resolve()


def verify_and_log_database_config() -> tuple[str, Path]:
    mode = get_application_mode()
    resolved_path = resolve_database_path()
    logger.info(
        "Nexora startup: mode=%s, database=%s",
        mode,
        resolved_path,
    )
    return mode, resolved_path


DATABASE_PATH = resolve_database_path()


# Початкові товари магазину (ті самі 8 товарів, що й у веб-інтерфейсі).
# Формат: (id, name, brand, category, price, stock_quantity, image, attributes)
SEED_PRODUCTS = [
    (1, "Mechanical Keyboard", "Logitech", "keyboard", 2500, 10,
     "images/mechanical-keyboard.jpg.jpg",
     {"switch_type": "Red", "layout": "US"}),
    (2, "Gaming Mouse", "Logitech", "mouse", 1500, 20,
     "images/gaming-mouse.jpg.jpg",
     {"dpi": 12000, "connection_type": "Wireless"}),
    (3, "Gaming Headset", "HyperX", "headphones", 3200, 15,
     "images/gaming-headset.jpg.jpg",
     {"wireless": True, "has_microphone": True}),
    (4, "Full HD Webcam", "Logitech", "webcam", 2200, 8,
     "images/full-hd-webcam.jpg.jpg",
     {"resolution": "1920x1080", "frame_rate": 60}),
    (5, "Wireless Keyboard", "Logitech", "keyboard", 1800, 12,
     "images/wireless-keyboard.jpg.jpg",
     {}),
    (6, "Gaming Mouse Pro", "Razer", "mouse", 2800, 7,
     "images/gaming-mouse-pro.jpg.jpg",
     {}),
    (7, "Wireless Headphones", "Sony", "headphones", 4500, 5,
     "images/wireless-headphones.jpg.jpg",
     {}),
    (8, "Streaming Webcam", "AverMedia", "webcam", 3900, 4,
     "images/streaming-webcam.jpg.jpg",
     {}),
]

# Неверифіковані (припущені) характеристики товарів 5–8 з попереднього сіду.
# Зберігаються для ідентифікації та нейтралізації без перезапису існуючої БД.
UNVERIFIED_SEED_ATTRIBUTES = {
    5: {"switch_type": "Membrane", "layout": "US"},
    6: {"dpi": 20000, "connection_type": "Wired"},
    7: {"wireless": True, "has_microphone": False},
    8: {"resolution": "3840x2160", "frame_rate": 30},
}


class Database:
    def __init__(self, database_path=None):
        self.database_path = database_path
        self.initialize()

    def connect(self):
        target_path = getattr(self, "database_path", None)
        if target_path is None:
            target_path = resolve_database_path()
        elif get_application_mode() == "test":
            if Path(target_path).resolve() == DEFAULT_DATABASE_PATH.resolve():
                raise DatabaseConfigurationError(
                    "Refusing to use production database (db.sqlite3) when NEXORA_ENV=test."
                )
        connection = sqlite3.connect(target_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self):
        with closing(self.connect()) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'Customer'
                    )
                """)

                connection.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        brand TEXT NOT NULL,
                        category TEXT NOT NULL,
                        price REAL NOT NULL CHECK (price >= 0),
                        stock_quantity INTEGER NOT NULL
                            CHECK (stock_quantity >= 0),
                        image TEXT,
                        attributes_json TEXT NOT NULL DEFAULT '{}'
                    )
                """)

                connection.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NULL,
                        customer_name TEXT NOT NULL,
                        customer_email TEXT NOT NULL,
                        delivery_type TEXT NOT NULL,
                        delivery_address TEXT NOT NULL,
                        payment_type TEXT NOT NULL,
                        total_amount REAL NOT NULL CHECK (total_amount >= 0),
                        status TEXT NOT NULL DEFAULT 'Created',
                        date TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                            ON DELETE SET NULL
                    )
                """)

                connection.execute("""
                    CREATE TABLE IF NOT EXISTS order_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        product_id INTEGER NOT NULL,
                        product_name TEXT NOT NULL,
                        price REAL NOT NULL CHECK (price >= 0),
                        quantity INTEGER NOT NULL CHECK (quantity > 0),
                        FOREIGN KEY (order_id) REFERENCES orders(id)
                            ON DELETE CASCADE
                    )
                """)

                self.__seed_products(connection)

    def __seed_products(self, connection):
        # Початкові товари додаються лише в порожню таблицю
        count = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        if count > 0:
            return

        connection.executemany(
            """
            INSERT INTO products (
                id, name, brand, category, price,
                stock_quantity, image, attributes_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    product_id, name, brand, category, price,
                    stock, image, json.dumps(attributes)
                )
                for (
                    product_id, name, brand, category, price,
                    stock, image, attributes
                ) in SEED_PRODUCTS
            ]
        )

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: str = "Customer"
    ) -> int:
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (name, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, email, password_hash, role)
                )
                return cursor.lastrowid

    def get_user_by_email(self, email: str):
        with closing(self.connect()) as connection:
            cursor = connection.execute(
                """
                SELECT id, name, email, password_hash, role
                FROM users
                WHERE email = ?
                """,
                (email,)
            )
            return cursor.fetchone()

    def get_user_by_id(self, user_id: int):
        with closing(self.connect()) as connection:
            cursor = connection.execute(
                """
                SELECT id, name, email, password_hash, role
                FROM users
                WHERE id = ?
                """,
                (user_id,)
            )
            return cursor.fetchone()

    def has_admin_user(self) -> bool:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM users WHERE role = 'Admin' LIMIT 1"
            ).fetchone()
            return row is not None

    # ------------------------------------------------------------------
    # Товари
    # ------------------------------------------------------------------

    @staticmethod
    def __row_to_product(row) -> dict:
        (
            product_id, name, brand, category, price,
            stock_quantity, image, attributes_json
        ) = row

        return {
            "id": product_id,
            "name": name,
            "brand": brand,
            "category": category,
            "price": price,
            "stock_quantity": stock_quantity,
            "image": image,
            "attributes": json.loads(attributes_json),
        }

    def get_all_products(self) -> list[dict]:
        with closing(self.connect()) as connection:
            cursor = connection.execute(
                """
                SELECT id, name, brand, category, price,
                       stock_quantity, image, attributes_json
                FROM products
                ORDER BY id
                """
            )
            return [self.__row_to_product(row) for row in cursor.fetchall()]

    def get_product_by_id(self, product_id: int) -> dict | None:
        with closing(self.connect()) as connection:
            cursor = connection.execute(
                """
                SELECT id, name, brand, category, price,
                       stock_quantity, image, attributes_json
                FROM products
                WHERE id = ?
                """,
                (product_id,)
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return self.__row_to_product(row)

    @staticmethod
    def __validate_stock_quantity(stock_quantity: int) -> None:
        if isinstance(stock_quantity, bool) or not isinstance(stock_quantity, int):
            raise ValueError("Stock quantity must be an integer.")

        if stock_quantity < 0:
            raise ValueError("Stock quantity cannot be negative.")

    def create_product(
        self,
        name: str,
        brand: str,
        category: str,
        price: float,
        stock_quantity: int,
        image: str | None = None,
        attributes: dict | None = None
    ) -> int:
        self.__validate_stock_quantity(stock_quantity)
        attributes_json = json.dumps(attributes or {})

        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO products (
                        name, brand, category, price,
                        stock_quantity, image, attributes_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name, brand, category, price,
                        stock_quantity, image, attributes_json
                    )
                )
                return cursor.lastrowid

    def update_product(
        self,
        product_id: int,
        name: str,
        brand: str,
        category: str,
        price: float,
        stock_quantity: int,
        image: str | None = None,
        attributes: dict | None = None,
    ) -> bool:
        self.__validate_stock_quantity(stock_quantity)
        attributes_json = json.dumps(attributes or {})

        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE products
                    SET name = ?,
                        brand = ?,
                        category = ?,
                        price = ?,
                        stock_quantity = ?,
                        image = ?,
                        attributes_json = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        brand,
                        category,
                        price,
                        stock_quantity,
                        image,
                        attributes_json,
                        product_id,
                    ),
                )
                return cursor.rowcount > 0

    def update_product_stock(
        self,
        product_id: int,
        new_stock: int
    ) -> bool:
        self.__validate_stock_quantity(new_stock)

        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE products
                    SET stock_quantity = ?
                    WHERE id = ?
                    """,
                    (new_stock, product_id)
                )
                return cursor.rowcount > 0

    def delete_product(self, product_id: int) -> bool:
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "DELETE FROM products WHERE id = ?",
                    (product_id,)
                )
                return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Замовлення
    # ------------------------------------------------------------------

    @staticmethod
    def __row_to_order(row, items: list[dict]) -> dict:
        (
            order_id,
            user_id,
            customer_name,
            customer_email,
            delivery_type,
            delivery_address,
            payment_type,
            total_amount,
            status,
            date,
        ) = row

        return {
            "id": order_id,
            "user_id": user_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "delivery_type": delivery_type,
            "delivery_address": delivery_address,
            "payment_type": payment_type,
            "total_amount": total_amount,
            "status": status,
            "date": date,
            "items": items,
        }

    @staticmethod
    def __row_to_order_item(row) -> dict:
        item_id, order_id, product_id, product_name, price, quantity = row
        return {
            "id": item_id,
            "order_id": order_id,
            "product_id": product_id,
            "product_name": product_name,
            "price": price,
            "quantity": quantity,
            "subtotal": price * quantity,
        }

    def __fetch_order_items(self, connection, order_id: int) -> list[dict]:
        cursor = connection.execute(
            """
            SELECT id, order_id, product_id, product_name, price, quantity
            FROM order_items
            WHERE order_id = ?
            ORDER BY id
            """,
            (order_id,)
        )
        return [self.__row_to_order_item(row) for row in cursor.fetchall()]

    def create_order_transaction(
        self,
        user_id: int | None,
        customer_name: str,
        customer_email: str,
        delivery_type: str,
        delivery_address: str,
        payment_type: str,
        total_amount: float,
        status: str,
        date: str,
        items: list[dict],
    ) -> int:
        if not items:
            raise ValueError("Замовлення має містити хоча б один товар.")

        with closing(self.connect()) as connection:
            with connection:
                if user_id is not None:
                    user_row = connection.execute(
                        "SELECT id FROM users WHERE id = ?",
                        (user_id,)
                    ).fetchone()
                    if user_row is None:
                        raise ValueError("Користувача не знайдено.")

                for item in items:
                    product_id = item["product_id"]
                    quantity = item["quantity"]
                    self.__validate_stock_quantity(quantity)
                    if quantity <= 0:
                        raise ValueError("Кількість товару має бути додатною.")

                    cursor = connection.execute(
                        """
                        UPDATE products
                        SET stock_quantity = stock_quantity - ?
                        WHERE id = ? AND stock_quantity >= ?
                        """,
                        (quantity, product_id, quantity)
                    )
                    if cursor.rowcount == 0:
                        existing = connection.execute(
                            "SELECT stock_quantity FROM products WHERE id = ?",
                            (product_id,)
                        ).fetchone()
                        if existing is None:
                            raise ValueError(
                                f"Товар з ID {product_id} не знайдено."
                            )
                        raise ValueError("Недостатньо товару на складі.")

                order_cursor = connection.execute(
                    """
                    INSERT INTO orders (
                        user_id, customer_name, customer_email,
                        delivery_type, delivery_address, payment_type,
                        total_amount, status, date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        customer_name,
                        customer_email,
                        delivery_type,
                        delivery_address,
                        payment_type,
                        total_amount,
                        status,
                        date,
                    )
                )
                order_id = order_cursor.lastrowid

                for item in items:
                    connection.execute(
                        """
                        INSERT INTO order_items (
                            order_id, product_id, product_name, price, quantity
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            order_id,
                            item["product_id"],
                            item["product_name"],
                            item["price"],
                            item["quantity"],
                        )
                    )

                return order_id

    def get_order_by_id(self, order_id: int) -> dict | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                """
                SELECT id, user_id, customer_name, customer_email,
                       delivery_type, delivery_address, payment_type,
                       total_amount, status, date
                FROM orders
                WHERE id = ?
                """,
                (order_id,)
            ).fetchone()

            if row is None:
                return None

            items = self.__fetch_order_items(connection, order_id)
            return self.__row_to_order(row, items)

    def get_orders_by_user_id(self, user_id: int) -> list[dict]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, customer_name, customer_email,
                       delivery_type, delivery_address, payment_type,
                       total_amount, status, date
                FROM orders
                WHERE user_id = ?
                ORDER BY id
                """,
                (user_id,)
            ).fetchall()

            return [
                self.__row_to_order(
                    row,
                    self.__fetch_order_items(connection, row[0])
                )
                for row in rows
            ]

    def get_all_orders(self) -> list[dict]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, customer_name, customer_email,
                       delivery_type, delivery_address, payment_type,
                       total_amount, status, date
                FROM orders
                ORDER BY id
                """
            ).fetchall()

            return [
                self.__row_to_order(
                    row,
                    self.__fetch_order_items(connection, row[0])
                )
                for row in rows
            ]

    def update_order_status(self, order_id: int, new_status: str) -> bool:
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE orders
                    SET status = ?
                    WHERE id = ?
                    """,
                    (new_status, order_id)
                )
                return cursor.rowcount > 0

    def cancel_order_transaction(self, order_id: int) -> bool:
        with closing(self.connect()) as connection:
            with connection:
                row = connection.execute(
                    "SELECT status FROM orders WHERE id = ?",
                    (order_id,)
                ).fetchone()
                if row is None:
                    return False

                current_status = row[0]
                if current_status == "Cancelled":
                    return True

                if current_status not in ("Created", "Paid"):
                    raise ValueError("Order cannot be cancelled.")

                items = connection.execute(
                    """
                    SELECT product_id, quantity
                    FROM order_items
                    WHERE order_id = ?
                    ORDER BY id
                    """,
                    (order_id,)
                ).fetchall()

                for product_id, quantity in items:
                    self.__validate_stock_quantity(quantity)
                    if quantity <= 0:
                        raise ValueError("Кількість товару має бути додатною.")

                    connection.execute(
                        """
                        UPDATE products
                        SET stock_quantity = stock_quantity + ?
                        WHERE id = ?
                        """,
                        (quantity, product_id)
                    )

                cursor = connection.execute(
                    """
                    UPDATE orders
                    SET status = 'Cancelled'
                    WHERE id = ? AND status IN ('Created', 'Paid')
                    """,
                    (order_id,)
                )
                if cursor.rowcount == 0:
                    raise ValueError("Order cannot be cancelled.")

                return True
