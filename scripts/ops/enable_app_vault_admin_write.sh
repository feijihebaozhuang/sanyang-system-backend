#!/bin/bash
# 在 87 应用机执行：开启 admin 网页写 156 vault（工序+勾选整包），并重启双端
set -euo pipefail

STABLE="${STABLE_DIR:-/www/feijihe/stable}"
VAULT_URL="${VAULT_URL:?例如 http://172.16.0.94:9443/api/permission_data}"
VAULT_WRITE_URL="${VAULT_WRITE_URL:-$VAULT_URL}"
VAULT_TOKEN="${VAULT_TOKEN:?与 156 permission_vault 一致}"

ENV_FILE="$STABLE/.env"
[ -f "$ENV_FILE" ] || { echo "缺少 $ENV_FILE"; exit 1; }

grep -v '^PERMISSION_VAULT_' "$ENV_FILE" > "${ENV_FILE}.tmp" || true
mv "${ENV_FILE}.tmp" "$ENV_FILE"
{
  echo ""
  echo "# permission vault (156) admin write — $(date +%Y-%m-%d)"
  echo "PERMISSION_VAULT_URL=${VAULT_URL}"
  echo "PERMISSION_VAULT_WRITE_URL=${VAULT_WRITE_URL}"
  echo "PERMISSION_VAULT_TOKEN=${VAULT_TOKEN}"
} >> "$ENV_FILE"

echo "已写入 .env（含 WRITE_URL），部署 .py 后重启..."
sudo systemctl restart sanyang-cs sanyang-production
sleep 2
systemctl is-active sanyang-cs sanyang-production
echo "验收: feijihe.top / zean.feijihe.top 权限页保存应返回 success"
