#!/bin/bash
# 三机验收脚本 — 在应用机或本机 curl 均可
set -euo pipefail

APP_HOST="${APP_HOST:-127.0.0.1}"
PUBLIC_PROD="${PUBLIC_PROD:-https://feijihe.top}"
PUBLIC_CS="${PUBLIC_CS:-https://zean.feijihe.top}"

echo "=== 本地端口 ==="
for p in 3001 3002; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://${APP_HOST}:${p}/" || echo "000")
  echo "  :${p} → HTTP ${code}"
done

echo "=== 外网 HTTPS ==="
for url in "$PUBLIC_PROD" "$PUBLIC_CS"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$url/" || echo "000")
  echo "  ${url} → HTTP ${code}"
done

echo "=== systemd ==="
if command -v systemctl &>/dev/null; then
  systemctl is-active sanyang-cs sanyang-production 2>/dev/null || true
fi

echo "=== MySQL（应用机 stable venv）==="
STABLE="${STABLE_DIR:-/www/feijihe/stable}"
if [ -f "$STABLE/.env" ] && [ -f "$STABLE/venv/bin/python3" ]; then
  (
    cd "$STABLE"
    source venv/bin/activate
    python3 -c "
import pymysql
from settings import get_db_config
c = dict(get_db_config())
c.pop('autocommit', None)
db = pymysql.connect(**c)
cur = db.cursor()
cur.execute('SELECT 1')
cur.execute('SELECT COUNT(*) FROM dimoldb')
n = cur.fetchone()[0]
print('  MySQL OK, dimoldb rows:', n)
"
  ) || echo "  MySQL 连接失败"
else
  echo "  跳过（非应用机或未部署 stable）"
fi

echo "=== 报价 API ==="
body='{"type":"juxing","length":26.5,"width":15.5,"height":2.5,"qty":1000,"material":"d6d","discount":100}'
resp=$(curl -s --connect-timeout 15 -X POST "${PUBLIC_PROD}/api/quote/calculate" \
  -H "Content-Type: application/json" -d "$body" || echo '{}')
if echo "$resp" | grep -q '"success": true'; then
  echo "  quote/calculate OK"
else
  echo "  quote/calculate FAIL: ${resp:0:200}"
fi

echo "=== 权限 vault（若已配 .env）==="
if [ -f "$STABLE/.env" ]; then
  grep -E '^PERMISSION_VAULT_URL=' "$STABLE/.env" || echo "  未配置 PERMISSION_VAULT_URL（权限仍在应用机 data.json）"
fi

echo "=== 完成 ==="
