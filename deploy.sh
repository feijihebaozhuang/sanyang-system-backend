#!/bin/bash
# ============================================================
# deploy.sh — 三羊系统部署脚本 v1
# 用法: ./deploy.sh stable        # 部署正式环境 (3001/3002)
#       ./deploy.sh dev           # 部署开发环境 (3003/3004)
# ============================================================
set -euo pipefail

REPO_DIR="/www/feijihe/repo"
REMOTE="origin"
DEFAULT_BRANCH_MAIN="main"
DEFAULT_BRANCH_DEV="dev"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ${NC} $1"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ${NC} $1"; }

get_port_entry() {
    local env="$1" app="$2"
    case "${env}:${app}" in
        stable:cs)    echo "3001:/www/feijihe/stable:app_cs.py" ;;
        stable:prod)  echo "3002:/www/feijihe/stable:app_production.py" ;;
        dev:cs)       echo "3003:/www/feijihe/dev:app_cs.py" ;;
        dev:prod)     echo "3004:/www/feijihe/dev:app_production.py" ;;
    esac
}

get_env_dir() {
    case "$1" in
        stable) echo "/www/feijihe/stable" ;;
        dev)    echo "/www/feijihe/dev" ;;
    esac
}

ENV="${1:?Usage: $0 {stable|dev}}"
if [ "$ENV" != "stable" ] && [ "$ENV" != "dev" ]; then
    err "Environment must be stable or dev"
    exit 1
fi

BRANCH=""
if [ "$ENV" = "stable" ]; then
    BRANCH="$DEFAULT_BRANCH_MAIN"
else
    BRANCH="$DEFAULT_BRANCH_DEV"
fi
for arg in "$@"; do
    if [[ "$arg" == --branch=* ]]; then
        BRANCH="${arg#*=}"
    fi
done

TARGET_DIR=$(get_env_dir "$ENV")

log "=== Deploy: env=$ENV branch=$BRANCH target=$TARGET_DIR ==="

# Step 1
log "[1/5] Git pull..."
cd "$REPO_DIR"
git fetch $REMOTE 2>&1 || { err "fetch failed"; exit 1; }
git checkout "$BRANCH" 2>&1 || { err "checkout failed"; exit 1; }
git pull $REMOTE "$BRANCH" 2>&1 || { err "pull failed"; exit 1; }
COMMIT=$(git rev-parse --short HEAD)
log "  Commit: $COMMIT ($BRANCH)"
rsync -a --delete --exclude=venv/ --exclude=__pycache__/ --exclude='*.pyc' --exclude=orders_cache.json --exclude=data.json --exclude=dimoldb.json --exclude=inventory.json --exclude='*.log' --exclude=.git/ "$REPO_DIR/" "$TARGET_DIR/"
log "  Code synced"

# Step 2
log "[2/5] pip install..."
VENV_DIR="$TARGET_DIR/venv"
[ ! -f "$VENV_DIR/bin/activate" ] && python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
[ -f "$TARGET_DIR/requirements.txt" ] && pip install -r "$TARGET_DIR/requirements.txt" -q

# Step 3
log "[3/5] Stop old processes..."
for app in cs prod; do
    entry=$(get_port_entry "$ENV" "$app")
    [ -z "$entry" ] && continue
    port=$(echo "$entry" | cut -d: -f1)
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    [ -z "$pids" ] && log "  port $port: not running" && continue
    kill "$pids" 2>/dev/null || true
    sleep 2
    lsof -ti :"$port" >/dev/null 2>&1 && kill -9 "$pids" 2>/dev/null || true
    log "  port $port: stopped"
done

# Step 4
log "[4/5] Start new processes..."
for app in cs prod; do
    entry=$(get_port_entry "$ENV" "$app")
    [ -z "$entry" ] && continue
    IFS=':' read -r port dir script <<< "$entry"
    logfile="/tmp/app_${port}.log"
    log "  Starting: $dir/$script -> :$port"
    cd "$dir"
    source "$VENV_DIR/bin/activate"
    setsid python3 "$script" > "$logfile" 2>&1 &
    log "  PID=$! log=$logfile"
done
sleep 3

# Step 5
log "[5/5] Health check..."
FAIL=0
for app in cs prod; do
    entry=$(get_port_entry "$ENV" "$app")
    [ -z "$entry" ] && continue
    port=$(echo "$entry" | cut -d: -f1)
    ok=0
    for i in $(seq 1 6); do
        code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port/" 2>/dev/null || echo "000")
        [ "$code" = "200" ] || [ "$code" = "302" ] || [ "$code" = "301" ] && ok=1 && break
        sleep 2
    done
    [ "$ok" -eq 1 ] && log "  OK :$port" || { err "  FAIL :$port"; FAIL=1; }
done

[ "$FAIL" -eq 0 ] && log "SUCCESS env=$ENV commit=$COMMIT" || err "FAILURE - check logs, no auto-rollback"
exit $FAIL
