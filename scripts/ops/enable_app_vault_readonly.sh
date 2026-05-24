#!/bin/bash
# 在应用机执行：把 156 vault 写入 stable/.env 并重启双端
set -euo pipefail

STABLE="${STABLE_DIR:-/www/feijihe/stable}"
VAULT_URL="${VAULT_URL:?例如 http://172.x.x.x:9443/permission_data.json}"
VAULT_TOKEN="${VAULT_TOKEN:?与 156 上一致}"

ENV_FILE="$STABLE/.env"
[ -f "$ENV_FILE" ] || { echo "缺少 $ENV_FILE"; exit 1; }

grep -v '^PERMISSION_VAULT_' "$ENV_FILE" > "${ENV_FILE}.tmp" || true
mv "${ENV_FILE}.tmp" "$ENV_FILE"
{
  echo ""
  echo "# permission vault (156) — $(date +%Y-%m-%d)"
  echo "PERMISSION_VAULT_URL=${VAULT_URL}"
  echo "PERMISSION_VAULT_TOKEN=${VAULT_TOKEN}"
} >> "$ENV_FILE"

echo "已写入 .env，重启服务..."
sudo systemctl restart sanyang-cs sanyang-production
sleep 2
systemctl is-active sanyang-cs sanyang-production
echo "验收: 生产端改工序保存应返回 403"
