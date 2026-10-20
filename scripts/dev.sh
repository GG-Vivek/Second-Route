#!/usr/bin/env bash
#
# Start the whole application on a developer machine.
#
# One command: it checks the prerequisites, prepares the database, runs
# the migrations, seeds the catalogue and a development organisation, and
# then starts the API and the frontend. Ctrl-C stops both.
#
# It is safe to run again: the database is only created when it is
# missing, the migrations only move forward, and the seeds are
# idempotent.
#
# Environment:
#   PGHOST          The PostgreSQL host. Default: 127.0.0.1.
#   PGPORT          The PostgreSQL port. Default: 5432.
#   PGDATABASE      The database to use. Default: secondroute.
#   POSTGRES_USER   The superuser to create the roles with. Default: the
#                   current user, which is what Homebrew's PostgreSQL uses.
#   POSTGRES_PASSWORD The password for the application role. Default:
#                   secondroute.
#   APP_PORT        The port the API listens on. Default: 8000.
#   WEB_PORT        The port the frontend listens on. Default: 5173.
#   SKIP_SETUP      Set to 1 to skip the database preparation.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"

: "${PGHOST:=127.0.0.1}"
: "${PGPORT:=5432}"
: "${PGDATABASE:=secondroute}"
: "${POSTGRES_USER:=$(whoami)}"
: "${POSTGRES_PASSWORD:=secondroute}"
: "${APP_PORT:=8000}"
: "${WEB_PORT:=5173}"

API_URL="http://127.0.0.1:${APP_PORT}"
WEB_URL="http://localhost:${WEB_PORT}"

BOLD=$'\033[1m'
DIM=$'\033[2m'
RED=$'\033[31m'
GREEN=$'\033[32m'
RESET=$'\033[0m'

step() { printf '%s==>%s %s\n' "${BOLD}" "${RESET}" "$1"; }
info() { printf '    %s%s%s\n' "${DIM}" "$1" "${RESET}"; }
fail() { printf '%serror:%s %s\n' "${RED}" "${RESET}" "$1" >&2; exit 1; }

# ---------------------------------------------------------------------
# The prerequisites
# ---------------------------------------------------------------------
step "Checking the prerequisites"
for command in uv node npm psql; do
    command -v "$command" >/dev/null 2>&1 || fail "$command is not installed."
done
info "uv $(uv --version 2>/dev/null | awk '{print $2}'), node $(node --version)"

if ! pg_isready -h "$PGHOST" -p "$PGPORT" >/dev/null 2>&1; then
    fail "PostgreSQL is not answering on ${PGHOST}:${PGPORT}.
    Start it, for example:
        brew services start postgresql@16"
fi
info "PostgreSQL is up on ${PGHOST}:${PGPORT}"

# ---------------------------------------------------------------------
# The dependencies
# ---------------------------------------------------------------------
step "Installing the dependencies"
(cd "$BACKEND_DIR" && uv sync --all-extras >/dev/null) || fail "the backend dependencies could not be installed."
[ -d "${FRONTEND_DIR}/node_modules" ] || (cd "$FRONTEND_DIR" && npm install >/dev/null) || fail "the frontend dependencies could not be installed."
info "the backend and the frontend are ready"

# ---------------------------------------------------------------------
# The database
# ---------------------------------------------------------------------
if [ "${SKIP_SETUP:-0}" != "1" ]; then
    step "Preparing the database"
    export PGHOST PGPORT PGDATABASE

    if ! psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${PGDATABASE}'" 2>/dev/null | grep -q 1; then
        info "creating the database ${PGDATABASE}"
        createdb -U "$POSTGRES_USER" -h "$PGHOST" -p "$PGPORT" "$PGDATABASE" || fail "the database could not be created."
    else
        info "the database ${PGDATABASE} is there"
    fi

    # The application must not connect as a superuser: PostgreSQL bypasses
    # row-level security for superusers, which would make the tenant
    # isolation decorative.
    POSTGRES_USER="$POSTGRES_USER" POSTGRES_DB="$PGDATABASE" POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        bash "${REPO_ROOT}/docker/postgres/01-create-app-role.sh" >/dev/null \
        || fail "the database roles could not be created."

    # The application role owns the schema, so the migrations can run.
    psql -U "$POSTGRES_USER" -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" \
        -c "GRANT ALL ON SCHEMA public TO secondroute_app;" >/dev/null 2>&1 || true
    psql -U "$POSTGRES_USER" -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" \
        -c "ALTER SCHEMA public OWNER TO secondroute_app;" >/dev/null 2>&1 || true
    info "the roles are in place"

    step "Running the migrations"
    (cd "$BACKEND_DIR" && DATABASE_URL="postgresql+psycopg2://secondroute_app:${POSTGRES_PASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}" \
        uv run alembic upgrade head >/dev/null) || fail "the migrations failed."
    info "the schema is up to date"
