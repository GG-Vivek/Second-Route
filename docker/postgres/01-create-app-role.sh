#!/bin/bash
# Create the database roles the application and the backup use.
#
# The application must not connect as a superuser. PostgreSQL bypasses
# row-level security for superusers, and for any role with BYPASSRLS, no
# matter what the policies say. Connecting as one would make the
# tenant-isolation policies decorative: every query would see every
# tenant's rows.
#
# The bootstrap superuser stays as the owner of the database, so that
# migrations and administration still work. The application role is the
# one the service connects as, and it owns the tables the migrations
# create.
#
# There is a third role, for the backups. A backup has to contain every
# row, including other tenants', so it needs BYPASSRLS. It is a member of
# the application role, which is what gives it the privileges on the
# tables the application owns. Without that membership pg_dump cannot
# read the tables at all.
#
# The backup is a full copy of everyone's data. It is protected by the
# restic repository's encryption and by who can reach the repository, not
# by the database's own isolation.

set -euo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_APP_USER:=secondroute_app}"
: "${POSTGRES_APP_PASSWORD:=${POSTGRES_PASSWORD:-changeme}}"
: "${POSTGRES_BACKUP_USER:=${POSTGRES_APP_USER}_backup}"
: "${POSTGRES_BACKUP_PASSWORD:=${POSTGRES_APP_PASSWORD}}"

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 \
    --set app_user="$POSTGRES_APP_USER" \
    --set app_password="$POSTGRES_APP_PASSWORD" \
    --set backup_user="$POSTGRES_BACKUP_USER" \
    --set backup_password="$POSTGRES_BACKUP_PASSWORD" \
    --set db_name="$POSTGRES_DB" <<'SQL'
-- The role the application connects as. NOSUPERUSER and NOBYPASSRLS are
-- the point: they are what make the row-level security policies apply.
SELECT format(
    'CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS '
    'PASSWORD %L',
    :'app_user', :'app_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')
\gexec

-- The role the backups use. BYPASSRLS, because a backup holds every
-- tenant's rows. It is a member of the application role, which gives it
-- the privileges on the tables the application owns.
SELECT format(
    'CREATE ROLE %I LOGIN NOSUPERUSER CREATEDB NOCREATEROLE BYPASSRLS PASSWORD %L',
    :'backup_user', :'backup_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'backup_user')
\gexec

SELECT format('GRANT %I TO %I', :'app_user', :'backup_user')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles
    WHERE rolname = :'backup_user'
      AND pg_has_role(rolname, :'app_user', 'member')
)
\gexec

-- The application role creates the tables, so it needs to be able to work
-- in the public schema.
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'db_name', :'app_user')
\gexec

SELECT format('GRANT USAGE, CREATE ON SCHEMA public TO %I', :'app_user')
\gexec
SQL
