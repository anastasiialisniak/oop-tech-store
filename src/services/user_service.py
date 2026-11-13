import sqlite3

from pwdlib import PasswordHash

from src.models.user import Admin, Customer, User
from src.services.database import Database


class UserService:
    def __init__(self, database: Database | None = None):
        self.__database = database if database is not None else Database()
        self.__password_hash = PasswordHash.recommended()

    @staticmethod
    def __row_to_user(user_data) -> Customer | Admin | None:
        if user_data is None:
            return None

        user_id, name, email, _password_hash, role = user_data

        if role == "Customer":
            return Customer(user_id, name, email)

        if role == "Admin":
            return Admin(user_id, name, email)

        return None

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

    def has_admin_user(self) -> bool:
        return self.__database.has_admin_user()

    def create_admin_user(
        self,
        name: str,
        email: str,
        password: str,
    ) -> Admin:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Name cannot be empty.")

        if not isinstance(email, str) or not email.strip():
            raise ValueError("Invalid email address.")

        name = name.strip()
        email = email.strip().lower()
        local_part, separator, domain_part = email.partition("@")
        if (
            not separator
            or not local_part
            or "." not in domain_part
            or domain_part.startswith(".")
            or domain_part.endswith(".")
        ):
            raise ValueError("Invalid email address.")

        if not isinstance(password, str) or len(password) < 8:
            raise ValueError("Password must contain at least 8 characters.")

        if self.__database.get_user_by_email(email) is not None:
            raise ValueError(
                "A user with this email already exists. Existing accounts cannot be promoted."
            )

        hashed_password = self.__password_hash.hash(password)

        try:
            user_id = self.__database.create_user(
                name,
                email,
                hashed_password,
                role="Admin",
            )
        except sqlite3.IntegrityError:
            raise ValueError(
                "A user with this email already exists. Existing accounts cannot be promoted."
            )

        return Admin(user_id, name, email)

    def bootstrap_admin(
        self,
        name: str,
        email: str,
        password: str,
        allow_additional: bool = False,
    ) -> Admin:
        if not allow_additional and self.has_admin_user():
            raise ValueError(
                "An Admin account already exists. Bootstrap is only allowed when no Admin exists."
            )

        return self.create_admin_user(name=name, email=email, password=password)

    def get_user_by_email(self, email: str) -> User | None:
        if not isinstance(email, str) or not email.strip():
            return None

        email = email.strip().lower()
        user_data = self.__database.get_user_by_email(email)
        return self.__row_to_user(user_data)

    def get_user_by_id(self, user_id: int) -> User | None:
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
            return None

        user_data = self.__database.get_user_by_id(user_id)
        return self.__row_to_user(user_data)

    def authenticate_user(
        self,
        email: str,
        password: str
    ) -> User | None:
        if not isinstance(email, str) or not isinstance(password, str):
            return None

        email = email.strip().lower()
        user_data = self.__database.get_user_by_email(email)

        if user_data is None:
            return None

        _user_id, _name, _email, password_hash, _role = user_data

        if not self.__password_hash.verify(password, password_hash):
            return None

        return self.__row_to_user(user_data)
