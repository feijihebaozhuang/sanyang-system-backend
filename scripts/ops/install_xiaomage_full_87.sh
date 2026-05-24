#!/bin/bash
# 87 小马哥全权初始化 — root 执行一次（或小马哥 sudo bash）
# 之后：deploy / 重启 / 权限 / 飞书 全由小马哥在 87 本机处理，老板不再敲命令
#
# 用法（Workbench root）：
#   export GITEE_TOKEN='Gitee私人令牌'   # 小马哥账号令牌，老板仅加仓库成员
#   curl -fsSL "https://gitee.com/api/v5/repos/feijihesanyan/sanyang-system/tarball/main?access_token=${GITEE_TOKEN}" | tar xz -C /tmp
#   DIR=$(find /tmp -mindepth 1 -maxdepth 1 -type d | head -1)
#   sudo GITEE_TOKEN="$GITEE_TOKEN" bash "$DIR/scripts/ops/install_xiaomage_full_87.sh"
set -euo pipefail

ADMIN="${ADMIN_USER:-admin}"
BASE="/www/feijihe"
STABLE="$BASE/stable"
REPO="$BASE/repo"
HERMES_CFG="/home/admin/.hermes/config.yaml"
HERMES_ENV="/home/admin/.hermes/env"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log() { echo "[xiaomage-full] $*"; }
die() { echo "[xiaomage-full] 错误: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "请 root 执行"

mkdir -p "$BASE" "$STABLE"
chown -R "$ADMIN:$ADMIN" "$BASE" /home/admin/.hermes 2>/dev/null || true

# ── A. 小马哥 Hermes：本机 local，禁止 SSH 跳板 ──
if [ -f "$HERMES_CFG" ]; then
  cp -a "$HERMES_CFG" "${HERMES_CFG}.bak.$(date +%Y%m%d_%H%M)"
  sed -i 's/backend: ssh/backend: local/g' "$HERMES_CFG"
  sed -i '/host: 8\./d;/host: 172\./d;/port: 22/d;/^[[:space:]]*user: admin/d;/password:/d' "$HERMES_CFG"
  log "Hermes → backend: local"
fi
mkdir -p /home/admin/.hermes
touch "$HERMES_ENV"
grep -q '^FEISHU_ALLOWED_USERS=' "$HERMES_ENV" 2>/dev/null || echo 'FEISHU_ALLOWED_USERS=*' >> "$HERMES_ENV"
grep -q '^STABLE_DIR=' "$HERMES_ENV" 2>/dev/null || echo "STABLE_DIR=$STABLE" >> "$HERMES_ENV"
grep -q '^REPO_DIR=' "$HERMES_ENV" 2>/dev/null || echo "REPO_DIR=$REPO" >> "$HERMES_ENV"
if [ -n "${GITEE_TOKEN:-}" ]; then
  grep -v '^GITEE_TOKEN=' "$HERMES_ENV" > "${HERMES_ENV}.tmp" || true
  mv "${HERMES_ENV}.tmp" "$HERMES_ENV"
  echo "GITEE_TOKEN=${GITEE_TOKEN}" >> "$HERMES_ENV"
  grep -q '^GITEE_TOKEN=' "$STABLE/.env" 2>/dev/null || echo "GITEE_TOKEN=${GITEE_TOKEN}" >> "$STABLE/.env"
fi
chown -R "$ADMIN:$ADMIN" /home/admin/.hermes

# ── B. admin 免密 sudo ──
echo "${ADMIN} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/admin
chmod 0440 /etc/sudoers.d/admin
visudo -c -f /etc/sudoers.d/admin

# ── C. 权限：暂停 156 vault，stable/data.json 为准 ──
if [ -f "$STABLE/.env" ]; then
  cp -a "$STABLE/.env" "$STABLE/.env.bak.$(date +%Y%m%d_%H%M)"
  grep -v '^PERMISSION_VAULT_' "$STABLE/.env" > "$STABLE/.env.tmp" || true
  mv "$STABLE/.env.tmp" "$STABLE/.env"
  echo "PERMISSION_VAULT_OFF=1" >> "$STABLE/.env"
fi

# ── D. Gitee repo + deploy ──
if [ -n "${GITEE_TOKEN:-}" ]; then
  export GITEE_TOKEN SOURCE_DIR="$SCRIPT_DIR/.."
  if [ -f "$SCRIPT_DIR/bootstrap_repo_87.sh" ]; then
    sudo -u "$ADMIN" GITEE_TOKEN="$GITEE_TOKEN" bash "$SCRIPT_DIR/bootstrap_repo_87.sh"
  fi
else
  log "WARN: 无 GITEE_TOKEN，跳过 git；小马哥向老板要令牌后重跑本脚本"
  rsync -a --include='*.py' --include='scripts/' --include='scripts/**' --include='deploy/' --include='deploy/**' --exclude='*' "$SCRIPT_DIR/../" "$STABLE/" 2>/dev/null || true
fi

# ── E. systemd gunicorn ──
if [ -f "$REPO/deploy/install-systemd.sh" ]; then
  bash "$REPO/deploy/install-systemd.sh"
elif [ -f "$SCRIPT_DIR/../deploy/install-systemd.sh" ]; then
  bash "$SCRIPT_DIR/../deploy/install-systemd.sh"
fi

# ── F. 定时：小马哥不在时自动 pull + self-repair ──
CRON_FILE="/etc/cron.d/sanyang-xiaomage"
cat > "$CRON_FILE" <<EOF
# 三羊 87 自动同步（小马哥全权运维）
0 * * * * ${ADMIN} cd ${REPO} && git pull origin main && ${REPO}/deploy.sh && systemctl restart sanyang-cs sanyang-production >> /tmp/sanyang-deploy.log 2>&1
*/15 * * * * ${ADMIN} test -x ${STABLE}/scripts/ops/cron_self_repair.sh && ${STABLE}/scripts/ops/cron_self_repair.sh >> /tmp/sanyang-self-repair.log 2>&1
EOF
chmod 644 "$CRON_FILE"

# ── G. 重启 ──
systemctl restart hermes-agent 2>/dev/null || log "WARN: 无 hermes-agent"
systemctl restart sanyang-cs sanyang-production 2>/dev/null || true
sleep 3

touch /home/admin/.hermes/xiaomage_ready
chown "$ADMIN:$ADMIN" /home/admin/.hermes/xiaomage_ready

log "========== 验收 =========="
systemctl is-active hermes-agent sanyang-cs sanyang-production 2>/dev/null || true
curl -s -o /dev/null -w "3001:%{http_code} 3002:%{http_code}\n" http://127.0.0.1:3001/ http://127.0.0.1:3002/ || true
log "完成。飞书 @小马哥：你已全权负责 87，C push 后你 git pull && deploy。"
