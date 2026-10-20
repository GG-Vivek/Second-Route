#!/usr/bin/env bash
# The restore drill.
#
# Proves that a backup can actually be restored: take a backup, restore it
# into a fresh, empty database, and check that the restored database holds
# the same rows as the original.
#
# This is the acceptance test for F5.8 - "a restore into a fresh
# environment reproduces row counts and passes the smoke test". It runs
# against a real PostgreSQL, because a restore that has not been performed
# is not a restore.
#
# Environment:
#   DATABASE_URL       The database to back up and restore from. Required.
#   RESTIC_REPOSITORY  Where the backups live. Required.
#   RESTIC_PASSWORD    The repository password. Or RESTIC_PASSWORD_FILE.
#   DRILL_DATABASE     Name of the fresh database to restore into. Default:
#                      secondroute_restore_drill. It is dropped afterwards.
#   DRILL_ADMIN_URL    A connection URL for a role that may create and drop
#                      databases. Defaults to the source URL's user, which
#                      must be allowed to.
#   KEEP_DRILL_DB      Set to 1 to leave the restored database in place, so
#                      that it can be inspected.
#
# Exit status is 0 when the drill passed.

LOG_TAG="drill"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_cmd psql createdb dropdb pg_dump restic python3
require_restic_repository

: "${DATABASE_URL:?DATABASE_URL is required: the drill needs a database to back up}"
: "${DRILL_DATABASE:=secondroute_restore_drill}"
: "${KEEP_DRILL_DB:=0}"

# Two roles, and the difference between them matters.
#
# The application role is held to the tenant-isolation policies, so it is
# the one that reads the data and that the application runs as. The backup
# role can read every row, because a backup holds every tenant's data and
# pg_dump refuses to dump a table whose rows the policies would filter.
APP_URL_RAW="${DATABASE_URL}"
APP_URL="$(app_db_url)"
BACKUP_URL="$(db_url)"

# The role that creates and drops the fresh database.
#
# It is not the backup role: that role exists to read every row and to
# nothing else, and giving it the right to create databases would give it
# the right to read every tenant's data in a database of its own choosing.
# The application's role creates the database unless an administrator URL
# says otherwise.
ADMIN_URL_RAW="${DRILL_ADMIN_URL:-${DATABASE_URL}}"
ADMIN_URL="$(strip_driver "${ADMIN_URL_RAW}")"

