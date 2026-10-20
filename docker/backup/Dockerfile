# The backup service (Phase 5 - F5.8).
#
# Takes a pg_dump of the database and hands it to restic, which sends it
# to the configured repository. restic is BSD-2 licensed and pg_dump comes
# with PostgreSQL, so the image needs nothing that is not already in the
# project's approved stack.
FROM alpine:3.20

RUN apk add --no-cache \
    bash \
    ca-certificates \
    curl \
    postgresql16-client \
    restic \
    tzdata

# The scripts are mounted by the stack; the copy here is a fallback for
# running the image on its own.
COPY scripts/ /scripts/

ENV BACKUP_INTERVAL_SECONDS=86400

# The loop runs the backup once at startup and then once a day. A failed
# backup is logged and the loop continues, so a transient failure does not
# stop the next attempt; the absence of a new snapshot is what shows that
# the backups have stopped working.
ENTRYPOINT ["/bin/bash", "-c"]
CMD ["/scripts/backup_loop.sh"]
