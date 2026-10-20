"""
Create the database role the application connects as.

The application must not connect as a superuser. PostgreSQL bypasses
row-level security for superusers, and for any role with BYPASSRLS, no
matter what the policies say. Connecting as the bootstrap superuser
would make the tenant-isolation policies decorative: every query would
see every tenant's rows.

This script is the CI equivalent of ``docker/postgres/01-create-app-role.sh``.
It connects with the bootstrap superuser - the one the PostgreSQL service
creates - and creates an ordinary role for the application to use.

Usage::

    python scripts/create_app_role.py \\
        --admin-url postgresql://test:test@localhost:5432/secondroute_test \\
        --app-user secondroute_app \\
        --app-password test
"""

from __future__ import annotations

import argparse
import sys

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--admin-url",
        required=True,
        help="Connection URL for the bootstrap superuser.",
    )
    parser.add_argument(
        "--app-user",
        default="secondroute_app",
        help="Name of the role the application connects as.",
    )
    parser.add_argument(
        "--app-password",
        default="test",
        help="Password for the application role.",
    )
    parser.add_argument(
        "--database",
        default="secondroute_test",
        help="Name of the database the application role needs access to.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    connection = psycopg2.connect(args.admin_url)
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (args.app_user,))
            if cursor.fetchone() is None:
                # NOSUPERUSER and NOBYPASSRLS are the point: they are what
                # make the row-level security policies apply.
                cursor.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                        "NOBYPASSRLS PASSWORD %s"
                    ).format(sql.Identifier(args.app_user)),
                    (args.app_password,),
                )
                print(f"Created role {args.app_user}.")

            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(args.database), sql.Identifier(args.app_user)
                )
            )
            # The application role creates and owns its own tables, so it
            # needs to be able to create them in the public schema.
            cursor.execute(
                sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(
                    sql.Identifier(args.app_user)
                )
            )
    finally:
        connection.close()

    print(f"The application role {args.app_user} is ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
