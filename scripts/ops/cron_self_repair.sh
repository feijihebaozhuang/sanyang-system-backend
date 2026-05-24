#!/bin/bash
# 87 上 admin 用户 cron 用：每小时本机自我修复（小马哥配置一次即可）
# crontab -e 加一行：
# 0 * * * * /www/feijihe/stable/scripts/ops/cron_self_repair.sh >> /tmp/sanyang-self-repair.log 2>&1
set -euo pipefail
STABLE="${STABLE_DIR:-/www/feijihe/stable}"
ENV="$STABLE/.env"
[ -f "$ENV" ] || exit 0
TOK=$(grep ^FLASK_SECRET_KEY= "$ENV" | cut -d= -f2 | head -c 32)
[ -n "$TOK" ] || exit 0
curl -sf -X POST "http://127.0.0.1:3002/api/internal/self-repair?restart=0" \
  -H "X-Ops-Token: $TOK" || true
