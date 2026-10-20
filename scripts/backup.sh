#!/usr/bin/env bash
# Take one backup of the database and store it in the restic repository.
#
# The dump is written to a staging directory first and then handed to
# restic. The dump and the restic repository are deliberately separate:
# the repository is expected to live on a different machine, or with a
# different provider, from the database it holds a copy of.
#
# Environment:
#   DATABASE_URL            Connection URL. Defaults to the libpq variables.
#   RESTIC_REPOSITORY       Where the backups live. Required.
#   RESTIC_PASSWORD         The repository password. Or RESTIC_PASSWORD_FILE.
#   BACKUP_DIR              Staging directory for the dump. Default: a
#                            temporary directory that is cleaned up afterwards.
#   RETENTION               restic forget arguments. Default keeps seven
#                            daily, four weekly and six monthly snapshots.
#   SKIP_PRUNE              Set to 1 to skip the prune step, which is the
#                            slow part. Useful for a quick manual backup.
#
# Exit status is 0 when a snapshot was created and the repository is
# healthy afterwards.

LOG_TAG="backup"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_cmd pg_dump restic
require_restic_repository

: "${BACKUP_DIR:=$(mktemp -d -t secondroute-backup-XXXXXX)}"
: "${RETENTION:=--keep-daily 7 --keep-weekly 4 --keep-monthly 6}"
: "${SKIP_PRUNE:=0}"

CLEANUP_DIR=0
if [[ -z "${BACKUP_DIR:-}" || ! -d "${BACKUP_DIR}" ]]; then
    BACKUP_DIR="$(mktemp -d -t secondroute-backup-XXXXXX)"
    CLEANUP_DIR=1
fi

cleanup() {
    if [[ "$CLEANUP_DIR" == "1" && -d "${BACKUP_DIR}" ]]; then
        rm -rf "${BACKUP_DIR}"
    fi
}
trap cleanup EXIT

mkdir -p "${BACKUP_DIR}"

STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
DUMP_FILE="${BACKUP_DIR}/secondroute-${STAMP}.dump"

log "dumping the database to ${DUMP_FILE}"
# The custom format is compressed and can be restored in parallel, which
# matters for a database of any size.
if ! pg_dump --format=custom --file="${DUMP_FILE}" "$(db_url)"; then
    log "ERROR: pg_dump failed. No backup was taken."
    exit 1
fi

DUMP_SIZE="$(wc -c <"${DUMP_FILE}" | tr -d ' ')"
log "dump is ${DUMP_SIZE} bytes"

log "storing the dump in ${RESTIC_REPOSITORY}"
# The dump is stored from inside the staging directory, so the snapshot
# holds the dump at its root rather than at the path the temporary
# directory happened to have.
SNAPSHOT_OUTPUT="$(cd "${BACKUP_DIR}" && restic backup --tag secondroute-database --tag "dump-${STAMP}" \
    --host "$(hostname -s 2>/dev/null || echo unknown)" \
    . 2>&1)" || {
    log "ERROR: restic backup failed:"
    printf '%s\n' "${SNAPSHOT_OUTPUT}" >&2
    exit 1
}
printf '%s\n' "${SNAPSHOT_OUTPUT}" >&2

SNAPSHOT_ID="$(printf '%s\n' "${SNAPSHOT_OUTPUT}" | sed -n 's/.*snapshot \([0-9a-f]*\) saved.*/\1/p' | head -1)"
if [[ -z "${SNAPSHOT_ID}" ]]; then
    # Some restic versions word the summary differently, so the snapshot is
    # looked up by its tag instead.
    SNAPSHOT_ID="$(restic snapshots --tag "dump-${STAMP}" --json 2>/dev/null \
        | python3 -c '
import json, sys

snapshots = json.load(sys.stdin)
if not snapshots:
    print("")
else:
    newest = max(snapshots, key=lambda snapshot: snapshot["time"])
    print(newest["short_id"])
')"
fi
log "snapshot ${SNAPSHOT_ID:-unknown} created"

if [[ "${SKIP_PRUNE}" != "1" ]]; then
    log "pruning the repository (${RETENTION})"
    # shellcheck disable=SC2086
    restic forget ${RETENTION} --tag secondroute-database --prune >&2 || {
        log "WARNING: the prune step failed. The backup itself is fine."
    }
fi

log "checking the repository"
restic check >&2 || {
    log "ERROR: the repository failed its integrity check. Do not trust these backups."
    exit 1
}

log "backup complete: ${SNAPSHOT_ID:-unknown}"
