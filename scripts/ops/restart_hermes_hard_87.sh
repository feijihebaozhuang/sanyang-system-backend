#!/bin/bash
# 87 硬重启 Hermes：patch 配置 → 杀残留进程 → systemd 拉起 → 验收 env 是否 local
# root 在 Workbench 执行一次；解决「restart 了但旧实例还在跑」
set -euo pipefail

ADMIN="${ADMIN_USER:-admin}"
REPO="/www/feijihe/repo"
HERMES="/home/admin/.hermes"
CFG="$HERMES/config.yaml"

log() { echo "[hermes-hard] $*"; }
[ "$(id -u)" -eq 0 ] || { echo "请 root 执行"; exit 1; }

PATCH="$REPO/scripts/ops/patch_hermes_config.py"
[ -f "$PATCH" ] || { echo "missing $PATCH"; exit 1; }

log "1/5 patch config + env"
python3 "$PATCH"
chown -R "${ADMIN}:${ADMIN}" "$HERMES"

log "2/5 stop systemd"
systemctl stop hermes-agent.service 2>/dev/null || true
sleep 2

log "3/5 kill stray hermes (admin 用户残留)"
pkill -u "$ADMIN" -f '[h]ermes gateway' 2>/dev/null || true
pkill -u "$ADMIN" -f '[h]ermes-agent' 2>/dev/null || true
pkill -u "$ADMIN" -f '[h]ermes run' 2>/dev/null || true
sleep 2
REMAIN=$(pgrep -u "$ADMIN" -af hermes 2>/dev/null || true)
if [ -n "$REMAIN" ]; then
  log "WARN: 仍有 hermes 进程，强杀:"
  echo "$REMAIN"
  pkill -9 -u "$ADMIN" -f hermes 2>/dev/null || true
  sleep 1
fi

log "4/5 start systemd"
systemctl daemon-reload 2>/dev/null || true
systemctl start hermes-agent.service
sleep 4

log "5/5 验收"
echo "=== systemctl ==="
systemctl is-active hermes-agent.service || true
systemctl show hermes-agent.service -p MainPID,ActiveState,SubState --no-pager

MAINPID=$(systemctl show hermes-agent.service -p MainPID --value 2>/dev/null || echo "")
if [ -n "$MAINPID" ] && [ "$MAINPID" != "0" ] && [ -r "/proc/$MAINPID/environ" ]; then
  echo "=== 进程环境 TERMINAL_* (MainPID=$MAINPID) ==="
  tr '\0' '\n' < "/proc/$MAINPID/environ" | grep -E '^TERMINAL_' || echo "(无 TERMINAL_ 变量 — 可能从 env 文件 lazy load)"
fi

echo "=== ps hermes ==="
ps aux | grep -E '[h]ermes' || echo "(无 hermes 进程?)"

echo "=== config terminal + ssh 行 ==="
grep -nE '^(terminal:|  backend:|  ssh_|ssh_host|ssh_user|  shell:|  cwd:)' "$CFG" || true
grep -nE 'ssh_host|ssh_user|TERMINAL' "$HERMES/env" "$HERMES/.env" 2>/dev/null || true

echo "=== systemd unit TERMINAL ==="
systemctl cat hermes-agent.service 2>/dev/null | grep -iE 'TERMINAL|Environment' || true

echo "=== journal (最近) ==="
journalctl -u hermes-agent -n 25 --no-pager 2>/dev/null | tail -25

echo ""
log "说明: local 模式 **不应** 有 ssh_host/ssh_user；应有 TERMINAL_ENV=local"
log "验收后飞书 **新开对话** @小马哥: cd /www/feijihe/repo && git status"