# The backend's virtual environment, found relative to the repository
# rather than to the working directory, so the drill runs from anywhere.
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
if [[ ! -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
    log "ERROR: no backend virtual environment at ${BACKEND_DIR}/.venv"
    log "Create it first, or point PYTHON at an interpreter that has the app's dependencies."
    exit 1
fi
PYTHON="${BACKEND_DIR}/.venv/bin/python"

# The parts of the connection, one per line. Read with a loop rather
# than mapfile, which bash 3.2 does not have.
DB_PARTS=()
while IFS= read -r _line; do
    DB_PARTS+=("$_line")
done <<<"$(db_parts "$ADMIN_URL")"
PGHOST="${DB_PARTS[0]}"
PGPORT="${DB_PARTS[1]}"
PGDATABASE="${DB_PARTS[2]}"
PGUSER="${DB_PARTS[3]}"
# The host has to be exported as well: createdb and dropdb are given the
# maintenance database by name, so they resolve the connection through the
# libpq variables. Without the host they fall back to the Unix socket,
# which is not where the server is listening when it is reached over TCP -
# which is the case for a database in a container.
export PGHOST
export PGPORT
export PGDATABASE
export PGUSER

# The source database, for the log line. It is the application URL's
# database, which is not the administrator URL's database when the two
# differ.
SOURCE_DB="$(db_parts "$APP_URL" | sed -n '3p')"

log "source database: ${SOURCE_DB} on ${PGHOST}:${PGPORT}"
log "drill database:  ${DRILL_DATABASE}"

cleanup() {
    if [[ "${KEEP_DRILL_DB}" != "1" ]]; then
        log "dropping the drill database ${DRILL_DATABASE}"
        dropdb --if-exists --force --maintenance-db="$PGDATABASE" "${DRILL_DATABASE}" >/dev/null 2>&1 || true
    else
        log "leaving the drill database ${DRILL_DATABASE} in place"
    fi
}
trap cleanup EXIT

# ---------------------------------------------------------------------
# 1. A fresh, empty database to restore into.
# ---------------------------------------------------------------------
log "creating the fresh database ${DRILL_DATABASE}"
dropdb --if-exists --force --maintenance-db="$PGDATABASE" "${DRILL_DATABASE}" >/dev/null 2>&1 || true
if ! createdb --maintenance-db="$PGDATABASE" "${DRILL_DATABASE}"; then
    log "ERROR: could not create the drill database. The role needs CREATEDB."
    exit 1
fi

DRILL_URL="${APP_URL%/*}/${DRILL_DATABASE}"
# The same database, addressed with the original URL, for the application.
# The driver is named explicitly, because the application talks to the
# database asynchronously and a URL without a driver is resolved to a
# driver that is not installed.
DRILL_URL_RAW="$(async_url "${APP_URL_RAW%/*}/${DRILL_DATABASE}")"
# The backup role, pointed at the drill database, for the restore.
DRILL_BACKUP_URL="${BACKUP_URL%/*}/${DRILL_DATABASE}"

# ---------------------------------------------------------------------
# 2. Take the backup.
# ---------------------------------------------------------------------
log "taking a backup"
if ! "${SCRIPT_DIR}/backup.sh"; then
    log "ERROR: the backup failed."
    exit 1
fi

# ---------------------------------------------------------------------
# 3. Restore into the fresh database.
# ---------------------------------------------------------------------
log "restoring into the fresh database"
if ! BACKUP_DATABASE_URL="${DRILL_BACKUP_URL}" DATABASE_URL="${DRILL_URL}" \
    RESTORE_OWNER_ROLE="${RESTORE_OWNER_ROLE:-$(db_user "${DATABASE_URL}")}" \
    "${SCRIPT_DIR}/restore.sh"; then
    log "ERROR: the restore failed."
    exit 1
fi

# ---------------------------------------------------------------------
# 4. The row counts must match.
# ---------------------------------------------------------------------
# The counts are read with the backup role, not the application's. The
# application's role is held to the tenant-isolation policies, and with no
# organisation in context it reads *no rows at all* from the tables that
# carry tenant data - the units, the decisions, the outcomes, the audit
# log. Comparing the counts the application role sees would compare zero
# with zero and pass even if the restore had lost every unit.
log "comparing the row counts"
if ! "${PYTHON}" "${SCRIPT_DIR}/row_counts.py" --source "${BACKUP_URL}" \
    --target "${DRILL_BACKUP_URL}"; then
    log "ERROR: the restored database does not reproduce the original."
    exit 1
fi

# ---------------------------------------------------------------------
# 5. The smoke test: the restored database must be usable.
# ---------------------------------------------------------------------
log "running the smoke test against the restored database"
# The schema version has to be the same, so the restored database is at the
# same revision as the original.
SOURCE_VERSION="$(psql --dbname "$APP_URL" --tuples-only --no-align \
    --command "SELECT version_num FROM alembic_version" 2>/dev/null | tr -d '[:space:]')"
DRILL_VERSION="$(psql --dbname "$DRILL_URL" --tuples-only --no-align \
    --command "SELECT version_num FROM alembic_version" 2>/dev/null | tr -d '[:space:]')"
if [[ -z "$DRILL_VERSION" ]]; then
    log "ERROR: the restored database has no alembic version. It is not a usable database."
    exit 1
fi
if [[ "$SOURCE_VERSION" != "$DRILL_VERSION" ]]; then
    log "ERROR: schema version differs: source ${SOURCE_VERSION}, restored ${DRILL_VERSION}"
    exit 1
fi
log "schema version matches: ${DRILL_VERSION}"

# The application must be able to start against the restored database and
# answer its health check. This runs the real startup path, migrations
# included.
log "starting the application against the restored database"
LOG_FILE="$(mktemp -t secondroute-drill-app-XXXXXX.log)"
DATABASE_URL="${DRILL_URL_RAW}" \
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" \
SECRET_KEY="${SECRET_KEY:-drill-secret-key-that-is-long-enough}" \
ENVIRONMENT=test \
PYTHONPATH="${BACKEND_DIR}/src" \
timeout 90 "${PYTHON}" -m uvicorn secondroute.api.main:app --host 127.0.0.1 --port 8099 \
    >"${LOG_FILE}" 2>&1 &
APP_PID=$!

HEALTH_OK=0
for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8099/health >/dev/null 2>&1; then
        HEALTH_OK=1
        break
    fi
    sleep 2
done

if [[ "$HEALTH_OK" != "1" ]]; then
    log "ERROR: the application did not become healthy against the restored database."
    log "--- application log ---"
    cat "${LOG_FILE}" >&2
    kill "$APP_PID" >/dev/null 2>&1 || true
    exit 1
fi

HEALTH_BODY="$(curl -fsS http://127.0.0.1:8099/health)"
log "health check: ${HEALTH_BODY}"

# The database check is the one that matters here: Redis is not part of
# the backup, and the health endpoint reports "degraded" when it is down.
if ! printf '%s' "${HEALTH_BODY}" | grep -q '"database":"ok"'; then
    log "ERROR: the application cannot reach the restored database."
    exit 1
fi

kill "$APP_PID" >/dev/null 2>&1 || true
wait "$APP_PID" 2>/dev/null || true

log "DRILL PASSED: the backup restored into a fresh database, the row counts match, and the application runs against it."
