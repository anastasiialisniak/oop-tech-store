from datetime import datetime, timezone

from src.models.order import Order
from src.models.product import Product
from src.services.database import Database
from src.services.payment_delivery_factory import PaymentDeliveryFactory
from src.services.product_service import ProductService


class OrderService:
    """Сервіс управління замовленнями з використанням доменних ООП-моделей та транзакцій SQLite."""

    ALLOWED_STATUSES = {
        "Created",
        "Paid",
        "Shipped",
        "Completed",
        "Cancelled",
    }

    def __init__(
        self,
        database: Database | None = None,
        product_service: ProductService | None = None,
    ):
        self.__db = database if database is not None else Database()
        self.__product_service = (
            product_service
            if product_service is not None
            else ProductService(self.__db)
        )

    @staticmethod
    def __validate_customer_data(customer_name: str, customer_email: str) -> tuple[str, str]:
        if not isinstance(customer_name, str) or not customer_name.strip():
            raise ValueError("Ім'я покупця не може бути порожнім.")

        if (
            not isinstance(customer_email, str)
            or not customer_email.strip()
            or "@" not in customer_email.strip()
        ):
            raise ValueError("Некоректна електронна пошта покупця.")

        return customer_name.strip(), customer_email.strip().lower()

    @staticmethod
    def __validate_raw_items(items: list[dict]) -> list[tuple[int, int]]:
        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Замовлення має містити хоча б один товар.")

        validated: list[tuple[int, int]] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Елемент замовлення має бути словником.")

            product_id = item.get("product_id", item.get("productId"))
            quantity = item.get("quantity")

            if (
                isinstance(product_id, bool)
                or not isinstance(product_id, int)
                or product_id <= 0
            ):
                raise ValueError("Некоректний ідентифікатор товару.")

            if (
                isinstance(quantity, bool)
                or not isinstance(quantity, int)
                or quantity <= 0
            ):
                raise ValueError("Кількість товару має бути додатним цілим числом.")

            validated.append((product_id, quantity))

        return validated

    def __build_domain_order_for_status(self, record: dict) -> Order:
        delivery = PaymentDeliveryFactory.create_delivery(
            delivery_type=record["delivery_type"],
            address=record["delivery_address"],
        )
        payment_amount = max(float(record["total_amount"]), 0.01)
        payment = PaymentDeliveryFactory.create_payment(
            payment_type=record["payment_type"],
            amount=payment_amount,
        )
        domain_order = Order(
            order_id=record["id"],
            payment=payment,
            delivery=delivery,
        )
        domain_order.change_status(record["status"])
        return domain_order

    def __enrich_order_record(
        self,
        record: dict,
        payment_message: str | None = None,
    ) -> dict:
        items_total = sum(
            float(item["price"]) * int(item["quantity"])
            for item in record.get("items", [])
        )
        total_amount = float(record["total_amount"])
        delivery_cost = max(round(total_amount - items_total, 2), 0.0)

        domain_order = self.__build_domain_order_for_status(record)

        enriched = {
            **record,
            "items_total": items_total,
            "delivery_cost": delivery_cost,
            "can_be_cancelled": domain_order.can_be_cancelled(),
        }
        if payment_message is not None:
            enriched["payment_message"] = payment_message

        return enriched

    def create_order(
        self,
        customer_name: str,
        customer_email: str,
        delivery_type: str,
        payment_type: str,
        items: list[dict],
        delivery_address: str | None = None,
        distance_km: float | None = None,
        card_number: str | None = None,
        user_id: int | None = None,
        date: str | None = None,
    ) -> dict:
        if user_id is not None:
            if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
                raise ValueError("Некоректний ідентифікатор користувача.")

        clean_name, clean_email = self.__validate_customer_data(
            customer_name,
            customer_email,
        )
        validated_items = self.__validate_raw_items(items)

        normalized_delivery_type = PaymentDeliveryFactory.validate_delivery_type(
            delivery_type
        )
        normalized_payment_type = PaymentDeliveryFactory.validate_payment_type(
            payment_type
        )

        # 1. Створюємо об'єкт Delivery через фабрику та обчислюємо вартість поліморфно
        delivery = PaymentDeliveryFactory.create_delivery(
            delivery_type=normalized_delivery_type,
            address=delivery_address,
            distance_km=distance_km,
        )
        delivery_cost = delivery.calculate_cost()

        # 2. Завантажуємо актуальні доменні об'єкти Product з бази даних
        domain_products_by_id: dict[int, Product] = {}
        for product_id, _qty in validated_items:
            if product_id not in domain_products_by_id:
                product = self.__product_service.get_domain_product(product_id)
                if product is None:
                    raise ValueError(f"Товар з ID {product_id} не знайдено.")
                domain_products_by_id[product_id] = product

        # 3. Попередній підрахунок суми для ініціалізації Payment
        preliminary_items_total = sum(
            domain_products_by_id[product_id].calculate_final_price() * qty
            for product_id, qty in validated_items
        )
        expected_total = preliminary_items_total + delivery_cost

        # 4. Створюємо об'єкт Payment через фабрику
        payment = PaymentDeliveryFactory.create_payment(
            payment_type=normalized_payment_type,
            amount=expected_total,
            card_number=card_number,
        )

        # 5. Створюємо доменний об'єкт Order та додаємо позиції через Order.add_item()
        domain_order = Order(
            order_id=1,
            payment=payment,
            delivery=delivery,
        )

        snapshot_items: list[dict] = []
        for product_id, quantity in validated_items:
            product = domain_products_by_id[product_id]
            # Order.add_item() перевіряє залишок, викликає product.reduce_stock(quantity)
            # і додає OrderItem(product, quantity)
            domain_order.add_item(product, quantity)
            snapshot_items.append(
                {
                    "product_id": product.get_product_id(),
                    "product_name": product.get_name(),
                    "price": product.calculate_final_price(),
                    "quantity": quantity,
                }
            )

        # 6. Розраховуємо фінальну суму через Order.calculate_total() та проводимо оплату
        total_amount = domain_order.calculate_total()
        payment_message = payment.process_payment()

        order_date = (
            date.strip()
            if isinstance(date, str) and date.strip()
            else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        )

        # 7. Зберігаємо замовлення, позиції та списання залишків в ОДНІЙ транзакції SQLite
        order_id = self.__db.create_order_transaction(
            user_id=user_id,
            customer_name=clean_name,
            customer_email=clean_email,
            delivery_type=normalized_delivery_type,
            delivery_address=delivery.get_address(),
            payment_type=normalized_payment_type,
            total_amount=total_amount,
            status=domain_order.get_status(),
            date=order_date,
            items=snapshot_items,
        )

        created_record = self.__db.get_order_by_id(order_id)
        return self.__enrich_order_record(
            created_record,
            payment_message=payment_message,
        )

    def get_order_by_id(self, order_id: int) -> dict | None:
        if isinstance(order_id, bool) or not isinstance(order_id, int) or order_id <= 0:
            return None

        record = self.__db.get_order_by_id(order_id)
        if record is None:
            return None

        return self.__enrich_order_record(record)

    def get_orders_by_user(self, user_id: int) -> list[dict]:
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
            return []

        records = self.__db.get_orders_by_user_id(user_id)
        return [self.__enrich_order_record(r) for r in records]

    get_customer_orders = get_orders_by_user

    def get_all_orders(self) -> list[dict]:
        records = self.__db.get_all_orders()
        return [self.__enrich_order_record(r) for r in records]

    def update_order_status(self, order_id: int, new_status: str) -> dict | None:
        if isinstance(order_id, bool) or not isinstance(order_id, int) or order_id <= 0:
            return None

        if not isinstance(new_status, str) or not new_status.strip():
            raise ValueError("Статус замовлення не може бути порожнім.")

        target_status = new_status.strip()
        record = self.__db.get_order_by_id(order_id)
        if record is None:
            return None

        domain_order = self.__build_domain_order_for_status(record)
        current_status = domain_order.get_status()

        # Перевірка допустимості статусу через доменний метод Order.change_status()
        if target_status not in self.ALLOWED_STATUSES:
            domain_order.change_status(target_status)

        # Ідемпотентна обробка повторного встановлення поточного статусу
        if target_status == current_status:
            return self.__enrich_order_record(record)

        if current_status in {"Completed", "Cancelled"}:
            raise ValueError(
                f"Неможливо змінити статус замовлення у стані '{current_status}'."
            )

        if target_status == "Cancelled":
            # Використовує Order.can_be_cancelled() та Order.cancel()
            domain_order.cancel()

            # Валідація повернення залишків через доменну модель Product.increase_stock()
            # для товарів, які все ще існують у каталозі
            domain_products_by_id: dict[int, Product] = {}
            for item in record.get("items", []):
                product_id = item["product_id"]
                quantity = item["quantity"]
                if product_id not in domain_products_by_id:
                    domain_product = self.__product_service.get_domain_product(product_id)
                    if domain_product is not None:
                        domain_products_by_id[product_id] = domain_product
                if product_id in domain_products_by_id:
                    domain_products_by_id[product_id].increase_stock(quantity)

            # Атомарне повернення товарів на склад та оновлення статусу в одній транзакції SQLite
            self.__db.cancel_order_transaction(order_id)
            updated_record = self.__db.get_order_by_id(order_id)
            return self.__enrich_order_record(updated_record)
        elif target_status == "Completed":
            # Використовує Order.mark_as_completed() (дозволено лише зі стану 'Shipped')
            domain_order.mark_as_completed()
        elif target_status == "Paid":
            if current_status != "Created":
                raise ValueError(
                    "Статус 'Paid' можна встановити лише для замовлення зі статусом 'Created'."
                )
            domain_order.change_status("Paid")
        elif target_status == "Shipped":
            if current_status not in {"Created", "Paid"}:
                raise ValueError(
                    "Відправити можна лише замовлення зі статусом 'Created' або 'Paid'."
                )
            domain_order.change_status("Shipped")
        else:
            if current_status != "Created":
                raise ValueError(
                    "Неможливо повернути замовлення до статусу 'Created'."
                )
            domain_order.change_status(target_status)

        self.__db.update_order_status(order_id, domain_order.get_status())
        updated_record = self.__db.get_order_by_id(order_id)
        return self.__enrich_order_record(updated_record)