fi

# ---------------------------------------------------------------------
# The configuration
# ---------------------------------------------------------------------
step "Writing the configuration"

APP_DB_URL="postgresql+asyncpg://secondroute_app:${POSTGRES_PASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}"

# The configuration files are only written when they are missing. An
# existing one belongs to the developer, and rewriting it would point
# their own runs at a different database.
if [ ! -f "${BACKEND_DIR}/.env" ]; then
    cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env"
    info "wrote backend/.env"
fi
if [ ! -f "${FRONTEND_DIR}/.env" ]; then
    cp "${FRONTEND_DIR}/.env.example" "${FRONTEND_DIR}/.env"
    info "wrote frontend/.env"
fi

# The servers are started with the address this run is using, whatever
# the files say. An environment variable takes priority over the file, so
# the run always talks to the database it was told to.
export DATABASE_URL="$APP_DB_URL"
export VITE_PROXY_TARGET="$API_URL"
info "the API will use ${PGDATABASE} on ${PGHOST}:${PGPORT}"

# ---------------------------------------------------------------------
# The seeds
# ---------------------------------------------------------------------
step "Seeding"
(cd "$BACKEND_DIR" && uv run python scripts/load_skus.py 2>/dev/null | tail -1) || fail "the catalogue could not be loaded."
(cd "$BACKEND_DIR" && uv run python scripts/seed_dev_org.py 2>/dev/null | grep "org id" ) \
    || fail "the development organisation could not be created."

# ---------------------------------------------------------------------
# The servers
# ---------------------------------------------------------------------
step "Starting the API and the frontend"

API_LOG="$(mktemp -t secondroute-api-XXXXXX.log)"
WEB_LOG="$(mktemp -t secondroute-web-XXXXXX.log)"

cleanup() {
    trap - INT TERM EXIT
    [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null || true
    [ -n "${WEB_PID:-}" ] && kill "$WEB_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

(cd "$BACKEND_DIR" && uv run uvicorn secondroute.api.main:app --host 127.0.0.1 --port "$APP_PORT" >"$API_LOG" 2>&1) &
API_PID=$!

(cd "$FRONTEND_DIR" && npm run dev -- --port "$WEB_PORT" >"$WEB_LOG" 2>&1) &
WEB_PID=$!

wait_for() {
    local url="$1" name="$2" log="$3"
    for _ in $(seq 1 60); do
        if curl -fsS -o /dev/null "$url" 2>/dev/null; then
            return 0
        fi
        sleep 1
    done
    printf '%s%s did not come up. Its log is at %s%s\n' "$RED" "$name" "$log" "$RESET" >&2
    tail -20 "$log" >&2
    return 1
}

wait_for "${API_URL}/health" "the API" "$API_LOG" || exit 1
wait_for "$WEB_URL" "the frontend" "$WEB_LOG" || exit 1

ORG_ID="$(cd "$BACKEND_DIR" && uv run python scripts/seed_dev_org.py 2>/dev/null | awk '/org id/{print $3}')"

printf '\n%s%s is running%s\n' "$GREEN" "SecondRoute" "$RESET"
printf '    the application   %s\n' "$WEB_URL"
printf '    the API           %s/api/v1\n' "$API_URL"
printf '    the health check  %s/health\n' "$API_URL"
printf '    the organisation  %s\n' "${ORG_ID:-unknown}"
printf '\n    Every request has to name the organisation:\n'
printf '        curl -H "X-Org-Id: %s" %s/api/v1/units\n' "${ORG_ID:-<the id>}" "$API_URL"
printf '\n    %sCtrl-C stops both.%s\n\n' "$DIM" "$RESET"

wait
