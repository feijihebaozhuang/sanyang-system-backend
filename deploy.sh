#!/bin/bash
# ============================================================
# deploy.sh — 三羊系统部署（仅 main → stable 3001/3002）
# 用法: ./deploy.sh [stable] [--branch=main]
# 本地开发: git pull origin main（见 pull-main.ps1）
# ============================================================
set -euo pipefail

REPO_DIR="/www/feijihe/repo"
REMOTE="origin"
BRANCH="main"
TARGET_DIR="/www/feijihe/stable"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ${NC} $1"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ${NC} $1"; }

get_port_entry() {
    case "$1" in
        cs)   echo "3001:/www/feijihe/stable:app_cs.py" ;;
        prod) echo "3002:/www/feijihe/stable:app_production.py" ;;
    esac
}

for arg in "$@"; do
    case "$arg" in
        stable|--stable) ;;
        --branch=*) BRANCH="${arg#*=}" ;;
        dev)
            err "已取消开发环境。请使用: ./deploy.sh"
            exit 1
            ;;
        *)
            if [ "$arg" != "stable" ] && [[ "$arg" != --branch=* ]]; then
                err "未知参数: $arg"
                err "用法: $0 [stable] [--branch=main]"
                exit 1
            fi
            ;;
    esac
done

log "=== Deploy: branch=$BRANCH target=$TARGET_DIR (3001/3002) ==="

log "[1/5] Git pull..."
cd "$REPO_DIR"
git fetch $REMOTE 2>&1 || { err "fetch failed"; exit 1; }
git checkout "$BRANCH" 2>&1 || { err "checkout failed"; exit 1; }
git pull $REMOTE "$BRANCH" 2>&1 || { err "pull failed"; exit 1; }
COMMIT=$(git rev-parse --short HEAD)
log "  Commit: $COMMIT ($BRANCH)"
# 铁律：只同步 .py / 脚本，不覆盖服务器上 admin 维护的 JSON / .env / HTML
rsync -a \
  --include='*/' \
  --include='*.py' \
  --include='requirements.txt' \
  --include='deploy.sh' \
  --include='deploy-docker.sh' \
  --include='Dockerfile' \
  --include='docker-compose.yml' \
  --include='.dockerignore' \
  --include='scripts/' \
  --include='scripts/**' \
  --exclude='*.json' \
  --exclude='.env' \
  --exclude='*.html' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='.git/' \
  --exclude='*' \
  "$REPO_DIR/" "$TARGET_DIR/"
log "  Code synced (.py only; JSON 保留在 stable 目录)"

if [ -d "$REPO_DIR/static" ]; then
  rsync -a "$REPO_DIR/static/" "$TARGET_DIR/static/"
  log "  static/ synced (auth_session.js, prod_ui.js, …)"
fi
for html in index.html index_cs.html; do
  if [ -f "$REPO_DIR/$html" ]; then
    cp -f "$REPO_DIR/$html" "$TARGET_DIR/$html"
    log "  $html copied"
  fi
done
if [ -f "$REPO_DIR/index_production.html" ]; then
  cp -f "$REPO_DIR/index_production.html" "$TARGET_DIR/index_production.html"
fi

log "[2/5] pip install..."
VENV_DIR="$TARGET_DIR/venv"
[ ! -f "$VENV_DIR/bin/activate" ] && python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
[ -f "$TARGET_DIR/requirements.txt" ] && pip install -r "$TARGET_DIR/requirements.txt" -q

if [ -f "$TARGET_DIR/scripts/migrate_orders_cache_to_mysql.py" ]; then
  log "[2b] 订单缓存 → MySQL（表空时：JSON / 旧表 orders_cache）..."
  MIGRATE_ARGS=()
  CACHE_JSON="$TARGET_DIR/orders_cache.json"
  [ -f "$CACHE_JSON" ] && MIGRATE_ARGS+=(--cache "$CACHE_JSON")
  python3 "$TARGET_DIR/scripts/migrate_orders_cache_to_mysql.py" "${MIGRATE_ARGS[@]}" \
    || warn "  迁移跳过或失败，可稍后手动: migrate_orders_cache_to_mysql.py --from-table orders_cache"
fi

log "[2c] Python compile check (all .py)..."
python3 "$TARGET_DIR/scripts/compile_all_py.py" || { err "语法检查失败，中止部署"; exit 1; }
python3 "$TARGET_DIR/scripts/check_truncation.py" || { err "截断模式检查失败，中止部署"; exit 1; }
python3 "$TARGET_DIR/scripts/verify_webhook_route.py" || { err "Webhook 路由未注册，中止部署"; exit 1; }

log "[3/5] Stop old processes..."
for app in cs prod; do
    entry=$(get_port_entry "$app")
    port=$(echo "$entry" | cut -d: -f1)
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    [ -z "$pids" ] && log "  port $port: not running" && continue
    kill "$pids" 2>/dev/null || true
    sleep 2
    lsof -ti :"$port" >/dev/null 2>&1 && kill -9 "$pids" 2>/dev/null || true
    log "  port $port: stopped"
done

log "[4/5] Start new processes..."
for app in cs prod; do
    entry=$(get_port_entry "$app")
    IFS=':' read -r port dir script <<< "$entry"
    logfile="/tmp/app_${port}.log"
    log "  Starting: $dir/$script -> :$port"
    cd "$dir"
    source "$VENV_DIR/bin/activate"
    nohup python3 "$script" > "$logfile" 2>&1 &
    log "  PID=$! log=$logfile"
done
sleep 3

log "[5/5] Health check..."
FAIL=0
for app in cs prod; do
    entry=$(get_port_entry "$app")
    port=$(echo "$entry" | cut -d: -f1)
    ok=0
    for i in $(seq 1 6); do
        code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port/" 2>/dev/null || echo "000")
        [ "$code" = "200" ] || [ "$code" = "302" ] || [ "$code" = "301" ] && ok=1 && break
        sleep 2
    done
    [ "$ok" -eq 1 ] && log "  OK :$port" || { err "  FAIL :$port"; FAIL=1; }
done

[ "$FAIL" -eq 0 ] && log "SUCCESS commit=$COMMIT" || err "FAILURE - check logs"
exit $FAIL
