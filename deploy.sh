#!/bin/bash
# ============================================================
# deploy.sh — 三羊系统一键部署（main → stable 3001/3002/3003）
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

# admin 跑 deploy 时必须 sudo systemctl（NOPASSWD 见 scripts/ops/setup_admin_nopasswd.sh）
_run_systemctl() {
    if [ "$(id -u)" -eq 0 ]; then
        systemctl "$@"
    elif sudo -n systemctl "$@" 2>/dev/null; then
        :
    else
        err "systemctl 需要 root 或 admin 免密 sudo"
        err "请 root 执行一次: bash $REPO_DIR/scripts/ops/setup_admin_nopasswd.sh"
        err "或: sudo bash $REPO_DIR/deploy.sh"
        exit 1
    fi
}

get_port_entry() {
    case "$1" in
        cs)       echo "3001:/www/feijihe/stable:app_cs.py" ;;
        prod)     echo "3002:/www/feijihe/stable:app_production.py" ;;
        customer) echo "3003:/www/feijihe/stable:app_customer_order.py" ;;
    esac
}

health_port() {
    local port=$1
    local timeout=${2:-3}
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port/api/health" 2>/dev/null || echo "000")
    [ "$code" = "200" ]
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

ROLLBACK_DIR="/tmp/sanyang_rollback_$(date +%s)"
SERVICES="cs prod customer"
SERVICE_NAMES="sanyang-cs.service sanyang-production.service sanyang-customer-order.service"

log "=== Deploy: branch=$BRANCH target=$TARGET_DIR (3001/3002/3003) ==="

# ========== 备份旧代码（用于回滚）==========
log "[0/5] Backing up current code to $ROLLBACK_DIR..."
mkdir -p "$ROLLBACK_DIR"
for app in $SERVICES; do
    entry=$(get_port_entry "$app")
    port=$(echo "$entry" | cut -d: -f1)
    script=$(echo "$entry" | cut -d: -f3)
    cp -f "$TARGET_DIR/$script" "$ROLLBACK_DIR/${script}.bak" 2>/dev/null || true
done
# 备份 HTML
for html in index.html index_cs.html index_production.html index_customer_order.html login_guanli.html main_app.html; do
    [ -f "$TARGET_DIR/$html" ] && cp -f "$TARGET_DIR/$html" "$ROLLBACK_DIR/${html}.bak"
done
# 备份 pytest.ini 和 tests/
[ -f "$TARGET_DIR/pytest.ini" ] && cp -f "$TARGET_DIR/pytest.ini" "$ROLLBACK_DIR/pytest.ini.bak"
[ -d "$TARGET_DIR/tests" ] && cp -r "$TARGET_DIR/tests" "$ROLLBACK_DIR/tests.bak"
log "  备份完成"

# ========== 拉取代码 ==========
log "[1/5] Git pull..."
cd "$REPO_DIR"
git fetch $REMOTE 2>&1 || { err "fetch failed"; exit 1; }
git checkout "$BRANCH" 2>&1 || { err "checkout failed"; exit 1; }
git pull $REMOTE "$BRANCH" 2>&1 || { err "pull failed"; exit 1; }
COMMIT=$(git rev-parse --short HEAD)
log "  Commit: $COMMIT ($BRANCH)"

# ========== 同步代码 ==========
log "[1b] Syncing code to $TARGET_DIR..."
# 铁律：只同步 .py / 脚本 / 测试，不覆盖服务器上 admin 维护的 JSON / .env
rsync -a \
  --include='*/' \
  --include='*.py' \
  --include='requirements.txt' \
  --include='deploy.sh' \
  --include='deploy/' \
  --include='deploy/**' \
  --include='deploy-docker.sh' \
  --include='Dockerfile' \
  --include='docker-compose.yml' \
  --include='.dockerignore' \
  --include='scripts/' \
  --include='scripts/**' \
  --include='tests/' \
  --include='tests/**' \
  --include='pytest.ini' \
  --exclude='*.json' \
  --exclude='.env' \
  --exclude='*.html' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='.git/' \
  --exclude='*' \
  "$REPO_DIR/" "$TARGET_DIR/"
log "  Python files / scripts / tests synced"

if [ -d "$REPO_DIR/static" ]; then
  rsync -a "$REPO_DIR/static/" "$TARGET_DIR/static/"
  log "  static/ synced"
fi
for html in index.html index_cs.html index_production.html index_customer_order.html login_guanli.html main_app.html; do
  if [ -f "$REPO_DIR/$html" ]; then
    cp -f "$REPO_DIR/$html" "$TARGET_DIR/$html"
    log "  $html copied"
  fi
done

# ========== 依赖安装 + 语法检查 ==========
log "[2/5] pip install..."
VENV_DIR="$TARGET_DIR/venv"
[ ! -f "$VENV_DIR/bin/activate" ] && python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
[ -f "$TARGET_DIR/requirements.txt" ] && pip install -r "$TARGET_DIR/requirements.txt" -q

log "[2b] Syntax check + validation..."
python3 -c "
import py_compile, sys, os
errors = []
target = '$TARGET_DIR'
for f in os.listdir(target):
    if f.endswith('.py'):
        try:
            py_compile.compile(os.path.join(target, f), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(str(e))
if errors:
    print('\\n'.join(errors))
    sys.exit(1)
" || { err "Python 语法检查失败，中止部署"; exit 1; }

# ========== 判断使用 systemd 还是后台进程 ==========
USE_SYSTEMD=0
if command -v systemctl >/dev/null 2>&1 \
    && systemctl list-unit-files sanyang-cs.service sanyang-production.service sanyang-customer-order.service >/dev/null 2>&1; then
    USE_SYSTEMD=1
fi

# ========== 重启 ==========
RESTART_FAILED=0
if [ "$USE_SYSTEMD" -eq 1 ]; then
    log "[3/5] Restart via systemd..."
    _run_systemctl daemon-reload 2>/dev/null || true
    for svc in sanyang-cs.service sanyang-production.service sanyang-customer-order.service; do
        _run_systemctl restart "$svc" || { err "  $svc 重启失败"; RESTART_FAILED=1; }
    done
    sleep 3
else
    log "[3/5] Stop old processes..."
    for app in $SERVICES; do
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
    for app in $SERVICES; do
        entry=$(get_port_entry "$app")
        IFS=':' read -r port dir script <<< "$entry"
        logfile="/tmp/app_${port}.log"
        log "  Starting: $dir/$script -> :$port"
        cd "$dir"
        nohup "$VENV_DIR/bin/python3" "$script" > "$logfile" 2>&1 &
        log "  PID=$! log=$logfile"
    done
    sleep 3
fi

# ========== 健康检查 ==========
log "[5/5] Health check (GET /api/health)..."
FAIL=0
for app in $SERVICES; do
    entry=$(get_port_entry "$app")
    port=$(echo "$entry" | cut -d: -f1)
    name=$(echo "$entry" | cut -d: -f3)
    ok=0
    for i in $(seq 1 10); do
        if health_port "$port"; then
            ok=1 && break
        fi
        sleep 2
    done
    if [ "$ok" -eq 1 ]; then
        log "  ✅ OK :$port ($name)"
    else
        err "  ❌ FAIL :$port ($name)"
        FAIL=1
    fi
done

# ========== 失败回滚 ==========
if [ "$FAIL" -eq 1 ] || [ "$RESTART_FAILED" -eq 1 ]; then
    err ""
    err "============================================"
    err "  部署失败！正在回滚到上一个版本..."
    err "============================================"
    warn "  回滚备份目录: $ROLLBACK_DIR"
    for app in $SERVICES; do
        entry=$(get_port_entry "$app")
        port=$(echo "$entry" | cut -d: -f1)
        script=$(echo "$entry" | cut -d: -f3)
        bak="$ROLLBACK_DIR/${script}.bak"
        if [ -f "$bak" ]; then
            cp -f "$bak" "$TARGET_DIR/$script"
            log "  回滚: $script"
        fi
    done
    for html in index.html index_cs.html index_production.html index_customer_order.html login_guanli.html main_app.html; do
        bak="$ROLLBACK_DIR/${html}.bak"
        [ -f "$bak" ] && cp -f "$bak" "$TARGET_DIR/$html" && log "  回滚: $html"
    done
    if [ -f "$ROLLBACK_DIR/pytest.ini.bak" ]; then
        cp -f "$ROLLBACK_DIR/pytest.ini.bak" "$TARGET_DIR/pytest.ini"
    fi
    if [ -d "$ROLLBACK_DIR/tests.bak" ]; then
        rm -rf "$TARGET_DIR/tests"
        cp -r "$ROLLBACK_DIR/tests.bak" "$TARGET_DIR/tests"
    fi

    warn "  回滚完成，重启旧版本..."
    if [ "$USE_SYSTEMD" -eq 1 ]; then
        for svc in $SERVICE_NAMES; do
            _run_systemctl restart "$svc" 2>/dev/null || true
        done
        sleep 3
    fi
    err "  请检查日志后重试部署"
    exit 1
fi

# ========== 部署成功 ==========
log ""
log "✅ SUCCESS commit=$COMMIT"
log "   3001(客服) /api/health → ✅"
log "   3002(生产) /api/health → ✅"
log "   3003(管理) /api/health → ✅"

# ========== 后置检查 ==========
log "[post] 运行自动化测试..."
if [ -d "$TARGET_DIR/tests" ]; then
    bash "$TARGET_DIR/tests/run.sh" 2>&1 || warn "  测试有失败项，不影响部署"
fi

log "[post] Nginx /api/ 反代检查..."
if command -v nginx >/dev/null 2>&1; then
    if sudo -n nginx -t 2>/dev/null; then
        sudo -n nginx -s reload 2>/dev/null && log "  Nginx reloaded" || warn "  Nginx reload 失败"
    fi
fi

log "部署完成 ✅"
exit 0
