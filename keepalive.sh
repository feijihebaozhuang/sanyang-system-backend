#!/bin/bash
# 三羊包装生产管理系统 - 自动保活脚本（每1分钟执行）
# 检测Flask服务是否运行，挂了就重启

APP_DIR="/www/wwwroot/feijihe"
PORT=3001

# 检查端口是否监听
if ! ss -tlnp | grep -q ":$PORT "; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 服务挂掉了，正在重启..."
    cd "$APP_DIR"
    (python3 app.py > /dev/null 2>&1 &)
    disown
    sleep 3
    if ss -tlnp | grep -q ":$PORT "; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 重启成功！"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 重启失败，再试一次..."
        sleep 2
        cd "$APP_DIR"
        (python3 app.py > /dev/null 2>&1 &)
        disown
        sleep 4
        if ss -tlnp | grep -q ":$PORT "; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 第二次重启成功！"
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 重启失败"
        fi
    fi
else
    # 顺便检查是否还能正常返回HTTP 200
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/ 2>/dev/null)
    if [ "$STATUS" != "200" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 服务端口在监听但HTTP返回$STATUS，可能僵死，杀掉重启..."
        OLD_PID=$(lsof -ti:$PORT 2>/dev/null)
        if [ -n "$OLD_PID" ]; then
            kill "$OLD_PID" 2>/dev/null
            sleep 2
        fi
        cd "$APP_DIR"
        (python3 app.py > /dev/null 2>&1 &)
        disown
        sleep 3
        if ss -tlnp | grep -q ":$PORT "; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 僵死恢复成功！"
        fi
    fi
fi
