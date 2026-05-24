#!/bin/bash
# 87 紧急恢复：不依赖小马哥/156 vault，权限回 data.json，网站先能改能存
# 阿里云 Workbench 或云助手 → root/admin 执行
set -euo pipefail

STABLE="${STABLE_DIR:-/www/feijihe/stable}"
ENV_FILE="$STABLE/.env"

log() { echo "[emergency] $*"; }

[ -d "$STABLE" ] || { echo "无 $STABLE"; exit 1; }

# 1. 关掉 vault（156 数据不对时会冲掉生产线）
if [ -f "$ENV_FILE" ]; then
  cp -a "$ENV_FILE" "${ENV_FILE}.bak.$(date +%Y%m%d_%H%M)"
  grep -v '^PERMISSION_VAULT_' "$ENV_FILE" > "${ENV_FILE}.tmp" || true
  echo "" >> "${ENV_FILE}.tmp"
  echo "# emergency $(date +%F) — vault 暂停，权限走 stable/data.json" >> "${ENV_FILE}.tmp"
  echo "PERMISSION_VAULT_OFF=1" >> "${ENV_FILE}.tmp"
  mv "${ENV_FILE}.tmp" "$ENV_FILE"
  log "已设 PERMISSION_VAULT_OFF=1"
fi

# 2. 若有 Gitee 令牌则拉最新代码；没有则跳过
if [ -n "${GITEE_TOKEN:-}" ]; then
  export GITEE_TOKEN SOURCE_DIR=""
  TMP=$(mktemp -d)
  curl -fsSL "https://gitee.com/api/v5/repos/feijihesanyan/sanyang-system/tarball/main?access_token=${GITEE_TOKEN}" \
    -o "$TMP/repo.tar.gz"
  tar -xzf "$TMP/repo.tar.gz" -C "$TMP"
  SOURCE_DIR=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)
  mkdir -p /www/feijihe/repo
  rsync -a --include='*.py' --include='requirements.txt' --exclude='*' "$SOURCE_DIR/" "$STABLE/"
  log "已从 Gitee 同步 .py 到 stable"
else
  log "未设 GITEE_TOKEN，只改 .env；请确保 stable 里 py 已是最新"
fi

# 3. Hermes 改 local（若存在）
CFG=/home/admin/.hermes/config.yaml
if [ -f "$CFG" ]; then
  sed -i 's/backend: ssh/backend: local/g' "$CFG"
  sed -i '/host: 8\./d;/port: 22/d;/password:/d' "$CFG"
  log "Hermes → local"
fi

# 4. 重启
sudo systemctl restart sanyang-cs sanyang-production 2>/dev/null || true
sudo systemctl restart hermes-agent 2>/dev/null || true
sleep 2
curl -s -o /dev/null -w "3001:%{http_code} 3002:%{http_code}\n" http://127.0.0.1:3001/ http://127.0.0.1:3002/ || true
log "完成。admin 在网页改权限应能保存；真源暂用 stable/data.json"
