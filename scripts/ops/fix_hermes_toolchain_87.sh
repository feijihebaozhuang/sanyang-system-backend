#!/bin/bash
# 87 小马哥工具链一键修复（root 执行一次）
# 解决：git dubious ownership、admin 无 sudo、GITEE_TOKEN 缺失、terminal 未配 shell
set -euo pipefail

ADMIN="${ADMIN_USER:-admin}"
REPO="/www/feijihe/repo"
STABLE="/www/feijihe/stable"
HERMES="/home/admin/.hermes"

log() { echo "[toolchain] $*"; }
[ "$(id -u)" -eq 0 ] || { echo "请 root 执行"; exit 1; }

# 1. 目录归属
chown -R "${ADMIN}:${ADMIN}" /www/feijihe "$HERMES"

# 2. admin 免密 sudo
echo "${ADMIN} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/admin
chmod 0440 /etc/sudoers.d/admin
visudo -c -f /etc/sudoers.d/admin

# 3. admin 用户 git 安全目录（Hermes 用 admin 跑 git）
su - "$ADMIN" -c "git config --global --add safe.directory ${REPO}"
su - "$ADMIN" -c "git config --global --add safe.directory ${STABLE}"

# 4. GITEE_TOKEN 同步到 hermes/env
if [ -f "$STABLE/.env" ]; then
  TOK=$(grep '^GITEE_TOKEN=' "$STABLE/.env" | head -1 | cut -d= -f2- | tr -d '\r"' || true)
  if [ -n "$TOK" ]; then
    mkdir -p "$HERMES"
    grep -v '^GITEE_TOKEN=' "$HERMES/env" 2>/dev/null > "$HERMES/env.tmp" || true
    mv "$HERMES/env.tmp" "$HERMES/env"
    echo "GITEE_TOKEN=${TOK}" >> "$HERMES/env"
  fi
fi
grep -q '^FEISHU_ALLOWED_USERS=' "$HERMES/env" 2>/dev/null || echo 'FEISHU_ALLOWED_USERS=*' >> "$HERMES/env"
grep -q '^STABLE_DIR=' "$HERMES/env" 2>/dev/null || echo "STABLE_DIR=${STABLE}" >> "$HERMES/env"
grep -q '^REPO_DIR=' "$HERMES/env" 2>/dev/null || echo "REPO_DIR=${REPO}" >> "$HERMES/env"
chown -R "${ADMIN}:${ADMIN}" "$HERMES"

# 5. config.yaml：terminal local + toolsets all + feishu 全工具（勿用 sed 删 host/password，会误伤）
PATCH="$REPO/scripts/ops/patch_hermes_config.py"
[ -f "$PATCH" ] || PATCH="$STABLE/scripts/ops/patch_hermes_config.py"
python3 "$PATCH"
chown "${ADMIN}:${ADMIN}" "$HERMES/config.yaml"

# 6. 权限 vault 关（避免冲配置）
if [ -f "$STABLE/.env" ]; then
  grep -q '^PERMISSION_VAULT_OFF=1' "$STABLE/.env" || echo 'PERMISSION_VAULT_OFF=1' >> "$STABLE/.env"
fi

# 7. 以 admin 身份验收（= 小马哥实际执行环境）
log "=== admin 工具链验收 ==="
su - "$ADMIN" -c "sudo -n true && echo sudo:OK"
su - "$ADMIN" -c "cd ${REPO} && git status -sb | head -3"
su - "$ADMIN" -c "test -x ${STABLE}/venv/bin/gunicorn && echo gunicorn:OK"
su - "$ADMIN" -c "curl -sf -o /dev/null -w '3002:%{http_code}\n' http://127.0.0.1:3002/"

systemctl restart hermes-agent.service
sleep 3
log "=== hermes ==="
systemctl is-active hermes-agent.service
grep -E '^(TERMINAL_ENV|TERMINAL_CWD|TERMINAL_SSH_HOST)=' "$HERMES/env" "$HERMES/.env" 2>/dev/null || true
grep -A5 '^terminal:' "$HERMES/config.yaml"
grep -A3 '^toolsets:' "$HERMES/config.yaml" || true
grep -A20 '^platform_toolsets:' "$HERMES/config.yaml" | head -25 || true
journalctl -u hermes-agent -n 30 --no-pager 2>/dev/null | grep -iE 'terminal|ssh|disabled|tool' || true

log "完成。请飞书 @小马哥 新开对话发：cd /www/feijihe/repo && git status"
log "（必须新开对话；旧会话会缓存旧工具列表）"
log "若仍无 terminal，把 patch --check 输出发给 C"
