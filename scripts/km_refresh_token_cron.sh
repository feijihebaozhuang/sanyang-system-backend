#!/usr/bin/env bash
# 快麦 accessToken 续期（建议 crontab 每 25 天执行一次）
# 例：0 3 1,26 * * /www/feijihe/stable/scripts/km_refresh_token_cron.sh >> /var/log/km_token_refresh.log 2>&1
set -euo pipefail
STABLE="${STABLE_DIR:-/www/feijihe/stable}"
cd "$STABLE"
export KM_TOKEN_FILE="${KM_TOKEN_FILE:-$STABLE/km_token.json}"
python3 -c "import km_api; km_api.km_ensure_session(force=True); print('km token refresh ok')"
