#!/bin/bash
# 在 156 权限机执行（需 root）
# 用法: sudo VAULT_TOKEN='随机串' APP_SERVER_IP='8.166.132.87' bash install_permission_vault_156.sh
set -euo pipefail

CONFIG_DIR="/opt/sanyang-config"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_SCRIPT="${REPO_SCRIPT:-${SCRIPT_DIR}/../permission_vault_server.example.py}"
VAULT_TOKEN="${VAULT_TOKEN:?请设置环境变量 VAULT_TOKEN}"
APP_SERVER_IP="${APP_SERVER_IP:-8.166.132.87}"

if [ "$(id -u)" -ne 0 ]; then
  echo "请: sudo VAULT_TOKEN=xxx APP_SERVER_IP=8.166.132.87 bash $0"
  exit 1
fi

if [ ! -f "$REPO_SCRIPT" ]; then
  echo "缺少 $REPO_SCRIPT，请 scp 应用机 repo/scripts/permission_vault_server.example.py 到 156"
  exit 1
fi

mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/permission_data.json" ]; then
  echo '{}' > "$CONFIG_DIR/permission_data.json"
  echo "WARN: 已创建空 permission_data.json，请先从应用机导入"
fi

cp -f "$REPO_SCRIPT" "$CONFIG_DIR/permission_vault_server.py"
chown -R admin:admin "$CONFIG_DIR"

UNIT="/etc/systemd/system/sanyang-permission-vault.service"
SYSTEMD_SRC="${SCRIPT_DIR}/../../deploy/systemd/sanyang-permission-vault.service"
if [ ! -f "$SYSTEMD_SRC" ]; then
  echo "缺少 $SYSTEMD_SRC"
  exit 1
fi
sed "s|/opt/sanyang-config|$CONFIG_DIR|g" "$SYSTEMD_SRC" > "$UNIT"
sed -i "s|# Environment=PERMISSION_VAULT_TOKEN=.*|Environment=PERMISSION_VAULT_TOKEN=${VAULT_TOKEN}|" "$UNIT" || true
if ! grep -q "PERMISSION_VAULT_TOKEN=${VAULT_TOKEN}" "$UNIT"; then
  echo "Environment=PERMISSION_VAULT_TOKEN=${VAULT_TOKEN}" >> "$UNIT"
fi

systemctl daemon-reload
systemctl enable sanyang-permission-vault
systemctl restart sanyang-permission-vault

if command -v firewall-cmd &>/dev/null; then
  firewall-cmd --permanent --add-rich-rule="rule family=\"ipv4\" source address=\"${APP_SERVER_IP}\" port port=\"9443\" protocol=\"tcp\" accept" 2>/dev/null || true
  firewall-cmd --reload 2>/dev/null || true
fi

echo "vault 状态:"
systemctl --no-pager status sanyang-permission-vault | head -5
echo ""
echo "本机自测:"
curl -s -H "Authorization: Bearer ${VAULT_TOKEN}" "http://127.0.0.1:9443/permission_data.json" | head -c 200
echo ""
echo "应用机 .env 追加:"
echo "PERMISSION_VAULT_URL=http://<156内网IP>:9443/permission_data.json"
echo "PERMISSION_VAULT_TOKEN=${VAULT_TOKEN}"
