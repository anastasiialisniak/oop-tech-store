from abc import ABC, abstractmethod


class User(ABC):
    def __init__(self, user_id: int, name: str, email: str):
        if user_id <= 0:
            raise ValueError("User ID must be positive.")

        if not name:
            raise ValueError("Name cannot be empty.")

        if "@" not in email:
            raise ValueError("Invalid email address.")

        self.__user_id = user_id
        self.__name = name
        self.__email = email

    def change_email(self, new_email: str) -> None:
        if "@" not in new_email:
            raise ValueError("Invalid email address.")

        self.__email = new_email

    def get_email_domain(self) -> str:
        return self.__email.split("@")[1]

    @abstractmethod
    def get_role(self) -> str:
        pass


class Customer(User):
    def __init__(
        self,
        user_id: int,
        name: str,
        email: str
    ):
        super().__init__(user_id, name, email)
        self.__order_count = 0

    def add_order(self) -> None:
        self.__order_count += 1

    def get_order_count(self) -> int:
        return self.__order_count

    def get_role(self) -> str:
        return "Customer"


class Admin(User):
    def __init__(
        self,
        user_id: int,
        name: str,
        email: str
    ):
        super().__init__(user_id, name, email)

    def get_role(self) -> str:
        return "Admin"

    def can_manage_products(self) -> bool:
        return True


