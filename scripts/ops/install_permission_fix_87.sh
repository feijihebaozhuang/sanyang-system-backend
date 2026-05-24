#!/bin/bash
# 在 87 Workbench 执行（root 或 admin+sudo）
# 用法：先把 C 给的 sanyang-perm-fix.zip 解压到 /tmp/sanyang-perm-fix/
set -euo pipefail

SRC="${1:-/tmp/sanyang-perm-fix}"
STABLE="${STABLE_DIR:-/www/feijihe/stable}"

for f in config_json.py app_production.py app_cs.py permission_vault.py; do
  [ -f "$SRC/$f" ] || { echo "缺少 $SRC/$f"; exit 1; }
done
[ -d "$STABLE" ] || { echo "缺少目录 $STABLE"; exit 1; }

cp -a "$SRC/config_json.py" "$SRC/app_production.py" "$SRC/app_cs.py" "$SRC/permission_vault.py" "$STABLE/"
echo "已复制 4 个 py 到 $STABLE"

ENV_FILE="$STABLE/.env"
if [ -f "$ENV_FILE" ] && ! grep -q '^PERMISSION_VAULT_WRITE_URL=' "$ENV_FILE" 2>/dev/null; then
  VAULT_URL="$(grep '^PERMISSION_VAULT_URL=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r')"
  if [ -n "$VAULT_URL" ]; then
    echo "PERMISSION_VAULT_WRITE_URL=$VAULT_URL" >> "$ENV_FILE"
    echo "已追加 PERMISSION_VAULT_WRITE_URL"
  fi
fi

sudo systemctl restart sanyang-cs sanyang-production
sleep 2
systemctl is-active sanyang-cs sanyang-production
echo "完成。请在 feijihe.top 权限页试保存。"
