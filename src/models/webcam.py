from .product import Product


class Webcam(Product):
    def __init__(
        self,
        product_id: int,
        name: str,
        brand: str,
        price: float,
        stock_quantity: int,
        resolution: str,
        frame_rate: int
    ):
        super().__init__(
            product_id,
            name,
            brand,
            price,
            stock_quantity
        )

        self.__resolution = resolution
        self.__frame_rate = frame_rate

    def get_description(self) -> str:
        return (
            f"Webcam with {self.__resolution} resolution "
            f"and {self.__frame_rate} FPS."
        )