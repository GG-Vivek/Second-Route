# Restoring from a backup

Phase 5 - F5.8.

A backup that has never been restored is a hope, not a backup. This runbook
is the drill: it takes a backup, restores it into a fresh database, and
checks that the restored database holds the same rows as the original and
that the application runs against it.

The drill is automated. Run it and it does all of that.

---

## What is backed up

| Data | Backed up | How |
|---|---|---|
| The PostgreSQL database | Yes | `pg_dump` in the custom format, stored with restic |
| The frontend build | No | Rebuilt from the repository |
| Redis | No | Sessions and caches; losing it costs a re-login |
| Object storage (photos) | No | Not yet in use; see "Not covered" below |

The database holds everything that matters: the units, the inspections, the
photos' metadata, the decisions, the audit log, the outcomes and the
overrides.

## Where the backups live

The restic repository is configured by `RESTIC_REPOSITORY`. It must be
somewhere other than the database's own machine. The free options that
work with restic are:

- **Cloudflare R2** - `s3:https://<account-id>.r2.cloudflarestorage.com/secondroute`
- **A second host over SSH** - `sftp:backup@backup.example.com:/var/backups/secondroute`
- **A local directory** - only for a drill. A repository on the same disk
  as the database does not survive the failure it is there for.

`RESTIC_PASSWORD` unlocks the repository. **Losing it loses the backups.**
Keep it in the same place as the other secrets, and keep a copy somewhere
the VM cannot reach.

---

## The two database roles

The staging stack uses two roles, and the difference between them is not
cosmetic.

| Role | Attributes | Used for |
|---|---|---|
| `secondroute_app` | `NOSUPERUSER NOBYPASSRLS` | The application |
| `secondroute_app_backup` | `BYPASSRLS`, member of `secondroute_app` | The backups |

**The application must not have `BYPASSRLS`.** PostgreSQL bypasses
row-level security for a role with that attribute, so an application that
had it would see every tenant's rows and the isolation policies would be
decorative.

**The backup role must have `BYPASSRLS`, and must be a member of the
application role.** A backup holds every tenant's data, so it has to read
every row; and `pg_dump` refuses outright to dump a table whose rows the
policies would filter:

```
pg_dump: error: query failed: ERROR:  query would be affected by
row-level security policy for table "audit_log"
```

The membership is what gives the backup role the privileges on the tables
the application owns. The `BYPASSRLS` attribute is not inherited
upwards, so the application role does not gain it.

**The backup is a full copy of everyone's data.** It is protected by the
restic repository's encryption and by who can reach the repository, not by
the database's own isolation.

---

## The drill

On the VM, with the stack running:

```bash
cd /opt/secondroute
docker compose --env-file .env.staging \
    -f docker-compose.yml -f docker-compose.staging.yml exec -T backup \
    /scripts/verify_restore.sh
```

The drill:

1. creates a fresh, empty database,
2. takes a backup of the live database,
3. restores the newest snapshot into the fresh database,
4. compares the row counts of every table, and
5. starts the application against the restored database and checks that it
   reports the database as reachable.

It prints `DRILL PASSED` when every step succeeded, and exits non-zero
otherwise. The restored database is dropped at the end. Set
`KEEP_DRILL_DB=1` to leave it in place and look at it.

### Running it against a copy rather than the live database

The drill backs up and restores the database named by `DATABASE_URL`. To
run it against a copy, point it at one:

```bash
DATABASE_URL=postgresql://secondroute_app:...@postgres:5432/secondroute_copy \
    /scripts/verify_restore.sh
```

### The same drill, on a developer machine

The drill needs a real PostgreSQL, `pg_dump` and restic. It runs anywhere
those exist:

```bash
createdb secondroute_drill
export DATABASE_URL=postgresql://secondroute_app:password@localhost:5432/secondroute_drill
export BACKUP_DATABASE_URL=postgresql://secondroute_app_backup:password@localhost:5432/secondroute_drill
export RESTIC_REPOSITORY=/tmp/secondroute-drill-repo
export RESTIC_PASSWORD=drill-only-password
restic init
./scripts/verify_restore.sh
```

