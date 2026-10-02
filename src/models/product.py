from abc import ABC, abstractmethod


class Product(ABC):
    def __init__(
        self,
        product_id: int,
        name: str,
        brand: str,
        price: float,
        stock_quantity: int
    ):
        if price < 0:
            raise ValueError("Price cannot be negative.")

        if stock_quantity < 0:
            raise ValueError("Stock quantity cannot be negative.")

        self.__product_id = product_id
        self.__name = name
        self.__brand = brand
        self.__price = price
        self.__stock_quantity = stock_quantity

    def is_available(self) -> bool:
        return self.__stock_quantity > 0

    def reduce_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        if quantity > self.__stock_quantity:
            raise ValueError("Not enough products in stock.")

        self.__stock_quantity -= quantity

    def increase_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        self.__stock_quantity += quantity

    def apply_discount(self, percent: float) -> None:
        if not 0 <= percent <= 100:
            raise ValueError("Discount must be between 0 and 100.")

        self.__price *= (1 - percent / 100)

    def calculate_final_price(self) -> float:
        return self.__price

    @abstractmethod
    def get_description(self) -> str:
        pass