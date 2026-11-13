"""Secure CLI command to create an additional (or initial) Admin account in Nexora.

Usage (interactive prompt):
    python -m src.scripts.create_admin

In test mode:
    $env:NEXORA_ENV="test"
    $env:NEXORA_DB_PATH="db.test.sqlite3"
    python -m src.scripts.create_admin
"""

import sys

from src.scripts.bootstrap_admin import main as bootstrap_main


def main(argv: list[str] | None = None) -> int:
    return bootstrap_main(argv=argv, default_allow_additional=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
