#!/bin/bash
# 在 213 数据机 cron 每日执行
# 0 3 * * * /home/admin/scripts/mysql_daily_backup_213.sh
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/home/admin/backup/sanyang}"
MYSQL_USER="${MYSQL_USER:-sanyang_app}"
MYSQL_DB="${MYSQL_DB:-sanyang}"
# 密码：export MYSQL_PWD=... 或在 ~/.my.cnf

mkdir -p "$BACKUP_DIR"
FILE="${BACKUP_DIR}/sanyang_$(date +%Y%m%d_%H%M).sql.gz"

mysqldump -u "$MYSQL_USER" \
  --single-transaction --routines --triggers \
  "$MYSQL_DB" | gzip > "$FILE"

echo "backup: $FILE ($(du -h "$FILE" | cut -f1))"
find "$BACKUP_DIR" -name 'sanyang_*.sql.gz' -mtime +14 -delete
