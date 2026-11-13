import math

from src.models.delivery import CourierDelivery, Delivery, PickupDelivery
from src.models.payment import CardPayment, CashPayment, Payment


class PaymentDeliveryFactory:
    """Фабрика для створення поліморфних об'єктів оплати (Payment) та доставки (Delivery)."""

    SUPPORTED_DELIVERY_TYPES = {"pickup", "courier", "nova-poshta", "ukrposhta"}
    SUPPORTED_PAYMENT_TYPES = {"card", "cash"}
    DEFAULT_PICKUP_ADDRESS = "Самовивіз із магазину Nexora"
    DEFAULT_COURIER_DISTANCE_KM = 5.0
    DEFAULT_SIMULATED_CARD = "0000111122223333"

    @classmethod
    def validate_delivery_type(cls, delivery_type: str) -> str:
        if not isinstance(delivery_type, str) or not delivery_type.strip():
            raise ValueError("Спосіб доставки не може бути порожнім.")

        normalized = delivery_type.strip().lower()
        if normalized not in cls.SUPPORTED_DELIVERY_TYPES:
            raise ValueError(f"Непідтримуваний спосіб доставки: '{delivery_type}'.")
        return normalized

    @classmethod
    def validate_payment_type(cls, payment_type: str) -> str:
        if not isinstance(payment_type, str) or not payment_type.strip():
            raise ValueError("Спосіб оплати не може бути порожнім.")

        normalized = payment_type.strip().lower()
        if normalized not in cls.SUPPORTED_PAYMENT_TYPES:
            raise ValueError(f"Непідтримуваний спосіб оплати: '{payment_type}'.")
        return normalized

    @classmethod
    def create_delivery(
        cls,
        delivery_type: str,
        address: str | None = None,
        distance_km: float | None = None,
    ) -> Delivery:
        normalized_type = cls.validate_delivery_type(delivery_type)

        if normalized_type == "pickup":
            if address is None:
                resolved_address = cls.DEFAULT_PICKUP_ADDRESS
            elif not isinstance(address, str) or not address.strip():
                raise ValueError("Адреса самовивозу не може бути порожнім рядком.")
            else:
                resolved_address = address.strip()

            return PickupDelivery(resolved_address)

        # Кур'єрська або поштова доставка вимагає непустої адреси
        if not isinstance(address, str) or not address.strip():
            raise ValueError("Адреса доставки не може бути порожньою.")

        if distance_km is None:
            resolved_distance = cls.DEFAULT_COURIER_DISTANCE_KM
        else:
            if (
                isinstance(distance_km, bool)
                or not isinstance(distance_km, (int, float))
                or not math.isfinite(distance_km)
                or distance_km <= 0
            ):
                raise ValueError("Відстань доставки має бути додатним числом.")
            resolved_distance = float(distance_km)

        return CourierDelivery(address.strip(), resolved_distance)

    @classmethod
    def create_payment(
        cls,
        payment_type: str,
        amount: float,
        card_number: str | None = None,
    ) -> Payment:
        normalized_type = cls.validate_payment_type(payment_type)

        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(amount)
            or amount <= 0
        ):
            raise ValueError("Сума оплати має бути додатним числом.")

        if normalized_type == "card":
            if card_number is None:
                resolved_card = cls.DEFAULT_SIMULATED_CARD
            elif not isinstance(card_number, str) or len(card_number.strip()) < 4:
                raise ValueError("Некоректний номер картки.")
            else:
                resolved_card = card_number.strip()

            return CardPayment(float(amount), resolved_card)

        return CashPayment(float(amount))
