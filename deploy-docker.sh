#!/bin/bash
# ============================================================
# deploy-docker.sh — Docker 部署（只重建 .py 镜像，不覆盖 JSON 配置）
# 用法: ./deploy-docker.sh [--branch=main]
# ============================================================
set -euo pipefail

REPO_DIR="/www/feijihe/repo"
STABLE_DIR="/www/feijihe/stable"
REMOTE="origin"
BRANCH="main"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ${NC} $1"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ${NC} $1"; }

for arg in "$@"; do
  case "$arg" in
    --branch=*) BRANCH="${arg#*=}" ;;
  esac
done

log "=== Docker Deploy: branch=$BRANCH ==="

log "[1/6] Git pull..."
cd "$REPO_DIR"
git fetch "$REMOTE"
git checkout "$BRANCH"
git pull "$REMOTE" "$BRANCH"
COMMIT=$(git rev-parse --short HEAD)
log "  Commit: $COMMIT"

log "[2/6] 同步 .py 到 stable（不覆盖 *.json / .env）..."
mkdir -p "$STABLE_DIR"
rsync -a \
  --include='*/' \
  --include='*.py' \
  --include='requirements.txt' \
  --include='Dockerfile' \
  --include='docker-compose.yml' \
  --include='deploy-docker.sh' \
  --include='scripts/' \
  --include='scripts/**' \
  --include='static/' \
  --include='static/**' \
  --exclude='*.json' \
  --exclude='.env' \
  --exclude='*.html' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='.git/' \
  --exclude='*' \
  "$REPO_DIR/" "$STABLE_DIR/"

log "[3/6] 语法检查..."
cd "$STABLE_DIR"
python3 scripts/compile_all_py.py
python3 scripts/check_truncation.py
python3 scripts/verify_webhook_route.py

CACHE_JSON="$STABLE_DIR/orders_cache.json"
if [ ! -f "$CACHE_JSON" ]; then
  warn "  创建空占位 $CACHE_JSON（无历史订单时可忽略）"
  echo '{"orders":[],"report":{}}' > "$CACHE_JSON"
fi

log "[4/6] docker compose build..."
docker compose build

log "[5/6] docker compose up -d (network_mode=host，MYSQL_HOST 应为 127.0.0.1)..."
docker compose up -d

sleep 4

if [ -f "$CACHE_JSON" ]; then
  log "[5b] 订单缓存迁移（表空时 JSON/旧表 → MySQL）..."
  docker compose exec -T cs python scripts/migrate_orders_cache_to_mysql.py \
    --cache /app/orders_cache.json \
    || warn "  迁移跳过或失败，容器启动后仍会尝试自动迁移"
else
  warn "  未找到 $CACHE_JSON，跳过部署期迁移（依赖启动时 bootstrap）"
fi

log "[6/6] Webhook 探活..."
FAIL=0
for port in 3001 3002; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${port}/api/webhook/kuaimai" || echo "000")
  if [ "$code" = "200" ]; then
    log "  OK webhook :$port -> $code"
  else
    err "  FAIL webhook :$port -> $code"
    FAIL=1
  fi
done

[ "$FAIL" -eq 0 ] && log "SUCCESS commit=$COMMIT" || err "FAILURE"
exit "$FAIL"
