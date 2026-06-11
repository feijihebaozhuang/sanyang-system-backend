#!/bin/bash
# 213 重装 Ubuntu 后：只装 MySQL 8 + 导入（在 213 root 执行）
# 用法：
#   gunzip -c /path/sanyang_full_YYYYMMDD.sql.gz | bash setup_mysql_only_213.sh --import-stdin
#   bash setup_mysql_only_213.sh --import-file /path/sanyang_full_YYYYMMDD.sql.gz
set -euo pipefail

MYSQL_DB="${MYSQL_DB:-sanyang}"
MYSQL_APP_USER="${MYSQL_APP_USER:-sanyang_app}"
# 87 应用机 VPC 内网 IP（import 前 export；不确定可用 % 仅配合安全组）
APP_HOST="${APP_HOST:-%}"
IMPORT_FILE="${IMPORT_FILE:-}"

log() { echo "[setup-213-mysql] $*"; }

[ "$(id -u)" -eq 0 ] || { echo "请 root 执行"; exit 1; }

install_mysql() {
  log "安装 mysql-server ..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y mysql-server gzip
  systemctl enable mysql
  systemctl start mysql
}

configure_mysql() {
  local bind="${BIND_ADDRESS:-0.0.0.0}"
  local cnf="/etc/mysql/mysql.conf.d/99-sanyang.cnf"
  log "写入 $cnf bind-address=$bind"
  cat > "$cnf" <<EOF
[mysqld]
bind-address = ${bind}
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
max_connections = 200
EOF
  systemctl restart mysql
}

create_user_db() {
  local pwd="${MYSQL_APP_PASSWORD:?请 export MYSQL_APP_PASSWORD（与 87 stable/.env 一致）}"
  log "建库建用户 ${MYSQL_APP_USER}@${APP_HOST} ..."
  mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MYSQL_APP_USER}'@'${APP_HOST}' IDENTIFIED BY '${pwd}';
ALTER USER '${MYSQL_APP_USER}'@'${APP_HOST}' IDENTIFIED BY '${pwd}';
GRANT SELECT, INSERT, UPDATE, DELETE ON \`${MYSQL_DB}\`.* TO '${MYSQL_APP_USER}'@'${APP_HOST}';
FLUSH PRIVILEGES;
SQL
}

import_dump() {
  if [ "${1:-}" = "--import-stdin" ]; then
    log "从 stdin 导入 ..."
    gunzip -c | mysql "$MYSQL_DB"
  elif [ -n "$IMPORT_FILE" ] || [ "${1:-}" = "--import-file" ]; then
    local f="${IMPORT_FILE:-$2}"
    [ -f "$f" ] || { echo "文件不存在: $f"; exit 1; }
    log "导入 $f ..."
    gunzip -c "$f" | mysql "$MYSQL_DB"
  else
    log "跳过导入（无 --import-stdin / --import-file）"
    return 0
  fi
  local n
  n=$(mysql -N -e "SELECT COUNT(*) FROM \`${MYSQL_DB}\`.dimoldb" 2>/dev/null || echo 0)
  log "dimoldb rows: $n"
  [ "$n" -gt 1000 ] || { echo "WARN: dimoldb 行数异常，请核对"; exit 1; }
}

mark_mysql_only() {
  mkdir -p /etc/sanyang /home/admin/backup/sanyang /home/admin/scripts
  echo "mysql-only reinstall $(date -Iseconds)" > /etc/sanyang/213-mysql-only.marker
  log "标记: /etc/sanyang/213-mysql-only.marker"
}

install_mysql
configure_mysql
create_user_db
import_dump "$@"
mark_mysql_only
log "完成。87 上: systemctl restart sanyang-cs sanyang-production && bash scripts/ops/verify_production.sh"
