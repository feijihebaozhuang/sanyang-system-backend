#!/bin/bash
# 应用机 8.166.132.87 上执行（需 root 或能 sudo 的账号一次）
# 用途：admin 免密 sudo，deploy.sh 里 systemctl 不再卡密码
set -euo pipefail

SUDOERS_FILE="/etc/sudoers.d/admin"
ADMIN_USER="${ADMIN_USER:-admin}"

if [ "$(id -u)" -ne 0 ]; then
  echo "请用 root 执行，或: sudo bash $0"
  exit 1
fi

if ! id "$ADMIN_USER" &>/dev/null; then
  echo "用户不存在: $ADMIN_USER"
  exit 1
fi

# 确保在 sudo/wheel 组
if getent group wheel &>/dev/null; then
  usermod -aG wheel "$ADMIN_USER" 2>/dev/null || true
fi
if getent group sudo &>/dev/null; then
  usermod -aG sudo "$ADMIN_USER" 2>/dev/null || true
fi

echo "${ADMIN_USER} ALL=(ALL) NOPASSWD: ALL" > "$SUDOERS_FILE"
chmod 0440 "$SUDOERS_FILE"

if ! visudo -c -f "$SUDOERS_FILE"; then
  rm -f "$SUDOERS_FILE"
  echo "语法错误，已回滚"
  exit 1
fi

if su - "$ADMIN_USER" -c 'sudo -n true'; then
  echo "OK: ${ADMIN_USER} NOPASSWD 已生效"
else
  echo "WARN: 配置已写入，但验收失败。请 ${ADMIN_USER} 重新登录 SSH 后再试: sudo -n true"
  exit 1
fi
