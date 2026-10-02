from abc import ABC, abstractmethod


class Payment(ABC):
    def __init__(self, amount: float):
        if amount <= 0:
            raise ValueError("Payment amount must be positive.")

        self.__amount = amount

    def get_amount(self) -> float:
        return self.__amount

    @abstractmethod
    def process_payment(self) -> str:
        pass

    @abstractmethod
    def refund(self) -> str:
        pass


class CardPayment(Payment):
    def __init__(self, amount: float, card_number: str):
        super().__init__(amount)

        if len(card_number) < 4:
            raise ValueError("Invalid card number.")

        self.__card_number = card_number

    def process_payment(self) -> str:
        return f"Card payment of {self.get_amount():.2f} UAH processed."

    def refund(self) -> str:
        return f"Card payment of {self.get_amount():.2f} UAH refunded."


class CashPayment(Payment):
    def process_payment(self) -> str:
        return f"Cash payment of {self.get_amount():.2f} UAH processed."

    def refund(self) -> str:
        return f"Cash payment of {self.get_amount():.2f} UAH refunded."