#!/bin/bash
# 213 数据机：只保留 MySQL + 备份脚本，清掉 Hermes/Flask/三羊应用（防抢飞书）
#
# ⚠️ 仅在 213（8.138.10.213）以 root 执行
# ⚠️ 不 stop mysqld、不删 /var/lib/mysql
#
# 213 上没有 git 时，从 87 拷脚本（Gitee 私有库 raw 会 403）：
#   scp /www/feijihe/repo/scripts/ops/purge_213_non_mysql.sh admin@8.138.10.213:/tmp/
#   ssh admin@8.138.10.213 'sudo bash /tmp/purge_213_non_mysql.sh --execute'
#
# 公网 raw（仅公开仓库可用，私有会 403）：
#   curl -fsSL 'https://gitee.com/feijihesanyan/sanyang-system/raw/main/scripts/ops/purge_213_non_mysql.sh' | bash -s -- --execute
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

[ "$(id -u)" -eq 0 ] || { echo "请 root 执行（admin 无法 kill Hermes / 删系统目录）"; exit 1; }

if [ -d /www/feijihe/stable ] && systemctl is-active sanyang-production >/dev/null 2>&1; then
  echo "ERROR: sanyang-production 在本机 active，像 87 应用机，禁止 purge"
  exit 1
fi

log "模式: $([ "$EXEC" -eq 1 ] && echo EXECUTE || echo DRY-RUN)"
log "MySQL（purge 前后应保持 running）:"
systemctl is-active mysql mysqld mariadb 2>/dev/null | head -3 || true

BACKUP="/home/admin/backup/213-purge-$(date +%Y%m%d_%H%M)"
run "mkdir -p '$BACKUP'"

# ── 1. 停 systemd ──
log "1/8 停 Hermes / Flask / OpenClaw systemd"
for u in hermes-agent sanyang-cs sanyang-production openclaw openclaw-gateway; do
  run "systemctl stop '$u' 2>/dev/null || true"
  run "systemctl disable '$u' 2>/dev/null || true"
done

# admin 用户级 systemd（Hermes 常藏这里）
if id admin >/dev/null 2>&1; then
  run "sudo -u admin XDG_RUNTIME_DIR=/run/user/\$(id -u admin) systemctl --user stop hermes-agent 2>/dev/null || true"
  run "sudo -u admin XDG_RUNTIME_DIR=/run/user/\$(id -u admin) systemctl --user disable hermes-agent 2>/dev/null || true"
  run "rm -rf /home/admin/.config/systemd/user/hermes*.service 2>/dev/null || true"
fi

# ── 2. 强杀进程（admin pkill 常无效，必须 root kill -9）──
log "2/8 强杀 Hermes / Flask / OpenClaw 进程"
for pat in 'hermes_cli.main gateway' hermes-agent 'app_cs.py' 'app_production.py' openclaw; do
  if [ "$EXEC" -eq 1 ]; then
  while read -r pid; do
    [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null || true
  done < <(pgrep -f "$pat" 2>/dev/null || true)
  else
    pgrep -af "$pat" 2>/dev/null || true
  fi
done

# ── 3. 备份后删 Hermes 整目录 ──
log "3/8 移除 /home/admin/.hermes"
if [ -d /home/admin/.hermes ]; then
  if [ "$EXEC" -eq 1 ]; then
    tar czf "$BACKUP/hermes-home.tgz" -C /home/admin .hermes 2>/dev/null || true
    chown admin:admin "$BACKUP/hermes-home.tgz" 2>/dev/null || true
  else
    echo "  [dry-run] backup -> $BACKUP/hermes-home.tgz"
    du -sh /home/admin/.hermes 2>/dev/null || true
  fi
  run "rm -rf /home/admin/.hermes"
fi

# ── 4. 删三羊代码 / 运行时 ──
log "4/8 移除 /www/feijihe、/opt 下三羊残留"
for d in /www/feijihe /opt/feijihe /opt/sanyang /home/admin/feijihe /home/admin/sanyang-system; do
  if [ -d "$d" ]; then
    if [ "$EXEC" -eq 1 ]; then
      bn=$(basename "$d")
      tar czf "$BACKUP/${bn}.tgz" -C "$(dirname "$d")" "$bn" 2>/dev/null || true
    fi
    run "rm -rf '$d'"
  fi
done

# ── 5. systemd 单元 ──
log "5/8 清理 systemd 单元"
for f in /etc/systemd/system/hermes*.service \
         /etc/systemd/system/sanyang*.service \
         /etc/systemd/system/openclaw*.service \
         /lib/systemd/system/hermes*.service; do
  [ -e "$f" ] || continue
  run "rm -f '$f'"
done
run "systemctl daemon-reload 2>/dev/null || true"

# ── 6. nginx / supervisor ──
log "6/8 nginx / supervisor"
for f in /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*; do
  [ -e "$f" ] || continue
  if grep -qE 'feijihe|sanyang|3001|3002|18888' "$f" 2>/dev/null; then
    run "rm -f '$f'"
    NGINX_TOUCH=1
  fi
done
if [ "${NGINX_TOUCH:-0}" = 1 ]; then
  run "nginx -t 2>/dev/null && systemctl reload nginx 2>/dev/null || systemctl stop nginx 2>/dev/null || true"
fi
if [ -f /etc/supervisor/conf.d/hermes.conf ]; then
  run "rm -f /etc/supervisor/conf.d/hermes.conf /etc/supervisor/conf.d/sanyang*.conf"
  run "supervisorctl update 2>/dev/null || true"
fi

# ── 7. cron 里非 MySQL 的三羊任务（保留 mysql_daily_backup）──
log "7/8 检查 cron"
if [ "$EXEC" -eq 1 ] && id admin >/dev/null 2>&1; then
  crontab -l -u admin 2>/dev/null | grep -viE 'hermes|feijihe|app_production|app_cs|openclaw|deploy\.sh' | crontab -u admin - 2>/dev/null || true
fi

# ── 8. 标记 + 验收 ──
log "8/8 标记与验收"
run "mkdir -p /etc/sanyang"
run "echo 'mysql-only since $(date -Iseconds)' > /etc/sanyang/213-mysql-only.marker"

if [ "$EXEC" -eq 1 ]; then
  sleep 1
  echo ""
  log "=== 验收 ==="
  if ps aux | grep -E '[h]ermes|[a]pp_production|[a]pp_cs|[o]penclaw'; then
    log "FAIL: 仍有业务进程，请把 ps 输出贴给大虾"
    exit 1
  else
    echo "  无 Hermes/Flask/OpenClaw 进程 OK"
  fi
  ss -tlnp 2>/dev/null | grep -E '3001|3002|18888' && exit 1 || echo "  无 3001/3002/18888 OK"
  if systemctl is-active mysql mysqld mariadb 2>/dev/null | grep -q active; then
    echo "  MySQL: active OK"
  else
    log "WARN: MySQL 未 active，请人工检查"
  fi
  echo "  备份: $BACKUP"
  echo "  保留: mysqld + /home/admin/backup + mysql_daily_backup_213.sh cron"
  log "完成。213 仅数据层；小马哥只在 87。"
else
  log "预览结束。root 执行: bash $0 --execute"
  log "私有库请从 87 scp 本脚本到 213，勿用 curl raw"
fi
