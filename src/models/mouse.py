from .product import Product


class Mouse(Product):
    def __init__(
        self,
        product_id: int,
        name: str,
        brand: str,
        price: float,
        stock_quantity: int,
        dpi: int,
        connection_type: str
    ):
        super().__init__(
            product_id,
            name,
            brand,
            price,
            stock_quantity
        )

        self.__dpi = dpi
        self.__connection_type = connection_type

    def get_description(self) -> str:
        return (
            f"Mouse with {self.__dpi} DPI "
            f"and {self.__connection_type} connection."
        )