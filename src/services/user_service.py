
from src.models.user import Customer


class UserService:
    def __init__(self):
        self.__users: dict[str, Customer] = {}

    def register_user(
        self,
        user_id: int,
        name: str,
        email: str,
    ) -> Customer:
        email = email.strip().lower()
        name = name.strip()

        if not name:
            raise ValueError("Name cannot be empty.")

        if email in self.__users:
            raise ValueError("A user with this email already exists.")

        user = Customer(user_id, name, email)
        self.__users[email] = user

        return user

    def get_user_by_email(self, email: str) -> Customer | None:
        email = email.strip().lower()
        return self.__users.get(email)
