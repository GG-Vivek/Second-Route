#!/usr/bin/env bash
# Restore the database from a restic snapshot.
#
# The snapshot is fetched into a temporary directory and the dump it holds
# is restored into the target database with pg_restore.
#
# Environment:
#   DATABASE_URL            Target connection URL. Defaults to the libpq
#                            variables.
#   RESTIC_REPOSITORY       Where the backups live. Required.
#   RESTIC_PASSWORD         The repository password. Or RESTIC_PASSWORD_FILE.
#   SNAPSHOT_ID             Which snapshot to restore. Default: the most
#                            recent one tagged secondroute-database.
#   RESTORE_DIR             Where to unpack the snapshot. Default: a
#                            temporary directory that is cleaned up afterwards.
#
# The target database is expected to exist and to be empty. Use
# --clean to drop the objects it holds first.
#
# Exit status is 0 when the restore completed.

LOG_TAG="restore"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_cmd restic pg_restore
require_restic_repository

CLEAN=0
TARGET_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --clean)
            CLEAN=1
            shift
            ;;
        *)
            log "ERROR: unknown argument '$1'"
            exit 2
            ;;
    esac
done

: "${SNAPSHOT_ID:=}"
if [[ -z "${SNAPSHOT_ID}" ]]; then
    log "finding the most recent snapshot"
    # The newest snapshot is chosen here rather than by asking restic for
    # the latest one, because that filter does not apply to restic's JSON
    # output: every snapshot comes back, and the first is the oldest.
    SNAPSHOT_ID="$(restic snapshots --tag secondroute-database --json 2>/dev/null \
        | python3 -c '
import json, sys

snapshots = json.load(sys.stdin)
if not snapshots:
    print("")
else:
    newest = max(snapshots, key=lambda snapshot: snapshot["time"])
    print(newest["short_id"])
')"
    if [[ -z "${SNAPSHOT_ID}" ]]; then
        log "ERROR: the repository holds no snapshot tagged secondroute-database."
        exit 1
    fi
fi
log "restoring snapshot ${SNAPSHOT_ID}"

RESTORE_DIR="$(mktemp -d -t secondroute-restore-XXXXXX)"
cleanup() {
    rm -rf "${RESTORE_DIR}"
}
trap cleanup EXIT

if ! restic restore "${SNAPSHOT_ID}" --target "${RESTORE_DIR}" >&2; then
    log "ERROR: restic could not fetch the snapshot."
    exit 1
fi

DUMP_FILE="$(find "${RESTORE_DIR}" -name '*.dump' -type f | sort | tail -1)"
if [[ -z "${DUMP_FILE}" ]]; then
    log "ERROR: the snapshot holds no dump file."
    exit 1
fi
log "restoring ${DUMP_FILE} into the target database"

if [[ "$CLEAN" == "1" ]]; then
    log "dropping the existing objects in the target database"
    TARGET_ARGS+=(--clean --if-exists)
fi

# The array may be empty, and bash 3.2 treats an empty array expansion
# under "set -u" as an error, so it is expanded defensively.
TARGET_ARGS_SAFE=(${TARGET_ARGS[@]+"${TARGET_ARGS[@]}"})

# --exit-on-error stops the restore at the first problem, so a broken
# restore is reported rather than quietly leaving a partial database.
if ! pg_restore --exit-on-error --no-owner --no-privileges ${TARGET_ARGS_SAFE[@]+"${TARGET_ARGS_SAFE[@]}"} \
    --dbname "$(db_url)" "${DUMP_FILE}"; then
    log "ERROR: pg_restore failed. The target database is not a faithful copy."
    exit 1
fi

# The role that restored the tables owns them, because it created them.
# The application has to own them as well, or it cannot migrate them or
# use them. The restore role is a member of the application role, which is
# what lets it hand them over.
if [[ -n "${RESTORE_OWNER_ROLE:-}" ]]; then
    log "handing the restored tables to ${RESTORE_OWNER_ROLE}"
    if ! psql --dbname "$(db_url)" --set ON_ERROR_STOP=1 \
        --set owner_role="${RESTORE_OWNER_ROLE}" <<'SQL' >/dev/null
REASSIGN OWNED BY SESSION_USER TO :"owner_role";
SQL
    then
        log "ERROR: could not hand the restored tables to ${RESTORE_OWNER_ROLE}."
        log "The application will not be able to use the restored database."
        exit 1
    fi
fi

log "restore complete"
