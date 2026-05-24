#!/bin/bash
# 213 数据机：只保留 MySQL，清掉 Hermes/Flask/三羊应用残留（防抢飞书、防 SSH 跳板）
#
# ⚠️ 仅在 213（8.138.10.213）以 root 执行一次
# ⚠️ 不删 MySQL 数据目录、不 stop mysqld（除非显式 PURGE_STOP_MYSQL=1，默认不碰）
#
# 用法：
#   bash purge_213_non_mysql.sh              # 预览
#   bash purge_213_non_mysql.sh --execute    # 真删
set -euo pipefail

EXEC=0
[ "${1:-}" = "--execute" ] && EXEC=1

log() { echo "[purge-213] $*"; }
run() {
  if [ "$EXEC" -eq 1 ]; then
    eval "$@"
  else
    echo "  [dry-run] $*"
  fi
}

[ "$(id -u)" -eq 0 ] || { echo "请 root 执行"; exit 1; }

# 防误删：要求本机像 213（有 mysqld 且无 87 应用目录或 hostname 提示）
if ! command -v mysqld >/dev/null 2>&1 && ! systemctl is-active mysql >/dev/null 2>&1 && ! systemctl is-active mysqld >/dev/null 2>&1; then
  log "WARN: 未检测到 MySQL 服务，确认这是 213 数据机再 --execute"
fi
if [ -d /www/feijihe/repo ] && [ -f /www/feijihe/stable/app_production.py ] 2>/dev/null; then
  if systemctl is-active sanyang-production >/dev/null 2>&1; then
    echo "ERROR: 这像 87 应用机（sanyang-production active），禁止在本机 purge"
    exit 1
  fi
fi

log "模式: $([ "$EXEC" -eq 1 ] && echo EXECUTE || echo DRY-RUN)"
log "MySQL 状态（purge 前后应保持 running）:"
systemctl is-active mysql mysqld mariadb 2>/dev/null | head -3 || true

BACKUP="/home/admin/backup/213-purge-$(date +%Y%m%d_%H%M)"
run "mkdir -p '$BACKUP'"

# ── 1. 停业务进程 ──
log "1/6 停 Hermes / Flask / 三羊 systemd"
for u in hermes-agent sanyang-cs sanyang-production openclaw; do
  run "systemctl stop '$u' 2>/dev/null || true"
  run "systemctl disable '$u' 2>/dev/null || true"
done

run "pkill -9 -u admin -f 'hermes_cli.main gateway' 2>/dev/null || true"
run "pkill -9 -u admin -f hermes-agent 2>/dev/null || true"
run "pkill -9 -u admin -f 'app_cs.py' 2>/dev/null || true"
run "pkill -9 -u admin -f 'app_production.py' 2>/dev/null || true"

# ── 2. 备份后删 Hermes（飞书长连接抢 87 的根源）──
log "2/6 移除 /home/admin/.hermes"
if [ -d /home/admin/.hermes ]; then
  if [ "$EXEC" -eq 1 ]; then
    tar czf "$BACKUP/hermes-home.tgz" -C /home/admin .hermes 2>/dev/null || true
  else
    echo "  [dry-run] tar backup .hermes -> $BACKUP/hermes-home.tgz"
  fi
  run "rm -rf /home/admin/.hermes"
fi

# ── 3. 删三羊代码树（213 不应有 repo/stable）──
log "3/6 移除 /www/feijihe"
if [ -d /www/feijihe ]; then
  if [ "$EXEC" -eq 1 ]; then
    tar czf "$BACKUP/feijihe-www.tgz" -C /www feijihe 2>/dev/null || true
  else
    echo "  [dry-run] tar backup /www/feijihe -> $BACKUP/feijihe-www.tgz"
  fi
  run "rm -rf /www/feijihe"
fi

# ── 4. 删 systemd 单元文件（若存在）──
log "4/6 清理 systemd 单元"
for f in /etc/systemd/system/hermes-agent.service \
         /etc/systemd/system/sanyang-cs.service \
         /etc/systemd/system/sanyang-production.service; do
  [ -f "$f" ] && run "rm -f '$f'"
done
run "systemctl daemon-reload 2>/dev/null || true"

# ── 5. 删 nginx 里三羊站点（若整站只为 Flask）──
log "5/6 检查 nginx 三羊站点"
for f in /etc/nginx/sites-enabled/*feijihe* /etc/nginx/conf.d/*feijihe*; do
  [ -e "$f" ] || continue
  run "rm -f '$f'"
  NGINX_RELOAD=1
done
if [ "${NGINX_RELOAD:-0}" = 1 ]; then
  run "nginx -t && systemctl reload nginx 2>/dev/null || true"
fi

# ── 6. 标记 + 验收 ──
log "6/6 写入标记并验收"
run "mkdir -p /etc/sanyang"
run "echo 'mysql-only since $(date -Iseconds)' > /etc/sanyang/213-mysql-only.marker"

if [ "$EXEC" -eq 1 ]; then
  echo ""
  log "=== 验收 ==="
  ps aux | grep -E '[h]ermes|[a]pp_production|[a]pp_cs' || echo "  无 Hermes/Flask 进程 OK"
  ss -tlnp | grep -E '3001|3002|18888' || echo "  无 3001/3002/18888 OK"
  systemctl is-active mysql mysqld mariadb 2>/dev/null | grep -q active && echo "  MySQL: active OK" || echo "  WARN: MySQL 未 active，请人工检查"
  echo "  备份目录: $BACKUP"
  log "完成。213 仅保留 MySQL；小马哥只在 87。"
else
  log "以上为预览。确认后执行: sudo bash $0 --execute"
fi
