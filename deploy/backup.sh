#!/bin/sh
# Backup SQLite DB + storage. Cron diário: 0 2 * * * /path/to/backup.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sync2meet}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

DB="${SYNC2MEET_DB:-$ROOT/backend/sync2meet.db}"
STORAGE="${SYNC2MEET_STORAGE:-$ROOT/backend/storage}"

if [ -f "$DB" ]; then
  sqlite3 "$DB" ".backup '$BACKUP_DIR/sync2meet-$STAMP.db'"
fi
if [ -d "$STORAGE" ]; then
  tar -czf "$BACKUP_DIR/storage-$STAMP.tar.gz" -C "$(dirname "$STORAGE")" "$(basename "$STORAGE")"
fi

find "$BACKUP_DIR" -type f -mtime +14 -delete
echo "Backup concluído: $BACKUP_DIR"
