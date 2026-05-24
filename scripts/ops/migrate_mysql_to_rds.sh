#!/bin/bash
# 8 月 213 → 阿里云 RDS 迁移（应用机 + 213 配合）
# 用法见 docs/三机部署方案-小马哥.md 第十章
set -euo pipefail

SOURCE_HOST="${SOURCE_HOST:-172.19.18.36}"
SOURCE_USER="${SOURCE_USER:-sanyang_app}"
SOURCE_DB="${SOURCE_DB:-sanyang}"

RDS_HOST="${RDS_HOST:?RDS 内网地址 rm-xxx.mysql.rds.aliyuncs.com}"
RDS_USER="${RDS_USER:-sanyang_app}"
RDS_DB="${RDS_DB:-sanyang}"

DUMP="/tmp/sanyang_to_rds_$(date +%Y%m%d_%H%M).sql.gz"

echo "[1/3] 从 213 导出..."
mysqldump -h "$SOURCE_HOST" -u "$SOURCE_USER" -p \
  --single-transaction --routines --triggers \
  "$SOURCE_DB" | gzip > "$DUMP"
ls -lh "$DUMP"

echo "[2/3] 导入 RDS..."
gunzip -c "$DUMP" | mysql -h "$RDS_HOST" -u "$RDS_USER" -p "$RDS_DB"

echo "[3/3] 请手动改应用机 stable/.env:"
echo "  MYSQL_HOST=${RDS_HOST}"
echo "  MYSQL_USER=${RDS_USER}"
echo "  然后: sudo systemctl restart sanyang-cs sanyang-production"
echo "  验收: bash scripts/ops/verify_production.sh"
