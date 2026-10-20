#!/usr/bin/env python3
"""Compare the row counts of two databases, table by table.

A restore is only faithful if the restored database holds the same rows as
the one it was taken from. This compares the two and exits non-zero when
they differ, so a drill can fail on a mismatch rather than on a human
noticing.

The comparison is by table name, and a table that is present in one
database but not the other is a mismatch too.

Usage:
    row_counts.py --source URL --target URL
    row_counts.py --source URL            # print the source's counts
"""

from __future__ import annotations

import argparse
import sys
from urllib.parse import urlparse, urlunparse

import psycopg2
import psycopg2.extras


def normalise_url(url: str) -> str:
    """Return the URL in a form psycopg2 understands.

    The application uses an async driver in its connection URL. The
    PostgreSQL client libraries do not understand the driver suffix.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme
    for async_driver in ("postgresql+asyncpg", "postgresql+psycopg2", "postgres+asyncpg"):
        if scheme == async_driver:
            scheme = "postgresql"
            break
    return urlunparse(parsed._replace(scheme=scheme))


def table_counts(url: str) -> dict[str, int]:
    """Return the row count of every user table in the database."""
    counts: dict[str, int] = {}
    with psycopg2.connect(normalise_url(url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
                """
            )
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                # The table name comes from pg_catalog, not from user
                # input, but it is quoted anyway so that a table with an
                # unusual name cannot break the query.
                cursor.execute(f'SELECT count(*) FROM "{table}"')
                counts[table] = int(cursor.fetchone()[0])
    return counts


def compare(source: dict[str, int], target: dict[str, int]) -> list[str]:
    """Return a description of every difference between the two counts."""
    problems: list[str] = []
    for table in sorted(set(source) | set(target)):
        in_source = table in source
        in_target = table in target
        if in_source and not in_target:
            problems.append(f"{table}: missing from the target (source has {source[table]})")
        elif in_target and not in_source:
            problems.append(f"{table}: only in the target ({target[table]} rows)")
        elif source[table] != target[table]:
            problems.append(
                f"{table}: source has {source[table]}, target has {target[table]}"
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="URL of the original database.")
    parser.add_argument(
        "--target",
        help="URL of the restored database. Without it, the source's counts are printed.",
    )
    args = parser.parse_args()

    try:
        source = table_counts(args.source)
    except psycopg2.Error as error:
        print(f"ERROR: could not read the source database: {error}", file=sys.stderr)
        return 1

    if not args.target:
        for table, count in source.items():
            print(f"{table}\t{count}")
        return 0

    try:
        target = table_counts(args.target)
    except psycopg2.Error as error:
        print(f"ERROR: could not read the target database: {error}", file=sys.stderr)
        return 1

    problems = compare(source, target)
    if problems:
        print("ERROR: the restored database does not match the original:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    total = sum(source.values())
    print(f"OK: {len(source)} tables match, {total} rows in total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
