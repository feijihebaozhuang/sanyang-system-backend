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
rsync -a --delete \
  --exclude=venv/ --exclude=__pycache__/ --exclude='*.pyc' \
  --exclude=orders_cache.json --exclude=data.json --exclude=dimoldb.json --exclude=inventory.json \
  --exclude='*.log' --exclude=.git/ \
  --exclude=.env --exclude=alibaba_shops.json --exclude=km_token.json \
  "$REPO_DIR/" "$TARGET_DIR/"
log "  Code synced"

log "[2/5] pip install..."
VENV_DIR="$TARGET_DIR/venv"
[ ! -f "$VENV_DIR/bin/activate" ] && python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
[ -f "$TARGET_DIR/requirements.txt" ] && pip install -r "$TARGET_DIR/requirements.txt" -q

CACHE_JSON="$TARGET_DIR/orders_cache.json"
if [ -f "$CACHE_JSON" ] && [ -f "$TARGET_DIR/scripts/migrate_orders_cache_to_mysql.py" ]; then
  log "[2b] orders_cache.json → MySQL（表空时自动导入）..."
  python3 "$TARGET_DIR/scripts/migrate_orders_cache_to_mysql.py" --cache "$CACHE_JSON" \
    || warn "  迁移跳过或失败，可稍后手动执行 migrate_orders_cache_to_mysql.py"
fi

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
