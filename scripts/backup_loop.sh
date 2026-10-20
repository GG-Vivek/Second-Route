#!/usr/bin/env bash
# The backup loop (Phase 5 - F5.8).
#
# Runs a backup, then sleeps, then runs another. A failure is logged and
# the loop carries on: the absence of a new snapshot is what shows that
# the backups have stopped working, so stopping the loop on the first
# failure would only hide the problem.
#
# The interval comes from BACKUP_INTERVAL_SECONDS and defaults to a day.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${BACKUP_INTERVAL_SECONDS:=86400}"

log() {
    printf '%s [%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "backup-loop" "$*" >&2
}

log "starting the backup loop, every ${BACKUP_INTERVAL_SECONDS} seconds"

while true; do
    if "${SCRIPT_DIR}/backup.sh"; then
        log "backup succeeded"
    else
        log "ERROR: the backup failed. The next attempt is in ${BACKUP_INTERVAL_SECONDS} seconds."
    fi
    sleep "${BACKUP_INTERVAL_SECONDS}"
done
