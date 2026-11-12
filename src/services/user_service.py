
import sqlite3

from pwdlib import PasswordHash

from src.models.user import Customer
from src.services.database import Database


class UserService:
    def __init__(self):
        self.__database = Database()
        self.__password_hash = PasswordHash.recommended()

    def register_user(
        self,
        name: str,
        email: str,
        password: str
    ) -> Customer:
        name = name.strip()
        email = email.strip().lower()

        if not name:
            raise ValueError("Name cannot be empty.")

        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters.")

        hashed_password = self.__password_hash.hash(password)

        try:
            user_id = self.__database.create_user(
                name,
                email,
                hashed_password
            )
        except sqlite3.IntegrityError:
            raise ValueError(
                "A user with this email already exists."
            )

        return Customer(user_id, name, email)

    def get_user_by_email(self, email: str) -> Customer | None:
        email = email.strip().lower()

        user_data = self.__database.get_user_by_email(email)

        if user_data is None:
            return None

        user_id, name, email, password_hash, role = user_data

        if role != "Customer":
            return None

        return Customer(user_id, name, email)

    def authenticate_user(
        self,
        email: str,
        password: str
    ) -> Customer | None:
        email = email.strip().lower()

        user_data = self.__database.get_user_by_email(email)

        if user_data is None:
            return None

        user_id, name, email, password_hash, role = user_data

        if role != "Customer":
            return None

        if not self.__password_hash.verify(password, password_hash):
            return None

        return Customer(user_id, name, email)
