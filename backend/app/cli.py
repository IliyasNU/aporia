"""Small maintenance commands. Admin roles are assigned here, never through the API.

python -m app.cli set-role ada@example.com admin
docker compose exec api python -m app.cli set-role ada@example.com admin
"""

import argparse
import sys

from app.db.session import SessionLocal
from app.models import UserRole
from app.services.moderation import set_role


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    role = commands.add_parser("set-role", help="make a user an admin, or a regular user again")
    role.add_argument("email")
    role.add_argument("role", choices=[r.value for r in UserRole])
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        try:
            user = set_role(db, args.email, UserRole(args.role))
        except LookupError as exc:
            print(exc, file=sys.stderr)
            return 1
    print(f"@{user.handle} is now {user.role}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
