from .product import Product
from .payment import Payment
from .delivery import Delivery


class OrderItem:
    def __init__(self, product: Product, quantity: int):
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        self.__product = product
        self.__quantity = quantity

    def calculate_subtotal(self) -> float:
        return self.__product.calculate_final_price() * self.__quantity

    def get_quantity(self) -> int:
        return self.__quantity


class Order:
    def __init__(
        self,
        order_id: int,
        payment: Payment,
        delivery: Delivery
    ):
        if order_id <= 0:
            raise ValueError("Order ID must be positive.")

        self.__order_id = order_id
        self.__items: list[OrderItem] = []
        self.__payment = payment
        self.__delivery = delivery
        self.__status = "Created"

    def add_item(self, product: Product, quantity: int) -> None:
        item = OrderItem(product, quantity)
        self.__items.append(item)

    def calculate_total(self) -> float:
        products_total = sum(
            item.calculate_subtotal()
            for item in self.__items
        )

        return products_total + self.__delivery.calculate_cost()

    def change_status(self, new_status: str) -> None:
        allowed_statuses = {
            "Created",
            "Paid",
            "Shipped",
            "Completed",
            "Cancelled"
        }

        if new_status not in allowed_statuses:
            raise ValueError("Invalid order status.")

        self.__status = new_status

    def can_be_cancelled(self) -> bool:
        return self.__status in {"Created", "Paid"}

    def cancel(self) -> None:
        if not self.can_be_cancelled():
            raise ValueError("Order cannot be cancelled.")

        self.__status = "Cancelled"

    def mark_as_completed(self) -> None:
        if self.__status != "Shipped":
            raise ValueError(
                "Only shipped orders can be completed."
            )

        self.__status = "Completed"

    def get_status(self) -> str:
        return self.__status