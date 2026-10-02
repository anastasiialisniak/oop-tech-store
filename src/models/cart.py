from .product import Product


class CartItem:
    def __init__(self, product: Product, quantity: int):
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        if not product.is_available():
            raise ValueError("Product is not available.")

        self.__product = product
        self.__quantity = quantity

    def increase_quantity(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive.")

        self.__quantity += amount

    def decrease_quantity(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive.")

        if amount > self.__quantity:
            raise ValueError("Cannot decrease quantity below zero.")

        self.__quantity -= amount

    def calculate_subtotal(self) -> float:
        return self.__product.calculate_final_price() * self.__quantity

    def is_empty(self) -> bool:
        return self.__quantity == 0


class Cart:
    def __init__(self):
        self.__items: list[CartItem] = []

    def add_product(self, product: Product, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        if not product.is_available():
            raise ValueError("Product is not available.")

        item = CartItem(product, quantity)
        self.__items.append(item)

    def remove_product(self, product: Product) -> None:
        for item in self.__items:
            if item._CartItem__product is product:
                self.__items.remove(item)
                return

        raise ValueError("Product is not in the cart.")

    def calculate_total(self) -> float:
        return sum(item.calculate_subtotal() for item in self.__items)

    def clear(self) -> None:
        self.__items.clear()

    def is_empty(self) -> bool:
        return len(self.__items) == 0

    def get_item_count(self) -> int:
        return len(self.__items)