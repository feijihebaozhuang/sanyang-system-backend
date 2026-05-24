#!/bin/bash
# 87 应用机首次/修复：从 Gitee 拉代码到 /www/feijihe/repo 并 deploy 到 stable
# 在阿里云 Workbench 登录 8.166.132.87 后执行。
#
# 前置（一次性）：老板在 Gitee 把你加为仓库开发者；你在 Gitee 生成「私人令牌」。
# 用法：
#   export GITEE_TOKEN='你的私人令牌'
#   bash bootstrap_repo_87.sh
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-feijihesanyan}"
REPO_NAME="${REPO_NAME:-sanyang-system}"
BRANCH="${BRANCH:-main}"
BASE="/www/feijihe"
REPO="$BASE/repo"
STABLE="$BASE/stable"
GITEE_TOKEN="${GITEE_TOKEN:-}"
SOURCE_DIR="${SOURCE_DIR:-}"

log() { echo "[bootstrap] $*"; }
die() { echo "[bootstrap] 错误: $*" >&2; exit 1; }

[ -n "$GITEE_TOKEN" ] || die "请先 export GITEE_TOKEN='Gitee私人令牌'（设置→私人令牌→projects 读权限）"

sudo mkdir -p "$BASE"
sudo chown -R "${SUDO_USER:-admin}:admin" "$BASE" 2>/dev/null || true

_fetch_tarball() {
  local dest="$1"
  curl -fsSL \
    "https://gitee.com/api/v5/repos/${REPO_OWNER}/${REPO_NAME}/tarball/${BRANCH}?access_token=${GITEE_TOKEN}" \
    -o "$dest/repo.tar.gz"
}

_git_clone_repo() {
  log "git clone（tarball 404 时用此方式）…"
  rm -rf "$REPO"
  git clone -b "$BRANCH" \
    "https://oauth2:${GITEE_TOKEN}@gitee.com/${REPO_OWNER}/${REPO_NAME}.git" \
    "$REPO"
}

if [ ! -d "$REPO/.git" ]; then
  log "repo 不存在，从 Gitee 拉代码…"
  TMP=$(mktemp -d)
  if [ -n "$SOURCE_DIR" ] && [ -d "$SOURCE_DIR" ]; then
    log "使用已解压目录: $SOURCE_DIR"
    mkdir -p "$REPO"
    cp -a "$SOURCE_DIR/." "$REPO/"
  elif _git_clone_repo 2>/dev/null; then
    log "git clone 成功"
  else
    log "git clone 失败，尝试 tarball…"
    _fetch_tarball "$TMP"
    mkdir -p "$REPO"
    tar -xzf "$TMP/repo.tar.gz" -C "$TMP"
    EXTRACTED=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)
    cp -a "$EXTRACTED/." "$REPO/"
  fi
  rm -rf "$TMP"
  cd "$REPO"
  if [ ! -d .git ]; then
    git init -q
    git remote add origin "https://oauth2:${GITEE_TOKEN}@gitee.com/${REPO_OWNER}/${REPO_NAME}.git" 2>/dev/null \
      || git remote set-url origin "https://oauth2:${GITEE_TOKEN}@gitee.com/${REPO_OWNER}/${REPO_NAME}.git"
    git fetch origin "$BRANCH" -q
    git checkout -B "$BRANCH" FETCH_HEAD -q
  fi
  log "repo 就绪: $(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)"
else
  log "repo 已存在，git pull…"
  cd "$REPO"
  git remote set-url origin "https://oauth2:${GITEE_TOKEN}@gitee.com/${REPO_OWNER}/${REPO_NAME}.git" 2>/dev/null || true
  git fetch origin "$BRANCH"
  git checkout "$BRANCH"
  git pull origin "$BRANCH"
  log "当前 commit: $(git rev-parse --short HEAD)"
fi

[ -d "$STABLE" ] || mkdir -p "$STABLE"
[ -f "$STABLE/.env" ] || die "缺少 $STABLE/.env，请先从旧机备份或复制 .env.example"

log "deploy → stable（只同步 .py，不覆盖 JSON/.env）…"
bash "$REPO/deploy.sh"

ENV_FILE="$STABLE/.env"
if [ -f "$ENV_FILE" ] && grep -q '^PERMISSION_VAULT_URL=' "$ENV_FILE" 2>/dev/null \
  && ! grep -q '^PERMISSION_VAULT_WRITE_URL=' "$ENV_FILE" 2>/dev/null; then
  VAULT_URL="$(grep '^PERMISSION_VAULT_URL=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r')"
  echo "PERMISSION_VAULT_WRITE_URL=${VAULT_URL}" >> "$ENV_FILE"
  log "已追加 PERMISSION_VAULT_WRITE_URL"
fi

log "重启服务…"
sudo systemctl restart sanyang-cs sanyang-production
sleep 2
systemctl is-active sanyang-cs sanyang-production
log "完成。验收: curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3002/"
