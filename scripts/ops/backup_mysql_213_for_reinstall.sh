#!/bin/bash
# 213 重装前：全库导出 + 校验（在 213 root 执行，或 87 远程 mysqldump）
# 备份必须拷到 87/OSS，再动重装。
set -euo pipefail

SOURCE_HOST="${SOURCE_HOST:-127.0.0.1}"
MYSQL_USER="${MYSQL_USER:-sanyang_app}"
MYSQL_DB="${MYSQL_DB:-sanyang}"
BACKUP_DIR="${BACKUP_DIR:-/home/admin/backup/sanyang-reinstall}"
STAMP="$(date +%Y%m%d_%H%M)"
DUMP="${BACKUP_DIR}/sanyang_full_${STAMP}.sql.gz"
META="${BACKUP_DIR}/sanyang_full_${STAMP}.meta"

mkdir -p "$BACKUP_DIR"

if [ -z "${MYSQL_PWD:-}" ] && [ -f /home/admin/.my.cnf ]; then
  export MYSQL_PWD="$(grep -E '^password=' /home/admin/.my.cnf | head -1 | cut -d= -f2- | tr -d ' \"')"
fi
if [ -z "${MYSQL_PWD:-}" ] && [ -f /root/.my.cnf ]; then
  export MYSQL_PWD="$(grep -E '^password=' /root/.my.cnf | head -1 | cut -d= -f2- | tr -d ' \"')"
fi

echo "[1/4] mysqldump ${MYSQL_DB} @ ${SOURCE_HOST} ..."
mysqldump -h "$SOURCE_HOST" -u "$MYSQL_USER" \
  --single-transaction --routines --triggers --events \
  "$MYSQL_DB" | gzip > "$DUMP"

echo "[2/4] 校验 gzip ..."
gunzip -t "$DUMP"

echo "[3/4] 统计 ..."
BYTES=$(stat -c%s "$DUMP" 2>/dev/null || stat -f%z "$DUMP")
TABLES=$(gunzip -c "$DUMP" | grep -c '^CREATE TABLE' || true)
{
  echo "stamp=$STAMP"
  echo "file=$DUMP"
  echo "bytes=$BYTES"
  echo "create_table_lines=$TABLES"
  echo "host=$SOURCE_HOST"
  echo "database=$MYSQL_DB"
} > "$META"

if [ "$TABLES" -lt 5 ]; then
  echo "ERROR: CREATE TABLE 过少 ($TABLES)，勿继续重装"
  exit 1
fi

echo "[4/4] 完成"
ls -lh "$DUMP"
cat "$META"
echo ""
echo "下一步（87 上，把备份拷离 213）："
echo "  scp admin@8.138.10.213:${DUMP} /home/admin/backup/"
echo "  scp admin@8.138.10.213:${META} /home/admin/backup/"
