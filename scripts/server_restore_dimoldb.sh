#!/bin/bash
# 213 生产端：拉代码 → 导入刀模 merged.json → 复制 index.html
# 用法: bash scripts/server_restore_dimoldb.sh
set -euo pipefail

REPO="${REPO:-/www/feijihe/repo}"
STABLE="${STABLE:-/www/feijihe/stable}"
MERGED="${MERGED:-$REPO/data/import/dimoldb/dimoldb_merged.json}"

cd "$REPO"
git pull origin main

if [ ! -f "$MERGED" ]; then
  echo "缺少 $MERGED ，请确认 git pull 后文件存在"
  exit 1
fi

"$REPO/deploy.sh"

cp "$REPO/index.html" "$STABLE/index.html"
chown admin:sanyang "$STABLE/index.html" 2>/dev/null || true

cd "$STABLE"
# shellcheck source=/dev/null
source venv/bin/activate
python3 "$REPO/scripts/import_dimoldb_merged_json.py" "$MERGED"
echo "[OK] dimoldb 已导入，请重启 3002/3001"
