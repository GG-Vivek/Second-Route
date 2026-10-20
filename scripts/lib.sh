#!/usr/bin/env bash
# Shared helpers for the backup and restore scripts.
#
# Sourced, not executed.

set -euo pipefail

# Print a timestamped message to stderr, so that stdout stays usable for
# data (row counts, identifiers) that a caller might want to capture.
log() {
    printf '%s [%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "${LOG_TAG:-backup}" "$*" >&2
}

# Fail with a message if a command is not installed.
require_cmd() {
    for cmd in "$@"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            log "ERROR: '$cmd' is not installed. Install it and try again."
            exit 1
        fi
    done
}

# Remove the async driver suffix from a connection URL.
#
# The application uses an async driver in its URL; the PostgreSQL command
# line tools do not understand the driver suffix.
strip_driver() {
    local url="$1"
    url="${url/postgresql+asyncpg:/postgresql:}"
    url="${url/postgresql+psycopg2:/postgresql:}"
    printf '%s' "$url"
}

# Print a connection URL with the asynchronous driver named.
#
# The application talks to the database with asyncpg. A URL that names no
# driver is resolved by SQLAlchemy to psycopg, which is not installed, so
# the application would fail to start with a bare "No module named
# 'psycopg'". The driver is named here, so that a URL written the natural
# way still starts the application.
async_url() {
    local url="$1"
    case "${url}" in
        postgresql://*) url="postgresql+asyncpg://${url#postgresql://}" ;;
        postgresql+psycopg2://*) url="postgresql+asyncpg://${url#postgresql+psycopg2://}" ;;
    esac
    printf '%s' "$url"
}

# Print the connection URL the backup and restore tools use.
#
# BACKUP_DATABASE_URL, when it is set, is used instead of DATABASE_URL. The
# backup needs a role that can read every row: the application's role is
# held to the tenant-isolation policies, and pg_dump refuses to dump a
# table whose rows the policies would filter.
db_url() {
    local url="${BACKUP_DATABASE_URL:-${DATABASE_URL:-}}"
    if [[ -z "$url" ]]; then
        # Fall back to the standard libpq environment variables.
        url="postgresql://${PGUSER:-postgres}@${PGHOST:-localhost}:${PGPORT:-5432}/${PGDATABASE:-secondroute}"
    fi
    strip_driver "$url"
}

# Print the connection URL the application uses.
#
# This is the role that is held to the tenant-isolation policies, so it is
# the right one for reading the data and for running the application
# against a restored copy of it.
app_db_url() {
    local url="${DATABASE_URL:-}"
    if [[ -z "$url" ]]; then
        url="postgresql://${PGUSER:-postgres}@${PGHOST:-localhost}:${PGPORT:-5432}/${PGDATABASE:-secondroute}"
    fi
    strip_driver "$url"
}

# Print the host, port, database and user of the connection URL, one per
# line. Used to build the fresh database the drill restores into.
#
# With no argument it describes the backup URL, which is the one the
# backup and restore tools use. A URL can be given instead, which is what
# the drill does for the role that creates and drops databases: that role
# is deliberately not the backup role, which is not allowed to create
# databases.
db_parts() {
    local url
    url="${1:-}"
    if [[ -z "$url" ]]; then
        url="$(db_url)"
    fi
    python3 - "$url" <<'PY'
import sys
from urllib.parse import urlparse

parsed = urlparse(sys.argv[1])
print(parsed.hostname or "localhost")
print(parsed.port or 5432)
print((parsed.path or "/secondroute").lstrip("/"))
print(parsed.username or "postgres")
PY
}

# Print the role name of a connection URL.
db_user() {
    local url
    url="$(strip_driver "$1")"
    python3 - "$url" <<'PY'
import sys
from urllib.parse import urlparse

print(urlparse(sys.argv[1]).username or "postgres")
PY
}

# Fail unless the restic repository is configured and reachable.
require_restic_repository() {
    if [[ -z "${RESTIC_REPOSITORY:-}" ]]; then
        log "ERROR: RESTIC_REPOSITORY is not set. The backup has nowhere to go."
        exit 1
    fi
    if [[ -z "${RESTIC_PASSWORD:-}" && -z "${RESTIC_PASSWORD_FILE:-}" ]]; then
        log "ERROR: set RESTIC_PASSWORD or RESTIC_PASSWORD_FILE. The repository must be unlockable."
        exit 1
    fi
    require_cmd restic
    if ! restic snapshots --no-lock >/dev/null 2>&1; then
        log "ERROR: the restic repository at ${RESTIC_REPOSITORY} cannot be opened."
        log "Check the credentials, and run 'restic init' if the repository is new."
        exit 1
    fi
}
