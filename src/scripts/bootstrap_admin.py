"""Secure administrator provisioning CLI for Nexora.

Supports:
- One-time initial Admin bootstrap (default)
- Creating additional Admin accounts (`--allow-additional` or via `src.scripts.create_admin`)

Usage (interactive prompt):
    python -m src.scripts.create_admin
    # or:
    python -m src.scripts.bootstrap_admin --allow-additional

In test mode:
    $env:NEXORA_ENV="test"
    $env:NEXORA_DB_PATH="db.test.sqlite3"
    python -m src.scripts.create_admin
"""

import argparse
import getpass
import os
import sys

from src.models.user import Admin
from src.services.database import (
    Database,
    DatabaseConfigurationError,
    verify_and_log_database_config,
)
from src.services.user_service import UserService


def run_bootstrap(
    database: Database | None = None,
    name: str | None = None,
    email: str | None = None,
    password: str | None = None,
    interactive: bool = True,
    allow_additional: bool = False,
) -> Admin:
    if database is None:
        verify_and_log_database_config()
        database = Database()

    service = UserService(database=database)

    if not allow_additional and service.has_admin_user():
        raise ValueError(
            "An Admin account already exists in the target database. "
            "One-time bootstrap refused. To create an additional Admin account "
            "with a different email, run: python -m src.scripts.create_admin "
            "(or pass --allow-additional)."
        )

    resolved_name = (
        name
        if name is not None
        else os.environ.get("NEXORA_ADMIN_NAME", "").strip()
    )
    resolved_email = (
        email
        if email is not None
        else os.environ.get("NEXORA_ADMIN_EMAIL", "").strip()
    )
    resolved_password = (
        password
        if password is not None
        else os.environ.get("NEXORA_ADMIN_PASSWORD")
    )

    if interactive:
        if not resolved_name:
            resolved_name = input("Admin name (Ім'я адміністратора): ").strip()
        if not resolved_email:
            resolved_email = input("Admin email (Електронна пошта адміністратора): ").strip()
        if not resolved_password:
            print(
                "Примітка: з міркувань безпеки введення пароля приховане "
                "(символи НЕ відображаються на екрані під час набору). "
                "Введіть пароль і натисніть Enter."
            )
            first_pass = getpass.getpass(
                "Admin password (Пароль, мінімум 8 символів — введення приховане): "
            )
            confirm_pass = getpass.getpass(
                "Confirm admin password (Підтвердіть пароль — введення приховане): "
            )
            if first_pass != confirm_pass:
                raise ValueError("Passwords do not match.")
            resolved_password = first_pass

    if not resolved_name or not resolved_email or not resolved_password:
        raise ValueError(
            "Admin credentials were not provided. Set NEXORA_ADMIN_NAME, "
            "NEXORA_ADMIN_EMAIL, and NEXORA_ADMIN_PASSWORD or run interactively."
        )

    return service.bootstrap_admin(
        name=resolved_name,
        email=resolved_email,
        password=resolved_password,
        allow_additional=allow_additional,
    )


def format_bootstrap_success_message(admin: Admin) -> str:
    return (
        f"[Nexora Bootstrap] Administrator account created successfully "
        f"(id={admin.get_user_id()}, name='{admin.get_name()}', "
        f"email='{admin.get_email()}', role={admin.get_role()}). "
        f"You can now sign in via the 'Вхід' tab on the website."
    )


def main(argv: list[str] | None = None, default_allow_additional: bool = False) -> int:
    parser = argparse.ArgumentParser(
        description="Provision a Nexora Administrator (Admin) account."
    )
    parser.add_argument(
        "--allow-additional",
        action="store_true",
        default=default_allow_additional,
        help="Allow creating an additional Admin account with a new email even if an Admin already exists.",
    )
    args = parser.parse_args(argv if argv is not None else [])

    try:
        admin = run_bootstrap(
            interactive=sys.stdin.isatty(),
            allow_additional=args.allow_additional,
        )
    except (DatabaseConfigurationError, ValueError) as exc:
        print(f"[Nexora Bootstrap Error] {exc}", file=sys.stderr)
        return 1

    print(format_bootstrap_success_message(admin))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
