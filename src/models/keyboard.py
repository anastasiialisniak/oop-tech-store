from .product import Product


class Keyboard(Product):
    def __init__(
        self,
        product_id: int,
        name: str,
        brand: str,
        price: float,
        stock_quantity: int,
        switch_type: str,
        layout: str
    ):
        super().__init__(
            product_id,
            name,
            brand,
            price,
            stock_quantity
        )

        self.__switch_type = switch_type
        self.__layout = layout

    def get_description(self) -> str:
        return (
            f"Keyboard with {self.__switch_type} switches "
            f"and {self.__layout} layout."
        )