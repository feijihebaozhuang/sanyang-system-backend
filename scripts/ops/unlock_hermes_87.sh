#!/bin/bash
# 87 应用机 Workbench 用 root 执行一次 — 解锁小马哥 Hermes 工具链
# 现象：工具链被 SSH 卡死、跑不了 git/deploy/systemctl
set -euo pipefail

HERMES_CFG="${HERMES_CFG:-/home/admin/.hermes/config.yaml}"
HERMES_ENV="${HERMES_ENV:-/home/admin/.hermes/env}"
ADMIN_USER="${ADMIN_USER:-admin}"

log() { echo "[unlock-hermes] $*"; }
die() { echo "[unlock-hermes] 错误: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "请用 root 在 Workbench 执行: sudo bash $0"

# ── 1. Hermes：SSH 模式 → 本机 local（核心）──
if [ -f "$HERMES_CFG" ]; then
  cp -a "$HERMES_CFG" "${HERMES_CFG}.bak.$(date +%Y%m%d_%H%M)"
  sed -i 's/backend: ssh/backend: local/g' "$HERMES_CFG"
  sed -i '/host: 8\.166\.132\.87/d' "$HERMES_CFG"
  sed -i '/host: 8\.138\.10\.213/d' "$HERMES_CFG"
  sed -i '/port: 22/d' "$HERMES_CFG"
  sed -i '/^[[:space:]]*user: admin/d' "$HERMES_CFG"
  sed -i '/^[[:space:]]*password:/d' "$HERMES_CFG"
  log "Hermes config → backend: local（已删 SSH 段）"
else
  log "WARN: 无 $HERMES_CFG，跳过 Hermes 配置（确认 Agent 是否已装到 87）"
fi

# ── 2. admin 免密 sudo（Agent 重启服务不再卡密码）──
SUDOERS="/etc/sudoers.d/admin"
echo "${ADMIN_USER} ALL=(ALL) NOPASSWD: ALL" > "$SUDOERS"
chmod 0440 "$SUDOERS"
visudo -c -f "$SUDOERS"
su - "$ADMIN_USER" -c 'sudo -n true' && log "admin NOPASSWD OK"

# ── 3. Gitee 令牌（可选，有了才能 git pull 私有库）──
if [ -n "${GITEE_TOKEN:-}" ]; then
  mkdir -p "$(dirname "$HERMES_ENV")"
  grep -v '^GITEE_TOKEN=' "$HERMES_ENV" 2>/dev/null > "${HERMES_ENV}.tmp" || true
  mv "${HERMES_ENV}.tmp" "$HERMES_ENV"
  echo "GITEE_TOKEN=${GITEE_TOKEN}" >> "$HERMES_ENV"
  chown -R "${ADMIN_USER}:${ADMIN_USER}" /home/admin/.hermes
  log "已写入 GITEE_TOKEN 到 $HERMES_ENV"
else
  log "提示: 未设 GITEE_TOKEN，deploy 仍无法 git pull。老板加仓库成员后："
  log "  GITEE_TOKEN=令牌 sudo bash $0"
fi

# ── 4. 重启 Hermes ──
if systemctl list-unit-files | grep -q hermes-agent; then
  systemctl restart hermes-agent
  sleep 2
  systemctl is-active hermes-agent && log "hermes-agent active"
else
  log "WARN: 无 hermes-agent.service，请确认 Hermes 已安装到 87"
fi

log "完成。飞书 @小马哥 让他试: cd /www/feijihe/repo && git pull 或 bootstrap 脚本"
