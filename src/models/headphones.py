from .product import Product


class Headphones(Product):
    def __init__(
        self,
        product_id: int,
        name: str,
        brand: str,
        price: float,
        stock_quantity: int,
        wireless: bool,
        has_microphone: bool
    ):
        super().__init__(
            product_id,
            name,
            brand,
            price,
            stock_quantity
        )

        self.__wireless = wireless
        self.__has_microphone = has_microphone

    def get_description(self) -> str:
        connection = "Wireless" if self.__wireless else "Wired"
        microphone = "with microphone" if self.__has_microphone else "without microphone"

        return f"Headphones: {connection}, {microphone}."