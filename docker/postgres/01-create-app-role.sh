#!/bin/bash
# Create the role the application connects as.
#
# The application must not connect as a superuser. PostgreSQL bypasses
# row-level security for superusers, and for any role with BYPASSRLS, no
# matter what the policies say. Connecting as the bootstrap superuser
# would make the tenant-isolation policies decorative: every query would
# see every tenant's rows.
#
# The bootstrap superuser stays as the owner of the database, so that
# migrations and administration still work. The application role is the
# one the service connects as, and it owns the tables it creates - which
# is why the policies are created with FORCE ROW LEVEL SECURITY.

set -euo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_APP_USER:=secondroute_app}"
: "${POSTGRES_APP_PASSWORD:=${POSTGRES_PASSWORD:-changeme}}"

# The role name and password are passed in as psql variables so that they
# are quoted correctly, whatever they contain.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 \
    --set app_user="$POSTGRES_APP_USER" \
    --set app_password="$POSTGRES_APP_PASSWORD" \
    --set db_name="$POSTGRES_DB" <<'SQL'
-- The role the application connects as. NOSUPERUSER and NOBYPASSRLS are
-- the point: they are what make the row-level security policies apply.
SELECT format(
    'CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD %L',
    :'app_user', :'app_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')
\gexec

-- The application role creates and owns its own tables, so it needs to be
-- able to create them in the public schema.
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'db_name', :'app_user')
\gexec

SELECT format('GRANT USAGE, CREATE ON SCHEMA public TO %I', :'app_user')
\gexec
SQL
