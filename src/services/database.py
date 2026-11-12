
import sqlite3
from pathlib import Path
from contextlib import closing


DATABASE_PATH = Path(__file__).resolve().parents[2] / "db.sqlite3"


class Database:
    def __init__(self):
        self.initialize()

    def connect(self):
        return sqlite3.connect(DATABASE_PATH)

    def initialize(self):
        with closing(self.connect()) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'Customer'
                    )
                """)

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: str = "Customer"
    ) -> int:
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (name, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, email, password_hash, role)
                )
                return cursor.lastrowid

    def get_user_by_email(self, email: str):
        with closing(self.connect()) as connection:
            cursor = connection.execute(
                """
                SELECT id, name, email, password_hash, role
                FROM users
                WHERE email = ?
                """,
                (email,)
            )
            return cursor.fetchone()
