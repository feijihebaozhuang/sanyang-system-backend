#!/bin/bash
# 小马哥交接三步合一（C push 后，87 Workbench root 执行一次）
#   export GITEE_TOKEN='私人令牌'
#   sudo bash scripts/ops/xiaomage_handoff_87.sh
set -euo pipefail

GITEE_TOKEN="${GITEE_TOKEN:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log() { echo "[handoff] $*"; }
die() { echo "[handoff] 错误: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "请 root 执行"

# 1. config.yaml terminal → local + cwd repo
log "1/3 patch hermes config.yaml"
mkdir -p /home/admin/.hermes
python3 "$SCRIPT_DIR/patch_hermes_config.py"
chown -R admin:admin /home/admin/.hermes

# admin 免密 sudo（小马哥 restart 不卡）
echo 'admin ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/admin
chmod 0440 /etc/sudoers.d/admin
visudo -c -f /etc/sudoers.d/admin

# 2. repo + deploy
log "2/3 bootstrap repo + deploy"
[ -n "$GITEE_TOKEN" ] || die "请 export GITEE_TOKEN"
export GITEE_TOKEN
TMP=$(mktemp -d)
curl -fsSL \
  "https://gitee.com/api/v5/repos/feijihesanyan/sanyang-system/tarball/main?access_token=${GITEE_TOKEN}" \
  -o "$TMP/repo.tar.gz"
tar -xzf "$TMP/repo.tar.gz" -C "$TMP"
SOURCE_DIR=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)
export SOURCE_DIR
bash "$SOURCE_DIR/scripts/ops/bootstrap_repo_87.sh"

# vault 暂停，权限走 data.json
STABLE=/www/feijihe/stable
if [ -f "$STABLE/.env" ]; then
  grep -v '^PERMISSION_VAULT_' "$STABLE/.env" > "$STABLE/.env.tmp" || true
  mv "$STABLE/.env.tmp" "$STABLE/.env"
  echo "PERMISSION_VAULT_OFF=1" >> "$STABLE/.env"
  grep -q '^GITEE_TOKEN=' "$STABLE/.env" || echo "GITEE_TOKEN=${GITEE_TOKEN}" >> "$STABLE/.env"
fi
echo "GITEE_TOKEN=${GITEE_TOKEN}" >> /home/admin/.hermes/env
chown -R admin:admin /home/admin/.hermes

# gunicorn systemd
if [ -f /www/feijihe/repo/deploy/install-systemd.sh ]; then
  bash /www/feijihe/repo/deploy/install-systemd.sh
fi

# 3. restart hermes + apps
log "3/3 restart hermes-agent + flask"
systemctl restart hermes-agent.service
systemctl restart sanyang-cs sanyang-production 2>/dev/null || true
sleep 3
touch /home/admin/.hermes/xiaomage_ready
chown admin:admin /home/admin/.hermes/xiaomage_ready

log "========== done =========="
systemctl is-active hermes-agent.service sanyang-cs sanyang-production 2>/dev/null || true
grep -A5 '^terminal:' /home/admin/.hermes/config.yaml || true
curl -s -o /dev/null -w "3001:%{http_code} 3002:%{http_code}\n" http://127.0.0.1:3001/ http://127.0.0.1:3002/ || true