`BACKUP_DATABASE_URL` is the role that takes the backup. Leaving it unset
makes the drill fail, because `pg_dump` cannot read through the
tenant-isolation policies. That failure is the point: a deployment that
backs up with the application's role cannot take a backup at all.

The test suite runs the same drill as
`backend/tests/phase5/test_backup_restore.py`. It skips when PostgreSQL,
`pg_dump` or restic are not available.

---

## Restoring by hand

When a restore is needed rather than tested, the steps the drill takes are
the steps to take.

### 1. Find the snapshot

```bash
export RESTIC_REPOSITORY=...
export RESTIC_PASSWORD=...
restic snapshots --tag secondroute-database
```

Pick the snapshot by its time. The most recent one is the default.

### 2. Restore into a fresh database

```bash
createdb secondroute_restored
DATABASE_URL=postgresql://secondroute_app:...@postgres:5432/secondroute_restored \
    /scripts/restore.sh
```

`restore.sh` fetches the snapshot, finds the dump inside it and restores it
with `pg_restore --exit-on-error`, so a restore that hits a problem stops
rather than leaving a half-restored database.

To restore a particular snapshot, set `SNAPSHOT_ID`.

### 3. Check it

```bash
python3 scripts/row_counts.py \
    --source postgresql://secondroute_app:...@postgres:5432/secondroute \
    --target postgresql://secondroute_app:...@postgres:5432/secondroute_restored
```

It prints `OK: <n> tables match, <n> rows in total`, or lists every
difference.

### 4. Point the application at it

Change `DATABASE_URL` in `.env.staging` to the restored database and
restart the backend:

```bash
docker compose --env-file .env.staging \
    -f docker-compose.yml -f docker-compose.staging.yml up -d backend
```

The application runs the migrations at startup, so the restored database
is brought to the current schema version.

### 5. Check the application

```bash
curl -fsS https://$DOMAIN/health
```

`"database":"ok"` means the application is talking to the restored
database.

---

## What to do when the drill fails

| The drill says | What it means | What to do |
|---|---|---|
| `the restored database does not reproduce the original` | The row counts differ | Do not use the restore. Find out what was lost before trusting the rest of it. |
| `the schema version differs` | The backup is from a different version of the application | Apply the migrations to the restored database before using it. |
| `the application did not become healthy` | The restore completed but the application cannot use it | Read the application log the drill prints. The database is restored; the problem is above it. |
| `the repository holds no snapshot` | There are no backups | The backups have been failing. Check the backup service's logs. |
| `pg_restore failed` | The dump is damaged | Try an older snapshot. |
| `the repository failed its integrity check` | The repository is damaged | Do not trust the backups in it. Copy what can be read and rebuild the repository. |

---

## The backup schedule

The backup service runs `scripts/backup.sh` once at startup and then every
`BACKUP_INTERVAL_SECONDS` (a day by default). Each run:

1. writes a `pg_dump` in the custom format,
2. stores it in the restic repository, tagged `secondroute-database`,
3. prunes the repository, keeping seven daily, four weekly and six monthly
   snapshots,
4. checks the repository's integrity.

A failed backup is logged and the loop continues, so one transient failure
does not stop the next attempt. **Check that the snapshots are actually
appearing.** The drill is the check: run it on a schedule, not only when
something has gone wrong.

---

## Not covered

- **Redis.** Sessions and caches only. A restore does not bring it back.
- **Object storage.** The photos themselves are not in the database yet.
  When they are, they need backing up too, and the drill has to check the
  object count as well as the row count.
- **The frontend build.** Rebuilt from the repository. A checkout of the
  commit that was deployed is the record of what was running.
- **Secrets.** The database's contents are backed up; the secrets that
  protect them are not. `RESTIC_PASSWORD` and `SECRET_KEY` need their own
  backup, somewhere the VM cannot reach.
