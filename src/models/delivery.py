from abc import ABC, abstractmethod


class Delivery(ABC):
    def __init__(self, address: str):
        if not address:
            raise ValueError("Address cannot be empty.")

        self.__address = address

    def get_address(self) -> str:
        return self.__address

    @abstractmethod
    def calculate_cost(self) -> float:
        pass

    @abstractmethod
    def estimate_delivery_time(self) -> str:
        pass


class CourierDelivery(Delivery):
    def __init__(self, address: str, distance_km: float):
        super().__init__(address)

        if distance_km <= 0:
            raise ValueError("Distance must be positive.")

        self.__distance_km = distance_km

    def calculate_cost(self) -> float:
        return 80 + self.__distance_km * 15

    def estimate_delivery_time(self) -> str:
        return "1-2 business days"


class PickupDelivery(Delivery):
    def calculate_cost(self) -> float:
        return 0.0

    def estimate_delivery_time(self) -> str:
        return "Ready for pickup today"