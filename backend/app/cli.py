"""Maintenance commands for people with server access (never exposed through the API).

    python -m app.cli set-role ada@example.com admin       # or: user
    python -m app.cli delete-article <article-id>          # permanent removal (SEC-07)
    python -m app.cli delete-comment <comment-id>
    python -m app.cli delete-user ada@example.com          # account and everything it owns
    python -m app.cli delete-subscriber fan@example.com    # forget an address (SEC-06)
    python -m app.cli seed-demo                            # demo data; refused in production

In Docker: docker compose exec api python -m app.cli <command> ...
"""

import argparse
import sys
import uuid

from app.db.session import SessionLocal
from app.models import UserRole
from app.services import demo, maintenance
from app.services.moderation import set_role


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    role = commands.add_parser("set-role", help="make a user an admin, or a regular user again")
    role.add_argument("email")
    role.add_argument("role", choices=[r.value for r in UserRole])
    commands.add_parser("delete-article", help="delete an article permanently").add_argument(
        "article_id", type=uuid.UUID
    )
    commands.add_parser("delete-comment", help="delete a comment permanently").add_argument(
        "comment_id", type=uuid.UUID
    )
    commands.add_parser("delete-user", help="delete an account and its content").add_argument(
        "email"
    )
    commands.add_parser(
        "delete-subscriber", help="remove an email address from all newsletters"
    ).add_argument("email")
    commands.add_parser("seed-demo", help="create clearly labelled demo data (not in production)")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        try:
            if args.command == "set-role":
                user = set_role(db, args.email, UserRole(args.role))
                print(f"@{user.handle} is now {user.role}")
            elif args.command == "delete-article":
                print(f"Deleted article “{maintenance.delete_article(db, args.article_id)}”")
            elif args.command == "delete-comment":
                maintenance.delete_comment(db, args.comment_id)
                print("Deleted the comment")
            elif args.command == "delete-user":
                print(f"Deleted @{maintenance.delete_user(db, args.email)} and their content")
            elif args.command == "delete-subscriber":
                count = maintenance.delete_subscriber(db, args.email)
                print(f"Removed the address from {count} subscription(s)")
            elif args.command == "seed-demo":
                handles = demo.seed_demo(db)
                if handles:
                    print(f"Created demo accounts {', '.join(handles)}")
                    print(f"Sign in as demo_reader@example.com / {demo.DEMO_PASSWORD}")
                else:
                    print("Demo data already exists")
        except (LookupError, RuntimeError) as exc:
            print(exc, file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
